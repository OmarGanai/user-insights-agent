# Slack Bot Activation Report Upgrade Plan

Last updated: 2026-02-21  
Scope: Implemented-spec record (PR1 + PR2 + PR3 complete; activation_v1 chart set created and validated)

## 1) Objective

Upgrade the weekly Slack bot report so it is activation-first, diagnostic, and decision-oriented for the current product phase.

Primary business objective:
- Improve activation urgency and decision quality while the app transitions toward AI-assisted household planning.
- Weekly KPI target remains 40-50% activation conversion.

## 1.0) Document State

- This file is now a completed implementation record, not a pending-work handoff.
- Historical sections are retained for traceability; completion status is captured in Sections 1.1, 10, 13, and 15.

## 1.1) Current Implementation Status (As of 2026-02-21)

- PR1 (`Chart Contract + Slack Structure`) is implemented in repo and validated with unit tests + golden dry-run fixture.
- PR2 (`iOS Releases + Focused Context + Temporal Memory`) is implemented in repo and validated with unit tests.
- PR3 (`Feedback Theming + Reliability Layer + Final Prompt Tuning`) is implemented in repo and validated with unit tests.
- Report contract is now `5 core + 3 supplemental` charts.
- Activation chart set contract (`activation_v1`) is now fully created + validated in `tenant-prod` (`appId=639837`).
- Chart contract artifacts are live:
- `docs/metric-dictionary.yaml`
- `docs/metric-dictionary.md`
- `docs/chart-build-sheet.yaml`
- Config cutover + rollback switch is live: `REPORT_CHART_SET=legacy|activation_v1` (default is `activation_v1`).
- Slack output order/gates are implemented and tested:
- `Executive Summary` -> `Key Metrics` -> `Insights & Next Steps`.
- PR2 artifacts now live:
- `docs/context/base-app-context.md`
- `docs/context/activation-weekly-context.md`
- `docs/ios-releases.md`
- `docs/temporal-memory-contract.md`
- `services/report_context.py`
- `services/temporal_memory.py`
- PR3 artifacts now live:
- `services/feedback_themes.py`
- `docs/report-style-contract.md`
- `docs/amplitude-chart-parser-reliability-notes.md`
- `activation_v1` validated chart IDs:
- `core_composite_activation_14d`: `0pl4jd50`
- `core_signup_to_any_dent_created`: `i3i58uut`
- `core_signup_to_calendar_connect_completed`: `ectuc1bm`
- `core_signup_to_appliance_added`: `w2p98xci` (existing, retained)
- `core_signup_to_hive_member_invited`: `p8g2bhzg`
- `supp_dent_action_mix_breakdown`: `9wo48n2l`
- `supp_calendar_started_to_completed`: `i2cqwsyx`
- `supp_14d_repeat_after_activation_proxy`: `0zug54x7`
- Debug Studio now includes stage artifacts for:
- Typeform feedback themes
- App context sections
- iOS release context
- This document now serves as a historical record of the implemented spec.

## 2) Locked Decisions From Planning

1. Environment scope:
- Use Amplitude `tenant-prod` only (`appId=639837`).
- Ignore `tenant dev/stg` for weekly reporting decisions.

2. Reporting cadence and framing:
- Report runs on Mondays.
- Standard chart framing should match current pattern:
- `Last 4 Weeks`
- `Weekly`
- `Previous Period vs`
- Segment excluding tenant employees.

3. Primary KPI definition:
- Activation KPI = `Signup: Completed -> any 1 high-value action within 14 days`.
- This will be the first chart in the report.

4. High-value action set for composite KPI:
- `Calendar Connect: Completed`
- `Task: Created`
- `Event: Created`
- `Note: Created`
- `Document: Uploaded`
- `House: Appliance Added`
- `Hive: Member Invited`

5. Weekly Slack content structure:
- Main post emphasizes `5 core charts`.
- `3 supplemental` charts are shown as compact diagnostics appendix.
- Report language should include both absolute counts and percentages.
- Do not use statistical-significance framing in decision text at current scale.

