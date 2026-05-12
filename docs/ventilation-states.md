# Ventilation states and modes

`python-duco-connectivity` keeps `VentilationState` and `VentilationMode`
close to the Duco API reference documentation used during development while
remaining tolerant of values that have been observed in real payloads.

## Documented spec-defined modes

The Duco API reference documentation used during development, which is not
shipped in this repository, defines these ventilation mode values:

- `-`
- `AUTO`
- `MANU`
- `OVRL`
- `EXTN`
- `COOL`
- `N/A`
- `DSBL`

The library exposes the `-` mode as `VentilationMode.NONE` and the `N/A` mode
as `VentilationMode.NA` so callers can work with both documented values as
first-class enum members instead of losing them to the generic
`VentilationMode.UNKNOWN` fallback.

## Documented spec-defined states

The Duco API reference documentation used during development, which is not
shipped in this repository, defines these ventilation state values:

- `AUTO`
- `AUT1`
- `AUT2`
- `AUT3`
- `MAN1`
- `MAN2`
- `MAN3`
- `EMPT`
- `CNT1`
- `CNT2`
- `CNT3`
- `-`

The library exposes the `-` state as `VentilationState.NONE` so callers can use
it as a first-class enum member instead of losing that value to the generic
`VentilationState.UNKNOWN` fallback.

## Compatibility states

The library also retains these timed manual variants as explicit enum members:

- `MAN1x2`
- `MAN2x2`
- `MAN3x2`
- `MAN1x3`
- `MAN2x3`
- `MAN3x3`

These values are not listed in the documented reference spec, but they have
appeared in Duco payloads and action discovery responses. Keeping them as
explicit members avoids turning known device behavior into `UNKNOWN` for
downstream consumers.

## Fallback behavior

If the device reports any future unmapped ventilation state, the client still
falls back to `VentilationState.UNKNOWN`.

If the device reports any future unmapped ventilation mode, the client still
falls back to `VentilationMode.UNKNOWN`.
