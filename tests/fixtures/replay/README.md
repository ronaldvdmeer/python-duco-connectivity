# Replay sample fixtures

This directory stores local raw Duco payloads for replay-based sample
validation.

For the full testing rationale and local sample workflow, start with
`docs/replay-testing.md`.

The `raw/` directory is intentionally ignored by git. Keep local sample files
there when you want to validate raw captures on your own machine.

## Layout

- Use a stable profile slug, such as `silent-connect-v25`, for each device or
  firmware family you want to replay locally.
- Store local samples under `raw/<profile>/`.
- Group fixtures by HTTP method first, then by API-relative path segments.
- Use `__base__.json` for requests without query parameters.
- Use a filename such as `module=General;submodule=Board.json` when query
  parameters are present.
- Sort query parameters by key before building the file name.
- URL-encode query keys and values when they contain characters that would make
  the file name ambiguous.

## Examples

- `raw/silent-connect-v25/GET/api/__base__.json`
- `raw/silent-connect-v25/GET/info/module=General;submodule=Board.json`
- `raw/silent-connect-v25/GET/info/nodes/__base__.json`

## Replay helpers

The shared helpers live in `tests/helpers/replay.py`.

These helpers are meant to be imported by tests. You do not need to run
`tests/helpers/replay.py` directly.

They are used to:

- discover available local replay profiles
- resolve deterministic fixture paths
- load one local sample fixture
- load a full local sample fixture set for a profile

They do not try to turn every stored fixture into a publishable compatibility
contract. In this repository, replay stays intentionally narrow and focuses on
local validation of your own raw captures.

## Run the replay helper tests

If you want to run the replay-related tests locally, first activate the
repository virtual environment.

```bash
source .venv/bin/activate
```

Then run the focused replay helper tests:

```bash
pytest tests/test_replay_helpers.py
```

If you want to validate a local sample profile, run:

```bash
export DUCO_SAMPLE_PROFILE=silent-connect-v25
pytest tests/test_local_sample_validation.py
```

## Working With Local Sample Captures

1. Collect raw payloads locally in `tests/fixtures/replay/raw/<profile>/` using
   the same deterministic request layout described above.
2. Keep the files local; do not commit them.
3. Set `DUCO_SAMPLE_PROFILE=<profile>`.
4. Run `pytest tests/test_local_sample_validation.py`.