6. Incomplete interval handling:
- Keep default chart behavior (`excludeCurrentInterval=false`) to match existing chart setup.
- Operational expectation: Monday run timing minimizes partial-week distortion.

7. Delivery format for this planning cycle:
- Execution continues as `3 sequential PRs`.
- PR1, PR2, and PR3 were completed; chart creation/validation and cutover-readiness work has since been completed as recorded below.

## 3) Current-State Validation (Amplitude MCP)

Validated in `tenant-prod`:
- Core tracked events exist:
- `Signup: Completed`, `Task: Created`, `Event: Created`, `Note: Created`, `House: Appliance Added`, `Hive: Member Invited`, `Life Tab: Viewed`, `Life Tab: Member Tapped`.
- New useful event exists:
- `Calendar Connect: Completed` (and `Calendar Connect: Started`).
- Exact FTUE events are not present as named:
- `FTUE: Begun`
- `FTUE: First Item Created`
- `FTUE: First Hive Invite`
- `FTUE: Completed (First Item Assigned)`

API diagnostics capability validated:
- Funnel chart query returns conversion percentages plus step counts.
- Events segmentation chart query returns raw time-series volumes.
- This supports percentage + absolute-number diagnosis even without significance testing.

Additional validation from implementation:
- `House: Appliance Added` business event has volume; several route-level appliance events from UX docs are sparse/near-zero in current weekly windows.
- Do not rely on route-change appliance events as required diagnostics in weekly decisioning.

## 4) Target Chart Portfolio (8 Total)

## 4.1 Core (Main Report, Ordered)

1. Core-1 (Primary KPI): `Signup -> Composite Activation (any 1 high-value action)`  
Status: Implemented and validated  
Chart id: `0pl4jd50`

2. Core-2: `Signup -> Any DENT Created (Task/Event/Note/Document)`  
Status: Implemented and validated  
Chart id: `i3i58uut`

3. Core-3: `Signup -> Calendar Connect: Completed`  
Status: Implemented and validated  
Chart id: `ectuc1bm`

4. Core-4: `Signup -> House: Appliance Added`  
Status: Existing chart to keep  
Known chart id: `w2p98xci`

5. Core-5: `Signup -> Hive: Member Invited`  
Status: Implemented and validated  
Chart id: `p8g2bhzg`

## 4.2 Supplemental Diagnostics (Compact Appendix)

6. Supp-1: DENT action mix breakdown (Task vs Event vs Note vs Document conversion from signup)  
Status: Implemented and validated  
Chart id: `9wo48n2l`

7. Supp-2: Calendar connection quality funnel (`Calendar Connect: Started -> Calendar Connect: Completed`)  
Status: Implemented and validated  
Chart id: `i2cqwsyx`

8. Supp-3: 14-day repeat behavior after activation proxy (retention-style)  
Status: Implemented and validated  
Chart id: `0zug54x7`  
Modeling decision: preferred custom activation-proxy start event implemented (`ce:Activation Proxy`)

## 4.3 Existing Charts to De-emphasize (Not in Main 8)

- `oys29da5` (`Signup -> Life Tab: Viewed`)  
- `gfhad295` (`Signup -> Life Tab: Member Tapped`)  
- `sb8w2oof` (Hive invite retention)  

These remain useful as optional context but are less aligned with immediate activation priorities than the selected 8.

## 5) Chart Definition Standards

Apply these defaults to all new charts unless explicitly overridden:
- Project: `tenant-prod` (`appId=639837`)
- Segment: `≠ tenant employees`
- Range: `Last 4 Weeks`
- Interval: `Weekly`
- Comparison: `Previous Period vs` enabled
- Metric output should allow reporting both:
- Conversion percentage
- Absolute counts (base and converted where available)

