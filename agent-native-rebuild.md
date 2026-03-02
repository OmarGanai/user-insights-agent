# Agent-Native Rebuild Implementation Plan (Public-Safe, Tenant-Configurable)

## Execution Tracking (Codex Run 2026-03-01)
- [x] Read plan and map current repository baseline.
- [x] Define first shippable scope: deliver Phase 0 public-safe controls + Phase 1 runtime skeleton + Phase 2 tool contracts (partial) without breaking compatibility adapter.
- [x] Implement tenant-scoped session/task/artifact/approval runtime with checkpoint/resume.
- [x] Implement primitive CRUD tool contracts and discovery tool constraints.
- [x] Add approval-gated side-effect path for Slack posting.
- [x] Add public-safety scans and defaults (tenant identifier + runtime artifact checks).
- [x] Sanitize tenant-specific literals in code/docs/tests for public-safe defaults.
- [x] Add tests for lifecycle, checkpoint/resume, approval gates, discovery safety, and scanner checks.
- [x] Validate with available test/lint commands in this environment and document any missing dependencies.
- [x] Update this plan with completed checkboxes and residual follow-up scope.

### Residual Follow-up Scope (Next Iteration)
- [x] Finalize repo-boundary cutover (retain root as sole active repo and retire or archive legacy nested `amplitude-insights-bot/` assets).
- [ ] Wire native Google ADK runtime objects (current implementation includes an ADK adapter and local loop fallback).
- [x] Build Agent Console UI parity against new `/v1/*` runtime APIs.
- [x] Add capability refresh UX and approval inbox UX in the console.
- [x] Add CI workflow wiring for `scripts/public_safety_scan.py` and deterministic test gate.
- [x] Complete prompt-profile canary rollout plumbing and evaluation harness.

## Summary
Rebuild the current pipeline into a true agent system, implemented on Google ADK (Python), that is public-safe by default (no tenant data in code/history/docs), while supporting private tenant overlays (including tenant) through runtime config and secrets.

## Repository Baseline and Cutover Constraints (Local Snapshot: 2026-03-01)
1. Active implementation files are in repository root (`clients/`, `services/`, `scripts/`, `tests/`, `docs/`) and root is the active git worktree.
2. Legacy nested folder `amplitude-insights-bot/` is retired from tracked scope and treated as local-only/non-canonical.
3. Historical sensitive-identifier baseline was high before sanitization; ongoing public-safety scans should remain mandatory.
4. Secret-bearing local env file may still exist at `amplitude-insights-bot/.env`; subtree remains git-ignored and untracked.
5. Live Amplitude contract test requires credentials and should remain opt-in, while deterministic tests stay default.

## Public-Safe Cutover Checklist (Specific to This Copy)
1. Keep one active repo boundary at current root and retire or archive legacy nested `amplitude-insights-bot/` assets from day-to-day workflow.
2. Quarantine or rewrite high-risk content before public release:
   `docs/history/*`, `docs/legacy-product-analytics.md`, `docs/context/*`, `docs/ios-release-notes.yaml`, sensitive fixtures under `tests/fixtures/*`.
3. Replace tenant-specific literals in code/tests/docs (`tenant*`, Amplitude app links/IDs, tenant channel names) with tenant-agnostic placeholders.
4. Keep runtime/generated artifacts out of git (`tmp/**`, tenant workspace runtime files, debug outputs).

## Objectives
1. Replace workflow-coded orchestration with an event-driven agent loop.
2. Preserve proven domain logic by exposing it as primitive tools.
3. Enforce tenant isolation and approval gates for irreversible actions.
4. Provide first-class human interaction via Agent Console UI and API.
5. Make the public repo reusable by any organization without private leakage.
6. Standardize agent runtime on Google ADK (Python) with Gemini model access per tenant.

