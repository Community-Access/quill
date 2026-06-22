# Changelog

## 0.7.0 Beta 1 (in development)

First pre-release of the 0.7.0 line. Tagged off `release/0.7.0-verbosity` once the remaining waves (#271 verbosity rebuild, #238-#246 braille phase 3-4, #300-#359 polish, planning-folder retirement) merge. The GitHub Pages update feed remains pointed at 0.5.0 so testers checking for updates do not see a phantom bump until 0.7.0 ships as a stable release. See `RELEASE.md` for the tag-time flip step and the full pre-tag checklist.

### Document Language: edit anything as any language (#181)

- **A pinned Document Language now drives the editing characteristics, not just token navigation (#181).** Setting a language (HTML on a plain `.txt`, say) makes Bold/Italic insert the right markup, enables the heading/table/list/tag menu items, switches comment toggling to that language's syntax, and steers heading/structure navigation, the outline, link insertion, and live preview — all via a new pin-aware `_effective_markup_kind()`/`_current_markup_context()` and a `markup_kind` on `LanguageProfile`. Comment toggling (`format_ops.toggle_line/block_comment`) takes the profile so it wins over the file name. Set it with **Ctrl+Shift+L**, **Navigate > Set Document Language...**, the new **Format > Document Language** radio submenu, or Enter on the status-bar **Language** segment (which shows **(set)** when pinned). "Auto-detect from file" clears the override; a Save As hint fires when the language's extension doesn't match the file. Tab-only (not remembered across reopen). Added **C#** and **PHP** profiles.
- **Optional automatic language detection on paste/typing (#181).** New wx-free `quill/core/language_detect.py` scores ~18 languages from weighted structural signals with VS Code-style confidence discipline (absolute floor, relative margin, ambiguity penalties for YAML/TOML/SQL, session-history bias, and a `should_switch()` hysteresis gate) — no ML, no dependency. The `language_detection_mode` setting (default **off**; **hint**/**prompt**/**auto**, in Settings > Editing) drives a debounced detector (`main_frame_language_detect.py`) that runs only on unpinned untitled/`.txt` documents, never overrides a real extension or a user choice, and — unlike a silent or visual-only switch — keeps a screen-reader user informed. Verified it does not misfire on plain prose or pasted ASCII-braille (BRF). Tests: `test_language_detect.py` (20 cases), plus markup_kind and profile-aware comment tests.

### Offline speech: model manager, formats, and reliability

- **Model downloads no longer freeze the app, and show real progress (#617).** `FasterWhisperProvider.is_available()` did a full `import faster_whisper` (which pulls in CTranslate2 and can take ~25 s on first load) on the UI thread whenever the Whisperer menu built its registry — freezing the whole app. It now probes with `importlib.util.find_spec` (~2 ms); the heavy import stays in the transcription path, which runs on a worker thread. Model downloads run on a worker thread behind a cancelable progress dialog with a real percentage and screen-reader milestone announcements (Faster Whisper downloads report byte-level progress via a tqdm subclass). Cancel is cooperative — the progress callback raises, aborting the stream and cleaning up the partial file.
- **Discoverable model deletion + machine-fit guidance (#617).** Manage Speech Models now shows an explicit Download / Remove action picker (deletion is no longer inferred silently from install state). The header shows a one-line machine summary (RAM + GPU); each model estimates the RAM it needs and is flagged when it exceeds available memory; the best fit is marked "Recommended for your computer"; heavy models note when no GPU is present; and the download prompt warns on low disk space before starting. Fit/recommendation/disk logic is wx-free in `quill/core/speech/service.py` (unit-tested), reusing the BITS Whisperer RAM/GPU/disk probes.
- **Transcribe almost any audio or video format (#617).** whisper.cpp only reads 16 kHz mono WAV, so other inputs (MP3, M4A, MP4, MOV, MKV, …) could silently fail. When `ffmpeg` is available QUILL now transcodes the file to a temporary 16 kHz mono WAV first via the new wx-free `quill/core/speech/ffmpeg.py` (bundled-first-then-PATH resolver, basename allowlist, runs through `run_subprocess_safely` so no console window flashes); Faster Whisper decodes these formats itself. Without ffmpeg, QUILL passes a `.wav` through and gives a clear, actionable message for other formats. The Transcribe/Captions pickers were widened to the full format list. ffmpeg is GPL/LGPL and QUILL does **not** bundle it (non-redistributor stance) — it uses a system or user-installed copy.
- **Offline speech lives under Tools > Speech > Whisperer (#617).** The on-device transcription, captions, dictation, and voice-command items moved out of the AI menu — they need no AI account or key, so they no longer imply an AI dependency. The Windows installer's optional `speechwhisper` component (whisper.cpp engine payload under `tools\speech\whispercpp`) is now emitted by the installer-script generator so a build keeps the offline engine.
- **Hugging Face download hardening + transparency (#617).** Three changes to how speech models are fetched: (1) the model manager shows each model's license and a model-card URL in the row label and the download confirm (`service.model_card_url` derives it from either the whisper.cpp resolve URL or the FW repo id); (2) supply-chain pinning — whisper.cpp models download from a pinned commit with a per-file `sha256` (the existing verifier now runs), Faster Whisper repos pin a `revision` (new `SpeechModelInfo.revision`), and the stale tinydiarize speaker-detection URL (which 404'd against `ggerganov/whisper.cpp`) was fixed to `akashmjn/tinydiarize-whisper.cpp`; (3) an optional Hugging Face token (new wx-free `quill/core/speech/hf_auth.py`, reusing the `QUILL:huggingface:token` credential) is attached to both download paths when present, a 429 becomes a clear "add a token or retry" message, and `Tools > Speech > Whisperer > Hugging Face Token...` sets it via a masked dialog. A token is not required for the public MIT models. Tests: `test_hf_auth.py`, plus catalog-pinning and license/card-url assertions.
- **Watch Folder can now auto-transcribe arriving audio on-device (WATCH-9).** A new **Transcribe audio (Whisperer)** watch action runs whisper.cpp / Faster Whisper entirely on your machine over each audio or video file a watch profile claims, writing a sibling `.txt` transcript — nothing is uploaded, so it needs no consent (the on-device counterpart to the existing cloud `Transcribe audio (OpenAI Whisper)` action). It replaces the old "not available yet" placeholder, is discoverable in the watch action picker, and reports clear guidance (open Tools > Speech > Whisperer > Manage Speech Models) when no offline model is installed rather than failing silently. New wx-free `quill/core/speech/transcribe.py` picks the best available offline provider and model; the two transcription watch actions moved into a new `quill/core/watch_transcribe.py` to keep `watch_actions.py` within its size budget. Tests: `test_transcribe.py` (8) and the WhispererTranscribeAction cases in `test_watch_actions.py`. This is the first item delivered from the BITS Whisperer consolidation workstream.
- **Choose the transcript output format: Text, SubRip (.srt), WebVTT (.vtt), or Markdown (WATCH-9).** The offline transcribe watch action now honors an `output_format` option and writes the sibling file with the matching extension, reusing `speech/formatters.py` (the action returns the full timestamped result, not just text). SRT/VTT carry timestamps and fall back to plain text when the engine returns no segments, so a profile never writes an empty caption file. A **Transcript format** picker was added to the Add/Edit Watch Profile dialog. To stay under the GATE-11 size budget, that dialog's `_edit_watch_profile` was extracted from `main_frame.py` into a new `quill/ui/main_frame_watch_profile.py` (`WatchProfileDialogMixin`), ratcheting the `main_frame.py` budget down by ~430 lines.

### Text-file round-trip and accessibility fixes

- **UTF-8 BOM no longer leaks into the buffer (#648).** `quill.io.text.read_text_document` reads raw bytes, detects a UTF-8 BOM, decodes with `utf-8-sig` (so no editable `U+FEFF`), and stores `utf-8-sig` as the encoding so the BOM is re-added byte-for-byte on save. Byte-exact round-trip tests in `tests/unit/io/test_text.py`.
- **CRLF and blank-line runs preserved on save (#649).** Line endings are now detected from the raw bytes (the previous `path.read_text()` translated CRLF→LF before detection, so it always mis-detected LF). `quill.io.export.write_document_as` writes `.txt`/`.text` verbatim instead of routing them through `markdown_to_plain_text`, which collapsed runs of 3+ newlines to 2; the explicit **Save As Plain Text** command still flattens markup on purpose.
- **AI Hub tab group has an accessible name (#643/#646).** The `AIHubDialog` notebook now sets an explicit accessible name so VoiceOver announces the settings dialog's tab group (best-effort; macOS verification pending). GATE-11 budget rebaselined accordingly.

### Offline voice commands (Speech S5)

- **Drive QUILL hands-free, offline, with spoken commands (#663).** New **AI > Speech > Voice Command (Offline)** (`tools.voice_command`) is push-to-talk: run it, speak one command ("save", "bold", "next heading", "word count", "command palette", …), run it again to act. Recognition uses the on-device `quill/core/speech` stack (whisper.cpp) — no cloud, no upload. The set of commands voice can invoke is the **agent safe-tool allowlist** (`SAFE_TOOL_IDS`), so a misheard phrase can never trigger a destructive action; dispatch double-checks the allowlist before running. Off by default (`settings.voice_commands_enabled`) and always disabled in Safe Mode, matching the assistant/agent guarantees. The matcher (`quill/core/speech/voice_commands.py`, wx-free) is exact/alias/sub-sequence based with a cancel phrase ("cancel" / "never mind") and a spoken "no command matched; heard: …" when nothing fits. This is the *offline* counterpart to the existing Windows-dictation "Hey QUILL Commands" mode. Tests: `test_voice_commands.py` (16 cases) + `test_voice_command_wiring.py` (5). Closes #663 (Speech S5). **Live mic/recognition behavior warrants a manual smoke run.**

### Verbosity system (live wiring + polish)

- **Verbosity rebuild — wired into the editor and reachable (#365), and the 100-item polish consolidated (#366).** Sub-PR 1.5 makes the system live: a `VerbosityController` (wx-free, in `quill/core/verbosity/controller.py`) owns the engine, Quiet/Meeting modes, the undo stack, announcement history, mastery, and Safe Mode; `MainFrame` gains a `VerbosityCommandsMixin` and registers eight `verbosity.*` commands (palette- and Keyboard-Manager-reachable). `_announce` routes through the controller **only once the user engages verbosity**, so the default path is unchanged until then; once live, Quiet/Meeting suppress speech while the status-bar floor remains. Default chords (no conflicts; `quote_lines` keeps `Ctrl+Shift+Q`): Quiet = QUILL key + Q, Meeting = QUILL key + Shift+Q, Verbosity Undo = `Ctrl+Shift+Z`. Eight scalar `verbosity_*` settings persist (mastery, validation mode, history, task-profile suggestions, Safe Mode); collection-typed state lives in `verbosity_custom.json`. Tests: `test_verbosity_controller.py`, `test_verbosity_settings.py`, `test_verbosity_wiring.py` (incl. a `quote_lines` regression guard). GATE-11 rebaselined (`settings.py` 933→971, `main_frame.py` 25295→25355). Sub-PR 1.6 (the "100-item addendum") was **consolidated** during the 2026-06-21 tracker cleanup into the deduplicated *Polish backlog* in `docs/planning/verbosity-system.md` rather than built as 100 separate items: the themed survivors are tracked there (several already shipped as settings knobs and profile recipes), and the screen-reader-redundant ideas (typing/command echo, speech-rate knobs, punctuation profiles) are recorded as "recommend do not build." **Live in-app behavior (chords firing, mode suppression, badges) warrants a manual smoke run before release.**

### Verbosity system (the UI)

- **Verbosity rebuild — the wxPython UI landed (#364).** Sub-PR 1.4 adds the user-facing surfaces, all A11Y-4 hardened (label-then-control, mnemonics, `SetName`/`SetHint`, `apply_modal_ids`, no icon-only buttons) and wired to the already-tested pure core. New under `quill/ui/`: `verbosity_prefs.py` (the embeddable preferences panel — profile picker, the four-channel mix with the always-on Visual floor, validation-mode and mastery boxes, a filterable verb table with master/detail, initial focus on the filter), `verbosity_token_editor.py` (Simple/Advanced **RadioBox** view per the §5 decision, `Ctrl+T` validate / `Ctrl+Shift+P` preview via `EVT_CHAR_HOOK`, Save disabled while errors exist, Speak-current-template and Insert-token), `verbosity_data_order.py` (Move Up/Down/Reset/Preview), `verbosity_chord_editor.py` (per-chord overrides), `verbosity_library.py` (template CRUD + Install QVP), `verbosity_qvp_install.py` (pick → validate → install with the spoken sequence and accepted/rejected/warnings read-back), `verbosity_history.py` (review/replay/copy/explain with a filter), `verbosity_preview_lab.py` (the 14 scenarios with per-channel output), `verbosity_safe_mode.py` (scoped non-destructive resets), and `verbosity_import_export.py` (data-only profile import/export). The 3-tab About dialog already ships (About Quill, #260). The dialog inventory was regenerated (12 new hardened surfaces) and the A11Y-4 banned-pattern, button-contract, escape-z-order, and GATE-11 gates all pass. Tests: `tests/unit/ui/test_verbosity_ui.py` (62 source-contract cases). The dialogs are not yet launched from menus/chords — that wiring (and the user-guide/release-notes coverage) is sub-PR 1.5 (#365).

### Verbosity system (QVP packs, library, preview)

- **Verbosity rebuild — QVP packs, template library, and scenario preview landed (#363, closes §20 #382).** Sub-PR 1.3 adds the shareable-pack and preview core, still wx-free. New `quill/core/schemas/qvp.json` defines the canonical `.qvp.json` format (§20). `quill/core/verbosity/qvp.py` loads and validates packs **by hand** (QUILL ships no jsonschema runtime dependency) and runs the §21 install flow — JSON → schema → `kind` → `min_quill_version` gate → metadata → template ids → namespace collisions → dependency check → validate each template against its target verb → install → announce — returning a `QVPInstallResult` (`accepted`, `rejected_templates` with reasons, `warnings`, and the spoken sequence). Packs are strictly data: there is no `exec`/`eval`/`__import__` path, asserted by test. `library.py` is the templates library: a flat collection across built-in / user / QVP sources with save/rename/delete CRUD and the cross-verb *apply* that strips tokens a verb doesn't track and reports them ("Removed 2 tokens because this verb does not track them: cell, region."). `preview.py` renders fourteen canned scenarios through the engine, surfacing per-channel output and decision metadata for the Preview Lab. `schema.py`'s QVP schema now loads from the canonical `qvp.json` (single source of truth). Tests: `test_verbosity_qvp.py`, `test_verbosity_library.py`, `test_verbosity_preview.py`, plus golden snapshots in `tests/golden/verbosity/` (220 verbosity cases total; qvp coverage 95%). Partial progress on §19/§21/§23 (#381/#383/#385) whose CRUD/install-dialog/lab UIs land with the UI sub-PR.

### Verbosity system (engine and runtime modes)

- **Verbosity rebuild — engine, modes, history, and stores landed (#362, closes §30 #392).** Sub-PR 1.2 builds on the foundation with the central routing engine and its companions, still wx-free and strict-typed in `quill/core/verbosity/`. No user-facing surface yet (chords, badges, and dialogs come with the UI sub-PR), but the decision layer is complete and the engine is now reachable from the assistant-panel and AI-Hub announce paths via a no-op `speak_legacy_text()` passthrough. New modules: `engine.py` (`VerbosityEngine.speak()` → `RenderedAnnouncement` + `ExplanationTrace`; decides template precedence per-chord → per-verb → QVP → default, routes channels with the always-on visual floor, applies Quiet/Meeting/Expert suppression and the per-profile sound policy), `quiet.py` (Quiet Mode + the bounded §11 undo stack), `meeting.py` (Meeting Mode), `mastery.py` (per-verb use counter that offers a step-down once at threshold, no nagging), `history.py` (bounded, filterable announcement history with token-value redaction on by default), `explain.py` ("Why did QUILL say that?" trace → plain copyable text), `safe_mode.py` (`QUILL_SAFE_MODE` detection + non-destructive scoped resets for verb/chord/all), `feedback_tuning.py` (local Too Much / Too Little / Just Right store with a gentle one-shot suggestion), `task_profiles.py` (opt-in, default-off per-extension profile suggestions), `import_export.py` (`.quill-verbosity-profile.json` import/export — strictly data, no code-execution path, schema-checked), and `storage.py` (atomic `verbosity_custom.json` read/write that degrades to empty defaults on a corrupt file). Tests: 11 new `tests/unit/core/test_verbosity_*.py` modules (180 verbosity cases total; engine coverage 96%). `assistant_panel.py`/`ai_hub_dialog.py` +6 each (GATE-11 rebaselined). Partial progress on §9/§10/§11/§24-§27/§29/§31/§35 (#371/#372/#373/#386/#387/#388/#389/#391/#393/#397) whose chord/badge/dialog halves land with the UI sub-PR.

### Verbosity system (core foundation)

- **Verbosity rebuild — pure-domain foundation landed (#361, closes §6/§12/§15: #368, #374, #377).** New wx-free, strict-typed `quill/core/verbosity/` package, the foundation the per-verb verbosity rebuild (`docs/planning/verbosity-system.md`) builds on. No user-facing behavior changes yet — the engine, runtime modes (Quiet/Meeting), and UI land in later sub-PRs. Modules: `channels.py` (`Channel(Flag)` with the always-on VISUAL accessibility floor + `route_channels`), `tokens.py` (`TokenSpec` + the twelve engine filters; **no custom filters** — the data-only security boundary), `parser.py` (strict `{name}` / `${filter:name}` / `${filter:arg:name}` parser that returns structured errors instead of raising, plus §13 `validate()` with token allowlist, filter-type checking, and the spoken summary), `profiles.py` (built-in Beginner/Normal/Expert/Quiet + `CustomProfile` JSON round-trip, and `active_profile()` — the first real consumer of the legacy `announcement_verbosity` knob, mapping minimal/normal/verbose onto the profile ladder), `verbs.py`/`registry.py` (`VerbSpec` + `Severity` + the 34-verb §15 catalog and a duplicate-protected `VerbRegistry`), `data_order.py` (frozen, hashable `DataOrder`), and `schema.py` (draft-07 schemas for settings, custom profiles, QVP packs, and import/export). Tests: `tests/unit/core/test_verbosity_*.py` (102 cases; parser coverage 99%). The §15 prose says "44 verbs" but enumerates 34; the catalog ships the enumerated 34 and the count is asserted from the catalog itself. Partial progress on §5/§7/§13/§14 (#367/#369/#375/#376) whose UI/engine halves remain open.

### Publishing and export

- **DAISY 2.02 text-only talking-book export (#251).** New **File > Export > DAISY Talking Book** turns the current buffer into a DAISY 2.02 text-only book that opens in DAISY software readers and on hardware players (Victor Reader Stream, Plextalk, APH units), or in APH Book Wizard Producer to add TTS audio. A DAISY book is a folder, so the chosen name becomes a folder holding `ncc.html` (Navigation Control Center with `dc:`/`ncc:` metadata and heading links), `content.html` (XHTML with an `id` on every readable element), and `book.smil` (a SMIL 1.0 reading-order container, zero-duration since the book is text-only). Headings become player navigation points; documents with no headings (or whose first heading is below `h1`) get a synthetic title `h1` so navigation stays well-formed; inline Markdown is flattened to readable text. The writer is wx-free and strict-typed in new `quill/io/daisy.py` (`write_daisy_textonly`) and reads the live editor buffer, so no save is required first. `main_frame.py` +63 and `main_frame_menu.py` +8 (GATE-11 rebaselined). Tests in `tests/unit/io/test_daisy.py` (well-formed XML, DAISY metadata, heading→SMIL→content reference integrity, inline-markup stripping, synthetic-heading promotion). Completes Wave 1 / Phase 1.

### Planning and program management

- **Issue tracker consolidated to a 1.0 plan of record (2026-06-21).** `docs/planning/roadmap.md` was rewritten from a per-issue archive dump into the consolidated **QUILL 1.0 Plan of Record**, organized by workstream and naming the three sibling-product integrations being folded into QUILL: **BITS Whisperer** (speech/dictation, brand retained; `s:\code\bw`), **GLOW** (accessibility audit + agents; `s:\code\glow`), and **ChapterForge** (audio → chaptered audiobook/podcast; `c:\code\forum`). The GitHub tracker was reconciled to match: **open issues dropped from 232 to 80.** Closed 152 with pointers to their new home — the 100 verbosity brainstorm addenda (deduplicated into a themed polish backlog in `verbosity-system.md`, with screen-reader-redundant ideas like typing/command echo and speech-rate knobs recorded as "recommend do not build"), 11 AI placeholders (→ the Agentic AI PRD), 30 Tier-6 documentation stubs (→ a Docs & Tutorials track), 7 content-free FEAT stubs (no recoverable intent; their source `planning.md` was deleted), localization (already shipped), 3 Linux issues (out of scope), and 3 meta/archive placeholders. The GLOW integration (#528–#534, #593–#598) and BITS Whisperer (#515, #566–#577, #617, #663) stay open as live 1.0 workstreams.

### Planning and program management (earlier)

- **Issue tracker consolidated into shipping workstreams.** The full text of every open planning/design issue was gathered into consolidated workstream specs under `docs/planning/` (`verbosity-system.md`, `roadmap.md`, `braille-mode-backlog.md`, `feature-backlog.md`) with no content loss; the issues remain open and individually tracked. `docs/planning/program-tracker.md` is the living tracker — buckets, per-bucket risk/impact/value/effort, priority totals, status, and execution waves — driving every open issue to closure by **shipping** it.
- **Offline speech & dictation plan (#617).** `docs/planning/dictation-and-speech.md` grounds the offline speech-to-text provider architecture in the current code (today dictation only shells out to Windows dictation; the vosk/whisper settings are dead stubs) and lays out a bold-but-simple reengineering: one offline-first speech engine, two user verbs (Dictate / Transcribe), an accessible model manager, captions, and gated voice commands that reuse the agent `SAFE_TOOL_IDS` allowlist.

### Braille Mode (Phase 3 — proofing and progress)

- **BRF sidecar foundation (BR-015, #238).** New `quill/core/brf_sidecar.py` persists per-file braille-workflow state — last position, proofing progress, page anchors, and notes — alongside a braille file as `<name>.brf.quill.json`. Reads/writes are atomic (`storage.write_json_atomic`); the braille file is never modified; malformed sidecars raise a clear `BRFSidecarError`; a missing sidecar reads as `None`. Pure, wx-free, strict-typed, with round-trip / atomicity / validation tests in `tests/unit/core/test_brf_sidecar.py`. Foundation for restore-on-open (#239) and the Proofing submenu (#240).
- **Restore last position on opening a braille file (BR-016, #239).** Reopening a `.brf`/`.brl`/`.pef`/`.ueb` file now returns the caret to where you left off (from the sidecar) and announces it, e.g. "BRF file opened. 87 braille pages detected. Last position: braille page 12, line 14, cell 31." Restore is skipped in safe mode and when sidecar saving is off; a stale offset past the end of an edited file is clamped. Pure logic in new `quill/core/brf_progress.py`; the open flow delegates its announcement to a thin `main_frame_braille._brf_open_message` handler (`main_frame.py` unchanged, net zero). Tests in `tests/unit/core/test_brf_progress.py` and `tests/unit/ui/test_brf_open_restore.py`.
- **Braille > Proofing submenu (BR-017, #240).** Eight keyboard commands for braille proofing: Mark Current Page Proofed / Needs Review / Clear Mark, Add Proofing Note, Read Progress Summary, List Proofed Pages, List Pages Needing Review (both jump to the chosen page), and Export Proofing Report (to `.txt`). All state is written to the per-file sidecar (the braille file is never modified). Pure logic in new `quill/core/brf_proofing.py`; the submenu and handlers live in new `quill/ui/main_frame_braille_phase3.py` (`BrailleProofingCommandsMixin`, MRO-layered like Phase 2; `main_frame.py` +2 for the import + MRO insertion). Commands degrade gracefully on non-braille or unsaved documents. Tests in `tests/unit/core/test_brf_proofing.py` and `tests/unit/ui/test_braille_proofing.py`.
- **BRF layout validator (BR-018, #241).** New pure, read-only `quill/core/brf_validator.py` walks a braille document and emits `BRFWarning` records across ten categories: line-too-long, page-too-long, page-too-short, missing form feeds, mixed line endings, non-NABCC characters, malformed page-separator indicators, page-numbering gaps/duplicates, running-head inconsistency, and Unicode-braille-as-BRF. Each warning carries offset/line/page, a speakable message, and a severity. The validator never modifies the text. Tests in `tests/unit/core/test_brf_validator.py` (every category, a clean-document baseline, and the bundled corpus sample). The Validation submenu + Warnings List dialog is #242.
- **Braille > Validation submenu (BR-019, #242).** Four commands wire the validator (#241) into the editor: Validate BRF Layout (runs the validator and opens an accessible Warnings List — choose a warning to jump to it), Next Warning and Previous Warning (step the caret through findings, announcing "Warning N of M: ..."), and Warnings Summary (total count and top three categories). Added to the Phase 3 mixin (`BrailleProofingCommandsMixin`) — no new MRO insertion; the Warnings List is a stock `wx.SingleChoiceDialog` registered as native in the dialog inventory. Tests in `tests/unit/ui/test_braille_validation.py`. With this, **Braille proofing and validation (Phases 3 and 4) are complete.**
- **Selection-aware braille back-translation (BR-023, #246).** **Back-Translate (draft)** (Braille > Translation) now back-translates the **selected** braille passage when there is a selection, and the whole document otherwise, announcing which it used ("Back-translation draft from selection/document. N words. Review against the BRF."). This completes the back-translation deliverable of #246 — letting a proofreader recover the source text of a single passage. Tests in `tests/unit/ui/test_braille_translation.py`. (The separate "compare back-translation with source" feature was descoped; per-page source linking remains out of scope, needing a cross-format Source-Position model.)

### Speech and dictation

- **Dictation engine setting made honest (Speech wave S0, #617).** `settings.dictation_engine` moved to the `offline`/`windows`/`cloud` model with default `windows` (the only functional engine today); legacy `vosk`/`whisper` values migrate to `offline` to preserve local-engine intent. The dead `_transcribe_audio` local-recognizer stub (no audio capture was ever wired up) was removed, and `quill/core/dictation.py` now documents plainly that dictation drives the OS dictation panel until the offline engine lands. No change to dictation behavior; `settings.py` stayed at its GATE-11 budget. Tests in `tests/unit/core/test_dictation.py` and `test_settings_migration.py`.
- **Offline speech-to-text foundation (Speech wave S1, #617).** New pure, wx-free `quill/core/speech/` package: a typed provider protocol + data model (`provider.py` — `SpeechToTextProvider`, model/segment/result records), TXT/SRT/VTT/JSON output formatters (`formatters.py`), an atomic installed-model store (`models.py`), a lazy provider registry that skips unavailable/broken providers (`registry.py`), and a curated whisper.cpp model catalog with accessible size/accuracy/speed descriptions (`catalog.py`, recommending the Small model). No heavy dependencies and nothing imported at startup; the whisper.cpp provider, model-manager UI, and transcription/dictation flows build on this in S2–S3. Tests in `tests/unit/core/speech/`.
- **Offline transcription + model manager (Speech wave S2, #617).** A new **AI > Speech** menu makes private, on-device transcription discoverable: **Manage Speech Models...** (download or remove whisper.cpp models — sizes shown, downloaded over verified HTTPS from the Hugging Face Hub whisper.cpp repo, blocked in Safe Mode) and **Transcribe Audio or Video (Offline)...** (pick a file; QUILL transcribes locally on a background thread and opens the draft transcript in a new document). The `WhisperCppProvider` drives a whisper.cpp CLI via `run_subprocess_safely` with a narrow executable allowlist; the new outbound model download is recorded in the network-egress audit. Logic lives in `quill/core/speech/` + `quill/ui/main_frame_speech.py` (`SpeechCommandsMixin`); the two stock dialogs are registered native in the dialog inventory. Requires the offline speech engine (see below) and a downloaded model. Tests in `tests/unit/core/speech/` and `tests/unit/ui/test_speech_commands.py`.
- **Offline dictation, captions, microphone selection, and a bundled engine (Speech wave S3, #617).** AI > Speech gains: **Generate Captions (Offline)...** (transcribe with timestamps, save as SRT/VTT), **Dictate (Offline)** (push-to-talk: speak into the document at the cursor as one undoable edit; bound to **QUILL Key + Shift+D**, with distinct start/stop earcons via the `transcription_started`/`transcription_stopped` sound events and status-bar state), and **Dictation Microphone...** (choose the input device; saved in `<data>/speech-settings.json`). Mic capture uses the optional `sounddevice` extra (`quill[speech]`), lazily imported with a clear fallback to Windows dictation. **The whisper.cpp engine is now a distributable component**: a new installer component ("offline speech engine (whisper.cpp)") installs it to `tools\speech\whispercpp`, the build script gains `--whisper-dir` staging, and `resolve_whisper_executable` searches the QUILL-managed locations (`{QUILL_APP_ROOT}/tools/speech/whispercpp`, `<data>/speech-engine`) before PATH — so users no longer install whisper.cpp separately or edit PATH. New `quill/core/speech/capture.py` (+ device enumeration), `quill/ui/main_frame_speech.py` commands, keymap binding, and tests; the speech commands are registered for the command palette.
- **Transcript formats and speaker attribution (Speech wave S3, #617).** Transcribe (Offline) now asks for a transcript format — **Plain text, Markdown, or HTML** (captions remain SRT/VTT) — via new `formatters.to_markdown`/`to_html` (the existing `to_plain_text` gains speaker support). **Speaker attribution** ("who is speaking when") is produced offline with whisper.cpp tinydiarize: the catalog adds a "Small English with speaker detection" model (`small.en-tdrz`), `TranscriptionRequest.diarize` adds the `-tdrz` flag, the parser turns `[SPEAKER_TURN]` markers into `Speaker 1` / `Speaker 2` labels on each `TranscriptionSegment`, and transcripts render those labels (bold in Markdown/HTML). Transcribe auto-enables diarization when the speaker model is installed. **`sounddevice` is now bundled** in the Windows build (added to the bundled dependency groups), so offline dictation works out of the box. Tests in `tests/unit/core/speech/test_formatters.py` and `test_whispercpp.py`.

- **Faster Whisper engine (Speech wave S4, #617).** Added an optional, GPU-aware second offline engine. New `quill/core/speech/providers/fasterwhisper.py` (`FasterWhisperProvider`) loads a CTranslate2 model directory in-process, auto-selecting CUDA/float16 when a GPU is visible and CPU/int8 otherwise (`pick_device_and_compute`), and maps library segments to QUILL's `TranscriptionSegment` (`segments_from_faster_whisper`, unit-tested). A Faster Whisper model catalog (`catalog.FASTER_WHISPER_MODELS`, incl. `distil-large-v3`) downloads CTranslate2 repos from the Hugging Face Hub via `huggingface_hub.snapshot_download` (Safe-Mode gated). `default_registry` registers it only when the optional `fasterwhisper` extra imports, so an uninstalled engine never appears. The new `settings.speech_provider` (`""`/`whispercpp`/`fasterwhisper`) plus a **Speech Engine** chooser in Manage Speech Models lets users pick the engine; the choice drives transcription, captions, and dictation. whisper.cpp remains the default and needs nothing extra; Faster Whisper does not attribute speakers. Tests in `tests/unit/core/speech/test_fasterwhisper_provider.py`.
- **In-app display-language switcher (#i18n).** **Tools > Writing & Language > Change Display Language...** lists every installed translation plus System default and saves the choice to `settings.language`, re-initialising the locale (`available_languages`/`language_display_name` in `quill/core/i18n.py`). Translations are now submission-ready: the `.pot` template was regenerated from source, `quill.tools.compile_translations` builds `.mo` files via Babel (no `pybabel` CLI), and `quill/locale` is packaged into the wheel. The context-help coverage gate (`check_help_coverage`) was repaired (it pointed at the wrong path and checked nothing) and now validates topic integrity and flags commands missing help, with `--scaffold` to add stubs. Tests in `tests/unit/core/test_i18n.py`, `tests/unit/tools/test_help_coverage.py`, and `tests/unit/tools/test_compile_translations.py`.

### Build and naming

- **Public name is now QUILL for All.** The 0.7.0 release adopts `QUILL for All` as the user-visible project name in the About dialog, installer, crash reports, support bundles, and the repository README. The old `Quill` short name remains as `APP_SHORT_NAME` for legacy menu and shell-verb entries so the right-click "Open in Quill" verbs keep working. The new public name is paired with a one-paragraph Independence Notice that names Quill.js, QuillBot, and Quill.org so a first-time user can tell the project apart from similarly named products.
- **Trademark and legal docs.** New top-level `TRADEMARKS.md` and `NOTICE` files codify the naming policy and short copyright; `docs/legal/legal-notices.md` and `docs/legal/trademark-notices.md` carry the longer legal text. The repo no longer claims a registered trademark anywhere; all references are descriptive. `tests/unit/tools/test_legal_docs.py` and `tests/unit/core/test_branding.py` guard against future drift.
- **Single source of truth for the build identity.** New `build/version.toml` (base version, channel, prerelease number, product name, publisher, website) is read by `tools/generate_build_info.py` to produce `quill/_build_info.py` (consumed by the About dialog, support info, and crash reports) and `build/build-info.txt` (for humans and support). `quill/build_info.py` is a safe read wrapper that falls back to dev-build defaults if the generated module is missing. `quill/branding.py` carries the user-visible name constants so the About dialog, README, and crash reports always agree. `quill.core.about_info.AboutInfo` is refactored to consume the new sources and adds `product_name`, `display_version`, `license_name`, `independence_notice`, and `support_info` fields.
- **InnoSetup installer is wired to the same source.** `scripts/build_windows_distribution.py` now reads product name and publisher from `build/version.toml` (via the new `_build_identity` helper) so the installer's `AppName`, `AppPublisher`, `OutputBaseFilename`, and Add/Remove Programs metadata stay in lockstep with the About dialog. The `installer/quill.iss` filename pattern moved from `Quill-Setup-X` to `Quill-for-All-Setup-X` to match. The GATE-VC version-consistency gate now resolves the canonical version from `build/version.toml` when present, so the About dialog, installer, and CHANGELOG must all agree on the same display version.
- **About dialog gains a Legal tab and a Copy Support Info button.** The native 4-tab `About QUILL for All` dialog (Overview / Legal / Dependencies / Links) shows the Independence Notice, copyright, license name, and support info on the Legal tab; the dialog title is dynamic (`f"About {product_name}"`); the new **Copy Support Info** button writes the `support_info` string to the clipboard for inclusion in bug reports.

### QUILL Key branding and menu label clarity

- **QUILL Key chord shown as `QUILL Key + <key>` in every user-visible surface.** The 0.7.0 release replaces the raw `Ctrl+Shift+Grave, <key>` form with the branded `QUILL Key + <key>` form across menus, the About > Keyboard Reference page, the QUILL Key Help dialog, the QUILL Key cheat sheet, and the status bar / announce messages emitted while a chord prefix is pending. The stored binding (`Ctrl+Shift+Grave` in `DEFAULT_KEYMAP` / `keymap.json` / `quill_key_binding` setting) is unchanged — only the user-visible label moves. New `quill.core.keymap_format.format_binding_for_display` and `format_quill_key_chord` are the single source of truth for the rewrite; `quill.branding.QUILL_KEY_LABEL = "QUILL Key"` is the single source of truth for the constant. Test coverage: 18 cases in `tests/unit/core/test_keymap_format.py`.
- **A 4th `menu_lint` invariant guards against binding/label drift.** `quill.tools._check_binding_label_consistency` walks the AST of `quill/ui/main_frame_menu.py` and flags three regression classes: (a) `self._menu_label("", "command.with.binding")` patterns where the title literal is empty for a command that has a keybinding, (b) hand-written `<name>\t<binding>` literals whose tab portion disagrees with the matching `DEFAULT_KEYMAP` entry or wx stock-id binding, and (c) labels that end with a trailing tab and no binding portion. The runtime gap-check in `MainFrame._menu_label` (a one-shot `logger.warning` per affected item at first menu build) is the safety net for user-customization drift. The new check is wired into `python -m quill.tools.menu_lint` and exposed via 12 new cases in `tests/unit/tools/test_binding_label_consistency.py`.
- **Product name and publisher no longer hard-coded in tools and scripts.** `tools/generate_build_info.py`, `scripts/generate_update_feed.py`, and `scripts/build_windows_distribution.py` all read `APP_DISPLAY_NAME` and `APP_ORGANIZATION` from `quill.branding` so a rebrand touches one file. The TOML path still wins when `build/version.toml` provides a value (the installer / feed can be re-branded per release); the constant is the safety net for older checkouts and dev builds.

### Doc fixes

- **AI Hub menu path canonicalized to `AI > AI Hub...`** (#335). The release notes, the user guide, and the PRD no longer refer to a `Tools > AI Hub` alternative or to a `Tools > AI Assistant > AI Hub...` path. All paths now match the actual menu registered by `quill/ui/main_frame_menu.py`.
- **Update feed note + new `RELEASE.md` checklist** (#334). The 0.7.0 Beta 1 note already points at 0.5.0 to prevent a phantom update bump; the new `RELEASE.md` file documents the full pre-tag checklist and the tag-time flip step, and is linked from this section so the next release rotates the feed cleanly.
- **`quill.pot` version stamp + extraction freshness** (#336). `quill/locale/quill.pot` carries `Project-Id-Version: QUILL 0.7.0` and a fresh `POT-Creation-Date`. The POT was regenerated via `pybabel extract`; 402 new msgids were picked up from the post-0.6.0 source drift.
- **Translations: POT-only ship** (#340). The release notes now state explicitly that no `.po` or `.mo` files ship. The release notes point to `docs/translating.md` and `MAINTAINERS.md` for the translation contribution path.
- **Keymap consolidation: AI and compare chords on the same `Ctrl+Alt+Shift+` chord class** (#357). The inline F7 / Shift+F7 / F8 / Shift+F8 / Ctrl+Shift+T accelerators on the AI Spell Check, AI Spell Check Interactive, AI Grammar and Style, Translate Selection, AI Thesaurus, Next Difference, Previous Difference, and Announce Difference menu items are removed; the same commands are now bound to `Ctrl+Alt+Shift+S` / `I` / `G` / `T` / `H` and `Ctrl+Alt+Shift+.` / `,` / `D` respectively. The 8 new bindings each carry the inline `# §edsharp-ok` justification comment naming the screen-reader binding they reserve the chord class against, paired with matching entries in `_CTRL_ALT_DOCUMENTED` in `quill/tools/menu_lint.py`. `view.toggle_dark_mode` moves to `Alt+Shift+D` (different modifier stack from the compare binding). `docs/keybinding-standard.md` and `docs/release notes/release0.7.0.md` were updated; `docs/CONTROL_REFERENCE.md` was regenerated.
- **`quill/ui/style_panel.py` renamed to `quill/ui/train_style_dialog.py`** (#328). The Train Writing Style dialog's filename now matches its class. The rename updates the `quill/ui/main_frame.py` import site, the `tests/unit/ui/fixtures/dialog_inventory.json` qualname, the `tests/unit/ui/test_ai_tool_dialog_async_contract.py` source-path argument, the two PRD references (sections `3783` and `5963`), the `dialogs.md` and `.github/copilot-instructions.md` module lists, and the historical 2026-06-11l rebaseline comment in `quill/tools/module_size_budgets.json`. The new file (184 lines) is under the default 600 cap, so no explicit budget entry was needed.
- **`sound_manager.py`: promote `is_unsafe_path` and add public `set_volume`; unregister indent overlay events on every reload** (#332). `quill.core.sound_pack.is_unsafe_path` is the public traversal guard (the private `_path_is_unsafe` alias is kept so the loader's own validator does not have to round-trip through itself). `quill.platform.sound_player.SoundPlayer.set_volume(volume)` is the new public method for the master output level (clamps to `[0.0, 1.0]`, no-op on backends without a volume control, never raises). `SoundPlayer.unregister_event` and `SoundPlayer.unregister_events` are new public APIs used by the indent tone overlay so its events are explicitly removed on every reload, including `load_indent_tone_pack("")`. `quill/ui/sound_manager.py` no longer reaches into `_backend._output` or imports `_path_is_unsafe`. New tests: `tests/unit/platform/test_sound_player.py` (six new cases for `set_volume` / `unregister_event` / `unregister_events`) and `tests/unit/ui/test_sound_manager.py` (the new public-API-hygiene + indent-overlay-unregister guard).
- **`build_session_payload`: pair documents and caret positions via `zip(strict=True)` with an invariant assert** (#304). `quill/core/sessions.py` defaults missing caret positions to `0` for leniency, then asserts the lengths match before calling `zip(documents, positions, strict=True)`. A regression that breaks the length invariant now turns into `AssertionError` or `ValueError` instead of silently dropping trailing documents. Three new tests in `tests/unit/core/test_sessions.py` cover the padded-short input, the exact-length input, and the default-None input.
- **Trust-consent re-consent prompt on disclosure update** (#305). `quill/core/onboarding.py` now ships `current_trust_consent_version`, `trust_consent_change_log`, and `load_trust_consent_status` so the onboarding flow can distinguish "never consented" from "consented to an older disclosure". The trust consent version bumps to `2` with a delta naming the new BITS Whisperer, Glow update, and local-Quillin permission model disclosures. `quill/ui/main_frame._show_trust_consent_onboarding` prepends the per-version delta as numbered bullet points and changes the dialog title to `Trust and Privacy Consent` when re-consent is needed; `_first_run_trust_consent_prompt` stays `True` for users with stale consent so the prompt re-fires on next launch. Seven new tests in `tests/unit/core/test_onboarding.py` cover missing-file, current-version, older-version, malformed-version, non-dict, the reconsent helper, and the change-log invariant.
- **`documents_from_session` distinguishes missing key from empty list** (#342). `quill/core/sessions.py` now returns a single untitled `Document` only when the `documents` key is absent (sentinel for "no session seen") or when the value is non-list (malformed payload). An explicit `"documents": []` round-trips as an empty list, so a session saved with no open documents now restores with no open documents. Four new tests in `tests/unit/core/test_sessions.py` cover the missing-key, empty-list, non-list, and round-trip paths.

## 0.7.0 — Meet You Where You Are, with Braille Mode Phase 2 (2026-06-18)

### EdSharp port

- **Section-move chord pair** (`Alt+Shift+Up` / `Alt+Shift+Down`).  Pressing the chord while the caret is on a Markdown or HTML heading swaps that section with its previous (or next) sibling at the same level.  The move announces the sibling heading it swapped with.  Plain-text documents announce the chord is unavailable.  Fenced code blocks are honored so a `# fake` line inside a ``` fence is never promoted to a real sibling.  The chord displaced the previous expand/shrink selection pair, which migrates to the QUILL-key chord (`Ctrl+Shift+Grave, J` / `Ctrl+Shift+Grave, Shift+J`); saved user keymaps from older builds route through `legacy_rebindings`.
- **Heading shortcuts** at `Ctrl+Alt+1..6` (EdSharp PR #3).  The six heading shortcuts move from the QUILL-key chord space to `Ctrl+Alt+1` through `Ctrl+Alt+6`.  Each chord carries an inline `# §edsharp-ok` justification comment naming the screen-reader binding it overrides (NVDA's switch-to-synth-1..6) and a paired entry in `_CTRL_ALT_DOCUMENTED` in the menu-lint gate.
- **List toggle** at `Ctrl+Alt+7` and `Ctrl+Alt+8` (EdSharp PR #3).  `Ctrl+Alt+7` toggles a bullet list; `Ctrl+Alt+8` toggles a numbered list.  Each chord inspects the caret: if it is on a list item, the markers are stripped; otherwise a new list is inserted.  Plain-text documents announce the chord is unavailable.  Numbered-list insertion is governed by a new `list_auto_fill_numbers` setting (Preferences -> Editing -> Lists, default off) and a per-document five-minute arming flag set when the user toggles a numbered list; the three OR together so writers can stay in fill mode without re-pressing the chord.  New menu entries: Insert -> List -> Toggle Bullet / Toggle Numbered.  `Ctrl+Alt+9` for link insertion is intentionally not added because `Ctrl+K` already covers that command.
- **Section status bar cell**.  New `Section` cell that reads `Section: Heading N (ordinal of total)` whenever the caret is on a heading in a Markdown or HTML document.  Hidden by default; opt in via Preferences -> Status Bar.  Plain-text documents and carets on non-heading lines show nothing; the cell inherits the dead-widget guard from the other live-editor cells so a queued caret event after Ctrl+F4 cannot crash the status-bar refresh.
- **Revised §10.8 Ctrl+Alt+ policy**.  The original §10.8 policy banned `Ctrl+Alt+` outright.  The 0.7.0 revision relaxes the rule but keeps the gate strict: a `Ctrl+Alt+` binding may enter `DEFAULT_KEYMAP` when it is in the `_CTRL_ALT_DOCUMENTED` allowlist **or** carries an inline `# §edsharp-ok` justification comment naming the screen-reader binding it overrides.  Unjustified bindings still fail the gate.  Full audit in `docs/keybinding-standard.md`.
- **Copy Tray binding drift guard**.  New `quill.tools.check_copy_tray_binding` gate ensures the 12 Copy Tray paste slots (`Ctrl+Shift+1..9`, `Ctrl+Shift+0`, `Ctrl+Shift+-`, `Ctrl+Shift+=`) keep their default bindings.  A future change that reassigned any of those chords would now fail the gate.  The gate is automatically delegated from `menu_lint` so a single `python -m quill.tools.menu_lint` invocation covers all keymap and menu structural invariants.
- **Heading Organizer duplicate-H1 check is opt-in (#303).** A new `heading_organizer_warn_duplicate_h1` setting (default `False`) lets authors who deliberately write multi-H1 works opt into the duplicate-H1 accessibility warning. Existing behaviour is preserved for users who do not toggle the setting on. The setting lives in `quill.core.settings.Settings` and is read by the Heading Organizer's `Validate` button; the validator itself (`validate_heading_sequence`) keeps its `require_single_h1` keyword argument for unit tests and programmatic callers.
- **Dictation device picker deferred to 0.7.1 (#308).** The **Choose Dictation Device** menu entry planned for the Reading & Dictation submenu has been pulled from this release. The underlying infrastructure (`quill.core.dictation.list_dictation_devices` plus the `dictation_device_index` setting) is in place, but the menu surface and dialog contract were not finished in time for a quality release. The picker ships in 0.7.1 with a dedicated dialog. Until then, QUILL uses the system's default dictation input.

### Braille Mode Phase 2

- **Print-page and running-head detection (BR-013).** `quill/core/brf_page_detection.py` walks the BRF page map once and emits confidence-labelled indicators: high (separator line with anchor, or right-margin continuation), medium (right-aligned number), low (ambiguous). The detector also produces a `BraillePageMarker` per page and a `RunningHead` per page. When the detector has no anchor for the caret page, the status bar's print segment reads `Print ?` so the fallback is visible, not silent. Pure module — imports nothing from `wx` — covered by 12 unit tests including a real-world corpus test against the 5-page sample at `tests/corpus/braille/one_crazy_night.brf`.
- **Detailed status and print-page navigation (BR-014).** Six new Braille menu commands: Go to Print Page, Next/Previous Print Page Change, Announce Running Head, Include/Omit Running Head in Status. `Read Detailed Braille Status` now composes the full example string from the spec (print page, continuation letter, running head, proofing state, detection confidence) and `Read Current Print Page` no longer hard-codes "Print page unknown". Default key bindings intentionally left unset (matching the Phase 1 convention). Phase 2 is split into its own `main_frame_braille_phase2.py` mixin to keep `main_frame_braille.py` under the GATE-11 module-size budget.
- **Planning consolidation.** The 6,700-line `docs/planning/braille.md` was rolled into `docs/planning/planning.md` under "Feature: Braille Mode" so the live roadmap stays the single source of truth; the standalone file and its `.html`/`.epub` siblings were deleted; structure tests now assert it cannot reappear.

### Bug fixes (post-review triage)

- **Keymap: dead legacy-preview migration deleted.** `merge_keymaps`'s `legacy_preview_conflict` block checked the new chord defaults instead of the legacy ones, so it never fired for a real saved keymap; `legacy_rebindings` already migrates the same case correctly. Deleted per the locked decision on #274. Also removed an exact-duplicate comment block (#282) and added a debug log when `list_keymap_profiles` drops a malformed profile JSON instead of silently skipping it (#299).
- **Keymap: settings carry-over on load.** `quill.core.keymap.load_keymap` now drops saved entries whose command id is no longer in `DEFAULT_KEYMAP`, whose chord is whitespace-only, or whose chord collides with another command in the merged map, and persists the surviving subset back to disk so the on-disk `keymap.json` reflects what was actually honored. Files that are already clean are left untouched. Documents the Beta 2 settings carry-over rule in `docs/release notes/release0.7.0-beta2.md`; a standalone migration utility remains on the roadmap.
- **Section move: explicit enum match.** The edge-case announce branch in `_move_section` matched `MoveResult.NO_SIBLING` via a bare `else`; a future enum member would have silently announced the wrong outcome. Now every member is matched explicitly with a defensive fallback (#322).
- **Screen-reader name/focus gaps closed across five dialogs/panels.** Notebook panel name/goal labels and entry controls gain `SetName` (#327); the rich-text mode toggle button and indicator label gain `SetName` (#326); `SessionBrowserDialog._on_jump` now focuses the branch list after rebuilding it (#324); `status_dialog.py` converts its five `name=` kwargs to post-construction `SetName()` calls for consistency with the rest of the codebase (#320); the Command Palette and Go to Anything search fields gain `SetHint` placeholders in addition to their existing `SetName` (#325).
- **Removed orphaned `whisperer.about` menu-id scaffolding.** A `wx.NewIdRef()` and its `Bind()` call had no menu item wired to them; deleted both plus the stale `_command_to_menu_id_map` entry. The command itself remains live via Command Palette / Go to Anything (#284).
- **`kqp_validator._validate_file` renamed to `validate_file`.** The function is imported across the core/tools boundary, so the leading underscore was misleading (#290).
- **Copy Tray binding gate now discovers bundled profiles instead of hard-coding them.** `check_copy_tray_binding` previously checked only two named profile files; it now globs `profile_*.json`, so `profile_minimal.json` and any future bundled profile are covered automatically (#285).
- **Removed two never-shipped `future.*` feature placeholders; fixed `core.dictionary`'s dead command mapping.** `future.character_inspector` and `future.regex_library` had zero backing commands anywhere in the codebase and were deleted from the catalog and profile tables. `core.dictionary` (Dictionary and Thesaurus) was a real dead mapping: `tools.thesaurus` is now mapped to it in `feature_command_map.py`, so disabling the feature correctly hides the command from the Command Palette (#306).
- **Copy Tray accessibility: search-result announcement, status label, and modal-dialog delegation.** `_TraySearchDialog` now announces the first auto-selected search result after `SetSelection(0)` (#330). `CopyTrayDialog` gained a dedicated status `StaticText` plus a `_set_status` helper (SetLabel + announce) so ephemeral status messages (slot loaded/saved/cleared/pinned) no longer overwrite the listbox's stable accessible name (#329); `.show()` now delegates to `show_modal_dialog` instead of calling `ShowModal()` directly (#323).
- **`SoundEventsDialog` section headings now have an accessible name.** Each bold section heading gains `SetName(f"{heading} heading")` (#331).
- **Security: Heading Styles CSS/HTML injection fixed.** `HeadingStyle.declarations()` interpolated `text_align` and `font_family` unescaped into inline `style=""` attributes. `text_align` is now restricted to `{left, right, center, justify}`; `font_family` is HTML-escaped (#279).
- **F1 help for Copy Tray now matches the shipped 12-slot tray.** `topics.json` described the original nine-slot design (`Ctrl+1..9` paste, `Ctrl+Shift+T` open); updated to the real bindings (`Ctrl+Shift+1..9, 0, -, =` paste, `Ctrl+Shift+Grave, X` open) and regenerated `CONTROL_REFERENCE.md` (#276).
- **Version stamp swept to 0.7.0.** README, the userguide intro, both QUILL-PRD.md status lines, planning.md, translating.md, and quill.pot's `Project-Id-Version` all still referenced 0.5.0/0.6.0/0.6.1/0.1.5. Also collapsed CHANGELOG.md's two duplicate `## 0.6.0` headers into one (#277).
- **`Move Section Up`/`Down` menu ids were never wired.** `_id_move_section_up`/`_id_move_section_down` fed the global accelerator table (`Alt+Shift+Up`/`Down`) but had no `Append`/`Bind`, so the documented chord was silently inert outside the right-click context menu (which used its own local ids). Added real Format -> Line menu entries and frame-level bindings, matching the existing Move Line Up/Down pattern (#278).
- **`menu_lint.py`'s §10.3 required-cluster check now walks the AST instead of substring-matching.** A comment merely mentioning a cluster's label text (e.g. `"AI &Assistant"`) used to satisfy the gate; it now must appear as the label argument of a real `AppendSubMenu(...)` call, matching the rigor `_check_depth` already had (#286).
- **Snippet placeholders: full name/error contract.** `render_snippet` previously echoed a placeholder's raw `${kind:rest}` token verbatim into the document if no value was supplied; it now resolves through `extract_placeholders` and raises a `ValueError` naming the placeholder (e.g. `Workflow tested`), not just the token, so a caller no longer has to re-parse the token to report what's missing. `extract_placeholders` raises a clear error on an empty placeholder name or empty choice options instead of silently dropping the token. `_PLACEHOLDER_PATTERN` now allows one level of nested braces (`${input:Hello ${world}}`). `insert_snippet` and the `;trigger` auto-expand path catch the new error and report the snippet by name instead of crashing (#287).
- **AI Hub tab count: userguide.md was missing the Instructions tab.** It listed four tabs (Provider, On-Device, Audio Services, Advanced); release notes already correctly said five. Added the Instructions tab to the summary list (#293).
- **Profile/Quillin doc-drift resolved, code wins.** Release notes and the user guide disagreed on three points. Profile count: the wizard's seven `onboarding_profiles.py` intent profiles and the ten `features.py` technical FeatureProfiles are separate, already-accurate layers; added a cross-reference in the user guide instead of forcing one number. Writer/Casual Writer: adopted "Writer" (the wizard's canonical name) consistently in both docs, dropping the "renamed to Casual Writer" claim. Quillin count: `quill/quillins_bundled/` has fourteen directories, not five (release notes, which only ever described the new-in-0.7.0 set) or thirteen (user guide, which omitted Math Equations); reframed as fourteen bundled, five new in 0.7.0, nine carryover (#292).
- **F1 help for every braille command.** `quill/core/help/topics.json` now covers all 25 braille feature commands (status, navigation, page tools, translation, back-translation, pack install, line/cell, progress, save-as-clean, line-ending normalize). A new regression test in `tests/unit/tools/test_help_coverage.py` (`test_every_braille_command_has_a_help_topic`) walks `COMMAND_FEATURE_MAP` and fails CI if any new `braille.*` command is registered without a topic, preventing a future silent gap. Regenerated `docs/CONTROL_REFERENCE.md` to 134 topics with a new Braille Mode section (#294).
- **Release notes / user-guide contradiction on print-page detection removed.** Both documents now say the print-page segment is always populated when a print-to-braille anchor is available and reads `Print ?` only when no anchor exists, instead of the earlier "arrives in a later phase" claim. BR-013 has been live since 0.6.1 and is exercised by `quill/core/brf_page_detection.py` (#295).
- **Wizard page count corrected in release notes and user guide.** The setup wizard has six pages (Welcome, Intent, Extras, AI Provider, Keyboard and Sound, Summary) and five if you do not enable AI on the Extras page. Release notes line 80 was rewritten and the `docs/user guide/userguide.md` "Personalising QUILL" section was rewritten end-to-end so the page list (with the AI-conditional sixth page) and the profile summary table both match the canonical `quill/ui/setup_wizard_pages.py` (#297).
- **CommandRegistry gains `try_register` and `replace`.** `try_register(id, ...)` returns `bool` so tooling can detect collisions without catching `ValueError`; `replace(id, ...)` overwrites an existing entry for the rare case where a caller needs to take over a built-in command's slot. The original `register` behaviour is unchanged. Five new tests in `tests/unit/core/test_commands.py` (#312).
- **Markdown `apply_nl2br` now honours CommonMark fence semantics.** Previously it toggled on any line starting with three backticks; lines inside a tilde fence or with two backticks could be misidentified, and a tilde opener was never recognised. The fence detector now lives in a shared `quill/core/markdown_fences.py` module, recognises 3+ backticks and 3+ tildes (up to 3 leading spaces of indent), and a closing fence must use the same character as the opener and be at least as long. New tests cover tilde fences, four-backtick fences, the cross-character case (tilde opener is not closed by a backtick run), and the under-length closer case. `quill/core/markdown_extensions.py` no longer carries its own `startswith("```")` toggle (#307).

## 0.6.0 — Insert Automation, Quillin Platform, Braille Mode, AI Writing Toolkit (2026-06-17)

> Note: 0.6.0 was rolled into the CHANGELOG directly without a standalone `release0.6.0.md`; the section below is the canonical 0.6.0 record. The 0.6.1 release notes (`docs/release notes/release0.6.1.md`) are the first standalone post-0.5.0 release-notes file. (Closes #345.)

### Text hygiene

- **Quill Eraser.** `Tools → Writing & Language → Quill Eraser...` / `Quill Eraser on Selection...`. Deterministic, rule-based text hygiene checker: seven rules covering multiple spaces, trailing whitespace, space before punctuation, excessive blank lines, missing space after sentence/comma/colon punctuation, and lowercase sentence starts. Findings are presented in a modeless, keyboard-navigable review dialog with Apply Fix, Ignore, Go to Issue, Previous/Next, and Rescan actions. All actions are screen-reader-announced. Code files receive a prompt before checking; only safe trailing-space checks run unless you opt in. URLs, emails, file paths, code spans, decimal numbers, times, and (in Markdown) code blocks, front matter, and link URLs are never flagged. Four new preference fields control confidence threshold, two-space-after-period exception, max blank lines, and per-rule disable list. New files: `quill/core/hygiene/` package (findings.py, ignored_ranges.py, rules.py, engine.py), `quill/ui/hygiene_dialog.py`, `quill/ui/main_frame_hygiene.py`. New feature `core.hygiene` in the feature catalog. 41 unit tests in `tests/unit/core/test_hygiene_rules.py`.

### AI writing features

- **AI Hub (5-tab settings dialog).** `quill/ui/ai_hub_dialog.py` replaces the single-screen AI Connection dialog with a tabbed hub: Provider (provider choice, API key, model, test connection), On-Device (Ollama URL and recommended models), Audio Services (Deepgram key, max speakers), Instructions (custom system prompts per task), and Advanced (consent text, reset, safe mode docs). `open_ai_hub()` in `main_frame.py` now opens this dialog.
- **AI Thesaurus (Shift+F8).** `quill/core/ai/thesaurus.py` + `quill/ui/ai_thesaurus_dialog.py`. Sends the selected word and its surrounding context sentence to the configured AI provider and returns a list of synonyms with usage notes. Replace the word in-document from the dialog or double-click a synonym to apply immediately. Covered by `tests/unit/core/ai/test_ai_thesaurus.py` (16 tests).
- **Agentic writing tasks.** `quill/core/ai/agent_session.py` + `quill/ui/ai_agent_result_dialog.py`. Four new commands: AI > Rewrite Selection, AI > Summarize Selection, AI > Expand Selection (new), AI > Generate Table of Contents (new). Each runs on a background thread with a cancellation stop event and presents results in a two-part dialog (step log + final output) with Insert, Replace, Copy, and Re-Run actions. Covered by `tests/unit/core/ai/test_agent_session.py` (23 tests).
- **Custom Instructions.** `quill/core/ai/custom_instructions.py` provides per-task AI system prompts with user overrides. Twelve tasks ship with built-in defaults (chat, spell_check, grammar_check, rewrite, summarize, expand, toc, translate, thesaurus, document_qa, research, accessibility_agent). User overrides stored in `%APPDATA%\Quill\ai_custom_instructions.json` (only changed fields; defaults always from code). `apply_instruction(task_id, base_prompt)` is called by every AI module; it never raises — any failure returns the base prompt unchanged. Covered by `tests/unit/core/ai/test_custom_instructions.py` (22 tests).
- **Custom Instructions wired to all AI modules.** `apply_instruction()` integrated into spell check, grammar check, translation, thesaurus, document Q&A, and all four agent tasks. Users can change tone, format, or language model behaviour for any task without touching code.
- **Prompt caching.** `custom_instructions.py` gains `split_instruction(task_id, base_prompt) -> (str, str)` which returns the system prompt and user prompt as separate strings. `generate_assistant_response()` gains a `system_prompt` parameter; `build_chat_body()` and `build_chat_headers()` are extended to route the system prompt through each provider's caching path: Anthropic Claude uses `cache_control: ephemeral` blocks with the `anthropic-beta: prompt-caching-2024-07-31` header (5-minute cache, ~10% token cost); OpenAI/OpenRouter use a `role=system` message that qualifies for automatic prefix caching above 1024 tokens (~50% cost); Gemini uses `systemInstruction`; Ollama uses `role=system`. All six AI modules (spell_check, grammar_check, translation, thesaurus, document_qa, agent_session) updated from `apply_instruction` to `split_instruction`. 14 new tests in `test_assistant_ai.py` and `test_custom_instructions.py` lock in the caching contract per provider.
- **Expand Selection and Generate TOC agent profiles.** `assistant_agents.py` gains `expand` and `toc` profiles with carefully written default prompts.
- **Vision Prompt Library.** `quill/core/ai/vision_prompts.py` + `quill/ui/image_prompt_manager_dialog.py`. Twelve evaluated IDT-sourced image-description prompt styles, a management dialog, pre-describe picker, and "Try a different prompt" post-describe flow. Contributed by Kelly Ford. Settings sync bug fixed.
- **Image style prompt editing.** Built-in image description prompt text is now editable. `ai_hub_dialog.py` gains an Image Styles sub-tab within the Instructions tab. Each of Kelly's twelve styles shows a read-only reference panel (the shipped default) alongside an override editor and a Reset to Default button. Enable/disable is also surfaced here. `vision_builtin_overrides: dict[str, str]` added to `Settings`; `resolve_prompt_text()` checks overrides before the built-in constant. Saves on AI Hub OK; applied immediately on every subsequent Describe Image call.
- **Default AI writing prompts revised.** All twelve writing task default prompts in `custom_instructions.py` rewritten: tighter persona statements, explicit output rules (return only the text), screen-reader-aware guidance (prefer short sentences, direct language), and per-task specificity (accessibility agent now checks sentence length, jargon, passive voice, and link/image text; research assistant structures output into Claims, Key Points, Assumptions, Open Questions, Next Steps).
- **AI Hub Instructions tab restructured.** `_build_instructions_tab()` now renders a sub-notebook with two pages: Writing Tasks (existing twelve writing prompts) and Image Styles (Kelly's twelve image description prompts), unified under the same list + editor + reset-to-default UX.

### Accessibility fixes

- **JAWS label-buddy Z-order (#249).** Tabbing through Preferences dialogs under JAWS now announces field labels correctly. The fix converts every pre-created labeled control in `open_general_preferences/_make_control`, `open_profiles_and_features_settings`, and `ai_model_panel._build_tier_section` to factory callables so `StaticText` labels are always created before their associated `wx.Choice`/`wx.SpinCtrl`/`wx.TextCtrl` in the Windows child list. `wx.CheckBox` and `wx.Button` are exempt (they carry their own label text). Six gating tests in `tests/unit/ui/test_dialog_label_ordering.py` lock in the correct creation order. The Quillin preferences renderer (`quillin_prefs_dialog.py`) enforces label-first order throughout by construction.

### New features

- **Math Equations Quillin (`com.quill.bundled.math-equations`).** `Insert → Insert Equation...` (`Ctrl+Shift+E`) inserts LaTeX or MathML at the caret via two sequential accessible dialogs: a prompt for the equation text (with selection pre-fill and delimiter stripping) and a display-mode choice (Inline `$...$` / Block `$$...$$`). MathML input (`<math ...>`) is detected automatically and inserted verbatim without a mode step. Browser Preview and HTML export now inject MathJax 3 (CDN) so equations render visually. Sample equations in `docs/math/latex_testing.md`. 14 unit tests in `tests/unit/core/test_quillins_bundled_math_equations.py`. Contribution by Robert Danaraj; redesigned as a sandboxed Quillin.

- **Quillin preferences rendering.** All five bundled Quillins with `contributes.preferences` declarations now have live settings dialogs accessible from the Preferences hub. New `quill/ui/quillin_prefs_dialog.py` renders boolean (CheckBox), integer (SpinCtrl), string (TextCtrl), and choice (Choice) controls from the declarative manifest schema. Conditional `visible_when` and `enabled_when` rules are wired to wx change events so dependent controls update live. `main_frame_quillins.py` gains `_pref_manifests()` and `open_quillin_preferences()`. `open_preferences()` dynamically appends one hub entry per enabled Quillin with preferences.

- **Non-AI table of contents and Markdown profiles (#257).** New `Insert → Table of Contents` builds a TOC directly from headings — deterministic, offline, no model in the loop — replacing a `[TOC]` marker or inserting after the first heading. `Format → Markdown` adds Select Markdown Profile (Standard, GitHub-Style, Documentation, Poetry and Lyrics, Accessible Publishing, Technical Writing, PRD and Release Notes, Custom), Preserve Single Line Breaks (`nl2br`), and Read Markdown Processing Status. New pure core modules `quill/core/markdown_extensions.py` (heading extraction, slug generation matching Browser Preview's anchors, TOC generation, heading-structure diagnostics, `nl2br`) and `quill/core/markdown_profiles.py` (friendly-name extension catalog and the eight profile presets). New feature `core.markdown_profiles` (category `"markdown"`) — kept as a sibling of, not a subset of, `future.ai`, so disabling AI never disables the table of contents. 24 new unit tests.

- **Minimum required encoding (#256).** `quill/core/encoding_tools.py` gains `minimum_encoding`/`can_encode`/`describe_minimum_encoding`, picking the simplest lossless encoding in the order ASCII → Latin-1 → Windows-1252 → UTF-8. New `Format → HTML & Encoding → Analyze Encoding Requirements` and `Save Using Minimum Required Encoding...` commands. (Entity decoding itself — `&eacute;` → `é` — already shipped via `decode_html_entities`; this closes the remaining "don't force UTF-8 when a narrower legacy encoding still fits" half of the request.) New feature `core.text_encoding` (category `"text"`) now tags every entity/encoding command, replacing the generic always-on fallback they had before. Plus four small text-utility gaps closed alongside it: Remove Email Quote Markers, Strip Low ASCII Characters, Strip High ASCII Characters, and Convert to Hex Dump. 26 new/extended unit tests.

- **Casual Writer and Author or Student profiles.** The **Writer** feature profile is renamed **Casual Writer** (id unchanged, so saved settings are unaffected) to make room for a new ninth persona, **Author or Student**: long-form writing with a table of contents, footnotes, and citations for papers, theses, and class assignments. It turns on the new Markdown profiles and encoding features by default. New `Format → Markdown → Select Citation Style...` command and `Settings.citation_style` field choose between Markdown footnotes (default) and full MLA/Chicago/APA bibliography entries via the existing `quill/core/citations.py` (#203) — no new dependency either way.

- **More text-utility power tools.** Eight commands close the remaining text-utility gaps reported after the encoding-tools work above shipped: `Format → Line → Number Lines (Advanced)...` (start, increment, digit or Roman-numeral style, zero-padding, custom suffix, left/right alignment); `Format → HTML & Encoding → Convert OEM (DOS) to ANSI` / `Convert ANSI to OEM (DOS)` (CP437 ↔ Windows-1252 codepage-mismatch repair); `Convert Line-Drawing Characters to ASCII` / `Strip Line-Drawing Characters` (Unicode box-drawing U+2500–U+257F to `-`/`|`/`+`, or removed outright); `Search → Multi Replace...` (up to four search/replace pairs in one pass, optional case-insensitive); `Search → Count Occurrences...`; and `Tools → Line Statistics` (count, total, average, median, mode, standard deviation over one number per line). New pure functions in `quill/core/line_ops.py` (`to_roman_numeral`, `number_lines_advanced`), `quill/core/encoding_tools.py` (`oem_to_ansi`, `ansi_to_oem`, `convert_box_drawing_to_ascii`, `strip_box_drawing`), and `quill/core/format_ops.py` (`multi_replace`, `count_occurrences`, `compute_line_statistics`). Tagged `core.format`, `core.text_encoding`, `core.search`, and `core.analysis`. 27 new unit tests.

- **Emmet-style abbreviation expansion (MVP).** Three new `Edit` menu commands expand compact markup abbreviations into full HTML or CSS. `Expand Abbreviation` replaces the selection (or the token immediately before the cursor) in place, as one atomic undo step. `Preview Abbreviation...` expands into a scratch buffer without touching the document. `Explain Abbreviation...` opens a plain-text breakdown of the parsed tree. New pure core module `quill/core/emmet.py`: a recursive-descent parser for the core Emmet grammar (child `>`, sibling `+`, climb-up `^`, grouping `()`, multiplication `*N`, numbering `$`/`$$`, ids, classes, attributes, text content), with numbering resolved against the nearest enclosing multiplier, implicit tags/attributes for common elements, void-tag rendering, a curated common-subset CSS abbreviation table, and canned accessibility snippets (`!`, `!a11y`, `skiplink`, `form:a11y`, `table:a11y`). Mode (HTML vs. CSS) follows the current file's extension. New feature `core.emmet` (category `"markup"`). Placeholder/tab-stop navigation, a snippet manager, Quillin extension points for custom expansion providers, a Markdown abbreviation pack, and a full fuzzy CSS abbreviation engine are explicitly out of scope for this MVP (see PRD §29.3). 53 new unit tests.

## 0.5.1 — Sound Packs, Compare Mode, Code-Aware Editing, Encoding Tools (2026-06-15)

### New features

- **Save As Word (.docx).** `quill/io/export.py::write_document_as` now routes
  `.docx` through Pandoc (`gfm -> docx`) via `pandoc.py::convert_file_with_pandoc`,
  mapping Markdown headings to real Word styles for a navigable document. RTF
  was already supported; the Save As dialog gains a "Word Document (*.docx)"
  type (#204).
- **Citation help (MLA, Chicago, APA).** New pure `quill/core/citations.py`
  formats book / journal article / website sources in MLA 9, Chicago 17
  (author-date), and APA 7 — both in-text and bibliography, with per-style
  author handling (et al., initials, ampersand). **Insert -> Insert Citation...**
  is an accessible form that inserts the in-text citation, the bibliography
  entry, or both at the cursor (#203).
- **QSP sound pack system.** A pluggable earcon engine: `quill/core/sound_pack.py`
  loads a sound pack (a directory or `.qsp` zip with a `manifest.json` mapping
  event IDs to WAV files), `quill/ui/sound_manager.py` plays them non-blocking,
  and `quill/core/sound_events.py` is the canonical `SoundEvent` catalog. Ships
  the synthesised **Ink** pack plus four **indentation-tone** packs (pentatonic,
  whole-tone, diatonic, chromatic) that play a pitched tone as the caret crosses
  indent levels. Partial packs and an overlay architecture let an indent-tone
  pack layer over a primary pack. **Tools → Reading & Dictation → Sound Events...**
  toggles individual events; **Toggle Sound Notifications** flips them all and
  plays a confirming earcon. Quillins can contribute sounds via the host API.
  Generators: `scripts/gen_ink_sounds.py`, `scripts/gen_indent_tones.py`.
  Covered by `tests/unit/core/test_sound_pack.py`,
  `tests/unit/platform/test_sound_player.py` (#181/#182/#184).
- **Keyboard-first compare mode.** `quill/core/compare_service.py` (pure difflib
  engine) and `quill/ui/compare_dialog.py` (modal, screen-reader-first) add
  keyboard difference review: F8/Shift+F8 next/previous, Ctrl+F8 re-announce,
  Alt+F8 inline word changes, Ctrl+Shift+F8 whitespace toggle. Covered by
  `tests/unit/core/test_compare_service.py` (#193/#194).
- **Compare-mode sound events.** Five earcons — `compare_enter_mode`,
  `compare_exit_mode`, `compare_next_difference`, `compare_previous_difference`,
  `compare_no_more_differences` — fired across the compare dialog and the legacy
  F8 session, with a Compare section in the Sound Events dialog. Covered by
  `tests/unit/core/test_compare_sound_events.py` (#186).
- **Code-aware editing.** `quill/core/language_profile.py` dispatches a language
  profile by file extension (Python, JS/TS, Kotlin, Shell, Markdown, JSON, TOML,
  SQL, plain fallback); `quill/core/token_nav.py` adds Next/Previous Token
  navigation; **Navigate → Set Document Language** overrides detection. Covered
  by `tests/unit/core/test_language_profile.py`, `test_token_nav.py` (#181).
- **Text encoding tools.** `quill/core/encoding_tools.py` (wx-free) backs three
  Format → HTML & Encoding commands: Show Non-ASCII Characters (review report
  with Latin-1 / Windows-1252 convertibility), Convert Non-ASCII to HTML Entities
  (named with numeric fallback), and Re-encode As (UTF-8 / UTF-8 BOM / Latin-1 /
  Windows-1252 / ASCII, lossless via numeric-entity fallback). Covered by
  `tests/unit/core/test_encoding_tools.py` (#197).
- **Speak-status commands.** QUILL-key chords speak the window title
  (`Ctrl+Shift+Grave, F`), the full file path (`, P`), and a status summary
  (`, Q`) without leaving the editor (#189).
- **CLI `--goto` and `--diff`.** `--goto FILE[:LINE[:COL]]` opens a file at a
  position in one argument; `--diff LEFT RIGHT` opens two files straight into
  compare mode. `_parse_goto` correctly handles Windows drive-letter paths (#192).
- **Report a Bug enhancements.** The dialog opens focused on Summary and adds a
  screen-reader picker (None / JAWS / NVDA / Narrator / VoiceOver / Other,
  pre-selected from detection) plus remembered name and email fields, all sent
  with the report (#188).
- **Compare power features.** Character-level diff highlighting, word-level
  speech of inline changes, and Compare Selection With Clipboard, alongside the
  difference list, whitespace options, and accessible speech of the MVP
  (#193/#194).
- **Document switching with Ctrl+Tab / Ctrl+Shift+Tab** moves to the next or
  previous open document (#190).
- **Persistent startup folder.** A setting controls the initial folder for Open
  and Save As; file dialogs now default to Documents instead of the install
  directory (#168).
- **Feature search** now finds copy tray, macros, and abbreviations (#171).
- **Developer file extensions** added to the Open dialog wildcard (Kotlin, TS,
  Go, Rust, and more) (#191); **file-open focus** now lands in the editor with a
  screen-reader announcement, removing the Alt+Tab workaround (#187).
- **HEIC/HEIF image support** for AI image description (#164).
- **About screen** lists all GitHub contributors, fetched from the contributors
  API with a baked-in offline fallback; Ken Perry and Kelly Ford added.

### Bug fixes and security

- **Setup Wizard accessibility fixes.** The "Play sounds for mode changes"
  checkbox on step 2 now carries its label on the control, so screen readers
  announce it instead of an unlabeled checkbox (#208). On step 3, the Feature
  Profile choices use a single `wx.RadioBox` so arrowing past the last choice
  wraps within the group instead of escaping into the Back/Next/Cancel buttons,
  and the group is announced as one labelled control (#209).
- **Quill exits reliably when run from source.** A modeless top-level window
  (such as the Ask Quill chat frame) could keep the wx main loop alive after
  the main window closed, leaving the process running. `_on_close` now destroys
  straggler top-level windows so the app always exits (#210).
- **Report a Bug fields are now editable.** The form fields no longer reject
  keyboard input under NVDA; the dialog was rebuilt without the intermediate
  `wx.Panel` that broke editing, and moved from Tools to Help (#178). The bug
  report also no longer blocks the UI thread — the network call runs off-thread
  with a timeout fallback (#188).
- **Screen-reader chatter silenced.** JAWS no longer announces "splitter window"
  and "panel" on menu close and app focus; the layout container is no longer
  exposed in the accessibility tree (#170).
- **Describe Image** no longer fails silently — corrected an `AttributeError`
  on the region-tracking call (#165).
- **Startup is faster and quieter.** Screen-reader detection is offloaded to a
  background thread, a WebView2 prewarm crash is fixed, and the title no longer
  flashes "untitled Quill unavailable" before the app finishes loading
  (#176/#177). The preview pane no longer hangs for minutes and is dismissable
  (#174).
- **First-run experience fixed.** The first window now gains foreground focus so
  the trust/privacy dialog is reachable (#166); the personalization wizard can be
  re-triggered after first run (#167); the wizard's startup beep and Cancel
  focus are fixed.
- **Crash-recovery snapshot preview** is no longer blank for screen readers
  (#180).
- **User guide opens correctly.** It opens as read-only HTML in the browser
  instead of as an editable Markdown tab (#173), with a glossary of domain terms
  (#172), and a WebView2 fault no longer throws a `0x8007139f` error — the
  preview control is caught and rebuilt (#175/#183).
- **macOS: API keys and tokens persist via the login Keychain** instead of
  crashing on save when the Windows DPAPI import was unavailable (#160).
- **macOS notarized build** signs Pillow's bundled dylibs and uses
  hardened-runtime entitlements, fixing notarization.
- **Manage Features dialog** and the SSH Quick Connect / Site Manager dialogs
  were clarified and corrected (#161/#162).
- **Embedded Python build** bootstraps setuptools and fixes the LicenseFile path.
- Internal sound-design notes moved out of the repo root (`x.md` → `docs/wsp.md`).

### Governance

- **Kelly Ford** added as a project owner (contributors list, CODEOWNERS, and
  repo maintain access) alongside the existing maintainers.

## 0.5.0 — Developer Console, GitHub Integration, Keyboard Packs, Autoupdate (2026-06-12)

### New features

- **QUILL Developer Console (QDC).** Python and TypeScript consoles with session
  history, output capture, and a `q.*` host API for reading/writing document
  content. Opened from the Developer menu. Covered by `tests/unit/devtools/`.
- **GitHub Remote Files.** Open, browse, and save files directly from/to GitHub
  repositories (File > Open Remote > GitHub). Token stored in Windows Credential
  Manager; first-use consent dialog before any network call.
- **Keyboard packs (.kqp).** Export and import complete keybinding sets as
  self-contained `.kqp` JSON files (File > Keyboard Pack). Validated on import;
  atomic write on export.
- **Autoupdate pipeline.** Vendored `accessibleapps/app_updater` under
  `quill/_vendor/autoupdate`; release scripts (`build_update_zip.py`,
  `fetch_bootstrappers.py`, `generate_file_manifest.py`) produce
  installer-compatible update ZIPs with SHA-256 manifests.
- **Context-sensitive help.** `Ctrl+Shift+Grave, Shift+H` announces the most relevant shortcuts for
  the current focus context (`Alt+H` is reserved for the Help menu mnemonic).
  F1 shows per-control help; Shift+F1 opens "What Can I Do Here?".
  Implemented in `quill/ui/context_help.py` and `quill/ui/main_frame.py`.
- **Setup wizard.** First-run nine-page wizard guides new users through screen
  reader, AI, SSH, and cloud configuration.
- **Translation infrastructure.** Babel-based i18n scaffolding: `quill/locale/quill.pot`
  template, `babel.cfg` extraction config, and `quill/core/i18n.py` runtime loader.
  Strings in legacy modules and several new 0.5.0 surfaces (GitHub provider,
  update flow status strings) are not yet wrapped with `_()`. No translations are
  shipped; the `.pot` template is the floor. See
  `docs/localization/translation-contributor-plan.md` for contribution workflow.
- **Per-provider model memory.** AI chat remembers the last selected model per
  provider and restores it on next open.

### Accessibility and screen reader improvements

- **QDC console keyboard control.** `EVT_CHAR_HOOK` at the frame level now handles
  Esc (close), F1 (help), Ctrl+L (clear), Ctrl+Shift+C (copy transcript), Ctrl+S
  (save transcript) from any focused element inside the console window.
- **QDC console focus return.** Closing the console returns caret focus to the
  document editor via `focus_editor_cb`, not just `parent.SetFocus()`.
- **QDC history navigation announced.** Up/Down history recall announces
  "History N of M: entry" so screen reader users hear what was recalled.
- **QDC TypeScript worker start announced.** "Developer Console ready" is spoken
  when the Node worker is available. Previously the status bar changed silently.
- **QDC clipboard copy announced.** Copy-transcript announces success or failure.
- **QDC TypeScript console opens in TypeScript mode** instead of Python.
  `open_typescript_console()` calls `win.set_language("TypeScript")`.
- **AI chat, Skill Library, Prompt Library status changes announced.** All three
  dialogs now route status updates through `_set_status()` which calls both
  `SetLabel` and `announce_cb`. 13 status sites in AI chat, 9 in Skill Library,
  5 in Prompt Library were previously silent.
- **Command Palette and Go-to-Anything status announced.** Search result counts
  and unavailable-command messages are now spoken.
- **GitHub browser status announced.** Loading states, errors, and directory
  confirmations are spoken via `announce_cb`. Enter key works on the repository
  name field (`TE_PROCESS_ENTER`). Backspace no longer hijacks while editing the
  field. Focus moves to the first item after a directory loads.
- **SSH remote browser path announced.** Directory changes are spoken after each
  navigation step via `announce_cb` in `RemoteBrowserDialog`.
- **Setup wizard page transitions announced.** Each of the nine pages announces
  "Step N of 9: Title" and focus lands on page content rather than the Next button.
- **All modal dialogs through z-order gate.** Setup wizard, devtools consent,
  and GitHub URL/commit-message dialogs now route through `_show_modal_dialog` and
  `_show_message_box`, eliminating the "dialog opens behind main window" class.
- **Unhandled crash dialog readable by screen readers.** A Win32 `MessageBoxW`
  (readable by Narrator/NVDA even with no wx running) now shows on any unhandled
  exception, with the error message and crash report file path.
- **TTS self-voicing non-blocking.** The pyttsx3 TTS worker now runs on a daemon
  thread with a queue, so announcements for low-vision users no longer block the
  UI thread. SR detection result is cached with a 30-second TTL so starting
  NVDA mid-session stops double-talk within one announcement cycle.
- **GATE-12 (announce-gap) added.** `check_announce_gap.py` is a pre-commit gate
  that flags any dialog updating a status `StaticText` via `SetLabel` without an
  announce call. Triggers on `quill/ui/` and `quill/devtools/` files.

### Bug fixes and security

- Python console `compile()` now appends trailing `\n` before single-mode
  compile, fixing `SyntaxError` on compound statements (`for`, `with`, `if`).
- Nuitka build dependency removed entirely (was unreliable; took 44+ min and
  stalled). Purged from `pyproject.toml`, CI, and scripts.
- Stray `leasey.html` at repo root removed.
- Safe Mode now gates the Developer Console in addition to AI and Quillins.
- `write_json_atomic` now fsyncs before `os.replace` to survive power cuts.
- CLI missing-file paths now print a warning instead of silently skipping.
- `_screen_reader_active()` re-probes every 30 seconds (was cached forever).
- `safe_subprocess` passes `CREATE_NO_WINDOW` on Windows to suppress console flash.
- Redaction now covers GitHub PATs, OpenAI keys, AWS access keys, Slack tokens,
  and long alphanumeric tokens in addition to the existing bearer/hex patterns.
- GitHub URL parser rewrote using `urllib.parse` to handle query strings, anchors,
  and percent-encoded paths.
- Vendor autoupdate `_version_tuple` handles pre-release version segments.
- TypeScript console host API calls (`documentText`, `replaceSelection`, etc.) are
  now marshaled to the UI thread via `wx.CallAfter` + `threading.Event`. Previously
  they ran on the Node reader thread, violating the wx threading invariant.
- GitHub temp files now land in a content-addressed slot (`sha256(repo:ref:path)[:16]`)
  instead of a flat basename. Eliminates wrong-repo commits when two files share a name.
- GitHub `get_identity()` is no longer called on the UI thread. All three entry points
  (`Open Repository`, `Open File URL`, `Manage Accounts`) now post it to a daemon thread
  before showing any dialog, fulfilling the module docstring's threading promise.

## Security Hardening and UX Delight — 1.0 Release Pass (2026-05-01)

This section records the 13 HIGH-severity security fixes, 16 UX delight features, and the LOW/NIT fixes applied during the pre-1.0 code review. All items below were open in `issues.md` before this pass and are now closed.

### HIGH security and reliability fixes (all 13 closed)

- **H-SAFE-1 / H-1-tests — Safe Mode now enforced in all load-bearing paths.** `--safe-mode` / `QUILL_SAFE_MODE=1` disables AI responses, the watch folder, and Quillin contributions. Covered by `test_safe_mode_blocks_assistant_network_calls`.
- **H-1 — Subprocess args no longer logged in full.** `redaction.py::format_args_for_log` redacts every argument; only the executable basename and arg count are preserved. Covered by `test_run_subprocess_safely_does_not_log_secrets`.
- **H-2 — Crash bundle redacts secrets before shipping.** `build_diagnostic_bundle` runs `redact_text_for_bundle_with_stats` on every text file. Covered by `test_diagnostic_bundle_redacts_secrets_and_paths`.
- **H-3 — `recent_commands` sanitized before embedding in diagnostic bundle.** `filter_recent_commands` validates every item against the command-id grammar and drops anything invalid.
- **H-4-core — `recovery.py` state mutations serialized.** `begin_session`, `mark_clean_exit`, and `_record_offer_outcome` are now protected by a `threading.RLock` (in-process) and `msvcrt.locking` / `fcntl.flock` (cross-process). Covered by `test_concurrent_begin_session_serialize_via_lock`.
- **H-1-core — `QUILL_DATA_DIR` gated on `_DEV_BUILD`.** Release builds ignore the env var entirely. Dev builds additionally require the path to be under `Path.home()`. Covered by `tests/unit/core/test_paths.py` (4 tests).
- **H-2-core — External engine executable allowlist.** `configure_engine` and `probe_engine` validate the executable basename against `_ENGINE_EXECUTABLE_BASENAMES` before any I/O. Covered by `test_configure_engine_rejects_unallowed_executable` and `test_probe_engine_rejects_unallowed_executable`.
- **H-3-core — SSH uses `RejectPolicy` by default.** `paramiko.AutoAddPolicy` is only available when `trust_first_use=True` is passed explicitly. System host keys are always loaded first. Covered by 4 tests in `test_ssh_client.py`.
- **H-4-core-2 — IPC queue append serialized in-process.** `enqueue_open_request` acquires a module-level `threading.Lock` before opening the JSONL file. Covered by `test_concurrent_enqueue_serializes_via_lock`.
- **H-1-ui / H-2-ui — Quillin consent and remove-confirm dialogs use the modal contract.** Both `quillin_consent` and `on_remove` now route through `_show_modal_dialog` + `apply_modal_ids`. Covered by `test_quillin_consent_uses_modal_contract` and `test_on_remove_uses_modal_contract`.
- **H-3-ui — Watch Queue Monitor properly cleaned up on close.** `_on_close` explicitly destroys the monitor dialog and clears all references before the watch service stops.
- **H-1-platform / H-2-platform — `pyttsx3` engine is a process-wide singleton.** Initialization happens once; a `_pyttsx3_engine_failed` gate prevents repeated failure. `reset_pyttsx3_engine_for_tests()` helper added for test isolation.
- **H-3-platform — `Windows.Media.Ocr` import wrapped.** `winsdk` imports are wrapped in `try/except ImportError`; `_WINSDK_AVAILABLE` flag prevents crashes on non-Windows builds. Covered by `test_module_imports_without_winsdk`.
- **H-4-platform — macOS VoiceOver errors now logged.** The `except Exception: pass` branch is now `logger.warning(...)`. Covered by `test_macos_announce_error_logged`.

### Magic / UX delight (all 16 closed — §8)

- **Key cheatsheet (`Alt+Shift+/`).** `open_key_cheatsheet()` opens a searchable dialog listing every command and its keybinding.
- **Go to anything (`Ctrl+Shift+Grave, G`).** `GoToAnythingDialog` in `quill/ui/palette.py` searches commands (`>` prefix) and headings (`#` prefix). Activating a heading calls `go_to_line_number(lineno)` on `MainFrame`.
- **Earcons.** `_play_quill_sound()` fires at mode-entry transitions, queued separately from TTS so it does not interrupt screen-reader output.
- **"Why Don't I See a Feature?" (`Alt+F1`).** `explain_unavailable_feature()` announces the reason a command is unavailable.
- **Live contrast checker (`Ctrl+Shift+Grave, Shift+C`).** `announce_contrast_ratio()` computes the WCAG 2.1 relative-luminance ratio for the current theme and announces it. Also fires automatically after `_apply_theme()`.
- **Magic Paste (`Ctrl+Alt+V`).** `magic_paste()` inspects the clipboard for a URL, Markdown block, or base64 image and presents a picker before inserting.
- **Recovery diff UX.** `_offer_crash_recovery()` now includes a 30-line read-only snapshot preview so users can review content before deciding to restore.
- **Status bar context help (`Ctrl+Shift+Grave, Shift+H`).** `announce_context_mode_shortcuts()` announces the most useful keys for the current mode in priority order. (`Alt+H` is reserved for the Help menu mnemonic.)
- **Soft error recovery link.** `_show_error_with_hint()` is used for file-open, export, and import errors. A "What to try next..." toggle reveals a `wx.TE_READONLY` area with contextual guidance.
- **TTS fallback announcement.** `_check_tts_fallback_on_startup()` fires at startup and announces "Screen reader fallback active. F8 to retry TTS." when `pyttsx3` could not be initialised. `retry_tts_init()` exposed in `prism_bridge.py`.
- **Recovery `had_replacements` note.** `read_recovery_snapshot()` returns `(text, had_replacements)`; the recovery dialog shows a warning when replacement characters are detected.
- **Annisuggestion.** `top_suggestion()` in `quill/core/palette.py` surfaces the most-used recent command (≥3 uses, within 1 hour) as a `suggestion` status-bar cell. Activating the cell runs the command.
- **Crash-recovery loop fix (M-28).** `RecoveryOffer.dismissal_count` adapts the dialog text and relabels the skip button "Discard and Continue" after 3 dismissals.
- **File-context summary (`Alt+I`).** `show_document_summary()` announces word count, line count, heading count, last-saved time, and recovery snapshot presence.
- **A11Y live indicator.** `"sr_name"` status-bar cell shows which screen reader is detected, populated by `detect_screen_reader()` from `sr_detect.py`.
- **"Resume from where I left off".** Caret position is saved per autosave cycle (`save_cursor_position()` in `recovery.py`) and per workspace snapshot (`caret_positions_from_session()` in `sessions.py`). Both are restored on next open.

### MEDIUM — Sweep 14 (14 fixes: M-10 through M-26 batch)

- **M-12** — `io/rtf_safety.py`: removed `\bAUTOTEXT\b` from `_REMOTE_FIELD_RE`; `AUTOTEXT` is a benign boilerplate-insert control word, not a remote-fetch instruction. Covered by `test_autotext_not_flagged_as_remote`.
- **M-26** — `tools/module_size_budgets.json`: added `"_next_target_main_frame": 15000` to make the CQ-1 decomposition trajectory explicit.
- **M-21** — `stability/safe_regex.py`: added `_compile_cached` (`lru_cache(maxsize=128)`) so `safe_finditer` and `safe_subn` reuse compiled patterns across calls. Covered by `test_safe_finditer_uses_cached_compile`.
- **M-23** — `stability/wx_dispatch.py`: `call_ui_safely` now logs a `WARNING` when `wx.CallAfter` is unavailable and it falls back to synchronous execution on the caller thread. Covered by `test_call_ui_safely_logs_warning_without_wx`.
- **M-10** — `io/pdf.py`: `extract_pdf_text` now catches any `Exception` from each extractor (not just `ModuleNotFoundError`), so a malformed PDF falls through to the next extractor without crashing. Covered by `test_malformed_pdf_returns_empty_text_not_crash`.
- **M-17** — `stability/diagnostics.py`: `setup_fault_handler` now closes the previous handle and calls `faulthandler.cancel_dump_traceback_later()` before opening a new one, so handles stay bounded across long sessions. Added `close_diagnostic_handles()` helper. Covered by `test_diagnostic_handles_bounded`.
- **M-18** — `stability/task_manager.py`: `shutdown(wait, cancel_futures=not wait)` replaced with `shutdown(wait=True, cancel_pending=False)` — the two parameters are now independent. Covered by `test_task_manager_shutdown_decoupled`.
- **M-19** — `stability/wx_heartbeat.py`: `WxHeartbeatWatchdog.stop(timeout=5.0)` now calls `self._thread.join(timeout=timeout)` after setting the stop event, so callers know the watchdog has fully stopped. Covered by `test_watchdog_stop_joins_thread`.
- **M-20** — `stability/wx_heartbeat.py`: replaced the `already_dumped` boolean with a `last_dump_time` timestamp; the watchdog re-dumps when `age >= dump_after_seconds` AND at least `dump_after_seconds` seconds have elapsed since the last dump. This ensures a brief UI unblock followed by a second block triggers a second dump. Covered by `test_watchdog_re_dumps_after_recovery_window`.
- **M-22** — `stability/feature_contracts.py`: `validate_feature_contract` now enforces two additional rules: `risky`/`advanced` features must have `disabled_in_safe_mode=True`; `experimental` features must have `default_enabled=False`. Covered by `test_feature_contract_full_validation`.
- **M-11** — `io/structured.py`: `_format_spreadsheet` now catches `zipfile.BadZipFile` separately from generic `Exception` and returns a "corrupted file" message pointing the user to repair in Excel/LibreOffice, rather than the generic "import not available" message. Covered by `test_corrupt_xlsx_surfaces_actionable_error`.
- **M-13** — `io/rtf.py`: added `_detect_rtf_encoding(path)` which reads the first 512 bytes to extract the `\ansicpg` code-page number; `read_rtf_document` now uses the detected encoding instead of hard-coded `cp1252`, so Cyrillic (CP1251) and other non-Western RTF files decode correctly. Covered by `test_cyrillic_rtf_decoded_with_ansicpg`.
- **M-16** — `core/ai/assistant.py`: `make_default_backend()` now logs a `WARNING` when the configured provider probe fails, rather than silently swallowing the exception. Covered by `test_unreachable_provider_announced`.
- **M-25** — `tools/quillin_lint.py`: `_string_errors` now uses the `regex` package with `timeout=0.5` when available (falls back to `re` if not installed), guarding against ReDoS in Quillin manifest pattern validation. Covered by `test_redos_pattern_rejected`.

### MEDIUM — Sweep 15 (8 fixes: M-3, M-5, M-6, M-7, M-8, M-9, M-14, M-15)

- **M-9** — `io/pages.py`: `_read_pages_via_iwa` now acquires a module-level `threading.Lock` (stored as `_codec._quill_id_name_map_lock`) around the `ID_NAME_MAP` patch/restore cycle. Two concurrent `.pages` openers can no longer corrupt each other's codec state. Covered by `test_concurrent_reads_serialize_via_lock`.
- **M-14** — `core/read_aloud.py`: `_speak_sentence_dectalk` and `_run_espeak_live` now track `start = time.monotonic()` and call `process.kill()` + raise `ReadAloudUnavailableError` when `_MAX_SYNTHESIS_SECONDS` (120 s) elapses. Hanging DECtalk/eSpeak processes can no longer stall the worker thread indefinitely. Covered by `test_dectalk_killed_after_wall_clock_timeout`.
- **M-15** — `core/read_aloud.py`: `synthesize_with_piper` now writes the text to a `NamedTemporaryFile` and passes it as `stdin` (an open file object) instead of using `input=text`. This bypasses the 64 KiB OS pipe-buffer limit for large inputs and adds `timeout=_MAX_SYNTHESIS_SECONDS` to `subprocess.run`. Covered by `test_piper_long_text_via_temp_file`.
- **M-5** — `core/ai/foundation_models.py`: `FoundationModelsBackend` now caches a single `asyncio` event loop on a daemon thread (`fm-event-loop`) and submits all coroutines via `asyncio.run_coroutine_threadsafe`. `asyncio.run()` was creating a new loop per call, leaking OS handles. Covered by `test_event_loop_reused_across_calls`.
- **M-6** — `core/updates.py`: `verify_manifest_signature` now returns `False` immediately when `QUILL_UPDATE_MANIFEST_KEY` is not set. A salt-only HMAC (the default placeholder) is no longer accepted as a valid signature, preventing MITM forgery on unconfigured deployments. Covered by `test_salt_only_signature_rejected`.
- **M-7** — `core/python_sandbox.py`: added `_ProtectedGlobals(dict)` — a `dict` subclass whose `__setitem__` silently ignores writes to `"__builtins__"`. The sandbox's `globals_ns` is now a `_ProtectedGlobals` instance, preventing user code from replacing the restricted builtins dict via `globals()["__builtins__"] = original_builtins`. Covered by `test_builtins_rebinding_blocked`.
- **M-8** — `ui/main_frame.py`: `_watch_run_macro` already routes all UI-thread macro dispatch through `wx.CallAfter`. Verified clean; added `test_macro_dispatch_marshalled_to_ui_thread` to lock in the contract.
- **M-3** — `core/ai/external_engine.py`: `configure_engine` now calls `which(command[0])` (injectable for tests, defaults to `shutil.which`) and raises `ValueError` if the executable is not on `PATH` and no absolute path was given. A new `which=` parameter makes the check testable without modifying `PATH`. Covered by `test_unresolvable_executable_rejected`.

### MEDIUM — Sweep 16 (6 fixes: M-24, M-28, M-29, M-30, M-31, M-32) — all MEDIUM closed

- **M-24** — `tools/dialog_button_contract.py`: extended the dialog-button audit to also verify that every `apply_modal_ids` `affirmative_id` is backed by a real button or `CreateButtonSizer` flag, or that the scope handles `WXK_RETURN`/`WXK_NUMPAD_ENTER` manually. Removed the bogus `affirmative_id=wx.ID_OK` from five `assistant_tools.py` dialogs (no ID_OK button existed); added `# noqa: dialog_button_contract` to `preview_dialog.py` where the button ID is a loop variable (false positive). Covered by `test_unbacked_affirmative_id_flagged` and `test_audit_accepts_enter_handler_for_affirmative_id`.
- **M-28** — `ui/main_frame.py`: `_show_modal_dialog` gains a `restore_editor_focus: bool = True` parameter. The crash-recovery loop now passes `restore_editor_focus=False` so `editor.SetFocus()` is not called between re-show iterations, eliminating the focus-racing that caused screen readers to announce the editor between dialog opens. Covered by `test_crash_recovery_loop_does_not_steal_focus`.
- **M-29** — `ui/assistant_tools.py`: `RunPythonDialog._on_run` now dispatches `run_python_sandbox` to a daemon worker thread and delivers results back via `wx.CallAfter(_finish_run, result)`. The Run and Apply buttons are disabled during execution and re-enabled in `_finish_run`. Long-running sandbox scripts no longer freeze the UI thread or the screen reader. Covered by `test_run_python_does_not_block_ui_thread`.
- **M-30** — `ui/main_frame_browse.py`: `_run_browse_prewarm` now creates a per-run `threading.Event` (`cancel_event`). Before starting a new worker thread it sets any in-flight event (`old_cancel.set()`). The worker checks `cancel_event.is_set()` before calling `wx.CallAfter`, so a superseded build drops its result without triggering a UI update. Covered by `test_prewarm_thread_cancelled_on_repeat`.
- **M-31** — `ui/sticky_notes.py`: `StickyNotesVaultDialog._delete_selected` now uses `show_message_box` from `quill.ui.dialog_contract` instead of raw `self._wx.MessageBox`. Screen readers now hear the enter/exit announcement cues for the delete confirmation dialog. Covered by `test_delete_confirm_uses_contract_helper`.
- **M-32** — `ui/main_frame_image.py`: replaced both `time.sleep(0.1)` polling loops (OCR and image-description progress) with `wx.MilliSleep(100)`, and removed the `import time` that was no longer needed. `wx.MilliSleep` pumps the wx event queue between sleeps, eliminating CPU busy-wait while OCR or AI description runs.

### LOW — L-23 (csv_grid.py cell-ID stride)

- **L-23** — `quill/ui/csv_grid.py:GetSelection`: replaced the `row * 1000 + col` position encoding with `row * _CELL_POSITION_STRIDE + col` where `_CELL_POSITION_STRIDE = 16384`. The old stride collided for any column ≥ 1000 (e.g. row=1,col=0 → 1000 == row=0,col=1000). The new stride matches Excel's maximum column count (16 384) so no realistic spreadsheet can produce a collision. Seven regression tests added in `tests/unit/ui/test_csv_grid.py`.

### LOW and NIT — Sweep 12 (§6 and §7 fully closed)

- **L-17** — `tests/stability/test_stability.py`: added 6 direct unit tests for `redaction.py` (previously tested only indirectly via the bundle): `test_redact_command_arg_replaces_secret_name_value_pair`, `test_redact_command_arg_strips_windows_path_prefix`, `test_format_args_for_log_preserves_basename_and_count`, `test_format_args_for_log_empty_returns_no_args`, `test_redact_text_for_bundle_drops_bearer_line_and_reports_stats`, `test_filter_recent_commands_drops_non_id_strings`. Test count: 25 → 31.
- **L-18** — `tests/performance/test_budgets.py`: added `pytestmark = pytest.mark.perf` and registered the `perf` marker in `pyproject.toml`. Wall-clock budget tests can now be excluded with `-m "not perf"` in latency-sensitive CI environments.
- **L-19** — `dialogs.md`: added a cross-reference block near the top of the file pointing to `tests/accessibility/test_accessibility_suite.py`, `tests/accessibility/test_announcement_grammar.py`, and `docs/qa/final-qa-test-plan.md §6` ("Dialog estate pass").
- **L-20** — `docs/qa/final-qa-test-plan.md`: `§5.1` already carries all three required artifacts (`dialog_inventory.json` mtime, `module_size_budgets.json _rebaseline_*` keys, and wxPython runtime version, plus the public surface fixture and glow-core engine hash). Confirmed and closed.
- **N-13** — `quill/core/bookmarks.py`: added a module docstring explaining the rationale for keeping this as a separate wx-free module (pure dict operations, independently unit-testable without importing wx). Mirrors the existing `clipboard_collector.py` docstring.
- **N-14** — `quill/core/clipboard_collector.py`: existing module docstring (`EDS-11` reference, explicit wx-free contract) is sufficient. Confirmed and closed.

### LOW and NIT fixes (§6 and §7 continued)

- **L-2** — `core/lexical.py`: added `logger.debug("Lexical provider %s failed: %s", ...)` inside the broad `except` so provider regressions surface in diagnostic logs.
- **L-3** — `core/ai/assistant.py`: added `logger.warning(...)` inside the Foundation Models backend probe `except` so probe failures appear in the diagnostic bundle.
- **L-4** — `core/lexical_preload.py`: added `logger.debug(...)` inside the preload `except` so non-fatal warm-up failures are visible in debug logs.
- **L-6** — `core/watch_queue.py`: documented why `threading.RLock` is required (`_dequeue_item` re-enters `_try_flush` under the same lock; plain `Lock` would deadlock).
- **L-14** — `tools/check_banned_patterns.py`: enriched the unregistered-dialog-surface violation message to hint that stock `wx` dialogs should be added to `_NATIVE_WX_DIALOGS` in `dialog_inventory.py`.
- **L-16 / N-5** — `tools/ui_surface.py`: wrapped the bare `next(...)` call in `try/except StopIteration` and raised `SystemExit` with a clear message when `MainFrame` cannot be found (e.g. after a rename).
- **M-27** — `pyproject.toml`: added `"Operating System :: MacOS"` classifier to match the documented macOS support.
- **L-1** — `core/paths.py`: on Windows, missing `APPDATA` now raises `RuntimeError` with a clear message instead of silently falling back to the hidden `~/.quill` directory. Non-Windows still uses `~/.quill` as before. New test `test_windows_raises_when_appdata_missing` locks this in.
- **L-7** — `core/glow.py`: narrowed the `ImportError`-only case in `_load_glow_core`; all other broad `except Exception` sites in the GLOW backend now log `logger.warning(...)` before returning the safe fallback.
- **L-10** — `io/ocr.py`: narrowed `except Exception` to `except ImportError` in `_import_windows_ocr` so non-import errors are not silently swallowed.
- **L-21** — `stability/*.py`: all stability modules already carry `Implements: ROADMAP ...` docstrings — confirmed and closed.
- **L-22** — `tests/unit/tools/test_bundled_quillin_lint.py`: added `test_bad_quillin_fixture_is_rejected` negative test with a `fixtures/bad_quillin/manifest.json` that fails schema validation (missing `id`, invalid `version`).
- **N-10** — `dialogs.md`: safe mode flag already referenced at lines 280-305 — confirmed and closed.
- **N-3** — `stability/crash_report.py`: bundle filename now uses ISO-8601 (`YYYYMMDDTHHMMSSZ`) instead of a raw 19-digit nanosecond epoch, making bundles human-inspectable in Explorer and sorted correctly by name.
- **L-11** — `io/structured.py`: duplicate of M-11 (low because there is an existing fallback); closed as a reference item — will be addressed with M-11.

- **L-8** — `updates.py`: removed unnecessary `getattr` guard around `response.headers.get("Content-Length")`.
- **L-12** — `safe_mode.py`: deleted unused `safe_mode_message()` export.
- **L-15** — `network_egress_audit.py`: duplicate egress-site key now raises `ValueError` at scan time so no new egress site can be silently dropped.
- **N-1** — `stability/__init__.py`: re-exported `build_diagnostic_bundle`, `configure_logging`, and `run_subprocess_safely` for ergonomic call sites.
- **N-4** — `module_size_budgets.json`: `_comment` / `_rebaseline_*` keys are now stripped before the budget map is read.
- **N-7** — `quillin_lint.py`: `_JSON_TYPES` is now `types.MappingProxyType({...})` for immutability.
- **N-8** — `dialog_button_contract.py`: `_FLAG_TO_ID` reverse-lookup dict used by `_collect_button_ids`; `# noqa: dialog_button_contract` opt-out added.
- **N-9** — `feature_contracts.py`: `requires_timeout: bool | None = None` moved to end of dataclass for default-value ordering.
- **N-11** — `external_engine.py`: `configure_engine` docstring documents POSIX-style shell-command format and `shlex.split` semantics.
- **N-12** — `recovery.py`: `_validate_session_id()` helper replaces three `UUID(session_id)` side-effect calls.
- **N-15** — `dictation.py`: `try/except ImportError` block carries explicit Windows-only intent comment.
- **N-16** — `announcements.py`: `format_progress` docstring states its pure-function, no-I/O, thread-safe contract.
- **M-1** — `core/watch_actions.py`: added `_humanize_action_error(action_id, error)` and routed the 8 broad `except Exception` sites (`OpenAction`, `MoveAction`, `CopyAction`, `ConvertAction`, `RunMacroAction`, `RunPythonTransformAction`, `AiAction`, `OcrAction`) plus the registry's last-resort guard through it. Screen-reader users now get plain-English messages such as `"Quill cannot complete the move. The folder is read-only or you lack permission — choose a folder you own."` instead of `"[Errno 13] Permission denied: 'C:\\…'"`. Coverage: `test_humanize_permission_error_is_actionable`, `test_humanize_file_not_found_mentions_reappear`, `test_humanize_generic_oserror_keeps_strerror`, `test_humanize_unrecognized_error_falls_back_to_str`, `test_move_action_permission_error_humanized`. Budget re-baselined (+57 lines).
- **L-9** — `core/storage_mode.py`: `portable_root_dir()` now honours the `_DEV_BUILD` flag (set at module load from `QUILL_DEV_BUILD == "1"`), so release builds ignore `QUILL_PORTABLE_ROOT` even if a user has it set. Mirrors the H-1-core treatment of `QUILL_DATA_DIR`. Coverage: `test_release_build_ignores_quill_portable_root` and `test_dev_build_honours_quill_portable_root`.
- **L-13** — `stability/task_manager.py`: `QuillTask` now carries `submitted_at` (wall-clock at submit) and `result_summary` (one of `"pending"`, `"ok"`, `"cancelled"`, `"failed"`, exposed as a `TaskResult` literal). The worker's exception handler pre-tags the result, and the done callback only re-derives it when the worker never reached its exception path — eliminating a race where a cooperative cancel looked like `"failed"`. The diagnostic bundle picks the new fields up automatically because `_snapshot_task` runs `asdict()` on the dataclass. Coverage: `test_task_manager_records_submitted_at_and_pending_result`, `test_task_manager_result_summary_ok_after_success`, `test_task_manager_result_summary_failed_on_exception`, `test_task_manager_result_summary_cancelled`.
- **L-5** — `core/assistant_ai.py`: wrapped `unprotect_secret` in `try/except Exception` so a DPAPI decrypt failure (portable install moved between machines, current user differs from the original) no longer propagates. A new module-level `ASSISTANT_KEY_UNLOCK_FAILED_MESSAGE` constant (`"The saved API key is encrypted for a different Windows user. Open AI Connection and enter the key again."`) is now surfaced from `verify_assistant_connection()` and `list_assistant_models()` whenever `assistant_secret_unlock_failed()` returns True and no fresh key is supplied. The original provider "unauthorized" error is replaced with an actionable message. Coverage: `test_verify_assistant_connection_surfaces_unlock_failure`, `test_list_assistant_models_surfaces_unlock_failure`.
- **N-6** — `core/spellcheck.py` and `core/thesaurus.py`: added public `reset_caches()` helpers to both modules. Each takes its module's own backend/load lock, so a reset cannot race a lazy loader. `tests/performance/test_budgets.py` now calls the public helpers instead of poking `_WORDLIST_CACHE` / `_INDEX` directly; the old private-attribute reset code is retained as a backward-compat shim. New tests in `tests/unit/core/test_reset_caches.py` lock in the new contract: `test_spellcheck_reset_caches_clears_all_globals`, `test_spellcheck_reset_caches_acquires_backend_lock`, `test_spellcheck_preload_after_reset_loads_wordlist`, `test_thesaurus_reset_caches_clears_index_and_error`, `test_thesaurus_reset_caches_acquires_load_lock`, `test_thesaurus_preload_after_reset_is_idempotent`.

---

## QUILL Brand Identity

**QUILL** stands for **Quality, Usable, Inclusive, Lightweight, Literate**.

**QUILL: A quality, usable, inclusive, lightweight, and literate editor built for everyone who writes, codes, learns, and creates.**

## Cross-platform support and on-device AI

- **macOS support.** Quill now runs on macOS as well as Windows from one codebase. Announcements route to VoiceOver (never speaking over it); release Mac builds are code-signed with a Developer ID certificate and notarized by Apple.
- **Ask Quill chat.** An on-device AI chat rendered as a fully accessible WebView document — heading-navigable turns, announced replies, an in-page message box, and Escape to close. Verified in NVDA, JAWS, and VoiceOver.
- **On-device AI, no cloud required.** Apple Foundation Models on macOS; llama.cpp (CPU, GGUF) on Windows/Linux; optional Ollama (local/cloud) or a custom endpoint. The assistant answers in chat by default and never edits a document without approval.
- **Train Writing Style** conditions the assistant on your own writing.
- **Accessible WebView library.** The chat, preview, About box, and update/consent dialogs are built on the open-source `wx-accessible-webview` library (extracted from Quill).

## AI reliability and clarity (highlights)

- **Clearer AI connection messages.** Quill now tells the difference between a rejected API key ("Authentication failed. Check your API key.") and a valid key that lacks access to a model or region ("Access denied..."), and reports rate limiting, warm-up, and local-server-not-running states in plain language.
- **Warm-up retry.** When a model is still loading, Quill briefly retries before reporting it as warming up, instead of failing the first attempt.
- **No false 403s.** Connection status is matched on real HTTP status codes, so host ports like `localhost:11403` are never mistaken for an error.
- **Smarter quick writing actions.** Rewrite, Summarize, Continue Writing, and Fix Grammar now work with or without a selection, fall back to a sensible scope (paragraph or whole document), and announce the scope and word count.
- **AI-off guard everywhere.** The quick writing actions respect the AI-enabled setting from any entry point, including the command palette and keybindings.
- **Portable key recovery.** If a saved API key cannot be unlocked on the current device, the AI status line prompts you to re-enter it instead of showing a confusing authentication error.

## Quill 0.1.5 Beta

Quill 0.1.5 Beta focuses on safe rollout surfaces for BITS Whisperer, clearer preference parity, and more accessible status monitoring without changing core editor behavior.

### Added and improved in 0.1.5

- Added QUILL Quick Nav browse-style mode with `Ctrl+Shift+Grave`, cursor-only movement, and explicit non-editing behavior while active.
- Added mnemonic Quick Nav movement for links, lists, list items, tables, block quotes, bookmarks, code blocks, table of contents, headings, heading levels 1 through 6, paragraphs, sentences, and blocks, with `Shift` reversing direction where applicable.
- Added configurable Quick Nav wrap behavior and configurable Quick Nav feedback mode (`speech`, `sound`, `both`, `none`).
- Added document-surface-aware Quick Nav indexing for Markdown and HTML, including heading parsing, Markdown and HTML list-item anchors, paragraph anchors, and sentence anchors.
- Added Quick Nav cache invalidation on document edits, full-text replacement operations, and tab switches to preserve performance and correctness.
- Added BITS Whisperer provider onboarding, readiness checks, capability matrix, and guarded download queue controls.
- Added live Help status-page updates with quieter refresh announcements that only speak when tracked values change.
- Added Preferences controls for AI enable state, BITS Whisperer safe mode lock, auto-open status behavior, and refresh cadence.
- Added rollout-safe diagnostics snapshots and startup onboarding for BW setup defaults.
- Enabled Ruff markdown preview formatting so release docs can stay formatted consistently.
- Added robust command-line options, including `--help`, `--version`, startup cursor targeting (`--line`, `--column`), `--new-window`, and `--wait`.

## Quill 0.1.2 Beta

Quill 0.1.2 Beta expands Quill's writing flow with prediction, snippets, in-app preview, local assistant workflows, and packaging/onboarding polish.

### Added and improved in 0.1.2

- Added **Word Prediction** with `Ctrl+Space`, including document-word, HTML tag, and Markdown tag suggestions.
- Moved **Insert Snippet** to `Ctrl+Alt+Space` and **Manage Snippets** to `Ctrl+Alt+Shift+Space` so snippet insertion no longer clashes with prediction.
- Added a **Word Prediction as you type** preference and View-menu toggle.
- Added **In-App Preview** and **Side-by-Side Preview** with keyboard-first focus movement.
- Added a local **Writing Assistant** menu surface with rewrite/summarize/continue/grammar quick actions and ranked command suggestions.
- Added a sandboxed **Run Python** transform tool for document/selection automation.
- Added first-run **Writing Assistant onboarding** plus **Preferences -> AI Connection** for provider, host, and model setup.
- Added secure optional API-key storage for AI endpoints using **Windows DPAPI**.
- Added AI provider support for **Ollama Cloud (API key)** and improved custom-endpoint handling.
- Added explicit **Ollama Cloud onboarding** guidance in AI Connection, including note that free personal-use access is available with lower usage limits.
- Added **Verify Connection**, **List Models**, and **Recommend Model** actions in AI connection settings.
- Added automatic AI-connection verification on save and an AI-menu status flow with **Ready / Needs attention / Not checked**.
- Added an AI-menu detail line with short verification reason text.
- Improved screen-reader behavior by announcing plain-language AI verification outcomes immediately.
- Improved Ask Quill chat accessibility by announcing incoming responses/proposals/errors as they arrive.
- Updated Windows packaging to stage an assistant setup guide and expose an optional `aiassistant` installer component.
- Added custom profile management with opt-in inheritance from a parent built-in profile or an explicit bare-bones start.
- Added profile quick picker hotkey **Alt+Shift+P** (`help.switch_feature_profile`).
- Updated profile switching so custom profiles can carry feature states, settings, and keymap bindings together.
- Added Markdown list editing flow updates: `Enter` continues list items, `Enter` on an empty marker exits the list, and `Tab`/`Shift+Tab` nest or promote list items.
- Added a **List Manager** (`Ctrl+Alt+L`) under Format -> List for tree-based list restructuring (move, promote/demote, add, edit, delete).
- Added structured **PowerPoint (.pptx) import** with slide titles as headings, bullet levels as nested lists, table extraction, and speaker-note extraction.
- Added **Style Headings...** under Insert -> Heading to apply font family, size, and alignment to current-level or all headings in Markdown/HTML.
- Added **Heading Organizer** (`Ctrl+Alt+Shift+H`) for keyboard-first heading promotion/demotion, section reordering, heading renaming, and accessibility validation before apply.
- Added release-safety fallback for beta testing: Word (`.doc`, `.docx`) and CSV/TSV now open in the standard plain-text editing surface by default.
- Kept structured Word and CSV grid implementations in-repo behind an internal gate for continued verification.
- Added **Watch Folder automation** under **Tools -> Dictation** to monitor a folder and auto-open newly detected supported files.
- Added **Watch Folder Settings** and **Watch Folder Status** commands for path, subfolder, startup, and polling control.
- Added **Watch Folder onboarding** to Startup Wizard and first-run setup flow.
- Removed duplicate path reporting by hiding the status-bar file path item when full path is already shown in the title bar.
- Fixed intermittent unit-test file-locking in UI navigation tests by isolating `QUILL_DATA_DIR` per test.
- Expanded docs and release notes for the complete 0.1.2 feature set.

## Quill 0.1.1 Beta

Quill 0.1.1 Beta advances the 0.1 baseline with update-path hardening, status-bar parity completion, menu/discoverability polish, and documentation alignment.

### Added and improved in 0.1.1

- Completed status-bar interaction parity: focused cell context actions now include **Activate**, **Hide this item**, and **Status bar settings**.
- Added **Restore Defaults** to Status Bar Settings and persisted layout changes.
- Hardened **Help -> Check for Updates...** with guided installer handoff, including close-now support for clean setup.
- Simplified the Search menu to a single **Replace...** entry; replace-all now lives in the Replace dialog and keeps the existing replace-all hotkey path.
- Clarified naming and discoverability around **Workspace Snapshots**, **Recent Marks (Ring)**, and status-bar terminology.
- Expanded regression coverage for search/extend-selection and no-selection transform behavior.
- Added About-dialog acknowledgments for contributors and beta testers.
- Added a full snippets workflow: searchable insert (`Ctrl+Space`), manage (`Ctrl+Alt+Space`), placeholder prompts, trigger expansion, and starter packs.
- Regenerated the signed update feed for `0.1.1`.

## Quill 0.1.0 Beta

Quill 0.1 Beta is the first broad, coherent release of Quill as a screen-reader-first writing, reading, review, and document-intelligence environment for Windows from Blind Information Technology Solutions (BITS) and Community Access.

### Highlights

- Native wxPython editor shell with command palette, tabs, menus, and interactive status bar
- Plain text, Markdown, HTML, EPUB, PDF, DOCX, ODT, RTF, JSON, XML, TOML, CSV, TSV, notebook, and SQLite reading surfaces
- Deterministic GLOW audit and fix workflows inside Quill for plain text, Markdown, and HTML
- Guided optional-tool onboarding for Pandoc, Tesseract OCR, LibreOffice, Ghostscript, HTML Tidy, XML Lint, and PyMarkdown
- Pandoc Conversion Wizard for opening supported source files as Markdown, HTML, or plain text tabs
- In-app diagnostics review before export and in-app bug-report review before launching the Community Access support form
- Autosave, backups, recovery, persistent undo, trusted locations, notifications, and signed update checks
- Windows packaging flow with embedded Python, portable bundle generation, and Inno Setup installer compilation

### What feels new in this release

The Help menu now acts like a real support surface instead of a dead end. Users can review diagnostics before Quill writes a zip, review a bug report before Quill opens the browser, and route support feedback into the shared Community Access support flow with more confidence and less guesswork.

Quill also now has a more practical format-bridge story. With Pandoc available, documents can move into stable text-centric workflows without pushing users into command-line tooling. The external-tools dialog explains what each helper unlocks and keeps the setup story transparent.

### Evening polish updates

- File > Sessions was clarified as **workspace snapshots** with clearer menu labels for saving, opening, recent snapshots, and current workspace documents.
- Mark Ring and Bookmarks language was clarified in-app to distinguish temporary jump points (mark ring) from named jump points (bookmarks).
- Tools menu information architecture was simplified into clear submenus: Writing and Language, Read Aloud, Integrations, Document Intake, Authoring and Automation, Compare Documents, Accessibility, Support, and Customize.
- Added a menu binding contract test so menu IDs and EVT_MENU handlers stay aligned as menus evolve.
- Completed status-bar parity details: focused cell context menu now offers Activate, Hide this item, and Status bar settings.
- Status Bar Settings now includes Restore Defaults and persists layout changes immediately.
- Help -> Check for Updates now includes a guided installer handoff that can close Quill before running setup.
- Version bumped to 0.1.1 for the next patch upgrade path.
- About Quill now includes a sincere thanks to contributors and beta testers: Techopolis, Taylor Arndt, Michael Doise, Kayla Bentas, Shane Popplestone, and Becky Knobb.

### Packaging and release quality

- Embedded Python runtime verification with pinned SHA-256 validation
- Runtime dependency bundling derived from project metadata for UI and spell-check support
- Compiled Windows installer output: `Quill-Setup-0.1.exe`
- Release provenance and SBOM generation support via `scripts/generate_release_artifacts.py`

### Support and feedback

Quill 0.1.1 Beta uses a unified Help-menu support flow. `Help -> Report a Bug...` now handles report preparation, optional diagnostics generation, in-app review, and support-form handoff in one guided path. `Help -> Save Diagnostics...` remains available for standalone diagnostics export.

### Notes

This is a beta release. The product direction is aligned with the Quill 1.0 PRD, while some workflows are still evolving toward that fuller 1.0 target.