For composite/diagnostic charts:
- Prefer funnel definitions where base/step counts are directly interpretable.
- Use events-segmentation for action-mix and raw-volume trend visibility.

## 6) Slack Report Target Structure

Main section order:
1. Activation KPI status vs target (40-50%)
2. Top 3 metric movers from core charts (ordered 1 through 5 source set, with chart links)
3. What likely changed this week (release context + feedback themes + confidence)
4. Immediate actions
- Every action should include `owner`, `priority`, and `expected impact`.

Diagnostics appendix:
- 3 supplemental charts with compact notes.
- Keep terse and decision-focused.

Formatting rules:
- Every key observation should include:
- Percentage
- Absolute count or denominator/step volume
- Chart title and link

## 7) Context and Data Inputs To Improve Report Quality

## 7.1 iOS Release Context

Requirement:
- Add a maintained release log at:
- `docs/ios-releases.md`
- On each pipeline run:
- Query Apple lookup API for app id `6480279827` (`https://itunes.apple.com/lookup?id=6480279827`).
- Prepend newest-first.
- De-duplicate by exact `version + build`.

Implementation update:
- Implemented in `services/report_context.py`.
- Release ingestion is non-blocking for report publishing.
- Fallback dedupe key is documented and implemented as `version + release_date` when build is unavailable.

## 7.2 App Context Refactor

Split broad context into:
- `docs/context/base-app-context.md`
- `docs/context/activation-weekly-context.md`

Intent:
- Keep static context stable.
- Keep weekly activation context lightweight and frequently updated.

Implementation update:
- Context loader now prefers split files and falls back to legacy `app-context.md` when needed.

## 7.3 Metric Dictionary (Bot Source of Truth)

Create and maintain:
- `docs/metric-dictionary.yaml` (machine source)
- `docs/metric-dictionary.md` (human-readable mirror)

## 7.4 Typeform Feedback Coverage

Requirement:
- Use full responses for the lookback window (`LOOKBACK_DAYS`), not response-count truncation.
- Preserve current time-window behavior and avoid arbitrary top-N truncation in prompt inputs.

## 7.5 Feedback Theming

Before final LLM prompt:
- Group feedback into themes.
- Include mention counts.
- Include representative snippets.
- Feed themes into analysis context rather than only raw snippets.

## 7.6 Temporal Memory

Add prior-report memory to support:
- What changed week-over-week.
- What persisted.
- What action status should be revisited.

Implementation update:
- Contract and schema documented at `docs/temporal-memory-contract.md`.
- Runtime memory file path is `tmp/weekly-report-memory.json`.
- Memory writes are idempotent and rotate `latest_report` to `previous_report` on changes.

## 8) Executed PR Sequencing Plan (3 Sequential PRs)

## PR 1: Chart Contract + Slack Structure

Goal:
- Align report output with new 5-core + 3-supplemental contract and ordering.

Status:
- Complete in repo.

Completed work:
1. Add chart catalog contracts and naming standards.
2. Wire core/supplemental grouping into config and report assembly.
3. Update Slack blocks to:
- Core-first main narrative.
- No supplemental appendix section in the default weekly post.
4. Ensure report statements include both percentages and counts.
5. Add tests for ordering, section layout, and required fields.

Acceptance criteria:
1. Dry run renders 5 core charts first and 3 supplemental afterward.
2. Output observations include percentage + absolute figures.
3. Existing chart pipeline still runs without regression.

Validation evidence:
- `python3 -m unittest discover -s tests -p 'test_*.py'` passed.
- Golden fixture maintained at:
- `tests/fixtures/pr1_legacy_dry_run_sections.json`

## PR 2: iOS Releases + Focused Context + Temporal Memory

Goal:
- Improve analysis context quality before feedback theming.

Status:
- Complete in repo.

Completed work:
1. iOS release fetch + markdown update logic.
2. Context split (base + activation-weekly).
3. Memory contract for prior report continuity.
4. Prompt payload updates to include structured release/context/memory sections.
5. Tests for release dedupe and context loading behavior.
6. Tests for temporal memory idempotence/rotation behavior.

