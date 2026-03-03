import tempfile
import unittest
from pathlib import Path

from agent_runtime.context_injection import ContextInjector
from agent_runtime.store import FileWorkspaceStore


class ContextInjectionTest(unittest.TestCase):
    def test_context_injection_contains_required_dynamic_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = FileWorkspaceStore(root=Path(tmp_dir) / "workspace")
            session = store.create_session(
                tenant_id="tenant-context",
                objective="Generate digest",
                prompt_profile="default",
                mode="hybrid",
            )
            store.create_task(session_id=session["id"], title="Collect metrics", metadata={"stage": "collect"})
            store.create_artifact(
                run_id=session["id"],
                kind="slack_payload",
                rel_path="outputs/slack_payload.json",
                content={"text": "Preview", "blocks": []},
            )
            store.append_message(session_id=session["id"], role="user", content="Generate weekly digest", meta={})

            injector = ContextInjector(store=store)
            snapshot = injector.build_context_snapshot(session_id=session["id"])

            self.assertIn("static", snapshot)
            self.assertIn("dynamic", snapshot)

            static = snapshot["static"]
            self.assertIn("identity", static)
            self.assertIn("policy", static)
            self.assertIn("tool_usage_rules", static)

            dynamic = snapshot["dynamic"]
            for key in (
                "tenant_config_summary",
                "capability_manifests",
                "recent_artifacts",
                "active_tasks",
                "memory_summary",
                "vocabulary_map",
            ):
                self.assertIn(key, dynamic)


if __name__ == "__main__":
    unittest.main()
