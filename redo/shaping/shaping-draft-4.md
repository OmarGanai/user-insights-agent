---
shaping: true
title: Vector - Shaping Draft 4
status: draft
selected_shape: B
---

# Vector - Shaping Draft 4

## Frame

### Source
- Prior artifact: `redo/shaping/shaping-draft-3.md`
- Prior implementation reference: `redo/previous-api-usage.md`
- API validation pass: Context7 + official docs review on 2026-03-02

### Problem
Product teams lose momentum because metrics, release notes, and feedback are fragmented across tools, so synthesis and reporting are slow and hard to trust.

### Project Outcome
Ship a public open-source demo in weekend scope that turns fragmented product signals into an actionable decision brief with human review before Slack publish.

## Core User JTBD
Given new product data across tools, give me an actionable weekly report I can trust, edit quickly, and post to Slack.

### Primary User
PM / Product Ops.

---

## Requirements (R)

| ID | Requirement | Status |
|----|-------------|--------|
| R0 | Deliver a public open-source demo in a weekend timeframe. | Core goal |
| R0.1 | Repository is public and contains setup instructions for local run. | Must-have |
| R0.2 | A live demo URL is available for reviewers. | Must-have |
| R1 | Produce an actionable decision brief workflow from source ingestion through publish. | Core goal |
| R1.1 | Workflow is Sources -> Draft -> Report. | Must-have |
| R1.2 | Human can review and edit before publish. | Must-have |
| R1.3 | Decision brief includes ranked recommendations with owner, next step, and ETA. | Must-have |
| R2 | Ingest the required product signals. | Must-have |
| R2.1 | Pull metrics from Amplitude. | Must-have |
| R2.2 | 🟡 Pull feedback from Typeform Responses API using `response_type=completed` and date/cursor pagination. | Must-have |
| R2.3 | 🟡 Pull iOS release metadata from Apple Lookup API and merge release-note narrative from curated Markdown. | Must-have |
| R2.4 | Show per-source ingest status and timestamp. | Must-have |
| R2.5 | 🟡 Account for delayed Typeform availability of very recent responses in ingest status messaging. | Must-have |
| R3 | Make claims traceable and synthesis grounded in context. | Must-have |
| R3.1 | Product context document is read during synthesis. | Must-have |
| R3.2 | Each claim/recommendation links to evidence snippets or source references. | Must-have |
| R3.3 | Debugger shows normalized intermediate data. | Must-have |
| R3.4 | Debugger shows the prompt/context snapshot used for the run. | Must-have |
| R3.5 | Debugger provides source-level error visibility and retry controls. | Must-have |
| R4 | Slack output is faithful between preview and publish. | Must-have |
| R4.1 | Preview uses the same Block Kit structure as final payload. | Must-have |
| R4.2 | 🟡 User can publish to Slack; dynamic channel selection at publish-time requires Web API (`chat.postMessage`) rather than Incoming Webhooks. | Must-have |
| R5 | System satisfies agent-native architecture constraints. | Must-have |
| R5.1 | Every UI action has an equivalent agent tool. | Must-have |
| R5.2 | Agent sees the same source snapshots, context docs, and run history as user. | Must-have |
| R5.3 | Drafts, edits, evidence, and final report share one artifact model. | Must-have |
| R5.4 | Tool layer exposes primitives; reasoning remains in the agent. | Must-have |
| R5.5 | Runtime prompt injects source inventory, capability map, vocabulary, and recent run state. | Must-have |
| R6 | MVP implementation constraints are respected. | Must-have |
| R6.1 | Stack is Google ADK (Python) plus Gemini 3 Flash. | Must-have |
| R6.2 | 🟡 API keys/tokens are managed through `.env` for MVP (Amplitude key/secret, Typeform token, Slack credential, Gemini key). | Must-have |
| R6.3 | Scope favors minimal implementation over extensibility. | Must-have |
| R6.4 | 🟡 If MVP uses Incoming Webhooks, posting target is preconfigured; channel picker is explicitly out of MVP unless bot-token path is added. | Must-have |
| R7 | UX is simple, intentional, and high quality for desktop/laptop. | Undecided |
| R7.1 | UI presents a clear 3-column layout (Sources, Draft, Report). | Must-have |
| R7.2 | Debugger is available via tab/drawer without interrupting draft/report flow. | Must-have |
| R7.3 | Visual quality bar is met (not cluttered, not enterprise-heavy). | Undecided |
| R8 | Shape B should preserve seams for a future conversational Slack analyst mode. | Nice-to-have |
| R8.1 | Architecture can add Slack thread Q&A using the same evidence/context primitives. | Nice-to-have |

---

## Context7 Validation Pass (2026-03-02)

