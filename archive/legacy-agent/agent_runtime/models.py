from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

SessionStatus = Literal[
    "pending",
    "running",
    "waiting_approval",
    "completed",
    "blocked",
    "failed",
    "expired",
]
TaskStatus = Literal["pending", "running", "completed", "blocked", "failed"]
ApprovalStatus = Literal["pending", "approved", "rejected", "deleted"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class AgentSession:
    id: str
    tenant_id: str
    objective: str
    prompt_profile: str
    prompt_version: str
    prompt_variant: str
    prompt_path: str
    status: SessionStatus
    mode: str
    iteration_count: int
    checkpoint_path: str
    created_at: str
    updated_at: str
    block_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentTask:
    id: str
    session_id: str
    title: str
    status: TaskStatus
    notes: str
    metadata: Dict[str, Any]
    started_at: str
    ended_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovalRequest:
    id: str
    session_id: str
    action_type: str
    payload_path: str
    summary: str
    status: ApprovalStatus
    requested_at: str
    resolved_at: str
    resolver: str
    reviewer_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactRef:
    id: str
    run_id: str
    kind: str
    path: str
    checksum: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChatMessage:
    id: str
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolPlan:
    plan_id: str
    tool_calls: list[Dict[str, Any]]
    backend: Literal["gemini", "deterministic"]
    fallback_used: bool
    raw_model_output: str
    validation_warnings: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolResult:
    success: bool
    output: Any
    should_continue: bool
    requires_approval: bool
    error_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityManifest:
    tenant_id: str
    fetched_at: str
    ttl_expires_at: str
    amplitude: Dict[str, Any]
    typeform: Dict[str, Any]
    slack: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def ok(output: Any = None, *, should_continue: bool = True) -> ToolResult:
    return ToolResult(success=True, output=output, should_continue=should_continue, requires_approval=False)


def needs_approval(output: Any = None) -> ToolResult:
    return ToolResult(success=False, output=output or {}, should_continue=False, requires_approval=True)


def error(message: str, *, code: str = "error", recoverable: bool = False) -> ToolResult:
    prefix = "recoverable_" if recoverable else ""
    return ToolResult(
        success=False,
        output={"message": message},
        should_continue=False,
        requires_approval=False,
        error_code=f"{prefix}{code}",
    )
