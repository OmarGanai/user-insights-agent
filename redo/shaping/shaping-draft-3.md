---
title: Vector — 1-Page PRD (v3)
status: draft
---

## Frame

**Problem**
Product teams lose momentum because metrics, release notes, and feedback are fragmented across tools.

**Goal**
Ship a public, open-source demo agent in a weekend that turns fragmented product signals into an actionable decision brief, with human review before Slack posting.

**Primary user**
PM / Product Ops.

**Core outcome**
Inputs (sources) -> Draft (analysis/chat) -> Report (Slack-ready decision brief).

## UX Direction (MVP)

NotebookLM-inspired, simple and polished 3-column desktop/laptop layout:

1. **Sources column (left)**  
   Amplitude, Typeform, iOS release notes (Markdown + App Store Connect API latest), product context doc.
2. **Draft column (center)**  
   Agent analysis + editable draft conversation/workbench.
3. **Report column (right)**  
   Slack Block Kit preview + publish controls.

Plus a **Debugger UI** (tab/drawer) to inspect how the report was stitched together.

## Requirements (R)

| ID | Requirement |
|---|---|
| R1 | Weekend scope, minimal implementation. |
| R2 | Stack: Google ADK (Python) + Gemini 3 Flash. |
| R3 | Sources: Amplitude, Typeform, iOS release notes from Markdown file and App Store Connect API. |
| R4 | Use product context document during synthesis. |
| R5 | Output = actionable decision brief with clear actions. |
| R6 | Human-in-the-loop review/edit before publish. |
| R7 | Preview must match final Slack Block Kit structure. |
| R8 | Publish to Slack channel. |
| R9 | Agent-native architecture compliance (below). |
| R10 | Manual API keys via `.env` for MVP. |
| R11 | Open-source repo + live demo URL. |
| R12 | Ship Shape B now; evolve toward Shape C (Slack Q&A on posted reports). |
| R13 | UI quality bar: visually strong, simple, and intentional (“sexy”), not enterprise clutter. |
| R14 | Include debugger view for source -> transform -> claim traceability. |

## R9 Agent-Native Compliance (Must Pass)

1. **Action parity**: every UI action has a corresponding agent tool.
2. **Context parity**: agent sees same source snapshots, context docs, and run history as user.
3. **Shared workspace**: drafts, edits, evidence links, and final report are in one shared artifact model.
4. **Primitives over workflows**: tools fetch/read/write/render/post/trace; reasoning stays in agent.
5. **Dynamic context injection**: runtime prompt includes source inventory, capability map, vocabulary, and recent run state.

## Capability Map (Shape B MVP)

| UI Action | Agent Tool Equivalent | Status |
|---|---|---|
| Load sources list/status | `list_sources`, `get_source_status` | ✅ |
| Fetch latest source data | `fetch_amplitude`, `fetch_typeform`, `read_release_notes_file`, `fetch_app_store_release_notes` | ✅ |
| Read context doc | `read_product_context` | ✅ |
| Generate draft | `write_report_draft` | ✅ |
| Edit draft section | `update_report_section` | ✅ |
| Render Slack preview | `render_blockkit_preview` | ✅ |
| Publish to Slack | `post_slack_message` | ✅ |
| Open debugger trace | `get_pipeline_trace`, `get_evidence_for_claim` | ✅ |
| Ask report follow-up in Slack thread | `answer_thread_question` | ⚠️ (Shape C) |

## Actionable Report Shape (MVP)

**Decision Brief v1 sections**
1. Executive summary
2. What changed (key signals)
3. Why it changed (hypotheses + confidence)
4. Recommendations (ranked actions)
5. Owner + next step + ETA
6. Evidence appendix (claim -> source links/snippets)

## Debugger (MVP)

**Purpose**
User can verify report integrity and trust the output.

**Minimum features**
1. Per-source ingest status + timestamps
2. Normalized intermediate data preview
3. Claim-to-evidence trace (each recommendation linked to source evidence)
4. Prompt/context snapshot used for this run
5. Error panel with retry per source

## Shape Progression

**Now: Shape B (Review-First Reporter)**  
Run -> Draft -> Edit -> Block Kit preview -> Publish.

**Later: Shape C (Conversational Slack Analyst)**  
After posting, team members ask questions in Slack thread; agent answers using same evidence and context primitives.
