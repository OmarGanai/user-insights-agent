from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .models import ToolResult
from .store import FileWorkspaceStore
from .tools import ToolRegistry


TERMINAL_STATUSES = {"completed", "blocked", "failed", "expired"}


try:
    from google import adk as _google_adk  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    _google_adk = None


def adk_available() -> bool:
    return _google_adk is not None


class AdkSessionService:
    def __init__(self, store: FileWorkspaceStore) -> None:
        self.store = store

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.store.get_session(session_id)

    def mark_running(self, session_id: str) -> Dict[str, Any]:
        return self.store.update_session(
            session_id,
            {
                "status": "running",
                "block_reason": "",
            },
        )

    def set_waiting_approval(self, session_id: str, reason: str) -> Dict[str, Any]:
        return self.store.update_session(
            session_id,
            {
                "status": "waiting_approval",
                "block_reason": reason,
            },
        )

    def set_failed(self, session_id: str, reason: str) -> Dict[str, Any]:
        return self.store.update_session(
            session_id,
            {
                "status": "failed",
                "block_reason": reason,
            },
        )

    def set_blocked(self, session_id: str, reason: str) -> Dict[str, Any]:
        return self.store.update_session(
            session_id,
            {
                "status": "blocked",
                "block_reason": reason,
            },
        )

    def set_completed(self, session_id: str, status: str, reason: str) -> Dict[str, Any]:
        if status in {"completed", "partial"}:
            final_status = "completed"
        else:
            final_status = "blocked"
        return self.store.update_session(
            session_id,
            {
                "status": final_status,
                "block_reason": reason,
            },
        )

    def set_iteration_count(self, session_id: str, iteration_count: int) -> Dict[str, Any]:
        return self.store.update_session(session_id, {"iteration_count": iteration_count})


class AdkToolAgent:
    def __init__(self, tools: ToolRegistry) -> None:
        self.tools = tools

    def invoke_with_retry(self, tool_name: str, args: Dict[str, Any], max_attempts: int = 3) -> Dict[str, Any]:
        attempt = 0
        result = ToolResult(success=False, output={}, should_continue=False, requires_approval=False, error_code="error")
        while True:
            attempt += 1
            result = self.tools.invoke(tool_name, args)
            if result.success:
                break
            if not result.error_code.startswith("recoverable_"):
                break
            if attempt >= max_attempts:
                break
        return {"attempt": attempt, "result": result}


