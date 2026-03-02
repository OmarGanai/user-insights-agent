# Contributing

## Development Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Test Policy
Use deterministic tests as the default local/CI gate.

Run the deterministic baseline:
```bash
python3 -m unittest tests.test_agent_runtime tests.test_public_safety_scan
```

Run the full deterministic suite (excluding live Amplitude contract):
```bash
python3 - <<'PY'
import pathlib
import subprocess
import sys

excluded = {"test_amplitude_live_chart_contract.py"}
modules = [
    f"tests.{path.stem}"
    for path in sorted(pathlib.Path("tests").glob("test_*.py"))
    if path.name not in excluded
]
subprocess.check_call([sys.executable, "-m", "unittest", *modules])
PY
```

Live integration test (opt-in only; requires credentials):
```bash
python3 -m unittest tests.test_amplitude_live_chart_contract
```

## Public-Safety Gate
Before opening a PR, run:
```bash
python3 scripts/public_safety_scan.py --root .
```

This scan fails if:
1. banned tenant identifiers are found in tracked sources
2. runtime artifacts under `tmp/` or `workspace/` are tracked by git

## Approval-Gated Side Effects
Slack posting is side-effectful and must remain approval-gated through runtime approval tools.

When changing runtime/tooling behavior:
1. preserve `post_slack_payload` approval checks
2. add tests for approval lifecycle or policy changes
3. avoid direct side-effect calls in deterministic tests

## Documentation Expectations
When behavior changes, update the corresponding docs in:
1. `README.md` for operator-facing usage
2. `docs/` for contracts/plans and migration notes
3. `agent-native-rebuild.md` for cutover scope and status
