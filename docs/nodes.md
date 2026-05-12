# Node models

`async_get_nodes()` and `async_get_node_info()` return the public `Node` model.
The library keeps that model close to the Duco payload shape while still using
explicit typed submodels for the sections that are already stable in the public
API notes.

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

## Motor state

`Node.motor_state` uses `NodeMotorStateInfo`, which mirrors the documented
integer fields from the public `MotorStateCtrl` payload:

- `device_type`
- `req`
- `pos_req`
- `pos`

Each field remains optional so the parser can preserve compatibility with
payloads that omit the motor section entirely or only expose part of it.