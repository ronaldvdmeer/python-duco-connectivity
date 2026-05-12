# Sanitized replay fixtures

This directory stores sanitized real-world Duco payloads for replay-based
compatibility tests.

Only sanitized fixtures belong in version control. Use `raw/` as a local staging
area when you need to prepare new samples before sanitizing them. Git ignores
everything inside `raw/` except its `.gitignore` placeholder.

## Layout

- Store publishable fixtures under `sanitized/<profile>/`.
- Use a stable profile slug, such as `silent-connect-v25`, for each device or
  firmware family you want to replay.
- Group fixtures by HTTP method first, then by API-relative path segments.
- Use `__base__.json` for requests without query parameters.
- Use a filename such as `module=General;submodule=Board.json` when query
  parameters are present.
- Sort query parameters by key before building the file name.
- URL-encode query keys and values when they contain characters that would make
  the file name ambiguous.

## Examples

- `sanitized/silent-connect-v25/GET/api/__base__.json`
- `sanitized/silent-connect-v25/GET/info/module=General;submodule=Board.json`
- `sanitized/silent-connect-v25/GET/info/nodes/__base__.json`

The shared helpers in `tests/helpers/replay.py` use this layout to discover
profiles, resolve deterministic file paths, and load full sanitized fixture
sets for follow-up replay coverage.