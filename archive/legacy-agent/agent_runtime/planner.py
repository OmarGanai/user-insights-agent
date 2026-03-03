from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List
from uuid import uuid4

import requests

from .models import ToolPlan


SAFE_CHAT_TOOLS = {
    "create_task",
    "list_tasks",
    "create_artifact",
    "read_artifact",
    "update_artifact",
    "list_artifacts",
    "validate_slack_payload",
    "post_slack_payload",
    "discover_amplitude_capabilities",
    "discover_typeform_capabilities",
    "discover_slack_capabilities",
    "create_approval_request",
    "get_approval_request",
    "complete_task",
}

SESSION_ID_TOOLS = {
    "create_task",
    "list_tasks",
    "list_artifacts",
    "post_slack_payload",
    "complete_task",
}


class PlannerError(RuntimeError):
    pass


class GeminiPlanner:
    def __init__(self, api_key: str = "", model: str = "") -> None:
        self.api_key = api_key.strip() or os.getenv("GEMINI_API_KEY", "").strip()
        self.model = model.strip() or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    def plan(self, session: Dict[str, Any], message: str, context_snapshot: Dict[str, Any]) -> ToolPlan:
        if not self.api_key:
            raise PlannerError("GEMINI_API_KEY is not configured")

        prompt = self._build_prompt(session=session, message=message, context_snapshot=context_snapshot)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        raw_payload = response.json()
        raw_text = _gemini_text(raw_payload)
        parsed = _parse_json_payload(raw_text)
        tool_calls = parsed.get("tool_calls")
        if not isinstance(tool_calls, list):
            raise PlannerError("Gemini planner response missing tool_calls list")
        return ToolPlan(
            plan_id=f"plan_{uuid4().hex[:12]}",
            tool_calls=[call for call in tool_calls if isinstance(call, dict)],
            backend="gemini",
            fallback_used=False,
            raw_model_output=raw_text,
            validation_warnings=[],
        )

    def _build_prompt(self, session: Dict[str, Any], message: str, context_snapshot: Dict[str, Any]) -> str:
        slim_context = {
            "session": context_snapshot.get("dynamic", {}).get("session"),
            "active_tasks": context_snapshot.get("dynamic", {}).get("active_tasks", [])[:8],
            "recent_artifacts": context_snapshot.get("dynamic", {}).get("recent_artifacts", [])[:10],
            "capabilities": context_snapshot.get("dynamic", {}).get("capability_manifests", {}),
            "vocabulary_map": context_snapshot.get("dynamic", {}).get("vocabulary_map", {}),
            "policy": context_snapshot.get("static", {}).get("policy", ""),
        }
        return (
            "You are planning tool calls for a tenant-scoped runtime. "
            "Respond ONLY as JSON with shape {\"tool_calls\": [{\"tool\": str, \"args\": object}]}.\n"
            f"Session: {json.dumps(session, ensure_ascii=True)}\n"
            f"User message: {message}\n"
            f"Context snapshot: {json.dumps(slim_context, ensure_ascii=True)}\n"
            "Rules:\n"
            "- Use only primitive tools.\n"
            "- Always end with complete_task.\n"
            "- If posting is requested, include post_slack_payload with dry_run true.\n"
            "- Use create_artifact path 'outputs/slack_payload.json' for previews.\n"
        )


