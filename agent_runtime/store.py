from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import AgentSession, AgentTask, ApprovalRequest, ArtifactRef, utc_now_iso


INDEX_FILE = ".indexes.json"
DEFAULT_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent / "workspace"


class FileWorkspaceStore:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root or DEFAULT_WORKSPACE_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        if not self._index_path().exists():
            self._write_json(
                self._index_path(),
                {"sessions": {}, "tasks": {}, "approvals": {}, "runs": {}, "artifacts": {}},
            )

    def _index_path(self) -> Path:
        return self.root / INDEX_FILE

    def _read_indexes(self) -> Dict[str, Dict[str, Any]]:
        payload = self._read_json(self._index_path(), default={})
        if not isinstance(payload, dict):
            return {"sessions": {}, "tasks": {}, "approvals": {}, "runs": {}, "artifacts": {}}
        for key in ("sessions", "tasks", "approvals", "runs", "artifacts"):
            payload.setdefault(key, {})
            if not isinstance(payload[key], dict):
                payload[key] = {}
        return payload

    def _write_indexes(self, indexes: Dict[str, Dict[str, Any]]) -> None:
        self._write_json(self._index_path(), indexes)

    def tenant_root(self, tenant_id: str) -> Path:
        return self.root / "tenants" / tenant_id

    def ensure_tenant(self, tenant_id: str) -> Path:
        root = self.tenant_root(tenant_id)
        for rel in (
            "config",
            "prompts",
            "runs",
            "sessions",
            "approvals/pending",
            "approvals/resolved",
            "memory",
            "events",
            "capabilities",
        ):
            (root / rel).mkdir(parents=True, exist_ok=True)

        tenant_config = root / "config" / "tenant.yaml"
        if not tenant_config.exists():
            template = {
                "tenant_id": tenant_id,
                "display_name": "Tenant",
                "amplitude": {
                    "app_slug": "tenant",
                    "base_url": "https://amplitude.com/api/3",
                },
                "typeform": {
                    "enabled": False,
                },
                "slack": {
                    "enabled": False,
                    "webhook_env": "SLACK_WEBHOOK_URL",
                },
            }
            self._write_text(tenant_config, json.dumps(template, indent=2) + "\n")

        prompt_profile = root / "prompts" / "default.md"
        if not prompt_profile.exists():
            self._write_text(prompt_profile, "# Tenant Default Prompt\nOperate safely within tenant boundaries.\n")

        temporal_memory = root / "memory" / "temporal-memory.json"
        if not temporal_memory.exists():
            self._write_json(
                temporal_memory,
                {
                    "schema_version": 1,
                    "last_updated_utc": "",
                    "latest_report": None,
                    "previous_report": None,
                },
            )

        return root

    def _session_path(self, tenant_id: str, session_id: str) -> Path:
        return self.tenant_root(tenant_id) / "sessions" / f"{session_id}.json"

    def _task_path(self, tenant_id: str, session_id: str, task_id: str) -> Path:
        return self.tenant_root(tenant_id) / "sessions" / session_id / "tasks" / f"{task_id}.json"

    def _approval_path(self, tenant_id: str, status: str, approval_id: str) -> Path:
        return self.tenant_root(tenant_id) / "approvals" / status / f"{approval_id}.json"

    def _checkpoint_path(self, tenant_id: str, run_id: str) -> Path:
        return self.tenant_root(tenant_id) / "runs" / run_id / "checkpoint.json"

    def _events_path(self, tenant_id: str) -> Path:
        return self.tenant_root(tenant_id) / "events" / "events.ndjson"

    def _next_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    def create_session(self, tenant_id: str, objective: str, prompt_profile: str, mode: str) -> Dict[str, Any]:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not objective.strip():
            raise ValueError("objective is required")

        self.ensure_tenant(tenant_id)
        session_id = self._next_id("ses")
        run_id = session_id
        checkpoint_rel = f"workspace/tenants/{tenant_id}/runs/{run_id}/checkpoint.json"
        now = utc_now_iso()
        session = AgentSession(
            id=session_id,
            tenant_id=tenant_id,
            objective=objective.strip(),
            prompt_profile=prompt_profile.strip() or "default",
            status="pending",
            mode=mode.strip() or "hybrid",
            iteration_count=0,
            checkpoint_path=checkpoint_rel,
            created_at=now,
            updated_at=now,
            block_reason="",
        )
        self._write_json(self._session_path(tenant_id, session_id), session.to_dict())
        (self.tenant_root(tenant_id) / "runs" / run_id).mkdir(parents=True, exist_ok=True)

        indexes = self._read_indexes()
        indexes["sessions"][session_id] = tenant_id
        indexes["runs"][run_id] = tenant_id
        self._write_indexes(indexes)
        return session.to_dict()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        tenant_id = self._tenant_for_session(session_id)
        payload = self._read_json(self._session_path(tenant_id, session_id), default={})
        if not payload:
            raise KeyError(f"Unknown session_id: {session_id}")
        return payload

    def update_session(self, session_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = self._tenant_for_session(session_id)
        path = self._session_path(tenant_id, session_id)
        session = self._read_json(path, default={})
        if not session:
            raise KeyError(f"Unknown session_id: {session_id}")
        for key, value in fields.items():
            if key in {"id", "tenant_id", "created_at"}:
                continue
            session[key] = value
        session["updated_at"] = utc_now_iso()
        self._write_json(path, session)
        return session

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        tenant_id = self._tenant_for_session(session_id)
        session_path = self._session_path(tenant_id, session_id)
        session_payload = self._read_json(session_path, default={})
        if session_path.exists():
            session_path.unlink()

        session_task_dir = self.tenant_root(tenant_id) / "sessions" / session_id
        if session_task_dir.exists():
            shutil.rmtree(session_task_dir)

        run_dir = self.tenant_root(tenant_id) / "runs" / session_id
        if run_dir.exists():
            shutil.rmtree(run_dir)

        indexes = self._read_indexes()
        indexes["sessions"].pop(session_id, None)
        indexes["runs"].pop(session_id, None)

        for task_id, meta in list(indexes["tasks"].items()):
            if isinstance(meta, dict) and meta.get("session_id") == session_id:
                indexes["tasks"].pop(task_id, None)

        for approval_id, meta in list(indexes["approvals"].items()):
            if isinstance(meta, dict) and meta.get("session_id") == session_id:
                indexes["approvals"].pop(approval_id, None)

        for artifact_path, meta in list(indexes["artifacts"].items()):
            if isinstance(meta, dict) and meta.get("run_id") == session_id:
                indexes["artifacts"].pop(artifact_path, None)

        self._write_indexes(indexes)
        return session_payload

    def create_task(self, session_id: str, title: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not title.strip():
            raise ValueError("title is required")
        session = self.get_session(session_id)
        tenant_id = session["tenant_id"]

        task_id = self._next_id("task")
        now = utc_now_iso()
        task = AgentTask(
            id=task_id,
            session_id=session_id,
            title=title.strip(),
            status="pending",
            notes="",
            metadata=metadata or {},
            started_at=now,
            ended_at="",
        )
        path = self._task_path(tenant_id, session_id, task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(path, task.to_dict())

        indexes = self._read_indexes()
        indexes["tasks"][task_id] = {"tenant_id": tenant_id, "session_id": session_id}
        self._write_indexes(indexes)
        return task.to_dict()

    def list_tasks(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        task_dir = self.tenant_root(session["tenant_id"]) / "sessions" / session_id / "tasks"
        if not task_dir.exists():
            return []
        tasks: List[Dict[str, Any]] = []
        for path in sorted(task_dir.glob("*.json")):
            task = self._read_json(path, default={})
            if task:
                tasks.append(task)
        return tasks

    def update_task(self, task_id: str, status: str, notes: str) -> Dict[str, Any]:
        indexes = self._read_indexes()
        meta = indexes["tasks"].get(task_id)
        if not isinstance(meta, dict):
            raise KeyError(f"Unknown task_id: {task_id}")

        tenant_id = str(meta["tenant_id"])
        session_id = str(meta["session_id"])
        path = self._task_path(tenant_id, session_id, task_id)
        task = self._read_json(path, default={})
        if not task:
            raise KeyError(f"Unknown task_id: {task_id}")

        task["status"] = status
        task["notes"] = notes
        if status in {"completed", "blocked", "failed"}:
            task["ended_at"] = utc_now_iso()
        self._write_json(path, task)
        return task

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        indexes = self._read_indexes()
        meta = indexes["tasks"].get(task_id)
        if not isinstance(meta, dict):
            raise KeyError(f"Unknown task_id: {task_id}")

        tenant_id = str(meta["tenant_id"])
        session_id = str(meta["session_id"])
        path = self._task_path(tenant_id, session_id, task_id)
        payload = self._read_json(path, default={})
        if path.exists():
            path.unlink()
        indexes["tasks"].pop(task_id, None)
        self._write_indexes(indexes)
        return payload

    def create_artifact(self, run_id: str, kind: str, rel_path: str, content: Any) -> Dict[str, Any]:
        tenant_id = self._tenant_for_run(run_id)
        safe_rel = self._safe_relative_path(rel_path)
        full_path = self.tenant_root(tenant_id) / "runs" / run_id / safe_rel
        full_path.parent.mkdir(parents=True, exist_ok=True)

        raw = self._normalize_artifact_content(content)
        if full_path.suffix.lower() == ".json":
            parsed = self._try_parse_json(raw)
            if parsed is not None:
                self._write_json(full_path, parsed)
            else:
                self._write_text(full_path, raw)
        else:
            self._write_text(full_path, raw)

        checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        artifact_id = self._next_id("art")
        ref = ArtifactRef(
            id=artifact_id,
            run_id=run_id,
            kind=kind.strip() or "generic",
            path=self._relative_to_workspace(full_path),
            checksum=checksum,
            created_at=utc_now_iso(),
        )

        meta_dir = self.tenant_root(tenant_id) / "runs" / run_id / ".artifacts"
        meta_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(meta_dir / f"{artifact_id}.json", ref.to_dict())

        indexes = self._read_indexes()
        indexes["artifacts"][ref.path] = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "artifact_id": artifact_id,
        }
        self._write_indexes(indexes)

        return ref.to_dict()

    def read_artifact(self, rel_path: str) -> Dict[str, Any]:
        full_path = self._resolve_artifact_path(rel_path)
        payload: Any
        if full_path.suffix.lower() == ".json":
            payload = self._read_json(full_path, default={})
        else:
            payload = full_path.read_text(encoding="utf-8")
        return {
            "path": self._relative_to_workspace(full_path),
            "content": payload,
        }

    def update_artifact(self, rel_path: str, content: Any) -> Dict[str, Any]:
        full_path = self._resolve_artifact_path(rel_path)
        raw = self._normalize_artifact_content(content)
        if full_path.suffix.lower() == ".json":
            parsed = self._try_parse_json(raw)
            if parsed is not None:
                self._write_json(full_path, parsed)
            else:
                self._write_text(full_path, raw)
        else:
            self._write_text(full_path, raw)

        checksum = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return {
            "path": self._relative_to_workspace(full_path),
            "checksum": checksum,
            "updated_at": utc_now_iso(),
        }

    def delete_artifact(self, rel_path: str) -> Dict[str, Any]:
        full_path = self._resolve_artifact_path(rel_path)
        payload = self.read_artifact(rel_path)
        if full_path.exists():
            full_path.unlink()

        indexes = self._read_indexes()
        indexes["artifacts"].pop(payload["path"], None)
        self._write_indexes(indexes)
        return payload

    def create_approval_request(
        self,
        session_id: str,
        action_type: str,
        payload_path: str,
        summary: str,
    ) -> Dict[str, Any]:
        session = self.get_session(session_id)
        tenant_id = session["tenant_id"]
        approval_id = self._next_id("apr")
        now = utc_now_iso()
        approval = ApprovalRequest(
            id=approval_id,
            session_id=session_id,
            action_type=action_type.strip(),
            payload_path=payload_path.strip(),
            summary=summary.strip(),
            status="pending",
            requested_at=now,
            resolved_at="",
            resolver="",
            reviewer_note="",
        )
        path = self._approval_path(tenant_id, "pending", approval_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(path, approval.to_dict())

        indexes = self._read_indexes()
        indexes["approvals"][approval_id] = {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "status": "pending",
        }
        self._write_indexes(indexes)
        return approval.to_dict()

    def get_approval_request(self, approval_id: str) -> Dict[str, Any]:
        tenant_id, status = self._tenant_and_status_for_approval(approval_id)
        path = self._approval_path(tenant_id, "pending" if status == "pending" else "resolved", approval_id)
        payload = self._read_json(path, default={})
        if not payload:
            raise KeyError(f"Unknown approval_id: {approval_id}")
        return payload

    def resolve_approval_request(
        self,
        approval_id: str,
        decision: str,
        reviewer_note: str,
        resolver: str = "human",
    ) -> Dict[str, Any]:
        tenant_id, status = self._tenant_and_status_for_approval(approval_id)
        if status != "pending":
            raise ValueError(f"Approval {approval_id} is already resolved")

        pending_path = self._approval_path(tenant_id, "pending", approval_id)
        approval = self._read_json(pending_path, default={})
        if not approval:
            raise KeyError(f"Unknown approval_id: {approval_id}")

        normalized_decision = decision.strip().lower()
        if normalized_decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")

        approval["status"] = normalized_decision
        approval["resolved_at"] = utc_now_iso()
        approval["resolver"] = resolver
        approval["reviewer_note"] = reviewer_note.strip()

        resolved_path = self._approval_path(tenant_id, "resolved", approval_id)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(resolved_path, approval)
        if pending_path.exists():
            pending_path.unlink()

        indexes = self._read_indexes()
        if approval_id in indexes["approvals"]:
            indexes["approvals"][approval_id]["status"] = normalized_decision
        self._write_indexes(indexes)
        return approval

    def delete_approval_request(self, approval_id: str) -> Dict[str, Any]:
        tenant_id, status = self._tenant_and_status_for_approval(approval_id)
        path = self._approval_path(tenant_id, "pending" if status == "pending" else "resolved", approval_id)
        payload = self._read_json(path, default={})
        if path.exists():
            path.unlink()

        indexes = self._read_indexes()
        indexes["approvals"].pop(approval_id, None)
        self._write_indexes(indexes)
        return payload

    def create_metric_contract(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_tenant(tenant_id)
        path = self.tenant_root(tenant_id) / "config" / "metric-contract.json"
        record = {
            "tenant_id": tenant_id,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "payload": payload,
        }
        self._write_json(path, record)
        return record

    def read_metric_contract(self, tenant_id: str) -> Dict[str, Any]:
        path = self.tenant_root(tenant_id) / "config" / "metric-contract.json"
        return self._read_json(path, default={})

    def update_metric_contract(self, tenant_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = self.read_metric_contract(tenant_id)
        if not current:
            current = self.create_metric_contract(tenant_id, payload={})

        payload = current.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        payload.update(patch)
        current["payload"] = payload
        current["updated_at"] = utc_now_iso()
        path = self.tenant_root(tenant_id) / "config" / "metric-contract.json"
        self._write_json(path, current)
        return current

    def delete_metric_contract(self, tenant_id: str) -> Dict[str, Any]:
        path = self.tenant_root(tenant_id) / "config" / "metric-contract.json"
        payload = self._read_json(path, default={})
        if path.exists():
            path.unlink()
        return payload

    def append_event(self, session_id: str, event: Dict[str, Any]) -> None:
        session = self.get_session(session_id)
        tenant_id = session["tenant_id"]
        event_payload = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "timestamp": utc_now_iso(),
        }
        event_payload.update(event)

        path = self._events_path(tenant_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event_payload, ensure_ascii=True) + "\n")

    def save_checkpoint(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self.get_session(session_id)
        path = self._checkpoint_path(session["tenant_id"], session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "session_id": session_id,
            "saved_at": utc_now_iso(),
            **payload,
        }
        self._write_json(path, checkpoint)
        return checkpoint

    def load_checkpoint(self, session_id: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        path = self._checkpoint_path(session["tenant_id"], session_id)
        return self._read_json(path, default={})

    def clear_checkpoint(self, session_id: str) -> None:
        session = self.get_session(session_id)
        path = self._checkpoint_path(session["tenant_id"], session_id)
        if path.exists():
            path.unlink()

    def latest_pending_approval(
        self,
        session_id: str,
        action_type: str,
        payload_path: str,
    ) -> Optional[Dict[str, Any]]:
        session = self.get_session(session_id)
        tenant_id = session["tenant_id"]
        pending_dir = self.tenant_root(tenant_id) / "approvals" / "pending"
        if not pending_dir.exists():
            return None

        latest: Optional[Dict[str, Any]] = None
        for path in sorted(pending_dir.glob("*.json")):
            approval = self._read_json(path, default={})
            if not approval:
                continue
            if approval.get("session_id") != session_id:
                continue
            if approval.get("action_type") != action_type:
                continue
            if approval.get("payload_path") != payload_path:
                continue
            latest = approval
        return latest

    def approved_action_exists(self, session_id: str, action_type: str, payload_path: str) -> bool:
        session = self.get_session(session_id)
        tenant_id = session["tenant_id"]
        resolved_dir = self.tenant_root(tenant_id) / "approvals" / "resolved"
        if not resolved_dir.exists():
            return False

        for path in sorted(resolved_dir.glob("*.json")):
            approval = self._read_json(path, default={})
            if not approval:
                continue
            if approval.get("session_id") != session_id:
                continue
            if approval.get("action_type") != action_type:
                continue
            if approval.get("payload_path") != payload_path:
                continue
            if approval.get("status") == "approved":
                return True
        return False

    def read_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        self.ensure_tenant(tenant_id)
        path = self.tenant_root(tenant_id) / "config" / "tenant.yaml"
        raw = path.read_text(encoding="utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def write_tenant_config(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_tenant(tenant_id)
        path = self.tenant_root(tenant_id) / "config" / "tenant.yaml"
        self._write_text(path, json.dumps(payload, indent=2) + "\n")
        return payload

    def _tenant_for_session(self, session_id: str) -> str:
        indexes = self._read_indexes()
        tenant_id = indexes["sessions"].get(session_id)
        if not tenant_id:
            raise KeyError(f"Unknown session_id: {session_id}")
        return str(tenant_id)

    def _tenant_for_run(self, run_id: str) -> str:
        indexes = self._read_indexes()
        tenant_id = indexes["runs"].get(run_id)
        if not tenant_id:
            raise KeyError(f"Unknown run_id: {run_id}")
        return str(tenant_id)

    def _tenant_and_status_for_approval(self, approval_id: str) -> tuple[str, str]:
        indexes = self._read_indexes()
        meta = indexes["approvals"].get(approval_id)
        if not isinstance(meta, dict):
            raise KeyError(f"Unknown approval_id: {approval_id}")
        tenant_id = str(meta.get("tenant_id") or "")
        status = str(meta.get("status") or "pending")
        return tenant_id, status

    def _safe_relative_path(self, value: str) -> Path:
        rel = Path(value.strip())
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Artifact path must be relative within workspace")
        if str(rel).strip() == "":
            raise ValueError("Artifact path is required")
        return rel

    def _resolve_artifact_path(self, rel_path: str) -> Path:
        rel = self._safe_relative_path(rel_path)
        full = self.root / rel
        if not str(full.resolve()).startswith(str(self.root.resolve())):
            raise ValueError("Artifact path escapes workspace")
        if not full.exists():
            raise FileNotFoundError(f"Artifact does not exist: {rel_path}")
        return full

    def _relative_to_workspace(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.root.resolve()))

    def _normalize_artifact_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        return json.dumps(content, indent=2, ensure_ascii=True)

    def _try_parse_json(self, raw: str) -> Optional[Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default

    def _write_json(self, path: Path, payload: Any) -> None:
        raw = json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=False)
        self._write_text(path, raw + "\n")

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
