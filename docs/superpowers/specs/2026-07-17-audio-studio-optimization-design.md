# Audio Studio optimization - design

Date: 2026-07-17. Status: design (pending implementation).
Related: `docs/design/2026-07-17-quill-as-extraction-design.md` (QUILL-AS
extraction, implemented).

## Goal

Two sub-projects on the QUILL Audio Studio surface:

1. **Trim-out** - slim the standalone QUILL-AS vendored closure so it no
   longer ships modules a standalone audio tool does not need (Quillins,
   braille, document-editing deps, GLOW, BITS Whisperer speech, spellcheck,
   math). The embedded Audio Studio inside QUILL's `MainFrame` keeps all of
   it.
2. **Port-in** - bring four proven patterns from QUILL Radio / QUILL Cast into
   Audio Studio: a real library tree with pinned views, resume-on-launch +
   Recently Played, media keys + a playback sleep timer, and per-book volume
   / Mute / a promoted Play Queue.

Both keep QUILL as source of truth. Features and guarded-import refactors
land in `quill/` first, are verified in embedded QUILL, then
`scripts/vendor_from_quill.py` re-syncs the standalone. The standalone
inherits everything via re-vendor; nothing is written only in the standalone.

## Non-goals

- Touching Radio or Cast wrappers.
- Removing modules from embedded QUILL. The DROP set stays fully present and
  functional in `quill/`.
- Renaming the `quillas` package or changing the shared `%APPDATA%\Quill`
  store.
- A packaging/Inno/PyInstaller rebuild (separate step, after code is green).

## Architecture & sync model

- **Source of truth:** `quill/`. Embedded Audio Studio (inside `MainFrame`
  and its mixins) and standalone Audio Studio (`quillas/apps/studio.py`) run
  the same feature code. The standalone just drops modules the embedded app
  keeps.
- **Trim mechanism:** guarded imports. Hard references to droppable modules
  become `try/except ImportError` with a `None` (or feature-flag) fallback in
  `quill/`. Embedded QUILL has the modules, so guards fall through to normal
  behavior and the full test suite stays green. QUILL-AS adds the same
  modules to a deny-list in `vendor_from_quill.py` so they are absent; guards
  take the no-op path. Both paths get tests.
- **Port-in mechanism:** each feature lands in `quill/` first - a `core/`
  backing module mirroring the Radio/Cast pattern (`core/radio/history.py`,
  `core/radio/wake_timer.py`, `ui/radio/favorite_actions.py`,
  `ui/podcasts/show_actions.py`) plus its UI surface in `quill/ui/audio_studio/`
  or the shell - then `vendor_from_quill.py` re-syncs into `quillas/`.
  Shell-only wiring (media-key hotkeys, per-app preferences JSON) is written
  in both the embedded shell (`MainFrame`/`app_shell.py`) and the standalone
  shell (`quillas/apps/studio.py`), and recorded in the "local deltas" list.
- **Sequencing:** Phase 1 trim (closure stable + slim + QUILL-AS green),
  Phase 2 port-in (four features, additive, each re-vendored). Trim first so
  new feature code lands on a base where absent-module imports are already
  the norm and re-vendor cannot silently re-pull trimmed modules.

## Phase 1 - Trim design

### Classification

Every module the ast-driven closure currently drags in is classified:

- **KEEP (audio-core, never deny-listed):** `core/speech`, `core/publish`,
  the `core/ai` narration stack (providers, cloud_tts, elevenlabs_tts,
  gemini_tts, transcription, translation, onboarding, free_models, tts,
  tts_chunk, model_manager, provider_backend, assistant, library,
  agent_catalog), `ui/audio_studio`, `stability`, `platform`,
  `core/schemas`, `core/keymap`, and the existing named SEED modules.
  `assistant_ai`, `ai_chat`, `skill_pack`, `skill_store`, and
  `accessibility_agent` stay because Audio Studio's AI-narration and agent
  harness use them; only their references to DROP modules get guarded.
- **DROP (deny-list + guard):** `quillins` / `quillins_bundled`,
  `braille_pack`, `math`, `pandoc_install`, `pdf_ocr_install`,
  `node_install`, `git_binaries`, `python_sandbox`, `glow`, `bw_speech`,
  `spellcheck`.
- **VERIFY (read the call site, then KEEP or DROP):** any module not in the
  two lists above that the closure pulls in during the trim pass. Decided
  per-module; default to KEEP when in doubt.

### Guard pattern

Applied at each DROP import site in `quill/` (located by grep, listed in
the audit table below):

