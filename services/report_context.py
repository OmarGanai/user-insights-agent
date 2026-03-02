from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency fallback
    yaml = None


IOS_APP_ID = "6480279827"
IOS_LOOKUP_URL = f"https://itunes.apple.com/lookup?id={IOS_APP_ID}"

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_APP_CONTEXT_PATH = REPO_ROOT / "app-context.md"
BASE_APP_CONTEXT_PATH = REPO_ROOT / "docs" / "context" / "base-app-context.md"
ACTIVATION_WEEKLY_CONTEXT_PATH = REPO_ROOT / "docs" / "context" / "activation-weekly-context.md"
IOS_RELEASE_LOG_PATH = REPO_ROOT / "docs" / "ios-releases.md"
IOS_RELEASE_NOTES_PATH = REPO_ROOT / "docs" / "ios-release-notes.yaml"


def load_context_sections(
    base_context_path: Path = BASE_APP_CONTEXT_PATH,
    activation_context_path: Path = ACTIVATION_WEEKLY_CONTEXT_PATH,
    legacy_context_path: Path = LEGACY_APP_CONTEXT_PATH,
) -> Dict[str, str]:
    base_context = _read_text_file(base_context_path)
    activation_context = _read_text_file(activation_context_path)

    if base_context or activation_context:
        return {
            "base_app_context": base_context,
            "activation_weekly_context": activation_context,
            "context_source": "split",
        }

    legacy_context = _read_text_file(legacy_context_path)
    if legacy_context:
        return {
            "base_app_context": legacy_context,
            "activation_weekly_context": "",
            "context_source": "legacy_fallback",
        }

    return {
        "base_app_context": "",
        "activation_weekly_context": "",
        "context_source": "none",
    }


def refresh_ios_release_log(
    lookup_url: str = IOS_LOOKUP_URL,
    log_path: Path = IOS_RELEASE_LOG_PATH,
    http_get: Callable[..., requests.Response] = requests.get,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    fetched_at = _format_utc(now_utc or datetime.now(timezone.utc))
    existing_entries = read_ios_release_log(log_path)

    try:
        response = http_get(lookup_url, timeout=20)
        response.raise_for_status()
        payload = response.json()
        latest_release = _parse_latest_release(payload, fetched_at=fetched_at)
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "status": "error",
            "lookup_url": lookup_url,
            "log_path": str(log_path),
            "error": _truncate_error(str(exc) or "lookup failed"),
            "recent_releases": existing_entries[:5],
        }

    known_keys = {entry.get("dedupe_key", "") for entry in existing_entries}
    if latest_release["dedupe_key"] in known_keys:
        return {
            "status": "unchanged",
            "lookup_url": lookup_url,
            "log_path": str(log_path),
            "latest_release": latest_release,
            "recent_releases": existing_entries[:5],
        }

    merged_entries = [latest_release] + existing_entries
    try:
        _write_ios_release_log(log_path=log_path, entries=merged_entries)
    except OSError as exc:
        return {
            "status": "error",
            "lookup_url": lookup_url,
            "log_path": str(log_path),
            "error": f"failed to write ios release log: {_truncate_error(str(exc))}",
            "latest_release": latest_release,
            "recent_releases": merged_entries[:5],
        }

    return {
        "status": "updated",
        "lookup_url": lookup_url,
        "log_path": str(log_path),
        "latest_release": latest_release,
        "recent_releases": merged_entries[:5],
    }


