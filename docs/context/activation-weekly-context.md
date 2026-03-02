# Activation Weekly Context

This file is intentionally lightweight and should be updated frequently with current activation hypotheses, releases, and known operational caveats.

## Current Focus

- Weekly activation KPI target: 40-50% (`Signup: Completed -> any high-value action within 14d`).
- Report contract: 5 core metrics + 3 supplemental diagnostics.
- Rollback safety: `REPORT_CHART_SET=legacy|activation_v1` (default `activation_v1`).

## Current Caveats

- `activation_v1` chart IDs are complete and validated.
- Treat low-volume movement cautiously and use explicit confidence wording.
- Keep Monday report timing assumptions in mind for incomplete-week effects.
