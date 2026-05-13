# Sanitized replay fixtures

This directory stores sanitized real-world Duco payloads for replay-based
compatibility tests.

Only sanitized fixtures belong in version control. Use `raw/` as a local staging
area when you need to prepare new samples before sanitizing them. Git ignores
everything inside `raw/` except its `.gitignore` placeholder.

Raw installation data must never be committed, even temporarily.

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

## Minimum sanitization requirements

Before you open a pull request, replace or redact any value that can identify a
real installation or expose a secret.

At minimum, sanitize these categories when they appear:

- serial numbers and hardware identifiers such as `SerialBoardBox`,
  `SerialBoardComm`, and `SerialDucoComm`
- network identifiers such as IP addresses, Wi-Fi SSIDs, hostnames, MAC
  addresses, and similar LAN details
- human-entered names or labels such as zone names, room names, and device
  names
- credentials or secrets such as passwords, tokens, keys, or other values that
  would grant access outside the repository

Prefer replacing values over removing keys so the payload shape, value types,
and endpoint coverage stay representative of the real response.

Examples from the current sanitized fixtures:

- replace a real static IP with a documentation-safe address such as
  `192.0.2.94`
- replace a real Wi-Fi SSID with a generic value such as `duco-test-net`
- replace real serial numbers with stable placeholders such as `RS0000000001`

Keep numeric IDs when tests need them to preserve request routing or
cross-references between payloads, but replace free-form text that identifies a
person, home, or room.

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
2. Create or update a publishable profile under
  `tests/fixtures/replay/sanitized/<profile>/`.
3. Copy the raw payloads into the sanitized profile and redact or replace every
  installation-specific or secret value before staging anything in Git.
4. Keep the request path, query-derived file names, and JSON structure stable so
  the replay helpers can still resolve the fixtures deterministically.
5. Review the sanitized diff before committing to confirm that no raw hostnames,
  addresses, labels, serials, or secrets remain.
6. Run `pytest tests/test_replay_helpers.py` and any replay-based tests that use
  the new profile.

## Recommended workflow

Use this lightweight workflow when preparing samples for contribution:

1. Capture the raw responses locally into `raw/`.
2. Decide on a stable profile slug such as `silent-connect-v25` for the device
  or firmware family represented by the sample.
3. Copy the raw files into `sanitized/<profile>/` using the deterministic method
  and endpoint layout described above.
4. Replace sensitive values with stable placeholders that preserve the original
  type and general format.
5. Check related payloads together so shared identifiers stay internally
  consistent after sanitization.
6. Run the replay helper tests and inspect `git diff` before opening the PR.

Only sanitized fixtures may be committed to the repository.
