# Quill Social extensions: the NetworkAdapter is the seam

**Status: the extension seam already exists — do not add the main QUILL Quillins
framework here.**

The Part-3 sample-Quillins wave (radio.directory, weather.alerts,
studio.pipeline, beacon.resolver) added per-app, host-mediated provider
contributions to the **main** QUILL Quillins framework (`quill/core/quillins`,
`quill/quillins_bundled`). Quill Social is deliberately **excluded** from that
wave, and this note records why, so a future contributor does not duplicate an
existing, better-fitting extension point.

## Why Quill Social is different

- Quill Social (`standalone/social`) is a **separate codebase** with its own
  extension contract: `quill_social.adapters.base.NetworkAdapter`, resolved
  per account by `quill_social.adapters.registry.adapter_for_account`. Each
  network (Mastodon, Bluesky, Lemmy, RSS, OPDS, Telegram, Hacker News, the mock)
  is already a pluggable adapter behind one interface.
- The main QUILL Quillins framework's app targets (`APP_IDS` in
  `quill/core/quillins/model.py`) are `quill`, `radio`, `cast`, `weather`,
  `studio`, `beacon`. **`social` is intentionally not a target**, so a QUILL
  Quillin cannot declare `targets: ["social"]` and validation would reject it.
  There is no `QuillinAppHost` in Quill Social to populate a per-app registry.

## The adapter contribution shape (the real seam)

A new network in Quill Social is a `NetworkAdapter`:

```python
class NetworkAdapter(Protocol):
    network: str                 # the account's network id
    def capabilities(self) -> NetworkCapabilities: ...
    def timeline(self, ...) -> list[Post]: ...
    def publish(self, ...) -> Post: ...
    # read / interact methods per PRD 11, 29.1
```

To add a network, implement that Protocol under
`standalone/social/quill_social/adapters/` and register its builder in
`adapters/registry.py` (the one place that maps an `Account` to its adapter and
resolves credentials at the boundary, PRD 31.1). This mirrors, in Quill Social's
own idiom, exactly what the main framework's `radio.directory` /
`weather.alerts` / `studio.pipeline` / `beacon.resolver` registries do for their
apps: one interface, host-mediated, credentials resolved at the edge.

## Deferred, not dropped

A `social.network` contribution *type* in the main QUILL Quillins framework is
**deferred**: it would require adding `social` to `APP_IDS`, giving Quill Social a
`QuillinAppHost`, and bridging two credential/consent models — a cross-codebase
integration well beyond a sample-Quillin wave, and redundant with the
`NetworkAdapter` contract that already serves this exact purpose. If the two
frameworks are ever unified, the `NetworkAdapter` above is the adapter shape to
wrap; until then, new networks should be added as `NetworkAdapter`s.
