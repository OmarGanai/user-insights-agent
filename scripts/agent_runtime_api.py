#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import unquote

from agent_runtime import AgentRuntime


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
        raise ValueError(f"Invalid JSON body: {exc}")
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

    def _handle_error(self, exc: Exception, status: int = 400) -> None:
        self._send(status, {"error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
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

            if path == "/v1/sessions":
                payload = self.runtime.create_session(
                    tenant_id=str(body.get("tenant_id") or "").strip(),
                    objective=str(body.get("objective") or "").strip(),
                    prompt_profile=str(body.get("prompt_profile") or "default"),
                    mode=str(body.get("mode") or "hybrid"),
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
