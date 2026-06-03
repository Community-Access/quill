# GOLDEN: The QUILL Path to Magical, Accessible Greatness

Status: Draft 1, authored 2026-06-01. Owner: product and engineering. Current product version: 0.1.5 Beta (target: 1.0 GA).

This is the master plan to take QUILL from an already strong, screen-reader-first editor to something genuinely delightful, dependable, and shocking in the best way. It combs the whole product: every layer, every feature, the QUILL key, navigation, selection, documentation, podcasts and tutorials, plus a full code-quality, security, and performance review.

Non-negotiable principle: everything ships accessible. No feature is "done" until it is fully operable and pleasant with NVDA, JAWS, Narrator, and VoiceOver, by keyboard alone, in high contrast, and at large font sizes.

## How to read this document

- Sections 1 to 13 are the reasoned plan, grouped by theme.
- Section 14 is the prioritized, trackable backlog. Each item has an ID, priority, size, and acceptance criteria. Treat that table as the single source of truth for execution.
- Priorities: P0 (must fix or land for 1.0), P1 (high value, near-term), P2 (valuable, post-1.0), P3 (exploratory or stretch).
- Sizes: S (under a day), M (a few days), L (about a week), XL (multi-week).

## Table of contents

1. Vision and the "magical and accessible" bar
2. Product-wide delight themes
3. The QUILL key as a flagship feature
4. Navigation deep dive (Quick Nav)
5. Selection deep dive
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
2. A consistent "scope" concept. Many actions operate on selection, paragraph, or document. Make that fallback model uniform and always announced. See NAV-3, SEL-2.
3. Progressive disclosure. First-run users see scaffolding and tips; power users can silence it. Tie this to feature profiles. See UX-2.
4. Earcons (optional, off by default). Subtle, distinct sounds for mode-enter, action-done, not-found. Already partially present for the QUILL key; generalize tastefully and make it opt-in. See QK-6.
5. Recoverability everywhere. Undo, backups, crash recovery, and "return to editor" are universal guarantees. Audit every dialog for an escape and a default. See A11Y-4.
6. Honesty about AI and extraction. Always show provider, model, scope, and confidence. Never a silent network call. Already strong; keep it as a hard rule. See AI-5.
7. Feature flags are a fundamental, not an afterthought. Every feature is individually switchable through the existing `FeatureManager` (`quill/core/features.py`), and the UI must honor that choice everywhere: a disabled feature hides or disables its commands, menu items, status-bar cells, QUILL key and Quick Nav entries, settings groups, and onboarding prompts, and a feature with unmet dependencies stays off. Feature profiles (Essential, Writer, Developer Power Text, Accessibility Professional, Full QUILL) let users adopt whole sets at once, and individual toggles override within a profile. Every new feature ships with a `FeatureDefinition` (id, dependencies, maturity, privacy, and whether it is off by default), so users can turn anything on or off and the product respects it consistently, with no orphaned or dead commands. See FLAG-1 through FLAG-4.

---

## 3. The QUILL key as a flagship feature

Today the QUILL key is implemented as a prefix chord, `Ctrl+Shift+Grave`, followed by a second key, with a 1.5 second timeout window. It drives document actions (headings, snippets, preview, read aloud, dictation, sticky notes) and a separate Quick Nav browse mode that uses single-letter keys (H for heading, A for link, L for list, I for list item, T for table, Q for block quote, B for bookmark, P for paragraph, S for sentence, and so on).

This is good bones. The problem: the QUILL key is powerful but under-told and slightly inconsistent. It deserves to be the signature interaction that people talk about.

### 3.1 Make the QUILL key a named, prominent identity

