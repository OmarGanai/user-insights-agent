# Vector

Vector is a review-first product reporting app with a 3-column workflow:

- Sources panel (left)
- Draft workbench (center)
- Slack preview + publish panel (right)

Current implementation target is **V4** from:

- `redo/shaping/shaping-final.md`
- `redo/shaping/vector-slices-final.md`
- `redo/shaping/V4-plan.md`

## What V4 Adds

- Canonical Block Kit serializer (`renderBlockkitPreview`) used by both preview and publish
- Real webhook publish endpoint (`post_slack_message`) with timeout + response error handling
- Publish metadata persistence on the shared report artifact:
  - destination label
  - attempt timestamp
  - success/failure state
  - error text and HTTP status when available
- UI visibility for publish metadata in Sources, Draft, and Publish panels

## API Endpoints (V4)

- `GET /api/report-artifact`
- `PATCH /api/report-artifact/sections/:sectionId`
- `GET /api/report-artifact/preview`
- `POST /api/report-artifact/publish`

## Local Development

```bash
cd /Users/omarganai/Coding/user-insights-agent
pnpm install
cp .env.example .env
pnpm dev
```

Open:

- `http://localhost:3000`

## Environment

Required for real Slack publish:

- `SLACK_WEBHOOK_URL`
- `SLACK_CHANNEL` (label shown in UI metadata)

If `SLACK_WEBHOOK_URL` is missing, publish calls fail safely and surface the error in UI.

### Optional Future Mode (Not MVP)

Bot-token publish mode (`chat.postMessage`) is intentionally deferred. See `.env.example` placeholders:

- `SLACK_BOT_TOKEN`
- `SLACK_DEFAULT_CHANNEL_ID`

## End-to-End Payload Equivalence Check

Start the app, then run:

```bash
pnpm test:e2e:payload-equivalence
```

This script compares:

1. Payload returned by `GET /api/report-artifact/preview`
2. Payload used by `POST /api/report-artifact/publish` in dry-run mode

and fails if they differ.

## Legacy Agent Archive

The previous Python-based runtime is archived under:

- `archive/legacy-agent/`
