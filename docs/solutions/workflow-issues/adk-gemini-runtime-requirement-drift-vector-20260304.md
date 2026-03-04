---
module: System
date: 2026-03-04
problem_type: workflow_issue
component: development_workflow
symptoms:
  - "V3 was marked completed while active runtime never executed Google ADK + Gemini synthesis."
  - "`complete_task` appeared in trace output as derived metadata instead of an explicit agent-loop completion call."
  - "Runtime prompt/context snapshot was generated but not consumed by any model in the active path."
  - "Current runtime docs and env template excluded Gemini runtime requirements from active setup guidance."
root_cause: missing_workflow_step
resolution_type: workflow_improvement
severity: high
tags: [adk, gemini, agent-native, acceptance-gates, checklist-drift]
---

# Troubleshooting: ADK + Gemini Requirement Drift in Vector V3/V4

## Problem
The implementation diverged from the shaping contract: shaped requirements specified Google ADK (Python) + Gemini for agent reasoning, while active code path used deterministic TypeScript synthesis. V3 checklist closure became misleading because it validated output shape, not runtime identity.

## Environment
- Module: System-wide (Vector runtime + shaping workflow)
- Affected Component: V3/V4 execution path, checklist closure criteria, test gates
- Date: 2026-03-04

## Symptoms
- `redo/shaping/shaping-final.md` requires agent reasoning and ADK+Gemini stack (`R5.4`, `R5.6`, `R6.1`).
- V3 plan was marked `status: completed` with agent-loop items checked as done.
- Active generate path was:
  - `app/api/report-artifact/generate/route.ts` -> `writeReportDraft()`
  - `lib/vector/workflows.ts` -> `writeReportDraftPrimitive()`
  - `lib/vector/primitives.ts` -> `synthesizeReportDraft(...)`
  - `lib/vector/synthesis.ts` deterministic hypothesis/recommendation generation
- `complete_task` trace step was appended from computed source coverage status, not emitted by an agent runtime tool call.
- `.env.example` and README focused on source adapters and Slack publish, with no active Gemini runtime requirements.

## What Didn't Work

**Attempted Solution 1:** Treating "agent-loop contract" as interface semantics (trace fields + completion status payload).
- **Why it failed:** This met trace schema expectations but did not satisfy shaped requirement that reasoning stay in the agent runtime.

**Attempted Solution 2:** Verifying V3 through output-contract tests only (`sections`, `evidenceMap`, `promptSnapshot`, trace step presence).
- **Why it failed:** Tests proved deterministic pipeline behavior, not ADK+Gemini execution.

**Attempted Solution 3:** Archiving prior Python runtime as legacy while continuing TS deterministic synthesis as active implementation.
- **Why it failed:** Removed runtime parity with shaping constraints without introducing replacement ADK execution in active flow.

## Solution
Adopt a two-part fix: (1) process guardrails to prevent requirement drift, and (2) implementation plan to deliver real ADK + Gemini runtime with deterministic fallback.

### Process guardrails (immediate)
1. Reopen V3/V4 checklist items tied to true agent runtime semantics.
2. Add hard acceptance gates to plans and CI:
   - Runtime identity gate: at least one integration test must prove ADK endpoint/model path was invoked.
   - Completion semantics gate: `complete_task` must be emitted by the agent runtime payload, not derived in TS synthesis.
   - Config gate: `.env.example` + README must include Gemini runtime keys when ADK path is required.
3. Split verification into:
   - Output correctness (artifact shape)
   - Runtime correctness (agent backend provenance)

### Implementation plan: ADK + Gemini in active path

#### Phase 0: Re-baseline contracts
- Update V3/V4 plan files: mark runtime-dependent items as open.
- Add an explicit "runtime proof" checklist section.
- Define canonical completion payload contract returned by runtime:
  - `status: success | partial | blocked`
  - `summary: string`
  - `completedAt: ISO timestamp`
  - `backend: adk_gemini | deterministic_fallback`

