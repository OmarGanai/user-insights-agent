#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clients.amplitude import AmplitudeClient
from clients.feedback import TypeformClient
from config import Settings
from services.feedback_themes import build_feedback_theme_summary
from services.orchestrator import run_weekly_report
from services.report_context import build_ios_release_context, load_context_sections


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run each data-pipeline stage locally and write step outputs to JSON files."
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/pipeline-debug",
        help="Directory where step output files will be written.",
    )
    parser.add_argument(
        "--chart-id",
        action="append",
        default=[],
        help="Optional chart ID override. Repeat for multiple charts.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help="Optional Typeform lookback override.",
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip Gemini analysis and emit a placeholder analysis payload.",
    )
    return parser.parse_args()


def _validate_required_for_local(settings: Settings, require_ai: bool) -> None:
    required = {
        "AMPLITUDE_API_KEY": settings.amplitude_api_key,
        "AMPLITUDE_SECRET_KEY": settings.amplitude_secret_key,
    }
    if require_ai:
        required["GEMINI_API_KEY"] = settings.gemini_api_key

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _clone_settings_with_overrides(settings: Settings, lookback_days: int) -> Settings:
    return Settings(
        amplitude_api_key=settings.amplitude_api_key,
        amplitude_secret_key=settings.amplitude_secret_key,
        amplitude_base_url=settings.amplitude_base_url,
        chart_ids=list(settings.chart_ids),
        typeform_token=settings.typeform_token,
        typeform_form_id=settings.typeform_form_id,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        slack_webhook_url=settings.slack_webhook_url,
        slack_channel=settings.slack_channel,
        lookback_days=lookback_days,
        skip_ai_analysis=settings.skip_ai_analysis,
        report_chart_set=settings.report_chart_set,
        report_app_id=settings.report_app_id,
    )


def run_local_debug_pipeline(
    settings: Settings,
    output_dir: str,
    chart_ids: Optional[List[str]] = None,
    lookback_days: Optional[int] = None,
    skip_ai: bool = False,
) -> Dict[str, Any]:
    _validate_required_for_local(settings, require_ai=not skip_ai)

    chart_id_override = chart_ids if chart_ids is not None else None
    selected_chart_ids = chart_ids or settings.chart_ids
    if not selected_chart_ids:
        raise ValueError("No chart IDs provided. Set AMPLITUDE_CHART_IDS or pass --chart-id.")

    effective_lookback_days = lookback_days if lookback_days is not None else settings.lookback_days
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Keep low-level data artifacts for debugging context.
    amplitude_client = AmplitudeClient(
        base_url=settings.amplitude_base_url,
        api_key=settings.amplitude_api_key,
        secret_key=settings.amplitude_secret_key,
    )
    feedback_client = TypeformClient(token=settings.typeform_token, form_id=settings.typeform_form_id)

    print(f"[1/4] Fetching {len(selected_chart_ids)} Amplitude chart(s)")
    chart_results = amplitude_client.query_charts(selected_chart_ids)
    _write_json(output / "01_amplitude_query_charts.json", chart_results)

    print(f"[2/4] Fetching Typeform responses for last {effective_lookback_days} day(s)")
    feedback_items = feedback_client.fetch_recent_responses(days=effective_lookback_days)
    _write_json(output / "02_typeform_feedback.json", feedback_items)
    feedback_themes = build_feedback_theme_summary(feedback_items)
    _write_json(output / "02b_typeform_feedback_themes.json", feedback_themes)
    context_sections = load_context_sections()
    _write_json(output / "02c_app_context_sections.json", context_sections)
    ios_release_context = build_ios_release_context()
    _write_json(output / "02d_ios_release_context.json", ios_release_context)

    # Use the exact production orchestration path for analysis + Slack payload parity.
    print("[3/4] Running production orchestration in dry-run mode")
    effective_settings = _clone_settings_with_overrides(settings, lookback_days=effective_lookback_days)
    orchestration = run_weekly_report(
        settings=effective_settings,
        dry_run=True,
        chart_ids=chart_id_override,
        skip_ai=skip_ai,
    )
    analysis = dict(orchestration.get("analysis") or {})
    _write_json(output / "03_ai_analysis.json", analysis)

    print("[4/4] Writing production-equivalent Slack payload preview")
    payload = dict(orchestration.get("slack_preview") or {"text": "User Insights Digest", "blocks": []})
    if settings.slack_channel:
        payload["channel"] = settings.slack_channel
    _write_json(output / "04_slack_payload_preview.json", payload)

    summary = {
        "output_dir": str(output.resolve()),
        "chart_count": int(orchestration.get("chart_count", len(selected_chart_ids))),
        "feedback_count": int(orchestration.get("feedback_count", len(feedback_items))),
        "feedback_theme_count": int(
            orchestration.get("feedback_theme_count", int(feedback_themes.get("theme_count", 0)))
        ),
        "context_source": str(context_sections.get("context_source") or "unknown"),
        "ios_release_ingestion_status": str(
            orchestration.get(
                "ios_release_ingestion_status",
                ios_release_context.get("ingestion_status") or "unknown",
            )
        ),
        "skip_ai": skip_ai,
        "analysis_meta": orchestration.get("analysis_meta", analysis.get("analysis_meta", {})),
        "production_parity_mode": True,
    }
    print(f"Done. Wrote debug artifacts to: {summary['output_dir']}")
    return summary


def main() -> None:
    args = parse_args()
    settings = Settings.load()
    skip_ai = bool(args.skip_ai or settings.skip_ai_analysis)
    selected_chart_ids = args.chart_id if args.chart_id else None
    run_local_debug_pipeline(
        settings=settings,
        output_dir=args.output_dir,
        chart_ids=selected_chart_ids,
        lookback_days=args.lookback_days,
        skip_ai=skip_ai,
    )


if __name__ == "__main__":
    main()
