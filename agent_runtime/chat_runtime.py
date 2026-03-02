from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .context_injection import ContextInjector
from .models import ToolPlan
from .planner import DeterministicPlanner, GeminiPlanner, PlanValidator
from .store import FileWorkspaceStore


RunTurnFn = Callable[[str, Optional[List[Dict[str, Any]]]], Dict[str, Any]]


class ChatRuntime:
    def __init__(
        self,
        store: FileWorkspaceStore,
        run_turn_fn: RunTurnFn,
        context_injector: Optional[ContextInjector] = None,
        gemini_planner: Optional[GeminiPlanner] = None,
        deterministic_planner: Optional[DeterministicPlanner] = None,
        validator: Optional[PlanValidator] = None,
    ) -> None:
        self.store = store
        self.run_turn_fn = run_turn_fn
        self.context_injector = context_injector or ContextInjector(store=store)
        self.gemini_planner = gemini_planner or GeminiPlanner()
        self.deterministic_planner = deterministic_planner or DeterministicPlanner()
        self.validator = validator or PlanValidator()

    def build_context_snapshot(self, session_id: str) -> Dict[str, Any]:
        return self.context_injector.build_context_snapshot(session_id=session_id)

    def list_messages(self, session_id: str) -> List[Dict[str, Any]]:
        return self.store.list_messages(session_id=session_id)

    def chat_turn(
        self,
        session_id: str,
        message: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text = message.strip()
        if not text:
            raise ValueError("message is required")
        session = self.store.get_session(session_id)
        self.store.append_message(session_id=session_id, role="user", content=text, meta={"options": options or {}})

        context_snapshot = self.context_injector.build_context_snapshot(session_id=session_id)
        planner_backend = "gemini"
        fallback_used = False
        validation_warnings: List[str] = []

        try:
            plan = self.gemini_planner.plan(
                session=session,
                message=text,
                context_snapshot=context_snapshot,
            )
        except Exception as exc:
            fallback_used = True
            planner_backend = "deterministic"
            validation_warnings.append(f"Gemini planner failed: {exc}")
            plan = self.deterministic_planner.plan(
                session=session,
                message=text,
                _context_snapshot=context_snapshot,
            )
            plan = ToolPlan(
                plan_id=plan.plan_id,
                tool_calls=plan.tool_calls,
                backend=plan.backend,
                fallback_used=True,
                raw_model_output=str(exc),
                validation_warnings=list(plan.validation_warnings),
            )

        plan = self.validator.validate(plan=plan, session=session, preview_only=True)
        if validation_warnings:
            plan.validation_warnings.extend(validation_warnings)

        execution = self.run_turn_fn(session_id, plan.tool_calls)
        updated_session = execution.get("session") or self.store.get_session(session_id)
        tenant_id = str(updated_session["tenant_id"])
        pending_approvals = [
            approval
            for approval in self.store.list_approval_requests(tenant_id=tenant_id, status="pending")
            if approval.get("session_id") == session_id
        ]
        approval_created = any(bool(row.get("requires_approval")) for row in (execution.get("results") or []))
        self.store.append_event(
            session_id=session_id,
            event={
                "type": "chat_turn",
                "planner_backend": planner_backend if not fallback_used else "deterministic",
                "fallback_used": bool(fallback_used or plan.fallback_used),
                "tool_count": len(plan.tool_calls),
                "approval_created": approval_created,
                "session_status_final": str(updated_session.get("status") or ""),
            },
        )
        citations = _extract_citations(execution)
        assistant_content = _assistant_response_text(
            status=str(updated_session.get("status") or ""),
            citations=citations,
            pending_count=len(pending_approvals),
            validation_warnings=plan.validation_warnings,
        )

        assistant_message = self.store.append_message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            meta={
                "status": updated_session.get("status"),
                "citations": citations,
                "planner_backend": planner_backend if not fallback_used else "deterministic",
                "fallback_used": bool(fallback_used or plan.fallback_used),
                "validation_warnings": plan.validation_warnings,
                "pending_approvals": [row.get("id") for row in pending_approvals],
            },
        )

        return {
            "session": updated_session,
            "assistant_message": {
                "role": "assistant",
                "content": assistant_message["content"],
                "status": updated_session.get("status"),
                "citations": citations,
            },
            "planner": {
                "backend": planner_backend if not fallback_used else "deterministic",
                "fallback_used": bool(fallback_used or plan.fallback_used),
                "validation_warnings": plan.validation_warnings,
            },
            "execution": {
                "results": execution.get("results", []),
                "remaining_calls": execution.get("remaining_calls", 0),
            },
            "approvals": {
                "pending": pending_approvals,
            },
        }


def _extract_citations(execution: Dict[str, Any]) -> List[str]:
    citations: List[str] = []
    for result in execution.get("results") or []:
        if not isinstance(result, dict):
            continue
        output = result.get("output")
        if not isinstance(output, dict):
            continue
        for key in ("path", "payload_path"):
            value = output.get(key)
            if not isinstance(value, str):
                continue
            normalized = value.strip().replace("\\", "/")
            if normalized.startswith("workspace/"):
                citations.append(normalized)
            elif normalized.startswith("tenants/"):
                citations.append(f"workspace/{normalized}")
    deduped = []
    seen = set()
    for citation in citations:
        if citation in seen:
            continue
        seen.add(citation)
        deduped.append(citation)
    return deduped


def _assistant_response_text(
    status: str,
    citations: List[str],
    pending_count: int,
    validation_warnings: List[str],
) -> str:
    status_value = status.strip().lower()
    if status_value == "completed":
        prefix = "Completed the requested objective."
    elif status_value == "waiting_approval":
        prefix = f"Work paused for approval ({pending_count} pending)."
    elif status_value == "blocked":
        prefix = "Run is blocked and may need additional input."
    elif status_value == "failed":
        prefix = "Run failed while executing the planned tool calls."
    else:
        prefix = f"Run status: {status or 'unknown'}."

    lines = [prefix]
    if citations:
        lines.append("Artifacts:")
        lines.extend([f"- {path}" for path in citations])
    if validation_warnings:
        lines.append("Planner notes:")
        lines.extend([f"- {note}" for note in validation_warnings[:5]])
    return "\n".join(lines)
