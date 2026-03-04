---
shaping: true
title: Vector - Slices Final
status: final
selected_shape: B
source_shaping_doc: redo/shaping/shaping-final.md
---

# Vector - Slices Final

## Context

This document slices selected Shape B from `redo/shaping/shaping-final.md` into vertical, demo-able implementation increments.

The UX/UI baseline comes from the Vercel prototype at `redo/shaping/vercel`.

## Prototype References

| Surface | Prototype file | Notes |
|---------|----------------|-------|
| App shell and 3-column layout | `redo/shaping/vercel/app/page.tsx` | Column widths, collapse rails, global header, debugger bar |
| Sources panel | `redo/shaping/vercel/components/vector/sources-panel.tsx` | Source rows, refresh affordance, expandable charts, stale warning |
| Draft workbench | `redo/shaping/vercel/components/vector/draft-workbench.tsx` | Editable sections, hypotheses, recommendations, evidence chips |
| Publish/preview panel | `redo/shaping/vercel/components/vector/report-preview.tsx` | Ready state, Slack preview, publish states |
| Debugger drawer | `redo/shaping/vercel/components/vector/debugger-drawer.tsx` | Pipeline/prompt tabs, expandable trace rows |

## Slice Strategy

| Slice | Objective | Shape B parts covered | Requirement focus | Demo output |
|-------|-----------|-----------------------|-------------------|-------------|
| V1 | Ship interactive 3-column review shell using mock data | B5, B7 (UI shell), B4 (artifact stub) | R1.1, R1.2, R7.1, R7.2, R7.3 | User can open app, inspect sources, edit draft text, toggle preview/debugger |
| V2 | Make source ingestion real and observable | B1, B2, B5.2 | R2, R2.1-R2.5, R3.1 | User can fetch live sources, see freshness/errors, and inspect source status |
| V3 | 🟡 Make draft generation and evidence trace real with explicit agent-loop completion + primitive-tool contract | B3, B4, B7, B8 | 🟡 R1.3, R3.2-R3.5, R5.1-R5.7 | User can generate draft from real snapshots, edit/persist, and trace claims to evidence |
| V4 | Make Slack preview/publish + packaging production-ready | B6, B9 | R0, R0.1, R0.2, R4, R6 | User can preview exact payload, publish via configured Slack path, and run public demo setup |

---

## V1 Slice: Review Shell (Mock-Backed)

### UI Affordances (V1)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| U1 Sources Panel (mock list) | Web App: Left Column | Show source inventory and status badges from mock data. | N5 |
| U3 Draft Workbench (editable) | Web App: Center Column | Edit section text inline and view hypotheses/recommendations. | N5 |
| U4 Report Preview (mock serializer output) | Web App: Right Column | Show ready state and Slack-style preview from artifact data. | N6 |
| U5 Publish Button (simulated) | Web App: Right Column | Exercise sending/sent state transitions without backend publish. | N7 |
| U6 Debugger Toggle + Drawer | Web App: Footer + Drawer | Open/close debugger and switch between Pipeline and Prompt tabs. | N8 |

### Non-UI Affordances (V1)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| N5 Shared Report Artifact (in-memory stub) | Frontend State | Hold draft sections + evidence references in one artifact shape. | U3, N6 |
| N6 Block Kit Renderer (client stub) | Frontend | Convert artifact to preview model for the right panel. | U4 |
| N7 Slack Publisher (simulated client action) | Frontend | Drive publish UI states (`idle -> sending -> sent`) only. | U5 |
| N8 Pipeline Trace Log (mock) | Frontend | Provide static pipeline/prompt data for debugger UI integration. | U6 |

### Wiring by Place (V1)

| Place | Wiring |
|-------|--------|
| Web App | U1/U3 update and read N5; U4 reads N6; U5 triggers N7; U6 reads N8 |
| Backend | None in V1 (all behavior uses stubbed data) |

### V1 Demo Check

- Open app at desktop width and verify 3-column layout with collapsible side rails.
- Edit one draft section and see updated content in both center column and preview.
- Toggle debugger drawer and switch tabs.
- Trigger simulated publish and observe state progression.

---

## V2 Slice: Live Sources + Status

### UI Affordances (V2)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| U1 Sources Panel (live) | Web App: Left Column | Show live source status, timestamps, and stale/error messaging. | N3 |
| U2 Refresh Source Button (live fetch) | Web App: Left Column | Re-fetch a single source and update status transitions. | N2 |
| U3 Draft Workbench source freshness chips | Web App: Center Column | Surface which snapshot version is feeding the current draft. | N1, N3 |

### Non-UI Affordances (V2)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| N1 Source Snapshot Store | Backend | Persist normalized source snapshots per run. | N4, N8 |
| N2 Source Fetch Orchestrator | Backend Tools | Call Amplitude, Typeform, iOS Lookup + release markdown adapters. | N1, N3 |
| N3 Source Status Index | Backend | Track per-source sync state, recency, and adapter-level errors. | U1, U3 |
| B2 Context loader bootstrap | Backend | Ensure product context doc is loadable and versioned for later synthesis. | N4 |

### Wiring by Place (V2)

| Place | Wiring |
|-------|--------|
| Web App | U1 reads N3; U2 invokes N2; U3 reads source freshness from N3 |
| Backend Tools | N2 updates N1 and N3 per source |
| Backend | N1 stores normalized snapshots and exposes latest run inventory |