## Success Criteria
1. Public repo contains zero tenant identifiers or tenant-specific data.
2. Agent can complete weekly-digest objectives via tools + prompt loop.
3. Slack posting is blocked until explicit approval.
4. Session checkpoint/resume works after interruption.
5. Capability map parity tests pass for all console actions.
6. Discovery tools are read-only, scoped, rate-limited, and redacted.
7. Private tenant overlay can be applied without code changes.

## In Scope
1. Agent runtime, tools, prompt profiles, workspace schema, API, console UI.
2. Discovery contracts for Amplitude/Typeform/Slack.
3. Approval workflow and policy enforcement.
4. Public-safe repo restructuring and docs.
5. Test harness for parity, loop behavior, and security constraints.

## Out of Scope (V1)
1. Self-modifying code behavior.
2. Mobile-specific runtime patterns.
3. Multi-agent swarm orchestration.

## System Architecture
1. Google ADK (Python) provides the event-driven session runtime and turn execution loop.
2. Tools are primitive and composable; no workflow tools.
3. ADK sessions/state are persisted with tenant-scoped workspace artifacts and checkpoint index files.
4. Prompt profiles define behavior and can be versioned independently from code.
5. Approval service gates side-effectful actions.
6. Console UI and API are parity-equivalent interfaces.

## Capability Map (Parity)
| User Action | Agent Capability | Tool(s) |
|---|---|---|
| Start analysis run | Create objective session | `create_session` |
| Run agent | Execute turn loop | `run_turn` |
| Pause/resume run | Continue from checkpoint | `resume_session` |
| Inspect status | Read tasks/events/artifacts | `get_session`, `list_tasks`, `list_artifacts` |
| Edit payload | Update output artifact | `update_artifact` |
| Validate payload | Schema and policy checks | `validate_slack_payload` |
| Post to Slack | Side-effectful publish | `request_approval`, `post_slack_payload` |
| Change metric mapping | Update tenant contract | `request_approval`, `update_metric_contract` |
| Explore integrations | Discover available resources | `discover_*_capabilities` |

## Tool Contracts (Primitive + CRUD Complete)
All tool contracts are implemented as ADK tools (plus MCP-compatible integrations where useful), while retaining the same CRUD semantics below.

### Session tools
1. `create_session(tenant_id, objective, prompt_profile, mode)`
2. `get_session(session_id)`
3. `update_session(session_id, fields)`
4. `delete_session(session_id)`

### Task tools
1. `create_task(session_id, title, metadata)`
2. `list_tasks(session_id)`
3. `update_task(task_id, status, notes)`
4. `delete_task(task_id)`

### Artifact tools
1. `create_artifact(run_id, kind, path, content)`
2. `read_artifact(path)`
3. `update_artifact(path, content)`
4. `delete_artifact(path)`

### Approval tools
1. `create_approval_request(session_id, action_type, payload_path, summary)`
2. `get_approval_request(approval_id)`
3. `resolve_approval_request(approval_id, decision, reviewer_note)`
4. `delete_approval_request(approval_id)`

### Metric contract tools
1. `create_metric_contract(tenant_id, payload)`
2. `read_metric_contract(tenant_id)`
3. `update_metric_contract(tenant_id, patch)`
4. `delete_metric_contract(tenant_id)`

### Discovery tools
1. `discover_amplitude_capabilities(tenant_id, force_refresh=false)`
2. `discover_typeform_capabilities(tenant_id, force_refresh=false)`
3. `discover_slack_capabilities(tenant_id, force_refresh=false)`

## Discovery Tool Details and Constraints

### `discover_amplitude_capabilities`
1. Returns: accessible app/projects, chart metadata, chart types, queryability flags.
2. Constraints: read-only metadata endpoints only.
3. Constraints: max 5 upstream requests per invocation.
4. Constraints: per-request timeout 10s; retries 2 with exponential backoff.
5. Constraints: max 200 discovered entities per invocation.
6. Constraints: host allowlist `amplitude.com` only.
7. Constraints: cache TTL 10 minutes per tenant.
8. Constraints: redact tokens and auth headers from logs/artifacts.

