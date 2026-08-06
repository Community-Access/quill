# Companion apps that are not part of public QUILL 1.0

QUILL 1.0.0 ships as the editor plus **two** public companion apps: **Quill
Radio** and **Quill Weather**. Everything documented in this folder is gated out
of a public build and is verified only for *absence* from public surfaces
(`docs/planning/signoff/QUILL-1.0.0-SIGNOFF.md`, section G).

The gate is `RELEASED_APPS` in `quill/core/app_launcher.py`
(`{"quill", "radio", "weather"}`), plus `QUILL_DEV_BUILD=1` for developers. With
the flag off, the QuillVille menu, the command palette, the Explorer shell verb,
and the build products for these apps are all hidden.

| App | Docs | Gate |
|---|---|---|
| Quill Cast (podcast client) + the editor-embedded Podcasts feature | [`cast/README.md`](cast/README.md) | `RELEASED_APPS`; `core.podcasts` is dev-build-only for 1.0 |
| Media Player | [`player/README.md`](player/README.md) | `is_app_released("player")` on `app.open_media_player` |
| Quill Converter (standalone audio converter) | [`converter/README.md`](converter/README.md) | `RELEASED_APPS`; the "Convert with Quill" shell verb is gated with it |
| QuillBeacon | [`beacon/README.md`](beacon/README.md) | `RELEASED_APPS`; still an independent repo |
| Audio Studio (standalone app) | [`../audio-studio/README.md`](../audio-studio/README.md) | `RELEASED_APPS` |

Each file here holds the user-guide and PRD material that was **relocated, not
deleted**, out of the public docs during the 1.0.0 documentation consolidation.
When an app ships publicly, its file is the material to promote back.

**Two things this folder is not:**

- `docs/podcast/` is the 54-episode audio course *about* QUILL, not Quill Cast's
  documentation. The name collision is unfortunate; the app's docs are in
  [`cast/`](cast/README.md).
- The *editor-embedded* audio tools stay public and stay in the user guide:
  **Tools > Speech > Audiobook & Batch Speech...**, the Chapter Workbench,
  **Export to Translated Speech Audio**, the **Voices > Convert Audio...**
  dialog, the `quill convert` CLI, and the **Book Library**. Only the standalone
  apps moved.
