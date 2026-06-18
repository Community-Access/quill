# Changelog

## 0.6.0 — Insert Automation, Quillin Platform, Braille Mode, AI Writing Toolkit (2026-06-17)

### Text hygiene

- **Quill Eraser.** `Tools → Writing & Language → Quill Eraser...` / `Quill Eraser on Selection...`. Deterministic, rule-based text hygiene checker: seven rules covering multiple spaces, trailing whitespace, space before punctuation, excessive blank lines, missing space after sentence/comma/colon punctuation, and lowercase sentence starts. Findings are presented in a modeless, keyboard-navigable review dialog with Apply Fix, Ignore, Go to Issue, Previous/Next, and Rescan actions. All actions are screen-reader-announced. Code files receive a prompt before checking; only safe trailing-space checks run unless you opt in. URLs, emails, file paths, code spans, decimal numbers, times, and (in Markdown) code blocks, front matter, and link URLs are never flagged. Four new preference fields control confidence threshold, two-space-after-period exception, max blank lines, and per-rule disable list. New files: `quill/core/hygiene/` package (findings.py, ignored_ranges.py, rules.py, engine.py), `quill/ui/hygiene_dialog.py`, `quill/ui/main_frame_hygiene.py`. New feature `core.hygiene` in the feature catalog. 41 unit tests in `tests/unit/core/test_hygiene_rules.py`.

## 0.6.0 — Insert Automation, Quillin Platform, Braille Mode, AI Writing Toolkit (2026-06-16)

See `rel.md` for the full narrative release notes.

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