### `discover_typeform_capabilities`
1. Returns: accessible forms, form IDs, field metadata, pagination support.
2. Constraints: read-only endpoints only.
3. Constraints: max 5 upstream requests; timeout 10s; retries 2.
4. Constraints: max 100 forms and max 200 fields summarized.
5. Constraints: host allowlist `api.typeform.com` only.
6. Constraints: cache TTL 10 minutes per tenant.
7. Constraints: redact respondent-level PII in discovery artifacts.

### `discover_slack_capabilities`
1. Returns: webhook reachability, payload limits, channel override behavior.
2. Constraints: discovery never sends message payloads to channels.
3. Constraints: optional dry validation against Block Kit schema only.
4. Constraints: max 3 upstream checks; timeout 8s; retries 1.
5. Constraints: host allowlist `slack.com` and webhook host only.
6. Constraints: cache TTL 5 minutes.
7. Constraints: redact webhook URL except host and terminal hash suffix.

### Shared discovery policy
1. Discovery is always read-only and non-mutating.
2. Discovery must be tenant-scoped and cannot cross-tenant resources.
3. Discovery failures degrade gracefully to tenant-configured defaults.
4. All discovery outputs must be tagged with `source`, `fetched_at`, `ttl_expires_at`.

## Agent Loop Protocol (Explicit Completion)
1. States: `pending`, `running`, `waiting_approval`, `completed`, `blocked`, `failed`, `expired`.
2. A turn executes tool calls and writes checkpoints after each tool result.
3. Only `complete_task` can end a successful run.
4. `complete_task(status="partial")` allowed for partial completion.
5. `complete_task(status="blocked")` required when blocked with reason.
6. Max 30 iterations per turn; overflow moves to `blocked` with resumable checkpoint.
7. Recoverable tool failures retry up to 3 attempts with backoff and jitter.
8. Gated actions pause run and create approval request.

## Context Injection Contract
1. Inject static: system identity, policy, tool usage rules.
2. Inject dynamic: tenant config summary, capability manifests, recent artifacts, active tasks, memory snapshot.
3. Refresh triggers: session start, every 5 iterations, after approval resolution.
4. Context budget policy: newest active task context first, then latest run artifacts, then memory summary.
5. Always include user-facing vocabulary mapping between UI terms and tool semantics.

## Shared Workspace Schema
1. `workspace/tenants/{tenant_id}/config/tenant.yaml`
2. `workspace/tenants/{tenant_id}/prompts/{profile}.md`
3. `workspace/tenants/{tenant_id}/runs/{run_id}/inputs/*.json`
4. `workspace/tenants/{tenant_id}/runs/{run_id}/analysis/*.md`
5. `workspace/tenants/{tenant_id}/runs/{run_id}/outputs/*.json`
6. `workspace/tenants/{tenant_id}/approvals/pending/*.json`
7. `workspace/tenants/{tenant_id}/approvals/resolved/*.json`
8. `workspace/tenants/{tenant_id}/memory/context.md`
9. `workspace/tenants/{tenant_id}/memory/temporal-memory.json`
10. `workspace/tenants/{tenant_id}/events/events.ndjson`

## API Surface (Public Interfaces)

### Session APIs
1. `POST /v1/sessions`
2. `GET /v1/sessions/{id}`
3. `POST /v1/sessions/{id}/turn`
4. `POST /v1/sessions/{id}/resume`
5. `GET /v1/sessions/{id}/tasks`
6. `POST /v1/sessions/{id}/tasks`
7. `DELETE /v1/sessions/{id}`

### Approval APIs
1. `GET /v1/approvals/{id}`
2. `POST /v1/approvals/{id}/resolve`
3. `GET /v1/tenants/{tenant_id}/approvals/pending`
4. `GET /v1/tenants/{tenant_id}/approvals/resolved`

### Capability APIs
1. `GET /v1/tenants/{tenant_id}/capabilities`
2. `POST /v1/tenants/{tenant_id}/capabilities/refresh`
3. `GET /v1/runtime`

