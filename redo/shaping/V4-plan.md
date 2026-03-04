---
shaping: true
title: Vector - V4 Plan
status: active
slice: V4
source_slices_doc: redo/shaping/vector-slices-final.md
---

# Vector - V4 Plan

## Goal

Finalize Slack preview/publish fidelity and distribution packaging for a public, runnable demo.

## Scope In

- Canonical Block Kit serializer shared by preview and publish
- Real publish action via configured Slack webhook destination
- Publish metadata persistence and UI visibility
- Public setup docs + `.env.example` + deploy instructions/demo URL
- Runtime-proof and config-proof CI gates for ADK+Gemini path
- Optional bot-token channel-selection seam (explicitly non-MVP)

## Scope Out

- Full bot-token channel picker implementation
- Slack conversational thread analyst mode

## Implementation Checklist

- [x] Implement canonical renderer (`render_blockkit_preview`) as the single payload source.
- [x] Wire right-panel preview to canonical serializer output.
- [x] Implement `post_slack_message` webhook publish with robust error handling.
- [x] Persist publish metadata (timestamp, destination label, success/failure) on shared artifact.
- [x] Surface publish metadata in UI (sources/report context).
- [ ] Add ADK+Gemini runtime configuration (`ADK_RUNTIME_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`) to `.env.example` and setup docs.
- [x] Document optional bot-token path (`chat.postMessage`) as future mode only.
- [x] Run end-to-end test that compares preview payload and published payload equivalence.
- [ ] Ensure publish path operates on artifacts generated from ADK runtime (no deterministic synthesis fallback in active path).
- [ ] Add CI runtime-proof and config-parity gates to block checklist drift.

## Verification

- [x] Preview payload and published payload are equivalent for the same artifact.
- [x] Publish success and failure states are clear to user.
- [ ] External reviewer can run project locally from docs and environment template including ADK+Gemini runtime prerequisites.
- [ ] Runtime-proof CI gates pass on pull requests.
- [ ] Live demo URL is published and documented.

## Demo Script

1. Generate/update a report artifact.
2. Open preview and inspect payload representation.
3. Publish to configured Slack destination.
4. Verify message landed and publish metadata is visible in app.
5. Follow setup docs from clean environment and confirm local run.

## Exit Criteria

- V4 closes B6/B9 and satisfies demo packaging requirements with ADK+Gemini runtime guardrails enforced in CI.

## Post-MVP Deferred Follow-Ups

- Defer explicit CRUD completeness matrix + parity tests for all entities until after V4 MVP core flow is accepted.
- Defer emergent-capability/composability validation (prompt-only feature additions + open-ended outcome tests) until after V4 MVP core flow is accepted.