```python
try:
    from quill.core import quillins as _quillins
except ImportError:  # absent in standalone Audio Studio
    _quillins = None
```

Call sites check `if _quillins is not None:`. Embedded: present, normal
behavior. Standalone: no-op. Feature-registry entries in `features.py` /
`feature_catalog.py` / `settings_specs.py` register a DROP feature only when
its module resolved, so the standalone's feature/settings list shrinks
automatically without separate config.

### Import sites to guard (audit table)

| DROP module        | Importing sites in closure                                           |
|--------------------|----------------------------------------------------------------------|
| quillins           | `core/speech/quillin_providers.py`                                   |
| braille_pack       | `core/release_assets.py`, `core/optional_components.py`, `ui/main_frame_speech_downloads.py` |
| pandoc_install     | `core/external_tools.py`, `core/optional_components.py`, `ui/main_frame_speech_downloads.py` |
| pdf_ocr_install    | `core/optional_components.py`, `ui/main_frame_speech_downloads.py`    |
| node_install       | `core/optional_components.py`, `ui/main_frame_speech_downloads.py`    |
| git_binaries       | `core/release_assets.py`, `core/optional_components.py`               |
| python_sandbox     | `core/watch_actions.py`                                              |
| spellcheck         | `core/features.py`, `core/settings.py`, `core/feature_catalog.py`, `core/feature_command_map.py`, `core/settings_specs.py` |
| glow               | `core/diagnostics.py`, `core/features.py`, `core/watch_actions.py`, `core/feature_catalog.py`, `core/feature_command_map.py` |
| bw_speech          | `core/speech/service.py`                                             |
| math               | `core/speech/earcon.py`, `core/release_assets.py`, `core/optional_components.py`, `ui/main_frame_speech_downloads.py` |

`optional_components.py` already has the Studio's
`_optional_component_allowlist` hook (existing delta); the controllers for
pandoc/pdf-ocr/node/git/braille/math are already dormant in the standalone.
Guarding the *imports* lets the modules themselves be absent, not just the
controllers disabled.

### Vendor script change

Add `DENYLIST = { ... }` (the DROP set above) to
`scripts/vendor_from_quill.py`. In `copy_module`, skip any module whose leaf
name is in `DENYLIST` (return a sentinel so the closure walker treats it as
"deliberately absent," like the existing `_feedback_token` blocklist). In
`wanted_modules`, a DENYLIST hit is recorded as unresolved-but-expected
rather than chased.

### Verification loop

1. Add guards in `quill/`; run `pytest -q` in `S:\QUILL` - must stay green
   (modules present, guards fall through).
2. Add a QUILL-side unit test that monkeypatches `importlib` to raise
   `ImportError` for each DROP module and asserts the guard path is taken
   and no `NameError` escapes. Covers the absent path on the QUILL side.
3. Add the DENYLIST; re-run `vendor_from_quill.py` + `vendor_tests.py`.
4. Run `pytest -q` in `S:\QUILL-AS` (basetemp `.quill-as-pytest-tmp`).
   Any new `ImportError` = a missed guard; fix in `quill/`, re-vendor,
   iterate.
5. Record before/after file and line counts for the `quillas` package.

### Embedded-QUILL safety

Guarded imports are no-ops when modules are present. The full `pytest -q` in
`S:\QUILL` must stay green throughout Phase 1. No DROP module is removed
from `quill/`; only import sites become tolerant of absence.

## Phase 2 - Port-in design

Each feature: QUILL-first, then re-vendor. Backing modules mirror the
Radio/Cast structure. New `core/audio_studio/` package holds the
data-layer pieces (parallel to `core/radio/`, `core/podcasts/`).

### Feature 1 - Library tree + pinned views

- **Source pattern:** Cast's flat list -> real tree (`ui/podcasts/show_actions.py`,
  pinned views Favorites/New Episodes/Continue Listening/Inbox + nested
  folders).
- **Backing:** new `core/audio_studio/library.py` - folder/book model on the
  book library entries, pinned-view queries (Favorites, In Progress,
  Recently Played, Inbox/new imports), persisted via the existing
  `versioned_store` / atomic JSON. Nested folders like Cast (path-based).
- **UI:** new `ui/audio_studio/library_tree.py` mirroring the Cast tree +
  context menu (Open, Reveal in Workbench, Toggle Favorite, Delete, New
  Folder, Move). Replaces the flat "Your books" list in the StudioAppFrame
  home and in embedded Audio Studio's library mode.
- **Delta note:** the standalone home is `StudioAppFrame`; embedded is
  `MainFrame` library mode. Both consume the same `library.py` and tree
  widget.