### Prompt Profile APIs
1. `GET /v1/tenants/{tenant_id}/prompt-profiles/{profile}/rollout`
2. `POST /v1/tenants/{tenant_id}/prompt-profiles/{profile}/rollout`
3. `GET /v1/tenants/{tenant_id}/prompt-profiles/{profile}/evaluation`

### Artifact APIs
1. `GET /v1/sessions/{id}/artifacts`
2. `GET /v1/artifacts/{artifact_id}`
3. `PUT /v1/artifacts/{artifact_id}`

## Core Types
1. `AgentSession { id, tenant_id, objective, status, mode, iteration_count, checkpoint_path, created_at, updated_at }`
2. `AgentTask { id, session_id, title, status, notes, started_at, ended_at }`
3. `ApprovalRequest { id, session_id, action_type, payload_path, summary, status, requested_at, resolved_at, resolver }`
4. `ToolResult { success, output, should_continue, requires_approval, error_code }`
5. `ArtifactRef { id, run_id, kind, path, checksum, created_at }`
6. `CapabilityManifest { tenant_id, fetched_at, ttl_expires_at, amplitude, typeform, slack }`

## Agent Console UI (How You Interact)
1. Session Launcher: select tenant, objective, prompt profile, and mode.
2. Live Trace: see task transitions and tool calls with outcomes.
3. Artifacts Panel: inspect/edit generated payloads and analysis files.
4. Approval Inbox: approve/reject pending actions with risk summary and diff.
5. Capabilities Panel: view latest discovery manifests and refresh status.
6. Resume Controls: resume blocked sessions from checkpoints.
7. API Inspector: copy equivalent API calls for automation.

## API Interaction Workflow (How You Interact Programmatically)
1. Call `POST /v1/sessions` with `tenant_id` and `objective`.
2. Call `POST /v1/sessions/{id}/turn`.
3. Poll `GET /v1/sessions/{id}` for status.
4. If `waiting_approval`, call `POST /v1/approvals/{id}/resolve`.
5. Call `/turn` again until `completed`, `blocked`, or `failed`.
6. Fetch artifacts via `GET /v1/sessions/{id}/artifacts`.

## Prompt Profiles and Governance
1. Prompt files:
   - `prompts/system/base.md`
   - `prompts/system/policy.md`
   - `prompts/tasks/weekly_digest.md`
   - `prompts/tasks/anomaly_investigation.md`
2. Prompt versions are immutable and referenced by `prompt_profile + version`.
3. Canary rollout: 10% sessions for 7 days before full rollout.
4. Rollback: set tenant profile back to previous version in `tenant.yaml`.

## Security and Privacy Controls
1. Public repo has zero tenant-specific defaults, IDs, links, or product names.
2. Secrets via env only; never written to workspace artifacts.
3. Redaction middleware for tool logs and event traces.
4. Gated actions enforce human approval before side effects.
5. CI checks:
   - banned-token scan,
   - secret scan,
   - tenant identifier scan,
   - tracked-artifact allowlist scan.

## Reuse and Migration Strategy
1. Reuse internals from existing parsers/clients as tool implementations.
2. Replace monolithic orchestrator with Google ADK agent runtime + tool registry + prompt profiles.
3. Evolve debug UI into Agent Console instead of pipeline form.
4. Start from fresh public repository history with sanitized docs/templates only.

## Implementation Mapping (Current Modules -> Agent-Native Components)
| Current module | Agent-native target |
|---|---|
| `services/orchestrator.py` | Google ADK agent definition, runner wiring, and policy-gated tool execution |
| `clients/amplitude.py` | `tools/amplitude/*` query/summarize primitives |
| `clients/feedback.py` | `tools/typeform/*` fetch/redact primitives |
| `clients/slack.py` | `tools/slack/validate_payload` + approval-gated `post_payload` |
| `services/report_context.py` | `tools/context/*` loaders/discovery helpers |
| `services/temporal_memory.py` | tenant-scoped memory tools (`workspace/tenants/*/memory`) |
| `scripts/debug_pipeline_ui.py` | Agent Console foundation (trace/artifacts/approvals) |
| `main.py` | compatibility adapter to session runtime (V1) |

