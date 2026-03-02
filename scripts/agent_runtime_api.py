#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import unquote

from agent_runtime import AgentRuntime, runtime_descriptor


AGENT_CONSOLE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Agent Console</title>
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap");

    :root {
      --bg: #f2eee6;
      --ink: #111111;
      --card: #fffdf7;
      --line: rgba(17, 17, 17, 0.15);
      --accent: #126a8a;
      --accent-2: #8a4f0f;
      --good: #146b46;
      --warn: #8a4f0f;
      --bad: #9b1c1c;
      --mono: "IBM Plex Mono", monospace;
      --body: "Space Grotesk", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: var(--body);
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 12%, rgba(18, 106, 138, 0.12), transparent 25%),
        radial-gradient(circle at 88% 8%, rgba(138, 79, 15, 0.12), transparent 25%),
        var(--bg);
      padding: 18px;
    }

    .wrap { max-width: 1280px; margin: 0 auto; }

    .hero {
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: #fffaf0;
      margin-bottom: 14px;
    }

    .hero h1 {
      margin: 0;
      font-size: clamp(24px, 4vw, 38px);
      letter-spacing: -0.02em;
    }

    .hero p {
      margin: 8px 0 0;
      color: rgba(17, 17, 17, 0.72);
      max-width: 900px;
    }

    .grid {
      display: grid;
      grid-template-columns: 1.25fr 1fr;
      gap: 12px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--card);
      padding: 12px;
      min-width: 0;
    }

    .panel h2 {
      margin: 0 0 10px;
      font-size: 18px;
      letter-spacing: -0.01em;
    }

    .section {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 10px;
      margin-bottom: 10px;
    }

    .section h3 {
      margin: 0 0 8px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-family: var(--mono);
    }

    .row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 8px;
    }

    .row-3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 8px;
    }

    label {
      display: block;
      font-size: 12px;
      font-family: var(--mono);
      margin-bottom: 4px;
      color: rgba(17, 17, 17, 0.72);
    }

    input, textarea, select, button {
      width: 100%;
      font: inherit;
    }

    input, textarea, select {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px;
      background: #fffefb;
    }

    textarea {
      font-family: var(--mono);
      font-size: 12px;
      min-height: 120px;
      resize: vertical;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 9px 10px;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }

    button.secondary { background: var(--accent-2); }
    button.ghost { background: #ebe4d7; color: #201e1b; }
    button.good { background: var(--good); }
    button.bad { background: var(--bad); }

    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 8px;
    }

    .actions button {
      flex: 1 1 120px;
      min-width: 120px;
    }

    .status {
      margin-top: 8px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 8px;
      font-family: var(--mono);
      font-size: 12px;
      background: #faf7f0;
    }

    .status.ok { color: var(--good); }
    .status.warn { color: var(--warn); }
    .status.error { color: var(--bad); }

    .list {
      border: 1px solid var(--line);
      border-radius: 10px;
      max-height: 220px;
      overflow: auto;
      background: #fff;
    }

    .list-item {
      padding: 8px;
      border-bottom: 1px solid var(--line);
      font-size: 12px;
    }

    .list-item:last-child { border-bottom: 0; }

    .pill {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 7px;
      margin-right: 5px;
      margin-bottom: 5px;
      font-size: 11px;
      font-family: var(--mono);
      background: #f7f2e8;
    }

    pre {
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      background: #121212;
      color: #d6f7ff;
      font-size: 12px;
      overflow: auto;
      max-height: 260px;
      font-family: var(--mono);
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    @media (max-width: 1080px) {
      .grid { grid-template-columns: 1fr; }
      .row, .row-3 { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Agent Console</h1>
      <p>Session launcher, turn controls, artifacts editor, approval inbox, and capability refresh using the same <code>/v1/*</code> runtime APIs.</p>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Control Plane</h2>

        <div class="section">
          <h3>Session Launcher</h3>
          <div class="row">
            <div><label for="tenantId">Tenant ID</label><input id="tenantId" value="tenant-default" /></div>
            <div><label for="sessionId">Session ID</label><input id="sessionId" placeholder="created session id" /></div>
          </div>
          <div class="row">
            <div><label for="promptProfile">Prompt Profile</label><input id="promptProfile" value="default" /></div>
            <div><label for="mode">Mode</label><select id="mode"><option value="hybrid">hybrid</option><option value="manual">manual</option></select></div>
          </div>
          <label for="objective">Objective</label>
          <textarea id="objective">Produce a weekly digest and stop with complete_task.</textarea>
          <div class="actions">
            <button id="createSessionBtn">Create Session</button>
            <button id="loadSessionBtn" class="ghost">Load Session</button>
            <button id="deleteSessionBtn" class="bad">Delete Session</button>
          </div>
        </div>

        <div class="section">
          <h3>Turn Execution</h3>
          <label for="toolCalls">Tool Calls (JSON array)</label>
          <textarea id="toolCalls">[
  {"tool": "create_task", "args": {"session_id": "", "title": "Collect evidence", "metadata": {"stage": "collect"}}},
  {"tool": "complete_task", "args": {"session_id": "", "status": "completed"}}
]</textarea>
          <div class="actions">
            <button id="runTurnBtn">Run Turn</button>
            <button id="resumeBtn" class="secondary">Resume Session</button>
            <button id="refreshTasksBtn" class="ghost">Refresh Tasks</button>
            <button id="refreshArtifactsBtn" class="ghost">Refresh Artifacts</button>
          </div>
        </div>

        <div class="section">
          <h3>Session Snapshot</h3>
          <div id="sessionPills"></div>
          <pre id="sessionJson">{}</pre>
        </div>

        <div class="section">
          <h3>Tasks</h3>
          <div id="taskList" class="list"></div>
        </div>

        <div class="section">
          <h3>Artifacts</h3>
          <div id="artifactList" class="list"></div>
          <div class="row" style="margin-top:8px;">
            <div><label for="artifactPath">Artifact Path</label><input id="artifactPath" placeholder="tenants/.../outputs/file.json" /></div>
            <div><label for="artifactHint">Path Hint</label><input id="artifactHint" value="Use list above to autofill" readonly /></div>
          </div>
          <label for="artifactContent">Artifact Content (JSON or text)</label>
          <textarea id="artifactContent">{}</textarea>
          <div class="actions">
            <button id="loadArtifactBtn" class="ghost">Load Artifact</button>
            <button id="saveArtifactBtn" class="secondary">Save Artifact</button>
          </div>
        </div>
      </div>

      <div class="panel">
        <h2>Ops Panels</h2>

        <div class="section">
          <h3>Capabilities</h3>
          <div class="actions">
            <button id="loadCapsBtn" class="ghost">Load Capabilities</button>
            <button id="refreshCapsBtn" class="secondary">Refresh Capabilities</button>
          </div>
          <pre id="capsJson">{}</pre>
        </div>

        <div class="section">
          <h3>Approval Inbox</h3>
          <div class="row">
            <div><label for="approvalNote">Reviewer Note</label><input id="approvalNote" value="Reviewed in Agent Console" /></div>
            <div><label for="resolver">Resolver</label><input id="resolver" value="human" /></div>
          </div>
          <div class="actions">
            <button id="loadApprovalsBtn" class="ghost">Load Pending</button>
            <button id="loadResolvedBtn" class="ghost">Load Resolved</button>
          </div>
          <div id="approvalList" class="list"></div>
        </div>

        <div class="section">
          <h3>API Inspector</h3>
          <pre id="apiInspector">No API call yet.</pre>
        </div>
      </div>
    </section>
    <div id="status" class="status">Ready.</div>
  </div>

  <script>
    (() => {
      const el = (id) => document.getElementById(id);
      const state = {
        session: null,
        lastCall: null,
      };

      function setStatus(message, tone = "") {
        const status = el("status");
        status.className = "status " + (tone || "");
        status.textContent = message;
      }

      function renderInspector(method, path, body) {
        let curl = `curl -sS -X ${method} http://127.0.0.1:8788${path}`;
        if (body !== undefined) {
          curl += " -H \\"Content-Type: application/json\\"";
          curl += " -d '" + JSON.stringify(body) + "'";
        }
        el("apiInspector").textContent = curl;
      }

      async function api(method, path, body) {
        renderInspector(method, path, body);
        const options = { method, headers: { "Content-Type": "application/json" } };
        if (body !== undefined) options.body = JSON.stringify(body);
        const resp = await fetch(path, options);
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(data.error || `${resp.status} ${resp.statusText}`);
        }
        return data;
      }

      function sessionId() {
        return String(el("sessionId").value || "").trim();
      }

      function tenantId() {
        return String(el("tenantId").value || "").trim();
      }

      function syncToolCallSessionId() {
        const sid = sessionId();
        if (!sid) return;
        try {
          const parsed = JSON.parse(el("toolCalls").value);
          if (!Array.isArray(parsed)) return;
          parsed.forEach((item) => {
            if (!item || typeof item !== "object") return;
            if (!item.args || typeof item.args !== "object") item.args = {};
            if ("session_id" in item.args || item.tool === "create_task" || item.tool === "complete_task") {
              item.args.session_id = sid;
            }
          });
          el("toolCalls").value = JSON.stringify(parsed, null, 2);
        } catch (_err) {
          // keep raw textarea unchanged when not parseable
        }
      }

      function renderSession(session) {
        state.session = session;
        el("sessionJson").textContent = JSON.stringify(session || {}, null, 2);
        const pills = [];
        if (session && typeof session === "object") {
          for (const key of ["id", "status", "prompt_profile", "prompt_version", "prompt_variant", "iteration_count"]) {
            if (session[key] === undefined) continue;
            pills.push(`<span class="pill">${key}: ${String(session[key])}</span>`);
          }
        }
        el("sessionPills").innerHTML = pills.join("");
      }

      function renderList(containerId, rows, emptyMessage, htmlBuilder) {
        const host = el(containerId);
        if (!Array.isArray(rows) || rows.length === 0) {
          host.innerHTML = `<div class="list-item">${emptyMessage}</div>`;
          return;
        }
        host.innerHTML = rows.map((row) => `<div class="list-item">${htmlBuilder(row)}</div>`).join("");
      }

      async function loadSession() {
        const sid = sessionId();
        if (!sid) throw new Error("session_id is required");
        const session = await api("GET", `/v1/sessions/${encodeURIComponent(sid)}`);
        renderSession(session);
        syncToolCallSessionId();
        return session;
      }

      async function loadTasks() {
        const sid = sessionId();
        if (!sid) throw new Error("session_id is required");
        const payload = await api("GET", `/v1/sessions/${encodeURIComponent(sid)}/tasks`);
        renderList(
          "taskList",
          payload.tasks || [],
          "No tasks.",
          (task) => [
            `<span class="pill">${task.id || "-"}</span>`,
            `<span class="pill">${task.status || "-"}</span>`,
            `<div><strong>${task.title || "-"}</strong></div>`,
            task.notes ? `<div>${task.notes}</div>` : "",
          ].join(""),
        );
        return payload;
      }

      async function loadArtifacts() {
        const sid = sessionId();
        if (!sid) throw new Error("session_id is required");
        const payload = await api("GET", `/v1/sessions/${encodeURIComponent(sid)}/artifacts`);
        renderList(
          "artifactList",
          payload.artifacts || [],
          "No artifacts.",
          (artifact) => {
            const path = String(artifact.path || "");
            const safePath = path.replace(/"/g, "&quot;");
            return [
              `<span class="pill">${artifact.size || 0} bytes</span>`,
              `<div style="margin:6px 0;"><code>${path}</code></div>`,
              `<button class="ghost" onclick="window.__loadArtifact('${safePath}')">Load</button>`,
            ].join("");
          },
        );
        return payload;
      }

      async function loadArtifact(pathOverride) {
        const path = String(pathOverride || el("artifactPath").value || "").trim();
        if (!path) throw new Error("artifact path is required");
        el("artifactPath").value = path;
        const payload = await api("GET", `/v1/artifacts/${encodeURIComponent(path)}`);
        const content = payload.content;
        if (typeof content === "string") {
          el("artifactContent").value = content;
        } else {
          el("artifactContent").value = JSON.stringify(content, null, 2);
        }
        return payload;
      }

      async function saveArtifact() {
        const path = String(el("artifactPath").value || "").trim();
        if (!path) throw new Error("artifact path is required");
        const raw = String(el("artifactContent").value || "");
        let content = raw;
        try {
          content = JSON.parse(raw);
        } catch (_err) {
          // treat as plain text when not valid JSON
        }
        return api("PUT", `/v1/artifacts/${encodeURIComponent(path)}`, { content });
      }

      async function loadCapabilities(refresh) {
        const tenant = tenantId();
        if (!tenant) throw new Error("tenant_id is required");
        const endpoint = refresh
          ? `/v1/tenants/${encodeURIComponent(tenant)}/capabilities/refresh`
          : `/v1/tenants/${encodeURIComponent(tenant)}/capabilities`;
        const payload = refresh ? await api("POST", endpoint, {}) : await api("GET", endpoint);
        el("capsJson").textContent = JSON.stringify(payload, null, 2);
        return payload;
      }

      async function loadApprovals(status) {
        const tenant = tenantId();
        if (!tenant) throw new Error("tenant_id is required");
        const payload = await api("GET", `/v1/tenants/${encodeURIComponent(tenant)}/approvals/${status}`);
        const approvals = payload.approvals || [];
        renderList(
          "approvalList",
          approvals,
          `No ${status} approvals.`,
          (approval) => {
            const id = String(approval.id || "");
            const safeId = id.replace(/"/g, "&quot;");
            const action = String(approval.action_type || "-");
            const summary = String(approval.summary || "");
            const statusLabel = String(approval.status || "-");
            const controls = status === "pending"
              ? `
                <div class="actions">
                  <button class="good" onclick="window.__resolveApproval('${safeId}','approved')">Approve</button>
                  <button class="bad" onclick="window.__resolveApproval('${safeId}','rejected')">Reject</button>
                </div>
              `
              : "";
            return `
              <span class="pill">${statusLabel}</span>
              <span class="pill">${action}</span>
              <div><code>${id}</code></div>
              <div>${summary}</div>
              ${controls}
            `;
          },
        );
        return payload;
      }

      async function resolveApproval(approvalId, decision) {
        const note = String(el("approvalNote").value || "").trim();
        const resolver = String(el("resolver").value || "").trim() || "human";
        await api("POST", `/v1/approvals/${encodeURIComponent(approvalId)}/resolve`, {
          decision,
          reviewer_note: note,
          resolver,
        });
        return loadApprovals("pending");
      }

      async function runTurn() {
        const sid = sessionId();
        if (!sid) throw new Error("session_id is required");
        const toolCalls = JSON.parse(el("toolCalls").value || "[]");
        const payload = await api("POST", `/v1/sessions/${encodeURIComponent(sid)}/turn`, { tool_calls: toolCalls });
        if (payload.session) renderSession(payload.session);
        await loadTasks();
        await loadArtifacts();
        return payload;
      }

      async function resumeSession() {
        const sid = sessionId();
        if (!sid) throw new Error("session_id is required");
        const payload = await api("POST", `/v1/sessions/${encodeURIComponent(sid)}/resume`, {});
        if (payload.session) renderSession(payload.session);
        await loadTasks();
        await loadArtifacts();
        return payload;
      }

      async function createSession() {
        const body = {
          tenant_id: tenantId(),
          objective: String(el("objective").value || "").trim(),
          prompt_profile: String(el("promptProfile").value || "default").trim() || "default",
          mode: String(el("mode").value || "hybrid"),
        };
        const session = await api("POST", "/v1/sessions", body);
        el("sessionId").value = session.id || "";
        renderSession(session);
        syncToolCallSessionId();
        await loadTasks();
        await loadArtifacts();
        return session;
      }

      async function deleteSession() {
        const sid = sessionId();
        if (!sid) throw new Error("session_id is required");
        const payload = await api("DELETE", `/v1/sessions/${encodeURIComponent(sid)}`);
        renderSession({});
        el("taskList").innerHTML = "";
        el("artifactList").innerHTML = "";
        return payload;
      }

      async function loadRuntimeDescriptor() {
        const payload = await api("GET", "/v1/runtime");
        setStatus(`Runtime: ${payload.runtime} (available=${payload.available})`, payload.available ? "ok" : "warn");
      }

      async function perform(action) {
        try {
          await action();
          setStatus("OK", "ok");
        } catch (err) {
          setStatus(err.message || String(err), "error");
        }
      }

      el("createSessionBtn").addEventListener("click", () => perform(createSession));
      el("loadSessionBtn").addEventListener("click", () => perform(loadSession));
      el("deleteSessionBtn").addEventListener("click", () => perform(deleteSession));
      el("runTurnBtn").addEventListener("click", () => perform(runTurn));
      el("resumeBtn").addEventListener("click", () => perform(resumeSession));
      el("refreshTasksBtn").addEventListener("click", () => perform(loadTasks));
      el("refreshArtifactsBtn").addEventListener("click", () => perform(loadArtifacts));
      el("loadArtifactBtn").addEventListener("click", () => perform(() => loadArtifact("")));
      el("saveArtifactBtn").addEventListener("click", () => perform(saveArtifact));
      el("loadCapsBtn").addEventListener("click", () => perform(() => loadCapabilities(false)));
      el("refreshCapsBtn").addEventListener("click", () => perform(() => loadCapabilities(true)));
      el("loadApprovalsBtn").addEventListener("click", () => perform(() => loadApprovals("pending")));
      el("loadResolvedBtn").addEventListener("click", () => perform(() => loadApprovals("resolved")));

      el("sessionId").addEventListener("input", syncToolCallSessionId);
      window.__loadArtifact = (path) => perform(() => loadArtifact(path));
      window.__resolveApproval = (approvalId, decision) => perform(() => resolveApproval(approvalId, decision));

      loadRuntimeDescriptor().catch(() => setStatus("Runtime descriptor unavailable.", "warn"));
    })();
  </script>
</body>
</html>
"""


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
                self._send(200, runtime_descriptor())
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
