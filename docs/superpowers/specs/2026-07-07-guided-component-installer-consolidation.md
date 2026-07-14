# Guided Component Installer & Speech Consolidation

**Status:** proposed · **Date:** 2026-07-07 · **Branch:** `fix/hub-download-test-ux` (follow-up to the 0.9.0 Beta 2 Download Optional Components hub, PR #875)

## Why

Beta-2 shipped the Download Optional Components hub, but testing on a clean build surfaced that acquiring the *heavy* components is still scattered and rough: separate Tools > Speech "Download …" menu items, downloads that dump you out of the hub, Test buttons that fire on components that can't actually run yet, and Kokoro that silently failed because a transitive dependency (`babel`) was pruned from the installer.

The goal: **one magical place** — the Download Optional Components hub — to discover, install, test, remove, and manage every optional component, with friendly, guided, responsive flows. *Meet people where they are.* Consolidation, top-notch UX.

## Principles

- **One front door.** The hub is where you get anything optional. Point-of-use prompts route into it.
- **Guided, not dumped.** Multi-step installs (engine + model, package + models) are walked through with clear explanations and progress, and land you **back in the hub**, never in an unrelated tab or the editor.
- **Only offer what can work.** Test/preview appear only when the component can actually run; otherwise the row guides you to finish (get a model / a voice), never a bug report for a normal not-yet-downloaded state.
- **Small installer, on-demand heft.** Bundle only what every user needs; download the big engines/models on first use.

## Scope

### 1. Consolidate the Tools > Speech submenu (remove the scattered download items)

Remove these three menu items and fold their function into the hub:
- `Download &FFmpeg…` (`tools.speech_ffmpeg`)
- `Download &Offline Speech Engine…` (`tools.speech_offline_engine`, whisper.cpp)
- `Download Faster Whisper &Engine…` (`tools.speech_engine_download`)

Keep the *usage* entries (`Speech and Dictation…`, `Dictate (Offline)`, Voice Command/Conversation/Wake, Speak Voice Status). Manage Speech Models and Manage Voices remain reachable from the hub's **Manage** buttons (and from the Speech and Dictation dialog for choosing the *active* model/voice).

### 2. Guided offline-speech (Whisper) flow

A single hub entry — "Offline speech (dictation & transcription)" — opens a short wizard:
1. **Choose the engine** with plain-language explanations of the trade-off:
   - **Faster Whisper** — most accurate, uses more disk/RAM, GPU-aware.
   - **whisper.cpp** — lighter and fast on CPU, great for most machines.
2. **Choose a model** — tiny → large, each with size and a "recommended for your computer" mark (Manage Speech Models already computes this). **Default to tiny** so the user is working immediately.
3. Install engine + selected model with visible progress; return to the hub with the row now showing Installed + Test.

### 3. Guided Kokoro flow + unbundle for footprint

- **Unbundle Kokoro from the installer.** Remove `kokoro` from `DEFAULT_BUNDLED_DEPENDENCY_GROUPS` in `scripts/build_windows_distribution.py`. Verified safe: `install_kokoro_onnx()` pip-installs the full tree (incl. `babel` transitively via phonemizer→segments→csvw) into an engine-pack, and `activate_engine_packs()` puts it on `sys.path`. This shrinks the installer *and* fixes #881 without bundling babel.
- **Guided install:** one flow fetches the onnx package (+deps) **and** the voice models, then returns to the hub.

### 4. MP3 export support as a guided download

Fold the `mutagen` MP3-support acquisition into the same wizard-style flow (progress + friendly copy) instead of a bare dependency gap.

### 5. Stay-in-the-hub + focus (the beta-2 test findings)

- Downloads run without leaving the hub; on completion the row refreshes and focus returns to the list. (Fixes "eSpeak/MathCAT/whisper took me out of the dialog.")
- Test/preview dialogs are parented to the hub so focus never lands behind the modal. (Fixes the keyboard trap.)
- Test only runs when previewable; otherwise route to Manage. (Done: `VerifyResult.remedy`; no-voice → Manage Voices.)

## Already landed on this branch

- **`fix(build)` #881 / Kokoro:** stop pruning `babel` (kokoro-onnx needs it at runtime). Superseded in spirit by the unbundle above, but harmless and correct if Kokoro ever stays bundled.
- **`fix(components)` Test routing:** expected "no model / no voice" states route to Manage Speech Models / Manage Voices instead of erroring or offering a bug report.
- **Manage models/voices routing buttons** (from PR #875).

## Non-goals

- Not changing how the *active* voice/model is chosen (that stays in Speech and Dictation / Manage Voices).
- Not bundling any large engine/model in the installer.

## Open decisions

- Whether the guided wizard is a new dialog or additional pages inside the existing hub. Recommendation: keep it in the hub's flow (a lightweight step panel) so it stays "one place."
- Exact copy for the Faster Whisper vs whisper.cpp explanation (needs a friendly, screen-reader-first pass).
