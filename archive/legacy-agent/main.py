#!/usr/bin/env python3

import argparse

from config import Settings
from services.orchestrator import run_weekly_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run weekly Amplitude insights report.")
    parser.add_argument("--dry-run", action="store_true", help="Run analysis without posting to Slack.")
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip Gemini analysis and continue with deterministic evidence-based output.",
    )
    parser.add_argument(
        "--chart-id",
        action="append",
        default=[],
        help="Optional chart ID override. Repeat for multiple charts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.load()
    skip_ai = bool(args.skip_ai or settings.skip_ai_analysis)
    settings.validate_required(require_slack=not args.dry_run, require_ai=not skip_ai)

    selected_chart_ids = args.chart_id if args.chart_id else None
    run_weekly_report(
        settings=settings,
        dry_run=args.dry_run,
        chart_ids=selected_chart_ids,
        skip_ai=skip_ai,
    )


if __name__ == "__main__":
    main()
