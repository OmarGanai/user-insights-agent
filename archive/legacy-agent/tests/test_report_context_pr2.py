import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from services.report_context import (
    build_ios_release_context,
    load_ios_release_notes,
    load_context_sections,
    read_ios_release_log,
    refresh_ios_release_log,
)


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class ReportContextPR2Test(unittest.TestCase):
    def test_load_context_sections_prefers_split_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            base_path = root / "base.md"
            weekly_path = root / "weekly.md"
            legacy_path = root / "legacy.md"
            base_path.write_text("Base context", encoding="utf-8")
            weekly_path.write_text("Weekly context", encoding="utf-8")
            legacy_path.write_text("Legacy context", encoding="utf-8")

            sections = load_context_sections(
                base_context_path=base_path,
                activation_context_path=weekly_path,
                legacy_context_path=legacy_path,
            )

            self.assertEqual(sections["context_source"], "split")
            self.assertEqual(sections["base_app_context"], "Base context")
            self.assertEqual(sections["activation_weekly_context"], "Weekly context")

    def test_load_context_sections_falls_back_to_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            legacy_path = root / "legacy.md"
            legacy_path.write_text("Legacy context", encoding="utf-8")

            sections = load_context_sections(
                base_context_path=root / "missing-base.md",
                activation_context_path=root / "missing-weekly.md",
                legacy_context_path=legacy_path,
            )

            self.assertEqual(sections["context_source"], "legacy_fallback")
            self.assertEqual(sections["base_app_context"], "Legacy context")
            self.assertEqual(sections["activation_weekly_context"], "")

    def test_refresh_ios_release_log_dedupes_version_and_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "ios-releases.md"
            payload = {
                "results": [
                    {
                        "version": "1.2.3",
                        "buildVersion": "456",
                        "currentVersionReleaseDate": "2026-02-19T15:04:05Z",
                    }
                ]
            }

            first = refresh_ios_release_log(
                lookup_url="https://itunes.apple.com/lookup?id=6480279827",
                log_path=log_path,
                http_get=lambda *_args, **_kwargs: _FakeResponse(payload),
                now_utc=datetime(2026, 2, 20, 1, 2, 3, tzinfo=timezone.utc),
            )
            second = refresh_ios_release_log(
                lookup_url="https://itunes.apple.com/lookup?id=6480279827",
                log_path=log_path,
                http_get=lambda *_args, **_kwargs: _FakeResponse(payload),
                now_utc=datetime(2026, 2, 20, 2, 3, 4, tzinfo=timezone.utc),
            )

            self.assertEqual(first["status"], "updated")
            self.assertEqual(second["status"], "unchanged")

            rows = read_ios_release_log(log_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["dedupe_key"], "1.2.3+456")
            self.assertEqual(rows[0]["dedupe_basis"], "version+build")

    def test_build_ios_release_context_uses_release_date_fallback_key_when_build_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "ios-releases.md"
            payload = {
                "results": [
                    {
                        "version": "2.0.0",
                        "currentVersionReleaseDate": "2026-02-18T00:00:00Z",
                    }
                ]
            }

            context = build_ios_release_context(
                lookup_url="https://itunes.apple.com/lookup?id=6480279827",
                log_path=log_path,
                http_get=lambda *_args, **_kwargs: _FakeResponse(payload),
            )

            self.assertEqual(context["ingestion_status"], "updated")
            self.assertTrue(context["recent_releases"])
            self.assertEqual(context["recent_releases"][0]["dedupe_basis"], "version+release_date")
            self.assertIn("2.0.0+2026-02-18", context["recent_releases"][0]["dedupe_key"])

    def test_load_ios_release_notes_returns_loaded_with_valid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            notes_path = Path(tmp_dir) / "ios-release-notes.yaml"
            notes_path.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "releases:",
                        "  - version: '2.3.2'",
                        "    release_date: '2026-02-04'",
                        "    highlights:",
                        "      - 'Chat with tenant right from your Time and People tabs.'",
                        "  - version: '2.3.1'",
                        "    release_date: '2026-01-23'",
                        "    highlights:",
                        "      - 'Upload larger documents with no size headaches.'",
                    ]
                ),
                encoding="utf-8",
            )

            result = load_ios_release_notes(notes_path=notes_path)

            self.assertEqual(result["status"], "loaded")
            self.assertEqual(result["error"], "")
            self.assertEqual(len(result["recent_release_notes"]), 2)
            self.assertEqual(result["recent_release_notes"][0]["version"], "2.3.2")
            self.assertTrue(result["recent_release_notes"][0]["highlights"])

    def test_build_ios_release_context_merges_curated_notes_by_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "ios-releases.md"
            notes_path = Path(tmp_dir) / "ios-release-notes.yaml"
            notes_path.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "releases:",
                        "  - version: '2.3.2'",
                        "    release_date: '2026-02-04'",
                        "    highlights:",
                        "      - 'Chat with tenant right from your Time and People tabs.'",
                        "  - version: '2.2.0'",
                        "    release_date: '2025-12-01'",
                        "    highlights:",
                        "      - 'Legacy note.'",
                    ]
                ),
                encoding="utf-8",
            )
            payload = {
                "results": [
                    {
                        "version": "2.3.2",
                        "currentVersionReleaseDate": "2026-02-04T20:04:25Z",
                    }
                ]
            }

            context = build_ios_release_context(
                lookup_url="https://itunes.apple.com/lookup?id=6480279827",
                log_path=log_path,
                notes_path=notes_path,
                http_get=lambda *_args, **_kwargs: _FakeResponse(payload),
            )

            self.assertEqual(context["release_notes_ingestion_status"], "loaded")
            self.assertEqual(context["release_notes_ingestion_error"], "")
            self.assertTrue(context["recent_release_notes"])
            self.assertTrue(context["recent_releases_with_notes"])
            merged = context["recent_releases_with_notes"][0]
            self.assertTrue(merged["notes_available"])
            self.assertIn("Chat with tenant", merged["highlights"][0])

    def test_build_ios_release_context_handles_missing_or_invalid_notes_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "ios-releases.md"
            missing_notes_path = Path(tmp_dir) / "missing-ios-release-notes.yaml"
            payload = {
                "results": [
                    {
                        "version": "2.3.2",
                        "currentVersionReleaseDate": "2026-02-04T20:04:25Z",
                    }
                ]
            }

            missing_context = build_ios_release_context(
                lookup_url="https://itunes.apple.com/lookup?id=6480279827",
                log_path=log_path,
                notes_path=missing_notes_path,
                http_get=lambda *_args, **_kwargs: _FakeResponse(payload),
            )
            self.assertEqual(missing_context["ingestion_status"], "updated")
            self.assertEqual(missing_context["release_notes_ingestion_status"], "missing")
            self.assertEqual(missing_context["recent_release_notes"], [])

            invalid_notes_path = Path(tmp_dir) / "invalid-ios-release-notes.yaml"
            invalid_notes_path.write_text("releases: [broken", encoding="utf-8")

            invalid_context = build_ios_release_context(
                lookup_url="https://itunes.apple.com/lookup?id=6480279827",
                log_path=log_path,
                notes_path=invalid_notes_path,
                http_get=lambda *_args, **_kwargs: _FakeResponse(payload),
            )
            self.assertEqual(invalid_context["ingestion_status"], "unchanged")
            self.assertEqual(invalid_context["release_notes_ingestion_status"], "error")
            self.assertTrue(invalid_context["release_notes_ingestion_error"])


if __name__ == "__main__":
    unittest.main()