Acceptance criteria:
1. Duplicate releases are not appended.
2. Prompt context is focused and bounded.
3. Report can reference recent changes vs persistent issues.

Validation evidence:
- `python3 -m unittest discover -s tests -p 'test_*.py'` passed (`Ran 32 tests ... OK`).
- New PR2 tests:
- `tests/test_report_context_pr2.py`
- `tests/test_temporal_memory_pr2.py`

## PR 3: Feedback Theming + Reliability Layer + Final Prompt Tuning

Goal:
- Improve diagnostic quality and confidence framing under low volume.

Status:
- Complete in repo.

Completed work:
1. Removed prompt-side feedback truncation by count (kept `LOOKBACK_DAYS` window behavior).
2. Added theme extraction pipeline for feedback.
3. Added reliability annotations from chart data:
- Base counts and converted counts
- Incomplete bucket awareness
- Low-volume caution handling
4. Validated reliability fields against official Amplitude chart API docs and aligned parser assumptions.
5. Finalized report style contract for clear decisions.
6. Added tests and fixtures for themed feedback and confidence behavior.

Acceptance criteria:
1. Report references theme counts and representative feedback.
2. Low-confidence claims are explicitly labeled when evidence is thin.
3. Monday run output is stable, concise, and action-oriented.

Validation evidence:
- `python3 -m unittest discover -s tests -p 'test_*.py'` passed (`Ran 37 tests ... OK`).
- New PR3 tests/fixtures:
- `tests/test_feedback_themes_pr3.py`
- `tests/test_orchestrator_pr3.py`
- `tests/fixtures/pr3_feedback_theme_summary.json`

## 9) Risks and Guardrails

1. Low user volume:
- Treat significance as out of scope.
- Emphasize directional read with absolute numbers and transparent confidence.

2. Taxonomy drift:
- Enforce metric dictionary as source of truth.
- Keep event naming mappings explicit in config.

3. Overly long prompt context:
- Bound input size by structured context sections.
- Favor summaries over large raw dumps.

4. Environment contamination:
- Hard-scope all report queries to `tenant-prod` only.

## 10) Implementation Record Checklist (Completed)

1. `activation_v1` chart creation + validation completed.
2. `supp_appliance_path_quality` remains removed.
3. Report contract remains `5 core + 3 supplemental`.
4. PR3 behavior/tests remain intact.
5. Cutover/rollback switch remains in place (`REPORT_CHART_SET=legacy|activation_v1`).
6. Sections 11, 12, 13, and 14 remain release-gate references for ongoing operation.

## 11) Non-Negotiable Guardrails (To Prevent Implementation Errors)

1. Environment lock:
- Every Amplitude query for weekly reporting must use `appId=639837` only.
- Never merge prod and staging events/charts in the same report payload.

2. Segment lock:
- Use the same exclusion logic as current production funnels:
- user property `userdata_cohort` with condition `is not` value `5cn1caqx` (tenant employees cohort).
- Do not silently change this segment in new charts.

3. Chart identity rules:
- New chart definitions must get explicit names matching the metric dictionary.
- Do not overwrite existing chart semantics behind old IDs.
- Metric dictionary must be the canonical mapping of `metric_key -> chart_id -> intent`.

4. Report contract stability:
- Keep output JSON schema stable (`headline`, `key_changes`, `possible_explanations`, `suggested_actions`, metadata).
- Do not ship prompt/report format changes without updating tests and fixture snapshots.

5. Core chart failure behavior:
- If any core chart fails to query, include a pipeline note in report output.
- Do not fabricate missing values.
- Degrade confidence and continue with available evidence unless all core charts fail.

6. Typeform completeness:
- Ensure feedback retrieval is bounded by `LOOKBACK_DAYS` time window, not arbitrary item limits.
- Review current pagination ceiling (`max_pages=10`) so high-response periods are not silently truncated.

