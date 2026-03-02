import tempfile
import unittest
from pathlib import Path

from agent_runtime import AgentRuntime
from agent_runtime.store import FileWorkspaceStore


class AgentRuntimeLifecycleTest(unittest.TestCase):
    def _runtime(self) -> AgentRuntime:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        store = FileWorkspaceStore(root=Path(self.tmp_dir.name) / "workspace")
        return AgentRuntime(store=store)

    def test_session_turn_completes_only_via_complete_task(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-one", objective="Run digest")

        result = runtime.run_turn(
            session_id=session["id"],
            tool_calls=[
                {
                    "tool": "create_task",
                    "args": {
                        "session_id": session["id"],
                        "title": "Collect metrics",
                        "metadata": {"stage": "collect"},
                    },
                },
                {
                    "tool": "complete_task",
                    "args": {
                        "session_id": session["id"],
                        "status": "completed",
                    },
                },
            ],
        )

        self.assertEqual(result["session"]["status"], "completed")
        self.assertEqual(result["remaining_calls"], 0)
        tasks = runtime.tools.list_tasks(session_id=session["id"])["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Collect metrics")

    def test_turn_without_complete_task_blocks(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-one", objective="Run digest")

        result = runtime.run_turn(
            session_id=session["id"],
            tool_calls=[
                {
                    "tool": "create_task",
                    "args": {
                        "session_id": session["id"],
                        "title": "Collect metrics",
                        "metadata": {},
                    },
                }
            ],
        )

        self.assertEqual(result["session"]["status"], "blocked")
        self.assertIn("without complete_task", result["session"]["block_reason"])


class AgentRuntimeApprovalGateTest(unittest.TestCase):
    def _runtime(self) -> AgentRuntime:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        store = FileWorkspaceStore(root=Path(self.tmp_dir.name) / "workspace")
        return AgentRuntime(store=store)

    def test_slack_post_requires_approval_then_resumes(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-two", objective="Publish digest")
        artifact = runtime.tools.create_artifact(
            run_id=session["id"],
            kind="slack_payload",
            path="outputs/slack_payload.json",
            content={
                "text": "Weekly digest",
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "hello"}}],
            },
        )

        first = runtime.run_turn(
            session_id=session["id"],
            tool_calls=[
                {
                    "tool": "post_slack_payload",
                    "args": {
                        "session_id": session["id"],
                        "payload_path": artifact["path"],
                        "dry_run": True,
                    },
                },
                {
                    "tool": "complete_task",
                    "args": {
                        "session_id": session["id"],
                        "status": "completed",
                    },
                },
            ],
        )

        self.assertEqual(first["session"]["status"], "waiting_approval")
        approval_id = first["results"][0]["output"]["approval_id"]

        runtime.tools.resolve_approval_request(
            approval_id=approval_id,
            decision="approved",
            reviewer_note="ok",
            resolver="qa",
        )

        resumed = runtime.resume_session(session_id=session["id"])
        self.assertEqual(resumed["session"]["status"], "completed")


class AgentRuntimeDiscoveryTest(unittest.TestCase):
    def _runtime(self) -> AgentRuntime:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        store = FileWorkspaceStore(root=Path(self.tmp_dir.name) / "workspace")
        return AgentRuntime(store=store)

    def test_discovery_tools_emit_scoped_redacted_manifests(self) -> None:
        runtime = self._runtime()

        amp = runtime.tools.discover_amplitude_capabilities("tenant-three")
        typ = runtime.tools.discover_typeform_capabilities("tenant-three")
        slk = runtime.tools.discover_slack_capabilities("tenant-three")

        self.assertEqual(amp["tenant_id"], "tenant-three")
        self.assertEqual(typ["tenant_id"], "tenant-three")
        self.assertEqual(slk["tenant_id"], "tenant-three")
        self.assertTrue(amp["constraints"]["read_only"])
        self.assertIn("amplitude.com", amp["constraints"]["host_allowlist"])
        self.assertIn("api.typeform.com", typ["constraints"]["host_allowlist"])
        self.assertIn("slack.com", slk["constraints"]["host_allowlist"])
        self.assertIn("ttl_expires_at", amp)
        self.assertIn("ttl_expires_at", typ)
        self.assertIn("ttl_expires_at", slk)


if __name__ == "__main__":
    unittest.main()
