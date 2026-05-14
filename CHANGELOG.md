# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/ronaldvdmeer/python-duco-connectivity/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.3.0
[0.2.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.2.0
[0.1.1]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.1.1
[0.1.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.1.0
