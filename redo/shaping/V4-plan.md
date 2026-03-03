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
- [x] Add webhook configuration and required secrets to `.env.example` and setup docs.
- [x] Document optional bot-token path (`chat.postMessage`) as future mode only.
- [x] Run end-to-end test that compares preview payload and published payload equivalence.

## Verification

- [x] Preview payload and published payload are equivalent for the same artifact.
- [x] Publish success and failure states are clear to user.
- [x] External reviewer can run project locally from docs and environment template.
- [ ] Live demo URL is published and documented.

## Demo Script

1. Generate/update a report artifact.
2. Open preview and inspect payload representation.
3. Publish to configured Slack destination.
4. Verify message landed and publish metadata is visible in app.
5. Follow setup docs from clean environment and confirm local run.

## Exit Criteria

- V4 closes B6/B9 and satisfies demo packaging requirements for the weekend public release.

## Post-MVP Deferred Follow-Ups

- Defer explicit CRUD completeness matrix + parity tests for all entities until after V4 MVP core flow is accepted.
- Defer emergent-capability/composability validation (prompt-only feature additions + open-ended outcome tests) until after V4 MVP core flow is accepted.
