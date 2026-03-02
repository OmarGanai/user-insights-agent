---
shaping: true
title: Vector (Demo 1) — 1-Page PRD
status: draft
---

## Frame

**Problem**
Product teams spend too much time stitching together metrics, release notes, and user feedback before they can decide what to do next.

**Goal**
Ship a public, open-source demo agent in one weekend that proves AI automation execution quality and helps product teams move faster.

**Users**
Product managers and product ops at small-to-mid software teams.

**Core JTBD**
“Given new product data across tools, give me an actionable weekly report I can trust, edit quickly, and post to Slack.”

## Requirements (R)

| ID | Requirement |
|---|---|
| R1 | Build in a weekend, minimal code and setup. |
| R2 | Use Google ADK (Python) + Gemini 3 Flash. |
| R3 | Pull data from Amplitude, App Store release notes, and Typeform. |
| R4 | Use a product context document (flows/surfaces) during synthesis. |
| R5 | Produce actionable report sections (summary, signals, hypotheses, recommendations). |
| R6 | Human-in-the-loop: user can preview and edit before posting. |
| R7 | Preview must match Slack Block Kit output fidelity. |
| R8 | Post final report to Slack channel. |
| R9 | Follow agent-native architecture principles (tools + decision loop, not static script pipeline). |
| R10 | Publish as open-source repo + live demo URL. |

## Candidate Shapes

**Shape A: Single-pass Reporter**
Run integrations, generate report, auto-post to Slack.
- Strength: fastest implementation.
- Weakness: fails edit/preview fidelity requirement.

**Shape B: Review-First Reporter (recommended)**
Run integrations, draft report, render Block Kit preview, user edits, then publish.
- Strength: satisfies trust + control + Slack parity.
- Weakness: slightly more UI/UX work.

**Shape C: Conversational Analyst Workspace**
Chat-first interface with iterative analysis and multi-turn edits.
- Strength: most flexible.
- Weakness: exceeds weekend scope.

## Fit Check

| Requirement | A | B | C |
|---|---|---|---|
| R1 Weekend scope | ✅ | ✅ | ❌ |
| R2 Stack constraint | ✅ | ✅ | ✅ |
| R3 3 integrations | ✅ | ✅ | ✅ |
| R4 Context doc grounding | ✅ | ✅ | ✅ |
| R5 Actionable report | ✅ | ✅ | ✅ |
| R6 Preview + edit | ❌ | ✅ | ✅ |
| R7 Block Kit parity | ⚠️ | ✅ | ✅ |
| R8 Slack publish | ✅ | ✅ | ✅ |
| R9 Agent-native | ⚠️ | ✅ | ✅ |
| R10 Public proof-of-work | ✅ | ✅ | ⚠️ |

**Chosen shape: Shape B (Review-First Reporter).**

## Scope

**In scope (MVP)**
1. Manual run trigger.
2. Read 3 integrations.
3. Context doc injection.
4. Draft generation.
5. Block Kit preview.
6. Inline edit before publish.
7. Slack publish.

**Out of scope (MVP)**
1. Scheduling/orchestration.
2. Multi-workspace tenancy.
3. Fine-grained role permissions.
4. Long-term memory and trend baselining.

## Success Criteria

1. User can go from “Run report” to “Posted in Slack” in under 10 minutes.
2. At least one meaningful recommendation appears in each report.
3. Preview and final Slack post match structurally (same sections/format).
4. Demo is publicly accessible (GitHub + live demo).
