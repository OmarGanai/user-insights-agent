from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

from clients.slack import SlackWebhookClient

from .discovery import DiscoveryService
from .models import ToolResult, error, needs_approval, ok
from .store import FileWorkspaceStore


ToolFunc = Callable[..., Any]


class ToolRegistry:
    def __init__(self, store: Optional[FileWorkspaceStore] = None) -> None:
        self.store = store or FileWorkspaceStore()
        self.discovery = DiscoveryService(self.store)
        self._tools: Dict[str, ToolFunc] = {
            "create_session": self.create_session,
            "get_session": self.get_session,
            "update_session": self.update_session,
            "delete_session": self.delete_session,
            "create_task": self.create_task,
            "list_tasks": self.list_tasks,
            "update_task": self.update_task,
            "delete_task": self.delete_task,
            "create_artifact": self.create_artifact,
            "read_artifact": self.read_artifact,
            "update_artifact": self.update_artifact,
            "delete_artifact": self.delete_artifact,
            "create_approval_request": self.create_approval_request,
            "request_approval": self.create_approval_request,
            "list_approval_requests": self.list_approval_requests,
            "get_approval_request": self.get_approval_request,
            "resolve_approval_request": self.resolve_approval_request,
            "delete_approval_request": self.delete_approval_request,
            "create_metric_contract": self.create_metric_contract,
            "read_metric_contract": self.read_metric_contract,
            "update_metric_contract": self.update_metric_contract,
            "delete_metric_contract": self.delete_metric_contract,
            "get_prompt_profile_rollout": self.get_prompt_profile_rollout,
            "update_prompt_profile_rollout": self.update_prompt_profile_rollout,
            "evaluate_prompt_profile": self.evaluate_prompt_profile,
            "discover_amplitude_capabilities": self.discover_amplitude_capabilities,
            "discover_typeform_capabilities": self.discover_typeform_capabilities,
            "discover_slack_capabilities": self.discover_slack_capabilities,
            "validate_slack_payload": self.validate_slack_payload,
            "post_slack_payload": self.post_slack_payload,
            "complete_task": self.complete_task,
        }

    def invoke(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> ToolResult:
        if tool_name not in self._tools:
            return error(f"Unknown tool: {tool_name}", code="unknown_tool")

        payload = args or {}
        try:
            result = self._tools[tool_name](**payload)
            if isinstance(result, ToolResult):
                return result
            return ok(result)
        except Exception as exc:
            return error(str(exc), code="tool_execution")

    # Session tools
    def create_session(self, tenant_id: str, objective: str, prompt_profile: str = "default", mode: str = "hybrid") -> Dict[str, Any]:
        return self.store.create_session(tenant_id=tenant_id, objective=objective, prompt_profile=prompt_profile, mode=mode)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.store.get_session(session_id)

    def update_session(self, session_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.update_session(session_id, fields)

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        return self.store.delete_session(session_id)

    # Task tools
    def create_task(self, session_id: str, title: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.store.create_task(session_id=session_id, title=title, metadata=metadata or {})

    def list_tasks(self, session_id: str) -> Dict[str, Any]:
        return {"tasks": self.store.list_tasks(session_id)}

    def update_task(self, task_id: str, status: str, notes: str = "") -> Dict[str, Any]:
        return self.store.update_task(task_id=task_id, status=status, notes=notes)

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        return self.store.delete_task(task_id)

    # Artifact tools
    def create_artifact(self, run_id: str, kind: str, path: str, content: Any) -> Dict[str, Any]:
        return self.store.create_artifact(run_id=run_id, kind=kind, rel_path=path, content=content)

    def read_artifact(self, path: str) -> Dict[str, Any]:
        return self.store.read_artifact(path)

    def update_artifact(self, path: str, content: Any) -> Dict[str, Any]:
        return self.store.update_artifact(path, content)

    def delete_artifact(self, path: str) -> Dict[str, Any]:
        return self.store.delete_artifact(path)

    # Approval tools
    def create_approval_request(self, session_id: str, action_type: str, payload_path: str, summary: str) -> Dict[str, Any]:
        return self.store.create_approval_request(
            session_id=session_id,
            action_type=action_type,
            payload_path=payload_path,
            summary=summary,
        )

    def get_approval_request(self, approval_id: str) -> Dict[str, Any]:
        return self.store.get_approval_request(approval_id)

    def list_approval_requests(self, tenant_id: str, status: str = "pending") -> Dict[str, Any]:
        return {
            "approvals": self.store.list_approval_requests(tenant_id=tenant_id, status=status),
            "tenant_id": tenant_id,
            "status": status,
        }

    def resolve_approval_request(
        self,
        approval_id: str,
        decision: str,
        reviewer_note: str = "",
        resolver: str = "human",
    ) -> Dict[str, Any]:
        return self.store.resolve_approval_request(
            approval_id=approval_id,
            decision=decision,
            reviewer_note=reviewer_note,
            resolver=resolver,
        )

    def delete_approval_request(self, approval_id: str) -> Dict[str, Any]:
        return self.store.delete_approval_request(approval_id)

    # Metric contract tools
    def create_metric_contract(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.create_metric_contract(tenant_id=tenant_id, payload=payload)

    def read_metric_contract(self, tenant_id: str) -> Dict[str, Any]:
        return self.store.read_metric_contract(tenant_id=tenant_id)

    def update_metric_contract(self, tenant_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.update_metric_contract(tenant_id=tenant_id, patch=patch)

    def delete_metric_contract(self, tenant_id: str) -> Dict[str, Any]:
        return self.store.delete_metric_contract(tenant_id=tenant_id)

    # Prompt profile rollout tools
    def get_prompt_profile_rollout(self, tenant_id: str, prompt_profile: str = "default") -> Dict[str, Any]:
        return self.store.get_prompt_profile_rollout(tenant_id=tenant_id, prompt_profile=prompt_profile)

    def update_prompt_profile_rollout(
        self,
        tenant_id: str,
        prompt_profile: str = "default",
        rollout: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = rollout if isinstance(rollout, dict) else {}
        return self.store.update_prompt_profile_rollout(
            tenant_id=tenant_id,
            prompt_profile=prompt_profile,
            rollout=payload,
        )

    def evaluate_prompt_profile(self, tenant_id: str, prompt_profile: str = "default") -> Dict[str, Any]:
        return self.store.evaluate_prompt_profile(tenant_id=tenant_id, prompt_profile=prompt_profile)

    # Discovery tools
    def discover_amplitude_capabilities(self, tenant_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        return self.discovery.discover_amplitude_capabilities(tenant_id=tenant_id, force_refresh=force_refresh)

    def discover_typeform_capabilities(self, tenant_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        return self.discovery.discover_typeform_capabilities(tenant_id=tenant_id, force_refresh=force_refresh)

    def discover_slack_capabilities(self, tenant_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        return self.discovery.discover_slack_capabilities(tenant_id=tenant_id, force_refresh=force_refresh)

    def validate_slack_payload(self, path: str) -> Dict[str, Any]:
        artifact = self.store.read_artifact(path)
        content = artifact.get("content")
        if not isinstance(content, dict):
            raise ValueError("Slack payload must be a JSON object")

        text = str(content.get("text") or "").strip()
        blocks = content.get("blocks")
        if not text:
            raise ValueError("Slack payload requires non-empty text")
        if not isinstance(blocks, list):
            raise ValueError("Slack payload requires blocks list")
        if len(blocks) > 50:
            raise ValueError("Slack payload cannot exceed 50 blocks")

        return {
            "valid": True,
            "path": artifact["path"],
            "block_count": len(blocks),
            "text_length": len(text),
        }

    def post_slack_payload(
        self,
        session_id: str,
        payload_path: str,
        approval_id: str = "",
        dry_run: bool = True,
    ) -> ToolResult:
        if not self.store.approved_action_exists(
            session_id=session_id,
            action_type="slack_post",
            payload_path=payload_path,
        ):
            pending = self.store.latest_pending_approval(
                session_id=session_id,
                action_type="slack_post",
                payload_path=payload_path,
            )
            if pending is None:
                pending = self.store.create_approval_request(
                    session_id=session_id,
                    action_type="slack_post",
                    payload_path=payload_path,
                    summary="Slack post requested from agent tool execution",
                )
            return needs_approval(
                {
                    "approval_id": pending["id"],
                    "status": pending["status"],
                    "message": "Approval required before posting to Slack",
                }
            )

        if approval_id:
            approval = self.store.get_approval_request(approval_id)
            if approval.get("status") != "approved":
                return error("Provided approval_id is not approved", code="approval_not_approved")

        artifact = self.store.read_artifact(payload_path)
        payload = artifact.get("content")
        if not isinstance(payload, dict):
            return error("Slack payload artifact must contain JSON object", code="invalid_payload")

        if dry_run:
            return ok(
                {
                    "posted": False,
                    "dry_run": True,
                    "path": artifact["path"],
                    "message": "Slack post skipped in dry-run mode",
                }
            )

        session = self.store.get_session(session_id)
        config = self.store.read_tenant_config(session["tenant_id"])
        webhook_env = str(((config.get("slack") or {}).get("webhook_env") or "SLACK_WEBHOOK_URL")).strip()
        webhook_url = __import__("os").environ.get(webhook_env, "") if webhook_env else ""
        webhook_url = str(webhook_url).strip()
        if not webhook_url:
            return error("Slack webhook is not configured", code="missing_webhook")

        client = SlackWebhookClient(webhook_url=webhook_url, channel=payload.get("channel"))
        client.post_payload(payload)
        return ok(
            {
                "posted": True,
                "dry_run": False,
                "path": artifact["path"],
            }
        )

    def complete_task(self, session_id: str, status: str = "completed", reason: str = "") -> Dict[str, Any]:
        normalized = status.strip().lower() or "completed"
        if normalized not in {"completed", "partial", "blocked"}:
            raise ValueError("complete_task status must be completed, partial, or blocked")
        return {
            "session_id": session_id,
            "status": normalized,
            "reason": reason.strip(),
        }