### V2 Demo Check

- Trigger full ingest and verify status updates across all required sources.
- Refresh one source and confirm status transitions and timestamp update.
- Force a source error and verify user-facing error visibility.

---

## V3 Slice: Draft Synthesis + Evidence Trace

### UI Affordances (V3)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| U3 Draft Workbench (generated content) | Web App: Center Column | Render generated brief sections, hypotheses, and recommendations. | N4, N5 |
| U7 Claim Evidence Inspector | Debugger Drawer | Open claim-level provenance from evidence chips and hypothesis data blocks. | N9 |
| U6 Debugger (live trace) | Web App: Footer + Drawer | Show ingest -> normalize -> synthesize -> render trace and prompt snapshot. | N8 |

### Non-UI Affordances (V3)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| N4 Synthesis Engine | Backend Agent | Build six-section decision brief from snapshots + product context. | N5, N6 |
| N5 Shared Report Artifact (persisted) | Backend | Persist draft, edits, evidence map, and run metadata. | U3, N6, N9 |
| N8 Pipeline Trace Log (live) | Backend | Capture tool calls, transform steps, prompt/context snapshot. | U6 |
| N9 Evidence Resolver | Backend | Resolve claim -> evidence links/snippets from normalized snapshots. | U7 |
| B8 Runtime context injection | Backend Agent runtime | Inject source inventory, capability map, vocabulary, and recent run state. | N4 |
| N10 Agent completion signal contract | 🟡 Backend Agent runtime | 🟡 Provide explicit `complete_task` signaling with `success` / `partial` / `blocked` status and summary payload. | U6 |
| N11 Primitive tool contract | 🟡 Backend Tools + Agent runtime | 🟡 Keep primitives as source of truth; any workflow helpers delegate to primitives and do not embed decision logic. | N4, N8 |

### Wiring by Place (V3)

| Place | Wiring |
|-------|--------|
| Backend Agent | 🟡 N4 consumes N1 + context docs, writes N5, appends N8, and exits via N10 completion signal |
| Web App | U3 reads/writes N5; U6 reads N8; U7 resolves details via N9 |
| Backend | 🟡 N9 reads N5 and snapshots to return claim-level provenance; N11 enforces primitive-first tool layering |

### V3 Demo Check

- Generate a draft from live snapshots and context documents.
- Edit at least one section and confirm persisted change on reload.
- Click evidence chips and inspect corresponding provenance in debugger.
- Open pipeline trace and verify prompt/context snapshot visibility.

---

## V4 Slice: Slack Publish + Packaging

### UI Affordances (V4)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| U4 Report Preview (serializer-backed) | Web App: Right Column | Render preview from the same serializer used for publish payload. | N6 |
| U5 Publish Button (real) | Web App: Right Column | Post reviewed payload to configured Slack destination. | N7 |
| U1/U3 publish metadata tags | Web App: Left + Center | Show last publish time/status and destination transparency. | N5 |

### Non-UI Affordances (V4)

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| N6 Block Kit Renderer (canonical) | Backend | Single serializer for preview and final Slack payload. | U4, N7 |
| N7 Slack Publisher (webhook MVP) | Backend Tools | Publish payload to one configured destination and store result metadata. | N5 |
| N7b Optional Web API publisher | Backend Tools | Future path for dynamic channel selection with bot token/scopes. | N5 |
| B9 Packaging + docs | Repo + deploy | Public repo docs, `.env.example`, and demo deployment instructions/URL. | R0 |

### Wiring by Place (V4)

| Place | Wiring |
|-------|--------|
| Backend | N6 renders from N5 artifact; N7 posts payload and writes publish metadata back to N5 |
| Web App | U4 consumes N6 output; U5 calls N7 and reflects delivery state |
| Distribution | B9 ensures public setup and live demo availability |

### V4 Demo Check

- Preview and publish use byte-equivalent serialized blocks.
- Publish succeeds to configured Slack destination and metadata is visible in app.
- Public setup docs + `.env.example` allow local run by external reviewer.

---

## Cross-Slice Guardrails

- Keep webhook mode as MVP default; channel picker remains optional `chat.postMessage` follow-on path.
- Preserve shared artifact model as system boundary across slices.
- Every new UI action must have an explicit agent-tool equivalent before slice close.
- Apply the R7 rubric from `redo/shaping/spike-r7-results-ux-rubic-shape-b.md` at each slice that changes UI.
- Runtime-constrained requirements require runtime-proof evidence before checklist close (test and trace must prove `backend=adk_gemini` when ADK+Gemini is required).
- 🟡 Agent loops must terminate using explicit `complete_task` semantics; do not use heuristic completion detection.
- 🟡 Tooling stays primitive-first across slices; workflow tools are optional wrappers, not capability gates.
- No deterministic synthesis fallback is allowed in active generation paths for ADK+Gemini-constrained slices.

## Post-MVP Deferred Architecture Items (After Core Flow Works)

These are intentionally deferred until V1-V4 MVP core flow is complete.

| Item | Deferred scope | Trigger to pick up |
|------|----------------|--------------------|
| D1 | Explicit CRUD completeness matrix for report/snapshot/status entities (including delete/archive semantics and parity tests) | After V4 exit criteria are met |
| D2 | Emergent capability + composability validation pass (prompt-only feature additions and open-ended outcome tests) | After V4 exit criteria are met |
