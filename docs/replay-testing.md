# Replay testing

Replay-based sample validation sits between synthetic unit tests and opt-in
live tests.

Use it when you have real Duco payloads from a box you do not own, or when you
want a small deterministic check that known real-world samples still parse.

This layer is intentionally narrow. It is not meant to become a second full
test suite for every public client method.

## Testing strategy

This repository now uses three automated test layers:

- Synthetic unit tests use handcrafted payloads and mocked HTTP responses.
- Replay sample-validation tests use sanitized real-world payloads that are
  replayed through a small set of normal typed `DucoClient` methods.
- Live tests exercise your own Duco device locally for read paths, safe writes,
  and latency probes.

These layers complement each other:

- Synthetic tests stay fast, focused, and easy to reason about.
- Replay tests protect a few high-value parsing paths against real payload shape
  drift across Duco families.
- Live tests validate end-to-end behavior against actual hardware.

## What replay is for

Replay tests have one job in this repository: keep committed real-world samples
useful.

That means replay should answer questions like:

- Do these sanitized fixtures still load?
- Do a few core typed readers still parse them?
- Did sanitization preserve the parts of the payload shape we care about?

Replay should not try to answer every question that belongs in unit tests or
live tests.

In particular, replay is not meant to:

- cover every `async_get_*` method
- simulate write behavior
- replace live validation against a real Duco box

## Where shared captures fit

Raw payload exports from other installations are not a separate test category.
They are source material for replay profiles.

That makes them especially valuable here:

- Your own captures can cover a `silent-connect-v25` style profile.
- Shared captures can cover `ducobox-energy-v25` and `ducobox-focus-v25` style
  profiles.
- The same replay compatibility tests can then run against all three profiles.

That gives the repository broader real-world sample coverage without requiring
you to own all box variants locally.

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
and sample-validation coverage.

## Review checklist for sanitized output

Before committing a new replay profile, verify that:

- product-identifying fields like `BoxName`, `BoxSubTypeName`, and
  `PublicApiVersion` still describe the right Duco family
- installation-specific identifiers are no longer present
- the file layout still matches the request being replayed
- the new profile adds useful endpoint coverage instead of duplicating an
  existing profile exactly

## Running replay tests

Run the helper and sample-validation tests after adding or changing replay data:

```bash
.venv/bin/pytest tests/test_replay_helpers.py tests/test_replay_sanitizer.py
```

If the profile adds or changes committed request fixtures for the core replay
readers, also run:

```bash
.venv/bin/pytest tests/test_replay_read_compatibility.py
```

The replay suite intentionally exercises only a small set of high-value typed
overview readers:

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
- the value of the test is in parsing a known sample, not in live box behavior

Prefer live tests when:

- you need to validate state changes against a real device
- timing, request budgets, or polling behavior matter
- the code path depends on hardware-side behavior that a stored payload cannot
  represent

## Scope rule

Before adding replay coverage for a new endpoint, first ask whether the sample
would add clear value beyond the existing unit tests and live tests.

If the answer is mainly “more coverage would be nice,” prefer not to add it.
Keep replay small enough that fixture maintenance stays cheap and the purpose of
the suite stays obvious.