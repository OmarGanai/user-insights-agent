#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

_BANNED_TOKENS = (
    "ee" + "va",
    "ee" + "va-prod",
    "ee" + "va-ai",
)
BANNED_IDENTIFIER_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(token) for token in _BANNED_TOKENS) + r")\b",
    re.IGNORECASE,
)
DEFAULT_EXCLUDES = [
    ".git/**",
    "**/.git/**",
    "tmp/**",
    "workspace/**",
    "**/.DS_Store",
    "amplitude-insights-bot/.env",
    "scripts/public_safety_scan.py",
    "tests/test_public_safety_scan.py",
]
DEFAULT_RUNTIME_ARTIFACT_GLOBS = [
    "tmp/**",
    "workspace/tenants/*/runs/**",
    "workspace/tenants/*/events/events.ndjson",
    "**/pipeline-debug/**",
]


def _iter_files(root: Path, excludes: Sequence[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if any(fnmatch.fnmatch(rel, pattern) for pattern in excludes):
            continue
        yield path


def scan_identifiers(
    root: Path,
    excludes: Sequence[str] = DEFAULT_EXCLUDES,
    pattern: re.Pattern[str] = BANNED_IDENTIFIER_PATTERN,
) -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
    for path in _iter_files(root, excludes):
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                findings.append({"path": rel, "line": index, "text": line.strip()})
    return findings


def scan_runtime_artifacts(
    root: Path,
    artifact_globs: Sequence[str] = DEFAULT_RUNTIME_ARTIFACT_GLOBS,
    candidate_paths: Optional[Sequence[str]] = None,
) -> List[str]:
    findings: List[str] = []
    if candidate_paths is not None:
        rel_paths = [path.replace("\\", "/") for path in candidate_paths]
    else:
        rel_paths = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel_paths.append(str(path.relative_to(root)).replace("\\", "/"))

    for rel in rel_paths:
        if any(fnmatch.fnmatch(rel, pattern) for pattern in artifact_globs):
            findings.append(rel)
    return sorted(set(findings))


def _git_tracked_files(root: Path) -> List[str]:
    git_dir = root / ".git"
    if not git_dir.exists():
        return []

    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return []

    paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return paths


def run_scan(root: Path) -> Tuple[List[Dict[str, object]], List[str]]:
    identifier_findings = scan_identifiers(root)
    tracked_files = _git_tracked_files(root)
    artifact_findings = scan_runtime_artifacts(root, candidate_paths=tracked_files) if tracked_files else []
    return identifier_findings, artifact_findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan repository for tenant-specific identifiers and runtime artifacts")
    parser.add_argument("--root", default=".", help="Project root to scan")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    identifier_findings, artifact_findings = run_scan(root)

    if identifier_findings:
        print("Banned tenant identifier findings:")
        for finding in identifier_findings:
            print(f"- {finding['path']}:{finding['line']} {finding['text']}")

    if artifact_findings:
        print("Tracked runtime artifact findings:")
        for path in artifact_findings:
            print(f"- {path}")

    if identifier_findings or artifact_findings:
        return 1

    print("Public-safety scan passed: no banned identifiers or runtime artifacts found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
