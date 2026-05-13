# Replay testing

Replay-based compatibility tests sit between synthetic unit tests and opt-in
live tests.

Use them when you have real Duco payloads from a box you do not own, or when
you want stronger confidence that typed parsing still works across multiple box
families and API variants.

## Testing strategy

This repository now uses three automated test layers:

- Synthetic unit tests use handcrafted payloads and mocked HTTP responses.
- Replay compatibility tests use sanitized real-world payloads that are replayed
  through the normal typed `DucoClient` methods.
- Live tests exercise your own Duco device locally for read paths, safe writes,
  and latency probes.

These layers complement each other:

- Synthetic tests stay fast, focused, and easy to reason about.
- Replay tests protect against real payload shape drift across Duco families.
- Live tests validate end-to-end behavior against actual hardware.

## Where shared captures fit

Raw payload exports from other installations are not a separate test category.
They are source material for replay profiles.

That makes them especially valuable here:

- Your own captures can cover a `silent-connect-v25` style profile.
- Shared captures can cover `ducobox-energy-v25` and `ducobox-focus-v25` style
  profiles.
- The same replay compatibility tests can then run against all three profiles.

That gives the repository broader real-world coverage without requiring you to
own all box variants locally.

## Profile naming

Use profile names that describe both the box family and the API generation you
are replaying.

Good examples:

- `silent-connect-v25`
- `ducobox-energy-v25`
- `ducobox-focus-v25`

If you later discover a materially different payload shape for the same box
family, add another profile instead of mutating an existing one silently.

## Raw fixture layout

Store raw input files locally under `tests/fixtures/replay/raw/<profile>/`.

The raw layout should mirror the sanitized layout so the sanitizer can process
an entire profile in one pass:

- `tests/fixtures/replay/raw/<profile>/GET/api/__base__.json`
- `tests/fixtures/replay/raw/<profile>/GET/info/module=General;submodule=Board.json`
- `tests/fixtures/replay/raw/<profile>/GET/info/nodes/__base__.json`

Git ignores everything below `tests/fixtures/replay/raw/`. Keep raw files there
only as local staging material.

## Sanitization workflow

1. Copy or export raw payloads into a profile under
   `tests/fixtures/replay/raw/<profile>/`.
2. Keep the same deterministic method/path/file layout that sanitized fixtures
   already use.
3. Run the sanitizer tool.
4. Review the generated files under `tests/fixtures/replay/sanitized/<profile>/`.
5. Commit only the sanitized output.

From the repository root:

```bash
.venv/bin/python tools/replay_sanitizer.py ducobox-energy-v25
```

The sanitizer also accepts flat export files like `ENERGY_info.json` or
`FOCUS_config_zones.json` when they are grouped in a source folder such as
`tests/fixtures/replay/raw/Energy/` or `tests/fixtures/replay/raw/Focus/`.
In that case, pass both the publishable profile slug and the raw source folder:

```bash
.venv/bin/python tools/replay_sanitizer.py ducobox-energy-v27 --raw-profile Energy
.venv/bin/python tools/replay_sanitizer.py ducobox-focus-v26 --raw-profile Focus
```

The sanitizer currently preserves API-shape and device-family information while
replacing installation-specific values such as:

- serial numbers
- IP addresses
- MAC addresses
- host names
- SSIDs
- Wi-Fi keys and similar secrets
- user-defined names for nodes, groups, or zones

The goal is to keep replay fixtures publishable while still useful for parser
and compatibility coverage.

## Review checklist for sanitized output

Before committing a new replay profile, verify that:

- product-identifying fields like `BoxName`, `BoxSubTypeName`, and
  `PublicApiVersion` still describe the right Duco family
- installation-specific identifiers are no longer present
- the file layout still matches the request being replayed
- the new profile adds useful endpoint coverage instead of duplicating an
  existing profile exactly

## Running replay tests

Run the helper and compatibility tests after adding or changing replay data:

```bash
.venv/bin/pytest tests/test_replay_helpers.py tests/test_replay_sanitizer.py
```

If the profile adds new committed request fixtures for typed readers, also run:

```bash
.venv/bin/pytest tests/test_replay_read_compatibility.py
```

The replay compatibility suite currently exercises these typed overview readers
whenever the matching fixtures are present in a committed profile:

- `GET /api`
- `GET /config`
- `GET /config/nodes`
- `GET /config/zones`
- `GET /info/nodes`
- `GET /info/zones`
- `GET /info?module=General&submodule=Board`

The current real-world multi-profile baseline is:

- `silent-connect-v26`
- `ducobox-energy-v27`
- `ducobox-focus-v26`

## When to prefer replay tests over live tests

Prefer replay tests when:

- the payload came from a device you do not own
- you want deterministic regression coverage for a previously observed payload
- the value of the test is in parsing and model compatibility, not in live box
  behavior

Prefer live tests when:

- you need to validate state changes against a real device
- timing, request budgets, or polling behavior matter
- the code path depends on hardware-side behavior that a stored payload cannot
  represent