---
shaping: true
title: Vector - V3 Plan
status: draft
slice: V3
source_slices_doc: redo/shaping/vector-slices-draft-1.md
---

# Vector - V3 Plan

## Goal

Deliver real decision-brief synthesis, persisted shared artifact editing, and claim-to-evidence debugging on top of live source snapshots.

## Scope In

- Synthesis engine using normalized snapshots + product/company context
- Shared report artifact persistence for draft + edits + evidence map
- Evidence resolver and debugger claim provenance inspection
- Live pipeline trace and prompt/context snapshot capture
- Runtime context injection for agent-native parity
- 🟡 Explicit agent completion signaling (`complete_task`: `success` / `partial` / `blocked`)
- 🟡 Primitive-first tool contract (workflow helpers may exist only as wrappers)

## Scope Out

- Final Slack delivery path and public demo packaging
- Slack thread Q&A mode (Shape C follow-on)

## Implementation Checklist

- [ ] Implement `write_report_draft` flow to produce required brief sections, hypotheses, and recommendations.
- [ ] Implement shared artifact persistence model (`draft`, `edits`, `evidence`, `run metadata`).
- [ ] Wire `update_report_section` to persisted artifact updates.
- [ ] Implement evidence mapping and `get_evidence_for_claim` resolution endpoint/tool.
- [ ] Implement pipeline trace capture and prompt snapshot retrieval for debugger.
- [ ] Inject runtime context payload (source inventory, capability map, vocabulary, recent run state) into synthesis runtime.
- [ ] 🟡 Implement explicit `complete_task` completion signaling and persist completion status/summary in run metadata.
- [ ] 🟡 Enforce primitive-first tooling for V3 paths; document any workflow helper as a delegating wrapper over primitives.
- [ ] Wire center workbench and debugger drawer to live artifact + trace APIs.
- [ ] Add integration tests for synthesis output contract and evidence trace integrity.

## Verification

- [ ] Generating a draft from live snapshots produces all required sections.
- [ ] Editing one section persists and survives reload/new fetch.
- [ ] Clicking evidence chips opens debugger with correct provenance.
- [ ] Debugger shows ingest/normalize/synthesize/render trace with prompt snapshot.
- [ ] 🟡 Agent runs terminate via explicit `complete_task` status rather than heuristic stop conditions.
- [ ] 🟡 Primitive-first tool contract is verifiable in the V3 execution path (workflow helpers delegate, not decide).

## Demo Script

1. Trigger generation from latest source snapshots.
2. Edit one section and save.
3. Open hypothesis data and click an evidence chip.
4. Verify debugger opens to matching claim/source trace.
5. Open prompt tab and inspect prompt/context snapshot.

## Exit Criteria

- V3 closes B3/B4/B7/B8 mechanics with real synthesis + traceable evidence and persisted artifact edits.