def build_ios_release_context(
    lookup_url: str = IOS_LOOKUP_URL,
    log_path: Path = IOS_RELEASE_LOG_PATH,
    notes_path: Path = IOS_RELEASE_NOTES_PATH,
    http_get: Callable[..., requests.Response] = requests.get,
) -> Dict[str, Any]:
    refresh_result = refresh_ios_release_log(
        lookup_url=lookup_url,
        log_path=log_path,
        http_get=http_get,
    )
    recent_releases = refresh_result.get("recent_releases")
    if not isinstance(recent_releases, list):
        recent_releases = read_ios_release_log(log_path)[:5]
    notes_result = load_ios_release_notes(notes_path=notes_path)
    recent_release_notes = notes_result.get("recent_release_notes")
    if not isinstance(recent_release_notes, list):
        recent_release_notes = []
    merged_releases = _merge_releases_with_notes(
        recent_releases=recent_releases,
        recent_release_notes=recent_release_notes,
    )

    return {
        "app_id": IOS_APP_ID,
        "lookup_url": lookup_url,
        "release_log_path": str(log_path),
        "release_notes_path": str(notes_path),
        "ingestion_status": str(refresh_result.get("status") or "unknown"),
        "ingestion_error": str(refresh_result.get("error") or "").strip(),
        "dedupe_policy": "version+build (fallback: version+release_date when build is unavailable)",
        "recent_releases": recent_releases[:5],
        "release_notes_ingestion_status": str(notes_result.get("status") or "unknown"),
        "release_notes_ingestion_error": str(notes_result.get("error") or "").strip(),
        "recent_release_notes": recent_release_notes[:5],
        "recent_releases_with_notes": merged_releases[:5],
    }


def load_ios_release_notes(notes_path: Path = IOS_RELEASE_NOTES_PATH) -> Dict[str, Any]:
    raw_text = _read_text_file(notes_path)
    if not raw_text:
        return {
            "status": "missing",
            "error": "",
            "recent_release_notes": [],
        }

    try:
        payload = _parse_json_or_yaml(raw_text)
        notes = _normalize_release_notes_payload(payload)
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "status": "error",
            "error": _truncate_error(str(exc) or "failed to parse release notes"),
            "recent_release_notes": [],
        }

    return {
        "status": "loaded",
        "error": "",
        "recent_release_notes": notes[:5],
    }


def read_ios_release_log(log_path: Path = IOS_RELEASE_LOG_PATH) -> List[Dict[str, str]]:
    text = _read_text_file(log_path)
    if not text:
        return []

    entries: List[Dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0].lower() == "version":
            continue
        version, build, release_date, dedupe_key, fetched_at = cells[:5]
        if not version:
            continue
        entries.append(
            {
                "version": version,
                "build": "" if build == "-" else build,
                "release_date": "" if release_date == "-" else release_date,
                "dedupe_key": dedupe_key,
                "dedupe_basis": "version+build"
                if build and build != "-"
                else "version+release_date",
                "fetched_at_utc": "" if fetched_at == "-" else fetched_at,
            }
        )
    return entries


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _parse_json_or_yaml(raw_text: str) -> Any:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        if yaml is None:
            raise ValueError(
                "iOS release notes file is not valid JSON and PyYAML is not installed."
            ) from None

    parsed = yaml.safe_load(raw_text)
    if parsed is None:
        raise ValueError("iOS release notes file is empty after parsing.")
    return parsed