## Implementation Phases

### Phase 0: Public-safe foundation
1. New clean repo history.
2. MIT license and minimal docs.
3. Tenant-agnostic config templates.
4. CI safety scans.

### Phase 1: Runtime skeleton
1. Bootstrap Google ADK runtime (agent config, runner, session service).
2. Session model and state machine aligned with ADK session lifecycle.
3. Loop runner with explicit `complete_task` semantics.
4. Checkpoint persistence and resume behavior.
5. Event trace pipeline.

### Phase 2: Tool layer
1. Primitive CRUD tools implemented as ADK tools.
2. Wrapper tools for Amplitude/Typeform/Slack using existing client logic.
3. Discovery tools with constraints/caching.
4. Artifact IO tooling.

### Phase 3: Policy and approvals
1. Approval request lifecycle.
2. Gated action middleware.
3. Risk summaries and diff generation.
4. Approval API endpoints.

### Phase 4: Console and API parity
1. Agent Console UI.
2. Session/approval/artifact APIs.
3. Capability explorer UI.
4. End-to-end parity tests.

### Phase 5: Prompt-native behavior
1. Weekly digest task prompt.
2. Anomaly investigation prompt.
3. Prompt versioning and canary rollout.
4. Outcome evaluation harness.

## Phase Exit Gates
1. Phase 0 exit gate: tenant-identifier scan count is 0 in tracked files; secret scan and artifact allowlist checks pass.
2. Phase 1 exit gate: lifecycle and checkpoint/resume tests pass across interrupted sessions.
3. Phase 2 exit gate: CRUD and discovery tool contracts pass, including host allowlist and redaction checks.
4. Phase 3 exit gate: no side-effect tool executes without an approved `ApprovalRequest`.
5. Phase 4 exit gate: parity matrix passes for all console actions against API/tool equivalents.
6. Phase 5 exit gate: behavior variance is achieved through prompt profile/version changes without code edits.

## Test Plan and Scenarios

### Core correctness
1. Session lifecycle transitions are valid and complete.
2. `complete_task` is required for successful completion.
3. Resume restores message/task/artifact continuity.
4. ADK runner executes deterministic turns and preserves state across resume boundaries.

### Parity
1. Every console action has a tool/API equivalent.
2. Capability map parity tests enforced in CI.

### Discovery safety
1. Discovery tools never mutate external systems.
2. Discovery respects host allowlists and timeout/retry budgets.
3. Discovery outputs are redacted and tenant-scoped.

### Approval gates
1. Slack post cannot execute without approval.
2. Rejected approval blocks side effect and preserves artifacts.
3. Approval audit trail is complete.

### Prompt-native behavior
1. Objective can be completed with tool composition and no workflow tool.
2. New prompt profile can change behavior without code change.

### Public-safety regression
1. No tenant strings/IDs in tracked files.
2. No runtime artifacts or secrets tracked.
3. Clean-history publication check passes.

### CI execution defaults
1. Live integration tests are opt-in only (run when explicitly enabled plus required credentials are present).
2. Default CI path runs deterministic/unit suites only.
3. PR checks fail on any tenant-specific identifier match in tracked files.
4. PR checks fail when runtime workspace/debug artifacts are tracked.

## Rollout Plan
1. Internal alpha on one non-sensitive tenant.
2. Beta with 2-3 tenants and approval-only posting.
3. Public release of tenant-agnostic core.
4. Private tenant overlay onboarding package.

## Assumptions and Defaults
1. Python remains the implementation language.
2. Google ADK (Python) is the runtime SDK in V1.
3. Hybrid approval mode is default.
4. Workspace is file-first and git-ignored for runtime data.
5. Discovery tools are metadata-focused and read-only.
6. Tenant enablement is private overlay only, never public defaults.
7. `main.py` compatibility adapter is retained in V1 to preserve migration continuity.
8. Private tenant model access uses Gemini credentials via tenant-scoped secret configuration.

