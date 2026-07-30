# Weather Extra Alerts

**Bundled QUILL Quillin** — `com.quill.weatherextraalerts`

A reference implementation of the `alert_sources` contribution model (the
`weather.alerts` capability). It runs only in **Quill Weather**
(`targets: ["weather"]`).

## What it does

Adds an extra source of active weather alerts to Quill Weather's alert watch.
When the watch checks for alerts, the host asks this Quillin for any extra ones
and merges them with the built-in NWS feed, so a community advisory or a regional
feed can surface alongside the official alerts.

It is **declarative and host-mediated**: the Quillin declares a handler that
returns alert rows; the host merges them into the watch. The Quillin makes no
network call of its own — the sample advisory is read from its own storage — so
it needs no `net` capability (least privilege).

## How it works

- `contributes.alert_sources` declares the source `id`, its `handler` name, and a
  suggested `interval_seconds` poll cadence.
- The handler (`extra_alerts`) returns alert rows (`{"id", "event", ...}`) as JSON
  written to storage under the result key the host reads.
- `quill.core.weather.headless_check.run_check` merges the contributed alerts with
  the fetched NWS alerts before diffing against what the user has already seen.

## Capabilities

- `weather.alerts` — contribute a weather alert source.
- `storage` — read the configured advisory and return the alert rows.

## License

MIT. See `LICENSE`.