def _normalize_release_notes_payload(payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("iOS release notes must parse to an object with a 'releases' list.")

    raw_releases = payload.get("releases")
    if not isinstance(raw_releases, list):
        raise ValueError("iOS release notes are missing a valid 'releases' list.")

    normalized: List[Dict[str, Any]] = []
    seen_versions = set()
    for raw_release in raw_releases:
        if not isinstance(raw_release, dict):
            continue

        version = _clean_value(raw_release.get("version"))
        if not version or version in seen_versions:
            continue

        highlights = _normalize_string_list(raw_release.get("highlights") or raw_release.get("notes"), limit=12)
        if not highlights:
            continue

        entry: Dict[str, Any] = {
            "version": version,
            "release_date": _clean_value(raw_release.get("release_date") or raw_release.get("date")),
            "highlights": highlights,
        }

        summary = _clean_value(raw_release.get("summary"))
        if summary:
            entry["summary"] = _truncate_text(summary, limit=300)

        impact_tags = _normalize_string_list(raw_release.get("impact_tags"), limit=10)
        if impact_tags:
            entry["impact_tags"] = impact_tags

        normalized.append(entry)
        seen_versions.add(version)

    return normalized


def _normalize_string_list(value: Any, limit: int) -> List[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = [str(item) for item in value]
    else:
        return []

    normalized: List[str] = []
    for candidate in candidates:
        cleaned = _clean_value(candidate)
        if not cleaned:
            continue
        normalized.append(_truncate_text(cleaned, limit=300))
        if len(normalized) >= limit:
            break
    return normalized


def _merge_releases_with_notes(
    recent_releases: List[Dict[str, str]],
    recent_release_notes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    notes_by_version: Dict[str, Dict[str, Any]] = {}
    for note in recent_release_notes:
        if not isinstance(note, dict):
            continue
        version = _clean_value(note.get("version"))
        if not version:
            continue
        notes_by_version[version] = note

    merged: List[Dict[str, Any]] = []
    for raw_release in recent_releases[:5]:
        if not isinstance(raw_release, dict):
            continue
        release = dict(raw_release)
        version = _clean_value(release.get("version"))
        note = notes_by_version.get(version)
        if note:
            release["notes_available"] = True
            release["highlights"] = note.get("highlights") or []
            if note.get("summary"):
                release["summary"] = note.get("summary")
            if note.get("impact_tags"):
                release["impact_tags"] = note.get("impact_tags")
            if note.get("release_date"):
                release["curated_release_date"] = note.get("release_date")
        else:
            release["notes_available"] = False
        merged.append(release)
    return merged


def _parse_latest_release(payload: Dict[str, Any], fetched_at: str) -> Dict[str, str]:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results:
        raise ValueError("apple lookup response missing results")
    item = results[0] if isinstance(results[0], dict) else {}
    version = _clean_value(item.get("version"))
    if not version:
        raise ValueError("apple lookup response missing version")

    build = _first_non_empty(
        item,
        keys=("build", "buildVersion", "bundleVersion", "softwareVersionExternalIdentifier"),
    )
    release_date = _normalize_release_date(
        _first_non_empty(item, keys=("currentVersionReleaseDate", "releaseDate"))
    )

    if build:
        dedupe_basis = "version+build"
        dedupe_key = f"{version}+{build}"
    else:
        dedupe_basis = "version+release_date"
        fallback_date = release_date or "unknown_date"
        dedupe_key = f"{version}+{fallback_date}"

    return {
        "version": version,
        "build": build,
        "release_date": release_date,
        "dedupe_key": dedupe_key,
        "dedupe_basis": dedupe_basis,
        "fetched_at_utc": fetched_at,
    }


def _first_non_empty(item: Dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _clean_value(item.get(key))
        if value:
            return value
    return ""


def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    cleaned = str(value).strip()
    return cleaned.replace("\n", " ").replace("|", "/")


def _normalize_release_date(value: str) -> str:
    if not value:
        return ""
    try:
        normalized = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return _format_utc(normalized)


def _write_ios_release_log(log_path: Path, entries: List[Dict[str, str]]) -> None:
    lines = [
        "# iOS Releases",
        "",
        "Auto-updated by the weekly report pipeline.",
        "",
        f"Source: `{IOS_LOOKUP_URL}`",
        "",
        "Deduplication key: `version + build`; fallback: `version + release_date` when build is unavailable.",
        "",
        "| Version | Build | Release Date (UTC) | Dedupe Key | Fetched At (UTC) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        lines.append(
            "| {version} | {build} | {release_date} | {dedupe_key} | {fetched_at} |".format(
                version=entry.get("version") or "-",
                build=entry.get("build") or "-",
                release_date=entry.get("release_date") or "-",
                dedupe_key=entry.get("dedupe_key") or "-",
                fetched_at=entry.get("fetched_at_utc") or "-",
            )
        )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truncate_error(value: str, limit: int = 180) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _truncate_text(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
