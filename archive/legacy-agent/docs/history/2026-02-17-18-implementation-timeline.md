# Amplitude Insights Bot: Planning, Execution, and Testing Timeline

## Scope

This document reconstructs the end-to-end implementation history for the recent local-testing and reporting-quality workstream in `<redacted-org>/amplitude-insights-bot`, combining:

- Conversation/execution trail (Cursor transcript and terminal runs)
- Git commit history and changed files
- Local debug artifacts generated during validation

It is intentionally historical (what happened, in order), not prescriptive.

## Source Records Used

- Conversation transcript: `c3b86afd-8fcc-435b-b853-479f0b307ed1`
- Git history from local repo (`main`) and pushed remote (`origin/main`)
- Local artifacts under `tmp/pipeline-debug-*`

---

## High-Level Sequence

1. Initial bot scaffold and Gemini/Typeform/GitHub hardening landed.
2. Local testability became the priority (dry-run, no Slack side effects, stage-by-stage visibility).
3. Multi-repo GitHub context support (`private-org/ios`, `private-org/react-web`) replaced single-repo assumptions.
4. `--skip-github` path was added to keep local iteration unblocked during token approval/auth issues.
5. Major Amplitude parsing fix shipped for non-`timeSeries` payloads.
6. Date-range/cohort verification was completed using artifacts + docs/MCP capability checks.
7. Funnel semantics were corrected from step-count interpretation to period-over-period conversion interpretation.
8. Prompting and report readability were iterated:
   - facts-first mode + `app-context.md` grounding
   - then title/link-based chart references + grounded, low-confidence inference allowance
9. Full test/re-run cycle passed; changes were committed and pushed.

---

## Commit Timeline (Chronological)

> Repo: https://github.com/<redacted-org>/amplitude-insights-bot

### Foundation and Core Integrations

- `1f301dd` (2026-02-17 17:43:18 -0500)  
  **Initial scaffold for Amplitude Insights Bot**  
  Added project structure, clients, config, orchestrator, analyzer, workflow, env template.  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/1f301dd

- `a06d5c4` (2026-02-17 17:46:24 -0500)  
  **Switch insights analysis from OpenAI to Gemini**  
  Migrated analysis provider and related config/docs/workflow wiring.  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/a06d5c4

### Repo Constraints and External Data Stability

- `33113df` (2026-02-17 19:00:07 -0500)  
  **Restrict bot to private-org org defaults**  
  Hardened owner defaults and workflow/env assumptions.  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/33113df

- `889c7fa` (2026-02-17 19:15:18 -0500)  
  **Grant GitHub token permissions for PR context**  
  Workflow token permission update.  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/889c7fa

- `716bacd` (2026-02-17 19:16:48 -0500)  
  **Make Typeform feedback fetch non-blocking**  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/716bacd

- `1c8807f` (2026-02-17 19:18:06 -0500)  
  **Harden Typeform timestamp handling and fallback**  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/1c8807f

- `2e2a658` (2026-02-17 19:20:41 -0500)  
  **Align Typeform client with responses API docs**  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/2e2a658

- `17689a2` (2026-02-17 19:23:17 -0500)  
  **Add Gemini rate-limit retries and model fallback**  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/17689a2

- `7014964` (2026-02-17 19:28:13 -0500)  
  **Update Gemini defaults to supported 3.x models**  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/7014964

- `f690e56` (2026-02-17 19:40:33 -0500)  
  **Sync latest internal tool file updates**  
  README / env sync.  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/f690e56

### Local Testing and Pipeline Debugging Flow

- `c46ea7b` (2026-02-17 20:12:18 -0500)  
  **Add skip_github option to run_weekly_report for local testing**  
  Added skip path and local debug pipeline/test updates.  
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/c46ea7b

### Accuracy and Readability Iteration Bundle

- `17e411a` (2026-02-17 21:31:08 -0500)  
  **Improve Amplitude report accuracy and readability**  
  Bundled:
  - Amplitude parser upgrades (`clients/amplitude.py`)
  - Chart reference/title mapping (`config.py`)
  - Analyzer prompt/context changes (`services/analyzer.py`)
  - Orchestrator/local-debug chart-title+link wiring
  - New tests (`tests/test_amplitude_summary.py`, `tests/test_analyzer.py`)
  - `app-context.md` inclusion
  https://github.com/<redacted-org>/amplitude-insights-bot/commit/17e411a

---

## Detailed Execution History

## Phase 1: Local-First Pipeline Validation Design

### Planning Decisions

- Keep GitHub Actions out of the loop for iteration speed.
- Validate each stage independently with persisted artifacts.
- Avoid Slack side effects during testing.

### Execution

