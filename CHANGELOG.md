# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.15.0] - 2026-09-01

### Changed

- **Breaking — bypass target setter requires metadata**: `async_set_bypass_supply_temperature_target()` now requires the `target` keyword argument. The legacy compatibility path that accepted calls without target metadata and applied only the v0.12 finite and exact-decicelsius checks has been removed. Callers must retrieve a `BypassSupplyTemperatureTarget` first and pass it as `target=target` to validate against the target-specific zone, minimum, maximum, and increment before one PATCH is issued. No hidden GET is performed. Migration: call `async_get_bypass_supply_temperature_target(zone_id)` or `async_get_bypass_supply_temperature_targets()` once per coordinator cycle and pass the resulting target to the setter. The only known first-party consumer, `home-assistant/core`, already uses the metadata-aware form since [#180980](https://github.com/home-assistant/core/pull/180980)
  ([#146](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/146)).

## [0.14.0] - 2026-08-31

### Changed

- **Bypass target metadata integrity**: Require complete and coherent value,
  minimum, increment, and maximum metadata from bypass target convenience
  helpers. Bulk reads isolate invalid targets per zone, while strict reads and
  write responses raise `DucoError` for invalid target metadata
  ([#142](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/142)).
- **Target-owned bypass value policy**: Add exact range and step validation plus
  explicit half-up normalization to `BypassSupplyTemperatureTarget`. Bypass
  writes can now accept already-polled target metadata to validate before one
  PATCH without a hidden GET; calls without metadata retain the legacy finite
  and exact-decicelsius checks temporarily
  ([#143](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/143)).
- **Optional capability discovery**: Return natural empty results for explicit
  unsupported responses from ventilation-temperature and bulk bypass target
  discovery. Strict single-target reads continue to raise
  `DucoUnsupportedCapabilityError`, and malformed or operational failures remain
  exceptions
  ([#144](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/144)).

## [0.13.1] - 2026-08-31

### Fixed

- **Diagnostic model constructor compatibility**: Restore pre-0.13 direct
  `DiagComponent` construction with raw status strings and positional raw
  payloads while retaining normalized statuses and rejecting inconsistent
  `raw_status` values
  ([#130](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/130)).

## [0.13.0] - 2026-08-31

### Changed

- **Typed diagnostic status values**: Normalize known diagnostic subsystem
  statuses as `DiagStatus` values while preserving the exact API value in
  `DiagComponent.raw_status`; unknown future statuses now produce `status=None`
  without losing their raw value
  ([#128](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/128)).

## [0.12.0] - 2026-08-26

### Added

- **Bulk bypass supply target reads**: Add
  `async_get_bypass_supply_temperature_targets()` to retrieve every available
  zone target with one `/config` request, keyed by zone ID while omitting
  targets absent from successful responses
  ([#125](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/125)).

## [0.11.0] - 2026-07-19

### Changed

- **Bypass target helper contract**: Require `async_get_bypass_supply_temperature_target()` to return a typed target for successful parameter-specific reads, and raise `DucoError` when the requested field is missing from an otherwise valid `/config` response ([#123](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/123)).

## [0.10.0] - 2026-07-17

### Changed

- **Unsupported optional capabilities**: Raise `DucoUnsupportedCapabilityError` for explicit `400 {"Code":3,"Result":"FAILED"}` responses from the ventilation-temperature and bypass-target endpoints, separating unsupported endpoints from omitted optional data in valid responses ([#120](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/120)).

## [0.9.0] - 2026-07-16

### Fixed

- **Optional temperature capabilities**: Treat the Duco response
  `400 {"Code":3,"Result":"FAILED"}` as an unavailable optional ventilation
  temperature or bypass target endpoint, while preserving other response errors
  for callers ([#118](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/118)).

## [0.8.0] - 2026-07-13

### Added

- **Temperature convenience helpers**: Add a typed
  `async_get_ventilation_temperature_info()` reader for
  `GET /info?module=Ventilation`, plus typed
  `async_get_bypass_supply_temperature_target()` and
  `async_set_bypass_supply_temperature_target()` helpers for
  `HeatRecovery.Bypass.TempSupTgtZoneX` so callers can work in Celsius without
  dropping to the raw decicelsius config surface
  ([#116](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/116)).

### Enhanced

- **Documentation and validation**: Expand the generated API reference, config
  docs, README examples, and local live-testing coverage for the new
  temperature helper surfaces
  ([#116](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/116)).

## [0.7.1] - 2026-06-19

### Fixed

- Treat unsupported `HeatRecovery` info requests as an absent optional
  capability in `async_get_time_filter_remaining()` instead of surfacing the
  box's generic `400 {"Code":3,"Result":"FAILED"}` response to callers
  ([#114](https://github.com/ronaldvdmeer/python-duco-connectivity/pull/114)).

## [0.7.0] - 2026-06-19

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

[Unreleased]: https://github.com/ronaldvdmeer/python-duco-connectivity/compare/v0.15.0...HEAD
[0.15.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.15.0
[0.14.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.14.0
[0.13.1]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.13.1
[0.13.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.13.0
[0.12.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.12.0
[0.11.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.11.0
[0.10.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.10.0
[0.9.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.9.0
[0.8.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.8.0
[0.7.1]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.7.1
[0.7.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.7.0
[0.6.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.6.0
[0.5.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.5.0
[0.4.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.4.0
[0.3.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.3.0
[0.2.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.2.0
[0.1.1]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.1.1
[0.1.0]: https://github.com/ronaldvdmeer/python-duco-connectivity/releases/tag/v0.1.0
