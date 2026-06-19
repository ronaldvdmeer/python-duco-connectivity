# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add a typed `async_get_time_filter_remaining()` helper for
  `GET /info?module=HeatRecovery` so callers can consume the optional
  `TimeFilterRemain` field without dropping to the generic raw `/info` reader.

## [0.6.0] - 2026-06-03

### Changed

- **Diagnostics subsystem contract**: Add a typed `DiagInfo` wrapper for
  `GET /info?module=Diag`, preserve raw subsystem component and status strings
  for forward compatibility, and keep `async_get_diagnostics()` as a
  convenience wrapper over the richer typed response
  ([#110](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/110))

### Enhanced

- **Diagnostics parsing resilience**: Return empty typed collections when
  `Diag` or `SubSystems` are absent, skip incomplete subsystem entries instead
  of failing parsing, and expand regression coverage for missing, partial, and
  future diagnostic values
  ([#110](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/110))
- **Ruff alignment**: Align the local Ruff configuration and related cleanup
  with the Home Assistant core rule set
  ([#109](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/109))

## [0.5.0] - 2026-05-17

### Added

- Add explicit selector strategy and typed-versus-raw boundary documentation
  for the public API surface.
- Add typed board and software version primitives, plus typed model families
  for action, config, zone, and group surfaces.

### Changed

- Tighten stable LAN metadata, node read models, and ventilation read models so
  public callers receive deliberate typed values instead of incidental raw
  strings where the API contract is stable.

### Enhanced

- Expand the generated API reference and regression coverage for the broader
  typed public surface.

## [0.4.0] - 2026-05-14

### Added

- Add typed HTTP response errors so non-2xx responses expose the HTTP status,
  request path, and response body through `DucoResponseError` without changing
  typed success returns.

### Fixed

- Keep default response error messages clean when the response body is empty or
  whitespace-only.
- Keep the generated API reference aligned with the published response error
  surface.

## [0.3.0] - 2026-05-14

### Added

- Expand the public client surface with generic `GET /info`, `GET /config`,
  and `PATCH /config` helpers, plus focused typed readers for node, zone, and
  zone-group data.
- Add public system and node action discovery and execution support, including
  typed action request and discovery models.
- Add a raw `GET` escape hatch for unmapped endpoints so callers can inspect
  additional public API data without waiting for a typed wrapper.
- Add the `duco-probe` function probe CLI, generated API reference tooling,
  and focused documentation for actions, config, live testing, replay testing,
  payload preservation, ventilation states, and zones.
- Add local live-test coverage and replay-based compatibility validation for
  supported public read paths.

### Changed

- Preserve the original API object on typed response models through
  `raw_payload` so unknown fields remain inspectable without abandoning typed
  accessors.
- Expose the public `MotorStateCtrl` node payload through optional
  `Node.motor_state` and `NodeMotorStateInfo` fields.
- Expand `NodeType`, `NetworkType`, `VentilationState`, and
  `VentilationMode` to cover more documented public API values while
  preserving `UNKNOWN` fallback behavior for future unmapped values.

## [0.2.0] - 2026-05-09

### Added

- **Core migration compatibility**: Added backward-compatible aliases for old
  `python-duco-client` names still used during the Home Assistant core
  migration, including `ApiEndpointInfo`, `DucoRateLimitError`,
  `ApiInfo(api_version=...)`, `ApiInfo.api_version`, and
  `async_get_write_req_remaining()` ([#6](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/6))

### Changed

- **Debug instrumentation**: Added targeted debug logging for client
  initialization, request/response flow, enum fallbacks to `UNKNOWN`, and
  compatibility-path usage to make migration troubleshooting easier
  ([#6](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/6))

### Fixed

- **`ApiInfo` constructor compatibility**: Preserved the previous positional
  constructor shape for `reported_api_version` and `endpoints` while adding the
  legacy `api_version` compatibility keyword
  ([#6](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/6))

### Enhanced

- **Regression coverage**: Expanded tests for compatibility aliases, caller
  logging, and public model constructor compatibility
  ([#6](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/6))

## [0.1.1] - 2026-05-08

### Fixed

- Add explicit `NetworkType.MB` support for nodes reported over MB transport.
- Harden host parsing in `DucoClient` so host values with embedded ports are
  parsed correctly, conflicting `host` and `port` inputs are rejected, HTTP
  scheme casing is accepted, embedded credentials are rejected, and malformed
  embedded ports raise a consistent client-specific `ValueError`.
- Fall back to `DiagStatus.UNKNOWN` for unrecognized diagnostic status strings.
- Fall back to `VentilationState.UNKNOWN` and `VentilationMode.UNKNOWN` for
  future ventilation values so node parsing stays resilient to new firmware
  responses.

### Enhanced

- Add focused regression tests for the new parsing edge cases.

## [0.1.0] - 2026-05-08

### Added

- Initial public release of `python-duco-connectivity`.
- Async HTTP client for the local unauthenticated Duco Connectivity API.
- Typed models for API info, board info, LAN info, nodes, diagnostics, and
  write-budget data.
- Support for requesting ventilation state changes through the public action
  endpoint.
- CI validation with pytest, Ruff, mypy, Bandit, and pip-audit.
- PyPI Trusted Publishing workflow for tagged releases.

[Unreleased]: https://github.com/ronaldvdmeer/python-duco-connectivity/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.6.0
[0.5.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.5.0
[0.4.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.4.0
[0.3.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.3.0
[0.2.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.2.0
[0.1.1]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.1.1
[0.1.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.1.0
