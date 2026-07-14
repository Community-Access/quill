# QUILL 0.8.0 Beta - User Acceptance Test Runbook (Step by Step)

One continuous, numbered checklist for the public-beta sign-off. Every action and
every validation is a single numbered step with its own checkbox. Numbers run
straight through from start to finish and never restart, so you always know exactly
where you left off: your resume point is simply "I am on Step N."

Work top to bottom. Check a box `[x]` only when that step actually passed in front of
you. If a step fails, write the step number, what you saw, and any crash-bundle path
in the Issue Log at the end, then keep going unless the step is marked
RELEASE BLOCKER.

## How to read each step

- `- [ ] **N.** Do this. EXPECT: what must be true.`
- Tags you will see:
  - RELEASE BLOCKER - must Pass before public beta (user gets stuck or loses data if not).
  - [unit-backed] - logic has automated tests; your job is to confirm it in the real app.
  - [needs setup: X] - requires an optional download/account/server; if you cannot
    provide X, mark the step Blocked with the reason. Never check it on faith.
  - [packaged-only] / [Windows] / [macOS] - only applies to that build or platform.
- Run the first pass of every UI step **keyboard-only** (ignore the mouse), then a
  second pass reading with the screen reader's review/virtual cursor.
- For every step, the honest outcomes are Pass, Fail, Blocked, or Not tested.

## Before you touch a key (read once)

- Use a packaged 0.8.0 Beta Windows build, NVDA and JAWS both available (Narrator and
  VoiceOver where noted; VoiceOver for the macOS part).
- Have the three installers staged (see `upgrade-path-regression-0.8.0.md`):
  `Quill-Setup-0.5.0.exe`, `Quill-for-All-Setup-0.7.0.Beta.1.exe`,
  `Quill-for-All-Setup-0.8.0 Beta 1.exe`.
- Have a fixtures folder with: `.txt .md .html .rtf .docx .doc .odt .epub .pptx
  .xlsx .csv`, a text `.pdf`, a scanned/image-only `.pdf`, a LaTeX snippet, and a
  `.brf`. Keep spare copies; some steps write or delete.
- This runbook references its sibling plans instead of repeating them:
  `fresh-install-regression-0.8.0.md`, `upgrade-path-regression-0.8.0.md`,
  `screen-reader-test-plan.md`.

---

## Part A - Prepare and reset the machine

- [ ] **1.** Confirm the machine meets the bar: Windows 11, NVDA and JAWS installed,
  virtualization available if you also plan the Sandbox fresh-install. EXPECT: both
  screen readers launch and speak.
- [ ] **2.** Copy the three staged installers and the fixtures folder somewhere local.
  EXPECT: all files present and openable.
- [ ] **3.** Back up any real QUILL data you care about: copy `%APPDATA%\Quill`
  elsewhere. EXPECT: a backup exists (the reset deletes this folder).
- [ ] **4.** Open PowerShell in `docs\release`. Run `.\clean-quill-install.ps1 -Backup`.
  EXPECT: it stops any QUILL process, runs any uninstaller, and removes both branding
  folders and the data dirs; it prints "Clean."
- [ ] **5.** Verify clean: `Test-Path "$env:LOCALAPPDATA\Programs\Quill"`,
  `...\Programs\QUILL for All"`, `"$env:APPDATA\Quill"`, `"$env:LOCALAPPDATA\Quill"`.
  EXPECT: every one returns False. RELEASE BLOCKER for the upgrade test if not clean.

## Part B - Install the 0.5.0 baseline and create real state

- [ ] **6.** Run `Quill-Setup-0.5.0.exe`; accept the per-user defaults; finish.
  EXPECT: installs to `%LOCALAPPDATA%\Programs\Quill`; Start Menu group is `Quill`.
- [ ] **7.** Launch QUILL 0.5.0 from the Start menu. EXPECT: the window appears, no
  crash dialog, and the screen reader announces the window on foreground.
- [ ] **8.** Help > About. EXPECT: version reads 0.5.0.
- [ ] **9.** Create a new document, type a known paragraph, and Save it to a path you
  record. EXPECT: file saved; note the exact text for later comparison.
- [ ] **10.** Change one visible setting (e.g. a speech voice or verbosity level).
  EXPECT: the change is accepted and persists.
- [ ] **11.** Open the Keymap editor and remap one command; save. EXPECT: remap saved.
- [ ] **12.** Confirm 0.5.0 wrote its state: `Test-Path "$env:APPDATA\Quill\settings.json"`
  returns True; list `%APPDATA%\Quill`. EXPECT: settings/keymap/recovery files exist.
  RELEASE BLOCKER if no state was written (the migration test below would be meaningless).
- [ ] **13.** Record a baseline snapshot for later diffing:
  `Get-ChildItem "$env:APPDATA\Quill" -Recurse | Select FullName,Length | Sort FullName`.
  EXPECT: you have the listing saved.
- [ ] **14.** Close QUILL fully; confirm no `quill.exe`/`pythonw.exe` remains in Task
  Manager. EXPECT: process gone.