class DeterministicPlanner:
    def plan(self, session: Dict[str, Any], message: str, _context_snapshot: Dict[str, Any]) -> ToolPlan:
        session_id = str(session["id"])
        tenant_id = str(session["tenant_id"])
        prompt_profile = str(session.get("prompt_profile") or "default")
        prompt_version = str(session.get("prompt_version") or "v1")
        prompt_signature = f"{prompt_profile}:{prompt_version}"
        lower = message.lower()
        tool_calls: List[Dict[str, Any]] = []

        if any(token in lower for token in {"weekly", "digest", "summary", "report"}):
            tool_calls.extend(
                [
                    {
                        "tool": "create_task",
                        "args": {
                            "session_id": session_id,
                            "title": f"Generate weekly digest ({prompt_signature})",
                            "metadata": {
                                "stage": "planning",
                                "prompt_profile": prompt_profile,
                                "prompt_version": prompt_version,
                            },
                        },
                    },
                    {"tool": "discover_amplitude_capabilities", "args": {"tenant_id": tenant_id}},
                    {"tool": "discover_typeform_capabilities", "args": {"tenant_id": tenant_id}},
                    {"tool": "discover_slack_capabilities", "args": {"tenant_id": tenant_id}},
                    {
                        "tool": "create_artifact",
                        "args": {
                            "run_id": session_id,
                            "kind": "slack_payload",
                            "path": "outputs/slack_payload.json",
                            "content": {
                                "text": f"User Insights Digest Preview ({prompt_signature})",
                                "blocks": [
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": (
                                                "*User Insights Digest*\\n"
                                                f"Preview generated from deterministic planner ({prompt_signature})."
                                            ),
                                        },
                                    }
                                ],
                            },
                        },
                    },
                    {
                        "tool": "validate_slack_payload",
                        "args": {
                            "path": f"workspace/tenants/{tenant_id}/runs/{session_id}/outputs/slack_payload.json",
                        },
                    },
                ]
            )
            if any(token in lower for token in {"post", "publish", "slack", "send"}):
                tool_calls.append(
                    {
                        "tool": "post_slack_payload",
                        "args": {
                            "session_id": session_id,
                            "payload_path": f"workspace/tenants/{tenant_id}/runs/{session_id}/outputs/slack_payload.json",
                            "dry_run": True,
                        },
                    }
                )
            tool_calls.append(
                {
                    "tool": "complete_task",
                    "args": {
                        "session_id": session_id,
                        "status": "completed",
                        "reason": f"Digest preview prepared ({prompt_signature})",
                    },
                }
            )
        elif "anomaly" in lower:
            tool_calls.extend(
                [
                    {
                        "tool": "create_task",
                        "args": {
                            "session_id": session_id,
                            "title": f"Investigate anomaly ({prompt_signature})",
                            "metadata": {
                                "stage": "investigation",
                                "prompt_profile": prompt_profile,
                                "prompt_version": prompt_version,
                            },
                        },
                    },
                    {"tool": "discover_amplitude_capabilities", "args": {"tenant_id": tenant_id}},
                    {
                        "tool": "complete_task",
                        "args": {
                            "session_id": session_id,
                            "status": "completed",
                            "reason": f"Anomaly investigation scaffold prepared ({prompt_signature})",
                        },
                    },
                ]
            )
        else:
            tool_calls.extend(
                [
                    {
                        "tool": "create_task",
                        "args": {
                            "session_id": session_id,
                            "title": f"Handle user objective ({prompt_signature})",
                            "metadata": {
                                "stage": "generic",
                                "prompt_profile": prompt_profile,
                                "prompt_version": prompt_version,
                            },
                        },
                    },
                    {
                        "tool": "complete_task",
                        "args": {
                            "session_id": session_id,
                            "status": "completed",
                            "reason": f"Generic objective processed ({prompt_signature})",
                        },
                    },
                ]
            )

        return ToolPlan(
            plan_id=f"plan_{uuid4().hex[:12]}",
            tool_calls=tool_calls,
            backend="deterministic",
            fallback_used=False,
            raw_model_output="",
            validation_warnings=[],
        )


class PlanValidator:
    def validate(
        self,
        plan: ToolPlan,
        session: Dict[str, Any],
        *,
        preview_only: bool = True,
        allow_side_effects: bool = False,
    ) -> ToolPlan:
        tenant_id = str(session["tenant_id"])
        session_id = str(session["id"])
        warnings: List[str] = list(plan.validation_warnings)
        sanitized_calls: List[Dict[str, Any]] = []

        for index, raw_call in enumerate(plan.tool_calls):
            tool_name = str(raw_call.get("tool") or "").strip()
            if tool_name not in SAFE_CHAT_TOOLS:
                warnings.append(f"Dropped unsupported tool at index {index}: {tool_name or '<empty>'}")
                continue
            args = raw_call.get("args")
            if not isinstance(args, dict):
                args = {}
            safe_args = dict(args)

            if tool_name in SESSION_ID_TOOLS:
                safe_args["session_id"] = session_id

            if tool_name == "create_artifact":
                safe_args["run_id"] = session_id
                path = str(safe_args.get("path") or "outputs/generated.json").strip()
                safe_args["path"] = _sanitize_relative_path(path)

            if tool_name in {"validate_slack_payload", "post_slack_payload"}:
                default_path = f"workspace/tenants/{tenant_id}/runs/{session_id}/outputs/slack_payload.json"
                key = "path" if tool_name == "validate_slack_payload" else "payload_path"
                raw_path = str(safe_args.get(key) or default_path).strip()
                if not _path_within_tenant(raw_path, tenant_id):
                    warnings.append(f"Rejected cross-tenant path for {tool_name}")
                    continue
                safe_args[key] = _normalize_workspace_path(raw_path)

            if tool_name.startswith("discover_"):
                safe_args["tenant_id"] = tenant_id

            if tool_name == "post_slack_payload":
                if preview_only and safe_args.get("dry_run") is not True:
                    warnings.append("Forced dry_run=true for post_slack_payload in preview-only mode")
                safe_args["dry_run"] = True if preview_only else bool(safe_args.get("dry_run", True))
                if not preview_only and safe_args["dry_run"] is False and not allow_side_effects:
                    warnings.append("Rejected side-effect post_slack_payload without side-effect policy")
                    continue

            schema_error = _schema_error(tool_name, safe_args)
            if schema_error:
                warnings.append(f"Dropped {tool_name}: {schema_error}")
                continue

            sanitized_calls.append({"tool": tool_name, "args": safe_args})

        if not any(call.get("tool") == "complete_task" for call in sanitized_calls):
            warnings.append("Added complete_task because plan omitted explicit completion")
            sanitized_calls.append(
                {
                    "tool": "complete_task",
                    "args": {
                        "session_id": session_id,
                        "status": "completed",
                        "reason": "Auto-complete added by validator",
                    },
                }
            )

        return ToolPlan(
            plan_id=plan.plan_id,
            tool_calls=sanitized_calls,
            backend=plan.backend,
            fallback_used=plan.fallback_used,
            raw_model_output=plan.raw_model_output,
            validation_warnings=warnings,
        )


