# Daily Stamp

**Bundled QUILL Quillin** — `com.quill.dailystamp`

A Layer-1 (no-code) sample that demonstrates the multi-app `targets` field. It
declares `targets: ["quill", "beacon"]`, so the **same** Quillin loads in both
the full editor and in Quill Beacon.

## What it does

Contributes one command, **Insert Daily Stamp**, whose `run.snippet` is the
`${date}` placeholder. In the editor the stamp is inserted at the cursor; in a
companion app (Beacon) the same command copies today's date to the clipboard —
the app-host's snippet path for apps that have no editor document.

## How it demonstrates `targets`

`targets` decides which app(s) a Quillin loads in. Most Quillins target a single
surface; this one lists two (`quill` and `beacon`) to show that a Quillin can span
the editor and a companion app from one manifest. The loader filters discovery by
app id, so an editor session and a Beacon session each pick this Quillin up, while
a Radio or Weather session (not listed) never does.

## Why Layer-1 (no `document.events`)

Beacon-facing samples cannot use editor-only capabilities. `document.events`
(document lifecycle) is editor-only by the Quillins SEC invariant — a manifest
that declares it may not target a non-editor app, because those apps have no live
editor document to act on. To span the editor and Beacon this sample therefore
stays Layer-1: a pure snippet command, which needs no capability and no entry
module, and works in both surfaces.

## Capabilities

None. This is a snippet-only (Layer-1) Quillin.

## License

MIT. See `LICENSE`.