## Repository Research Summary (Local Snapshot: 2026-03-01)

### Architecture & Structure
1. Root repository is an active git worktree (`origin=https://github.com/OmarGanai/user-insights-agent.git`), with a mixed architecture:
   - legacy pipeline runtime (`main.py`, `services/orchestrator.py`, `clients/*`)
   - agent-native runtime slice (`agent_runtime/*`, `scripts/agent_runtime_api.py`)
2. Repository layout is domain-grouped and stable:
   - runtime/service code: `agent_runtime/`, `services/`, `clients/`, `scripts/`
   - prompts/contracts/docs: `prompts/`, `docs/`
   - verification: `tests/`
   - generated data roots: `workspace/`, `tmp/`
3. Dependency surface remains intentionally small (`requirements.txt`): `python-dotenv`, `requests`, `PyYAML`.
4. Recency baseline is fresh: current tree traces to commit `452473e` (`2026-03-01`).

### Issue Conventions
1. Root-level issue templates now exist under `.github/ISSUE_TEMPLATE/` (`bug_report.yml`, `feature_request.yml`).
2. Root-level PR template now exists at `.github/PULL_REQUEST_TEMPLATE.md`.
3. Label taxonomy remains minimal (`bug`, `enhancement` defaults in templates) and can be expanded later.
4. Practical implication: basic issue/PR conventions are now codified in-repo.

### Documentation Insights
1. Primary planning authority for agent-native cutover is this file (`agent-native-rebuild.md`) plus runtime contracts in `docs/*`.
2. Key operator-facing docs have been normalized to repo-relative paths:
   - `README.md`
   - `docs/product-analyst-spec.md`
   - `docs/pipeline-debug-studio-quickstart.md`
   - `docs/metric-dictionary.md`
3. README workflow reference is aligned with root CI (`.github/workflows/ci.yml`).
4. Testing norms are explicit and unittest-based (`python3 -m unittest ...` in `README.md` and `docs/product-analyst-spec.md`).
5. Public-safety policy is implemented and executable via `scripts/public_safety_scan.py`; local run currently passes.

### Templates Found
1. Root template inventory:
   - issue templates: `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/ISSUE_TEMPLATE/feature_request.yml`
   - PR template: `.github/PULL_REQUEST_TEMPLATE.md`
   - RFC templates: none found
2. Root CI workflow exists at `.github/workflows/ci.yml` (deterministic tests + public-safety scan).
3. Legacy nested workflow template has been retired from tracked tree; root `.github/workflows/ci.yml` is the sole active workflow.
4. Local-only legacy env artifacts (if present) remain out of tracked/public-safe scope via root gitignore and scan excludes.

### Implementation Patterns
1. Python typing-first style across runtime and services (`typing`, dataclasses, explicit return payloads).
2. Tool dispatch pattern is centralized in `agent_runtime/tools.py` via string-to-callable registry with structured `ToolResult`.
3. Session orchestration follows explicit state transitions and completion gate (`complete_task`) in `agent_runtime/runtime.py`.
4. Tenant isolation is filesystem-enforced in `agent_runtime/store.py` (`workspace/tenants/{tenant_id}/...`).
5. Discovery design enforces read-only constraints + TTL caching + redaction metadata in `agent_runtime/discovery.py`.
6. Test suite convention uses `unittest.TestCase` with deterministic fixtures and targeted patching/mocking.
7. `ast-grep` is not available in this local environment; pattern analysis used `rg` fallback.

### Recommendations
1. Keep repo-boundary cutover enforced by not reintroducing tracked files under `amplitude-insights-bot/`.
2. Continue normalizing or redacting legacy private-org references in historical docs where public distribution requires it.
3. Keep `scripts/public_safety_scan.py` as a required CI gate and pair it with tracked-artifact checks for `tmp/` and `workspace/`.
4. Remove local `amplitude-insights-bot/` remnants on developer machines once migration references are no longer needed.
