from __future__ import annotations

from typing import Any, Dict


try:
    from google import adk as _google_adk  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    _google_adk = None


def adk_available() -> bool:
    return _google_adk is not None


def runtime_descriptor() -> Dict[str, Any]:
    if adk_available():
        return {
            "runtime": "google_adk",
            "available": True,
            "provider": "google",
        }
    return {
        "runtime": "local_loop_fallback",
        "available": False,
        "provider": "google",
        "note": "Install Google ADK package to enable native ADK runner wiring.",
    }
