# Debug UI Incident Timeline (Run Button and Toggle Failures)

## Scope

This document captures the troubleshooting timeline for the `scripts/debug_pipeline_ui.py` frontend incident where:

- `Run Pipeline` button appeared clickable but did not execute the pipeline.
- `Human Readable` / `Machine Readable` toggles appeared non-functional.
- Browser console initially showed no useful logs.

The goal is historical reconstruction plus practical lessons to improve debugging speed next time.

## Source Records Used

- Terminal commands and outputs from this session.
- Served HTML checks from `http://127.0.0.1:8787/`.
- Console error lines provided by user.
- Local file diff for `scripts/debug_pipeline_ui.py`.

---

## High-Level Summary

1. UI enhancements were added (human/machine toggle + Slack visual preview).
2. Controls stopped working due JavaScript parse errors in served HTML.
3. Initial diagnosis was slowed by stale server processes still serving old HTML after code changes.
4. Two independent JS parse bugs were found and fixed.
5. Inline button instrumentation proved useful when main script failed early.
6. After final fix and server restart, controls worked again.

---

## Detailed Timeline

## Phase 1: Feature Additions

What we tried:

- Rebuilt `debug_pipeline_ui.py` HTML/JS UI to include:
- Global `Human Readable` / `Machine Readable` mode switch.
- Stage-specific human summaries.
- Slack-like rendered preview panel.

Observed problem:

- User reported `Run Pipeline` and mode toggles were non-functional.

## Phase 2: First Connectivity and Runtime Checks

What we tried:

- Checked local listener with `lsof -nP -iTCP:8787 -sTCP:LISTEN`.
- Checked endpoint with `curl -sS http://127.0.0.1:8787/api/defaults`.

Problems encountered:

- In-sandbox `curl` intermittently failed due isolation from user localhost.
- Process showed as listening, but behavior checks were inconsistent until elevated local checks were used.

What fixed this part:

- Used local elevated curl checks to confirm endpoint and served HTML content.

## Phase 3: First Instrumentation Attempt

What we tried:

- Added main-script logging (`[PipelineDebugUI] ...`) around init, click handlers, fetch calls, and errors.
- Added `window.__runPipeline` binding and fallback click wiring.

Why attempts did not work initially:

- Browser still received older served HTML snapshot from a previously running process.
- User saw no new logs because updated script was not yet what browser parsed.

## Phase 4: Inline Click Instrumentation

What we tried:

- Added inline `onclick` handlers directly in button HTML for:
- Run button.
- Human toggle.
- Machine toggle.
- Inline handlers wrote status text and console lines independent of main JS parser state.

Result:

- User confirmed inline status changed to `Inline run click captured`.
- Console showed inline click logs.
- Console also showed `window.__runPipeline missing`, proving main script had not finished parsing/executing.

This was a key turning point.

## Phase 5: Parse Error #1 (Quote Escape Map Key)

User-provided console error:

- `Uncaught SyntaxError: Unexpected string (index:626:11)`

What we found:

- Served JS around line 626 contained:
- `""": "&quot;",`
- This came from embedded JS object key escaping inside Python triple-quoted HTML.

What we changed:

- Rewrote `escapeHtml()` from object-literal lookup to explicit `if` chain.
- Removed fragile escaped-quote key in object literal.

Why repeated attempts still failed for a while:

- Server still served pre-fix content until process restart.

## Phase 6: Parse Error #2 (Regex Newline Escape)

User-provided console error after first fix:

- `Uncaught SyntaxError: Invalid regular expression: missing / (index:881:27)`

What we found:

- Served JS line appeared as split regex literal:
- `html = html.replace(/`
- `/g, "<br>");`
- Root cause was `\n` escaping inside Python triple-quoted string becoming an actual newline in embedded JS.

What we changed:

- Replaced regex newline conversion with escape-safe code:
- `html = html.split(String.fromCharCode(10)).join("<br>");`

Why repeated attempts still failed briefly:

- Again, stale process served old HTML until restart/refresh.

## Phase 7: Final Verification

What we checked:

- Confirmed served line range now contains fixed newline conversion.
- Confirmed no remaining problematic syntax in served slices.
- Confirmed inline click capture and main handler availability.

Outcome:

- UI behavior recovered.
- Button and toggles functioned.

---

## Problem Catalog

### Problem A: Hidden parse errors in embedded JS

- Symptom: button click does nothing, no app logs.
- Root cause: script parse failure prevents initialization.
- Why hard to spot: inline logs were missing until inline handlers were added.

### Problem B: Stale server process serving outdated HTML

- Symptom: local source file differs from served HTML.
- Root cause: process not restarted after patch.
- Why hard to spot: repeated code fixes looked correct in file, but browser still ran old script.

### Problem C: Localhost checks from sandbox context

- Symptom: endpoint seemed unreachable from assistant context.
- Root cause: sandbox networking isolation differences.
- Mitigation: use explicit local/elevated endpoint checks when validating user-local servers.

---

## Repeated Attempts and Why They Failed

1. Added richer JS logs in main script.
- Failed because main script never parsed; logs never executed.

2. Added fallback event listeners (`window.__runPipeline`, click handlers).
- Failed because parse errors happened earlier; handler registration code never ran.

3. Patched source file and re-checked AST/Node syntax locally.
- Still failed in browser because running server served stale pre-patch HTML.

4. Re-ran curl checks without verifying served line ranges.
- Slower feedback loop; stale build issue remained undetected until line-based HTML verification was used.

---

## What Worked Best

1. Inline `onclick` diagnostics in raw HTML.
- Works even when main script fails to parse.
- Quickly distinguishes DOM click issues from JS initialization issues.

2. Served HTML line-range inspection.
- `curl | nl -ba | sed -n '<line-range>p'` exposed exact parse-break lines.

3. Verifying served content, not just file content.
- Prevented false confidence from correct local file with stale running process.

---

## Process Improvements for Future Incidents

1. Add a visible build marker in served HTML.
- Example: `window.__UI_BUILD = "2026-02-20T11:xx:xxZ"` and render in status line.
- Immediate proof browser is on latest build.

2. Add a restart-and-verify routine when changing embedded JS.
- Restart server.
- Hard refresh.
- Check sentinel string via curl.

3. Prefer escape-safe JS in Python-embedded HTML.
- Avoid regex/backslash-heavy snippets in triple-quoted strings.
- Prefer straightforward string operations where equivalent.

4. Keep inline emergency diagnostics for critical controls.
- Run button/toggles should always emit minimal status even if full app init fails.

5. Add a tiny smoke check command for served JS parse risk.
- Extract `<script>` and run `node --check` as part of local verification.

---

## Quick Playbook (Next Time)

1. Reproduce click failure.
2. Add/confirm inline button `onclick` status updates.
3. Check served HTML line range where console points.
4. Fix syntax at source.
5. Restart server, hard refresh, confirm sentinel in served HTML.
6. Re-test controls.
7. Remove or keep diagnostics as needed.

