---
shaping: true
title: Vector - V1 Plan
status: draft
slice: V1
source_slices_doc: redo/shaping/vector-slices-draft-1.md
---

# Vector - V1 Plan

## Goal

Ship the interactive review shell (Sources / Draft / Publish + Debugger) with mock-backed state so the core UX loop is demo-able end to end.

## Scope In

- 3-column desktop layout with collapse rails
- Draft section inline editing with Save/Cancel
- Slack preview toggle and simulated publish states
- Debugger drawer toggle with Pipeline/Prompt tabs
- In-memory shared artifact wiring between Draft and Preview

## Scope Out

- Live ingestion APIs (Amplitude/Typeform/iOS)
- LLM synthesis
- Real Slack publishing
- Persisted backend artifact storage

## Implementation Checklist

- [ ] Port or align shell layout from `redo/shaping/vercel/app/page.tsx` into the main app surface.
- [ ] Implement left panel open/collapse behavior with icon rail tooltips.
- [ ] Implement draft workbench editing loop (`idle -> editing -> saved/canceled`) using local state.
- [ ] Wire draft artifact state so preview reflects edits immediately.
- [ ] Implement right panel ready/preview modes and simulated publish state progression.
- [ ] Implement debugger footer toggle + drawer tabs using mock pipeline/prompt data.
- [ ] Run R7 rubric subset for V1 surfaces (layout, hierarchy, interaction clarity).

## Verification

- [ ] At 1280x800 and 1440x900, center column is visually dominant and no horizontal scroll appears.
- [ ] Editing a section updates preview content without reload.
- [ ] Collapsed rails can reopen both side panels.
- [ ] Debugger opens/closes without blocking center workflow.

## Demo Script

1. Load the app and collapse/reopen both side columns.
2. Edit one draft section and save.
3. Open Slack preview and verify updated content.
4. Click publish and observe sending/sent states.
5. Open debugger and switch between Pipeline and Prompt tabs.

## Exit Criteria

- V1 delivers a complete, interactive UI loop with mock data and satisfies V1 demo checks from `vector-slices-draft-1.md`.