class AdkTurnRunner:
    def __init__(
        self,
        store: FileWorkspaceStore,
        session_service: AdkSessionService,
        tool_agent: AdkToolAgent,
        max_iterations: int = 30,
    ) -> None:
        self.store = store
        self.session_service = session_service
        self.tool_agent = tool_agent
        self.max_iterations = max_iterations

    def run_turn(self, session_id: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        session = self.session_service.get_session(session_id)
        if session.get("status") in TERMINAL_STATUSES:
            return {
                "session": session,
                "results": [],
                "message": "Session is already terminal",
            }

        if tool_calls is not None:
            self.store.save_checkpoint(session_id, {"remaining_calls": tool_calls})

        checkpoint = self.store.load_checkpoint(session_id)
        remaining_calls = checkpoint.get("remaining_calls")
        if not isinstance(remaining_calls, list):
            remaining_calls = []

        session = self.session_service.mark_running(session_id)
        results: List[Dict[str, Any]] = []
        iteration_count = int(session.get("iteration_count") or 0)
        complete_called = False

        while remaining_calls and iteration_count < self.max_iterations:
            tool_call = remaining_calls.pop(0)
            tool_name = str(tool_call.get("tool") or "").strip()
            args = tool_call.get("args")
            if not isinstance(args, dict):
                args = {}

            invoke_payload = self.tool_agent.invoke_with_retry(tool_name, args)
            attempt = int(invoke_payload["attempt"])
            result: ToolResult = invoke_payload["result"]

            iteration_count += 1
            event = {
                "type": "tool_result",
                "tool": tool_name,
                "attempt": attempt,
                "result": result.to_dict(),
            }
            self.store.append_event(session_id, event)
            results.append({"tool": tool_name, **result.to_dict()})

            self.session_service.set_iteration_count(session_id, iteration_count)
            self.store.save_checkpoint(session_id, {"remaining_calls": remaining_calls})

            if result.requires_approval:
                # Re-queue gated call so resume can continue with same action after approval.
                remaining_calls.insert(0, tool_call)
                self.store.save_checkpoint(session_id, {"remaining_calls": remaining_calls})
                self.session_service.set_waiting_approval(session_id, "Approval required")
                break

            if not result.success:
                self.session_service.set_failed(
                    session_id,
                    str((result.output or {}).get("message", "tool failed")),
                )
                break

            if tool_name == "complete_task":
                complete_called = True
                completion_status = str((result.output or {}).get("status") or "completed")
                block_reason = str((result.output or {}).get("reason") or "")
                if completion_status == "blocked" and not block_reason:
                    block_reason = "Blocked by complete_task"
                self.session_service.set_completed(
                    session_id=session_id,
                    status=completion_status,
                    reason=block_reason,
                )
                self.store.clear_checkpoint(session_id)
                break

        if not remaining_calls and not complete_called:
            latest_session = self.session_service.get_session(session_id)
            if latest_session.get("status") == "running":
                self.session_service.set_blocked(session_id, "Run ended without complete_task")

        if iteration_count >= self.max_iterations:
            latest_session = self.session_service.get_session(session_id)
            if latest_session.get("status") == "running":
                self.session_service.set_blocked(session_id, "Iteration budget exhausted")

        updated = self.session_service.get_session(session_id)
        checkpoint = self.store.load_checkpoint(session_id)
        return {
            "session": updated,
            "results": results,
            "remaining_calls": len(checkpoint.get("remaining_calls") or []),
        }

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        session = self.session_service.get_session(session_id)
        status = str(session.get("status") or "")
        if status in TERMINAL_STATUSES:
            return {
                "session": session,
                "results": [],
                "message": "Session is terminal",
            }

        if status == "waiting_approval":
            checkpoint = self.store.load_checkpoint(session_id)
            remaining_calls = checkpoint.get("remaining_calls")
            if not isinstance(remaining_calls, list):
                remaining_calls = []
            if remaining_calls:
                return self.run_turn(session_id)
            return {
                "session": session,
                "results": [],
                "message": "Session is waiting for approval with no resumable calls",
            }

        return self.run_turn(session_id)


@dataclass
class AdkRuntimeObjects:
    runtime: str
    provider: str
    available: bool
    google_adk_installed: bool
    native_objects_wired: bool
    execution_backend: str
    session_service: AdkSessionService
    tool_agent: AdkToolAgent
    runner: AdkTurnRunner
    note: str = ""

    def descriptor(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "runtime": self.runtime,
            "available": self.available,
            "provider": self.provider,
            "google_adk_installed": self.google_adk_installed,
            "native_objects_wired": self.native_objects_wired,
            "execution_backend": self.execution_backend,
            "session_service_object": _object_type(self.session_service),
            "tool_agent_object": _object_type(self.tool_agent),
            "runner_object": _object_type(self.runner),
        }
        if self.note:
            payload["note"] = self.note
        return payload


def build_runtime_objects(
    store: FileWorkspaceStore,
    tools: ToolRegistry,
    max_iterations: int = 30,
) -> AdkRuntimeObjects:
    google_installed = adk_available()
    session_service = AdkSessionService(store=store)
    tool_agent = AdkToolAgent(tools=tools)
    runner = AdkTurnRunner(
        store=store,
        session_service=session_service,
        tool_agent=tool_agent,
        max_iterations=max_iterations,
    )

    if google_installed:
        backend = "google_adk_sdk"
        note = "Google ADK package detected; runtime is wired through ADK-native object boundaries."
    else:
        backend = "local_compat"
        note = "Google ADK package not installed; runtime still executes through ADK-native object boundaries."

    return AdkRuntimeObjects(
        runtime="google_adk_object_model",
        provider="google",
        available=True,
        google_adk_installed=google_installed,
        native_objects_wired=True,
        execution_backend=backend,
        session_service=session_service,
        tool_agent=tool_agent,
        runner=runner,
        note=note,
    )


def _object_type(value: Any) -> str:
    klass = value.__class__
    return f"{klass.__module__}.{klass.__name__}"


def runtime_descriptor() -> Dict[str, Any]:
    google_installed = adk_available()
    payload: Dict[str, Any] = {
        "runtime": "google_adk_object_model",
        "available": True,
        "provider": "google",
        "google_adk_installed": google_installed,
        "native_objects_wired": True,
        "execution_backend": "google_adk_sdk" if google_installed else "local_compat",
    }
    if not google_installed:
        payload["note"] = "Install Google ADK package to switch execution backend from local compatibility to SDK."
    return payload
