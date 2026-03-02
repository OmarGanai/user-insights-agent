# User Insights Agent

Weekly metrics analysis bot that combines:
- Amplitude chart data
- Typeform feedback snippets

Then sends an AI-generated summary to Slack.

Agent-native runtime components now also exist in:
- `agent_runtime/` (tenant-scoped session/task/artifact/approval runtime + tool registry)
- `scripts/agent_runtime_api.py` (local API surface for session/approval/capability/artifact endpoints)
- `scripts/public_safety_scan.py` (tenant-identifier and runtime-artifact safety checks)

## What It Does

1. Queries configured Amplitude charts.
2. Pulls recent Typeform responses (optional).
   - Includes text/choice answers only (email fields are excluded).
3. Uses Gemini to generate:
   - key metric changes
   - possible explanations
   - suggested actions
   - pipeline note when fallback model is used
4. Posts a structured weekly digest to `#user-insights` via Slack webhook.

## Setup

```bash
cd /Users/omarganai/Coding/user-insights-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` values.

Chart contract + cutover:
- `REPORT_CHART_SET=legacy|activation_v1` (default `activation_v1`)
- Canonical metric mapping: `docs/metric-dictionary.yaml`
- Use `legacy` only as rollback when needed.

PR2 context artifacts:
- Split context files:
  - `docs/context/base-app-context.md`
  - `docs/context/activation-weekly-context.md`
- iOS release ingestion log:
  - `docs/ios-releases.md`
- Temporal memory contract:
  - `docs/temporal-memory-contract.md`
  - Runtime memory file: `tmp/weekly-report-memory.json`

Gemini model behavior:
- Default model: `gemini-3-flash-preview`
- Optional Pro model when paid quota is enabled: `gemini-3.1-pro-preview` (or `gemini-3-pro-preview`)
- Automatic fallback model: `gemini-3-flash-preview`
- If fallback is used, the report includes an explicit pipeline note in `Insights & Next Steps`.

## Local Usage

Dry run (no Slack post):

```bash
python main.py --dry-run
```

Temporarily skip Gemini analysis (useful during quota/rate-limit windows):

```bash
python main.py --dry-run --skip-ai
```

You can also set `SKIP_AI_ANALYSIS=true` in `.env` to make this the default behavior.

Dry run now returns Slack preview sections in this order:
- Executive Summary
- Key Metrics
- Insights & Next Steps

Live chart contract verification (direct Amplitude API; opt-in):

```bash
python3 -m unittest tests.test_amplitude_live_chart_contract
```

This validates dictionary metadata against live chart query payloads:
- chart type shape (`funnel` vs `retention`)
- weekly bucket spacing
- funnel previous-period comparison when configured by dictionary standard

Run for specific chart IDs:

```bash
python main.py --dry-run --chart-id oys29da5 --chart-id rviqohkp
```

Write per-stage debug artifacts locally (no Slack post):

```bash
python scripts/local_debug_pipeline.py --chart-id oys29da5 --lookback-days 1
```

This writes:
- `tmp/pipeline-debug/01_amplitude_query_charts.json`
- `tmp/pipeline-debug/02_typeform_feedback.json`
- `tmp/pipeline-debug/03_ai_analysis.json`
- `tmp/pipeline-debug/04_slack_payload_preview.json`

Skip the AI call while still verifying upstream/downstream pipeline wiring:

```bash
python scripts/local_debug_pipeline.py --skip-ai
```

Run a local browser UI to execute the pipeline and inspect each stage JSON:

```bash
python scripts/debug_pipeline_ui.py --host 127.0.0.1 --port 8787
```

Then open:
- `http://127.0.0.1:8787`

Debug UI Slack workflow:
- Run pipeline in the UI to load the generated Slack payload JSON.
- Review/edit payload in the built-in JSON editor.
- Open Slack Block Kit Builder (`https://app.slack.com/block-kit-builder/`) and paste payload for Slack-accurate rendering.
- Post the edited payload directly from the UI using `Post Edited Payload To Slack`.

Run the agent-runtime API locally:

```bash
python scripts/agent_runtime_api.py --host 127.0.0.1 --port 8788
```

Then open the Agent Console:

- `http://127.0.0.1:8788`

Prompt-profile rollout APIs (example):

```bash
curl -sS http://127.0.0.1:8788/v1/tenants/tenant-default/prompt-profiles/default/rollout
```

```bash
curl -sS -X POST http://127.0.0.1:8788/v1/tenants/tenant-default/prompt-profiles/default/rollout \
  -H "Content-Type: application/json" \
  -d '{
    "stable_version": "v1",
    "versions": {
      "v1": {"path": "default.md"},
      "v2": {"path": "default_v2.md"}
    },
    "canary": {"enabled": true, "version": "v2", "percent": 10}
  }'
```

Run public-safety scan:

```bash
python scripts/public_safety_scan.py --root .
```

## GitHub Actions

Workflow file: `.github/workflows/ci.yml`

Add these repository secrets:
- `AMPLITUDE_API_KEY`
- `AMPLITUDE_SECRET_KEY`
- `GEMINI_API_KEY`
- `SLACK_WEBHOOK_URL`
- `AMPLITUDE_CHART_IDS` (optional CSV)
- `TYPEFORM_TOKEN` (optional)
- `TYPEFORM_FORM_ID` (optional)
- `GEMINI_MODEL` (optional, defaults to `gemini-3-flash-preview`)