### Feature 2 - Resume-on-launch + Recently Played

- **Source pattern:** Cast's `core/podcasts/history.py` (recently-played,
  distinct from Continue Listening) + Resume Last Episode on Launch.
- **Backing:** new `core/audio_studio/history.py` - recently-played books
  (timestamps, last chapter, listening position). Distinct from the
  existing listening-position resume store (per Jeff's Cast call that
  recently-played != continue-listening).
- **Shell wiring:** resume-last-book-on-launch in `StudioAppFrame` and
  `MainFrame` startup; Recently Played submenu in the File/Library menu.
- **Delta note:** startup hook lives in both shells.

### Feature 3 - Media keys + sleep timer

- **Source pattern:** Radio's `RegisterHotKey` media keys in
  `ui/app_shell.py`; `core/radio/wake_timer.py` timer pattern.
- **Backing:** new `core/audio_studio/sleep_timer.py` - playback sleep timer
  (fade-then-stop, configurable delay, optional end-of-chapter stop),
  mirroring `wake_timer.py` structure and threading rules (background work
  on `QuillTaskManager`, UI via `wx.CallAfter`).
- **Shell wiring:** media-key hotkeys (play/pause, next/prev chapter, stop)
  registered in `app_shell.py` (standalone) and `MainFrame` (embedded);
  Sleep Timer menu item + dialog.
- **Hotkey isolation:** per Jeff's rule, standalone keystrokes are separate
  from QUILL's keymap - the standalone registers its own media-key hotkeys,
  does not extend `core/keymap`.

### Feature 4 - Per-book volume + Mute + Play Queue

- **Source pattern:** Radio per-favorite `volume_percent` + Mute
  (`PodcastPlayerController`); Cast Play Queue promoted to top-level
  menu + command.
- **Backing:** extend the book profile (`core/audio_studio/library.py` or
  existing project profile schema v2) with `volume_percent` and `muted`;
  new `core/audio_studio/play_queue.py` - ordered chapter queue with
  add/next/remove/clear, persisted per book.
- **UI:** `PlayerPanel` gains volume slider + Mute toggle bound to the
  current book's profile; Play Queue promoted to a top-level menu item +
  command (was Workbench-only), with a queue drawer/dialog. Mirrors
  Cast's queue surface.
- **Delta note:** menu/command registration differs between shells but the
  command id and backing module are shared.

### Port-in verification per feature

- `pytest -q` in `S:\QUILL` after each feature (embedded path).
- Re-run `vendor_from_quill.py`; the new `core/audio_studio/` and
  `ui/audio_studio/library_tree.py` are added to SEED so they vendor.
- `pytest -q` in `S:\QUILL-AS` (standalone path, incl. the new deny-list).
- UIA regression coverage for new dialogs (Sleep Timer, Play Queue drawer)
  extended in `tests/uia/`.

## Error handling & risks

- **Missed guard -> standalone ImportError.** Mitigated by the iterate-until-
  green verification loop and the QUILL-side absent-path monkeypatch test.
  Each iteration is small (one module).
- **Feature-registry drift.** `features.py` / `feature_catalog.py` /
  `settings_specs.py` reference DROP modules; guarding the import and
  gating registration on resolution keeps both registries valid. The
  `feature_command_map` and settings specs must not hard-fail when a feature
  is absent.
- **Re-vendor churn.** Guarded imports are in `quill/`, so a re-vendor keeps
  them; the DENYLIST is the only standalone-side addition. No growing delta
  list.
- **CRLF/LF flips.** The Edit tool can flip line endings on QUILL files.
  Check `git diff --stat` for whole-file churn; normalize with a bytes
  replace before committing.
- **Test isolation.** QUILL-AS uses its own basetemp; do not remove the
  `_DEV_BUILD` conftest fixture.
- **Embedded regression.** Every phase ends with `pytest -q` green in
  `S:\QUILL`. No DROP module is deleted from `quill/`.

## Definition of done

- Phase 1: `quillas` package measurably smaller; `pytest -q` green in both
  `S:\QUILL` and `S:\QUILL-AS`; DENYLIST landed; guarded imports landed in
  `quill/`; absent-path unit test green.
- Phase 2: four features shipped in `quill/`, re-vendored into `quillas/`,
  green in both test suites; UIA coverage added; local-deltas list updated.

## Out of scope (carried from extraction design)

Document editing, the assistant chat UI, radio/podcasts, braille, and the
QUILL CI gate scripts (module size budgets, dialog inventory, egress audit)
remain QUILL-side; the vendored copies of shared code are validated there.