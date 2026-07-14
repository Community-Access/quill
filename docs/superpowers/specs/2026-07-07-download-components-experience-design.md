# Download Optional Components — the warm, complete experience (design)

Extends GitHub issue #874 (the unified missing-component surface). #874 wired
the *routing* into one picker; this spec makes that picker a first-class,
delightful place: reordered by importance, with install **and** removal, sizes
on every row, a rich description, and a "hear this voice" test — then routes the
scattered startup prompts into it.

## Problem

`quill/ui/optional_components_dialog.py` (`show_optional_components_picker`) is
today a thin list: name / status / size / category columns, a Download button,
and a one-line detail label. It works, but it is not the "magical" hub it should
be, and several rough edges are user-visible:

1. **Order is by category, not importance.** `gather_optional_components()`
   (`quill/core/optional_components.py`) emits engine → voices → tool →
   dictionaries. Users reach for Pandoc and the braille pack first; those should
   lead.
2. **No removal.** A component can be installed but never uninstalled from here,
   and there is no way to reclaim the disk or turn a feature back off.
3. **Missing sizes.** Spell-check dictionary rows pass `size_hint=""` (they show
   "—"); every row should state its size.
4. **Thin description.** The single detail line can't convey what a component
   enables, its size, and its impact.
5. **No confidence check.** After a voice engine installs, nothing lets the user
   *hear* it — the reassurance that the install actually worked.
6. **Focus flow.** The picker closes (`EndModal`) and the download runs behind
   it (`open_optional_components` in `quill/ui/main_frame_speech.py` dispatches
   after the modal closes). The user is dropped back to the document, not kept
   in the hub where the row now reads "Installed".
7. **Scattered entry.** The startup braille-pack prompt
   (`main_frame._maybe_prompt_braille_pack_install`) and #874's failure routes
   are separate journeys; several should simply land the user *here*, guided.

## Non-goals

- Not a new download engine. Each component keeps its tested, progress-reporting
  installer (`_download_kokoro_models`, `install_piper`, `download_braille_pack`,
  `fetch_component`, …). This is a UI + orchestration layer over them.
- Not per-voice rows. Voice *engines* are one row each (Kokoro, Piper, eSpeak,
  DECtalk); individual voice-model downloads stay in the Voice Browser.
- Not removing bundled/system components. Remove targets only QUILL-downloaded
  copies under the **active data dir** (the portable data folder in portable
  mode, `%APPDATA%\Quill` otherwise — see Portable mode below); it never deletes
  a system Pandoc, an upgrader's `{app}` copy, or anything QUILL did not fetch.

## Design

### 1. Importance ordering

`OptionalComponent` gains an integer `priority` (lower = higher in the list);
`gather_optional_components()` sorts by `(priority, name)`. Proposed order:
Pandoc, braille pack, whisper.cpp, Kokoro, Piper, eSpeak, DECtalk, ffmpeg,
libmpv, MathCAT, Vosk, then the spell-check dictionaries (alphabetical). The
dialog renders in returned order (no re-sort in the UI).

### 2. Sizes on every row

Give the dictionary rows a real `size_hint`. Two options — decide in
implementation:
- **(a)** a static per-dictionary estimate ("~4 MB"), simplest; or
- **(b)** read the pinned asset's size where one exists (the `release_assets`
  entries know their `filename`; a size field could be added).
Recommend (a) for now (dictionaries are all a few MB), with a TODO for (b).

### 3. Rich description box

