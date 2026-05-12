# Sanitized replay fixtures

This directory stores sanitized real-world Duco payloads for replay-based
compatibility tests.

Only sanitized fixtures belong in version control. Use `raw/` as a local staging
area when you need to prepare new samples before sanitizing them. Git ignores
everything inside `raw/` except its `.gitignore` placeholder.

## Layout

- Store publishable fixtures under `sanitized/<profile>/`.
- Use a stable profile slug, such as `silent-connect-v25`, for each device or
  firmware family you want to replay.
- Group fixtures by HTTP method first, then by API-relative path segments.
- Use `__base__.json` for requests without query parameters.
- Use a filename such as `module=General;submodule=Board.json` when query
  parameters are present.
- Sort query parameters by key before building the file name.
- URL-encode query keys and values when they contain characters that would make
  the file name ambiguous.

## Examples

- `sanitized/silent-connect-v25/GET/api/__base__.json`
- `sanitized/silent-connect-v25/GET/info/module=General;submodule=Board.json`
- `sanitized/silent-connect-v25/GET/info/nodes/__base__.json`

## Replay helpers

The shared helpers live in `tests/helpers/replay.py`.

These helpers are meant to be imported by tests. You do not need to run
`tests/helpers/replay.py` directly.

They are used to:

- discover available sanitized replay profiles
- resolve deterministic fixture paths
- load one sanitized fixture
- load a full sanitized fixture set for a profile

## Run the replay helper tests

If you want to run the replay-related tests locally, first activate the
repository virtual environment.

```bash
cd /Users/ronald/SynologyDrive/Projecten/HomeAssistant/python-duco-connectivity
source .venv/bin/activate
```

Then run the focused replay helper tests:

```bash
pytest tests/test_replay_helpers.py
```

If you want to run the full test suite instead:

```bash
pytest
```

## Working with new fixture samples

1. Collect raw payloads locally in `tests/fixtures/replay/raw/`.
2. Sanitize all installation-specific or sensitive values before committing
  anything.
3. Move the publishable sanitized payloads into
  `tests/fixtures/replay/sanitized/<profile>/`.
4. Keep the path and filename layout deterministic so the replay helpers can
  find the fixtures reliably.

Only sanitized fixtures may be committed to the repository.