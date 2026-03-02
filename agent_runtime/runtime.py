from __future__ import annotations

from typing import Any, Dict, List, Optional

from .adk_adapter import AdkRuntimeObjects, build_runtime_objects
from .chat_runtime import ChatRuntime
from .context_injection import ContextInjector
from .store import FileWorkspaceStore
from .tools import ToolRegistry


class AgentRuntime:
    def __init__(self, store: Optional[FileWorkspaceStore] = None, max_iterations: int = 30) -> None:
        self.store = store or FileWorkspaceStore()
        self.tools = ToolRegistry(self.store)
        self.max_iterations = max_iterations
        self.adk_runtime: AdkRuntimeObjects = build_runtime_objects(
            store=self.store,
            tools=self.tools,
            max_iterations=max_iterations,
        )
        self.context_injector = ContextInjector(store=self.store, tools=self.tools)
        self.chat = ChatRuntime(
            store=self.store,
            run_turn_fn=self.adk_runtime.runner.run_turn,
            context_injector=self.context_injector,
        )

    def create_session(self, tenant_id: str, objective: str, prompt_profile: str = "default", mode: str = "hybrid") -> Dict[str, Any]:
        return self.tools.create_session(
            tenant_id=tenant_id,
            objective=objective,
            prompt_profile=prompt_profile,
            mode=mode,
        )

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.tools.get_session(session_id)

    def runtime_descriptor(self) -> Dict[str, Any]:
        payload = self.adk_runtime.descriptor()
        payload.update(
            {
                "planner_backend_default": "gemini",
                "planner_fallback_enabled": True,
                "chat_mode_enabled": True,
            }
        )
        return payload

    def run_turn(self, session_id: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return self.adk_runtime.runner.run_turn(session_id=session_id, tool_calls=tool_calls)

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        return self.adk_runtime.runner.resume_session(session_id=session_id)

    def list_artifacts(self, session_id: str) -> Dict[str, Any]:
        return {"artifacts": self.store.list_artifacts(session_id=session_id)}

    def chat_turn(self, session_id: str, message: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.chat.chat_turn(session_id=session_id, message=message, options=options)

    def list_messages(self, session_id: str) -> Dict[str, Any]:
        return {"messages": self.chat.list_messages(session_id=session_id)}

    def build_context_snapshot(self, session_id: str) -> Dict[str, Any]:
        return self.chat.build_context_snapshot(session_id=session_id)
