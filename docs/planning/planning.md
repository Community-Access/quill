# QUILL planning: open work and completed log

Running capture for the push to a polished 0.5.0. **Open items are at the top in
priority order; the completed log is the running total at the bottom.** Below the
completed log is the consolidated planning archive (ROADMAP, editors, glow, aa,
pi) with the deeper, ID-tagged idea backlog.

## Future feature plans

Long-form specs for features that have not been promoted to a release yet
live under `docs/`. These are reference designs, not active milestones:

- **[`docs/braille.md`](braille.md)** — **QUILL Braille Mode** (`.brf`/`.brl`
  /`.pef`/`.ueb`). A six-phase roadmap (BRF Core, Page Intelligence, Proofing &
  Progress, Validation, optional UEB Translation Pack, Source-to-BRF linking).
  English UEB only in v1.0; liblouis lives in an out-of-process worker, never
  bundled. Implementation will only begin after the current 0.5.0/0.6.0 push
  ships, but the spec is the source of truth for the data structures, status
  bar design, and screen-reader announcements.

---

## Open issues (priority order)

### P0 — verify what shipped this pass (ship-blocking)
- **O1. Verify bundled GLOW.** Build a real `--bundle-python --compile-installer`
  distribution and confirm the bundled engine resolves and runs
  (`import quill_glow_core` + one structured audit). Ref: GLOW-1/8.
- **O2. Live installer pass** on a clean Windows 10/11 VM: install, Start-menu
  launch, Open-With + Send-to-Quill verbs, uninstall data prompt. Inno Setup 6.3+.

### P1 — 0.5.0 UX issues (new list)
- **O5. Ask QUILL (Alt+Q) magic [#4].** Keep the HTML/WebView chat (the user
  likes it); add the controls around it.
  - **[DONE]** Always-visible active-provider/model bar with a "Change provider or
    model" reveal; Save sets the default. Insert-into-document footer: scope (Last
    response / Entire transcript) x format (Plain text / Markdown / HTML), backed
    by `quill/core/ai/chat_export.py`. Core shipped: `chat_export`, per-provider
    key + default-model storage, `test_chat` (all tested).
  - **[OPEN]** Per-message action buttons *inside* the WebView (copy / insert /
    regenerate / delete on each turn) — limited by the external
    `wx_accessible_webview` component; today granularity is last-response vs whole
    transcript. A model **dropdown** (populated from the provider) instead of the
    free-text model field.
  - **[OPEN] Two AI stacks.** The chat dialog uses `quill.core.ai_chat`
    (PROVIDERS + credential_store) while the AI Hub / connection dialog uses
    `quill.core.assistant_ai` (providers.py + per-provider keys). Unify these as
    part of O6 so keys/models/defaults are shared, not duplicated.
- **O6. AI Hub = one rich, multi-provider config surface [#5].** The friction:
  today there is ONE active provider, ONE globally-stored key, and ONE model, so
  you cannot set up OpenAI *and* Claude *and* Gemini each with their own key and
  default model and flip between them — switching providers loses the previous
  key, and the Hub is only a launcher (no inline provider/model editing).
  Design (Settings-style two-pane): left = a list of every provider (Ollama
  local, Ollama Cloud, OpenAI, Claude, OpenRouter, Gemini, custom); right = that
  provider's config (host, API key, default model, a "List models" picker), a
  **Test Chat** button to confirm it actually answers, and a "Make active"
  action. Merge "AI Model and Connection" (on-device model tiers) in as its own
  left-pane entry. Every provider's key/model persists independently so a user
  can work through them all.
  - **[DONE] Core foundation (`quill/core/assistant_ai.py`, 46 tests):**
    `test_chat(settings, api_key)` (the Test Chat primitive); per-provider key
    storage `provider_credential_target` / `load_provider_api_key` /
    `save_provider_api_key` / `clear_provider_api_key` (each provider keeps its
    own key under a distinct credential target); and `set_active_provider(settings,
    key)` which persists the per-provider key, saves the active connection, and
    mirrors the key to the legacy active-key store so generation uses it
    immediately.
  - **[DONE] Menu cleanup + About merge.** `open_ai_hub` now opens the
    consolidated config dialog; the **AI Model and Connection** and **Forget API
    Key** menu items were removed (per-provider Forget lives in the Hub), and
    **About BITS Whisperer** was folded into **About Quill** (its two menu items
    removed). Tests updated.
  - **[OPEN] Polish:** a true Settings-style two-pane Hub (provider list + panel)
    over the current provider-dropdown surface; unify the chat dialog's separate
    `ai_chat` stack so keys/models are shared.
- **O7. GLOW deferred for 0.5.0 [#3].** Per direction, GLOW is hidden rather than
  fixed for now: a new locked-off `core.glow` feature gates the audit/fix and
  "Check for GLOW Updates" commands and menu items, so GLOW is invisible to users.
  Report a Bug / diagnostics are unaffected (they read the GLOW engine version
  independently). When GLOW is re-introduced, remove `locked_off` and fix the
  updater 404 (engine refs `s:\code\glow`, `s:\code\quill-glow-core`).

### P1 — honesty / correctness (carried over)
- **O11. GLOW consent surfaces.** Per-action structured-audit prompt (GLOW-3) and
  networked-feature consent — AI alt-text, PII redaction, WCAG language (GLOW-7).
- **O12. Azure provider.** Implement (deployment-vs-model endpoint) or formally
  drop from the spec. Docs already accurate. Ref: AI-15.

### P2 — planned features (ROADMAP tier order)
- **O13. Startup wizard extra pages:** watch-folder, GLOW consent, language selector.
- **O14. Quick Nav enhancements:** live-count panel, table review, misspellings /
  search as nav types.
- **O15. Un-gate structured Word view + CSV grid** after validation.
- **O16. BITS Whisperer transcription runtime** + three-tier providers. Ref: BW-1, BW-9.
- **O17. Native RTF editing** (`core.rich_text_lens`). Ref: RTF lens.
- **O18. Quillin Hub launch** (`hub.quillforall.org`).
- **O19. macOS port** to shipping quality. Ref: #42.

### P3 — hygiene / backlog
- **O20. Extract `main_frame_statusbar.py`** to lower its budget below the
  rebaselined 540.
- **O21. Master backlog:** the consolidated ROADMAP below is the authoritative,
  tier-ordered list (AI-*, GLOW-*, BW-*, DLG-*, DOC-*, MENU-*, SET-*); editors/aa/pi
  hold the long-form idea inventory.

---

## Completed log (running total)

- **Documentation consolidation, round 3.** Down to 7 root docs. userguide.md
  absorbed developer-console, skills-tutorial, and features; QUILL-PRD.md absorbed
  engineering, qa, deployment, ACCESSIBLEAPPS_INTEGRATION, and the rtf design doc.
  CONTROL_REFERENCE.md kept standalone (it is generated from topics.json by
  build_docs.py — part of the help system). All code/test/CI/site references
  updated; structure test updated; artifacts regenerated (7 md / 7 html / 7 epub,
  parity guard green).
- **AI Hub menu consolidation [#5] + About merge [#1].** `AI Hub` now opens the
  full provider config dialog (provider/key/model, **Test Chat**, per-provider
  **Forget key**, **On-device model...**). Removed the **AI Model and Connection**
  and **Forget API Key** menu items; folded **About BITS Whisperer** into the
  single **About Quill** dialog and removed its two menu entries. Tests updated.
- **GLOW hidden for 0.5.0 [#3].** New locked-off `core.glow` feature gates all
  GLOW audit/fix and update commands + menu items, so GLOW is invisible to users
  until it is finished. Report a Bug / diagnostics remain unaffected.
- **About dialog markdown tables.** `_render_markdown` (browser_preview.py) now
  renders GFM pipe tables as real `<table>` HTML, so the About dialog's dependency
  tables (and every Markdown preview) render correctly. 9 tests.
- **AI Hub config surface [#5, partial].** `AssistantConnectionDialog` became a
  multi-provider config surface: a **Test Chat** button (async), a per-provider
  **Forget this provider's key** button, per-provider key + default-model load on
  provider switch, and `set_active_provider` on save so each provider keeps its
  own key/model. Open: retitle to "AI Hub", remove the redundant **AI Model** /
  **AI Connection** / **Forget API Key** menu items (with test updates), merge
  **About BITS Whisperer** into **About QUILL** (#1), and unify the chat dialog's
  separate `ai_chat` stack.
- **F1 help on the document window [#7].** The main editor (`wx.TextCtrl`) got a
  friendly accessible name ("Document"), and F1 in the editor now routes to the
  `main.editor` help topic via a new `show_topic_help` mixin helper (it was
  resolving to "no help" because the control had no topic name).
- **Session branches blank field [#6].** The unlabeled, empty read-only field in
  the AI Writing Sessions dialog now has a visible "Branch details" label, a
  friendly accessible name, and helpful placeholder text instead of being blank.
- **Ask Quill (Alt+Q) [#4, partial].** Added an always-visible active-provider/
  model bar with a "Change provider or model" reveal, and an Insert-into-document
  footer (Last response / Entire transcript x Plain / Markdown / HTML). New core:
  `quill/core/ai/chat_export.py` (9 tests), per-provider key + default-model
  storage and `test_chat` in `assistant_ai.py` (tests added). The HTML chat is
  unchanged.
- **About dialog version [#2].** The About body was hardcoded to "Quill 0.1 Beta";
  now uses `quill.__version__` (0.5.0) for the heading and prose.
- **"Regex" → "Regular Expressions" [#8].** Renamed the Regular Expression Helper
  and the Count/Extract Regular Expression Matches commands (menu labels, dialog
  title, status messages, the `core.search.regex` feature name, and the bundled
  text-tools manifest/README); test updated.

1. **Doc consolidation, round 2.** `accessibility.md` folded into `engineering.md`;
   the quillin docs + the scripting contract folded into `quillins.md`; every
   code/test/CI/site reference updated; `test_repo_layout.py` updated; artifacts
   regenerated.
2. **Doc consolidation, round 1.** planning/accessibility/features/engineering/qa
   folders rolled into root docs; announce + announcement-beta into
   `announcement.md`; translation docs into `translating.md`; copy_tray_notes into
   `features.md`; the QDC tutorial + automation spec into `developer-console.md`.
3. **QDC `q` API completed.** Built the missing facades in `quill/core/scripting.py`
   (selection, doc, editor, settings, profile, bookmarks, quillins, macros +
   begin/end aliases, spell, diagnostics, describe_command) with defensive host
   plumbing; 36 tests; mypy + ruff clean.
4. **QDC docs reconciled** to the shipped 0.5.0 reality (status note + updated
   Implementation Status).
5. **GLOW ships bundled** (not optional): `glow` added to
   `DEFAULT_BUNDLED_DEPENDENCY_GROUPS`; the full engine installs into the runtime;
   contract wheel kept as offline fallback.
6. **Installer correctness:** architecture/MinVersion/ChangesAssociations added;
   dead `aiassistant` component removed; `announcement-beta.md` dropped from
   `Excludes`; `installer/quill.iss` regenerated; generator tests updated.
7. **Ctrl+Space conflict fixed:** IntelliSense no longer steals `Ctrl+Space`;
   word prediction is `Ctrl+.`, `Ctrl+Space` is Select Chunk (keymap §4.22); docs
   corrected.
8. **AI provider description drift fixed** in `settings_specs.py` (all seven
   providers).
9. **Azure / startup-wizard docs made accurate** (PRD lists real providers and the
   as-built 9-page wizard; planned steps labelled planned).
10. **Module-size gate rebaselined** (`main_frame_statusbar.py` 529 → 540, dated note).
11. **Crashing/hanging tests resolved:** the two flagged tests pass; full
    unit+stability runs ~84s with no hangs; stale `--ignore` guidance removed.
12. **`select_paragraph`** kept palette-only by design; documented.
13. **Doc artifacts** regenerated; parity guard green.

---

# Consolidated planning documents

_Rolled up from the former docs/planning/ folder on 2026-06-13. Each section preserves the original document in full._


---

<!-- Source: docs/planning/ROADMAP.md -->

# QUILL Roadmap: The Path to Magical, Accessible Greatness

Status: Draft 1, authored 2026-06-01. Owner: product and engineering. Current product version: 0.1.5 Beta (target: 1.0 GA).

This is the master plan to take QUILL from an already strong, screen-reader-first editor to something genuinely delightful, dependable, and shocking in the best way. It combs the whole product: every layer, every feature, the QUILL key, navigation, selection, documentation, podcasts and tutorials, plus a full code-quality, security, and performance review.

> This roadmap is the project's living hub: it combines the tier completion tracker, the work-in-progress and completed living lists, and a dated progress log. It was previously named `golden.md`.

Non-negotiable principle: everything ships accessible. No feature is "done" until it is fully operable and pleasant with NVDA, JAWS, Narrator, and VoiceOver, by keyboard alone, in high contrast, and at large font sizes.

## How to read this document

- Sections 1 to 13 are the reasoned plan, grouped by theme.
- Section 14 is the prioritized, trackable backlog. Each item has an ID, priority, size, and acceptance criteria. Treat that table as the single source of truth for execution.
- Priorities: P0 (must fix or land for 1.0), P1 (high value, near-term), P2 (valuable, post-1.0), P3 (exploratory or stretch).
- Sizes: S (under a day), M (a few days), L (about a week), XL (multi-week).

## Table of contents

1. Vision and the "magical and accessible" bar
2. Product-wide delight themes
4. Navigation deep dive (Quick Nav)
6. Menus and information architecture
7. Keymaps and profiles
8. Feature-by-feature enhancement pass
9. Missing features and new magic
10. Code quality review
11. Security review
12. Performance review
13. Documentation, podcasts, and tutorials
14. Prioritized backlog (tracker)
15. Suggested release sequencing

---

## 1. Vision and the "magical and accessible" bar

QUILL already does something most editors never attempt: it treats blind and low-vision writers as the primary audience, not an afterthought. The opportunity now is to make the product feel alive and considerate at every touch point.

What "magical" means here, concretely:

- Every action confirms its outcome in plain language, with consistent phrasing across screen readers.
- The product anticipates intent. It meets people where they are: a new user gets gentle scaffolding, a power user gets speed and silence.
- Nothing is a dead end. Every error explains the next step. Every surface has a way back to the editor.
- Discoverability without clutter. The right command is reachable in two or three keystrokes, and the system teaches itself as you use it.
- Trust is felt. Local-first, explicit consent, visible progress, honest extraction quality.

What "accessible, no questions asked" means here, concretely:

- Stock controls in the writing path, no custom-drawn editor surfaces.
- Focus is always predictable and recoverable. Modal close returns focus to the editor.
- Announcements never fight the screen reader. On macOS we route through VoiceOver and never self-voice.
- Contrast and keyboard-trap checks run in continuous integration, not just on demand.

---

## 2. Product-wide delight themes

These themes cut across many features and inform the backlog.

1. Outcome announcements with a shared grammar. Define a small announcement style guide (verb, object, scope, count) and apply it everywhere. Example: "Rewrote paragraph, 42 words." See backlog A11Y-1.
2. A consistent "scope" concept. Many actions operate on selection, paragraph, or document. Make that fallback model uniform and always announced. See NAV-3.
3. Progressive disclosure. First-run users see scaffolding and tips; power users can silence it. Tie this to feature profiles. See UX-2.
4. Earcons (optional, off by default). Subtle, distinct sounds for mode-enter, action-done, not-found. Custom WAV earcons for the QUILL key (enter, exit, move, error) are now implemented and configurable in Preferences (QK-6, done 2026-06-10). Generalize earcons to other modes tastefully, keep them opt-in.
5. Recoverability everywhere. Undo, backups, crash recovery, and "return to editor" are universal guarantees. Audit every dialog for an escape and a default. See A11Y-4.
6. Honesty about AI and extraction. Always show provider, model, scope, and confidence. Never a silent network call. Already strong; keep it as a hard rule. See AI-5.
7. Feature flags are a fundamental, not an afterthought. Every feature is individually switchable through the existing `FeatureManager` (`quill/core/features.py`), and the UI must honor that choice everywhere: a disabled feature hides or disables its commands, menu items, status-bar cells, QUILL key and Quick Nav entries, settings groups, and onboarding prompts, and a feature with unmet dependencies stays off. Feature profiles (Essential, Writer, Developer Power Text, Accessibility Professional, Full QUILL) let users adopt whole sets at once, and individual toggles override within a profile. Every new feature ships with a `FeatureDefinition` (id, dependencies, maturity, privacy, and whether it is off by default), so users can turn anything on or off and the product respects it consistently, with no orphaned or dead commands. See FLAG-1 through FLAG-4.

---

## 4. Navigation deep dive (Quick Nav)

Quick Nav already supports 13 element types with an asynchronous prewarm cache (debounced at 250 milliseconds, large-document threshold at 20,000 characters). This is strong. Here is how to make it magical.

### 4.1 A unified Quick Nav panel

Add an opt-in "Quick Nav panel" (QUILL key plus N) that lists every navigable element type with live counts ("Headings: 12, Links: 8, Tables: 2"). Arrow into a type, then arrow through instances with a one-line context preview, and Enter to jump. This complements, not replaces, the fast single-letter browse. See NAV-1.

### 4.2 Directional and wrapping controls

- Make next or previous direction explicit and consistent for every element type (Shift reverses direction). Announce wrap events ("wrapped to top"). See NAV-2.
- Honor a configurable "wrap navigation" setting that already exists for find. Reuse it for Quick Nav.

### 4.3 Richer element awareness

- Headings: announce level and number ("Heading 2, 3 of 7"). See NAV-5.
- Links: announce link text and destination, and whether it is an image link with or without alt text (cross-reference the Link Inventory). See NAV-6.
- Tables: enter a lightweight table review mode that announces row and column position while reading cells. See NAV-7.
- Misspellings and search matches as first-class Quick Nav types. See NAV-8.

### 4.4 Semantic landmarks and "jump to anything"

- Build a single index of landmarks (headings, links, tables, code blocks, bookmarks, marks, comments or footnotes) and expose a type-ahead jumper (QUILL key plus G). See NAV-4.
- Cache invalidation correctness: ensure the prewarm cache invalidates on edits within the changed region only, and verify there is no race in cache rebuild. See NAV-9, PERF-5.

---

## 6. Menus and information architecture

The menu bar is exhaustive but the Tools menu has grown very large (roughly 800 lines of construction), and preferences are scattered across View, Tools > Customize, and Tools > Read Aloud > Backend.

### 6.1 Introduce a coherent Settings home

- Create a single Preferences surface (or a clearly grouped Settings menu) that gathers the scattered toggles. Keep deep links from context, but provide one front door. See MENU-1.

### 6.2 Split the Tools menu

- Promote Accessibility and Support to clearer positions. Consider a dedicated Accessibility top-level menu given the product's mission. See MENU-2.

### 6.3 Reduce redundancy and clarify

- Insert Link appears in both Edit and Insert. Keep one primary and make the other a clearly secondary discoverability alias, or remove duplication. See MENU-3.
- Ensure every menu item shows its current keybinding (already common) and that labels match the announcement grammar. See MENU-4.

### 6.4 Context-sensitive help that actually helps

- "What Can I Do Here?" should list commands relevant to the cursor context (inside a list, a table, a code block, a link) with their keybindings, and read well top to bottom. See HELP-1.
- The same instant help is reachable as QUILL key plus question mark anywhere, and as question mark inside any QUILL sub-mode, so users never have to leave the keyboard to learn what is possible. See QK-9.

### 6.5 Deep, tunable settings for every feature

The product should let users tune QUILL like crazy. Every feature that has timing, verbosity, behavior, or appearance should expose those knobs in a discoverable, accessible Settings surface, with sensible defaults, plain-language descriptions, per-setting reset, and search. Power users can shape QUILL precisely to their hands and ears; new users never have to touch any of it.

- Every feature gets a settings group. Each major area (QUILL key, Quick Nav, selection, Read Aloud and speech, spell check, thesaurus, find and replace, snippets, macros, document intake, watch folder, sticky notes, status bar, AI, autosave and recovery, accessibility and announcements) has its own clearly labeled group with all of its tunable options in one place. See SET-1.
- Tune timing and pacing. QUILL key timeout (including no-timeout-until-Escape), Quick Nav debounce and large-document threshold, autosave interval, announcement throttle, Read Aloud rate and pitch and per-sentence pause, and dictation pause sensitivity are all user-adjustable with live preview where possible. See SET-2, QK-4.
- Tune verbosity and announcements. A global verbosity level plus per-event overrides (for example, announce wrap events, announce counts, announce mode entry and expiry, read with spelling, punctuation level) so users decide exactly how chatty QUILL is. See SET-3, FEAT-13.
- Tune behavior. Wrap navigation on or off, sticky browse mode, confirmation prompts on or off per destructive action, default export preset, default new-document format, smart quotes and autoformat toggles, and Quick Nav element types to include or skip. See SET-4.
- Robust settings model. Group the 45-plus flat fields into nested, versioned dataclasses with schema migration, validation on load, and a corrupt-file recovery path that never loses other settings. This is the engineering backbone that makes deep tunability safe. See CQ-4, SET-5.
- Discover, search, reset, and share. The Settings surface is fully keyboard and screen-reader navigable, every setting has a plain-language description and a per-setting reset, settings are searchable by name, and the whole configuration can be exported and imported (and reset to defaults) so users can back up or share a finely tuned setup. See SET-6, SET-7.
- Pre-configuration for organizations. Document a settings schema reference so administrators can pre-tune QUILL for a lab or classroom before first run. See SET-7, DOC-7.

---

## 7. Keymaps and profiles

The keymap system has defaults, a Word pack, import and export, reset, and conflict detection. Vim and Emacs packs are referenced but not implemented.

- Ship at least two more complete keyboard packs: Vim-style and Emacs-style, plus a VS Code-style pack for developers. Each must be fully accessible and documented. See KEY-1.
- Wire conflict detection into the editor and import flow with spoken warnings and a resolution prompt. See KEY-3.
- Add a "print or export keyboard reference" that produces an accessible HTML and EPUB cheat sheet filtered by the active profile. See KEY-2, DOC-6.
- Validate keybinding syntax on save and explain errors in plain language. See KEY-4.

---

## 8. Feature-by-feature enhancement pass

This section proposes targeted delight for existing features. Each maps to a backlog ID.

- Read Aloud: add sentence highlighting sync where the screen reader allows, a "read from cursor" and "read selection" distinction, and a "read with spelling" mode for proofreading. Cache synthesized audio to avoid regenerating identical sentences. See FEAT-1, PERF-3.
- Spell check: pre-load the wordlist in a background thread at startup so the first check is instant; add "add to document dictionary" and "ignore for session" with clear announcements. See FEAT-2, PERF-1.
- Thesaurus: background pre-load, and inline synonym replacement that announces the substitution. See FEAT-3, PERF-2.
- Find and Replace: add "replace and find next" muscle memory, regex named-group preview, and a saved-recipe quick picker. See FEAT-4.
- Snippets: add tab-stops navigation with announced placeholders and a snippet picker with live preview. See FEAT-5.
- Compare documents: add a spoken summary ("12 changes: 5 additions, 4 deletions, 3 edits") and synchronized navigation announcements. See FEAT-6.
- Macros: add named macros with descriptions, a safe replay that announces each step, and export or import. See FEAT-7.
- Document Intake: make the intake report a calm, skimmable summary with confidence and a one-key path to cleanup recipes. See FEAT-8.
- Watch Folder: evolve the single watched folder into Watch Profiles — many folders, each bound to its own action, all feeding one monitorable queue. Announce new arrivals with a non-interrupting notification and a one-key "open it." See FEAT-9 and the WATCH family (WATCH-1 through WATCH-9).
- Sticky Notes: make the vault searchable and screen-reader pageable, with quick capture confirmation. See FEAT-10.
- Status bar: ensure every cell has a crisp spoken label and a context menu, and that layout changes persist and announce. See FEAT-11.

---

## 9. Missing features and new magic

Ideas that would expand the product, in priority order within the backlog.

- Universal "Go to anything" jumper (headings, files, bookmarks, symbols). See NAV-4.
- Session restore polish: name and reopen named workspaces, announce what was restored. See FEAT-12.
- Distraction-free or focus mode tuned for screen readers (silences non-essential chatter, keeps essential confirmations). See FEAT-13.
- Reading ruler and line-focus for low-vision users (high-contrast, large, configurable). See FEAT-14.
- Inline definitions and word lookup (dictionary plus thesaurus) on a single key. See FEAT-15.
- Document health dashboard: one pane combining accessibility audit, contrast, link or alt-text inventory, and plain-language lint. See FEAT-16.
- Export presets: one-key "export to clean HTML or Word or PDF" with announced results, building on Pandoc. See FEAT-17.
- Autosave and recovery transparency: a visible, spoken "last saved" and "recovered from" state. See FEAT-18.
- External file-change watch and safe reload: detect when the open document is changed (or deleted) by another program, reload in place without moving the cursor when the buffer is clean, and offer a clear, spoken reload-or-keep-mine choice on conflict; fully configurable and quiet by default. See FEAT-19.
- Watch Profiles: many folders, many actions, one monitorable queue. The signature automation feature — a blind writer sets up named "profiles," each watching its own folder and running its own action, then monitors everything from one accessible queue. See the design below and the WATCH family (WATCH-1 through WATCH-9).

### Watch Profiles: many folders, many actions, one monitorable queue

Today QUILL watches one folder and opens whatever lands there. That is useful, but it is a single trick. The aggressive vision turns it into a personal, accessible automation hub that no mainstream editor offers a screen-reader user — and it becomes a quiet differentiator that ties the whole product together.

The shape of it:

- **Many independent profiles, each its own watcher.** A profile is a named, enabled-or-disabled rule: a folder to watch, the filters that decide what counts, the one action to take, and what to do with the file afterward. A user can run several at once — "Incoming transcripts" watching a Dropbox folder, "Audio to transcribe" watching a recorder's export folder, "Make accessible" watching a shared drive, "Clean exports" watching a scans folder — and each runs concurrently and fails in isolation, so one bad file never stalls the others.
- **Each folder bound to a different action.** The action is the magic. The built-in set covers Open, Convert or export to a chosen format, Move/copy/archive to a destination, Run a named macro, and Run a saved Python transform, plus consented AI actions (summarize, tag, rewrite to a style). Two more actions light up as their tiers land: "Audit and fix accessibility" through GLOW, and "Transcribe" through BITS Whisperer — which completes a genuinely unique drop-audio-in, get-an-accessible-edited-document-out loop, entirely hands-free and screen-reader-narrated.
- **One queue you can actually watch.** Every detected file becomes a queue item with a clear lifecycle — queued, processing, done, failed, skipped — with ordering, de-duplication (a file is claimed once, never double-processed across profiles), retry with backoff, and pause/resume per profile or globally. The queue is durable: it survives a restart and recovers cleanly, so nothing is silently lost.
- **A Watch Queue Monitor that is born accessible.** Surfaced from Help (alongside the status page) and from the Tools menu, it is a screen-reader-pageable list of queue items showing state, action, profile, source file, outcome, and timing, with one-key pause, resume, retry, open-result, and clear. Arrivals and completions announce through the shared announcement grammar as calm, non-interrupting notifications ("Transcribed meeting.m4a, opened as meeting.md"), and a live per-profile counter ("Make accessible: 3 done, 1 working, 0 failed") gives an at-a-glance pulse without visual reliance.
- **Magical, but safe and quiet by default.** Networked and AI actions stay opt-in per profile with the same no-silent-network promise as the rest of QUILL; nothing reaches a cloud without an explicit, per-profile consent. Wall-clock and concurrency caps (shared with the Python sandbox limits) keep a runaway folder from overwhelming the machine. A dry-run preview shows exactly what a profile would do before it is armed. Profiles are exportable and importable, so a power user or an administrator can pre-configure a whole automation setup and hand it to someone on day one.
- **Feature-flag aware to its core.** The whole Watch Profiles surface lives behind the existing `FeatureManager` and respects it the way every other feature does (delight theme 7). The engine gets its own feature id (succeeding `core.watch_folder`), and each action is gated by the feature that powers it: the AI actions require the AI feature and its consent, the GLOW action requires `core.glow`, the transcription action requires `core.bw_transcription`. When a feature is off, its action is hidden from the profile editor and the action registry advertises it as unavailable with an announced reason rather than failing silently, and the Watch Queue Monitor, menu items, and status entries disappear in lockstep. A profile that depends on a now-disabled action is paused, not lost, and resumes when the feature is re-enabled. Users can run a minimal Open-only setup or a full automation hub purely by toggling features, and the UI always matches their choices.

Why this is a key differentiator: it is the rare feature that is simultaneously a productivity superpower and an accessibility superpower. For a sighted user it is a slick automation hub; for a blind writer it is the difference between manually shepherding every file and simply dropping work into folders and listening to a calm queue do it. It also unifies the product's most distinctive engines — AI editing, GLOW accessibility, and BITS Whisperer transcription — behind one simple, learnable mental model: a folder, an action, a queue.

---

## 10. Code quality review

Overall the codebase is well-structured: clean dataclass document model, a tidy command registry, an elegant three-tier spell-check, a well-designed sandbox, and a solid stability layer (task manager, wx dispatch, safe subprocess, safe regex). No TODO or FIXME debt markers were found in core, which is excellent hygiene. The findings below are about hardening and scaling, not rescue.

### 10.1 Module size and cohesion

- `quill/ui/main_frame.py` is 18,748 lines with 200-plus methods (verified 2026-06-01). This is the single biggest maintainability risk. Extract cohesive mixins or controller modules: menu construction, QUILL key and Quick Nav, selection and marks, file and session lifecycle, status bar, AI actions. Keep behavior identical and covered by tests. See CQ-1. A verified decomposition map into 22 subsystems with line ranges is in Part II, section 16.6.
- `quill/core/read_aloud.py` (roughly 1,130 lines) should become a package with one module per TTS engine behind a common base. See CQ-2.
- `quill/io/structured.py` (roughly 450 lines, 20-plus format branches) should use a dispatch table or per-format reader modules. See CQ-3.
- `quill/core/settings.py` (45-plus fields, a very large `from_dict`) should group related settings into nested dataclasses with versioned schema migration. See CQ-4.

### 10.2 Typing and contracts

- `storage.read_json` and `write_json_atomic` use `Any`. Introduce typed helpers or `TypedDict` and generics where practical so deserialization is type-safe. See CQ-5.
- Apple Foundation Models backend uses `Any` for the SDK handle. Type it behind a Protocol so the core stays strict. See CQ-6.
- Keep strict mypy on `quill/core` and `quill/io` green in continuous integration on every pull request, scoped to those paths to avoid the whole-tree slowdown that previously froze a machine. See CQ-7, PERF-8.

### 10.3 Error handling discipline

- There are several broad `except Exception` blocks marked with noqa (in `assistant_ai.py`, `spellcheck.py`, `ai/assistant.py`, `diagnostics.py`, `updates.py`, `read_aloud.py`). Each is defensible as graceful degradation, but each should log at debug or warning with context so real bugs are not invisible. Define a small "degrade and log" helper and use it consistently. See CQ-8.
- IO reader fallback chains currently return human-readable strings instead of raising. Keep the friendly surface, but log the underlying cause so diagnostics capture it. See CQ-9.

### 10.4 Documentation in code

- Add module docstrings to `io/structured.py`, `search.py`, and other public modules that lack them, and method docstrings to the public surface of `Document`, `CommandRegistry`, and the IO readers and writers. See CQ-10.

### 10.5 Tests to add

- Spell-check tier fallback (enchant to wordlist to stub) and the background pre-load path. See CQ-11.
- Undo and redo behavior and persistence edge cases. See CQ-12.
- IO format coverage beyond text: at least Markdown, HTML, JSON, CSV, DOCX (via the bridge), and PDF quality scoring with small fixtures. See CQ-13.
- Path-safety tests that confirm writes cannot escape the app data directory. See CQ-14, SEC-2.
- Thread-safety test for the thesaurus cache and any other lazily loaded global. See CQ-15.
- A characterization test harness around `main_frame` before the extraction in CQ-1, so refactors are provably behavior-preserving. See CQ-16.

### 10.6 Concurrency

- Note: a verified audit (Part II) confirms the thesaurus, spell-check, and watch-folder caches already use locks, so there is no race there. The remaining concurrency work is documenting the invariants and the storage atomic-write behavior on Windows. See CQ-15, CQ-17, CQ-18.
- Document thread-safety invariants for all module-level caches in a short engineering note. See CQ-17.

---

## 11. Security review

Threat model note: most user data files live under the per-user app data directory, which is trusted in the single-user desktop model. The findings below harden against tampered config, untrusted document inputs, and supply-chain risk.

### 11.1 Subprocess and executable path validation (highest priority)

- TTS and speech engines, and external tools, can be configured with executable paths read from settings. If the settings file is tampered with, an arbitrary executable could be launched. Validate configured executable paths at load time: confirm existence, and prefer an allowlist of known tool names resolved via `shutil.which` or the bundled path. See SEC-1.
- OCR passes a language code to Tesseract via a command flag. Whitelist language codes to prevent flag or argument injection. See SEC-3.
- Continue routing all subprocess calls through `stability/safe_subprocess.py`, and document a `cwd` safety requirement so callers cannot point it outside expected directories. See SEC-4.

### 11.2 Path traversal hardening

- Add a single helper that asserts a resolved path stays within an expected base directory, and use it in `storage.write_json_atomic` and other persistence call sites. Add tests. See SEC-2, CQ-14.

### 11.3 Network and downloads

- Verify TLS certificates explicitly on all outbound requests (AI endpoints, update checks, DECtalk or model downloads). See SEC-5.
- Verify a checksum or signature for any downloaded binary or model before use (DECtalk runtime, GGUF models). See SEC-6.

### 11.4 Secrets

- Current key storage (Windows Credential Manager first, DPAPI-encrypted file fallback; macOS Keychain) is sound. Document the shared-account limitation and add a "forget key" command that clears both stores and announces success. See SEC-7.

### 11.5 Plugins

- The plugin system is a v1.0 skeleton with no sandbox, signing, or capability model. Do not enable third-party plugin loading in a shipping build until a capability model, signature verification, and a trust prompt exist. Gate it behind a clearly experimental, off-by-default flag. See SEC-8.

### 11.6 Python sandbox

- The user Python transform runs in an isolated subprocess with an import allowlist and blocked builtins. Add a wall-clock and memory limit to prevent denial of service from infinite loops, and announce when a transform is terminated for exceeding limits. See SEC-9.

---

## 12. Performance review

The product is responsive for typical workloads. These changes remove first-use stalls and keep the UI thread free.

- Pre-load the 370,000-word spell-check list on a background thread at startup so the first spell check does not stall. See PERF-1.
- Pre-load the thesaurus index in the background; first lookup currently pays the full load cost. See PERF-2.
- Cache synthesized TTS audio so identical sentences are not re-rendered, and avoid round-tripping every sentence through temp files where possible. See PERF-3.
- Replace OCR busy-wait polling with a proper wait or `communicate` to remove the 100 millisecond granularity and reduce churn. See PERF-4.
- Confirm the Quick Nav prewarm cache invalidates only the changed region and never blocks typing; add a perf test for large documents. See PERF-5, NAV-9.
- Move non-critical persistence (settings, palette usage, recent files) off the UI thread or batch writes to avoid synchronous disk stalls. See PERF-6.
- Cache markup-kind inference and heading or block scans per document revision instead of re-scanning on each navigation. See PERF-7.
- Keep the strict type check fast and scoped in continuous integration, and document the safe local command (`mypy quill\core quill\io`) so contributors never run an unscoped, machine-freezing scan. See PERF-8, CQ-7.
- Add a small performance budget suite (startup time, first spell check, first thesaurus lookup, Quick Nav prewarm on a large file) to catch regressions. See PERF-9.

---

## 13. Documentation, podcasts, and tutorials

Documentation greatness is a first-class theme of this plan, equal in weight to the product and engineering work. QUILL's mission demands documentation that is itself a model of accessibility, clarity, and completeness: every feature explained, every keystroke listed, every artifact available in Markdown, HTML, and EPUB, and the whole docs folder organized so that a reader (or a contributor, or a screen-reader user) can always find the right page fast. The bar is not "adequate docs"; it is documentation people point to as exemplary.

Documentation is already strong: a 3,900-plus line PRD, a comprehensive user guide, engineering docs, an accessibility conformance report and VPAT, a localization plan, and multi-format output (Markdown, HTML, EPUB) enforced by a docs-artifact gate. The gaps are learning content, a few reference pieces, and consolidation of the docs folder itself.

### 13.1 Documentation completeness

- Add a dedicated QUILL key primer to the user guide and a standalone quick-reference, positioned as the signature feature. See DOC-1.
- Add a navigation and selection guide that teaches Quick Nav and structural selection with worked examples. See DOC-2.
- Add a developer quickstart for contributors (environment, run from source, test, lint, type-check, build). See DOC-3.
- Generate an API or module reference from docstrings (for example with a lightweight static generator) and publish it in the multi-format pipeline. See DOC-4.
- Keep the docs-artifact gate green: every changed Markdown file regenerates its HTML and EPUB. This is already enforced; document it for contributors. See DOC-5.
- Produce an accessible, profile-filtered keyboard reference in HTML and EPUB. See DOC-6, KEY-2.

### 13.2 Podcast transcripts (launch-ready)

Create a short podcast series with full, accessible transcripts ready for distribution at launch. Transcripts are the primary artifact; audio is optional and secondary. Each transcript must be clean, well-structured Markdown with headings and speaker labels, and follow the plain-language lint already in the repo. Proposed episodes:

1. "Meet QUILL: a text editor that puts blind and low-vision writers first." See POD-1.
2. "The QUILL key: one key to navigate, format, and read." See POD-2.
3. "Reading and reviewing with confidence: Read Aloud, intake quality, and trust." See POD-3.
4. "Writing with on-device AI you control." See POD-4.
5. "Make any document accessible: GLOW, audits, and cleanup." See POD-5.

Each episode delivers a Markdown transcript plus an optional short script for narration. Reuse the existing plain-language lint and docs-artifact pipeline so transcripts ship as HTML and EPUB too.

### 13.3 Tutorials

Create task-focused tutorials, text-first and screen-reader-validated, with optional audio walkthrough transcripts:

1. First session: open, edit, save, and recover. See TUT-1.
2. Navigate any document with the QUILL key and Quick Nav. See TUT-2.
3. Select and transform text by structure. See TUT-3.
4. Find and replace, including regex, safely. See TUT-4.
5. Set up and use AI assistance privately. See TUT-5.
6. Convert and clean up messy documents with Pandoc and cleanup recipes. See TUT-6.
7. Customize keymaps and profiles to fit your hands. See TUT-7.

Each tutorial includes numbered steps, the exact keystrokes, and the expected spoken confirmation, so a screen-reader user can follow along and verify success at each step.

### 13.4 Review and consolidate the docs folder

Treat the `docs/` folder as a product surface that deserves the same care as the code. Review it end to end, consolidate overlap, fix accessibility, and raise every page to a consistent high-quality bar. This is the work that makes documentation greatness real rather than aspirational.

- Full docs audit and inventory. Catalog every file under [docs/](../) (PRD, user guide, engineering docs, accessibility ACR and VPAT, localization, announcements, and the generated HTML and EPUB), note status (current, stub, stale, duplicate), and record the result so nothing is missed. See DOC-14.
- Consolidate and structure. Establish a clear top-level docs index (a single entry page that links to user docs, learning content, reference, and engineering docs), merge overlapping or stub pages, remove or clearly mark stale content, and ensure a predictable folder structure so readers and contributors always know where a topic lives. See DOC-15.
- Raise quality to a consistent bar. Give every page a clear purpose statement, consistent heading structure, working internal links, and a last-reviewed date. Expand the skeletal engineering docs (architecture, module contracts, data layout, runtime model, diagnostics runbook, quality gates) beyond stubs. See DOC-12, DOC-16.
- Documentation accessibility pass. Apply the project's own markdown accessibility rules across all docs source: replace emoji with text labels, remove em-dashes, ensure accessible tables and meaningful link text, and add alt text or text alternatives for any diagrams. Regenerate artifacts and keep the docs-artifact gate green. See DOC-11.
- Make consolidation durable. Add a docs style guide and a contributor checklist (purpose, structure, accessibility, regenerate artifacts) so the folder stays consolidated and high quality over time. See DOC-17.

---

## 14. Prioritized backlog (tracker)

This table is the execution source of truth. Update Status as work progresses. Status values: Todo, In progress, Blocked, Done.

### P0: must land for 1.0

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| SEC-9 | Resource limits for the Python sandbox | Security | M | Todo | A wall-clock and memory limit terminate runaway transforms; termination is announced; test included. |
| KEY-3 | Wire keymap conflict detection into UI and import | Keymaps | M | Todo | Conflicts are detected on bind and import, announced, and resolvable. |
| DOC-1 | QUILL key primer and quick reference | Docs | M | Todo | User guide section plus standalone reference; ships as HTML and EPUB via the gate. |
| DOC-5 | Document the docs-artifact gate for contributors | Docs | S | Todo | Contributor docs explain regenerating HTML and EPUB; gate stays green. |

### P1: high value, near-term

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| CQ-8 | Degrade-and-log helper for broad excepts | Code quality | S | Todo | A shared helper logs context; broad excepts in core use it; no silent failures remain in the listed files. |
| DLG-3.8 | Tier 6 final-QA SR pass — manual NVDA/JAWS/Narrator across `dialogs.md` | Accessibility | M | Tier 6 SR sign-off (maintainer) | The standalone **Tier 6** final-QA item. Execute the full screen-reader sign-off using the written plan `docs/qa/final-qa-test-plan.md` (§6 dialog estate pass): NVDA baseline, JAWS spot (startup, assistant, sticky notes, watch profiles), Narrator sanity, with each `dialogs.md` row carrying pass/fail evidence against a single named build. Requires a live Windows screen-reader runtime and human listening, so it is owned by the maintainer. It aggregates the residual SR sign-off for DLG-2 and DLG-3.6, whose code-level work is Done. Honestly held open until the pass is logged. |
| CQ-11 | Spell-check fallback and preload tests | Code quality | S | Todo | Tier fallback is now covered: `tests/unit/core/test_spellcheck_backend.py` pins each of the three tiers (enchant, bundled wordlist, built-in stub) by seeding the module caches and confirms `backend_info` and `is_known_word` honour the active tier, plus a personal-dictionary override. The background-preload half stays open until a spell-check preload API exists (tracked by PERF-1). |
| NAV-2 | Consistent directional and wrapping Quick Nav | Navigation | M | Todo | Every element type supports next and previous with announced wrap. |
| SHELL-2 | Structured-Markdown OCR verb (AI structuring pass) | Integration | M | In progress | The `ocr-structured` verb, its `shell_verb_ocr_structured` setting, and its AI/assistant gating are wired through the registry, IPC, CLI, and `_handle_shell_request`. **Delivered:** the assistant gained a `structure` operation (`_OPERATION_PROMPTS["structure"]`) that reflows raw OCR text into clean structured Markdown — joining lines broken mid-sentence by the scan, grouping paragraphs, and inferring headings/lists/tables — while the prompt explicitly forbids summarizing, adding, or inventing content; it reuses the existing chunking, `_wrap`, and backend so large scans are handled. `_handle_shell_request` passes `structured=True` for the structured verb; `_run_ocr_on_path` gained a `structured` parameter and, inside the existing OCR worker thread (so the call stays off the UI thread and shares the progress dialog), runs the recognized text through `_apply_ocr_structuring`, which structures via the assistant when one is available and reports available, and otherwise degrades safely to plain OCR with a status note explaining why the pass was skipped. The review dialog title and the insert status line reflect whether the structured pass ran. Covered by core unit tests for the `structure` operation (registration, OCR text reaches the model, the no-summarize instruction) and source-contract tests for the worker wiring and the structured-verb dispatch; ruff + strict mypy clean. **Remaining (honest, needs a live AI key):** the structuring transform cannot be verified end to end here because it requires a configured/available assistant backend; the structuring *quality* on real-world OCR output (multi-column PDFs, tables, headers/footers) still needs tuning against live model responses, and the off-thread assistant call needs a real run to confirm thread-safety and latency under the progress dialog. Until that live verification, this stays honestly In progress. |
| SHELL-3 | Installer-registered "Send to Quill" context-menu verbs (classic/Show-more-options menu) | Integration | M | In progress | **Delivered:** the Inno Setup installer now registers the "Send to Quill" file right-click verbs, generated directly from the single core registry (`quill/core/shell_verbs.py`) by `build_shell_verb_registry_lines()` in `scripts/build_windows_distribution.py`, so the installer menu, the runtime registry writer, the CLI `--action` map, and the Settings toggles can never drift. Each verb is written per file extension under `HKCU\Software\Classes\SystemFileAssociations\<ext>\shell\Quill.<verb_id>` with a `"{app}\run-quill.cmd" --action <action> "%1"` command (run-quill.cmd forwards `%*` to `python -m quill`), gated behind a new opt-in `shellverbs` task, and tagged `uninsdeletekey` for clean uninstall. Six contract tests assert per-verb/per-extension coverage, opt-in + uninstall-clean flags, the launch command, and end-to-end presence in the generated `.iss`; the committed `installer/quill.iss` is regenerated. **Remaining (Windows-runtime only):** one live install → right-click a `.png`/`.pdf` → confirm the verb appears (Show more options / Shift+F10) and runs → uninstall → confirm removal. The Windows 11 *primary*-menu `IExplorerCommand` sparse-package (which the OS gates behind compiled COM + package identity) is descoped to QUILL 2.0. Tracks intake issues #113 (umbrella), #114 (Windows Explorer), and #116 (structured OCR data model, delivered by SHELL-1/SHELL-2); macOS Finder (#115) stays blocked on the macOS port (#42). |
| KEY-1 | Vim, Emacs, and VS Code keyboard packs | Keymaps | L | Todo | Three complete, documented, accessible packs are selectable. |
| MENU-2 | Split the Tools menu and elevate Accessibility | Menus | M | Todo | Tools is smaller; Accessibility is easy to find; labels match announcement grammar. |
| HELP-1 | Context-aware What Can I Do Here | Help | M | Todo | The help lists commands relevant to the cursor context with keybindings, readable top to bottom. |
| FEAT-2 | Spell-check usability polish | Features | S | Todo | Add to document dictionary and ignore for session, with announcements. |
| DICT-3 | User-selectable source mode with merge-and-compare | Features | S | Todo | The user chooses, per lexical kind (spelling suggestions, synonyms, definitions), which source to trust: **Offline only** (fast, always available — the existing spell/thesaurus data), **Online only** (the DICT-1 providers, richer but slower and consent-gated), or **Both, combined**. In combined mode QUILL queries offline and online in parallel, then merges the result lists into one de-duplicated, ranked set that records each entry's provenance (\"offline\", \"Free Dictionary\", \"Datamuse\", or \"both\"), so a word both sources agree on ranks first and the user can see where each suggestion came from. The merge is a pure, tested `core` function (offline list ∪ online list with case-fold de-dupe and a stable agreement-weighted ordering); the online half degrades gracefully so a slow or failed provider never blocks the offline answer. A setting (and the CTX-1 menu) exposes the mode; tests cover the union/de-dupe, agreement ranking, provenance labelling, and the offline-only fallback when consent is off or the network is down. |
| FEAT-16 | Document health dashboard | Features | L | Todo | One pane combines audit, contrast, link or alt-text inventory, and plain-language lint. |
| AI-5 | Reaffirm no-silent-network and scope honesty in code and tests | AI | S | Todo | A test asserts no network call without consent; provider, model, and scope are always shown. |
| DOC-2 | Navigation and selection guide | Docs | M | Todo | Worked examples for Quick Nav and structural selection ship in all formats. |
| DOC-14 | Full docs folder audit and inventory | Docs | S | Todo | Every file under docs is cataloged with status (current, stub, stale, duplicate); the inventory is recorded so nothing is missed. |
| DOC-15 | Consolidate and structure the docs folder | Docs | M | Todo | A single top-level docs index links user docs, learning content, reference, and engineering docs; overlapping and stub pages are merged; stale content is removed or marked; folder structure is predictable. |
| DOC-16 | Raise every docs page to a consistent quality bar | Docs | M | Todo | Each page has a purpose statement, consistent headings, working internal links, and a last-reviewed date; skeletal engineering docs are expanded. |
| DOC-17 | Docs style guide and contributor checklist | Docs | S | Todo | A style guide and a checklist (purpose, structure, accessibility, regenerate artifacts) keep the docs folder consolidated and high quality over time. |
| DOC-18 | Retire the stale, PRD-duplicating engineering/accessibility docs; keep only wired, of-value references | Docs | L | In progress | **Done (scope as decided with the maintainer):** the nine stale, PRD-duplicating engineering documents (`architecture`, `runtime-model`, `data-layout`, `module-contracts`, `roadmap-mapping`, the engineering `README` index, `ai-distribution-recommendations`, `diagnostics-runbook`, `quality-gates`) and their generated `.html`/`.epub` artifacts were retired; their content already lives in `docs/QUILL-PRD.md`. The CONTRIBUTING guide gained a self-contained architecture overview so it no longer depends on the deleted engineering README, and the three broken cross-references were fixed (`SECURITY.md` quality-gates link removed, `docs/site/index.html` engineering-index link removed, the `cp -R docs/engineering` step dropped from `github-pages.yml`). **Intentionally kept as living references (of value, actively wired):** `docs/engineering/{macos-build,security-advisory-workflow,thread-safety}.md` (README/SECURITY/golden evidence) and `docs/accessibility/{acr-vpat,announcement-style-guide}.md` (the ACR/VPAT generator default and the announcement-grammar spec). **Remaining:** folding those five retained references into the PRD as consolidated sections (and then fully retiring both folders) is deferred; until then this row stays In progress. |
| DOC-6 | Profile-filtered keyboard reference | Docs | M | Todo | Accessible HTML and EPUB cheat sheet filtered by active profile. |
| POD-1 | Podcast transcript: Meet QUILL | Docs | S | Todo | Clean Markdown transcript passes plain-language lint and ships as HTML and EPUB. |
| POD-2 | Podcast transcript: The QUILL key | Docs | S | Todo | As above, focused on the QUILL key. |
| TUT-1 | Tutorial: first session | Docs | S | Todo | Numbered steps with keystrokes and expected spoken confirmations. |
| TUT-2 | Tutorial: navigate with the QUILL key | Docs | S | Todo | As above, navigation focused. |

### P2: valuable, post-1.0

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| CQ-2 | Read Aloud engine package split | Code quality | L | Todo | One module per engine behind a base; behavior unchanged; tests pass. |
| CQ-3 | IO structured dispatch table | Code quality | M | Todo | Format routing uses a table or per-format modules; complexity reduced; tests pass. |
| CQ-4 | Settings nested schema and migration | Code quality | L | Todo | Settings grouped into nested dataclasses with versioned migration; round-trip tests pass. |
| CQ-5 | Typed storage helpers | Code quality | M | Todo | read_json and write helpers are typed; core stays strict. |
| CQ-6 | Type the Foundation Models SDK handle | Code quality | S | Todo | A Protocol replaces Any; mypy strict passes. |
| CQ-9 | Log underlying causes in IO fallbacks | Code quality | S | Todo | Friendly messages remain; root causes are logged for diagnostics. |
| CQ-10 | Add missing module and method docstrings | Code quality | M | Todo | Listed public modules and methods are documented. |
| PERF-4 | Replace OCR busy-wait | Performance | S | Todo | OCR uses a proper wait; no fixed-interval polling. |
| PERF-5 | Quick Nav cache invalidation correctness | Performance | M | Todo | Only changed regions invalidate; large-document perf test passes. |
| PERF-6 | Off-thread or batched persistence | Performance | M | Todo | Settings, palette, and recent writes do not stall the UI thread. |
| PERF-7 | Cache markup and structure scans per revision | Performance | M | Todo | Navigation reuses cached scans; measurable improvement on large files. |
| NAV-3 | Uniform scope fallback model | Navigation | S | Todo | Selection, paragraph, document fallback is consistent and announced across actions. |
| NAV-6 | Link navigation announces text, destination, alt state | Navigation | S | Todo | Link browse announces details and alt-text presence. |
| NAV-7 | Table review mode | Navigation | M | Todo | Cell reading announces row and column position. |
| NAV-8 | Misspellings and matches as Quick Nav types | Navigation | S | Todo | Both are navigable element types with announcements. |
| NAV-9 | Quick Nav prewarm race audit | Navigation | S | Todo | No race in cache rebuild; covered by a test. (Pairs with PERF-5.) |
| KEY-2 | Exportable keyboard reference | Keymaps | S | Todo | Reference exports as accessible HTML and EPUB. (Pairs with DOC-6.) |
| KEY-4 | Validate keybinding syntax on save | Keymaps | S | Todo | Invalid bindings are rejected with a plain-language explanation. |
| MENU-4 | Labels match announcement grammar | Menus | S | Todo | Menu labels and announcements are consistent. |
| FEAT-1 | Read Aloud read-from-cursor, read-selection, spell mode | Features | M | Todo | Three modes work and announce; audio caching applies. (Pairs with PERF-3.) |
| FEAT-3 | Thesaurus inline replacement | Features | S | Todo | Synonym replacement announces the substitution. |
| FEAT-4 | Find and Replace ergonomics | Features | S | Todo | Replace-and-find-next, named-group preview, recipe quick picker. |
| FEAT-5 | Snippet tab-stops and picker | Features | M | Todo | Tab-stops announce placeholders; picker previews. |
| FEAT-6 | Compare spoken summary | Features | S | Todo | A spoken change summary and synchronized navigation announcements. |
| FEAT-7 | Named macros with safe replay | Features | M | Todo | Named, described macros replay with per-step announcements; export and import. |
| FEAT-8 | Calm Document Intake summary | Features | S | Todo | Skimmable intake with one-key path to cleanup. |
| FEAT-9 | Watch Folder arrival announcements | Features | S | Todo | Non-interrupting notification with one-key open. Delivered as part of the WATCH family (WATCH-4); retained for traceability. |
| WATCH-8 | GLOW "audit and fix accessibility" watch action | Features | M | Todo | A watch action that registers through the WATCH-2 registry and runs the GLOW audit-and-fix flow (GLOW-1 through GLOW-5) over each arriving document against a chosen standards profile, reversibly, surfacing findings in the queue outcome. Becomes available once GLOW lands; until then the action advertises itself as unavailable with an announced reason. Tests cover registration and the unavailable-until-GLOW path. |
| WATCH-9 | BITS Whisperer "transcribe" watch action | Features | M | Todo | A watch action that registers through the WATCH-2 registry and transcribes arriving audio via BITS Whisperer (BW-1 through BW-4), emitting an editable document that the queue can then chain to other profiles — completing the drop-audio-in, accessible-edited-document-out loop. Becomes available once BITS Whisperer lands; until then it advertises itself as unavailable with an announced reason. Tests cover registration and the unavailable-until-BW path. |
| FEAT-10 | Searchable Sticky Notes vault | Features | M | Todo | Vault is searchable and pageable; capture confirms. |
| FEAT-11 | Status bar label and persistence polish | Features | S | Todo | Every cell announces; layout persists and announces. |
| POD-3 | Podcast transcript: Reading and reviewing | Docs | S | Todo | Transcript passes lint; ships in all formats. |
| POD-4 | Podcast transcript: On-device AI | Docs | S | Todo | As above. |
| POD-5 | Podcast transcript: Make documents accessible | Docs | S | Todo | As above. |
| TUT-3 | Tutorial: select and transform by structure | Docs | S | Todo | Numbered steps with keystrokes and confirmations. |
| TUT-4 | Tutorial: find and replace safely | Docs | S | Todo | As above. |
| TUT-5 | Tutorial: private AI setup | Docs | S | Todo | As above. |
| TUT-6 | Tutorial: convert and clean up documents | Docs | S | Todo | As above. |
| TUT-7 | Tutorial: customize keymaps and profiles | Docs | S | Todo | As above. |
| DOC-3 | Developer quickstart | Docs | S | Todo | Environment, run, test, lint, type-check, build steps documented. |
| DOC-4 | Generated API or module reference | Docs | M | Todo | Reference generated from docstrings and published in all formats. |

### P3: exploratory or stretch

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| FEAT-12 | Named workspace restore polish | Features | M | Todo | Named workspaces reopen and announce what was restored. |
| FEAT-13 | Screen-reader-tuned focus mode | Features | M | Todo | Non-essential chatter is silenced; essential confirmations remain. |
| FEAT-14 | Reading ruler and line focus | Features | M | Todo | Configurable, high-contrast, large line focus for low vision. |
| FEAT-15 | One-key inline definition and lookup | Features | S | Todo | Dictionary and thesaurus lookup on a single key with announcement. |
| FEAT-17 | One-key export presets | Features | M | Todo | Clean HTML, Word, and PDF export with announced results. |
| FEAT-18 | Save and recovery transparency | Features | S | Todo | Visible and spoken last-saved and recovered-from state. |
| NAV-10 | Symbol navigation for source files | Navigation | M | Todo | Functions, classes, and headings index for code; type-ahead jump. |
| AI-2 | Multi-modal image understanding | AI | L | Todo | Optional, opt-in image analysis with consent and announced results. |
| LINUX-1 | Linux platform layer exploration | Platform | XL | Todo | A spike assesses an accessible Linux path; decision recorded. |
| LINUX-2 | Accessible Linux platform layer to product quality | Platform | XL | Todo | Following the LINUX-1 spike, a platform layer (screen-reader bridge, secret store, shell integration) ships at the same accessibility and stability bar as Windows and macOS, gated on the same checks. |
| ECO-1 | Plugin capability, signing, and marketplace model | Ecosystem | XL | Todo | A documented capability and signing model lets vetted third-party plugins load safely off the experimental flag (builds on SEC-8), with a review process; no unsigned plugin runs by default. |
| L10N-1 | Full localization of UI and documentation | Localization | XL | Todo | The UI and the core documentation set are fully translated and accessibility-reviewed for the committed launch languages, with a process to keep translations current. |
| COLLAB-1 | Asynchronous review and sharing (scoped) | Features | L | Todo | A local-first, accessible async review and comment exchange (export, annotate, merge) is delivered; real-time multi-user editing remains explicitly out of scope with the reason recorded. |
| COMP-1 | Project-wide Find in Folder and Workspace Search | Features | L | Todo | QUILL ships an accessible folder and workspace search surface with saved scopes, include and exclude globs, file type filters, and replace-in-results preview. Results are exposed as a stable, keyboard-first list with document, line, and snippet context; Enter jumps, Ctrl+Enter opens side-by-side review, and all actions announce count, scope, and wrap behavior with the shared grammar. Search and replace operations stream off the UI thread, support cancellation, and preserve one-step undo for in-file replacements. |
| COMP-2 | Workspace model parity (sessions plus folders plus project panels) | Features | L | Todo | QUILL adds a unified workspace model on top of existing sessions: named workspaces can include ad-hoc files, folder trees, and pinned project groups, with persistent open-state and cursor restoration announcements. A single Workspace hub supports create, clone, rename, archive, and reopen-most-recent, and clearly distinguishes session snapshots from durable project workspaces. Folder and project trees are fully screen-reader operable with predictable node announcements, context commands, and no focus traps. |
| COMP-3 | Plugin admin lifecycle and trust UX | Ecosystem | XL | Todo | Building on ECO-1 and SEC-8, QUILL ships an accessible plugin manager with Installed, Available, Updates, and Incompatible states, each with clear risk and capability labels. Install and update flows require explicit consent for manifest-declared permissions (network, filesystem, subprocess), and signature or provenance status is announced before activation. Disable, rollback, and safe-mode recovery are first-class, with deterministic behavior when a plugin becomes incompatible or fails to load. |
| COMP-4 | Encoding conversion suite and legacy text recovery | Features | M | Todo | QUILL extends encoding support from choose and reload to explicit convert workflows with loss-risk preview, fallback options, and recoverability. Users can convert active documents between common encodings, compare before and after byte interpretation in a review pane, and cancel safely before write. Status bar and announcements always report active encoding and conversion outcome, and batch conversion (workspace or folder) is available behind explicit confirmation. |
| COMP-5 | Macro studio maturity (safe replay, import/export, repeat modes) | Features | M | Todo | QUILL upgrades macro workflows with named and described macros, replay controls (once, N times, until condition), and optional per-step speech confirmations. Macro import and export include conflict resolution (keep mine, replace, duplicate as new), compatibility notes, and dry-run verification before activation. Replay is deterministic, cancellable, and bounded to prevent runaway loops, with clear post-run summaries of actions applied. |
| COMP-6 | Two-pane split editing and compare-grade navigation | Features | M | Todo | QUILL adds an optional split editing mode that keeps stock controls and predictable focus semantics, with explicit announcements for pane entry, active pane, and synchronized navigation state. Users can open two files or two positions of one file, lock or unlock scroll, and drive pane focus and movement entirely by keyboard. The feature reuses compare navigation primitives so jumps, hunk traversal, and region review remain coherent and screen-reader friendly. |

---

## 15. Suggested release sequencing

1. Harden and gate (P0 security, accessibility, and continuous integration items). These protect users and unblock everything else. This is the 1.0 quality bar.
2. Land the QUILL key flagship (QK-1 through QK-5, NAV-1, NAV-4) plus the primer and first tutorials. This is the story that makes QUILL memorable.
3. Decompose main_frame safely (CQ-16 then CQ-1) to make all future work faster and lower risk.
4. Performance polish (PERF-1 through PERF-3 and PERF-9) so first use feels instant.
5. Documentation and launch content (remaining podcasts and tutorials, keyboard reference, developer quickstart) so launch lands with a complete learning surface.
6. Post-1.0 delight and expansion (P2 and P3) guided by beta feedback.

Definition of greatness for this plan: when a first-time blind writer can open QUILL, discover the QUILL key, navigate a messy document by structure, fix it, read it back, and save it, all by keyboard, with every step confirmed clearly, and a returning power user can do the same in silence at speed, then QUILL is golden.

---

## Part II: Verified line-by-line audit (2026-06-01)

This part records a structured, tool-assisted audit that read across the entire source tree (148 Python files, 37,559 lines), all documentation, the test suite (118 test files), and the build and release scripts. Findings below are concrete and carry file-and-line citations so they can be acted on directly. Each new actionable item is added to the backlog in section 16.10 with a stable ID, and the P0 correctness bugs are also called out at the top because several are latent crashes.

Tooling run for this audit:

- ruff on the `quill` package: 113 findings (83 line-too-long, 10 undefined-name, 7 unsorted-imports, 5 unused-import, 3 quoted-annotation, 2 zip-without-strict, 2 unused-variable, 1 redefinition). On `tests` and `scripts`: 36 findings.
- mypy scoped to `quill/core` and `quill/io` (the strict zone): 44 errors across 14 files. Important correction to earlier notes: the strict zone is not currently clean; only the two AI files touched in a previous session were verified green. The scoped command remains `mypy quill\core quill\io` to avoid the whole-tree scan that previously exhausted memory.

### 16.1 Confirmed correctness bugs (latent crashes), highest priority

These are real defects found by reading the code, several confirmed by ruff undefined-name analysis. They should be fixed before 1.0.

1. Corrupted method `_show_bw_onboarding` in [quill/ui/main_frame.py](../../quill/ui/main_frame.py#L19426) (lines 19426 to 19470). The method body contains copy-pasted "Insert Link" dialog code and references undefined names `selected_text` (line 19442), `dialog` (line 19463), and `profiles` (line 19470), plus assigns `display_text` and `url` that are never used. If this onboarding path is reached it raises `NameError`. The intended behavior is to confirm the BITS Whisperer rollout and then present a profile choice. This is a P0 crash. See BUG-1.
2. Four bare `wx.` calls that should be `self._wx.` in [quill/ui/main_frame.py](../../quill/ui/main_frame.py#L16983) at lines 16983, 17015, 17022, and 17042 (`wx.GetSingleChoice` and `wx.GetTextFromUser` in the heading-style prompts). Module-level `wx` is not imported; it is only stored as `self._wx` (assigned around line 683). These four call sites raise `NameError` at runtime when the heading-style flow executes. This is a P0 crash on a real user path. See BUG-2.
3. Undefined type annotation `VoiceOption` in [quill/ui/main_frame.py](../../quill/ui/main_frame.py#L12503) at lines 12503 and 12532. The symbol is imported as `ReadAloudVoiceOption` (around line 240) but the annotations use the bare name. With `from __future__ import annotations` this does not crash at call time, but it breaks `typing.get_type_hints` and static analysis. Fix by using the imported alias. See BUG-3.
4. Redefinition of `URLError` in [quill/ui/main_frame.py](../../quill/ui/main_frame.py#L339): imported first from `urllib.error` (line 15) and again from `quill.core.updates` (line 339). The second import shadows the first. Pick one source. See BUG-4.
5. Unchecked llama.cpp response shape in [quill/core/ai/llama_cpp_backend.py](../../quill/core/ai/llama_cpp_backend.py#L113) (lines 113 to 117): `out["choices"][0]["message"]["content"]` will raise `KeyError` or `IndexError` on a malformed or version-mismatched response. Add validation and a friendly error. See BUG-5.
6. XML element handling bug in [quill/io/structured.py](../../quill/io/structured.py#L614) (lines 614 and 615): a `list[str]` is assigned where an `Element` is expected and then passed to `str.join`, which mypy flags as an assignment and arg-type error. This is a real type-level defect in the DOCX path. See BUG-6.
7. Potential infinite loop in [quill/core/ai/assistant.py](../../quill/core/ai/assistant.py#L196) chunk splitting if `max_chars <= 0` is ever passed; add a guard. See BUG-7.

### 16.2 Security findings (verified)

Highest priority first. Most user files live under the trusted per-user app data directory, so the focus is tampered configuration, untrusted document inputs, and supply chain.

1. XML entity expansion (billion laughs) in document parsing. [quill/io/structured.py](../../quill/io/structured.py#L416) uses `ET.fromstring` for XML (line 416), DOCX `word/document.xml` (around line 408), and PPTX slide XML; [quill/io/pages.py](../../quill/io/pages.py#L107) parses PPTX XML similarly. None disable entity expansion, so a crafted file can cause memory and CPU exhaustion. Fix by switching to `defusedxml` or a hardened parser for all untrusted XML. P0 hardening. See SEC-10.
2. Decompression bombs in ZIP-based formats (DOCX, XLSX, ODT, PPTX) in [quill/io/structured.py](../../quill/io/structured.py#L604) (around lines 604, 683, 717). The archives are read without checking total uncompressed size. Add a cumulative size limit before reading entries. See SEC-11.
3. Subprocess executable paths sourced from settings. [quill/core/external_tools.py](../../quill/core/external_tools.py#L132) (around line 132) expands and runs configured executable paths (for example the DECtalk executable and other engines) without validating they live in a trusted location. If `settings.json` is tampered, this is arbitrary code execution. Validate against an allowlist or bundled or `shutil.which`-resolved path. This pairs with the earlier SEC-1. See SEC-1.
4. PATH hijacking via tool discovery in [quill/core/external_tools.py](../../quill/core/external_tools.py#L102) (around lines 102 to 115): `shutil.which` trusts the process PATH. Document the risk and prefer bundled tool paths where available. See SEC-12.
5. Update download without binary checksum or signature verification in [quill/core/updates.py](../../quill/core/updates.py#L249) (around line 249). The manifest signature is verified, but the downloaded asset itself is not checksum-verified before use. Verify a hash from the signed manifest against the downloaded bytes. This pairs with SEC-6. See SEC-6.
6. Incomplete secret redaction in diagnostics. [quill/core/diagnostics.py](../../quill/core/diagnostics.py#L20) (around lines 20 to 29) redacts `Authorization: Bearer` style tokens but misses patterns like `token:`, `password:`, and `NAME_KEY=` environment assignments. Broaden the redaction patterns so diagnostic bundles never leak partial secrets. See SEC-13.
7. Python sandbox environment and resource limits. [quill/core/python_sandbox.py](../../quill/core/python_sandbox.py#L143) inherits `PATH` into the subprocess (around line 143) and passes the user code as a base64 environment variable (around line 145), which can appear in a process list on shared systems; there is also no wall-clock or memory cap beyond the timeout. Add memory and CPU limits and avoid leaking the payload via the environment where possible. This refines SEC-9. See SEC-9, SEC-14.
8. `run_subprocess_safely` does not validate `cwd` or the executable in [quill/stability/safe_subprocess.py](../../quill/stability/safe_subprocess.py#L11) (around lines 11 to 26), and only catches `TimeoutExpired`, not `OSError` or `FileNotFoundError`. Add validation and wrap the missing exception. This refines SEC-4. See SEC-4, SEC-15.
9. Credential and Keychain input validation. [quill/platform/windows/credential_manager.py](../../quill/platform/windows/credential_manager.py#L73) does not validate `target_name` (around lines 73 to 99), and [quill/platform/macos/keychain.py](../../quill/platform/macos/keychain.py#L30) does not check the `security` subprocess return code in `set_secret` (around lines 30 to 50). Validate names against a safe pattern and check return codes. See SEC-16.
10. Shell integration registry command in [quill/platform/windows/shell_integration.py](../../quill/platform/windows/shell_integration.py#L35) is safe today because it derives from `launcher_command()`, but it is not escaped; document that it must never accept user input, or escape it if that changes. See SEC-17.

### 16.3 Correctness and robustness (non-crashing) findings

1. Windows atomic write is not guaranteed. [quill/core/storage.py](../../quill/core/storage.py#L16) uses temp file plus `replace` (around line 16). On Windows this can be a two-step operation under contention. Confirm `os.replace` semantics and, where needed, add retry-on-`PermissionError` so a concurrent reader cannot cause data loss. See CQ-19.
2. Version comparison ignores pre-release suffixes in [quill/core/updates.py](../../quill/core/updates.py#L136) (around line 136): `1.2.0-rc1` parses as `1.2.0`, so a release candidate sorts equal to the stable. Decide and document the intended ordering. See CQ-20.
3. Snippet placeholder regex does not handle nested braces in [quill/core/snippets.py](../../quill/core/snippets.py#L90) (around lines 90 to 120). Document the limitation or support nesting. See FEAT-5.
4. TOML parse has no guard in [quill/core/compliance.py](../../quill/core/compliance.py#L142) (around lines 142 to 160): a corrupted `pyproject.toml` aborts the dependency audit. Wrap and report. See CQ-21.
5. Credential empty-blob path in [quill/platform/windows/credential_manager.py](../../quill/platform/windows/credential_manager.py#L68) returns an empty secret indistinguishable from absent; log and document. See CQ-22.

### 16.4 Typing gaps in the strict zone (the 44 mypy errors)

The strict zone (`quill/core` and `quill/io`) currently reports 44 errors in 14 files. Representative clusters, all to be driven to zero and then kept green in continuous integration (see CQ-7):

- [quill/core/ipc.py](../../quill/core/ipc.py#L75): six errors from a `handle: object` annotation that is then used as a file object, plus `fcntl` attributes that are POSIX-only. The cross-platform branch on `os.name` is logically sound; annotate the handle as `IO[bytes]` or `Any` and guard the `fcntl` import for type-checkers. See TYPE-1.
- [quill/core/bw_speech.py](../../quill/core/bw_speech.py#L169): an `Any` returned where `float` is declared (line 169), missing parameter annotations (lines 223, 255), and the optional `faster_whisper` import. See TYPE-2.
- [quill/core/read_aloud.py](../../quill/core/read_aloud.py#L298): the `kokoro.KPipeline` attribute is not visible to mypy (line 298); fix the ignore code. See TYPE-3.
- [quill/core/dictation.py](../../quill/core/dictation.py#L10): `None` assigned to a `Callable`-typed name (line 10), and `recognize_whisper` and `recognize_vosk` on an untyped recognizer (lines 71, 78). See TYPE-4.
- [quill/io/pages.py](../../quill/io/pages.py#L73): missing return and parameter annotations (lines 73, 78, 91), untyped third-party `keynote_parser`, and an `Any` returned as `str` (line 238). See TYPE-5.
- [quill/io/structured.py](../../quill/io/structured.py#L173): untyped `openpyxl` import (line 173), a missing annotation (line 249), and the Element bug from 16.1 item 6 (lines 614, 615). See TYPE-6, BUG-6.
- [quill/core/ai/llama_cpp_backend.py](../../quill/core/ai/llama_cpp_backend.py#L65): missing annotations (lines 65, 71), a `None`-typed attribute later assigned a `Llama` (line 82), and an `Any` returned as `str` (line 118). See TYPE-7.
- [quill/core/ai/assistant.py](../../quill/core/ai/assistant.py#L130): missing annotations (lines 130, 200). See TYPE-8.

Where third-party stubs are missing (`openpyxl`, `faster_whisper`, `keynote_parser`, `kokoro`, `llama_cpp`), either install the available stub packages (for example `types-openpyxl`) or add precise per-import ignores with the correct error codes, and add Protocols for the SDK handles so the strict zone stays honest.

### 16.5 Performance findings (verified)

1. Spell-check wordlist loads synchronously (about 370,000 words) in [quill/core/spellcheck.py](../../quill/core/spellcheck.py#L100) (around lines 100 to 115), under the backend lock, stalling the first check. Background preload at startup. Pairs with PERF-1. See PERF-1.
2. Thesaurus index loads synchronously (a large data file) in [quill/core/thesaurus.py](../../quill/core/thesaurus.py#L52) (around lines 52 to 60) on first lookup. Background preload. Pairs with PERF-2. See PERF-2.
3. Read Aloud accumulates uncompressed audio arrays in memory in [quill/core/read_aloud.py](../../quill/core/read_aloud.py#L295) (around lines 295 to 325); stream to file for long documents, and cache identical sentences. Pairs with PERF-3. See PERF-3, PERF-10.
4. Spreadsheet reading loads entire worksheets into memory in [quill/io/structured.py](../../quill/io/structured.py#L193) (around lines 193 to 199); cap rows or stream. See PERF-11.
5. DOCX and PPTX load whole XML payloads and build full in-memory documents in [quill/io/structured.py](../../quill/io/structured.py#L604) (around lines 604 and 637); consider streaming and run these off the UI thread. See PERF-12.
6. PDF extraction materializes all pages in [quill/io/pdf.py](../../quill/io/pdf.py#L58) (around line 58); page-stream for very large PDFs. See PERF-13.
7. File search scans whole documents with no chunking in [quill/core/file_search.py](../../quill/core/file_search.py#L48) (around lines 48 to 70); stream large corpora. See PERF-14.

Concurrency note (correction): the spell-check wordlist cache, the enchant dictionary, the thesaurus index, and the watch-folder seen-set all already use `threading.Lock`. There is no missing lock there. The remaining work is documenting these invariants (CQ-17) and the Windows atomic-write behavior (CQ-19).

### 16.6 main_frame.py decomposition map (verified seams)

The 18,748-line [quill/ui/main_frame.py](../../quill/ui/main_frame.py) divides cleanly into roughly 22 subsystems. This map is the basis for CQ-1 (extract behind characterization tests, CQ-16):

- Initialization and setup: lines 678 to 860.
- Command registry and keybinding: lines 971 to 4975.
- Menu building and identifier management: lines 2358 to 4640 (the single largest block).
- Event binding and frame lifecycle: lines 4927 to 6663.
- QUILL key mode: lines 5162 to 5287.
- Browse and navigation (Quick Nav, ARIA regions): lines 5358 to 5817.
- Tab and document management: lines 5016 to 5120 and 5781 to 5860.
- Text editor operations: lines 5849 to 6201.
- Context menus: lines 6206 to 6650.
- Status bar: lines 7252 to 7675.
- Dialogs and modal presentation: lines 7675 to 7702.
- File input/output and sessions: lines 7067 to 7141 and 8075 to 8824.
- Speech and Read Aloud: lines 12400 to 13460.
- Update checking: lines 14963 to 15100.
- Find and replace: lines 15655 to 16000.
- Link insertion: lines 16080 to 16210.
- Heading styles: lines 16950 to 17060 (contains BUG-2).
- List manager: lines 17259 to 17700.
- Intellisense and autocomplete: lines 18079 to 18240.
- Onboarding and first run: lines 14369 to 19700 (contains BUG-1).

### 16.7 IO contract and coverage findings

- Readers that follow `read(path) -> Document` and raise on error are compliant (text and structured confirmed). Several formats are read-only by design (PDF, Pages) and lack `write`; only Pages implements `outline`. If the product promises `outline` for structured formats, add it for DOCX, PPTX, and XLSX. See IO-1.
- Format test coverage is thin: only text, PDF, OCR, pandoc, and structured have any tests, and pandoc and structured are minimal. There are no fixtures exercising real conversions. The "100-plus formats" claim rests almost entirely on pandoc and is essentially untested end to end. See CQ-13 and the test plan in 16.9.

### 16.8 Documentation findings (verified)

- Missing entirely: API or module reference, developer quickstart, plugin developer guide, a static (offline) keyboard reference, a configuration schema reference, a troubleshooting guide, and any podcast transcripts or tutorial or video scripts. See DOC-1 through DOC-6, DOC-7, DOC-8, and the POD and TUT items.
- The accessibility conformance report at [docs/accessibility/acr-vpat.md](../accessibility/acr-vpat.md) is a template with placeholder evidence. It must be either filled in with a real 0.1.5 assessment or clearly labeled as not yet assessed. See DOC-9.
- The PRD at [docs/QUILL-PRD.md](../QUILL-PRD.md) mixes 1.0 specification with 0.1.5 reality; its header should state plainly that it specifies 1.0 and that 0.1.5 implements the subset marked in the roadmap mapping. See DOC-10.
- Documentation accessibility: the PRD uses emoji (check marks, warning and cross symbols, and others) and em-dashes throughout. Per the project's own markdown accessibility rules, replace emoji with text labels such as the words pass, warning, and error, and replace em-dashes. This applies to the source markdown so the generated HTML and EPUB inherit the fix. See DOC-11.
- The engineering docs (architecture, module-contracts, data-layout, runtime-model, diagnostics-runbook, quality-gates) are useful but skeletal (most under 50 lines). Expand them alongside the API reference. See DOC-12.
- User guide gaps: concrete AI setup examples (for example connecting to a local Ollama endpoint and an error matrix for 401 versus 403 versus 500), spell-check dictionary workflow, watch-folder walkthrough, and a troubleshooting section (Quick Nav key conflicts, garbled PDF extraction, autosave disk pressure). See DOC-13.

### 16.9 Test strategy findings (verified)

- Inventory: 118 test files. Core has the most coverage; the UI monolith, the IO format matrix, integration, performance, and accessibility content depth are the weak spots.
- The 18,748-line UI has only a handful of behavior tests. Before decomposition (CQ-1), add a characterization suite (CQ-16) covering tab lifecycle, undo and redo isolation, autosave and recovery, session restore, Quick Nav, find and replace, spell-check as you type, sticky notes, and macros.
- Add policy and attack-surface tests for the Python sandbox (allowed versus blocked modules, escape attempts, resource limits), spell-check tier fallback, Read Aloud backend fallback, and IO format smoke tests with real fixtures. See CQ-11, CQ-13, CQ-23, CQ-24.
- Performance tests are smoke-level only; add the budget suite (PERF-9).
- Scripts: the release orchestrator [scripts/release_readiness.py](../../scripts/release_readiness.py) runs ruff, pip-audit strict, pytest, docs build, and corpus verification, but there is no dependency lockfile and no timeouts on long commands; the Windows build pins an embeddable Python by a hardcoded hash that requires a code change to rotate. See CQ-25, CQ-26.

### 16.10 New backlog items from the verified audit

These extend the section 14 tracker. Priorities follow the same scheme. The confirmed latent crashes are P0.

#### P0 correctness bugs (new)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |

#### P0 and P1 security (new and refined)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| SEC-12 | Document and reduce PATH-hijack exposure for tool discovery | Security | S | Todo | Bundled tool paths are preferred; the residual risk is documented. |

#### P1 and P2 quality, typing, performance, IO, docs, tests (new)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| CQ-23 | Python sandbox policy and attack-surface tests | Code quality | M | Todo | Tests cover allowed versus blocked modules, escape attempts, and resource limits. |
| CQ-24 | Read Aloud backend fallback tests | Code quality | M | Todo | Each backend and the fallback order is tested with stubs. |
| CQ-25 | Add dependency lockfile and CI timeouts | Build | M | Todo | Dependencies are pinned for release runs; long commands have timeouts. |
| CQ-26 | Make the embeddable Python hash configurable | Build | S | Todo | The Windows build reads the expected hash from config, not a code constant. |
| IO-1 | Add outline support for structured formats | IO | M | Todo | DOCX, PPTX, and XLSX provide an outline, or the contract is amended and documented. |
| DOC-7 | Configuration schema reference | Docs | M | Todo | Settings, keymap, and data schemas are documented for pre-configuration. |
| DOC-8 | Troubleshooting guide | Docs | S | Todo | Common issues (key conflicts, PDF extraction, AI connection, autosave) are documented with fixes. |
| DOC-9 | Replace or label the ACR template | Docs | M | Todo | The conformance report reflects a real 0.1.5 assessment or is clearly marked not yet assessed. |
| DOC-10 | Clarify 1.0 versus 0.1.5 in the PRD header | Docs | S | Todo | The PRD states its 1.0 scope and the 0.1.5 implemented subset. |
| DOC-11 | Make the PRD and docs accessible | Docs | M | Todo | Emoji are replaced with text labels and em-dashes removed across docs source; artifacts regenerated and the docs gate passes. |
| DOC-12 | Expand engineering docs | Docs | M | Todo | Architecture, contracts, data layout, runtime model, diagnostics, and quality gates are filled out beyond stubs. |
| DOC-13 | Fill user-guide gaps | Docs | M | Todo | AI setup examples, spell-check dictionary workflow, watch-folder walkthrough, and troubleshooting are added. |

### 16.11 Summary of verified counts

- Confirmed latent-crash bugs: 7 (BUG-1 through BUG-7), of which two (BUG-1, BUG-2) are on real user paths in the UI.
- Security findings: 10 verified items spanning untrusted-input parsing, supply chain, secret handling, and subprocess and credential validation.
- Strict-zone typing errors: 44 across 14 files (TYPE-1 through TYPE-8 cover the clusters).
- Lint findings: 113 in the package and 36 in tests and scripts (CQ-18).
- Performance hotspots: 7 verified (PERF-1, PERF-2, PERF-3, PERF-10 through PERF-14).
- Documentation gaps: 7 missing artifacts plus accessibility and version-clarity fixes (DOC-1 through DOC-13).
- Test gaps: the UI monolith, the IO format matrix, sandbox policy, and a performance budget are the highest-value additions.

Revised sequencing note: the new P0 correctness bugs (BUG-1 and BUG-2 especially) and the untrusted-input hardening (SEC-10, SEC-11) should be folded into step 1 of the section 15 sequencing, because they are small, concrete, and protect users immediately.

---

## Part III: Quality gates and the AI and agent program

This part does two bold things. First, it defines a ladder of automated quality gates so that every change (whether written by a person or by an AI coding assistant such as Copilot) is held to a high, consistent, machine-checked bar before it can merge. Second, it reimagines QUILL's own AI and agent features so they become a signature strength: local-first, fully accessible, consented, reversible, and genuinely useful to a blind or low-vision writer.

The two are connected. Strong gates are what let a team move fast with AI assistance without drifting in quality. They turn "the AI wrote it" from a risk into an advantage, because nothing reaches users that has not passed the same objective checks.

### 17. Quality gates for an AI-assisted workflow

The repository already has the raw materials: ruff, mypy, pytest, a docs-artifact gate, pip-audit in the release script, accessibility and performance test folders, and a release readiness orchestrator. The work is to assemble these into an explicit, enforced gate ladder, close the holes the audit found, and make the gates fast enough to run on every change.

#### 17.1 The gate ladder

Three tiers, each stricter than the last:

- Pre-commit (local, seconds). Format and lint the changed files, run quick syntax and undefined-name checks, and block commits that fail. This catches the class of bug the audit found (bare `wx.` calls, undefined names, unsorted imports) before they ever leave a developer's machine. See GATE-1.
- Pull request (continuous integration, minutes). The full objective bar that must be green to merge: lint, scoped strict typing, the test suite with a coverage floor, the accessibility checks, the docs-artifact gate, and the security scans. See GATE-2 through GATE-9.
- Release (pre-tag, thorough). The existing release readiness orchestrator, hardened: pinned dependencies, command timeouts, corpus verification, performance budgets, and provenance and software bill of materials generation. See GATE-10, CQ-25, CQ-26.

#### 17.2 The specific gates to enforce

- Lint gate. Ruff must be clean (or explicitly justified) on the package, tests, and scripts. Closes the 113 plus 36 findings and keeps them closed. See GATE-2, CQ-18.
- Typing gate. Strict mypy on `quill/core` and `quill/io`, always scoped to those paths (never the whole tree, which previously froze a machine), must report zero errors. Drives the 44 strict-zone errors to zero and holds the line. See GATE-3, CQ-7.
- Banned-pattern gate. A small, fast check that fails the build on known footguns: a bare `wx.` reference in `main_frame` (must be `self._wx`), undefined names, duplicate imports, `print` left in library code, `ET.fromstring` on untrusted XML (must use the hardened parser), and `except Exception` without a logged cause. This is the gate that would have caught BUG-1, BUG-2, BUG-4, and SEC-10 automatically. See GATE-4.
- Test and coverage gate. The full pytest suite (unit, integration, accessibility, performance smoke) must pass, with a coverage floor that ratchets upward over time and a hard floor for `quill/core` and `quill/io`. New code may not lower coverage. See GATE-5, CQ-13.
- Characterization gate for the UI monolith. Before and during the `main_frame` decomposition, a characterization suite must pass so refactors are provably behavior-preserving. See GATE-6, CQ-16, CQ-1.
- Accessibility gate. Keyboard-trap and contrast checks, plus the announcement-grammar and focus-order assertions, run on every pull request, not on demand. No UI change merges if it regresses screen-reader operability. See GATE-7, A11Y items.
- Security gate. pip-audit (strict) for dependency vulnerabilities, a static security scan (for example bandit or semgrep) for subprocess, XML, and path-traversal patterns, a check that all untrusted XML uses the hardened parser, and a "no plaintext secret" scan of diagnostics output. See GATE-8, SEC-10 through SEC-17.
- No-silent-network gate. An automated test asserts that no AI or network code path makes an outbound call without explicit consent, and that provider, model, and scope are always surfaced. This makes the product's core trust promise machine-enforced, not just a convention. See GATE-9, AI-5.
- Docs-artifact and accessibility gate. Every changed Markdown file regenerates its HTML and EPUB, and the docs accessibility rules (no emoji, no em-dashes, accessible tables, meaningful links) are linted. See GATE-2 (docs job), DOC-11, DOC-5.
- Performance budget gate. Startup time, first spell-check, first thesaurus lookup, large-document Quick Nav, and Read Aloud start must stay within published budgets; a regression fails the build. See GATE-10, PERF-9.
- Module-size budget gate. A soft, ratcheting budget on the largest files (starting with `main_frame`) that prevents new growth and rewards extraction, so the monolith shrinks monotonically. See GATE-11, CQ-1.

#### 17.3 Make AI coding assistants productive and safe in this repo

The goal is that an AI assistant (Copilot or an agent) can contribute high-quality, accessible, secure code with minimal back-and-forth, because the repository tells it exactly how, and the gates catch anything that slips.

- Strengthen the repository guidance. Expand the existing `.github/copilot-instructions.md` and add an `AGENTS.md` so any assistant has a crisp, current description of the architecture, the strict-typing zone, the scoped mypy command, the accessibility non-negotiables, the no-silent-network rule, the PowerShell and commit conventions, and the definition of done. See GATE-12.
- Ship a machine-readable definition of done. A short checklist (accessible, typed in the strict zone, tested, lint-clean, no silent network, docs regenerated) that both humans and agents follow, mirrored by the gates so the checklist is actually enforced. See GATE-13.
- Encode the footguns the audit found. Document the bare `wx.` versus `self._wx` rule, the hardened-XML rule, the scoped-mypy rule, and the path-safety helper directly in the guidance, with examples, so assistants do not reintroduce them. See GATE-12.
- Add CODEOWNERS and required reviews for the highest-risk areas (security, the sandbox, the AI provider boundary, the platform secret stores) so sensitive changes always get human eyes even when AI-authored. See GATE-14.
- Provide test-first scaffolding. Templates and fixtures (IO sample files, an accessibility test harness, a sandbox policy harness) so an assistant can write the test alongside the change and the coverage gate is easy to satisfy. See GATE-5, CQ-23, CQ-13.
- Keep the guidance honest over time. A periodic check that the instructions match reality (version, commands, structure), so assistants are never working from stale facts. See GATE-12.

### 18. Make QUILL's own AI and agents amazing

QUILL already has a thoughtful AI layer: a provider and model boundary, an enable toggle with an honest status badge, an Assistant Hub, Ask QUILL chat, model and connection management, a Writing Assistant, a Prompt Studio, an Agent Center scaffold, selection actions, style training, and a Speech submenu, all gated behind explicit consent with no silent network calls. The bold move is to turn this solid foundation into the most accessible AI writing experience anywhere: local-first, fully spoken, always reversible, and genuinely agentic for the tasks that matter most to this audience.

Guiding principles for all AI and agent work, non-negotiable:

- Local-first and private by default. On-device models (llama.cpp and Apple Foundation Models) are first-class; any cloud use is explicit, per-action, and clearly labeled. See AI-5.
- Consent, visibility, and reversibility. Every AI action shows provider, model, and scope, streams visible progress, and produces a result the user can review and undo. No AI edit is ever silent or irreversible. See AI-5, AI-7.
- Accessible to the core. Every AI surface is fully keyboard and screen-reader operable, with results that read well top to bottom and diffs that can be reviewed line by line by ear. See A11Y items.

#### 18.1 Make the assistant feel magical

- Streaming, announced responses. Replies stream incrementally with accessible, throttled announcements so the user hears progress without being flooded. See AI-1.
- Preview-and-apply diffs that are reviewable by ear. Any AI edit is presented as a structured, navigable diff (added, removed, changed), readable line by line with the screen reader, with apply, apply-partially, and reject, and a single undo. This is the feature that makes AI editing trustworthy for a blind writer. See AI-7.
- Context-aware actions. The actions offered adapt to the cursor or selection context (inside a list, a table, a heading, a code block) and to the document type, so the right help is always one key away, including from the QUILL key. See AI-8, HELP-1.
- A real prompt library. Save, name, organize, and share prompts and recipes, with a quick picker and live preview, building on Prompt Studio. See AI-9.
- Style that is truly yours. Strengthen style training so the assistant can match a user's voice, explain why it made a change, and stay consistent across a document. See AI-10.

#### 18.2 A genuine, accessible agent program

Move the Agent Center from scaffold to a small set of reliable, consented, reversible agents that each complete a real multi-step task and narrate every step. An agent never acts without consent, announces each step as it works, and produces a reviewable, undoable result.

- The Accessibility agent (the headline). Tell QUILL "make this document accessible" and it runs a consented, announced, reversible plan: audit structure, fix heading levels, add or improve alt text (with the user confirming each suggestion), tighten link text, apply plain-language improvements, then re-run the audit and report what changed. Every step is a reviewable diff and a single undo. This is the agent that embodies the product's mission. See AGENT-1.
- The Cleanup agent. Turn a messy imported document (bad OCR, broken structure, inconsistent formatting) into clean, well-structured text through a sequence of cleanup recipes, each announced and reversible. See AGENT-2, FEAT-8.
- The Review agent. Produce a spoken, skimmable review of a document (structure, readability, accessibility, consistency) with one-key jumps to each issue, building on the document health dashboard. See AGENT-3, FEAT-16.
- A safe, local agent loop. The agent runtime plans, takes one consented step at a time, can call only a small allowlist of in-app tools (navigate, edit-with-diff, run a sandboxed transform, run an audit), never the network without explicit consent, with a hard step cap and a guard against loops, and full step-by-step announcement. This reuses the existing sandbox and stability layers. See AGENT-4, SEC-9.
- Grounded answers over the user's own content. Optional, local retrieval over open documents and the sticky-notes vault so "ask QUILL" can answer from what the user is actually working on, always citing where an answer came from, never sending content anywhere without consent. See AI-11.

#### 18.3 Trust, safety, and evaluation for AI

- Machine-enforced no-silent-network, as a gate, not just a convention. See GATE-9, AI-5.
- An evaluation harness for AI quality. A small, repeatable set of tasks (accessibility fixes, cleanup, summarization) with expected-quality checks, so AI and agent changes can be measured and regressions caught before release. See AI-12.
- Redaction and offline integrity. Diagnostics never capture document content or secrets (SEC-13), and every AI feature degrades gracefully and announces clearly when a model is unavailable or a key is missing. See CQ-8, AI-6.

#### 18.4 Review of the cloud and local providers (OpenAI, OpenRouter, Gemini, Azure, Ollama, Claude)

A focused review of the provider boundary in `quill/core/assistant_ai.py`, the backends in `quill/core/ai/`, and how the UI wires them found one structural defect and several smaller correctness and enhancement gaps. The provider configuration surface is genuinely strong; the gap is that it is not yet connected to generation.

- The headline defect: configured providers never generate. `assistant_ai.py` fully implements provider selection, secure key storage (Credential Manager with a DPAPI fallback), HTTPS-only policy for cloud endpoints, model discovery, and connection verification for all six providers. But the `Assistant` is always constructed with no backend (`Assistant()` in `main_frame.py`), so generation always runs through `make_default_backend()`, which is Apple Foundation Models on macOS or local llama.cpp elsewhere. Selecting OpenAI, OpenRouter, Gemini, Azure OpenAI, Ollama, or Claude lets a user save a key, list models, and pass verification, yet every actual rewrite, summarize, chat, or agent step still runs on the local model. This is the single most important fix in the AI area: wire a provider-aware chat backend so the selected provider is the one that responds. See AI-13.
- Provider-specific correctness, needed once chat is wired:
  - OpenAI, OpenRouter, custom: standard `POST /v1/chat/completions`; OpenRouter benefits from optional `HTTP-Referer` and `X-Title` attribution headers.
  - Claude: messages API at `POST /v1/messages` with `x-api-key`, `anthropic-version`, and a required `max_tokens`; the model-listing headers are already correct.
  - Gemini: `POST /v1beta/models/{model}:generateContent` with `x-goog-api-key`; the request and response shape differ from the OpenAI schema and need their own adapter.
  - Azure OpenAI: chat targets a deployment, not a model name, at `/openai/deployments/{deployment}/chat/completions?api-version=...`; the connection UI should make the deployment-versus-model distinction explicit. See AI-15.
  - Ollama (local): generation should use `POST /api/chat`; model listing already uses `/api/tags` correctly.
- Streaming. No provider streams today; responses are blocking. Streaming with throttled, accessible announcements (AI-1) should be implemented once per provider in the shared backend so progress is heard, not awaited in silence. See AI-14.
- Tests and trust. There are no contract tests that exercise each provider's request and response shape. Add recorded or mocked per-provider contract tests (no live network in CI) so a provider change cannot silently break generation, and extend the existing, well-designed error taxonomy (auth, forbidden, rate-limited, warming-up, timeout) from the listing path to the chat path so users get the same cause-specific, screen-reader-friendly messages. See AI-16, AI-17.
- What is already good and should be preserved: the HTTPS-only policy with a careful local-loopback and private-network exception (a sound anti-SSRF posture), the Credential Manager plus DPAPI key handling with an honest "could not unlock on this device" status, the retry-with-backoff on transient categories, and the duplicate-tolerant model-name extraction across `models`, `data`, and `items` payload shapes.

#### 18.5 On the GitHub Copilot SDK: a measured recommendation

The user is right to be cautious. The recommendation is to not ship or integrate the GitHub Copilot SDK as a flagship or default path for 1.0, and instead to treat it as an optional, clearly labeled provider behind the same AIBackend boundary, considered after 1.0. The reasoning:

- It would add real value: strong models, and for developer-leaning users a familiar, already-paid-for entitlement. That value is genuine and worth capturing eventually.
- But it conflicts with QUILL's core promises if made central. Copilot requires a paid subscription and an interactive GitHub OAuth device-flow sign-in, which is friction at odds with the local-first, bring-your-own-key, no-silent-network design and with the screen-reader-first simplicity of the connection flow. Its terms and telemetry posture are also a poorer fit for a privacy-first writing tool than a user's own API key.
- The pragmatic path: because the provider boundary is OpenAI-compatible, most of Copilot's value is already reachable through the existing custom OpenAI-compatible provider and through OpenAI, Claude, Gemini, and OpenRouter directly. So the marginal benefit of a dedicated Copilot integration is modest, while the cost (a bespoke auth flow, subscription gating, accessibility review of the sign-in, and ongoing terms compliance) is real. Add it later, gated and optional, only if beta users ask for it, and never as a default. See AI-18.

#### 18.6 New backlog items for gates and AI

These extend the section 14 tracker.

##### Quality gates (mostly P0 and P1)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| GATE-12 | Strengthen AI assistant repository guidance | Gates | S | Todo | copilot-instructions and a new AGENTS.md describe architecture, strict zone, scoped mypy, accessibility, no-silent-network, the audit footguns, and the definition of done; a check keeps them current. |
| GATE-13 | Machine-checked definition of done | Gates | S | Todo | A short done checklist (accessible, typed, tested, lint-clean, no silent network, docs regenerated) is documented and mirrored by the gates. |
| GATE-14 | CODEOWNERS and required review for high-risk areas | Gates | S | Todo | Security, sandbox, AI boundary, and secret-store changes require a human review even when AI-authored. |

##### AI and agent features

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| AI-8 | Context-aware AI actions | AI | M | Todo | Offered actions adapt to cursor or selection context and document type and are reachable from the QUILL key. |
| AI-9 | Prompt library and recipes | AI | M | Todo | Prompts and recipes can be saved, named, organized, shared, and picked with live preview. |
| AI-10 | Style training and explainable edits | AI | M | Todo | The assistant can match a user's voice and explain why it made each change, consistently across a document. |
| AI-11 | Local grounded answers over user content | AI | L | Todo | Optional local retrieval over open documents and the sticky-notes vault answers questions with citations and no network without consent. |
| AI-12 | AI evaluation harness | AI | M | Todo | A repeatable task set with quality checks measures AI and agent output and catches regressions before release. |
| AGENT-2 | Cleanup agent | AI | M | Todo | A messy import is cleaned through announced, reversible recipes ending in well-structured text. |
| AGENT-3 | Review agent | AI | M | Todo | A spoken, skimmable review reports structure, readability, accessibility, and consistency with one-key jumps to issues. |
| AGENT-4 | Safe local agent runtime | AI | L | Todo | The agent plans and takes one consented step at a time, calls only an in-app tool allowlist, never the network without consent, has a hard step cap and loop guard, and announces every step; reuses the sandbox and stability layers. |

##### AI provider review (from section 18.4 and 18.5)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| AI-18 | GitHub Copilot SDK as an optional post-1.0 provider | AI | M | Todo | If pursued, Copilot is an optional, clearly labeled provider behind the AIBackend boundary with an accessible OAuth device-flow sign-in, gated and never default; documented rationale (section 18.5) is honored. Not required for 1.0. |
| AI-19 | Accessible subscription sign-in (no pasted API key) | AI | M | In progress | Derived from the Pi research (see `docs/planning/pi.md`). Add a guided, fully keyboard-and-screen-reader login that lets a user authenticate with an existing provider subscription via an interactive flow (for example OAuth device flow) instead of pasting an unreadable API key, alongside the current key path. The most user-facing accessibility win from Pi: "sign in with the subscription you already have" rather than "paste a 51-character secret you cannot see." Credentials in DPAPI, explicit consent, no silent network, registered in the GATE-9 egress audit. Sits behind the AIBackend boundary (AI-13) and reuses the connection error taxonomy (AI-17). **Delivered:** `quill/core/ai/device_login.py` is a complete, wx-free, strict-typed OAuth 2.0 Device Authorization Grant (RFC 8628) state machine. `request_device_code` starts the flow; `announce_device_code` speaks the screen-reader instruction ("open <url> in your browser and enter the code WDJB-MJHT; this code expires in about 15 minutes."); `poll_once` classifies the provider's reply into pending / slow_down / authorized / denied / expired / error; `run_device_login` drives the full polling loop honoring the provider `interval`, backing off on `slow_down`, and stopping at `expires_in`, returning the terminal result; `describe_login_result` speaks the outcome. Every network exchange is an **injected** `poster`, so the engine adds no new `urlopen`/`urlretrieve` site to the GATE-9 egress inventory and is fully tested without a live endpoint (7 tests covering parse, state classification, success-after-pending, slow-down back-off, deadline expiry, denial, and the spoken announcements). ruff + strict mypy clean. **Remaining (honest, Linux/cloud blocker):** the flow state machine is complete and tested, but the real HTTPS poster, the DPAPI token storage, the consent surface (a dialog showing the device code + URL + expiry and letting the user start/cancel the flow), and the AIBackend (AI-13) wiring (integrate device-login as an alternative credential source for supported providers) are not yet built. No live subscription sign-in ships from this environment. **Windows finish-line:** Create a `DeviceLoginDialog` (show device code + URL + expiry, "Open in browser" button, "I've authorized, continue" button, cancel path). Wire it into the AI provider configuration surface (e.g., "Sign in with OpenAI account" button in the assistant setup). Implement a real HTTPS poster (using `urlopen` with TLS verification). Store the resulting token in DPAPI (via `quill/platform/windows/credential_manager.py`). Wire the token into `AIBackend` credential resolution so the provider uses the device-login token instead of requiring a pasted API key. Test on a real Windows machine with a live provider endpoint (e.g., OpenAI device authorization), verify the full flow (show code, user authorizes in browser, QUILL polls and retrieves token, token is used for subsequent AI requests, no pasted key required). Confirm the flow is fully keyboard and screen-reader accessible at every step. |

---

## Part IV: The combined accessibility suite (GLOW and BITS Whisperer)

QUILL does not exist alone. It sits beside two sibling products built for the same audience, and there is a rare opportunity to fuse them into a single, coherent, best-in-class accessibility suite rather than three overlapping apps. This part defines how to bring GLOW (document accessibility audit and fix) and BITS Whisperer (audio transcription) into QUILL as first-class, deeply integrated capabilities, what to keep, what to drop, and what shared foundation makes it durable.

The strategic case: all three products share a mission (do excellent work for blind and low-vision people), a stack (Python and wxPython, accessibility-first, local-first), and an audience. Three separate apps mean three menus to learn, three update mechanisms, three places for a document to live, and triplicated engineering. One suite, with QUILL as the writing and editing home, GLOW as its accessibility engine, and BITS Whisperer as its transcription engine, is simpler for users and far more powerful: write, transcribe, audit, fix, and publish in one place, by keyboard and voice, with one set of conventions.

### 19. GLOW integration: make QUILL accessibility-native

> The full, step-by-step 1.0 execution plan for this section (Tier 2 scope,
> sequenced after Tier 4) — the three-repo layout (`s:\code\quill-glow-core`,
> `s:\code\glow`, and QUILL), the ordered GLOW-0 through GLOW-7 work, the
> definition of done, and the risk register — lives in [glow.md](glow.md)
> under `docs/planning/`. This section is the narrative; [glow.md](glow.md)
> is the build sheet,
> and the two must stay in step.

QUILL already contains `quill/core/glow.py`, a text-level GLOW audit and fix surface (generic link text, plain-language lint, audit and fix reports for the selection or document) wired to commands such as `tools.glow_fix_document` and `tools.glow_fix_selection`. Separately, GLOW is a full document-accessibility platform (a VS Code agent toolkit, a desktop app, and a web app) enforcing ACB Large Print, APH, WCAG 2.2 AA, and Microsoft Accessibility Checker rules across Word, Excel, PowerPoint, PDF, EPUB, HTML, and Markdown, with audit, auto-fix, template generation, and conversion. The shared library `quill-glow-core` already exposes a stable host-facing API (`audit_by_extension`, `fix_by_extension`, `convert_to_markdown`, `get_component_versions`) with a dispatch core, a safe no-op fallback, and a GLOW backend adapter.

The plan: adopt `quill-glow-core` as the single shared engine so QUILL's in-editor GLOW and the GLOW desktop and web apps audit and fix by exactly the same rules, with one place to improve them.

Where the code lives (for the implementer): the shared engine is the `quill-glow-core` repo at `s:\code\quill-glow-core` (package `quill_glow_core`, public API in `src/quill_glow_core/services.py`: `configure_default_services`, `audit_by_extension`, `fix_by_extension`, `convert_to_markdown`, `get_component_versions`, plus `from_glow_backend`, which bridges to the canonical engine `acb_large_print_core`). The full GLOW platform repo is `s:\code\glow`. Note: `s:\code\glow-7.0.0` is a stale snapshot and should be ignored; do not read or modify it. This GLOW work therefore spans up to three repos — QUILL (this repo, the presentation layer), `quill-glow-core` (the shared contract), and `glow` (the rule engine) — so changes must be coordinated, each committed in its own repo, and the shared API kept stable.

Cross-repo prerequisite for GLOW-1 step 1: the `s:\code\glow` repo currently has failing CI/tests. Before QUILL depends on `quill-glow-core` (GLOW-1), the `glow` repo's failures must be diagnosed and fixed and its suite brought green, so QUILL builds on a stable engine rather than inheriting breakage. This is the first task of GLOW-1 and is tracked in the GLOW-1 acceptance criteria.

- Depend on the shared core. Replace QUILL's bespoke text-level checks with calls into `quill-glow-core` (`configure_default_services` then `audit_by_extension` and `fix_by_extension`), keeping QUILL's friendly in-editor reports as the presentation layer. When the GLOW backend is present, QUILL gets the full ACB, APH, WCAG, and MSAC rule sets; when it is absent, the safe no-op fallback keeps QUILL fully functional. See GLOW-1.
- Audit and fix by structure, not just text. Today QUILL audits plain text, Markdown, and HTML. Extend it through the shared core to audit and fix the structured formats QUILL already reads (DOCX, PPTX, XLSX, PDF, EPUB) so a user can open a real document and run a full accessibility audit in place. See GLOW-2, IO-1.
- An in-editor accessibility report that reads beautifully. Present GLOW findings as a navigable, screen-reader-pageable list grouped by severity, each with a one-key jump to the location, a plain-language explanation, and (where fixable) a reviewable apply-and-undo. This is the same surface the Accessibility agent (AGENT-1) drives. See GLOW-3, AGENT-1, AI-7.
- Standards profiles in QUILL. Surface GLOW's profiles (ACB 2025 Baseline, APH Submission, Combined Strict) as a setting so a user can choose the rigor that fits their work, with the active profile shown in every report for traceable evidence. See GLOW-4, SET-1.
- One-key publish to accessible output. Reuse GLOW's conversion chain (MarkItDown plus Pandoc, with LibreOffice-assisted pre-conversion and PyMuPDF table preservation) so QUILL can export clean, accessible Word, HTML, EPUB, and PDF with announced results. This realizes FEAT-17 on a proven engine. See GLOW-5, FEAT-17.
- Shared versioning and telemetry. Use `get_component_versions` and the startup telemetry so QUILL can show which accessibility engine and rule version is active, keeping the honesty principle. See GLOW-6.

What to keep lightweight in QUILL: QUILL should not absorb GLOW's web app, its branding-profile deployment machinery, or its template-generation server flows. QUILL consumes the shared core; the GLOW desktop and web apps remain the heavyweight authoring and batch surfaces. The boundary is clean: shared rules and fixers in `quill-glow-core`, three thin presentation layers on top.

### 20. BITS Whisperer integration: transcription becomes a QUILL superpower

> Status (2026-06-02): deferred to **QUILL 2.0**. BITS Whisperer is not part of
> the 1.0 milestone; its build order lives in Tier 5 (Part V). In the shipping 1.0
> application the entire suite is held back behind the locked-off
> `core.bw_whisperer` feature flag — the **BITS Whisperer** menu is not appended to
> the menu bar, its palette commands are gated out via the `bw_*` feature
> dependencies, and the first-run Startup Wizard skips the BITS Whisperer
> onboarding step — so no transcription surface reaches a 1.0 user. The narrative
> below is the 2.0 integration vision; the `quill/core/bw_speech.py` and
> `quill/core/bw_providers.py` scaffolding is retained as the 2.0 foundation.

QUILL already contains `quill/core/bw_speech.py`, a speech-model manager that mirrors a subset of BITS Whisperer (faster-whisper model specs, hardware eligibility, a model manager, provider status), exposed through a "BITS Whisperer" menu group (Speech Model Manager, Provider Center, Use Recommended, and so on). BITS Whisperer itself is a mature, accessibility-first transcription app: 18 providers (cloud and on-device), 14 Whisper models, AI translation and summarization, live microphone transcription, speaker diarization, a watch folder, scheduled transcription, do-not-disturb, a plugin system, seven export formats, and a setup wizard, all WCAG-adapted with a menu-first, screen-reader-first design.

The opportunity is large: a writer who can transcribe an interview or a lecture and immediately edit, audit, and publish it, all in one accessible app, has something no mainstream editor offers. The plan is to bring BITS Whisperer's transcription engine into QUILL as a first-class "Transcribe" capability, reusing BW's provider and model layer rather than reimplementing it.

What to bring into QUILL (high value):

- Transcribe to a document. Add a Transcribe command that takes an audio or video file (or a folder) and produces a QUILL document with the transcript, ready to edit, audit with GLOW, and publish. Reuse BW's provider abstraction and faster-whisper model manager (the `bw_speech.py` foundation already present). See BW-1.
- Local-first providers by default. Surface BW's on-device providers (local Whisper via faster-whisper, Vosk, Parakeet, Windows Speech, Azure Embedded) as the default, with cloud providers strictly opt-in and consented, matching QUILL's no-silent-network rule. See BW-2, AI-5.
- Live dictation into the editor. Bring BW's live microphone transcription in as an accessible "dictate into the document" mode with clear start, stop, and status announcements, complementing QUILL's existing dictation. See BW-3.
- Speaker labels and clean structure. Use BW's diarization to produce well-structured, speaker-labeled transcripts that QUILL can then clean with the Cleanup agent. See BW-4, AGENT-2.
- AI translation and summarization on the transcript, through QUILL's own consented AI layer rather than a parallel one. See BW-5, AI-8.
- Watch folder and batch. Offer BW's watch-folder and batch transcription as an optional power feature, announced non-intrusively, reusing QUILL's existing watch-folder pattern. See BW-6, FEAT-9.
- A unified Provider and Model Center. Consolidate BW's provider and model management with QUILL's AI model and connection management into one accessible Settings home, so a user manages all engines (writing AI, transcription providers, speech models) in one place. See BW-7, MENU-1, SET-1.

What to drop or de-scope from the standalone BITS Whisperer plan once integrated:

- Retire the duplicate application shell. The separate BW main window, tray icon, setup wizard, and updater are not needed inside QUILL; QUILL provides the shell, onboarding, and update path. Keep BW as a library, not a second app. See BW-8.
- Drop duplicated subsystems. BW's own settings store, watch folder, plugin manager, registration and licensing, beta service, and Copilot chat panel should defer to QUILL's equivalents rather than ship twice. Consolidate to one of each. See BW-8.
- Reconsider breadth of cloud providers. Eighteen providers is a maintenance load; in the suite, lead with the strong on-device set plus a small, well-supported cloud selection, and treat the long tail as optional plugins rather than core. See BW-9.
- Unify export. QUILL plus GLOW already cover accessible export (Word, HTML, EPUB, PDF, Markdown); transcript-specific formats (SRT, VTT) become QUILL export presets rather than a separate BW exporter. See BW-10, FEAT-17.

The combined-suite outcome: one accessible app where a blind or low-vision user can transcribe spoken audio, write and edit the result, audit and fix it to ACB, APH, and WCAG standards, and publish accessible output, entirely by keyboard and voice, with local-first privacy and one consistent set of conventions. That is a genuinely category-defining product, and it reuses two existing, proven engines instead of building from scratch.

### 21. Shared foundation for the suite

- One shared accessibility core. `quill-glow-core` is the single source of audit and fix rules for QUILL, GLOW desktop, and GLOW web. See GLOW-1.
- One transcription engine. BITS Whisperer's provider and model layer becomes a library consumed by QUILL (and still usable standalone if desired). See BW-1, BW-8.
- One set of conventions and gates. The quality-gate ladder (Part III) and the accessibility non-negotiables apply across the suite, so all three surfaces meet the same bar. See GATE-2.
- One identity for the user. Shared secret storage, shared update path, and a single Settings home reduce cognitive load and duplicated engineering. See SET-1, BW-7.

#### 21.1 New backlog items for the combined suite

These extend the section 14 tracker. The GLOW family (GLOW-1 through GLOW-8) has a
dedicated execution plan in [glow.md](glow.md); keep both in step when any GLOW
item changes scope or status.

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| GLOW-1 | Adopt quill-glow-core as the shared engine | Suite | M | In progress | Step 1 (glow repo, not yet verified): in `s:\code\glow`, the consumed desktop core (`acb_large_print` / `acb_large_print_core`, the target of `from_glow_backend`) is already green (308 tests); fix the failing Flask web suite (`acb_large_print_web`: the `/guide/` content string, branding injection, and form-POST tests) and reconcile the version sweep (VERSION 8.0.0 vs README vs TODO.md), committing in the `glow` repo so the whole engine is green. Step 2 (QUILL side, DONE): QUILL audits and fixes via `quill-glow-core` behind the optional extra `glow = ["quill-glow-core[glow]"]`; `quill/core/glow.py` gained a file-based seam (`audit_file`/`fix_file`, `get_glow_services`, `glow_backend_available`) plus a `_glow_finding_to_quill` adapter (severity map critical/high -> error, medium-band -> warning, low -> info; carries `score`/`grade` on `GlowFileAuditResult` and folds ACB `metadata`/location into the suggestion), using the GLOW backend when present and the safe `NoOpCoreServices`/unavailable fallback when absent; the in-editor text reports (`audit_text`/`fix_text`/`build_audit_report`) are unchanged; `tests/unit/core/test_glow_backend.py` covers both backend and fallback paths. `quill_glow_core` registered in the mypy ignore-missing list so the scoped strict gate stays green. Remaining: verify/finish Step 1 in the `glow` repo. Coordinate the three repos and keep the shared API stable. Ignore the stale `s:\code\glow-7.0.0` snapshot. |
| GLOW-2 | Audit and fix structured formats in-editor | Suite | L | Todo | DOCX, PPTX, XLSX, PDF, and EPUB can be audited (and fixed where supported) in place through the shared core. |
| GLOW-3 | Navigable in-editor accessibility report | Suite | M | Todo | Findings are a screen-reader-pageable list grouped by severity with one-key jump, plain-language explanation, and reviewable apply-and-undo. |
| GLOW-4 | Standards profiles setting | Suite | S | Todo | ACB Baseline, APH Submission, and Combined Strict are selectable; the active profile shows in every report. |
| GLOW-5 | Accessible publish via the GLOW conversion chain | Suite | M | Todo | One-key export to accessible Word, HTML, EPUB, and PDF using the shared conversion chain, with announced results. |
| GLOW-7 | Consent gate for GLOW optional AI and network features | Suite | S | In progress | Core contract done: `quill/core/glow.py` defines the `GlowNetworkConsent` model (AI alt-text, Presidio PII redaction, WCAG language processing — all OFF by default) and `glow_network_features_all_off()`; `audit_file`/`fix_file` forward a feature-enabling option only when a caller passes a consent object that explicitly enables it, so the default path is provably network-free. Tests assert the defaults are off, that the default GLOW path forwards no network kwarg, that only consented features are forwarded, and that `quill/core/glow.py` contains no egress call site; the GATE-9 inventory stays green. Settings now carries `glow_enabled` (the local engine is on by default) plus three consent flags (AI alt-text, PII redaction, language processing — all off), a "GLOW Accessibility" entry in Preferences and a GLOW step in the Startup Wizard let the user review and change them (both sanctioned `web` DLG-3 surfaces), and onboarding state persists separately. Remaining: wire the per-action consent prompt (visible progress and outcome) at the point a user invokes a structured GLOW audit — that surface lands with the in-editor report (GLOW-3). |
| GLOW-8 | Consented, signed in-app GLOW engine updates | Suite | M | In progress | Lets a user check for and apply a newer GLOW engine without waiting for a full QUILL release, reusing the updater trust model. Done: `quill/core/glow_updates.py` (wx-free) adds a signed `GlowUpdateManifest` (HMAC-SHA256 over the canonical form, verified before any download), HTTPS host-allow-listed URLs, per-wheel SHA-256 verification, an offline `--no-index` install with an injectable command runner, and `apply_glow_update` with rollback to the vendored wheels on failure; `check_for_glow_update` compares the manifest to `installed_glow_version()`. UI: a `tools.check_glow_updates` command and a Help-menu "Check for GLOW Updates..." item route through `MainFrame.check_for_glow_updates`, which gates download/install behind a second confirmation, announces the result, and tells the user to restart to apply. GATE-9: the new `fetch_glow_manifest` egress site is registered. Packaging: the Windows build now installs the vendored `quill-glow-core` contract wheel offline (`_install_vendored_glow`, `--find-links vendor/wheels`, with an import smoke check), the contract version is bumped to 0.1.1 and pinned, and `scripts/refresh_glow_wheel.py` re-vendors reproducibly from a committed source checkout. Tests: `tests/unit/core/test_glow_updates.py` (15) plus `tests/unit/ui/test_glow_update_wiring.py` (6). Remaining (2.0): the heavy `acb-large-print` backend is not yet vendored, so the full engine still installs online/opt-in; publish the signed manifest feed and exercise the live download-and-apply on a frozen Windows build. |
| BW-1 | Canonical transcript model and audio-to-document transcription | Suite | L | Todo | Add `quill/core/transcript.py` (a `Transcript` / `TranscriptSegment` / `TranscriptMetadata` model) that normalizes every BITS Whisperer provider's output to one shape, then a Transcribe command produces an editable transcript document from it, reusing BW's `TranscriptionService` / `ProviderManager` / `ModelManager` and the faster-whisper model layer; on-device by default. The model is the keystone the rest of the tier depends on. |
| BW-2 | Local-first transcription providers with consented cloud | Suite | M | Todo | On-device providers are default; cloud providers are opt-in and consented; no silent network calls. |
| BW-3 | Live dictation into the editor | Suite | M | Todo | Live microphone transcription writes into the document with clear start, stop, and status announcements. |
| BW-4 | Speaker-labeled, structured transcripts | Suite | M | Todo | Diarization produces speaker-labeled structure that the Cleanup agent can refine. |
| BW-5 | Translate and summarize transcripts via QUILL AI | Suite | M | Todo | Translation and summarization run through QUILL's consented AI layer, not a parallel one. |
| BW-6 | Watch-folder and batch transcription | Suite | M | Todo | Optional batch and watch-folder transcription reuses QUILL's watch-folder pattern with non-intrusive announcements. |
| BW-7 | Unified Provider and Model Center | Suite | M | Todo | Writing AI, transcription providers, and speech models are managed in one accessible Settings home. |
| BW-8 | Consume BITS Whisperer as a library, retire the duplicate shell | Suite | L | Todo | QUILL provides the shell, onboarding, settings, watch folder, plugins, and updates; BW ships as a consumed library, not a second app. |
| BW-9 | Three-tier provider exposure via feature flags | Suite | M | Todo | Providers are exposed in tiers behind feature flags: `core.bw_providers_local` (always on, offline) -> `core.bw_providers_plus` (opt-in Deepgram, OpenAI, Groq with cost estimation) -> `core.bw_providers_enterprise` (all 18). The long tail is reachable only at the enterprise tier; cloud providers are opt-in per action with keys in the OS credential vault. |
| BW-10 | Unify transcript export into QUILL presets | Suite | S | Todo | SRT and VTT become QUILL export presets; there is one export path for the suite. |

### 21.2 Packaging and freezing: the Nuitka evaluation (deferred to QUILL 2.0)

> Status (2026-06-03): deferred to **QUILL 2.0**. This is a packaging *decision*,
> not a feature, and it does not advance any open 1.0 acceptance criterion.
> Shipping 1.0 stays on the working embeddable-Python bundle
> ([scripts/build_windows_distribution.py](../../scripts/build_windows_distribution.py)),
> which also keeps the v1.1 plugin path trivial. The section below is the full
> analysis and the go/no-go gate for revisiting freezing in 2.0.

**The starting point (honest).** QUILL today ships raw `quill/**/*.py` source
alongside a pinned official **python-3.12.6-embed-amd64** runtime. The source on
disk is fully readable and editable by any end user. The PRD's *intended* frozen
build (§10.6) names **PyInstaller one-folder** but is unimplemented. So the real
choice is three-way: (a) today's embeddable-Python + source, (b) PyInstaller
one-folder, (c) **free Nuitka `--standalone`**. [Nuitka](https://nuitka.net/) is a
Python→C optimizing compiler.

**Framing assumptions that shape the verdict.**

- **Free Nuitka only.** QUILL is MIT-licensed in a public repo. Nuitka
  Commercial's headline — obfuscate source/constants/keys against reverse
  engineering (€250–400/yr) — is **structurally moot** because the source is
  already public. Paying to hide a public codebase is incoherent, so the
  commercial tier is disqualified outright and every gain below is from *free*
  Nuitka. That deletes Nuitka's marquee feature from the benefit column.
- **Standalone (one-folder), never onefile.** Onefile self-extracts to temp on
  every launch (slower cold start, AV/SmartScreen false positives). The PRD
  already chose folder mode for exactly this reason; the same constraint applies.

**Real gains (free Nuitka).**

- **G1 — Startup/import speed (the only measurable technical gain).** Compiled
  module bodies skip parse + bytecode-compile, so cold-start import is genuinely
  faster than both alternatives. Bounded and modest: the win is in import/startup,
  **not** steady-state editing — once the UI is up you are in wxPython event loops
  and native DLLs (TTS, llama, OCR) that Nuitka cannot speed up. It is a lever for
  PERF-9's startup budget, but deferred imports in pure source can also hit that
  budget, so Nuitka is *a* lever, not the only one.
- **G2 — A real binary you authored (the genuine non-perf gain).** Today QUILL
  signs and ships someone else's `python.exe`. Nuitka produces a real PE you
  compiled: cleaner `signtool` identity, faster SmartScreen reputation accrual,
  and tamper resistance against casual in-place edits of the writing-path source.
  This is operational hygiene and integrity, **not** IP protection (free Nuitka
  leaves constants/data readable, and the source is on GitHub anyway).
- **G3 — Marginally tighter layout.** Easily erased by the native dependency
  payload (llama/OCR/dictionaries dominate the §10.6 "180–220 MB" footprint). Not
  a real differentiator.

**Real risks (concentrated on QUILL's most safety-critical surfaces).**

- **R1 — Native/dynamic dependency resolution (the dominant risk).** Nuitka's
  static analyzer must find every module and native DLL at build time, and QUILL's
  stack is full of packages that load native code through *runtime* discovery that
  static analysis cannot follow without manual `--include-*` help: `winsdk`
  (WinRT OCR projections are dynamically generated), `pyenchant` (libenchant +
  provider DLLs via filesystem plugin paths), `prismatoid` (the screen-reader
  announcement bridge), `pyttsx3` (SAPI5 COM driver discovery), and
  `llama-cpp-python` (`llama.dll` + optional GPU backends). The failure mode is
  not "won't compile" — it is a build that **succeeds** with a backend **silently
  missing at runtime**, and the breakages cluster precisely on the
  accessibility-critical and AI paths QUILL exists to deliver.
- **R2 — Source tests cannot see freeze breakage (a verification gap).** The
  entire quality bar (ruff, mypy on core/io, GATE-11, A11Y-4, source-contract,
  headless a11y, SR scenarios) runs against *source*, never the compiled artifact.
  Adopting Nuitka therefore *mandates a new CI lane*: build the standalone bundle
  and run `tests/a11y` + an SR scenario **against the built `quill.exe`**. Without
  it, R1's silent-backend failures ship unverified — a direct violation of the
  honesty mandate. This is a permanent, slower second test lane.
- **R3 — The v1.1 plugin runtime (a structural collision).** The PRD plugin model
  (§10.10) loads plugins as `.py` at runtime; the current "ship interpreter + ship
  source" model makes that trivial. A compiled binary is a closed world. Nuitka
  bundles libpython so runtime import of pure-Python plugins is *technically*
  possible, but `__file__`/path semantics differ, plugins importing uncompiled
  third-party packages fail to resolve, and the clean "drop a `.py` in
  `plugins/`" UX gets fragile. Moot for 1.0 (first-party only, compile them in);
  a genuine architectural tension to pre-commit to for 1.1.
- **R4 — Data-file/`__file__` relocation (moderate, auditable).** QUILL discovers
  bundled data by package-relative paths (`quill/data/words_alpha.txt`,
  `th_en_US_v2.dat`, `quill/core/schemas/*.json` for atomic-write validation).
  Nuitka relocates modules, so every `Path(__file__).parent / …` loader must be
  verified under the compiled layout — easy to miss for the schema path, which
  would break *saving*, not just a feature.
- **R5 — Field-crash debuggability.** Compiled code still yields tracebacks but
  with muddier line-mapping than interpreted source, slightly harder for a small
  team's own support. (Commercial "traceback encryption" is the wrong direction
  for an OSS project that *wants* readable diagnostics.)

**Not real risks (so they are not over-weighted):** wxPython compatibility (Nuitka
has a dedicated wx plugin), C-toolchain/compile time (a non-factor for this team),
cost/lock-in (free tier only), and onefile AV issues (avoided by folder mode).

**Net assessment.** The asymmetry is the conclusion: the gains are nice-to-have
(snappier launch, cleaner signing) while the risks land on must-not-break
(screen-reader announcements, TTS, OCR, AI, plugins). For a screen-reader-first
app where a silently-missing SR bridge is a category-defining failure invisible to
the current source-based bar, the risk/reward is unfavorable *now*.

**Recommendation.** Do **not** adopt for 1.0. Re-evaluate **free Nuitka,
standalone only** as a measured 2.0 packaging spike (PKG-1), gated on one
empirical question, and explicitly drop Nuitka Commercial. The deciding contest is
*Nuitka-standalone vs. PyInstaller-one-folder*, not Nuitka vs. nothing, and the
tiebreaker is dependency-packaging robustness on those five native packages,
measured against a built artifact.

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| PKG-1 | Freezing spike: free Nuitka `--standalone` vs. PyInstaller one-folder | Packaging | L | Todo (2.0) | A time-boxed, evidence-producing spike. (1) Build QUILL with free Nuitka `--standalone` (never `--onefile`), wx plugin enabled, `quill` package included. (2) Manually resolve native includes for the five hard dependencies — `winsdk`, `pyenchant`, `prismatoid`, `pyttsx3`, `llama-cpp-python` — and confirm each backend loads at runtime in the built artifact. (3) Add a CI lane that runs `tests/a11y` + an SR scenario **against the built `quill.exe`**, not source, and require it green. (4) Verify package-relative data discovery (`quill/data/*`, `quill/core/schemas/*.json`) and atomic-write/save under the relocated layout. (5) Compare cold-start time and installed footprint against both the embeddable-Python bundle and a PyInstaller one-folder build. **Go** only if all five native backends resolve and the built-artifact a11y lane passes; otherwise record a clean **No** with evidence. Commercial Nuitka is explicitly out of scope (moot for an MIT public repo). |

---

## Part V: Impact ranking and build order

The user's directive is to develop with an impact-first mindset, and to be wise about whether and when to do hardening, security, and refactoring. This part ranks the entire plan, including QUILL's own features, from most impactful to least, and explains the reasoning so the order is clear and defensible. We are building for greatness and high quality, so impact here means lasting value to the user and to the product's standing, not just visible novelty.

### 22. How impact is judged

Two ideas, kept distinct on purpose:

- User impact: how much an item improves the real experience of a blind or low-vision writer (and the power user). A delightful, discoverable QUILL key is high user impact; an internal refactor is not.
- Leverage: how much an item unlocks or de-risks everything else. The quality-gate ladder and the main_frame characterization tests are low direct user impact but very high leverage, because they make all later work faster, safer, and higher quality.

Great products optimize for both. The wise sequence does the small, high-leverage protections first (so nothing later regresses users), then the high user-impact flagship work, then the larger structural and breadth investments, then the long tail. Specifically, on the user's question: yes, hardening and security and refactoring are worth doing, but not all at once and not all first. The cheap, user-protecting parts of hardening (the latent-crash bug fixes and the untrusted-input security) are top-tier because they are small and prevent real harm. The large refactor (decomposing the UI monolith) is high leverage but should come after the flagship value lands and only behind characterization tests, so it never becomes risk for its own sake.

### 23. The ranked tiers

Each tier lists what belongs in it and why, with the value it brings and the high-value outcome it produces. Items are referenced by their backlog IDs. The order follows the build directive: QUILL's own features and the cheap hardening come first, then GLOW, then BITS Whisperer last, with structural health and documentation sequenced around them.

#### Tier 1: Protect users and unlock the team (do first)

These are small, cheap, and either prevent real harm or unlock everything after them. Highest impact-to-effort ratio in the whole plan.

- Fix the latent-crash bugs: BUG-1, BUG-2 (real user paths), then BUG-3 through BUG-7. Value: the product cannot crash on a path a user can reach. Outcome: basic trust and a clean baseline.
- Harden untrusted input and the worst security gaps: SEC-10 and SEC-11 (XML and zip bombs), SEC-1 (executable-path validation), SEC-13 (secret redaction). Value: a malicious or malformed file cannot harm the user. Outcome: a defensible 1.0 safety bar.
- Stand up the gate ladder: GATE-1 through GATE-9, especially GATE-4 (banned patterns), GATE-9 (no-silent-network), and GATE-3 (scoped typing). Value: quality becomes objective and AI-assisted work accelerates safely. Outcome: nothing regresses users again, and Copilot and agents become a force multiplier instead of a risk.
- The accessibility gate on every change: GATE-7. Value: the mission becomes machine-enforced. Outcome: no UI change can quietly break a screen reader.
- Make feature flags a kept promise: FLAG-1 (and FLAG-2 as a definition-of-done check). Value: turning a feature off actually removes it from every surface, with no orphaned commands or dead menu entries. Outcome: users trust that the product respects their choices, and every later feature inherits the same contract for free. The richer profiles UI (FLAG-3) and export (FLAG-4) follow in Tier 2.

Why first: these are inexpensive, they protect users immediately, and they make every later step cheaper and safer. Skipping them would mean building flagship features on sand.

#### Tier 2: The flagship experience users will talk about (do next)

The highest user-impact features: the reasons a blind writer would choose and recommend QUILL.

- The QUILL key as a discoverable, tunable, consistent flagship: QK-1 through QK-5, QK-9 (question-mark cheat sheet and per-mode help). Value: the signature interaction becomes learnable in seconds and fast forever. Outcome: a memorable identity no competitor has.
- Navigation by structure: NAV-1, NAV-4 (go-to-anything), NAV-5. Value: moving by semantic units. Outcome: real documents become navigable by ear at speed.
- Bring visuals into text with OCR: OCR-1 through OCR-5. Value: a blind writer pulls text out of an image, a screenshot, a clipboard grab, or a screen region and hears it land in the document, working offline by default through the built-in Windows OCR engine with no install, and through Tesseract when the user opts in during onboarding. Outcome: inaccessible images stop being dead ends, and the same engine plugs into Watch Profiles so whole folders of images become readable documents automatically.
- Send files straight to QUILL from the file manager: SHELL-1 through SHELL-3. Value: a blind writer right-clicks an image, PDF, or document in Explorer and chooses Open, OCR, OCR to structured Markdown, or Read aloud, and the running QUILL instance carries it out — the same verbs reachable in-app and from the command line (`quill --action ocr <path>`), all opt-in through the Integration and Context Menu settings. Outcome: QUILL becomes the obvious destination for inaccessible files anywhere on the system, with the classic Explorer menu shipping first (SHELL-1) and the Windows 11 modern-menu packaging and the AI structuring pass tracked honestly as remaining (SHELL-2, SHELL-3).
- The Accessibility agent and trustworthy AI editing: AGENT-1, AI-7 (diffs reviewable by ear), AI-1 (streaming), AI-6 (graceful degradation). Value: "make this document accessible," done step by step, reversibly, by keyboard and voice. Outcome: a category-defining capability that embodies the mission.
- Make the configured AI providers actually work: AI-13 (the headline fix), AI-15 (provider correctness), AI-17 (chat-path error messages), then AI-14 (streaming) and AI-16 (contract tests). Value: when a user selects OpenAI, OpenRouter, Gemini, Azure, Ollama, or Claude, that provider is the one that responds, instead of silently falling back to the local model. Outcome: the provider boundary becomes trustworthy and the QUILL AI surface is honest end to end. This is both a QUILL feature and AI hardening, so it sits here with the flagship.
- Deep, tunable settings: SET-1 through SET-7. Value: users shape QUILL precisely to their hands and ears. Outcome: the product meets people exactly where they are.
- Feature profiles and per-feature control: FLAG-3 and FLAG-4. Value: users adopt whole sets of features at once (Essential through Full QUILL) or toggle anything individually, with dependencies resolved and announced, and can export or pre-configure the whole set. Outcome: the feature-flag promise from Tier 1 becomes a rich, accessible control surface, so people run exactly the QUILL they want.
- Trustworthy external-change handling: FEAT-19. Value: a file edited by another program is never silently lost or silently overwritten; clean files reload in place without losing the cursor, and conflicts get a clear spoken choice. Outcome: QUILL feels safe and alive when documents change underneath it, which matters most to a screen-reader user who cannot see a flicker.
- Watch Profiles, the accessible automation hub: WATCH-1 through WATCH-7 (many folders, each bound to its own action, all feeding one durable, monitorable queue with an accessible Watch Queue Monitor in Help). Value: a blind writer drops work into folders and listens to a calm queue process it — open, convert, move, run a macro or Python transform, or a consented AI action — instead of shepherding every file by hand. Outcome: a productivity-and-accessibility superpower that unifies QUILL's distinctive engines behind one learnable model (a folder, an action, a queue), and a quiet differentiator no mainstream editor offers. The GLOW and transcription actions (WATCH-8, WATCH-9) plug into the same registry as their tiers land.
- Dialogs that never trap or go silent: DLG-1, enforced by the A11Y-4 contract guard. Value: the safe submit-once forms (find-in-files, Status Bar Layout, the voice chooser, Watch Folder Settings, the YAML editor, General Preferences) move onto the one shared accessible `show_web_form` surface, and a machine-enforced guard makes the construction bug class behind the find-in-files Cancel trap (#84) and the bookmark dialogs (#85) un-regressable. Outcome: every dialog has a reliable Escape, an explicit default, and returns focus to the editor, and new dialogs are correct by construction. This executes the form wave of issue #73; the interactive AI-tool dialogs are converted individually and screen-reader-verified later (DLG-2, Tier 4), never batch-rewritten.

Why second: this is where user love is won. It comes right after the protections so the flagship is built on a safe, gated base.

#### Tier 3: GLOW, the accessibility engine inside QUILL (QUILL 1.0 — Tier 2 scope, sequenced after Tier 4)

> Status (2026-06-03): **back in QUILL 1.0.** Per maintainer direction the shared `quill-glow-core` engine requirements are now met (the engine is green), so the GLOW family (GLOW-1 through GLOW-7) returns to the 1.0 milestone, classified under Tier 2 (the flagship experience) and sequenced for execution after the Tier 4 structural work. The GLOW watch-action binding (WATCH-8) and the axe-core / Accessibility Agents workstream (AX-A through AX-F) remain deferred to **QUILL 2.0**. The "Tier 3" heading is retained for continuity with the cross-repo execution plan in [glow.md](glow.md).

Per the build directive, GLOW comes before transcription: it deepens QUILL's core mission of accessible documents and reuses a proven engine.

- GLOW as the in-app accessibility engine: GLOW-1 through GLOW-5. Step 1 of GLOW-1 is a cross-repo prerequisite: fix the failing CI in the `s:\code\glow` engine repo and bring it green before QUILL depends on it. Then QUILL audits and fixes real documents to ACB, APH, and WCAG standards in place, through the shared `quill-glow-core` API rather than the thin local bridge. The work spans three repos (QUILL, `quill-glow-core`, `glow`); the stale `s:\code\glow-7.0.0` snapshot is ignored. Value: writing and document accessibility become one app, built on a stable engine. Outcome: a category-defining, accessibility-native editor.
- GLOW interaction quality: surface findings as reviewable-by-ear diffs and one-key jumps, reuse the consented, reversible flow from the Accessibility agent (AGENT-1), and keep the standards profiles (ACB 2025 Baseline, APH Submission, Combined Strict) explicit and announced. Value: the audit-and-fix loop is fully accessible. Outcome: GLOW feels native to QUILL, not bolted on.
- Code-quality and integration fixes for the boundary: replace the thin `quill/core/glow.py` bridge with calls into `quill-glow-core`, add contract tests for the shared API, and keep version and component reporting honest. Value: a clean, tested seam. Outcome: GLOW improvements flow into QUILL without surprises.
- GLOW as a watch action: WATCH-8. Value: register GLOW's audit-and-fix flow as a Watch Profile action so a shared folder of incoming documents is made accessible automatically, reversibly, and announced through the queue. Outcome: the accessibility engine becomes hands-free for whole folders, not just the open document.

Why third: high strategic value that extends the core mission, depends on the gated base (Tier 1), and is most compelling once the flagship experience (Tier 2) already feels great. Most cost is integration, not invention.

#### Tier 4: Structural health and performance that keep greatness durable (high leverage)

Not flashy, but what lets the product stay excellent as it grows.

- The largest refactor, done first: DLG-3. Review every single dialog across `quill/ui/*` and convert any custom-drawn or hand-rolled dialog that could conform to a stock wxPython construct — even an enhanced wxPython standard built on stock controls — into native wxPython. The risk this retires is concrete and otherwise invisible to a Linux/source-contract bar: controls that do not work, focus landing on the wrong control, and rendering breakage all live in custom dialogs. The A11Y-4 dialog-contract guard is strengthened in the same effort so the residual-custom-dialog bug class is caught at author time and cannot regress. This supersedes the batch ambition of DLG-2 (its individual AI-tool conversions fold in) and is sequenced ahead of the monolith decomposition so the dialog estate is sound before CQ-1/CQ-16 split it. Value: dialogs that are correct by construction. Outcome: the single highest-risk surface in the UI becomes durable and verifiable. DLG-3 also folds in and supersedes issues #73 and #72, whose concrete inventory it inherits:
  - **Two sanctioned dialog kinds, nothing bespoke.** **Native** (`wx.MessageDialog`/`wx.MessageBox`) for confirms, saves, and simple messages; the existing **accessible web surfaces** for anything that displays rich content or captures input — reuse `AccessibleChatView` (the Ask Quill chat input pattern), `AccessibleHtmlDialog` for display, and `MarkdownPreviewDialog` for previews. No new component is built.
  - **Keep as-is (already correct):** `AskQuillChatDialog` (web chat), `MarkdownPreviewDialog` (web), the unsaved-changes prompt (native `wx.MessageDialog`), and the delete-note confirm (native).
  - **Convert to web (display or input):** `StickyNoteEditorDialog` and `StickyNotesVaultDialog` (`quill/ui/sticky_notes.py`); `RunPythonDialog`, `PromptStudioDialog`, `AgentCenterDialog`, `WritingAssistantDialog`, `SearchableModelPickerDialog`, `AIHubDialog`, and `AssistantConnectionDialog` (`quill/ui/assistant_tools.py`); `AIModelDialog` (`quill/ui/ai_model_panel.py`); `TrainStyleDialog` (`quill/ui/style_panel.py`); and the onboarding/welcome flow, which must render in a web surface instead of dumping raw HTML into a `Document` (this fixes #72).
  - **Convert to native `wx.MessageDialog`:** the trust-consent prompt, the untrusted-location prompt, and the assorted confirm prompts in `quill/ui/main_frame.py`.
  - **Decide case-by-case:** `CommandPaletteDialog` (search + list picker) — likely web for consistent screen-reader behavior.
  - **Bugs this closes:** the first-run onboarding **startup crash** on Windows and macOS with a screen reader active (it lives in a hand-rolled onboarding dialog in the `show_startup_wizard_page` → profile/assistant/speech/watch-folder sequence); the sticky-note editor landing focus on **Save** instead of the text field; and #72's raw-HTML welcome document.
  - **Acceptance:** no hand-rolled `wx.Dialog` subclasses remain for confirm/message flows (those use `wx.MessageDialog`/`MessageBox`); input/display dialogs use the existing accessible web surfaces (not a new component); first-run onboarding completes without crashing on Windows and macOS with a screen reader on; welcome/onboarding content renders rather than appearing as raw HTML.
- Decompose the UI monolith behind characterization tests: CQ-16 then CQ-1, with GATE-6 and GATE-11. Value: every future change gets faster and safer. Outcome: the 18,748-line risk becomes maintainable. Sequencing note: do this after Tier 2 ships and after DLG-3, never as a prerequisite to Tier 2, and always behind passing characterization tests.
- Drive the strict-typing zone and lint to clean: TYPE-1 through TYPE-8, CQ-18. Value: a class of bugs disappears at author time. Outcome: a codebase that resists regression.
- Remove first-use stalls and enforce budgets: PERF-1 through PERF-3, PERF-9 through PERF-14, GATE-10. Value: the app feels instant. Outcome: performance that does not slip back.
- The remaining security hardening: SEC-7, SEC-14 through SEC-17, SEC-8 (plugins stay gated); SEC-6 (download checksum verification) is done. Value: defense in depth. Outcome: a product that is safe by construction.
- Last code item before documentation: ORG-1, a full source-tree organizational review. Relocate root-level platform files to their sanctioned homes (for example `macos_app.py`/`setup_macos.py` into `quill/platform/macos/`), consolidate scattered root design docs into `docs/`, and rationalize the build/dist scratch folders into one ignored output convention. Sequenced **dead last among Tier 4 code** because it touches imports, CI paths, installer scripts, and packaging manifests, so it runs only after the other refactors settle and entirely behind the GATE-6/GATE-11/A11Y-4 and full-test gates. Value: a best-in-class repository tree a new contributor can navigate at a glance. Outcome: structure that matches the quality of the code inside it.

Why fourth: high leverage but mostly invisible to users, so it follows the work that wins user love, while the cheap protective parts of it already happened in Tier 1.

#### Tier 5: BITS Whisperer transcription (deferred to QUILL 2.0)

> Status (2026-06-02): deferred to **QUILL 2.0**. BITS Whisperer is the second distinctive engine and the integration plan below stands, but it is no longer part of the 1.0 milestone.

Transcription is the second proven engine QUILL absorbs, and with the tier swap it now precedes documentation so the docs can describe a product whose transcription is already built. BITS Whisperer (`s:\code\bw`) is production-ready (875 tests passing, CI green, a framework-agnostic core with no `wx` imports), so unlike GLOW there is no engine-repo fix to do first — this tier is pure, clean integration.

- The canonical transcript model is the keystone: BW-1. Add `quill/core/transcript.py` (a `Transcript` / `TranscriptSegment` / `TranscriptMetadata` model) so all of BITS Whisperer's providers, whose raw outputs differ in timestamp and diarization shape, normalize to one structure that GLOW audit, AI clean-up, and export all consume. Value: provider variance never leaks into QUILL. Outcome: one stable shape everything builds on. Everything else in this tier depends on it.
- Wire the transcription runtime: BW-2, BW-3. Add `quill/core/bw_transcription.py` (a wrapper binding BITS Whisperer's `TranscriptionService` / `ProviderManager` / `ModelManager` to QUILL's async and announcement model) and `quill/io/transcripts.py` (JSON↔Markdown with speaker labels and timestamps). The existing `bw_speech.py` model management and `bw_providers.py` readiness surfaces finally drive real transcription. Value: transcribe audio, then edit, audit, and publish without leaving QUILL. Outcome: a write-transcribe-audit-publish loop no mainstream editor has.
- Three-tier provider exposure behind feature flags: BW-9. `core.bw_providers_local` (always on, offline Whisper/Vosk/Windows Speech) → `core.bw_providers_plus` (opt-in Deepgram, OpenAI, Groq, with cost estimation) → `core.bw_providers_enterprise` (all 18). Cloud providers are opt-in per action with keys in the OS credential vault; nothing reaches a network silently. Value: progressive disclosure instead of an 18-provider wall. Outcome: a newcomer transcribes locally in two keystrokes; a pro unlocks the full matrix.
- Transcription as a watch action: WATCH-9. Register BITS Whisperer transcription as a Watch Profile action so dropping audio into a folder produces an editable, accessible document automatically, which the queue can chain into the GLOW (WATCH-8) and export actions. Outcome: the drop-audio-in, accessible-edited-document-out loop becomes fully hands-free and screen-reader-narrated — the most distinctive single payoff of the WATCH family.
- Right-size and unify the suite: BW-4 (consume BITS Whisperer purely as a library — do NOT absorb its duplicate shell, tray, setup wizard, updater, settings dialog, watch folder, plugin manager, or license/registration; QUILL owns those surfaces), BW-7 (one shared export path), and one Settings home and one update path (Part IV, section 21). Value: less to learn, less to maintain. Outcome: a coherent suite rather than overlapping apps.
- Defer the far edges (beyond this tier, guided by feedback): live microphone captioning (extends dictation), speaker-turn analysis and meeting minutes, multilingual segmentation, and a transcription cost dashboard. Value: keep the tier focused on the proven loop. Outcome: the headline ships clean; the explorations follow real demand.

Packaging note for 2.0: the freezing decision (PKG-1, §21.2) is a 2.0 packaging spike, not part of this transcription tier. It runs as an independent, evidence-producing evaluation of free Nuitka `--standalone` vs. PyInstaller one-folder, gated on the five native backends resolving and an a11y lane passing against the built `quill.exe`. 1.0 ships on the existing embeddable-Python bundle.

Why fifth: it is the second category-defining engine and it completes the WATCH loop, but it sits one step further from the writing-and-accessibility core than GLOW, so it follows the flagship, GLOW, and structural work — and now precedes documentation so the docs describe it as finished.

#### Tier 6: Documentation greatness and the learning surface (completes the product, last)

A great product is not done until people can learn it — and per the tier swap, documentation lands last so it describes a product that is already built, safe, delightful, GLOW-native, and transcription-capable. The BITS Whisperer docs at `s:\code\bw\docs` (PRD, USER_GUIDE, GETTING_STARTED) are reused and harmonized into QUILL's voice rather than rewritten from scratch.

- Consolidate and elevate the docs folder: DOC-14 through DOC-17, DOC-11 (accessibility), DOC-12 (engineering docs). Value: documentation that is itself a model of accessibility and clarity. Outcome: nobody is left behind.
- DOC-18 (PRD consolidation and clean polish): bring `docs/QUILL-PRD.md` fully current with shipped behavior, then roll the entire `docs/accessibility/` and `docs/engineering/` document sets up into the PRD as consolidated sections so the PRD is the single source of truth. Once their content lives in the PRD, retire the `docs/accessibility/` and `docs/engineering/` folders (and their generated `.html`/`.epub` artifacts), updating every cross-reference and the docs-artifact gate accordingly. Regenerate the PRD `.html`/`.epub` via pandoc and pass `scripts/check_docs_artifacts.py` and `scripts/plain_language_lint.py`. Value: one authoritative, accessible, well-polished PRD instead of scattered folders. Outcome: a clean documentation surface with no duplication or drift.
- The learning surface: DOC-1 through DOC-8, the podcasts (POD-1 through POD-5), and the tutorials (TUT-1 through TUT-7), now including the transcription and GLOW audit loops as first-class lessons. Value: a complete path from first launch to mastery. Outcome: a launch that lands with a full learning experience.
- Test breadth: CQ-11 through CQ-16, CQ-23, CQ-24, the IO matrix, and the sandbox policy suite. Value: confidence that everything documented actually works. Outcome: durable quality.
- Breadth and exploration (folded in here as the final reach): NAV-10 (symbol navigation), AI-11 (local grounded answers), AI-12 (evaluation harness), AI-18 (optional GitHub Copilot SDK provider, only if beta users ask), FEAT-12 through FEAT-18, LINUX-2 (accessible Linux to the product bar), ECO-1 (plugin capability, signing, marketplace), L10N-1 (full UI and docs localization), and COLLAB-1 (accessible asynchronous review and sharing). Value: new reach and polish. Outcome: a growing product shaped by real user feedback, with nothing of substance left below best-in-class.

#### Power Tools feature parity (delivered in QUILL 1.0)

> Status (2026-06-09): **delivered**. Originally captured as a QUILL 2.0 backlog
> from a competitive analysis of Power Tools 4.0 (Jamal Mazrui, 2007 to 2017), a
> respected screen-reader-first Windows text editor (the "Homer editor
> interface"), this set of self-contained editor conveniences (EDS-1 through
> EDS-21) was pulled forward and completed for 1.0. Each command's wx-free logic
> lives in a dedicated `quill/core` module with unit tests; the UI layer wires
> them through `PowerToolsActionsMixin`, registers them on the command palette and
> Keymap Editor (no default keybinding, to avoid colliding with QUILL's curated
> keymap), and surfaces them on the **Tools > Power Tools** submenu.

Why this matters competitively: Power Tools is one of the few editors built, like
QUILL, primarily for blind and low-vision writers, and it accumulated two decades
of small, speech-friendly editor conveniences. QUILL already matches or exceeds
Power Tools across its entire core editing, navigation, search, snippet, structured
text, and file-management surface, and far exceeds it on AI, accessibility audit
(GLOW), OCR and image description, modern TTS, dictation, macros, watch folders,
feature profiles, and cross-screen-reader announcements. Power Tools's only large
category QUILL deliberately does not pursue is RTF *live rich-editing* (visual
word processing on a `wx.RichTextCtrl`) and JScript.NET scripting add-ins; RTF as
a *file format* is delivered as an io-layer round-trip (EDS-21). The actionable
residue — a set of roughly twenty self-contained editor conveniences plus the RTF
format work — is listed as EDS-1 through EDS-21 below, all delivered in 1.0.

**Competitive analysis: Power Tools 4.0 vs QUILL**

| Capability area | Power Tools 4.0 | QUILL today | Verdict |
| --- | --- | --- | --- |
| Core editing (copy/cut/paste, undo/redo, select all) | Yes | Yes (+ persistent undo) | QUILL parity+ |
| Case conversion (upper/lower/proper/swap) | Yes | Yes | Parity |
| Sort / reverse / unique / trim / join lines | Yes | Yes | Parity |
| Find, find-again, reverse, regex replace | Yes | Yes (+ regex helper) | QUILL parity+ |
| Go to line / page, bookmarks, brace match, block nav | Yes | Yes | Parity |
| Indent/outdent, toggle comment | Yes | Yes | Parity |
| Snippets, HTML/Markdown tag insertion | Yes (100+ snippets) | Yes | Parity |
| Structured text (sections, table of contents, headings) | Yes (dashes+form-feed) | Yes (heading/region nav, outline) | QUILL different approach |
| Spell check, thesaurus | Yes (needs MS Word) | Yes (native) | QUILL parity+ |
| Format converters, open-other-format, export | Yes | Yes (pandoc, external tools) | Parity |
| Encoding conversion (100+ encodings, codepoint dump) | Yes | Partial (choose-encoding only) | Gap (EDS scope) |
| Small editor conveniences (insert special char, date/time, number lines, hard-wrap, read-only guard, delete-to-bounds) | Yes | Yes | Delivered (EDS-1..20) |
| On-demand speech queries (say address/status/selection) | Yes | Yes | Delivered (EDS-14) |
| Key Describer, indent-announce mode | Yes | Yes | Delivered (EDS-17, EDS-18) |
| RTF as a file format (read formatting, write back) | Yes | Yes (io-layer round-trip) | Delivered (EDS-21) |
| RTF live rich editing (justify/style/font, format nav) | Yes | Opt-in Rich text lens (read-only rich view delivered; editable rich in progress) | Partial (RTF-22) |
| JScript.NET scripting add-ins, exposed object model | Yes | No (plugins + AI instead) | Out of scope by design |
| Compiler/run integration, LaTeX, PyBrace/PyDent | Yes | Partial (external tools) | Out of scope / future plugins |
| Burn to CD, Send-To menu, MDI tile/cascade, web download | Yes | No | Obsolete / not pursued |
| AI assistant (rewrite, summarize, continue, agents) | No | Yes | QUILL only |
| Accessibility audit and fix (GLOW) | No | Yes | QUILL only |
| OCR and on-demand image description | No | Yes | QUILL only |
| Modern TTS read-aloud + audio export, dictation, macros | No | Yes | QUILL only |
| Watch folders, feature profiles, onboarding | No | Yes | QUILL only |
| Cross-screen-reader announcement engine, DPAPI secrets | Partial (direct SR speech) | Yes (NVDA/JAWS/Narrator parity) | QUILL parity+ |

**power-tool items (all delivered in QUILL 1.0)**

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| RTF-22 | Optional native Rich text lens (rtf.md Part One) | Features | L | In progress | An opt-in alternative editor surface that renders bold/italic/headings/bullets/links natively in a `wx.richtext.RichTextCtrl`, gated behind the `editor_surface` setting (default `plain`) so the stock `wx.TextCtrl` stays the default writing path. QUILL Markdown remains the canonical document value, so every existing offset-based command, search, metric, outline, autosave, and persistent-undo keeps working unchanged through the surface. **Delivered:** wx-free rich model and conversions (`quill/io/rtf_model.py`), RTF safety scanning that strips OLE/object groups and flags remote fields before native loading (`quill/io/rtf_safety.py`, wired into `read_rtf_document`), spoken-format vocabulary (`quill/core/format_speech.py`), the editor-surface protocol (`quill/ui/editor_surface.py`), the dual-lens `RichTextSurface` with a read-only native rich view plus the canonical Markdown lens (`quill/ui/rich_text_surface.py`), lossless lens switching (`view.switch_editing_lens`, `Ctrl+Shift+Grave, K`), and `.rtf` files opening in the rich lens when enabled. All covered by wx-free unit/source-contract tests, strict-mypy and ruff clean. **In progress (honest):** an editable rich surface with rich-native persistent undo — the rich lens currently renders read-only and editing happens in the Markdown lens, because faithful structural reconstruction from a live `RichTextCtrl` buffer plus rich undo is the subtlest part of the proposal and is not yet complete. |

Note on RTF and the editor control surface: QUILL's writing path is a stock
`wx.TextCtrl` on purpose, because plain-text-first editing gives the strongest,
most predictable screen-reader fidelity (NVDA, JAWS, Narrator parity) and is a
standing design rule. There are two distinct "RTF support" scopes and only one is
pursued. **In scope (EDS-21):** RTF as a *format* in the io layer, where formatting
is read into QUILL's Markdown-style markup and written back out to RTF, with the
editor surface unchanged. This is a clean extension of the existing `io/*` contract
and the right home for the lossy `_format_rtf` extract that exists today. **Out of
scope by design:** RTF as a *live rich-editing surface* on the default writing
path. The stock `wx.TextCtrl` remains the default and only writing control, because
plain-text-first editing gives the strongest screen-reader fidelity and every
existing command and EDS-1..20 convenience assumes it. RTF-22 adds an **opt-in**
Rich text lens (off by default) that renders formatting natively in a
`wx.richtext.RichTextCtrl` *without* changing the canonical document model — QUILL
Markdown stays the editable canonical value, the rich view is an overlay, and the
two lenses switch losslessly. A fully editable rich surface with rich-native undo
remains honestly in progress (see RTF-22). Importantly, none of EDS-1 through EDS-20
depend on RTF; they are plain-text conveniences that ship on the current surface
regardless of whether EDS-21 lands.

Status: delivered in 1.0. Every EDS item is a self-contained editor convenience,
implemented with its wx-free logic in a dedicated `quill/core` module (unit-tested)
and wired into the editor through `PowerToolsActionsMixin`, the command palette, the
Keymap Editor, and the Tools > Power Tools submenu. The two large Power Tools
categories QUILL omits, RTF *live* word processing and JScript.NET scripting,
remain deliberate scope choices rather than backlog items (see the RTF note above;
EDS-21 delivers RTF only as an io-layer file format).

#### 2.0 competitive parity plan (Notepad++ benchmark, adapted for QUILL)

This plan captures the highest-value competitive gaps identified in the Notepad++ comparison and folds them into QUILL 2.0 without violating QUILL's accessibility and trust principles.

1. **Search at project scale (COMP-1).** Deliver a first-class Find in Folder and Workspace Search flow so technical writers and developer users can search and replace across real projects without leaving QUILL. The key requirement is not just speed; it is accessibility stability: results must be reviewable by ear, keyboard traversal must never lose context, and operation summaries must announce exactly what changed.
2. **Workspace depth, not just session recall (COMP-2).** Expand existing session support into an explicit workspace model with named sets, folder trees, and project groups, including reliable restore announcements. This is the core context-switching parity move: users should reopen "what I was working on" in one action with deterministic focus and state restoration.
3. **Plugin lifecycle parity, but safer than competitors (COMP-3).** Build a complete plugin management lifecycle that users can operate fully by keyboard and screen reader, while preserving QUILL's stricter consent and capability boundaries. The bar is functional parity with Notepad++ plugin administration plus stronger security posture (permission prompts, provenance, rollback, and safe-mode fallback).
4. **Encoding conversion as an explicit workflow (COMP-4).** Close the known encoding gap by adding convert flows, loss-risk preview, and reversible outcomes, not just open or reload choices. This targets legacy-document and mixed-encoding workflows where blind users currently need external tools to recover text safely.
5. **Macro power-user maturity (COMP-5).** Move macros from basic utility to a robust automation surface with naming, descriptions, repeat controls, import/export, and deterministic replay behavior. The objective is a "safe automation" model where productivity gains do not come at the cost of unpredictable edits or silent failures.
6. **Two-pane editing for review-heavy workflows (COMP-6).** Add optional split editing that remains stock-control and announcement-correct, enabling side-by-side review and synchronized navigation. This is specifically scoped for compare and revision tasks and must preserve QUILL's no-focus-chaos rule.
7. **GitHub Copilot SDK as an optional cloud provider (COMP-7).** Add a GitHub Copilot adapter behind the existing `quill/ai/*` provider boundary and consent/egress gates (AI-13, GATE-9), never a default and off until the user opts in. It reuses the device-login sign-in path (AI-19) so a user can authenticate with a subscription they already have instead of pasting a hidden API key, and it explicitly targets Copilot's **free tier** so the capability is reachable without a paid plan. Strictly local-first defaults are preserved: the bundled GGUF models stay the default, no document content leaves the device without per-action consent, and the adapter advertises an unavailable path with an announced reason when the user is not signed in. The subscription/sign-in friction is the reason this stays post-1.0 rather than a core capability.

Intentional non-goal in this parity plan: **multi-caret and rectangular editing remain out of scope** for QUILL's primary interaction model, because they conflict with screen-reader navigation patterns and the plain, predictable edit-field-first philosophy.

Why sixth: essential for greatness, but it should describe a product that is already built, safe, delightful, and feature-complete, so it follows everything it documents.

Why last: valuable but not required for a great, trustworthy 1.0; the transcription suite and the stretch items are best chosen with beta evidence in hand, and the build directive explicitly places transcription after QUILL, hardening, and GLOW.

### 24. The development mindset in one paragraph

Lead with cheap protections and gates, because they make everything after them safe and fast. Then spend the bulk of the energy on the flagship QUILL experience, including making the configured AI providers actually respond (AI-13), because that is where greatness is felt and where the product must be honest. Bring GLOW in next, since it extends QUILL's accessibility mission and reuses a proven engine, and only then add BITS Whisperer transcription, which is the most distant from the writing core. Treat the big refactor and performance and security depth as high-leverage investments that follow, not precede, the user-facing wins, and always do the refactor behind characterization tests. On the GitHub Copilot SDK: keep it optional and post-1.0, behind the same provider boundary, never a default, because its subscription and sign-in friction conflict with the local-first, bring-your-own-key promise even though the underlying models add value. Finish by making the documentation and learning surface as excellent as the product. Do not do hardening or refactoring for their own sake or all at once; do the parts that protect users early, and the parts that only reshape code later, once their value is clear and their risk is contained.

---

## Part VI: State of the union

If every item in this plan were completed (Parts I through V: the delight program, the verified bug and security and typing and performance fixes, the documentation greatness work, the quality-gate ladder, the AI and agent program, the combined GLOW and BITS Whisperer suite, and the impact-ordered build sequence), here is the scale and standing the product would reach.

### Live progress log (honest, updated as each major section lands)

This log is the single honest record of where the product actually stands as work completes. It is updated at the end of every major section so the team always meets at a truthful assessment, not an aspirational one. Newest entry first.

#### Tier completion tracker (remaining backlog items per tier)

This table tracks how many of the backlog IDs each tier names are still open. It is updated whenever an item closes, so the count of remaining work at every level is always visible at a glance. Counts cover the IDs explicitly listed in each tier's prose in section 23; a few infrastructure IDs that serve two tiers (for example GATE-6 and CQ-16) are counted once, in their primary tier.

| --- | --- | --- | --- | --- | --- |
| Tier 1 | Protect users and unlock the team | 23 | 23 | 0 | (complete) |
| Tier 2 | Flagship experience | 67 | 58 | 9 | AI-19, SHELL-2, SHELL-3, GLOW-1, GLOW-2, GLOW-3, GLOW-4, GLOW-5, GLOW-7 |
| Tier 4 | Structural health and performance | 32 | 32 | 0 | (complete) |
| Tier 6 | Documentation and learning surface | 35 | 3 | 32 | DLG-3.8, DOC-14..18, DOC-11, DOC-12, DOC-1..8, POD-1..5, TUT-1..7, CQ-11, CQ-14, CQ-23, CQ-24, LINUX-2 |
| **1.0 subtotal** | Tiers 1, 2, 4, 6 (the QUILL 1.0 scope) | **157** | **116** | **41** | |
| Tier 3 (2.0) | GLOW watch action — deferred to QUILL 2.0 | 1 | 0 | 1 | WATCH-8 |
| Tier 5 (2.0) | BITS Whisperer transcription — deferred to QUILL 2.0 | 28 | 0 | 28 | BW-1..10, WATCH-9, NAV-10, AI-11, AI-12, AI-18, FEAT-12..18, LINUX-1, ECO-1, L10N-1, COLLAB-1 |
| AX (2.0) | Accessibility Agents / axe-core engine — deferred to QUILL 2.0 | 6 | 0 | 6 | AX-A..F |
| PKG (2.0) | Packaging / freezing evaluation — deferred to QUILL 2.0 | 1 | 0 | 1 | PKG-1 |
| EDS | Power Tools feature parity — delivered in QUILL 1.0 | 21 | 21 | 0 | (complete) |
| **2.0 subtotal** | BITS Whisperer + axe-core + GLOW watch action (power-tool delivered; GLOW engine now in 1.0) | **57** | **21** | **36** | |
| **Total** | All tiers (1.0 + 2.0) | **213** | **135** | **78** | |

> Deferral note (2026-06-02): per maintainer direction, the GLOW accessibility
> engine (Tier 3, including the WATCH-8 GLOW watch action), the BITS Whisperer
> transcription suite (Tier 5, including the WATCH-9 transcribe watch action), and
> the Accessibility Agents / axe-core workstream (AX-A through AX-F) are all moved
> out of the 1.0 milestone and into **QUILL 2.0**. The Done/Remaining columns were
> reconciled to the per-tier sums (the previous Total of 55/125 did not match the
> rows); going forward the totals are internally consistent. QUILL 1.0 ships when
> the 1.0 subtotal reaches zero remaining.
>
> Scope move (2026-06-03): per maintainer direction, the GLOW accessibility
> engine family (**GLOW-1 through GLOW-7**) returns from QUILL 2.0 into the **1.0**
> milestone now that the shared `quill-glow-core` engine requirements are met (the
> engine is green). The seven items are classified under **Tier 2** (the flagship
> experience) and sequenced for execution **after Tier 4**. Only these seven move:
> the GLOW watch-action binding (**WATCH-8**) and the axe-core / Accessibility
> Agents workstream (**AX-A through AX-F**) stay in 2.0. The grand Total is
> unchanged (the seven items relocate between milestones); the 1.0 subtotal rises
> by seven and the 2.0 subtotal falls by seven.

#### Feature status by tier (the two living lists)

These two tables are the at-a-glance companion to the per-area item tables above:
every feature in the 1.0 scope appears in exactly one of them, grouped by tier.
When an item closes, move its ID from **Work in progress** to **Completed** in the
same change, so both lists stay a truthful snapshot. The canonical per-item detail
(acceptance text and evidence) always lives in the per-area tables higher up; these
two are the watch lists. Items deferred to QUILL 2.0 (BITS Whisperer, axe-core,
and the GLOW watch action) are tracked separately in the third table and are not
part of either 1.0 list. The GLOW engine family (GLOW-1..7) is in the 1.0 lists
under Tier 2.

**Work in progress (QUILL 1.0 — open items)**

| Tier | Status | Feature IDs |
| --- | --- | --- |
| Tier 2 — Flagship | In progress | AI-19, SHELL-2, SHELL-3, GLOW-1, GLOW-2, GLOW-3, GLOW-4, GLOW-5, GLOW-7 (GLOW family sequenced after Tier 4) |
| Tier 6 — Documentation | In progress / Todo | DLG-3.8 (SR sign-off, maintainer), DOC-1, DOC-2, DOC-3, DOC-4, DOC-5, DOC-6, DOC-7, DOC-8, DOC-11, DOC-12, DOC-14, DOC-15, DOC-16, DOC-17, DOC-18, POD-1, POD-2, POD-3, POD-4, POD-5, TUT-1, TUT-2, TUT-3, TUT-4, TUT-5, TUT-6, TUT-7, CQ-11, CQ-23, CQ-24, LINUX-2 |

**Completed (QUILL 1.0 — Done)**

| Tier | Feature IDs |
| --- | --- |
| Tier 1 — Protect users | BUG-1, BUG-2, BUG-3, BUG-4, BUG-5, BUG-6, BUG-7, SEC-1, SEC-10, SEC-11, SEC-13, GATE-1, GATE-2, GATE-3, GATE-4, GATE-5, GATE-6, GATE-7, GATE-8, GATE-9, FLAG-1, FLAG-2 |
| Tier 2 — Flagship | QK-1, QK-2, QK-3, QK-4, QK-5, QK-9, NAV-1, NAV-4, NAV-5, AI-1, AI-6, AI-7, AI-13, AI-14, AI-15, AI-16, AI-17, AI-21, AI-23, WATCH-1, WATCH-2, WATCH-3, WATCH-4, WATCH-5, WATCH-6, WATCH-7, SET-1, SET-4, SET-5, SET-6, SET-7, SHARE-1, SHARE-2, SHARE-3, FLAG-3, FLAG-4, MENU-3, MENU-1, MENU-5, DICT-1, CTX-1, DICT-2, FEAT-19, DLG-1, OCR-1, OCR-2, OCR-3, OCR-4, OCR-5, A11Y-4, SET-2, SET-3, AGENT-1, SHELL-1, GLOW-6 |
| Tier 4 — Structural health | CQ-7, CQ-12, CQ-13, CQ-14, CQ-15, CQ-16, CQ-17, CQ-18, CQ-19, CQ-20, CQ-21, CQ-22, GATE-10, GATE-11, PERF-1, PERF-2, PERF-3, PERF-8, PERF-9, PERF-10, PERF-11, PERF-12, PERF-13, PERF-14, SEC-4, SEC-6, SEC-7, SEC-8, SEC-14, SEC-15, SEC-16, SEC-17, TYPE-1, TYPE-2, TYPE-3, TYPE-4, TYPE-5, TYPE-6, TYPE-7, TYPE-8, CQ-1, DLG-2, DLG-3, ORG-1 |
| power-tool (delivered in 1.0) | EDS-1, EDS-2, EDS-3, EDS-4, EDS-5, EDS-6, EDS-7, EDS-8, EDS-9, EDS-10, EDS-11, EDS-12, EDS-13, EDS-14, EDS-15, EDS-16, EDS-17, EDS-18, EDS-19, EDS-20, EDS-21 |

**Deferred to QUILL 2.0 (not in the 1.0 lists)**

| Workstream | Feature IDs | Why deferred |
| --- | --- | --- |
| GLOW watch action (Tier 3) | WATCH-8 | The GLOW engine (GLOW-1..7) moved into QUILL 1.0 (Tier 2, sequenced after Tier 4) now that the shared `quill-glow-core` engine is green; the Watch Profile binding stays a 2.0 follow-on. |
| BITS Whisperer transcription (Tier 5) | BW-1, BW-2, BW-3, BW-4, BW-5, BW-6, BW-7, BW-8, BW-9, BW-10, WATCH-9 | The second distinctive engine; a clean 2.0 integration after the 1.0 flagship ships. |
| Accessibility Agents / axe-core (AX) | AX-A, AX-B, AX-C, AX-D, AX-E, AX-F | Builds on the GLOW engine and report surface; stays a 2.0 workstream per maintainer direction even though the GLOW engine itself is now in 1.0. |
| Tier 5 stretch explorations | NAV-10, AI-11, AI-12, AI-18, FEAT-12, FEAT-13, FEAT-14, FEAT-15, FEAT-16, FEAT-17, FEAT-18, LINUX-1, ECO-1, L10N-1, COLLAB-1 | Post-1.0 breadth, chosen with beta feedback in 2.0. |
| Competitive parity plan (Notepad++ benchmark) | COMP-1, COMP-2, COMP-3, COMP-4, COMP-5, COMP-6, COMP-7 | Closes high-value project workflow gaps (search, workspace, plugin lifecycle, encoding conversion, macros, split review) plus an optional GitHub Copilot SDK cloud provider, while preserving QUILL's screen-reader-first and explicit-consent architecture. |

Completed outside the formal tier lists (cross-cutting protections and quality work that the tiers reference only by theme): SEC-2 (path-escape guard for persistence writes), SEC-3 (OCR language allowlist), SEC-4 (documented and validated cwd safety for safe_subprocess), SEC-5 (verified TLS everywhere), GATE-1 (pre-commit), PERF-8 (documented scoped type-check), CQ-17 (thread-safety invariants note), and A11Y-1 (announcement grammar). The GATE-3/CQ-7 cleanup also incidentally cleared the `quill/core` and `quill/io` portion of the TYPE-1..8 zone, though those formal rows stay open until each is individually verified and closed.

#### 2026-06-12: ORG-1 closed — source-tree reorganization and repo-wide Markdown health

ORG-1 (the last open Tier 4 code item) is **Done**. The full source-tree
organizational review landed as a sequence of mechanical, behavior-preserving
moves with every gate green:

- **Platform files relocated.** `macos_app.py` → `quill/platform/macos/macos_app.py`
  (a thin `from quill.__main__ import main` re-export behind the existing
  `quill/platform/*` contract, mirroring `quill/platform/windows/*`) and
  `setup_macos.py` → `scripts/setup_macos.py`. `pyproject.toml` and
  `scripts/build_macos.sh` were repathed in the same change, and
  `docs/engineering/macos-build.{md,html,epub}` documents the new layout.
- **Root design docs consolidated.** `aa`, `glow`, `pi`, and the project hub
  `ROADMAP` (`.md` plus regenerated `.html`/`.epub`) moved into `docs/planning/`.
  All 55 internal relative links in `ROADMAP.md` and every external reference (the
  copilot instructions, the blocked-items and dialog-estate engineering docs, and
  the structure guard) were repointed in step; the docs-artifact gate stays green.
- **Single ignored-output convention.** `build/`, `release-dist-*`,
  `installer-smoke*`, `windows-distribution`, and `release-artifacts*` are all
  covered by `.gitignore` with **zero tracked files** — no dead or duplicated
  tracked scratch artifacts remain.
- **Repo-wide Markdown health.** A new root `.markdownlint-cli2.jsonc` (read by
  both `markdownlint-cli2` and the VS Code Problems pane) plus a full cleanup
  brings every tracked `.md` to **0 lint errors**: MD040 fenced-code languages,
  MD049/MD050 emphasis style, MD056 table-column counts, MD010 hard tabs,
  MD005/MD007 list indentation, MD022/MD025/MD028/MD032 spacing, and MD012/MD047
  trailing-newline fixes across the PRD, scripting, accessibility, and QA docs and
  the contributor instructions. A `--fix` prose-corruption hazard was caught and
  reverted (a wrapped `+` conjunction misread as a list bullet). The 10 workflow
  files were reviewed; no references to moved paths exist.
- **Mechanical guard.** `tests/unit/structure/test_repo_layout.py` enforces the
  sanctioned layout (no loose root Python, the limited root-Markdown allowlist, the
  relocated planning-doc triples, the macOS file homes) so the tree cannot drift.

- **Counts:** ORG-1 closes, moving **Tier 4 to 32 of 32 done (0 remaining)** —
  Tier 4 is now complete. The QUILL 1.0 scope moves to **115 of 157 done (42
  remaining)** and the overall total to **134 of 213**.

#### 2026-06-11: "Send to Quill" classic Explorer menu made drift-proof — installer/registry sync guarded (issue #114)

The classic Windows Explorer "Send to Quill" context-menu integration
(issue #114) is code-complete and now durably guarded against silent drift. The shipped
path is end-to-end: the single core verb registry (`quill/core/shell_verbs.py`)
drives the runtime registry writer, the CLI `--action` flag, the Settings
toggles, and the Inno Setup installer's `[Registry]` verb entries — all four
verbs (Open, OCR, OCR-structured, Read aloud) across every supported extension,
opt-in via the `shellverbs` task and `uninsdeletekey`-clean on uninstall. Verbs
reach a running instance over single-instance IPC and are keyboard-reachable via
Shift+F10 / "Show more options".

- **New guard:** `test_committed_installer_iss_is_in_sync_with_generator` reads
  the committed `installer/quill.iss`, extracts its declared `AppVersion`,
  regenerates with `build_inno_setup_script(version)`, and asserts the committed
  file is byte-identical to the generator output. Because `installer/quill.iss`
  carries a "Generated by ...; Edit `build_inno_setup_script()`, not this file"
  header, any change to the generator (a new shell verb or extension) without
  regenerating the committed installer now fails CI — the shipped Explorer menu
  can never silently diverge from the single core verb registry.
- **Validated:** ruff format/check clean; all 12 `test_build_windows_distribution`
  tests pass (including the new guard) and all 16 `test_shell_verbs` +
  `test_shell_integration` tests pass; the committed installer is confirmed in
  sync with the generator at version 0.1.5.
- **Honest remainder for #114:** the only outstanding work is the one-time live
  Windows install → right-click `.png`/`.pdf` → run → uninstall smoke (a manual
  release-time verification, not a code gap), and the Windows 11 *primary*-menu
  `IExplorerCommand` sparse-package, which remains descoped to QUILL 2.0 (the OS
  gates it behind compiled COM + package identity). The classic menu — the
  shipped, accessible, tested integration — is the workable 1.0 scope.
- **Counts:** unchanged — this hardens an existing in-progress item; SHELL-3's
  formal closure still awaits the manual Windows smoke and the 2.0 modern-menu
  work.

#### 2026-06-11: Bug fix — Keymap Editor dialog (issue #119) restored

The Keymap Editor (`Tools → Keymap Editor…`) regressed: the command list showed
empty and the OK button could not dismiss the dialog (users had to kill the
process). Root cause was a parent-ownership mismatch in `open_keymap_editor`: the
controls were parented to an inner `wx.Panel`, but the OK button created by
`dialog.CreateButtonSizer(...)` (a child of the dialog, not the panel) was added
to the *panel's* sizer. That mixed sizer tree mislaid the OK button — leaving it
non-functional — and the broken `SetSizerAndFit` collapsed the list.

- **Fix:** every control is now parented directly to the dialog and laid out in a
  single sizer, matching the proven `_choose_searchable_option` pattern. The OK
  button (`SetDefault`), `apply_modal_ids`, and `_show_modal_dialog` wiring are
  unchanged, so the dialog keeps its explicit default/escape and accessible
  announce path. No behavior change to the binding-edit flow or persistence.
- **Guard:** `tests/unit/ui/test_keymap_editor_contract.py` now asserts the
  controls are dialog-parented (`wx.ListBox(dialog`, `wx.Button(dialog`,
  `dialog.SetSizer(root)`) and that no inner `wx.Panel(dialog)` returns.
- **Validated:** ruff format/check clean; the keymap-editor contract test, the
  DLG-3 `dialog_inventory` snapshot (unchanged — the panel was never a dialog
  surface; 154 surfaces, classification unchanged), the dialog-contract guard,
  and the A11Y-4 banned-pattern gate all pass.
- **Counts:** unchanged — this is a defect fix, not a tier-item closure.

#### 2026-06-11: DLG-3 and DLG-2 close (code complete); final-QA test plan written; SR sign-off relocated to Tier 6 (DLG-3.8)

The dialog-estate code program reached genuine Done, and the residual manual screen-reader sign-off was given a real home and a real script.

- **Final-QA test plan written:** `docs/qa/final-qa-test-plan.md` (with paired `.html`/`.epub`) is the authoritative manual and exploratory plan for the 1.0 release — environments, entry/exit criteria, a severity model, evidence capture, the full dialog-estate SR matrix (NVDA full / JAWS spot / Narrator sanity, keyed to `dialogs.md` sections A–X), and the keyboard, file-lifecycle, AI/consent, OCR, startup/recovery, read-aloud, installer, performance, high-contrast, and localization passes.
- **DLG-3 closed (Done):** every code-level phase (DLG-3.0–DLG-3.7 plus the DLG-3.T triage) is Done and machine-guarded; the dialog inventory, hardening contract, web-surface governance, and startup hardening guards all hold. The one residual item — the manual NVDA/JAWS/Narrator pass — is not code; it is relocated, not fabricated.
- **DLG-2 closed (Done):** all interactive AI/assistant tool dialogs meet the modal/focus/async contract (pinned by `test_ai_tool_dialog_async_contract.py`); its SR verification folds into DLG-3.8.
- **DLG-3.8 relocated to Tier 6:** the manual SR pass is now a standalone Tier 6 final-QA item, owned by the maintainer and executed against the new test plan. It honestly stays open (it needs a live Windows screen-reader runtime and human listening) and aggregates the SR sign-off for DLG-2 and DLG-3.6.
- **Tooling fixed:** `scripts/check_docs_artifacts.py` now recurses the whole `docs/**` tree (previously only direct `docs/*.md` children were checked), so docs in subfolders like `docs/qa/` are held to the same HTML/EPUB parity convention.
- **Counts:** Tier 4 moves to **31 of 32 done (1 remaining: ORG-1)**; Tier 6 gains DLG-3.8 to **35 total, 3 done, 32 remaining**; the QUILL 1.0 scope is **114 of 157 done (43 remaining)**; the overall total is **133 of 213**.

#### 2026-06-11: CQ-1 complete — main_frame decomposed into eight cohesive mixins, behavior preserved

The `main_frame.py` monolith decomposition reached genuine Done. The final two named clusters were extracted verbatim into dedicated mixins, completing the eight-seam program with no behavior change.

- **Seventh seam (selection/marks):** the structural-selection and temporary-jump mark-ring cluster (line/paragraph/block selection, `expand_selection`/`shrink_selection`, `_has_active_selection`, `_selection_action_specs`, the public `quill_key_selection_actions`, the `select_to_*` family, and the `set_mark`/`pop_mark`/`exchange_point_and_mark`/`list_marks` ring, ~223 lines) moved into `quill/ui/main_frame_selection.py` as `SelectionMarksMixin`. The bookmark trio stayed in `main_frame.py` to avoid a `_NavigatorNode` circular import. GATE-6 surface and the DLG-3 `dialog_inventory.json` snapshot regenerated (the `wx.SingleChoiceDialog` re-keyed module, stays `native`; 154 totals unchanged).
- **Eighth seam (menu construction):** the full `_build_menu` method (~2,384 lines, the single largest method) moved into `quill/ui/main_frame_menu.py` as `MenuBuilderMixin`; an AST analysis confirmed zero free module-level references. The 2,398-line module got an explicit acknowledged GATE-11 budget entry (a new entry, not a raised one). Nine source-contract tests that scanned `main_frame.py` for menu-wiring text were updated to read both `main_frame.py` and `main_frame_menu.py`.
- `main_frame.py` dropped 21,637→21,412 (selection) →19,029 (menu); both budgets ratcheted down. All eight clusters (browse-mode, AI actions, status bar, image capture, QUILL key/Quick Nav, file/session lifecycle, selection/marks, menu construction) are now dedicated mixins.
- **Verified live on Windows:** the full 352-test UI suite (green before and after), GATE-11, GATE-6 public-surface, the dialog-contract/inventory gates, and the A11Y-4 banned-pattern gate all pass. CQ-1's acceptance (split into mixins, no behavior change, characterization tests pass before and after) is genuinely met.
- **Counts:** CQ-1 closes, moving Tier 4 to **29 of 32 done (3 remaining: DLG-3, DLG-2, ORG-1)**, the QUILL 1.0 scope to **112 of 156 done (44 remaining)**, and the overall total to **131 of 212**.

#### 2026-06-04: DLG-3 triage settled (0 convert / 48 harden / 1 keep-web); Phase 3 contract hardening complete

The 49 `hardened_custom` dialogs were triaged on the live wx 4.2.5 Windows runtime. A source scan for custom-drawn paint code (`EVT_PAINT`/`wx.lib.agw`/`OnPaint`/`wx.PaintDC`/owner-draw/`wx.html2`) returned **zero** hits, confirming every surface is already a stock-widget `wx.Dialog`. Disposition: **0 convert, 48 harden, 1 keep-web** (`AskQuillChatDialog`).

- **Phase 2 (DLG-3.2) closed as no-applicable-work:** no dialog is a lossless one-shot — flattening any of them into a stock `wx.MessageDialog`/`wx.SingleChoiceDialog`/`wx.TextEntryDialog` would drop live search, lists, previews, or multi-action rows. Honest "Done (no applicable work)," not a fabricated conversion.
- **Phase 3 (DLG-3.3) Done:** a machine-derived AST audit found 5 surfaces off the shared `dialog_contract`. Four were wired onto `apply_modal_ids` (and routed direct `ShowModal()` through the announcing `_show_modal_dialog`, with deterministic initial focus): `_present_quill_key_help`, `_offer_crash_recovery`, `_present_quick_nav`, `_choose_searchable_option`. The fifth, `show_watch_folder_status`, is a correctly-hardened modeless monitor. All 49 now pass a new durable guard.
- **New anti-regression control:** `tests/unit/ui/test_dialog_hardening_contract.py` AST-asserts every `hardened_custom` surface in the inventory snapshot wires the contract, so a future bespoke dialog that skips `apply_modal_ids`/show fails CI at author time.
- **Report:** `docs/engineering/dialog-estate-report.md` captures the full triage table, per-phase status, and honest remaining work (Phases 4–8).

#### 2026-06-03: DLG-3 plan folded into the PRD; per-phase tracking ledger added

The full dialog-estate plan (previously the `zfix.md` working file) was merged into the PRD as **§9.13 Dialog estate governance (DLG-3)** so the thinking is canonical and survives the scratch-file deletion. The PRD section captures the surface policy, source-of-truth inventory, per-dialog interaction contract, control-surface completeness, the "every dialog touched" definition, high-risk clusters, the eight execution waves, the dialog-by-dialog coverage map, the definitive conversion decisions, the operational/enforcement mandates, anti-regression controls, and the definition of done.

- **golden.md tracking:** DLG-3 is now decomposed into individually-tracked sub-items DLG-3.0 through DLG-3.8 (plus DLG-3.T triage) so each phase shows discrete progress. Phases 0–1 (the enforcement engine), the triage, Phase 2 (no applicable work), Phase 3 (contract hardening), Phase 4 (web-surface governance guard), Phase 5 (startup/onboarding hardening guard), and Phase 7 (dialog-launch characterization) are Done; Phase 6 (assistant/AI consolidation) and Phase 8 (manual SR pass, needs a live Windows screen-reader runtime) remain. DLG-3 stays honestly "In progress" until those two close.
- **Working files retired:** `zfix.md`/`zfix.html` deleted now that their content lives in the PRD.
- **Live runtime confirmed:** this Windows machine has wxPython 4.2.5 (msw/Phoenix, wxWidgets 3.2.9), so the conversion waves are verified by instantiating real dialogs, not source-contract-only. A source scan confirmed **zero** custom-drawn dialogs exist — every `hardened_custom` surface is a `wx.Dialog` composed of stock native controls, so the work is triage-and-convert/harden, not a from-scratch rewrite.

#### 2026-06-03: Repository cleanup — editor history untracked, working files ignored, stale engineering docs retired

A no-risk housekeeping pass got the tree to a genuinely clean state.

- **Editor history untracked and ignored:** the VS Code Local History extension's `.history/` tree (119 tracked files) was removed from version control with `git rm -r --cached` (kept on disk) and added to `.gitignore`; the malformed first line of `.gitignore` (`,__pycache__/`) was corrected to `__pycache__/`.
- **Working/scratch files ignored:** `zfix*` (the in-flight `zfix*.md`/`.html` working files, four of which were tracked) were untracked and added to `.gitignore`, and the stray empty `Status` file was removed and ignored. `git status` is now clean with no stray untracked files.
- **Stale engineering docs retired (DOC-18, scoped):** the nine PRD-duplicating engineering documents and their `.html`/`.epub` artifacts were deleted; their content already lives in the PRD. The three references that would have broken were fixed (`SECURITY.md`, `docs/site/index.html`, `github-pages.yml`), and CONTRIBUTING.md absorbed a self-contained architecture overview. The five actively-wired references (`macos-build`, `security-advisory-workflow`, `thread-safety`, `acr-vpat`, `announcement-style-guide`) were intentionally retained, so every remaining golden.md evidence link stays valid. DOC-18 advances to In progress (folding the five retained refs into the PRD is deferred).

#### 2026-06-03: DLG-3 dialog estate made source-of-truth and machine-gated (enforcement engine landed)

The flagship Tier 4 dialog refactor's enforcement engine (PRD §9.13 Phase 0 + Phase 1) shipped: QUILL's dialog estate is now generated from source and gated, so no dialog can ship unregistered, unclassified, or on a bespoke surface.

- **Authoritative registry from source:** `quill/tools/dialog_inventory.py` AST-scans all of `quill/**/*.py` and records every dialog *surface* — each `wx.Dialog(...)`, every stock wx dialog (`wx.MessageDialog`/`RichMessageDialog`/`MessageBox`/choosers/text/file/dir pickers/progress/about), and every `show_web_form(...)` call — under a stable, line-independent key (`<module>::<enclosing_qualname>::<kind>`, with `#n` for repeats) and its sanctioned classification. The first scan inventoried **154** surfaces (**100** `native`, **49** `hardened_custom`, **5** `web`), committed to `tests/unit/ui/fixtures/dialog_inventory.json`.
- **Two gates make it un-regressable:** `tests/unit/ui/test_dialog_inventory.py` (four tests) fails on any new/moved/removed/reclassified dialog or unsanctioned surface, and a new `_check_dialog_registry` cross-check inside the GATE-4 A11Y-4 banned-pattern gate (`quill/tools/check_banned_patterns.py`, run in Security CI) fails the build on any unregistered or misclassified dialog. Adding a dialog now *forces* a deliberate `python -m quill.tools.dialog_inventory --write`, whose classification is reviewed in the diff — the "magical" gating the plan asked for.
- **Instructions hardened:** `.github/copilot-instructions.md` gained a "Dialog Excellence Mandates" block (seven non-negotiable rules) and a Dialog Change Checklist, plus the source-of-truth rule that a scan/registry disagreement means the work is incomplete.
- ruff + strict mypy clean on the new/changed tools; the banned-pattern gate reports no violations; 16 dialog-gate tests pass.
- **Honest remainder:** this is the enforcement engine only. The per-dialog conversion waves (PRD §9.13 Phases 2–8 — simple→native, enhanced-native standardization, web standardization, startup/onboarding hardening, assistant/AI consolidation), CQ-16 characterization expansion, and the manual NVDA/JAWS/Narrator pass across `dialogs.md` require a live Windows screen-reader runtime and are **not** done, so DLG-3 moves Todo → **In progress** (not Done). Tier 4 counts are unchanged (DLG-3 stays in the not-done bucket).

#### 2026-06-03: "Send to Quill" shell verbs landed (SHELL-1 Done) and the structured-OCR pass wired (SHELL-2 advanced)

A new file-manager / in-app / CLI verb system shipped, and the AI structuring pass for the structured-OCR verb was built and tested up to its live-key boundary.

- **SHELL-1 (Done):** a wx-free, platform-free verb registry (`quill/core/shell_verbs.py`) is the single source of truth for the Open, OCR, OCR-structured, and Read-aloud "Send to Quill" actions. The verbs flow end to end on Windows: the single-instance IPC queue carries an `action` field, a new `--action` CLI flag (validated against the registry) reaches a running instance, a new **Integration and Context Menu** settings group drives which verbs appear, the Windows shell-integration plan registers verbs under `SystemFileAssociations\<ext>\shell\Quill.<verb>` without owning the file association, and `MainFrame._handle_shell_request` dispatches open/ocr/read at both first-launch and live IPC. Covered by core tests (`test_shell_verbs.py`, IPC, settings, registry) and context-menu plan tests; ruff + strict mypy clean.
- **SHELL-2 (advanced, still In progress):** the assistant gained a `structure` operation that reflows raw OCR text into clean Markdown (joining scan-broken lines, grouping paragraphs, inferring headings/lists/tables) while forbidding summarizing or inventing content; `_run_ocr_on_path` gained a `structured` flag and runs the recognized text through `_apply_ocr_structuring` inside the existing OCR worker thread, structuring via the assistant when available and degrading safely to plain OCR with a status note otherwise. Covered by `test_structure_operation.py` and source-contract tests. The honest remainder is live-key end-to-end verification and structuring-quality tuning on real-world OCR output.
- **SHELL-3 (advanced, still In progress):** the Inno Setup installer now registers the "Send to Quill" file right-click verbs, generated directly from the core registry by `build_shell_verb_registry_lines()` so the installer menu can never drift from the in-app menu, the CLI `--action` map, or the Settings toggles. Each verb is written per extension under `HKCU\Software\Classes\SystemFileAssociations\<ext>\shell\Quill.<verb_id>` with a `"{app}\run-quill.cmd" --action <action> "%1"` command, gated behind a new opt-in `shellverbs` task and tagged `uninsdeletekey`; the committed `installer/quill.iss` was regenerated. Covered by six new contract tests in `test_build_windows_distribution.py`. The honest remainder is one live install → right-click → run → uninstall verification pass (Inno Setup must be installed). The Windows 11 *primary*-menu `IExplorerCommand` sparse-package is descoped to QUILL 2.0 (the OS gates it behind compiled COM + package identity). Tracks intake #113/#114/#116; macOS Finder (#115) stays blocked on the macOS port (#42).
- Counts: SHELL-1 closes; SHELL-2 and SHELL-3 join AI-19 as the open Tier 2 items, moving Tier 2 to **57 of 60 done (3 remaining: AI-19, SHELL-2, SHELL-3)**.

#### 2026-06-10: Tier 2 flagship closed to a single honest blocker — SET-2, SET-3, and AGENT-1 landed Done

Three Tier 2 rows closed end to end on the Windows dev box, leaving AI-19 as the only honest remaining flagship item (a live provider device-login endpoint that cannot ship from this environment).

- **SET-3 (Done):** `announce_punctuation_level` (none/some/most/all) now drives engine-independent punctuation verbalization in the new wx-free `quill/core/punctuation_speech.py`, applied to every Read Aloud sentence before it reaches any TTS engine (pyttsx3, DECTalk, eSpeak, and the shared WAV path for piper/kokoro/openvoice). Rather than wait on a per-engine punctuation parameter the current TTS set never exposed, QUILL substitutes spoken symbol names itself, so the setting behaves identically across all backends; contractions are preserved (the apostrophe is never spoken) and levels are cumulative. `quill/core/sentence_split.py` was extracted from `read_aloud.py` to keep that module within its GATE-11 budget. Covered by `test_punctuation_speech.py`, `test_sentence_split.py`, and a Read Aloud controller test.
- **SET-2 (Done):** the exploratory `dictation_sensitivity` field was **dropped** rather than shipped inert. The dictation path launches the Windows Win+H recognizer, which exposes no sensitivity control, so a stored-but-no-op slider would have misled users. The field is removed from `settings.py` and `settings_registry.py`; any legacy `dictation_sensitivity` key in a saved settings file is ignored on load. A real sensitivity parameter belongs with a future live-mic capture backend on the dictation roadmap, not as a no-op pacing control. Every other timing/pacing setting in the row has a live consumer, so SET-2 is genuinely complete.
- **AGENT-1 (Done) and renamed to "Accessibility Tune-Up":** the deterministic, consented, single-undo accessibility fixer was renamed across its entire user-facing surface (menu, dialog title, announcements, report tabs) to differentiate it from the conversational "Accessibility Agent" assistant persona and from the broader 2.0 "Accessibility Agents" (MCP) ecosystem. The internal command id `tools.ai_accessibility_agent`, the `quill/core/accessibility_agent.py` module, and the `AccessibilityAgentDialog` class are unchanged to avoid churn. Structure and plain language are auto-fixed; alt-text and link-text steps stay advisory-only by design (flagged for human authoring, not auto-written) — a deliberate product decision, not a blocker. Verified by `test_accessibility_agent.py` and `test_assistant_tools_dialog_callbacks.py`; `dialogs.md` updated to the new menu path.
- All changed `quill/core` files stay wx-free and strict-mypy-clean; ruff is green; GATE-11 module budgets hold.
- Counts: SET-2, SET-3, and AGENT-1 close, moving Tier 2 to **56 of 57 done (1 remaining: AI-19)**, the QUILL 1.0 scope to **94 of 143 done (49 remaining)**, and the overall total to **94 of 206**.

#### 2026-06-10: Native Windows OCR verified end to end — OCR-1 landed Done

Run on a real Windows 11 box with the bundled `winsdk` wheel installed, the native `Windows.Media.Ocr` backend was verified recognizing text for the first time, closing the last honest blocker on OCR-1.

- **OCR-1 (Done):** `available_engines()` reports `['windows']` once `winsdk` is present, and `ocr_image(path, engine="windows")` recognized a generated test image (`Hello QUILL OCR` / `Native Windows engine`) verbatim through the live WinRT engine — fully offline, no Tesseract. The packaging chain that makes this zero-install for end users is real and in place: `winsdk` is declared in `pyproject.toml`'s `ocr` extra under `sys_platform == 'win32'`, and `scripts/build_windows_distribution.py` bundles the `ocr` group by default (`("ui", "spellcheck", "ocr")`). The WinRT OCR engine itself is a built-in Windows component, so users install nothing.
- **Test hermeticity fix:** installing `winsdk` locally exposed a latent isolation bug — five Tesseract-path tests in `tests/unit/io/test_ocr.py` passed only because winsdk was absent (so `auto` fell back to Tesseract). They now pin `engine=ENGINE_TESSERACT`, so the OCR suite (35 tests) is green whether or not the native backend is installed.
- **Still honestly open:** SET-2 (no sensitivity-aware dictation backend; Win+H exposes no such control) and AI-19 (needs a live provider device-login endpoint) remain genuinely blocked even on Windows.
- Counts: OCR-1 closes, moving Tier 2 to **52 of 57 done (5 remaining)**, the QUILL 1.0 scope to **90 of 143 done (53 remaining)**, and the overall total to **90 of 185**.

#### 2026-06-10: Structural health — A11Y-4 and GATE-11 closed Done; CQ-1 first seam extracted

Three Tier 2/Tier 4 structural items advanced, two to **Done** and the big decomposition to a genuine **In progress** with its first real seam landed.

- **A11Y-4 (Done, Tier 2):** the dialog-construction contract is now machine-enforced. `quill/tools/check_banned_patterns.py` gained AST checks (`_check_dialog_contract`, `_check_raw_xml`) that flag the `EXPAND`/outer-sizer/default-button/`Destroy` bug class behind the find-in-files Cancel trap (#84) and the bookmark dialogs (#85), so the contract is un-regressable by construction rather than by review.
- **GATE-11 (Done, Tier 4):** a ratcheting module-size budget gate (`quill/tools/module_size_budget.py` + `module_size_budgets.json`, eight tests) caps every module at 600 lines unless it carries an explicit, acknowledged budget that may only **decrease**. This instruments the CQ-1 decomposition: as code leaves `main_frame.py`, its budget ratchets down and can never silently regrow.
- **CQ-1 (In progress, Tier 4 — first seam):** the real decomposition began. The 25-method browse-mode navigation cluster (~455 lines) was extracted verbatim from `main_frame.py` into `quill/ui/main_frame_browse.py` as `BrowseModeMixin`, which `MainFrame` now inherits; every call resolves identically through the MRO, so behavior is unchanged. `main_frame.py` dropped from 23,332 to 22,877 lines (the GATE-11 budget ratcheted with it); the mixin is 487 lines, under the 600 cap. Proven behavior-identical by the existing main_frame UI suite (274 passing; one pre-existing, unrelated `web_form` test-stub failure) and the unchanged public-surface characterization fixture — all moved methods are private. This establishes the mixin pattern for the remaining clusters (menu construction, QUILL key/Quick Nav, selection/marks, file/session lifecycle, status bar, AI actions), so CQ-1 stays honestly **In progress** (XL) rather than Done.
- Counts: A11Y-4 was already reconciled to Tier 2 Done; GATE-11 closes, moving Tier 4 to **12 of 30 done (18 remaining)**, the QUILL 1.0 scope to **89 of 143 done (54 remaining)**, and the overall total to **89 of 185**.

#### 2026-06-10: OCR capture sources completed end to end — OCR-3 landed Done

On the same real Windows box that verified OCR-1, the two missing capture sources were built, wired, and validated, closing OCR-3.

- **OCR-3 (Done, Tier 2):** clipboard-image and screen capture now join file capture as first-class OCR sources. `ocr_clipboard_image` grabs the current clipboard image and `ocr_screen_capture` grabs the whole screen or the active window (chosen via a stock `wx.SingleChoiceDialog`); both use the wx-free `quill/platform/windows/screen_capture.py` helper (PIL `ImageGrab` + `win32gui`) and funnel through the same shared `_run_ocr_on_path` pipeline (off-thread OCR, `wx.ProgressDialog`, `OcrReviewDialog` with Insert/Copy/Discard, focus returned to the editor) as file capture. Empty-clipboard and capture-failure cases are handled gracefully rather than crashing. Both commands are registered (`tools.ocr_clipboard`, `tools.ocr_screen`), gated by matching `core.features` entries, menued, id-ref'd, and event-bound. Verified on Windows with the live `Windows.Media.Ocr` engine.
- **Decomposition (CQ-1/GATE-11):** to land OCR-3 without growing oversized modules, the image-capture cluster was extracted from `main_frame.py` into `quill/ui/main_frame_image.py` as `ImageCaptureMixin`; the AI image-description body builder moved to `quill/core/ai/vision.py`; the command→feature map moved to its own module; and the assistant provider catalog (`ModelRecommendation` plus the seven `*_for_provider`/`provider_*` helpers) was extracted to `quill/core/ai/providers.py` and re-exported from `assistant_ai.py`, bringing that module back under its GATE-11 budget. All four modules pass GATE-11.
- **Quality gates:** ruff format/check clean and strict mypy "Success" on the changed `quill/core` files (`assistant_ai.py`, `ai/providers.py`, `ai/vision.py`); GATE-11 OK across all modules; the OCR review/contract suite plus the assistant_ai and AI-core suites are green (three new OCR-3 source-contract tests cover the methods, the Windows capture helper, and the MainFrame wiring).
- Counts: OCR-3 closes, moving Tier 2 to **53 of 57 done (4 remaining)**, the QUILL 1.0 scope to **91 of 143 done (52 remaining)**, and the overall total to **91 of 206**.

#### 2026-06-09: Sharing dialogs completed — SHARE-1 and SHARE-2 landed Done

The two Share/Restore dialogs moved from **In progress** to **Done** by wiring every declared shareable section through the offer/apply layer and behaviorally separating the two modes.

- **SHARE-1 (Done):** `gather_export_offers` (in the wx-free `quill/ui/share_dialogs.py`) now serializes **all eight shareable sections** — settings groups, features/profile, keymap, snippets, macros, watch profiles, personal dictionary, and writing-style models — and offers each only when its store actually holds content, so the export checklist reflects exactly what the user has. Keymap is offered only when bindings differ from the shipped defaults. `quill/core/snippets.py` gained `snippet_library_from_dict` so import parses a snippets payload through the identical validation path as a disk load.
- **SHARE-2 (Done):** `apply_import` derives **merge** for a `.quillprofile` and **replace** for a `.quillbackup`: profile merge overlays keymap, overlays snippets by id (incoming wins) and macros by name, adds watch profiles only when absent, and unions style samples; backup replace swaps each store wholesale. The personal dictionary stays additive in both modes because there is no public "forget all" word API (documented in `_apply_dictionary`). FLAG-1 is wired — when importing features auto-enables a dependency, each forced-on feature is announced as "Enabled X to satisfy a feature dependency."
- **Tests:** `tests/unit/ui/test_share_dialogs.py` grew to 11 tests, adding coverage for content-gated offers across the six new sections, a full backup round-trip that restores every store, additive profile merge for the keymap, and the FLAG-1 dependency announcement.
- The two wx dialogs (`open_share_export_dialog`, `open_share_import_dialog`) are unchanged structurally — they drive their checklists entirely from the helper layer, so the new sections appear automatically and the existing `dialogs.md` rows stay accurate.
- Quality gates: ruff format/check clean on the edited files, strict mypy clean on `quill/core/snippets.py` and the wx-free `quill/ui/share_dialogs.py`, and the `test_share_dialogs.py`, `test_snippets.py`, `test_macros.py`, and `test_share_package.py` suites pass.
- Counts: SHARE-1 and SHARE-2 close, moving Tier 2 to **41 of 58 done (17 remaining)** and the QUILL 1.0 scope to **78 of 144 done (66 remaining)**.

#### 2026-06-09: Settings tier closed out — SET-1, SET-4, and SET-7 landed Done

Three open Settings items moved to **Done**, leaving only the two genuinely runtime-blocked Settings rows (SET-2, SET-3) open in that area.

- **SET-1 (Done):** the tabbed `wx.Notebook` Settings dialog renders one page per registry group (general, editing, navigation, accessibility, read aloud, AI, transcription, watch folders, updates) from `settings_registry` specs. Every scalar setting in those areas is surfaced; collection-style customization (snippet bodies, recorded macros, sticky-note content, status-bar layout) is intentionally handled by its own dedicated accessible manager dialog rather than a scalar registry control, which matches the stated acceptance (the named groups, not those collections).
- **SET-4 (Done):** the last unwired toggle, `browse_mode_sticky`, now makes the QUILL key **N** browse entry lock until Escape (`_enter_quill_key_mode(sticky=...)`), joining the already-live `confirm_destructive_actions`, `default_new_document_format`, `default_export_preset`, `autoformat_smart_quotes`/`autoformat_dashes`, and `quick_nav_include_*` consumers. Covered by `test_prefix_then_n_honors_sticky_browse_default` (15 quill-key tests pass).
- **SET-7 (Done):** export to `.qsf`, import, and reset-to-factory all work; the same import path *is* the admin pre-configure mechanism. The optional admin schema write-up is tracked separately as DOC-7 in Tier 6 and is not part of this functional row.
- **Honestly still open:** SET-2 (`dictation_sensitivity` has no sensitivity-aware capture backend — Win+H exposes no control) and SET-3 (`announce_punctuation_level` has no Read Aloud consumer — the engines take no punctuation parameter) remain In progress with documented blockers.
- Counts: SET-1, SET-4, SET-7 close, moving Tier 2 to **39 of 58 done (19 remaining)** and the QUILL 1.0 scope to **76 of 144 done (68 remaining)**.

#### 2026-06-08: Trustworthy AI editing — AI-1, AI-6, AI-7, and AI-14 landed Done end to end

The four open AI-experience items moved from Todo to **Done**, delivering streaming, graceful degradation, and a reviewable-by-ear diff across `core` and the wxPython UI, honestly tested.

- **AI-14 / AI-1 (Done):** `generate_assistant_response_stream` in `quill/core/assistant_ai.py` parses each wired provider's streaming wire format (OpenAI/OpenRouter/custom/Azure and ollama_cloud chat-completions SSE, Claude content-block SSE, Gemini generateContent SSE, local Ollama NDJSON) into token deltas via `parse_stream_event` + `iter_stream_text`, reusing the AI-13 endpoint-security, verified-TLS, retry, and error taxonomy. `ProviderChatBackend.respond_stream` surfaces the deltas to the UI; a pre-stream failure degrades cleanly to the blocking path and a mid-stream failure raises without a duplicate, while the base `AIBackend.respond_stream` emits the full reply once as a fallback. The Ask Quill chat consumes the stream as throttled, accessible status announcements through the assertive aria-live region plus a single final transcript append — the external `AccessibleChatView` supports no in-place token mutation, so progress is *heard* without flooding the screen reader.
- **AI-6 (Done):** a wx-free `quill/core/ai/availability.py` is the single source of truth for AI readiness; `describe_availability(feature_name, ...)` returns a clear, announceable message that names the feature and distinguishes "AI is turned off", "a model is unavailable", and "a key is missing" (with a `needs_key` flag), and it never blocks the editor.
- **AI-7 (Done):** `quill/core/ai/diff_review.py` builds a navigable added/removed/changed diff via `SequenceMatcher`; each `DiffHunk` carries a screen-reader phrase and line-by-line detail (marking blank lines), and `DiffReview.apply(accepted)` honors a partial-accept set while keeping unchanged segments verbatim. The accessible `DiffReviewDialog` presents the hunks as a stock `wx.CheckListBox` (all pre-checked) with a read-only details pane and Apply Checked / Accept All / Reject All / Close; applying replaces the selection as **one undo step** and announces the count. It is reachable from Ask Quill chat — approving an AI "replace" whose text differs from the selection opens the review (`MainFrame.open_ai_diff_review`).
- Tests: `tests/unit/core/ai/test_streaming.py`, `test_streaming_backend.py`, `test_availability.py`, `test_diff_review.py`, and the `DiffReviewDialog` cases in `tests/unit/ui/test_assistant_tools_dialog_callbacks.py` (45 passed). Quality gates: ruff format/check clean on all touched files; strict mypy clean on the touched `quill/core` modules (`diff_review.py`, `availability.py`, `backend.py`, `provider_backend.py`, `assistant.py`, `assistant_ai.py`); the UI public-surface snapshot was refreshed for the new `open_ai_diff_review` method, and `dialogs.md` gained a row for the **Review AI Changes** dialog.
- Counts: AI-1, AI-6, AI-7, and AI-14 close, moving Tier 2 to **36 of 58 done (22 remaining)** and the QUILL 1.0 scope to **73 of 144 done (71 remaining)**.

#### 2026-06-06: Watch Profiles finished — WATCH-5, WATCH-6, and WATCH-7 landed Done end to end

The three open Watch Profiles items moved from In progress to **Done**, completing the accessible automation hub (a folder, an action, a queue) end to end across `core`, `io`, and the wxPython UI.

- **WATCH-5 (Done):** `quill/core/watch_profiles.py` gained per-profile `name_patterns` (fnmatch globs) and a schedule (`schedule_mode` of always, a daily active window, or a midnight-wrapping quiet-hours window, plus start/end minute-of-day), all normalized, validated (a zero-width window is rejected), and round-tripped through `to_dict`/`from_dict`; `profile_is_active(...)` gates the poll loop. The **Edit Watch Profile** dialog was rebuilt to expose the full surface — suffix and name-pattern comma lists, min-size and min-age spinners, a schedule-mode chooser with hour/minute spinners, per-action option controls (convert target, macro name, sandboxed Python code/suffix/timeout, AI mode), and a **Preview (dry run)** button — all stock-control, keyboard, and screen-reader navigable with announced validation. Parenting stays panel to panel-sizer to root per the dialog contract.
- **WATCH-6 (Done):** the per-profile AI consent control now shows the active provider/model and scope (`_watch_ai_consent_detail` reads the resolved model spec) before arming; the dry-run preview is surfaced via the editor's Preview button (`registry.dry_run(...)`, side-effect-free); and a resource-cap termination is announced distinctly — `_on_watch_queue_event` classifies a SEC-9 sandbox wall-clock kill ("Execution timed out") via `_watch_message_is_resource_cap` and announces "Watch stopped … it exceeded the time limit and was terminated to protect your machine" instead of a plain failure. The consent gate and atomic claim were already enforced in `core`.
- **WATCH-7 (Done):** `MainFrame` now supplies the real built-in action handlers the registry was awaiting — `_watch_convert_file` (Pandoc off the UI thread, writes the converted file), `_watch_run_macro` (marshals macro replay onto the UI thread), and `_watch_run_ai` (honors the AI on/off switch, writes a `.{mode}.md` sidecar so the editor is never overwritten) — wired into `WatchService` via `on_convert`/`on_run_macro`/`on_ai`. Open, Move, Copy, and sandboxed Python were already functional; the action set is now complete end to end.
- Tests: the core schedule/name-pattern and active-window behaviour is covered in `tests/unit/core/test_watch_profiles.py`; the UI wiring, handlers, filters/schedule/per-action/consent/dry-run surface, the resource-cap classifier, and the distinct cap-termination announcement are covered in `tests/unit/ui/test_main_frame_watch_service.py`. The full `tests/unit/core` and `tests/unit/ui` suites are green (971 passed, 2 skipped), the accessibility suite passes, and the UI public-surface characterization snapshot was refreshed.
- Counts: WATCH-5, WATCH-6, and WATCH-7 close, moving Tier 2 to **32 of 58 done (26 remaining)** and the QUILL 1.0 scope to **69 of 144 done (75 remaining)**. Quality gates: ruff format/check clean on all touched files, strict mypy clean on the touched `quill/core` modules (`watch_profiles.py`, `watch_actions.py`), and the menu and dialog (A11Y-4) contract guards pass. `dialogs.md` gained a row for the **Preview (dry run)** result dialog.

#### 2026-06-06: Settings/sharing — SET-5 and SHARE-3 landed Done; SHARE-1 and SHARE-2 dialogs landed In progress

The four "Settings / sharing" backlog items advanced together, two to Done and two to In progress, with the deterministic core fully tested and the two wx dialogs wired into Tools > Customize.

- **SET-5 (Done):** new wx-free `quill/core/settings_migration.py` serializes the flat `Settings` into a nested, versioned document (`schema_version` 1; fields grouped via the settings registry, unspecced fields preserved under `_ungrouped`). `load_settings` now migrates older nested documents and legacy flat documents through `from_versioned`, and `_safe_from_dict` recovers from corruption by dropping only the offending field while keeping every valid sibling; junk falls back to defaults. `save_settings` writes the versioned form atomically. The import cycle (settings to settings_migration to settings_registry) is broken with lazy imports inside load/save. Seven tests in `tests/unit/core/test_settings_migration.py` cover round-trip losslessness, nested and legacy migration, per-field corruption recovery, and junk handling.
- **SHARE-3 (Done):** new wx-free `quill/core/share_package.py` defines the portable package both SHARE dialogs use — `.quillprofile` (shareable) and `.quillbackup` (full restore) — with a manifest (schema version, kind, name, source version, sorted contents, ISO timestamp) and a read-aloud `package_summary`. Fourteen sections are marked shareable or private; `build_package` raises `PrivacyError` on a profile carrying a private section and scrubs private settings fields, while `read_package` defensively strips smuggled-in private sections and re-scrubs. Eleven tests in `tests/unit/core/test_share_package.py` include the privacy guarantee (no secret/recent-path/license/device field can reach a profile) and a file round-trip.
- **SHARE-1 / SHARE-2 (In progress):** a wx-free helper layer `quill/ui/share_dialogs.py` (offers, build/write export, read/apply import with a feature-state snapshot that rolls back on any failure) is covered by seven logic tests, and two wx dialogs (`open_share_export_dialog`, `open_share_import_dialog`) are wired into Tools > Customize. Export offers a profile/backup radio, named package, section checklist, structural privacy (private sections unchecked and disabled in profile mode), and a save dialog with the correct extension. Import opens a `.quillprofile`/`.quillbackup`, shows a screen-reader-pageable read-only preview, applies only the chosen sections with automatic rollback, and routes imported settings through the shared persist-and-refresh path. Three source-contract tests guard the wiring. **Honest remaining work:** the package format supports keymap, snippets, macros, watch profiles, dictionary, style models, and UI layout, but only settings and features are wired into the offer/apply lists today; the merge-vs-replace distinction and FLAG-1 dependency announcements on import are not yet implemented — so both stay In progress.
- Counts: SET-5 and SHARE-3 close, moving Tier 2 to **29 of 58 done (29 remaining)** and the QUILL 1.0 scope to **66 of 144 done (78 remaining)**. SHARE-1 and SHARE-2 move Todo to In progress. Quality gates: ruff format/check clean on all new and edited files, strict mypy clean on the touched `quill/core` modules (and on the wx-free `share_dialogs.py`), `main_frame` imports cleanly, and the menu and dialog (A11Y-4) contract guards pass. `dialogs.md` gained rows for both new dialogs.

#### 2026-06-05: AGENT-1 accessibility agent — deterministic engine and reviewable, single-undo UI landed

The headline "make this document accessible" agent moved from Todo to **In progress**.

- New wx-free, strict-typed core engine `quill/core/accessibility_agent.py` builds on the in-repo `glow.py` audit/fix primitives and `plain_language.py`. `build_plan(...)` audits four domains — structure (markdown heading spacing to auto, heading-jump to advisory, html missing `lang` to auto), alt text (markdown/html missing alt to advisory), link text (generic "click here" link text to advisory), and plain language (controlled-vocabulary swaps to auto, case-preserving) — and returns an ordered, per-step-consented plan. `apply_plan(plan, text, accepted_ids)` applies only the accepted auto-fixable steps, re-audits via `audit_text`, and returns an `AgentRunResult` with a run report and before/after finding counts.
- New `AccessibilityAgentDialog` (`quill/ui/assistant_tools.py`) surfaces the plan as an accessible `wx.CheckListBox` (auto-fixable steps pre-checked, advisory steps listed for review) with a read-only before/after details pane and an Apply Checked Steps button. `make_document_accessible()` in `main_frame.py` announces the spoken summary, runs the dialog, and on apply replaces the whole editor buffer with one `editor.Replace(0, last, text)` so the change is a **single undo**, then opens the re-audit report in a named scratch tab. Reachable at Tools > AI > Make This Document Accessible... (command `tools.ai_accessibility_agent`); it is deterministic and offline, so it stays outside the AI-enable gate.
- Tests: 14 core engine tests (`tests/unit/core/test_accessibility_agent.py`) plus two dialog-apply behavior tests. Quality gates green: ruff format/check clean, strict mypy clean on the new core module, the menu and dialog contract guards pass, `dialogs.md` gained a row for the new dialog.
- **Honest remaining work:** structure and plain language are auto-fixed, but alt-text and link-text are advisory-only (flagged, not auto-authored), so AGENT-1 stays **In progress** rather than Done. The Done count is unchanged (Tier 2 stays 27 of 58 done, 31 remaining); AGENT-1 simply moves Todo to In progress.

#### 2026-06-04: WATCH-6 and WATCH-7 advanced in core; running totals reconciled to the tracker

Code shipped in `quill/core` (wx-free), and the State-of-the-union counts were reconciled so the per-entry running totals stop disagreeing with the tier tracker.

- WATCH-7 grew its full built-in action set in `quill/core/watch_actions.py`: alongside the shipped Open and Move actions, the registry now carries `CopyAction` (copy to a destination, original left in place), `ConvertAction` (export to a chosen format through a caller-supplied IO/Pandoc handler), `RunMacroAction` (replay a named macro through a caller-supplied editor handler), `RunPythonTransformAction` (read the file's text, run a saved transform through the SEC-9 sandbox with a clamped timeout, write the result in place or to a suffixed file), and the consent-gated `AiAction` (summarize/tag/rewrite through a caller-supplied handler). Each validates its options, returns `done`/`failed`/`skipped` outcomes that route through the queue lifecycle, and offers a `preview`. Open, Move, Copy, and the sandboxed Python transform are fully functional; Convert, Run macro, and consented AI are implemented and unit-tested at the registry seam and wired through `WatchService`/`default_registry`, awaiting the UI to supply their handlers (the same callback pattern Open already uses). WATCH-7 stays **In progress**.
- WATCH-6 moved from Todo to **In progress**. The consent gate now lives in `WatchActionRegistry.run` (any `requires_consent` action — today the AI action — returns an announced `skipped` outcome until the profile carries explicit `options["consent"] is True`, honoring AI-5's no-silent-network promise), and a side-effect-free `WatchActionRegistry.dry_run(...)` returns a plain-language preview of what a profile would do or the reason it would not (unknown action, disabled feature, invalid options, missing consent). The sandboxed Python transform honors a clamped wall-clock cap shared with SEC-9, and the single-threaded worker already serializes processing (concurrency of one). Remaining for WATCH-6: the per-profile consent UI that shows provider/model/scope, surfacing the dry-run preview in the profile manager, and announcing resource-cap termination. Twenty new core tests cover the five actions plus the consent gate and dry-run; `test_watch_actions.py` is 34 passing and the full `-k watch` core suite is 93 passing. ruff format and check clean.
- Count reconciliation: WATCH-6/WATCH-7 are In progress, not Done, so no row closed and the **done count is unchanged**. The authoritative current count is the tier-completion tracker at the top of this section: **64 of 144 done in the QUILL 1.0 scope (80 remaining), and 64 of 186 across all tiers (122 remaining)**. The trailing "total N of 180" figures in the older log entries below (47, 48, 50, 54, 55) predate two events — the AX-A..F additions that took the all-tier pool from 180 to 186, and the tracker reconciliation noted in the deferral note (which corrected a previous Total of 55/125 that did not match the per-tier sums). Those historical entries are left as-is as a point-in-time record; the tracker table is canonical going forward.

#### 2026-06-04: Per-setting Reset buttons completed SET-6

Code shipped. Every control in the tabbed Settings dialog now carries its own accessible **Reset** button, closing SET-6.

- `open_general_preferences` gained a `writers` map (mirroring the existing `readers` map) plus `_reset_one` and `_reset_button` helpers. Each rendered control — bool, choice, int, float, text, and the special preview-browser choice — gets a compact **Reset** button whose accessible name is `Reset {label} to default`. Pressing it restores that single setting to `registry.default_value(key)` and announces the change via the status line; the restored value is committed on OK alongside the rest of the form, so it follows the same apply-on-OK model as every other edit (no surprise immediate persistence).
- This complements the existing whole-dialog Reset to Factory Defaults and the per-spec plain-language descriptions and search, completing SET-6's "every setting has a per-setting reset" clause. Quality gates green: ruff format and check clean, the settings dialog and registry unit suites pass; `main` stays green. Tier 2 moves to 27 of 58 done (31 remaining), total 55 of 180. SET-7 stays In progress pending only the admin pre-tune schema reference doc (DOC-7); SET-1..5 remain In progress.

#### 2026-06-03: Watch Profiles shipped end to end, and the top-level Menu Editor landed

Code shipped across two flagship surfaces. The single legacy watch-folder was replaced by the full multi-profile Watch Profiles automation hub, and the first slice of the user-customizable Menu Editor (MENU-5) went live.

- The Watch family advanced from planning to shipping. The `wx`-free engine now lives in `quill/core` (multi-profile `WatchProfile`s with isolated failure and shared de-duplication, a typed `WatchActionRegistry`, and a durable, restart-safe processing queue), fronted by a `WatchService` facade and consumed by a rebuilt UI. WATCH-1 (multi-profile engine), WATCH-2 (pluggable action registry), WATCH-3 (durable queue), and WATCH-4 (the accessible **Watch Queue Monitor**, reachable from Help and Tools, with one-key pause/resume/retry/open-result/clear and announced arrivals and completions) are **Done**. WATCH-5 (the **Watch Folder Profiles** manager dialog — create, edit, duplicate, enable, delete, with folder, filters, action, and post-action handling) is In progress pending its dedicated global Settings-defaults group. WATCH-7 is In progress: the Open and Move/archive built-in actions ship through the registry, while Convert, Run macro, Run sandboxed Python, and consented AI actions remain registered as `UnavailableAction` placeholders that advertise themselves with an announced reason until their tiers land. WATCH-6 (consent gate, dry-run preview, resource caps) stays Todo. This moves Tier 2 to 26 of 58 done (32 remaining) and the total to 54 of 180.
- MENU-5 delivered its top-level slice. Edit > Customize Menus... (`app.menu_editor`) opens a stock-control dialog — a list of top-level menus with Move Up/Down, Rename..., Show/Hide, and one Reset to Factory Defaults — that edits a working copy and persists only on Save. A post-build transform pass then applies the saved order, labels, and visibility to the menu bar, bailing out untouched if any menu label is unrecognised so bad customization data can never corrupt the menu bar. Five transform tests plus the existing model tests cover it. The per-item and editor context-menu UI remain the next step; the shared `MenuCustomization` model (with `CONTEXT_MENU_KEY`) already supports both, so MENU-5 stays In progress. (Commit 5b05ab5.)
- The update checker was also hardened in this window (versioned feed parsing with correct pre-release ordering per CQ-20), keeping the no-silent-network promise intact.

#### 2026-06-02: Settings became a single registry-driven tabbed front door

Code shipped. The scattered single-panel "General preferences" was replaced by one accessible tabbed Settings dialog (`Ctrl+,` then `General`) that is generated from a new shared settings registry, and the back-up/restore plumbing was consolidated into that same dialog so it no longer needs its own Tier 2 commands.

- `quill/core/settings_registry.py` (UI-agnostic, fully unit-tested) defines eight groups (general, editing, navigation, accessibility, read aloud, AI, transcription, updates) and roughly forty typed specs (bool, choice, int, float, text), each carrying a plain-language description, optional feature id, and search keywords. It exposes group/spec lookup, case-insensitive search, per-key and full reset, and versioned export/import (schema_version 1).
- `quill/core/menu_customization.py` (the MENU-core model: reorder, rename, hide, reset, with a context-menu key) landed alongside it with its own tests; the menu-editor UI that consumes it is the next step.
- The new Settings dialog renders one `wx.Notebook` page per group with a search row that jumps to the first matching control, special-cases the preview-browser choice, the beta-channel consent gate, and the AI master toggle, and skips any spec whose feature flag is disabled. Export to `.qsf`, Import from `.qsf`, and Reset to Factory Defaults are buttons inside the one dialog, all routed through a shared apply-refresh path. This advances SET-1, SET-6, and SET-7 to In progress and starts MENU-1; the `.qsf` (settings) and `.qpf` (profile) extensions are now reserved. `dialogs.md` was updated to map the consolidated dialog and its buttons.
- Quality gates green: ruff format and check clean, the full UI unit suite (174 tests) plus the new `test_main_frame_settings_dialog.py` behavior tests pass; `main` stays green. Tier counts are unchanged because the SET items are In progress rather than Done.
- Follow-on the same day: the editor context-menu configuration (MENU-5, E-core) was proven to fold entirely into the shared `MenuCustomization` model through `CONTEXT_MENU_KEY`, with new tests covering context-menu reorder, hide, rename, and independence from the menu-bar order. MENU-3 (Insert Link de-duplication) was confirmed Done and MENU-5 opened as In progress for the menu-bar and context-menu editor. The remaining UI-side steps (the menu-build transform pass and the Menu Editor dialog) are deliberately deferred as the riskier work in the large `main_frame.py` surface.
- FLAG-4 closed as a low-risk quick win: feature-flag and profile state now round-trips through a versioned `.qpf` QUILL profile file. The pure-core helpers `export_feature_profile_file` / `import_feature_profile_file` (in `quill/core/features.py`, tolerant import, two new unit tests) build on the pre-existing `export_profile_data` / `import_profile_data`, and Export profile / Import profile buttons now sit beside the Settings Export/Import/Reset row. Importing reapplies accelerators and rebuilds the menu, and the outcome is announced. Tier 2 drops to 36 remaining.
- SEC-2 closed as a low-risk, pure-core security win: a shared `resolve_within` helper (with a `PathEscapeError`) in `quill/core/storage.py` resolves a candidate path and refuses any target that escapes a permitted base directory (via `..`, an absolute path, or a symlink-resolved escape). `write_json_atomic` gained an opt-in `base` parameter that runs the guard before writing, and the pure-core app-data JSON writers (`recent`, `search-history`, `palette-usage`, `features`, `menu_customization`) now pass `base=app_data_dir()` so they can never be tricked into writing outside the application data area. User-driven exports (`.qsf` settings, `.qpf` profiles) deliberately stay unguarded because they target user-chosen locations. Four new unit tests prove traversal is blocked and in-base writes still succeed. Being a cross-cutting protection rather than a tier-listed ID, it does not move the tier counts.
- CQ-14 and CQ-19 closed in the same `storage.py` pass: CQ-14 (path-safety tests) is satisfied by the SEC-2 traversal tests, and CQ-19 hardens the atomic write itself — `os.replace` now runs through a small `_atomic_replace` retry loop (five attempts, 50 ms backoff) that absorbs the transient `PermissionError` Windows raises when an antivirus scanner, backup agent, or screen-reader hook briefly holds the destination open, then re-raises if the lock persists. Two new tests simulate transient contention (succeeds after retries) and permanent contention (re-raises). Both are cross-cutting code-quality rows and do not move the tier counts.
- CQ-20 closed as a pure-core quick win: version pre-release ordering is now intentional and tested. `_version_tuple` in `quill/core/updates.py` previously stripped non-digits per segment, so `1.2.0-rc1` parsed as patch `1` and wrongly outranked the final `1.2.0`. It now separates the pre-release suffix from the `major.minor.patch` core and appends a stage rank so that, for the same triplet, a final build sorts after every pre-release and the stages order final > rc > beta > alpha (unknown suffixes fall to the earliest stage). Five new tests in `tests/unit/core/test_updates.py` cover stage ordering, the suffix-leak regression, and `select_latest` preferring the final release. Cross-cutting code quality, so the tier counts are unchanged.
- A security-hardening triplet closed across the subprocess and credential surfaces. SEC-4 and SEC-15 hardened `run_subprocess_safely` (`quill/stability/safe_subprocess.py`): it now rejects an empty `args` sequence and a `cwd` that is not an existing directory (both `ValueError`), documents the safety contract that callers pass a trusted absolute directory, and wraps a launch `OSError`/`FileNotFoundError` into a clearly logged, re-raised `OSError` naming the tool. SEC-16 added a shared `validate_credential_identifier` (`quill/platform/credential_validation.py`) that rejects empty, over-long, control-character, and leading-dash identifiers, then wired it into the Windows credential manager (`target_name`) and the macOS keychain (`account`/`service`); the macOS `set_secret` already checked its return code. SEC-15 and SEC-16 are Tier 4 items, so Tier 4 moves to 11 of 30 done (19 remaining) and the total to 47 of 180; SEC-4 is a cross-cutting documentation row and is not tier-counted. Eleven new unit tests (five subprocess, six credential) cover the new guards.
- CQ-22 closed alongside the credential-validation work: `load_generic_credential` in `quill/platform/windows/credential_manager.py` now documents and debug-logs the two "no usable secret" outcomes so callers can tell them apart — an **absent** credential returns `None`, while a stored entry with an **empty** blob returns a `StoredCredential` whose `secret` is `""`. A new Windows-only test (`tests/unit/platform/windows/test_credential_manager.py`) proves the distinction with a real Credential Manager round-trip (absent then None, empty then `""`, deleted then None again) and that identifier validation still rejects a leading-dash target. Cross-cutting code quality, so the tier counts are unchanged.
- CQ-17 closed as a pure-documentation win: a new engineering note, [docs/engineering/thread-safety.md](../engineering/thread-safety.md), captures the cache-locking invariants that were previously only implied by the code. It records the two patterns Quill uses — double-checked module-level locking with an immutable published snapshot for read-mostly caches (the spell-check wordlist and enchant handle behind `_BACKEND_LOCK`, the thesaurus index behind `_LOAD_LOCK`), and a per-instance lock taken around every access for genuinely mutable state (the watch-folder seen-set) — plus the stability helpers and a rule that forbids new unguarded module-level mutable caches in `quill/core`. No code changed, so the tier counts are unchanged.
- CQ-15 closed as the natural follow-on to that note, and is the first Tier 6 item to land. `tests/unit/core/test_cache_concurrency.py` turns the documented invariants into an executable guard: it cold-starts the thesaurus index and the spell-check wordlist, then hammers `thesaurus.lookup` and `spellcheck.is_known_word`/`backend_info` from sixteen threads released together on a barrier. The tests prove the double-checked lock collapses the thundering herd to a single expensive load (the thesaurus parser runs once; the wordlist file is read at most once) and that every thread observes the same published snapshot and the same active backend tier. The shared note from CQ-17 satisfies the "short note of the invariants" half. CQ-15 is a Tier 6 ID, so Tier 6 moves to 1 of 33 done (32 remaining) and the total to 48 of 180. Note on sequencing: the *content* documentation (tutorials, podcasts, user guides) is deliberately held until the features they describe are built — closing CQ-15 takes a no-risk test item that happens to live in Tier 6 without prematurely documenting moving targets.
- CQ-12 and CQ-13 followed as the next two no-risk Tier 6 test items, both exercising already-stable code. CQ-13 ("IO format coverage") confirmed Markdown, HTML, JSON, CSV, DOCX bridge, and PDF scoring all have fixture-based tests: JSON/CSV/DOCX-bridge/PDF-scoring were already covered in `tests/unit/io/test_structured.py`, and Markdown/HTML fixtures were added to `tests/unit/io/test_text.py` (they open verbatim through the plain-text reader and round-trip through the writer). CQ-12 ("Undo and redo tests") grew `tests/unit/core/test_undo_store.py` to cover the edge cases — missing-history load, no-op clear, non-string/non-list payload filtering, the `limit` boundary (including a non-positive limit coerced to one), the returned bounded list, multi-cycle accumulation, and per-path isolation. CQ-11 ("Spell-check fallback and preload tests") was only half-closeable: its tier-fallback half landed as `tests/unit/core/test_spellcheck_backend.py`, which pins each of the three backend tiers (enchant, bundled wordlist, stub) and proves `backend_info`/`is_known_word` honour the active tier, but the background-preload half stays open because no spell-check preload API exists yet (tracked by PERF-1). With CQ-12 and CQ-13 done, Tier 6 moves to 3 of 33 (30 remaining) and the total to 50 of 180; CQ-11 remains Todo.
- SET-1 advanced (still In progress) with a zero-risk registry pass: three already-wired `Settings` fields that had behavior but no Settings-dialog presence were surfaced as registry specs — `auto_side_preview` (open preview beside the editor) plus the `csv_open_mode` and `word_open_mode` open-as choices. Because they reuse the flat `Settings` dataclass and its `from_dict` normalization, the tabbed dialog auto-renders them and the existing registry guard tests (field-mapping and choice-acceptance) cover them, with one focused test pinning their presence. No behavior changed and no `main_frame.py` edits were needed; snippets, macros, sticky notes, and status-bar registry specs still keep SET-1 open, so the tier counts are unchanged.

#### 2026-06-01 (planning): Watch Profiles scoped, and feature-flag respect made fundamental

No code shipped in this entry; it records two planning decisions committed to `golden.md` (and `golden.html`) before Tier 2 begins.

- Watch Profiles (the WATCH family, WATCH-1 through WATCH-9) turns today's single watch-folder into a personal, accessible automation hub: many named profiles, each watching its own folder and bound to its own action (Open, convert or export, move or archive, run a macro, run a sandboxed Python transform, consented AI actions, plus GLOW "audit and fix" and BITS Whisperer "transcribe" as their tiers land), all feeding one durable, restart-safe queue with an accessible Watch Queue Monitor in Help. The core seven items are Tier 2 (flagship); the GLOW action is Tier 3 and the transcription action is Tier 5, plugging into the same registry. This is positioned as a key differentiator because it is simultaneously a productivity and an accessibility superpower and it unifies QUILL's distinctive engines behind one learnable model: a folder, an action, a queue.
- Feature flags were elevated from an implementation detail to a stated fundamental (new product-wide delight theme 7) backed by the FLAG family. The codebase already has a mature `FeatureManager` (feature ids, dependencies, maturity, privacy, profiles, command-visibility filtering, status-bar gating); FLAG-1 makes "disabled feature is gone from every surface" a tested UI contract, FLAG-2 makes shipping a `FeatureDefinition` part of the definition of done, and FLAG-3/FLAG-4 add the rich feature-profile UI and export. FLAG-1 and FLAG-2 are foundational and were added to Tier 1 (its only remaining items); FLAG-3 and FLAG-4 are Tier 2. The entire Watch Profiles surface is specified to honor these flags, so users can run anything from an Open-only setup to a full automation hub purely by toggling features, with the UI always matching their choices.

Backlog totals moved from 142 to 155 (WATCH-1..9 and FLAG-1..4); Tier 1 is now 20 of 22 (the gate ladder and protections complete, FLAG-1/FLAG-2 open), and Tier 2 grew to 38 items.

#### 2026-06-01 (planning): GLOW and BITS Whisperer gap analysis, agreed decisions, and the docs/BITS tier swap

A grounded read of the three integration repos (`s:\code\quill-glow-core`, `s:\code\glow`, `s:\code\bw`) produced a gap analysis and five agreed decisions that this revision encodes.

- The failing CI in `s:\code\glow` is in the Flask web app (`acb_large_print_web`), not the engine QUILL consumes: the desktop core (`acb_large_print` / `acb_large_print_core`, the `from_glow_backend` target) already passes 308 tests. Decision: full good-citizen cleanup — fix the web suite, reconcile the version sweep (VERSION 8.0.0 vs README vs TODO.md 2.8.0), and keep the desktop core green. GLOW-1 step 1 is rescoped accordingly.
- Structured-format audit (DOCX, PPTX, XLSX, PDF, EPUB) is the Tier 3 headline, not a deferred item: GLOW-2 is in scope, since "open a real document and audit it in place" is the whole point and the engine already supports it.
- Feature-flag respect extends to BITS providers: three tiers (`core.bw_providers_local` always on, `core.bw_providers_plus` opt-in, `core.bw_providers_enterprise` all 18). BW-9 was rewritten from "right-size the set" to this tiered model.
- BITS Whisperer is healthy (875 tests passing, CI green, framework-agnostic core), so Tier 5 has no engine-repo fix — pure integration. The canonical `quill/core/transcript.py` model (BW-1) is the keystone the rest of the tier depends on.
- New GLOW items: GLOW-6 now explicitly surfaces engine/rule version in `diagnostics.py` and About; GLOW-7 adds a consent gate so GLOW's optional networked AI features are off by default and honor the no-silent-network rule and the GATE-9 egress audit.

Tier swap: per the standing request, BITS Whisperer transcription moves to Tier 5 and documentation to Tier 6, so the docs land last and describe a product that is already GLOW-native and transcription-capable, reusing the `s:\code\bw\docs` material. The roadmap prose (section 23), the tier tracker, and the WATCH cross-references were all updated. Backlog totals moved 156 -> 159 (GLOW-6 counted, GLOW-7 new, BW-10 counted). Execution is authorized for Tiers 2 through 6 end to end, keeping `main` green throughout.

#### Bookmark: Accessibility Agents integration (research, deferred to QUILL 2.0)

> Decision (2026-06-02): deferred to **QUILL 2.0**. The axe-core / Accessibility
> Agents workstream (AX-A through AX-F) builds on the GLOW engine and report
> surface, and GLOW is itself a 2.0 item, so this whole workstream follows GLOW
> into 2.0. The research and design below stand; nothing here is part of the 1.0
> milestone, and the tier-renumbering it describes does not apply to 1.0.

A research evaluation of the Community Access "Accessibility Agents" project
(`s:\code\agents`, MIT-licensed) is written up in full in [aa.md](aa.md) under
`docs/planning/`. The maintainer is inclined to adopt it. If approved, it becomes a NEW
Tier 4 inserted immediately after Tier 3 (GLOW), which renumbers the current
tiers: Tier 4 (structural health and performance) -> Tier 5, Tier 5 (BITS
Whisperer) -> Tier 6, and Tier 6 (documentation) -> Tier 7.

The project is about 80 LLM-driven accessibility agents across five host
platforms (Claude Code, Copilot, Gemini, Codex, and a Node.js MCP server with 24
scanning tools). Most of it targets web developers and CI and is out of scope for
a desktop writing app; the value to QUILL is narrower but real, and it already
ships a GLOW bridge, so it is designed to interoperate with Tier 3, not compete.
The proposed work (provisional prefix `AX-`) is six workstreams, all building on
the shared GLOW engine and all behind `FeatureManager` (FLAG-1), reusing the
consented AI layer (AI-13), and honoring the no-silent-network rule (GATE-9):

- AX-A: adopt the desktop / wxPython / screen-reader knowledge agents
  (`wxpython-specialist`, `desktop-a11y-specialist`, `desktop-a11y-testing-coach`)
  as curated contributor guidance in repo memory and instructions. Zero runtime
  risk; pure documentation; can land even if the rest is declined.
- AX-B: an optional, off-by-default local MCP audit backend for structured
  formats (DOCX, PPTX, XLSX, PDF, EPUB, Markdown) that normalizes into the GLOW-3
  report surface, adopted only where additive to GLOW. Adds an optional (never
  hard) Node.js dependency with a clean "backend unavailable" path.
- AX-C: expose QUILL's own GLOW engine through the project's existing GLOW-bridge
  contract so the wider ecosystem can audit and fix through QUILL, gated by the
  GLOW-7 consent rules.
- AX-D: consented agent-assisted remediation (alt text, plain-language rewrites)
  folded into the Accessibility agent (AGENT-1) flagship, never a second AI
  network path; explicit, announced, reviewable apply-and-undo, off by default.
- AX-E: an axe-core / WCAG 2.2 AA web accessibility check on the HTML a user
  authors or exports, plus the document-level Web Accessibility specialists
  (`aria-specialist`, `keyboard-navigator`, `contrast-master`, `forms-specialist`,
  `modal-specialist`, `live-region-controller`, `alt-text-headings`,
  `tables-data-specialist`, `link-checker`, `i18n-accessibility`) as the consented
  explain-and-fix layer. Decisive technical finding: axe-core needs no Node.js —
  it is a single self-contained `axe.min.js` (about half a megabyte, bundled, so
  zero per-scan bandwidth) injected into QUILL's already-shipped off-screen Edge
  WebView2 (`wx-accessible-webview`). The scan is therefore in-process, local, and
  a SILENT REVIEW by construction: the WebView is created off-screen and never
  shown, so a background or watch-folder check runs with no UI at all; the
  navigable findings dialog (GLOW-3) appears only on demand. The optional Node
  backend (AX-B) is needed only for the heavier Playwright behavioural passes, not
  the everyday HTML check.
- AX-F: an optional, off-by-default HTML/CSS/SVG validity check on the HTML a user
  authors or exports, using the Nu Html Checker (vnu, `validator/validator`,
  MIT-licensed), normalized into the GLOW-3 report surface. This is the validity
  complement to AX-E's axe-core accessibility check: axe-core answers "is this
  accessible," vnu answers "is this well-formed, standards-conformant HTML," and
  malformed markup is a common upstream cause of assistive-technology failures.
  Decisive technical finding: vnu needs no Node.js — it is a Java tool shipped as a
  self-contained precompiled Windows binary (`vnu-runtime-image`) that bundles its
  own Java runtime, so it adds no Node and no separate Java install. It runs as a
  local command-line check (or an optional local HTTP service) over the generated
  doc artifacts and any user HTML export, invoked the same way pandoc is — from
  `scripts/`/`tools/`, never inside the pure `quill/core` tree. Local and silent by
  construction: no network, results folded into the navigable findings dialog
  (GLOW-3) on demand. Pairs naturally with the existing `check_docs_artifacts.py`
  gate over QUILL's pandoc-generated `*.html`.

Sequencing: this tier lands after Tier 3 (GLOW) because AX-B, AX-C, AX-D, AX-E,
and AX-F all build on the shared GLOW engine and its report surface; documentation
still lands last so it describes a product that is already GLOW-native,
agent-assisted, and transcription-capable. Open questions for the maintainer are
in [aa.md](aa.md) section 6. Do not start this work or renumber the tiers until
the maintainer confirms after reviewing [aa.md](aa.md).

#### Continuation brief (resume point for the next agent or session)

Tier 1's original scope is complete: all seven bugs, the cheap security hardening, and the full gate ladder (GATE-1 through GATE-9) are committed and enforced in three CI workflows (`pr-ci.yml`, `security-ci.yml`, `accessibility-ci.yml`). The working tree is gate-clean: `ruff format --check .` passes, `ruff check . --ignore E501` passes, `mypy quill\core quill\io` reports zero errors, and the full suite is 701 passed / 7 skipped with 72.28% core+io coverage. Two foundational feature-flag items (FLAG-1, FLAG-2) were subsequently added to Tier 1 and are open; the richer feature-profile UI (FLAG-3, FLAG-4) sits in Tier 2.

First task before anything else (OPS-1): make `main` green. The gate jobs were red because they installed only `.[dev]` while the UI tests need `wx` and the typing gate needs the optional modules ignored; the fix (install `.[dev,ui]` in the test jobs and add `markitdown`/`certifi`/`pdfplumber`/`pyttsx3` to the mypy overrides) is committed and verified — PR CI, Security CI, and Accessibility CI all conclude success on `main` (commit d62d3bd). OPS-1 is Done.

The agreed next sequence (decided with the maintainer): (1) do the cheap Tier 4 quality cleanup first — CQ-18 (the ~43 remaining E501 line-length wraps, after which the `--ignore E501` can be removed from the lint gate and pre-commit) and individually verify/close the TYPE-1..8 rows — because it is low-risk, behavior-preserving, and makes every later PR land in a clean tree; (2) then build Tier 2 flagship work (QUILL key QK-1..5/QK-9, navigation NAV-1/4/5, then AI-13 provider wiring); (3) do the big `MainFrame` decomposition (CQ-1/CQ-16) last, behind the GATE-6 characterization snapshot, never before Tier 2. Tiers are then executed in order through Tier 6: Tier 3 GLOW (engine adopted via quill-glow-core, structured-format audit as the headline), Tier 4 structural health, Tier 5 BITS Whisperer transcription (the docs/BITS swap puts transcription before documentation), and Tier 6 documentation last.

Parallelization guidance (no code collision): the cheap cleanup and the flagship work own disjoint directories, so they can run as separate agents — Agent A on `quill/io`, `quill/core` (non-`ai`), `quill/platform`, `quill/tools`; Agent B on the QUILL key and NAV/SEL features in `quill/ui/` plus new `quill/core/` modules; Agent C on docs under `docs/`. The single hard rule: only one agent may touch `quill/ui/main_frame.py` at a time, because it is the 18k-line shared surface, and the `MainFrame` decomposition must be serialized after the features land. Each agent regenerates `golden.html` with pandoc, updates this tracker, and commits per item.

#### 2026-06-01 (fixes + planning): two reported dialog bugs fixed, and a principled dialog-standardization decision

Two GitHub issues reported by a beta tester were fixed on `main` and a design question about the many hand-rolled dialogs was settled.

- #84 (could not exit the find-within-files dialog): `_prompt_file_search` added its `StdDialogButtonSizer` with `wx.ALIGN_RIGHT` instead of `wx.EXPAND`, so on Windows the OK/Cancel buttons were left unrealized and Cancel could not be clicked, trapping the user. The fix mirrors the proven single-document search dialog (`_prompt_search`): the button sizer is added with `wx.EXPAND`, an explicit default button is set, Enter submits, and focus is deferred via `CallAfter`. The identical bug in the sibling Status Bar Layout dialog (which also never gave the dialog its own outer sizer) was fixed in the same change, and the misspelling-review dialog got its missing outer sizer too.
- #85 (Go To and List Bookmarks did nothing): both bookmark dialogs were hardened. `go_to_bookmark` now forces a default selection and wires affirmative/escape ids so it is reliably dismissible; `_show_tree_navigator` (List Bookmarks) now wires modal ids, focuses the tree via `CallAfter`, and guarantees `Destroy()` in a `finally`. Regression tests cover the jump, the modal-id wiring, and the empty-bookmarks announcement.
- Dialog-standardization decision (principled, no damage): a wholesale rewrite was deliberately rejected. The evidence is that the bug class is inconsistent construction, not custom dialogs per se — the near-identical `_prompt_search` worked while `_prompt_file_search` did not. wxPython also has no stock multi-field form dialog, and the interactive AI-tool dialogs are working, accessible-today features that the maintainer's own assessment on issue #73 says must be converted individually with a screen reader, never batch-rewritten. So the plan adds a narrow, additive pair: `A11Y-4` is sharpened into a machine-enforced dialog-contract guard (a GATE-6-style conformance test for the exact `EXPAND`/outer-sizer/default-button/`Destroy` contract), `DLG-1` (Tier 2) migrates only the safe submit-once forms onto the already-shipped `show_web_form` helper, and `DLG-2` (Tier 4) defers the interactive tools to individual screen-reader-verified conversions. Backlog totals moved from 164 to 166; Tier 2 grew to 44 and Tier 4 to 30.

#### 2026-06-01 (later still): Tier 1 complete — full gate ladder enforced, tree gate-clean

What shipped and is committed to `main`, completing Tier 1:

- The remaining five gates are done. `pr-ci.yml` adds the required PR pipeline (GATE-2) with a lint job (format check plus `ruff check` with E501 deferred to CQ-18), a `unit-tests` job that runs the full suite under a hard 70% core+io coverage floor (GATE-5, current 72.28%), and a `characterization` job (GATE-6). `security-ci.yml` adds a `security-checks` job (GATE-8) running the hardened-XML check and the TLS, redaction, XML-bomb, zip-cap, sandbox, and OCR-allowlist invariant suites. Accessibility CI now also runs the announcement-grammar conformance suite (GATE-7).
- The characterization gate freezes the `MainFrame` public surface (235 methods) in a committed snapshot via `quill/tools/ui_surface.py`, so the planned decomposition stays behavior-preserving; the snapshot is regenerated deliberately with `python -m quill.tools.ui_surface --write`.
- The cheap quality cleanup that makes the gates honest landed with it: the whole first-party tree was formatted (`ruff format`, ~90 files) and the auto-fixable lint cleared (imports, bugbear `zip(strict=)`, pyupgrade, stray E402), leaving only the E501 line-length backlog deferred to CQ-18. A vendored/distribution `extend-exclude` keeps the gate scoped to real source.
- A real ordering bug was found and fixed in the process: the autosave uniqueness suffix `-001` sorted *before* the bare `.snap` name (because `-` < `.`), so `latest_autosave` could return the older snapshot when two saves shared a microsecond stamp. Every snapshot now carries a zero-padded counter so filenames always sort in write order; verified stable across repeated runs.

Honest standing after this entry: Tier 1 is 20 of 20 — done. The safety floor, the typing zone, the accessibility grammar, and the no-silent-network promise are all machine-enforced on every PR, and the tree is clean enough that the next work lands safely. Still nothing user-facing and flagship has shipped (Tier 2 remains 0 of 29); per the agreed plan the next move is the cheap Tier 4 quality cleanup (CQ-18, TYPE rows) and then the flagship QUILL key and navigation work, with the monolith decomposition deliberately last.

#### 2026-06-01 (later): Gate ladder enforced in CI, scoped typing clean, and the announcement grammar landed

What shipped and is committed to `main`, building directly on the morning's Tier 1 entry:

- The quality-gate ladder is now real in CI, not just described. A required Security CI pipeline runs three new jobs that block merge: `scoped-strict-typing` (`mypy quill\core quill\io`, GATE-3 and CQ-7), `banned-patterns` (GATE-4), and `no-silent-network` (GATE-9). Pre-commit hooks (GATE-1) catch format, lint, and undefined-name problems before a commit, and CONTRIBUTING documents the scoped type-check command and why the whole-tree scan is never used (PERF-8).
- The scoped strict-typing zone is genuinely clean: all 33 real type errors across `quill/core` and `quill/io` were fixed (missing annotations, `Any` returns, a wrong tuple annotation, typed file-lock handles, a type-safe snippet clone), and stub-less third-party imports are handled with explicit module overrides so the gate measures our own code. `mypy` reports zero errors across 96 source files.
- The banned-pattern gate is an AST checker, not a brittle text grep: it fails on bare `wx.` in `main_frame` where `wx` is not locally bound (the BUG-2 class), on raw `ET.fromstring` outside `safe_xml` (the SEC-10 class), and on any weakening of ruff's undefined-name and redefinition rules (the BUG-1 and BUG-4 classes), with tests proving it catches each shape.
- The no-silent-network gate inventories every outbound call site in the package and fails when a new one appears without a reviewed rationale tying it to a user action or explicit consent. All eight current egress points are documented.
- Two more cheap protections landed: every HTTPS call now goes through a single verified TLS context (SEC-5), and OCR language codes are validated against a strict allowlist before Tesseract is invoked so a tampered setting cannot inject CLI options (SEC-3).
- Accessibility gained a shared announcement grammar: a written style guide plus a UI-agnostic `quill/core/announcements.py` (`format_announcement`, `format_progress`, `pluralize`) that the AI writing-action announcer now uses, with tests verifying the key phrases (A11Y-1).

Honest standing after this entry: Tier 1 is 15 of 20 items done; the five remaining are gate work that needs more infrastructure (the full PR pipeline GATE-2, coverage floor GATE-5, the characterization suite GATE-6, the accessibility-PR gate GATE-7, and the security-scan gate GATE-8). The accessibility-PR gate (GATE-7) now has a concrete grammar to check against, which de-risks it. Nothing user-facing and flagship has started yet (Tier 2 remains at 0 of 29). The safety floor and the team's velocity protections are now materially higher; the next strategic move is the flagship QUILL key and navigation work, not more gates.

#### 2026-06-01: Tier 1 protections landed (latent-crash bugs, cheap security hardening, AI error taxonomy)

What shipped and is committed to `main`:

- All seven verified latent-crash bugs are fixed with regression tests: the corrupted onboarding method and its three deleted helpers (BUG-1), the four bare `wx.` heading-style calls (BUG-2), the undefined `VoiceOption` annotations (BUG-3), the duplicate `URLError` import (BUG-4), the unchecked llama.cpp response shape (BUG-5), the DOCX or PPTX element name collision (BUG-6), and the non-positive chunk-split guard (BUG-7).
- The cheap, user-protecting security hardening is in: all untrusted XML now parses with entity expansion disabled against billion-laughs (SEC-10), ZIP-based formats enforce a cumulative decompression cap (SEC-11), diagnostics redaction covers token, password, and NAME_KEY patterns (SEC-13), and configured speech executable paths are validated against an allowlist so tampered settings cannot launch arbitrary programs (SEC-1).
- Two pre-existing test failures, unrelated to the above but found along the way, were fixed honestly rather than ignored: an autosave snapshot-collision bug where a coarse Windows clock overwrote snapshots, and four stale keymap tests that had not been updated after the deliberate QUILL key chord migration.
- The in-progress AI connection work was reviewed, judged safe and forward-aligned, and committed: a structured error taxonomy (auth 401, forbidden 403, rate-limited, warming-up, not-running, timeout, unreachable) matched on numeric status codes rather than substrings, a bounded warm-up retry, and portable-key unlock-failure recovery. This is the foundation the AI-13 provider wiring and AI-17 chat-path messages build on.

Honest dimension movement since the 0.1.5 baseline:

| Dimension | Baseline (0.1.5) | Now (2026-06-01) | Why it moved |
| --- | --- | --- | --- |
| Security and privacy | Level 3 | Level 3 to 4 | Untrusted-input hardening (XML, zip, redaction) and executable-path validation close the worst input and supply-chain gaps; remaining items (network checksums, sandbox limits, gate enforcement) keep this short of Level 5. |
| Code quality and architecture | Level 3 | Level 3 (cleaner) | Seven latent crashes removed and pre-existing test rot fixed; the UI monolith and lint/typing debt remain, so the level holds. |
| AI and agents | Level 2 | Level 2 to 3 | Connection diagnostics are now honest and screen-reader-friendly; the headline gap (configured providers still fall back to local generation, AI-13) is not yet closed. |
| Test coverage | Level 2 to 3 | Level 3 | New regression tests for every bug class and the AI taxonomy; the broad UI characterization and IO matrix work is still ahead. |

What is explicitly not done yet: the quality-gate ladder is not enforced in CI (GATE items), the configured AI providers still do not drive generation (AI-13), and the UI monolith is intact (CQ-1). The flagship QUILL key work (QK-6/7/8) and the selection deep dive (SEL-1 through SEL-5) shipped in June 2026; navigation (NAV family) and the full settings tuning surface (SET family) remain ahead. Overall standing remains roughly Level 3, already Level 4 on accessibility; this section moved the safety floor up and delivered the first major user-facing flagship features.

### What QUILL would be

QUILL would be a mature, 1.0-grade, screen-reader-first writing application: not a promising beta, but a dependable daily tool that a blind or low-vision writer could trust for real work, and that a sighted power user would also find fast and pleasant. The signature QUILL key would be a genuinely memorable interaction (discoverable with one question mark, tunable, consistent, and documented as the headline feature), and the accessibility agent would be a category-defining capability: tell the app to make a document accessible, and watch it do so, step by step, reversibly, entirely by keyboard and voice. The AI surface would also be honest end to end: when a user picks OpenAI, OpenRouter, Gemini, Azure, Ollama, or Claude, that provider is the one that responds, instead of the configuration being accepted while generation silently falls back to the local model (AI-13). GLOW would be folded in as the in-app accessibility engine, and transcription would arrive last as a unifying capability, in that deliberate order.

### Scale on the dimensions that matter

The following self-assessment uses a simple five-level scale: Level 1 prototype, Level 2 beta, Level 3 product, Level 4 polished product, Level 5 best-in-class or category-defining. Today's honest baseline is included for contrast.

| Dimension | Today (0.1.5 beta) | After this plan | Notes |
| --- | --- | --- | --- |
| Accessibility | Level 4: strong, screen-reader-first | Level 5: category-defining | Accessibility is gated on every change; the accessibility agent has no real peer. |
| Core writing and navigation | Level 3 to 4 | Level 5 | QUILL key, Quick Nav, and structural selection become a cohesive, discoverable, tunable system. |
| AI and agents | Level 2: strong config, but providers do not yet generate | Level 4 to 5 | Today the provider boundary, key storage, and model discovery are excellent, but a configured cloud or Ollama provider silently falls back to the local model (AI-13); after this plan, local-first, consented, reversible, fully accessible AI editing and a real accessibility agent, with the selected provider actually responding. |
| Code quality and architecture | Level 3: well-structured but a monolith | Level 5 | The UI monolith is fully decomposed behind characterization tests; strict typing and lint are clean and enforced everywhere, not only in the core zone. |
| Security and privacy | Level 3 | Level 5 | Untrusted-input hardening, supply-chain checks, machine-enforced no-silent-network, and a documented plugin capability and signing model (ECO-1). |
| Performance | Level 3 | Level 5 | First-use stalls removed; budgets enforced by a gate; large-document and Read Aloud paths tuned to best-in-class responsiveness. |
| Documentation | Level 3 to 4 | Level 5 | Consolidated, accessible, complete, with primers, references, podcasts, tutorials, and full localization (L10N-1). |
| Combined suite (GLOW and transcription) | Level 2: separate apps, partial bridges | Level 5 | Write, transcribe, audit, fix, and publish in one accessible app on shared engines. |
| Engineering process and gates | Level 2: tools exist, not enforced | Level 5 | A full gate ladder makes quality objective and lets AI assistance accelerate safely. |
| Test coverage | Level 2 to 3 | Level 5 | UI characterization, IO matrix, sandbox policy, per-provider contract tests, and a performance budget close every major gap, with a ratcheting coverage floor. |
| Platform breadth | Level 3: Windows and macOS | Level 5 | Windows and macOS are excellent and Linux reaches the same accessibility and stability bar (LINUX-2). |

### Overall standing

- Today: a strong, accessibility-leading 0.1.5 beta with an excellent foundation, a few latent bugs, a large UI monolith, an AI provider surface whose configuration outruns its wiring (cloud and Ollama selections do not yet drive generation), and quality tools that are present but not yet enforced. Roughly Level 3 overall, already Level 4 on accessibility.
- After this plan: a confident, releasable product at Level 5 across every dimension that matters, and clearly category-defining on accessibility and on accessible AI-assisted editing. It would be, credibly, the most accessible writing application available, with an agent capability that no mainstream editor offers, backed by an engineering process strong enough to keep it that way. Because the plan now commits to closing every dimension to highest quality (the former frontiers below are committed work, not deferred hopes), nothing of substance is left at less than best-in-class once it is complete.

### Closing every remaining gap to highest quality

The earlier draft of this plan listed frontiers that would remain even after full implementation. To meet the directive that nothing be left below highest quality, those frontiers are now committed plan items rather than acknowledged shortfalls:

- Platform breadth. Beyond the Linux spike (LINUX-1), the plan now commits to an accessible Linux platform layer at the same bar as Windows and macOS (LINUX-2).
- Collaboration. Real-time multi-user editing stays deliberately out of scope (with the reason recorded), but the plan commits to local-first, accessible asynchronous review and sharing so collaboration is not a blank (COLLAB-1).
- Ecosystem. The plan commits to a documented plugin capability and signing model and a review process, so a safe third-party ecosystem can grow off the experimental flag (ECO-1, building on SEC-8).
- Localization depth. The plan commits to full UI and core-documentation localization for the launch languages, with a process to keep translations current (L10N-1).

These are large (XL) investments and are sequenced into Tier 6 after the 1.0 wins, but they are now part of the committed plan, so the honest answer to "what would still fall short?" is: nothing of substance. The only remaining limits are deliberate scope choices (no real-time co-editing) and the permanent reality that a living product keeps improving with user feedback.


---

## Changelog

### 2026-06-10

#### EdSharp selection parity

Eight new selection commands implementing the EdSharp F8-based anchor model:

- `edit.start_selection` (F8): sets an anchor at the cursor position
- `edit.complete_selection` (Shift+F8): selects anchor to cursor, announces span
- `edit.reselect` (Ctrl+Shift+F8): restores the last committed selection
- `edit.go_to_start_of_selection` (Alt+Shift+F8): moves cursor to selection start
- `edit.copy_all` (Ctrl+F8): copies the entire document
- `edit.unselect_all` (Ctrl+Shift+A): collapses selection to cursor
- `edit.say_selected`: announces selected text via screen reader
- `edit.read_all` (Alt+F8): reads the document from the beginning
- `edit.toggle_extend_selection_mode`: improved entry/exit announcements with anchor position and span

All eight appear in the Selection menu and command palette.

#### QUILL key improvements (QK-6, QK-7, QK-8)

- **QK-6 earcons**: Four custom WAV file path settings (`quill_key_sound_enter`, `quill_key_sound_exit`, `quill_key_sound_move`, `quill_key_sound_error`) exposed in Preferences > Navigation and QUILL Key with a Browse button. `_play_quill_sound` tries the WAV path first and falls back to beeps when no path is set.
- **QK-7 mental model clarity**: Prefix mode announcement now names both modes, says "press again for sticky mode" and "? for help". Browse mode entry announcement is condensed and adds "period repeats last action".
- **QK-8 repeat last action**: Period key (.) in browse mode repeats the previous browse action. Reports "No previous QUILL action" with an error earcon if nothing has been run yet.

#### Selection features (SEL-1, SEL-2, SEL-3, SEL-4, SEL-5)

- **SEL-1 bindings**: `edit.select_paragraph` bound to Ctrl+Alt+P; `edit.select_block` to Ctrl+Shift+B. Both announce scope and word count. Both now appear in the Selection menu.
- **SEL-2 bindings**: `edit.expand_selection` bound to Alt+Shift+Up; `edit.shrink_selection` to Alt+Shift+Down. Both appear in the Selection menu.
- **SEL-3**: QUILL key + A with text selected opens scope-aware selection actions (already implemented, marked done).
- **SEL-4 named marks and review buffer**: Three new commands — `set_named_mark` (prompts for a name and stores the cursor position), `jump_to_named_mark` (pick from a list, jump to position with line/column announcement), `open_review_buffer` (opens selection in a read-only dialog for non-destructive screen-reader paging). All accessible via Selection > Named Marks submenu and command palette.
- **SEL-5 status bar indicator**: Extend selection mode now shows an "EXT" badge in the status bar whenever active, using the same dynamic-pane mechanism as the QUILL key indicator. Entry and exit already announced in a prior session.

#### Roadmap maintenance

Removed completed sections and backlog rows: QUILL key section (§3, QK-6/7/8/6b), selection section (§5, SEL-1 through SEL-5). Stale references to these IDs updated throughout narrative and tier tables.


---

<!-- Source: docs/planning/aa.md -->

# Research: integrating Accessibility Agents (`s:\code\agents`) into QUILL

Status: research proposal for review. Nothing here is approved or built. If
accepted, this becomes a new tier inserted after Tier 3 (GLOW), pushing the
current Tiers 4, 5, and 6 down to 5, 6, and 7. A bookmark is recorded in
`ROADMAP.md` so the decision is not lost.

This document evaluates the `s:\code\agents` repository (the Community Access
"Accessibility Agents" project) and proposes a concrete, QUILL-shaped way to
adopt the parts that fit, while being honest about the parts that do not.

## 1. What the project is

Accessibility Agents is an MIT-licensed, open-source ecosystem of about 80
specialized AI agents plus a Node.js MCP server, organized into teams (web,
document, GitHub workflow, developer tools, standards, and orchestrators). Its
premise is that LLMs drop accessibility context by default, so it packages
accessibility expertise as agents, skills, instructions, and scanning tools that
run across five host platforms: Claude Code, GitHub Copilot, Gemini CLI, Codex
CLI, and a standalone MCP server.

Key facts that shape integration:

- License: MIT (Copyright 2026 Taylor Arndt). Permissive; compatible with QUILL.
- The agents themselves are Markdown/YAML/TOML prompt definitions meant to run on
  external LLMs (Claude, Copilot, Gemini). That conflicts with QUILL's
  local-first, no-silent-network rule unless gated behind explicit consent.
- The MCP server is Node.js. It exposes 24 scanning tools over MCP (stdio or HTTP
  on localhost:3100), several of which are pure local scanners.
- It already contains a "GLOW bridge" (`glow_audit_document`, `glow_fix_document`,
  `glow_convert_document`, `glow_generate_report`, `glow_health_check`), so the
  project and QUILL's Tier 3 GLOW engine are designed to interoperate, not
  compete.
- It ships a `wxpython-specialist`, a `desktop-a11y-specialist`, and a
  `desktop-a11y-testing-coach` agent — desktop, Windows-UIA, and NVDA/JAWS/Narrator
  knowledge directly relevant to QUILL's own development.

## 2. Honest fit assessment

Most of the project is built for web developers and CI pipelines, not for a
local-first desktop writing app. The table separates what realistically fits
QUILL from what does not.

| Component | Fits QUILL? | Why |
| --- | --- | --- |
| MCP server document scanners (Office, PDF, EPUB, Markdown) | Partial | Useful as an optional, local audit backend, but overlaps GLOW (Tier 3). Adopt only where additive. |
| MCP axe-core and Playwright web scanners | Yes | QUILL authors and exports HTML; axe-core/Playwright audit that live markup, which GLOW does not cover. Clean additive value. See Workstream E. |
| GLOW bridge MCP tools | Yes (inverted) | Instead of QUILL calling them, QUILL can expose its own GLOW engine the way the bridge expects, so the wider ecosystem can audit through QUILL. |
| `wxpython-specialist`, `desktop-a11y-specialist`, `desktop-a11y-testing-coach` agents | Yes | Read-only knowledge sources for QUILL's own contributors; can seed QUILL's repo instructions and testing docs. |
| The 80-agent Copilot/Claude/Gemini/Codex packs | No | They run on external LLMs and target web/GitHub workflows; not a runtime feature of a desktop app. |
| VS Code extension | No | QUILL is not a VS Code surface. |
| GitHub Action | Repo-only | Could guard the QUILL repo's own docs/sample-document accessibility in CI, but is not part of the shipped app. |
| Go CLI installers | No | Platform setup for the agents project itself. |

## 3. The core tension to resolve first

QUILL's non-negotiables are local-first operation, no silent network calls, and
explicit per-action consent before any document content leaves the machine. The
Accessibility Agents that add the most "magic" (the LLM-driven specialists) are
inherently networked. Therefore any agent-backed capability in QUILL must:

- be a feature behind `FeatureManager` (FLAG-1), off by default;
- reuse QUILL's existing consented AI provider layer (AI-13 and the connection
  error taxonomy already built), never a second parallel network path;
- pass the GATE-9 no-silent-network egress audit, with every outbound call
  reviewed and announced;
- degrade gracefully to the fully local GLOW engine when AI is off.

The local MCP scanners and the desktop-knowledge agents do not have this tension
and are the safe first steps.

## 4. Proposed integration shape (if approved)

The work splits into four workstreams, ordered from lowest risk and highest
certainty to highest ambition. These would become the backlog IDs of the new
tier (proposed prefix `AX-` for "accessibility agents").

### Workstream A: adopt the desktop-accessibility knowledge (no runtime change)

- Bring the `wxpython-specialist`, `desktop-a11y-specialist`, and
  `desktop-a11y-testing-coach` guidance into QUILL's own repository memory and
  contributor instructions, attributed under MIT, as a curated distillation (not
  a wholesale copy).
- Outcome: QUILL contributors get the community's wxPython and Windows-UIA and
  screen-reader testing patterns without any network or runtime dependency.
- Risk: none. Pure documentation. This can happen even if the rest is declined.

### Workstream B: a local accessibility-audit backend via the MCP server

- Treat the Accessibility Agents MCP server as an optional, locally spawned audit
  backend for the structured formats QUILL reads (DOCX, PPTX, XLSX, PDF, EPUB,
  Markdown), behind a new feature id (for example `core.ax_audit`), off by
  default.
- QUILL talks to it over stdio MCP from a small Python client in `core` (UI
  agnostic), spawning the Node process only on demand and only for local files.
- The findings are normalized into the same finding shape GLOW-3 already defines,
  so the existing navigable, screen-reader-pageable report surface renders them
  with no new UI.
- Honesty: this overlaps GLOW. The rule is that the MCP backend is only adopted
  where it is genuinely additive to GLOW (for example a format or check GLOW does
  not cover), and the report always names which engine produced each finding
  (consistent with GLOW-6).
- Dependency reality: this adds an optional Node.js runtime. It must be a clearly
  optional extra (like the `glow` extra), never a hard dependency, with a clean
  "backend unavailable" path and an announced reason.

### Workstream C: expose QUILL's GLOW engine the way the bridge expects

- The agents project already defines a GLOW bridge contract. Rather than QUILL
  consuming it, QUILL can present its Tier 3 GLOW capability through the same
  contract so the broader Accessibility Agents ecosystem can audit and fix
  through QUILL's engine.
- This is the cleanest division of labor: one shared accessibility engine
  (`quill-glow-core`, per Tier 3), surfaced to both QUILL's in-editor reports and
  any MCP client.
- Gated by the same GLOW consent rules (GLOW-7) and the no-silent-network audit.

### Workstream D: consented, agent-assisted remediation (most ambitious)

- For fixes that genuinely need an LLM (for example drafting alt text or plain
  language rewrites), reuse the agent prompts as the instruction layer on top of
  QUILL's own consented AI provider, never the agents' external LLM paths.
- Every such action is explicit, announced, reviewable (apply-and-undo, matching
  AI-7), and off by default.
- This is where the "agent team that will not let accessibility slide" idea meets
  QUILL's Accessibility agent (AGENT-1) flagship; the two should share one
  surface, not build two.

### Workstream E: axe-core / web accessibility check on authored and exported HTML

This is a strong, concrete fit that the rest of this proposal hinted at but is
worth calling out on its own, because QUILL is not only a plain-text editor: it
reads and writes HTML through `quill/io`, it has a browser preview surface, and
GLOW-5 will add accessible HTML export. So the HTML a user authors or is about to
publish is real web content that an axe-core check applies to directly.

- What it does: run an axe-core (WCAG 2.2 AA) audit over the current HTML
  document, the exported HTML, or a selection, and present the violations in the
  same navigable, screen-reader-pageable findings surface GLOW-3 defines (rule id,
  impact, the offending element, a plain-language explanation, and a one-key jump
  to the location in the editor).
- How it runs, honoring local-first: the agents project's MCP server already
  bundles axe-core and Playwright and exposes `run_axe_scan`,
  `run_playwright_keyboard_scan`, `run_playwright_contrast_scan`, and
  `run_playwright_state_scan`. QUILL spawns that local MCP backend on demand
  (the same Node process as Workstream B), feeds it a local file or a
  `file://` URL for the rendered HTML, and never touches the network. There is no
  remote service and no document content leaves the machine.
- Two depths, user's choice:
  - Static check: axe-core run against the HTML source or a headless render of
    it. Fast, covers structure, ARIA, contrast, labels, headings, link text,
    landmarks, and the common WCAG failures. This is the default.
  - Behavioral check: the Playwright scanners add keyboard-traversal,
    dynamic-state, and runtime-contrast passes for HTML with interactivity. This
    is heavier and opt-in.
- Where it surfaces: a Tools command ("Check web accessibility (axe-core)"), the
  QUILL key, and — for export — an optional pre-publish gate on GLOW-5 accessible
  HTML export so a user can choose to be warned before shipping inaccessible
  markup. It also slots cleanly into the WATCH-2 action registry so a watched
  folder of HTML files is audited automatically.
- Relationship to GLOW: complementary, not duplicative. GLOW's strength is
  document formats (DOCX, PPTX, XLSX, PDF, EPUB) and QUILL's own text-level
  checks; axe-core is the established engine for live HTML/DOM accessibility,
  which GLOW does not run. The findings surface names which engine produced each
  result (consistent with GLOW-6), so the user always knows whether a finding came
  from GLOW, QUILL, or axe-core.
- Guardrails: behind its own feature id (for example `core.ax_web_audit`), off by
  default, no hard Node.js dependency, a clean "axe-core backend unavailable"
  path with an announced reason, and registered in the GATE-9 egress audit even
  though the scan is local (so the no-silent-network promise is provably kept).
- Honest caveat to keep in the product: axe-core, like all automated tooling,
  catches roughly a third to a half of real issues. The surface should repeat the
  project's own warning that automated checks are a starting point, not a
  substitute for testing with NVDA, JAWS, and keyboard-only navigation.

#### The wider Web Accessibility team (beyond axe-core)

axe-core and the Playwright passes are the engine, but the project's Web
Accessibility team is mostly a set of LLM-driven specialist agents that explain
and remediate rather than just flag. They are the natural "explain and fix"
layer on top of the static scan, and they matter to QUILL because the HTML a user
authors or exports is exactly their domain. The relevant specialists:

- `aria-specialist` — ARIA roles, states, properties, and widget patterns
  (the First Rule of ARIA, allowed children, deprecated roles).
- `keyboard-navigator` — tab order, focus management, focus restoration,
  keyboard shortcuts.
- `contrast-master` — colour contrast, dark mode, focus-indicator visibility.
- `forms-specialist` — label association, error identification, validation
  messages, multi-step flows.
- `modal-specialist` — dialog focus trapping, escape behaviour, focus
  restoration.
- `live-region-controller` — dynamic announcements (toasts, loading states,
  ARIA live politeness).
- `alt-text-headings` — alt text for images and SVGs, heading hierarchy,
  landmarks.
- `tables-data-specialist` — data-table markup, scope, captions, complex-table
  descriptions.
- `link-checker` — ambiguous or repeated link text and link purpose.
- `i18n-accessibility` — language tagging, RTL, multilingual content.
- `web-issue-fixer` and `playwright-verifier` — apply a fix and then re-run the
  behavioural scan to confirm it actually resolved.

How these fit QUILL, honestly:

- They are prompt-defined agents that run on an LLM, so in QUILL they are not a
  separate runtime. They become the instruction layer on top of QUILL's own
  consented AI provider (the same rule as Workstream D), turning a raw axe-core
  violation into a plain-language explanation and a reviewable, apply-and-undo
  fix in the editor. A contrast finding is explained by `contrast-master`; a
  missing label is fixed by `forms-specialist`; a bad heading order is repaired
  by `alt-text-headings`.
- The split of labour is clean: the static scanners (axe-core, Playwright) find
  and locate the issue with zero network and zero AI; the specialist agents,
  only when the user turns AI on and consents, explain and propose the fix; the
  `web-issue-fixer`/`playwright-verifier` loop re-scans to prove the fix worked.
  A user who keeps AI off still gets the full local scan and the navigable
  findings list — they just do not get the AI-written explanations and fixes.
- This is the web counterpart of QUILL's Accessibility agent (AGENT-1). The two
  should share one findings-and-remediation surface, with these specialists as
  the web-specific knowledge the agent draws on, never a parallel UI.

What we would still leave out: the team's framework-specific agents (React, Vue,
Svelte, Tailwind, Next.js, design-system auditors, web components, email and
mobile) target code a writing app does not produce, so they stay out of QUILL.
QUILL adopts only the document-level HTML specialists that apply to authored and
exported pages.

#### Running axe-core with no Node.js, no network, and no visible UI

The question of whether axe-core needs Node.js is important, and the answer is
no. axe-core is a single self-contained JavaScript file with zero runtime
dependencies — Node.js is only one of several ways to host it. QUILL already
embeds the engine that hosts it best: the accessible Edge WebView2 component
(`wx-accessible-webview`, already used by the assistant panel and the web-form
helper). The plan is therefore to run axe-core inside QUILL's own process, not
through an external Node backend.

How it works, concretely:

- Vendor the single minified `axe.min.js` (about half a megabyte, MIT/MPL-2.0)
  into QUILL as a bundled asset. It ships inside the app; there is no download
  and no per-scan bandwidth at all.
- Create the WebView2 control off-screen and never attach it to a visible
  window, so the scan is a silent review: the user sees no browser, no flash, no
  pop-up. The control is created, used, and destroyed entirely in the background.
- Load the HTML to audit into that off-screen control from a local
  `file://`/temp source (the current document's HTML, the exported HTML, or a
  selection). Nothing leaves the machine.
- Inject the bundled `axe.min.js` and call `axe.run(...)` via the WebView's
  script-execution path (the same `RunScript`/`ExecuteScript` bridge QUILL
  already uses), then read back the JSON result.
- Normalize that JSON into the shared finding shape (GLOW-3) so the results are
  announced and reviewed through the existing surface — or, in pure-silent mode,
  simply counted and logged for a watch action with no surface at all.

Why this is the right fit for QUILL:

- No Node.js runtime, no npm, no separate process, and no MCP server are required
  for the static axe-core scan. WebView2 is already a QUILL dependency on
  Windows, so the only thing added is a vendored JS file. (The optional Node MCP
  backend from Workstream B remains relevant only for the heavier Playwright
  behavioural passes; the everyday HTML check does not need it.)
- It is genuinely zero-bandwidth after install: the engine is bundled, the scan
  is local, and the GATE-9 egress audit can prove no outbound call exists.
- It is silent by construction: an off-screen WebView means there is no UI to
  show, which is exactly the behaviour we want for a background or watch-driven
  review.

On a pure-Python alternative (no WebView at all): there is no faithful pure-Python
port of axe-core's full WCAG ruleset. The existing Python packages
(`axe-core-python`, `axe-selenium-python`) only drive axe-core through Selenium,
which means a real browser plus a webdriver — heavier and less self-contained
than QUILL's own WebView2, not lighter. Pure-Python HTML linters exist but apply
a small, different rule set and are not axe-core. So the recommended path is the
bundled-`axe.min.js`-in-the-offscreen-WebView approach above: it is the
lowest-bandwidth, no-Node, no-UI option and it reuses infrastructure QUILL
already ships. A small pure-Python structural pre-check (headings, alt text, link
text, lang) can run as a fast first pass for environments where WebView2 is
unavailable, with axe-core as the authoritative engine when it is present.

The silent-review default: unless the user explicitly opens the findings surface,
the axe-core check runs with no visible UI — created off-screen, executed,
results captured, control torn down — so it is safe to run as a background
pre-publish check or a WATCH-2 action over a folder of HTML without ever
interrupting the writer. The navigable findings dialog (GLOW-3) is shown only on
demand.

## 5. What we would deliberately not do

- Not bundle the 80-agent multi-platform packs into the shipped app.
- Not add the VS Code extension, Gemini, or Codex surfaces.
- Not introduce a second AI network path or a second settings or consent store.
- Not make Node.js a hard runtime dependency of QUILL.
- Not duplicate GLOW; where they overlap, GLOW is the engine and the agents are
  additive guidance or an optional alternate backend.

## 6. Open questions for review

1. Is the optional Node.js MCP backend (Workstreams B and E) acceptable, or
   should QUILL stay pure-Python and take only Workstreams A and C? Note that the
   axe-core web check (E) is the single most concrete user-facing win and the main
   reason to accept the optional Node backend.
2. Should agent-assisted remediation (Workstream D) be folded entirely into the
   existing Accessibility agent (AGENT-1) flagship rather than a separate tier?
3. Do we want QUILL to be a GLOW provider to the ecosystem (Workstream C), or keep
   the engine in-app only?
4. Sequencing: this tier is proposed to land after Tier 3 (GLOW) because B, C, and
   D all build on the shared GLOW engine. Confirm that ordering.

## 7. Proposed tier placement

If approved, insert as the new Tier 4, immediately after GLOW:

- Current Tier 4 (structural health and performance) becomes Tier 5.
- Current Tier 5 (BITS Whisperer transcription) becomes Tier 6.
- Current Tier 6 (documentation) becomes Tier 7.

Rationale: the valuable QUILL-shaped pieces (B, C, D) depend on the shared GLOW
engine from Tier 3, and documentation should still land last so it describes a
product that is already GLOW-native, agent-assisted, and transcription-capable.

## 8. Bottom line

The realistic value to QUILL is narrower than the project's breadth suggests, but
real: a curated desktop-accessibility knowledge base for contributors
(Workstream A, zero risk), an optional additive local audit backend that reuses
the existing report surface (Workstream B), a clean way to share one GLOW engine
with the wider ecosystem (Workstream C), a consented path to agent-assisted
remediation that folds into QUILL's own Accessibility agent (Workstream D), and an
axe-core / Playwright web accessibility check on the HTML a user authors or
exports (Workstream E) that runs entirely locally and fills the one gap GLOW does
not cover. The MIT license, the bundled axe-core engine, and the existing GLOW
bridge make this feasible; QUILL's local-first and no-silent-network rules define
the guardrails. Everything else in the project is for web teams and CI, and we
leave it there.


---

<!-- Source: docs/planning/pi.md -->

# Learning from Pi: deriving the magic for QUILL

Status: research note for review. Nothing here is approved or built. Pi itself is
not adoptable by QUILL (it is ~93% TypeScript, ships as npm packages, runs on
Node.js, and is a coding agent with a redraw-heavy TUI that fights screen
readers). But its *design* is excellent, and several of its ideas translate
directly into QUILL's accessible, local-first writing context. This note
separates the transferable magic from the parts we leave behind.

Source: `earendil-works/pi` (MIT), `pi.dev/docs/latest`. Identified as the Pi
Agent Harness: a minimal terminal coding agent plus a unified LLM API, agent
runtime, and TUI library.

## Why Pi is worth learning from

Pi's stated philosophy is "stay small at the core, extend everything else."
Around that core it has solved, unusually well, four problems QUILL also has:
managing AI providers, managing long conversations, carrying durable context,
and integrating from another language. Those solutions are the magic.

## The magic, mapped to QUILL

### 1. Subscription login, not just API keys (the biggest accessibility win)

Pi lets a user authenticate with an existing Claude Pro/Max, ChatGPT Plus/Pro, or
GitHub Copilot subscription via an interactive `/login` flow, storing credentials
locally — no API key required. For a blind or low-vision user, "sign in with the
subscription you already have" is dramatically more accessible than "create an
API key, copy this 51-character secret, paste it without seeing it."

For QUILL: add a guided, fully keyboard-and-screen-reader login that can use an
existing subscription where the provider supports it, alongside the current API
key path. Must honor QUILL's rules: credentials in DPAPI, explicit consent, no
silent network, and the GATE-9 egress audit. This is the single most user-facing
piece of magic to derive. Maps to AI-13 and the existing connection settings.

### 2. Conversation sessions that branch, fork, and resume

Pi treats the conversation as a durable, navigable tree: sessions auto-save,
`-c` continues the latest, `-r` browses past ones, and `/fork` and `/clone`
branch the conversation so a user can try two approaches without losing state.

For QUILL this is genuinely category-defining for *writing*, not just coding: a
writer could branch a draft ("rewrite this section two different ways and let me
compare"), keep both, and resume later, all by keyboard with announced state.
QUILL already has Save Session/Open Session and an assistant transcript; this
elevates them into a first-class, branchable, resumable writing-with-AI history.
The accessible surface is a navigable list/tree of session branches, each
announced, with one-key jump and compare. Candidate new backlog cluster.

### 3. Durable context/instruction files the AI cannot drop

Pi loads `AGENTS.md`/`CLAUDE.md` at startup (a global one plus a per-project one)
so the model always honors project-specific instructions, with `/reload` to pick
up edits live. The magic is that the guidance never falls out of context.

For QUILL: a per-document or per-project "writing instructions" file (house
style, tone, words to avoid, audience) that the assistant always honors and that
the user can edit and reload. This pairs naturally with QUILL's existing Train
Writing Style feature — train the voice, and pin the rules. Honest, visible, and
user-owned. Candidate backlog item.

### 4. A language-agnostic integration boundary (RPC / JSON event mode)

This is the most important architectural lesson and it solves the exact problem
that blocked direct adoption. Pi exposes three non-interactive surfaces: a
one-shot `-p` mode (pipe text or files in, get a result), a `--mode json`
structured event stream, and a `--mode rpc` that talks JSONL over stdin/stdout so
*any language* can drive it. Pi is TypeScript, yet a Python app can integrate it
cleanly over stdio without sharing a runtime.

For QUILL: this is the template for how QUILL should consume *any* external agent
engine — Pi, the Accessibility Agents MCP server (see `aa.md`), or future tools —
without language lock-in: spawn a local subprocess, speak JSONL/MCP over stdio,
keep it off by default, consent-gated, and covered by the egress audit. Adopt the
*pattern*, not the package. This directly de-risks the `aa.md` Workstream B/E
question about non-Python backends.

### 5. Model switching with speed/cost tiers, mid-session

Pi switches models mid-session (`/model`, Ctrl+L) and cycles "thinking levels"
(Shift+Tab): a fast cheap model to explore, a smarter one to finalize.

For QUILL: let the user pick a fast/local model for quick edits and a stronger
one for a careful rewrite, switchable mid-task with an announced change, surfaced
in the existing AI model panel. Local-first means the fast tier can be an
on-device model. Small, high-value refinement to the AI model surface.

### 6. Compaction for long sessions

Pi compacts context and summarizes branches so long sessions stay within the
window without losing the thread.

For QUILL: a long writing-and-editing session with the assistant should compact
gracefully and announce when it does, rather than silently truncating. A quietly
important reliability feature for real, long-form work.

### 7. Inline command output, with an opt-out from context

Pi's `!cmd` runs a command and feeds the output to the model; `!!cmd` runs it
without adding the output to the context window — explicit control over what the
model sees.

For QUILL the transferable idea is the *control*, not shell access: when a user
pulls in external text (a file, a quote, a snippet), they should be able to
choose whether it enters the AI's context. A small honesty-and-privacy
refinement, not a shell feature.

### 8. Supply-chain hardening as a posture

Pi pins exact dependency versions, sets a minimum release age to avoid same-day
supply-chain attacks, installs with `--ignore-scripts`, and treats the lockfile
as ground truth.

For QUILL: this matches the existing GATE/SEC ladder and is worth mirroring for
any new optional Node-based backend we add (per `aa.md`): pin it, age-gate it,
no install scripts, audited.

## What we deliberately do not take from Pi

- The TypeScript/Node codebase and npm packages — wrong runtime for QUILL.
- The coding-agent identity (read/write/edit/bash on a repo) — QUILL is a writing
  app for end users, not a dev tool.
- The differential-rendering TUI — dynamic terminal redraws are hostile to
  NVDA/JAWS/Narrator; QUILL stays with stock, accessible controls.
- `pi-ai` as a dependency — QUILL already has a consented multi-provider layer;
  we study Pi's API design, we do not import it.

## The one-line takeaway

Pi's reusable magic for QUILL is four ideas: subscription login instead of
pasted API keys, branchable/resumable AI sessions, durable per-document writing
instructions, and a language-agnostic stdio/JSON integration boundary for
external engines. The first three are user-facing delight; the fourth is the
architecture that makes both `aa.md` (Accessibility Agents) and any future
external engine safe to adopt from a Python app. We derive the patterns; we do
not take the code.


---

<!-- Source: docs/planning/glow.md -->

# Tier 3 plan: the GLOW accessibility suite

This document is the full, reviewable plan for Tier 3 of QUILL: making QUILL
accessibility-native by adopting GLOW as its shared accessibility engine. It is
written so you can review the intent and the cross-repo coordination while the
work is in progress. It expands on section 19 and section 21 of `ROADMAP.md` and
the GLOW-1 through GLOW-7 and WATCH-8 backlog rows, and it is the source of truth
for what changes land in each of the three repositories.

This is a planning document. Nothing here is built yet. Items are tracked in
`ROADMAP.md` under the GLOW IDs.

## 1. The goal in one sentence

A user opens any real document in QUILL, runs a full accessibility audit in
place, hears the findings as a navigable spoken list, applies reviewable fixes,
and publishes clean accessible output, all by keyboard and voice, using exactly
the same rules that the GLOW desktop and web apps use.

## 2. The three repositories and their roles

Tier 3 spans up to three separate repositories. Each is committed on its own, and
the shared API between them is kept stable so they can move independently.

| Repo | Path | Role in the suite |
| --- | --- | --- |
| QUILL | this repo | The presentation layer. In-editor reports, the editor shell, onboarding, keyboard and screen-reader surfaces. Consumes the shared core. |
| quill-glow-core | `s:\code\quill-glow-core` | The shared contract. A stable host-facing API that both QUILL and the GLOW apps call. Package `quill_glow_core`, public API in `src/quill_glow_core/services.py`. |
| glow | `s:\code\glow` | The rule engine. The canonical accessibility engine (`acb_large_print_core`) plus the GLOW desktop and web apps. |

Important: `s:\code\glow-7.0.0` is a stale snapshot. It is ignored entirely. Do
not read it and do not modify it.

The boundary is deliberately clean: shared rules and fixers live in
`quill-glow-core`, and three thin presentation layers sit on top (QUILL in-editor,
GLOW desktop, GLOW web). QUILL never absorbs GLOW's web app, its branding-profile
deployment machinery, or its template-generation server flows.

## 3. The shared contract (quill-glow-core)

The shared library already exposes a stable host-facing API. QUILL calls into it
rather than reimplementing rules:

- `configure_default_services`: set up the engine and its fallbacks.
- `audit_by_extension`: audit a document, dispatched by file type.
- `fix_by_extension`: apply fixes, dispatched by file type.
- `convert_to_markdown`: the conversion entry point.
- `get_component_versions`: report which engine and rule version is active.
- `from_glow_backend`: bridge that wires the shared core to the canonical
  engine `acb_large_print_core`.

The dispatch core has two backends behind it:

- The GLOW backend, present when the optional dependency is installed, gives
  QUILL the full ACB Large Print, APH, WCAG 2.2 AA, and Microsoft Accessibility
  Checker rule sets across Word, Excel, PowerPoint, PDF, EPUB, HTML, and
  Markdown.
- A safe no-op fallback (`NoOpCoreServices`), used when the backend is absent,
  keeps QUILL fully functional with its existing text-level behavior and no
  crash.

## 4. The current QUILL surface that Tier 3 replaces

QUILL already contains `quill/core/glow.py`, a text-level GLOW audit and fix
surface: generic link-text detection, plain-language lint, and audit and fix
reports for the selection or document, wired to commands such as
`tools.glow_fix_document` and `tools.glow_fix_selection`. Tier 3 keeps these
friendly in-editor reports as the presentation layer and routes the actual rule
checking and fixing through the shared core instead of the bespoke checks.

## 5. The ordered plan

### Step 0 (prerequisite, part of GLOW-1): get the glow repo green

Before QUILL depends on `quill-glow-core`, the `glow` repo must build green.

- The consumed desktop core (`acb_large_print` / `acb_large_print_core`, the
  target of `from_glow_backend`) is already green at 308 tests.
- The failing part is the Flask web suite (`acb_large_print_web`): the `/guide/`
  content string, branding injection, and form-POST tests.
- Reconcile the version sweep (VERSION 8.0.0 against README against TODO.md).
- Commit the fix in the `glow` repo so the whole engine is green, so QUILL
  builds on a stable engine rather than inheriting breakage.

### Step 1 (GLOW-1): adopt quill-glow-core as the shared engine

- Add a new optional extra to QUILL: `glow = ["quill-glow-core[glow]"]`.
- QUILL audits and fixes via `quill-glow-core`, using the GLOW backend when
  present and the `NoOpCoreServices` fallback when absent.
- `quill/core/glow.py` becomes a thin presentation shim plus a
  `_glow_finding_to_quill` adapter. The adapter maps GLOW severities
  (critical and high) to QUILL's `error` level and carries `score`, `grade`,
  and ACB `metadata` through to the report.
- In-editor reports are unchanged for users.
- Tests cover both the backend path and the fallback path.

Status (QUILL side, done): the optional `glow` extra is declared, and
`quill/core/glow.py` gained a file-based seam — `audit_file`/`fix_file`,
`get_glow_services`, `glow_backend_available`, and the `_glow_finding_to_quill`
adapter (critical/high -> `error`, medium-band -> `warning`, low -> `info`;
`score`/`grade` carried on `GlowFileAuditResult`, ACB `metadata` and location
folded into the suggestion). The existing in-editor text reports
(`audit_text`/`fix_text`/`build_audit_report`) are untouched, and
`tests/unit/core/test_glow_backend.py` exercises both the backend and the
fallback paths. `quill_glow_core` is registered in the mypy ignore-missing list
so the scoped strict gate stays green. Remaining for GLOW-1: complete and verify
Step 0 in the `glow` repo (green Flask web suite + version reconciliation).

### Step 2 (GLOW-2, with IO-1): audit and fix by structure, not just text

- Today QUILL audits plain text, Markdown, and HTML.
- Extend it through the shared core to audit and, where supported, fix the
  structured formats QUILL already reads: DOCX, PPTX, XLSX, PDF, and EPUB.
- A user can open a real document and run a full accessibility audit in place.

### Step 3 (GLOW-3, with AGENT-1 and AI-7): the in-editor report that reads beautifully

- Present GLOW findings as a navigable, screen-reader-pageable list grouped by
  severity.
- Each finding has a one-key jump to its location, a plain-language
  explanation, and, where fixable, a reviewable apply-and-undo.
- This is the same surface the Accessibility agent (AGENT-1) drives later.

### Step 4 (GLOW-4, with SET-1): standards profiles as a setting

- Surface GLOW's profiles (ACB 2025 Baseline, APH Submission, Combined Strict)
  as a QUILL setting.
- The active profile is shown in every report for traceable evidence.

### Step 5 (GLOW-5, realizing FEAT-17): one-key accessible publish

- Reuse GLOW's conversion chain (MarkItDown plus Pandoc, with
  LibreOffice-assisted pre-conversion and PyMuPDF table preservation).
- QUILL exports clean, accessible Word, HTML, EPUB, and PDF with announced
  results.

### Step 6 (GLOW-6): show the active engine and rule version

- Use `get_component_versions` and the startup telemetry so QUILL can display
  which accessibility engine and rule version is active.
- Surface it in `diagnostics.py` and the About dialog, keeping the honesty
  principle.

Status: Done. `quill/core/glow.py` adds `GlowEngineVersions`,
`glow_engine_versions()` (reads the backend name and `get_component_versions`,
sorts components, never raises), and `glow_engine_version_summary()`. The
diagnostics environment info carries a `glow_engine` key through a
try/except-wrapped `_safe_glow_engine_summary()`, and the About dialog shows the
same summary. Verified against the live backend (release 8.0.0); the fallback
yields "GLOW engine: not installed" when the backend is absent. Covered by
`tests/unit/core/test_glow_backend.py`.

### Step 7 (GLOW-7): consent gate for optional AI and network features

- GLOW's optional networked features (AI alt-text generation, Presidio PII
  redaction, WCAG language processing) are off by default.
- When a user enables one, it is gated by an explicit per-action consent prompt
  with visible progress and outcome, honoring QUILL's no-silent-network rule and
  the GATE-9 egress audit.
- A test asserts the defaults are off and that no GLOW path performs a silent
  outbound call.

Status: In progress. The core contract and consent UI are done — the
`GlowNetworkConsent` model (all three features off by default), consent-gated
`audit_file`/`fix_file`, the Settings flags (`glow_enabled` on by default plus
the three consent flags off), the "GLOW Accessibility" Preferences entry, and
the Startup Wizard GLOW step (both sanctioned `web` surfaces). Remaining: the
per-action consent prompt at audit time, which lands with the in-editor report
(GLOW-3).

## 6. How Tier 3 connects to the rest of QUILL

- Watch Profiles (Tier 2): once GLOW lands, WATCH-8 registers an "audit and fix
  accessibility" watch action through the WATCH-2 registry, so a watched folder
  of documents is audited and fixed automatically against a chosen standards
  profile, reversibly, with findings surfaced in the queue outcome. Until GLOW
  is present, the action advertises itself as unavailable with an announced
  reason.
- Feature flags: the GLOW capability gets a feature id (`core.glow`) and honors
  `FeatureManager`. When the feature is off, its commands, the watch action, and
  its menu entries disappear in lockstep, and no GLOW path runs.
- The Accessibility agent (Tier 2 flagship, AGENT-1): drives the same GLOW-3
  report surface to make documents accessible step by step, reversibly, by
  keyboard and voice.

## 7. What stays out of QUILL

QUILL consumes the shared core. It does not absorb:

- GLOW's web application.
- GLOW's branding-profile deployment machinery.
- GLOW's template-generation server flows.

The GLOW desktop and web apps remain the heavyweight authoring and batch
surfaces. QUILL is the in-editor accessibility home.

## 8. Acceptance and definition of done

Tier 3 is done when:

- The `glow` repo is green and committed (Step 0).
- QUILL audits and fixes through `quill-glow-core` with both backend and
  fallback paths tested (GLOW-1).
- Structured formats audit in place (GLOW-2).
- The report is a navigable, spoken, reviewable surface (GLOW-3).
- Standards profiles are selectable and shown in every report (GLOW-4).
- One-key accessible publish works with announced results (GLOW-5).
- The active engine and rule version are visible (GLOW-6).
- Optional networked features are off by default and consent-gated, with a test
  proving no silent egress (GLOW-7).
- Every change is committed in its own repo and the shared API stays stable.

## 9. Risks and how the plan handles them

- Cross-repo breakage: the shared API is kept stable and each repo is committed
  independently, so a change in the rule engine does not silently break QUILL.
- Missing backend: the `NoOpCoreServices` fallback keeps QUILL fully functional
  when the GLOW backend is not installed.
- Silent network calls: GLOW-7 plus the GATE-9 egress audit make any outbound
  call explicit, consented, and tested.
- Inheriting a red engine: Step 0 requires the `glow` repo to be green before
  QUILL depends on it.

## Maintenance note

Keep this document in step with the GLOW backlog rows in `ROADMAP.md`. When a
GLOW item changes scope or status, update both this file and `ROADMAP.md` in the
same change.


---

<!-- Source: docs/planning/editors.md -->

# Editors.md — Competitive Analysis and Design Synthesis for QUILL

> Author: this document. Date: 2026-06-01. Scope: a working competitive
> analysis of QUILL against leading general-purpose, programmer, and
> prose editors; a feature matrix; an honest gap analysis with industry
> expectations; a recommended menu consolidation; a Ulysses/Obsidian/Scrivener-
> inspired redesign of Workspaces and the Document Navigator that is
> unmistakably QUILL in spirit; and a long list of "make it amazing"
> proposals. Every recommendation is written for a screen-reader-first
> Windows desktop app whose north star is the QUILL key, Quick Nav, and
> the dialog contract.

---

## 1. Executive summary

QUILL is already a strikingly opinionated editor: stock controls in the
writing path, a screen-reader-first design, the QUILL key chord, Quick
Nav across 13 element types, a deep command palette, Workspace
Snapshots, headings organizer, compare documents, macros, an AI menu
gated by consent, GLOW accessibility, BITS Whisperer dictation, a rich
Quillins extension model, and a stability/safety surface that
mainstream editors rarely equal. Compared to the editor market it sits
somewhere between a programmer's text tool and a pro writing tool —
and that hybrid is exactly its edge.

The competitive analysis shows three things:

1. QUILL's *interactive navigation* and *accessibility-grade confirmations*
   are industry-leading. No mainstream editor matches its 13-element
   Quick Nav, its structured selection primitives, or its dialog
   contract enforcement.
2. QUILL's *document and project organization* (the Workspace concept,
   Document Navigator, multi-document sessions) is functional but
   under-developed compared with Ulysses's library, Obsidian's vault
   and backlinks index, Scrivener's index sheet, and Org-mode's
   hierarchy and agenda.
3. QUILL's *menu* has grown organically and now approaches the depth
   of a kitchen sink. The good news is the architecture supports a
   much cleaner organization. The bad news is that the current Tools
   menu reaches three levels in places and a few entries are mis-homed.

The rest of this document lays out the matrix, the gap list, the
proposed menu consolidation, the Workspaces + Document Navigator
redesign, and a long creative list of "make it amazing" ideas tailored
to QUILL's voice.

---

## 2. Feature matrix

Legend: ✅ first-class, ◑ partial, ○ not present, — N/A. The
"industry expectation" column is the user-facing behavior a sighted,
keyboard-only, or screen-reader user would expect to find without
explanation. The "QUILL today" column is observed from the codebase
and user guide as of 2026-06-01.

| Capability                                          | Industry expectation                                                                                          | QUILL today                              | Status |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ------ |
| Undo / redo with persistence                        | Multi-level undo; survives crash                                                                              | Multi-level undo; persistent undo toggle | ✅     |
| Find / replace (text)                               | Modal find bar; next/prev; replace; selection scope                                                            | In-document Find bar, replace, next/prev | ✅     |
| Regex find / replace                                | Toggle for regex; group preview                                                                               | Regex supported; named-group preview planned | ◑ |
| Find in files                                       | Cross-file search with results list                                                                           | Search menu (search_in_files, replace_in_files) | ✅ |
| Bookmarks (named, persistent)                       | Set / go to / list; per-document                                                                              | `navigate.set_bookmark`, `go_to_bookmark`, `list_bookmarks` | ✅ |
| Temporary marks / "point and mark"                  | Push/pop ring; exchange point/mark; list marks                                                                | `edit.set_mark`, `pop_mark`, `exchange_point_mark`, `list_marks` | ✅ |
| Line / paragraph / block selection                  | Three distinct selection units; announce which                                                                 | `select_line`, `select_paragraph`, `select_block` | ✅ |
| Structural navigation                               | Next/prev heading, block, structure; match bracket; region                                                    | `navigate.next_heading`, `next_block`, `next_structure`, `match_bracket`, `next_region` | ✅ |
| Outline / structure panel                           | Dockable tree with preview and jump; per-markup-kind                                                           | `open_outline_navigator`, `_show_tree_navigator` (modal); also a YAML navigator | ◑ |
| Quick Nav (jump to anything)                        | Single keystroke to a categorised index with type-ahead                                                        | `open_quick_nav` (NAV-1/NAV-4) with 13 element types | ✅ |
| Command palette                                     | Fuzzy find over all commands with scope and recent                                                             | `_id_palette`, palette.py                 | ✅     |
| Project / "workspace" concept                       | Named, restorable collection of open documents, settings, and UI state                                          | "Workspace Snapshots" submenu in File (`_sessions_menu`) and `_refresh_sessions_menu`; `core/sessions.py` | ◑ |
| Multi-cursor / multi-selection                      | Multiple carets, column selection, box select                                                                 | Not in core; `extend_selection_mode` toggle | ○ |
| Snippets / text expansion                           | Trigger, tab stops, placeholders, scope                                                                        | `core/snippets.py` (11 KB), `format.insert_snippet`, `format.manage_snippets` | ✅ |
| Snippet variables (date, filename, cursor)          | Tokens at expansion time                                                                                      | Supported (see Snippet format)           | ✅     |
| Command-based snippet system                        | JScript / Lua / Python actions inside snippets                                                                | Python sandbox in core; no in-snippet scripting in user guide | ◑ |
| Spell check                                         | As-you-type; dialog; dictionary management                                                                    | Three-tier spell-check; status / dialog; dictionary status | ✅ |
| Thesaurus                                           | Synonym lookup, inline replace                                                                                | `tools.thesaurus` (background pre-load planned) | ◑ |
| Grammar / style lint                                | Rules engine, inline annotations                                                                              | GLOW audit + fix, selection-level       | ✅     |
| Word count / reading time                           | Document, selection, periodic                                                                                 | `tools.word_count`                       | ✅     |
| Auto-save / recovery                                | Periodic save; recovery on crash with preview                                                                  | `core/autosave.py`; recovery snapshot dialog with 30-line preview | ✅ |
| Backups                                                                     | Local copies of prior versions                                                                                | `core/backups.py`; restore from backup   | ✅     |
| Compare documents                                                              | Side-by-side or unified diff; navigate; announce                                                              | `compare_menu` (Compare Documents) with announce, summary, copy, sync toggle | ✅ |
| Macros                                                                       | Record / play / save; named                                                                                   | `core/macros`; macro menu with start/stop/play/manage | ✅ |
| TTS / read aloud                                                             | Start/pause/stop; voice pick; speed; export audio                                                              | `core/read_aloud.py` (~46 KB), full menu | ✅ |
| Dictation                                                                    | Toggle; voice commands; offline model                                                                          | BITS Whisperer (deferred to 2.0 as a top-level menu; 1.0 ships dictation under Watch/Dictation submenu) | ◑ |
| OCR                                                                          | Image, clipboard, screen; image description                                                                     | `tools.ocr_image`, `tools.ocr_clipboard`, `tools.ocr_screen`, `tools.describe_image` | ✅ |
| OCR result post-processing (cleanup recipes)                                 | One-key cleanup of OCR output                                                                                  | "Clean exports" profile mentioned in roadmap; not surfaced in menu | ◑ |
| On-device / private AI                                                       | Opt-in; explicit consent; no silent network                                                                     | AI menu gated; `core.bw_whisperer` provider model; consent flow | ✅ |
| Cloud AI (ChatGPT, Claude, local endpoints)                                 | Model picker; API key; forget key                                                                              | `AI Model and Connection...`; `Forget API Key`; status badge | ✅ |
| AI rewrite / summarize / continue / fix grammar                              | In-editor actions                                                                                              | `ai_rewrite_selection`, `ai_summarize_selection`, `ai_continue_writing`, `ai_fix_grammar` | ✅ |
| AI prompt studio / agent center                                              | Custom prompts; agent tools                                                                                    | `ai_prompt_studio`, `ai_agent_center`, `ai_hub` | ✅ |
| Conversational AI side panel                                                 | Chat persistent side region, share selection                                                                       | `ask_quill_chat`, `ai_assistant` (windowed) | ◑ |
| Image description / alt-text helper                                          | Generate alt-text for embedded images                                                                          | `tools.describe_image`; accessibility tune-up agent | ✅ |
| Accessibility audit                                                          | Periodic; spoken report                                                                                        | `tools.accessibility_audit`              | ✅     |
| Keyboard trap / tab-order snapshot                                           | Diagnose focus traps                                                                                            | `tools.keyboard_trap_snapshot`           | ✅     |
| Contrast validation                                                          | Check palette against WCAG                                                                                     | `tools.validate_contrast`                | ✅     |
| Sticky notes                                                                  | Quick capture; searchable vault                                                                                | Sticky Notes submenu (sticky_notes, new sticky note) | ✅ |
| Watch folder                                                                  | Many folders, many actions, one monitorable queue                                                                | Watch Service (`quill.core.watch_service.WatchService`) with `WatchProfileStore` + `WatchManager` + `WatchQueue`; "Watch Folder Profiles..." / "Watch Folder Queue..." / toggle; CRUD on each profile | ◑ |
| Pandoc integration                                                            | Convert between formats                                                                                         | `tools.pandoc_wizard`                    | ✅     |
| External tools / format support                                              | Allowlist of executables                                                                                        | `tools.external_tools`                   | ✅     |
| SSH / remote file open                                                        | Quick connect; site manager                                                                                    | `Open over SSH` submenu (Quick Connect, Site Manager) | ✅ |
| File format readers/writers                                                   | Markdown, HTML, RTF, EPUB, DOCX, PDF, JSON, CSV, YAML, plain text                                             | `quill/io/structured.py` and per-format modules | ✅ |
| EPUB reader / navigator                                                       | Open and jump inside EPUB                                                                                       | `open_epub_navigator`                    | ✅     |
| YAML structure editor                                                         | Visual tree edit for YAML documents                                                                            | `open_yaml_structure_editor`             | ✅     |
| Heading organizer                                                             | Validate and reshape heading sequence                                                                          | `open_heading_organizer`                 | ✅     |
| Customizable menus / keymap                                                   | Editor for menu and keymap                                                                                     | `app.menu_editor`, `keymap_editor`; `core/menu_customization.py` (12 KB) | ✅ |
| Profiles (Essential, Writer, Developer, A11y Pro, Full)                      | Switch whole profile; health check                                                                              | Feature profiles + `switch_feature_profile`; `feature_profile_health_check` | ✅ |
| Feature flag manager                                                          | Per-feature toggle                                                                                              | `individual_feature_toggles`             | ✅     |
| Custom profiles / Quick Profiles                                              | User-saved bundles of settings                                                                                  | `core/custom_profiles.py`                | ✅     |
| Status bar layout customization                                               | Pick cells, persist                                                                                            | `status_bar_settings`                    | ✅     |
| Plug-in / extension model                                                     | Manifest, sandbox, signing                                                                                     | Quillins manifest validated; `quillins_bundled/` examples | ◑ |
| Export and back up / import                                                   | One-key share                                                                                                   | `share_export`, `share_import`           | ✅     |
| Export presets (EPUB, PDF, DOCX, HTML)                                        | Pick target and options                                                                                         | Pandoc wizard; export presets partial    | ◑ |
| Print                                                                          | Page setup, print preview                                                                                      | `file.page_setup`, `file.print`          | ✅     |
| Auto-format / smart punctuation                                              | Smart quotes, dashes, ellipses                                                                                  | Core autoformat; smart quotes not surfaced as toggle | ◑ |
| Word prediction                                                                | Inline completion                                                                                              | `edit.word_prediction`                   | ✅     |
| Intellisense as you type                                                       | Lightweight, scoped to language                                                                                | `core/intellisense.py`                   | ◑ |
| Markdown / HTML / rich-text preview                                           | Side by side or focused                                                                                        | `view.preview`, `view.split_preview`, `view.focus_preview`, `view.browser_preview` | ✅ |
| Distraction / focus mode                                                      | Hide chrome, center text, silence chatter                                                                       | "Focus Preview" is the closest; no full-screen "Focal" mode | ◑ |
| Reading ruler / line focus                                                    | Highlight current line/paragraph                                                                                | Not surfaced; high-contrast settings only | ◑ |
| Inline definitions / word lookup                                              | Single key for dictionary + thesaurus                                                                            | Thesaurus dialog; no inline look-up      | ◑ |
| Document health unified report                                                | One pane for accessibility + lint + link inventory                                                              | Accessibility audit; link inventory; contrast; not unified | ◑ |
| External file change watch                                                    | Detect edits; reload safely                                                                                    | `core/external_change.py`                | ✅     |
| Code folding                                                                  | Collapse / expand                                                                                              | Not surfaced                              | ○     |
| Multi-pane editor (split, grid)                                              | Horizontal/vertical split, save layout                                                                          | "Preview Side by Side" exists; no true multi-pane text editor split | ◑ |
| Tab / tile open documents                                                     | One tab per document                                                                                            | `show_tab_control` toggle in View        | ✅     |
| Status bar: line, col, selection length                                      | Always present                                                                                                  | Status bar with cells (status_bar_settings to choose) | ✅ |
| Recent files / recent folders                                                 | MRU list                                                                                                        | `Open Recent` submenu                    | ✅     |
| Recent sessions / restore last session                                        | Auto-restore on launch                                                                                          | "Workspace Snapshots" submenu in File; auto-restore on launch | ✅ |
| Auto-update                                                                    | Notify; one-key update                                                                                          | `check_updates`; auto-check toggle in Settings | ✅ |
| Crash reporting                                                                | Opt-in bundle                                                                                                  | `save_diagnostics`; `report_bug`        | ✅     |
| Localization                                                                   | Multi-language UI                                                                                              | Translation contributor plan in place    | ◑     |
| High-contrast / dark mode                                                     | System-aware                                                                                                    | `toggle_dark_mode`; `validate_contrast`; high-contrast respected | ✅ |
| Math / equation editor                                                        | LaTeX-style inline and block                                                                                    | Not surfaced                              | ○     |
| Bibliographies / citations                                                    | Reference list management                                                                                       | Not surfaced                              | ○     |
| Co-located todos / checkboxes                                                 | Task list with states                                                                                          | Task list insertion (`insert_task_list`); List Manager | ✅ |
| Bidirectional links / backlinks                                               | Wiki-style [[link]] with back-link pane                                                                          | Follow link exists; no backlink pane    | ○     |
| Backlinks / relational index                                                   | Cross-document links and references                                                                              | Not in QUILL (deferred to 2.0)            | ○     |
| Index-sheet view                                                               | One card per document or section                                                                                | Not in QUILL                              | ○     |
| Outline view (persistent side region)                                          | Persistent tree side panel                                                                                      | Outline Navigator is a modal; no persistent side region | ◑ |

The takeaway: QUILL is in the top tier for navigation, accessibility,
AI integration (gated), writing-quality tooling, and document safety.
Its *project organization* layer (workspaces, library, multi-document
backlinks, smart folders, goals) is functional but under-developed
relative to dedicated writing apps.

---

## 3. Where QUILL aligns with industry

These are the strengths that match or exceed editor expectations, and
the rough proof points inside the codebase.

1. **Stock controls in the writing path.** Per
   `accessible-dialogs.instructions.md`, every input is `wx.TextCtrl` or
   `wx.ListBox`. No custom-drawn editor surface, which means
   screen readers see the same role and name everywhere.
2. **Three-tier spell check** with enchant, wordlist, and stub. Background
   pre-load is on the roadmap (PERF-1) and the menu surfaces every
   level: Spell Check dialog, Previous/Next Misspelling, Misspelling
   List, Dictionary Status, Add to Document Dictionary, Ignore for
   Session.
3. **Structured selection primitives.** Select Line / Paragraph / Block
   are separate commands, not a single ambiguous "extend selection"
   that other editors make the user discover.
4. **Mark ring.** Set / Pop / Exchange / List. Few mainstream editors
   ship a visible mark ring as a first-class menu.
5. **Quick Nav across 13 element types** with a category filter and
   type-ahead. This is VS Code's Command Palette behavior applied to
   document structure, with a count badge.
6. **Heading organizer** validates and rewrites heading sequences for
   accessibility and clean exports. No mainstream editor has this.
7. **Compare Documents** with synchronized navigation, announcement of
   the current difference, a "Difference Summary," and copy
   individual/all differences. Compare in Word is a hidden ribbon
   dialog; in Notepad++ it is a plugin; in VS Code it is an extension
   unless you have Pro. QUILL ships it as a first-class tool.
8. **Workspace Snapshots** that name and restore document sets, caret
   positions, and active document. The naming and saving model is
   Ulysses-like.
9. **Two-stage AI consent.** No silent network; provider, model, scope,
   and confidence are announced.
10. **BITS Whisperer** (deferred to 2.0 as a top-level menu but present
    in 1.0 as a submenu) is genuinely novel for a screen-reader-first
    editor: offline speech-to-text with model management and a queue
    you can monitor without sight.
11. **Watch Folder Profiles** is the rare automation hub that is
    operable with a screen reader; the "many folders, many actions,
    one queue" redesign on the roadmap is a real differentiator.
12. **GLOW (Grammar, Logic, Organization, Writing)** is QUILL's
    accessibility-and-prose-fix engine; the four sub-commands (audit
    document, audit selection, fix document, fix selection) make it
    simple by design.
13. **Quillins extension model** is sandboxed, manifest-validated, and
    ships with a Lint tool (`quill.tools.quillin_lint`). Compared with
    Vimscript or VS Code's open extension marketplace, it is a
    deliberately tight perimeter.

The user-visible principle behind all of this: *every action has a
spoken outcome, every dialog has a default and an escape, every
feature can be turned off*. That is the bar the rest of the editor
market does not consistently meet.

---

## 4. Where QUILL is behind or behaves unexpectedly

These are the gaps the matrix surfaces, with the "industry expects"
framing, the QUILL reality, and an honest callout when current
behavior diverges from what a user would assume.

### 4.1 Project organization is shallow

- **Industry expectation.** Ulysses users live in a "library" with
  groups, filters, and goals. Obsidian users live in a "vault" with
  backlinks, tags, and Bases. Scrivener users live in a "binder" with
  index sheet and outliner. Org-mode users live in a tree with
  agenda.
- **QUILL today.** Workspace Snapshots save and restore the current
  open-document set. There is no persistent library, no grouping, no
  filters, no per-workspace palette of recent activity. The
  "Recent Files" menu exists but Workspace Snapshots is a sibling
  concept, not a superset.
- **Honest callout.** "Open from Workspace Snapshot" can look like a
  glorified "Reopen Closed Tab" to a new user. The snapshot is
  loadable, but the snapshot UI is not yet a library.

### 4.2 Outline Navigator is a modal, not a persistent side region

- **Industry expectation.** Word, Scrivener, and most writing apps
  ship a persistent outline pane that you can show, hide, and let
  track the cursor. Ulysses shows the editor + sheet list always.
  Obsidian shows the file tree.
- **QUILL today.** `_show_tree_navigator` builds a `wx.Dialog` with a
  splitter (tree + preview), is launched by `open_outline_navigator`
  (and `open_epub_navigator`, `open_yaml_structure_editor`), and is
  destroyed on close. The same pattern is reused for Misspelling
  Navigator, Document Intake, and others.
- **Honest callout.** The dialog is excellent and screen-reader
  friendly, but a power user editing a 200-page manuscript will
  repeatedly open and close the modal. A persistent outline panel
  (toggle from View) would match industry behavior without
  breaking the dialog contract.

### 4.3 Multi-cursor / column select is absent

- **Industry expectation.** VS Code, Sublime, JetBrains IDEs, vim,
  Emacs all support multiple carets. Notepad++ supports column /
  block selection. Word supports column select with Alt.
- **QUILL today.** Only an "extend selection mode" toggle exists,
  which extends the next selection motion. No multi-caret, no
  column / box select.
- **Honest callout.** This is the single largest missing editing
  primitive for users who came from a programmer editor. Add a
  power-tool that toggles column-select on Alt+drag and a
  keyboard command to add a caret above / below.

### 4.4 Word-prediction and intellisense are present but not visible

- **Industry expectation.** Word shows suggestions inline. VS Code
  shows completions on demand and as you type. Notepad++ has an
  autocomplete plugin that does the same.
- **QUILL today.** `edit.word_prediction` opens a dialog. There is no
  as-you-type inline completion surfaced in the menu or the status
  bar. `core/intellisense.py` exists; nothing in the menu says so.
- **Honest callout.** Users will assume the feature is broken. The
  fix is to make it a visible, opt-in "Inline word prediction" toggle
  in the status bar / settings, with announcement on accept.

### 4.5 AI chat is windowed, not a persistent side region

- **Industry expectation.** Cursor, VS Code + Copilot, JetBrains AI,
  Notion AI, and Ulysses's "Ask Ulysses" all anchor a chat side
  panel that shares selection with the editor.
- **QUILL today.** "Ask Quill Chat..." and "Writing Assistant..."
  open floating windows. The selection is shared only through copy
  and paste.
- **Honest callout.** The chat is functional; it just is not a
  persistent side region, and a chat panel that owns a left or right
  persistent side region with the outline tree on the other side
  would be a much more useful default.

### 4.6 Grammar fix is not in the document until asked

- **Industry expectation.** Grammarly underlines; one key accepts.
  GLOW already audits and fixes, but the audit step is explicit.
- **QUILL today.** `glow_audit_document` and `glow_audit_selection`
  must run before `glow_fix_document` and `glow_fix_selection`. The
  fix only changes the document after the user sees the report.
- **Honest callout.** This is a defensible design (transparency), but
  the menu should make it obvious: the "GLOW" submenu already does.
  Keep the contract; add a "GLOW Quick Fix on Selection" that audits
  + fixes + announces the change count in one key.

### 4.7 No "Focus Mode" / "Focal" surface

- **Industry expectation.** Word has Focus Mode. Bear has a
  chrome-less compose. Ulysses has a minimal editor. iA Writer has
  Focus Mode with a sentence highlight. Notepad++ has a "Distraction
  Free" plugin.
- **QUILL today.** The closest is "Focus Preview." That hides the
  editor chrome for the preview, not the editor itself.
- **Honest callout.** "Focus Preview" is misleadingly named. A real
  "Focal Mode" (F11?) that hides status bar, menu bar, side
  region, and centers the current paragraph with optional reading
  ruler and sentence highlighting is the correct fit for a
  screen-reader product; it should silence non-essential chatter,
  keep essential confirmations, and be a one-key toggle.

### 4.8 Snippet tab stops / placeholders are not announced

- **Industry expectation.** VS Code, Sublime, JetBrains, vim, and
  TextMate all support tab stops with placeholders; the user is
  walked through each stop with `Tab` and `Shift+Tab`.
- **QUILL today.** Snippets exist and the menu offers Insert and
  Manage; there is no documented "tab stop" walk-through. The snippet
  format may support placeholders (it does in EdSharp and most modern
  editors).
- **Honest callout.** Verify in `core/snippets.py` and document.
  If placeholders are not yet announced, add a `Snippets` tutorial
  to the user guide and make the placeholder name spoken on arrival.

### 4.9 Goto line / page has no "line" speech preview

- **Industry expectation.** A "Go to line" usually shows the line
  content in a preview before the user commits.
- **QUILL today.** `navigate.go_to_line` jumps; no preview.
- **Honest callout.** Add a one-line preview pane in the Go-To-Line
  dialog with the current line's text, the line number, the column,
  and a "Speak Line" button. Trivial to add, big screen-reader win.

### 4.10 No saved searches / no smart folders

- **Industry expectation.** Most pro editors and writing apps
  support saved filters: "All headings containing TODO," "All
  documents opened this week," "All files with more than N
  misspellings."
- **QUILL today.** None. `file_search` exists but is a one-shot
  search.
- **Honest callout.** Add a "Saved Searches" manager and tie it to
  Workspace Snapshots. Saved searches are an under-rated
  accessibility win because they let a screen-reader user ask
  "what's new?" in a single keystroke.

### 4.11 No word-count goal / writing target

- **Industry expectation.** Ulysses has writing goals (words,
  characters, time). Scrivener has project targets. Word has
  word-count target notifications. Bear has a daily streak.
- **QUILL today.** Word count exists; no goal / target surface.
- **Honest callout.** Add a "Writing Goal" dialog and a status-bar
  cell that announces progress. Tying the goal to a Workspace
  Snapshot makes this very Ulysses-like.

### 4.12 Status bar cells are customizable but the UX is hidden

- **Industry expectation.** VS Code and Word expose a clear "Status
  Bar Layout..." picker.
- **QUILL today.** `status_bar_settings` exists. The menu labels it
  clearly. The dialog must be polished.
- **Honest callout.** Verify the dialog (a screen-reader test pass)
  and add an "Add a cell" / "Remove a cell" / "Reorder" flow that
  is fully keyboard-driven.

### 4.13 No reading ruler / line focus for low-vision users

- **Industry expectation.** Word, Pages, macOS, NVDA, and many
  editors support a reading ruler that follows the caret.
- **QUILL today.** Not surfaced.
- **Honest callout.** Add a "Reading Ruler" toggle and a "Line
  Focus" toggle under View, behind a feature flag, with high-contrast
  aware theming.

### 4.14 Smart quotes / auto-format not surfaced

- **Industry expectation.** Word, Pages, Ulysses, Bear all convert
  straight quotes to typographic quotes as you type.
- **QUILL today.** `core/autoformat.py` exists; not on by default,
  not visible in the menu.
- **Honest callout.** Surface as a setting ("Auto-format as you
  type") with sub-toggles for quotes, dashes, ellipses. Announce the
  substitution so a screen-reader user knows the character changed.

### 4.15 No image embed flow (other than OCR)

- **Industry expectation.** Markdown editors let you paste / drop an
  image. Ulysses, Bear, iA Writer all do.
- **QUILL today.** OCR Image and Describe Image are present. Image
  insertion is not. Markdown reference links work.
- **Honest callout.** Add "Insert Image from File..." and "Insert
  Image from Clipboard" under Insert. The accessibility win is that
  the dialog should immediately offer a "Describe Image..." button
  that uses Describe Image, so the alt text and the embed happen
  together.

### 4.16 Inline spelling suggestions are not visible in the menu

- **Industry expectation.** Word, Pages, macOS show a context menu
  with "Replace with..." suggestions.
- **QUILL today.** Misspelling List exists; no inline context menu
  for replacements.
- **Honest callout.** Add a context menu for misspelled words
  offering the top three suggestions + "Add to Dictionary" + "Ignore
  for Session." Already possible with the wx context menu; surface
  the wired action in the menu so it is discoverable.

### 4.17 No "duplicate selection" as a structural copy

- **Industry expectation.** Several editors have "Duplicate Line"
  and "Duplicate Selection."
- **QUILL today.** `format.duplicate_line` exists. No
  `duplicate_selection` (block-level copy).
- **Honest callout.** Add `edit.duplicate_selection` to the Edit
  menu; it's two lines of code and a big productivity win.

### 4.18 The Tools menu is deep

- **Industry expectation.** Most successful editors keep top-level
  menus flat with one level of submenu. VS Code's File menu has 9
  items, Edit has 12, View has 22, all flat.
- **QUILL today.** The Tools menu has 14 direct submenus and the
  Read Aloud, BITS Whisperer, and AI submenus each go a level
  deeper. The Custom Profiles under Help also add a third level.
- **Honest callout.** This is a documentation and discoverability
  problem, not a code problem. See §6 for the proposed
  consolidation.

### 4.19 Watch Folder — multi-profile infrastructure is in, the screen-reader UX is the gap

- **Industry expectation.** Folder Watching tools (Hazel on Mac,
  File Juggler on Windows) all support many rules. A
  screen-reader-first editor needs the same, with every rule,
  match, and action spoken on the same channel as the rest of the
  editor.
- **QUILL today.** The infrastructure is genuinely in. The
  `WatchService` facade (`quill/core/watch_service.py`) owns:
  - a `WatchProfileStore` with full CRUD —
    `add_profile`, `update_profile`, `delete_profile`,
    `set_profile_enabled`, `duplicate_profile`, `profiles()`;
  - a `WatchManager` that runs pollers for *all* enabled profiles
    concurrently, with a single `WatchQueue`;
  - a `WatchWorker` plus the durable queue at
    `%APPDATA%\Quill\watch\watch-queue.json`;
  - a `WatchActionRegistry` (open / convert / run macro / AI)
    wired through the UI layer's callbacks.
  The Tools menu exposes "Watch Folder &Profiles...",
  "Watch Folder &Queue...", and the toggle.
- **Honest callout.** The plumbing matches Hazel / File Juggler in
  scope, not "single profile." The real gap is the
  screen-reader-tuned UX: a stock `wx.Dialog` for add / edit /
  enable / disable that announces every field; a queue dialog that
  announces profile, file, action, and result with a spoken tail
  on completion; a one-key "Open Watch Queue"; an opt-in
  "announce on match" toggle in Preferences. The settings dialog
  currently lives in the main frame and likely needs the
  dialog-inventory treatment before it can honestly be called
  "aligned with industry."

### 4.20 BITS Whisperer (offline speech-to-text) is deferred

- **Industry expectation.** Dragon, Apple Dictation, Windows Voice
  Typing all exist.
- **QUILL today.** Dictation is a submenu, BITS Whisperer is feature-
  flagged behind `core.bw_whisperer` (off by default in 1.0), and
  per the standing rules, items needing a real Windows runtime must
  stay honestly "In progress."
- **Honest callout.** This is correctly called out in the standing
  rules; keep it in progress and don't pretend it's done.

### 4.21 Selection mechanics — what the code already does, what it doesn't

The selection pipeline lives in three files
(`quill/core/selection.py`, `quill/core/marks.py`,
`quill/ui/main_frame_selection.py`) and is genuinely well-factored
for a screen-reader product. The screen-reader contract — *announce
the scope, the word count, and the new bounds after every change* —
is held by `_announce_selection_scope` in the mixin.

| Mechanism                            | QUILL today                                                                                                                                  | Industry comparison                                                            |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Word / line / paragraph / block span | Five primitive span functions (`word_span`, `line_span`, `paragraph_span`, `sentence_span`, `block_span`) return `(start, end)` for a caret | Emacs has `mark-word` / `mark-paragraph`; Word has Extend Mode; vim has `vw`     |
| Scope classification                 | `selection_scope` returns one of `none / word / line / sentence / paragraph / block / document / lines / span`                                | Sublime/VS Code announce "1 selection, 4 words"; QUILL is more granular       |
| Expand / shrink                      | `expand_selection` walks word → line → sentence → paragraph → block → document with a stack; `shrink_selection` pops the stack                | VS Code's Expand / Shrink Selection; IntelliJ "Extend Selection"               |
| Extend selection mode                | `edit.toggle_extend_selection_mode` (F8) flips a sticky flag; while on, shift+arrow extends from the current caret; toggle off to leave | Emacs transient-mark; vim visual-mode; *different* from EdSharp's F8 (single-shot session, see §4.21.1) |
| Mark ring                            | `MarkRing` (20 entries, dedup, exchange) with `set_mark` / `pop_mark` / `exchange_point_and_mark` / `list_marks`                            | Emacs' global-mark-ring; EdSharp's mark ring; Scrivener's bookmark ring         |
| Select-to commands                   | `select_to_start_of_line`, `select_to_end_of_line`, `select_to_start_of_document`, `select_to_end_of_document`                              | Standard; UX is the announcement                                               |
| QUILL key selection actions          | `quill_key_selection_actions` opens a stock `wx.SingleChoiceDialog` whose options adapt to scope + markup surface                              | Ulysses's "Quick Action" panel; VS Code's "Refactor This..." — QUILL is better |

#### 4.21.1 EdSharp's F8 vs. QUILL's F8 — the two dialects of "begin a selection"

Both editors let you mark a region of text so you can copy, cut,
reformat, or read it aloud, but they model the *act of marking*
quite differently. This is the single most important
selection-UX comparison for a screen-reader-first editor, and the
audit recommendation is to **speak both dialects** rather than
pick one.

**EdSharp's F8 is a "begin / end" event pair, not a mode.**

- **Press F8 once** → "Start Selection." EdSharp drops an invisible
  anchor exactly where the caret sits and remembers the caret
  position as the *start* of a future selection. The status bar /
  screen reader announces something like *"Selection started at
  line 12, column 5."* The cursor can now move around freely
  (arrows, mouse, click, search) without selecting anything yet.
  This is *not* a sticky mode — it is the first half of a two-step
  operation.
- **Move the caret** anywhere (including via search results,
  go-to-line, etc.) — nothing is highlighted as you go. The anchor
  stays put at the original spot.
- **Press Shift+F8** → "Complete Selection." EdSharp now draws and
  announces the rectangular region from the anchor to wherever the
  caret has moved to, and that region is the "active selection."
  From this point on, Copy, Cut, Say Selected, Quote, etc. operate
  on it.
- **Press F8 again on an existing selection** → "Reselect"
  (Ctrl+Shift+F8) or "Go to Start of Selection" (Alt+Shift+F8) to
  refine.

So the EdSharp flow is **Anchor → Roam → Capture**: anchor once,
wander anywhere, capture the region at the moment you choose.
There is no state to remember to turn off; F8 / Shift+F8 are an
*event pair*, not a toggle.

**QUILL's F8 is a sticky mode flag.**

- `edit.toggle_extend_selection_mode` (F8) is a *toggle*: pressing
  F8 turns the flag on, pressing F8 again turns it off. The flag
  lives in `self._extend_selection_mode` and the anchor lives in
  `self._extend_selection_anchor` on `MainFrame` (see
  `quill/ui/main_frame.py:945` and the branches that consult the
  flag at 3074, 3530, 3535, 3593, 3601, 11741, 11758, 11774,
  16296, 16309).
- When the flag is **on**, the *next* shift+arrow / shift+click /
  shift+End / shift+Home / etc. extends the selection from the
  current caret — there is no separate "begin" step. The flag
  stays on across many motions; it stays on across copy / cut
  (those don't touch the flag); it stays on until you press F8
  again, press Escape (a dedicated Escape branch at 3074 and 3530
  turns it off), or do something like a click without shift
  (treated as an implicit off-switch).
- When the flag is **off**, shift+arrow behaves the *normal* wx
  way — a one-character shift-select that disappears as soon as
  you release shift.

So the QUILL flow is **Enable → Shift-move → Disable**: a mode
you have to remember to leave on, with the bonus that *every*
shift+motion honors it (e.g. shift+Ctrl+End extends to end of
document), and the cost that the SR user has to remember the
flag is still set when they think they are doing a normal
selection.

**The QUILL flow has real ergonomic issues that the prose above
understates.** Reading the actual code
(`quill/ui/main_frame.py:3530–3558`, `_move_extend_selection_caret`
at 3621–3701, and the commit helpers at 3592–3619), the
"F8 + arrows + copy" gesture does *not* behave the way the
summary sentence above suggests:

1. **F8 does not capture the anchor.** The first keypress of F8
   only flips the flag. The anchor is set *lazily* on the first
   movement-key event (line 3552–3553) or on the first
   non-excluded action (e.g. find, line 16295 calls
   `_ensure_extend_selection_anchor`). So if you press F8 and
   then *do nothing* for ten seconds, the editor has a flag set
   and no anchor.
2. **The anchor is set to the *pre-motion* caret, not the *F8
   time* caret.** In practice these are the same — you pressed
   F8, you didn't move — but the contract is "the anchor is
   wherever the caret is on the first move." If you press F8,
   click the mouse somewhere, then arrow down, the anchor is the
   *click* position, not the F8 position.
3. **During the arrow-down phase, the selection is *invisible*.**
   `_handle_extend_selection_key` (3530–3558) moves the caret via
   `_move_extend_selection_caret`, then at 3556 explicitly
   collapses the selection to `(caret, caret)`. The SR hears
   *only* caret-move announcements ("line 14, column 5… line 15,
   column 5…") with no "selected" prefix. A sighted user sees
   the highlight stretch; a blind user gets no audio equivalent
   of the growing region.
4. **The selection is only *applied* to the editor at the moment
   a "commit" key fires.** Copy, Cut, Delete, Format commands,
   and tools.glow_fix_selection are in the commit set
   (`_EXTEND_SELECTION_ACTION_COMMANDS` at 864, with the prefix
   test at 860–863). The commit runs `_apply_extend_selection`
   (3592–3598), which finally does
   `SetSelection(min(anchor, caret), max(anchor, caret))`. Until
   then, the editor's selection range is `None..None`.
5. **If you stop without committing, the work is lost.** Pressing
   F8 a second time hits the Escape-style branch at 3530–3534
   and discards the anchor with `SetSelection(caret, caret)`. So
   "F8, arrow 6, F8 to stop" leaves *no* selection — and the
   arrow key announcements in step 3 made it *sound* like the
   region was being built. A blind user has no way to recover
   the anchor.
6. **Ctrl+C works only by accident of the Skip order.** At
   3548–3551, the handler calls `_commit_pending_extend_selection`
   *before* `event.Skip()`. wx's native Ctrl+C then reads
   `GetSelection()` after the commit, so the clipboard gets the
   correct region. But this depends on the key handler running
   *before* wx's copy, and on the user pressing a key that is
   recognized as a "commit" key. Hit Escape and the region is
   gone (step 5).
7. **Mouse-based extend is half-supported.** A bare click is
   treated as an implicit off-switch, so click-move-shift-click
   does not benefit from the F8 flag. Shift+click works as a
   normal wx shift-select. There is no "F8 then click" anchor
   placement.

**Net effect.** A power user with eyes on the screen gets a
selection that grows visibly and copies correctly. A screen-reader
user gets *no* spoken evidence of the growing region, no spoken
announcement of the final anchor, no announced bounds at copy
time, and a high risk of losing the work entirely if they hit
F8 again or Escape by reflex. The mode toggle is genuinely a
power-user feature for sighted code editing; for a screen-reader-
first product the **recommended default is the EdSharp event-pair
model**, with the F8 mode preserved as an opt-in profile.

#### 4.21.2 Should we change F8 to match the EdSharp model? — recommendation

Short answer: **no, do not change F8. Add three new commands and
let the user choose.** Here is the reasoning, broken into the
parts that are easy to get wrong.

**Why "just change F8" is the wrong move for 1.0**

1. **It would break every existing muscle-memory user.** F8 is in
   `quill/core/keymap.py:52` as a default binding, in the Edit
   menu check item at `quill/ui/main_frame_menu.py:138–144` and
   1748–1750, in the feature-command map at
   `quill/core/feature_command_map.py:150`, and in the public
   surface fixture at
   `tests/unit/ui/fixtures/main_frame_public_surface.json:213`.
   The "extend mode" semantics are tested in five places in
   `tests/unit/ui/test_main_frame_navigation.py` (1275, 1303,
   1316, 1330, 1690, 1704, 1715). A semantics change would force
   a keymap migration, a menu relabel, a feature-flag rename, a
   public-surface fixture regen, and a regression pass on those
   seven tests. None of that is a 1.0 win.
2. **The mode is *correctly* used as a power-user feature.** The
   toggle composes with every shift+motion and shift+command.
   F8 → shift+Ctrl+End selects to end of document in one gesture;
   F8 → find_next → find_next captures a "search hits" region;
   F8 → select_line then re-pressing F8 toggles the line into a
   region. None of that is in EdSharp's event-pair model without
   extra keypresses.
3. **The bugs are bugs, not design flaws.** The screen-reader pain
   is real, but it is caused by *missing announcements* and
   *missing commit visibility*, not by the mode itself. The
   right fix is to add the announcements (one line per
   handler in `_handle_extend_selection_key`, one PR), not to
   delete the mode.

**Why EdSharp-style commands are the right *addition***

1. **They fill the actual gap.** A screen-reader user who presses
   F8 today gets "Extend selection mode on (F8)" — they don't
   get the line / column. They press the down arrow six times
   and get six caret announcements with no growing region. They
   press Ctrl+C and the clipboard has the right text but no
   audio confirmation. None of that is fixed by changing the F8
   semantics; all of it is fixed by adding commands that
   announce.
2. **They cost very little.** The implementation surface for the
   event-pair model in QUILL is roughly:
   - `edit.start_selection` — sets an explicit anchor at the
     caret, announces "Selection started at line N, column M,"
     and stores the anchor in a new field
     `self._selection_anchor: int | None`. Toggle behavior on
     the same key (Ctrl+.) so re-pressing just refreshes the
     anchor.
   - `edit.complete_selection` — collapses the anchor and the
     current caret into a region via
     `editor.SetSelection(min, max)`, announces "Selected N
     words from line A col B to line C col D," and clears the
     anchor.
   - `edit.reselect` — re-applies the last applied region
     (cheap if `core/selection.py` already tracks the last
     applied pair).
   - `edit.go_to_start_of_selection` / `edit.go_to_end_of_selection`
     — move the caret to one end or the other, leaving the
     selection visible.

   The first two are ~40 lines of code in the same place as
   `toggle_extend_selection_mode` (main_frame.py:6369). The
   second two are ~20 lines. Total: under 100 LOC plus
   announcements and keymap entries.
3. **They compose with the existing mode.** A user can press F8
   for the power-user mode, *or* Ctrl+. for the EdSharp
   anchor/finish pair, *or* just use plain shift+arrows for
   normal one-off selections. The three are not mutually
   exclusive. A user who keeps the F8 flag on by accident and
   then presses Ctrl+. gets a fresh anchor at the caret; the
   F8 flag is irrelevant to the event-pair model.
4. **They let QUILL speak both dialects.** This is the right
   call for a screen-reader-first product: do not pick a
   favorite editor's mental model, *expose all the useful ones*
   with a consistent spoken contract.

**The recommended F8 change is small and additive**

What we *should* change in the F8 code path is the announcement
gap, not the mode:

- At 6369–6375 (the `toggle_extend_selection_mode` body), when
  the flag goes on, announce "Extend selection mode on. Anchor
  at line N, column M" using
  `line_column_for_position(insertion_point)`. The helper
  already exists in `quill/core/marks.py`.
- At 3074 (the Escape branch) and 3530–3534 (the F8-off
  branch), if there is a pending region, announce "Extend
  selection mode off. Last region: N words from line A col B
  to line C col D" *before* clearing the anchor. This is the
  "no silent loss" fix.
- At 3548–3551 (the non-movement-key branch), after
  `_commit_pending_extend_selection` runs and the
  `event.Skip()` returns, the next native key handler (Copy,
  Cut, etc.) operates on the committed region; we already
  have the region in scope. Add a one-line announcement
  there: "Committed selection: N words from line A col B to
  line C col D." This is the "audible proof the copy worked"
  fix.
- Add a status-bar cell "Selection session: anchored at line
  N" that updates on every F8 / Ctrl+. / Reselect. A
  screen-reader user can query the cell with a custom key
  ("Where is the anchor?") and get an immediate answer.

The four changes above are roughly 30 lines of code and three
unit tests. They do not require a keymap migration, a menu
relabel, a fixture regen, or a regression pass. They are
backwards-compatible and they bring the F8 mode into the same
announcement discipline as the rest of the selection pipeline.
**That is the right scope for QUILL 1.0.**

**What we should *not* do in 1.0**

- Do not rename F8. Do not change the menu label "Extend
  Selection Mode (F8)." Do not change the
  `edit.toggle_extend_selection_mode` semantics. Do not change
  the feature-command map. Do not regen the public surface
  fixture.
- Do not introduce a "EdSharp mode" toggle that flips the
  meaning of F8. The risk of footguns (a user toggles it,
  forgets, presses F8, gets the wrong behavior) is higher
  than the benefit of the unification.
- Do not deprecate the F8 mode. A power user who edits code
  or XML or CSV lives in this mode. Removing it is a real
  regression for that cohort.

**What we *should* do in 1.0** (revised Tier 1 list):

1. Add the four announce-on-commit changes above to
   `toggle_extend_selection_mode` and friends.
2. Add `edit.start_selection` (Ctrl+.) and
   `edit.complete_selection` (Ctrl+Shift+.).
3. Add `edit.reselect` and `edit.go_to_start_of_selection`.
4. Document all three in `dialogs.md` (because the new
   commands appear in the Edit menu and the keymap) and in
   the Help > QUILL Key Primer surface.
5. Add a selection-mechanics regression test that exercises
   the announce-on-commit path with a mocked TTS sink so the
   announcement contract is locked in.

If we get all five right, the EdSharp model is *available*,
the F8 mode is *announced correctly*, the screen-reader user
has a clear answer to "where is the anchor?" at all times,
and no existing user breaks.

**Where the two designs differ in feel:**

| Aspect                        | EdSharp F8 (event pair)                                                          | QUILL F8 (mode toggle)                                                  |
| ----------------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Mental model                  | "I am starting a selection session; I will end it later."                       | "I am in extend mode; every shift+arrow extends."                       |
| When the anchor is set        | At the moment you press F8 — never moves again until you Reset.                 | Implicit, at the moment of the *first* shift+motion in the session.    |
| How the selection is captured | A second, distinct keypress (Shift+F8) announces the region.                    | Each shift+arrow redraws and re-announces the region live.              |
| What "F8" means in a script   | "Begin." Always idempotent, never lingering.                                    | "Flip a state." Idempotent in pairs (on / off), surprising in between. |
| Failure mode                  | User forgets the anchor; presses Shift+F8 and gets a stale region.              | User forgets the flag is on; every shift+arrow keeps extending and the selection balloons. |
| SR announcement               | One anchor announcement at the start, one region announcement at the end.        | No anchor announcement; a region announcement per shift+motion.         |
| Composition with search       | "Search then F8 then Shift+F8" — the search hit becomes the end.                 | "Search then shift+Enter" extends, but the search is not part of the selection session; F8 is irrelevant. |

**Where QUILL wins.** The mode approach composes with *every*
shift+motion and shift+command in the editor for free. You can
F8 → shift+Ctrl+End and get "selection to end of document" with
one gesture. EdSharp would need an extra "Complete" keypress to
capture. The Escape branch means a screen-reader user who hears
*anything* go wrong can hit Escape and be safely out, which
matches the rest of the dialog contract.

**Where EdSharp wins.** The event-pair model is *declarative and
stateless*: at any moment the answer to "is the editor in a
selection session?" is "look for the most recent F8 with no
matching Shift+F8." There is no flag to forget, no anchor to
leak, no mode indicator to misinterpret. This is the model
Word's Quick Parts dialog, macOS text fields, and most modern
web text fields use. The anchor is announced explicitly
("Selection started at line 12, column 5"), so the screen
reader always knows the *origin* of a future selection, not
just the *current bounds*. QUILL's mixin announces the *bounds*
of the result; EdSharp announces the *anchor* of the intent.
"Reselect" and "Go to Start of Selection" are first-class
commands; QUILL has an expand / shrink stack but no explicit
"last region before current" recall across sessions.

**Honest call.** The right thing for QUILL 1.0 is **not** to
replace the mode toggle — that is a lot of code to throw away
and a real workflow win for power users — but to **add**
EdSharp-style commands alongside it:

- `edit.start_selection` (Ctrl+.) — sets an explicit anchor at
  the caret, announces it, and starts a "selection session."
  Unlike F8, it does not touch `_extend_selection_mode` and does
  not require the user to remember to disable anything.
- `edit.complete_selection` (Ctrl+Shift+.) — collapses the anchor
  + current caret into a region, announces it, and the editor
  is back to a normal single-caret state.
- `edit.reselect` and `edit.go_to_start_of_selection` — populate
  the LibreOffice / EdSharp gap.
- `edit.copy_with_position` — paste a copy of the selection with
  a trailing `[line 12 col 5 – line 14 col 22]` footer; useful
  for AI prompts.

These five commands cost roughly what Select Chunk costs (one
core helper in `quill/core/selection.py`, one announcement in
the mixin, one binding in `quill/core/keymap.py`) and they let
QUILL speak *both* dialects: the power-user mode toggle for
shift-motion composition, and the explicit begin / finish pair
for SR users who prefer the declarative model. That is the same
"every action has a spoken outcome" principle QUILL already
follows, applied to selection itself.

**Gaps vs. industry** (honest):

- **No Select Chunk (Ctrl+Space).** EdSharp's "Select Chunk" is a
  whitespace-bounded "W"-like motion. QUILL has word-span and
  line-span; a chunk-span (whitespace-and-punctuation run) is
  missing. Implement as a thin wrapper around
  `re.finditer(r'\S+', text)` and a cursor-position lookup.
- **No "Reselect" (EdSharp Ctrl+Shift+F8) or "Go to Start of
  Selection" (Alt+Shift+F8).** The expand / shrink stack effectively
  serves Reselect, but only for the current extend session. A
  Reselect that survives the extend session (last-popped-but-not-
  current) is a small, useful addition.
- **No anchor / point swap that survives the clipboard.** Emacs'
  `exchange-point-and-mark` is correct; QUILL mirrors it. But QUILL
  does not echo the anchor location when set — a screen-reader user
  pressing F8 then Shift+arrow hears the *new* bounds but not the
  anchor. Add an announcement: "Anchor at line 12, column 5."
- **No column / box select.** See §4.3.
- **No "Copy with anchor" pair (start + end positions).** Useful
  for AI prompts that need offset ranges. Add a `copy_with_position`
  to the Edit menu: copies the selection and a footnote with the
  line / column range.
- **No "Mark here, jump there" status line.** The mark-ring list
  dialog lists marks with line / column but does not show the
  current ring head. Add a status-bar cell that announces "Mark ring
  depth: 4."

### 4.22 EdSharp 4.0.1 specific gaps

EdSharp is the closest reference for QUILL's screen-reader-first
niche. The hotkey summary in `S:\EdSharp-4.0.1\hotkeys.txt`
exposes a number of primitives that are *not* in QUILL but are
trivial to add. Honest call: the items below are real gaps.

| EdSharp hotkey / command                 | QUILL status                                                                                  | Notes for implementation                                                                     |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Select Chunk (Ctrl+Space)**            | Not present; `edit.word_prediction` is bound to Ctrl+Space                                    | Reassign or add `edit.select_chunk`; build `chunk_span(text, cursor)` primitive             |
| **Start Selection (F8) / Complete (Shift+F8)** | QUILL's F8 toggles extend-mode (different semantics)                                   | Two distinct ideas. Keep extend-mode on F8 (the QUILL convention) and add a separate "Start Selection" on Ctrl+. that anchors without extending |
| **Reselect (Ctrl+Shift+F8)**             | Partially — expand/shrink stack                                                                | Implement as "pop expand stack without committing"                                          |
| **Go to Start of Selection (Alt+Shift+F8)** | Not present                                                                                  | One-liner: collapse anchor to the smaller of the two bounds                                 |
| **Copy All (Ctrl+F8) / Unselect All (Ctrl+Shift+A)** | Not present                                                                            | Trivial                                                                                      |
| **Read All (Alt+F8) / Say Selected (Shift+Space) / Say Chunk (Shift+BackSpace)** | Not surfaced in the QUILL menu (Read Aloud exists for document playback)        | "Say Selected" maps cleanly to the existing TTS pipeline; "Say Chunk" is a chunk-span + TTS  |
| **Copy Append (Alt+C) / Cut Append (Alt+X)** | Not present                                                                                | Append to a per-document "Scratchpad" or to the clipboard with a " (continued)" separator    |
| **Append from Clipboard (Alt+7)**         | Not present                                                                                  | A toggle that, when on, auto-pastes every clipboard copy at the caret. Screen-reader users may find this noisy; gate it behind a "QUILL" chord |
| **Quote (Ctrl+Q) / Unquote (Ctrl+Shift+Q)** | Not present                                                                                | Wrap each line of the selection with a comment prefix inferred from the file extension (`#` for Python, `//` for C, `<!-- -->` for HTML, `>` for Markdown) |
| **Special Character (F2)**                | Not present in the QUILL menu (Power Tools may have it; verify)                              | Promote to Insert > Special Character... and bind to F2. Show a `wx.ListBox` of named Unicode blocks + a code-point entry |
| **Hard Line Break (Ctrl+Shift+H)**        | Not present                                                                                  | Calls `wrap_ops.hard_wrap(text, width)` with a prompted width. The inverse of `format.join_lines` |
| **Join Lines (Ctrl+Shift+J)**             | QUILL has `format.join_lines` (Ctrl+J family in some profiles; see `quill/core/keymap.py`) | Already there; verify the binding and the announcement parity with `wrap_ops.join_paragraph` |
| **Trim Blanks (Ctrl+Shift+Enter)**        | Not present                                                                                  | Trim trailing whitespace on every line of the selection; `format_ops.trim_trailing_whitespace` exists but is not on a single key |
| **Number Items (Alt+Shift+N) / Order Items (Alt+Shift+O) / Reverse Items (Alt+Shift+Z)** | QUILL has `sort_lines_ascending` / `descending` / `reverse_lines`; no per-item renumber | `line_ops.number_lines(text, start=1)` exists; expose a "Number Items" command and a "Number Items in Document" command |
| **Keep Unique (Alt+Shift+K)**             | `remove_duplicate_lines` exists; not on a single key                                          | Bind to a free chord and announce "Removed N duplicate lines"                                |
| **PyDent / PyBrace**                      | Not present                                                                                  | Python-indent ↔ braces converter. Power Tool or Quillin candidate                             |
| **Curly Brace Match (Ctrl+Shift+] / [)**  | `navigate.match_bracket` exists; no jump to enclosing / next                                 | Two commands: jump-to-enclosing and jump-to-next                                            |
| **Format Code (Ctrl+4)**                  | Not surfaced                                                                                | Wrap a Quillin: "Format Code" that uses Black / Ruff / isort depending on the file extension  |
| **Repeat Line (Ctrl+Y)**                  | QUILL's Ctrl+Y is Redo                                                                      | Either remap or add an Edit > "Repeat Line" with a different key                              |
| **Evaluate Expression (Ctrl+=)**         | Not present                                                                                  | Quillin: JScript / Python sandbox evaluation against the selection. Power Tool                |
| **Alternate Menu (Alt+F10)**             | Not present                                                                                  | A flat alphabetized list of every command. Easy to build from `quill.core.command_registry` |
| **SendTo Menu (Ctrl+F10)**                | Not present                                                                                  | A "Send to..." menu of internal actions (Editor, Read Aloud, Browser Preview, Compare)        |
| **Insert Time (Alt+Shift+;) / Calculate Date (Ctrl+Shift+;)** | Snippet variables exist (`$date$`, `$time$`) | Surface the two on first-class hotkeys                                                       |

The most important *single* addition here is **Select Chunk
(Ctrl+Space)**: it is a structural motion that QUILL's selection
pipeline can support today (one helper, one binding change, one
announcement). The second is **Quote / Unquote (Ctrl+Q /
Ctrl+Shift+Q)**: trivially useful, screen-reader-friendly
(announce the comment style that was applied), and the code is
already half-written in `quill.core.format_ops.toggle_line_comment`.

### 4.23 Text Monkey PRO transformation gaps

Text Monkey PRO (`http://www.boxersoftware.com/tmfeat.htm`) is a
useful reference for the *kind* of text cleanup that writers do all
day. QUILL's `Format > Transform Lines` submenu already covers a
respectable slice; the table below maps Text Monkey's categories
to QUILL's primitives, marking honest gaps.

| Text Monkey category                  | QUILL today                                                                                                | Gap                                                                                              |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **Email cleanup** (sense quoted email, remove `>` prefixes, line break → space) | Not present                                                                                              | One Quillin. Strip `> ` and `>`, then replace each `\n` with a space when the next line starts with `> ` |
| **Web document cleanup** (delete HTML tags, decode `&quot;` and `&#034;`) | `quill.io.structured` and `quill.io.export` import/export HTML using `html.escape` / `html.unescape`; no in-document "Strip HTML" command | Add `format.strip_html` and `format.decode_entities`; the latter is one call: `html.unescape(text)` |
| **Space ops** (reduce space runs, one / two spaces after sentence enders) | `format_ops.normalize_whitespace` collapses all whitespace runs to a single space; not a first-class command in the Format menu | Promote to a command and add a "Two spaces after period" toggle for the typography crowd |
| **Line ops** (delete duplicate lines, delete lines containing text) | `format_ops.remove_duplicate_lines` (with `case_sensitive` flag) is used by `LineCommandsMixin.remove_duplicate_lines`; "delete lines containing" is not surfaced | Add `format.delete_lines_containing` and `format.delete_lines_not_containing` (the opposite)     |
| **Indent ops** (indent with N spaces, custom string) | `format_ops.indent_lines` and `outdent_lines` use a configurable `indent_unit`                       | Promote to a dialog that lets the user type the indent string and applies it to the selection     |
| **HTML operations** (delete tags, decode / encode entities, &#nnn; obfuscation for email) | `quill.io.structured` and `quill.io.export` handle entities on import / export; no in-document command | Add `format.delete_html_tags` and `format.encode_entities` (use `html.escape`)                     |
| **Sort variations** (numerical, by line length, ANSI / Locale, random) | `format_ops.sort_lines(text, descending=False, case_sensitive=False)` uses an alphabetic key | Add `sort_lines_numeric`, `sort_lines_by_length`, `sort_lines_locale`, and `shuffle_lines` as Power Tools (or new commands) |
| **Auto-number** (roman numerals, padding, leading zeros) | `line_ops.number_lines(text, start=1, separator=". ")` is a basic implementation                | Extend to a dialog that picks start, separator, roman / arabic, padding                          |
| **Strip** (low ASCII, high ASCII, OEM line drawing) | Not present                                                                                              | Quillin candidate. Use `str.isprintable` / Unicode categories                                    |
| **Replace** (up to 4 simultaneous search / replace pairs) | `format.replace_all` is a single pair                                                                       | Quillin or Power Tool: a "Multi-Replace" dialog with N (configurable) pairs                      |
| **Stats** (sum, average, median, mode, std deviation on selected numbers) | `compute_document_stats` returns characters / words / lines                                              | Add a "Statistics on Selection" dialog that parses numbers and reports sum / mean / median / mode / stddev |
| **Hex dump conversion**                 | Not present                                                                                              | `format.to_hex_dump` / `format.from_hex_dump` Quillin candidate                                  |
| **Teen Text / Crazy Text** conversion  | Not present                                                                                              | Fun Quillin candidate. Not a 1.0 feature                                                         |
| **Clipboard viewer / editor with undo** | `wx.TheClipboard` is used by `magic_paste`, `copy_with_source`, and the standard paste path; no built-in viewer | A "Clipboard History" persistent side region that stores the last N (configurable) clipboard items; this also lets QUILL build the Copy Append / Cut Append behaviors EdSharp users want |

**High-priority additions** (mapped to existing core modules):

1. **`format.strip_html_tags(text) -> str`** — strip everything
   matching `<[^>]+>` from the selection. Useful for AI-pasted
   output. Put in `quill/core/format_ops.py` and wire to Format >
   Transform Selection.
2. **`format.decode_html_entities(text) -> str`** — `html.unescape`
   wrapper. Same home, same menu.
3. **`format.keep_unique_lines`** — the `case_sensitive` flag on
   `remove_duplicate_lines` already covers it; rename / alias the
   command to "Keep Unique Lines (Case Sensitive)" so the
   discoverability matches the industry term.
4. **`format.shuffle_lines`** — Quillin candidate, one core helper.
5. **`tools.statistics_on_selection`** — the dialog from
   `quill/core/metrics.py` + a number-parser. Spec the dialog as a
   stock `wx.Dialog` with a `wx.TextCtrl` for the report.

The clipboard history panel is the single biggest Text-Monkey-
adjacent win for screen-reader users: it makes Copy Append / Cut
Append / Append from Clipboard implementable, and it gives the user
a spoken record of the last N things they copied.

---

## 5. Industry callouts that QUILL handles correctly

Some behaviors that are easy to get wrong and that QUILL has right —
these are worth saying out loud so they don't regress.

1. **Find and Replace are inside Edit; cross-file search is in
   Search.** This matches the conventional split and matches VS Code
   / Word.
2. **Selection submenu** keeps line / paragraph / block distinct and
   adds "Recent Marks (Ring)" as a nested submenu. This is the Emacs
   influence done well, and it is keyboard-friendly.
3. **The Status Bar settings** live in Tools > Customize, not in
   View. This is a Microsoft convention; it survives menu shuffles.
4. **Insert / Format / Navigate are separate menus.** This matches
   Word and avoids the Notepad++ "everything is in one Format menu"
   trap.
5. **BITS Whisperer is a submenu of Tools when enabled**, and
   demoted from a top-level menu so the main bar stays at ten
   entries.
6. **Pandoc Wizard lives in Tools > Authoring and Automation** —
   not in a buried settings dialog. Power users can find it.
7. **External Tools** lives next to Pandoc and has an executable
   allowlist enforced by the codebase. This is the correct security
   posture.
8. **Compare Documents** is a real submenu (not a sub-submenu) with
   "Next Difference" / "Previous Difference" / "Announce Current" /
   "Difference List" / "Synchronized Navigation" / "Summary" / "Copy
   Current" / "Copy All." That is unusually complete.
9. **Custom Profiles and Feature Profiles** are under Help, not
   buried. Users can find them.
10. **Accessibility Audit, Keyboard Trap Snapshot, Contrast, Link
    Inventory** are all in Tools > Accessibility, not scattered. This
    is a deliberate discoverability choice.

---

## 6. Menu consolidation proposal

The current menu is 10 top-level entries, with Tools being 14-deep
and three submenus reaching a third level. The proposal is to keep
ten top-level menus (the Windows norm) and keep two as the
maximum depth inside any submenu.

### 6.1 Top-level layout (unchanged)

> File, Edit, View, Insert, Format, Navigate, Search, Tools, Window,
> Help. The conventional Windows order. Status bar settings lives in
> Tools > Customize.

### 6.2 Tools submenu: the proposed reorganization

Group the 14 current Tools submenus into 7 logical clusters. The
ordering is by frequency of use: writing essentials first, then
automation, then meta / configuration.

| Cluster                  | Items (submenu)                                                                              | Why                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Writing & Language       | Word Count, Spell Check, Previous/Next Misspelling, Misspelling List, Thesaurus, Dictionary Status | Unchanged from current "Writing and Language" submenu.                  |
| Reading & Dictation      | Read Aloud (with Voice / Settings / Generate Audio), Announcement Backend, Dictation, Watch Folder, OCR & Image | Merge Read Aloud + Dictation + Watch Folder + OCR/Image into one "Reading & Dictation" submenu. |
| Automation               | Macros, GLOW, Compare Documents, AI Assistant, BITS Whisperer                                 | Rename the current "Authoring & Automation" cluster; pull AI into it (it already lives under Tools). |
| Workspace                | Workspace Snapshots (relocated here from File), Sticky Notes, Sessions, Recent Files (relocated) | A new cluster that owns document organization. See §7.                 |
| Power Tools              | (All current Power Tools items)                                                              | Unchanged.                                                                 |
| Quillins                 | (All current Quillin items)                                                                  | Unchanged.                                                                 |
| Customization & Support  | Customize (Preferences, Menus, Profiles & Features, Status Bar, Export, Import, Keymap), Accessibility (Audit, Trap, Contrast, Link Inventory), Support (Notifications, Report Bug, Save Diagnostics, Logs, Updates) | A single "Settings & Support" cluster.                                  |

The Tools menu in two-deep form looks like:

```
Tools
├── Command Palette
├── ──────────
├── Writing & Language
│     ├── Word Count
│     ├── Spell Check
│     ├── Previous Misspelling
│     ├── Next Misspelling
│     ├── Misspelling List
│     ├── Thesaurus
│     └── Dictionary Status
├── Reading & Dictation
│     ├── Read Aloud  ▸
│     │     ├── Start / Pause
│     │     ├── Stop
│     │     ├── Voice
│     │     ├── Settings
│     │     └── Generate Audio
│     ├── Announcement Backend
│     ├── Dictation
│     ├── Watch Folder ▸
│     │     ├── Monitoring (in Settings)
│     │     ├── Profiles
│     │     └── Queue
│     ├── OCR Image
│     ├── OCR Clipboard
│     ├── OCR Screen
│     └── Describe Image
├── Automation
│     ├── Macros
│     ├── GLOW
│     ├── Compare Documents
│     ├── Document Intake
│     ├── Pandoc Wizard
│     ├── Regex Helper
│     ├── External Tools
│     └── YAML Structure Editor
├── AI Assistant
│     ├── Use AI
│     ├── AI Status
│     ├── AI Detail
│     ├── AI Hub
│     ├── Ask Quill Chat
│     ├── AI Model and Connection
│     ├── Forget API Key
│     ├── Session Branches
│     ├── Writing Assistant
│     ├── Prompt Studio
│     ├── Agent Center
│     ├── Accessibility Tune-Up
│     ├── Rewrite Selection
│     ├── Summarize Selection
│     ├── Continue Writing
│     ├── Fix Grammar
│     ├── Train Writing Style
│     └── Writing Instructions
├── BITS Whisperer (if enabled)
├── Workspace
│     ├── Workspace Snapshots ▸
│     │     ├── Save Current Snapshot
│     │     ├── Save As...
│     │     ├── Recent Snapshots ▸
│     │     └── Manage Snapshots...
│     ├── New Workspace from Folder...
│     ├── Sticky Notes
│     └── New Sticky Note
├── Power Tools
├── Quillins
├── Accessibility
│     ├── Accessibility Audit
│     ├── Keyboard Trap & Tab-Order Snapshot
│     ├── Validate Contrast
│     ├── Link Inventory & Alt-Text Catalog
│     ├── Inline Word Prediction (toggle)
│     ├── Auto-Format as You Type (toggle)
│     └── Smart Quotes (toggle)
└── Customize & Support
      ├── Preferences
      ├── Customize Menus
      ├── Profiles and Features
      ├── Status Bar Layout
      ├── Export and Back Up
      ├── Import or Restore
      ├── Keymap Editor
      ├── Export Keymap
      ├── Import Keymap
      ├── Reset Keymap
      ├── Notifications
      ├── Report a Bug
      ├── Save Diagnostics
      ├── Open Logs Folder
      ├── Open Diagnostics Folder
      └── Check for Updates
```

Two notable relocations:

- **Workspace Snapshots moves from File > Workspace Snapshots to
  Tools > Workspace**. The File menu is for "open / save this
  document" actions. Workspace is a "session of documents" concept
  and belongs with the cluster that will own the new Library
  surface (§7). A "Recent Snapshots" submenu replaces "Recent
  Sessions" inside the cluster.
- **Read Aloud** keeps its current submenu shape but is now nested
  inside Reading & Dictation. This keeps the two deep clusters
  (Read Aloud and Watch Folder) capped at the second level, which
  matches the standing "no third level" rule from the menu
  consolidation notes.

### 6.3 File menu

Suggested File menu reorganization (kept flat):

```
File
├── New
├── New from Template ▸  (existing Power Tools file-create items)
├── Open...
├── Open Recent ▸
├── Open from URL...
├── Open over SSH ▸
├── Workspace ▸  (new top-level submenu; see §6.4)
├── ──────────
├── Save
├── Save As...
├── Save All
├── Save As Plain Text...
├── ──────────
├── Reload from Disk
├── Restore Backup...
├── ──────────
├── Page Setup...
├── Print...
├── ──────────
├── Close Document
└── Exit
```

The Workspace submenu here is a *gateway* that links to the new
Workspace surfaces (Library, Snapshots, New from Folder) and to the
Tools > Workspace cluster where the management dialogs live. This
gives keyboard and screen-reader users two paths into the same
content.

### 6.4 View menu

```
View
├── Toggle Soft Wrap
├── Auto Side-by-Side Preview
├── Show Tab Control
├── Wrap Find Searches
├── Start With No Document Open
├── ──────────
├── Preview
├── Preview Side by Side
├── Focus Preview
├── Browser Preview
├── ──────────
├── Outline (toggle persistent outline panel; new)
├── Library (toggle persistent library panel; new)
├── Sticky Notes (toggle persistent sticky notes panel; new)
├── AI Chat (toggle persistent AI panel; new)
├── ──────────
├── Focus Mode (new; see §9.7)
└── Reading Ruler (new; see §9.8)
```

The four new toggles (Outline / Library / Sticky Notes / AI Chat)
show or hide the corresponding dialog content as a persistent
side region (see §7). "Focus Mode" is a one-key "F11" full-screen
writing surface that hides every chrome. "Reading Ruler" is a
high-contrast line-focus toggle for low-vision users.

### 6.5 Navigate menu

Already strong. Suggested additions (all behind the existing
feature-flag system):

- **Go To Bookmark in Workspace** — jump across documents in the
  current Workspace.
- **Go To Snippet** — fuzzy jump to a snippet.
- **Go To Misspelling** — already in the menu under Tools > Writing &
  Language; add a hotkey.
- **Go To Link** — already in Insert and Edit; ensure a key.
- **Go To Heading in Workspace** — cross-document heading jump
  when the active Workspace exposes headings.

### 6.6 Insert menu

Add: **Insert Image from File...**, **Insert Image from Clipboard**,
**Insert Math Block (LaTeX)**, **Insert Citation...** (when a
citation style is configured), **Insert Divider (Horizontal Rule)**,
**Insert Special Character...** (already likely in Power Tools;
promote to a first-class Insert entry).

### 6.7 Format menu

Add: **Auto-Format as You Type** toggle (under
Customize & Support currently; promote to Format or to View), and
**Smart Quotes / Smart Dashes / Smart Ellipses** toggles.

### 6.8 Help menu

Already has a sensible structure. Suggested additions:

- **QUILL Key Primer** (a screen-reader-friendly in-app quick
  reference, gated by the Help system).
- **Keyboard Reference (Printable)** — produces an accessible HTML /
  EPUB cheat sheet filtered by the active profile.
- **Workspace Tour** — first-run walkthrough of the new Library
  surface.

### 6.9 Search menu

Add: **Saved Searches**, **Search Results Window** (toggle docked
results), **Filter by Document** (when a Workspace is loaded).

---

## 7. Workspaces and Document Navigator: the redesign

This is the heart of the ask: take the existing Workspace Snapshots
concept and the existing `open_outline_navigator` modal and turn them
into a Ulysses/Obsidian/Scrivener-inspired but unmistakably QUILL
organization layer. The north star is *calm, keyboard-first, screen-
reader-narrated project organization*, with no new visual chrome a
sighted user would not also value.

### 7.1 Terminology

- **Workspace.** A named, restorable collection of documents,
  bookmarks, snippets, sticky notes, AI conversations, settings
  overrides, and shell hooks. The unit of "this is the project I am
  working on right now."
- **Sheet.** A single document inside a Workspace. Sheets are the
  atomic unit of focus. (The Ulysses name for a single document is
  "sheet" — borrowed on purpose because it is the right metaphor.)
- **Group.** A named, ordered folder of sheets within a Workspace.
  Groups nest. Groups are stored in the Workspace, not on the
  filesystem; the on-disk layout is the user's choice. (Ulysses
  uses "groups"; Scrivener uses "folders" inside the binder.)
- **Section.** A heading range inside a sheet. Sections are the
  unit of focus within a sheet. Already surfaced by
  `_outline_navigator`; now first-class inside the Library.
- **Library.** The on-screen, persistent side panel that shows the
  current Workspace's structure (Groups, Sheets, Sections) and
  drives the editor. (Ulysses name; matches the metaphor.)
- **Sticky Note.** A per-Workspace or global note pinned to a sheet
  or section. (Already exists; promote to a first-class Library
  surface.)
- **Snip.** A saved snippet bound to a Workspace. (New; extends the
  snippet system with a per-Workspace scope.)
- **Goal.** A writing target bound to a Workspace (daily / session /
  deadline). (Ulysses feature; new to QUILL.)
- **Filter.** A saved search / smart folder inside a Workspace.
  Filters are evaluated against the Workspace's sheets and persist
  with it.
- **Snapshot.** A saved point-in-time state of a Workspace.
  (Already exists; renamed for clarity.)
- **Session.** A loaded Workspace with the live documents open in
  the editor.

### 7.2 The Library panel

A docked `wx.Panel` on the left of the editor, toggleable from View
("Library"). The Library is the screen-reader page region with a
list of groups, sheets, and sections. It is *not* a tree (a flat
list with a heading level is more accessible); it shows the
Workspace's structure as a list with a single "level" disclosure
indicator.

Components (all stock wx):

- **Header** — Workspace name, last-saved time, word / character
  count, optional progress goal.
- **Filter** — a `wx.TextCtrl` at the top with a type-ahead filter.
  Matches sheet titles, sheet text, section titles, sticky note
  text, and tags. Announces the match count as it changes.
- **List region** — a `wx.ListBox` populated from the current
  Workspace's structure. Each entry has a label ("Chapter 3 >
  Beat sheet > 4. The reversal"), a kind (Group / Sheet / Section
  / Sticky Note / Filter result), and an optional state badge
  ("draft," "reviewed," "misspellings: 4," "modified").
- **Action bar** — buttons (or keyboard shortcuts): New Sheet, New
  Group, Rename, Delete, Move Up / Down, Promote / Demote, Open
  Sticky Note, Set Goal, Snapshot Now.
- **Context menu** — wired to the same actions. Stock wx context
  menu; no custom-drawn tree.

Behavior:

- **Live focus follows caret.** When the cursor moves to a section,
  the Library's selection moves with it (if the user has not
  manually scrolled the Library). Announce the change.
- **Keyboard re-order.** "Move Sheet Up" / "Move Sheet Down" /
  "Move Sheet to Group..." all in the Edit and Library menus.
- **Open in new editor tab / new window.** Long-form editing
  benefits from multiple open sheets. The Window menu gets "Next
  Sheet" / "Previous Sheet" if the user opts in to "open sheets in
  a tabbed editor."
- **Read-only by default; explicit write.** New Workspaces are
  empty until the user creates a sheet. Opening an existing
  Workspace Snapshot loads the document set, the caret positions,
  the AI sessions, and the sticky notes.
- **Save behavior.** A Workspace saves automatically on sheet save,
  on snapshot, and on a debounced interval (similar to settings
  persistence). Manual "Save Snapshot" is a menu item.

### 7.3 Outline panel (a docked tree)

Use the existing `_show_tree_navigator` logic but render it as a
panel, not a modal. The current modal is excellent for the
"right-now jump to" use case; the docked panel is for "let me see
the structure as I work." Behind the scenes both share a common
"outline index" primitive in `core/outline.py`. Both render the
same data through the same announcement grammar so the two
surfaces never disagree.

- The docked panel reads from the active sheet only.
- The modal still works for cross-document jumps inside a
  Workspace.
- Both speak the same names: headings, sections, blocks.

### 7.4 Workspace creation and persistence

A Workspace is a JSON file under `%APPDATA%\Quill\workspaces\`
(validated against `quill/core/schemas/workspace.json`). The
schema is intentionally tight:

```jsonc
{
  "schema_version": 1,
  "id": "ws_<uuid>",
  "name": "My Novel",
  "description": "Working title for the third book.",
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "groups": [
    {
      "id": "g_chapters",
      "name": "Chapters",
      "sheets": ["s_intro", "s_chapter1", "s_chapter2"],
      "groups": []
    }
  ],
  "sheets": {
    "s_intro": {
      "id": "s_intro",
      "title": "Introduction",
      "path": "C:\\...\\intro.md",
      "format": "markdown",
      "sticky_notes": ["n_open_question"],
      "snippets": ["sn_opening_quote"],
      "tags": ["draft"],
      "last_caret": 1234
    }
  },
  "sticky_notes": {
    "n_open_question": {
      "id": "n_open_question",
      "title": "Open question",
      "body": "Is the protagonist a reliable narrator?",
      "pinned_to": "s_intro"
    }
  },
  "snippets": {
    "sn_opening_quote": {
      "id": "sn_opening_quote",
      "title": "Opening quote",
      "body": "> ..."
    }
  },
  "tags": ["draft", "reviewed"],
  "filters": [
    {
      "id": "f_open_loose_ends",
      "name": "Open loose ends",
      "query": "TODO OR FIXME"
    }
  ],
  "goal": {
    "kind": "words_per_day",
    "target": 500,
    "period": "day"
  },
  "snapshots": [
    {
      "id": "snap_<uuid>",
      "name": "First draft complete",
      "saved_at": "2026-06-01T12:00:00Z"
    }
  ]
}
```

The schema is intentionally simple: groups nest, sheets live in
groups, sticky notes and snippets are flat collections with
optional pinning. Tags are a free-form string list. Filters and
goals are optional.

### 7.5 File-system mapping

A Workspace is a *logical* layer on top of the user's filesystem;
it does not require a particular directory layout. The user
chooses where each sheet lives; the Workspace stores the path. The
"New from Folder..." command:

1. Walks the chosen folder.
2. Filters by extension (configurable: `.md`, `.txt`, `.epub`, etc.).
3. Suggests a Group / Sheet structure based on the folder tree.
4. Asks once: "Use this layout? Yes / Preview / Edit." The Preview
   shows the proposed tree before any save.
5. Writes the Workspace file.

A "New from EPUB..." command opens an EPUB and creates a Workspace
where the chapters are sheets and the headings are sections.
Matches `open_epub_navigator` semantics.

### 7.6 Workspace Snapshots reborn

- Rename "Workspace Snapshots" to **Snapshots** (the term in the
  Ulysses vocabulary).
- A Snapshot stores the *complete state* of a Workspace at a point
  in time: sheets, caret positions, sticky notes, snippets, AI
  sessions, and the document bytes. This is what the current
  Workspace Snapshots already does; it just needs the rename and
  the menu relocation.
- A Snapshot is immutable. Restoring a Snapshot reopens the
  Workspace from the saved state. Diffing Snapshots is exposed
  through Compare Documents (current menu, current engine).
- Snapshots are exportable as a single `.qws.json` file (the
  Workspace file) and importable, with a conflict-resolution
  dialog for name collisions.

### 7.7 Filters and Smart Folders

A Filter is a saved search. Evaluation rules:

- Match sheets by title, body, sticky-note text, snippet text, or
  tags.
- Boolean expressions: `tag:draft AND title:ch*`.
- Regex support is opt-in.
- Result is a virtual group; opening a result jumps to the match
  in the source sheet.

Filters surface in the Library as a "Filters" sub-list. Selecting
a filter narrows the Library list to its matches; selecting
"Clear Filter" returns to the full list.

### 7.8 Goals and Progress

A Goal is a daily, session, or deadline target. The simplest form:

- Words per day (or characters or sentences).
- Words per session.
- Word count deadline ("reach 50,000 words by 2026-09-30").

The status bar gets a "Progress" cell that announces the
percentage and the remaining words. The Library header shows the
same. A "Streak" cell tracks consecutive days. A spoken
notification at end of session ("Goal reached: 500 words today")
is opt-in and respects the shared announcement grammar.

### 7.9 Cross-document navigation

A Workspace exposes new Navigate menu items:

- **Go To Heading in Workspace** — fuzzy jump across sheets in
  the current Workspace.
- **Go To Bookmark in Workspace** — same.
- **Go To Sticky Note in Workspace** — same.
- **Go To Tag** — opens the Library with the tag filter applied.
- **Go To Filter Result** — opens the active filter's matches.

All of these compose with the existing `quick_nav` index and
benefit from the same prewarm cache.

### 7.10 What this looks like as a flow

A first-run writer opens QUILL and is offered: "Start a new
Workspace, open a recent Workspace, or open a file." Selecting
"Start a new Workspace" shows a dialog: "Name, optional
description, optional folder to import from." A new Library
panel appears (or the docked outline tree appears) and the user
starts writing.

After 20 minutes the Library is full of groups, sheets, sticky
notes, and one filter ("TODO"). The status bar shows "Words:
1,234 of 500 today — goal reached." A single keystroke (Ctrl+K,
or QUILL+K) opens the command palette; typing "snapshot" offers
"Snapshot Workspace" and "Manage Snapshots."

A blind user goes through the same flow with the screen reader
narrating "Group: Chapters. Sheet: Introduction. Section: The
premise. Heading level 1. Word count 312." The panel is a
single list region, not a tree, and the focus is always
predictable.

### 7.11 Why this matches the Ulysses / Obsidian / Scrivener bar

- **Ulysses** — library, sheets, groups, filters, goals. QUILL
  borrows the *vocabulary* and the *single-list region* but
  replaces the Mac-only metaphors (sheet sidebar, keyboarder
  two-pane split) with the QUILL key + Quick Nav + docked panel
  + Workspace Snapshot model.
- **Obsidian** — vault, graph, backlinks, Bases. QUILL borrows
  the *vault metaphor* (Workspace = local vault) and the
  *saved filters* (Filters) but explicitly does not adopt the
  graph view in 1.0 (per the standing rules, axe-core, etc., are
  deferred to 2.0). A future "Backlinks" panel that scans the
  Workspace for `[[wiki-style]]` links is a natural 2.0 add-on.
- **Scrivener** — binder, corkboard, outliner, snapshots.
  QUILL borrows the *snapshots* (immutable saves) and the
  *binder* (Library panel) and adds a *Filter* concept that
  Scrivener lacks.
- **Org-mode** — tree, tags, agenda, babel. QUILL borrows the
  *tags* and the *agenda* (Goal) but not the babel / executable
  block. The user Python sandbox and Quillins cover similar
  ground in a more contained way.
The shape is *QUILL-native*: a docked left panel, the QUILL key,
Quick Nav, command palette, and a Workspace Snapshot JSON. The
metaphors are borrowed because they are the right ones; the
implementation is QUILL's.

---

## 8. "Make it amazing" — creative proposals

These are not strict backlog items. They are sketches to inspire
discussion, in priority order.

### 8.1 The QUILL key "what can I do here" panel

The roadmap already calls for a non-modal QUILL key overlay. The
proposal: when the user presses the QUILL key and pauses (no
follow-on key within 250ms), a small overlay appears at the
bottom-left of the editor showing the top ten follow-on keys for
the current context. The overlay is *navigable by arrows*, *closes
on Escape*, and is *announced by the screen reader*. Pressing a
follow-on key dismisses the overlay and runs the command. This is
"Spotlight meets the QUILL key."

### 8.2 Spoken Workspace Tour

A first-run experience for Workspaces: when the user opens a new
Workspace, the QUILL voice narrator walks through the structure
("Workspace: My Novel. 3 groups, 12 sheets, 4 sticky notes. Group
1: Chapters. Sheet 1: Introduction..."). The user can press
Escape to skip, or Space to continue. This is Ulysses's "Sheets"
onboarding, screen-reader-first.

### 8.3 Inline word and character count per section

A docked *Section Stats* cell that shows the word count, the
character count, the reading time, and the "misspelling hint" (a
small badge that links to the Misspelling List filtered to this
section). Updates as the user types. Announced on demand by a
status-bar query.

### 8.4 "Focal Mode" (F11)

A full-screen writing surface that hides the menu bar, the status
bar, the Library panel, the sticky notes, and the AI chat. The
editor is centered, the current paragraph is highlighted, and a
reading ruler (an optional 2-line band) follows the cursor. The
screen reader narrates the current sentence, the next sentence,
and the document position on every caret move. Voice: "Sentence
twelve of forty-two, paragraph three of seven, sheet
'Introduction', line 41." This is a writer's room, not a
distraction surface.

### 8.5 Audio Workspace

A Workspace that lives in the audio domain. A user opens an
audio file (or records into QUILL via BITS Whisperer), the
transcript becomes a sheet, the sticky notes become bookmarks,
and the Workspace's Goal is "minutes recorded today." This is
the same Workspace concept applied to a different content
type — and it is genuinely novel for a screen-reader-first
editor.

### 8.6 In-line AI "ghost" suggestions

A non-modal AI completion surface: as the user types, a small
ghost text appears (gray, italic) showing the AI's suggested
continuation. Pressing a configurable key ("QUILL + ." or "Tab
when no other completion is showing") accepts the suggestion.
"QUILL + ," dismisses. The suggestions are opt-in per Workspace
and respect the consent gate. This is a much lighter-weight AI
experience than the dialog-based rewrite / continue flow that
already exists.

### 8.7 Reading Mode

A mode that turns the editor into a read-only surface with a
configurable line-focus highlight, an optional reading ruler,
and a single key ("R") that reads the current sentence / line /
paragraph aloud using the existing Read Aloud engine. The screen
reader is *not* competing; the editor narrates only on demand.
This is iA Writer's Focus Mode with a screen-reader twist.

### 8.8 "Speak workspace" command

A single key that reads the Library's current selection in full:
the Workspace name, the structure (group > sheet > section), the
sticky notes pinned to the current sheet, the goal status, and
the last snapshot time. This is QUILL's "I am here" speech. It
takes one line of code and is a confidence-builder for new
users.

### 8.9 Inline status for sticky notes

When a sticky note is pinned to a sheet, a small status-bar cell
shows the count and the most-recent title. Focusing the cell
opens a query dialog; pressing Enter jumps to the Sticky Notes
panel filtered to the current sheet.

### 8.10 Quick Goal

A status-bar cell that opens a one-field "Daily Goal" prompt on
Enter. The user types 500, presses Enter, and the Goal is set
for the current Workspace. The cell updates to show progress.

### 8.11 Section-level Word Prediction

Take the existing `edit.word_prediction` dialog and add an inline,
opt-in, as-you-type variant that completes the current word from
the surrounding 50 characters of context. The screen reader is
*not* interrupted; the suggestion appears as a status-bar cell
and is accepted with one key. This is a much smaller lift than
LLM completion and is a high-frequency productivity win.

### 8.12 "Reveal in Workspace"

A context-menu action on any file path in the editor: "Reveal in
Workspace." If the file is in the current Workspace, the Library
panel scrolls to the matching sheet and announces it. If the
file is not in the current Workspace, the user is offered "Add
to Workspace" / "Open in New Workspace" / "Cancel."

### 8.13 Cross-document outline

A new Quick Nav category: "Workspace Headings" — every heading
in every sheet in the current Workspace, with a small badge
("Chapter 3 > 4. The reversal") showing the parent sheet. A
single keystroke jumps to it. This composes with `quick_nav`
without a new code path.

### 8.14 Section-level diff and review

A "Review Changes" mode that shows the diff between the current
sheet and the last Snapshot, organized by section. The screen
reader announces the section name and the change count. This is
Scrivener's "Compare" applied at the section level.

### 8.15 Section-anchored sticky notes

A sticky note can be pinned to a *section*, not just a sheet. The
note moves with the section as the user edits. This is a small
data-model change with a large usability impact for writers
doing research-heavy work.

### 8.16 Snippet: "paste Workspace context"

A snippet that, when expanded, pastes a YAML or Markdown
front-matter block with the current Workspace name, sheet name,
section name, line, and column. Useful for AI prompts, bug
reports, and structured notes.

### 8.17 Per-sheet feature profile

Allow a Workspace to override the global feature profile per
sheet. A research sheet might have AI disabled; a draft sheet
might have GLOW disabled; a publish sheet might have macros
disabled. This is a power-user feature; it does not need to be
the default.

### 8.18 Custom panel slots

A `View > Panels` submenu that lets the user choose which docked
panels to show: Library, Outline, Sticky Notes, AI Chat, Spell
Check, Search Results, Misspelling List. Each panel is a single
wx region; the user composes the layout.

### 8.19 Workspace-only "export to EPUB"

A command on the Workspace that orders the sheets, applies the
heading hierarchy, generates a table of contents, and exports a
single EPUB. The Pandoc wizard already does the conversion; the
Workspace layer does the assembly.

### 8.20 Workspace as a search corpus

Add a checkbox to the existing `search_in_files` dialog: "Limit
to current Workspace." The user can search the whole machine
or just the project.

### 8.21 "Sticky Note to Sheet" promote

A command on a sticky note that promotes it to a full sheet.
The note's title becomes the sheet title; the body becomes the
sheet's first paragraph. This is the inverse of "Sheet to
Sticky Note" and a common workflow ("I wrote a note, now I want
to expand it").

### 8.22 AI on a Workspace

The AI Hub gets a "Workspace" tab that shows the current
Workspace's structure and lets the user ask questions like
"What open loose ends do I have?" or "List the three
introductions that mention the antagonist." Answers cite the
sheet and section. The consent gate is the same.

### 8.23 Cross-Workspace references

A Workspace can include sheets from other Workspaces as
"references." Useful for a research Workspace feeding a
manuscript Workspace. The reference is a read-only copy in the
referring Workspace; updates are detected on Snapshot save.

### 8.24 "Today" view

A new panel that shows everything that changed in the current
Workspace today: new sheets, edited sheets, new sticky notes,
new snapshots, AI sessions, and the Goal progress. This is
Ulysses's "Today" list, screen-reader-first.

### 8.25 Workspace Diff

Two Workspaces can be diffed (sheet presence, sticky note text,
filter results). Useful for "what's different between the draft
I sent to the editor and the one I have now?"

### 8.26 Voice-driven Workspace navigation

A voice command (Hey QUILL) that opens a sheet by name, sets a
goal, or pins a sticky note. "Hey QUILL, open the introduction."
"Hey QUILL, set today's goal to 750 words." The dictation
engine is the same; the command grammar is Workspace-aware.

### 8.27 Workspace onboarding

A first-run "Try a Sample Workspace" that ships with QUILL:
a tiny project ("Letter to a friend") with three sheets, one
sticky note, one filter, and one goal. The user opens it,
explores the Library, the Outline, the Sticky Notes, the
Snapshots, and the AI Hub — all without writing a word. The
onboarding is itself screen-reader-friendly.

### 8.28 Per-section reading time and Flesch-Kincaid

Each section gets an announced reading time and a Flesch-Kincaid
grade level. The status bar cell toggles between "Words,"
"Reading time," and "Grade level." This is a writing-quality
superpower for a screen-reader user who can't see the wall of
text and wants a number.
### 8.29 Workspace focus session

A "Start a 25-minute focus session" command that opens a single
sheet, hides the Library and Sticky Notes, sets a 25-minute
timer, and announces the start and end. At the end, the Library
returns, the Goal cell updates, and a "Snapshot" button is
offered.

### 8.30 "I am stuck" command

A single key that opens a Workspace-aware AI prompt: "Help me
write the next paragraph of the current sheet, using these
three notes and this filter result as context." The consent
gate is the same; the response is previewed in a docked panel
and accepted with a single key. This is the AI "writer's block"
killer.

---

## 9. Implementation roadmap

Suggested sequencing, mapped to the existing roadmap priority
language.

### 9.1 Tier 1 (1.0 essentials)

- **Workspaces and Library panel** (§7). The core of the redesign.
  The new schema, the persistent side panel, the snapshot rename.
- **Menu consolidation** (§6). Pure reorganization. Ship a
  `menus.md` companion document alongside.
- **Focus Mode** (§8.4). Single screen, hides chrome.
- **Inline word prediction** (§8.11). High-frequency, low-risk.
- **Auto-format toggle** (§4.14). High discoverability win.
- **Context menu for misspellings** (§4.16). High discoverability
  win.
- **Duplicate selection** (§4.17). Tiny lift, big win.
- **Image insert** (§4.15). Required for many writing apps.
- **Go To Line preview** (§4.9). Trivial.
- **Select Chunk (Ctrl+Space)** (§4.22). Single most important
  EdSharp gap. One core helper, one binding change.
- **Quote / Unquote lines (Ctrl+Q / Ctrl+Shift+Q)** (§4.22). Half
  the code already exists in `format_ops.toggle_line_comment`.
- **Strip HTML tags + decode entities** (§4.23). Two
  `format_ops` helpers, two menu commands.
- **Announce anchor on F8** (§4.21). The most under-noticed
  selection-UX gap.

### 9.2 Tier 2 (post-1.0, near-term)

- **Filters and Smart Folders** (§7.7). Composes with Library.
- **Goals and Progress** (§7.8). Composes with Library.
- **Cross-document outline and quick nav extensions** (§7.9, §8.13).
- **Section-level stats** (§8.3).
- **Inline status for sticky notes** (§8.9).
- **Quick Goal** (§8.10).
- **Reveal in Workspace** (§8.12).
- **Multi-cursor / column select** (§4.3). Larger lift; needs a
  design pass.
- **Saved Searches** (§4.10).
- **Snippets tab stop / placeholder walkthrough** (§4.8).
- **AI chat docked** (§4.5).
- **Reading Ruler** (§4.13).

### 9.3 Tier 3 (exploratory, 2.0 and beyond)

- **Backlinks panel / vault graph** (Obsidian-style; explicit
  deferral per standing rules).
- **Corkboard view** (Scrivener-style).
- **Audio Workspace** (§8.5). Needs BITS Whisperer complete.
- **In-line AI ghost suggestions** (§8.6). Needs the consent
  surface to be a first-class UI element.
- **Cross-Workspace references** (§8.23).
- **Workspace diff** (§8.25).
- **Voice-driven Workspace navigation** (§8.26). Needs the
  voice-commands grammar to mature.
- **Clipboard history panel** (§4.23). Needs the dialog
  inventory's docked-panel classification; useful for Copy
  Append / Cut Append, but bigger surface than a Tier 1 item.
- **Statistical summary on selection** (§4.23). Bigger scope
  than Strip-HTML; needs a number-parser and a report dialog.
- **Multi-replace dialog** (§4.23). Genuine writer workflow
  improvement, but the dialog design and undo semantics need
  a design pass.
- **PyDent / PyBrace converter** (§4.22). Quillin candidate;
  needs test corpus.

### 9.4 Tier 4 (creativity, optional)

- **"Speak workspace" command** (§8.8). One-liner; high delight.
- **Workspace-only "export to EPUB"** (§8.19).
- **Per-section reading time and grade level** (§8.28).
- **Section-anchored sticky notes** (§8.15).
- **Sticky Note to Sheet promote** (§8.21).
- **"Today" view** (§8.24).
- **Workspace focus session timer** (§8.29).
- **"I am stuck" command** (§8.30).
- **Sample Workspace onboarding** (§8.27).
- **Snippet: paste Workspace context** (§8.16).
- **Per-sheet feature profile** (§8.17).
- **Custom panel slots** (§8.18).
- **Reading Mode** (§8.7).
- **Inline status for sticky notes** (§8.9, overlap).
- **Snippets for Workspace context** (§8.16, overlap).

---

## 10. The Revision Plan (binding)

This section is the **single source of truth** for what QUILL 1.0
will land, in what order, and why. Every recommendation in §1
through §9 is either accepted as written, accepted with edits
recorded below, or explicitly deferred with a reason. No
recommendation is "to be decided later."

Three corrections to the rest of the document are made here, not
sprinkled through the previous sections, so the plan is reviewable
as one piece:

- **Ulysses "Sheets" → "Entries."** §7 used the Ulysses word
  *Sheet* for a single document inside a Workspace. The user
  flagged that the word is too Ulysses-specific. From this
  point forward a single document inside a Workspace is an
  **Entry**. Multiple documents are **Entries**. The Workspace
  is a **Notebook** of Entries. This is a name-only change; no
  data model field is renamed in 1.0 — the JSON key
  `sheets[]` becomes `entries[]` in the new schema, but old
  files with `sheets[]` continue to load until 2.0.
- **No reading ruler, no focus mode pane.** §8.4, §8.7, §8.13,
  §4.7, §4.13 described a Reading Ruler and a focal pane. The
  user said: *we don't need a ruler, we don't need a pane, use
  the Document Navigator for the feature here.* The Document
  Navigator is the existing `_show_tree_navigator` modal at
  `quill/ui/main_frame.py:11732` and its partners
  (`open_outline_navigator`, `open_epub_navigator`,
  `open_yaml_structure_editor`, the Misspelling Navigator, the
  Document Intake dialog). All "focal" / "ruler" / "line focus"
  / "Reading Mode" ideas are withdrawn; the Document Navigator
  is the canonical "where am I, what is around me" surface, and
  it is **promoted to a top-tier verb** (Open Navigator, F7
  with a dedicated binding, dialog contract classified as
  `hardened_custom`, status-bar cell "Navigator: §3.2 The
  reversal").
- **Match EdSharp exactly where it matters.** The selection
  audit (§4.21) and the EdSharp gap audit (§4.22) are now
  consolidated into a single binding decision: §10.1 below
  *adopts EdSharp's selection model verbatim* for the new
  selection verbs, *keeps the F8 mode toggle* as a power-user
  opt-in, and *adds the four missing announcements* to the F8
  path. The earlier §4.21.2 "add commands alongside" framing
  is replaced by "add commands that are EdSharp-exact in
  semantics, keyed exactly as EdSharp keys them, and announce
  the same way EdSharp announces."

Everything else in §1 through §9 is accepted as written unless
explicitly struck through here.

### 10.2 Workspaces and Entries — the binding spec

This subsection replaces §7. The redesign is preserved in
spirit and reduced in scope: **Ulysses-grade full library
is deferred to 2.0**; 1.0 ships a Workspace with a
persistent Entries list, a focused Document Navigator
surface, and a Saved Searches manager. The goal is "match
what EdSharp and Notepad++ users actually do today,"
not "match Ulysses."

**Naming (binding).** A Workspace contains **Entries**.
An Entry is one file. Entries are organized in **Groups**
(ordered, nestable, stored in the Workspace JSON, not on
the filesystem). An Entry can have **Sections** (heading
ranges, computed from the document, not stored). A
Workspace can have **Sticky Notes** (already exist),
**Snippets** (already exist), and **Filters** (saved
searches, new in 1.0). A Workspace can have a **Goal**
(words per day, new in 1.0). A Workspace can be
**Snapshotted** (already exists; renamed from "Workspace
Snapshots" to **Snapshots**).

The naming replaces the §7 vocabulary:

| §7 word        | New word         | Why                                        |
| -------------- | ---------------- | ------------------------------------------ |
| Sheet          | **Entry**        | User said: not "Sheets."                   |
| Library        | **Entries panel**| More specific; matches the noun.           |
| Workspace JSON | **Notebook JSON** | Optional; "Workspace" is the verb.       |
| Library header | **Notebook header** | Optional; the panel is the Entries panel. |
| Group          | **Group** (unchanged) | Ulysses-coined, but neutral.            |
| Section        | **Section** (unchanged) | Standard.                              |
| Snapshot       | **Snapshot** (unchanged) | Already correct.                      |
| Goal           | **Goal** (unchanged)    | Already correct.                      |
| Filter         | **Filter** (unchanged)  | Already correct.                      |

**Document Navigator is the focal surface.** Per the user
direction, there is **no** new reading ruler, no new
focal pane, no new "where am I" widget. The Document
Navigator — the existing `_show_tree_navigator` modal at
`quill/ui/main_frame.py:11732` and its partners — is the
canonical "structure" surface. The 1.0 plan for it:

- Bind **F5** to `navigate.open_document_navigator` (the
  Outline Navigator, currently `Ctrl+Shift+O`). F5 is
  free in the default keymap; F7 is already taken by
  Spell Check (`tools.spell_check_dialog`,
  `quill/core/keymap.py:37`) and is anchored by
  `Alt+F7` / `Shift+Alt+F7` / `Shift+F7`, so it cannot
  be the navigator binding. The original draft of this
  plan said F7 was "previously unmapped" — that was
  wrong; this is the correction.
- Keep `Ctrl+Shift+O` as the secondary binding so users
  who learned it before the F5 promotion still get the
  navigator (legacy compatibility).
- Add a "Notebook" tab to the Document Navigator dialog
  that shows the current Workspace's Entries and Groups
  (replacing the §7 "Library panel slides in" idea).
  The tab is a `wx.Notebook` page that reuses the same
  tree-control primitive the Outline tab already uses.
- Add a status-bar cell "Navigator: §3.2 The reversal"
  that updates on caret move and announces on demand
  (`view.announce_navigator_position`, no default key).
- The Document Navigator dialog's dialog contract
  classification in `dialogs_inventory.json` is
  `hardened_custom` (already is). No new dialog class.

**Entries panel (the docked list).** A new top-level
View toggle **"Entries"** shows or hides a docked
`wx.Panel` on the left of the editor. The panel is a
`wx.ListBox` with the current Workspace's structure
(Groups, Entries, Sections). The panel:

- Has a header with Workspace name, last-saved time,
  word / character count, and optional Goal.
- Has a type-ahead filter `wx.TextCtrl` at the top.
  Matches Entry titles, body, Section titles, Sticky
  Note text, and tags. Announces match count on
  change.
- Live-focus follows the caret when the user has not
  manually scrolled the panel.
- Keyboard re-order: "Move Entry Up," "Move Entry
  Down," "Move Entry to Group..." in the Edit menu
  and the Entries panel context menu.
- A new View toggle **"Sticky Notes"** shows or hides
  a docked Sticky Notes panel (the existing
  `sticky_notes` infrastructure gets a docked surface
  in 1.0; the dialog is still `sticky_notes`).
- The docked Sticky Notes panel shares the
  "docked panel" classification in
  `dialogs_inventory.json` and follows the §6 menu
  layout.

**Workspace (Notebook) JSON schema (binding).** A new
file `quill/core/schemas/notebook.json` plus the
loader / writer in `quill/core/notebook_store.py`.
Stored at
`%APPDATA%\Quill\notebooks\<notebook-id>.qnb.json`.
Atomically written via
`quill.core.storage.write_json_atomic`. Validated
against the schema on load. Top-level shape:

```jsonc
{
  "schema_version": 1,
  "id": "nb_<uuid>",
  "name": "My Novel",
  "description": "",
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "entries": {
    "e_intro": {
      "id": "e_intro",
      "title": "Introduction",
      "path": "C:\\...\\intro.md",
      "format": "markdown",
      "tags": ["draft"],
      "last_caret": 1234,
      "sticky_notes": ["n_open_question"]
    }
  },
  "groups": [
    {
      "id": "g_chapters",
      "name": "Chapters",
      "entry_ids": ["e_intro", "e_chapter1", "e_chapter2"],
      "groups": []
    }
  ],
  "sticky_notes": {
    "n_open_question": {
      "id": "n_open_question",
      "title": "Open question",
      "body": "Is the protagonist a reliable narrator?",
      "pinned_to": "e_intro"
    }
  },
  "snippets": {
    "sn_opening_quote": {
      "id": "sn_opening_quote",
      "title": "Opening quote",
      "body": "> ..."
    }
  },
  "filters": [
    {
      "id": "f_open_loose_ends",
      "name": "Open loose ends",
      "query": "TODO OR FIXME"
    }
  ],
  "goal": {
    "kind": "words_per_day",
    "target": 500,
    "period": "day"
  },
  "snapshots": [
    {
      "id": "snap_<uuid>",
      "name": "First draft complete",
      "saved_at": "2026-06-01T12:00:00Z"
    }
  ]
}
```

The schema is intentionally tight. Groups nest.
Entries live in groups. Sticky notes and snippets are
flat collections with optional pinning. Tags are a
free-form string list. Filters and goals are optional.
Snapshots are immutable saves of the entire notebook
state.

**Workspace creation commands (1.0 set).** Five new
commands in the File and Tools menus:

- `file.new_notebook` — opens a `wx.Dialog` (classified
  `hardened_custom`) prompting for name, description,
  optional folder to import from. Creates the
  `.qnb.json`. No entries yet.
- `file.new_notebook_from_folder` — walks a folder,
  filters by extension (configurable), creates one
  Entry per file, groups by relative directory. Shows
  a Preview page before save.
- `file.open_notebook` — opens a `wx.FileDialog` filtered
  to `.qnb.json`, loads the notebook, restores the
  Entries, the caret positions, the sticky notes, the
  AI sessions, and the Snippets.
- `file.save_snapshot` — saves the current state as an
  immutable Snapshot. Bound to Ctrl+Shift+S.
- `file.manage_snapshots` — opens a `wx.Dialog` listing
  the snapshots for the current notebook, with
  Restore / Rename / Delete actions.

**Cross-document navigation (1.0 set).** Four new
commands in the Navigate menu:

- `navigate.go_to_heading_in_notebook` — fuzzy jump
  across all headings in the current notebook's
  entries.
- `navigate.go_to_bookmark_in_notebook` — fuzzy jump
  across all bookmarks.
- `navigate.go_to_sticky_note_in_notebook` — fuzzy jump
  across all sticky notes.
- `navigate.go_to_tag` — opens the Entries panel with
  the tag filter applied.

All four reuse the existing `quick_nav` index from
`quill/core/navigate.py`. No new code path is needed
beyond a category filter.

**Filters (1.0 set).** A new "Saved Searches" manager
in the Search menu. A Filter is a named saved search.
Evaluation rules:

- Match entries by title, body, sticky-note text,
  snippet text, or tags.
- Boolean expressions: `tag:draft AND title:ch*`.
- Regex support is opt-in.
- Result is a virtual group; opening a result jumps to
  the match in the source entry.

Filters surface in the Entries panel as a "Filters"
sub-list. Selecting a filter narrows the Entries list
to its matches; selecting "Clear Filter" returns to
the full list.

**Goals (1.0 set).** A Goal is a daily, session, or
deadline target. The simplest form:

- Words per day (or characters or sentences).
- Words per session.
- Word count deadline.

The status bar gets a "Progress" cell that announces
the percentage and the remaining words. The Entries
panel header shows the same. A "Streak" cell tracks
consecutive days. A spoken notification at end of
session ("Goal reached: 500 words today") is opt-in
and respects the shared announcement grammar.

**Snapshot rename.** "Workspace Snapshots" is renamed
to "Snapshots." The File menu loses
"Workspace Snapshots" entirely; the Tools menu gains
"Notebook" with submenu "Save Snapshot" (Ctrl+Shift+S),
"Save As..." (name a snapshot), "Recent Snapshots"
(last 10), "Manage Snapshots..." (the dialog above).
The rename is reflected in `quill/core/keymap.py` and
the `menu_label("Workspace &Snapshots", ...)` calls at
`quill/ui/main_frame_menu.py:850` and equivalents.

**What is explicitly *not* in 1.0 (deferred to 2.0):**

- The full "Ulysses library" with groups of groups of
  groups, per-Entry feature profiles, per-Entry
  backgrounds, per-Entry goals, cross-Notebook
  references, Notebook diff, Audio Notebooks, voice-
  driven Notebook navigation, sample Notebook
  onboarding. These are §8 long-tail items that are
  genuinely 2.0 work.
- Backlinks / vault graph (Obsidian-style). Explicit
  2.0 deferral per standing rules.
- Index-sheet / corkboard view (Scrivener-style).
  Explicit 2.0 deferral.
- AI on a Workspace. The AI Hub gets a "Notebook" tab
  in 2.0; in 1.0 the AI actions operate on the active
  Entry only.

### 10.3 Menu consolidation (binding)

This subsection refines §6. The proposal is to keep
ten top-level menus (the Windows norm) and cap
submenu depth at two. The Tools menu gets a single
**reorganization**; nothing is removed from the
functionality. The relocations below are binding.

**Top-level layout (unchanged from §6):**
File, Edit, View, Insert, Format, Navigate, Search,
Tools, Window, Help. Status bar settings lives in
Tools > Customize.

**File menu (binding):**

```
File
├── New
├── New from Template ▸
├── Open...
├── Open Recent ▸
├── Open from URL...
├── Open over SSH ▸
├── ──────────
├── New Notebook
├── Open Notebook...
├── New Notebook from Folder...
├── ──────────
├── Save
├── Save As...
├── Save All
├── Save As Plain Text...
├── ──────────
├── Save Snapshot                  (was Workspace Snapshots > Save Current)
├── Save Snapshot As...
├── Recent Snapshots ▸
├── Manage Snapshots...
├── ──────────
├── Reload from Disk
├── Restore Backup...
├── ──────────
├── Page Setup...
├── Print...
├── ──────────
├── Close Document
└── Exit
```

**Edit menu (binding).** Adds the new selection verbs
from §10.1:

```
Edit
├── Undo
├── Redo
├── ──────────
├── Cut
├── Copy
├── Copy with Source                (Ctrl+Shift+C, unchanged)
├── Copy with Position              (new; trailing "[line N col M – line P col Q]")
├── Paste
├── Magic Paste                     (QUILL key, V; was Ctrl+Alt+V)
├── ──────────
├── Start Selection                 (F8; was Toggle Extend Selection Mode)
├── Complete Selection              (Shift+F8; new)
├── Reselect                        (Ctrl+Shift+F8; new)
├── Go to Start of Selection        (Alt+Shift+F8; new)
├── Go to End of Selection          (new)
├── Extend Selection Mode           (Insert+F8; was F8; preserves the mode)
├── ──────────
├── Select Line
├── Select Paragraph
├── Select Block
├── Expand Selection
├── Shrink Selection
├── Select Chunk                    (Ctrl+Space; new; replaces word_prediction on Ctrl+Space; word_prediction moves to QUILL key, W)
├── ──────────
├── Find
├── Find Next
├── Find Previous
├── Find All Matches
├── Replace...
├── Go to Line...
├── ──────────
├── Move Entry Up
├── Move Entry Down
├── Promote / Demote
└── Duplicate Selection             (new; block-level copy)
```

**Insert menu (binding).** Adds Image, Math, Citation
placeholders that were §4.15 / §4.18 recommendations:

```
Insert
├── Heading
├── Subheading
├── ──────────
├── Link
├── Footnote
├── Endnote
├── Citation...                     (new; placeholder for 1.0)
├── Divider (Horizontal Rule)
├── ──────────
├── Image from File...
├── Image from Clipboard
├── Math Block (LaTeX)
├── Special Character...            (F2; promoted from Power Tools)
├── Date / Time                     (Alt+Shift+; — EdSharp parity)
├── ──────────
├── Task List Item
├── Sticky Note
└── Quick Text ▸                    (existing snippet submenu)
```

**Format menu (binding).** Adds Strip HTML / decode
entities / Quote / Unquote / keep unique / shuffle /
statistics on selection from §4.23 and §4.22:

```
Format
├── Character Case ▸
│   ├── UPPER
│   ├── lower
│   ├── Title
│   ├── Sentence
│   └── Toggle (Swap)
├── ──────────
├── Toggle Line Comment             (Ctrl+/)
├── Toggle Block Comment            (Shift+Alt+A)
├── Quote Lines                     (Ctrl+Q; new)
├── Unquote Lines                   (Ctrl+Shift+Q; new)
├── ──────────
├── Indent
├── Outdent
├── Tab to Spaces                   (new)
├── Spaces to Tab                   (new)
├── ──────────
├── Trim Trailing Whitespace
├── Normalize Whitespace
├── Trim Blanks                     (Ctrl+Shift+Enter; new)
├── ──────────
├── Sort Lines Ascending
├── Sort Lines Descending
├── Reverse Lines
├── Shuffle Lines                   (new)
├── Keep Unique Lines               (Alt+Shift+K; new)
├── Remove Duplicate Lines          (was; kept)
├── Number Items                    (Alt+Shift+N; new)
├── Order Items                     (Alt+Shift+O; new)
├── Reverse Items                   (Alt+Shift+Z; new)
├── ──────────
├── Hard Line Break                 (Ctrl+Shift+H; new)
├── Join Lines                      (Ctrl+Shift+J; was)
├── ──────────
├── Strip HTML Tags                 (new)
├── Decode HTML Entities            (new)
├── Encode HTML Entities            (new)
└── Statistics on Selection         (new; sum/mean/median/mode/stddev)
```

**Navigate menu (binding).** Adds the four cross-
Notebook verbs and the Navigator toggle:

```
Navigate
├── Go to Line...
├── Go to Bookmark
├── Go to Heading
├── Go to Link
├── ──────────
├── Go to Heading in Notebook       (new)
├── Go to Bookmark in Notebook      (new)
├── Go to Sticky Note in Notebook   (new)
├── Go to Tag                      (new)
├── Go to Misspelling              (add; was under Tools)
├── ──────────
├── Open Document Navigator         (F5; promoted; was Ctrl+Shift+O; Ctrl+Shift+O remains)
├── Open EPUB Navigator
├── Open YAML Structure Editor
├── ──────────
├── Quick Nav
├── Announce Navigator Position     (new; status-bar cell query)
└── Announce Selection State       (new; status-bar cell query)
```

**Search menu (binding).** Adds Saved Searches and
the in-notebook filter:

```
Search
├── Find
├── Find Next
├── Find Previous
├── Replace...
├── Find in Files
├── ──────────
├── Saved Searches...
├── Search Results Window           (toggle docked results)
├── Filter by Current Notebook      (checkbox on Find in Files)
└── Clear Search History
```

**View menu (binding).** Adds the docked-panel
toggles, drops the "Focus Mode" and "Reading Ruler"
ideas:

```
View
├── Toggle Soft Wrap
├── Auto Side-by-Side Preview
├── Show Tab Control
├── Wrap Find Searches
├── Start With No Document Open
├── ──────────
├── Preview
├── Preview Side by Side
├── Focus Preview
├── Browser Preview
├── ──────────
├── Entries                         (toggle docked Entries panel; new)
├── Sticky Notes                    (toggle docked Sticky Notes panel; new)
├── Search Results                  (toggle docked Search Results; new)
├── Spell Check List                (toggle docked Misspelling List; new)
├── ──────────
├── Status Bar Layout...
├── Show All Characters             (toggle)
└── High Contrast                   (toggle)
```

**Tools menu (binding).** Reorganizes into seven
clusters. The two-deep cap is enforced.

```
Tools
├── Command Palette                  (Ctrl+K; moved from Navigate)
├── ──────────
├── Writing & Language
│   ├── Word Count
│   ├── Spell Check
│   ├── Previous Misspelling
│   ├── Next Misspelling
│   ├── Misspelling List
│   ├── Thesaurus
│   ├── Dictionary Status
│   ├── Add to Document Dictionary
│   └── Ignore for Session
├── Reading & Dictation
│   ├── Read Aloud ▸
│   ├── Stop Reading
│   ├── Say Selected                 (Shift+Space; new)
│   ├── Read All                     (Alt+F8; new)
│   ├── Dictation ▸
│   ├── OCR Image
│   ├── OCR Clipboard
│   ├── OCR Screen
│   └── Describe Image
├── GLOW
│   ├── Audit Document
│   ├── Audit Selection
│   ├── Fix Document
│   └── Fix Selection
├── Comparison
│   ├── Compare Documents
│   ├── Next Difference
│   ├── Previous Difference
│   ├── Announce Current Difference
│   ├── Difference List
│   ├── Synchronized Navigation
│   ├── Difference Summary
│   ├── Copy Current Difference
│   └── Copy All Differences
├── Watch Folder
│   ├── Watch Folder Profiles...
│   ├── Watch Folder Queue...
│   └── Toggle Watch Folder
├── AI Assistant
│   ├── Use AI
│   ├── AI Status
│   ├── AI Detail
│   ├── AI Hub
│   ├── Ask Quill Chat
│   ├── AI Model and Connection
│   ├── Forget API Key
│   ├── Session Branches
│   ├── Writing Assistant
│   ├── Prompt Studio
│   ├── Agent Center
│   ├── Accessibility Tune-Up
│   ├── Rewrite Selection
│   ├── Summarize Selection
│   ├── Continue Writing
│   ├── Fix Grammar
│   ├── Train Writing Style
│   └── Writing Instructions
├── Power Tools ▸
│   ├── Power Tools...
│   ├── Pandoc Wizard
│   ├── External Tools...
│   ├── Macros ▸
│   ├── Snippets ▸
│   ├── Form Library ▸
│   └── Authoring & Automation ▸
├── Accessibility
│   ├── Accessibility Audit
│   ├── Keyboard Trap & Tab-Order Snapshot
│   ├── Validate Contrast
│   ├── Link Inventory & Alt-Text Catalog
│   ├── Inline Word Prediction (toggle)
│   ├── Auto-Format as You Type (toggle)
│   └── Smart Quotes (toggle)
└── Customize & Support
    ├── Preferences
    ├── Customize Menus
    ├── Profiles and Features
    ├── Status Bar Layout
    ├── Export and Back Up
    ├── Import or Restore
    ├── Keymap Editor
    ├── Export Keymap
    ├── Import Keymap
    ├── Reset Keymap
    ├── Notifications
    ├── Report a Bug
    ├── Save Diagnostics
    ├── Open Logs Folder
    ├── Open Diagnostics Folder
    └── Check for Updates
```

**Window menu (unchanged from §6):** standard Window
list, plus "Next Entry" / "Previous Entry" toggles
when the user opts in to "open entries in a tabbed
editor" in Preferences.

**Help menu (binding).** Adds the QUILL Key Primer:

```
Help
├── Contents
├── QUILL Key Primer                 (new; in-app quick reference)
├── Keyboard Reference (Printable)   (new; HTML/EPUB cheat sheet filtered by active profile)
├── Notebook Tour                    (new; first-run walkthrough of the Entries panel)
├── ──────────
├── Check for Updates
├── About QUILL
└── ──────────
    ├── Custom Profiles ▸
    └── Report a Bug
```

### 10.4 The 1.0 milestone — what lands, in what order

The plan is sequenced into four milestones, each of
which is reviewable on its own. Each milestone ends
with a green test suite and a green dialog-inventory
gate.

**Milestone 1: Selection announcements + EdSharp parity. COMPLETE.**
All eight EdSharp-parity selection commands shipped (commit 46032bd).
`tests/unit/ui/test_edsharp_selection_parity.py` passes (22 tests).

**Milestone 2: Notebook (Workspace) JSON + Entries
panel + Document Navigator upgrades. COMPLETE.**
Shipped in the session following commit 106ef2c.
`notebook_store.py`, `notebook_panel.py`,
`notebook_navigator_page.py`, `NotebookUIMixin`,
`notebook_goal` status-bar cell, File > Notebook
submenu (5 commands), Navigate notebook commands
(4 commands), View > Show Entries Panel, snapshot
rename, `core.notebook` feature, `dialogs.md`
section X, `dialog_inventory.json` regenerated.

**Milestone 3: Format and Transform completeness
(this is the "Text Monkey PRO subset" milestone —
deliberately a subset, full Text Monkey is 2.0).**

- New helpers in `quill/core/format_ops.py`:
  `strip_html_tags`, `decode_html_entities`,
  `encode_html_entities`, `tab_to_space`,
  `space_to_tab`, `shuffle_lines`, `keep_unique_lines`,
  `trim_blanks`. All wx-free; covered by mypy in
  `quill\core`.
- New helper in `quill/core/stats.py`:
  `selection_statistics(text) -> dict` returning
  `count`, `sum`, `mean`, `median`, `mode`,
  `stddev` for the numbers in `text`.
- New menu commands per the Format menu in §10.3.
- Promote `Special Character` to Insert and bind F2.
- Promote `quote_lines` / `unquote_lines` to Edit
  and bind Ctrl+Q / Ctrl+Shift+Q.
- Promote `select_chunk` to Edit and bind
  Ctrl+Space. Move `word_prediction` to Ctrl+.
- **Acceptance:** a user can paste HTML into a
  document, select it, run Format > Strip HTML Tags,
  and see plain text; select a column of numbers
  and run Format > Statistics on Selection to get a
  spoken report; select a Python comment block and
  press Ctrl+Q to comment it, Ctrl+Shift+Q to
  uncomment it.
- **Multi-cursor and rectangular selection are
  NOT in this milestone.** The 2.0 design is
  §10.7. The 1.0 plan does not paint us into a
  corner because the single-range shim in
  §10.7.2 keeps every existing consumer
  compiling; the new commands are feature-flagged
  behind `feature.multi_caret_v2`.

**Milestone 4: Menu consolidation + keymap parity
(this is the "ship it" milestone — every binding
documented, every menu flat at two levels).**

- Land §10.3 in full: every menu reorganized, every
  submenu capped at two levels, every verb
  documented in `dialogs.md` and `menus.md`.
- `python -m quill.tools.dialog_inventory --write`
  runs clean.
- `python -m quill.tools.menu_lint` (new tool) runs
  clean.
- `python -m quill.tools.quillin_lint` runs clean.
- All four §10.1 / §10.2 / §10.3 test files pass.
- The full `pytest tests\unit\tests\stability`
  suite passes (with the two known hangs ignored
  per the standing rules).
- The `tests/unit/ui/fixtures/main_frame_public_surface.json`
  is regenerated via
  `python -m quill.tools.ui_surface --write` and
  committed.
- **Acceptance:** the `menus.md` companion document
  in the repo root describes the final menu
  layout, every command is bound, every dialog is
  in the inventory, every selection verb is
  announced.

### 10.5 What is explicitly out of scope for 1.0

The following are not 1.0 work and are not part of
this plan. They are listed here so the plan is
reviewable as a single bounded piece:

- Backlinks panel / vault graph (Obsidian-style);
  axe-core / Nu Html Checker; BITS Whisperer
  top-level promotion; GLOW watch-action binding
  (WATCH-8); the AX-A..F Accessibility Agents
  workstream; multi-cursor / column select;
  clipboard history panel; full Ulysses library
- Reading Ruler, Focal Mode, Reading Mode. All
  withdrawn per the user's direction. The Document
  Navigator is the canonical structure surface.
- Live OCR (OCR-1/3), live device-login AI (AI-19),
  sensitivity-aware dictation (SET-2), advisory
  agent mode (AGENT-1). All require a real Windows
  runtime and stay "In progress" per the standing
  rules.

### 10.6 Review checklist for the plan

The user will review the plan against these eight
questions; the answers must be unambiguous:

1. **Does F8 now announce an anchor?** Yes. F8 is
   `edit.start_selection`. It sets
   `self._selection_anchor`, calls
   `line_column_for_position`, and announces
   "Selection started at line N, column M."
2. **Does arrow-down after F8 announce a growing
   region?** No, by design — the EdSharp model is
   silent during roam. The *anchor* is announced at
   F8 time, the *region* is announced at Shift+F8
   time. (For users who want a live growing-region
   announcement, the Insert+F8 mode toggle still
   works and announces anchor and region spans.)
3. **Is "Sheets" gone?** Yes. Replaced with
   "Entries" in every menu, dialog, status-bar
   cell, and JSON field.
4. **Is there a reading ruler or focal pane?**
   No. Both withdrawn. The Document Navigator
   (F5) is the canonical structure surface.
5. **Are the EdSharp keys exactly where they were
   in EdSharp?** F8 = Start Selection. Shift+F8 =
   Complete Selection. Ctrl+Shift+F8 = Reselect.
   Alt+Shift+F8 = Go to Start of Selection.
   Ctrl+F8 = Copy All. Ctrl+Shift+A = Unselect
   All. Shift+Space = Say Selected. Alt+F8 =
   Read All. (Three of the six are new in 1.0; the
   user gets the same key, the same verb, the same
   announcement as EdSharp.)
6. **What is in 1.0 vs 2.0?** 1.0 is Milestones 1–4
   above. 2.0 is §10.5 above plus the multi-cursor
   and rectangular-selection design in §10.7.
   There is no "maybe later" — every item is
   either in 1.0, in 2.0, or in §10.5 as a deferral
   with a reason.
7. **What is the test plan?** Milestone 1 is complete:
   `tests/unit/ui/test_edsharp_selection_parity.py` (22 tests, passing).
   Milestone 2 adds
   `tests/unit/ui/test_notebook_store.py`,
   `tests/unit/ui/test_notebook_panel.py`,
   `tests/unit/ui/test_notebook_navigator_page.py`.
   The 2.0 multi-cursor work adds the ten test
   files in §10.7.9.
8. **How does multi-cursor not break the screen
   reader?** §10.7.3 — three obligations: (1)
   always speak one caret at a time, (2) every
   command is deterministic and idempotent with a
   single announcement per action, (3) no
   "primary/secondary" visual language. The full
   design is §10.7; the tests are §10.7.9.
9. **Why are there no `Ctrl+Alt+` bindings in the
   plan?** §10.8 — the QUILL key chord absorbs
   every `Ctrl+Alt+` verb. The full remap table
   is §10.8.2; the rationale is §10.8.1.

### 10.7 Multi-cursor and rectangular selection (2.0 design)

The plan keeps multi-cursor and rectangular
selection as a 2.0 feature (still listed in
§10.5). This subsection is the design we will
implement in 2.0 — screen-reader-first, no
visual metaphor, no parity theater. The job of
this subsection is to lock the design now so
the 1.0 work does not paint us into a corner
(especially around selection model, command
routing, and announcement surface).

#### 10.7.1 Why this is not 1.0

The current selection model is
`tuple[int, int]` (start, end) in
`quill/core/selection.py` and a single
`_extend_selection_anchor` in
`quill/ui/main_frame.py:945`. Every consumer —
copy, cut, paste, paste-with-source, magic-paste,
move-line-up/down, comment toggle, sort,
reverse, dedupe, every transform — assumes one
range. Promoting that to a list of ranges
silently breaks the entire command surface.
The honest path is to land the binding spec
above, then build multi-cursor on top of it
as a 2.0 milestone, with its own migration and
its own test plan. Same reasoning the plan
already uses for the AX workstream and BITS
Whisperer.

#### 10.7.2 Selection model (2.0)

Promote the single range to an ordered list of
disjoint, non-overlapping ranges called
**`SelectionSet`**. The primary caret is the
range that contains the focus point; every
other range is a **secondary caret** (no
"primary" vs "secondary" rhetoric in the
audible surface — just "caret 1 of 3, line N,
column M" when the user moves).

```python
# quill/core/selection_set.py (2.0, new file)
@dataclass(frozen=True, slots=True)
class Selection:
    start: int
    end: int  # inclusive-exclusive

class SelectionSet:
    primary: Selection
    others: tuple[Selection, ...]  # sorted by start
    anchor: int | None  # set by F8; refers to a position, not a range
```

Rules:

- All ranges are normalized (start <= end) and
  merged if they overlap when added
  (no two ranges that touch or overlap).
- The primary caret is the range that contains
  the focus point; on tie, the one that ends
  latest wins. The other ranges are read in
  start order for "next caret" navigation.
- `anchor` is **not** a range. It is the
  position set by F8 (Start Selection). When
  the user types or arrows, the *primary*
  range grows from `anchor`; secondary ranges
  do not grow. This is the EdSharp model, just
  extended to N primary regions. (See §10.1.)
- `quill/core/selection.py` keeps the existing
  `word_span` / `line_span` / `paragraph_span` /
  `sentence_span` / `block_span` / `expand_selection`
  / `shrink_selection` / `selection_scope` helpers;
  they now operate on a single `Selection` and
  return a `Selection`. New
  `selection_set_scope(set) -> list[str]` returns
  the scope of every range for the announcement
  surface.
- The single `tuple[int, int]` API stays as a
  **shim** that returns `(primary.start,
  primary.end)`. Every existing consumer keeps
  compiling; commands that touch a selection
  get a `SelectionSet`-aware variant behind a
  feature flag (`feature.multi_caret_v2`).

#### 10.7.3 Screen-reader-first model

The "screen reader first" rule is the reason
multi-cursor is a bigger lift than it is in
VS Code, and the reason it is the right lift.
The design has three obligations:

**1. Always speak one caret at a time.** The
focused caret is the **only** caret the screen
reader hears while it moves. Secondary carets
are silent during arrow / type / mouse motion.
The user can press a dedicated command
(`selection.speak_selection_set`,
**`Alt+Shift+Space`**, see §10.7.6) to hear
"3 carets. Caret 1 of 3: line 12, column 4.
'Hello world, 22 characters.' Caret 2 of 3:
line 14, column 8. 'Second line.' Caret 3 of 3:
line 16, column 1. 'Third line.'" This is the
one and only time the user hears about all
carets at once. The user can also press
`selection.next_caret` /
`selection.previous_caret` to step through
carets; stepping announces the new primary
caret the same way a single caret does today.

**2. Selection verbs are deterministic and
idempotent.** Copy, cut, delete, transform,
indent, comment toggle, sort, reverse, dedupe
all operate on the **`SelectionSet` as a
unit**, in a single undo entry, with a single
announcement. The rule is:

- "Operate on every caret, in parallel,
  against the original text snapshot." This
  is the VS Code rule; it is also the only
  rule that does not produce surprising
  results when ranges overlap a region that
  shifted because of an earlier caret's
  action.
- The announcement is the **count** of
  affected ranges and a one-line summary, not
  the full text of every region. "Replaced
  text in 3 places. 14 characters." not
  "Replaced 'Hello world' in caret 1 with
  'Goodbye world', replaced 'Second' in caret
  2 with 'Third'..." Multi-cursor is a
  power-user tool, not a screen-reader
  narrator.
- If the user explicitly wants per-caret
  speech, they call `selection.speak_affected`
  (**`Alt+Shift+'`**, see §10.7.6), which is
  the same verb broken down caret by caret.

**3. There is no "primary/secondary" visual
language.** There is a **focused caret** (the
one the screen reader is speaking), and there
are **other carets** (silent). The status-bar
cell shows "Caret 1 of 3" when the user has
asked for that cell. There is no "leader"
caret color, no "ghost caret" rendering, no
"inactive selection" gray, no blinking other
carets. The status cell is the only place
"of N" appears, and the user can hide it.

These three rules are what make the feature
ship-able to a screen-reader-first audience.
They are also the source of most of the test
matrix in §10.7.7.

#### 10.7.4 Adding and removing carets

**Add caret below**
(`selection.add_caret_below`):
**`QUILL key, J`** (add caret **J**ust
below). The chord pattern is "press the
QUILL key, release it, then J." The screen
reader announces "QUILL key" when the prefix
is pending, then "Caret added below" after
J. Adds a caret one visual row below the
current caret, in the same column (or the
last column of the shorter line if the row
is shorter). Announces "Caret 2 of 2, line
N, column M." If the focused caret is
already on the last visual row, the command
does nothing and announces "No row below."

**Add caret above**
(`selection.add_caret_above`):
**`QUILL key, K`**. The chord pattern is
the same: prefix-then-key. The K mnemonic
is "Karet above" (caret, with a K for the
keyboard tradition of K = up). Mirror of
the above.

**Add carets to all occurrences**
(`selection.add_caret_to_all_occurrences`):
**`QUILL key, A`** (the existing A binding
in Quick Nav; here it is repurposed under
the QUILL key chord to mean "Add caret to
all matches of the current word/selection").
If a selection is active, every match of
the selected text in the document gets a
caret. If no selection, the current word is
used. Announces "3 carets. Caret 1 of 3:
line 5." The first caret is the original;
matches are sorted by document order.
Empty-document and zero-match cases
announce "No matches" and the caret count
is unchanged.

**Add carets to line ends**
(`selection.add_caret_to_line_ends`):
**`QUILL key, E`** (E for "End of line").
Adds a caret at the end of every line in
the current selection. No selection = every
line in the document. Announces "Added
caret to N line ends."

**Remove focused caret**
(`selection.remove_focused_caret`):
**`QUILL key, X`** (X for the universal
"cut" mnemonic, repurposed as "cut this
caret out of the set"). If only one caret
remains, the command does nothing and
announces "1 caret. Cannot remove."
Otherwise announces "Caret removed. 2
carets remain."

**Remove all secondary carets**
(`selection.clear_secondary_carets`):
**`Escape`** (the existing Escape path is
reused; see below). Collapses back to a
single caret at the position of the focused
caret. The single caret is now the primary,
and the SelectionSet is empty (`others = ()`).
Announces "1 caret."

The Escape key already does three things
today (cancel extend-selection mode, cancel
find, close dialogs). The 2.0 Escape
resolution is: **dialog > rectangle >
multi-caret collapse > extend-selection
mode > find bar**. The first matching
context wins. This
is the same priority rule EdSharp and
Notepad++ use. Documented in the help
cheatsheet and the
`tests/unit/ui/test_escape_priority.py` test.

#### 10.7.5 Stepping between carets

**Next caret**
(`selection.next_caret`): **`QUILL key, N`**
(N for "Next caret"; the existing Quick
Nav `quill.quick_nav.skip_forward` keeps
`]`). Inside the QUILL key prefix, N steps
to the next caret in document order, N+Shift
steps to the previous. The screen reader
announces "Next caret. Caret 2 of 3, line
14, column 8." This is consistent with the
EdSharp / `expand_selection` model:
structural navigation is the single-caret
default (the Quick Nav letters H, A, L, I,
T, Q, B, ', C, P, S, [, ] still work as
before); multi-caret navigation is the
QUILL-key prefix.

**Previous caret**
(`selection.previous_caret`): **`QUILL key,
Shift+N`**. The mirror binding.

**Caret N of M**
(`selection.announce_caret_position`):
**`QUILL key, /`** (slash for "where am I?").
Says the focused caret's line, column,
"of N," and the count of characters from
the start of the document. The same
announcement the single-caret
status-bar cell already gives, extended for
multi-caret.

The behavior of Home, End, Page Up, Page
Down, Ctrl+Home, Ctrl+End, the word /
paragraph / sentence / block span commands
(§10.1) is: **apply to every caret, in
parallel, against the original text
snapshot**. The focused caret's announcement
is spoken; the other carets move silently.
The same rule as transform operations.

#### 10.7.6 Selection-set speech and copy

**Speak selection set**
(`selection.speak_selection_set`):
**`QUILL key, Space`**. The QUILL key
prefix, then Space. Reads the count of
carets, then reads each caret in document
order: caret number, line, column, and the
selected text (or the word at the caret if
no selection). This is the only command
that enumerates all carets; it is the
"what is multi-cursor doing right now"
command. The QUILL key, Space chord is the
2.0 successor to the 1.0 "QUILL key, Space
spells the situation report" — the binding
expands to enumerate the SelectionSet when
one exists, otherwise it falls through to
the 1.0 situation report.

**Speak affected carets**
(`selection.speak_affected`):
**`QUILL key, .`** (period; "dot" — the
"what just changed?" key). Reads only the
carets that were affected by the last
multi-caret command. After a multi-caret
paste that replaced text in 3 places, this
command says "Caret 1: was 'Hello', now
'Goodbye'. Caret 2: was 'World', now
'There'. Caret 3: was empty, now 'End'."
This is the screen-reader equivalent of VS
Code's `editor.action.showHover` for
multi-cursor results.

**Copy selection set**
(`selection.copy_selection_set`): bound to
**`QUILL key, C`** (was `Ctrl+Shift+Grave,
C` for the email form; the basic copy
stays on `Ctrl+C`, and the QUILL key, C
chord is the multi-caret copy). Resolution:
if the clipboard target is "for email"
(`edit.copy_selection_for_email`,
`Ctrl+Shift+Grave, C`), behavior is
unchanged. Otherwise, copy concatenates the
selected text from every caret in document
order, joined by `\n` (the rule every
multi-cursor editor uses; VS Code, Sublime,
Emacs, IntelliJ all do this). Single-caret
behavior is identical to today. The
announcement is "Copied from N carets. 47
characters." (or "Copied 12 characters."
when N=1).

**Cut, delete, paste** follow the same
rule. Paste places the same text at every
caret (the standard multi-cursor paste
semantic). Indent, outdent, comment toggle,
case transforms, sort, reverse, dedupe,
shuffle, join, hard wrap, number lines —
all operate on the SelectionSet as a unit
with a single undo entry and a single
announcement.

#### 10.7.7 Rectangular (column / box) selection

Rectangular selection is the older feature
(present in Notepad++ via Alt+drag and
Shift+Alt+arrows, in Emacs via `rectangle-mark-mode`,
in Sublime via `editor.action.insertCursorAbove`).
For QUILL, the model is the same SelectionSet,
just sourced differently. There is no
"column" concept in the user-facing
vocabulary; the verb is **"select
rectangle"** and the result is a
SelectionSet of N ranges, one per line in
the rectangle.

**Start rectangle selection**
(`selection.start_rectangle`):
**`QUILL key, R`** (R for "Rectangle" —
the mnemonic is R = rectangle, not
Alt+Shift+backtick, which conflicts with
no binding on Windows but is invisible
on a screen reader and has no spoken
label). Sets the rectangle anchor at the
current caret position. Announces
"Rectangle started at line N, column M.
Move with arrow keys."

**Extend rectangle**
(arrow keys while rectangle mode is on):
**`Shift+Arrow`** keys extend the rectangle
in the obvious direction. The SelectionSet
grows by one range per visual line covered.
Each line gets its own range, clamped to the
rectangle's start and end columns. Lines
shorter than the rectangle's end column
contribute an empty range (a zero-width
caret at the line end). The screen reader
**does not enumerate** ranges as the user
arrows; it says "Rectangle: 5 lines, 4
columns." once and then stays silent until
the rectangle is committed, replaced, or
the user calls `selection.speak_selection_set`.

**Commit rectangle**:
**`Enter`** or **any non-arrow key** (typing,
Escape to cancel, or a command). Enter
collapses the SelectionSet to the current
set of N ranges; further arrows behave
normally. The user can then type, paste,
indent, or transform.

**Cancel rectangle**:
**`Escape`** (priority rule from §10.7.4:
rectangle > multi-caret > extend-selection
> find). The anchor is discarded; the
SelectionSet collapses to a single caret at
the original anchor position.

**Quick column caret** (the Alt+click
equivalent, screen-reader-first):
**`QUILL key, Shift+R`** (R again, with
Shift, to drop a column). The caret moves
as a column-only caret, leaving a trail
of secondary carets in the rectangle
shape, without ever entering "rectangle
mode" as a named state. Announces
"Column caret, 4 lines." Each subsequent
arrow moves the focused caret and
re-anchors the others. **`QUILL key,
0`** (zero) drops the column and returns
to a single caret.

The visual surface of rectangular selection
is intentionally minimal: the existing
selection highlight extends, plus a status
cell "Rectangle: 5 lines, 4 columns." There
is no overlay rectangle, no shaded band, no
"column ruler." The status cell is the only
new chrome, and it is the same cell the
single-caret status bar already shows.

#### 10.7.8 What this changes in the existing code

Files touched in 2.0 (the full list — every
file is `quill/` or `tests/`, no new top-level
modules):

- `quill/core/selection.py` — keep the
  single-range helpers; add `Selection` and
  `SelectionSet` as the new types.
- `quill/core/selection_set.py` (new) —
  `SelectionSet` with merge, sort, primary
  resolution, and `selection_set_scope`.
- `quill/core/feature_command_map.py` —
  add `feature.multi_caret_v2`; gate the
  new command set behind it for the 1.0 →
  2.0 transition.
- `quill/core/keymap.py` — add the 12 new
  bindings (six caret-add / remove / speak,
  four caret-step / speak, one column caret,
  one start-rectangle). All behind the feature
  flag. The 1.0 keymap is unchanged.
- `quill/ui/main_frame.py:945` — replace
  `self._extend_selection_anchor: int | None`
  with `self._selection_set: SelectionSet`.
  Keep `_extend_selection_anchor` as a
  derived property that returns
  `self._selection_set.anchor`. The 7 test
  sites in
  `tests/unit/ui/test_main_frame_navigation.py`
  (lines 1275, 1303, 1316, 1330, 1690, 1704,
  1715) keep passing because the property
  preserves the existing API.
- `quill/ui/main_frame.py:3530–3701` — the
  `_handle_extend_selection_key` /
  `_move_extend_selection_caret` / etc.
  path keeps working for the single-primary
  case. New `MultiCaretMixin` (in
  `quill/ui/multi_caret.py`, new) handles
  the N-caret paths.
- `quill/ui/main_frame_menu.py` — add the
  new menu items under **Edit → Carets** and
  **Edit → Rectangle** submenus (both
  behind the feature flag).
- `quill/ui/main_frame_selection.py` —
  `SelectionMarksMixin` keeps its current
  API; the new verbs live in
  `MultiCaretMixin`.
- `quill/ui/dialog_inventory.py` — the
  multi-caret cheatsheet dialog (if any) is
  classified `native` (a `wx.Dialog` showing
  a `wx.TextCtrl` of the new keymap, per the
  dialog rules).
- `tests/unit/ui/fixtures/main_frame_public_surface.json` —
  regenerated via
  `python -m quill.tools.ui_surface --write`
  to include the new methods.
- `dialogs.md` — the multi-caret cheatsheet
  row is added (one row, one binding).

#### 10.7.9 Test plan for 2.0

The test plan is a direct map of the design
obligations in §10.7.3:

- `tests/unit/core/test_selection_set.py` —
  merge, sort, primary resolution, anchor
  preservation, overlap rejection.
- `tests/unit/core/test_selection_set_scope.py` —
  scope reporting for the announcement
  surface (one caret, N carets, mixed
  scopes).
- `tests/unit/ui/test_multi_caret_add_remove.py` —
  add-below, add-above, add-all-occurrences,
  add-line-ends, remove-focused,
  clear-secondary, Escape priority.
- `tests/unit/ui/test_multi_caret_step.py` —
  next/previous caret, context-aware
  Alt+Down resolution (single vs multi).
- `tests/unit/ui/test_multi_caret_speech.py` —
  `speak_selection_set`,
  `speak_affected`, the "1 of 3" announcement
  shape, the "Copied from N carets"
  announcement shape, status-cell content.
- `tests/unit/ui/test_multi_caret_transform.py` —
  every transform (sort, reverse, dedupe,
  indent, outdent, comment toggle, case
  transforms, join, hard wrap, number lines,
  shuffle, keep-unique) operates on the
  SelectionSet as a unit with one undo entry
  and one announcement.
- `tests/unit/ui/test_multi_caret_paste.py` —
  paste places the same text at every caret;
  paste when clipboard is multi-line does
  not collapse to one caret; undo restores
  every caret's pre-paste text.
- `tests/unit/ui/test_rectangle_selection.py` —
  start, extend, commit, cancel, column-caret
  shortcut, short-line clamping, status-cell
  shape, the Escape priority rule with
  rectangle > multi-caret > extend-selection
  > find.
- `tests/unit/ui/test_escape_priority.py` —
  the unified Escape resolver from §10.7.4.
- `tests/unit/ui/test_multi_caret_announcements.py` —
  the three obligations of §10.7.3 in one
  matrix: silent-other-carets-during-motion,
  single-spoken-announcement-per-action,
  speak_selection_set on demand.
- `tests/unit/ui/test_dialog_inventory.py` —
  the multi-caret cheatsheet dialog is
  registered with classification `native`.

#### 10.7.10 What this does **not** ship in 2.0

- **No multi-cursor in the Document Navigator
  or the Entries panel.** Carets are an
  editor-internal concept; they do not
  appear in the structure surface, the
  filter surface, the sticky-notes surface,
  the Notebook tabs, or the status bar of
  the editor-host window.
- **No multi-cursor across Notebook
  Entries.** Carets are scoped to a single
  document. The "add caret to all
  occurrences" command operates inside the
  active document only. Cross-Entry
  multi-cursor is deferred to a future 2.x
  milestone.
- **No multi-cursor for sticky-note
  captures.** The sticky-note capture buffer
  (`Ctrl+Shift+Grave, N`) remains a
  single-position capture; multi-position
  sticky notes are a separate feature with
  its own dialog contract.
- **No multi-cursor for AI suggestions.**
  The AI ghost-suggestion flow (§8.6) accepts
  one position at a time. Multi-position AI
  is deferred.
- **No multi-cursor in find/replace
  results.** Find-all-matches (`Alt+F3`)
  stays a list of single-position results
  in the Find Results panel; it is not a
  multi-caret launcher.
- **No "primary caret" color, "ghost caret"
  rendering, or "inactive selection"
  highlight.** The screen-reader-first rule
  in §10.7.3 is enforced by the absence of
  these affordances, not just by their
  silence.
- **No clipboard history panel.** A
  multi-cursor + clipboard history combo is
  a 2.x or 3.0 design; this plan keeps the
  two features decoupled.

This subsection is the design the 2.0
milestone will implement. The 1.0 plan
above is **unchanged** by it; the only
1.0 consequence is the selection model
must keep the shim in §10.7.2 so the 2.0
work is a feature-flagged addition, not a
breaking change.

### 10.8 The QUILL-key chord policy (binding, 1.0 and 2.0)

This subsection is the binding decision that
makes §10.7 work. The user said: *"We have the
QuillKey. We should remap Ctrl+Alt hotkeys."*
That direction is binding for 1.0, not just
2.0. Every `Ctrl+Alt+` verb in the default
keymap and in the new multi-cursor / rectangle
set is moved to a **QUILL key, X** chord.

#### 10.8.1 Why the QUILL key absorbs Ctrl+Alt

`Ctrl+Alt+` is the worst-served chord in the
default keymap. Three reasons:

1. **Windows reserves the right-hand side of
   `Ctrl+Alt+`** for the shell and the IME
   switcher. On most Windows machines,
   `Ctrl+Alt+letter` is filtered by the OS
   before any application sees it. The current
   `edit.magic_paste = Ctrl+Alt+V` is unreliable
   on a real Windows desktop for exactly this
   reason; the same is true of the planned
   `Ctrl+Alt+Down` / `Ctrl+Alt+Up` /
   `Ctrl+Alt+L` / `Ctrl+Alt+K` /
   `Ctrl+Alt+Shift+` ` / `Ctrl+Alt+Shift+C`
   multi-cursor verbs.
2. **NVDA / JAWS / Narrator intercept
   `Ctrl+Alt+` first.** The screen readers
   own `Ctrl+Alt+` for their own mode
   switching. Even when Windows passes the
   chord through, the screen reader usually
   eats it. A QUILL user who is already
   running a screen reader will never see
   `Ctrl+Alt+` reach QUILL.
3. **The QUILL key is already a first-class
   chord in the product.** `quill_key_binding`
   (`quill/core/settings.py:36`) is a
   user-configurable single binding (default
   `Ctrl+Shift+Grave`); the prefix-and-browse
   state machine lives in
   `quill/ui/main_frame_quill_key.py:30` and
   already has a timeout, a sticky lock
   (double-press), an Escape path, a
   `MODE_PREFIX` cheat sheet, a `MODE_BROWSE`
   cheat sheet, and the `_quill_key_action_for_event`
   map at line 274 that already routes 14
   Quick-Nav letters (H, A, L, I, T, Q, B, ',
   C, P, S, [, ]) to navigation actions. The
   chord already accepts an arbitrary
   follow-on letter. Adding more letters
   under the same prefix is **one new entry
   in the action map, one new cheat-sheet
   line, one new test**. No new state
   machine. No new dialog contract.

The standing rule for 1.0 becomes: **no
new `Ctrl+Alt+` binding is added to
`quill/core/keymap.py`**. Any new verb that
would have used `Ctrl+Alt+` is added under
the QUILL key prefix instead. Existing
`Ctrl+Alt+` bindings are remapped in 1.0,
not preserved as legacy.

#### 10.8.2 The remap table (1.0)

The following existing and planned bindings
move to the QUILL key chord. Every entry
shows the OLD chord, the NEW chord, the
command, and the spoken announce (or
"silent" if the command is its own
announcement). All entries are added to
`quill/core/keymap.py` and to
`quill/core/quill_key_help.py` so the
prefix cheat sheet lists them.

| Command                              | Old chord                  | New chord (QUILL key, …) | Announce after chord                  |
| ------------------------------------ | -------------------------- | ------------------------ | ------------------------------------- |
| `edit.magic_paste`                   | `Ctrl+Alt+V`               | **V**                    | "Magic Paste"                         |
| `format.list_manager`                | `Ctrl+Shift+Grave, L`      | **L**                    | "List Manager"                        |
| `format.heading_1` … `format.heading_6` | `Ctrl+Shift+Grave, 1` … `, 6` | **1** … **6**        | "Heading N"                           |
| `format.insert_html_tag`             | `Ctrl+Shift+Grave, H`      | **H**                    | "Insert HTML tag"                     |
| `format.insert_markdown_tag`         | `Ctrl+Shift+Grave, M`      | **M**                    | "Insert Markdown tag"                 |
| `format.insert_snippet`              | `Ctrl+Shift+Grave, S`      | **Shift+S**              | "Insert snippet"                      |
| `format.manage_snippets`             | `Ctrl+Shift+Grave, Shift+S`| **Shift+M**              | "Manage snippets"                     |
| `view.browser_preview`               | `Ctrl+Shift+Grave, V`      | **B**                    | "Browser preview"                     |
| `view.switch_editing_lens`           | `Ctrl+Shift+Grave, K`      | **K** (in browse mode)   | "Editing lens"                        |
| `tools.read_aloud_start_pause`       | `Ctrl+Shift+Grave, R`      | **R**                    | "Read aloud start/pause"              |
| `tools.read_aloud_stop`              | `Ctrl+Shift+Grave, Shift+R`| **Shift+R**              | "Read aloud stop"                     |
| `tools.dictation_toggle`             | `Ctrl+Shift+Grave, D`      | **D**                    | "Dictation on/off"                    |
| `tools.describe_image`               | `Ctrl+Shift+Grave, I`      | **I**                    | "Describe image"                      |
| `tools.sticky_note_capture`          | `Ctrl+Shift+Grave, N`      | **N**                    | "Sticky note capture"                 |
| `edit.copy_selection_for_email`      | `Ctrl+Shift+Grave, C`      | **Shift+C**              | "Copy selection for email"            |
| `navigate.heading_organizer`         | `Ctrl+Shift+Grave, O`      | **O**                    | "Heading organizer"                   |
| `view.announce_contrast`             | `Ctrl+Shift+Grave, Shift+C`| **Shift+H** (contrast)   | "High contrast: on/off"                |
| `navigate.go_to_anything`            | `Ctrl+Shift+Grave, G`      | **G**                    | "Go to anything"                      |
| `window.next_document`               | `Ctrl+Shift+Grave, Tab`    | (unchanged: `Ctrl+Tab`)  | silent (existing keymap)              |
| `window.previous_document`           | `Ctrl+Shift+Grave, Shift+Tab` | (unchanged: `Ctrl+Shift+Tab`) | silent                          |
| `view.send_to_tray`                  | `Ctrl+Shift+Grave, T`      | (unchanged: `Ctrl+Alt+T`)| silent — Windows-shell action, keep  |
| `view.toggle_tab_control`            | `Ctrl+Shift+Grave, Shift+T`| (unchanged: `Ctrl+Alt+Shift+T`)| silent — Windows-shell action   |

**The five `Ctrl+Alt+` shell-bound verbs in
the existing `keymap.py:430–450` keyboard
pack** (`CTRL+ALT+T`, `CTRL+ALT+SHIFT+T`,
`CTRL+ALT+P`, `CTRL+ALT+S`, `CTRL+ALT+V`,
`CTRL+ALT+C`, `CTRL+ALT+SHIFT+N`,
`CTRL+ALT+SHIFT+V`, `CTRL+ALT+L`,
`CTRL+ALT+1` … `CTRL+ALT+6`,
`CTRL+ALT+H`, `CTRL+ALT+M`,
`CTRL+ALT+SPACE`, `CTRL+ALT+SHIFT+SPACE`)
are the legacy compatibility aliases for
the same commands. They are kept for users
on the legacy "Quill Writer / Quill
Navigation / Quill Review" packs
(`keymap.py:127`), and are **deleted** from
the default pack. A 1.0 `keymap.py` lint
asserts: "no `Ctrl+Alt+` binding is
reachable from `KEYBOARD_PACK_DEFAULT`."

#### 10.8.3 The remap table (2.0, multi-cursor)

The §10.7 multi-cursor and rectangle bindings
that were originally `Ctrl+Alt+` are also
moved to the QUILL key chord:

| Command (2.0)                         | Old chord (draft)   | New chord (QUILL key, …) |
| ------------------------------------- | ------------------- | ------------------------ |
| `selection.add_caret_below`           | `Ctrl+Alt+Down`     | **J** (Just below)       |
| `selection.add_caret_above`           | `Ctrl+Alt+Up`       | **K** (Karet above)      |
| `selection.add_caret_to_all_occurrences` | `Ctrl+Shift+L`   | **A**                    |
| `selection.add_caret_to_line_ends`    | `Ctrl+Alt+L`        | **E** (End of line)      |
| `selection.remove_focused_caret`      | `Ctrl+Alt+K`        | **X**                    |
| `selection.clear_secondary_carets`    | `Escape` (kept)     | (kept; no change)        |
| `selection.next_caret`                | `Alt+Down` (clash)  | **N** (in prefix)        |
| `selection.previous_caret`            | `Alt+Up` (clash)    | **Shift+N** (in prefix)  |
| `selection.announce_caret_position`   | `Alt+Shift+P`       | **/** (where am I?)      |
| `selection.speak_selection_set`       | `Alt+Shift+Space`   | **Space** (in prefix)    |
| `selection.speak_affected`            | `Alt+Shift+'`       | **.** (period)           |
| `selection.copy_selection_set`        | `Ctrl+Shift+C` (clash) | **C** (in prefix)     |
| `selection.start_rectangle`           | `Alt+Shift+backtick`| **R** (Rectangle)        |
| `selection.quick_column_caret`        | `Alt+Shift+C` (clash)| **Shift+R** (in prefix)  |
| `selection.drop_column_caret`         | `Alt+Shift+0`       | **0** (in prefix)        |

This makes the multi-cursor feature
**invisible to a non-screen-reader
audience** at the keymap layer: there is
no `Ctrl+Alt+` or `Alt+Shift+` column in
the default pack. The only way to reach
the multi-cursor verbs is through the
QUILL key chord, which is itself
discoverable in Help > QUILL Key Primer
and in the prefix cheat sheet
(`MODE_PREFIX` cheat sheet, line 18 of
`quill/core/quill_key_help.py`).

#### 10.8.4 Mnemonic map (the public-facing table)

The cheat sheet and the Help > QUILL Key
Primer surface this consolidated map. The
keymap mentor (QK-9, line 47 of
`main_frame_quill_key.py`) teaches it on
the first press of the QUILL key. The
table the user actually hears:

```
QUILL key, then…
  A    Add caret to all occurrences of the current word / selection
  B    Browser preview
  C    Copy (multi-caret copy of the selection set)
  D    Dictation on / off
  E    Add caret to end of every line in the selection
  G    Go to anything
  H    Insert HTML tag
  I    Describe image
  J    Add caret Just below
  K    Karet above (add caret above)
  L    List Manager
  M    Insert Markdown tag
  N    Next caret (in prefix)  /  Sticky note capture (no selection)
  O    Heading Organizer
  R    Read aloud start/pause  /  Rectangle start (in prefix)
  S    Save snapshot  /  Insert snippet (with Shift)
  T    Tray (send to system tray)
  V    Magic Paste
  X    Remove focused caret
  /    Caret N of M  (where am I in the selection set?)
  0    Drop column caret  /  Re-center the editor
  1..6 Heading 1 .. Heading 6
  Shift+H  Contrast on/off announce
  Shift+M  Manage snippets
  Shift+N  Previous caret
  Shift+R  Read aloud stop  /  Quick column caret
  Shift+S  Insert snippet
  Shift+C  Copy selection for email
  Space   Speak selection set  /  Situation report (no multi-caret)
  .       Speak affected carets (after a multi-caret action)
```

Mnemonics that are already in the
existing Quick-Nav map (H = heading, A =
link, L = list, I = list_item, T = table,
Q = block_quote, B = bookmark, ' =
code_block, C = table_of_contents, P =
paragraph, S = sentence, TAB = block, ] =
skip_forward, [ = skip_backward) keep
their **narrow meaning when pressed
without the QUILL key prefix** (the
existing Quick-Nav feature), and gain a
**wider meaning when pressed after the
QUILL key prefix**. The two are the same
keystroke; the prefix is what tells the
state machine which meaning applies. The
status bar at all times shows which
state is active:

- No prefix pending: "Quick Nav ready"
- Prefix pending: "QUILL key: H=heading, A=link, …"
- Browse mode: "QUILL key browse: H=heading, A=add caret, …"

The 1.0 review checklist now has a ninth
question (§10.6, Q9) that confirms this
remap is in place.

---

## 11. The Magical Layer — proposals for 1.5 and 2.0

Every idea in this section passes the QUILL bar: it
must be operable entirely by keyboard, it must have
a spoken outcome, and it must not break any existing
dialog contract. These are not incremental features.
Each one changes what it *feels like* to use QUILL.
Priority order within each tier is by implementation
cost and likelihood of delight.

### 11.1 Delta narration — speak where you arrived, not the grid

**What.** Replace coordinate-only position announcements
("line 42, column 5") with a context sentence: "Moved
down 3 lines to: 'She looked up slowly.'" The
announcement leads with the fragment of text at the new
caret position (up to 8 words, trimmed at word boundary)
and appends the line number as a secondary hint. The
fragment is sourced from `editor.GetRange(pos, pos + 60)`
narrowed to the next word boundary.

**Why it is magical.** The screen-reader user hears the
document, not a spreadsheet. "Moved to 'The reversal
was unexpected'" is instantly meaningful. "Line 42,
column 1" is not. Every navigation command — Page Down,
next heading, jump to bookmark — becomes a sentence
about the writing instead of a grid coordinate. This
is the single highest-leverage change to QUILL's
announcement layer.

**Where it lives.** An opt-in toggle in Preferences >
Announcements: "Position speech: fragment (default),
coordinates, both." A per-profile setting so a developer
using QUILL for code can stay on coordinates.

**Implementation.** One new function
`announcement_fragment(text, pos, width=60) -> str`
in `quill/core/marks.py`. Replace the coordinate
format string in `_announce_selection_scope` and
`_announce_caret_position`. No other changes.

---

### 11.2 Structural earcons — navigate by sound, not speech

**What.** A set of short, distinct audio icons (non-TTS)
played at structural boundaries:

- Crossing from one heading section to another: a low
  two-note chime.
- Landing on a misspelling: a short, quiet tick.
- Landing on a GLOW annotation: a slightly longer tick
  in a different pitch.
- Entering a heading: a brief rising tone scaled to the
  heading level (H1 is lowest; H6 is highest).
- Opening an AI suggestion: a soft ascending arpeggio.

**Why it is magical.** Earcons complement TTS without
competing with it. A user scanning fast with arrow keys
does not want a full sentence announcement per line; they
want a spatial audio cue that says "something here."
Earcons are to QUILL what visual underlines and colors
are to sighted users: a pre-attentive signal that
narrows attention before the speech channel activates.

**Where it lives.** Tools > Accessibility > Sound Cues
(toggle, plus a "Sound Cue Levels..." dialog). Each cue
type is individually toggle-able. Volume is a percentage
of the system default. All cues respect system mute.
A "Preview" button in the dialog plays all cues in
sequence.

**Implementation.** `quill/platform/windows/earcon.py`
(new, ~80 LOC): wrap `winsound.PlaySound` with a
non-blocking queue. Each earcon is a short WAV bundled
in `quill/resources/earcons/`. The trigger sites are
the same hooks that fire `_announce_caret_position`
and `_announce_selection_scope`.

---

### 11.3 "Ask QUILL" — natural language document query

**What.** QUILL key + Q opens a single-line prompt.
The user types a question about the current document
or Notebook and hears a spoken one-sentence answer:

- "How many words in the introduction?" → "Introduction:
  847 words, reading time 4 minutes."
- "Where did I last write about memory?" → "Last mention
  of 'memory': line 312, section 3.2 'The aftermath'."
- "What headings are in chapter three?" → "Chapter Three
  has 4 sub-headings: 'The setup', 'The reversal'…"
- "What is my goal progress?" → "Goal: 278 of 500
  words today. 44% complete."

The answer is computed from the document index, the
Notebook JSON, and the existing Quick Nav primitives.
The AI layer handles questions the index cannot answer
(and only then, under the existing consent gate).

**Why it is magical.** No other screen-reader-first
editor lets the user ask a question about their document
in plain English and hear the answer in one second. This
is not a chat; there is no back-and-forth. It is a
query oracle with a one-shot answer. The distinction
matters: a chat UI imposes a conversation metaphor; a
query oracle respects the user's time.

**Where it lives.** A new command `tools.ask_quill`
(QUILL+Q) that opens a `wx.TextEntryDialog`
(classified `native`) with a single text field. The
response dialog is a `wx.MessageDialog` that also
copies the answer to the clipboard. Query history is
per-Notebook and accessible via Search > Saved Queries.

---

### 11.4 Notebook vocabulary — the project dictionary

**What.** Every Notebook carries a vocabulary list:
words the user has added as project-specific (character
names, place names, technical terms, invented words).
The spell checker and GLOW respect this list. Three
commands:

- "Add to Notebook Dictionary" (in the spell-check
  context actions and the right-click context menu):
  promotes a word from session scope to Notebook scope.
- "Notebook Vocabulary..." (Tools > Writing & Language):
  opens a `wx.Dialog` with the full project word list,
  add/remove, and import from a text file.
- "Dictionary Status" (already exists) shows the
  count of project words alongside the system and
  session word counts.

**Why it is magical.** A novelist who writes "Astryn"
as a character name should never see it flagged as a
misspelling after the first time they add it. A
technical writer should add acronyms once and forget.
Scrivener has "project replace" for phrases; QUILL has
a cleaner, spell-check-integrated vocabulary that
persists with the Notebook JSON. The first time a user
adds a word to their Notebook dictionary and hears
"Added 'Astryn' to My Novel vocabulary" they
understand immediately that QUILL is managing context,
not just words.

**Implementation.** A `vocabulary: []` list in the
Notebook JSON schema (`quill/core/schemas/notebook.json`).
The `enchant` pipeline in `quill/core/spell_check.py`
gains a `project_words` parameter. The context menu
wiring is the same as "Add to Document Dictionary."

---

### 11.5 Read Aloud proofreading mode — active, not passive

**What.** A new mode activated by "Read Aloud >
Proofread Document" (or Ctrl+Shift+R). In this mode:

1. Read Aloud narrates one sentence at a time at the
   normal voice rate, then pauses.
2. After the pause, QUILL announces the available
   actions: "Space: continue. R: replace. M: mark.
   N: add note. Escape: exit."
3. The user acts or continues.
4. After the full document is read, QUILL announces:
   "Proofread complete. 3 marks, 1 replacement, 47%
   of document reviewed."

A status-bar cell "Proofread: 47%" updates in real
time. Reviewed sentences are tracked in the Notebook
session (not persisted). The "R: replace" path opens
an inline one-line replacement prompt (a
`wx.TextEntryDialog`, classified `native`) pre-filled
with the current sentence.

**Why it is magical.** Read Aloud today is a passive
listener experience. The proofreading mode makes it
an active editing workflow. A blind user hears their
own words read back and can fix them without switching
context, searching for the caret position, or opening
a find/replace dialog. This is how professional
audiobook narrators proof their scripts, adapted for
QUILL's stock-control architecture.

**Implementation.** A new `ProofreadSession` class in
`quill/core/read_aloud.py` that owns the sentence
iterator, the mark list, and the action dispatcher.
The action keys are handled in a modal loop in
`quill/ui/main_frame_read_aloud.py` (new mixin, ~120
LOC). No new dialogs beyond the replacement prompt.

---

### 11.6 AI welcome-back summary on Notebook open

**What.** When AI is enabled and a Notebook has not
been open for more than 4 hours, opening it triggers
a one-sentence spoken summary:

"Last session: Chapter 3, 847 new words. Today's
goal: 500 words. You stopped at: 'She looked up
slowly.'"

The summary is generated from the Notebook JSON (no
network call: last-session word delta, Goal state,
last caret fragment from §11.1). If the AI provider
is available and the user has opted in, a second
sentence adds AI context: "The last section you
worked on discusses grief and memory."

**Why it is magical.** Every morning a novelist opens
QUILL and hears exactly where they left off. No
scrolling, no searching, no "where was I?" The welcome-
back summary is two seconds of audio that re-creates
the context a sighted user gets by scanning the
screen. It is the difference between QUILL being a
tool and QUILL being a working partner.

**Where it lives.** Preferences > AI > "Welcome-back
summary" toggle (default: off). Per-Notebook override
in the Notebook settings dialog.

---

### 11.7 Silent Mode — defer all speech to the OS screen reader

**What.** A status-bar toggle (or QUILL+F12) that
suppresses all QUILL-originated TTS announcements and
custom spoken output. In Silent Mode, QUILL focuses
entirely on providing correct ARIA roles, names,
states, and `wx.Accessible` event notifications so
NVDA, JAWS, or Narrator can narrate everything
natively.

Silent Mode does *not* disable keyboard access,
dialog contracts, or status cells. It only quiets
QUILL's own voice. A user who prefers their screen
reader's voice, grammar, and verbosity level over
QUILL's custom announcements gets a fully accessible
experience without both systems competing for the
audio channel.

**Why it is magical.** Most accessible software
forces users to choose between the app's narration
and the screen reader. QUILL's existing
`platform/windows/prism_bridge.py` already abstracts
the TTS channel; Silent Mode just sets the bridge to
a no-op stub. The screen reader then takes over with
zero integration work. This is the design complement
of the announcement grammar system: QUILL either
speaks beautifully in its own voice, or it steps
aside and lets the screen reader speak in its voice.

**Implementation.** A `silent: bool` flag on
`PrismBridge`. When set, all `announce(...)` calls
in the bridge return immediately without speaking.
`wx.Accessible` events continue to fire. The
status-bar cell changes label to "Silent" when on.
~10 LOC.

---

### 11.8 The QUILL key situation report

**What.** When the user presses the QUILL key and
holds it (or presses QUILL key + Space), QUILL speaks
a situation report:

"Chapter Three: The reversal. 312 words. Goal: 278
of 500 today. 1 nearby misspelling."

The report contains: the current heading and section,
the section word count, the Goal progress (if a Goal
is active), and the nearest annotation within 200
characters (misspelling, GLOW note, or sticky note).
One announcement, everything the user needs to know
about where they are.

**Why it is magical.** A sighted user glances at the
status bar and the outline panel and knows their
context in a fraction of a second. A screen-reader
user currently has to query each piece of information
separately. The situation report collapses that into
a single, predictable spoken phrase. It becomes
muscle memory: "I'm disoriented, QUILL+Space." The
answer is always the same shape, always complete,
always under 3 seconds.

**Where it lives.** A new command
`view.speak_situation_report` (QUILL+Space, or a
configurable QUILL key chord). One line in the QUILL
key dispatch table. Implementation draws on
`line_column_for_position` (marks.py), the Quick Nav
index (navigate.py), and the Goal state (notebook
JSON). ~30 LOC in `main_frame_view.py`.

---

### 11.9 Announcement grammar templates

**What.** The spoken output of every QUILL navigation
and action command is currently hard-coded in the
announcement layer. Exposing the format strings as
user-customizable templates would let power users
define how QUILL speaks to them:

- Default: "Heading 2: Methods — 847 words"
- Custom: "H2 Methods, 847"
- Developer: "§2 Methods [847]"

Template tokens for each announcement type (position,
heading, selection, annotation, goal) are documented
in Help > Announcement Grammar Reference. Templates
are stored in the Notebook JSON under `"announcement_overrides"`.
Edited in a new "Announcement Grammar" dialog in
Tools > Customize & Support.

**Why it is magical.** A legal writer, a novelist,
a programmer, and a student all want QUILL to speak
differently. The template system lets QUILL adapt to
each without requiring a feature flag per niche. It
is the meta-feature that makes every other
announcement customizable by the user, not by the
developer.

---

### 11.10 "Speak what you passed" on fast navigation

**What.** When the user presses Page Down or
Ctrl+Down multiple times in quick succession (within
600ms between keypresses), QUILL accumulates the
moves and, when the user pauses, speaks a summary
instead of enumerating every intermediate position:

"Moved down 8 paragraphs. Passed: 2 headings, 1
sticky note, 3 misspellings. Now at: 'The
investigation concluded.'"

This is the document equivalent of a GPS "in 400
metres, turn right" — a summary of what was passed,
not a coordinate per metre traveled. Single-key
navigation continues to announce as it does today.

**Why it is magical.** Fast navigation currently
floods the screen reader with intermediate
announcements that the user ignores anyway. The
summary mode turns rapid Page Down into a meaningful
report: the user knows what they flew over and where
they landed. The "passed N headings" count is
especially useful for knowing whether it is worth
scrolling back.

**Implementation.** A key-repeat accumulator in
`main_frame.py` that tracks the structural index
delta between the navigation-start position and
the pause position. Uses the same Quick Nav
primitives that drive the 13-element type counts.
The pause threshold (600ms default) is configurable
in Preferences > Navigation.


---

<!-- Source: docs/planning/editors2.md -->

# Editors.md — Competitive Analysis and Design Synthesis for QUILL

> Author: this document. Date: 2026-06-01. Scope: a working competitive
> analysis of QUILL against leading general-purpose, programmer, and
> prose editors; a feature matrix; an honest gap analysis with industry
> expectations; a recommended menu consolidation; a Ulysses/Obsidian/Scrivener-
> inspired redesign of Workspaces and the Document Navigator that is
> unmistakably QUILL in spirit; and a long list of "make it amazing"
> proposals. Every recommendation is written for a screen-reader-first
> Windows desktop app whose north star is the QUILL key, Quick Nav, and
> the dialog contract.

---

## 1. Executive summary

QUILL is already a strikingly opinionated editor: stock controls in the
writing path, a screen-reader-first design, the QUILL key chord, Quick
Nav across 13 element types, a deep command palette, Workspace
Snapshots, headings organizer, compare documents, macros, an AI menu
gated by consent, GLOW accessibility, BITS Whisperer dictation, a rich
Quillins extension model, and a stability/safety surface that
mainstream editors rarely equal. Compared to the editor market it sits
somewhere between a programmer's text tool and a pro writing tool —
and that hybrid is exactly its edge.

The competitive analysis shows three things:

1. QUILL's *interactive navigation* and *accessibility-grade confirmations*
   are industry-leading. No mainstream editor matches its 13-element
   Quick Nav, its structured selection primitives, or its dialog
   contract enforcement.
2. QUILL's *document and project organization* (the Workspace concept,
   Document Navigator, multi-document sessions) is functional but
   under-developed compared with Ulysses's library, Obsidian's vault
   and graph, Scrivener's corkboard, and Org-mode's hierarchy and
   agenda.
3. QUILL's *menu* has grown organically and now approaches the depth
   of a kitchen sink. The good news is the architecture supports a
   much cleaner organization. The bad news is that the current Tools
   menu reaches three levels in places and a few entries are mis-homed.

The rest of this document lays out the matrix, the gap list, the
proposed menu consolidation, the Workspaces + Document Navigator
redesign, and a long creative list of "make it amazing" ideas tailored
to QUILL's voice.

---

## 2. Feature matrix

Legend: ✅ first-class, ◑ partial, ○ not present, — N/A. The
"industry expectation" column is the user-facing behavior a sighted,
keyboard-only, or screen-reader user would expect to find without
explanation. The "QUILL today" column is observed from the codebase
and user guide as of 2026-06-01.

| Capability                                          | Industry expectation                                                                                          | QUILL today                              | Status |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ------ |
| Undo / redo with persistence                        | Multi-level undo; survives crash                                                                              | Multi-level undo; persistent undo toggle | ✅     |
| Find / replace (text)                               | Modal find bar; next/prev; replace; selection scope                                                            | In-document Find bar, replace, next/prev | ✅     |
| Regex find / replace                                | Toggle for regex; group preview                                                                               | Regex supported; named-group preview planned | ◑ |
| Find in files                                       | Cross-file search with results list                                                                           | Search menu (search_in_files, replace_in_files) | ✅ |
| Bookmarks (named, persistent)                       | Set / go to / list; per-document                                                                              | `navigate.set_bookmark`, `go_to_bookmark`, `list_bookmarks` | ✅ |
| Temporary marks / "point and mark"                  | Push/pop ring; exchange point/mark; list marks                                                                | `edit.set_mark`, `pop_mark`, `exchange_point_mark`, `list_marks` | ✅ |
| Line / paragraph / block selection                  | Three distinct selection units; announce which                                                                 | `select_line`, `select_paragraph`, `select_block` | ✅ |
| Structural navigation                               | Next/prev heading, block, structure; match bracket; region                                                    | `navigate.next_heading`, `next_block`, `next_structure`, `match_bracket`, `next_region` | ✅ |
| Outline / structure panel                           | Dockable tree with preview and jump; per-markup-kind                                                           | `open_outline_navigator`, `_show_tree_navigator` (modal); also a YAML navigator | ◑ |
| Quick Nav (jump to anything)                        | Single keystroke to a categorised index with type-ahead                                                        | `open_quick_nav` (NAV-1/NAV-4) with 13 element types | ✅ |
| Command palette                                     | Fuzzy find over all commands with scope and recent                                                             | `_id_palette`, palette.py                 | ✅     |
| Project / "workspace" concept                       | Named, restorable collection of open documents, settings, and UI state                                          | "Workspace Snapshots" submenu in File (`_sessions_menu`) and `_refresh_sessions_menu`; `core/sessions.py` | ◑ |
| Library / sheet / vault                             | Persistent on-disk collection of many items with grouping, filters, and search                                 | OO position partially filled by Workspace Snapshots | ○ |
| Multi-cursor / multi-selection                      | Multiple carets, column selection, box select                                                                 | Not in core; `extend_selection_mode` toggle | ○ |
| Snippets / text expansion                           | Trigger, tab stops, placeholders, scope                                                                        | `core/snippets.py` (11 KB), `format.insert_snippet`, `format.manage_snippets` | ✅ |
| Snippet variables (date, filename, cursor)          | Tokens at expansion time                                                                                      | Supported (see Snippet format)           | ✅     |
| Command-based snippet system                        | JScript / Lua / Python actions inside snippets                                                                | Python sandbox in core; no in-snippet scripting in user guide | ◑ |
| Spell check                                         | As-you-type; dialog; dictionary management                                                                    | Three-tier spell-check; status / dialog; dictionary status | ✅ |
| Thesaurus                                           | Synonym lookup, inline replace                                                                                | `tools.thesaurus` (background pre-load planned) | ◑ |
| Grammar / style lint                                | Rules engine, inline annotations                                                                              | GLOW audit + fix, selection-level       | ✅     |
| Word count / reading time                           | Document, selection, periodic                                                                                 | `tools.word_count`                       | ✅     |
| Auto-save / recovery                                | Periodic save; recovery on crash with preview                                                                  | `core/autosave.py`; recovery snapshot dialog with 30-line preview | ✅ |
| Backups                                                                     | Local copies of prior versions                                                                                | `core/backups.py`; restore from backup   | ✅     |
| Compare documents                                                              | Side-by-side or unified diff; navigate; announce                                                              | `compare_menu` (Compare Documents) with announce, summary, copy, sync toggle | ✅ |
| Macros                                                                       | Record / play / save; named                                                                                   | `core/macros`; macro menu with start/stop/play/manage | ✅ |
| TTS / read aloud                                                             | Start/pause/stop; voice pick; speed; export audio                                                              | `core/read_aloud.py` (~46 KB), full menu | ✅ |
| Dictation                                                                    | Toggle; voice commands; offline model                                                                          | BITS Whisperer (deferred to 2.0 as a top-level menu; 1.0 ships dictation under Watch/Dictation submenu) | ◑ |
| OCR                                                                          | Image, clipboard, screen; image description                                                                     | `tools.ocr_image`, `tools.ocr_clipboard`, `tools.ocr_screen`, `tools.describe_image` | ✅ |
| OCR result post-processing (cleanup recipes)                                 | One-key cleanup of OCR output                                                                                  | "Clean exports" profile mentioned in roadmap; not surfaced in menu | ◑ |
| On-device / private AI                                                       | Opt-in; explicit consent; no silent network                                                                     | AI menu gated; `core.bw_whisperer` provider model; consent flow | ✅ |
| Cloud AI (ChatGPT, Claude, local endpoints)                                 | Model picker; API key; forget key                                                                              | `AI Model and Connection...`; `Forget API Key`; status badge | ✅ |
| AI rewrite / summarize / continue / fix grammar                              | In-editor actions                                                                                              | `ai_rewrite_selection`, `ai_summarize_selection`, `ai_continue_writing`, `ai_fix_grammar` | ✅ |
| AI prompt studio / agent center                                              | Custom prompts; agent tools                                                                                    | `ai_prompt_studio`, `ai_agent_center`, `ai_hub` | ✅ |
| Conversational AI side panel                                                 | Chat docked to the side, share selection                                                                       | `ask_quill_chat`, `ai_assistant` (windowed) | ◑ |
| Image description / alt-text helper                                          | Generate alt-text for embedded images                                                                          | `tools.describe_image`; accessibility tune-up agent | ✅ |
| Accessibility audit                                                          | Periodic; spoken report                                                                                        | `tools.accessibility_audit`              | ✅     |
| Keyboard trap / tab-order snapshot                                           | Diagnose focus traps                                                                                            | `tools.keyboard_trap_snapshot`           | ✅     |
| Contrast validation                                                          | Check palette against WCAG                                                                                     | `tools.validate_contrast`                | ✅     |
| Sticky notes                                                                  | Quick capture; searchable vault                                                                                | Sticky Notes submenu (sticky_notes, new sticky note) | ✅ |
| Watch folder                                                                  | One folder, one action                                                                                          | Watch Folder Profiles (`watch_folder_settings`, `watch_folder_status`, `watch_folder_toggle`) — single profile set | ◑ |
| Pandoc integration                                                            | Convert between formats                                                                                         | `tools.pandoc_wizard`                    | ✅     |
| External tools / format support                                              | Allowlist of executables                                                                                        | `tools.external_tools`                   | ✅     |
| SSH / remote file open                                                        | Quick connect; site manager                                                                                    | `Open over SSH` submenu (Quick Connect, Site Manager) | ✅ |
| File format readers/writers                                                   | Markdown, HTML, RTF, EPUB, DOCX, PDF, JSON, CSV, YAML, plain text                                             | `quill/io/structured.py` and per-format modules | ✅ |
| EPUB reader / navigator                                                       | Open and jump inside EPUB                                                                                       | `open_epub_navigator`                    | ✅     |
| YAML structure editor                                                         | Visual tree edit for YAML documents                                                                            | `open_yaml_structure_editor`             | ✅     |
| Heading organizer                                                             | Validate and reshape heading sequence                                                                          | `open_heading_organizer`                 | ✅     |
| Customizable menus / keymap                                                   | Editor for menu and keymap                                                                                     | `app.menu_editor`, `keymap_editor`; `core/menu_customization.py` (12 KB) | ✅ |
| Profiles (Essential, Writer, Developer, A11y Pro, Full)                      | Switch whole profile; health check                                                                              | Feature profiles + `switch_feature_profile`; `feature_profile_health_check` | ✅ |
| Feature flag manager                                                          | Per-feature toggle                                                                                              | `individual_feature_toggles`             | ✅     |
| Custom profiles / Quick Profiles                                              | User-saved bundles of settings                                                                                  | `core/custom_profiles.py`                | ✅     |
| Status bar layout customization                                               | Pick cells, persist                                                                                            | `status_bar_settings`                    | ✅     |
| Plug-in / extension model                                                     | Manifest, sandbox, signing                                                                                     | Quillins manifest validated; `quillins_bundled/` examples | ◑ |
| Export and back up / import                                                   | One-key share                                                                                                   | `share_export`, `share_import`           | ✅     |
| Export presets (EPUB, PDF, DOCX, HTML)                                        | Pick target and options                                                                                         | Pandoc wizard; export presets partial    | ◑ |
| Print                                                                          | Page setup, print preview                                                                                      | `file.page_setup`, `file.print`          | ✅     |
| Auto-format / smart punctuation                                              | Smart quotes, dashes, ellipses                                                                                  | Core autoformat; smart quotes not surfaced as toggle | ◑ |
| Word prediction                                                                | Inline completion                                                                                              | `edit.word_prediction`                   | ✅     |
| Intellisense as you type                                                       | Lightweight, scoped to language                                                                                | `core/intellisense.py`                   | ◑ |
| Markdown / HTML / rich-text preview                                           | Side by side or focused                                                                                        | `view.preview`, `view.split_preview`, `view.focus_preview`, `view.browser_preview` | ✅ |
| Distraction / focus mode                                                      | Hide chrome, center text, silence chatter                                                                       | "Focus Preview" is the closest; no full-screen "Focal" mode | ◑ |
| Reading ruler / line focus                                                    | Highlight current line/paragraph                                                                                | Not surfaced; high-contrast settings only | ◑ |
| Inline definitions / word lookup                                              | Single key for dictionary + thesaurus                                                                            | Thesaurus dialog; no inline look-up      | ◑ |
| Document health dashboard                                                    | One pane for accessibility + lint + link inventory                                                              | Accessibility audit; link inventory; contrast; not unified | ◑ |
| External file change watch                                                    | Detect edits; reload safely                                                                                    | `core/external_change.py`                | ✅     |
| Code folding                                                                  | Collapse / expand                                                                                              | Not surfaced                              | ○     |
| Multi-pane editor (split, grid)                                              | Horizontal/vertical split, save layout                                                                          | "Preview Side by Side" exists; no true multi-pane text editor split | ◑ |
| Tab / tile open documents                                                     | One tab per document                                                                                            | `show_tab_control` toggle in View        | ✅     |
| Status bar: line, col, selection length                                      | Always present                                                                                                  | Status bar with cells (status_bar_settings to choose) | ✅ |
| Recent files / recent folders                                                 | MRU list                                                                                                        | `Open Recent` submenu                    | ✅     |
| Recent sessions / restore last session                                        | Auto-restore on launch                                                                                          | "Workspace Snapshots" submenu in File; auto-restore on launch | ✅ |
| Auto-update                                                                    | Notify; one-key update                                                                                          | `check_updates`; auto-check toggle in Settings | ✅ |
| Crash reporting                                                                | Opt-in bundle                                                                                                  | `save_diagnostics`; `report_bug`        | ✅     |
| Localization                                                                   | Multi-language UI                                                                                              | Translation contributor plan in place    | ◑     |
| High-contrast / dark mode                                                     | System-aware                                                                                                    | `toggle_dark_mode`; `validate_contrast`; high-contrast respected | ✅ |
| Math / equation editor                                                        | LaTeX-style inline and block                                                                                    | Not surfaced                              | ○     |
| Bibliographies / citations                                                    | Reference list management                                                                                       | Not surfaced                              | ○     |
| Co-located todos / checkboxes                                                 | Task list with states                                                                                          | Task list insertion (`insert_task_list`); List Manager | ✅ |
| Bidirectional links / backlinks                                               | Wiki-style [[link]] with back-link pane                                                                          | Follow link exists; no backlink pane    | ○     |
| Graph / canvas view                                                            | Visual map of document relationships                                                                            | Not in QUILL                              | ○     |
| Corkboard / index-card view                                                   | One card per document or section                                                                                | Not in QUILL                              | ○     |
| Outline view (dock)                                                            | Persistent tree side panel                                                                                      | Outline Navigator is a modal; no docked tree | ◑ |
| Document statistics / progress goals                                          | Word target, time, deadline                                                                                      | `word_count` shows numbers; no goal/target surface | ◑ |
| Daily / word-count goal                                                       | "500 words today"                                                                                                | Not surfaced                              | ○     |
| Notes within notes (block / sub-document)                                     | Transclusion, block reference                                                                                  | `navigate.next_structure` covers Markdown structures; not block-level | ◑ |
| Tags / keywords                                                                | First-class tag system                                                                                          | List Manager supports tags via markup; no first-class tag system | ◑ |
| Saved searches / smart folders                                                | Dynamic filters                                                                                                  | Not in QUILL                              | ○     |
| Full-text search with snippets                                                | Highlight matches with context                                                                                  | `search_in_files` exists; in-document Find Next/Prev is built-in | ✅ |
| Word / line wrap / soft wrap toggle                                           | Always present                                                                                                  | `view.toggle_soft_wrap`                  | ✅     |
| Indent settings (tabs vs spaces, width)                                       | Per-document                                                                                                   | `format.indent`, `format.outdent`; `convert_indentation_to_*` | ✅ |
| Auto-close brackets / quotes                                                  | Optional                                                                                                       | Not surfaced                              | ○     |
| Bracket matching highlight                                                    | On cursor move                                                                                                  | `navigate.match_bracket`                 | ✅     |
| Column / ruler / margin guides                                                | Visual aids                                                                                                    | Not surfaced                              | ○     |
| Drag-and-drop reordering of lines / blocks                                    | Mouse only or keyboard?                                                                                         | Move Line Up/Down; no block drag         | ◑     |
| Sort / unique / shuffle lines                                                 | Built-in                                                                                                        | Sort, Reverse, Remove Duplicates, Trim, Normalize, Indent conversions all in `Format > Transform Lines` | ✅ |
| Column / rectangular selection                                               | Multi-line, multi-character                                                                                     | Not in core                              | ○     |
| Line numbers (gutter)                                                         | Optional                                                                                                        | Not surfaced                              | ○     |
| Whitespace / EOL visualization                                                | Optional                                                                                                        | Not surfaced                              | ○     |
| Project templates                                                              | New from template                                                                                              | Power Tools file-create group likely contains templates; verify | ◑ |
| Project search and replace                                                    | Cross-file regex                                                                                                | `tools.replace_in_files`                 | ✅     |

The takeaway: QUILL is in the top tier for navigation, accessibility,
AI integration (gated), writing-quality tooling, and document safety.
Its *project organization* layer (workspaces, library, multi-document
graph, smart folders, goals) is functional but under-developed
relative to dedicated writing apps.

---

## 3. Where QUILL aligns with industry

These are the strengths that match or exceed editor expectations, and
the rough proof points inside the codebase.

1. **Stock controls in the writing path.** Per
   `accessible-dialogs.instructions.md`, every input is `wx.TextCtrl` or
   `wx.ListBox`. No custom-drawn editor surface, which means
   screen readers see the same role and name everywhere.
2. **Three-tier spell check** with enchant, wordlist, and stub. Background
   pre-load is on the roadmap (PERF-1) and the menu surfaces every
   level: Spell Check dialog, Previous/Next Misspelling, Misspelling
   List, Dictionary Status, Add to Document Dictionary, Ignore for
   Session.
3. **Structured selection primitives.** Select Line / Paragraph / Block
   are separate commands, not a single ambiguous "extend selection"
   that other editors make the user discover.
4. **Mark ring.** Set / Pop / Exchange / List. Few mainstream editors
   ship a visible mark ring as a first-class menu.
5. **Quick Nav across 13 element types** with a category filter and
   type-ahead. This is VS Code's Command Palette behavior applied to
   document structure, with a count badge.
6. **Heading organizer** validates and rewrites heading sequences for
   accessibility and clean exports. No mainstream editor has this.
7. **Compare Documents** with synchronized navigation, announcement of
   the current difference, a "Difference Summary," and copy
   individual/all differences. Compare in Word is a hidden ribbon
   dialog; in Notepad++ it is a plugin; in VS Code it is an extension
   unless you have Pro. QUILL ships it as a first-class tool.
8. **Workspace Snapshots** that name and restore document sets, caret
   positions, and active document. The naming and saving model is
   Ulysses-like.
9. **Two-stage AI consent.** No silent network; provider, model, scope,
   and confidence are announced.
10. **BITS Whisperer** (deferred to 2.0 as a top-level menu but present
    in 1.0 as a submenu) is genuinely novel for a screen-reader-first
    editor: offline speech-to-text with model management and a queue
    you can monitor without sight.
11. **Watch Folder Profiles** is the rare automation hub that is
    operable with a screen reader; the "many folders, many actions,
    one queue" redesign on the roadmap is a real differentiator.
12. **GLOW (Grammar, Logic, Organization, Writing)** is QUILL's
    accessibility-and-prose-fix engine; the four sub-commands (audit
    document, audit selection, fix document, fix selection) make it
    simple by design.
13. **Quillins extension model** is sandboxed, manifest-validated, and
    ships with a Lint tool (`quill.tools.quillin_lint`). Compared with
    Vimscript or VS Code's open extension marketplace, it is a
    deliberately tight perimeter.

The user-visible principle behind all of this: *every action has a
spoken outcome, every dialog has a default and an escape, every
feature can be turned off*. That is the bar the rest of the editor
market does not consistently meet.

---

## 4. Where QUILL is behind or behaves unexpectedly

These are the gaps the matrix surfaces, with the "industry expects"
framing, the QUILL reality, and an honest callout when current
behavior diverges from what a user would assume.

### 4.1 Project organization is shallow

- **Industry expectation.** Ulysses users live in a "library" with
  groups, filters, and goals. Obsidian users live in a "vault" with
  backlinks, tags, and Bases. Scrivener users live in a "binder" with
  corkboard and outliner. Org-mode users live in a tree with agenda.
- **QUILL today.** Workspace Snapshots save and restore the current
  open-document set. There is no persistent library, no grouping, no
  filters, no per-workspace palette of recent activity. The
  "Recent Files" menu exists but Workspace Snapshots is a sibling
  concept, not a superset.
- **Honest callout.** "Open from Workspace Snapshot" can look like a
  glorified "Reopen Closed Tab" to a new user. The snapshot is
  loadable, but the snapshot UI is not yet a library.

### 4.2 Outline Navigator is a modal, not a dock

- **Industry expectation.** Word, Scrivener, and most writing apps
  ship a persistent outline pane that you can show, hide, and let
  track the cursor. Ulysses shows the editor + sheet list always.
  Obsidian shows the file tree.
- **QUILL today.** `_show_tree_navigator` builds a `wx.Dialog` with a
  splitter (tree + preview), is launched by `open_outline_navigator`
  (and `open_epub_navigator`, `open_yaml_structure_editor`), and is
  destroyed on close. The same pattern is reused for Misspelling
  Navigator, Document Intake, and others.
- **Honest callout.** The dialog is excellent and screen-reader
  friendly, but a power user editing a 200-page manuscript will
  repeatedly open and close the modal. A docked outline tree (toggle
  from View) would match industry behavior without breaking the
  dialog contract.

### 4.3 Multi-cursor / column select is absent

- **Industry expectation.** VS Code, Sublime, JetBrains IDEs, vim,
  Emacs all support multiple carets. Notepad++ supports column /
  block selection. Word supports column select with Alt.
- **QUILL today.** Only an "extend selection mode" toggle exists,
  which extends the next selection motion. No multi-caret, no box
  select.
- **Honest callout.** This is the single largest missing editing
  primitive for users who came from a programmer editor. Add a
  power-tool that toggles column-select on Alt+drag and a
  keyboard command to add a caret above / below.

### 4.4 Word-prediction and intellisense are present but not visible

- **Industry expectation.** Word shows suggestions inline. VS Code
  shows completions on demand and as you type. Notepad++ has an
  autocomplete plugin that does the same.
- **QUILL today.** `edit.word_prediction` opens a dialog. There is no
  as-you-type inline completion surfaced in the menu or the status
  bar. `core/intellisense.py` exists; nothing in the menu says so.
- **Honest callout.** Users will assume the feature is broken. The
  fix is to make it a visible, opt-in "Inline word prediction" toggle
  in the status bar / settings, with announcement on accept.

### 4.5 AI chat is windowed, not docked

- **Industry expectation.** Cursor, VS Code + Copilot, JetBrains AI,
  Notion AI, and Ulysses's "Ask Ulysses" all dock a chat side panel
  that shares selection with the editor.
- **QUILL today.** "Ask Quill Chat..." and "Writing Assistant..."
  open floating windows. The selection is shared only through copy
  and paste.
- **Honest callout.** The chat is functional; it just is not docked,
  and a docked chat panel that owns a left or right dock with the
  outline tree on the other side would be a much more useful default.

### 4.6 Grammar fix is not in the document until asked

- **Industry expectation.** Grammarly underlines; one key accepts.
  GLOW already audits and fixes, but the audit step is explicit.
- **QUILL today.** `glow_audit_document` and `glow_audit_selection`
  must run before `glow_fix_document` and `glow_fix_selection`. The
  fix only changes the document after the user sees the report.
- **Honest callout.** This is a defensible design (transparency), but
  the menu should make it obvious: the "GLOW" submenu already does.
  Keep the contract; add a "GLOW Quick Fix on Selection" that audits
  + fixes + announces the change count in one key.

### 4.7 No "Focus Mode" / "Focal" surface

- **Industry expectation.** Word has Focus Mode. Bear has a
  chrome-less compose. Ulysses has a minimal editor. iA Writer has
  Focus Mode with a sentence highlight. Notepad++ has a "Distraction
  Free" plugin.
- **QUILL today.** The closest is "Focus Preview." That hides the
  editor chrome for the preview, not the editor itself.
- **Honest callout.** "Focus Preview" is misleadingly named. A real
  "Focal Mode" (F11?) that hides status bar, menu bar, sidebar, and
  centers the current paragraph with optional reading ruler and
  sentence highlighting is the correct fit for a screen-reader
  product; it should silence non-essential chatter, keep essential
  confirmations, and be a one-key toggle.

### 4.8 Snippet tab stops / placeholders are not announced

- **Industry expectation.** VS Code, Sublime, JetBrains, vim, and
  TextMate all support tab stops with placeholders; the user is
  walked through each stop with `Tab` and `Shift+Tab`.
- **QUILL today.** Snippets exist and the menu offers Insert and
  Manage; there is no documented "tab stop" walk-through. The snippet
  format may support placeholders (it does in EdSharp and most modern
  editors).
- **Honest callout.** Verify in `core/snippets.py` and document.
  If placeholders are not yet announced, add a `Snippets` tutorial
  to the user guide and make the placeholder name spoken on arrival.

### 4.9 Goto line / page has no "line" speech preview

- **Industry expectation.** A "Go to line" usually shows the line
  content in a preview before the user commits.
- **QUILL today.** `navigate.go_to_line` jumps; no preview.
- **Honest callout.** Add a one-line preview pane in the Go-To-Line
  dialog with the current line's text, the line number, the column,
  and a "Speak Line" button. Trivial to add, big screen-reader win.

### 4.10 No saved searches / no smart folders

- **Industry expectation.** Most pro editors and writing apps
  support saved filters: "All headings containing TODO," "All
  documents opened this week," "All files with more than N
  misspellings."
- **QUILL today.** None. `file_search` exists but is a one-shot
  search.
- **Honest callout.** Add a "Saved Searches" manager and tie it to
  Workspace Snapshots. Saved searches are an under-rated
  accessibility win because they let a screen-reader user ask
  "what's new?" in a single keystroke.

### 4.11 No word-count goal / writing target

- **Industry expectation.** Ulysses has writing goals (words,
  characters, time). Scrivener has project targets. Word has
  word-count target notifications. Bear has a daily streak.
- **QUILL today.** Word count exists; no goal / target surface.
- **Honest callout.** Add a "Writing Goal" dialog and a status-bar
  cell that announces progress. Tying the goal to a Workspace
  Snapshot makes this very Ulysses-like.

### 4.12 Status bar cells are customizable but the UX is hidden

- **Industry expectation.** VS Code and Word expose a clear "Status
  Bar Layout..." picker.
- **QUILL today.** `status_bar_settings` exists. The menu labels it
  clearly. The dialog must be polished.
- **Honest callout.** Verify the dialog (a screen-reader test pass)
  and add an "Add a cell" / "Remove a cell" / "Reorder" flow that
  is fully keyboard-driven.

### 4.13 No reading ruler / line focus for low-vision users

- **Industry expectation.** Word, Pages, macOS, NVDA, and many
  editors support a reading ruler that follows the caret.
- **QUILL today.** Not surfaced.
- **Honest callout.** Add a "Reading Ruler" toggle and a "Line
  Focus" toggle under View, behind a feature flag, with high-contrast
  aware theming.

### 4.14 Smart quotes / auto-format not surfaced

- **Industry expectation.** Word, Pages, Ulysses, Bear all convert
  straight quotes to typographic quotes as you type.
- **QUILL today.** `core/autoformat.py` exists; not on by default,
  not visible in the menu.
- **Honest callout.** Surface as a setting ("Auto-format as you
  type") with sub-toggles for quotes, dashes, ellipses. Announce the
  substitution so a screen-reader user knows the character changed.

### 4.15 No image embed flow (other than OCR)

- **Industry expectation.** Markdown editors let you paste / drop an
  image. Ulysses, Bear, iA Writer all do.
- **QUILL today.** OCR Image and Describe Image are present. Image
  insertion is not. Markdown reference links work.
- **Honest callout.** Add "Insert Image from File..." and "Insert
  Image from Clipboard" under Insert. The accessibility win is that
  the dialog should immediately offer a "Describe Image..." button
  that uses Describe Image, so the alt text and the embed happen
  together.

### 4.16 Inline spelling suggestions are not visible in the menu

- **Industry expectation.** Word, Pages, macOS show a context menu
  with "Replace with..." suggestions.
- **QUILL today.** Misspelling List exists; no inline context menu
  for replacements.
- **Honest callout.** Add a context menu for misspelled words
  offering the top three suggestions + "Add to Dictionary" + "Ignore
  for Session." Already possible with the wx context menu; surface
  the wired action in the menu so it is discoverable.

### 4.17 No "duplicate selection" as a structural copy

- **Industry expectation.** Several editors have "Duplicate Line"
  and "Duplicate Selection."
- **QUILL today.** `format.duplicate_line` exists. No
  `duplicate_selection` (block-level copy).
- **Honest callout.** Add `edit.duplicate_selection` to the Edit
  menu; it's two lines of code and a big productivity win.

### 4.18 The Tools menu is deep

- **Industry expectation.** Most successful editors keep top-level
  menus flat with one level of submenu. VS Code's File menu has 9
  items, Edit has 12, View has 22, all flat.
- **QUILL today.** The Tools menu has 14 direct submenus and the
  Read Aloud, BITS Whisperer, and AI submenus each go a level
  deeper. The Custom Profiles under Help also add a third level.
- **Honest callout.** This is a documentation and discoverability
  problem, not a code problem. See §6 for the proposed
  consolidation.

### 4.19 Watch Folder Profiles are documented in the roadmap but
  "single profile" is what the menu exposes today

- **Industry expectation.** Folder Watching tools (Hazel on Mac,
  File Juggler on Windows) all support many rules.
- **QUILL today.** `Watch Folder Profiles...` exists in the menu;
  the roadmap is clear that "many folders, many actions, one
  monitorable queue" is the future.
- **Honest callout.** Land the Watch Profiles feature; it's the
  biggest accessibility-driven productivity story QUILL has.

### 4.20 BITS Whisperer (offline speech-to-text) is deferred

- **Industry expectation.** Dragon, Apple Dictation, Windows Voice
  Typing all exist.
- **QUILL today.** Dictation is a submenu, BITS Whisperer is feature-
  flagged behind `core.bw_whisperer` (off by default in 1.0), and
  per the standing rules, items needing a real Windows runtime must
  stay honestly "In progress."
- **Honest callout.** This is correctly called out in the standing
  rules; keep it in progress and don't pretend it's done.

---

## 5. Industry callouts that QUILL handles correctly

Some behaviors that are easy to get wrong and that QUILL has right —
these are worth saying out loud so they don't regress.

1. **Find and Replace are inside Edit; cross-file search is in
   Search.** This matches the conventional split and matches VS Code
   / Word.
2. **Selection submenu** keeps line / paragraph / block distinct and
   adds "Recent Marks (Ring)" as a nested submenu. This is the Emacs
   influence done well, and it is keyboard-friendly.
3. **The Status Bar settings** live in Tools > Customize, not in
   View. This is a Microsoft convention; it survives menu shuffles.
4. **Insert / Format / Navigate are separate menus.** This matches
   Word and avoids the Notepad++ "everything is in one Format menu"
   trap.
5. **BITS Whisperer is a submenu of Tools when enabled**, and
   demoted from a top-level menu so the main bar stays at ten
   entries.
6. **Pandoc Wizard lives in Tools > Authoring and Automation** —
   not in a buried settings dialog. Power users can find it.
7. **External Tools** lives next to Pandoc and has an executable
   allowlist enforced by the codebase. This is the correct security
   posture.
8. **Compare Documents** is a real submenu (not a sub-submenu) with
   "Next Difference" / "Previous Difference" / "Announce Current" /
   "Difference List" / "Synchronized Navigation" / "Summary" / "Copy
   Current" / "Copy All." That is unusually complete.
9. **Custom Profiles and Feature Profiles** are under Help, not
   buried. Users can find them.
10. **Accessibility Audit, Keyboard Trap Snapshot, Contrast, Link
    Inventory** are all in Tools > Accessibility, not scattered. This
    is a deliberate discoverability choice.

---

## 6. Menu consolidation proposal

The current menu is 10 top-level entries, with Tools being 14-deep
and three submenus reaching a third level. The proposal is to keep
ten top-level menus (the Windows norm) and keep two as the
maximum depth inside any submenu.

### 6.1 Top-level layout (unchanged)

> File, Edit, View, Insert, Format, Navigate, Search, Tools, Window,
> Help. The conventional Windows order. Status bar settings lives in
> Tools > Customize.

### 6.2 Tools submenu: the proposed reorganization

Group the 14 current Tools submenus into 7 logical clusters. The
ordering is by frequency of use: writing essentials first, then
automation, then meta / configuration.

| Cluster                  | Items (submenu)                                                                              | Why                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Writing & Language       | Word Count, Spell Check, Previous/Next Misspelling, Misspelling List, Thesaurus, Dictionary Status | Unchanged from current "Writing and Language" submenu.                  |
| Reading & Dictation      | Read Aloud (with Voice / Settings / Generate Audio), Announcement Backend, Dictation, Watch Folder, OCR & Image | Merge Read Aloud + Dictation + Watch Folder + OCR/Image into one "Reading & Dictation" submenu. |
| Automation               | Macros, GLOW, Compare Documents, AI Assistant, BITS Whisperer                                 | Rename the current "Authoring & Automation" cluster; pull AI into it (it already lives under Tools). |
| Workspace                | Workspace Snapshots (relocated here from File), Sticky Notes, Sessions, Recent Files (relocated) | A new cluster that owns document organization. See §7.                 |
| Power Tools              | (All current Power Tools items)                                                              | Unchanged.                                                                 |
| Quillins                 | (All current Quillin items)                                                                  | Unchanged.                                                                 |
| Customization & Support  | Customize (Preferences, Menus, Profiles & Features, Status Bar, Export, Import, Keymap), Accessibility (Audit, Trap, Contrast, Link Inventory), Support (Notifications, Report Bug, Save Diagnostics, Logs, Updates) | A single "Settings & Support" cluster.                                  |

The Tools menu in two-deep form looks like:

```
Tools
├── Command Palette
├── ──────────
├── Writing & Language
│     ├── Word Count
│     ├── Spell Check
│     ├── Previous Misspelling
│     ├── Next Misspelling
│     ├── Misspelling List
│     ├── Thesaurus
│     └── Dictionary Status
├── Reading & Dictation
│     ├── Read Aloud  ▸
│     │     ├── Start / Pause
│     │     ├── Stop
│     │     ├── Voice
│     │     ├── Settings
│     │     └── Generate Audio
│     ├── Announcement Backend
│     ├── Dictation
│     ├── Watch Folder ▸
│     │     ├── Monitoring (in Settings)
│     │     ├── Profiles
│     │     └── Queue
│     ├── OCR Image
│     ├── OCR Clipboard
│     ├── OCR Screen
│     └── Describe Image
├── Automation
│     ├── Macros
│     ├── GLOW
│     ├── Compare Documents
│     ├── Document Intake
│     ├── Pandoc Wizard
│     ├── Regex Helper
│     ├── External Tools
│     └── YAML Structure Editor
├── AI Assistant
│     ├── Use AI
│     ├── AI Status
│     ├── AI Detail
│     ├── AI Hub
│     ├── Ask Quill Chat
│     ├── AI Model and Connection
│     ├── Forget API Key
│     ├── Session Branches
│     ├── Writing Assistant
│     ├── Prompt Studio
│     ├── Agent Center
│     ├── Accessibility Tune-Up
│     ├── Rewrite Selection
│     ├── Summarize Selection
│     ├── Continue Writing
│     ├── Fix Grammar
│     ├── Train Writing Style
│     └── Writing Instructions
├── BITS Whisperer (if enabled)
├── Workspace
│     ├── Workspace Snapshots ▸
│     │     ├── Save Current Snapshot
│     │     ├── Save As...
│     │     ├── Recent Snapshots ▸
│     │     └── Manage Snapshots...
│     ├── New Workspace from Folder...
│     ├── Sticky Notes
│     └── New Sticky Note
├── Power Tools
├── Quillins
├── Accessibility
│     ├── Accessibility Audit
│     ├── Keyboard Trap & Tab-Order Snapshot
│     ├── Validate Contrast
│     ├── Link Inventory & Alt-Text Catalog
│     ├── Inline Word Prediction (toggle)
│     ├── Auto-Format as You Type (toggle)
│     └── Smart Quotes (toggle)
└── Customize & Support
      ├── Preferences
      ├── Customize Menus
      ├── Profiles and Features
      ├── Status Bar Layout
      ├── Export and Back Up
      ├── Import or Restore
      ├── Keymap Editor
      ├── Export Keymap
      ├── Import Keymap
      ├── Reset Keymap
      ├── Notifications
      ├── Report a Bug
      ├── Save Diagnostics
      ├── Open Logs Folder
      ├── Open Diagnostics Folder
      └── Check for Updates
```

Two notable relocations:

- **Workspace Snapshots moves from File > Workspace Snapshots to
  Tools > Workspace**. The File menu is for "open / save this
  document" actions. Workspace is a "session of documents" concept
  and belongs with the cluster that will own the new Library
  surface (§7). A "Recent Snapshots" submenu replaces "Recent
  Sessions" inside the cluster.
- **Read Aloud** keeps its current submenu shape but is now nested
  inside Reading & Dictation. This keeps the two deep clusters
  (Read Aloud and Watch Folder) capped at the second level, which
  matches the standing "no third level" rule from the menu
  consolidation notes.

### 6.3 File menu

Suggested File menu reorganization (kept flat):

```
File
├── New
├── New from Template ▸  (existing Power Tools file-create items)
├── Open...
├── Open Recent ▸
├── Open from URL...
├── Open over SSH ▸
├── Workspace ▸  (new top-level submenu; see §6.4)
├── ──────────
├── Save
├── Save As...
├── Save All
├── Save As Plain Text...
├── ──────────
├── Reload from Disk
├── Restore Backup...
├── ──────────
├── Page Setup...
├── Print...
├── ──────────
├── Close Document
└── Exit
```

The Workspace submenu here is a *gateway* that links to the new
Workspace surfaces (Library, Snapshots, New from Folder) and to the
Tools > Workspace cluster where the management dialogs live. This
gives keyboard and screen-reader users two paths into the same
content.

### 6.4 View menu

```
View
├── Toggle Soft Wrap
├── Auto Side-by-Side Preview
├── Show Tab Control
├── Wrap Find Searches
├── Start With No Document Open
├── ──────────
├── Preview
├── Preview Side by Side
├── Focus Preview
├── Browser Preview
├── ──────────
├── Outline (toggle docked outline panel; new)
├── Library (toggle docked library panel; new)
├── Sticky Notes (toggle docked sticky notes panel; new)
├── AI Chat (toggle docked AI panel; new)
├── ──────────
├── Focus Mode (new; see §9.7)
└── Reading Ruler (new; see §9.8)
```

The four new toggles (Outline / Library / Sticky Notes / AI Chat)
dock the corresponding dialog content as a persistent side panel
(see §7). "Focus Mode" is a one-key "F11" full-screen writing
surface that hides every chrome. "Reading Ruler" is a high-contrast
line-focus toggle for low-vision users.

### 6.5 Navigate menu

Already strong. Suggested additions (all behind the existing
feature-flag system):

- **Go To Bookmark in Workspace** — jump across documents in the
  current Workspace.
- **Go To Snippet** — fuzzy jump to a snippet.
- **Go To Misspelling** — already in the menu under Tools > Writing &
  Language; add a hotkey.
- **Go To Link** — already in Insert and Edit; ensure a key.
- **Go To Heading in Workspace** — cross-document heading jump
  when the active Workspace exposes headings.

### 6.6 Insert menu

Add: **Insert Image from File...**, **Insert Image from Clipboard**,
**Insert Math Block (LaTeX)**, **Insert Citation...** (when a
citation style is configured), **Insert Divider (Horizontal Rule)**,
**Insert Special Character...** (already likely in Power Tools;
promote to a first-class Insert entry).

### 6.7 Format menu

Add: **Auto-Format as You Type** toggle (under
Customize & Support currently; promote to Format or to View), and
**Smart Quotes / Smart Dashes / Smart Ellipses** toggles.

### 6.8 Help menu

Already has a sensible structure. Suggested additions:

- **QUILL Key Primer** (a screen-reader-friendly in-app quick
  reference, gated by the Help system).
- **Keyboard Reference (Printable)** — produces an accessible HTML /
  EPUB cheat sheet filtered by the active profile.
- **Workspace Tour** — first-run walkthrough of the new Library
  surface.

### 6.9 Search menu

Add: **Saved Searches**, **Search Results Window** (toggle docked
results), **Filter by Document** (when a Workspace is loaded).

---

## 7. Workspaces and Document Navigator: the redesign

This is the heart of the ask: take the existing Workspace Snapshots
concept and the existing `open_outline_navigator` modal and turn them
into a Ulysses/Obsidian/Scrivener-inspired but unmistakably QUILL
organization layer. The north star is *calm, keyboard-first, screen-
reader-narrated project organization*, with no new visual chrome a
sighted user would not also value.

### 7.1 Terminology

- **Workspace.** A named, restorable collection of documents,
  bookmarks, snippets, sticky notes, AI conversations, settings
  overrides, and shell hooks. The unit of "this is the project I am
  working on right now."
- **Sheet.** A single document inside a Workspace. Sheets are the
  atomic unit of focus. (The Ulysses name for a single document is
  "sheet" — borrowed on purpose because it is the right metaphor.)
- **Group.** A named, ordered folder of sheets within a Workspace.
  Groups nest. Groups are stored in the Workspace, not on the
  filesystem; the on-disk layout is the user's choice. (Ulysses
  uses "groups"; Scrivener uses "folders" inside the binder.)
- **Section.** A heading range inside a sheet. Sections are the
  unit of focus within a sheet. Already surfaced by
  `_outline_navigator`; now first-class inside the Library.
- **Library.** The on-screen, persistent side panel that shows the
  current Workspace's structure (Groups, Sheets, Sections) and
  drives the editor. (Ulysses name; matches the metaphor.)
- **Sticky Note.** A per-Workspace or global note pinned to a sheet
  or section. (Already exists; promote to a first-class Library
  surface.)
- **Snip.** A saved snippet bound to a Workspace. (New; extends the
  snippet system with a per-Workspace scope.)
- **Goal.** A writing target bound to a Workspace (daily / session /
  deadline). (Ulysses feature; new to QUILL.)
- **Filter.** A saved search / smart folder inside a Workspace.
  Filters are evaluated against the Workspace's sheets and persist
  with it.
- **Snapshot.** A saved point-in-time state of a Workspace.
  (Already exists; renamed for clarity.)
- **Session.** A loaded Workspace with the live documents open in
  the editor.

### 7.2 The Library panel

A docked `wx.Panel` on the left of the editor, toggleable from View
("Library"). The Library is the screen-reader page region with a
list of groups, sheets, and sections. It is *not* a tree (a flat
list with a heading level is more accessible); it shows the
Workspace's structure as a list with a single "level" disclosure
indicator.

Components (all stock wx):

- **Header** — Workspace name, last-saved time, word / character
  count, optional progress goal.
- **Filter** — a `wx.TextCtrl` at the top with a type-ahead filter.
  Matches sheet titles, sheet text, section titles, sticky note
  text, and tags. Announces the match count as it changes.
- **Tree-list** — a `wx.ListBox` populated from the current
  Workspace's structure. Each entry has a label ("Chapter 3 >
  Beat sheet > 4. The reversal"), a kind (Group / Sheet / Section
  / Sticky Note / Filter result), and an optional state badge
  ("draft," "reviewed," "misspellings: 4," "modified").
- **Action bar** — buttons (or keyboard shortcuts): New Sheet, New
  Group, Rename, Delete, Move Up / Down, Promote / Demote, Open
  Sticky Note, Set Goal, Snapshot Now.
- **Context menu** — wired to the same actions. Stock wx context
  menu; no custom-drawn tree.

Behavior:

- **Live focus follows caret.** When the cursor moves to a section,
  the Library's selection moves with it (if the user has not
  manually scrolled the Library). Announce the change.
- **Drag-reorder via keyboard.** Power Tools recirculation. "Move
  Sheet Up" / "Move Sheet Down" / "Move Sheet to Group..." all in
  the Edit and Library menus.
- **Open in new editor tab / new window.** Long-form editing
  benefits from multiple open sheets. The Window menu gets "Next
  Sheet" / "Previous Sheet" if the user opts in to "open sheets in
  a tabbed editor."
- **Read-only by default; explicit write.** New Workspaces are
  empty until the user creates a sheet. Opening an existing
  Workspace Snapshot loads the document set, the caret positions,
  the AI sessions, and the sticky notes.
- **Save behavior.** A Workspace saves automatically on sheet save,
  on snapshot, and on a debounced interval (similar to settings
  persistence). Manual "Save Snapshot" is a menu item.

### 7.3 Outline panel (a docked tree)

Use the existing `_show_tree_navigator` logic but render it as a
panel, not a modal. The current modal is excellent for the
"right-now jump to" use case; the docked panel is for "let me see
the structure as I work." Behind the scenes both share a common
"outline index" primitive in `core/outline.py`.

- The docked panel reads from the active sheet only.
- The modal still works for cross-document jumps inside a
  Workspace.
- Both speak the same names: headings, sections, blocks.

### 7.4 Workspace creation and persistence

A Workspace is a JSON file under `%APPDATA%\Quill\workspaces\`
(validated against `quill/core/schemas/workspace.json`). The
schema is intentionally tight:

```jsonc
{
  "schema_version": 1,
  "id": "ws_<uuid>",
  "name": "My Novel",
  "description": "Working title for the third book.",
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "groups": [
    {
      "id": "g_chapters",
      "name": "Chapters",
      "sheets": ["s_intro", "s_chapter1", "s_chapter2"],
      "groups": []
    }
  ],
  "sheets": {
    "s_intro": {
      "id": "s_intro",
      "title": "Introduction",
      "path": "C:\\...\\intro.md",
      "format": "markdown",
      "sticky_notes": ["n_open_question"],
      "snippets": ["sn_opening_quote"],
      "tags": ["draft"],
      "last_caret": 1234
    }
  },
  "sticky_notes": {
    "n_open_question": {
      "id": "n_open_question",
      "title": "Open question",
      "body": "Is the protagonist a reliable narrator?",
      "pinned_to": "s_intro"
    }
  },
  "snippets": {
    "sn_opening_quote": {
      "id": "sn_opening_quote",
      "title": "Opening quote",
      "body": "> ..."
    }
  },
  "tags": ["draft", "reviewed"],
  "filters": [
    {
      "id": "f_open_loose_ends",
      "name": "Open loose ends",
      "query": "TODO OR FIXME"
    }
  ],
  "goal": {
    "kind": "words_per_day",
    "target": 500,
    "period": "day"
  },
  "snapshots": [
    {
      "id": "snap_<uuid>",
      "name": "First draft complete",
      "saved_at": "2026-06-01T12:00:00Z"
    }
  ]
}
```

The schema is intentionally simple: groups nest, sheets live in
groups, sticky notes and snippets are flat collections with
optional pinning. Tags are a free-form string list. Filters and
goals are optional.

### 7.5 File-system mapping

A Workspace is a *logical* layer on top of the user's filesystem;
it does not require a particular directory layout. The user
chooses where each sheet lives; the Workspace stores the path. The
"New from Folder..." command:

1. Walks the chosen folder.
2. Filters by extension (configurable: `.md`, `.txt`, `.epub`, etc.).
3. Suggests a Group / Sheet structure based on the folder tree.
4. Asks once: "Use this layout? Yes / Preview / Edit." The Preview
   shows the proposed tree before any save.
5. Writes the Workspace file.

A "New from EPUB..." command opens an EPUB and creates a Workspace
where the chapters are sheets and the headings are sections.
Matches `open_epub_navigator` semantics.

### 7.6 Workspace Snapshots reborn

- Rename "Workspace Snapshots" to **Snapshots** (the term in the
  Ulysses vocabulary).
- A Snapshot stores the *complete state* of a Workspace at a point
  in time: sheets, caret positions, sticky notes, snippets, AI
  sessions, and the document bytes. This is what the current
  Workspace Snapshots already does; it just needs the rename and
  the menu relocation.
- A Snapshot is immutable. Restoring a Snapshot reopens the
  Workspace from the saved state. Diffing Snapshots is exposed
  through Compare Documents (current menu, current engine).
- Snapshots are exportable as a single `.qws.json` file (the
  Workspace file) and importable, with a conflict-resolution
  dialog for name collisions.

### 7.7 Filters and Smart Folders

A Filter is a saved search. Evaluation rules:

- Match sheets by title, body, sticky-note text, snippet text, or
  tags.
- Boolean expressions: `tag:draft AND title:ch*`.
- Regex support is opt-in.
- Result is a virtual group; opening a result jumps to the match
  in the source sheet.

Filters surface in the Library as a "Filters" sub-list. Selecting
a filter narrows the Library list to its matches; selecting
"Clear Filter" returns to the full list.

### 7.8 Goals and Progress

A Goal is a daily, session, or deadline target. The simplest form:

- Words per day (or characters or sentences).
- Words per session.
- Word count deadline ("reach 50,000 words by 2026-09-30").

The status bar gets a "Progress" cell that announces the
percentage and the remaining words. The Library header shows the
same. A "Streak" cell tracks consecutive days. A spoken
notification at end of session ("Goal reached: 500 words today")
is opt-in and respects the shared announcement grammar.

### 7.9 Cross-document navigation

A Workspace exposes new Navigate menu items:

- **Go To Heading in Workspace** — fuzzy jump across sheets in
  the current Workspace.
- **Go To Bookmark in Workspace** — same.
- **Go To Sticky Note in Workspace** — same.
- **Go To Tag** — opens the Library with the tag filter applied.
- **Go To Filter Result** — opens the active filter's matches.

All of these compose with the existing `quick_nav` index and
benefit from the same prewarm cache.

### 7.10 What this looks like as a flow

A first-run writer opens QUILL and is offered: "Start a new
Workspace, open a recent Workspace, or open a file." Selecting
"Start a new Workspace" shows a dialog: "Name, optional
description, optional folder to import from." A new Library
panel slides in (or the docked tree appears) and the user starts
writing.

After 20 minutes the Library is full of groups, sheets, sticky
notes, and one filter ("TODO"). The status bar shows "Words:
1,234 of 500 today — goal reached." A single keystroke (Ctrl+K,
or QUILL+K) opens the command palette; typing "snapshot" offers
"Snapshot Workspace" and "Manage Snapshots."

A blind user goes through the same flow with the screen reader
narrating "Group: Chapters. Sheet: Introduction. Section: The
premise. Heading level 1. Word count 312." The panel is a
single list region, not a tree, and the focus is always
predictable.

### 7.11 Why this matches the Ulysses / Obsidian / Scrivener bar

- **Ulysses** — library, sheets, groups, filters, goals. QUILL
  borrows the *vocabulary* and the *single-list region* but
  replaces the Mac-only metaphors (sheet sidebar, keyboarder
  two-pane split) with the QUILL key + Quick Nav + docked panel
  + Workspace Snapshot model.
- **Obsidian** — vault, graph, backlinks, Bases. QUILL borrows
  the *vault metaphor* (Workspace = local vault) and the
  *saved filters* (Filters) but explicitly does not adopt the
  graph view in 1.0 (per the standing rules, axe-core, etc., are
  deferred to 2.0). A future "Backlinks" panel that scans the
  Workspace for `[[wiki-style]]` links is a natural 2.0 add-on.
- **Scrivener** — binder, corkboard, outliner, snapshots.
  QUILL borrows the *snapshots* (immutable saves) and the
  *binder* (Library panel) and adds a *Filter* concept that
  Scrivener lacks.
- **Org-mode** — tree, tags, agenda, babel. QUILL borrows the
  *tags* and the *agenda* (Goal) but not the babel / executable
  block. The user Python sandbox and Quillins cover similar
  ground in a more contained way.

The shape is *QUILL-native*: a docked left panel, the QUILL key,
Quick Nav, command palette, and a Workspace Snapshot JSON. The
metaphors are borrowed because they are the right ones; the
implementation is QUILL's.

---

## 8. "Make it amazing" — creative proposals

These are not strict backlog items. They are sketches to inspire
discussion, in priority order.

### 8.1 The QUILL key "what can I do here" panel

The roadmap already calls for a non-modal QUILL key overlay. The
proposal: when the user presses the QUILL key and pauses (no
follow-on key within 250ms), a small overlay appears at the
bottom-left of the editor showing the top ten follow-on keys for
the current context. The overlay is *navigable by arrows*, *closes
on Escape*, and is *announced by the screen reader*. Pressing a
follow-on key dismisses the overlay and runs the command. This is
"Spotlight meets the QUILL key."

### 8.2 Spoken Workspace Tour

A first-run experience for Workspaces: when the user opens a new
Workspace, the QUILL voice narrator walks through the structure
("Workspace: My Novel. 3 groups, 12 sheets, 4 sticky notes. Group
1: Chapters. Sheet 1: Introduction..."). The user can press
Escape to skip, or Space to continue. This is Ulysses's "Sheets"
onboarding, screen-reader-first.

### 8.3 Inline word and character count per section

A docked *Section Stats* cell that shows the word count, the
character count, the reading time, and the "misspelling hint" (a
small badge that links to the Misspelling List filtered to this
section). Updates as the user types. Announced on demand by a
status-bar query.

### 8.4 "Focal Mode" (F11)

A full-screen writing surface that hides the menu bar, the status
bar, the Library panel, the sticky notes, and the AI chat. The
editor is centered, the current paragraph is highlighted, and a
reading ruler (an optional 2-line band) follows the cursor. The
screen reader narrates the current sentence, the next sentence,
and the document position on every caret move. Voice: "Sentence
twelve of forty-two, paragraph three of seven, sheet
'Introduction', line 41." This is a writer's room, not a
distraction surface.

### 8.5 Audio Workspace

A Workspace that lives in the audio domain. A user opens an
audio file (or records into QUILL via BITS Whisperer), the
transcript becomes a sheet, the sticky notes become bookmarks,
and the Workspace's Goal is "minutes recorded today." This is
the same Workspace concept applied to a different content
type — and it is genuinely novel for a screen-reader-first
editor.

### 8.6 In-line AI "ghost" suggestions

A non-modal AI completion surface: as the user types, a small
ghost text appears (gray, italic) showing the AI's suggested
continuation. Pressing a configurable key ("QUILL + ." or "Tab
when no other completion is showing") accepts the suggestion.
"QUILL + ," dismisses. The suggestions are opt-in per Workspace
and respect the consent gate. This is a much lighter-weight AI
experience than the dialog-based rewrite / continue flow that
already exists.

### 8.7 Reading Mode

A mode that turns the editor into a read-only surface with a
configurable line-focus highlight, an optional reading ruler,
and a single key ("R") that reads the current sentence / line /
paragraph aloud using the existing Read Aloud engine. The screen
reader is *not* competing; the editor narrates only on demand.
This is iA Writer's Focus Mode with a screen-reader twist.

### 8.8 "Speak workspace" command

A single key that reads the Library's current selection in full:
the Workspace name, the structure (group > sheet > section), the
sticky notes pinned to the current sheet, the goal status, and
the last snapshot time. This is QUILL's "I am here" speech. It
takes one line of code and is a confidence-builder for new
users.

### 8.9 Inline status for sticky notes

When a sticky note is pinned to a sheet, a small status-bar cell
shows the count and the most-recent title. Hover (or focus) on
the cell opens a tooltip; pressing Enter jumps to the Sticky
Notes panel filtered to the current sheet.

### 8.10 Quick Goal

A status-bar cell that opens a one-field "Daily Goal" prompt on
Enter. The user types 500, presses Enter, and the Goal is set
for the current Workspace. The cell updates to show progress.

### 8.11 Section-level Word Prediction

Take the existing `edit.word_prediction` dialog and add an inline,
opt-in, as-you-type variant that completes the current word from
the surrounding 50 characters of context. The screen reader is
*not* interrupted; the suggestion appears as a status-bar cell
and is accepted with one key. This is a much smaller lift than
LLM completion and is a high-frequency productivity win.

### 8.12 "Reveal in Workspace"

A context-menu action on any file path in the editor: "Reveal in
Workspace." If the file is in the current Workspace, the Library
panel scrolls to the matching sheet and announces it. If the
file is not in the current Workspace, the user is offered "Add
to Workspace" / "Open in New Workspace" / "Cancel."

### 8.13 Cross-document outline

A new Quick Nav category: "Workspace Headings" — every heading
in every sheet in the current Workspace, with a small badge
("Chapter 3 > 4. The reversal") showing the parent sheet. A
single keystroke jumps to it. This composes with `quick_nav`
without a new code path.

### 8.14 Section-level diff and review

A "Review Changes" mode that shows the diff between the current
sheet and the last Snapshot, organized by section. The screen
reader announces the section name and the change count. This is
Scrivener's "Compare" applied at the section level.

### 8.15 Section-anchored sticky notes

A sticky note can be pinned to a *section*, not just a sheet. The
note moves with the section as the user edits. This is a small
data-model change with a large usability impact for writers
doing research-heavy work.

### 8.16 Snippet: "paste Workspace context"

A snippet that, when expanded, pastes a YAML or Markdown
front-matter block with the current Workspace name, sheet name,
section name, line, and column. Useful for AI prompts, bug
reports, and structured notes.

### 8.17 Per-sheet feature profile

Allow a Workspace to override the global feature profile per
sheet. A research sheet might have AI disabled; a draft sheet
might have GLOW disabled; a publish sheet might have macros
disabled. This is a power-user feature; it does not need to be
the default.

### 8.18 Custom panel slots

A `View > Panels` submenu that lets the user choose which docked
panels to show: Library, Outline, Sticky Notes, AI Chat, Spell
Check, Search Results, Misspelling List. Each panel is a single
wx region; the user composes the layout.

### 8.19 Workspace-only "export to EPUB"

A command on the Workspace that orders the sheets, applies the
heading hierarchy, generates a table of contents, and exports a
single EPUB. The Pandoc wizard already does the conversion; the
Workspace layer does the assembly.

### 8.20 Workspace as a search corpus

Add a checkbox to the existing `search_in_files` dialog: "Limit
to current Workspace." The user can search the whole machine
or just the project.

### 8.21 "Sticky Note to Sheet" promote

A command on a sticky note that promotes it to a full sheet.
The note's title becomes the sheet title; the body becomes the
sheet's first paragraph. This is the inverse of "Sheet to
Sticky Note" and a common workflow ("I wrote a note, now I want
to expand it").

### 8.22 AI on a Workspace

The AI Hub gets a "Workspace" tab that shows the current
Workspace's structure and lets the user ask questions like
"What open loose ends do I have?" or "List the three
introductions that mention the antagonist." Answers cite the
sheet and section. The consent gate is the same.

### 8.23 Cross-Workspace references

A Workspace can include sheets from other Workspaces as
"references." Useful for a research Workspace feeding a
manuscript Workspace. The reference is a read-only copy in the
referring Workspace; updates are detected on Snapshot save.

### 8.24 "Today" view

A new panel that shows everything that changed in the current
Workspace today: new sheets, edited sheets, new sticky notes,
new snapshots, AI sessions, and the Goal progress. This is
Ulysses's "Today" list, screen-reader-first.

### 8.25 Workspace Diff

Two Workspaces can be diffed (sheet presence, sticky note text,
filter results). Useful for "what's different between the draft
I sent to the editor and the one I have now?"

### 8.26 Voice-driven Workspace navigation

A voice command (Hey QUILL) that opens a sheet by name, sets a
goal, or pins a sticky note. "Hey QUILL, open the introduction."
"Hey QUILL, set today's goal to 750 words." The dictation
engine is the same; the command grammar is Workspace-aware.

### 8.27 Workspace onboarding

A first-run "Try a Sample Workspace" that ships with QUILL:
a tiny project ("Letter to a friend") with three sheets, one
sticky note, one filter, and one goal. The user opens it,
explores the Library, the Outline, the Sticky Notes, the
Snapshots, and the AI Hub — all without writing a word. The
onboarding is itself screen-reader-friendly.

### 8.28 Per-section reading time and Flesch-Kincaid

Each section gets an announced reading time and a Flesch-Kincaid
grade level. The status bar cell toggles between "Words,"
"Reading time," and "Grade level." This is a writing-quality
superpower for a screen-reader user who can't see the wall of
text and wants a number.

### 8.29 Workspace focus session

A "Start a 25-minute focus session" command that opens a single
sheet, hides the Library and Sticky Notes, sets a 25-minute
timer, and announces the start and end. At the end, the Library
returns, the Goal cell updates, and a "Snapshot" button is
offered.

### 8.30 "I am stuck" command

A single key that opens a Workspace-aware AI prompt: "Help me
write the next paragraph of the current sheet, using these
three notes and this filter result as context." The consent
gate is the same; the response is previewed in a docked panel
and accepted with a single key. This is the AI "writer's block"
killer.

---

## 9. Implementation roadmap

Suggested sequencing, mapped to the existing roadmap priority
language.

### 9.1 Tier 1 (1.0 essentials)

- **Workspaces and Library panel** (§7). The core of the redesign.
  The new schema, the docked panel, the snapshot rename.
- **Menu consolidation** (§6). Pure reorganization. Ship a
  `menus.md` companion document alongside.
- **Focus Mode** (§8.4). Single screen, hides chrome.
- **Inline word prediction** (§8.11). High-frequency, low-risk.
- **Auto-format toggle** (§4.14). High discoverability win.
- **Context menu for misspellings** (§4.16). High discoverability
  win.
- **Duplicate selection** (§4.17). Tiny lift, big win.
- **Image insert** (§4.15). Required for many writing apps.
- **Go To Line preview** (§4.9). Trivial.

### 9.2 Tier 2 (post-1.0, near-term)

- **Filters and Smart Folders** (§7.7). Composes with Library.
- **Goals and Progress** (§7.8). Composes with Library.
- **Cross-document outline and quick nav extensions** (§7.9, §8.13).
- **Section-level stats** (§8.3).
- **Inline status for sticky notes** (§8.9).
- **Quick Goal** (§8.10).
- **Reveal in Workspace** (§8.12).
- **Multi-cursor / column select** (§4.3). Larger lift; needs a
  design pass.
- **Saved Searches** (§4.10).
- **Snippets tab stop / placeholder walkthrough** (§4.8).
- **AI chat docked** (§4.5).
- **Reading Ruler** (§4.13).

### 9.3 Tier 3 (exploratory, 2.0 and beyond)

- **Backlinks panel / vault graph** (Obsidian-style; explicit
  deferral per standing rules).
- **Corkboard view** (Scrivener-style).
- **Audio Workspace** (§8.5). Needs BITS Whisperer complete.
- **In-line AI ghost suggestions** (§8.6). Needs the consent
  surface to be a first-class UI element.
- **Cross-Workspace references** (§8.23).
- **Workspace diff** (§8.25).
- **Voice-driven Workspace navigation** (§8.26). Needs the
  voice-commands grammar to mature.

### 9.4 Tier 4 (creativity, optional)

- **"Speak workspace" command** (§8.8). One-liner; high delight.
- **Workspace-only "export to EPUB"** (§8.19).
- **Per-section reading time and grade level** (§8.28).
- **Section-anchored sticky notes** (§8.15).
- **Sticky Note to Sheet promote** (§8.21).
- **"Today" view** (§8.24).
- **Workspace focus session timer** (§8.29).
- **"I am stuck" command** (§8.30).
- **Sample Workspace onboarding** (§8.27).
- **Snippet: paste Workspace context** (§8.16).
- **Per-sheet feature profile** (§8.17).
- **Custom panel slots** (§8.18).
- **Reading Mode** (§8.7).
- **Inline status for sticky notes** (§8.9, overlap).
- **Snippets for Workspace context** (§8.16, overlap).

---

## 10. Closing

QUILL is an editor that treats screen-reader users as the primary
audience and proves it in the architecture: stock controls, dialog
contracts, a typed core, a tight menu, and a roadmap that names the
right risks. The competitive analysis confirms that QUILL is at or
near the front of the pack on accessibility, navigation, AI
integration, and writing-quality tooling, and that the most
under-developed area is the project-organization layer.

The recommendations in this document are conservative in spirit: a
new Workspace JSON schema, a docked Library panel, a Goals surface,
a menu consolidation that flattens Tools, and a long list of
"delight" proposals that are mostly *composition* of primitives
that already exist in the codebase. Nothing in §7 or §8 requires
breaking the dialog contract, the feature-flag discipline, or the
core / io / ui boundary. Everything is a v1.x candidate; the most
ambitious items are honestly Tier 3 and explicitly future.

The bar is: a screen-reader user opens QUILL, presses the QUILL key,
types "library," and the Library panel appears with the current
Workspace's structure announced. They press "G" for group, name a
new group, name a sheet, paste a sticky note, set a daily goal of
500 words, and start writing. Two hours later they press
Ctrl+Shift+S to snapshot, type a name, and the snapshot is saved.
The next morning they press Ctrl+Shift+O, choose the snapshot, and
the editor re-opens to the same place with the same sticky note
pinned to the same section. That is a writing environment that is
not a compromise. That is QUILL.
