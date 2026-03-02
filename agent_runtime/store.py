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
DEFAULT_PROMPT_VERSION = "v1"
DEFAULT_CANARY_PERCENT = 10


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
                "prompt_profiles": {
                    "default": {
                        "stable_version": DEFAULT_PROMPT_VERSION,
                        "versions": {
                            DEFAULT_PROMPT_VERSION: {
                                "path": "default.md",
                                "description": "Tenant default prompt profile",
                            }
                        },
                        "canary": {
                            "enabled": False,
                            "version": "",
                            "percent": DEFAULT_CANARY_PERCENT,
                            "start_at": "",
                            "end_at": "",
                        },
                    }
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
        prompt_selection = self.resolve_prompt_profile(
            tenant_id=tenant_id,
            prompt_profile=prompt_profile,
            session_id=session_id,
        )
        checkpoint_rel = f"workspace/tenants/{tenant_id}/runs/{run_id}/checkpoint.json"
        now = utc_now_iso()
        session = AgentSession(
            id=session_id,
            tenant_id=tenant_id,
            objective=objective.strip(),
            prompt_profile=prompt_selection["profile"],
            prompt_version=prompt_selection["version"],
            prompt_variant=prompt_selection["variant"],
            prompt_path=prompt_selection["path"],
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

    def resolve_prompt_profile(
        self,
        tenant_id: str,
        prompt_profile: str,
        session_id: str,
        now_utc: Optional[datetime] = None,
    ) -> Dict[str, str]:
        profile_name = prompt_profile.strip() or "default"
        config = self.read_tenant_config(tenant_id)
        changed, profile_cfg = self._upsert_prompt_profile_config(config, profile_name)

        stable_version = str(profile_cfg.get("stable_version") or DEFAULT_PROMPT_VERSION).strip() or DEFAULT_PROMPT_VERSION
        versions = profile_cfg.get("versions")
        if not isinstance(versions, dict):
            versions = {}
            profile_cfg["versions"] = versions
            changed = True

        if stable_version not in versions:
            versions[stable_version] = {"path": f"{profile_name}.md", "description": ""}
            changed = True

        canary_cfg = profile_cfg.get("canary")
        if not isinstance(canary_cfg, dict):
            canary_cfg = {}
            profile_cfg["canary"] = canary_cfg
            changed = True

        selected_version = stable_version
        selected_variant = "stable"

        if self._canary_active(canary_cfg, now_utc=now_utc):
            canary_version = str(canary_cfg.get("version") or "").strip()
            canary_percent = int(canary_cfg.get("percent") or 0)
            if canary_version and canary_version in versions and canary_percent > 0:
                bucket = self._canary_bucket(f"{tenant_id}:{profile_name}:{session_id}")
                if bucket < canary_percent:
                    selected_version = canary_version
                    selected_variant = "canary"

        selected_cfg = versions.get(selected_version)
        if not isinstance(selected_cfg, dict):
            selected_cfg = {"path": f"{profile_name}.md", "description": ""}
            versions[selected_version] = selected_cfg
            changed = True

        rel_path = str(selected_cfg.get("path") or "").strip() or f"{profile_name}.md"
        rel = self._safe_prompt_path(rel_path)
        prompt_file = self.tenant_root(tenant_id) / "prompts" / rel
        if not prompt_file.exists():
            prompt_file.parent.mkdir(parents=True, exist_ok=True)
            prompt_file.write_text(
                "# Prompt Profile\n"
                f"profile={profile_name}\n"
                f"version={selected_version}\n",
                encoding="utf-8",
            )

        if changed:
            self.write_tenant_config(tenant_id, config)

        return {
            "profile": profile_name,
            "version": selected_version,
            "variant": selected_variant,
            "path": self._relative_to_workspace(prompt_file),
        }

    def get_prompt_profile_rollout(self, tenant_id: str, prompt_profile: str) -> Dict[str, Any]:
        profile_name = prompt_profile.strip() or "default"
        config = self.read_tenant_config(tenant_id)
        changed, profile_cfg = self._upsert_prompt_profile_config(config, profile_name)
        if changed:
            self.write_tenant_config(tenant_id, config)

        versions = profile_cfg.get("versions")
        if not isinstance(versions, dict):
            versions = {}

        canary = profile_cfg.get("canary")
        if not isinstance(canary, dict):
            canary = {}

        stable_version = str(profile_cfg.get("stable_version") or DEFAULT_PROMPT_VERSION).strip() or DEFAULT_PROMPT_VERSION
        return {
            "tenant_id": tenant_id,
            "prompt_profile": profile_name,
            "stable_version": stable_version,
            "versions": versions,
            "canary": {
                "enabled": bool(canary.get("enabled", False)),
                "version": str(canary.get("version") or "").strip(),
                "percent": int(canary.get("percent") or 0),
                "start_at": str(canary.get("start_at") or "").strip(),
                "end_at": str(canary.get("end_at") or "").strip(),
                "active_now": self._canary_active(canary),
            },
        }

    def update_prompt_profile_rollout(self, tenant_id: str, prompt_profile: str, rollout: Dict[str, Any]) -> Dict[str, Any]:
        profile_name = prompt_profile.strip() or "default"
        config = self.read_tenant_config(tenant_id)
        _, profile_cfg = self._upsert_prompt_profile_config(config, profile_name)

        if not isinstance(rollout, dict):
            raise ValueError("rollout payload must be an object")

        versions_update = rollout.get("versions")
        if versions_update is not None:
            if not isinstance(versions_update, dict):
                raise ValueError("rollout.versions must be an object")
            normalized_versions: Dict[str, Dict[str, str]] = {}
            for version_key, value in versions_update.items():
                version = str(version_key or "").strip()
                if not version:
                    raise ValueError("rollout.versions keys must be non-empty")
                if not isinstance(value, dict):
                    raise ValueError("rollout.versions entries must be objects")
                path = str(value.get("path") or "").strip()
                if not path:
                    raise ValueError(f"rollout.versions.{version}.path is required")
                rel = self._safe_prompt_path(path)
                normalized_versions[version] = {
                    "path": str(rel),
                    "description": str(value.get("description") or "").strip(),
                }
            profile_cfg["versions"] = normalized_versions

        if "stable_version" in rollout:
            stable_version = str(rollout.get("stable_version") or "").strip()
            if not stable_version:
                raise ValueError("rollout.stable_version cannot be empty")
            profile_cfg["stable_version"] = stable_version

        canary_update = rollout.get("canary")
        if canary_update is not None:
            if not isinstance(canary_update, dict):
                raise ValueError("rollout.canary must be an object")
            canary_cfg = profile_cfg.setdefault("canary", {})
            if not isinstance(canary_cfg, dict):
                canary_cfg = {}
                profile_cfg["canary"] = canary_cfg
            for key in ("enabled", "version", "percent", "start_at", "end_at"):
                if key in canary_update:
                    canary_cfg[key] = canary_update[key]

        versions = profile_cfg.get("versions")
        if not isinstance(versions, dict) or not versions:
            raise ValueError("Prompt profile rollout must define at least one version")

        stable_version = str(profile_cfg.get("stable_version") or "").strip() or DEFAULT_PROMPT_VERSION
        if stable_version not in versions:
            raise ValueError("stable_version must exist in versions map")

        canary_cfg = profile_cfg.get("canary")
        if not isinstance(canary_cfg, dict):
            canary_cfg = {}
            profile_cfg["canary"] = canary_cfg

        canary_percent = int(canary_cfg.get("percent") or 0)
        if canary_percent < 0 or canary_percent > 100:
            raise ValueError("canary.percent must be between 0 and 100")
        canary_cfg["percent"] = canary_percent

        canary_version = str(canary_cfg.get("version") or "").strip()
        if canary_version and canary_version not in versions:
            raise ValueError("canary.version must exist in versions map")

        for key in ("start_at", "end_at"):
            value = str(canary_cfg.get(key) or "").strip()
            if value:
                self._parse_iso8601(value)
            canary_cfg[key] = value

        for version_cfg in versions.values():
            if not isinstance(version_cfg, dict):
                continue
            rel = self._safe_prompt_path(str(version_cfg.get("path") or "").strip() or f"{profile_name}.md")
            version_cfg["path"] = str(rel)

        self.write_tenant_config(tenant_id, config)
        return self.get_prompt_profile_rollout(tenant_id, profile_name)

    def evaluate_prompt_profile(self, tenant_id: str, prompt_profile: str) -> Dict[str, Any]:
        profile_name = prompt_profile.strip() or "default"
        indexes = self._read_indexes()
        buckets: Dict[str, Dict[str, Any]] = {}
        total = 0

        for session_id, mapped_tenant in indexes.get("sessions", {}).items():
            if str(mapped_tenant) != tenant_id:
                continue
            session_path = self._session_path(tenant_id, str(session_id))
            session = self._read_json(session_path, default={})
            if not session:
                continue
            if str(session.get("prompt_profile") or "default") != profile_name:
                continue

            total += 1
            version = str(session.get("prompt_version") or DEFAULT_PROMPT_VERSION)
            variant = str(session.get("prompt_variant") or "stable")
            bucket_key = f"{version}:{variant}"
            bucket = buckets.setdefault(
                bucket_key,
                {
                    "prompt_version": version,
                    "prompt_variant": variant,
                    "sessions": 0,
                    "status_counts": {},
                    "avg_iterations": 0.0,
                    "completed_ratio": 0.0,
                },
            )

            bucket["sessions"] += 1
            status = str(session.get("status") or "pending")
            status_counts = bucket["status_counts"]
            status_counts[status] = int(status_counts.get(status) or 0) + 1
            bucket["avg_iterations"] += float(session.get("iteration_count") or 0)

        rows: List[Dict[str, Any]] = []
        for bucket in buckets.values():
            sessions = int(bucket.get("sessions") or 0)
            completed = int((bucket.get("status_counts") or {}).get("completed") or 0)
            if sessions > 0:
                bucket["avg_iterations"] = round(float(bucket["avg_iterations"]) / float(sessions), 3)
                bucket["completed_ratio"] = round(float(completed) / float(sessions), 3)
            rows.append(bucket)

        rows.sort(key=lambda row: (str(row["prompt_version"]), str(row["prompt_variant"])))
        return {
            "tenant_id": tenant_id,
            "prompt_profile": profile_name,
            "total_sessions": total,
            "buckets": rows,
        }

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

    def list_approval_requests(self, tenant_id: str, status: str = "pending") -> List[Dict[str, Any]]:
        normalized = status.strip().lower()
        if normalized not in {"pending", "resolved"}:
            raise ValueError("status must be pending or resolved")

        self.ensure_tenant(tenant_id)
        directory = self.tenant_root(tenant_id) / "approvals" / normalized
        if not directory.exists():
            return []

        approvals: List[Dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            payload = self._read_json(path, default={})
            if not isinstance(payload, dict) or not payload:
                continue
            approvals.append(payload)
        return approvals

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

    def _upsert_prompt_profile_config(self, config: Dict[str, Any], prompt_profile: str) -> tuple[bool, Dict[str, Any]]:
        changed = False
        prompt_profiles = config.get("prompt_profiles")
        if not isinstance(prompt_profiles, dict):
            prompt_profiles = {}
            config["prompt_profiles"] = prompt_profiles
            changed = True

        profile_cfg = prompt_profiles.get(prompt_profile)
        if not isinstance(profile_cfg, dict):
            profile_cfg = {
                "stable_version": DEFAULT_PROMPT_VERSION,
                "versions": {
                    DEFAULT_PROMPT_VERSION: {
                        "path": f"{prompt_profile}.md",
                        "description": "",
                    }
                },
                "canary": {
                    "enabled": False,
                    "version": "",
                    "percent": DEFAULT_CANARY_PERCENT,
                    "start_at": "",
                    "end_at": "",
                },
            }
            prompt_profiles[prompt_profile] = profile_cfg
            changed = True

        versions = profile_cfg.get("versions")
        if not isinstance(versions, dict) or not versions:
            profile_cfg["versions"] = {
                DEFAULT_PROMPT_VERSION: {
                    "path": f"{prompt_profile}.md",
                    "description": "",
                }
            }
            versions = profile_cfg["versions"]
            changed = True

        stable_version = str(profile_cfg.get("stable_version") or "").strip()
        if not stable_version:
            stable_version = DEFAULT_PROMPT_VERSION
            profile_cfg["stable_version"] = stable_version
            changed = True
        if stable_version not in versions:
            versions[stable_version] = {
                "path": f"{prompt_profile}.md",
                "description": "",
            }
            changed = True

        canary = profile_cfg.get("canary")
        if not isinstance(canary, dict):
            canary = {}
            profile_cfg["canary"] = canary
            changed = True
        defaults = {
            "enabled": False,
            "version": "",
            "percent": DEFAULT_CANARY_PERCENT,
            "start_at": "",
            "end_at": "",
        }
        for key, default_value in defaults.items():
            if key not in canary:
                canary[key] = default_value
                changed = True

        return changed, profile_cfg

    def _canary_bucket(self, key: str) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100

    def _canary_active(self, canary_cfg: Dict[str, Any], now_utc: Optional[datetime] = None) -> bool:
        if not bool(canary_cfg.get("enabled", False)):
            return False
        percent = int(canary_cfg.get("percent") or 0)
        if percent <= 0:
            return False
        start = str(canary_cfg.get("start_at") or "").strip()
        end = str(canary_cfg.get("end_at") or "").strip()
        now = now_utc or datetime.now(timezone.utc)
        if start:
            start_dt = self._parse_iso8601(start)
            if now < start_dt:
                return False
        if end:
            end_dt = self._parse_iso8601(end)
            if now > end_dt:
                return False
        return True

    def _safe_prompt_path(self, value: str) -> Path:
        rel = Path(value.strip())
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Prompt path must be relative within tenant prompt directory")
        if not rel.parts:
            raise ValueError("Prompt path is required")
        return rel

    def _parse_iso8601(self, value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid ISO-8601 timestamp: {value}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

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
