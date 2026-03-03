from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .discovery import DiscoveryService
from .models import utc_now_iso
from .store import FileWorkspaceStore
from .tools import ToolRegistry


REPO_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_BASE_PROMPT = REPO_ROOT / "prompts" / "system" / "base.md"
SYSTEM_POLICY_PROMPT = REPO_ROOT / "prompts" / "system" / "policy.md"


class ContextInjector:
    def __init__(self, store: FileWorkspaceStore, tools: Optional[ToolRegistry] = None) -> None:
        self.store = store
        self.tools = tools or ToolRegistry(store)
        self.discovery = DiscoveryService(store)

    def build_context_snapshot(self, session_id: str) -> Dict[str, Any]:
        session = self.store.get_session(session_id)
        tenant_id = str(session["tenant_id"])
        tenant_root = self.store.tenant_root(tenant_id)
        artifacts = self.store.list_artifacts(session_id=session_id)
        tasks = self.store.list_tasks(session_id=session_id)
        messages = self.store.list_messages(session_id=session_id)
        capabilities = self.discovery.full_manifest(tenant_id=tenant_id)

        active_tasks = [task for task in tasks if str(task.get("status") or "") not in {"completed", "failed"}]
        recent_artifacts = artifacts[-20:] if len(artifacts) > 20 else artifacts
        recent_messages = messages[-20:] if len(messages) > 20 else messages

        tenant_config = self.store.read_tenant_config(tenant_id)
        memory_summary = _memory_summary(tenant_root)
        vocabulary = _vocabulary_map()

        return {
            "generated_at": utc_now_iso(),
            "session_id": session_id,
            "tenant_id": tenant_id,
            "static": {
                "identity": _read_text(SYSTEM_BASE_PROMPT),
                "policy": _read_text(SYSTEM_POLICY_PROMPT),
                "tool_usage_rules": [
                    "Use primitive tools; avoid encoding business workflows in tool arguments.",
                    "Only execute side effects when policy and approvals allow.",
                    "Cite artifact paths when returning conclusions.",
                ],
            },
            "dynamic": {
                "session": session,
                "tenant_config_summary": _tenant_config_summary(tenant_config),
                "capability_manifests": capabilities,
                "recent_artifacts": recent_artifacts,
                "active_tasks": active_tasks,
                "recent_messages": recent_messages,
                "memory_summary": memory_summary,
                "vocabulary_map": vocabulary,
            },
        }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _tenant_config_summary(config: Dict[str, Any]) -> Dict[str, Any]:
    amplitude = config.get("amplitude") if isinstance(config.get("amplitude"), dict) else {}
    typeform = config.get("typeform") if isinstance(config.get("typeform"), dict) else {}
    slack = config.get("slack") if isinstance(config.get("slack"), dict) else {}
    return {
        "display_name": str(config.get("display_name") or "Tenant"),
        "amplitude": {
            "base_url": str(amplitude.get("base_url") or ""),
            "app_slug": str(amplitude.get("app_slug") or ""),
        },
        "typeform": {
            "enabled": bool(typeform.get("enabled", False)),
            "form_id": str(typeform.get("form_id") or ""),
        },
        "slack": {
            "enabled": bool(slack.get("enabled", False)),
            "webhook_env": str(slack.get("webhook_env") or "SLACK_WEBHOOK_URL"),
        },
        "prompt_profiles": list((config.get("prompt_profiles") or {}).keys())
        if isinstance(config.get("prompt_profiles"), dict)
        else [],
    }


def _vocabulary_map() -> Dict[str, str]:
    return {
        "start analysis run": "create_session",
        "run turn": "run_turn",
        "resume run": "resume_session",
        "view tasks": "list_tasks",
        "view artifacts": "list_artifacts",
        "edit artifact": "update_artifact",
        "validate slack payload": "validate_slack_payload",
        "post slack payload": "post_slack_payload",
        "request approval": "create_approval_request",
        "resolve approval": "resolve_approval_request",
        "refresh capabilities": "discover_*_capabilities",
    }


def _memory_summary(tenant_root: Path) -> Dict[str, Any]:
    temporal_path = tenant_root / "memory" / "temporal-memory.json"
    context_path = tenant_root / "memory" / "context.md"

    temporal_payload: Dict[str, Any] = {}
    if temporal_path.exists():
        try:
            temporal_payload = json.loads(temporal_path.read_text(encoding="utf-8"))
        except Exception:
            temporal_payload = {}

    context_excerpt = ""
    if context_path.exists():
        raw = context_path.read_text(encoding="utf-8").strip()
        if raw:
            context_excerpt = raw[:4000]

    return {
        "temporal_memory_path": str(temporal_path),
        "latest_report": temporal_payload.get("latest_report"),
        "previous_report": temporal_payload.get("previous_report"),
        "last_updated_utc": temporal_payload.get("last_updated_utc"),
        "context_excerpt": context_excerpt,
    }
