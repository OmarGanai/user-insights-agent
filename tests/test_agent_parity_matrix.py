import tempfile
import unittest
from pathlib import Path

from agent_runtime import AgentRuntime
from agent_runtime.store import FileWorkspaceStore


class AgentParityMatrixTest(unittest.TestCase):
    def test_ui_actions_have_agent_api_or_tool_parity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime = AgentRuntime(store=FileWorkspaceStore(root=Path(tmp_dir) / "workspace"))

            required_runtime_methods = {
                "create_session",
                "get_session",
                "run_turn",
                "resume_session",
                "chat_turn",
                "list_messages",
                "build_context_snapshot",
                "list_artifacts",
            }
            for method_name in required_runtime_methods:
                self.assertTrue(hasattr(runtime, method_name), msg=f"Missing runtime method: {method_name}")

            required_tools = {
                "create_task",
                "list_tasks",
                "create_artifact",
                "read_artifact",
                "update_artifact",
                "list_artifacts",
                "get_approval_request",
                "resolve_approval_request",
                "discover_amplitude_capabilities",
                "discover_typeform_capabilities",
                "discover_slack_capabilities",
            }
            tool_names = set(runtime.tools._tools.keys())
            for tool_name in required_tools:
                self.assertIn(tool_name, tool_names, msg=f"Missing tool for parity: {tool_name}")


if __name__ == "__main__":
    unittest.main()