- Confirmed `--dry-run` behavior path.
- Added local script flow to write stage outputs:
  - `01_amplitude_query_charts.json`
  - `02_github_recent_merges.json`
  - `03_typeform_feedback.json`
  - `04_ai_analysis.json`
  - `05_slack_payload_preview.json`

### Testing

- `python3 -m unittest tests/test_local_debug_pipeline.py` ran and passed in multiple iterations.
- Initial environment issues (missing deps / python command mismatch) were resolved in-session.

---

## Phase 2: GitHub Context Access and Repo Scope Correction

### Observed Failures

- Stage-2 GitHub fetch returned `404` when targeting `<redacted-org>/amplitude-insights-bot`.
- Then returned `401 Bad credentials` for desired repos pending token validity/approval.

### Execution

- Added `GITHUB_REPOS` CSV support for multi-repo PR context.
- Updated orchestrator + local debug script to iterate repos and merge/sort PRs.
- Added tests to ensure both repos are queried in order.

### Unblocking Strategy

- Added `--skip-github` to:
  - `main.py`
  - `services/orchestrator.py`
  - `scripts/local_debug_pipeline.py`
- Ensured stage-2 still writes an explicit empty artifact when skipped.

### Testing

- Local debug tests expanded:
  - multi-repo fetch assertions
  - skip-github no-call assertions
- Local runs completed end-to-end with GitHub stage intentionally bypassed.

---

## Phase 3: Amplitude `null/0` Summary Root Cause and Parser Expansion

### Problem

- Report summaries had `null` / `0` values despite non-empty chart payloads.

### Root Cause Found

- Summarizer only parsed `timeSeries`.
- Actual payloads included data under:
  - `data.series[].values` (segmentation/retention-like structures)
  - `data[].dayFunnels`
  - `data[].cumulativeRaw`
  - `data[].stepByStep`

### Execution

- Refactored extraction logic in `clients/amplitude.py`:
  - shape-specific helpers
  - numeric bucket extraction
  - date sorting helpers
  - fallback ordering for non-zero data
- Added dedicated coverage in `tests/test_amplitude_summary.py`.

### Testing

- `python3 -m unittest tests/test_amplitude_summary.py tests/test_local_debug_pipeline.py`
  passed after parser updates.
- Real artifact re-summarization produced meaningful values for charts previously empty.

---

## Phase 4: Date-Range and Cohort Verification Track

### User Questions Addressed

- Do API date windows match what’s visible in Amplitude?
- Are cohort filters included in chart API results?

### Execution and Findings

- Extracted date arrays from local artifact (`tmp/pipeline-debug-live/01_amplitude_query_charts.json`).
- Confirmed all tracked charts shared the same window in that run (`2026-01-19` to `2026-02-16`).
- Verified MCP server capability in workspace:
  - exposed `ui://amplitude/chart.html` resource descriptor
  - no direct chart-query callable tool in current MCP setup
- Pulled Amplitude docs context (Context7 / dashboard API docs) and inspected payload fields:
  - cohort filtering behavior is reflected in computed results
  - payload generally does not include friendly cohort labels as-is (only related metadata fields).

---

## Phase 5: Funnel Semantics Correction (Counts vs Conversion Period Compare)

### Trigger

- UI screenshots showed "Previous Period vs." comparison, but bot summary interpreted funnel arrays as step-count trend (`97 -> 54`) instead of conversion-period change (`61.9% -> 55.7%`).

### Execution

- Updated funnel summarization to detect two-period funnel payload shape and compute:
  - `current_conversion_pct`
  - `previous_conversion_pct`
  - percentage-point delta
  - relative delta
  - current/previous start/end counts
- Preserved generic extraction for non-period-comparison shapes.

### Validation Against Shared Charts

- `oys29da5`: now expressed as `55.67%` vs `61.9%`, not `54` vs `97`.
- `rviqohkp`: aligned with screenshot-scale conversion comparison.
- `hc4183lh`: aligned with screenshot-scale conversion comparison.

### Testing

- Added/updated funnel comparison tests in `tests/test_amplitude_summary.py`.
- Resolved rounding expectation mismatch and re-ran tests to green.

---

## Phase 6: Prompting Iterations (Facts, Context, Readability)

### Iteration A: Facts-First Constraint

- Added strict factual guidance to `services/analyzer.py`.
- Added `app-context.md` loading + prompt grounding:
  - `services/orchestrator.py`
  - `scripts/local_debug_pipeline.py`
- Added analyzer prompt tests (`tests/test_analyzer.py`).

Outcome:

- Report became strongly factual and explicitly low-confidence when evidence was weak.

### Iteration B: Readability and Stakeholder Clarity

- Replaced chart ID-centric references with chart titles + links in analyzer inputs.
- Added chart reference mapping in `config.py`:
  - `CHART_TITLE_OVERRIDES`
  - `get_chart_reference()`
