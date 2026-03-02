from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import ToolResult
from .store import FileWorkspaceStore
from .tools import ToolRegistry


TERMINAL_STATUSES = {"completed", "blocked", "failed", "expired"}


class AgentRuntime:
    def __init__(self, store: Optional[FileWorkspaceStore] = None, max_iterations: int = 30) -> None:
        self.store = store or FileWorkspaceStore()
        self.tools = ToolRegistry(self.store)
        self.max_iterations = max_iterations

    def create_session(self, tenant_id: str, objective: str, prompt_profile: str = "default", mode: str = "hybrid") -> Dict[str, Any]:
        return self.tools.create_session(
            tenant_id=tenant_id,
            objective=objective,
            prompt_profile=prompt_profile,
            mode=mode,
        )

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.tools.get_session(session_id)

    def run_turn(self, session_id: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        session = self.store.get_session(session_id)
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

        session = self.store.update_session(
            session_id,
            {
                "status": "running",
                "block_reason": "",
            },
        )

        results: List[Dict[str, Any]] = []
        iteration_count = int(session.get("iteration_count") or 0)
        complete_called = False

        while remaining_calls and iteration_count < self.max_iterations:
            tool_call = remaining_calls.pop(0)
            tool_name = str(tool_call.get("tool") or "").strip()
            args = tool_call.get("args")
            if not isinstance(args, dict):
                args = {}

            attempt = 0
            result: ToolResult
            while True:
                attempt += 1
                result = self.tools.invoke(tool_name, args)
                if result.success:
                    break
                if not result.error_code.startswith("recoverable_"):
                    break
                if attempt >= 3:
                    break

            iteration_count += 1
            event = {
                "type": "tool_result",
                "tool": tool_name,
                "attempt": attempt,
                "result": result.to_dict(),
            }
            self.store.append_event(session_id, event)
            results.append({"tool": tool_name, **result.to_dict()})

            self.store.update_session(session_id, {"iteration_count": iteration_count})
            self.store.save_checkpoint(session_id, {"remaining_calls": remaining_calls})

            if result.requires_approval:
                # Re-queue the gated tool call so resume can execute it after approval.
                remaining_calls.insert(0, tool_call)
                self.store.save_checkpoint(session_id, {"remaining_calls": remaining_calls})
                self.store.update_session(
                    session_id,
                    {
                        "status": "waiting_approval",
                        "block_reason": "Approval required",
                    },
                )
                break

            if not result.success:
                self.store.update_session(
                    session_id,
                    {
                        "status": "failed",
                        "block_reason": str((result.output or {}).get("message", "tool failed")),
                    },
                )
                break

            if tool_name == "complete_task":
                complete_called = True
                completion_status = str((result.output or {}).get("status") or "completed")
                block_reason = str((result.output or {}).get("reason") or "")
                if completion_status in {"completed", "partial"}:
                    self.store.update_session(session_id, {"status": "completed", "block_reason": block_reason})
                else:
                    self.store.update_session(session_id, {"status": "blocked", "block_reason": block_reason or "Blocked by complete_task"})
                self.store.clear_checkpoint(session_id)
                break

        if not remaining_calls and not complete_called:
            latest_session = self.store.get_session(session_id)
            if latest_session.get("status") == "running":
                self.store.update_session(
                    session_id,
                    {
                        "status": "blocked",
                        "block_reason": "Run ended without complete_task",
                    },
                )

        if iteration_count >= self.max_iterations:
            latest_session = self.store.get_session(session_id)
            if latest_session.get("status") == "running":
                self.store.update_session(
                    session_id,
                    {
                        "status": "blocked",
                        "block_reason": "Iteration budget exhausted",
                    },
                )

        updated = self.store.get_session(session_id)
        checkpoint = self.store.load_checkpoint(session_id)
        return {
            "session": updated,
            "results": results,
            "remaining_calls": len(checkpoint.get("remaining_calls") or []),
        }

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        session = self.store.get_session(session_id)
        status = str(session.get("status") or "")
        if status in TERMINAL_STATUSES:
            return {"session": session, "results": [], "message": "Session is terminal"}

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

    def list_artifacts(self, session_id: str) -> Dict[str, Any]:
        session = self.store.get_session(session_id)
        run_dir = self.store.tenant_root(session["tenant_id"]) / "runs" / session_id
        if not run_dir.exists():
            return {"artifacts": []}
        artifacts = []
        for path in sorted(run_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name == "checkpoint.json" or "/.artifacts/" in str(path):
                continue
            artifacts.append({"path": self.store._relative_to_workspace(path), "size": path.stat().st_size})
        return {"artifacts": artifacts}
