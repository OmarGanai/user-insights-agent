# Temporal Memory Contract

File path:

- `tmp/weekly-report-memory.json`

Schema (`schema_version=1`):

- `schema_version` (int)
- `last_updated_utc` (UTC timestamp)
- `latest_report` (object or null)
- `previous_report` (object or null)

`latest_report` / `previous_report` fields:

- `generated_at_utc`
- `headline`
- `kpi_status`
- `key_changes` (list)
- `possible_explanations` (list)
- `suggested_actions` (list)
- `core_metrics_snapshot` (list of metric evidence objects)

Update behavior:

- Idempotent writes: if a new snapshot is identical to `latest_report`, file is not rewritten.
- Rotation behavior: when changed, current `latest_report` moves to `previous_report` and new snapshot becomes `latest_report`.
- Failures to read/write memory must not block report publishing.
