from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

from config import get_chart_reference_catalog

from .models import utc_now_iso
from .store import FileWorkspaceStore


def _future_iso(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


class DiscoveryService:
    def __init__(self, store: FileWorkspaceStore) -> None:
        self.store = store

    def discover_amplitude_capabilities(self, tenant_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        tenant_root = self.store.ensure_tenant(tenant_id)
        cache_path = tenant_root / "capabilities" / "amplitude.json"
        cached = self._load_cache(cache_path)
        if cached and not force_refresh and not self._is_expired(cached.get("ttl_expires_at", "")):
            cached["cache_hit"] = True
            return cached

        catalog = get_chart_reference_catalog()
        charts = []
        for chart_id, ref in list(catalog.items())[:200]:
            charts.append(
                {
                    "chart_id": chart_id,
                    "chart_title": ref.get("chart_title", ""),
                    "chart_types": ref.get("chart_types", []),
                    "queryable": bool(chart_id),
                }
            )

        payload = {
            "tenant_id": tenant_id,
            "source": "local_metric_dictionary",
            "fetched_at": utc_now_iso(),
            "ttl_expires_at": _future_iso(10),
            "constraints": {
                "read_only": True,
                "max_upstream_requests": 5,
                "timeout_seconds": 10,
                "retries": 2,
                "max_entities": 200,
                "host_allowlist": ["amplitude.com"],
                "redaction": "auth headers and tokens are never logged",
            },
            "apps": [
                {
                    "name": "tenant-amplitude",
                    "chart_count": len(charts),
                }
            ],
            "charts": charts,
            "cache_hit": False,
        }
        self._save_cache(cache_path, payload)
        return payload

    def discover_typeform_capabilities(self, tenant_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        tenant_root = self.store.ensure_tenant(tenant_id)
        cache_path = tenant_root / "capabilities" / "typeform.json"
        cached = self._load_cache(cache_path)
        if cached and not force_refresh and not self._is_expired(cached.get("ttl_expires_at", "")):
            cached["cache_hit"] = True
            return cached

        config = self.store.read_tenant_config(tenant_id)
        form_id = str(((config.get("typeform") or {}).get("form_id") or "")).strip()
        forms = []
        if form_id:
            forms.append(
                {
                    "form_id": form_id,
                    "fields": [],
                    "pagination_supported": True,
                }
            )

        payload = {
            "tenant_id": tenant_id,
            "source": "tenant_config",
            "fetched_at": utc_now_iso(),
            "ttl_expires_at": _future_iso(10),
            "constraints": {
                "read_only": True,
                "max_upstream_requests": 5,
                "timeout_seconds": 10,
                "retries": 2,
                "max_forms": 100,
                "max_fields": 200,
                "host_allowlist": ["api.typeform.com"],
                "redaction": "respondent-level pii removed",
            },
            "forms": forms[:100],
            "cache_hit": False,
        }
        self._save_cache(cache_path, payload)
        return payload

    def discover_slack_capabilities(self, tenant_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        tenant_root = self.store.ensure_tenant(tenant_id)
        cache_path = tenant_root / "capabilities" / "slack.json"
        cached = self._load_cache(cache_path)
        if cached and not force_refresh and not self._is_expired(cached.get("ttl_expires_at", "")):
            cached["cache_hit"] = True
            return cached

        config = self.store.read_tenant_config(tenant_id)
        webhook_env = str(((config.get("slack") or {}).get("webhook_env") or "SLACK_WEBHOOK_URL")).strip()
        webhook_url = ""
        if webhook_env:
            webhook_url = str(__import__("os").environ.get(webhook_env, "")).strip()

        parsed = urlparse(webhook_url) if webhook_url else urlparse("")
        host = parsed.hostname or ""
        redacted_webhook = self._redact_webhook(webhook_url)

        payload = {
            "tenant_id": tenant_id,
            "source": "tenant_config",
            "fetched_at": utc_now_iso(),
            "ttl_expires_at": _future_iso(5),
            "constraints": {
                "read_only": True,
                "max_upstream_checks": 3,
                "timeout_seconds": 8,
                "retries": 1,
                "host_allowlist": ["slack.com", host] if host else ["slack.com"],
                "redaction": "webhook URL redacted to host + hash suffix",
            },
            "webhook": {
                "configured": bool(webhook_url),
                "host": host,
                "redacted": redacted_webhook,
                "channel_override_supported": True,
                "payload_limits": {"max_blocks": 50, "text_limit": 40000},
                "dry_validation_supported": True,
            },
            "cache_hit": False,
        }
        self._save_cache(cache_path, payload)
        return payload

    def full_manifest(self, tenant_id: str) -> Dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "fetched_at": utc_now_iso(),
            "ttl_expires_at": _future_iso(5),
            "amplitude": self.discover_amplitude_capabilities(tenant_id),
            "typeform": self.discover_typeform_capabilities(tenant_id),
            "slack": self.discover_slack_capabilities(tenant_id),
        }

    def _load_cache(self, cache_path):
        if not cache_path.exists():
            return None
        try:
            import json

            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_cache(self, cache_path, payload: Dict[str, Any]) -> None:
        import json

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    def _is_expired(self, value: str) -> bool:
        if not value:
            return True
        try:
            ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return True
        return ts <= datetime.now(timezone.utc)

    def _redact_webhook(self, webhook_url: str) -> str:
        if not webhook_url:
            return ""
        parsed = urlparse(webhook_url)
        host = parsed.hostname or ""
        suffix = hashlib.sha256(webhook_url.encode("utf-8")).hexdigest()[:8]
        return f"{host}#{suffix}" if host else f"redacted#{suffix}"
