---
shaping: true
title: Vector - V3 Plan
status: active
slice: V3
source_slices_doc: redo/shaping/vector-slices-final.md
---

# Vector - V3 Plan

## Goal

Deliver real decision-brief synthesis via Python ADK + Gemini, persisted shared artifact editing, and claim-to-evidence debugging on top of live source snapshots.

## Scope In

- Synthesis engine using normalized snapshots + product/company context
- Active generation path is Python ADK + Gemini (no deterministic synthesis fallback)
- Shared report artifact persistence for draft + edits + evidence map
- Evidence resolver and debugger claim provenance inspection
- Live pipeline trace and prompt/context snapshot capture
- Runtime context injection for agent-native parity and runtime consumption
- 🟡 Explicit agent completion signaling (`complete_task`: `success` / `partial` / `blocked`) emitted by runtime
- 🟡 Primitive-first tool contract (workflow helpers may exist only as wrappers)

## Scope Out

- Final Slack delivery path and public demo packaging
- Slack thread Q&A mode (Shape C follow-on)

## Blocking Runtime Proof Gates

- Runtime identity gate: integration tests must prove draft generation ran with `backend=adk_gemini` and non-empty `model`.
- Completion semantics gate: `complete_task` payload must originate from runtime response, not local heuristic derivation.
- Config parity gate: `.env.example` and `README.md` must include `GEMINI_API_KEY`, `GEMINI_MODEL`, and `ADK_RUNTIME_URL`.

## Completion Payload Contract

```json
{
  "status": "success | partial | blocked",
  "summary": "string",
  "completedAt": "ISO-8601 timestamp",
  "backend": "adk_gemini",
  "model": "gemini model id"
}
```

## Implementation Checklist

- [ ] Route `write_report_draft` through Python ADK runtime client as the primary synthesis path.
- [ ] Remove deterministic synthesis fallback from active generation flow.
- [ ] Persist runtime `backend` and `model` metadata alongside completion payload in artifact run metadata.
- [ ] Implement `write_report_draft` flow to produce required brief sections, hypotheses, and recommendations from runtime output.
- [x] Implement shared artifact persistence model (`draft`, `edits`, `evidence`, `run metadata`).
- [x] Wire `update_report_section` to persisted artifact updates.
- [x] Implement evidence mapping and `get_evidence_for_claim` resolution endpoint/tool.
- [x] Implement pipeline trace capture and prompt snapshot retrieval for debugger.
- [ ] Inject runtime context payload (source inventory, capability map, vocabulary, recent run state) into the ADK runtime request.
- [ ] 🟡 Implement explicit `complete_task` completion signaling from runtime and persist status/summary in run metadata.
- [ ] 🟡 Enforce primitive-first tooling for V3 paths; workflow helpers may delegate only and cannot decide.
- [x] Wire center workbench and debugger drawer to live artifact + trace APIs.
- [ ] Add integration tests for runtime identity gate and completion semantics gate.
- [ ] Add CI runtime guard checks for config parity and runtime proof.

## Verification

- [ ] Generating a draft from live snapshots produces all required sections via ADK runtime.
- [x] Editing one section persists and survives reload/new fetch.
- [x] Clicking evidence chips opens debugger with correct provenance.
- [x] Debugger shows ingest/normalize/synthesize/render trace with prompt snapshot.
- [ ] Runtime identity gate passes (`backend=adk_gemini`, `model` present).
- [ ] Completion semantics gate passes (`complete_task` from runtime payload, no heuristic completion detection).
- [ ] Config parity gate passes (`.env.example` + `README.md` include Gemini/runtime keys).
- [ ] 🟡 Primitive-first tool contract is verifiable in the V3 execution path (workflow helpers delegate, not decide).

## Demo Script

1. Trigger generation from latest source snapshots.
2. Edit one section and save.
3. Open hypothesis data and click an evidence chip.
4. Verify debugger opens to matching claim/source trace and runtime backend metadata.
5. Open prompt tab and inspect prompt/context snapshot and runtime completion payload.

## Exit Criteria

- V3 closes B3/B4/B7/B8 mechanics with ADK+Gemini synthesis, traceable evidence, persisted artifact edits, and all runtime proof gates passing.
