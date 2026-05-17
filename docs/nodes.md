# Node models

`async_get_nodes()` and `async_get_node_info()` return the public `Node` model.
The library keeps that model close to the Duco payload shape while still using
explicit typed submodels for the sections that are already stable in the public
API notes.

For selector-taking reads like `async_get_node_info(node_id, module=..., parameter=...)`,
the client exposes known stable node-module selectors as enums while still
accepting raw strings for newly observed firmware values. See
[selectors.md](selectors.md) for the selector contract.

## Node sections

- `Node.general` is always present and uses `NodeGeneralInfo`.
- `Node.ventilation` is populated when the payload includes the
  `Ventilation` section.
- `Node.sensor` is populated when the payload includes the `Sensor` section.
- `Node.motor_state` is populated when the payload includes the
  `MotorStateCtrl` section.
- `Node` and the typed node submodels keep the original API objects in
  `raw_payload` so newly observed fields remain inspectable before the typed
  model layer is expanded.

## General metadata

`NodeGeneralInfo` keeps the Duco field layout but now exposes the stable scalar
fields as compatibility-friendly typed primitives:

- `sub_type` uses `NodeSubtype`
- `parent` uses `NodeParentId`
- `asso` uses `NodeAssociationId`
- `name` uses `NodeName`
- `identify` uses `NodeIdentify`

These primitives stay string- or integer-compatible, so existing comparisons,
logging, and JSON serialization continue to work while the public model makes
the field meaning more explicit.

## Ventilation and sensor values

`Node.ventilation` keeps `VentilationState` and `VentilationMode` for the
closed enum families, and uses typed scalar wrappers for the remaining stable
fields:

- `time_state_remain` uses `VentilationTimeRemaining`
- `time_state_end` uses `VentilationTimeEnd`
- `flow_lvl_tgt` uses `VentilationFlowLevelTarget`

`Node.sensor` follows the same pattern for stable measured values:

- `co2` uses `NodeCo2Ppm`
- `iaq_co2` and `iaq_rh` use `NodeAirQualityIndex`
- `rh` uses `NodeRelativeHumidity`
- `temp` uses `NodeTemperature`

## Motor state

`Node.motor_state` uses `NodeMotorStateInfo`, which mirrors the documented
`MotorStateCtrl` payload while making the stable scalar fields explicit:

- `device_type` uses `NodeMotorDeviceType`
- `req` uses `NodeMotorRequest`
- `pos_req` and `pos` use `NodeMotorPosition`

Each field remains optional so the parser can preserve compatibility with
payloads that omit the motor section entirely or only expose part of it.