## Part C - Upgrade 0.5.0 -> 0.7.0 (the critical migration step)

- [ ] **15.** Run `Quill-for-All-Setup-0.7.0.Beta.1.exe` WITHOUT uninstalling 0.5.0.
  EXPECT: it recognizes the prior install (same AppId) and upgrades in place; it does
  not present as a brand-new install into a fresh dir.
- [ ] **16.** Check install-dir uniqueness: exactly one of `...\Programs\Quill` or
  `...\Programs\QUILL for All` exists; the other is False. EXPECT: exactly one.
  RELEASE BLOCKER if both exist (side-by-side duplication bug).
- [ ] **17.** Settings > Apps. EXPECT: exactly one QUILL entry in Add/Remove Programs.
- [ ] **18.** Check the Start Menu. EXPECT: one usable QUILL entry; no dead `Quill`
  shortcut pointing at a removed path.
- [ ] **19.** Launch the upgraded app. Help > About. EXPECT: version reads 0.7.0 Beta 1.
- [ ] **20.** EXPECT: the first-run setup wizard does NOT appear (existing user;
  `setup_wizard_completed` survived).
- [ ] **21.** Open the document you saved in Step 9. EXPECT: identical contents.
  RELEASE BLOCKER if content changed or the file cannot open.
- [ ] **22.** EXPECT: the setting changed in Step 10 is still in effect.
- [ ] **23.** EXPECT: the key remapped in Step 11 still works.
- [ ] **24.** Confirm settings migration ran: `(Get-Content "$env:APPDATA\Quill\settings.json"
  -Raw) -match '"schema_version"'` returns True (nested/versioned shape, not the old
  flat 0.5.0 layout). EXPECT: True.