- Give it a canonical name in all docs and UI: "the QUILL key." Establish that `Ctrl+Shift+Grave` is the QUILL key, and that it is also remappable for keyboards where Grave is awkward (for example to `Caps Lock` via an opt-in, or to a single dedicated key). See QK-1.
- Add a discoverable, always-available "QUILL key menu" overlay. When you press the QUILL key and pause, a non-modal, screen-reader-friendly list appears announcing the available follow-on keys grouped by purpose (Navigate, Insert, Format, Read, Dictate). This is a guided cheat sheet that does not block typing. See QK-2.
- QUILL key plus question mark shows the full, live QUILL key cheat sheet on demand: every follow-on key and what it does, grouped by purpose, in an accessible, screen-reader-pageable list that reflects the active keymap and profile (so it always matches the user's real bindings). This is the instant "what can I press" answer and the fastest path to discovery. See QK-9.
- Context-sensitive help is built into every mode: pressing question mark after entering a QUILL sub-mode shows only that mode's keys. For example, QUILL key plus N (Quick Nav) followed by question mark lists every navigation key (H heading, A link, L list, T table, and the rest) with live counts and current bindings; the same pattern applies to Insert, Format, Read, and Dictate sub-modes. Help is always one question mark away, wherever the user is. See QK-9, NAV-1.
- Status bar indicator. When QUILL key mode is pending or active, the status bar announces and shows a subtle state so users always know the mode is live. See QK-3.

### 3.2 Make the timeout forgiving and configurable

- The 1.5 second window is invisible and can feel like a trap. Make the timeout configurable (including "no timeout until Escape") and announce entry and expiry. See QK-4.
- Allow a sticky mode: press the QUILL key twice to "lock" browse mode until Escape, for extended navigation sessions. See QK-5.

### 3.3 Resolve the binding collisions and inconsistencies

- Today `Ctrl+Shift+Grave, N` is Sticky Note capture, while Quick Nav uses bare letters once in browse mode. Two different mental models share one prefix. Document the two modes clearly and consider unifying: a single QUILL key that opens a navigable, type-ahead "QUILL panel" with tabs for Navigate, Insert, Format, Read. See QK-2, QK-7.
- Audit all QUILL key chords for conflicts and ensure `find_keymap_conflict` is wired into the keymap editor and import flow with a spoken warning. See KEY-3.

### 3.4 Extend the QUILL key with new magic (opt-in, discoverable)

- QUILL key plus G: "Go to anything" universal jump (headings, bookmarks, links, open documents, recent files) with type-ahead. See NAV-4.
- QUILL key plus K: command palette scoped to the cursor context ("what can I do here").
- QUILL key plus number 0: jump to top, repeated for cycling key landmarks.
- QUILL key plus period: repeat last QUILL action. See QK-8.

Acceptance for the QUILL key program: a new user can discover every QUILL action without reading a manual, a power user can operate silently and fast, and the feature is documented as the headline interaction in the user guide and the marketing announcement.

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

## 5. Selection deep dive

Selection today includes line, paragraph, block, to-end and to-start of line and document, an Emacs-style mark ring (set, jump, swap, list), and an F8 extend-selection mode.

### 5.1 Bind and announce the structural selections

- Select Line, Select Paragraph, Select Block are present but unbound by default. Provide sensible default bindings and announce the resulting scope and word count. See SEL-1.

### 5.2 Expand and shrink selection by structure

- Add "expand selection" and "shrink selection" that grow or shrink by semantic unit: word, sentence, paragraph, block, document. This is one of the most loved features in modern editors and is highly accessible because each step announces its new scope. See SEL-2.

### 5.3 Selection actions surface

- After any selection, offer a quick "do something with this" affordance (QUILL key while a selection is active) that lists scope-aware actions: rewrite, summarize, fix grammar, read aloud, copy with source, convert case, count words. See SEL-3.

### 5.4 Multi-mark and rectangular review

- Allow naming marks and reviewing a marked range non-destructively. Consider a read-only "review buffer" that shows the marked region in a stock multiline control for screen-reader paging. See SEL-4.

### 5.5 Extend mode polish

- Make extend-selection mode announce on enter and exit, show state in the status bar, and confirm the committed scope when broken. See SEL-5.

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

- Full docs audit and inventory. Catalog every file under [docs/](docs/) (PRD, user guide, engineering docs, accessibility ACR and VPAT, localization, announcements, and the generated HTML and EPUB), note status (current, stub, stale, duplicate), and record the result so nothing is missed. See DOC-14.
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
| SEC-1 | Validate configured executable paths at load | Security | M | Done | Tampered settings cannot launch arbitrary executables; unknown tool paths are rejected and announced; tests cover the reject path. |
| SEC-2 | Path-escape guard for persistence writes | Security | S | Done | A shared helper blocks writes outside the app data base; used in storage writers; tests prove traversal is blocked. |
| SEC-3 | Whitelist OCR language codes | Security | S | Done | `validate_ocr_language` enforces the Tesseract code grammar (lowercase ISO segments with optional script suffix, joined by `+`); option-injection like `--config` or `-psm` and any malformed code is rejected with a clear message before reaching the CLI; tests cover accepted and rejected shapes. |
| SEC-5 | Explicit TLS verification on all network calls | Security | S | Done | A shared `verified_ssl_context()` (certifi-aware, `CERT_REQUIRED`, `check_hostname` on) backs AI, update, model-download, and DECTALK-download requests; HTTPS endpoints always pass it while local HTTP loopback does not; an audit test asserts no `_create_unverified_context` or `CERT_NONE` or disabled `check_hostname` anywhere in the package. |
| SEC-6 | Verify checksums for downloaded binaries and models | Security | M | Todo | DECtalk runtime and GGUF downloads are checksum-verified before use; failure aborts with a clear message. |
| SEC-8 | Gate plugin loading behind off-by-default experimental flag | Security | S | Todo | No third-party plugin loads in a default build; flag is documented as experimental. |
| SEC-9 | Resource limits for the Python sandbox | Security | M | Todo | A wall-clock and memory limit terminate runaway transforms; termination is announced; test included. |
| CQ-7 | Scoped strict mypy in CI on every pull request | Code quality | S | Done | A `scoped-strict-typing` job in Security CI runs `mypy quill\core quill\io` on every push and PR and blocks merge on any error; the scoped command is documented in CONTRIBUTING. The full TYPE backlog was cleared so the gate currently reports zero errors across 95 source files. |
| PERF-8 | Document and enforce scoped type-check command | Performance | S | Done | CONTRIBUTING specifies `mypy quill\core quill\io` as the only recommended type-check command and explains why the whole-tree scan is excluded; no unscoped scan is recommended anywhere. |
| A11Y-1 | Announcement style guide and audit | Accessibility | M | Done | A written grammar (`docs/accessibility/announcement-style-guide.md`) defines the shape `<Verb> <object>[, <count> <unit>(s)][, <detail>].` and is implemented in `quill/core/announcements.py` (`format_announcement`, `format_progress`, `pluralize`). The AI writing-action announcer now builds phrasing through the shared helpers, and unit tests verify the key phrases ("Rewrote paragraph, 42 words.", thousands separators, singular/plural units, verb-only and "Nothing to" forms). Migrating the remaining legacy status strings to the helpers is tracked as incremental follow-up. |
| A11Y-4 | Dialog escape and default audit, enforced by a contract guard | Accessibility | M | Todo | Every dialog has an Escape path and an explicit default, and focus returns to the editor on close. This is made un-regressable by a machine-enforced dialog-contract guard (a GATE-6-style conformance test) that fails when a `wx.Dialog` in the UI violates the construction contract that the find-in-files trap (#84) and the status-bar/misspelling layout bugs all shared: a `StdDialogButtonSizer` must be added with `wx.EXPAND` (never `wx.ALIGN_RIGHT`), the dialog must own an outer sizer wrapping its panel, an explicit default button and `apply_modal_ids` affirmative/escape id must be set, and the dialog must be `Destroy()`-ed. The guard steers new dialogs to the approved helpers (`quill/ui/dialog_contract.py`, the stock `wx.MessageDialog`/`SingleChoiceDialog`/`TextEntryDialog`, or the web `show_web_form`) so the bug class cannot recur. Pairs with the DLG cluster and GitHub issue #73. |
| OPS-1 | Green main: required CI gates must pass | Foundations | S | Done | The gate ladder is only real if it is green on `main`. The newly added gate jobs were red because they installed only `.[dev]`: the UI test modules need `wx` (the `ui` extra) and the scoped-typing job could not find optional modules (`markitdown`, `certifi`, `pdfplumber`, `pyttsx3`). Fix: install `.[dev,ui]` in the test jobs and add the optional modules to the mypy `ignore_missing_imports` overrides so the typing gate measures first-party code regardless of optional extras. Verified: PR CI, Security CI, and Accessibility CI all conclude success on `main` (commit d62d3bd). |
| FLAG-1 | Feature-flag respect is a UI contract | Foundations | M | Done | `FeatureManager.is_enabled`/`is_visible` are now dependency-aware: a feature whose dependency chain is not fully enabled is treated as off no matter how the dependency was disabled (profile or override), so `visible_commands`, status-bar cells, the palette, and menu gating all hide a feature when an upstream dependency is off. Contract tests cover the off-dependency case, command visibility filtering, and the all-dependencies-on case across representative features (dictation, BITS transcription, search). |
| FLAG-2 | Every new feature ships a FeatureDefinition | Foundations | S | Done | A source-contract test scans `quill/ui/main_frame.py` for every `feature_id="..."` wired to a command surface and fails if any references an id absent from `FEATURE_DEFINITIONS`, so no command is orphaned to an unknown feature. Combined with the existing palette/command filtering, this makes registering a `FeatureDefinition` (id, name, description, dependencies, maturity, privacy) the definition-of-done for a user-facing feature. |
| FLAG-3 | Feature profiles and per-feature toggles UI | Foundations | M | Done | An accessible surface lets users pick a feature profile (Essential, Writer, Developer Power Text, Accessibility Professional, Full QUILL) and override individual features within it; changes apply live, announce, and persist (schema-validated, atomic, recoverable). Dependencies resolve automatically (enabling a feature enables what it needs; disabling one quietly pauses dependents) and the resolution is announced. Fully keyboard and screen-reader navigable. Delivered: the Profiles and Features dialog already covered profile selection, live switch with undo, compare, reset, custom profiles, and import/export; this adds the per-feature override surface (Help > Feature Profiles > Manage Individual Features...), a stock `wx.CheckListBox` of every non-locked feature whose checkboxes reflect effective state and toggle live. Toggling calls the tested wx-free `FeatureManager.set_feature_enabled`/`describe_feature_toggle` helpers, which resolve the dependency cascade and return a screen-reader announcement; changes persist via the feature store and the menu rebuilds immediately. |
| FLAG-4 | Export, import, and pre-configure feature flags | Foundations | S | Done | The full feature-flag and profile state exports to and imports from a versioned `.qpf` QUILL profile file so a power user or administrator can pre-tune which features are on before first run, and reset is available through the existing Reset to Factory Defaults. Core round-trip helpers (`export_feature_profile_file` / `import_feature_profile_file`) live in `quill/core/features.py` with unit coverage, and Export profile / Import profile buttons sit beside the Settings Export/Import/Reset controls (`Ctrl+,` then General). Tolerant import ignores unknown profiles and locked features and announces the result. (Pairs with SET-7.) |
| QK-1 | Name and remappable QUILL key | QUILL key | S | Done | Docs and UI call it the QUILL key; the prefix chord is now read from `Settings.quill_key_binding` (default `Ctrl+Shift+Grave`) and matched by `_quill_key_prefix_matches`, which also understands the Grave/backtick key; remapping to another chord (for example `Alt+M`) works and the old default no longer triggers. |
| QK-3 | QUILL key mode status indicator | QUILL key | S | Done | A `quill_key_mode` status-bar cell reports Off / Prefix / Browse / Locked, appears automatically while the prefix is pending or a mode is active, and the prefix/enter/exit transitions announce. |
| QK-4 | Configurable, announced QUILL key timeout | QUILL key | S | Done | `Settings.quill_key_timeout_seconds` (clamped 0..60) drives both the prefix and browse-mode expiry via `_quill_key_timeout`; a value of 0 means no timeout; entry announces and expiry announces "QUILL key timed out" / "QUILL browse mode timed out". |
| KEY-3 | Wire keymap conflict detection into UI and import | Keymaps | M | Todo | Conflicts are detected on bind and import, announced, and resolvable. |
| DOC-1 | QUILL key primer and quick reference | Docs | M | Todo | User guide section plus standalone reference; ships as HTML and EPUB via the gate. |
| DOC-5 | Document the docs-artifact gate for contributors | Docs | S | Todo | Contributor docs explain regenerating HTML and EPUB; gate stays green. |

### P1: high value, near-term

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| CQ-1 | Decompose main_frame into cohesive modules | Code quality | XL | Todo | main_frame is split into controllers or mixins with no behavior change; characterization tests pass before and after. |
| CQ-16 | Characterization tests around main_frame | Code quality | L | Todo | Behavior is pinned by tests prior to CQ-1; coverage includes menus, QUILL key, selection, file lifecycle. |
| DLG-1 | Migrate hand-rolled submit-once form dialogs to the shared accessible helper | Code quality | M | Done | Executes the form wave of GitHub issue #73. Hand-rolled multi-field `wx.Dialog` forms that are pure submit-once input move onto the already-shipped `show_web_form` (`quill/ui/web_form.py`, accessible WebView with a native wx fallback) or, where a single field fits, a stock `wx.*` dialog. wxPython has no stock multi-field dialog, so this consolidates them on one tested, screen-reader-friendly surface rather than per-dialog focus/button code. Each migration keeps the existing inputs and outputs, lands behind a focused behavior test, and leaves the public surface unchanged (GATE-6). **Delivered:** Insert Link (two-field display-text + URL submit-once form) migrated onto `show_web_form`, keeping identical inputs and outputs (prefilled selection, `https://` default, blank-URL cancel, markdown/HTML/plain link emission) behind three focused behavior tests; public surface unchanged. **Delivered:** `_prompt_search` (Find All Matches dialog: query + optional replacement + mode choice + case-sensitive checkbox) migrated onto `show_web_form`, keeping identical inputs and outputs (query prefill, mode selection with Plain text/Whole word/Regular expression/Wildcard, case-sensitive checkbox, SearchOptions construction) behind six source-contract tests; public surface unchanged. **Deferred (honest):** find/replace-in-files (`_prompt_file_search`) carries a `DirPickerCtrl` Browse button that `show_web_form` does not support (text/textarea/select/checkbox only), plus mode/output `wx.Choice`es and conditional preview checkbox, so it remains a hand-rolled `wx.Dialog` and stays A11Y-4-compliant. Watch Folder Settings is a list manager (Add/Edit/Duplicate/Toggle/Delete) whose per-profile editor has Browse buttons, conditional schedule/action fields, and a sandboxed Python code editor — a CRUD flow, not a submit-once form. The read-aloud voice chooser is a per-engine chain of stock choice/entry dialogs (already simple). Status Bar Layout has Move Up/Down reordering (reorder flow, not submit-once). The YAML editor is a tree editor with Insert/Delete/Promote/Demote operations (tree CRUD, not submit-once). General Preferences is now the Settings dialog, a multi-page notebook with dynamic control generation, per-field reset buttons, and search — a complex live-update surface, not a submit-once form. These remain A11Y-4-compliant and are not migrated, to avoid degrading working dialogs. All genuinely submit-once dialogs suitable for `show_web_form` have been migrated. |
| QA-1 | Living dialog regression checklist | Code quality | S | Done | `dialogs.md` in the repo root is the master manual regression checklist for every user-facing dialog, each mapped to the keyboard command or menu path that opens it, grouped by menu, with nested and startup-only dialogs called out. It is generated from a full scrub of `quill/ui/` and the `quill/core/keymap.py` bindings, formatted as a tick-off todo list so a tester can record a full pass on a build. A contributor rule in `.github/copilot-instructions.md` ("Keep dialogs.md current") requires the matching row to be updated in the same change whenever a dialog is added, removed, renamed, or rebound, so the map never drifts. This is the manual companion to the A11Y-4 machine-enforced dialog-contract guard. |
| CQ-8 | Degrade-and-log helper for broad excepts | Code quality | S | Todo | A shared helper logs context; broad excepts in core use it; no silent failures remain in the listed files. |
| DLG-2 | Convert interactive tool dialogs individually, screen-reader verified | Code quality | L | Todo | The remaining custom dialogs that are interactive tools rather than forms (Run Python, Prompt Studio, Agent Center, Writing Assistant, the model pickers, AI Hub, Assistant Connection, Train Style, the command palette) are converted to the web or native pattern of issue #73 one at a time, each verified with a screen reader. These are working, accessible-today features with live lists, generate/preview/verify buttons, async downloads, and background threads, so they are explicitly NOT batch-rewritten; conversion is prioritized by which read poorly today and gated by the A11Y-4 contract guard. This is the structural-breadth half of the dialog work and sequences after Tier 2, alongside CQ-1. |
| CQ-11 | Spell-check fallback and preload tests | Code quality | S | Todo | Tier fallback is now covered: `tests/unit/core/test_spellcheck_backend.py` pins each of the three tiers (enchant, bundled wordlist, built-in stub) by seeding the module caches and confirms `backend_info` and `is_known_word` honour the active tier, plus a personal-dictionary override. The background-preload half stays open until a spell-check preload API exists (tracked by PERF-1). |
| CQ-13 | IO format coverage tests | Code quality | M | Done | Markdown, HTML, JSON, CSV, DOCX bridge, and PDF scoring all have fixture-based tests. JSON/CSV/DOCX-bridge/PDF-scoring live in `tests/unit/io/test_structured.py`; Markdown and HTML fixtures were added to `tests/unit/io/test_text.py`, confirming they open verbatim through the plain-text reader and round-trip through the writer. |
| CQ-15 | Document cache locking and add concurrency tests | Code quality | S | Done | Thesaurus/spell-check/watch-folder locks are confirmed present; a concurrency test exercises them and a short note records the invariants. The note is [docs/engineering/thread-safety.md](docs/engineering/thread-safety.md) (shared with CQ-17), and `tests/unit/core/test_cache_concurrency.py` hammers the thesaurus index and spell-check wordlist from sixteen threads against a cold cache, proving each expensive load runs at most once and every thread agrees on the published snapshot and active backend tier. |
| PERF-1 | Background preload of spell-check wordlist | Performance | S | Todo | First spell check does not stall; preload runs off the UI thread; perf test added. |
| PERF-2 | Background preload of thesaurus | Performance | S | Todo | First lookup does not stall; perf test added. |
| PERF-3 | Cache synthesized TTS audio | Performance | M | Todo | Identical sentences are not re-rendered; measurable latency reduction; test or benchmark added. |
| PERF-9 | Performance budget suite | Performance | M | Todo | Startup, first spell check, first thesaurus, and Quick Nav prewarm have budgets enforced in CI. |
| NAV-1 | Unified Quick Nav panel | Navigation | L | Done | Delivered as one unified surface with NAV-4 (`open_quick_nav`): a category list shows each element type with its live count, and the results list shows previews; fully keyboard and screen-reader operable. Built on the shared, fully unit-tested `quill/core/quick_nav.py` index. |
| NAV-2 | Consistent directional and wrapping Quick Nav | Navigation | M | Todo | Every element type supports next and previous with announced wrap. |
| NAV-4 | Go to anything jumper | Navigation | L | Done | One index of landmarks (headings, links, lists, list items, tables, block quotes, bookmarks, code blocks) with a type-ahead filter and category narrowing, bound to the QUILL key plus G (and the `navigate.quick_nav` command). Selecting an entry jumps to it. Shares the `quill/core/quick_nav.py` index with NAV-1. |
| NAV-5 | Heading level and position announcements | Navigation | S | Done | `heading_context_at` (in `heading_organizer.py`) reports a heading's level, 1-based ordinal, total count, and title by line match; `_navigate_heading` announces "Moved to next/previous heading, H<level>, <ordinal> of <total>: <title>" for both Markdown and HTML. Core and UI tests cover level/ordinal/title, leading-whitespace lines, off-heading None, and HTML. |
| SEL-1 | Bind and announce structural selections | Selection | S | Done | `select_line`, `select_paragraph`, and `select_block` announce scope and word count through the shared announcement grammar (`Selected line, 3 words.`), pluralized correctly for the singular case. UI tests cover line, paragraph, and the singular-word path. |
| SEL-2 | Expand and shrink selection by structure | Selection | M | Done | `expand_selection` grows the selection through word, line, sentence, paragraph, block, then whole document, announcing the new scope and word count at each step; `shrink_selection` walks back down a remembered stack. Core `expand_selection`/`word_span` plus `edit.expand_selection`/`edit.shrink_selection` commands; core and UI tests cover strict growth, the document ceiling, and stack-based shrink. |
| SEL-3 | Scope-aware selection actions surface | Selection | M | Done | With text selected, the QUILL key prefix then `A` opens an accessible stock choice dialog of actions tailored to the selection's structural scope (`quill/core/selection.selection_scope` classifies it as word / line / sentence / paragraph / block / lines / document). Case and clipboard actions always appear, Markdown/HTML emphasis appears only on a markup surface, and line-oriented actions (sort, indent, toggle comment) appear only for multi-line selections; the chosen action runs the existing tested command. The prefix status line advertises the `A` action whenever a selection is active. Covered by core scope tests and UI tests for the action list, the chosen-action dispatch, the no-selection message, and the prefix-then-`A` wiring. |
| OCR-1 | Native Windows OCR backend (zero-install) | Image to text | M | In progress | `quill/io/ocr.py` is now backend-pluggable (`OcrBackend` Protocol, `WindowsOcrBackend`, `TesseractBackend`, shared `OcrResult`/`OcrLine` with per-line confidence) with `select_engine`/`available_engines` and a clean unavailable path; the WinRT backend lives in `quill/platform/windows/windows_ocr.py` (`Windows.Media.Ocr`, offline, no network). Tests cover backend selection, fall-back, the unavailable path, and Tesseract TSV per-line confidence parsing. Remaining: live WinRT recognition is unverifiable in this environment (winsdk not installed), so the native-backend happy path is not yet exercised end to end. |
| OCR-2 | Tesseract opt-in backend via onboarding | Image to text | S | Done | A new `ocr_engine` setting (auto/windows/tesseract, validated in `Settings.from_dict`, surfaced in the settings registry under Accessibility, gated by `core.ocr`) drives backend selection; `auto` prefers the native Windows backend and falls back to Tesseract when present. `main_frame.ocr_image_file` passes the chosen engine through. When the chosen backend is unavailable the announced message points to OCR setup rather than failing silently. Tests cover engine resolution, the fall-back order, explicit-engine honoring, and the unavailable message. |
| OCR-3 | Capture sources: file, clipboard, screen region | Image to text | M | In progress | OCR from an image file is wired (`main_frame.ocr_image_file`, QUILL key + Tools menu, shared progress/outcome grammar, cancel path); the engine layer is capture-source-agnostic. Remaining: clipboard-image and keyboard-driven screen-region live capture require a real display/clipboard and a working OCR engine, neither verifiable in this environment, so those two capture paths stay open. |
| OCR-4 | Accessible OCR review and insert surface | Image to text | M | Done | The wx-free review renderer (`render_ocr_review`) emits the engine/language/low-confidence header and flags low-confidence lines (`OcrResult.low_confidence_lines`, `OcrLine.is_low_confidence`). The live review dialog (`OcrReviewDialog`, wired in `main_frame.ocr_image_file`) shows the recognized text in a stock `wx.TextCtrl(... TE_MULTILINE | TE_READONLY)` with Insert/Copy/Discard actions in a `wx.StdDialogButtonSizer` (buttons carry standard wx ids so they realize natively; Insert is the default, Discard is the escape id) and returns focus to the editor on close. Source-contract tests cover the readonly control, the three actions, the modal accessibility hooks, and the MainFrame wiring; the dialog is tracked in `dialogs.md`. |
| OCR-5 | OCR as a Watch Profile action | Image to text | S | Done | `OcrAction` is registered in the `default_registry` action registry, gated by `core.ocr` and offline-by-default (no consent gate), writing recognized text to a sibling `.txt` file. Tests cover registration, the disabled-feature skip path, a happy-path conversion with an injected handler, and the no-engine failure path. |
| QK-2 | QUILL key guided panel or overlay | QUILL key | L | Done | A screen-reader-friendly guide lists follow-on keys grouped by purpose, rendered from the shared `quill/core/quill_key_help.py` cheat-sheet builder into an accessible read-only dialog (outer sizer, EXPAND, default Close, Escape, focus returned to the editor). Shares one source of truth with QK-9. |
| QK-9 | QUILL key plus question mark cheat sheet and per-mode help | QUILL key | M | Done | QUILL key plus question mark shows the live cheat sheet of follow-on keys grouped by purpose, reflecting the active keymap (resolved through `_binding_for`) and live element counts from the browse navigation cache; pressing question mark while the prefix is pending shows the prefix keys, and inside browse mode shows the browse keys without leaving browse mode. `?` is recognized directly and as Shift+/. Core builder is UI-agnostic and fully unit-tested (`test_quill_key_help.py`); UI wiring is covered in `test_main_frame_quill_key.py`. |
| QK-5 | Sticky QUILL browse mode | QUILL key | S | Done | A second press of the QUILL key while the prefix is pending locks a sticky browse mode (`_quill_key_mode_sticky`) that ignores the timeout until Escape; entry announces "QUILL browse mode locked" and the status cell shows Locked. |
| KEY-1 | Vim, Emacs, and VS Code keyboard packs | Keymaps | L | Todo | Three complete, documented, accessible packs are selectable. |
| MENU-1 | Unified Preferences home | Menus | M | Done | Settings open through one tabbed front door (`Ctrl+,` then `General`) built from the shared settings registry, and the scattered Tools-menu toggles (announcement-trace capture, Hey QUILL commands, watch-folder monitoring) now redirect into Settings instead of carrying their own check state. |
| SET-1 | Per-feature settings groups | Settings | M | Done | The Settings dialog renders one accessible `wx.Notebook` page per registry group (general, editing, navigation, accessibility, read aloud, AI, transcription, watch folders, updates), each control generated from `quill/core/settings_registry.py` specs (bool, choice, int, float, text). Every scalar setting across these areas — including side preview, CSV/Word open mode, and snippet trigger expansion — is surfaced as a registry spec and auto-renders with per-setting reset and search. Collection-style customization that is not a single scalar value (snippet bodies, recorded macros, sticky-note content, and status-bar layout) is managed in its own dedicated accessible manager dialog (Snippet Manager, Macro Recorder, Sticky Notes Vault, Status Bar Layout) by design, rather than as a registry control. |
| SET-2 | Tunable timing and pacing | Settings | M | In progress | QUILL key timeout, Quick Nav debounce and threshold, autosave interval, announcement throttle, Read Aloud rate, pitch, and sentence pause, and dictation sensitivity are now registry-backed `Settings` fields (clamped in `from_dict`) and auto-render in the tabbed dialog with per-setting reset. Live consumers now wired: Read Aloud rate/pitch drive the engine live; the **autosave interval** is consumed on startup and re-applied when the Settings dialog closes; the **announcement throttle** is enforced in `_set_status` (suppresses repeat status speech within the window); **Quick Nav debounce** (`quick_nav_debounce_ms`) defers type-ahead filtering via `wx.CallLater` and **Quick Nav minimum characters** (`quick_nav_min_chars`) hold off query matching until the field reaches the configured length; the **QUILL key timeout** is read by `_quill_key_timeout`; the **Read Aloud sentence pause** (`read_aloud_sentence_pause_ms`) inserts an interruptible gap between sentences across every TTS engine loop. **Remaining (honest):** the dictation sensitivity field is surfaced/stored but the current dictation backend launches the Windows Win+H recognizer, which exposes no sensitivity control, so there is no consumer to wire until a sensitivity-aware capture engine (Whisper/Vosk live mic) lands. |
| SET-3 | Tunable verbosity and announcements | Settings | M | In progress | A global `announcement_verbosity` level (minimal/normal/verbose) plus per-event overrides (`announce_wrap`, `announce_counts`, `announce_mode_changes`, `announce_spelling`, `announce_punctuation_level`) are registry-backed and surface in the Accessibility tab. Live consumers now wired: `announce_wrap` gates the " (wrapped)" suffix on Find/Replace; `announce_counts` decides whether the word-count summary is spoken or set quietly; `announce_mode_changes` gates QUILL key/browse mode enter/exit speech in `_quill_feedback` (sound still plays); `announce_spelling` short-circuits the passive live-misspelling hint. **Deferred (honest):** `announce_punctuation_level` is stored/surfaced but has no consumer yet — the Read Aloud engine takes no punctuation parameter — so this row stays In progress. |
| SET-4 | Tunable behavior toggles | Settings | M | Done | Sticky browse, per-action confirmations, default export preset and new-document format, autoformat (smart quotes, dashes), and Quick Nav element inclusion (headings/links/lists) are registry-backed `Settings` fields and surface in the General/Editing/Navigation tabs; wrap navigation was already configurable. Every field has a live consumer: `confirm_destructive_actions` gates the discard-changes prompt; `default_new_document_format` sets the Save-As file-type filter for new/pathless documents; `default_export_preset` preselects the Pandoc Conversion Wizard output format; `autoformat_smart_quotes`/`autoformat_dashes` drive inline typography in the editor CHAR_HOOK via the wx-free `quill/core/autoformat.py`; `quick_nav_include_headings/links/lists` filter the Quick Nav index through `include_nav_items`; and `browse_mode_sticky` makes the QUILL key **N** browse entry lock until Escape (covered by `test_prefix_then_n_honors_sticky_browse_default`). |
| SET-5 | Robust settings model with migration | Settings | L | Done | Flat fields are serialized into a nested, versioned document (`schema_version` 1, fields grouped via the settings registry; unspecced fields preserved under `_ungrouped`) by `quill/core/settings_migration.py`. `load_settings` migrates older nested documents and legacy flat documents, and `_safe_from_dict` recovers from corruption by dropping only the offending field while preserving every valid sibling; junk documents fall back to defaults. `save_settings` writes the versioned form atomically. Round-trip, migration, junk-recovery, and per-field corruption tests pass (`tests/unit/core/test_settings_migration.py`). (Pairs with CQ-4.) |
| SET-6 | Searchable settings with per-setting reset and descriptions | Settings | M | Done | A search row inside the Settings dialog jumps to the first control matching a query (over label, key, description, group title, and keywords via `registry.search_specs`); per-spec plain-language descriptions are carried in the registry. Every rendered control now has its own accessible **Reset** button (accessible name `Reset {label} to default`) that restores that single setting to `registry.default_value(key)` via a per-key writer and announces the change; the restored value is committed on OK with the rest of the form. Implemented in `open_general_preferences` (`writers` map + `_reset_one`/`_reset_button` helpers) covering bool, choice, int, float, text, and the preview-browser choice. |
| SET-7 | Export, import, and pre-configure settings | Settings | S | Done | The Settings dialog can export the full configuration to a `.qsf` file, import one back, and reset every setting to factory defaults (with a confirmation gate). Serialized through `registry.export_settings`/`import_settings` (schema_version 1). The same `.qsf` import path is the admin pre-configure mechanism (ship a tuned file, users import it). The optional admin-facing schema reference write-up is tracked separately as DOC-7 in Tier 6 and is not part of this functional row. |
| SHARE-1 | One Export and Back Up dialog with a shareable-profile mode | Settings | M | Done | `open_share_export_dialog` (Tools > Customize > **Export and Back Up...**) is the single accessible front door: a radio group picks **Share a profile (privacy-clean)** or **Back up everything**, a name field labels the package, and a `wx.CheckListBox` chooses sections, each shown with a one-line plain-language summary. The privacy boundary is structural — in profile mode any section flagged private is unchecked and disabled, and the writer (`build_package`, SHARE-3) provably refuses to emit private data into a `.quillprofile` and scrubs private settings fields. Saves through a `wx.FileDialog` with the correct extension, honors the A11Y-4 contract via `apply_modal_ids` + the panel/outer-sizer + `SetDefault` surface, and announces what was written. The wx-free `quill/ui/share_dialogs.py` offer layer now serializes **all eight shareable sections** — settings groups, features/profile, keymap (offered only when customized away from defaults), snippets, macros, watch profiles, personal dictionary, and writing-style models — each gathered only when its store actually holds content, so the checklist reflects exactly what is present. Eleven logic tests cover offers, privacy, and round-trips (`tests/unit/ui/test_share_dialogs.py`). |
| SHARE-2 | One Import and Restore dialog with the same two modes | Settings | M | Done | `open_share_import_dialog` (Tools > Customize > **Import or Restore...**) mirrors SHARE-1: a `wx.FileDialog` opens a `.quillprofile` or `.quillbackup`, a screen-reader-pageable read-only `wx.TextCtrl` shows `package_summary` (including the privacy note), and a `wx.CheckListBox` of the importable sections lets the user apply only what they want. Application is recoverable: `apply_import` snapshots the feature state and rolls it back automatically if any section fails, imported settings flow through the shared `_settings_dialog_apply_refresh` persist-and-refresh path, and import notes/warnings surface in a follow-up message. Honors the A11Y-4 contract via `apply_modal_ids`. The mode is now behaviorally separated: a `.quillprofile` **merges** (keymap overlay, snippets overlaid by id with incoming winning, macros overlaid by name, watch profiles added when absent, style samples combined, dictionary words added) while a `.quillbackup` **replaces** each store wholesale; the personal dictionary is intentionally additive in both modes since there is no public "forget all" API (documented in `_apply_dictionary`). FLAG-1 is wired: when importing features auto-enables a dependency, each forced-on feature is announced as "Enabled X to satisfy a feature dependency." Covered by backup round-trip, profile-merge, and dependency-announcement tests in `tests/unit/ui/test_share_dialogs.py`. |
| SHARE-3 | Portable, privacy-safe profile and backup package format | Settings | S | Done | `quill/core/share_package.py` defines the versioned, human-readable package both SHARE dialogs read and write: a `.quillprofile` for shareable profiles and a `.quillbackup` for full restore points, each carrying a manifest (`schema_version` 1, kind, name, source version, sorted contents, ISO timestamp) and a `package_summary` "what's inside" string suitable for reading aloud before import. Fourteen sections are marked shareable or private; `build_package` raises `PrivacyError` if a profile would include a private section and scrubs private settings fields, while `read_package` defensively strips any private section a hand-edited profile smuggled in and re-scrubs settings. A round-trip test plus a privacy test (every secret/recent-path/license/device-path field provably cannot reach a profile) and file round-trip pass (`tests/unit/core/test_share_package.py`). (Implements the format behind SHARE-1/2 and the schemas FLAG-4 and SET-7 reference.) |
| MENU-2 | Split the Tools menu and elevate Accessibility | Menus | M | Todo | Tools is smaller; Accessibility is easy to find; labels match announcement grammar. |
| HELP-1 | Context-aware What Can I Do Here | Help | M | Todo | The help lists commands relevant to the cursor context with keybindings, readable top to bottom. |
| FEAT-2 | Spell-check usability polish | Features | S | Todo | Add to document dictionary and ignore for session, with announcements. |
| CTX-1 | Rich context and Application-key menu | Features | M | Done | Right-click and the Application/Menu key open one rich, fully keyboard- and screen-reader-operable context menu built from the word and selection under the cursor, turning a plain editor menu into a writer's command surface (GitHub issue #86). When the cursor is on a misspelled word the menu leads with the in-context spelling suggestions as selectable items, followed by **Add to dictionary** and **Ignore** (pairs with FEAT-2), so a correction is one keystroke away without opening the F7 dialog. Below that it offers **Look up** (definition, DICT-2) and **Thesaurus** (synonyms, DICT-1/2) for the current word, the scope-aware selection actions (SEL-3) when text is selected, and the usual cut/copy/paste. The menu is rebuilt live from the cursor context, every item is reachable and announced, and it honors `FeatureManager` so entries for disabled features do not appear. Tests cover the misspelled-word menu shape, the add-to-dictionary path, and feature-off filtering. Delivered: the pure, `wx`-free menu model lives in `quill/core/context_menu.py` (`CursorContext` → `build_context_menu` → ordered, feature-gated `MenuItem`s with single separators between non-empty groups) with a new `core.dictionary` feature gating Look Up/Thesaurus; tests cover the suggestion-led shape, add/ignore, lookup, selection clipboard, feature-off filtering, and separator placement. The UI wiring is in `main_frame.py`: `_build_ctx1_menu_items()` converts the menu model to wx items with handlers for all commands (spelling suggestions, add/ignore, lookup, thesaurus, cut/copy/paste), validated by source-contract tests in `tests/unit/ui/test_main_frame_ctx1_wiring.py`. |
| DICT-1 | Pluggable dictionary and thesaurus services (Free Dictionary, Datamuse) | Features | M | Done | `quill/core/lexical.py` adds a UI-agnostic `LexicalProvider` interface and an offline-first `LexicalService`: the bundled MyThes thesaurus is the always-available default, and two free, key-less online providers (Free Dictionary for definitions/synonyms/antonyms, Datamuse for synonyms/antonyms/rhymes/related) are only queried when the caller passes `online=True` (the consent gate), honoring GATE-9. All HTTPS goes through the verified TLS context (SEC-5); responses normalize into a shared `LexicalResult`, are cached per `(word, online)`, and degrade gracefully to offline when a provider raises or is unavailable. The new `_http_get_json` egress is registered in the GATE-9 audit. Tests cover provider normalization, the consent-off offline-only path, cache behavior, and error fallback. |
| DICT-2 | Accessible Look Up and definitions surface | Features | S | Done | A screen-reader-pageable Look Up surface presents a word's part of speech, definitions, and example sentences (Free Dictionary via DICT-1) alongside synonyms, antonyms, rhymes, and related words (Datamuse via DICT-1), each selectable to insert or to pivot the lookup. It is reachable from the context menu (CTX-1), the Tools menu, and the QUILL key, replaces the bare `SingleChoiceDialog` thesaurus with a richer but equally keyboard-first surface, and announces results through the shared grammar (A11Y-1). Gated by the DICT-1 feature; tests cover rendering from a normalized `LexicalResult`, the insert/pivot actions, and the offline-only shape. Delivered: the pure, `wx`-free surface lives in `quill/core/lexical.py` — `render_lookup` pages the word, sources, definitions (with part of speech and examples), synonyms, antonyms, related, and rhymes, and `build_lookup_items` flattens the result into selectable insert/context `LookupItem`s; tests cover the section rendering, the non-blank empty-result shape, and item insertability. The UI wiring is in `main_frame.py`: `show_lookup_dialog(word)` queries `_lexical_service`, renders the result in a wx.TE_READONLY TextCtrl, presents insertable items in a ListBox with double-click/Insert actions, and honors the `core.dictionary` feature gate, validated by source-contract tests in `tests/unit/ui/test_main_frame_dict2_wiring.py`. |
| DICT-3 | User-selectable source mode with merge-and-compare | Features | S | Todo | The user chooses, per lexical kind (spelling suggestions, synonyms, definitions), which source to trust: **Offline only** (fast, always available — the existing spell/thesaurus data), **Online only** (the DICT-1 providers, richer but slower and consent-gated), or **Both, combined**. In combined mode QUILL queries offline and online in parallel, then merges the result lists into one de-duplicated, ranked set that records each entry's provenance (\"offline\", \"Free Dictionary\", \"Datamuse\", or \"both\"), so a word both sources agree on ranks first and the user can see where each suggestion came from. The merge is a pure, tested `core` function (offline list ∪ online list with case-fold de-dupe and a stable agreement-weighted ordering); the online half degrades gracefully so a slow or failed provider never blocks the offline answer. A setting (and the CTX-1 menu) exposes the mode; tests cover the union/de-dupe, agreement ranking, provenance labelling, and the offline-only fallback when consent is off or the network is down. |
| FEAT-19 | External file-change watch and safe reload | Features | M | Done | QUILL watches the open document for external modification (and deletion). When the file changes on disk and the buffer is unmodified, it reloads in place without moving the cursor or scroll position and announces "Reloaded from disk." When the buffer has unsaved edits (a conflict), it never overwrites silently: it announces the change and offers reload, keep-mine, or compare, with a clear spoken prompt. Behavior is configurable (auto-reload-when-clean on or off, prompt-on-conflict, watch on or off, debounce interval) in a Settings group, defaults are safe and quiet, and the watcher runs off the UI thread reusing the existing watch-folder and stability patterns. Cursor, selection, and scroll are preserved across reload; tests cover clean reload, conflict prompt, deletion, and cursor preservation. Delivered: the pure, `wx`-free engine lives in `quill/core/external_change.py` — `FileSnapshot` (existence, size, mtime, content hash), `ExternalChangeWatcher` (poll → modified/deleted/none, reporting each change once), and `decide_reload` (clean→reload, dirty→conflict prompt, deleted→keep-mine prompt, quiet when disabled), plus four FEAT-19 Settings fields surfaced in the registry; tests cover snapshotting, change/deletion classification, watcher settling, and every decide-reload branch. The UI wiring is in `main_frame.py`: `_start_external_change_watcher()` creates a watcher with wx.Timer polling, `_stop_external_change_watcher()` cleans up, `_reload_from_disk_preserving_cursor()` reloads without moving the cursor, and `decide_reload()` is called with settings to decide the action, validated by source-contract tests in `tests/unit/ui/test_main_frame_feat19_wiring.py`. |
| WATCH-1 | Multi-profile watch engine | Features | L | Done | Replace the single `WatchFolderConfig`/`WatchFolderService` with a list of named, independently enabled `WatchProfile`s, each with its own folder, filters, action, and post-action handling. A `WatchManager` runs one watcher per profile concurrently with isolated failure (one bad profile or file never stalls the others), shared de-duplication so a file is claimed exactly once across profiles, and clean start/stop/restart. The whole surface lives behind a feature id that succeeds `core.watch_folder` and honors `FeatureManager` per FLAG-1: when the feature is off, no watcher runs and its surfaces disappear. The core stays UI-agnostic (no `wx`), reuses the existing poll/age/seen-set patterns, and persists profiles as schema-validated JSON under `%APPDATA%\Quill` with atomic writes and corrupt-file recovery. Tests cover concurrent profiles, isolation, dedupe, persistence round-trip, and the feature-off path. |
| WATCH-2 | Pluggable watch action registry | Features | M | Done | A typed action registry binds each profile to exactly one action via a stable action id. Actions implement a small contract (`describe`, `validate(options)`, `run(item) -> outcome`) so new actions register without touching the engine, and each action declares the feature id it requires so the registry can gate it through `FeatureManager` (FLAG-1). The registry is the seam GLOW (WATCH-8) and BITS Whisperer (WATCH-9) plug into. Unknown, disabled, or unavailable actions degrade gracefully with an announced reason rather than failing a profile. Tests cover registration, validation, the disabled-feature path, and the unavailable-action path. |
| WATCH-3 | Durable, monitorable processing queue | Features | L | Done | Every detected file becomes a queue item with an explicit lifecycle (queued, processing, done, failed, skipped), stable ordering, retry with bounded backoff, and per-profile and global pause/resume. The queue is durable across restarts (schema-validated, atomic, recoverable) and exposes events for the UI. An atomic claim guarantees no item is processed twice even across overlapping profiles. Tests cover lifecycle transitions, retry/backoff, pause/resume, dedupe under contention, and restart recovery. |
| WATCH-4 | Watch Queue Monitor (accessible status surface) | Features | M | Done | A screen-reader-pageable monitor, reachable from Help (next to the status page) and the Tools menu, lists queue items with state, action, profile, source, outcome, and timing, and offers one-key pause, resume, retry, open-result, and clear. The monitor and its menu and status entries are gated by the watch feature id and disappear in lockstep when it is off (FLAG-1). Arrivals and completions announce through the shared announcement grammar (A11Y-1) as calm, non-interrupting notifications, and a live per-profile counter ("Make accessible: 3 done, 1 working, 0 failed") gives an at-a-glance pulse without visual reliance. Fully keyboard and screen-reader operable; tests verify item rendering, the announced phrasing, the action keys, and the feature-off path. Subsumes and extends FEAT-9. |
| WATCH-5 | Per-profile configuration and Settings group | Features | L | Done | An accessible manager creates, edits, duplicates, enables, and deletes profiles. Each profile configures its folder, filters (suffix set, name patterns, min size and age, include-subfolders), action plus action options, schedule (always, a daily active window, or a quiet-hours window), and post-action handling (leave in place, move to a processed folder, or delete). A dedicated **Watch Folders** Settings group holds the six global watch defaults (enable, default folder, include-subfolders, process-existing, auto-start, poll interval) and auto-renders in the tabbed dialog with per-setting reset, search, and export/import; the poll interval is clamped 2-300 s. The **Edit Watch Profile** dialog now exposes the full per-profile surface — suffixes and name patterns (comma lists), min size and age spinners, a schedule-mode chooser with start/end hour-and-minute spinners, per-action option controls (convert target, macro name, sandboxed Python code/suffix/timeout, AI mode), and a dry-run preview — all keyboard and screen-reader navigable with live, announced validation. `core.watch_profiles` carries `name_patterns` and `schedule_mode`/`schedule_start_minute`/`schedule_end_minute`, normalizes and validates them, and gates polling with `profile_is_active` (window and midnight-wrapping quiet-hours). Tests cover create/edit/delete, validation, persistence, name-pattern matching, schedule activeness, and the UI surface contract. |
| WATCH-6 | Watch safety, consent, and resource governance | Features | M | Done | Networked and AI watch actions stay opt-in per profile under the no-silent-network promise (AI-5): nothing reaches a cloud without explicit per-profile consent, and the active provider/model and scope are shown in the profile editor before arming. Wall-clock and concurrency caps (shared with the Python sandbox limits, SEC-9) prevent a runaway folder from overwhelming the machine; a cap termination is now announced distinctly ("Watch stopped … it exceeded the time limit and was terminated to protect your machine") rather than as a plain failure. A dry-run preview, surfaced by a **Preview (dry run)** button in the profile editor, shows exactly what a profile would do (or why it would not) before it is armed. The atomic claim from WATCH-3 prevents double-processing. The `core` layer enforces the consent gate (`WatchActionRegistry.run` returns an announced `skipped` outcome for any `requires_consent` action — currently the AI action — until the profile carries explicit `options["consent"] is True`) and exposes a side-effect-free `WatchActionRegistry.dry_run(...)`. Tests cover the consent gate (skipped without consent, runs with consent), dry-run (runnable preview, invalid options, missing consent, unknown action), the resource-cap classifier and its distinct announcement, and the atomic claim. |
| WATCH-7 | Built-in watch actions | Features | M | Done | The core action set ships on top of WATCH-2 and is fully wired into the UI: Open, Convert/export to a chosen format (via the existing IO and Pandoc paths), Move/copy/archive to a destination, Run a named macro (FEAT-7), Run a saved Python transform (sandboxed, SEC-9), and consented AI actions (summarize, tag, rewrite) via the assistant. `quill/core/watch_actions.py` registers `OpenAction`, `MoveAction`, `CopyAction`, `ConvertAction`, `RunMacroAction`, `RunPythonTransformAction`, and the consent-gated `AiAction` through `default_registry`; `MainFrame` now supplies the real handlers (`_watch_convert_file` runs Pandoc off the UI thread and writes the result, `_watch_run_macro` marshals macro replay onto the UI thread, `_watch_run_ai` honors the AI on/off switch and writes a sidecar so the editor is never overwritten). Each action validates its options, announces its outcome, and routes failures to the queue's failed state with a clear reason, including the distinct resource-cap termination announcement. Tests cover each action's happy and failure paths at the registry seam plus the UI handler wiring and behaviour. |
| FEAT-16 | Document health dashboard | Features | L | Todo | One pane combines audit, contrast, link or alt-text inventory, and plain-language lint. |
| AI-5 | Reaffirm no-silent-network and scope honesty in code and tests | AI | S | Todo | A test asserts no network call without consent; provider, model, and scope are always shown. |
| DOC-2 | Navigation and selection guide | Docs | M | Todo | Worked examples for Quick Nav and structural selection ship in all formats. |
| DOC-14 | Full docs folder audit and inventory | Docs | S | Todo | Every file under docs is cataloged with status (current, stub, stale, duplicate); the inventory is recorded so nothing is missed. |
| DOC-15 | Consolidate and structure the docs folder | Docs | M | Todo | A single top-level docs index links user docs, learning content, reference, and engineering docs; overlapping and stub pages are merged; stale content is removed or marked; folder structure is predictable. |
| DOC-16 | Raise every docs page to a consistent quality bar | Docs | M | Todo | Each page has a purpose statement, consistent headings, working internal links, and a last-reviewed date; skeletal engineering docs are expanded. |
| DOC-17 | Docs style guide and contributor checklist | Docs | S | Todo | A style guide and a checklist (purpose, structure, accessibility, regenerate artifacts) keep the docs folder consolidated and high quality over time. |
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
| CQ-12 | Undo and redo tests | Code quality | S | Done | Edge cases and persistence are covered. `tests/unit/core/test_undo_store.py` exercises missing-history load, no-op clear of an absent history, filtering of non-string and non-list payloads, the `limit` boundary (including a non-positive limit coerced to one), the returned bounded list, multi-cycle accumulation, and per-path isolation so two documents never share a history. |
| CQ-14 | Path-safety tests | Code quality | S | Done | Writes cannot escape app data; tests included. (Pairs with SEC-2.) |
| CQ-17 | Thread-safety invariants note | Code quality | S | Done | A short engineering note documents cache locking rules. [docs/engineering/thread-safety.md](docs/engineering/thread-safety.md) documents the double-checked module-level cache pattern (spellcheck wordlist/enchant, thesaurus index) and the per-instance mutable-set pattern (watch-folder seen-set), plus the rule for new caches. |
| PERF-4 | Replace OCR busy-wait | Performance | S | Todo | OCR uses a proper wait; no fixed-interval polling. |
| PERF-5 | Quick Nav cache invalidation correctness | Performance | M | Todo | Only changed regions invalidate; large-document perf test passes. |
| PERF-6 | Off-thread or batched persistence | Performance | M | Todo | Settings, palette, and recent writes do not stall the UI thread. |
| PERF-7 | Cache markup and structure scans per revision | Performance | M | Todo | Navigation reuses cached scans; measurable improvement on large files. |
| NAV-3 | Uniform scope fallback model | Navigation | S | Todo | Selection, paragraph, document fallback is consistent and announced across actions. |
| NAV-6 | Link navigation announces text, destination, alt state | Navigation | S | Todo | Link browse announces details and alt-text presence. |
| NAV-7 | Table review mode | Navigation | M | Todo | Cell reading announces row and column position. |
| NAV-8 | Misspellings and matches as Quick Nav types | Navigation | S | Todo | Both are navigable element types with announcements. |
| NAV-9 | Quick Nav prewarm race audit | Navigation | S | Todo | No race in cache rebuild; covered by a test. (Pairs with PERF-5.) |
| SEL-4 | Named marks and review buffer | Selection | M | Todo | Marks can be named; a read-only review buffer pages a marked range. |
| SEL-5 | Extend mode polish | Selection | S | Todo | Enter and exit announce; status shows state; committed scope confirms. |
| QK-6 | Optional generalized earcons | QUILL key | S | Todo | Distinct, opt-in sounds for mode enter, action done, not found. |
| QK-7 | Unify QUILL key mental models | QUILL key | M | Todo | The two modes are clearly documented or unified into one panel; no ambiguity. |
| QK-8 | Repeat last QUILL action | QUILL key | S | Todo | A key repeats the last QUILL action with announcement. |
| KEY-2 | Exportable keyboard reference | Keymaps | S | Todo | Reference exports as accessible HTML and EPUB. (Pairs with DOC-6.) |
| KEY-4 | Validate keybinding syntax on save | Keymaps | S | Todo | Invalid bindings are rejected with a plain-language explanation. |
| MENU-3 | Resolve menu redundancy | Menus | S | Done | Insert Link duplication is rationalized: the Edit-menu alias was removed, leaving Insert as the single primary entry. |
| MENU-4 | Labels match announcement grammar | Menus | S | Todo | Menu labels and announcements are consistent. |
| MENU-5 | User-customizable menus and context menu (Menu Editor) | Menus | L | Done | A person can reorder, rename, and hide top-level menus, menu items, and editor context-menu entries, with one Reset to Factory Defaults, all through an accessible Menu Editor. The `wx`-free model layer lives in `quill/core/menu_customization.py` (delta-only, self-healing `reconcile`, versioned persistence) and covers the menu bar and the editor context menu through one shared `CONTEXT_MENU_KEY` model, with full unit coverage. Edit > Customize Menus... (`app.menu_editor`) opens a tabbed dialog with three tabs: **Top-Level Menus** (list + Move Up/Down, Rename, Show/Hide, Reset to Factory Defaults), **Menu Items** (two-pane: select a menu, then edit its items with Move Up/Down, Rename, Show/Hide), and **Context Menu** (list + Move Up/Down, Rename, Show/Hide). The dialog edits a working copy, persists only on Save, and rebuilds the live menu with a post-build transform pass. Items are discovered dynamically from the built menu bar at runtime. Source-contract tests verify the three-tab structure, item discovery methods, and A11Y-4 modal dialog contract compliance. |
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
| SEC-4 | Document cwd safety for safe_subprocess | Security | S | Done | Callers cannot point cwd outside expected directories; documented and tested. `run_subprocess_safely` documents the contract and validates `cwd` is an existing directory (with `args`/executable checks); covered with SEC-15. |
| SEC-7 | Forget key command and shared-account note | Security | S | Todo | A command clears both secret stores and announces; limitation documented. |
| AI-1 | Streaming response UI | AI | M | Done | Ask Quill chat replies now stream incrementally: `generate_assistant_response_stream` (in `assistant_ai.py`) yields token deltas per provider, the `AIBackend.respond_stream` interface carries them to the UI, and the chat surface announces throttled, accessible progress through the assertive `set_status` aria-live region while building the transcript, then appends the final answer as one `append_message`. Because the external `AccessibleChatView` supports no in-place token mutation, streaming is realized as throttled status announcements plus a single final transcript append (so the screen reader hears progress without being flooded), with a clean non-streaming fallback. Covered by `tests/unit/core/ai/test_streaming.py` and `test_streaming_backend.py`. |
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
| QK-6b | Earcon sound design pass | QUILL key | M | Todo | A small, tasteful sound set is designed and user-tested with screen-reader users. |
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

---

## 15. Suggested release sequencing

1. Harden and gate (P0 security, accessibility, and continuous integration items). These protect users and unblock everything else. This is the 1.0 quality bar.
2. Land the QUILL key flagship (QK-1 through QK-5, NAV-1, NAV-4, SEL-1 through SEL-3) plus the primer and first tutorials. This is the story that makes QUILL memorable.
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

1. Corrupted method `_show_bw_onboarding` in [quill/ui/main_frame.py](quill/ui/main_frame.py#L19426) (lines 19426 to 19470). The method body contains copy-pasted "Insert Link" dialog code and references undefined names `selected_text` (line 19442), `dialog` (line 19463), and `profiles` (line 19470), plus assigns `display_text` and `url` that are never used. If this onboarding path is reached it raises `NameError`. The intended behavior is to confirm the BITS Whisperer rollout and then present a profile choice. This is a P0 crash. See BUG-1.
2. Four bare `wx.` calls that should be `self._wx.` in [quill/ui/main_frame.py](quill/ui/main_frame.py#L16983) at lines 16983, 17015, 17022, and 17042 (`wx.GetSingleChoice` and `wx.GetTextFromUser` in the heading-style prompts). Module-level `wx` is not imported; it is only stored as `self._wx` (assigned around line 683). These four call sites raise `NameError` at runtime when the heading-style flow executes. This is a P0 crash on a real user path. See BUG-2.
3. Undefined type annotation `VoiceOption` in [quill/ui/main_frame.py](quill/ui/main_frame.py#L12503) at lines 12503 and 12532. The symbol is imported as `ReadAloudVoiceOption` (around line 240) but the annotations use the bare name. With `from __future__ import annotations` this does not crash at call time, but it breaks `typing.get_type_hints` and static analysis. Fix by using the imported alias. See BUG-3.
4. Redefinition of `URLError` in [quill/ui/main_frame.py](quill/ui/main_frame.py#L339): imported first from `urllib.error` (line 15) and again from `quill.core.updates` (line 339). The second import shadows the first. Pick one source. See BUG-4.
5. Unchecked llama.cpp response shape in [quill/core/ai/llama_cpp_backend.py](quill/core/ai/llama_cpp_backend.py#L113) (lines 113 to 117): `out["choices"][0]["message"]["content"]` will raise `KeyError` or `IndexError` on a malformed or version-mismatched response. Add validation and a friendly error. See BUG-5.
6. XML element handling bug in [quill/io/structured.py](quill/io/structured.py#L614) (lines 614 and 615): a `list[str]` is assigned where an `Element` is expected and then passed to `str.join`, which mypy flags as an assignment and arg-type error. This is a real type-level defect in the DOCX path. See BUG-6.
7. Potential infinite loop in [quill/core/ai/assistant.py](quill/core/ai/assistant.py#L196) chunk splitting if `max_chars <= 0` is ever passed; add a guard. See BUG-7.

### 16.2 Security findings (verified)

Highest priority first. Most user files live under the trusted per-user app data directory, so the focus is tampered configuration, untrusted document inputs, and supply chain.

1. XML entity expansion (billion laughs) in document parsing. [quill/io/structured.py](quill/io/structured.py#L416) uses `ET.fromstring` for XML (line 416), DOCX `word/document.xml` (around line 408), and PPTX slide XML; [quill/io/pages.py](quill/io/pages.py#L107) parses PPTX XML similarly. None disable entity expansion, so a crafted file can cause memory and CPU exhaustion. Fix by switching to `defusedxml` or a hardened parser for all untrusted XML. P0 hardening. See SEC-10.
2. Decompression bombs in ZIP-based formats (DOCX, XLSX, ODT, PPTX) in [quill/io/structured.py](quill/io/structured.py#L604) (around lines 604, 683, 717). The archives are read without checking total uncompressed size. Add a cumulative size limit before reading entries. See SEC-11.
3. Subprocess executable paths sourced from settings. [quill/core/external_tools.py](quill/core/external_tools.py#L132) (around line 132) expands and runs configured executable paths (for example the DECtalk executable and other engines) without validating they live in a trusted location. If `settings.json` is tampered, this is arbitrary code execution. Validate against an allowlist or bundled or `shutil.which`-resolved path. This pairs with the earlier SEC-1. See SEC-1.
4. PATH hijacking via tool discovery in [quill/core/external_tools.py](quill/core/external_tools.py#L102) (around lines 102 to 115): `shutil.which` trusts the process PATH. Document the risk and prefer bundled tool paths where available. See SEC-12.
5. Update download without binary checksum or signature verification in [quill/core/updates.py](quill/core/updates.py#L249) (around line 249). The manifest signature is verified, but the downloaded asset itself is not checksum-verified before use. Verify a hash from the signed manifest against the downloaded bytes. This pairs with SEC-6. See SEC-6.
6. Incomplete secret redaction in diagnostics. [quill/core/diagnostics.py](quill/core/diagnostics.py#L20) (around lines 20 to 29) redacts `Authorization: Bearer` style tokens but misses patterns like `token:`, `password:`, and `NAME_KEY=` environment assignments. Broaden the redaction patterns so diagnostic bundles never leak partial secrets. See SEC-13.
7. Python sandbox environment and resource limits. [quill/core/python_sandbox.py](quill/core/python_sandbox.py#L143) inherits `PATH` into the subprocess (around line 143) and passes the user code as a base64 environment variable (around line 145), which can appear in a process list on shared systems; there is also no wall-clock or memory cap beyond the timeout. Add memory and CPU limits and avoid leaking the payload via the environment where possible. This refines SEC-9. See SEC-9, SEC-14.
8. `run_subprocess_safely` does not validate `cwd` or the executable in [quill/stability/safe_subprocess.py](quill/stability/safe_subprocess.py#L11) (around lines 11 to 26), and only catches `TimeoutExpired`, not `OSError` or `FileNotFoundError`. Add validation and wrap the missing exception. This refines SEC-4. See SEC-4, SEC-15.
9. Credential and Keychain input validation. [quill/platform/windows/credential_manager.py](quill/platform/windows/credential_manager.py#L73) does not validate `target_name` (around lines 73 to 99), and [quill/platform/macos/keychain.py](quill/platform/macos/keychain.py#L30) does not check the `security` subprocess return code in `set_secret` (around lines 30 to 50). Validate names against a safe pattern and check return codes. See SEC-16.
10. Shell integration registry command in [quill/platform/windows/shell_integration.py](quill/platform/windows/shell_integration.py#L35) is safe today because it derives from `launcher_command()`, but it is not escaped; document that it must never accept user input, or escape it if that changes. See SEC-17.

### 16.3 Correctness and robustness (non-crashing) findings

1. Windows atomic write is not guaranteed. [quill/core/storage.py](quill/core/storage.py#L16) uses temp file plus `replace` (around line 16). On Windows this can be a two-step operation under contention. Confirm `os.replace` semantics and, where needed, add retry-on-`PermissionError` so a concurrent reader cannot cause data loss. See CQ-19.
2. Version comparison ignores pre-release suffixes in [quill/core/updates.py](quill/core/updates.py#L136) (around line 136): `1.2.0-rc1` parses as `1.2.0`, so a release candidate sorts equal to the stable. Decide and document the intended ordering. See CQ-20.
3. Snippet placeholder regex does not handle nested braces in [quill/core/snippets.py](quill/core/snippets.py#L90) (around lines 90 to 120). Document the limitation or support nesting. See FEAT-5.
4. TOML parse has no guard in [quill/core/compliance.py](quill/core/compliance.py#L142) (around lines 142 to 160): a corrupted `pyproject.toml` aborts the dependency audit. Wrap and report. See CQ-21.
5. Credential empty-blob path in [quill/platform/windows/credential_manager.py](quill/platform/windows/credential_manager.py#L68) returns an empty secret indistinguishable from absent; log and document. See CQ-22.

### 16.4 Typing gaps in the strict zone (the 44 mypy errors)

The strict zone (`quill/core` and `quill/io`) currently reports 44 errors in 14 files. Representative clusters, all to be driven to zero and then kept green in continuous integration (see CQ-7):

- [quill/core/ipc.py](quill/core/ipc.py#L75): six errors from a `handle: object` annotation that is then used as a file object, plus `fcntl` attributes that are POSIX-only. The cross-platform branch on `os.name` is logically sound; annotate the handle as `IO[bytes]` or `Any` and guard the `fcntl` import for type-checkers. See TYPE-1.
- [quill/core/bw_speech.py](quill/core/bw_speech.py#L169): an `Any` returned where `float` is declared (line 169), missing parameter annotations (lines 223, 255), and the optional `faster_whisper` import. See TYPE-2.
- [quill/core/read_aloud.py](quill/core/read_aloud.py#L298): the `kokoro.KPipeline` attribute is not visible to mypy (line 298); fix the ignore code. See TYPE-3.
- [quill/core/dictation.py](quill/core/dictation.py#L10): `None` assigned to a `Callable`-typed name (line 10), and `recognize_whisper` and `recognize_vosk` on an untyped recognizer (lines 71, 78). See TYPE-4.
- [quill/io/pages.py](quill/io/pages.py#L73): missing return and parameter annotations (lines 73, 78, 91), untyped third-party `keynote_parser`, and an `Any` returned as `str` (line 238). See TYPE-5.
- [quill/io/structured.py](quill/io/structured.py#L173): untyped `openpyxl` import (line 173), a missing annotation (line 249), and the Element bug from 16.1 item 6 (lines 614, 615). See TYPE-6, BUG-6.
- [quill/core/ai/llama_cpp_backend.py](quill/core/ai/llama_cpp_backend.py#L65): missing annotations (lines 65, 71), a `None`-typed attribute later assigned a `Llama` (line 82), and an `Any` returned as `str` (line 118). See TYPE-7.
- [quill/core/ai/assistant.py](quill/core/ai/assistant.py#L130): missing annotations (lines 130, 200). See TYPE-8.

Where third-party stubs are missing (`openpyxl`, `faster_whisper`, `keynote_parser`, `kokoro`, `llama_cpp`), either install the available stub packages (for example `types-openpyxl`) or add precise per-import ignores with the correct error codes, and add Protocols for the SDK handles so the strict zone stays honest.

### 16.5 Performance findings (verified)

1. Spell-check wordlist loads synchronously (about 370,000 words) in [quill/core/spellcheck.py](quill/core/spellcheck.py#L100) (around lines 100 to 115), under the backend lock, stalling the first check. Background preload at startup. Pairs with PERF-1. See PERF-1.
2. Thesaurus index loads synchronously (a large data file) in [quill/core/thesaurus.py](quill/core/thesaurus.py#L52) (around lines 52 to 60) on first lookup. Background preload. Pairs with PERF-2. See PERF-2.
3. Read Aloud accumulates uncompressed audio arrays in memory in [quill/core/read_aloud.py](quill/core/read_aloud.py#L295) (around lines 295 to 325); stream to file for long documents, and cache identical sentences. Pairs with PERF-3. See PERF-3, PERF-10.
4. Spreadsheet reading loads entire worksheets into memory in [quill/io/structured.py](quill/io/structured.py#L193) (around lines 193 to 199); cap rows or stream. See PERF-11.
5. DOCX and PPTX load whole XML payloads and build full in-memory documents in [quill/io/structured.py](quill/io/structured.py#L604) (around lines 604 and 637); consider streaming and run these off the UI thread. See PERF-12.
6. PDF extraction materializes all pages in [quill/io/pdf.py](quill/io/pdf.py#L58) (around line 58); page-stream for very large PDFs. See PERF-13.
7. File search scans whole documents with no chunking in [quill/core/file_search.py](quill/core/file_search.py#L48) (around lines 48 to 70); stream large corpora. See PERF-14.

Concurrency note (correction): the spell-check wordlist cache, the enchant dictionary, the thesaurus index, and the watch-folder seen-set all already use `threading.Lock`. There is no missing lock there. The remaining work is documenting these invariants (CQ-17) and the Windows atomic-write behavior (CQ-19).

### 16.6 main_frame.py decomposition map (verified seams)

The 18,748-line [quill/ui/main_frame.py](quill/ui/main_frame.py) divides cleanly into roughly 22 subsystems. This map is the basis for CQ-1 (extract behind characterization tests, CQ-16):

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
- The accessibility conformance report at [docs/accessibility/acr-vpat.md](docs/accessibility/acr-vpat.md) is a template with placeholder evidence. It must be either filled in with a real 0.1.5 assessment or clearly labeled as not yet assessed. See DOC-9.
- The PRD at [docs/QUILL-PRD.md](docs/QUILL-PRD.md) mixes 1.0 specification with 0.1.5 reality; its header should state plainly that it specifies 1.0 and that 0.1.5 implements the subset marked in the roadmap mapping. See DOC-10.
- Documentation accessibility: the PRD uses emoji (check marks, warning and cross symbols, and others) and em-dashes throughout. Per the project's own markdown accessibility rules, replace emoji with text labels such as the words pass, warning, and error, and replace em-dashes. This applies to the source markdown so the generated HTML and EPUB inherit the fix. See DOC-11.
- The engineering docs (architecture, module-contracts, data-layout, runtime-model, diagnostics-runbook, quality-gates) are useful but skeletal (most under 50 lines). Expand them alongside the API reference. See DOC-12.
- User guide gaps: concrete AI setup examples (for example connecting to a local Ollama endpoint and an error matrix for 401 versus 403 versus 500), spell-check dictionary workflow, watch-folder walkthrough, and a troubleshooting section (Quick Nav key conflicts, garbled PDF extraction, autosave disk pressure). See DOC-13.

### 16.9 Test strategy findings (verified)

- Inventory: 118 test files. Core has the most coverage; the UI monolith, the IO format matrix, integration, performance, and accessibility content depth are the weak spots.
- The 18,748-line UI has only a handful of behavior tests. Before decomposition (CQ-1), add a characterization suite (CQ-16) covering tab lifecycle, undo and redo isolation, autosave and recovery, session restore, Quick Nav, find and replace, spell-check as you type, sticky notes, and macros.
- Add policy and attack-surface tests for the Python sandbox (allowed versus blocked modules, escape attempts, resource limits), spell-check tier fallback, Read Aloud backend fallback, and IO format smoke tests with real fixtures. See CQ-11, CQ-13, CQ-23, CQ-24.
- Performance tests are smoke-level only; add the budget suite (PERF-9).
- Scripts: the release orchestrator [scripts/release_readiness.py](scripts/release_readiness.py) runs ruff, pip-audit strict, pytest, docs build, and corpus verification, but there is no dependency lockfile and no timeouts on long commands; the Windows build pins an embeddable Python by a hardcoded hash that requires a code change to rotate. See CQ-25, CQ-26.

### 16.10 New backlog items from the verified audit

These extend the section 14 tracker. Priorities follow the same scheme. The confirmed latent crashes are P0.

#### P0 correctness bugs (new)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| BUG-1 | Repair corrupted `_show_bw_onboarding` | UI correctness | S | Done | Method no longer references undefined names; the BITS Whisperer onboarding presents the intended profile choice; a test exercises the path so it cannot regress. |
| BUG-2 | Fix four bare `wx.` calls in heading-style prompts | UI correctness | S | Done | Lines 16983, 17015, 17022, 17042 use `self._wx`; a test invokes the heading-style flow without `NameError`. |
| BUG-3 | Fix undefined `VoiceOption` annotations | UI correctness | S | Done | Lines 12503 and 12532 use the imported alias; ruff reports no F821 for these. |
| BUG-4 | Resolve `URLError` redefinition | UI correctness | S | Done | A single import source for `URLError`; ruff F811 cleared. |
| BUG-5 | Validate llama.cpp response shape | AI correctness | S | Done | Malformed responses produce a friendly error, not `KeyError` or `IndexError`; test included. |
| BUG-6 | Fix DOCX Element handling in structured reader | IO correctness | S | Done | Lines 614 and 615 type-check and behave correctly on a fixture DOCX; mypy clean for that path. |
| BUG-7 | Guard chunk splitting against non-positive size | AI correctness | S | Done | `max_chars <= 0` cannot cause an infinite loop; test included. |

#### P0 and P1 security (new and refined)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| SEC-10 | Harden all untrusted XML parsing | Security | M | Done | DOCX, XLSX, ODT, PPTX, and generic XML use a parser with entity expansion disabled; a billion-laughs fixture is rejected quickly; test included. |
| SEC-11 | Decompression-bomb limits for ZIP formats | Security | S | Done | A cumulative uncompressed-size cap aborts oversized archives with a clear message; test included. |
| SEC-12 | Document and reduce PATH-hijack exposure for tool discovery | Security | S | Todo | Bundled tool paths are preferred; the residual risk is documented. |
| SEC-13 | Broaden diagnostics secret redaction | Security | S | Done | Redaction covers token, password, and NAME_KEY assignment patterns; test asserts no secret leaks. |
| SEC-14 | Python sandbox memory and CPU limits | Security | M | Todo | Runaway transforms are terminated by memory and wall-clock limits; payload is not exposed via the environment where avoidable; test included. (Extends SEC-9.) |
| SEC-15 | safe_subprocess validates cwd and wraps OSError | Security | S | Done | `cwd` and executable are validated; `OSError` and `FileNotFoundError` are caught and surfaced clearly; test included. (Extends SEC-4.) Empty args and non-directory `cwd` raise `ValueError`; launch `OSError` is logged and re-raised with the tool name; five new tests in `tests/stability/test_stability.py`. |
| SEC-16 | Validate credential and keychain inputs | Security | S | Done | `target_name`, account, and service match a safe pattern; macOS `set_secret` checks the return code; tests included. A shared `validate_credential_identifier` (in `quill/platform/credential_validation.py`) rejects empty, over-long, control-character, and leading-dash identifiers; wired into the Windows credential manager and the macOS keychain; six new unit tests. |
| SEC-17 | Document or escape shell-integration command | Security | S | Todo | The registry command path is documented as internal-only or escaped if user input is ever accepted. |

#### P1 and P2 quality, typing, performance, IO, docs, tests (new)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| CQ-18 | Resolve ruff debt across quill, tests, scripts | Code quality | S | Done | All ruff findings across `quill`, `tests`, and `scripts` are fixed or explicitly justified. The final E501 backlog (43 lines: 27 in `main_frame.py`/`read_aloud.py` wrapped via implicit string concatenation, 16 inherent installer-script literals given a documented per-file ignore mirroring the script under test) is cleared, so `ruff check .` runs with no `--ignore E501` in CI or pre-commit. Format, full lint, and scoped mypy are clean; full suite 739 passed. |
| CQ-19 | Verify and harden atomic write on Windows | Code quality | S | Done | Writes use `os.replace` with retry on transient `PermissionError`; a test simulates contention. |
| CQ-20 | Define version pre-release ordering | Code quality | S | Done | Release-candidate ordering is intentional and documented; test covers it. `_version_tuple` now separates the pre-release suffix and ranks final > rc > beta > alpha for the same x.y.z; `tests/unit/core/test_updates.py` covers it. |
| CQ-21 | Guard TOML parsing in compliance | Code quality | S | Todo | A corrupted `pyproject.toml` produces a clear error, not a silent abort. |
| CQ-22 | Document credential empty-blob behavior | Code quality | S | Done | Empty-secret versus absent-credential is logged and documented. `load_generic_credential` now has a docstring spelling out the absent (`None`) versus empty-secret (`secret=""`) outcomes, debug-logs each path, and `tests/unit/platform/windows/test_credential_manager.py` asserts the distinction with a real round-trip on Windows. |
| CQ-23 | Python sandbox policy and attack-surface tests | Code quality | M | Todo | Tests cover allowed versus blocked modules, escape attempts, and resource limits. |
| CQ-24 | Read Aloud backend fallback tests | Code quality | M | Todo | Each backend and the fallback order is tested with stubs. |
| CQ-25 | Add dependency lockfile and CI timeouts | Build | M | Todo | Dependencies are pinned for release runs; long commands have timeouts. |
| CQ-26 | Make the embeddable Python hash configurable | Build | S | Todo | The Windows build reads the expected hash from config, not a code constant. |
| TYPE-1 | Type `ipc.py` handle and guard fcntl | Typing | S | Done | `mypy quill/core/ipc.py` reports no issues in the strict zone (typed file-lock handles, fcntl attr guards from CQ-7). |
| TYPE-2 | Annotate `bw_speech.py` | Typing | S | Done | `mypy quill/core/bw_speech.py` reports no issues in the strict zone. |
| TYPE-3 | Fix `read_aloud.py` kokoro ignore | Typing | S | Done | `mypy quill/core/read_aloud.py` reports no issues; the kokoro import is covered by the `ignore_missing_imports` override. |
| TYPE-4 | Annotate `dictation.py` recognizer | Typing | S | Done | `mypy quill/core/dictation.py` reports no issues in the strict zone. |
| TYPE-5 | Annotate `io/pages.py` | Typing | S | Done | `mypy quill/io/pages.py` reports no issues in the strict zone. |
| TYPE-6 | Annotate `io/structured.py` and add openpyxl stubs | Typing | S | Done | `mypy quill/io/structured.py` reports no issues; openpyxl is covered by the `ignore_missing_imports` override. |
| TYPE-7 | Type the llama.cpp backend handle | Typing | S | Done | `mypy quill/core/ai/llama_cpp_backend.py` reports no issues in the strict zone. |
| TYPE-8 | Annotate `ai/assistant.py` | Typing | S | Done | `mypy quill/core/ai/assistant.py` reports no issues in the strict zone. |
| PERF-10 | Stream and cache Read Aloud audio | Performance | M | Todo | Long-document synthesis does not spike memory; identical sentences are cached. |
| PERF-11 | Cap or stream spreadsheet reads | Performance | S | Todo | Large sheets do not exhaust memory; a row cap or streaming applies. |
| PERF-12 | Stream DOCX and PPTX off the UI thread | Performance | M | Todo | Large office files do not block the UI thread. |
| PERF-13 | Page-stream large PDFs | Performance | S | Todo | Very large PDFs extract without materializing all pages at once. |
| PERF-14 | Chunk file search over large corpora | Performance | S | Todo | Search streams large inputs without quadratic blowups. |
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
| GATE-1 | Pre-commit hooks for format, lint, and quick checks | Gates | S | Done | `.pre-commit-config.yaml` runs `ruff format` and `ruff check` (which includes the F821 undefined-name rule) on changed files, blocking failing commits locally; CONTRIBUTING documents one-time install. |
| GATE-2 | Pull-request CI pipeline | Gates | M | Done | `.github/workflows/pr-ci.yml` runs lint (`ruff format --check` and `ruff check` with E501 deferred to CQ-18), the full unit and accessibility suites with the coverage floor (GATE-5), and the MainFrame characterization snapshot (GATE-6). Together with Security CI (scoped typing GATE-3, banned patterns GATE-4, no-silent-network GATE-9, security checks GATE-8) and Accessibility CI (the a11y suite, docs-artifact diff, and dialog regressions), every required job runs on push and pull_request. Branch protection should require these checks before merge. |
| GATE-3 | Strict typing gate (scoped) | Gates | S | Done | `mypy quill\core quill\io` reports zero errors and is enforced by the `scoped-strict-typing` CI job (required for merge); third-party stub gaps are handled via `ignore_missing_imports` module overrides in pyproject; the whole-tree scan is never used. |
| GATE-4 | Banned-pattern gate | Gates | S | Done | `quill/tools/check_banned_patterns.py` (AST-based) fails on bare `wx.` in main_frame where `wx` is not locally bound (the BUG-2 class), on raw `ET.fromstring`/`etree.fromstring` outside `safe_xml` (the SEC-10 class), and on any removal of ruff's `F` rule group that enforces undefined-name (F821) and redefinition (F811) checks (the BUG-1/BUG-4 classes); a CI job runs it and tests cover the checker. The `except Exception` logged-cause sub-rule is tracked under CQ (it needs handler-body refactors across 26 sites) and is not claimed here. |
| GATE-5 | Test and coverage floor | Gates | M | Done | The `unit-tests` job in `pr-ci.yml` runs the full `tests/unit` and `tests/accessibility` suites and enforces `--cov-fail-under=70` on `quill.core` and `quill.io` (current total 72.28%). `pytest-cov` is in the dev extras. The floor is a hard gate that must rise, never fall, as coverage improves; raising it is the mechanism for ratcheting. |
| GATE-6 | Characterization gate for main_frame | Gates | M | Done | `quill/tools/ui_surface.py` extracts the public method surface of `MainFrame` via AST (no `wx` needed) and a committed snapshot fixture (`tests/unit/ui/fixtures/main_frame_public_surface.json`, 235 methods) is checked by `tests/unit/ui/test_main_frame_characterization.py`, run as the `characterization` CI job. Any add/remove/rename of a public method fails until the snapshot is regenerated deliberately with `python -m quill.tools.ui_surface --write`, keeping the planned decomposition behavior-preserving. |
| GATE-7 | Accessibility gate on every PR | Gates | M | Done | Accessibility CI runs on every pull request: the keyboard-trap and focus-order checks (`RegionTracker` in `tests/unit/core/test_a11y_regions.py`), the screen-reader announcement transcript suite (`tests/accessibility`), the dialog escape/default contract regressions, and the new announcement-grammar conformance suite (`tests/accessibility/test_announcement_grammar.py`) that asserts the A11Y-1 grammar stays well-formed. Contrast handling is covered by the high-contrast platform tests. |
| GATE-8 | Security scan gate | Gates | M | Done | Security CI's `security-checks` job runs the hardened-XML / banned-pattern check (`check_banned_patterns`) and the static security invariant suites: verified TLS (`test_net_tls`), secret redaction / no-plaintext-secret diagnostics (`test_diagnostics`), XML-bomb hardening (`test_safe_xml`), zip decompression caps (`test_safe_archive`), the Python sandbox policy (`test_python_sandbox`), and the OCR argument allowlist (`test_ocr`). Dependency vulnerability auditing (`pip-audit --strict`) and the SBOM run in the adjacent job. A full third-party static analyzer (bandit) sweep is intentionally not claimed yet because the tree has 52 unreviewed `S`-rule findings; adopting it is tracked under the remaining SEC items. |
| GATE-9 | No-silent-network gate | Gates | S | Done | `quill/tools/network_egress_audit.py` inventories every outbound call site (`urlopen`/`urlretrieve`) in the package via AST; a required CI test fails when a new egress point appears without a reviewed rationale describing the user action or explicit consent that triggers it. All eight current sites are documented (Open from URL prompt, optional DECTALK/model downloads with progress, consented update checks, user-initiated model discovery). The runtime provider/model/scope-shown assertion is coupled to the AI provider wiring (AI-13) and is called out there rather than overclaimed here. |
| GATE-10 | Performance budget gate | Gates | M | Todo | Startup, first spell-check, first thesaurus lookup, large-document Quick Nav, and Read Aloud start stay within published budgets; regressions fail the build. |
| GATE-11 | Module-size budget gate | Gates | S | Todo | A ratcheting size budget prevents new growth in the largest files and decreases as extraction proceeds. |
| GATE-12 | Strengthen AI assistant repository guidance | Gates | S | Todo | copilot-instructions and a new AGENTS.md describe architecture, strict zone, scoped mypy, accessibility, no-silent-network, the audit footguns, and the definition of done; a check keeps them current. |
| GATE-13 | Machine-checked definition of done | Gates | S | Todo | A short done checklist (accessible, typed, tested, lint-clean, no silent network, docs regenerated) is documented and mirrored by the gates. |
| GATE-14 | CODEOWNERS and required review for high-risk areas | Gates | S | Todo | Security, sandbox, AI boundary, and secret-store changes require a human review even when AI-authored. |

##### AI and agent features

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| AI-6 | Graceful AI degradation and clear status | AI | S | Done | A wx-free `quill/core/ai/availability.py` produces a single source of truth for AI readiness: `describe_availability(feature_name, ...)` returns a structured result with a clear, announceable message that names the feature and distinguishes "AI is turned off", "a model is unavailable", and "a key is missing" (with a `needs_key` flag), and it never blocks the editor (the editor stays fully usable when AI is unavailable). Covered by `tests/unit/core/ai/test_availability.py` (disabled master switch, ready, reason passthrough, missing-key detection, feature-name weaving, never-blocks-editor). |
| AI-7 | Preview-and-apply AI diffs reviewable by ear | AI | L | Done | A wx-free diff engine (`quill/core/ai/diff_review.py`) builds a navigable added/removed/changed diff from original and revised text via `SequenceMatcher`: each `DiffHunk` has a screen-reader phrase (`describe()`, e.g. "Added 1 line at line 2.") and line-by-line `detail_lines()` marking removed/added (and blank) lines, and `DiffReview.apply(accepted)` rebuilds the text honoring a partial-accept set while leaving unchanged segments verbatim, with `accept_all`/`reject_all` and a `summary()`. The accessible `DiffReviewDialog` (`quill/ui/assistant_tools.py`) presents the hunks as a stock `wx.CheckListBox` (all pre-checked) with a read-only details pane, plus Apply Checked / Accept All / Reject All / Close; applying replaces the selection as **one undo step** and announces the count. It is reachable from Ask Quill chat: approving an AI "replace" whose proposed text differs from the selection opens the review (`MainFrame.open_ai_diff_review`). Covered by `tests/unit/core/ai/test_diff_review.py` (engine, partial apply, round-trip) and `tests/unit/ui/test_assistant_tools_dialog_callbacks.py` (apply-all, partial apply, reject-all). |
| AI-8 | Context-aware AI actions | AI | M | Todo | Offered actions adapt to cursor or selection context and document type and are reachable from the QUILL key. |
| AI-9 | Prompt library and recipes | AI | M | Todo | Prompts and recipes can be saved, named, organized, shared, and picked with live preview. |
| AI-10 | Style training and explainable edits | AI | M | Todo | The assistant can match a user's voice and explain why it made each change, consistently across a document. |
| AI-11 | Local grounded answers over user content | AI | L | Todo | Optional local retrieval over open documents and the sticky-notes vault answers questions with citations and no network without consent. |
| AI-12 | AI evaluation harness | AI | M | Todo | A repeatable task set with quality checks measures AI and agent output and catches regressions before release. |
| AGENT-1 | Accessibility agent (make this document accessible) | AI | L | In progress | A consented, announced, reversible plan audits and fixes structure, alt text, link text, and plain language, then re-audits and reports; every step is a reviewable diff and a single undo. The deterministic engine landed in `quill/core/accessibility_agent.py` (wx-free, strict-typed) on top of the in-repo `glow.py` + `plain_language.py` primitives: `build_plan` audits structure (markdown heading spacing, heading-jump, html missing `lang`), alt text, link text, and plain language and returns an ordered plan of per-step-consented `AgentStep`s; `apply_plan` applies only the accepted auto-fixable steps and re-audits, returning a run report. The `AccessibilityAgentDialog` (Tools > AI > Make This Document Accessible..., command `tools.ai_accessibility_agent`) shows each step as an accessible `wx.CheckListBox` with a before/after details pane; auto-fixable steps are pre-checked, advisory steps are listed for review. Applying replaces the whole editor buffer as **one undo** and opens a re-audit report tab; the summary is announced. **Remaining (honest):** structure and plain language are auto-fixed, but alt-text and link-text are advisory-only (flagged for human authoring, not auto-written) — AI-assisted alt-text/link-text authoring and richer structure repair are still to come, so this row stays In progress. |
| AGENT-2 | Cleanup agent | AI | M | Todo | A messy import is cleaned through announced, reversible recipes ending in well-structured text. |
| AGENT-3 | Review agent | AI | M | Todo | A spoken, skimmable review reports structure, readability, accessibility, and consistency with one-key jumps to issues. |
| AGENT-4 | Safe local agent runtime | AI | L | Todo | The agent plans and takes one consented step at a time, calls only an in-app tool allowlist, never the network without consent, has a hard step cap and loop guard, and announces every step; reuses the sandbox and stability layers. |

##### AI provider review (from section 18.4 and 18.5)

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| AI-13 | Wire configured providers to a real chat backend | AI | L | Done | `generate_assistant_response` in `assistant_ai.py` routes generation to the selected provider (OpenAI/OpenRouter/custom/Azure/ollama_cloud via chat-completions, Claude via messages, Gemini via generateContent, local Ollama via /api/chat); `ProviderChatBackend` adapts it to the `AIBackend` interface, and `make_default_backend` returns it whenever a saved connection exists and is not Off and reports available, so selecting a cloud or Ollama provider actually changes who responds. Reuses the endpoint-security check, verified TLS, retry/backoff, and error taxonomy; new egress registered in the GATE-9 audit. Verified by mocked-network tests. |
| AI-14 | Streaming responses across providers | AI | M | Done | `generate_assistant_response_stream` parses each wired provider's streaming format (OpenAI/OpenRouter/custom/Azure and ollama_cloud chat-completions SSE, Claude content-block SSE, Gemini generateContent SSE, local Ollama NDJSON) into token deltas via `parse_stream_event` + `iter_stream_text`, reusing the same endpoint-security, verified-TLS, and error taxonomy as AI-13. `ProviderChatBackend.respond_stream` surfaces the deltas to the UI for throttled accessible announcements (AI-1); on a pre-stream failure it degrades cleanly to the blocking `generate_assistant_response`, and a mid-stream failure raises without emitting a duplicate. Base `AIBackend.respond_stream` emits the full reply once as a fallback. Verified by mocked-network tests in `tests/unit/core/ai/test_streaming.py` and `test_streaming_backend.py`. |
| AI-15 | Provider-specific correctness | AI | M | Done | Azure targets a deployment in the URL (`/openai/deployments/<deploy>/chat/completions?api-version=...`) and omits the model from the body; Claude sends the required max_tokens; Gemini uses its own contents/generateContent request and parser; OpenRouter sends HTTP-Referer and X-Title attribution headers; Ollama chat uses /api/chat with stream=false. Each is covered by a contract test. |
| AI-16 | Per-provider contract tests | AI | M | Done | `test_provider_chat.py` covers each provider's request shape (endpoint, body, headers) and response parsing with mocked request/response and no live network; a provider schema change fails the build instead of silently breaking generation. |
| AI-17 | Extend the error taxonomy to the chat path | AI | S | Done | The chat path (`_post_chat`/`generate_assistant_response`) reuses the same auth/forbidden/rate-limited/warming-up/timeout/unreachable categories and cause-specific, screen-reader-friendly messages as model listing, with the same bounded warm-up retry; verified by 401/503/URLError tests. |
| AI-18 | GitHub Copilot SDK as an optional post-1.0 provider | AI | M | Todo | If pursued, Copilot is an optional, clearly labeled provider behind the AIBackend boundary with an accessible OAuth device-flow sign-in, gated and never default; documented rationale (section 18.5) is honored. Not required for 1.0. |
| AI-19 | Accessible subscription sign-in (no pasted API key) | AI | M | In progress | Derived from the Pi research (see `pi.md`). Add a guided, fully keyboard-and-screen-reader login that lets a user authenticate with an existing provider subscription via an interactive flow (for example OAuth device flow) instead of pasting an unreadable API key, alongside the current key path. The most user-facing accessibility win from Pi: "sign in with the subscription you already have" rather than "paste a 51-character secret you cannot see." Credentials in DPAPI, explicit consent, no silent network, registered in the GATE-9 egress audit. Sits behind the AIBackend boundary (AI-13) and reuses the connection error taxonomy (AI-17). **Delivered:** `quill/core/ai/device_login.py` is a complete, wx-free, strict-typed OAuth 2.0 Device Authorization Grant (RFC 8628) state machine. `request_device_code` starts the flow; `announce_device_code` speaks the screen-reader instruction ("open <url> in your browser and enter the code WDJB-MJHT; this code expires in about 15 minutes."); `poll_once` classifies the provider's reply into pending / slow_down / authorized / denied / expired / error; `run_device_login` drives the full polling loop honoring the provider `interval`, backing off on `slow_down`, and stopping at `expires_in`, returning the terminal result; `describe_login_result` speaks the outcome. Every network exchange is an **injected** `poster`, so the engine adds no new `urlopen`/`urlretrieve` site to the GATE-9 egress inventory and is fully tested without a live endpoint (7 tests covering parse, state classification, success-after-pending, slow-down back-off, deadline expiry, denial, and the spoken announcements). ruff + strict mypy clean. **In progress (honest):** the flow state machine is complete and tested, but the real HTTPS poster, the DPAPI token storage, the consent surface, and the AIBackend (AI-13) wiring are not yet built, so no live subscription sign-in ships and this row stays In progress. |
| AI-20 | Branchable, resumable AI writing sessions | AI | L | Done | Derived from Pi's session tree (see `pi.md`). Elevate the existing assistant transcript and Save/Open Session into a durable, navigable history: auto-saved sessions, continue-most-recent, browse-past, and fork/branch so a writer can try two rewrites of a section without losing state, then compare and resume. The surface is an accessible list or tree of branches, each announced, with one-key jump and compare; no redraw-heavy TUI. Honors FeatureManager (FLAG-1) and the shared announcement grammar (A11Y-1). **Delivered:** `quill/core/ai/sessions.py` is a complete, wx-free, strict-typed session-*tree* engine. Turns form a tree by `parent_id`; the active branch tip is `current_turn_id`. `append_turn` adds a child of the tip and advances it; `branch_from`/`resume` move the tip back to an earlier turn so the next append creates a *sibling* branch — both rewrites are kept, never lost. `path_to`/`current_path` give the conversation along any branch; `branch_tips`/`branch_points` enumerate the leaves and forks; `compare_branches` finds the common ancestor and the turns unique to each side; `relabel_turn` names a branch for navigation. Durable JSON persistence (`save_session`/`load_session`/`delete_session`/`list_sessions`/`most_recent_session`) writes atomically under `<data>/ai-sessions`, supports continue-most-recent (newest `updated_at` first) and browse-past, and rejects unsafe session ids (path-traversal guard). Screen-reader summaries (`summarize_session`, `describe_branches`) announce turn/branch counts and mark the current branch. Tested: linear append, sibling branching without state loss, branch comparison/fork detection, resume, relabel, spoken summaries, role validation, save/load round-trip, list ordering + continue-most-recent, and the unsafe-id guard (10 tests). **In progress (honest):** the engine and persistence are complete and tested, but the accessible branch-browser/compare UI surface and the wiring that records the live assistant transcript into the tree are not yet built, so this row stays In progress. | **UI wired:** `quill/ui/session_browser.py` (`SessionBrowserDialog`) is the accessible surface over the engine — a stock `wx.ListBox` named "Session branches" listing every branch tip (one announced row per branch, the active branch pre-selected and marked "(current)" via the new wx-free `branch_rows` helper), a "Jump to branch" button that calls `resume` + `save_session` and announces the move, and a "Compare with current" button that fills a read-only multiline `wx.TextCtrl` from the new wx-free `format_comparison` helper (common ancestor + turns unique to each side, as pageable text). It honors the A11Y-4 dialog contract (`apply_modal_ids`/`show_modal_dialog`). Reachable from the AI menu ("Session &Branches...", `tools.ai_session_browser`) via `MainFrame.open_ai_session_browser`, which loads `most_recent_session` and reports gracefully when no sessions exist. Tested: two wx-free engine tests (current-branch marking, pageable comparison text) plus a five-assertion source-contract test for the dialog wiring, with the public-surface fixture and dialog-contract guard updated. |
| AI-21 | Durable per-document writing instructions the assistant cannot drop | AI | M | Done | `quill/core/ai/writing_instructions.py` adds user-owned, editable plain-Markdown instruction files at two scopes: a global/project file (`<app data>/ai/writing-instructions.md`) and a per-document sidecar (`<document>.quill-instructions.md`), both re-read live on every generation (no caching). The Assistant gained `set_instructions_preamble`, and `_wrap` now leads with the pinned rules, then the trained style, then the task; `instructions_preamble` frames the rules as mandatory but forbids using them to shorten or skip the task. The Tools/AI menu and `tools.writing_instructions` command open the global file in QUILL's own editor (creating a friendly template on first use), so it is visible and user-controlled, never a hidden prompt. Pairs with Train Writing Style: train the voice, pin the rules. Tested: path resolution, save/load per scope, live reload, preamble framing, and the instructions-then-style-then-prompt ordering. |
| AI-22 | Mid-task model speed/cost tiers | AI | S | Done | Derived from Pi's mid-session model switching (see `pi.md`). Let the user pick a fast or local model for quick edits and a stronger model for a careful rewrite, switchable mid-task with an announced change, surfaced in the existing AI model panel. Local-first: the fast tier can be an on-device model. **Delivered:** `quill/core/ai/model_tiers.py` is a complete, wx-free, strict-typed tier engine over the existing `model_manager` registry. Two named tiers — `Fast` (default `llama-3.2-1b`, on-device, for quick edits) and `Strong` (default `phi-4-mini`, for careful rewrites) — each map to a model id (or `auto` = the RAM recommendation). `set_active_tier` switches tiers mid-task and persists the choice; `assign_model_to_tier` lets a user re-point either tier at any registered model; `resolve_tier_spec` resolves the active tier to a concrete `ModelSpec` via `model_manager`; `announce_tier_change`/`describe_tier` produce A11Y-1-style spoken announcements ("Switched to the Fast tier (Llama 3.2 1B Instruct) for quick edits."). Tier assignments and the active tier persist atomically under `<app data>/ai/model-tiers.json`. Tested: defaults, mid-task switch persistence, per-tier reassignment, `auto` assignment, unknown-tier/unknown-model rejection, `auto`→spec resolution, and the spoken announcements (8 tests); ruff + strict mypy clean. **UI wired:** the AI model panel (`quill/ui/ai_model_panel.py`) now surfaces a "Speed tier" section — an accessible **Active speed tier** picker (Fast/Strong) plus a per-tier model assignment control — that switches the active tier mid-task through `switch_active_tier` (a thin wx-free orchestration helper that persists the change and returns the A11Y-1 announcement) and speaks the result, and re-points either tier at any registered model via `assign_model_to_tier`. The `switch_active_tier` helper is covered by a behavior test (switch + idempotent re-select announcements), and the panel wiring is covered by a source-contract test (engine imports, tier section, announced switch, per-tier assignment). Done. |
| AI-23 | Graceful context compaction for long sessions | AI | M | Done | `quill/core/ai/compaction.py` adds a pure, tested compaction engine: `estimate_tokens`/`conversation_tokens` (tokenizer-free conservative heuristic), `needs_compaction`, and `compact_conversation`, which keeps the most recent turns verbatim and replaces the older head with one clearly labelled `Summary` turn produced by a caller-supplied summarizer (the on-device assistant), returning a `CompactionResult` with a `compacted` flag the caller uses to announce the condensation rather than silently truncating. A summarizer that fails or returns blank leaves the thread intact (never loses content). Tests cover the token heuristic, the over-budget compaction, recent-turn preservation, the too-few-turns and failed/blank-summary no-op paths. |
| AI-24 | Language-agnostic stdio/JSON boundary for external engines | AI | M | Done | Derived from Pi's RPC/JSON integration design (see `pi.md`), and the architectural keystone for adopting any non-Python engine from a Python app. Define one consented, off-by-default pattern for QUILL to drive an external engine over a local subprocess speaking JSONL or MCP on stdio — spawned on demand, covered by the GATE-9 egress audit, with a clean unavailable path. This is the same boundary the Accessibility Agents work (`aa.md`) needs for its optional Node backend, so building it once de-risks both. Adopt the pattern, not the package. **Delivered:** `quill/core/ai/external_engine.py` is a complete, wx-free, strict-typed boundary. A master consent switch and a per-engine `enabled` flag are both **off by default** and persist under `<app data>/ai/external-engines.json`. `probe_engine` decides availability with a human reason (master off, engine off, no command, missing program); `run_request` spawns the configured program on demand, writes one JSONL request line to stdin, reads one JSONL response from stdout, and maps every ordinary failure (disabled, missing executable, non-zero exit, invalid JSON, timeout, engine-reported `error`) to a structured `EngineResult` with `ok`/`unavailable`/`error` — it never raises for the expected failure modes, giving callers the required clean unavailable path. The subprocess runner is injectable, so the boundary is fully tested (10 tests) without spawning real processes. The boundary is local-only (pipes, no sockets); QUILL opens no network connection, so it adds no new site to the GATE-9 `urlopen`/`urlretrieve` egress inventory, and the off-by-default consent gate is the structural control. ruff + strict mypy clean. **UI wired:** the consent and command configuration now live in the registry-driven Settings home (no separate dialog): the AI page carries an off-by-default "Allow external engines" master checkbox plus an "External engine name"/"External engine command" pair and an "Enable this external engine" checkbox, persisted on OK via `set_external_engines_enabled` and `configure_engine` (a wx-free helper that turns the free-text command box into a token tuple with `shlex` and saves an `EngineConfig`). `list_engine_ids` and `configure_engine` are strict-typed and covered by core tests; the Settings integration is pinned by source-contract tests asserting the master/command controls and the persist-on-OK wiring, and the dialog-contract and public-surface guards stay green. No concrete external engine ships by design (adopt the pattern, not the package), but the consent gate, persistence, runtime boundary, and the Settings UI to enable an engine and configure its command are all complete and tested, so this row is Done. |


---

## Part IV: The combined accessibility suite (GLOW and BITS Whisperer)

QUILL does not exist alone. It sits beside two sibling products built for the same audience, and there is a rare opportunity to fuse them into a single, coherent, best-in-class accessibility suite rather than three overlapping apps. This part defines how to bring GLOW (document accessibility audit and fix) and BITS Whisperer (audio transcription) into QUILL as first-class, deeply integrated capabilities, what to keep, what to drop, and what shared foundation makes it durable.

The strategic case: all three products share a mission (do excellent work for blind and low-vision people), a stack (Python and wxPython, accessibility-first, local-first), and an audience. Three separate apps mean three menus to learn, three update mechanisms, three places for a document to live, and triplicated engineering. One suite, with QUILL as the writing and editing home, GLOW as its accessibility engine, and BITS Whisperer as its transcription engine, is simpler for users and far more powerful: write, transcribe, audit, fix, and publish in one place, by keyboard and voice, with one set of conventions.

### 19. GLOW integration: make QUILL accessibility-native

> The full, step-by-step Tier 3 execution plan for this section — the three-repo
> layout (`s:\code\quill-glow-core`, `s:\code\glow`, and QUILL), the ordered
> GLOW-0 through GLOW-7 work, the definition of done, and the risk register —
> lives in [glow.md](glow.md) at the repo root. This section is the narrative;
> [glow.md](glow.md) is the build sheet, and the two must stay in step.

QUILL already contains `quill/core/glow.py`, a text-level GLOW audit and fix surface (generic link text, plain-language lint, audit and fix reports for the selection or document) wired to commands such as `tools.glow_fix_document` and `tools.glow_fix_selection`. Separately, GLOW is a full document-accessibility platform (a VS Code agent toolkit, a desktop app, and a web app) enforcing ACB Large Print, APH, WCAG 2.2 AA, and Microsoft Accessibility Checker rules across Word, Excel, PowerPoint, PDF, EPUB, HTML, and Markdown, with audit, auto-fix, template generation, and conversion. The shared library `quill-glow-core` already exposes a stable host-facing API (`audit_by_extension`, `fix_by_extension`, `convert_to_markdown`, `get_component_versions`) with a dispatch core, a safe no-op fallback, and a GLOW backend adapter.

The plan: adopt `quill-glow-core` as the single shared engine so QUILL's in-editor GLOW and the GLOW desktop and web apps audit and fix by exactly the same rules, with one place to improve them.

Where the code lives (for the implementer): the shared engine is the `quill-glow-core` repo at `s:\code\quill-glow-core` (package `quill_glow_core`, public API in `src/quill_glow_core/services.py`: `configure_default_services`, `audit_by_extension`, `fix_by_extension`, `convert_to_markdown`, `get_component_versions`, plus `from_glow_backend`, which bridges to the canonical engine `acb_large_print_core`). The full GLOW platform repo is `s:\code\glow`. Note: `s:\code\glow-7.0.0` is a stale snapshot and should be ignored; do not read or modify it. Tier 3 therefore spans up to three repos — QUILL (this repo, the presentation layer), `quill-glow-core` (the shared contract), and `glow` (the rule engine) — so changes must be coordinated, each committed in its own repo, and the shared API kept stable.

Cross-repo prerequisite for Tier 3 step 1: the `s:\code\glow` repo currently has failing CI/tests. Before QUILL depends on `quill-glow-core` (GLOW-1), the `glow` repo's failures must be diagnosed and fixed and its suite brought green, so QUILL builds on a stable engine rather than inheriting breakage. This is the first task of GLOW-1 and is tracked in the GLOW-1 acceptance criteria.

- Depend on the shared core. Replace QUILL's bespoke text-level checks with calls into `quill-glow-core` (`configure_default_services` then `audit_by_extension` and `fix_by_extension`), keeping QUILL's friendly in-editor reports as the presentation layer. When the GLOW backend is present, QUILL gets the full ACB, APH, WCAG, and MSAC rule sets; when it is absent, the safe no-op fallback keeps QUILL fully functional. See GLOW-1.
- Audit and fix by structure, not just text. Today QUILL audits plain text, Markdown, and HTML. Extend it through the shared core to audit and fix the structured formats QUILL already reads (DOCX, PPTX, XLSX, PDF, EPUB) so a user can open a real document and run a full accessibility audit in place. See GLOW-2, IO-1.
- An in-editor accessibility report that reads beautifully. Present GLOW findings as a navigable, screen-reader-pageable list grouped by severity, each with a one-key jump to the location, a plain-language explanation, and (where fixable) a reviewable apply-and-undo. This is the same surface the Accessibility agent (AGENT-1) drives. See GLOW-3, AGENT-1, AI-7.
- Standards profiles in QUILL. Surface GLOW's profiles (ACB 2025 Baseline, APH Submission, Combined Strict) as a setting so a user can choose the rigor that fits their work, with the active profile shown in every report for traceable evidence. See GLOW-4, SET-1.
- One-key publish to accessible output. Reuse GLOW's conversion chain (MarkItDown plus Pandoc, with LibreOffice-assisted pre-conversion and PyMuPDF table preservation) so QUILL can export clean, accessible Word, HTML, EPUB, and PDF with announced results. This realizes FEAT-17 on a proven engine. See GLOW-5, FEAT-17.
- Shared versioning and telemetry. Use `get_component_versions` and the startup telemetry so QUILL can show which accessibility engine and rule version is active, keeping the honesty principle. See GLOW-6.

What to keep lightweight in QUILL: QUILL should not absorb GLOW's web app, its branding-profile deployment machinery, or its template-generation server flows. QUILL consumes the shared core; the GLOW desktop and web apps remain the heavyweight authoring and batch surfaces. The boundary is clean: shared rules and fixers in `quill-glow-core`, three thin presentation layers on top.

### 20. BITS Whisperer integration: transcription becomes a QUILL superpower

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

These extend the section 14 tracker. The GLOW family (GLOW-1 through GLOW-7) has a
dedicated execution plan in [glow.md](glow.md); keep both in step when any GLOW
item changes scope or status.

| ID | Item | Area | Size | Status | Acceptance criteria |
| --- | --- | --- | --- | --- | --- |
| GLOW-1 | Adopt quill-glow-core as the shared engine | Suite | M | Todo | Step 1: in `s:\code\glow`, the consumed desktop core (`acb_large_print` / `acb_large_print_core`, the target of `from_glow_backend`) is already green (308 tests); fix the failing Flask web suite (`acb_large_print_web`: the `/guide/` content string, branding injection, and form-POST tests) and reconcile the version sweep (VERSION 8.0.0 vs README vs TODO.md), committing in the `glow` repo so the whole engine is green. Step 2: QUILL audits and fixes via `quill-glow-core` (`s:\code\quill-glow-core`) behind a new optional extra `glow = ["quill-glow-core[glow]"]`, using the GLOW backend when present and the safe `NoOpCoreServices` fallback when absent; `quill/core/glow.py` becomes a thin presentation shim plus a `_glow_finding_to_quill` adapter (severity map critical/high -> error, carry `score`/`grade`/ACB `metadata`); in-editor reports unchanged for users; tests cover both backend and fallback paths. Coordinate the three repos and keep the shared API stable. Ignore the stale `s:\code\glow-7.0.0` snapshot. |
| GLOW-2 | Audit and fix structured formats in-editor | Suite | L | Todo | DOCX, PPTX, XLSX, PDF, and EPUB can be audited (and fixed where supported) in place through the shared core. |
| GLOW-3 | Navigable in-editor accessibility report | Suite | M | Todo | Findings are a screen-reader-pageable list grouped by severity with one-key jump, plain-language explanation, and reviewable apply-and-undo. |
| GLOW-4 | Standards profiles setting | Suite | S | Todo | ACB Baseline, APH Submission, and Combined Strict are selectable; the active profile shows in every report. |
| GLOW-5 | Accessible publish via the GLOW conversion chain | Suite | M | Todo | One-key export to accessible Word, HTML, EPUB, and PDF using the shared conversion chain, with announced results. |
| GLOW-6 | Show active accessibility engine and rule version | Suite | S | Todo | QUILL displays the GLOW engine and rule version via `get_component_versions` and startup telemetry, surfaced in `diagnostics.py` and the About dialog. |
| GLOW-7 | Consent gate for GLOW optional AI and network features | Suite | S | Todo | GLOW's optional networked features (AI alt-text generation, Presidio PII redaction, WCAG language processing) are OFF by default and, when a user enables them, are gated by an explicit per-action consent prompt with visible progress and outcome, honoring QUILL's no-silent-network rule and the GATE-9 egress audit. A test asserts the defaults are off and no GLOW path performs a silent outbound call. |
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
- Navigation and selection by structure: NAV-1, NAV-4 (go-to-anything), NAV-5, SEL-1 through SEL-3. Value: moving and selecting by meaning, not by guesswork. Outcome: real documents become navigable by ear at speed.
- Bring visuals into text with OCR: OCR-1 through OCR-5. Value: a blind writer pulls text out of an image, a screenshot, a clipboard grab, or a screen region and hears it land in the document, working offline by default through the built-in Windows OCR engine with no install, and through Tesseract when the user opts in during onboarding. Outcome: inaccessible images stop being dead ends, and the same engine plugs into Watch Profiles so whole folders of images become readable documents automatically.
- The Accessibility agent and trustworthy AI editing: AGENT-1, AI-7 (diffs reviewable by ear), AI-1 (streaming), AI-6 (graceful degradation). Value: "make this document accessible," done step by step, reversibly, by keyboard and voice. Outcome: a category-defining capability that embodies the mission.
- Make the configured AI providers actually work: AI-13 (the headline fix), AI-15 (provider correctness), AI-17 (chat-path error messages), then AI-14 (streaming) and AI-16 (contract tests). Value: when a user selects OpenAI, OpenRouter, Gemini, Azure, Ollama, or Claude, that provider is the one that responds, instead of silently falling back to the local model. Outcome: the provider boundary becomes trustworthy and the QUILL AI surface is honest end to end. This is both a QUILL feature and AI hardening, so it sits here with the flagship.
- Deep, tunable settings: SET-1 through SET-7. Value: users shape QUILL precisely to their hands and ears. Outcome: the product meets people exactly where they are.
- Feature profiles and per-feature control: FLAG-3 and FLAG-4. Value: users adopt whole sets of features at once (Essential through Full QUILL) or toggle anything individually, with dependencies resolved and announced, and can export or pre-configure the whole set. Outcome: the feature-flag promise from Tier 1 becomes a rich, accessible control surface, so people run exactly the QUILL they want.
- Trustworthy external-change handling: FEAT-19. Value: a file edited by another program is never silently lost or silently overwritten; clean files reload in place without losing the cursor, and conflicts get a clear spoken choice. Outcome: QUILL feels safe and alive when documents change underneath it, which matters most to a screen-reader user who cannot see a flicker.
- Watch Profiles, the accessible automation hub: WATCH-1 through WATCH-7 (many folders, each bound to its own action, all feeding one durable, monitorable queue with an accessible Watch Queue Monitor in Help). Value: a blind writer drops work into folders and listens to a calm queue process it — open, convert, move, run a macro or Python transform, or a consented AI action — instead of shepherding every file by hand. Outcome: a productivity-and-accessibility superpower that unifies QUILL's distinctive engines behind one learnable model (a folder, an action, a queue), and a quiet differentiator no mainstream editor offers. The GLOW and transcription actions (WATCH-8, WATCH-9) plug into the same registry as their tiers land.
- Dialogs that never trap or go silent: DLG-1, enforced by the A11Y-4 contract guard. Value: the safe submit-once forms (find-in-files, Status Bar Layout, the voice chooser, Watch Folder Settings, the YAML editor, General Preferences) move onto the one shared accessible `show_web_form` surface, and a machine-enforced guard makes the construction bug class behind the find-in-files Cancel trap (#84) and the bookmark dialogs (#85) un-regressable. Outcome: every dialog has a reliable Escape, an explicit default, and returns focus to the editor, and new dialogs are correct by construction. This executes the form wave of issue #73; the interactive AI-tool dialogs are converted individually and screen-reader-verified later (DLG-2, Tier 4), never batch-rewritten.

Why second: this is where user love is won. It comes right after the protections so the flagship is built on a safe, gated base.

#### Tier 3: GLOW, the accessibility engine inside QUILL (deferred to QUILL 2.0)

> Status (2026-06-02): deferred to **QUILL 2.0**. GLOW remains the second strategic priority and the design below stands, but it is no longer part of the 1.0 milestone; it ships as a 2.0 headline once the shared `quill-glow-core` engine is green. The axe-core / Accessibility Agents workstream (AX-A through AX-F) depends on this engine and is deferred with it.

Per the build directive, GLOW comes before transcription: it deepens QUILL's core mission of accessible documents and reuses a proven engine.

- GLOW as the in-app accessibility engine: GLOW-1 through GLOW-5. Step 1 of GLOW-1 is a cross-repo prerequisite: fix the failing CI in the `s:\code\glow` engine repo and bring it green before QUILL depends on it. Then QUILL audits and fixes real documents to ACB, APH, and WCAG standards in place, through the shared `quill-glow-core` API rather than the thin local bridge. The work spans three repos (QUILL, `quill-glow-core`, `glow`); the stale `s:\code\glow-7.0.0` snapshot is ignored. Value: writing and document accessibility become one app, built on a stable engine. Outcome: a category-defining, accessibility-native editor.
- GLOW interaction quality: surface findings as reviewable-by-ear diffs and one-key jumps, reuse the consented, reversible flow from the Accessibility agent (AGENT-1), and keep the standards profiles (ACB 2025 Baseline, APH Submission, Combined Strict) explicit and announced. Value: the audit-and-fix loop is fully accessible. Outcome: GLOW feels native to QUILL, not bolted on.
- Code-quality and integration fixes for the boundary: replace the thin `quill/core/glow.py` bridge with calls into `quill-glow-core`, add contract tests for the shared API, and keep version and component reporting honest. Value: a clean, tested seam. Outcome: GLOW improvements flow into QUILL without surprises.
- GLOW as a watch action: WATCH-8. Value: register GLOW's audit-and-fix flow as a Watch Profile action so a shared folder of incoming documents is made accessible automatically, reversibly, and announced through the queue. Outcome: the accessibility engine becomes hands-free for whole folders, not just the open document.

Why third: high strategic value that extends the core mission, depends on the gated base (Tier 1), and is most compelling once the flagship experience (Tier 2) already feels great. Most cost is integration, not invention.

#### Tier 4: Structural health and performance that keep greatness durable (high leverage)

Not flashy, but what lets the product stay excellent as it grows.

- Decompose the UI monolith behind characterization tests: CQ-16 then CQ-1, with GATE-6 and GATE-11. Value: every future change gets faster and safer. Outcome: the 18,748-line risk becomes maintainable. Sequencing note: do this after Tier 2 ships, never as a prerequisite to it, and always behind passing characterization tests.
- Drive the strict-typing zone and lint to clean: TYPE-1 through TYPE-8, CQ-18. Value: a class of bugs disappears at author time. Outcome: a codebase that resists regression.
- Remove first-use stalls and enforce budgets: PERF-1 through PERF-3, PERF-9 through PERF-14, GATE-10. Value: the app feels instant. Outcome: performance that does not slip back.
- The remaining security hardening: SEC-6, SEC-7, SEC-14 through SEC-17, SEC-8 (plugins stay gated). Value: defense in depth. Outcome: a product that is safe by construction.

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

Why fifth: it is the second category-defining engine and it completes the WATCH loop, but it sits one step further from the writing-and-accessibility core than GLOW, so it follows the flagship, GLOW, and structural work — and now precedes documentation so the docs describe it as finished.

#### Tier 6: Documentation greatness and the learning surface (completes the product, last)

A great product is not done until people can learn it — and per the tier swap, documentation lands last so it describes a product that is already built, safe, delightful, GLOW-native, and transcription-capable. The BITS Whisperer docs at `s:\code\bw\docs` (PRD, USER_GUIDE, GETTING_STARTED) are reused and harmonized into QUILL's voice rather than rewritten from scratch.

- Consolidate and elevate the docs folder: DOC-14 through DOC-17, DOC-11 (accessibility), DOC-12 (engineering docs). Value: documentation that is itself a model of accessibility and clarity. Outcome: nobody is left behind.
- The learning surface: DOC-1 through DOC-8, the podcasts (POD-1 through POD-5), and the tutorials (TUT-1 through TUT-7), now including the transcription and GLOW audit loops as first-class lessons. Value: a complete path from first launch to mastery. Outcome: a launch that lands with a full learning experience.
- Test breadth: CQ-11 through CQ-16, CQ-23, CQ-24, the IO matrix, and the sandbox policy suite. Value: confidence that everything documented actually works. Outcome: durable quality.
- Breadth and exploration (folded in here as the final reach): NAV-10 (symbol navigation), AI-11 (local grounded answers), AI-12 (evaluation harness), AI-18 (optional GitHub Copilot SDK provider, only if beta users ask), FEAT-12 through FEAT-18, LINUX-2 (accessible Linux to the product bar), ECO-1 (plugin capability, signing, marketplace), L10N-1 (full UI and docs localization), and COLLAB-1 (accessible asynchronous review and sharing). Value: new reach and polish. Outcome: a growing product shaped by real user feedback, with nothing of substance left below best-in-class.

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

| Tier | Scope | Total items | Done | Remaining | Open item IDs |
| --- | --- | --- | --- | --- | --- |
| Tier 1 | Protect users and unlock the team | 23 | 23 | 0 | (complete) |
| Tier 2 | Flagship experience | 57 | 50 | 7 | OCR-1, OCR-3, AGENT-1, AI-19, SET-2, SET-3, A11Y-4 |
| Tier 4 | Structural health and performance | 30 | 11 | 19 | CQ-16, CQ-1, DLG-2, GATE-11, PERF-1..3, PERF-9..14, GATE-10, SEC-6, SEC-7, SEC-8, SEC-14, SEC-17 |
| Tier 6 | Documentation and learning surface | 33 | 3 | 30 | DOC-14..17, DOC-11, DOC-12, DOC-1..8, POD-1..5, TUT-1..7, CQ-11, CQ-14, CQ-23, CQ-24, LINUX-2 |
| **1.0 subtotal** | Tiers 1, 2, 4, 6 (the QUILL 1.0 scope) | **143** | **87** | **56** | |
| Tier 3 (2.0) | GLOW accessibility engine — deferred to QUILL 2.0 | 8 | 0 | 8 | GLOW-1..7, WATCH-8 |
| Tier 5 (2.0) | BITS Whisperer transcription — deferred to QUILL 2.0 | 28 | 0 | 28 | BW-1..10, WATCH-9, NAV-10, AI-11, AI-12, AI-18, FEAT-12..18, LINUX-1, ECO-1, L10N-1, COLLAB-1 |
| AX (2.0) | Accessibility Agents / axe-core engine — deferred to QUILL 2.0 | 6 | 0 | 6 | AX-A..F |
| **2.0 subtotal** | GLOW + BITS Whisperer + axe-core | **42** | **0** | **42** | |
| **Total** | All tiers (1.0 + 2.0) | **185** | **87** | **98** | |

> Deferral note (2026-06-02): per maintainer direction, the GLOW accessibility
> engine (Tier 3, including the WATCH-8 GLOW watch action), the BITS Whisperer
> transcription suite (Tier 5, including the WATCH-9 transcribe watch action), and
> the Accessibility Agents / axe-core workstream (AX-A through AX-F) are all moved
> out of the 1.0 milestone and into **QUILL 2.0**. The Done/Remaining columns were
> reconciled to the per-tier sums (the previous Total of 55/125 did not match the
> rows); going forward the totals are internally consistent. QUILL 1.0 ships when
> the 1.0 subtotal reaches zero remaining.

#### Feature status by tier (the two living lists)

These two tables are the at-a-glance companion to the per-area item tables above:
every feature in the 1.0 scope appears in exactly one of them, grouped by tier.
When an item closes, move its ID from **Work in progress** to **Completed** in the
same change, so both lists stay a truthful snapshot. The canonical per-item detail
(acceptance text and evidence) always lives in the per-area tables higher up; these
two are the watch lists. Items deferred to QUILL 2.0 (GLOW, BITS Whisperer,
axe-core) are tracked separately in the third table and are not part of either 1.0
list.

**Work in progress (QUILL 1.0 — open items)**

| Tier | Status | Feature IDs |
| --- | --- | --- |
| Tier 2 — Flagship | In progress | SET-2, SET-3, AGENT-1, OCR-1, OCR-3, AI-19 |
| Tier 2 — Flagship | Todo | A11Y-4 |
| Tier 4 — Structural health | Todo | CQ-1, CQ-16, DLG-2, GATE-10, GATE-11, PERF-1, PERF-2, PERF-3, PERF-9, PERF-10, PERF-11, PERF-12, PERF-13, PERF-14, SEC-6, SEC-7, SEC-8, SEC-14, SEC-17 |
| Tier 6 — Documentation | Todo | DOC-1, DOC-2, DOC-3, DOC-4, DOC-5, DOC-6, DOC-7, DOC-8, DOC-11, DOC-12, DOC-14, DOC-15, DOC-16, DOC-17, POD-1, POD-2, POD-3, POD-4, POD-5, TUT-1, TUT-2, TUT-3, TUT-4, TUT-5, TUT-6, TUT-7, CQ-11, CQ-23, CQ-24, LINUX-2 |

**Completed (QUILL 1.0 — Done)**

| Tier | Feature IDs |
| --- | --- |
| Tier 1 — Protect users | BUG-1, BUG-2, BUG-3, BUG-4, BUG-5, BUG-6, BUG-7, SEC-1, SEC-10, SEC-11, SEC-13, GATE-1, GATE-2, GATE-3, GATE-4, GATE-5, GATE-6, GATE-7, GATE-8, GATE-9, FLAG-1, FLAG-2 |
| Tier 2 — Flagship | QK-1, QK-2, QK-3, QK-4, QK-5, QK-9, NAV-1, NAV-4, NAV-5, SEL-1, SEL-2, SEL-3, AI-1, AI-6, AI-7, AI-13, AI-14, AI-15, AI-16, AI-17, AI-21, AI-23, WATCH-1, WATCH-2, WATCH-3, WATCH-4, WATCH-5, WATCH-6, WATCH-7, SET-1, SET-4, SET-5, SET-6, SET-7, SHARE-1, SHARE-2, SHARE-3, FLAG-3, FLAG-4, MENU-3, MENU-1, MENU-5, DICT-1, CTX-1, DICT-2, FEAT-19, DLG-1, OCR-2, OCR-4, OCR-5 |
| Tier 4 — Structural health | CQ-7, CQ-12, CQ-13, CQ-14, CQ-15, CQ-17, CQ-18, CQ-19, CQ-20, CQ-21, CQ-22, PERF-8, SEC-4, SEC-15, SEC-16, TYPE-1, TYPE-2, TYPE-3, TYPE-4, TYPE-5, TYPE-6, TYPE-7, TYPE-8 |

**Deferred to QUILL 2.0 (not in the 1.0 lists)**

| Workstream | Feature IDs | Why deferred |
| --- | --- | --- |
| GLOW accessibility engine (Tier 3) | GLOW-1, GLOW-2, GLOW-3, GLOW-4, GLOW-5, GLOW-6, GLOW-7, WATCH-8 | Cross-repo engine integration; lands as a 2.0 headline once the shared `quill-glow-core` engine is green. |
| BITS Whisperer transcription (Tier 5) | BW-1, BW-2, BW-3, BW-4, BW-5, BW-6, BW-7, BW-8, BW-9, BW-10, WATCH-9 | The second distinctive engine; a clean 2.0 integration after the 1.0 flagship ships. |
| Accessibility Agents / axe-core (AX) | AX-A, AX-B, AX-C, AX-D, AX-E, AX-F | Builds on the GLOW engine and report surface, so it follows GLOW into 2.0. |
| Tier 5 stretch explorations | NAV-10, AI-11, AI-12, AI-18, FEAT-12, FEAT-13, FEAT-14, FEAT-15, FEAT-16, FEAT-17, FEAT-18, LINUX-1, ECO-1, L10N-1, COLLAB-1 | Post-1.0 breadth, chosen with beta feedback in 2.0. |

Completed outside the formal tier lists (cross-cutting protections and quality work that the tiers reference only by theme): SEC-2 (path-escape guard for persistence writes), SEC-3 (OCR language allowlist), SEC-4 (documented and validated cwd safety for safe_subprocess), SEC-5 (verified TLS everywhere), GATE-1 (pre-commit), PERF-8 (documented scoped type-check), CQ-17 (thread-safety invariants note), and A11Y-1 (announcement grammar). The GATE-3/CQ-7 cleanup also incidentally cleared the `quill/core` and `quill/io` portion of the TYPE-1..8 zone, though those formal rows stay open until each is individually verified and closed.

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
- CQ-17 closed as a pure-documentation win: a new engineering note, [docs/engineering/thread-safety.md](docs/engineering/thread-safety.md), captures the cache-locking invariants that were previously only implied by the code. It records the two patterns Quill uses — double-checked module-level locking with an immutable published snapshot for read-mostly caches (the spell-check wordlist and enchant handle behind `_BACKEND_LOCK`, the thesaurus index behind `_LOAD_LOCK`), and a per-instance lock taken around every access for genuinely mutable state (the watch-folder seen-set) — plus the stability helpers and a rule that forbids new unguarded module-level mutable caches in `quill/core`. No code changed, so the tier counts are unchanged.
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
(`s:\code\agents`, MIT-licensed) is written up in full in [aa.md](aa.md) at the
repo root. The maintainer is inclined to adopt it. If approved, it becomes a NEW
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

The agreed next sequence (decided with the maintainer): (1) do the cheap Tier 4 quality cleanup first — CQ-18 (the ~43 remaining E501 line-length wraps, after which the `--ignore E501` can be removed from the lint gate and pre-commit) and individually verify/close the TYPE-1..8 rows — because it is low-risk, behavior-preserving, and makes every later PR land in a clean tree; (2) then build Tier 2 flagship work (QUILL key QK-1..5/QK-9, navigation NAV-1/4/5, selection SEL-1..3, then AI-13 provider wiring); (3) do the big `MainFrame` decomposition (CQ-1/CQ-16) last, behind the GATE-6 characterization snapshot, never before Tier 2. Tiers are then executed in order through Tier 6: Tier 3 GLOW (engine adopted via quill-glow-core, structured-format audit as the headline), Tier 4 structural health, Tier 5 BITS Whisperer transcription (the docs/BITS swap puts transcription before documentation), and Tier 6 documentation last.

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

What is explicitly not done yet: the quality-gate ladder is not enforced in CI (GATE items), the configured AI providers still do not drive generation (AI-13), the UI monolith is intact (CQ-1), and the flagship QUILL key, navigation, selection, and settings work (Tier 2) has not started. Overall standing remains roughly Level 3, already Level 4 on accessibility; this section moved the safety floor up without yet adding user-facing flagship value.

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
