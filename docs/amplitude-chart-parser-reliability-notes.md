# Amplitude Chart Parser Reliability Notes (PR3)

Last updated: 2026-02-20

Purpose:
- Document parser assumptions used for reliability annotations.
- Keep assumptions aligned with official Amplitude chart API response examples.

Official references:
- Dashboard REST API overview and chart query examples:
  - https://developers.amplitude.com/docs/dashboard-rest-api

Observed documented response shapes used by parser:
1. Funnel comparison payloads
- `data[].cumulativeRaw` for base/converted counts.
- `data[].dayFunnels.series` with optional `dayFunnels.xValues` for interval-based data.

2. Events/segmentation payloads
- `data.series[].values` for period values.
- `data.xValues` for period labels.
- JSON time-series payloads may also provide `xValuesForTimeSeries`.

3. Retention payloads
- `data.series[].values[].incomplete` can flag incomplete buckets.

Parser alignment in code:
- Base/converted reliability counts come from funnel `current_start_count` and `current_end_count` when present.
- Incomplete-bucket detection checks:
  - explicit retention `incomplete` flags,
  - funnel `dayFunnels.isComplete` when available,
  - fallback inference from latest `xValues` recency.
- Low-volume caution is triggered from chart counts/values and lowers confidence labels.

Deliberate safeguards:
- Undocumented fields are treated as optional hints only.
- Missing base/converted counts degrade confidence to `medium` instead of fabricating counts.
- Reliability signals are additive and transparent (`notes` array in summary payload).
