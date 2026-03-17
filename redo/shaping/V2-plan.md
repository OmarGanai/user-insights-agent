---
shaping: true
title: Vector - V2 Plan
status: completed
slice: V2
source_slices_doc: redo/shaping/vector-slices-final.md
---

# Vector - V2 Plan

## Goal

Replace mock source status with real ingestion pipelines and normalized snapshot/status storage while preserving the V1 UX shell.

## Scope In

- Source adapters for Amplitude, Typeform (`response_type=completed`), iOS Lookup + release markdown
- Per-source status/timestamp/error index
- Manual source refresh action from Sources panel
- Snapshot persistence per run and source inventory exposure

## Scope Out

- LLM-generated draft content
- Claim-level evidence resolution
- Real Slack publishing

## Implementation Checklist

- [x] Define normalized source snapshot schema and status index schema.
- [x] Implement `fetch_amplitude` adapter with documented auth/payload handling.
- [x] Implement `fetch_typeform` adapter with date/cursor pagination and delayed-response awareness messaging.
- [x] Implement iOS release source merge (`read_release_notes_file` + `fetch_itunes_lookup_metadata`).
- [x] Implement orchestrator endpoint/tool for full and per-source refresh.
- [x] Wire Sources panel refresh control to live refresh action.
- [x] Show source freshness and error states in UI from live status index.
- [x] Add integration tests for each adapter and status transition behavior.

## Verification

- [x] A full ingest run creates snapshots for all required sources.
- [x] Refreshing one source updates only that source status/timestamp.
- [x] Error from one source does not block status visibility for others.
- [x] Typeform very-recent-data caveat is visible when applicable.

## Demo Script

1. Run full ingest and inspect source statuses in left panel.
2. Trigger refresh for one source and observe syncing -> synced transition.
3. Simulate one source failure and verify visible stale/error messaging.
4. Confirm latest snapshot inventory is available for downstream synthesis.

## Exit Criteria

- V2 closes B1/B2 mechanics with live source ingestion and visible source-level observability.