Replace the one-line `optional_components_detail` StaticText with a **read-only
multiline** `TextCtrl` (`wx.TE_MULTILINE | wx.TE_READONLY`). On row focus it
shows: what the component enables, its size, its on-disk footprint/impact, its
license note, and its current state ("Installed — Remove to free ~X and turn off
Y" / "Not installed — Download to enable Y"). Copy is warm and concrete. The
text is built by a wx-free `describe_component(component)` helper in
`optional_components.py` so it is unit-testable.

### 4. Install + Remove, installed-state controls

- The **Download** button is disabled (and labeled "Installed") when the focused
  row is installed; enabled otherwise.
- A **Remove** button is enabled only when the focused row is installed and is a
  QUILL-downloaded copy that can be removed.
- Removal logic is wx-free in `optional_components.py`:
  `removable_path(component_id) -> Path | None` (None = nothing QUILL can safely
  remove, e.g. a system Pandoc or bundled copy) and
  `remove_component(component_id) -> bool` (delete that path, clear any discover
  cache). The dialog confirms, calls it, then refreshes the row.

### 5. Remove closes the loop (disable dependent features)

Removing a component turns off what it powered. Most engine availability is
already *dynamic* (e.g. `kokoro_engine_ready()`, `discover_piper_executable()`),
so read paths degrade on their own. What needs explicit handling is durable
settings/menus that assume a component (e.g. braille translation surfaces, a
selected Read Aloud engine that just went away). Introduce a small map,
`COMPONENT_FEATURES: dict[str, tuple[str, ...]]`, from component_id to the
feature ids it enables, and on removal:
- if the removed engine is the *active* `read_aloud_engine`, reset it to the
  always-present SAPI 5 floor; and
- surface (do not silently flip) any feature the component gated, via the
  existing feature manager.

**Open question for implementation:** exact depth — reset active-engine +
refresh menus (recommended) vs. also toggling `features.json` entries. Pin the
concrete braille and Read Aloud call sites first, the way #874 pinned its sites.

### 6. Hear-this-voice test button

For voice-engine rows (Kokoro, Piper, eSpeak, DECtalk — those with an installed
speech engine), a **Test** button synthesizes a short, fixed QUILL blurb in a
default voice for that engine and plays it, so the user hears success. Wx-free
core: `TEST_BLURB` constant + reuse of `synthesize_with_kokoro` /
`synthesize_with_piper` / the eSpeak/DECtalk paths to a temp WAV; the dialog
plays it on the UI thread and announces "Playing a sample of <engine>…". The
button is hidden for non-voice components and disabled until the engine is
installed.

**Open question:** the blurb text. Recommend one short, on-brand line (a new
`TEST_BLURB` in `optional_components.py`), e.g. *"This is QUILL, reading to you
with the <engine> voice."* — confirm wording.

### 7. Keep the hub open; focus to progress, then back

Restructure so the picker **stays open** and drives the download in place:
- Activating Download runs the component's installer, showing the existing
  `AIProgressDialog` (which takes focus and announces progress).
- On completion the progress dialog closes, **focus returns to the picker**, the
  row refreshes to "Installed", Download disables, Remove/Test enable, and the
  description updates — the user never leaves the hub.
- This replaces the current "return the chosen id and `EndModal`, dispatch after
  close" flow in `open_optional_components`; the dispatch table moves into the
  dialog (or a controller it calls back into).

### 8. Route the scattered prompts here (with a guiding popup)

- **Startup braille prompt** (`_maybe_prompt_braille_pack_install`): instead of
  its own yes/no install, open the components dialog **preselected on braille**
  (using #874's `preselect`) and show a one-time guiding popup on landing:
  "You're in Download Optional Components. Braille pack is selected — press
  Download to set up braille translation, or Escape to skip." Gate the popup on
  a `seen_components_intro` setting so it shows once.
- **#874 failure routes** (`_offer_optional_component` / `_nudge_once`): already
  land here preselected; they inherit the richer dialog automatically.

### 9. Warm and fuzzy throughout

Encouraging, plain-language copy on buttons, descriptions, and announcements;
the Test button; the guiding popup; and the stay-in-place flow together make the
hub feel like a friendly setup assistant rather than a bare table.

## Testing

- `optional_components.py`: `priority` ordering; `describe_component` text for an
  installed vs not-installed component; `removable_path`/`remove_component`
  (returns None for a non-QUILL copy; deletes a fake app-data copy); dictionary
  rows now carry a non-empty size; `COMPONENT_FEATURES` maps only real feature
  ids. All wx-free, unit-tested.
- Source-contract tests (matching this beta's convention) for the dialog:
  Download disabled when installed, Remove present, Test present for voice rows,
  multiline read-only description, focus-returns-to-list after install.
- `_maybe_prompt_braille_pack_install` routes to `open_optional_components(
  preselect="braille")` and shows the one-time popup.
- The Test path: `synthesize_*` called with the engine's default voice to a temp
  file (mocked synth), then played.

## Files touched

`quill/core/optional_components.py` (priority, describe_component,
removable_path/remove_component, COMPONENT_FEATURES, TEST_BLURB, dict sizes),
`quill/ui/optional_components_dialog.py` (multiline description, Download/Remove/
Test buttons, installed-state gating, stay-open + focus-return flow),
`quill/ui/main_frame_speech.py` (`open_optional_components` restructure, Test/
Remove dispatch), `quill/ui/main_frame.py`
(`_maybe_prompt_braille_pack_install` reroute + guiding popup, #874 helpers),
`quill/core/settings.py` (`seen_components_intro` and any nudge state), plus
new/updated tests in `tests/unit/core/test_optional_components.py` and
`tests/unit/ui/`.

## Decisions (settled 2026-07-07)

1. **Remove → disable depth (§5):** reset the active Read Aloud engine to the
   always-present SAPI 5 when the removed engine was the active one, and refresh
   the braille/menus; do **not** flip `features.json`. Engine availability is
   already dynamic (`discover_*` / `*_ready`), so features self-degrade and
   restore cleanly when the user re-downloads.
2. **Test blurb (§6):** a reassuring, engine-named line —
   *"Hello from QUILL. If you can hear this, the {engine} voice is installed and
   ready to read your writing aloud."* The Test button covers every voice engine,
   **Kokoro included** (Kokoro, Piper, eSpeak, DECtalk).
3. **Dictionary sizes (§2):** static per-dictionary estimates now (they are all a
   few MB); revisit exact sizes later.
4. **Remove scope (§4):** app-data copies only. `removable_path` returns None for
   a system Pandoc, an upgrader's `{app}` copy, or anything QUILL did not fetch.

## Portable mode (must-hold invariant)

Optional components already download into the **active data dir** resolved by
`quill.core.paths.app_data_dir()`, which returns the portable data folder when
the install is in portable mode (`mode == "portable"` + a portable root) and
`%APPDATA%\Quill` otherwise (custom-path installs likewise). Every downloader
routes through it — `default_kokoro_model_dir()`, `managed_piper_dir()`,
`engine_packs_dir()`, the braille pack, and the spell-check dicts — so a portable
install keeps its assets beside the executable and never writes to `%APPDATA%`.

Because `removable_path` / `remove_component` resolve that same
`app_data_dir()`, Remove automatically targets the portable copy in portable
mode. The description box's footprint text must name the active data dir ("frees
~X in your QUILL data folder"), never a hardcoded `%APPDATA%`. Implementation
must add a test that in portable mode the resolved download/remove path is under
the portable root, not `%APPDATA%`.

## Round 2 requirements (2026-07-07)

### R1. Every component has a verify touch point ("prove it works")

The Test button generalises from voices to **a per-type verify action on every
component**, so a user can always confirm what they installed actually works:

- **Voice engines** (kokoro, piper, espeak, dectalk): speak `TEST_BLURB` in a
  default voice (as in §6).
- **STT engines** (whispercpp, vosk): the self-test in R2 below.
- **Tools** (pandoc, ffmpeg, node): run the tool's version probe
  (`pandoc --version`, `ffmpeg -version`, `node --version` via the existing
  safe-subprocess wrapper) and show the reported version.
- **braille**: translate a short sample with `lou_translate` and show the cells.
- **mathcat**: load and speak a sample expression (falls back to "loaded OK").
- **libmpv**: confirm the DLL loads via the existing loader.
- **spell dicts**: check a known word validates in that language.

Wx-free `verify_component(component_id) -> VerifyResult` in
`optional_components.py` (result = ok flag + a human line + optional detail),
so the dialog just renders/announces it. Disabled until the component is
installed.

### R2. Whisper (and Vosk) STT self-test — closing the confidence loop

To prove an offline STT engine works with no bundled audio asset, close the
loop through TTS: synthesize a fixed known phrase with the always-present SAPI 5
voice to a temp WAV, transcribe it with the installed engine, and show the user
what it heard — "Whisper heard: '<text>'". Pass when the transcription
fuzzy-matches the known phrase (token overlap over a threshold), so normal
recognition variance doesn't read as failure. Reuses the existing transcription
path; announced for screen-reader users. This is the STT arm of R1's
`verify_component`.

### R3. Rich failure info + one-click bug report

Every download/install/verify failure must surface the *real* cause and offer to
send it, not just flash a status line:

- Capture the full error: the exception message, the pip/stderr tail already
  logged to `quill.log` (Kokoro/Piper/engine installs write it), the
  component_id, and the resolved target path (portable-aware).
- Show it in a dialog with the detail in a read-only multiline box **and a
  "Send bug report" button** that routes into the existing feedback/diagnostics
  bundle flow (`feedback_hub` / Help > Save Diagnostics), pre-seeded with the
  captured error and the diagnostics bundle (which now carries the logged pip
  error). The bundle stays redacted (no document content).
- A wx-free `DownloadFailure` record (component_id, message, detail, log_excerpt,
  target) carries the info from the core installers up to the dialog.

### R4. Catalog completeness — add the missing components

`gather_optional_components()` is missing two downloadable components; add both
so the dialog has a touch point for everything QUILL can fetch:

- **piper** — detector `discover_piper_executable() is not None`; installer
  `piper_install.install_piper`; category VOICES.
- **node** — detector `node_install.is_node_available()`; installer
  `node_install.install_node_runtime`; category TOOL; "for Node Quillins and the
  Developer Console TypeScript interface".

A guard test asserts every component QUILL can install (each `release_assets`
asset + each `*_install` module + piper/node) appears in
`gather_optional_components()`, so a future downloadable component can't silently
miss the dialog again.

## Phasing

- **Phase 1** — wx-free core: add piper + node (R4), `priority` ordering,
  dictionary sizes, `describe_component`, and the completeness guard test.
- **Phase 2** — Remove: `removable_path`/`remove_component` (portable-aware),
  installed-state gating, engine-reset loop; portable-path test.
- **Phase 3** — verify touch points (R1) incl. voice Test and Whisper/Vosk
  self-test (R2), rich failure + bug report (R3).
- **Phase 4** — stay-open focus flow, reroute the startup braille prompt with the
  guiding popup, and the #874 failure routes.