- Updated Slack “Referenced Charts” section to show title-linked entries.
- Relaxed explanation section to allow grounded inference (while retaining confidence cues and non-fabrication guardrails).

Outcome:

- Report became easier to scan and share:
  - title-based chart mentions
  - clickable links
  - cautious hypotheses grounded in metrics + app context

---

## Testing and Verification Log (Consolidated)

## Unit / Integration-Style Tests

- Repeated successful runs:
  - `python3 -m unittest tests/test_local_debug_pipeline.py`
  - `python3 -m unittest tests/test_amplitude_summary.py tests/test_local_debug_pipeline.py`
  - `python3 -m unittest tests/test_analyzer.py tests/test_amplitude_summary.py tests/test_local_debug_pipeline.py`

## End-to-End Local Debug Runs

- Successful runs with artifacts:
  - `python3 scripts/local_debug_pipeline.py --output-dir tmp/pipeline-debug-live --skip-github`
  - `python3 scripts/local_debug_pipeline.py --output-dir tmp/pipeline-debug-final --skip-github`
  - `python3 scripts/local_debug_pipeline.py --output-dir tmp/pipeline-debug-factual --skip-github`
  - `python3 scripts/local_debug_pipeline.py --output-dir tmp/pipeline-debug-readable --skip-github`

## Runtime / External Failure Events Seen During Testing

- GitHub:
  - `404` on wrong repo target
  - `401 Bad credentials` during PAT approval/access mismatch
- Gemini:
  - transient `429` rate-limit retries (handled)
  - occasional transient `503` from fallback model endpoint during one run (retry succeeded in subsequent run)
- Environment:
  - local `urllib3` LibreSSL warning (non-blocking)

---

## Artifact Evolution Snapshot

- `tmp/pipeline-debug-live/01_amplitude_query_charts.json`  
  Primary raw evidence used for parser root-cause and date/cohort checks.

- `tmp/pipeline-debug-final/04_ai_analysis.json`  
  Captured post-parser-correction report style before readability pass.

- `tmp/pipeline-debug-factual/04_ai_analysis.json`  
  Captured strict facts-first output after context grounding.

- `tmp/pipeline-debug-readable/04_ai_analysis.json` and `05_slack_payload_preview.json`  
  Captured title/link-based, stakeholder-readable grounded report.

---

## Final State at End of This Session

- Branch status: `main` synced with `origin/main`.
- Latest pushed commit: `17e411a`.
- Working tree clean after push.

Primary capability outcomes now present in codebase:

- Local, stage-by-stage debug workflow with reproducible artifacts
- Skip-able GitHub context for faster local iteration
- Multi-repo GitHub PR ingestion
- Robust Amplitude chart summarization across observed payload shapes
- Correct funnel period-comparison semantics
- App-context-grounded analyzer prompting
- Readable, chart-title-and-link-oriented report language

---

## Verifiable Time/Effort Addendum

Only timing values with direct evidence (commit timestamps or terminal `elapsed_ms`) are included below.

## A) Commit-Window Effort Estimates (Wall-Clock)

These are measured as `end commit timestamp - start commit timestamp` and should be read as **observed implementation windows**, not pure coding-only time.

| Step Block | Verifiable Evidence | Window |
|---|---|---|
| Foundation scaffold + model migration | `1f301dd` (17:43:18 -0500) -> `a06d5c4` (17:46:24 -0500) | **00:03:06** |
| Org/pipeline hardening cluster | `33113df` (19:00:07 -0500) -> `f690e56` (19:40:33 -0500) | **00:40:26** |
| Local testing + skip-github + accuracy/readability bundle window | `c46ea7b` (20:12:18 -0500) -> `17e411a` (21:31:08 -0500) | **01:18:50** |
| Overall history span captured in this doc | `1f301dd` (17:43:18 -0500) -> `17e411a` (21:31:08 -0500) | **03:47:50** |

## B) Measured Validation Runtime Estimates (Terminal Logs)

These are exact command runtimes from terminal log footers.

| Step | Command | Outcome | Measured Runtime |
|---|---|---|---|
| Local pipeline validation run (AI on, GitHub skipped) | `python3 scripts/local_debug_pipeline.py --output-dir tmp/pipeline-debug-now --skip-github` | Success | **55,938 ms** |
| Factual-report run attempt | `python3 scripts/local_debug_pipeline.py --output-dir tmp/pipeline-debug-factual --skip-github` | Failed (`Gemini 503`) | **36,881 ms** |
| Readability/report-format run | `python3 scripts/local_debug_pipeline.py --output-dir tmp/pipeline-debug-readable --skip-github` | Success | **45,855 ms** |

No additional step-level estimates are included where direct timing evidence was not available.

