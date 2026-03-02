import tempfile
import unittest
from pathlib import Path

from scripts.public_safety_scan import run_scan, scan_identifiers, scan_runtime_artifacts


class PublicSafetyScanTest(unittest.TestCase):
    def test_identifier_scan_detects_banned_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "docs").mkdir(parents=True)
            banned_token = "ee" + "va-prod"
            (root / "docs" / "note.md").write_text(f"This mentions {banned_token} data.", encoding="utf-8")

            findings = scan_identifiers(root)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["path"], "docs/note.md")

    def test_runtime_artifact_scan_detects_workspace_runs_and_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "tmp").mkdir(parents=True)
            (root / "tmp" / "debug.json").write_text("{}", encoding="utf-8")
            event_path = root / "workspace" / "tenants" / "tenant-x" / "events"
            event_path.mkdir(parents=True)
            (event_path / "events.ndjson").write_text("{}\n", encoding="utf-8")

            findings = scan_runtime_artifacts(root)
            self.assertIn("tmp/debug.json", findings)
            self.assertIn("workspace/tenants/tenant-x/events/events.ndjson", findings)

    def test_run_scan_passes_when_repo_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "README.md").write_text("Generic tenant-safe docs", encoding="utf-8")

            identifiers, artifacts = run_scan(root)
            self.assertEqual(identifiers, [])
            self.assertEqual(artifacts, [])

    def test_identifier_scan_ignores_retired_legacy_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            legacy_dir = root / "amplitude-insights-bot"
            legacy_dir.mkdir(parents=True)
            banned_token = "ee" + "va-ai"
            (legacy_dir / "legacy.md").write_text(
                f"Legacy private note with {banned_token} token.",
                encoding="utf-8",
            )

            findings = scan_identifiers(root)
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
