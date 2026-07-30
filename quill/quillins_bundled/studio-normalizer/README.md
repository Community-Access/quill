# Studio Normalizer

**Bundled QUILL Quillin** — `com.quill.studionormalizer`

A reference implementation of the `pipeline_steps` contribution model (the
`studio.pipeline` capability). It runs only in the **Audio Studio**
(`targets: ["studio"]`).

## What it does

Adds a loudness-normalization step to the Audio Studio's audio-processing
pipeline. When the Studio builds its ffmpeg filter graph for the `master` stage,
the host asks this Quillin for a filter fragment and appends the returned
`loudnorm` filter, so exported narration lands at a consistent loudness.

It is **declarative and host-mediated**: the Quillin declares a handler that
returns an ffmpeg filter fragment for a stage; the host runs ffmpeg. The Quillin
touches no audio bytes and makes no network call of its own — so it needs no
`net` capability (least privilege).

## How it works

- `contributes.pipeline_steps` declares the step `id`, its `stage`
  (`pre` / `master` / `post`), its `display_name`, and the `handler` name.
- The handler (`loudnorm_filter`) receives `{"stage": ...}` and writes the ffmpeg
  filter fragment to storage under the result key the host reads.
- `quill.core.audio_enhance.build_filter_graph`, when a caller opts into a
  pipeline stage, consults `quill.core.audio_studio.pipeline_registry` and appends
  the contributed fragments to the `-af` graph.

## Capabilities

- `studio.pipeline` — contribute an audio-processing step.
- `storage` — return the ffmpeg filter fragment.

## License

MIT. See `LICENSE`.
