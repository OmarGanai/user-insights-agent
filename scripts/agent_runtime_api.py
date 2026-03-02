#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import unquote

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")

from agent_runtime import AgentRuntime


def _load_console_html() -> str:
    html_path = Path(__file__).resolve().with_name("agent_console.html")
    try:
        return html_path.read_text(encoding="utf-8")
    except OSError:
        return "<!doctype html><html><body><h1>Agent Console</h1><p>Missing scripts/agent_console.html</p></body></html>"


AGENT_CONSOLE_HTML = _load_console_html()


def _json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return payload


class _Handler(BaseHTTPRequestHandler):
    runtime = AgentRuntime()

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: int, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_html(self, status: int, html: str) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _handle_error(self, exc: Exception, status: int = 400) -> None:
        self._send(status, {"error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path == "/":
                self._send_html(200, AGENT_CONSOLE_HTML)
                return

            if path == "/v1/runtime":
                self._send(200, self.runtime.runtime_descriptor())
                return

            if path.startswith("/v1/tenants/") and "/prompt-profiles/" in path:
                tenant_part = path[len("/v1/tenants/") :]
                tenant_id, _, profile_part = tenant_part.partition("/prompt-profiles/")
                tenant_id = tenant_id.strip("/")
                if profile_part.endswith("/rollout"):
                    prompt_profile = unquote(profile_part[: -len("/rollout")].strip("/") or "default")
                    payload = self.runtime.tools.get_prompt_profile_rollout(
                        tenant_id=tenant_id,
                        prompt_profile=prompt_profile,
                    )
                    self._send(200, payload)
                    return
                if profile_part.endswith("/evaluation"):
                    prompt_profile = unquote(profile_part[: -len("/evaluation")].strip("/") or "default")
                    payload = self.runtime.tools.evaluate_prompt_profile(
                        tenant_id=tenant_id,
                        prompt_profile=prompt_profile,
                    )
                    self._send(200, payload)
                    return

            if path.startswith("/v1/tenants/") and path.endswith("/approvals/pending"):
                tenant_id = path[len("/v1/tenants/") : -len("/approvals/pending")].strip("/")
                payload = self.runtime.tools.list_approval_requests(tenant_id=tenant_id, status="pending")
                self._send(200, payload)
                return

            if path.startswith("/v1/tenants/") and path.endswith("/approvals/resolved"):
                tenant_id = path[len("/v1/tenants/") : -len("/approvals/resolved")].strip("/")
                payload = self.runtime.tools.list_approval_requests(tenant_id=tenant_id, status="resolved")
                self._send(200, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/tasks"):
                session_id = path[len("/v1/sessions/") : -len("/tasks")].strip("/")
                payload = self.runtime.tools.list_tasks(session_id=session_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/messages"):
                session_id = path[len("/v1/sessions/") : -len("/messages")].strip("/")
                payload = self.runtime.list_messages(session_id=session_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/context"):
                session_id = path[len("/v1/sessions/") : -len("/context")].strip("/")
                payload = self.runtime.build_context_snapshot(session_id=session_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/artifacts"):
                session_id = path[len("/v1/sessions/") : -len("/artifacts")].strip("/")
                payload = self.runtime.list_artifacts(session_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/sessions/"):
                session_id = path[len("/v1/sessions/") :].strip("/")
                payload = self.runtime.get_session(session_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/approvals/"):
                approval_id = path[len("/v1/approvals/") :].strip("/")
                payload = self.runtime.tools.get_approval_request(approval_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/tenants/") and path.endswith("/capabilities"):
                tenant_id = path[len("/v1/tenants/") : -len("/capabilities")].strip("/")
                payload = self.runtime.tools.discovery.full_manifest(tenant_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/artifacts/"):
                artifact_path = unquote(path[len("/v1/artifacts/") :].lstrip("/"))
                payload = self.runtime.tools.read_artifact(path=artifact_path)
                self._send(200, payload)
                return

            self._send(404, {"error": "Not found"})
        except KeyError as exc:
            self._handle_error(exc, status=404)
        except FileNotFoundError as exc:
            self._handle_error(exc, status=404)
        except Exception as exc:
            self._handle_error(exc, status=400)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            body = _json_body(self)

            if path.startswith("/v1/tenants/") and "/prompt-profiles/" in path and path.endswith("/rollout"):
                tenant_part = path[len("/v1/tenants/") :]
                tenant_id, _, profile_part = tenant_part.partition("/prompt-profiles/")
                tenant_id = tenant_id.strip("/")
                prompt_profile = unquote(profile_part[: -len("/rollout")].strip("/") or "default")
                payload = self.runtime.tools.update_prompt_profile_rollout(
                    tenant_id=tenant_id,
                    prompt_profile=prompt_profile,
                    rollout=body,
                )
                self._send(200, payload)
                return

            if path == "/v1/sessions":
                payload = self.runtime.create_session(
                    tenant_id=str(body.get("tenant_id") or "").strip(),
                    objective=str(body.get("objective") or "").strip(),
                    prompt_profile=str(body.get("prompt_profile") or "default"),
                    mode=str(body.get("mode") or "hybrid"),
                )
                self._send(201, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/tasks"):
                session_id = path[len("/v1/sessions/") : -len("/tasks")].strip("/")
                payload = self.runtime.tools.create_task(
                    session_id=session_id,
                    title=str(body.get("title") or "").strip(),
                    metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
                )
                self._send(201, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/turn"):
                session_id = path[len("/v1/sessions/") : -len("/turn")].strip("/")
                tool_calls = body.get("tool_calls")
                if tool_calls is not None and not isinstance(tool_calls, list):
                    raise ValueError("tool_calls must be a list when provided")
                payload = self.runtime.run_turn(session_id=session_id, tool_calls=tool_calls)
                self._send(200, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/resume"):
                session_id = path[len("/v1/sessions/") : -len("/resume")].strip("/")
                payload = self.runtime.resume_session(session_id=session_id)
                self._send(200, payload)
                return

            if path.startswith("/v1/sessions/") and path.endswith("/chat"):
                session_id = path[len("/v1/sessions/") : -len("/chat")].strip("/")
                message = body.get("message")
                if not isinstance(message, str) or not message.strip():
                    raise ValueError("message is required and must be a non-empty string")
                options = body.get("options")
                if options is not None and not isinstance(options, dict):
                    raise ValueError("options must be an object when provided")
                payload = self.runtime.chat_turn(
                    session_id=session_id,
                    message=message.strip(),
                    options=options if isinstance(options, dict) else {},
                )
                self._send(200, payload)
                return

            if path.startswith("/v1/approvals/") and path.endswith("/resolve"):
                approval_id = path[len("/v1/approvals/") : -len("/resolve")].strip("/")
                payload = self.runtime.tools.resolve_approval_request(
                    approval_id=approval_id,
                    decision=str(body.get("decision") or ""),
                    reviewer_note=str(body.get("reviewer_note") or ""),
                    resolver=str(body.get("resolver") or "human"),
                )
                self._send(200, payload)
                return

            if path.startswith("/v1/tenants/") and path.endswith("/capabilities/refresh"):
                tenant_id = path[len("/v1/tenants/") : -len("/capabilities/refresh")].strip("/")
                payload = {
                    "tenant_id": tenant_id,
                    "amplitude": self.runtime.tools.discover_amplitude_capabilities(tenant_id, force_refresh=True),
                    "typeform": self.runtime.tools.discover_typeform_capabilities(tenant_id, force_refresh=True),
                    "slack": self.runtime.tools.discover_slack_capabilities(tenant_id, force_refresh=True),
                }
                self._send(200, payload)
                return

            self._send(404, {"error": "Not found"})
        except KeyError as exc:
            self._handle_error(exc, status=404)
        except Exception as exc:
            self._handle_error(exc, status=400)

    def do_PUT(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            body = _json_body(self)
            if path.startswith("/v1/artifacts/"):
                artifact_path = unquote(path[len("/v1/artifacts/") :].lstrip("/"))
                payload = self.runtime.tools.update_artifact(
                    path=artifact_path,
                    content=body.get("content"),
                )
                self._send(200, payload)
                return
            self._send(404, {"error": "Not found"})
        except FileNotFoundError as exc:
            self._handle_error(exc, status=404)
        except Exception as exc:
            self._handle_error(exc, status=400)

    def do_DELETE(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path.startswith("/v1/sessions/"):
                session_id = path[len("/v1/sessions/") :].strip("/")
                payload = self.runtime.tools.delete_session(session_id=session_id)
                self._send(200, payload)
                return
            self._send(404, {"error": "Not found"})
        except KeyError as exc:
            self._handle_error(exc, status=404)
        except Exception as exc:
            self._handle_error(exc, status=400)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run agent runtime API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"Agent runtime API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down", file=sys.stderr)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
