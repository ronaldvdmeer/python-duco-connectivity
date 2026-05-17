# Public API boundaries

`python-duco-connectivity` uses typed models as its primary public API surface.
That is the default direction for the library, but it is not the only public
surface.

The client also keeps deliberate raw escape hatches so callers can keep working
with broader or newer Duco payloads without waiting for every field, selector,
or endpoint to be promoted into a typed model first.

This page defines where that boundary sits today and how follow-up typing work
should decide whether something belongs on the typed side or should stay raw.

## Core contract

- Prefer typed public models and typed client methods when the library already
  has a stable representation for the data you need.
- Keep typed models close to the Duco API payload shape instead of introducing
  Home Assistant-oriented or UI-oriented abstractions.
- Preserve deliberate raw escape hatches so new firmware fields, selector
  values, and unmapped endpoints remain reachable.
- Treat raw access as part of the public contract, not as an internal accident.

That split is intentional. The library is typed, but it is not meant to become
closed over only the parts of the Duco API that have already been modeled.

## Typed surface

The typed surface is the preferred entry point when it already describes the
endpoint or payload section you need.

Typed primitives can still be compatibility-conscious. When a Duco field has a
stable domain meaning but callers still benefit from string behavior, the
library can expose a string-compatible public type instead of a nested wrapper.
That is the pattern used for board and version primitives like `BoardName` and
`DucoVersion`, and for adjacent metadata families like `DucoSerialNumber`,
`LanMode`, `IpAddress`, `MacAddress`, and `HostName`.

That includes:

- typed readers like `async_get_api_info()`, `async_get_nodes()`,
  `async_get_zone_info()`, and `async_get_config()`
- typed writers like `async_set_config()` and `async_set_zone_config()`
- stable convenience wrappers like `async_get_board_info()` and
  `async_set_ventilation_state()`
- typed dataclasses and enums exported from `duco_connectivity`

Use the typed surface when:

- the relevant endpoint is already modeled
- the typed model already exposes the fields you need
- the library can name the data more clearly than a generic raw payload
- the selector set or value family is stable enough to justify discoverable
  public typing

## Raw surface

The raw surface exists so the library stays usable while the typed model layer
expands gradually.

That includes:

- `raw_payload` on typed response models
- `async_get_raw()` for unmapped `GET` endpoints
- endpoint-specific raw helpers like `async_get_node_config_raw()` and
  `async_set_node_config_raw()`
- raw string selector support on generic selector-taking methods

Use the raw surface when:

- the endpoint is not modeled yet
- the typed model does not expose a newly observed field yet
- the selector value you need is firmware-specific or not yet published as a
  stable enum
- the schema is still too broad, sparse, or unstable to justify a stronger
  public type

Raw support is deliberate, but it is still scoped:

- prefer a typed method first when it already matches the endpoint you need
- prefer endpoint-specific raw helpers over `async_get_raw()` when the client
  already names that endpoint family
- keep generic write access on explicit typed or endpoint-specific methods
  instead of adding an unrestricted write escape hatch

## `raw_payload` boundary

`raw_payload` is the narrowest escape hatch.

It exists so a typed model can stay the primary result type while still
preserving the original API object for forward compatibility.

Use `raw_payload` when:

- the surrounding model is already typed
- you only need one or two extra fields that the typed model has not promoted
  yet
- you want to inspect the original Duco object before proposing a model change

Do not treat `raw_payload` as a second normalized model layer. It intentionally
keeps the original Duco API shape.

## Selector escape hatches

Selectors follow the same boundary.

Known stable selector families can be published as endpoint-specific enums, but
generic selector-taking methods stay open to raw strings so newly observed
values remain reachable.

That means:

- typed selector enums improve discoverability for stable module and submodule
  families
- raw string selectors remain valid public input where the library has not
  closed the set deliberately
- selector enums are endpoint-specific hints, not global registries of every
  possible Duco selector value

See [selectors.md](selectors.md) for the selector-specific rules.

## When a field should stay raw

Keep a field or section raw when one or more of the following is true:

- the observed shape is still incomplete
- the published Duco notes describe it loosely or as an open-ended object
- the values vary across firmware in ways the library cannot yet name clearly
- the typed projection would hide important API details or guess at semantics
- callers still need the original nested `{"Val": ...}` shape

This is why some models intentionally expose only a stable typed subset while
preserving the original object in `raw_payload`.

## When to promote raw data into a typed model

Promote raw data into the typed surface when all of the following are true:

- the endpoint or field is part of the library's intended reusable scope
- the shape is stable in the published Duco notes, repeated observed payloads,
  or both
- a typed representation improves correctness, discoverability, or ergonomics
- the new type can stay close to the Duco API instead of inventing a new
  abstraction layer
- the change can remain additive or compatibility-conscious for existing users

When promoting a raw field or endpoint, keep these follow-up rules in mind:

- prefer adding typed access over removing an existing raw escape hatch unless
  there is a strong compatibility reason to tighten it
- keep `raw_payload` when it still provides forward-compatibility value
- document why any remaining raw fields are still raw
- update the related focused docs so future work can follow the same boundary

## Guidance for future typing work

Before adding a new public model, enum, or wrapper, decide which of these
questions you can answer with confidence:

- Is the Duco shape stable enough to model directly?
- Does the typed result improve caller experience without hiding the API shape?
- Is the selector family stable enough for an endpoint-specific enum?
- Would keeping this raw preserve important compatibility with newer firmware?
- Should the typed result keep `raw_payload` because the boundary is still only
  partially modeled?

If the answer is still uncertain, keep the surface raw for now and document the
reason instead of forcing premature typing.

## Related pages

- [api-reference.md](api-reference.md) for the compact inventory of typed and
  raw public methods
- [payload-preservation.md](payload-preservation.md) for `raw_payload` and
  generic raw endpoint access
- [selectors.md](selectors.md) for selector-specific typing rules