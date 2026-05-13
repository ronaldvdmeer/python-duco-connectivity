# Replay testing

Replay-based local sample validation sits between synthetic unit tests and
opt-in live tests.

Use it when you have raw Duco payloads on your machine and want a small
deterministic check that selected typed readers still parse them.

This flow is intentionally local-only. The sample files stay ignored under the
repository, and there is no sanitization or publishable-fixture workflow.

## Testing strategy

This repository now uses three automated test layers:

- Synthetic unit tests use handcrafted payloads and mocked HTTP responses.
- Local sample-validation tests can replay raw API captures through a small set
  of normal typed `DucoClient` methods.
- Live tests exercise your own Duco device locally for read paths, safe writes,
  and latency probes.

These layers complement each other:

- Synthetic tests stay fast, focused, and easy to reason about.
- Local sample validation lets you spot parser breakage on real captures without
  adding those captures to version control.
- Live tests validate end-to-end behavior against actual hardware.

## What replay is for

Replay has one job in this repository: help you validate your own local raw
captures when unit tests are too synthetic and live tests are not what you need.

That means replay should answer questions like:

- Do these local raw fixtures still load?
- Do a few core typed readers still parse them?

Replay should not try to answer every question that belongs in unit tests or
live tests.

In particular, replay is not meant to:

- cover every `async_get_*` method
- simulate write behavior
- replace live validation against a real Duco box

## Local-only rule

Raw captures for this workflow stay local.

- Store them under `tests/fixtures/replay/raw/<profile>/`
- Do not commit them
- Do not sanitize them for publication

If you later want to inspect a second box family, add another local profile on
your machine. The repository does not need to carry those files.

## Profile naming

Use profile names that describe both the box family and the API generation you
are replaying.

Good examples:

- `silent-connect-v25`
- `ducobox-energy-v25`
- `ducobox-focus-v25`

If you later discover a materially different payload shape for the same box
family, add another local profile instead of mutating an existing one silently.

## Local sample layout

Store raw input files locally under `tests/fixtures/replay/raw/<profile>/`.

Use the deterministic request layout directly:

- `tests/fixtures/replay/raw/<profile>/GET/api/__base__.json`
- `tests/fixtures/replay/raw/<profile>/GET/info/module=General;submodule=Board.json`
- `tests/fixtures/replay/raw/<profile>/GET/info/nodes/__base__.json`

Git ignores everything below `tests/fixtures/replay/raw/`. Keep raw files there
only as local validation material.

## Running replay tests

Run the helper tests after changing the local-sample helper logic:

```bash
.venv/bin/pytest tests/test_replay_helpers.py
```

To validate a local profile, set `DUCO_SAMPLE_PROFILE` and run the local sample
test:

```bash
export DUCO_SAMPLE_PROFILE=silent-connect-v26
.venv/bin/pytest tests/test_local_sample_validation.py
```

The local sample-validation test intentionally exercises only a small set of
high-value typed overview readers:

- `GET /api`
- `GET /config`
- `GET /info?module=General&submodule=Board`
- `GET /config/nodes`
- `GET /config/zones`
- `GET /info/nodes`
- `GET /info/zones`

## When to prefer replay tests over live tests

Prefer replay tests when:

- you already have raw payloads locally
- you want deterministic validation for a previously observed payload
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
