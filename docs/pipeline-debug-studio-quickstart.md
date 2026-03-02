# Pipeline Debug Studio Quickstart

Use this whenever you want to quickly run the local debug UI.

## Start Fresh

```bash
pkill -f "scripts/debug_pipeline_ui.py" || true
python3 /Users/omarganai/Coding/amplitude-insights-bot/scripts/debug_pipeline_ui.py --host 127.0.0.1 --port 8787
```

## Open in Browser

- `http://127.0.0.1:8787/?v=1`

Use a hard refresh (`Cmd+Shift+R`) if the UI looks stale.

## Quick Health Check

In another terminal:

```bash
curl -sS http://127.0.0.1:8787/api/defaults
```

If it returns JSON, the server is running correctly.

## If Button Clicks Do Nothing

1. Stop the server (`Ctrl+C` where it is running).
2. Re-run the **Start Fresh** commands above.
3. Hard refresh the browser.
