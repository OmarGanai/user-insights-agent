# Vector

Vector is a review-first product reporting app.

Current implementation target is **V1** from:
- `redo/shaping/shaping-final.md`
- `redo/shaping/vector-slices-final.md`
- `redo/shaping/V1-plan.md`

V1 scope:
- 3-column desktop shell (`Sources`, `Draft`, `Publish`)
- Inline draft editing with `Save` / `Cancel`
- Slack-style preview + simulated publish states
- Debugger drawer with Pipeline/Prompt tabs
- Shared in-memory artifact wiring between draft and preview

## Legacy Agent Archive

The previous Python-based agent runtime has been hard-archived to:

- `archive/legacy-agent/`

This includes previous root services, clients, scripts, tests, docs, and runtime assets.

## Local Development

```bash
cd /Users/omarganai/Coding/user-insights-agent
pnpm install
pnpm dev
```

Open:
- `http://localhost:3000`

## Environment

Copy the template and adjust values as needed:

```bash
cp .env.example .env
```

V1 is mock-backed, so no provider credentials are required for the current shell flow.

## Notes

- The UI baseline is promoted from `redo/shaping/vercel/` and is now the main root app.
- V2+ will wire real ingestion, synthesis, evidence trace, and Slack publish against the same shell.