7. PII hygiene:
- Do not include raw emails or direct identifiers in prompt or Slack output.
- Keep feedback snippets sanitized and minimally necessary.

8. iOS release ingestion constraints:
- Verify actual Apple lookup response fields before coding dedupe logic.
- If build number is unavailable from endpoint response, define and document fallback dedupe key (for example `version + release_date`).
- Release updater failures must not block weekly report publishing.

9. Temporal memory contract:
- Define one explicit file path and schema for prior report memory before implementation.
- Memory writes must be idempotent and robust in CI/local dry runs.

10. Time handling:
- Keep one consistent time basis in report generation (current code uses UTC for headers and timestamps).
- Avoid mixed local/UTC comparisons in period-over-period commentary.

11. Evidence-first writing rule:
- Every major claim in `key_changes` and `possible_explanations` must cite chart evidence (counts and percentages).
- When evidence is weak or missing, force explicit low-confidence wording.

## 12) Chart Build Sheet (Maintained Contract)

Maintain a concrete build sheet for every required chart with these fields:
- `metric_key`
- `chart_name`
- `chart_type` (funnel/eventsSegmentation/retention)
- `app_id` (must be `639837`)
- `segment_definition` (must match employee exclusion standard)
- `time_settings` (`Last 4 Weeks`, `Weekly`, `Previous Period vs`)
- `event_steps_or_series` (exact event names in order)
- `metric_mode` (conversion/uniques/etc.)
- `rationale` (what decision this chart supports)
- `chart_id` (empty until created; filled immediately after creation)
- `status` (`planned`, `created`, `validated`)

Minimum required build-sheet entries:
1. `core_composite_activation_14d`
2. `core_signup_to_any_dent_created`
3. `core_signup_to_calendar_connect_completed`
4. `core_signup_to_appliance_added` (existing id reference)
5. `core_signup_to_hive_member_invited`
6. `supp_dent_action_mix_breakdown`
7. `supp_calendar_started_to_completed`
8. `supp_14d_repeat_after_activation_proxy`

## 13) Cutover and Rollback Rules

Add an explicit chart-set switch in config:
- `REPORT_CHART_SET=legacy|activation_v1`

Cutover policy:
- Default to `activation_v1`.
- Switch to `legacy` only for rollback if release-gate checks fail.

Rollback policy:
- If any core chart query fails in production run:
- keep publishing report with explicit pipeline warning,
- and allow immediate revert by toggling back to `legacy`.

Current state:
- Cutover switch exists in code.
- Default is `activation_v1`.
- `activation_v1` chart IDs are now complete and validated.
- Keep `legacy` available for rollback if release-gate checks fail.

## 14) Golden Output Validation (Release Gate)

For each PR, maintain a golden dry-run artifact snapshot in `tmp/` (or test fixtures) and verify:
1. Section order is correct (`Executive Summary`, `Key Metrics`, `Insights & Next Steps`).
2. Main report references only the 5 core charts.
3. Optional supplemental diagnostics are available for debugging, but omitted from the default weekly Slack post.
4. Every key claim includes percentage plus at least one absolute number.
5. Chart links resolve to expected chart IDs from metric dictionary.
6. No PII appears in generated report text.

A PR is not complete until golden-output checks pass.

## 15) Completion Record (Closed Items)

1. `activation_v1` required chart IDs were created and validated.
2. `supp_14d_repeat_after_activation_proxy` modeling decision is finalized with the preferred custom activation-proxy start event.
3. Chart artifacts were updated (`metric-dictionary.yaml`, `metric-dictionary.md`, `chart-build-sheet.yaml`) with validated IDs and statuses.
4. Debug Studio was extended to expose:
- Typeform feedback theme output
- App context sections output
- iOS release context output
5. Test status remains green:
- `python3 -m unittest discover -s tests -p 'test_*.py'` passes.

This document is now retained as the implementation record for the built activation-report spec.
