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


class AgentRuntimePromptProfileRolloutTest(unittest.TestCase):
    def _runtime(self) -> AgentRuntime:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        store = FileWorkspaceStore(root=Path(self.tmp_dir.name) / "workspace")
        return AgentRuntime(store=store)

    def test_create_session_resolves_prompt_profile_version_metadata(self) -> None:
        runtime = self._runtime()
        session = runtime.create_session(
            tenant_id="tenant-rollout",
            objective="Run digest",
            prompt_profile="weekly_digest",
        )

        self.assertEqual(session["prompt_profile"], "weekly_digest")
        self.assertEqual(session["prompt_version"], "v1")
        self.assertEqual(session["prompt_variant"], "stable")
        prompt_file = runtime.store.root / session["prompt_path"]
        self.assertTrue(prompt_file.exists())
        self.assertTrue(prompt_file.name.endswith(".md"))

    def test_canary_rollout_selects_canary_variant_when_percent_is_100(self) -> None:
        runtime = self._runtime()
        runtime.tools.update_prompt_profile_rollout(
            tenant_id="tenant-rollout",
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
            tenant_id="tenant-rollout",
            objective="Run digest",
            prompt_profile="weekly_digest",
        )

        self.assertEqual(session["prompt_version"], "v2")
        self.assertEqual(session["prompt_variant"], "canary")
        prompt_file = runtime.store.root / session["prompt_path"]
        self.assertTrue(prompt_file.exists())

    def test_prompt_profile_evaluation_reports_version_buckets(self) -> None:
        runtime = self._runtime()
        runtime.tools.update_prompt_profile_rollout(
            tenant_id="tenant-rollout",
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
                    "percent": 0,
                },
            },
        )
        stable_session = runtime.create_session(
            tenant_id="tenant-rollout",
            objective="Stable run",
            prompt_profile="weekly_digest",
        )
        runtime.run_turn(
            session_id=stable_session["id"],
            tool_calls=[
                {
                    "tool": "complete_task",
                    "args": {
                        "session_id": stable_session["id"],
                        "status": "completed",
                    },
                }
            ],
        )

        runtime.tools.update_prompt_profile_rollout(
            tenant_id="tenant-rollout",
            prompt_profile="weekly_digest",
            rollout={
                "canary": {
                    "enabled": True,
                    "version": "v2",
                    "percent": 100,
                }
            },
        )
        canary_session = runtime.create_session(
            tenant_id="tenant-rollout",
            objective="Canary run",
            prompt_profile="weekly_digest",
        )
        runtime.run_turn(
            session_id=canary_session["id"],
            tool_calls=[
                {
                    "tool": "create_task",
                    "args": {
                        "session_id": canary_session["id"],
                        "title": "Collect metrics",
                        "metadata": {},
                    },
                }
            ],
        )

        evaluation = runtime.tools.evaluate_prompt_profile(
            tenant_id="tenant-rollout",
            prompt_profile="weekly_digest",
        )
        self.assertEqual(evaluation["total_sessions"], 2)
        bucket_keys = {
            (row["prompt_version"], row["prompt_variant"])
            for row in evaluation["buckets"]
        }
        self.assertIn(("v1", "stable"), bucket_keys)
        self.assertIn(("v2", "canary"), bucket_keys)


if __name__ == "__main__":
    unittest.main()
