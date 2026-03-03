import unittest
from unittest.mock import MagicMock, patch

from agent_runtime.models import ToolPlan
from agent_runtime.planner import GeminiPlanner, PlanValidator


class PlannerTest(unittest.TestCase):
    @patch("agent_runtime.planner.requests.post")
    def test_planner_parses_valid_json_plan(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    "{\"tool_calls\": ["
                                    "{\"tool\": \"complete_task\", \"args\": {\"status\": \"completed\"}}"
                                    "]}"
                                )
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        planner = GeminiPlanner(api_key="fake-key", model="fake-model")
        plan = planner.plan(
            session={"id": "ses_1", "tenant_id": "tenant-a"},
            message="Finish the digest",
            context_snapshot={"static": {}, "dynamic": {}},
        )

        self.assertEqual(plan.backend, "gemini")
        self.assertEqual(plan.tool_calls[0]["tool"], "complete_task")

    def test_plan_validator_rejects_cross_tenant_paths(self) -> None:
        validator = PlanValidator()
        plan = ToolPlan(
            plan_id="plan_1",
            tool_calls=[
                {
                    "tool": "validate_slack_payload",
                    "args": {
                        "path": "workspace/tenants/tenant-b/runs/ses_1/outputs/slack_payload.json",
                    },
                }
            ],
            backend="deterministic",
            fallback_used=False,
            raw_model_output="",
            validation_warnings=[],
        )

        validated = validator.validate(
            plan=plan,
            session={"id": "ses_1", "tenant_id": "tenant-a"},
        )

        tools = [call["tool"] for call in validated.tool_calls]
        self.assertNotIn("validate_slack_payload", tools)
        self.assertIn("complete_task", tools)
        self.assertTrue(any("cross-tenant" in note for note in validated.validation_warnings))

    def test_plan_validator_rejects_side_effect_without_policy(self) -> None:
        validator = PlanValidator()
        plan = ToolPlan(
            plan_id="plan_2",
            tool_calls=[
                {
                    "tool": "post_slack_payload",
                    "args": {
                        "payload_path": "workspace/tenants/tenant-a/runs/ses_1/outputs/slack_payload.json",
                        "dry_run": False,
                    },
                }
            ],
            backend="deterministic",
            fallback_used=False,
            raw_model_output="",
            validation_warnings=[],
        )

        validated = validator.validate(
            plan=plan,
            session={"id": "ses_1", "tenant_id": "tenant-a"},
            preview_only=False,
            allow_side_effects=False,
        )

        tools = [call["tool"] for call in validated.tool_calls]
        self.assertNotIn("post_slack_payload", tools)
        self.assertIn("complete_task", tools)
        self.assertTrue(any("side-effect" in note for note in validated.validation_warnings))


if __name__ == "__main__":
    unittest.main()
