# Companion apps that are not part of public QUILL 1.0

QUILL 1.0.0 opens these companion apps from its QuillVille menu: **Quill
Radio**, **Quill Weather**, **Quill Inkwell**, **Quill Converter** and **QUILL
Transcribe** (checked against the code on 2026-10-23). The apps documented in
this folder are not among them: QUILL hides them, and the 1.0.0 sign-off checks
only that they are *absent* from QUILL's public surfaces
(`docs/planning/signoff/QUILL-1.0.0-SIGNOFF.md`, section G).

The gate is `RELEASED_APPS` in `quill/core/app_launcher.py`
(`{"quill", "radio", "weather", "inkwell", "converter", "transcribe"}`), plus
`QUILL_DEV_BUILD=1` for developers. With the flag off, QUILL's QuillVille menu,
command palette and Explorer shell verb do not offer an app outside it. The gate
is QUILL's own: it does not stop an app having an installer of its own, and the
family build (`build-quill-apps.ps1 all`) makes installers for Quill Cast, Audio
Studio, Quill Beacon and Quill Social as well.

| App | Docs | Gate |
|---|---|---|
| Quill Cast (podcast client) + the editor-embedded Podcasts feature | [`cast/README.md`](cast/README.md) | `RELEASED_APPS`; `core.podcasts` is dev-build-only for 1.0 |
| Media Player | [`player/README.md`](player/README.md) | `is_app_released("player")` on `app.open_media_player` |
| Quill Beacon | [`beacon/README.md`](beacon/README.md) | `RELEASED_APPS`; lives in `quill/apps/beacon/` |
| Audio Studio (standalone app) | [`../audio-studio/README.md`](../audio-studio/README.md) | `RELEASED_APPS` |

Each file here holds the user-guide and PRD material that was **relocated, not
deleted**, out of the public docs during the 1.0.0 documentation consolidation.
When an app ships publicly, its file is the material to promote back. Quill
Converter has: it joined `RELEASED_APPS` with its 1.0.0 release, and
[`converter/README.md`](converter/README.md) stays as the record of what moved.

**Two things this folder is not:**

- `docs/podcast/` is the 54-episode audio course *about* QUILL, not Quill Cast's
  documentation. The name collision is unfortunate; the app's docs are in
  [`cast/`](cast/README.md).
- The *editor-embedded* audio tools stay public and stay in the user guide:
  **Tools > Speech > Audiobook & Batch Speech...**, the Chapter Workbench,
  **Export to Translated Speech Audio**, the **Voices > Convert Audio...**
  dialog, the `quill convert` CLI, and the **Book Library**. Only the standalone
  apps moved.