#### Phase 1: Add Python ADK runtime service
- Create `services/adk-runtime/` (Python) with:
  - ADK runner/session wiring
  - Gemini model config (`GEMINI_API_KEY`, `GEMINI_MODEL`)
  - Endpoint: `POST /synthesize` accepting normalized snapshots + runtime context
- Response must include:
  - generated sections/hypotheses/recommendations/evidence map
  - explicit `complete_task` payload
  - trace metadata with model/backend fields

Example interface sketch:
```python
# services/adk-runtime/app.py
@app.post("/synthesize")
def synthesize(req: SynthesisRequest) -> SynthesisResponse:
    result = adk_runner.run(req)
    return {
        "artifact": result.artifact,
        "completion": result.complete_task,  # emitted by runtime
        "trace": result.trace,
        "backend": "adk_gemini",
        "model": settings.gemini_model,
    }
```

#### Phase 2: Wire Next.js backend to runtime client
- Add runtime client module in TS (`lib/vector/agent-runtime-client.ts`).
- Replace direct deterministic synthesis call in the primary draft path.
- Keep deterministic synthesis as fallback only when runtime is unavailable.

Before (current active path):
```ts
const synthesis = synthesizeReportDraft(state, runtimeContext)
```

After (target path):
```ts
const runtimeResult = await synthesizeViaAgentRuntime({ state, runtimeContext })
const synthesis = runtimeResult.ok
  ? runtimeResult.payload
  : synthesizeReportDraft(state, runtimeContext) // explicit fallback mode
```

#### Phase 3: Completion semantics correction
- Remove TS-side computed `complete_task` as source of truth for runtime mode.
- Persist runtime-emitted completion payload into `artifact.runMetadata`.
- In fallback mode, mark backend as `deterministic_fallback` and annotate trace clearly.

#### Phase 4: Tooling and docs parity
- Add `.env.example` entries:
  - `GEMINI_API_KEY=`
  - `GEMINI_MODEL=gemini-3-flash-preview`
  - `ADK_RUNTIME_URL=`
- Update README with:
  - ADK runtime startup instructions
  - fallback behavior semantics
  - troubleshooting for missing Gemini creds/runtime unavailability

#### Phase 5: Test + CI gates
Add integration tests that fail unless runtime behavior is real:
1. `runtime_identity.test`:
   - asserts backend=`adk_gemini` in successful runtime mode
   - asserts model value is present
2. `completion_contract.test`:
   - asserts `complete_task` comes from runtime payload
   - asserts statuses only in `success|partial|blocked`
3. `fallback_contract.test`:
   - simulates runtime outage and verifies explicit fallback labeling
4. `docs_env_contract.test` (or lightweight lint script):
   - asserts GEMINI env vars are present in `.env.example` and README setup section

#### Phase 6: Re-close criteria
V3/V4 runtime-dependent items can be re-closed only when all of the following are true:
- ADK runtime path is exercised in integration tests.
- Runtime-emitted completion payload is persisted and visible in debugger.
- Fallback mode is explicit and non-default when runtime is healthy.
- Docs/env contract includes Gemini + runtime setup.

## Why This Works
This addresses the actual root cause: closure criteria were output-only and allowed runtime identity drift. The new approach adds runtime-proof gates, so checklist completion requires evidence of ADK+Gemini execution, not just shaped outputs. Separating runtime correctness from output correctness prevents recurrence.

## Prevention
- Add a "source-of-truth hierarchy" rule to shaping docs:
  - Shaping requirements > slice checkboxes > implementation convenience.
- Require every runtime-constrained requirement to have a corresponding failing test before implementation.
- Add a PR checklist item: "If requirement names a specific runtime/model, show proof artifact in test output or trace metadata."
- Enforce a drift check in review:
  - If plan says "agent reasoning", reject deterministic-only logic in active path unless explicitly marked fallback.

## Commands run
```bash
pnpm test:vector
pnpm typecheck
```

## Related Issues
No related issues documented yet.
