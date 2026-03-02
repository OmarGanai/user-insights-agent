from __future__ import annotations

from typing import Any, Dict, List, Optional

from .adk_adapter import AdkRuntimeObjects, build_runtime_objects
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
        return self.adk_runtime.descriptor()

    def run_turn(self, session_id: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return self.adk_runtime.runner.run_turn(session_id=session_id, tool_calls=tool_calls)

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        return self.adk_runtime.runner.resume_session(session_id=session_id)

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
