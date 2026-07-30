# Beacon Transit Resolver

**Bundled QUILL Quillin** — `com.quill.beacontransitresolver`

A reference implementation of the `location_resolvers` contribution model (the
`beacon.resolver` capability). It runs only in **Quill Beacon**
(`targets: ["beacon"]`).

## What it does

Adds a fallback location resolver to Quill Beacon. When a saved Universal
Location Descriptor (ULD) cannot be placed by the built-in locators (native,
structural, text-quote, fuzzy, positional), the host consults this Quillin as a
last-ditch layer. The sample does a case-insensitive search for the saved quote
and returns a low-confidence match, so Beacon surfaces it for review rather than
silently replacing an exact bookmark (PRD 10.2).

It is **declarative and host-mediated**: the Quillin declares a handler that
resolves a ULD against current content; the host calls it only after the exact
layers fail. The Quillin makes no network call of its own.

## How it works

- `contributes.location_resolvers` declares the resolver `id`, its `handler` name,
  and optional `content_types` scoping (e.g. `["web", "text"]`; empty means any).
- The handler (`resolve_location`) receives `{"loc": {...}, "content": ...}` and
  writes a resolution object (`matched` / `confidence` / `layer` / `position` /
  `message`) as JSON to storage under the result key the host reads.
- `quill.apps.beacon.uld.resolve` consults `quill.apps.beacon.resolver_registry`
  as a fallback layer before reporting "location not found".

## Capabilities

- `beacon.resolver` — contribute a location resolver.
- `storage` — return the resolution object.

## License

MIT. See `LICENSE`.