| API | Validation Finding | Impact on Draft 4 |
|-----|--------------------|-------------------|
| Amplitude Dashboard REST | `chart` retrieval is documented with Basic auth and chart CSV endpoint; query/segmentation/export APIs are documented under dashboard/export families. | 🟡 Keep Amplitude in MVP, but keep mechanism explicit and Basic-auth based. |
| Typeform Responses API | Supports `page_size` up to 1000, `since`/`until`, `after`/`before`; `completed` boolean is deprecated in favor of `response_type`. | 🟡 Tighten ingest requirements and tool behavior around `response_type=completed` and pagination. |
| Slack Block Kit + Publish | Block Kit limits apply (for example message block count), and Incoming Webhooks are tied to configured destination while Web API supports explicit channel targeting. | 🟡 Clarify requirement language so channel-picker behavior is not implied for webhook-only MVP. |
| Apple release source | Existing baseline usage relies on Apple Lookup API for latest live metadata and local Markdown for narrative release notes. | 🟡 Reword iOS source requirement to reflect Lookup+Markdown MVP mechanism. |

**References**
- [Amplitude Dashboard REST API](https://amplitude.com/docs/apis/analytics/dashboard-rest)
- [Typeform Retrieve responses](https://www.typeform.com/developers/responses/reference/retrieve-responses/)
- [Slack Incoming webhooks](https://api.slack.com/messaging/webhooks)
- [Slack Block Kit blocks reference](https://docs.slack.dev/reference/block-kit/blocks)
- [Apple iTunes Search API (Lookup)](https://performance-partners.apple.com/resources/documentation/itunes-store-web-service-search-api/)

## CURRENT: Fragmented Manual Workflow

| Part | Mechanism | Flag |
|------|-----------|:----:|
| CURRENT1 | PM pulls metrics, feedback, and release notes from separate tools by hand. | |
| CURRENT2 | Synthesis happens in ad hoc docs/chats without shared source snapshots. | |
| CURRENT3 | Slack updates are manually written and manually formatted. | |
| CURRENT4 | Claim-to-evidence trace is not first-class; trust depends on manual spot checks. | |
| CURRENT5 | No debugger view for ingest state, transforms, or prompt context. | |

## B: Review-First Reporter (Selected)

| Part | Mechanism | Flag |
|------|-----------|:----:|
| **B1** | **Source ingestion and snapshot store** | |
| B1.1 | `fetch_amplitude` pulls metrics and stores a run-scoped normalized snapshot. | |
| B1.2 | 🟡 `fetch_typeform` uses `response_type=completed` and date/cursor pagination, then stores a run-scoped normalized snapshot. | |
| B1.3 | 🟡 `read_release_notes_file` plus `fetch_itunes_lookup_metadata` merge narrative notes with latest live version/build metadata. | |
| B1.4 | `list_sources` and `get_source_status` expose status and timestamp for each source. | |
| **B2** | **Context grounding** | |
| B2.1 | `read_product_context` loads product context into the synthesis run context. | |
| **B3** | **Decision brief synthesis** | |
| B3.1 | `write_report_draft` generates the six-section decision brief from normalized inputs. | |
| B3.2 | Brief includes hypotheses with confidence and ranked recommendations with owner, next step, and ETA. | |
| B3.3 | Evidence appendix stores claim -> evidence mapping for each recommendation. | |
| **B4** | **Shared artifact model** | |
| B4.1 | Draft, user edits, evidence links, Block Kit payload, and publish metadata share one report artifact. | |
| B4.2 | `update_report_section` applies user edits directly to the shared report artifact. | |
| **B5** | **Review-first interface** | |
| B5.1 | Desktop/laptop 3-column layout exposes Sources, Draft workbench, and Report preview/publish controls. | |
| B5.2 | Sources column surfaces source freshness and ingest failures. | |
| **B6** | **Slack render and publish path** | |
| B6.1 | `render_blockkit_preview` and `post_slack_message` use the same serializer to prevent preview/publish drift. | |
| B6.2 | 🟡 Publish is explicit user action after review and uses one configured Slack destination in webhook mode. | |
| B6.3 | 🟡 Optional future publish mode: `chat.postMessage` path for explicit channel selection when bot token/scopes are present. | |
| **B7** | **Debugger** | |
| B7.1 | `get_pipeline_trace` shows ingest -> normalize -> synthesize -> render steps for the run. | |
| B7.2 | `get_evidence_for_claim` opens claim-level provenance and normalized source snippets. | |
| B7.3 | Debugger includes prompt/context snapshot and source-level retry controls. | |
| **B8** | **Agent-native parity and runtime context injection** | |
| B8.1 | Capability map enforces one tool equivalent per user action. | |
| B8.2 | Runtime context injection includes source inventory, capability map, vocabulary, and recent run state. | |
| **B9** | **Packaging and demo distribution** | |
| B9.1 | Public repository includes setup docs and `.env` template for keys. | |
| B9.2 | Deploy a demo URL that runs the review-first flow end to end. | |

## C: Conversational Slack Analyst (Follow-on)

| Part | Mechanism | Flag |
|------|-----------|:----:|
| C1 | Subscribe to Slack thread events and map each thread to a report artifact. | ⚠️ |
| C2 | `answer_thread_question` retrieves report evidence/context and responds in-thread with citations. | ⚠️ |
| C3 | Add citation-only and uncertainty fallback policies for low-confidence answers. | ⚠️ |
| C4 | Persist thread Q&A transcript in the same shared artifact for audit/debugging. | ⚠️ |

---

## Fit Check (Selected Shape): R x B

| Req | Requirement | Status | B |
|-----|-------------|--------|---|
| R0 | Deliver a public open-source demo in a weekend timeframe. | Core goal | ✅ |
| R1 | Produce an actionable decision brief workflow from source ingestion through publish. | Core goal | ✅ |
| R2 | Ingest the required product signals. | Must-have | ✅ |
| R3 | Make claims traceable and synthesis grounded in context. | Must-have | ✅ |
| R4 | Slack output is faithful between preview and publish. | Must-have | ✅ |
| R5 | System satisfies agent-native architecture constraints. | Must-have | ✅ |
| R6 | MVP implementation constraints are respected. | Must-have | ✅ |
| R7 | UX is simple, intentional, and high quality for desktop/laptop. | Undecided | ❌ |
| R8 | Shape B should preserve seams for a future conversational Slack analyst mode. | Nice-to-have | ✅ |

**Notes:**
- R7 fails: quality bar is subjective right now and has no explicit acceptance rubric.

## Unsolved Summary (Selected Shape B)

- Undecided requirements: R7, R7.3.
- Fit-check failures: R7.
- Needed to close R7: add a concrete UX acceptance rubric (layout, typography, spacing, visual hierarchy, and mobile/desktop checks).

---

## Detail B: Capability Map (Action Parity)

| UI Action | Agent Tool Equivalent | In B |
|---|---|---|
| Load sources list/status | `list_sources`, `get_source_status` | ✅ |
| Fetch latest source data | 🟡 `fetch_amplitude`, `fetch_typeform`, `read_release_notes_file`, `fetch_itunes_lookup_metadata` | ✅ |
| Read product context | `read_product_context` | ✅ |
| Generate draft | `write_report_draft` | ✅ |
| Edit draft section | `update_report_section` | ✅ |
| Render Slack preview | `render_blockkit_preview` | ✅ |
| Publish to Slack | 🟡 `post_slack_message` (webhook mode, fixed destination) or `post_slack_message_to_channel` (bot-token mode) | ✅ |
| Open debugger trace | `get_pipeline_trace`, `get_evidence_for_claim` | ✅ |
| Ask report follow-up in Slack thread | `answer_thread_question` | ❌ (Shape C) |

## Detail B: Breadboard (Starter)

### UI Affordances

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| U1 Sources Panel | Web App: Left Column | Shows source list, freshness, and errors. | N1, N2 |
| U2 Refresh Source Button | Web App: Left Column | Re-fetch one source on demand. | N2 |
| U3 Draft Workbench | Web App: Center Column | Displays and edits decision brief sections. | N4, N5 |
| U4 Report Preview | Web App: Right Column | Renders Slack Block Kit preview. | N6 |
| U5 Publish Button | Web App: Right Column | Publishes reviewed report to Slack. | N7 |
| U6 Debugger Toggle | Web App: Global Header | Opens debugger drawer/tab for current run. | N8 |
| U7 Claim Evidence Inspector | Debugger Drawer | Shows claim -> evidence provenance. | N9 |

### Non-UI Affordances

| Affordance | Place | Purpose | Wires Out |
|------------|-------|---------|-----------|
| N1 Source Snapshot Store | Backend | Stores normalized source snapshots per run. | N4, N8 |
| N2 Source Fetch Orchestrator | Backend Tools | Executes source adapters and updates status/timestamps. | N1, N3 |
| N3 Source Status Index | Backend | Tracks ingest status and retry metadata by source. | U1 |
| N4 Synthesis Engine | Backend Agent | Builds draft sections and hypotheses from snapshots and context. | N5, N6 |
| N5 Shared Report Artifact | Backend | Persists draft, edits, evidence map, and publish metadata. | U3, N6, N7, N9 |
| N6 Block Kit Renderer | Backend | Converts report artifact into Slack Block Kit payload. | U4, N7 |
| N7 Slack Publisher | 🟡 Backend Tools | Posts final payload via webhook (fixed destination) or Web API (explicit channel). | N5 |
| N8 Pipeline Trace Log | Backend | Captures run trace and prompt/context snapshot. | U6 |
| N9 Evidence Resolver | Backend | Resolves evidence links/snippets for each claim. | U7 |

### Wiring by Place

| Place | Wiring |
|-------|--------|
| Web App | U1 -> N1/N2; U2 -> N2; U3 -> N4/N5; U4 <- N6; U5 -> N7; U6 -> N8; U7 -> N9 |
| Backend Agent | N4 consumes N1 plus product context, then writes N5 and calls N6 |
| Backend Tools | N2 writes N1/N3; N7 posts Slack from N6 output; N9 reads N5 and source snapshots |
| Debugger | U6/U7 read N8/N9 tied to current report artifact in N5 |