def _gemini_text(payload: Dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise PlannerError("Gemini planner response missing candidates")
    first = candidates[0] if isinstance(candidates[0], dict) else {}
    content = first.get("content") if isinstance(first.get("content"), dict) else {}
    parts = content.get("parts") if isinstance(content.get("parts"), list) else []
    chunks: List[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            chunks.append(text.strip())
    if not chunks:
        raise PlannerError("Gemini planner response missing text payload")
    return "\n".join(chunks)


def _parse_json_payload(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise PlannerError(f"Planner output JSON parse failure: {exc}") from exc

    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError as exc:
            raise PlannerError(f"Planner output fenced JSON parse failure: {exc}") from exc

    first = stripped.find("{")
    last = stripped.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(stripped[first : last + 1])
        except json.JSONDecodeError as exc:
            raise PlannerError(f"Planner output embedded JSON parse failure: {exc}") from exc
    raise PlannerError("Planner output did not contain valid JSON")


def _sanitize_relative_path(value: str) -> str:
    raw = value.strip().replace("\\", "/")
    if not raw:
        return "outputs/generated.json"
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    parts = [part for part in parts if part != ".."]
    return "/".join(parts) if parts else "outputs/generated.json"


def _schema_error(tool_name: str, args: Dict[str, Any]) -> str:
    if tool_name == "create_task":
        title = str(args.get("title") or "").strip()
        if not title:
            return "title is required"
        return ""

    if tool_name == "create_artifact":
        kind = str(args.get("kind") or "").strip()
        path = str(args.get("path") or "").strip()
        if not kind:
            return "kind is required"
        if not path:
            return "path is required"
        if "content" not in args:
            return "content is required"
        return ""

    if tool_name in {"read_artifact", "update_artifact"}:
        path = str(args.get("path") or "").strip()
        if not path:
            return "path is required"
        return ""

    if tool_name == "validate_slack_payload":
        path = str(args.get("path") or "").strip()
        if not path:
            return "path is required"
        return ""

    if tool_name == "post_slack_payload":
        payload_path = str(args.get("payload_path") or "").strip()
        if not payload_path:
            return "payload_path is required"
        return ""

    if tool_name == "complete_task":
        status = str(args.get("status") or "completed").strip().lower()
        if status not in {"completed", "partial", "blocked"}:
            return "status must be completed, partial, or blocked"
        return ""

    if tool_name in {"discover_amplitude_capabilities", "discover_typeform_capabilities", "discover_slack_capabilities"}:
        tenant_id = str(args.get("tenant_id") or "").strip()
        if not tenant_id:
            return "tenant_id is required"
        return ""

    if tool_name in {"list_tasks", "list_artifacts"}:
        session_id = str(args.get("session_id") or "").strip()
        if not session_id:
            return "session_id is required"
        return ""

    return ""


def _path_within_tenant(path: str, tenant_id: str) -> bool:
    normalized = path.strip().replace("\\", "/")
    return normalized.startswith(f"workspace/tenants/{tenant_id}/") or normalized.startswith(f"tenants/{tenant_id}/")


def _normalize_workspace_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("workspace/"):
        return normalized[len("workspace/") :]
    return normalized