- [ ] **25.** Confirm retired ids migrated rather than breaking: a `pyttsx3` read-aloud
  engine becomes `sapi5`; a `vosk`/`whisper` dictation engine becomes `offline` (#617).
  EXPECT: the matching Preferences controls show a valid selection, no blank/error state.
- [ ] **26.** Diff `%APPDATA%\Quill` against the Step 13 snapshot. EXPECT: additive
  changes only; no data loss. RELEASE BLOCKER on data loss.
- [ ] **27.** Re-run the Step 13 snapshot command to capture a 0.7.0 baseline. EXPECT:
  saved for the next diff. Close QUILL fully.

## Part D - Upgrade 0.7.0 -> 0.8.0

- [ ] **28.** Run `Quill-for-All-Setup-0.8.0 Beta 1.exe` over the 0.7.0 install.
  EXPECT: in-place upgrade into the same dir; still exactly one install dir, one
  Add/Remove entry, one Start Menu group.
- [ ] **29.** Launch; Help > About. EXPECT: version reads 0.8.0 Beta 1 with a build stamp.
- [ ] **30.** EXPECT: no first-run wizard; the document, setting, and keymap from the
  earlier steps are all still present.
- [ ] **31.** EXPECT: `settings.json` still loads cleanly (`schema_version` present at
  the version 0.8.0 expects); diff against the 0.7.0 snapshot shows additive-only.
- [ ] **32.** EXPECT: no data-location migration error notice appears on launch; if one
  does, capture it.
- [ ] **33.** Help > Check for Updates. EXPECT: it does NOT advertise a newer version
  (the 0.8.0 feed is intentionally left on the prior release for this beta).

## Part E - Fresh-install confirmation (separate clean machine or Sandbox)

- [ ] **34.** On a clean machine/Sandbox, run the full `fresh-install-regression-0.8.0.md`
  plan. EXPECT: first-run wizard appears, app launches with SR announcement, About reads
  0.8.0 Beta 1, settings/keymap/recovery created fresh. RELEASE BLOCKER on a fresh-install crash.
- [ ] **35.** Confirm every bundled dependency from that plan's section 4 is present in
  the install dir (embedded Python, Pandoc, eSpeak-NG, DECtalk, Piper, braille pack,
  whisper.cpp binary + dlls, Vosk/Kokoro/OCR/spellcheck wheels). EXPECT: all present.

---

## Part F - First run, trust, Safe Mode (on the upgraded 0.8.0)

- [ ] **36.** [unit-backed] Launch with `--safe-mode`. EXPECT: AI, watch folder, and
  Quillin contributions are disabled and say so when invoked; core editing still works.
- [ ] **37.** Invoke an AI action in Safe Mode. EXPECT: a clear "disabled in Safe Mode"
  style message, no network call.
- [ ] **38.** Relaunch normally. EXPECT: AI is off by default and requires explicit enable.

## Part G - Document lifecycle (File menu)

- [ ] **39.** File > New, type a paragraph, Save to a new `.md`, close, reopen. EXPECT:
  content identical; no partial/zero-byte file ever on disk. RELEASE BLOCKER (data integrity).
- [ ] **40.** Open each fixture type in turn: `.txt`. EXPECT: opens, readable.
- [ ] **41.** Open `.md`. EXPECT: opens, readable, Markdown surface.
- [ ] **42.** Open `.html`. EXPECT: opens, readable.
- [ ] **43.** Open `.rtf`. EXPECT: opens in the rich-text surface, formatting preserved.
- [ ] **44.** Open `.docx`. EXPECT: opens, content and structure readable.
- [ ] **45.** Open `.doc`. EXPECT: opens or reports an honest unsupported-variant message.
- [ ] **46.** Open `.odt`. EXPECT: opens, readable.
- [ ] **47.** Open `.epub`; use the EPUB Navigator. EXPECT: opens; chapters navigable.
- [ ] **48.** Open `.pptx`. EXPECT: slides intake as navigable text.
- [ ] **49.** Open `.xlsx`. EXPECT: opens in a grid/structured surface.
- [ ] **50.** Open `.csv`. EXPECT: opens in the CSV grid; rows/columns navigable.
- [ ] **51.** Save As a Markdown doc to `.rtf`. EXPECT: real RTF written; extension drives format.
- [ ] **52.** Save As to `.html`. EXPECT: standalone HTML page written.
- [ ] **53.** Save As to `.txt`. EXPECT: markup stripped per the Links-in-plain-text setting.
- [ ] **54.** Save As to `.docx`. EXPECT: valid Word file.
- [ ] **55.** Confirm the post-Save-As reload behavior matches Settings > Editing
  (auto-reload / keep surface / prompt). EXPECT: behaves as configured.
- [ ] **56.** Open three modified docs and Save All. EXPECT: all three persist.
- [ ] **57.** Save As Plain Text on one. EXPECT: honors the chosen link export mode
  (text+URL default / text only / URL only / original Markdown).
- [ ] **58.** Edit a doc, change the file externally, Reload from Disk. EXPECT:
  confirmation first; edits discarded only after confirm.
- [ ] **59.** Edit/save a doc several times, then File > Restore Backup. [needs setup:
  autosave/backup on] EXPECT: prior versions listed and restore correctly.
- [ ] **60.** Check Open Recent; with "Drop missing recent files automatically" on,
  delete a fixed-drive entry's file. EXPECT: fixed-drive entry drops; USB/network
  entries are kept even when the drive is absent.
- [ ] **61.** File > Snapshots: save a snapshot of several open docs, close all, reopen
  the snapshot. EXPECT: the group reopens as saved.
- [ ] **62.** Copy text elsewhere; File > New from Clipboard. EXPECT: new doc seeded with it.
- [ ] **63.** [needs setup: network] File > Open from URL with a small text URL. EXPECT:
  host and expected size confirmed before download; nothing writes before you confirm;
  a blocked host is reported clearly.
- [ ] **64.** File > Page Setup, then Print (to PDF or printer). EXPECT: dialogs
  keyboard/SR accessible; output matches the document.
- [ ] **65.** Run Current File on a file with an associated tool. EXPECT: the right tool runs.
- [ ] **66.** Place caret on a path/link; Open Target at Cursor. EXPECT: target opens;
  empty target is a clear no-op.
- [ ] **67.** Rename Current File. EXPECT: file and editor state stay consistent.
- [ ] **68.** Delete Current File on a scratch copy. EXPECT: confirms before delete.
- [ ] **69.** With unsaved edits, Close Document then Exit. EXPECT: save prompt; Cancel
  aborts; no data lost. RELEASE BLOCKER (data integrity).

## Part H - Editing (Edit menu)

- [ ] **70.** Exercise Undo, Redo, Cut, Copy, Paste, Select All. EXPECT: each works;
  Undo/Redo granular and consistent.
- [ ] **71.** [unit-backed] Copy several items to Copy Tray slots; paste from a specific
  slot. EXPECT: slots hold distinct items; paste targets the right slot.
- [ ] **72.** Label a Copy Tray slot; use the management dialog and the system-tray path.
  EXPECT: labels persist; every entry point is keyboard/SR accessible.
- [ ] **73.** Copy With Source from a code/quote context. EXPECT: source/attribution included.
- [ ] **74.** Copy rich HTML elsewhere; Paste HTML as Markdown. EXPECT: clean Markdown.
- [ ] **75.** Selection submenu: Select Line, Paragraph, Block, to start/end of line,
  to start/end of document. EXPECT: each selection correct and announced.
- [ ] **76.** Recent Marks (ring): set a mark, jump to previous marks, swap cursor and
  mark, list recent marks. EXPECT: ring cycles; list navigable.
- [ ] **77.** Extend Selection Mode on/off. EXPECT: movement grows the selection in mode;
  normal movement restored on exit; state announced.
- [ ] **78.** Deletion group: Delete to Line Start, Line End, Document Top, Document
  Bottom, Delete Paragraph. EXPECT: each deletes exactly that range; Undo restores.
- [ ] **79.** Word Prediction (Ctrl+.): type to surface document words, HTML tags,
  Markdown tags; arrow + Enter to insert. EXPECT: suggestions navigable and insert correctly.
- [ ] **80.** Toggle Word Prediction off in General Preferences. EXPECT: it stops appearing.
- [ ] **81.** Follow Link with caret on a link. EXPECT: link opens; non-link is a no-op.

## Part I - Find, Replace, cross-file search

- [ ] **82.** Find, Find Next, Find Previous, Find All Matches. EXPECT: matches found,
  counted, announced; Find All lists every match navigably.
- [ ] **83.** Toggle Wrap Find Searches. EXPECT: wrapping behavior changes accordingly.
- [ ] **84.** Replace and Replace All. EXPECT: single and bulk replace work; counts
  announced; Undo reverts cleanly.
- [ ] **85.** Search modes: case, whole word, regex; then an invalid regex. EXPECT: each
  mode changes results; invalid regex is reported, not crashed.
- [ ] **86.** Search > Search in Files across the fixtures folder. EXPECT: results list
  every file/line, keyboard navigable.
- [ ] **87.** Replace Across Files (on scratch copies). EXPECT: only confirmed changes written.
- [ ] **88.** Count Regex Matches and Extract Regex Matches. EXPECT: correct count;
  extract pulls every match.
- [ ] **89.** Mark two blocks; Lines in First Block Only; Lines Common to Both Blocks.
  EXPECT: correct set results.

## Part J - Format and line transforms

- [ ] **90.** Change Case: Upper, Lower, Title, Sentence, Toggle on a selection. EXPECT:
  each correct; Undo restores.
- [ ] **91.** Toggle Line Comment, Toggle Block Comment. EXPECT: comment syntax matches
  the document type.
- [ ] **92.** Indent and Outdent. EXPECT: respect tab/space settings.
- [ ] **93.** Move Line Up/Down, Duplicate Line, Delete Line, Join Lines. EXPECT: each
  behaves; multi-line selections handled; Undo restores.
- [ ] **94.** Bold and Italic on a selection. EXPECT: correct markup for the document format.
- [ ] **95.** Transform Lines: Number Lines, then Number Lines (Advanced) with a start,
  increment, Roman/digit style, zero-pad width, suffix, and alignment. EXPECT: each
  option takes effect.
- [ ] **96.** Transform Lines: Hard-Wrap, Sort Ascending, Sort Descending, Reverse,
  Remove Duplicate Lines. EXPECT: each correct.
- [ ] **97.** Transform Lines: Trim Trailing Whitespace, Normalize Whitespace, Convert
  Indentation to Spaces, Convert Indentation to Tabs. EXPECT: each correct.

## Part K - Insert menu

- [ ] **98.** Insert Link. EXPECT: correct Markdown/HTML link for the document type.
- [ ] **99.** Insert Heading 1 through 6; Decrease Level; Increase Level. EXPECT: correct
  heading markup.
- [ ] **100.** Style Headings (font/size/alignment) for the current level, then all
  levels. EXPECT: styling applies to the chosen scope.
- [ ] **101.** List submenu: Bullet, Numbered, Task. EXPECT: correct list markup.
- [ ] **102.** List Manager and Structured List Studio (F2). EXPECT: keyboard/SR navigable;
  edits the list structure.
- [ ] **103.** Insert Code Block, Insert Footnote. EXPECT: valid markup.
- [ ] **104.** Insert Table (build a grid in the dialog). EXPECT: correct table inserted.
- [ ] **105.** Insert HTML Tag and Insert Markdown Tag. EXPECT: valid tags inserted.
- [ ] **106.** Insert Snippet; then Manage Snippets (create/edit/delete/import/export).
  EXPECT: snippets insert; management persists.
- [ ] **107.** Use snippet placeholders `${input}`, `${choice}`, `${date}`, `${time}`,
  `${cursor}`. EXPECT: placeholder navigation works.
- [ ] **108.** Preferences > Install Starter Snippet Packs. EXPECT: a starter library installs.
- [ ] **109.** Special Character picker (Shift+F2). EXPECT: searchable, keyboard navigable,
  inserts the glyph.
- [ ] **110.** Insert > Date and Time: Insert Date, Insert Time, Insert Date and Time.
  EXPECT: inserts using project `${date}`/`${time}` formats.
- [ ] **111.** Disable the insert-tools Quillin in Preferences. EXPECT: the Date and Time
  items disappear with it.
- [ ] **112.** Insert File Content from another file. EXPECT: contents inserted at the caret.
- [ ] **113.** Insert Equation (Ctrl+Shift+E): enter `E=mc^2`, choose inline vs block.
  EXPECT: mode step appears; correct delimiters inserted.
- [ ] **114.** Insert Equation: paste a `<math>` MathML fragment. EXPECT: inserted verbatim,
  no mode step.
- [ ] **115.** Re-invoke Ctrl+Shift+E on a selected LaTeX equation. EXPECT: delimiters
  stripped and the bare formula pre-fills the prompt.

## Part L - View and preview

- [ ] **116.** Toggle Soft Wrap. EXPECT: wrapping changes; file content unchanged.
- [ ] **117.** Auto Side-by-Side Preview; edit and watch it update. EXPECT: preview tracks edits.
- [ ] **118.** Focus Preview, then return to the editor. EXPECT: SR focus moves to the
  named "Preview" pane and back (see screen-reader TC-EDIT-003).
- [ ] **119.** Show Tab Control toggle. EXPECT: the document tab strip shows/hides.
- [ ] **120.** Start With No Document Open; restart. EXPECT: opens into an empty workspace.
- [ ] **121.** Preview, Preview Side by Side, Browser Preview. EXPECT: rendered views match
  the document; Browser Preview renders equations via MathJax.

## Part M - Navigate

- [ ] **122.** Go To Line, Go To Page, Go to Percent. EXPECT: caret lands correctly.
- [ ] **123.** Back Location and Forward Location (Alt+Left/Right on Windows). EXPECT:
  location history moves; chords match the platform.
- [ ] **124.** Next Heading / Previous Heading in a multi-heading doc. EXPECT: lands on
  the right headings; announced.
- [ ] **125.** Outline Navigator. EXPECT: navigable outline; selecting an entry jumps there.
- [ ] **126.** Heading Organizer (level edits, section reorder, validation). EXPECT:
  reorders sections; reports invalid heading nesting.
- [ ] **127.** Next/Previous Block, Next/Previous Structure, Next/Previous Region;
  Match Bracket. EXPECT: each moves to the correct element; bracket pair matched.
- [ ] **128.** Set Bookmark, Go To Bookmark, List Bookmarks. EXPECT: bookmarks set,
  persist, navigate; list keyboard navigable.
- [ ] **129.** First Non-Blank, Last Non-Blank. EXPECT: caret moves as described.

## Part N - Reading: Read Aloud and speech synthesis

- [ ] **130.** [needs setup: engines bundled] Read Aloud with eSpeak-NG. EXPECT: speaks;
  voice/rate work; stop is immediate.
- [ ] **131.** Read Aloud with DECtalk. EXPECT: speaks.
- [ ] **132.** Read Aloud with SAPI5/Windows. EXPECT: speaks.
- [ ] **133.** Read Aloud with Piper. EXPECT: speaks (note if absent in this build).
- [ ] **134.** Read Aloud with Kokoro. [needs setup: model] EXPECT: speaks after model present.
- [ ] **135.** Text cleanup for speech. EXPECT: markup/URLs spoken sensibly, not raw.
- [ ] **136.** Batch Export to Speech Audio for one document. EXPECT: audio file produced;
  progress announced; cancel works.
- [ ] **137.** [needs setup: AI/translation] Export to Translated Speech Audio (one doc).
  EXPECT: translated audio produced, or a clear "needs X" message.
- [ ] **138.** Build Audiobook from a folder of documents. EXPECT: combined audiobook with
  per-document structure; progress and completion announced.
- [ ] **139.** SSML Builder produces SSML; play it back. EXPECT: valid SSML; playback honors it.

## Part O - Dictation (speech-to-text)

- [ ] **140.** [Windows][needs setup: Windows speech] F9 hold-to-dictate. EXPECT:
  recognized text inserts as ONE undoable edit.
- [ ] **141.** Ctrl+F9 locked dictation session; then Escape. EXPECT: session toggles;
  Escape cancels cleanly.
- [ ] **142.** [packaged-only][needs setup: model download] Tools > Speech > Manage Speech
  Models: download a Whisper model; dictate with whisper.cpp. EXPECT: bundled
  `whisper-cli.exe` + dlls present; model downloads on first use; inserts as one edit.
- [ ] **143.** [needs setup: ~40MB model][unit-backed] Select Vosk; dictate. EXPECT:
  selectable out of the box; model downloads on first use; works.
- [ ] **144.** [packaged-only][needs setup][unit-backed] Tools > Speech > Whisperer >
  Download Faster Whisper Engine. EXPECT: wheel-only install into app-data engine-packs
  (no admin); engine then appears in the chooser; blocked in Safe Mode; confirmation +
  progress shown. (RELEASE-001 needs live packaged validation.)
- [ ] **145.** [needs setup: API keys][unit-backed] Configure and run the Groq, OpenAI
  Whisper, and ElevenLabs transcription Quillins. EXPECT: each transcribes; missing key
  reported clearly; egress only on explicit use.

## Part P - OCR and document intake

- [ ] **146.** [needs setup: OCR model may download] OCR Image on a scanned image /
  image-only PDF. EXPECT: text extracted into a document; progress announced.
- [ ] **147.** Open the text `.pdf` fixture. EXPECT: text extracts with sensible structure.
- [ ] **148.** Open the image-only `.pdf`. EXPECT: routes to OCR or clearly says it needs OCR.
- [ ] **149.** Confirm `.docx/.pptx/.xlsx` intake via markitdown yields clean navigable text.

## Part Q - AI Assistant

Throughout: no cloud call without an explicit AI action; no chat transcript persisted
by default; keys in Windows Credential Manager with DPAPI fallback.

- [ ] **150.** [needs setup: provider] AI Hub: pick a provider (Ollama local/cloud, OpenAI,
  Claude, OpenRouter, Gemini, or Custom OpenAI-compatible); confirm host/model. EXPECT:
  provider selectable; defaults pre-filled where applicable.
- [ ] **151.** Enter a key if required; Verify Connection. EXPECT: result announced in
  plain language; AI status line updates.
- [ ] **152.** List Models and filter; Recommend Model; Save. EXPECT: models fetched and
  filterable; a recommendation is offered; settings persist.
- [ ] **153.** Force each connection error and read the message: bad key (401), no-access
  (403), warming up, server-not-running, rate-limit, key-unlock-failed. EXPECT: each
  documented message appears and is reachable.
- [ ] **154.** [Windows][unit-backed] Confirm the saved key is in Credential Manager
  (DPAPI fallback), not plain text. EXPECT: not stored in clear.
- [ ] **155.** Rewrite Selection with a selection, then without. EXPECT: announces scope
  ("Rewrite paragraph (N words)"); empty target says "Nothing to rewrite".
- [ ] **156.** Summarize Selection, Continue Writing, Fix Grammar (with and without a
  selection). EXPECT: correct scope each; with AI off all announce "AI is turned off..."
  and do nothing.
- [ ] **157.** Ask AI (one-off question). EXPECT: a single answer returns.
- [ ] **158.** Check Grammar with AI. EXPECT: suggestions returned.
- [ ] **159.** Writing Assistant / Ask Quill Chat: send a prompt; jump between turns by
  heading; new replies announced. EXPECT: each turn is a heading; auto-announced.
- [ ] **160.** Have the assistant propose a command/edit; approve it. EXPECT: nothing
  applies without your approval.
- [ ] **161.** Change provider/model from the in-chat picker; Escape to close. EXPECT:
  the active provider/model bar updates; chat closes on Escape.
- [ ] **162.** [needs setup: model] On-device model: place a `.gguf` in the models dir
  (or set `QUILL_LLAMA_MODEL`); chat. EXPECT: responses without network.
- [ ] **163.** Prompt Studio / Prompt Library: build a custom prompt with template
  variables; save and reuse. EXPECT: variables resolve; saved prompts persist.
- [ ] **164.** Skill Library (.sqp): run a skill with parameters; import/validate a skill.
  EXPECT: skills run; parameter controls named (screen-reader TC-A11Y-003a); invalid
  skills reported.
- [ ] **165.** Agent Center: generate a guided task plan; review before sending. EXPECT:
  a reviewable plan; nothing executes without your go-ahead.
- [ ] **166.** Confirm first-run AI consent acknowledgement appeared once and AI stays off
  until enabled. EXPECT: explicit opt-in.

## Part R - Braille mode

- [ ] **167.** Open the `.brf` fixture; toggle Braille Mode; translate to/from UEB.
  EXPECT: uses the bundled liblouis pack; round-trips sensibly; mode announced.
- [ ] **168.** BRF tools and BRF sidecar. EXPECT: BRF tools operate; sidecar metadata
  preserved on save.

## Part S - Math, citations, markdown profiles

- [ ] **169.** Confirm equations export/render in Browser Preview and HTML export (MathJax).
  EXPECT: equations render correctly.
- [ ] **170.** Insert citations; build a bibliography. EXPECT: citations and generated
  bibliography correct and navigable.
- [ ] **171.** Switch Markdown profile; generate a Table of Contents. EXPECT: profile
  changes markup behavior; TOC reflects the headings.

## Part T - Verbosity and announcements

- [ ] **172.** [unit-backed] Set verbosity low, then medium, then high; perform move/
  select/save actions at each. EXPECT: announcement detail scales with the level.
- [ ] **173.** Confirm the verbosity status line is named "Verbosity status"
  (screen-reader TC-A11Y-002b). EXPECT: correct name.
- [ ] **174.** [unit-backed] Confirm no status-bar update is silent (GATE-12). EXPECT:
  every status change is announced.

## Part U - Accessibility core (run the screen-reader plan)

- [ ] **175.** Editor surface: focus the editor. EXPECT: announced "Document", text-area
  role, multi-line; typed text reads back; selection stays visible (screen-reader TC-EDIT-001).
- [ ] **176.** With focus in the editor, press Tab. EXPECT: focus LEAVES the editor; Tab
  is not trapped and inserts no tab character (TC-EDIT-002). RELEASE BLOCKER if trapped.
- [ ] **177.** Document tabs and side preview: arrow across tabs, Enter on one, focus the
  preview. EXPECT: "Open documents" tab group; Enter announces "Focused document <name>";
  preview named "Preview" (TC-EDIT-003).
- [ ] **178.** Status bar segments: invoke focus-status-bar; Tab across cells; Escape.
  EXPECT: each cell "Status bar, <label>, <value>"; Escape "Returned to editor" (TC-EDIT-004).
- [ ] **179.** Dialog naming/focus contract across representative dialogs: names present,
  initial focus on content not OK, Tab/Escape work, errors move focus to the field
  (screen-reader TC-A11Y-001..004, FOCUS-001, KEY-001). EXPECT: all pass. RELEASE BLOCKER class.
- [ ] **180.** Region model: Next/Previous Region movement. EXPECT: moves between regions;
  announced.
- [ ] **181.** Run the keyboard-trap / accessibility audit tool. EXPECT: it runs and reports.
- [ ] **182.** Contrast/theme: dirty-title style, title-path style, system-theme respect.
  EXPECT: information never conveyed by color alone; theme follows the setting.
- [ ] **183.** Sound notifications / earcons: toggle and trigger. EXPECT: meaningful,
  toggleable cues.
- [ ] **184.** Startup speech is opt-in (not automatic); the post-show foreground
  announcement fires on launch (#259). EXPECT: SR announces the window on launch; no
  forced startup speech.

## Part V - Profiles, keyboard packs, customization

- [ ] **185.** Switch a feature profile. EXPECT: enables/disables the documented feature
  set; persists.
- [ ] **186.** Fine-tune an individual feature toggle. EXPECT: overrides the profile; persists.
- [ ] **187.** Switch a keyboard pack. EXPECT: remaps keys as documented; announced.
- [ ] **188.** Keymap editor: remap a command, create a conflict, save. EXPECT: remap
  applies; conflicts warned, not silently overwritten.
- [ ] **189.** Customize Menus. EXPECT: customization persists; keyboard/SR accessible.
- [ ] **190.** Settings dialog: change a representative setting in each group; restart.
  EXPECT: changes persist atomically and survive restart; sensitive settings use DPAPI.

## Part W - Quick Nav, command palette

- [ ] **191.** Enter QUILL Quick Nav mode; exercise the QUILL-key prefix actions; use the
  Quick-Nav keyboard manager. EXPECT: mode toggles and is announced; prefix actions fire;
  manager edits Quick-Nav bindings.
- [ ] **192.** Command Palette: open it; use `>` general, `:` by id, `?` bound-first,
  `~` recent. EXPECT: each mode reranks; arrow/Enter run a command; Escape closes; list
  fully SR navigable.

## Part X - Quillins (extensions)

- [ ] **193.** Confirm the bundled Quillins are present and each contributes its items:
  insert-tools, line-tools, text-tools, markdown-helpers, math-equations, brf-tools,
  journal-stamp, status-scribe, smart-insert, doc-guardian, insert-character,
  ai-writing-prompts, ai-writing-skills, word-count-node, and the three transcription
  Quillins. EXPECT: contributions appear.
- [ ] **194.** Disable one Quillin. EXPECT: exactly its contributions disappear.
- [ ] **195.** Quillins Manager + Preferences: enable/disable/configure a Quillin. EXPECT:
  state persists; prefs keyboard/SR accessible.
- [ ] **196.** Trigger a Document Event that an event-driven Quillin handles. EXPECT: it
  fires on the documented event.
- [ ] **197.** [needs setup: bundled Node] Run the `word-count-node` example. EXPECT: the
  Node runtime executes it and returns a result.
- [ ] **198.** [unit-backed] Under `--safe-mode`, confirm no Quillin contributions load.
  EXPECT: none load.
- [ ] **199.** Lint a Quillin: `python -m quill.tools.quillin_lint <dir> --strict`. EXPECT:
  reports issues; a valid Quillin passes.

## Part Y - Eraser, abbreviation, insert automation

- [ ] **200.** Quill Eraser on the whole document, then Quill Eraser on Selection. EXPECT:
  removes the targeted content per spec; Undo restores.
- [ ] **201.** Define and trigger an abbreviation while typing; then toggle it off. EXPECT:
  expands as configured; can be disabled.
- [ ] **202.** Insert Automation: set up a smart trigger and an append anchor; append to a
  log file. EXPECT: triggers fire; appends land at the anchor; log entries accumulate.

## Part Z - Recovery, sessions, safety

- [ ] **203.** Confirm edits autosave per setting; backups accumulate (restore tested in
  Step 59). EXPECT: autosave occurs.
- [ ] **204.** Force a hard kill with unsaved work; relaunch. EXPECT: unsaved work is
  recovered or clearly offered for recovery. RELEASE BLOCKER (data integrity).
- [ ] **205.** Enable persistent undo; edit, close, reopen, Undo. EXPECT: undo history
  survives the reopen.
- [ ] **206.** Sessions restore open docs/state; Notebooks group documents. EXPECT: both
  behave as designed.
- [ ] **207.** Confirm marks (transient ring) and bookmarks (named, persistent) behave
  distinctly. EXPECT: clear distinction.
- [ ] **208.** Trusted locations: act on an untrusted location. EXPECT: prompts for trust
  and remembers the choice.

## Part AA - Remote files and GitHub

- [ ] **209.** [needs setup: servers][unit-backed] Manage Remote Sites; open and save over
  FTP. EXPECT: confirms host/expected size; no local write before confirm.
- [ ] **210.** Open/save over SFTP; confirm SSH host-key policy defaults to reject and
  trust-first-use only when enabled. EXPECT: secure default.
- [ ] **211.** Open/save over HTTPS/WebDAV. EXPECT: verified TLS; size/host confirmed.
- [ ] **212.** Open/save over S3 (or S3-compatible). EXPECT: works; explicit confirm.
- [ ] **213.** [needs setup: GitHub] File > Open from Remote > GitHub; open a repo. EXPECT:
  files open/save against the repo.
- [ ] **214.** In the GitHub open-repository form, submit invalid owner/repo. EXPECT:
  focus moves to the field and the error is announced (screen-reader TC-A11Y-004).

## Part AB - Updates and localization

- [ ] **215.** Help > Check for Updates (manual). EXPECT: does NOT advertise a newer
  version for this beta; the check is accessible and clear.
- [ ] **216.** Confirm the automatic-update setting and release-channel selection behave;
  no surprise downloads. EXPECT: consent respected.
- [ ] **217.** Change QUILL's display language; restart if required. EXPECT: UI strings
  localize; no raw `lazy_gettext` proxy leaks into a control (#261 class); untranslated
  strings fall back to English, not blank.

## Part AC - Help, About, crash, diagnostics

- [ ] **218.** F1 on several focused controls. EXPECT: help targets the focused control;
  the help surface is keyboard/SR accessible.
- [ ] **219.** Help > About; arrow across the native ListCtrl tabs (#260). EXPECT: version
  reads 0.8.0 Beta 1; tabs named (screen-reader TC-A11Y-001b) and keyboard navigable.
- [ ] **220.** Report a problem from inside QUILL. EXPECT: the flow collects what it needs
  and is accessible.
- [ ] **221.** Trigger a non-fatal error; review the crash-submit dialog and the produced
  bundle. EXPECT: dialog accessible; bundle written; secrets redacted (no keys/tokens).
  RELEASE BLOCKER (privacy) if secrets leak.
- [ ] **222.** Help > Application Status; Tab across the status tabs. EXPECT: tabs/lists
  named (screen-reader TC-A11Y-001a/002a); live task and download state shown.

## Part AD - Developer Console (QDC)

- [ ] **223.** Open the QDC; run basic Python; inspect state. EXPECT: first-run warning
  shown; commands run; SR-friendly transcript captured.
- [ ] **224.** Record and replay a macro in the QDC. EXPECT: macro records and replays.
- [ ] **225.** TypeScript console: run a snippet with the documented globals. EXPECT: runs
  in its worker within limits.
- [ ] **226.** Run the accessibility diagnostics commands from the console. EXPECT: reports
  region/focus/name state.
- [ ] **227.** Console safety: attempt a dangerous op and a remote execution. EXPECT:
  dangerous ops gated; remote honors the trust model; disabled in Safe Mode where applicable.

## Part AE - macOS [macOS]

- [ ] **228.** [macOS] Launch on macOS; navigate menus, editor, and dialogs with VoiceOver.
  EXPECT: fully VoiceOver accessible; Back/Forward location chords are Cmd+[ / Cmd+].
- [ ] **229.** [macOS] On Apple Silicon (macOS 26+), confirm Apple Foundation Models is the
  on-device AI backend. EXPECT: on-device responses where available.
- [ ] **230.** [macOS] Exercise macOS speech/dictation paths. EXPECT: behave or degrade cleanly.

## Part AF - Cross-cutting non-functional

- [ ] **231.** Run the whole core editing flow under `--safe-mode`. EXPECT: editing/format/
  navigate/search all work; AI, watch folder, Quillins off and say so.
- [ ] **232.** Start a long task (batch export or model download) and keep editing. EXPECT:
  UI stays responsive; work runs off the UI thread; progress announced; cancel works.
- [ ] **233.** [unit-backed] With consent off, attempt each outbound feature. EXPECT: no
  outbound call without explicit consent; each egress matches an audited call site.
- [ ] **234.** Where safe, interrupt during a settings/document save. EXPECT: no truncated/
  corrupt file; either old or new content survives whole.

## Part AG - Final uninstall

- [ ] **235.** Uninstall via Add/Remove Programs. EXPECT: the install dir is removed; no
  orphaned second QUILL entry; `%APPDATA%\Quill` intentionally left behind (data preserved).
- [ ] **236.** Confirm no dead Start Menu shortcut remains under `Quill` or `QUILL for All`.
  EXPECT: none.

---

## Issue Log

Record every Fail/Blocked here so nothing is lost between sessions.

| Step | Severity (Blocker/Major/Minor) | What you saw (and SR announcement) | Crash-bundle path | Issue # |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Resume tracker

- Last step completed:
- Next step to run:
- Date / session:

## Sign-off

- Tester(s):
- Build / commit under test:
- Screen reader(s) and version(s):
- OS / platform:
- Date started / finished:
- Steps attempted (range) / total 236:
- Release blockers found (must be zero to ship):
- Major / Minor issues filed (IDs):
- Blocked / Not-tested steps and why:
- Overall: Pass / Pass-with-known-issues / Fail
- Notes:
