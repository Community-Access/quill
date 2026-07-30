# Radio Community Directory

**Bundled QUILL Quillin** — `com.quill.radiocommunitydirectory`

A reference implementation of the `directory_providers` contribution model (the
`radio.directory` capability). It runs only in **Quill Radio**
(`targets: ["radio"]`).

## What it does

Adds a small "community" station directory to Quill Radio's **Find Stations**
search. When you search, the host asks this Quillin for matching stations and
merges them into the results alongside the built-in sources (Radio Browser,
TuneIn, iHeart, ...), badged with the `Community Directory` Source label.

It is **declarative and host-mediated**: the Quillin declares a handler that
returns station rows; the host folds them into the search fan-out. The Quillin
makes no network call of its own — the sample stations come from a static list —
so it needs no `net` capability (least privilege).

## How it works

- `contributes.directory_providers` declares the provider `id`, its
  `display_name` (the Source badge), and the `handler` name.
- The handler (`directory_search`) receives `{"query": ...}`, filters its static
  station list, and writes the matching rows as JSON to storage under the result
  key the host reads.
- `quill.core.radio.directory_search.directory_provider_stations` consults the
  registered providers during the Find Stations fan-out and turns each row into a
  `RadioStation`.

## Capabilities

- `radio.directory` — contribute a station-directory provider.
- `storage` — return the matching station rows.

## License

MIT. See `LICENSE`.
