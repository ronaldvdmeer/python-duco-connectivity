# Local live testing

Use the live test suite when you want to validate the client against your own
Duco box on your own network.

These tests are intentionally local-only:

- they are skipped unless you opt in explicitly
- they are not part of the default mock-based test workflow
- write tests stay behind a second explicit flag

## Prerequisites

- A Duco device that is reachable from the machine running the tests
- A local development environment with the project dev dependencies installed
- Sufficient Duco write budget before running the safe-write test

From the repository root, use any activated virtual environment you prefer. The
commands below use a local `.venv` so they stay copy-pasteable from a clean
checkout. Create it first if needed, then install the development dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Environment variables

Set the host of the Duco device before running the live suite:

```bash
export DUCO_TEST_HOST=192.168.1.10
```

Optional overrides:

```bash
export DUCO_TEST_PORT=80
export DUCO_TEST_TIMEOUT=10
export DUCO_TEST_INTER_TEST_DELAY=3
export DUCO_TEST_API_BENCHMARK_SAMPLES=10
export DUCO_TEST_API_BENCHMARK_INTERVAL=1
export DUCO_TEST_VENTILATION_NODE_ID=7
export DUCO_TEST_VENTILATION_TARGET_STATES=MAN1,AUTO
export DUCO_TEST_STATE_POLL_INTERVAL=0.5
export DUCO_TEST_STATE_POLL_ATTEMPTS=10
```

If `DUCO_TEST_HOST` is not set, the live fixtures skip the suite.
By default, the live suite also waits 3 seconds after each test to avoid
hammering the Duco box. Set `DUCO_TEST_INTER_TEST_DELAY=0` if you explicitly
want to disable that throttle.

## Copy-paste quick start

Replace the placeholder values once, then run the block for the test you want.

Smoke test:

```bash
export DUCO_TEST_HOST=192.168.1.10
.venv/bin/pytest tests/live/test_smoke.py --live
```

API latency probe:

```bash
export DUCO_TEST_HOST=192.168.1.10
export DUCO_TEST_API_BENCHMARK_SAMPLES=10
export DUCO_TEST_API_BENCHMARK_INTERVAL=1
.venv/bin/pytest tests/live/test_api_latency_probe.py --live --live-performance
```

Safe write test:

```bash
export DUCO_TEST_HOST=192.168.1.10
.venv/bin/pytest tests/live/test_safe_writes.py --live --live-writes
```

Ventilation state round-trip test:

```bash
export DUCO_TEST_HOST=192.168.1.10
export DUCO_TEST_VENTILATION_NODE_ID=7
export DUCO_TEST_VENTILATION_TARGET_STATES=MAN1,AUTO
.venv/bin/pytest tests/live/test_ventilation_state_writes.py --live --live-writes
```

Whole live suite, including writes:

```bash
export DUCO_TEST_HOST=192.168.1.10
export DUCO_TEST_VENTILATION_NODE_ID=7
export DUCO_TEST_VENTILATION_TARGET_STATES=MAN1,AUTO
.venv/bin/pytest tests/live --live --live-writes --live-performance
```

## Commands

Run the read-only smoke tests:

```bash
.venv/bin/pytest tests/live/test_smoke.py --live
```

Run all live read tests in the `tests/live` folder:

```bash
.venv/bin/pytest tests/live --live
```

Run the API latency probe with the default 10 samples and 1-second interval:

```bash
.venv/bin/pytest tests/live/test_api_latency_probe.py --live --live-performance
```

Run the same API latency probe with explicit settings that are easy to tweak:

```bash
export DUCO_TEST_API_BENCHMARK_SAMPLES=10
export DUCO_TEST_API_BENCHMARK_INTERVAL=1
.venv/bin/pytest tests/live/test_api_latency_probe.py --live --live-performance
```

Run the safe write test as a separate step:

```bash
.venv/bin/pytest tests/live/test_safe_writes.py --live --live-writes
```

Run the ventilation state round-trip test:

```bash
.venv/bin/pytest tests/live/test_ventilation_state_writes.py --live --live-writes
```

Run the whole live suite, including write and performance probes:

```bash
.venv/bin/pytest tests/live --live --live-writes --live-performance
```

Without `--live`, the live tests are skipped even when the environment
variables are already set. Without `--live-writes`, the write test is skipped.
Without `--live-performance`, the latency probe is skipped. Successful live
tests also print a concise summary to the terminal so you can see what was
read, written, or measured without needing a failure to inspect captured
output.

If a live test is skipped and you want the exact reason, rerun it with `-rs`:

```bash
.venv/bin/pytest tests/live/test_ventilation_state_writes.py --live --live-writes -rs
```

The API latency probe does not enforce a hard response-time threshold. It is a
local measurement tool for your own network and box, so use it to establish a
baseline first and only add limits later if you have stable local data.

## What the automated live suite covers

The first local live suite focuses on repeatable checks with a low operational
risk:

- `GET /api`
- Repeated `GET /api` latency sampling with summary stats
- `GET /info?module=General&submodule=Board`
- `GET /info?module=General&submodule=Lan`
- `GET /info?module=Diag`
- `GET /info/nodes`
- `GET /info/zones`
- `GET /action`
- `GET /action/nodes`
- `GET /info?module=General&submodule=PublicApi`
- `PATCH /config` as a no-op `TimeZone` write to the current value
- `POST /action/nodes/{node}` round-trip writes for `SetVentilationState`

## Manual validation checklist

Keep broader state-changing scenarios manual until each one has a clear and
safe rollback story.

Suggested local checklist:

1. Run the smoke suite first and confirm the read-only endpoints behave as expected.
2. Run the API latency probe when you want a local response-time baseline.
3. Run the safe write test separately and confirm it leaves the observed value unchanged.
4. Run the ventilation state round-trip test only for a node that advertises `SetVentilationState`.
5. Inspect `async_get_node_actions()` for the target node before trying any additional manual node action.
6. Capture the current state before any manual ventilation or node write.
7. Apply a temporary change only when you know how to restore the exact prior value.
8. Restore the original value immediately and confirm the device reports it back.

## Recommended local sequence

When you are iterating on the client, this order keeps the risk low:

1. Run the normal mock-based suite
2. Run `.venv/bin/pytest tests/live/test_smoke.py --live`
3. Optionally run `.venv/bin/pytest tests/live/test_api_latency_probe.py --live --live-performance`
4. Run `.venv/bin/pytest tests/live/test_safe_writes.py --live --live-writes`
5. Run `.venv/bin/pytest tests/live/test_ventilation_state_writes.py --live --live-writes`
6. Perform any broader manual validation only after the automated checks pass
