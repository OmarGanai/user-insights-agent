import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from agent_runtime import AgentRuntime
from agent_runtime.store import FileWorkspaceStore
from scripts import agent_runtime_api


class AgentRuntimeApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        store = FileWorkspaceStore(root=Path(self.tmp_dir.name) / "workspace")
        self.runtime = AgentRuntime(store=store)

        self.previous_runtime = agent_runtime_api._Handler.runtime
        agent_runtime_api._Handler.runtime = self.runtime
        self.addCleanup(self._restore_runtime)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), agent_runtime_api._Handler)
        self.port = int(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown_server)

    def _restore_runtime(self) -> None:
        agent_runtime_api._Handler.runtime = self.previous_runtime

    def _shutdown_server(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        expect_status: int = 200,
    ) -> Any:
        url = f"http://127.0.0.1:{self.port}{path}"
        data: Optional[bytes] = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8")
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            status = int(exc.code)

        self.assertEqual(status, expect_status, msg=body)
        if not body:
            return None
        return json.loads(body)

    def test_root_serves_console_html(self) -> None:
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url, timeout=5) as response:
            html = response.read().decode("utf-8")
            self.assertEqual(int(response.status), 200)
        self.assertIn("Agent Console", html)
        self.assertIn("/v1/sessions", html)

    def test_runtime_descriptor_and_capability_refresh(self) -> None:
        runtime_info = self._request("GET", "/v1/runtime")
        self.assertIn("runtime", runtime_info)
        self.assertIn("available", runtime_info)

        refreshed = self._request("POST", "/v1/tenants/tenant-api/capabilities/refresh", payload={})
        self.assertEqual(refreshed["tenant_id"], "tenant-api")
        self.assertIn("amplitude", refreshed)
        self.assertIn("typeform", refreshed)
        self.assertIn("slack", refreshed)

    def test_tasks_and_approval_inbox_endpoints(self) -> None:
        session = self._request(
            "POST",
            "/v1/sessions",
            payload={
                "tenant_id": "tenant-api",
                "objective": "Run API test",
                "prompt_profile": "default",
                "mode": "hybrid",
            },
            expect_status=201,
        )
        session_id = session["id"]

        tasks = self._request("GET", f"/v1/sessions/{session_id}/tasks")
        self.assertEqual(tasks["tasks"], [])

        created_task = self._request(
            "POST",
            f"/v1/sessions/{session_id}/tasks",
            payload={"title": "Collect inputs", "metadata": {"stage": "collect"}},
            expect_status=201,
        )
        self.assertEqual(created_task["title"], "Collect inputs")

        tasks = self._request("GET", f"/v1/sessions/{session_id}/tasks")
        self.assertEqual(len(tasks["tasks"]), 1)

        artifact = self.runtime.tools.create_artifact(
            run_id=session_id,
            kind="slack_payload",
            path="outputs/slack_payload.json",
            content={
                "text": "Digest",
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}}],
            },
        )
        turn = self._request(
            "POST",
            f"/v1/sessions/{session_id}/turn",
            payload={
                "tool_calls": [
                    {
                        "tool": "post_slack_payload",
                        "args": {
                            "session_id": session_id,
                            "payload_path": artifact["path"],
                            "dry_run": True,
                        },
                    }
                ]
            },
        )
        self.assertEqual(turn["session"]["status"], "waiting_approval")
        approval_id = turn["results"][0]["output"]["approval_id"]

        pending = self._request("GET", "/v1/tenants/tenant-api/approvals/pending")
        pending_ids = [row["id"] for row in pending["approvals"]]
        self.assertIn(approval_id, pending_ids)

        resolved = self._request(
            "POST",
            f"/v1/approvals/{approval_id}/resolve",
            payload={"decision": "approved", "reviewer_note": "ok", "resolver": "qa"},
        )
        self.assertEqual(resolved["status"], "approved")

        pending_after = self._request("GET", "/v1/tenants/tenant-api/approvals/pending")
        self.assertEqual(pending_after["approvals"], [])

        resolved_rows = self._request("GET", "/v1/tenants/tenant-api/approvals/resolved")
        resolved_ids = [row["id"] for row in resolved_rows["approvals"]]
        self.assertIn(approval_id, resolved_ids)


if __name__ == "__main__":
    unittest.main()
