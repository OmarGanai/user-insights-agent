import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_runtime import AgentRuntime
from agent_runtime.models import ToolPlan
from agent_runtime.store import FileWorkspaceStore


class ChatRuntimeTest(unittest.TestCase):
    def _runtime(self) -> AgentRuntime:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        store = FileWorkspaceStore(root=Path(self.tmp_dir.name) / "workspace")
        return AgentRuntime(store=store)

    def test_planner_fallback_on_model_failure(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-chat", objective="Generate digest")

        with patch.object(runtime.chat.gemini_planner, "plan", side_effect=RuntimeError("planner down")):
            payload = runtime.chat_turn(session_id=session["id"], message="Generate weekly digest")

        self.assertEqual(payload["planner"]["backend"], "deterministic")
        self.assertTrue(payload["planner"]["fallback_used"])

    def test_planner_fallback_when_gemini_plan_is_invalid_after_validation(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-chat", objective="Generate digest")

        invalid_plan = ToolPlan(
            plan_id="plan_invalid",
            tool_calls=[
                {"tool": "amplitude_get_chart_data", "args": {"chart_id": "abc123"}},
            ],
            backend="gemini",
            fallback_used=False,
            raw_model_output="{}",
            validation_warnings=[],
        )

        with patch.object(runtime.chat.gemini_planner, "plan", return_value=invalid_plan):
            payload = runtime.chat_turn(session_id=session["id"], message="Generate weekly digest")

        self.assertEqual(payload["planner"]["backend"], "deterministic")
        self.assertTrue(payload["planner"]["fallback_used"])
        self.assertIn(payload["session"]["status"], {"completed", "waiting_approval"})

    def test_chat_turn_weekly_digest_completes_without_manual_tool_calls(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-chat", objective="Generate digest")

        payload = runtime.chat_turn(session_id=session["id"], message="Generate weekly digest preview")

        self.assertEqual(payload["session"]["status"], "completed")
        self.assertGreaterEqual(len(payload["execution"]["results"]), 1)
        self.assertTrue(payload["assistant_message"]["content"])

    def test_chat_turn_creates_approval_when_post_requested(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-chat", objective="Generate digest")

        payload = runtime.chat_turn(session_id=session["id"], message="Generate weekly digest and post to slack")

        self.assertEqual(payload["session"]["status"], "waiting_approval")
        self.assertGreaterEqual(len(payload["approvals"]["pending"]), 1)

    def test_chat_turn_preview_only_never_live_posts(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-chat", objective="Generate digest")

        first = runtime.chat_turn(session_id=session["id"], message="Generate weekly digest and post to slack")
        approval_id = first["approvals"]["pending"][0]["id"]
        runtime.tools.resolve_approval_request(
            approval_id=approval_id,
            decision="approved",
            reviewer_note="ok",
            resolver="qa",
        )
        resumed = runtime.resume_session(session_id=session["id"])

        post_results = [row for row in resumed["results"] if row.get("tool") == "post_slack_payload"]
        self.assertGreaterEqual(len(post_results), 1)
        self.assertTrue(all(row["output"]["dry_run"] for row in post_results))
        self.assertTrue(all(not row["output"]["posted"] for row in post_results))

    def test_chat_turn_resume_after_approval(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-chat", objective="Generate digest")

        first = runtime.chat_turn(session_id=session["id"], message="Generate weekly digest and post to slack")
        approval_id = first["approvals"]["pending"][0]["id"]
        runtime.tools.resolve_approval_request(
            approval_id=approval_id,
            decision="approved",
            reviewer_note="ok",
            resolver="qa",
        )

        resumed = runtime.resume_session(session_id=session["id"])
        self.assertEqual(resumed["session"]["status"], "completed")

    def test_prompt_profile_version_changes_plan_behavior(self) -> None:
        runtime = self._runtime()
        runtime.tools.update_prompt_profile_rollout(
            tenant_id="tenant-chat",
            prompt_profile="weekly_digest",
            rollout={
                "stable_version": "v1",
                "versions": {
                    "v1": {"path": "weekly_digest.md"},
                    "v2": {"path": "weekly_digest_v2.md"},
                },
                "canary": {
                    "enabled": True,
                    "version": "v2",
                    "percent": 100,
                },
            },
        )
        session = runtime.create_session(
            tenant_id="tenant-chat",
            objective="Generate digest",
            prompt_profile="weekly_digest",
        )

        payload = runtime.chat_turn(session_id=session["id"], message="Generate weekly digest preview")
        citations = payload["assistant_message"]["citations"]
        self.assertGreaterEqual(len(citations), 1)
        artifact = runtime.tools.read_artifact(path=citations[0])
        text = artifact["content"]["text"]
        self.assertIn("weekly_digest:v2", text)

    def test_list_artifacts_tool_parity(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(tenant_id="tenant-chat", objective="Generate digest")
        runtime.tools.create_artifact(
            run_id=session["id"],
            kind="summary",
            path="outputs/summary.json",
            content={"ok": True},
        )

        runtime_view = runtime.list_artifacts(session["id"])["artifacts"]
        tool_view = runtime.tools.list_artifacts(session["id"])["artifacts"]

        self.assertEqual(runtime_view, tool_view)
        self.assertGreaterEqual(len(runtime_view), 1)


if __name__ == "__main__":
    unittest.main()
