# Quill: Product Requirements Document

## A magical, screen-reader-first writing and document environment, built in wxPython

Status: This document specifies Quill **1.0**. The current shipping build is **0.1.5 Beta**, which implements the v1.0 checklist (section 21.1–21.16) plus the post-1.0 foundation work in section 21.17 and later. Section 21 is the living implementation map and is kept current as features land.
Owner: Blind Information Technology Solutions (BITS) and Community Access
Target platform: Windows 10 and Windows 11
Target screen readers: NVDA (primary), JAWS, Narrator
UI framework: wxPython (wxWidgets 3.2 or newer)
Language: Python 3.12 or newer

---

## 1. Vision

Quill is a focused writing and document-reading workstation for blind and low-vision users. It opens almost anything, turns it into clean, navigable text in a familiar Windows edit field, and gives the writer a quiet, predictable place to think.

1. **Open by default.** Free, open source, with no proprietary scripting layer required. Works first class with NVDA out of the box, and equally well with JAWS or Narrator.
2. **Screen-reader-native.** Every surface is a standard Windows control (`wx.TextCtrl` multiline, `wx.ListBox`, `wx.Dialog`) so MSAA, UIA, IAccessible2 and braille routing all just work. No custom drawn controls in the writing path.
3. **Magical, not flashy.** "Magic" means the right thing happens without ceremony. PDFs become readable. Bookmarks survive edits. Backups are automatic. The command palette knows what you mean. Nothing surprises the screen reader.
4. **Local first, cloud optional.** Heavy lifting (PDF extraction, OCR, layout repair, spell checking) runs locally when possible. Cloud assistance is opt-in per action, transparent, and never silent.

If a sighted person watched a Quill user work, they would see almost nothing on screen. That is the point.

---

## 2. Goals and non-goals

### 2.1 Goals

- Provide a dependable plain-text writing surface that NVDA, JAWS and Narrator can read without quirks.
- Open a wide range of document formats and present them as editable text in a standard edit field.
- Preserve the original source file. Extracted or rendered text saves through "Save As" so originals are never overwritten.
- Offer practical writer tools: find and replace, bookmarks that survive edits, magical spell check, word count, page navigation, multiple documents, backups, recent files.
- Offer a discoverable command palette modelled on Visual Studio Code so users do not need to memorise every shortcut.
- Let every shortcut be reassigned through a friendly keymap editor.
- Offer optional, transparent AI assistance for awkward PDFs, scanned images and broken layouts.
- Integrate cleanly with Windows: file associations, "Open with", jump lists, taskbar.
- Be themable for low vision (high contrast, large fonts) without breaking screen-reader behaviour.

### 2.2 Non-goals

- Not a visual word processor. No bold, italic, fonts, colour styling in the writing surface for v1.
- Not a desktop publishing tool.
- Not a replacement for Microsoft Word or LibreOffice Writer.
- Not a book reader with pagination and reflow. Quill renders documents as editable text.
- Not an AI chat product. AI is used only to repair reading order or extract text.

### 2.3 Update Strategy and Micro-Updates

Quill uses `app_updater` (AccessibleApps, MIT license) for cross-platform incremental updates, enabling smaller, faster patches:

- **Incremental delivery**: Updates are distributed as small ZIP packages containing only changed files, not full reinstalls.
- **Automatic bootstrapper**: Platform-specific bootstrappers (`bootstrap.exe`, `bootstrap-mac.sh`, `bootstrap-lin.sh`) apply updates atomically after app exit and restart.
- **Accessible UX**: Update checks and progress are announced through the screen reader with clear prompts for user consent.
- **Backwards-compatible install**: Full installers (Inno Setup on Windows, `.dmg` on macOS) remain available for fresh installs or offline scenarios.
- **Signed feeds**: Update feeds are cryptographically signed (Ed25519 or RSA) to prevent tampering; signatures are verified client-side.

This enables shipping bug fixes and security patches as micro-updates without re-downloading the entire application, while maintaining security and platform best practices.

---

## 3. Target users and primary scenarios

### 3.1 Personas

1. **Mira, blind university student.** Reads PDF lecture notes daily. Needs them to make sense linearly, with reliable search and bookmarks she can name.
2. **Ade, blind technical writer.** Writes long Markdown and HTML. Wants to write in a quiet edit field, preview structure in a browser, and export cleanly.
3. **Pat, blind admin assistant.** Opens invoices and Word documents from email. Wants to copy reference numbers and totals quickly.
4. **Sam, low-vision novelist.** Uses Narrator with a large font and high contrast. Writes long manuscripts, restores from yesterday's backup occasionally.
5. **Jamie, blind sysadmin.** Edits INI, JSON, log and config files. Wants a calm editor that does not fight tooling.

### 3.2 Primary scenarios

- Open a 30-page PDF invoice, find the payment reference, copy it.
- Start a blank document, write a 2000-word article in Markdown, preview it in the browser, export to Word.
- Open a DOCX from a colleague, read it, save the extracted text as a `.txt` for archival without touching the original.
- Open a scanned receipt, ask Quill to OCR it through a cloud service, get a plain text rendering.
- Restore the version of `chapter-7.md` from two saves ago.
- Reassign `Ctrl+G` from Go To Line to Go To Bookmark because the user prefers a different convention.

---

## 4. Product principles

1. **The edit field is sacred.** The writing surface is a standard multi-line `wx.TextCtrl`. Nothing exotic. Screen readers see plain text. Always.
2. **Predictable keyboard.** Shortcuts match Windows conventions where they exist. New shortcuts are documented, discoverable, and reassignable.
3. **Speak the result, not the process.** After every meaningful action, Quill announces a short, useful result through the screen reader.
4. **Originals are read-only by default.** Anything rendered or extracted saves through Save As. Plain-text formats save in place.
5. **No silent network calls.** Any cloud assistance asks first, shows progress, and reports the outcome.
6. **Quiet by default.** No surprise toasts. No animated UI. No tabs that announce themselves on every switch.
7. **Recoverable.** Backups happen on save. Crash recovery on launch. Nothing the user wrote should ever be lost.
8. **Discoverable.** A searchable command palette lists every action with its current binding.

---

## 5. Functional requirements

### 5.1 Application shell

- Single window per running instance, with multiple documents inside.
- Three primary regions, always present: **menu bar** (5.1a), **central editor**, **status bar** (5.1b).
- Window title shows `document-name [modified] – Quill`. The word "modified" appears only when the document has unsaved changes.
- Tray icon optional, off by default.
- No splash screen.
- **Single-instance mode** is on by default. A second launch with a path opens that path in the existing window and brings it to the foreground. A setting allows multi-instance for advanced users.
- **F6 region cycling** moves keyboard focus through the three regions in order (editor → menu bar → status bar → editor). `Shift+F6` cycles in reverse. The region name is announced on entry ("Status bar"). If the Outline Navigator (5.16) is pinned, it joins the cycle between editor and menu bar.
- All regions are stock wx controls (`wx.MenuBar`, `wx.TextCtrl`, `wx.StatusBar` with a custom layout) so MSAA/UIA expose them correctly without scripts.

### 5.1a The magical menu bar

The menu bar is standards-based, predictable, and exhaustive. Every menu item is also a command in the palette, every item shows its current keybinding to the right of its label, and the displayed binding updates live when the user rebinds it. No menu item is hidden; disabled items remain visible with a short tooltip explaining why they are disabled in the current context.

Menu structure:

- **File**: New/Open/**New from Clipboard**/Open Recent/Open from URL, **Open from Remote / Save to Remote / Save Copy to Remote / Manage Remote Sites** (FTP, SFTP, HTTPS, WebDAV, S3 — verified TLS, host-allow-listed, explicit consent, screen-reader announcements), **Snapshots** (save/open workspace snapshot), **Notebook** submenu (**New Notebook / New from Folder / Open Notebook / Save Snapshot / Manage Snapshots** — multi-document workspace with entries panel, daily goal, and named snapshots), Save/Save As/Save All/Save as plain text, Reload/Restore backup, print flows, **Run current file / Open target at cursor / Rename / Delete current file**, close/exit.
- **Edit**: Undo/redo, clipboard (including **Paste HTML as Markdown**), **Find/Replace plus Find Next/Previous/All Matches**, selection helpers, **delete-to-line/document and delete-paragraph**, link insertion/follow, and **Recent Marks (Ring)** with plain-language labels.
- **View**: shell behavior, theme and visual controls (preference toggles such as persistent undo, spell-check-as-you-type, word prediction, dark mode, tray mode, title-path and dirty-title style now live in **Settings**).
- **Insert**: table/list/code/footnote/tag insertion helpers plus **special character, date and time, calculated date, and file content**.
- **Format**: case/comment/indent controls, rich text and heading controls, and a single **Transform Lines** submenu (number/hard-wrap lines plus sort/reverse/dedup/whitespace/indentation conversions).
- **Navigate**: line/page/bookmark movement, heading/block/structure movement, outline, bracket match, region movement, **go to percent / first / last non-blank**, and **Go to Entry / Heading / Bookmark / Sticky Note in Notebook** (cross-entry navigation when a Notebook is open).
- **Search**: in-files Find and Replace-across-files, plus **regex count/extract matches and block set-operations** (line filtering by block membership).
- **Tools**: regrouped into discoverable submenus (≤ 2 levels deep):
  - Sticky Notes
  - Writing and Language
  - Read Aloud
  - Integrations
  - Document Intake
  - AI Assistant *(demoted from top level; promotable back via Customize Menus)*
  - Authoring and Automation
  - GLOW
  - Macros
  - Compare Documents
  - Accessibility *(includes cursor address / document status / selection-length status queries)*
  - Support
  - Customize
  - Power Tools *(editor-behavior power toggles grouped together where no other menu is a natural home)*
  - Quillins *(includes **Text Tools** for line transforms/regex and **Insert Tools** for date/time placeholders)*
  - Dictation and Watch Folder Automation (BITS Whisperer) appears here when enabled.
- **Window**: document/tab management actions.
- **Help**: contextual help, onboarding docs, feature profile support, updates, and About.

All menu strings are translatable. Every menu item has a unique mnemonic. The menu bar may be hidden via View; when hidden, pressing `Alt` reveals it temporarily and `Esc` dismisses it again, matching Windows convention.

### 5.1b The magical status bar

The status bar is not a passive label strip. It is a fully keyboard-navigable row of items that any user can reach with `F6` and arrow through with Left and Right. Each item is a small interactive cell, and `Enter` on a cell either toggles a state, opens a chooser, or runs a related command. This is modelled on Visual Studio Code's status bar, adapted for screen-reader-first interaction.

Design rules:

- **Container**: a custom layout inside `wx.StatusBar` composed of small `wx.Window`-derived focusable buttons (`wx.lib.agw.AquaButton` style is rejected; we use plain `wx.Button` with flat styling). Each cell exposes itself as an MSAA button with name, role, value, and description so NVDA, JAWS, and Narrator read it as a real interactive control.
- **Reachable**: `F6` from the editor moves focus into the status bar at the cell the user last interacted with (or the leftmost cell on first entry). Left/Right arrow moves between cells with wrap-around. `Home`/`End` jump to first/last. `Esc` returns focus to the editor. Tab and Shift+Tab also move between cells inside the status bar.
- **Announced**: when focus enters the status bar, the region name and the focused cell are announced ("Status bar, Line 12, Column 7, button"). Cells announce their value when arrowed to.
- **Activated**: `Enter` or `Space` triggers the cell's primary action. `Shift+F10` or the Application key opens a context menu of related actions for that cell. Right-clicking is equivalent.
- **Live updates**: cell values update without stealing focus. Updates marshal via `wx.CallAfter` and use a debounced single accessibility event per cell per 200 ms to avoid speech spam.
- **Hideable per cell**: a context menu item "Hide this item" tucks any cell behind an overflow group. Overflow is reached at the right end ("More items, button"); Enter opens a small list of hidden cells, any of which can be restored.
- **Plugin-extensible** (v1.1): plugins may register status-bar cells with the same MSAA contract.

Cells shipped in v1.0, in left-to-right order:

| Cell | Default value | Primary action (Enter) | Context menu |
| --- | --- | --- | --- |
| **Document name** | `chapter-7.md` or `Untitled 1` | Opens Quick Switcher (palette `~`) | Switch document, Reveal in Explorer, Copy Path, Close |
| **Modified state** | `Modified` / `Saved` | Save | Save, Save As, Reload From Disk, Restore Backup |
| **Line / Column** | `Line 12, Column 7` | Opens Go To Line | Go To Line, Go To Page, Go To Bookmark |
| **Selection** | `Selection: 3 lines, 47 words` or hidden when no selection | Opens Document Statistics on selection | Statistics on selection, Convert case…, Sort selected lines |
| **Word count** | `1,248 words` | Opens Document Statistics on document | Statistics, Configure reading rate |
| **Page** | `Page 4 of 23` (only when document has page markers) | Opens Go To Page | Next page, Previous page, Page list |
| **Search term** | `Find: "reading order"` (only when a search term is set) | Opens Find with the term pre-filled | Find Next, Find Previous, Find All, Clear Search |
| **Encoding** | `UTF-8` | Opens Reload With Encoding | Reload With Encoding, Save With Encoding, Auto-detect |
| **Line endings** | `LF` / `CRLF` / `CR` | Cycles to the next style and prompts to confirm | Choose explicitly, Convert on save |
| **Indent** | `Spaces: 4` / `Tabs` | Opens indent settings | Convert to tabs, Convert to spaces, Set width |
| **Language** | `en-GB + tech + personal` (the active spell-check dictionary stack) | Opens dictionary stack chooser | Add dictionary, Pin to document, Per-paragraph (v1.2) |
| **Spell check** | `Spell check on` / `Spell check off`. When errors exist: `3 errors` | Toggles as-you-type spell check | Run spell check, Jump to next misspelling, Reset learning |
| **Read aloud** | `Read aloud: ready` or `Read aloud: speaking` | Toggles read-aloud playback | Voice…, Speed…, Read selection, Read document |
| **Accessibility audit** | `Audit: clean` or `Audit: 2 warnings` (only after a manual or auto audit) | Opens the Issues panel | Run audit, Configure rules, Ignore for this document |
| **AI status** | `AI: Ready` / `AI: Needs attention` / `AI: Not checked`, with a short detail line | Opens AI provider settings | Verify connection, Switch provider, View last response |
| **Background tasks** | `Idle` or `Extracting PDF, 42%` | Opens a small Tasks dialog listing in-flight operations with Cancel | Cancel all, Show task log |
| **Notifications** | `No new messages` or `2 messages` | Opens the Notifications dialog (release notes, available updates, backup recovery offers) | Dismiss all, Open Notifications |
| **Quill** (rightmost) | `Quill 1.0` | Opens About | Check for Updates, Release Notes |

Default visibility: Document name, Modified state, Line/Column, Word count, Encoding, Line endings, Spell check, Background tasks, Notifications. Other cells are present but tucked into overflow until first relevant use; they auto-surface when their context becomes relevant (for example Page appears as soon as a paged document is opened; Search term appears the moment a search term is set).

When title mode is configured to show the full file path, Quill suppresses a duplicate file-path status item to avoid repeated location noise.

### 5.1c Trust and verification

Quill explains what it did, how confident it is, and how to recover if extraction looked wrong.

- **Document Intake Report**: every non-plain-text open announces a short, screen-reader-friendly summary and exposes a full report with format, engine, page/sheet/slide counts, OCR use, AI use, confidence, detected structures, and sidecar path.
- **Copy With Source**: selected text can be copied with source location appended (file, page/line/column, engine, confidence) and the source map stays available for future citations.
- **Extraction quality review**: PDF-derived documents expose page-by-page confidence warnings and allow retry/review flows.
- **Cleanup recipes**: deterministic review-and-apply transforms for OCR/PDF cleanup (dehyphenate, remove headers/footers, normalize ligatures, line reflow).
- **Report Bad Extraction**: creates a support package with version, metadata, and no document content unless the user explicitly opts in.
- **What Can I Do Here?**: context-sensitive help for the current surface, available from the Help menu and command palette.
- **Safe mode**: a startup-safe mode disables plugins, experimental features, AI integrations, startup restore, background indexing, file watchers, custom themes, custom snippets, and network services for troubleshooting.
- **Portable mode clarity**: portable builds can store settings locally next to Quill.exe or in AppData, with a first-run choice and an independence command.
- **Golden document corpus**: release testing includes a canonical corpus of PDFs, DOCX, XLSX, PPTX, EPUB, Markdown, HTML, and OCR samples with expected extraction and announcement snapshots.

### 5.1f Profile safety and recovery

Feature profiles must be safe, explainable, reversible, and recoverable.

- **Why don’t I see this?** explains why a named feature is hidden, quiet, unavailable, or gated by the current profile.
- **Profile switch preview** shows visible, quiet, and off features before applying a profile change.
- **Undo last profile change** is available from Notifications after a profile switch.
- **Emergency reset to Essential** is available from launch and from the recovery flow.
- **Profile health check** validates feature IDs, dependencies, visibility paths, and profile JSON integrity.
- **Feature-coverage gate** fails CI when commands, menus, cells, pages, or help topics lack a valid feature ID.
- **Profile-aware keyboard reference** can filter to current profile, quiet features, off features, or diff views.
- **Profile-aware welcome guide** adapts onboarding to the active profile.
- **Privacy and network labels** declare local-only, external-helper, metadata-only, and network-sending features.
- **Feature maturity labels** distinguish core, stable, advanced, helper-required, and unavailable features.
- **Profile import safety** schema-validates profiles and prevents silent enablement of recovery-sensitive features.
- **Show what changed** produces a plain-text summary after profile switches.

### 5.1g Feature registry and user profiles

Quill’s feature-profile system is a first-class product surface, not a cosmetic preference layer.

- **Feature Registry**: a central registry assigns every feature an id, category, description, default state, dependencies, conflicts, privacy impact, network impact, accessibility notes, and profile tags.
- **Profile layering**: user overrides sit above custom profiles, shipped profiles, default registry state, and locked safety rules.
- **Shipped profiles**: Essential, Writer, Reader and Student, Office and Admin, Accessibility Professional, Developer and Power Text, Low Vision, Braille and Screen Reader Power User, Full Quill, and Custom.
- **Settings UI**: Profiles and Features page with search, feature table, explain/related commands, compare profiles, and profile management actions.
- **Custom profile creation**: users can create named custom profiles, select a parent shipped profile, and optionally inherit that parent's feature baseline.
- **Bare-bones start**: custom profile creation also supports an explicit non-inherited baseline (locked core safety features only), with a warning before commit.
- **Quick profile picker**: `Alt+Shift+P` opens fast switching for built-in and custom profiles.
- **Onboarding**: first run asks how Quill should start and chooses a profile.
- **Command/menu/status/help integration**: feature IDs govern command palette, menus, status-bar cells, settings rows, help topics, and format handlers.
- **Dependency enforcement**: enabling a feature can enable required dependencies; disabling a feature warns about affected features.
- **Storage**: feature flags and profiles are stored locally as JSON and can be imported/exported safely.
- **Safety rules**: locked-on features cannot be disabled by shipped profiles, custom profiles, imported profiles, plugins, or user overrides.
- **Feature metadata**: each feature declares risk, maturity, privacy, and network labels for use in settings and help.

### 5.1d Power search, regex, and special characters

Search and Unicode cleanup are first-class accessibility features, not power-user extras.

- **Search modes**: Find, Find All, Replace, Replace All, Find in Selection, and saved search recipes support plain text, whole word, regular expression, and wildcard modes.
- **Regex helper**: a screen-reader-friendly helper provides recipe presets, plain-language explanations, editable sample text, live match previews, and copy-pattern actions.
- **Plain-English errors**: regex errors are reported in single-sentence form with character positions and no traceback.
- **Match review**: users can review captured groups for a match, including named groups.
- **Replace preview**: Replace All shows a preview before applying, with undo as one step.
- **Saved searches**: common search/replace recipes can be stored with mode, scope, and description.
- **Special characters**: the Find dialog can insert special search tokens for tabs, line endings, non-breaking spaces, zero-width characters, smart quotes, ellipses, bullets, and Unicode character classes.
- **Character Inspector**: reports the character under the cursor by name, code point, category, and common encodings.
- **Invisible character view**: users can switch to an inspection view that describes invisible characters textually.
- **Unicode cleanup**: normalization and cleanup commands remove or rewrite common noisy characters with a preview first.

Menu and window stability requirement:

- **Menu mutation guard**: while native menus are open, Quill defers menu label/check/enable mutations and applies them on menu close. This avoids crash-prone churn during rapid keyboard menu navigation.

### 5.1e Feature flags and profiles

Quill should stay calm by default and unlock power features intentionally.

- **Feature states**: `on`, `quiet`, `off`, `locked on`, `locked off`.
- **Core stays locked on**: editor, open/save, backups, crash recovery, help, accessibility announcements, settings.
- **Advanced features can be quiet/off**: regex search, regex helper, saved searches, OCR, AI repair, document intake reports, extraction review, character tools, compare/diff helpers, diagnostics, plugin surfaces.
- **Profiles**: Essential, Writer, Reader and Student, Office and Admin, Accessibility Professional, Developer and Power Text, Low Vision, Braille and Screen Reader Power User, Full Quill, Custom.
- **Settings**: a Profiles and Features page lets the user switch profiles, compare them, and expose quiet features when desired.
- **Command/menu gating**: menus, palette entries, status-bar cells, help topics, and settings pages only surface features appropriate to the active profile.

### 5.2 Documents and the editor

- The editor is a multi-line `wx.TextCtrl` with `wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL | wx.TE_AUTO_URL`. `wx.TE_RICH2` is used only for selection and undo behaviour, not styling.
- UTF-8 internally. Line endings preserved on open, normalised to platform default on new documents.
- Soft wrap on by default; toggle with `Alt+Z`.
- Standard editing: cursor movement, selection, clipboard, undo and redo, all via the native edit control.
- `Ctrl+Delete` deletes the next word; `Ctrl+Backspace` deletes the previous word; result announced.
- Case conversion: `Ctrl+U` upper, `Ctrl+L` lower, `Ctrl+Shift+T` title. Selection if present, otherwise whole document.
- Multiple documents: `Ctrl+Tab` and `Ctrl+Shift+Tab` cycle. Switching announces document name only.
- Close current document: `Ctrl+W` or `Ctrl+F4`. Prompt to save if modified.
- Exit: `Alt+F4` or `Ctrl+Q`. Prompts for each modified document.
- Quill does not restore previous documents on launch by default. Opt-in setting available.

### 5.2a QUILL Quick Nav mode

Quill provides a browse-style, cursor-only navigation mode for long-form reading and structural movement in editable text surfaces.

- Activation: `Ctrl+Shift+Grave` enters QUILL Quick Nav mode.
- Exit: `Esc` exits QUILL Quick Nav mode.
- Direction rule: pressing `Shift` with a Quick Nav key reverses direction.
- Editing rule: no editing commands run while Quick Nav mode is active.
- Status rule: status bar reports Quick Nav mode state while active.
- Auto-exit rule: find and replace entry points return to normal command mode automatically.

Default Quick Nav keys:

- `H` / `Shift+H`: next and previous heading.
- `1` to `6` / `Shift+1` to `Shift+6`: next and previous heading at level 1 through 6.
- `A` / `Shift+A`: next and previous link anchor.
- `L` / `Shift+L`: next and previous list container.
- `I` / `Shift+I`: next and previous list item.
- `T` / `Shift+T`: next and previous table.
- `Q` / `Shift+Q`: next and previous block quote.
- `B` / `Shift+B`: next and previous bookmark.
- `'` / `Shift+'`: next and previous code block.
- `C`: open table of contents (outline navigator).
- `P` / `Shift+P`: next and previous paragraph.
- `S` / `Shift+S`: next and previous sentence.
- `Tab` / `Shift+Tab`: next and previous block.

Artifact tracking model:

- Quill maintains an in-memory navigation index per active document.
- Index key: full document text plus markup kind.
- Headings: parsed from Markdown and HTML heading structure.
- Links: indexed from Markdown link forms and HTML anchor tags.
- Lists: indexed from Markdown list block starts and HTML `ul`/`ol` tags.
- List items: indexed from Markdown list markers and HTML `<li>` tags.
- Tables: indexed from Markdown table starts and HTML `<table>` tags.
- Block quotes: indexed from Markdown quote starts and HTML `<blockquote>` tags.
- Code blocks: indexed from Markdown fenced code boundaries and HTML `<pre>`/`<code>` tags.
- Bookmarks: indexed from active bookmark positions.
- Paragraph anchors: blank-line paragraph boundaries for text/Markdown; block-level HTML tags (`p`, `li`, `blockquote`, `pre`, `h1` to `h6`, `td`, `th`) for HTML.
- Sentence anchors: sentence-ending punctuation boundaries.

Performance and invalidation:

- Quick Nav movement reuses cached anchors to avoid reparsing per keystroke.
- Index invalidates when document text changes, when full-text replacement occurs, and when active tab changes.
- Missing-target announcements are plain-language and surface-aware (for example, "No list items found in this HTML document").

Customization:

- Settings include wrap behavior for Quick Nav boundary traversal and feedback mode (`speech`, `sound`, `both`, `none`).
- Keyboard manager can reassign Quick Nav actions and leader sequences.

### 5.3 File operations

- `Ctrl+N` new blank document.
- `Ctrl+O` open via standard `wx.FileDialog`. Quill aims to be the most catholic accessible reader on Windows; the full supported list is in [section 5.3a](#53a-extended-format-support). The headline groups are:
  - **Plain text and config**: `txt`, `log`, `cue`, `ini`, `json`, `jsonc`, `json5`, `xml`, `csv`, `tsv`, `yaml`, `yml`, `toml`, `nfo`, `env`, `properties`, `conf`, `cfg`, `dotenv`.
  - **Markdown family**: `md`, `markdown`, `mdx`, `mdown`, `mdwn`, `mkd`, `mkdn`, `mkdown`, `ronn`, `qmd` (Quarto), `rmd` (R Markdown).
  - **Lightweight markup**: `rst` (reStructuredText), `adoc`/`asciidoc`, `textile`, `org` (Org-mode), `wiki`/`mediawiki`, `bbcode`, `tex`/`latex`, `bib`/`bibtex`, `typ` (Typst).
  - **HTML family**: `html`, `htm`, `xhtml`, `mhtml`/`mht`, `svg` (read as text + extracted `<text>` content).
  - **Office, modern**: `docx`, `docm`, `dotx`, `dotm`, `pptx`, `pptm`, `xlsx`, `xlsm`, `ods`, `odt`, `odp`, `odg`, `pages`, `key`, `numbers`.
  - **Office, legacy** (best-effort, with AI escalation): `doc`, `ppt`, `xls`, `wpd` (WordPerfect), `wps` (Works), `wri` (Windows Write), `sxw`/`sxc`/`sxi` (StarOffice).
  - **PDF and PostScript**: `pdf`, `ps`, `eps`, `xps`, `oxps`.
  - **E-books**: `epub`, `epub3`, `azw`, `azw3`, `mobi`, `kfx`, `fb2`, `lit`, `lrf`, `prc`, `pdb` (Palm), `tcr`, `cbz`/`cbr` (comic, text layers + OCR).
  - **Rich text**: `rtf`, `rtfd`.
  - **Subtitles and captions**: `srt`, `vtt`, `sbv`, `ass`/`ssa`, `sub`, `ttml`/`dfxp`, `scc`, `stl`, `cap`.
  - **Spreadsheets as text tables**: `csv`, `tsv`, `xlsx`, `xls`, `ods`, `numbers`, `parquet` (read-only), `feather` (read-only). Rendered as accessible plain-text tables with column headers, with `Ctrl+Shift+Right`/`Left` moving by column.
  - **Email and calendar**: `eml`, `msg` (Outlook), `mbox`, `pst` (one message at a time, with index), `ics` (calendar), `vcf` (contact card).
  - **Notes and journals**: `one` (OneNote, best-effort), `enex` (Evernote export), `note` (Apple Notes via iCloud export), `bear` (Bear export), `simplenote` JSON exports.
  - **Source code and scripts** (opened with syntax-aware tokenisation but presented as plain text): `py`, `pyw`, `pyi`, `js`, `mjs`, `cjs`, `ts`, `tsx`, `jsx`, `c`, `h`, `cpp`, `hpp`, `cs`, `java`, `kt`, `rs`, `go`, `rb`, `pl`, `pm`, `php`, `lua`, `swift`, `m`, `mm`, `r`, `jl`, `dart`, `scala`, `clj`, `cljs`, `ex`, `exs`, `erl`, `hs`, `fs`, `vb`, `ps1`, `psm1`, `psd1`, `bat`, `cmd`, `sh`, `bash`, `zsh`, `fish`, `sql`, `graphql`/`gql`, `proto`, `thrift`.
  - **Build, package and lock files**: `Makefile`, `CMakeLists.txt`, `*.gradle`, `*.sbt`, `package.json`, `pyproject.toml`, `requirements.txt`, `Pipfile`, `Cargo.toml`, `go.mod`, `pom.xml`, `*.csproj`/`*.sln`, `Dockerfile`, `*.dockerfile`, `*.tf`/`*.tfvars`, `*.bicep`, `*.k8s.yaml`.
  - **Diff, patch and VCS artefacts**: `diff`, `patch`, `gitignore`, `gitattributes`, `gitmodules`, `gitconfig`, `gitlog` (text dumps), `hgrc`.
  - **Data and notebook**: `ipynb` (Jupyter, read as a linear cell-by-cell document with role headers), `qmd`/`rmd` rendered notebooks, `pickle`/`joblib` (refused with explanation), `sqlite`/`db` (schema + sampled rows view, read-only).
  - **Logs and trace**: `log`, `gz`/`zip`/`tar`/`7z` (auto-extract single-text-file archives), `evtx` (Windows Event Log, summarised), `etl` (limited), `journal` JSON.
  - **Web feeds**: `rss`, `atom`, `opml`, `json-feed`.
  - **Chat and transcript exports**: WhatsApp `.txt` exports, Telegram `.json`/`.html` exports, Slack export JSON, Discord JSON exports, Teams transcript `.docx`/`.vtt`, Zoom `.vtt`/`.txt`, Otter `.txt`, ChatGPT export `.json` (rendered as linear conversation).
  - **DAISY and accessible publishing**: `daisy` (2.02, 3), `nimas`, `bbeb`, `pef` (braille). Read as plain text with section markers.
  - **Braille files**: `brf`, `brl`, `pef`, `ueb` (with optional back-translation to print via liblouis).
  - **Audio with transcripts** (transcript only): pairs of `.mp3`/`.wav`/`.m4a`/`.opus` with a sibling `.vtt`/`.srt`/`.txt` are opened as the transcript with playback shortcuts via plugin.
  - **Image with OCR** (opt-in OCR, local by default via Tesseract, AI escalation available): `png`, `jpg`/`jpeg`, `tif`/`tiff`, `bmp`, `webp`, `heic`, `avif`, `gif`, `jp2`. Multi-page TIFF supported.
  - **Scanned documents**: `djvu`, `cbz`/`cbr`, multi-page TIFF, image-only PDFs (handled by the PDF pipeline).
  - **Subtitle bundles in containers**: `mkv`/`mp4` (extract embedded text tracks only; no media playback).
  - **Web archives**: `warc`, `wacz`, single-file `.html` saves from browsers, `webarchive` (Safari, best-effort).
  - **Code-block exchange**: GitHub Gist URLs and `.gist.json`, Pastebin `.txt`, snippet bundles.
- `Ctrl+S` saves. For editable text formats, saves in place. For rendered/extracted formats, opens Save As.
- `Ctrl+Shift+S` opens Save As directly.
- Recent files: last N (default 10, range 5 to 50). If empty, announce "No recent files."
- File Explorer integration: settings panel lets the user register Quill with Windows for chosen extensions and add an "Open with Quill" verb.

### 5.3a Extended format support

The table below lists every format family Quill adds, why each matters, and how Quill renders it. Every renderer follows the same rules: present text in a standard edit field, preserve the original file, escalate to the enhanced extractor or AI repair only when local extraction is poor and the user asks.

| Format family | Specific formats added | Why it matters | How Quill renders it |
| --- | --- | --- | --- |
| **Spreadsheets** | `xlsx`, `xlsm`, `xls`, `ods`, `numbers`, `csv`, `tsv` | Blind users routinely receive spreadsheet attachments; current accessible tooling forces Excel | Each sheet becomes a section. Tables are emitted as accessible plain-text columns with header row, `Ctrl+Shift+Right/Left` navigates by column, `Ctrl+Shift+Down` summarises totals |
| **OpenDocument** | `odt`, `odp`, `odg`, `ods` | Common in EU public sector and academia | Direct extractor via `odfpy`; structure preserved as headings, lists, tables |
| **Apple iWork** | `pages`, `key`, `numbers` | Cross-platform collaboration is increasingly common; iWork files arrive in email frequently | Local extractor via the iWork archive format; AI escalation for complex layouts |
| **Legacy office** | `ppt`, `xls`, `wpd`, `wps`, `wri`, `sxw`/`sxc`/`sxi` | Older institutional archives still circulate | Best-effort local readers; AI escalation by sending the original file when local reading fails |
| **E-books (proprietary)** | `azw`, `azw3`, `mobi`, `kfx`, `fb2`, `lit`, `lrf`, `prc`, `pdb`, `tcr` | EPUB-only support excludes most Kindle and older e-book libraries | Reuse Calibre's conversion engine where present (plugin in v1.1) or bundled minimal readers for the open formats |
| **Comics with text** | `cbz`, `cbr` | Educational comics and graphic textbooks ship in CBZ | Extract pages, OCR each, present per-page text with page navigation |
| **DjVu and XPS** | `djvu`, `xps`, `oxps` | Academic scans (DjVu) and Microsoft alternatives to PDF (XPS) are common in research | Local extractors; PDF-style page navigation |
| **PostScript** | `ps`, `eps` | Academic preprints and older typeset documents | Convert via Ghostscript to text + page markers |
| **TeX and Typst** | `tex`, `latex`, `bib`, `bibtex`, `typ` | Academic and scientific writing community is largely TeX-based; no accessible plain editor handles it gracefully | Plain-text editing with optional rendered preview to PDF/HTML via local engines; bibtex entries readable as structured records |
| **Lightweight markup** | `rst`, `adoc`/`asciidoc`, `textile`, `org`, `wiki`/`mediawiki`, `bbcode` | Documentation toolchains for Python, Ruby, Asciidoctor, Emacs Org-mode, wikis | Plain-text editing; preview via the appropriate renderer; export to HTML/DOCX |
| **DAISY and braille** | `daisy` 2.02/3, `nimas`, `brf`, `brl`, `pef`, `ueb` | Accessible publishing standards that ironically lack accessible editors. Braille files need round-trip print/braille translation | Linear text presentation with chapter/section navigation; liblouis for braille back-translation; export to BRF |
| **MHTML and web archives** | `mhtml`/`mht`, `warc`, `wacz`, browser "single file" saves, Safari `.webarchive` | Saved web pages are the second-most common research artefact after PDF | Extract the primary document; show resources list; allow Preview as HTML |
| **SVG** | `svg` | SVG is text; titles, descriptions, and `<text>` content carry semantic meaning often inaccessible elsewhere | Show as XML in edit field plus a "Reading View" that extracts titles, descriptions, and text in document order |
| **Subtitles (full set)** | `sbv`, `ass`/`ssa`, `sub`, `ttml`/`dfxp`, `scc`, `stl`, `cap` | broadcast and YouTube captioners need the rest | Render as plain text with optional timecode column; export between formats |
| **Email and mail archives** | `eml`, `msg`, `mbox`, `pst` | Email frequently arrives as standalone files (forwarded, archived, exported); `.msg` and `.pst` are pure Microsoft and historically painful | Headers as a labelled block, body as plain text, attachments listed with "Open in Quill" actions; `pst` and `mbox` get an index UI |
| **Calendar and contacts** | `ics`, `vcf` | Common attachments; today opened by heavy apps | Render events and contacts as structured plain text records |
| **Notes ecosystems** | `one`, `enex`, Apple Notes export, `bear`, Simplenote JSON | People have years of notes locked in proprietary apps | Read-only renderers; each note opens as its own document |
| **Source code and config** | Full polyglot list in 5.3 | Programmers and sysadmins use Quill for quick edits; the screen-reader story for VS Code is good but heavyweight | Syntax-aware tokeniser informs spell check and word navigation; presentation remains plain text |
| **Build, package, IaC** | `Dockerfile`, `*.tf`, `*.bicep`, `*.k8s.yaml`, `pyproject.toml`, etc. | DevOps work is text-heavy and benefits from a calm reader | Plain text with section folding via shortcut, schema-aware error reporting in the `!` palette mode |
| **Diff and patch** | `diff`, `patch`, `gitconfig`, `gitignore` | Code review and merge work | Hunks rendered with `+`/`-` summarised aloud; `Ctrl+]` next hunk |
| **Notebooks** | `ipynb`, `qmd`, `rmd` | Data science and research; notebooks are JSON and unreadable in basic editors | Linearised: each cell becomes a section with role header ("Code cell 3", "Markdown cell 4", "Output of cell 3"), outputs included where text |
| **Data files** | `sqlite`/`db`, `parquet`, `feather` | Researchers and analysts frequently inspect data files | Read-only schema view + first N rows as a table; refuses to edit and explains why |
| **Logs and trace** | `evtx`, gzipped logs, single-file archives | Sysadmin and support workflows | Auto-extract; render with timestamp column |
| **Web feeds** | `rss`, `atom`, `opml`, `json-feed` | Accessible feed consumption | Render as a list of articles, Enter to open one |
| **Chat exports** | WhatsApp, Telegram, Slack, Discord, Teams, Zoom, Otter, ChatGPT | People archive conversations and need to search them | Linearised conversation with speaker headers, timestamps optional |
| **Image OCR** | `png`, `jpg`, `tif` (multi-page), `bmp`, `webp`, `heic`, `avif`, `gif`, `jp2`, plus `djvu` and scanned PDFs | Photographed receipts, signage, scanned mail | Local Tesseract OCR by default; AI escalation for handwriting or poor scans |
| **Audio with transcript** | `.mp3`/`.wav`/`.m4a`/`.opus` paired with `.vtt`/`.srt`/`.txt` | Podcasts, lectures, interviews with transcripts | Opens the transcript; optional playback plugin syncs cursor to audio |
| **Code-block exchange** | Gist URLs, Pastebin URLs, snippet bundles | Developers share text via URLs daily | One-shot fetch + open as unsaved document |

Some renderers (notably KFX, PST, legacy proprietary office, and some iWork variants) require optional helper tools installed locally. Quill detects what is present at startup and the Open dialog only advertises formats it can actually read on this machine. The long-term design is a full Settings → Format Support page; the current beta already ships an External Tools and Format Support dialog that shows supported helpers, the capabilities they unlock, and copy-to-clipboard installation hints (never an automatic install).

#### Editable vs. read-only matrix

Not every format we open is something a user should edit. Quill is explicit about which formats round-trip in place vs. require Save As:

- **Save in place**: every plain-text and lightweight-markup format, source code, configs, subtitles, braille (BRF), SVG, JSON/XML/YAML/TOML, notebooks (when the user has explicitly chosen to keep notebook structure on save).
- **Save As only (originals protected)**: DOCX/DOC, PPTX/PPT, XLSX/XLS, ODT/ODP/ODS, Pages/Keynote/Numbers, PDF, PS/EPS, XPS, EPUB and other e-books, RTF, DjVu, comics, MHTML and web archives, email (`eml`, `msg`, `pst`, `mbox`), calendar and contact files, OneNote, data files (`sqlite`, `parquet`, `feather`), all image formats.
- **Read-only with explicit refusal-to-edit message**: PST archives, parquet/feather, evtx, AZW3/KFX, anything DRM-protected.

#### Plugin escalation

Where bundling a large dependency would balloon installer size (Calibre, Ghostscript, Tesseract trained-data packs, MeCab for Japanese, LibreOffice headless for legacy office), Quill ships a thin shim and offers a one-click plugin install from the Format Support page. Plugins announce their license clearly before installing.

### 5.3b Microsoft Word document support (DOCX / DOC)

This section is the canonical, scoped statement of what Quill 1.0 does with Microsoft Word files (.docx and .doc). Anything not listed here is explicitly out of scope for v1.0 and tracked in the backlog.

#### 5.3b.1 Complexity and Risk Context

Microsoft Word documents (.docx = XML-based, .doc = binary OLE2 format) present genuine complexity risks:

1. **Formatting metadata**: fonts, sizes, colors, styles, themes, templates
2. **Complex structure**: headers, footers, text boxes, shapes, comments, tracked changes
3. **Media embedding**: images, charts, SmartArt, embedded objects, videos
4. **Advanced features**: fields, macros (VBA), content controls, form controls, ActiveX
5. **Reading order challenges**: columns, text boxes in non-linear positions, floating shapes
6. **Legacy cruft**: corrupted documents, OLE objects, mixed encodings, malformed XML

Quill's design principle ("The edit field is sacred") prevents visual formatting preservation in v1.0. Word files must be extracted to plain, linear text in `wx.TextCtrl` for guaranteed screen-reader compatibility with NVDA, JAWS, and Narrator.

#### 5.3b.2 Supported Features (What Gets Extracted)

**Core content (via Pandoc extraction):**

- ✅ Body text and paragraphs
- ✅ Headings (levels 1–6) → rendered as Markdown `#`, `##`, `###`, etc.
- ✅ Bullet and numbered lists (nested up to 3 levels)
- ✅ Hyperlinks → preserved as plain-text URLs or Markdown links
- ✅ Comments and tracked changes → extracted as plain text with attributions
- ✅ Footnotes and endnotes → appended as footnote text
- ✅ Tables → converted to plain-text table representation (Markdown or ASCII)
- ✅ Page breaks → rendered as visual markers `--- Page Break ---`
- ✅ Basic structural integrity: proper paragraph separation, list context

**Conversion support (via Pandoc bridge):**

- ✅ Word → Markdown (for universal editing)
- ✅ Word → HTML (for preview/export)
- ✅ Word → Plain text
- ✅ Word → RTF (via Pandoc if needed)
- ✅ Cross-format roundtrip: Markdown ↔ Word, HTML ↔ Word

**Metadata (stored in `Document.source_metadata`):**

- ✅ Document title, author, subject
- ✅ Creation/modification dates
- ✅ Word count, page count (if available)
- ✅ Character encoding detection and preservation
- ✅ Extraction engine name and version (Pandoc 3.1+)
- ✅ Quality score (0–100) quantifying extraction fidelity

#### 5.3b.3 Unsupported Features (Not Extracted, User Warned)

**Formatting (intentionally dropped for v1.0 compatibility):**

- ❌ Font names, sizes, colors, bold/italic/underline
- ❌ Paragraph alignment (left, center, right, justify)
- ❌ Line spacing, paragraph spacing, indentation
- ❌ Themes, master pages, custom styles
- ❌ Watermarks, page backgrounds

**Advanced structures (extracted with limitations or skipped):**

- ⚠️ **Images**: Filenames and captions only; image content is NOT OCR'd unless user opts in v1.1+
- ⚠️ **Charts**: Extracted as text labels only; visual data is lost
- ⚠️ **Text boxes and shapes**: Attempted extraction; may appear out of order or be skipped
- ⚠️ **Headers and footers**: Extracted, appended as a section at end of document
- ⚠️ **Columns**: Flattened to single column; reading order may be unpredictable

**Security-sensitive (explicitly blocked or sanitized):**

- ❌ **VBA macros**: Silently ignored; Pandoc subprocess does not execute any code
- ❌ Embedded executables or ActiveX controls
- ❌ External links to remote templates or resources (not followed)
- ❌ OLE embedded objects (attempted extraction of embedded text only)

**Deferred to v1.1+ (not attempted in v1.0):**

- ❌ Revision history or multi-user collaboration metadata
- ❌ Form fields and fillable controls
- ❌ Custom numbering or multi-level list hacks
- ❌ Mail merge fields
- ❌ Document protection or permissions (file access checked by OS only)

#### 5.3b.4 Architecture: I/O Module Design

**New module: `quill/io/word.py`**

- `read_word_document(path, timeout_sec=60.0, fallback_to_plaintext=True) → Document`
  - Extracts text from .docx or .doc file
  - Returns `Document` with extracted text, metadata, quality_score, and warnings
  - Timeout protection: max 60 seconds to prevent runaway conversions
  - Error cascade on failure: Pandoc → python-docx → plaintext fallback
  - Raises `UnsupportedFormatError` or `ExtractionTimeoutError` on fatal errors

- `write_word_document_safe(document, path=None, format="docx", warn_on_formatting_loss=True) → Path`
  - Safely writes extracted text back to Word format
  - Shows warning dialog: "Saving as plain text. Original Word formatting will be lost."
  - Uses Pandoc (Markdown → .docx) for clean roundtrip
  - Never overwrites original without explicit user confirmation

- `convert_word_to_markdown(path) → str`
  - Converts Word document to GitHub-flavored Markdown
  - Uses Pandoc with specific output flags for best compatibility

**Enhanced module: `quill/io/pandoc.py`**

Add Word-specific conversion routes:

```python
READER_MAP: dict[str, str] = {
    "docx": "docx",  # NEW: from .docx
    "doc": "doc",  # NEW: from .doc (legacy)
}

WRITER_MAP: dict[str, str] = {
    "word": "docx",  # NEW: export to .docx
    "word-old": "doc",  # NEW: export to .doc (legacy)
}


@dataclass(frozen=True, slots=True)
class WordMetadata:
    title: str | None
    author: str | None
    subject: str | None
    created: str | None
    modified: str | None
    word_count: int
    page_count: int
```

**Updated module: `quill/io/detect.py`**

```python
TEXT_EXTENSIONS = {
    # ... existing ...
    ".docx",  # NEW
    ".doc",  # NEW
}


def looks_like_word_document(path: Path) -> bool:
    return path.suffix.lower() in {".docx", ".doc"}
```

#### 5.3b.5 Error Handling: Graceful Cascade

Word extraction implements a three-tier fallback strategy to ensure the app never crashes on corrupted, malicious, or malformed files:

**Tier 1: Pandoc (primary path)**

- Subprocess-isolated extraction via Pandoc 3.1+
- Timeout: 60 seconds (hard limit)
- Success: `quality_score ≥ 60`
- On failure → Tier 2

**Tier 2: python-docx (fallback)**

- Basic paragraph/heading extraction only
- No Pandoc dependency required
- `quality_score ~40` (limited feature set)
- Errors logged; user sees warning banner
- On failure → Tier 3

**Tier 3: Emergency UTF-8 read**

- Last-resort: read file as text
- Returns garbled but won't crash
- `quality_score 0`
- Clear error message: "Document could not be fully read. Try opening in Microsoft Word first."

#### 5.3b.6 User-Facing Messaging (Document Intake Report)

When opening a .docx or .doc file, Quill displays an in-app banner (stored in `source_metadata`, displayed by `main_frame.py`):

```text
📄 Word Document Opened
This document has been converted to plain text for editing in Quill.
• Formatting (fonts, colors, styles) has been removed.
• Tables and lists have been simplified for readability.
• Images and charts have been replaced with captions only.
• If you need the original formatting, open this file in Microsoft Word.

Original file: Z:\documents\report.docx
Engine: Pandoc 3.1.0 | Quality score: 85/100

[🔄 Retry extraction]  [💾 Save as .txt]  [📖 Show details]
```

The banner is concise and accessible: each item is announced separately via screen reader, and action buttons are navigable via Tab.

**Where Am I enhancement:** When cursor is at the start of an extracted Word document, `Ctrl+Alt+W` (Where Am I) announces:
> "Word document. Title: Q2 Report. Author: Jane Doe. 8 pages, 2,451 words. Extracted by Pandoc 3.1.0. Quality: 85 out of 100. Formatting not preserved."

#### 5.3b.7 Pandoc Integration and Format Bridge

Pandoc is a universal document converter supporting 30+ input and output formats. Full integration enables:

**Phase 1 (v1.0 — this release):**

- Pandoc reads .docx and .doc files
- Export to Markdown, HTML, RTF via `File > Save As`
- Metadata extraction for document properties
- Fallback pipeline: Pandoc → python-docx → plaintext

**Phase 2 (v1.1):**

- Pandoc template engine for styled exports
- Batch conversion: `Tools > Convert Document`
- Support for .odt (LibreOffice), .tex (LaTeX)
- Optional: OCR images in Word documents (cloud service or local Tesseract)

**Phase 3 (v1.2+):**

- Pandoc filters for custom transformations
- Plugin API for format extension

**Installation and resource limits:**

- Pandoc is bundled with Quill on Windows (or installed via `choco install pandoc`)
- Subprocess isolation: Pandoc runs out-of-process; malicious code cannot harm Quill
- **Timeout**: 60 seconds per document (hard limit)
- **Memory**: Monitored via `psutil`; warns if > 500 MB used during extraction
- **File size**: Pre-check before extraction; if > 100 MB, warn and offer async extraction

#### 5.3b.8 Editable Rendering, Protected Original

Word files follow Quill's principle: **originals are read-only by default**.

- The extracted text is presented in the standard multi-line editor
- `Ctrl+S` opens **Save As** so the original `.docx` / `.doc` cannot be overwritten
- `Ctrl+Shift+S` opens Save As directly
- Save dialog offers: `.txt`, `.md` (Markdown), `.html`, `.docx` (new Word), or All Files
- Before saving to `.docx`, a warning dialog appears:
  > "Saving as plain text. Original Word formatting will be lost. Continue?"

#### 5.3b.9 Metadata and Quality Scoring

Extracted metadata is stored in the `Document.source_metadata` dict:

```python
source_metadata = {
    "source_kind": "word",
    "format": "docx",  # or "doc"
    "engine": "pandoc",
    "engine_version": "3.1.0",
    "quality_score": 85,  # 0–100
    "extraction_warnings": [
        "Images not extracted (captions only)",
        "Tracked changes simplified to plain text",
        "Columns flattened to single column",
    ],
    "word_metadata": {
        "title": "Q2 Report",
        "author": "Jane Doe",
        "subject": "Financial Review",
        "created": "2026-03-15T10:30:00Z",
        "modified": "2026-05-28T14:22:00Z",
        "word_count": 2451,
        "page_count": 8,
    },
}
```

**Quality score calculation (0–100):**

- Start at 100
- Subtract 5 per non-extracted image
- Subtract 10 per text box with suspected out-of-order content
- Subtract 15 if complex shapes or columns detected
- Subtract 20 if corrupted sections skipped
- Floor at 0, never negative

#### 5.3b.10 Risk Mitigation and Safety

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Large .docx files (10+ MB) cause extraction to hang | Application freeze, loss of edits to other docs | 60-second Pandoc timeout, async extraction option for large files |
| Corrupted Word files crash parser | Application crash | Graceful error cascade: Pandoc → python-docx → plaintext; never crash |
| Complex formatting confuses extraction order | User sees garbled text | Clear in-app banner: "Word formatting not preserved" + retry option |
| VBA macros or malicious code in .docx | Security vulnerability | Pandoc subprocess isolation; no code execution; explicit security testing |
| .doc (OLE) files fail silently | Silent data loss | Pandoc attempts .doc → XML; if it fails, fallback to python-docx |
| User saves edits back to .docx, loses formatting | Data loss if user relies on styles | Always prompt before save: "Saving as plain text. Continue?" + option to cancel |
| Memory explosion from embedded media | Out-of-memory crash | Pre-check file size; if > 50 MB, warn; if > 100 MB, offer async extraction |

#### 5.3b.10a Extraction Quality Diagnostics (Inspired by GLOW)

GLOW's document auditor and fixer provide patterns for deeply analyzing Word documents. Quill adopts similar diagnostic techniques to produce actionable extraction warnings:

**Paragraph-level diagnostics:**

- **Fake lists detection**: Scan paragraphs for manually typed bullet characters (•, ‣, ◯, ◯, ◦, ⁃) or numbered patterns ("1.", "a)") instead of built-in list styles; flag as "Potential fake list" in `source_metadata`
- **All-caps content**: Detect paragraphs in ALL CAPS (not formatting, but typed caps); if > 3 words, flag as potential heading that should be restyles
- **Long sections without headings**: If > 20 paragraphs appear without a heading, flag as "Consider adding structure" in extraction warnings
- **Repeated spaces for layout**: Detect runs of 3+ consecutive spaces used for visual alignment (e.g., `Qty: ___Price:___`); flag as "Document uses spaces for layout, which may reflow unexpectedly in Quill"
- **Repeated font families in paragraph**: Track non-Arial fonts per paragraph; cap reporting at 3 example locations + summary count to avoid spam

**Document-level diagnostics:**

- **Title and language metadata**: Extract document properties (title, language, author); if missing, flag "Document title not set in properties" as info-level warning
- **Page setup**: Extract margin configuration; compare against expected values; if margins are unusual (< 0.5" or > 1.5"), note in warnings
- **Hyphenation**: Detect if auto-hyphenation is enabled; flag as "Hyphenation may break words unexpectedly when text reflows"
- **Heading hierarchy**: Scan for missing levels (e.g., H1 followed by H3) or skipped levels; flag as structural issue

**Extraction engine diagnostics:**

- **Track extraction path**: Note which engine extracted each paragraph (Pandoc, python-docx, plaintext)
- **Per-paragraph confidence**: If Pandoc succeeded but python-docx fallback was triggered for some content, track which paragraphs used fallback
- **Engine switch detection**: If Pandoc extracted pages 1–8 but python-docx took pages 9–12, surface this as "Extraction method changed mid-document" warning

**Example source_metadata structure with GLOW-inspired diagnostics:**

```python
source_metadata = {
    "source_kind": "word",
    "format": "docx",
    "engine": "pandoc",
    "engine_version": "3.1.0",
    "quality_score": 78,  # Reduced from 85 due to diagnostics
    # GLOW-inspired diagnostics
    "extraction_diagnostics": {
        "fake_lists_detected": 2,  # Manually typed bullets
        "all_caps_paragraphs": 1,  # Heading-like caps text
        "long_sections_without_headings": ["Pages 5-6 (23 paragraphs)"],
        "repeated_space_paragraphs": 3,  # Layout abuse detected
        "non_arial_fonts": {"Times New Roman": 5, "Courier": 2},
        "hyphenation_enabled": True,
        "heading_hierarchy_issues": ["H1 at page 1, then H3 at page 2"],
        "extraction_engine_switches": ["Pandoc pages 1-8, python-docx pages 9-10"],
    },
    "extraction_warnings": [
        {
            "id": "FAKE_LISTS_DETECTED",
            "severity": "warning",
            "message": "2 paragraphs detected with manually typed bullet characters instead of built-in list styles",
            "location": "Paragraph 5, Paragraph 12",
            "user_action": "review",
            "suggestion": "Consider reformatting as proper lists in Word",
        },
        {
            "id": "LONG_SECTION_NO_HEADING",
            "severity": "info",
            "message": "23 paragraphs without a heading (pages 5-6)",
            "location": "Paragraphs 45-68",
            "user_action": "review",
            "suggestion": "Add section heading for readability",
        },
        {
            "id": "HYPHENATION_ENABLED",
            "severity": "warning",
            "message": "Automatic hyphenation is enabled; hyphenated words may reflow unexpectedly in Quill",
            "location": "Document Settings",
            "user_action": "accept",
            "suggestion": "Consider disabling hyphenation in Word for cleaner reflow",
        },
    ],
    "word_metadata": {
        "title": "Q2 Report",
        "author": "Jane Doe",
        "subject": "Financial Review",
        "created": "2026-03-15T10:30:00Z",
        "modified": "2026-05-28T14:22:00Z",
        "word_count": 2451,
        "page_count": 8,
        "language": "en-US",
        "margins": {
            "top_in": 1.0,
            "bottom_in": 1.0,
            "left_in": 1.0,
            "right_in": 1.0,
        },
    },
}
```

**User experience enhancement:**

Instead of a flat banner, Quill displays diagnostics with context:

```text
📄 Word Document Opened
Extracted via Pandoc 3.1.0 | Quality: 78/100 (down from 85 due to structural issues)

✓ 8 pages extracted, 2,451 words
✓ 12 headings (H1-H3) converted
⚠ 2 paragraphs with typed bullet characters (should be proper lists)
⚠ Long section without headings (23 paragraphs on pages 5-6)
⚠ Hyphenation enabled (may cause unexpected line breaks)
ℹ Document title: "Q2 Report" | Language: en-US

[🔍 View diagnostics] [💾 Save as .txt] [Learn more]
```

Clicking `[🔍 View diagnostics]` opens a detailed panel showing each diagnostic with suggestions and locations.

---

#### 5.3b.11 Testing Strategy

**Test corpus (stored in `tests/fixtures/word/`):**

| Document | Scenario |
|----------|----------|
| `simple_heading.docx` | Single heading + paragraph, minimal structure |
| `multi_page_structured.docx` | 5 pages, multiple headings (H1–H3), numbered + bulleted lists, tables |
| `embedded_images.docx` | 3 images with alt text; verify alt text extracted, images are not |
| `tracked_changes.docx` | Paragraph with deletions/insertions marked; verify resolved to plain text |
| `corrupted.docx` | Intentionally malformed XML; verify graceful fallback |
| `legacy_format.doc` | MS Word 97–2003 format; verify .doc reader works |
| `password_protected.docx` | Password-protected; verify clear error message |
| `large_50mb.docx` (stub) | Verify timeout protection and progress indication |
| `malicious_macros.docx` | Contains VBA code; verify Pandoc does NOT execute, code is dropped |
| `mixed_language.docx` | Chinese, Arabic, emoji; verify encoding preserved |

**Unit tests (`tests/unit/io/test_word.py`):**

```python
def test_read_docx_simple():
    doc = read_word_document(Path("tests/fixtures/word/simple_heading.docx"))
    assert "Heading" in doc.text
    assert doc.source_metadata["quality_score"] > 80


def test_read_doc_legacy_format():
    doc = read_word_document(Path("tests/fixtures/word/legacy_format.doc"))
    assert doc.text.strip()  # Non-empty
    assert "engine" in doc.source_metadata


def test_read_corrupted_falls_back():
    doc = read_word_document(Path("tests/fixtures/word/corrupted.docx"))
    assert doc.source_metadata.get("quality_score", 0) < 50
    assert len(doc.text) > 0  # No crash; degraded gracefully


def test_read_timeout_protection():
    with pytest.raises(ExtractionTimeoutError):
        read_word_document(
            Path("tests/fixtures/word/large_50mb.docx"),
            timeout_sec=0.1,
        )


def test_macros_not_executed():
    doc = read_word_document(Path("tests/fixtures/word/malicious_macros.docx"))
    assert "VBA" not in doc.text and "Sub " not in doc.text
```

**Integration tests (`tests/integration/test_word_open.py`):**

- Open .docx via UI; verify text loads, no crash
- Check source_metadata banner appears
- Verify status bar shows correct word count, page count
- Save extracted text back to .docx; verify roundtrip produces sensible output
- Verify warning dialog appears before save

**Accessibility tests (`tests/a11y/test_word_screen_reader.py`):**

- NVDA/JAWS reading of extracted text
- Verify metadata banner is announced properly
- Keyboard-only workflow: open → read → navigate → save

**Performance tests (`tests/perf/test_word_extraction_speed.py`):**

- Load 5, 50, 500-page documents; measure extraction time and memory
- Confirm 60-second timeout stops runaway conversions
- Verify UI remains responsive during extraction

#### 5.3b.12 Rollout and Communication

Word documents should open through a direct/native Word-document path by default when the local engine can handle them. If that path is unavailable or fails on a particular file, Quill should offer an explicit choice to fall back to extracted-text import so the user always knows which mode they are entering.

**Pre-release (release notes):**

- Announce: "New: Microsoft Word support (v1.0)"
- Link to knowledge base: "Opening Word Documents in Quill"
- Highlight limitations: "Formatting is not preserved; use Save As for best results"

**In-app messaging (on first Word document open):**

- Display metadata banner with quality score
- Offer `[📖 Learn more]`, `[💾 Save as .txt]`, `[📝 Open as extracted text]`, `[❌ Close]` actions when the direct/native path is not available
- Help menu entry: "Opening Word Documents in Quill"

**Documentation:**

- **README**: "Supported Formats" section lists .docx/.doc with caveats
- **Knowledge base**: Step-by-step guide for opening, extracting, saving Word documents
- **Command palette**: "Open Word Document" command has full description
- **FAQ**: Proactive entries for "What happens to my formatting?" and "Can I edit the original Word file?"

#### 5.3b.13 Success Criteria

By end of v1.0:

1. ✅ **Functional**: Users open .docx/.doc through a direct/native Word path when available; extracted text remains readable/navigable with screen readers as a fallback, content (headings, lists, tables, links) preserved accurately, save to .txt/Markdown/new .docx
2. ✅ **Safe**: No crashes on corrupted/malicious/large files, VBA not executed, timeout prevents runaway conversions, user warned before formatting loss
3. ✅ **Discoverable**: File > Open shows .docx/.doc as supported, File > Save As offers Word formats, in-app banner explains changes, help docs explain workflow
4. ✅ **Tested**: 10+ real-world documents tested, unit/integration/a11y/perf tests passing, no regressions in existing formats
5. ✅ **Documented**: User docs explain what is and is not supported, known limitations transparent, troubleshooting guide provided

#### 5.3b.14 Future Enhancements (Post-v1.0)

- **Async extraction**: Large files extract in background without blocking UI
- **OCR images**: Option to OCR images in Word documents (local Tesseract or cloud service)
- **Format bridge UI**: Visual flow chart of all supported conversions (Word native/direct ↔ Markdown ↔ HTML ↔ PDF)
- **Batch conversion**: "Convert 50 Word docs to Markdown" automation
- **Metadata editor**: Simple UI to edit document title, author, creation date
- **Plugin API**: Allow plugins to register custom Word extraction filters
- **Roundtrip fidelity**: Preserve more metadata on Word → edit → Word cycles
- **Document audit mode (v1.1+)**: Scan incoming Word docs for structural issues (fake lists, poor heading hierarchy, orphaned paragraphs) and warn user
- **MarkItDown fallback**: If available, use Microsoft's MarkItDown for improved .doc and .docx extraction before Pandoc
- **VML namespace awareness**: Enhanced python-docx fallback with VML shape and text-box extraction for legacy .doc files
- **Paragraph-level diagnostics**: Track which extraction engine handled each paragraph, surface problematic content for review
- **Styled template export**: When saving as .docx, offer ACB-style or custom templates for accessibility compliance

### 5.3c Microsoft PowerPoint document support (PPTX / PPT)

This section is the canonical specification for PowerPoint support in Quill 1.0. Anything not listed is explicitly out of scope for v1.0 and tracked in the backlog.

#### 5.3c.1 Complexity and Risk Context

PowerPoint presentations (.pptx = XML-based, .ppt = binary OLE2 format) present unique extraction challenges:

1. **Non-linear content**: Slides arranged by visual layout, not reading order; multiple shapes per slide
2. **Visual-first design**: Slide transitions, animations, speaker notes separate from visible content
3. **Nested structure**: Master slides, slide layouts, themes, custom templates, shapes groups
4. **Embedded media**: Images, charts, SmartArt, embedded audio/video, links
5. **Layout complexity**: Text boxes, shapes, grouped objects with reading-order dependencies
6. **Presenter-specific data**: Speaker notes, slide timings, presentation settings
7. **Legacy cruft**: .ppt binary format, corrupted presentations, mixed encoding, malformed XML

Quill prioritizes **linear text extraction and speaker notes over slide visual preservation**. The design principle ("The edit field is sacred") prevents visual formatting preservation in v1.0.

#### 5.3c.2 Supported Features (What Gets Extracted)

**Read (Pandoc extraction):**

- ✅ Slide titles
- ✅ Body text and bullet points (nested up to 3 levels)
- ✅ Text from text boxes (best-effort reading order)
- ✅ Speaker notes (always extracted, separately indexed)
- ✅ Hyperlinks → preserved as plain-text URLs or Markdown links
- ✅ Slide numbers and slide count
- ✅ Presentation metadata: title, author, subject, creation date
- ✅ Basic slide structure: explicit slide markers for boundary detection
- ✅ Chart and SmartArt labels (text-only; visual data is lost)

**Conversion support (via Pandoc bridge):**

- ✅ PowerPoint → Markdown (slide-by-slide structure)
- ✅ PowerPoint → HTML (presentation as linear HTML document)
- ✅ PowerPoint → Plain text

**Metadata:**

- ✅ Presentation title, author, subject, keywords
- ✅ Creation/modification dates
- ✅ Slide count, speaker notes count
- ✅ Character encoding detection and preservation

#### 5.3c.3 Unsupported Features (Not Extracted, Logged, User Warned)

**Visual design (intentionally dropped for v1.0 compatibility):**

- ❌ Slide backgrounds, themes, custom templates
- ❌ Font names, sizes, colors, bold/italic/underline
- ❌ Slide transitions and animations (detected but not played)
- ❌ Master slides and slide layouts (flattened to content only)
- ❌ Alignment, positioning, spacing of text boxes
- ❌ Watermarks, headers, footers

**Advanced structures (extracted with limitations or skipped):**

- ⚠️ **Images and pictures**: Filenames and captions only; image content is NOT OCR'd unless user opts in v1.1+
- ⚠️ **Charts**: Extracted as text labels only; visual data is lost; title and data labels if readable
- ⚠️ **SmartArt**: Converted to bullet-point approximation; visual hierarchy is lost
- ⚠️ **Embedded video/audio**: NOT extracted; presence flagged with duration if available
- ⚠️ **Text boxes and shapes**: Attempted extraction; may appear out of slide reading order
- ⚠️ **Slide layouts and masters**: Flattened to content only; layout structure is not preserved
- ⚠️ **Animations and timing**: Detected and reported but not executed; all animated content extracted

**Security-sensitive (explicitly blocked or sanitized):**

- ❌ Embedded ActiveX controls or macros (VBA) — silently ignored; Pandoc does not execute
- ❌ External links to remote templates or resources (not followed)
- ❌ OLE embedded objects

**Deferred to v1.1+ (not attempted in v1.0):**

- ❌ Presentation handout mode or notes pages export
- ❌ Custom animations or presentation sequences (click-through, auto-play)
- ❌ Form controls or interactive content
- ❌ Presenter view or presenter notes as a separate stream

#### 5.3c.4 Slide Linearization with Reading-Order Detection (GLOW-Inspired)

PowerPoint is inherently non-linear. Quill converts to linear text with intelligent reading-order analysis inspired by GLOW's accessibility auditor:

GLOW discovered that screen readers follow the XML tree order of shapes, not the visual layout. When these don't match, screen readers read slides in the wrong order. Quill analyzes both orders and extracts in visual order (what user sees) while flagging reading-order mismatches to the user.

**Output: Intelligent slide extraction with reading-order diagnostics**

```text
--- Slide 2: Agenda ---
[Title appears first - reading order verified]
Agenda

[3 text boxes detected on slide; visual order verified]
Left column (top-left position):
  • Introduction
    • Background
    • Scope

Right column (top-right position):
  • Main topics
    • Topic 1
    • Topic 2

Center callout (center position):
  🔹 All topics are in scope

📊 Reading Order Analysis:
  ✓ Visual order matches XML order (correct for screen readers)
  ✓ Title reads first (best practice)
  Shapes in reading order: Title → Left → Right → Center
```

#### 5.3c.5 Smart Speaker Notes Extraction (GLOW-Inspired)

Speaker notes are **always extracted and separately indexed** with intelligent metadata:

- Presence detection: slide has/lacks notes
- Timing hints: notes mentioning "2 minutes", "pause here", "auto-advance"
- Visual references: notes mentioning images, charts, diagrams on the slide
- Presenter guidance: transitions, animation, pacing guidance

Example metadata:

```python
{
    "slide": 5,
    "slide_title": "Results",
    "notes": "Reference the chart. This slide auto-advances in 5 seconds.",
    "notes_has_timing": True,
    "notes_mentions_visuals": True,
    "notes_word_count": 18,
}
```

**Magical UI integration:** When user navigates to a slide with speaker notes, Quill announces:

> "Slide 5 of 15: Results. Speaker notes mention slide visuals and timing. Notes say: 'Reference the chart. This slide auto-advances in 5 seconds.'"

#### 5.3c.6 Animations and Timing Detection with WCAG Analysis (GLOW-Inspired)

Animations are **detected, categorized, and intelligently reported** using GLOW's WCAG timing analysis:

- Slide-level auto-advance timing (WCAG 2.2.1): < 3 seconds flagged as violation
- Shape-level animations: entrance, exit, click-triggered animations categorized
- Animation impact: content appearing on click is flagged as potentially hidden

Example output:

```text
⏱ Animation Timing Analysis:
  • Title: "Fade in" (0.5s, starts with slide)
  • Content: "Fly in" (1.0s, appears on click)

🎯 Accessibility Notes:
  → Title auto-animates, so screen reader reads immediately
  → Content requires manual click to reveal
  → Quill has extracted ALL text; no content lost
  ⚠ Warning: Slide 3 auto-advances in 2.5s (< 3s WCAG recommendation)
```

#### 5.3c.7 Slide Title Analysis (GLOW-Inspired)

GLOW discovered that duplicate or missing slide titles break outline navigation. Quill analyzes titles:

- Missing titles: slide has no title shape
- Duplicate titles: same title on multiple slides
- Weak titles: titles that don't describe slide content

Example diagnostics:

```python
"extraction_diagnostics": {
    "slide_titles": [
        {"slide": 1, "title": "Title Slide", "issue": None},
        {"slide": 5, "title": "[No title]", "issue": "missing"},
        {"slide": 6, "title": "Agenda", "issue": "duplicate", "also_on_slides": [2]},
    ],
}
```

#### 5.3c.8 Link and Alt-Text Quality Analysis (GLOW-Inspired)

GLOW discovered accessibility patterns in hyperlinks and alt text. Quill checks for:

- **Bad link text**: "click here", "here", "link", "more"
- **Bare URLs**: raw URLs used as link text instead of descriptive text
- **Missing alt text**: images and charts without descriptions
- **Filename alt text**: alt text that's just the image filename (unhelpful)

#### 5.3c.9 Chart and Visual Content Analysis (GLOW-Inspired)

Quill detects charts, SmartArt, and images. For charts:

- Extracts chart type (column, line, pie, etc.)
- Extracts chart title and axis labels from XML
- Checks for alt text describing the chart
- Attempts to infer data values from label positions (with caution warnings)

#### 5.3c.10 Extraction Quality Diagnostics (GLOW-Inspired Comprehensive Scoring)

Instead of simple text-density scoring, Quill implements **findings-based quality scoring** modeled after GLOW's audit approach:

**Quality scoring system:**

- Baseline: 100 points
- Per-finding penalties (e.g., missing alt text: -5, auto-advance < 3s: -8, duplicate title: -3)
- Bonuses for best practices (speaker notes on >80% of slides: +2, correct reading order: +1)

Example breakdown:

```text
Quality Score: 78/100

Baseline:                                          100
-5 (Images without alt text)                        -5
-5 (Chart without alt text)                         -5
-8 (Slide 3: Auto-advance 2.5s < 3s WCAG)          -8
-3 (Duplicate title)                                -3
+1 (Reading order verified)                         +1
___________________________________________
Quality:                                            78
```

**In-app quality dashboard:**

```text
📊 PowerPoint Presentation Opened
Quality Score: 78/100

Extraction Summary:
  • 15 slides extracted
  • 12 slides have speaker notes
  • 5 animations detected
  • 8 images (5 with alt text, 3 missing)
  • 3 charts (1 with alt text, 2 missing)

⚠ Issues Found (3):
  1. Slide 3: Auto-advance too fast (2.5s < 3s) - WCAG 2.2.1
  2. Slides 2, 6: Duplicate title "Agenda"
  3. 3 images without alt text

✓ All text extracted successfully (no content lost)
```

#### 5.3c.11 User-Facing Messaging

When opening a .pptx or .ppt file, Quill displays:

```text
📊 PowerPoint Presentation Opened
This presentation has been converted to plain text for editing in Quill.
• Slide structure, formatting, and animations are not preserved.
• Text boxes and shapes have been simplified to plain text.
• Images, charts, and embedded media have been replaced with captions only.
• Speaker notes are available (12 slides have notes).
• If you need the original presentation, open this file in PowerPoint.

Original file: Z:\documents\Q2-review.pptx
Engine: Pandoc 3.1.0 | Slides: 15 | Quality score: 82/100

[📖 View notes]  [💾 Save as .txt]  [📖 Learn more]
```

**Where Am I enhancement:** When cursor is at document start, `Ctrl+Alt+W` announces:

> "PowerPoint presentation. Title: Q2 Review. 15 slides, 5,847 words. Speaker notes on 12 slides. Extracted by Pandoc 3.1.0. Quality: 82 out of 100."

#### 5.3c.12 Editable Rendering, Protected Original

Presentations follow Quill's principle: **originals are read-only by default**.

- Extracted text is presented in the standard editor
- `Ctrl+S` opens **Save As** so original `.pptx` cannot be overwritten
- Save dialog offers: `.txt`, `.md` (Markdown), `.html`, new `.pptx`, or All Files
- Before saving to `.pptx`, warning appears: "Saving as plain text. Original slide structure will be lost. Continue?"

#### 5.3c.13 Metadata and Extraction Diagnostics

Extracted metadata stored in `Document.source_metadata`:

```python
source_metadata = {
    "source_kind": "powerpoint",
    "format": "pptx",  # or "ppt"
    "engine": "pandoc",
    "quality_score": 82,  # 0–100 (findings-based)
    "powerpoint_metadata": {
        "title": "Q2 Review",
        "author": "Jane Doe",
        "subject": "Quarterly Business Review",
        "created": "2026-02-15T10:30:00Z",
        "modified": "2026-05-28T14:22:00Z",
        "slide_count": 15,
        "speaker_notes_count": 12,
    },
    "extraction_diagnostics": {
        "total_slides": 15,
        "slides_with_speaker_notes": 12,
        "animations_detected": 5,
        "auto_advance_violations": 1,  # < 3s
        "images_detected": 8,
        "charts_detected": 3,
        "reading_order_mismatches": 1,
        "findings": [
            {"type": "auto_advance_fast", "slide": 3, "timing_ms": 2500},
            {"type": "duplicate_title", "slides": [2, 6], "title": "Agenda"},
        ],
    },
}
```

#### 5.3c.14 Testing Strategy

**Test corpus (stored in `tests/fixtures/powerpoint/`):**

| Document | Scenario |
|----------|----------|
| `simple_title_slide.pptx` | Single slide with title and bullet points |
| `multi_slide_structured.pptx` | 10 slides with titles, nested bullets, speaker notes |
| `with_charts.pptx` | 5 slides with embedded charts; extract labels only |
| `with_images.pptx` | 3 slides with images and captions |
| `with_animations.pptx` | Slides with animations and transitions; verify all text extracted |
| `legacy_format.ppt` | MS PowerPoint 97–2003 format; verify .ppt reader works |
| `corrupted.pptx` | Intentionally malformed XML; verify graceful fallback |
| `large_100_slides.pptx` | Large presentation; verify timeout protection |

**Unit tests (`tests/unit/io/test_powerpoint.py`):**

```python
def test_read_pptx_simple():
    doc = read_powerpoint_presentation(Path("tests/fixtures/powerpoint/simple_title_slide.pptx"))
    assert "Slide 1" in doc.text
    assert doc.source_metadata["quality_score"] > 80


def test_speaker_notes_extracted():
    doc = read_powerpoint_presentation(Path("tests/fixtures/powerpoint/with_speaker_notes.pptx"))
    assert len(doc.source_metadata["speaker_notes"]) > 0


def test_animations_detected():
    doc = read_powerpoint_presentation(Path("tests/fixtures/powerpoint/with_animations.pptx"))
    assert doc.source_metadata["extraction_diagnostics"]["animations_detected"] > 0
```

#### 5.3c.15 Safety and Security

- ✅ **Sandbox execution**: Pandoc runs in subprocess
- ✅ **Resource limits**: Timeout (60s), memory monitoring
- ✅ **No code execution**: VBA macros NOT executed
- ✅ **Fallback chain**: Pandoc → python-pptx → plaintext
- ✅ **User consent**: Warning before overwriting original

#### 5.3c.16 Success Criteria

1. ✅ **Functional**: Users open .pptx/.ppt, extract text readable with screen readers, speaker notes accessible
2. ✅ **Safe**: No crashes on corrupted/malicious files, VBA not executed, user warned before data loss
3. ✅ **Discoverable**: File > Open shows .pptx/.ppt as supported, in-app banner explains changes
4. ✅ **Tested**: 10+ real presentations tested, unit/integration/a11y tests passing
5. ✅ **Documented**: User docs explain what is and is not supported

#### 5.3c.17 Future Enhancements (Post-v1.0)

- **Async extraction**: Large presentations extract in background without blocking UI
- **OCR images**: Option to OCR images in presentations (local Tesseract or cloud service)
- **Handout export**: Linearized slides + speaker notes as single document
- **Presentation outline navigator**: Slide titles as expandable tree with speaker notes
- **Batch conversion**: "Convert 10 presentations to Markdown"
- **Plugin API**: Allow plugins to register custom presentation extraction filters
- **MarkItDown fallback**: Use Microsoft's MarkItDown for improved extraction before Pandoc
- **Chart extraction**: Better chart data extraction (tables from visual charts via OCR)

### 5.4 Excel and CSV support (XLSX / XLS / CSV)

This section specifies Quill's support for tabular data formats: Excel workbooks (.xlsx, .xls) and CSV files (.csv, .tsv). The design prioritizes **accessible grid-based editing mode** as an alternative to traditional spreadsheet UIs, with keyboard-first navigation and GLOW-inspired data quality analysis.

#### 5.4.1 Design Philosophy: Accessible Grid, Not Spreadsheet

Traditional spreadsheets (Excel, LibreOffice Calc) are visual-first and mouse-oriented. Quill reimagines grid editing for keyboard and screen-reader users:

- **Linear keyboard navigation**: Arrow keys move through cells top-to-bottom, left-to-right
- **F2 cell editing**: Edit mode restricted to cell content only; cursor never leaves the cell
- **Status bar context**: "Row 5, Column C (Sales): $75,000" announced before user types
- **Accessible sorting/filtering**: Shift+F10 or right-click to sort columns ascending/descending, filter by value
- **No visual formatting preserved**: Bold, colors, borders intentionally dropped (edit field is sacred)
- **All transformations in plain-text mode**: Pivot tables, transpose, statistics available without leaving CSV Mode

#### 5.4.2 Scope: CSV Mode as Universal Tabular Editor

**CSV files (native support):**

- Open directly in CSV Mode
- Auto-detect delimiters (comma, semicolon, tab, pipe)
- Auto-detect column types (text, integer, float, date, currency, boolean)
- User can toggle first row as column headers
- Full grid editing capabilities (add/delete rows/columns, sort, filter)
- Save back to CSV (or export to Excel, TSV, JSON, SQL, HTML, Markdown)

**Excel files (.xlsx / .xls) - via MarkItDown bridge:**

- Detect format on open
- Auto-convert to CSV using MarkItDown (primary) or openpyxl (fallback)
- Multi-sheet support: user prompted to load sheet, combine all, or create separate documents
- All CSV Mode features work on converted Excel data
- Save options: back to CSV, new Excel file, or export to original Excel format
- Legacy .xls (binary) support via openpyxl fallback

**Why CSV as universal format:**

- Plain-text, version-control friendly, universally accessible
- No hidden metadata, macro viruses, or formatting complexity
- MarkItDown converts any table → CSV automatically
- Screen-reader friendly; structure is explicit (headers, rows, columns)
- Easy to validate, transform, and audit

#### 5.4.3 CSV Mode UI and Keyboard Shortcuts

**Status bar in CSV Mode shows:**

```text
📊 CSV Mode (15 rows × 4 columns) | Headers: ✓ | Delimiter: Comma
```

**Navigation (arrow keys):**

- Arrow keys: Move to adjacent cell (up/down/left/right)
- Ctrl+Home: Go to cell A1 (first cell)
- Ctrl+End: Go to last cell with data
- Ctrl+Right/Left: Jump to next/previous non-empty cell in row
- Ctrl+Down/Up: Jump to next/previous non-empty cell in column
- Page Up / Page Down: Move up/down by 10 rows

**Cell editing (F2 mode):**

- Press F2 to enter edit mode for current cell
- Cursor restricted to cell content only; cannot move to adjacent cells
- Backspace/Delete/Ctrl+A work as expected within the cell
- Escape cancels edit without saving
- Enter commits and moves to next row
- Shift+Enter commits and moves to previous row

**Sorting and filtering (Shift+F10 / Right-click):**

- Shift+F10 or right-click to open column context menu
  - "Sort Ascending" (A→Z, 0→9, empty at bottom)
  - "Sort Descending" (Z→A, 9→0, empty at top)
  - "Move Column Left / Right"
  - "Delete Column / Insert Column"
  - "Filter by Value" (if headers present)
- Ctrl+Shift+L: Toggle filter row (when headers present)

**Selection (Shift+arrows):**

- Shift+Arrow keys: Extend selection to adjacent cells
- Shift+Spacebar: Select entire row
- Ctrl+A: Select all cells

#### 5.4.4 Transformational Features (GLOW-Inspired Data Analysis)

**Quick stats (Ctrl+Alt+S):**
When a numeric column is selected, Ctrl+Alt+S opens statistics panel showing Sum, Average, Median, Min, Max, Standard Deviation.

**Data validation and quality (Ctrl+Alt+V):**
GLOW-inspired findings-based approach: detect empty cells, duplicates, type mismatches, outliers, inconsistent formatting with quality score and auto-fix suggestions.

**Pivot table (Ctrl+Alt+P):**
Group by column with aggregation (Sum, Average, Count, Min, Max).

**Transpose (Ctrl+Alt+T):**
Flip rows and columns.

**Find and replace with regex (Ctrl+H):**
Full regex support with capture groups.

**Concatenate / Split columns (Ctrl+Alt+C / Ctrl+Alt+X):**
Combine or split columns by delimiter.

**Unique values (Ctrl+Alt+U):**
Extract distinct values and create new sheet or copy to clipboard.

**Conditional formatting as comments (Ctrl+Alt+F):**
Mark cells based on conditions (e.g., "Salary > $90,000" adds comment).

#### 5.4.5 Multi-Sheet Excel Support

When opening Excel files with multiple sheets, user is prompted to load sheet, combine all, or create separate documents. Sheet navigation via Ctrl+Page Down/Up.

#### 5.4.6 Format Detection (GLOW-Inspired Type Inference)

When opening CSV or Excel files, Quill auto-detects column types (Text, Integer, Float, Date, Boolean, Currency), date format, currency symbols, encoding, and delimiters with quality assessment.

#### 5.4.7 Save and Export Options

Users can save to CSV, TSV, Pipe-delimited, Excel (.xlsx), JSON, HTML table, Markdown table, or SQL INSERT statements with accessibility options (include column types, freeze headers, set widths).

#### 5.4.8 MarkItDown Integration for Universal Format Conversion

Quill uses Microsoft's MarkItDown library as a Tier 1 converter for Excel files, PDF tables, and web tables, converting all tabular formats to CSV for consistent editing.

#### 5.4.9 Data Quality and Accessibility Patterns (GLOW-Inspired)

Built-in audits for column type consistency, dataset completeness, duplicate detection, and outlier analysis with actionable suggestions.

#### 5.4.10 Testing Strategy

Comprehensive test corpus including simple CSV, headers, mixed types, large files (10k rows), special characters, sparse data, malformed CSV, multi-sheet Excel, formulas, and legacy .xls files. Unit, integration, a11y, and performance tests all included.

#### 5.4.11 Safety and Security

- ✅ **Formula injection prevention**: CSV exports escape Excel formula indicators
- ✅ **Encoding safety**: Detects and preserves UTF-8, UTF-16, ANSI
- ✅ **Macro safety**: Excel macros NOT extracted or executed
- ✅ **Large file handling**: Warn if CSV > 50MB; streaming mode available
- ✅ **Local-only processing**: No network access

#### 5.4.12 Success Criteria

1. ✅ **Functional**: Users open CSV/Excel in accessible CSV Mode; grid navigation, sorting, filtering, transformations work
2. ✅ **Accessible**: Screen readers announce cell position/type/content; all operations keyboard-available
3. ✅ **Magical**: Quick stats, data quality audits, pivot tables, format conversion seamless
4. ✅ **Safe**: No formula injection; large files handled gracefully; macros never executed
5. ✅ **Tested**: Unit, integration, a11y, performance tests passing

#### 5.4.13 Future Enhancements (Post-v1.0)

- **Inline formulas**: Support Excel-like formulas (SUM, AVERAGE, IF) in CSV cells
- **Data source connections**: Live links to external CSV/Excel for refresh
- **Advanced pivot UI**: Keyboard-accessible pivot table builder
- **Chart generation**: Text-based charts from CSV data
- **Database import**: Import from SQL, JSON, APIs
- **VLOOKUP / INDEX-MATCH**: Lookup functions for multi-sheet joins
- **Macro recording**: Record/replay keyboard sequences
- **Data sanitization tools**: Trim spaces, standardize dates, fix typos

### 5.5 PDF handling in v1.0

This section is the canonical, scoped statement of what Quill 1.0 does with PDF files. Anything not listed here is explicitly out of scope for v1.0 and tracked in the backlog ([section 17](#17-backlog-and-deferred-items)).

**What v1.0 ships**

1. **Tier 1, local extraction (automatic on open).** A layered pipeline runs `pdfplumber` and `pypdfium2` (with `pdfminer.six` as a third fallback) per page, scores each extraction for readability (line count, alphabetic ratio, average line length, presence of suspicious one-word-per-line patterns), and picks the best result per page. Pages are concatenated with explicit page markers so page navigation is exact.
2. **Page navigation.** `Page Up` / `Page Down` move to the previous/next page marker. `Ctrl+G` opens Go To Page when page markers exist. The status bar's Page cell shows `Page n of m`. Reaching the first or last page is announced.
3. **Embedded bookmarks.** Bookmarks (Adobe's outline) become Quill bookmarks for that document and appear in the Outline Navigator (5.16) under their original hierarchy. They are read-only with respect to the original PDF; renaming, adding, and deleting affect Quill's own bookmark store.
4. **Password-protected PDFs.** On open, Quill prompts for the password through a standard modal dialog. The password is used in-memory only and is never written to disk, never logged, never sent over the network.
5. **Editable rendering, protected original.** The extracted text is presented in the standard editor. `Ctrl+S` opens **Save As** so the original `.pdf` cannot be overwritten by extracted text. The Save dialog offers Text, Markdown, HTML, and All Files.
6. **Document metadata.** Author, title, subject, keywords, creation date, modification date, and page count are accessible via `File > Document Properties…` and announced in Where Am I when the document is a PDF.
7. **PDF document statistics.** Document Statistics (5.19) reports page count, image count per page (informational), tagged-structure presence, and language metadata.
8. **Accessibility audit, informational.** The Accessibility Audit (5.20) reports whether the PDF has tagged structure, whether it has embedded bookmarks, the image-only page count, language metadata, and password protection state. It does not modify the PDF.
9. **Tier 3, AI-assisted reading order (opt-in, manual).** `Tools > Improve Reading Order…` sends the PDF to the user-configured LLM provider (the user supplies the API key; nothing is bundled). The action **always** asks for confirmation before sending, shows the host name and approximate size in the confirmation dialog, announces progress every ~20 seconds during the request, and reports the outcome. Refuses, with a clear spoken message, if the PDF exceeds the configured page-count limit (default 40). Results open as a new unsaved document whose Save defaults to Save As.
10. **OCR for scanned PDFs.** When tier 1 yields no readable text on a page, Quill offers a one-click escalation to local OCR via the bundled Tesseract (English shipped, additional languages downloadable). For longer scanned PDFs the user may instead escalate to tier 3 AI rendering.
11. **Selection and copy.** Standard selection works in the extracted text. `Ctrl+C` copies as plain text. There is no copy-with-formatting target in v1.0 (the extracted text has none).
12. **Find, Outline, Bookmarks, Word Count, Document Statistics, Read Aloud, Accessibility Audit** all work over the extracted text exactly as they do for any other document.
13. **Compare** (`Tools > Compare With File…`) works against the extracted text representation; comparing two PDFs compares their extracted plain-text forms.

**What v1.0 does not ship (deferred to backlog)**

- **Tier 2 "enhanced local" extractor.** No pure-Python local layout analyser meets the v1.0 quality bar. v1.0 has tier 1 and tier 3 only.
- **Heading synthesis from font-size analysis** when no embedded bookmarks exist. Off by default; available as an opt-in experimental switch in Advanced settings, clearly labelled as experimental.
- **PDF form filling and signing.** Not in v1.0.
- **Writing back to PDF** (annotation, highlight, comment). Not in v1.0; original PDF is read-only by design.
- **Embedded media** (audio, video, 3D, attachments inside the PDF). Not in v1.0.
- **XFA forms.** Not in v1.0.
- **Tagged-structure tree editor.** Reading the structure summary is in; editing it is backlog.

### 5.6 Improve reading order

A general action under Tools and the command palette:

- For text-based documents, sends the current document text to the configured LLM for layout repair.
- For PDF and legacy DOC, sends the original file so text boxes and visual columns can be analysed.
- For PPTX, can send the file when local extraction is insufficient.
- Always asks first. Never used to answer questions about the document.
- Result opens as a new unsaved document; Save defaults to Save As.

### 5.7 HTML and Markdown

- HTML files open as plain text in the editor.
- `File > Preview as HTML` writes a temporary HTML file and opens the default browser.
- Markdown files open as plain text.
- `File > Preview Markdown as HTML` renders via `markdown-it-py` and opens the browser.
- `File > Export Markdown as HTML` saves a standalone HTML file.
- `File > Export Markdown as Word` produces a `.docx` via `python-docx`, preserving headings, lists, links, tables, code blocks.

### 5.8 Find and replace

Find in Quill is designed to feel like Microsoft editors and Visual Studio Code at the same time: F3 just works once a term is known, the search term is remembered everywhere it makes sense, and everything is announced.

**The search term, the central concept.** Quill maintains a single "current search term" per editor. The term is set by any of:

- typing in the Find dialog and pressing Enter,
- pressing `Ctrl+F3` with a selection (the selection becomes the search term),
- pressing `Ctrl+F3` with no selection (the word under the cursor becomes the search term),
- restoring it from session storage on launch (when enabled),
- arrow-selecting a previous term from the Find dialog's history dropdown.

The status bar's **Search term** cell (5.1b) displays the current search term and its options. `Enter` on the cell reopens Find pre-filled.

**Keystrokes**

- `Ctrl+F` opens Find. Pressing Enter searches forward, sets the search term, selects the match, and announces `Found on line 12: <line text>`.
- `Ctrl+Shift+F` opens Find anchored to backwards search.
- `F3` advances to the **next** occurrence of the current search term without opening any dialog. If no term is set, F3 opens Find with focus in the input. If a term is set, F3 simply selects the next match and announces line + context. At end of document, search wraps to the start (announced as "Wrapped to top").
- `Shift+F3` does the same in reverse, wrapping at the start to the end ("Wrapped to bottom").
- `Ctrl+F3` sets the current word or selection as the search term and advances. `Ctrl+Shift+F3` sets it and retreats. This is the Visual Studio convention.
- `Alt+F3` opens **Find All**: a list of every match with line number and context line, in a stock `wx.ListBox`. Enter jumps to a match; the dialog stays open so the user can iterate. The cell at the bottom shows `Match 3 of 17`.
- `Ctrl+H` opens Replace. Options: case sensitive, whole word, regex, **in selection** (pre-checked when a selection is present on open). Replace, Replace All, Find Next, Find Previous buttons. Replace All reports `Replaced 12 occurrences`. Undo is one step.
- `Esc` from any Find or Replace dialog closes it and returns focus to the editor at the previous cursor position (not at the last match unless the user pressed Enter).
- **"Not found"** is always spoken, never silent. After two consecutive not-found beeps, Quill suggests opening Find All to verify the term.

**History and persistence**

- Find and Replace remember the last 20 terms per session (in-memory) and the last 100 across sessions (on-disk, in `%APPDATA%\Quill\search-history.json`; cleared from a single button in Settings → Privacy). Replacement strings have their own parallel history.
- The dropdown arrow on the Find input opens history; Up/Down arrows in the input cycle through history when the input is empty.

**Incremental preview (opt-in, off by default)**

- A Settings switch `Editing → Incremental Find Preview` makes the editor preview the next match as the user types in the Find dialog (Notepad++ style). Escape returns the cursor to where it was before Find opened. Enter commits and closes. Off by default because preview-driven cursor movement can confuse screen readers; we expose it for users who prefer it.

**Predictable announcements**

- On every match Quill announces a structured one-liner: `Found on line N: <line text>`. The line text is truncated to 200 characters with an ellipsis to keep speech short. Long lines are abbreviated around the match so the matched text is always in the spoken slice.
- On wrap: `Wrapped to top` or `Wrapped to bottom`, followed by the match announcement.
- On Replace All: `Replaced N occurrences in document` or `Replaced N occurrences in selection`.
- On regex error: a single sentence, no traceback.

**Find in current selection.** When the editor has a non-empty selection at the moment Find or Replace is opened, the "In selection" checkbox is pre-checked; Replace All scopes its work to the selection. F3 and Shift+F3 continue to operate document-wide regardless, because muscle memory expects that.

**Find next while typing.** When the Find dialog is closed and the search term is set, typing in the editor does not interfere with F3; the search term is preserved until the user clears it (`Ctrl+Shift+\` or status-bar cell context menu → Clear Search).

**Project-wide Find (Find in Folder)** is deferred to v1.2.

### 5.9 Spell checking (magical, local-first)

This section was significantly expanded in v0.2 of this PRD. See [section 6](#6-spell-checking-deep-dive) for the full design and the decision rationale.

Quill ships **its own spell checking engine**, built on Hunspell dictionaries, designed from the ground up for screen-reader speed and predictability. It does **not** depend on TinySpell or any other external spell-checker process.

- `F7` opens the full Spell Check dialog (Word-style, but accessible).
- As-you-type checking is on by default. Misspellings are tracked in a sidecar model (not visual squiggles) and announced gently on word boundary if the user opts in.
- `Ctrl+;` jumps to the next misspelling and opens an inline suggestion popup (a small modal list, fully keyboard driven).
- Suggestions come from Hunspell plus an n-gram reranker trained on the user's writing for personalised top-3 suggestions.
- Personal dictionary persists per user; per-document dictionary persists in a sidecar file.
- Multiple simultaneous dictionaries: e.g. English (UK) plus a technical jargon list plus the document's own dictionary, merged with priority.
- All entirely local. No cloud round-trip ever for spell check.

### 5.10 Word count and navigation

- `Ctrl+Shift+W` reports words, characters, and paragraphs. Reports on selection if present.
- `Page Up` / `Page Down` navigate by real page markers (PDF). Announces page on move.
- `Ctrl+G` opens Go To Line, or Go To Page when page markers exist.

### 5.10 Bookmarks

- Bookmarks are **named jump points** intended for durable anchors a user wants to revisit by name.
- `Ctrl+B` sets a bookmark at the current position. Prompts for a name.
- Stored per bookmark: name, line number, column, ~120 characters of surrounding text, document path, ISO timestamp.
- `Ctrl+Shift+G` opens Bookmarks Manager.
- On jump: if the stored line still contains the surrounding text, go there. If not, search for the surrounding text and update the bookmark. If still not found, fall back to line number and announce "approximate position."
- Bookmarks for saved documents persist in `%APPDATA%\Quill\bookmarks\<hash>.json`.

### 5.11 Selection helpers and Where Am I

- `Ctrl+Shift+,` marks selection anchor; `Ctrl+Shift+.` extends selection.
- `Ctrl+Shift+I` Where Am I. In the editor: line, column, word count, modified state, page if available. In dialogs: structured description of the current field.

### 5.12 Command palette (Visual Studio Code style)

This is a centrepiece of v0.2. See [section 7](#7-command-palette-deep-dive) for the complete design.

- Single shortcut: `Ctrl+Shift+P` (also `F1`).
- Prefix-driven modes inside one input field, exactly like VS Code:
  - No prefix: command search.
  - `>` explicit command prefix (typing it is optional; a fresh palette starts in command mode).
  - `?` shows help for available prefixes.
  - `:` go to line.
  - `@` go to bookmark in current document.
  - `#` go to bookmark across all open documents.
  - `!` show warnings and errors (spell check issues, broken bookmarks, unsupported features used).
  - `<` open a recent file.
  - `~` switch open document.
  - `=` open a setting.
- Fuzzy matching with subsequence scoring, recency boost, and frequency boost (most-recently-used commands float to the top).
- Each row shows: command title, current keybinding, source (core or plugin), and a short hint.
- Right-arrow on a command edits its keybinding inline (see [section 8](#8-keymap-and-keystroke-reassignment)).
- Fully keyboard driven. Standard `wx.ListBox` underneath, with a `wx.SearchCtrl` on top. All accessible via stock screen-reader behaviour.

### 5.13 Document backups

- On every save of an existing file, the previous saved bytes are copied to `%APPDATA%\Quill\backups\<hash>\<iso-timestamp>.bak`.
- `File > Restore Document Backup` lists backups for the current document, newest first.
- Restore prompts for confirmation. Before overwriting the editor, the current buffer is backed up too.
- Restored text is marked modified; user saves with `Ctrl+S`.
- Retention: default keep last 50 per document, prune older than 90 days, never delete the most recent 5.
- Crash recovery: autosave snapshot every 30 seconds while a document is dirty; on launch, Quill offers to recover any orphan snapshots.

### 5.14 Settings

`Ctrl+,` opens Settings, organised in a `wx.Treebook`:

- **General**, **Editing**, **Reading**, **Spell check**, **PDF and AI**, **Files**, **Appearance**, **Backups**, **Keyboard** (see [section 8](#8-keymap-and-keystroke-reassignment)), **Privacy**.

### 5.15 Plugin system (v1.1)

- Plugins are Python packages discovered in `%APPDATA%\Quill\plugins`.
- Each plugin can register commands, file format readers and writers, settings pages, palette entries, and **default keybindings** (which the user can override).
- Plugin manifest must declare network and filesystem use.

### 5.16 Outline Navigator (heading tree)

One of Quill's signature productivity wins for readers and writers. Opens a tree of every heading in the current document, fully accessible, and lets the user jump anywhere in two keystrokes.

- `Ctrl+Shift+H` opens the Outline Navigator. The window contains a filter `wx.SearchCtrl`, a `wx.TreeCtrl` of headings, and standard OK/Cancel/Jump buttons. Everything stock; screen readers handle it natively.
- The outline is computed deterministically per format:
  - **Markdown**: ATX (`#`) and Setext (`===`, `---`) headings, parsed via `markdown-it-py` AST.
  - **HTML/XHTML/MHTML**: `<h1>`…`<h6>` and `<section><h*>` patterns via `beautifulsoup4`. ARIA `role="heading" aria-level="n"` is honoured.
  - **reStructuredText**: title underline conventions via `docutils`.
  - **AsciiDoc**: `=` through `======` lines.
  - **Org-mode**: `*` through `******` lines.
  - **LaTeX/Typst**: `\part`, `\chapter`, `\section`, `\subsection`, `\subsubsection`, `\paragraph`; Typst `= heading` syntax.
  - **DOCX**: paragraphs styled Heading 1–9 (via `python-docx`).
  - **EPUB**: `nav.xhtml` first, falling back to `toc.ncx`.
  - **PDF**: embedded document bookmarks (the same tree shown in Adobe Reader's bookmarks pane); also synthesised from font-size analysis when no bookmarks exist (opt-in, off by default).
  - **DAISY**: navigation document.
  - **Subtitle files**: chapter markers if present; otherwise time-bucketed sections every five minutes.
  - **Jupyter notebooks**: each Markdown heading inside Markdown cells, plus a synthetic node per cell.
  - **Generic fallback**: lines that look like headings (ALL CAPS short lines, numbered sections like `1.`, `1.1`) are offered as a flat list with a warning that the document has no real structure.
- Tree behaviour:
  - Up/Down arrow navigates between headings. Right Arrow expands; Left Arrow collapses. `*` (numpad or shift+8) expands all descendants of the focused node.
  - Typing in the filter field narrows the visible tree to headings whose text matches (substring, case-insensitive). The first match is announced. `Tab` returns focus to the tree.
  - `Enter` jumps the editor to the selected heading, closes the dialog, and announces `Jumped to heading level 2: <text>`.
  - `F2` renames the heading in place (editable formats only) and updates the document.
  - `Ctrl+C` copies the heading title; `Ctrl+Shift+C` copies the path (`Chapter 3 › Section 2 › Subsection 1`).
- The Outline Navigator also lives in the command palette under the `#` prefix when the current document has structure, so headings appear inline with document switching.
- Targets: build the tree for any text-based document up to 1 MB in under 50 ms; up to 10 MB in under 500 ms.

### 5.17 Jump-by-structure shortcuts

In-editor navigation by document structure, alongside the Outline dialog:

- `Ctrl+PgDn` / `Ctrl+PgUp`: next / previous heading of any level. Announces `Heading level 2: <text>`.
- `Ctrl+Alt+1` through `Ctrl+Alt+6`: next heading of level 1–6. `Ctrl+Alt+Shift+1–6` for previous.
- `Ctrl+Alt+0`: jump to the next paragraph that is not a heading (useful for skimming).
- `Ctrl+]` / `Ctrl+[`: next / previous block boundary (code fence, list, table, blockquote) in Markdown and HTML.
- `Ctrl+Alt+B`: jump to the start of the current logical block; `Ctrl+Alt+E` to the end.
- All shortcuts reassignable.

### 5.18 Line and block operations

VS Code-style editor productivity, all standard text-control operations:

- `Alt+Up` / `Alt+Down`: move the current line (or all selected lines) up or down. Announces the swap.
- `Ctrl+Shift+D`: duplicate the current line or selection.
- `Ctrl+Shift+K`: delete the entire current line.
- `Ctrl+L`: select the current line (repeat to extend by line).
- `Ctrl+J`: join the current and next line with a single space.
- `Tab` / `Shift+Tab` on a multi-line selection: indent or outdent.
- `Ctrl+/`: toggle line comment using the current document's comment marker (`#`, `//`, `<!-- -->`, etc.).
- `Ctrl+Shift+/`: toggle block comment where supported.
- **Tools menu**: Sort Selected Lines (ascending/descending, case-sensitive option, natural-numeric option), Remove Duplicate Lines, Reverse Lines, Trim Trailing Whitespace, Convert Indent (tabs↔spaces), Normalize Whitespace, Wrap to Column N.
- **Smart list continuation** (Markdown, opt-in): pressing Enter on a `-`, `*`, or `1.` line continues the list and increments numeric markers; pressing Enter on an empty list item ends the list.
- **Bracket and quote auto-pair** (off by default; per-format toggle in Settings). Never enabled in plain text.

### 5.19 Document statistics and reading metrics

Local, instant, never sends content anywhere.

- `Ctrl+Alt+S` opens the Document Statistics dialog.
- Reports: characters with and without spaces, words, sentences, paragraphs, lines, headings per level, links, images, code blocks, tables, footnotes.
- Estimated reading time at a configurable rate (default 200 wpm) and speaking time (default 150 wpm).
- Readability scores: Flesch Reading Ease, Flesch–Kincaid Grade Level, Gunning Fog, SMOG, Automated Readability Index. Each line in the dialog is a separate `wx.StaticText` so screen readers can read them one at a time.
- Longest sentence (with click-to-jump), average sentence length, longest paragraph.
- If a selection exists, statistics report on the selection and the title says so explicitly.
- Status bar shows running word count for the current document or selection.

### 5.20 Accessibility auditor

Quill's audience is exactly the audience that needs to _produce_ accessible documents. v1.0 ships a first-class auditor.

- `Ctrl+Alt+A` runs an Accessibility Audit on the current document and opens the Issues dialog. (The same list is reachable via the command palette `!` prefix.)
- **Markdown and HTML** checks: heading-level skips (h2 to h4), missing or empty `alt` text on images, `alt` text equal to the filename, generic link text (`click here`, `here`, `read more`, `link`), empty links, duplicate link text pointing to different targets, tables without header rows, deeply nested lists (>5), paragraphs longer than 500 words, missing `lang` attribute on `<html>`, missing page title.
- **DOCX** checks: missing alt text on inline images, heading-style skips, generic link text, tables without header rows, document language not set, missing title.
- **PDF** checks (informational): whether the PDF has any tagged structure, presence of embedded bookmarks, image-only page count, language metadata, password protection.
- **Markdown front-matter** checks: required keys present (configurable per project).
- Issues panel: list with severity (error/warning/info), location, message, and “Why this matters” explanation. `Enter` jumps to the issue, `Delete` dismisses for the session, `Ctrl+I` ignores the rule in this document (persisted in the document's sidecar).
- Two companion catalogs:
  - **Alt-text catalog** (`Ctrl+Alt+I`): every image with its current alt text, edit in place for editable formats, jump-to-source.
  - **Link inventory** (`Ctrl+Alt+L`): every link with target and accessible name; flags duplicates and internal-vs-external; copy URLs.
- Audit completes in under 200 ms for documents up to 100 KB; up to 5 s for documents up to 5 MB.

### 5.21 Table mode for Markdown and HTML tables

When the editor cursor enters a Markdown pipe table, a Markdown grid table, or an HTML `<table>`, Quill enters Table Mode and announces it.

- `Ctrl+Shift+Right` / `Ctrl+Shift+Left`: next or previous cell; the column header is announced first, then the cell content (`Column "Price": $4.99`).
- `Ctrl+Shift+Down` / `Ctrl+Shift+Up`: next or previous row in the same column.
- `F2`: open the current cell in a small editor dialog with the column header in the title.
- `Ctrl+Alt+T`: insert a row below; `Ctrl+Alt+Shift+T`: insert a column after.
- `Ctrl+Alt+R`: delete the current row; `Ctrl+Alt+C`: delete the current column. Both confirm.
- `Ctrl+Alt+H`: toggle the current row as the header row (Markdown only).
- Tables remain valid Markdown or HTML on save: Quill re-aligns pipes and pads columns on every edit so the underlying text stays readable as plain text.

### 5.22 Editor essentials

A group of small, individually unremarkable features whose absence would feel cheap. All ship in v1.0.

- **Encoding picker**: `File > Open With Encoding…`, `File > Reload With Encoding…`. Status bar shows the active encoding. Auto-detection on open via `charset-normalizer`; user can always override.
- **Line endings**: `File > Line Endings` (LF, CRLF, CR). Status bar shows the active style. “Convert on save” is an opt-in setting.
- **Reload from disk**: `Ctrl+Shift+R`. If the editor has unsaved changes, prompt.
- **External-change watcher**: detect when the file changes outside Quill; offer to reload (auto-reload if the editor is unmodified).
- **Insert date / time**: `Ctrl+Alt+D` (with a one-time format chooser that the user can re-open from Settings).
- **Templates**: `File > New From Template…`. Templates live in `%APPDATA%\Quill\templates\`. Ships with: Markdown article, Meeting notes, Daily journal, Letter, Issue report, README, Changelog, MIT license header, Markdown blog post with front-matter.
- **Word prediction**: `Ctrl+.` opens an IntelliSense-style picker for document words plus HTML and Markdown tag completions. It can also run automatically while typing when enabled in Settings.
- **Snippets**: per-format snippet packs with trigger + Tab expansion. `Ctrl+Alt+Space` opens Insert Snippet; `Ctrl+Alt+Shift+Space` opens Manage Snippets. Off by default in prose, on by default in code. Editable in Settings.
- **Save options** (per document and per workspace): trim trailing whitespace on save, ensure final newline, normalise line endings on save.
- **Smart paste**: by default, strip rich-text formatting when pasting from sources that include it.
- **Sessions**: `File > Save Session…` and `File > Open Session…` preserve the set of open documents and per-document cursor position.
- **Print**: `Ctrl+P` opens the system print dialog, preserving the editor font and encoding.
- **Extract to plain text**: `Tools > Save As Plain Text` works for any opened format and is the canonical way to harvest text from a non-editable source.
- **Compare two documents**: `Tools > Compare With File…` supports an interactive compare session and can also produce a unified-diff document in a new editor tab. Interactive compare mode moves the cursor between differing line groups, offers a difference list, and supports synchronized compare navigation. Diff hunks remain navigable with `Ctrl+]` / `Ctrl+[`.

### 5.23 Recent locations history (browser-style back/forward)

- `Ctrl+Alt+Left` moves back through cursor jump points; `Ctrl+Alt+Right` moves forward.
- Push triggers: Find match, F3/Shift+F3 jump, bookmark jump, outline jump, Go To Line, Go To Page, opening a document, switching documents.
- The ring holds up to 100 entries per editor, deduplicated when consecutive entries collapse to the same line.
- A small `Navigate → List Recent Locations…` dialog shows the ring as a list with document, line, and the line text; Enter jumps. Stock `wx.ListBox`.
- Each location remembers document path, line, column, and a hash of nearby text so jumps survive small edits exactly as bookmarks do (5.10).

### 5.24 Mark ring

A second, lighter-weight navigation system for power users. Inspired by Emacs but adapted to Windows muscle memory.
Marks are **temporary jump points**; bookmarks (5.10) are named and more durable.

- `Ctrl+Shift+M` sets an anonymous mark at the cursor; status bar briefly announces `Mark set`.
- `Ctrl+M` pops to the most recent mark; further presses walk back through the ring.
- `Ctrl+Shift+X` exchanges point (cursor) and mark, useful for jumping to where the user was and back.
- `Edit → Mark Ring → List Marks…` shows the ring in a stock `wx.ListBox` with document, line, column, and surrounding text snippet.
- Up to 50 marks in a circular buffer per session. Marks do not persist across sessions in v1.0.
- All keystrokes reassignable. `Ctrl+.` is reserved for Word Prediction by default, so users who rely on another screen-reader chord can reassign it; the conflict detector (8.4) flags the well-known cases at install time.

### 5.25 Read Aloud (secondary voice, not the screen reader)

Quill ships a read-aloud feature that uses a **secondary** voice the user picks from a list. It deliberately does not compete with the screen reader: the screen reader keeps doing its job while read-aloud plays, and the user can use a different voice for each so they are easy to tell apart.

- Backend: SAPI 5 voices and Windows OneCore voices via `pywin32`/`comtypes`. Detected at startup; the list is presented in `Settings → Read Aloud` and in the Read Aloud voice chooser.
- `Ctrl+Alt+P` starts/pauses read-aloud from the current cursor; `Ctrl+Alt+S` stops; `Ctrl+Alt+.` skips to the next sentence; `Ctrl+Alt+,` previous.
- Granularity: sentence by default; settings allow paragraph or word.
- Highlight follows: the editor cursor moves to the start of the currently spoken sentence so when read-aloud stops, the user is exactly where they last heard. The status bar's Read Aloud cell shows progress.
- Selection-only mode: when invoked with a selection, read-aloud reads only the selection and stops at the end.
- Voice, speed, pitch, volume all configurable. Three named profiles (Reading, Proofreading, Skim) save preferred values.
- The read-aloud voice never overrides the screen reader's announcements; if a screen reader speaks something while read-aloud is active, read-aloud continues but is briefly ducked.

### 5.25b Watch Folder automation

Quill provides an optional watch-folder workflow under `BITS Whisperer -> Dictation and Watch Folder` for low-friction
document intake. Users can point Quill at one or more folders, drop supported files into them, and have Quill
process those files automatically without leaving the editor.

The original single-folder watcher has been replaced by a multi-profile **Watch Service** built on the wx-free
`quill.core.watch_service` facade. Each watch profile is an independent rule set with its own watched folder,
recursion and polling behaviour, file filters, and action (for example: open in editor, or run an intake
action). Profiles are stored through `watch_profile_store` and validated against a schema, so an invalid or
partial profile can never start a worker.

- Multiple named watch profiles can be configured and enabled or disabled independently.
- Supported drop formats follow Quill's core supported file-extension set, optionally narrowed per profile.
- Polling, subfolder recursion, and the per-profile action are configurable from Watch Folder Settings.
- A dedicated, fully accessible **Watch Queue Monitor** (`Watch` menu) lists queued, in-progress, completed,
  and failed items so users can track and retry automation without a visual dashboard.
- Watch work runs off the UI thread through `watch_worker`/`watch_queue`; results marshal back through
  `wx.CallAfter` and surface in the status/notification channel. No silent failures.
- Watch-folder automation is configured from Preferences (Watch Folder Automation). A first-run wizard onboarding step for it is planned (see docs/planning.md).

### 5.25c BITS Whisperer phased transcription rollout

Quill integrates BITS Whisperer speech capabilities in phased increments to minimize regression risk
and preserve accessibility reliability.

Phase 1 scope:

- Keep current dictation behavior stable while introducing BITS Whisperer speech model management.
- Surface model controls under `BITS Whisperer -> Speech Models`.
- Add `BITS Whisperer -> Providers` with guided provider-center flows for staged onboarding.
- Provide machine-aware default recommendations based on local configuration.
- Include faster-whisper engine readiness checks and explicit user guidance.
- Ensure `Help -> Status Page` can remain open and refresh dynamically with speech/BITS rollout task updates.
- Add rollout-safe insight surfaces under `BITS Whisperer -> Rollout` (readiness check and capability matrix).
- Add guarded download queue controls for staged model acquisition (retry failed downloads and clear history).
- Keep advanced runtime paths staged for subsequent phases.

Phase 2+ scope:

- Expand runtime model execution paths and deeper transcription behavior.
- Broaden model-family support as quality and hardware validation mature.

### 5.25a Speech Experience Platform (planned before implementation)

This section defines the next speech milestone as a complete user-facing platform, not a single settings dialog.

Goals:

- Add a first-class **Speech** submenu under the top-level **AI** menu.
- Add two downloadable local speech engines: **Kokoro** and **Piper**.
- Keep **DECtalk** and **eSpeak NG** as bundled local engines for immediate read-aloud availability.
- Provide voice lifecycle UX end to end: discover, download, preview, set preferred, configure, remove.
- Keep installer size lean by making heavier engines download-only while preserving bundled fallback voices.
- Preserve screen-reader-first behavior with predictable announcements, keyboard-first flows, and no surprise network actions.

#### 5.25a.1 AI menu information architecture

The top-level **AI** menu gains a **Speech** submenu with discoverable, keyboard-rebindable commands:

- `AI -> Speech -> Open Speech Center...`
- `AI -> Speech -> Browse Voice Library...`
- `AI -> Speech -> Download Voices...`
- `AI -> Speech -> Preview Current Voice`
- `AI -> Speech -> Set Preferred Voice...`
- `AI -> Speech -> Manage Installed Voices...`
- `AI -> Speech -> Speech Settings...`

The Speech submenu mirrors the command palette and status surfaces, with live keybinding labels exactly like other menu items.

#### 5.25a.2 Engine model and no-bundle policy

Supported engines for this milestone:

- `windows-native` (existing SAPI/OneCore path)
- `dectalk-local` (bundled)
- `espeak-local` (bundled)
- `kokoro-local`
- `piper-local`

Policy:

- DECtalk and eSpeak NG ship with QUILL as local bundled engines.
- No Kokoro or Piper voices are bundled in installer or portable artifacts.
- Voice models are downloaded on demand into `%APPDATA%\Quill\speech\voices\...`.
- Downloads require explicit user action and clear size disclosure before start.
- Speech onboarding includes preview-first guidance and availability announcements before model download.

#### 5.25a.3 Voice library and download UX

Speech Center includes a searchable voice catalog with filters:

- engine (Windows Native, Kokoro, Piper)
- language and region
- gender/style tags where available
- size band (small/medium/large)
- installed vs not installed

Each voice row exposes:

- voice name and engine
- language and locale
- on-disk size
- install state
- preferred marker

Download behavior:

- resumable downloads with progress and remaining size
- hash verification before activation
- cancellation without corrupt partial state
- failed-download recovery with retry guidance

#### 5.25a.4 Voice preview and A/B comparison

Users can preview voices before and after install.

- Preview text field with stock sample text button
- A/B preview mode for rapid compare between two selected voices
- playback controls: play, stop, replay
- optional "Preview with current speaking settings" toggle

When pre-install preview audio is available from metadata, Quill may fetch a small sample clip on demand. If no preview clip exists, preview requires install and Quill states this clearly.

#### 5.25a.5 Preferred voice and defaults model

Users can star one voice as **Preferred** with one command.

Resolution order for active voice:

1. explicit per-document override (future-compatible field)
2. explicit per-language preferred voice
3. global preferred voice
4. engine fallback voice

Setting a voice as preferred is immediate and announced in plain language.

#### 5.25a.6 Per-voice configuration and platform defaults

Every installed voice has editable settings saved as a profile, and users can mark any profile as default.

Per-voice settings (minimum set):

- rate
- pitch
- volume
- pause style and punctuation pause behavior
- sentence/paragraph chunk size
- output device selection

Platform-aware defaults:

- Windows native voices keep their own defaults
- Kokoro and Piper voices each keep separate defaults
- users can apply "Use as default for this engine" or "Use as global default"

This gives users both broad defaults and precise per-voice control.

#### 5.25a.7 Voice removal and storage hygiene

Manage Installed Voices supports safe removal:

- remove one voice
- remove all voices for selected engine
- show reclaimed disk size before confirmation
- preserve user settings history without dangling references

If the removed voice was preferred, Quill prompts for a replacement or applies deterministic fallback and announces it.

#### 5.25a.8 Speech onboarding flow

First-time speech onboarding starts when the user opens Speech Center with no installed downloadable voices.

Flow:

1. Explain available engines and that voices are optional downloads.
2. Ask preferred language/locale.
3. Recommend starter voices for Kokoro and Piper.
4. Offer quick preview where possible.
5. Download selected voices.
6. Ask user to mark preferred voice.
7. Offer one-click "Make these settings my default".

The onboarding flow can be re-run via `Help -> Run Onboarding Again` and `AI -> Speech -> Open Speech Center...`.

#### 5.25a.9 Accessibility and safety requirements

- Every Speech Center control is a stock wx control with correct label, role, and state.
- Progress updates are announced without flooding speech output.
- No auto-downloads or silent background network actions.
- All destructive actions (remove voice, reset defaults) require confirmation.
- All errors are plain-language and actionable.

#### 5.25a.10 Delivery phases (bold, realistic)

Phase 1: Foundation

- AI menu Speech submenu
- Speech Center shell
- installed-voice management for existing Windows native voices

Phase 2: Downloadable voices

- Kokoro and Piper catalog
- download, verify, install, remove
- preferred voice and per-engine defaults

Phase 3: Advanced polish

- A/B preview panel
- storage budget manager and cleanup recommendations
- per-language preferred voice routing
- richer voice profile presets (Narration, Proofread, Fast skim)

#### 5.25a.11 Acceptance criteria

- A new user can install at least one Kokoro or Piper voice in under 3 minutes from Speech Center.
- A user can preview at least two voices and set one preferred without opening Settings.
- A user can remove a voice and recover disk space with clear confirmation and fallback behavior.
- All commands are available through menu, command palette, and keybindings.
- Installer size does not increase due to bundled voice payloads.

#### 5.25a.12 DECtalk compatibility evaluation track

Quill should explicitly evaluate adding DECtalk as an optional speech engine path.

Why consider it:

- DECtalk remains important to many long-time screen-reader and speech users.
- It offers a distinctive speech character some users actively prefer for proofreading and navigation tasks.
- Community-maintained projects (including modern build efforts) suggest practical integration paths worth exploration.

Plan scope (evaluation first, not automatic ship):

- Add `dectalk-local` as a candidate engine in Speech Center behind an experimental flag.
- Prototype voice discovery, preview, and preferred-voice selection through the same Speech lifecycle model used for Kokoro and Piper.
- Keep no-bundle policy: no DECtalk voice payloads included in installer or portable builds.

Hard gates before general availability:

- **Licensing and redistribution clarity**: legal review confirms what can be downloaded, redistributed, or user-supplied.
- **Accessibility parity**: DECtalk path must pass the same screen-reader announcement, keyboard-only, and status reporting requirements as other engines.
- **Stability and performance**: startup, preview, and long-form read-aloud must meet baseline responsiveness and failure-recovery standards.
- **Configuration parity**: preferred voice, per-voice settings, per-engine defaults, and removal behavior must match other engines.

User experience requirements if approved:

- DECtalk appears in `AI -> Speech` as another engine option, not a separate workflow.
- Voice install/onboarding language is plain and explicit about source, size, and any licensing constraints.
- Users can preview and set a DECtalk voice as preferred in one flow.
- Users can remove DECtalk voices and recover storage with deterministic fallback behavior.

Positioning:

- DECtalk is treated as a high-value compatibility and user-preference path.
- It does not replace Windows native, Kokoro, or Piper; it complements them when available and compliant.

### 5.26 Number lines and strip line numbers

A small tool that addresses a real recurring user request.

- `Tools → Number Lines…` opens a dialog with format options: `1.`, `[1]`, `1:`, `1)`, `001`, and a custom Python `str.format` template using `{n}`.
- Start index, increment, zero-padding, and "only number non-blank lines" options.
- Applies to the whole document or selection.
- `Tools → Strip Line Numbers` reverses by regex; the regex used to add numbers is also the regex used to strip them.
- Undo is one step; the tool reports `Numbered 482 lines` or `Stripped numbers from 482 lines`.

### 5.27 Open from URL

- `Ctrl+Alt+O` opens a small dialog with a URL field. Accepts `http://`, `https://`, raw GitHub URLs, gist URLs, and Pastebin URLs.
- Quill downloads the resource to a per-session temp file, detects the format from the response `Content-Type` and the URL extension, and opens it with the appropriate reader.
- Network announcement: the dialog shows the host name and an estimate of bytes (where the server reports `Content-Length`) before download starts; the download is cancellable.
- The opened document has the URL as its display path, no associated file on disk; `Ctrl+S` opens Save As.
- Redirects are followed up to 5 hops; redirects to a different host prompt for confirmation.
- All TLS errors and 4xx/5xx responses are reported with a single readable sentence, no stack traces.

### 5.27a Remote Sites (FTP, SFTP, HTTPS, WebDAV, S3)

Remote I/O is the natural extension of "Open from URL": once a user has a saved site, opening and saving is one click, with the same explicit-safety guarantees.

- **File menu → Open from Remote** (default key: QUILL key then `R`) opens a two-pane site list + remote directory browser. Sites are sorted alphabetically; the user can search/filter. The dialog uses native wx controls; the directory pane is a stock `wx.ListCtrl` so screen readers can read filenames in order with no synthesized markup.
- **Save to Remote** (QUILL key then `Shift+R`) and **Save Copy to Remote...** (menu only) use the same dialog in a "Save" mode that includes a target file name field.
- **Manage Remote Sites...** (QUILL key then `Shift+M`) opens the site list editor with **New site...** / **Edit site...** / **Delete site** buttons and a per-protocol sub-dialog (FTP, SFTP, WebDAV, S3) that validates required fields before enabling Save.
- A **site** is `RemoteSite(id, name, protocol, host, port, username, root_dir, trust_first_use, extra)` with protocol-specific fields in `extra` (e.g. `s3_bucket`, `webdav_base`, `s3_endpoint`, `s3_region`, `s3_access_key`, `s3_secret_key`). Sites are persisted to `%APPDATA%\Quill\remote-sites.json` via atomic write; passwords are persisted separately through `quill/core/remote_sites.py` using the Windows Credential Manager → DPAPI file → macOS Keychain ladder.
- **Five transport modules** live in `quill/io/`, all wx-free:
  - `remote_transport.py` — `RemoteTransport` ABC + `RemoteEntry`, `DownloadResult`, `RemoteTransportError`/`RemoteAuthError`/`RemoteNotFoundError`, `chunked_copy`, `merge_headers`.
  - `http_transport.py` — `download_url(url, *, timeout, progress, max_bytes) -> HttpDownload` with verified TLS, default `_MAX_BYTES` cap, visible progress.
  - `ftp_transport.py` — FTP and FTPS open/save, MLSD time parser, listing normalization.
  - `sftp_transport.py` — paramiko SFTP open/save; honours `settings.ssh_trust_first_use` and `paramiko.AutoAddPolicy`.
  - `webdav_transport.py` — depth-1 `PROPFIND` directory listing, basic auth, parsed through `quill.core.safe_xml.fromstring` to refuse DTD/entity expansion.
  - `s3_transport.py` + `s3_sigv4.py` — manual AWS SigV4 signer for Amazon S3 and any S3-compatible endpoint; boto3 path is opportunistic and falls back to the signer when boto3 is missing.
- A document opened from a remote site is **read-only by default**; the title shows `(from site:path)` so the user always knows where it came from. `Save` on a read-only remote document opens **Save Copy to Remote...** instead of overwriting the remote.
- Network egress is gated by `quill/tools/network_egress_audit.py`; every transport call site has a written rationale. The audit is a CI gate.
- All `Save to Remote` writes use the SSH-style tilde backup: a copy of the previous file lives next to the target as `<name>~`, written in the original newline style.

### 5.28 Format-aware bracket and quote navigation

- `Ctrl+]` and `Ctrl+[` already navigate by block in editor-mode (5.17); when inside a code-aware context (code file, Markdown code fence, HTML tag), they instead jump to the matching bracket, quote, fence, or HTML tag.
- `Ctrl+Shift+\` is the explicit "Match Bracket" command (also reachable from Navigate menu).
- `Ctrl+Shift+]` extends the selection from the cursor to the matching bracket.
- Bracket matching is language-aware: respects strings and comments in supported languages; Markdown respects fence boundaries.
- The match is announced as `Matched bracket on line N, column C` so screen-reader users do not lose context.

### 5.29 Format menu (text transforms, no styling)

A dedicated menu surfacing transforms that are otherwise reachable via Tools or shortcuts. The menu exists because discoverability matters more than purity.

- Capitalisation: Upper Case, Lower Case, Title Case, Sentence Case, Toggle Case.
- Lines: Move Line Up/Down, Duplicate Line, Delete Line, Join Lines, Toggle Line Comment, Toggle Block Comment.
- Indent: Indent, Outdent, Convert to Tabs, Convert to Spaces, Set Indent Width….
- Markdown helpers: Insert Heading (levels 1–6), Insert Bullet List, Insert Numbered List, Insert Task List, Insert Table…, Insert Link…, Insert Code Block, Insert Footnote.
- Markdown list editing behavior: `Enter` continues bullet/numbered/task items, `Enter` on an empty marker exits the list, and `Tab`/`Shift+Tab` nest or promote list items when the caret is on a list line.
- List Manager: `Format -> List -> List Manager...` (`Ctrl+Alt+L`) opens a keyboard-first tree editor for moving, promoting/demoting, adding, editing, and deleting list items.
- Magical tag helpers: Insert HTML Tag… (with attribute picker) and Insert Markdown Tag… (semantic snippet picker).
- Snippet helpers: Insert Snippet… (`Ctrl+Alt+Space`) and Manage Snippets… (`Ctrl+Alt+Shift+Space`) with searchable filtering, placeholder prompts, and starter-pack onboarding.
- Prediction helpers: Word Prediction… (`Ctrl+.`) with words, HTML tags, and Markdown tag completions.
- Surface-aware formatting shortcuts (Markdown/HTML only): `Ctrl+B` bold, `Ctrl+I` italic, and heading levels `Ctrl+Alt+1` through `Ctrl+Alt+6`.
- Re-flow: Wrap to Column…, Re-flow Paragraph.

### 5.29a Magical HTML and Markdown tag picker

- `Format → Insert HTML Tag…` opens a keyboard-first picker of common tags (`section`, `article`, headings, list/table tags, inline emphasis, links, images, code).
- After selecting a tag, Quill prompts for optional attributes in a compact `key=value; key2=value2` format and inserts valid tag text into the editor.
- If text is selected, Quill wraps the selection in the chosen non-void tag. If not selected, Quill inserts an opening/closing pair and places the cursor between them. Void tags (`img`, `br`, `hr`, `input`) are inserted self-closing.
- `Format → Insert Markdown Tag…` opens a semantic picker (`Bold`, `Italic`, `Inline Code`, `Code Block`, `Heading`, `List`, `Task List`, `Blockquote`, `Link`, `Image`, `Table`, `Footnote`) and inserts the matching markdown snippet.
- For Link and Image, Quill asks for the target URL and composes the final markdown in one action.
- All picker actions are mirrored in the command palette and are keybindable through the keymap system.
- `Edit → Insert Link…` (`Ctrl+K`) uses a format-aware inserter: markdown links in Markdown docs, `<a href>` in HTML docs, and `text (url)` form in plain text.

### 5.29b Snippet insertion and trigger expansion

- Snippets are stored locally under `%APPDATA%\Quill\snippets\snippets.json` with atomic writes.
- `Format → Insert Snippet…` opens the same keyboard-first searchable picker pattern used across Quill insertion flows.
- Supported placeholders in snippet bodies: `${input:name}`, `${choice:a|b}`, `${date}`, `${time}`, `${cursor}`.
- Trigger expansion can run while typing (for example `;meeting` plus a delimiter), and remains user-controllable via General Preferences.
- Starter packs are installable from Preferences and snippet management so onboarding can begin with practical templates.

### 5.29c Word prediction and tag IntelliSense

- `Ctrl+.` opens a prediction picker that reuses the same accessible searchable-pattern UX as other insertion dialogs.
- Predictions draw from the current document words, the merged spell dictionaries, and the HTML/Markdown tag vocabularies Quill already ships.
- When enabled in General Preferences, the same helper can auto-refresh while typing so the prediction list follows the current fragment.
- Accepting a prediction inserts the chosen word or tag completion at the caret; Escape dismisses the popup without changing text.

### 5.30 Bookmark export and import

- `Tools → Bookmarks → Export…` writes the bookmark set for the current document to a single JSON file alongside its hash so it round-trips cleanly.
- `Tools → Bookmarks → Import…` adds bookmarks from a file, with a preview dialog showing each bookmark and a per-row checkbox.
- Conflict resolution: on import, identical names produce a numbered suffix; identical positions are merged.
- A second action, `Tools → Bookmarks → Export All…`, writes every bookmark across every document the user has ever opened, useful for moving machines.

### 5.31 Trusted locations (Office-style)

- `Settings → Privacy → Trusted Locations` is a list of folders Quill opens without extra prompts.
- Files opened from outside trusted locations that are unusually large (default >25 MB), password-protected, or in a Grade B/C format show a one-time prompt: `Open <path>?` with Open, Open and Trust this folder, Cancel.
- Network-mounted folders are never auto-trusted; a setting must enable them explicitly.
- The trusted locations list is editable, exportable, and importable.

### 5.32 Jump List and shell integration

- Windows Taskbar Jump List shows Recent Files (last 10) and Pinned Files; Tasks include `New Document`, `Open File…`, and `Open from URL…`.
- Implementation via `pywin32`'s `ICustomDestinationList`.
- Shell context menu entries (registered from `Settings → Files`):
  - `Open with Quill` for every registered extension.
  - `Open with Quill (As Plain Text)` for every text-like extension, forcing the plain-text reader regardless of detected format.
  - **Open Folder With Quill** is deferred to v1.1 (it implies a folder-tree panel).
- All shell verbs install per-user (no admin elevation required) and uninstall cleanly.

### 5.33 Diagnostics and bug reporting

- `Help → Report a Bug…` is the unified support flow. It opens an in-app review screen with the report summary and destination URL, supports optional diagnostics zip generation, copies the environment summary to the clipboard, and then opens a pre-filled Community Access support-hub issue form in the default browser with no logs; the user reviews and submits manually.
- `Help → Save Diagnostics…` remains available for standalone diagnostics export and writes a zip with:
  - the last 7 days of logs (action names and outcomes only; no document content),
  - settings (with API keys redacted),
  - the active keymap,
  - the last 50 commands executed,
  - the screen-reader detection result and version (if available),
  - basic environment info (Windows build, Python build, wxPython build, locale).
- Nothing leaves the machine. The user chooses where to save the zip and what to do with it.

### 5.34 Welcome and Keyboard Reference

- **Welcome** opens a tutorial document in a new tab that walks new users through the editor, command palette, outline navigator, find/F3, spell check, and accessibility audit. The document is editable; users can save their own annotated copy.
- **Keyboard Reference** is auto-generated from the current keymap and opens as a Markdown document in the editor. It is grouped by menu, includes the "when" context for each binding, and updates the next time the user opens it after any rebind. Because it is just a document, users can search it with Find, jump with the Outline Navigator, and print it.
- **Tip of the Day** is off by default; when on, it appears once per launch as a small dismissible dialog with a single tip drawn from real palette actions, each tip a one-liner with a `Try it` button that runs the action.

### 5.35 Notifications centre

- The status bar's **Notifications** cell holds Quill's announcements: available updates, recovered autosave snapshots offered on launch, finished AI tasks, finished long-running OCR or extraction jobs, and any plugin messages.
- `Enter` on the cell opens a small Notifications dialog (stock `wx.ListBox` with timestamps); Delete dismisses individual entries; `Shift+Delete` dismisses all.
- Quill never raises toast or balloon notifications. All asynchronous events surface here and on the status bar's Background Tasks cell.

### 5.36 "What changed on save" (opt-in)

- Off by default. When on (`Settings → Reading → Announce save summary`), every successful save announces a one-liner: `Saved chapter-7.md, 4 lines changed, 38 words added`.
- Computed by diffing the previous saved bytes against the new bytes; cheap on documents up to 5 MB.
- Useful for ambient awareness during long editing sessions; trivially ignorable for users who prefer silence.

### 5.37 Link tools

A small family of related commands that make working with links comfortable for screen-reader users.

- **Insert link** (`Ctrl+K`): opens a small dialog with URL and display text fields. If a URL is on the clipboard, the URL field is pre-filled. If a selection exists, it becomes the display text. Enter inserts `[text](url)` in Markdown, `<a href="url">text</a>` in HTML, a plain URL in plain text, and a properly escaped link in reStructuredText, AsciiDoc, Org, and Textile. Cancel restores the cursor.
- **Insert quoted text** (`Ctrl+Shift+>`): indents the selection by one level of `>` for Markdown and email-style replies. `Ctrl+Shift+<` dedents one level. `Tools → Strip Quote Markers` removes them entirely. Idempotent: re-indenting a block already at level N goes to N+1, not back to 1.
- **Follow link** (`Ctrl+Enter`): when the cursor is on a Markdown link, HTML `href`, or a plain URL, opens it in the default browser. The status bar announces the destination host first (`Opening github.com…`) so the user always knows what they are about to open. Anchor links inside the current document jump in-editor instead.
- **Reveal link target** (`Ctrl+Shift+Enter`): announces the target without opening it (`Link target: https://example.com/path`).
- **Copy link target** (`Ctrl+Alt+K`): copies the URL of the link under the cursor.

### 5.38 Document properties and front-matter

- **Document properties dialog** (`File → Document Properties…`): edit document language (BCP-47 tag), title, author, description, keywords. For DOCX, EPUB, HTML, ODT these write into the document's metadata in place; for plain text, Markdown, reStructuredText, AsciiDoc, Org, and Typst they write into a sidecar `<filename>.quill.yml`. The document language drives the spell-check dictionary stack automatically.
- **Front-matter editor** (`Ctrl+Alt+F`): when the cursor is in or above YAML or TOML front-matter (Jekyll, Hugo, Zola, Quarto, Pandoc styles), opens a structured editor. Each key becomes a labelled `wx.StaticText` plus `wx.TextCtrl` pair. Save writes back as valid YAML or TOML, preserving comments and ordering wherever possible. New keys can be added; required keys (configurable per project) are highlighted.
- The front-matter editor recognises common keys (`title`, `date`, `author`, `tags`, `categories`, `draft`, `slug`, `description`, `lang`, `permalink`) and gives them sensible widgets (date picker for dates, multi-line for description, etc.). Unknown keys get a plain text field.

### 5.39 Autosave control and persistent undo

- **Autosave** is on by default at 30-second intervals. The status bar gains an **Autosave** cell showing `Autosave: 30 s` or `Autosave: off`. Enter cycles 15 s, 30 s, 60 s, 5 min, off. Settings dialog exposes the same plus a custom interval.
- **Persistent undo** keeps each document's undo stack alongside its autosave snapshots. Reopening a recently closed document restores up to 100 undo steps. Off by default for plain-text files larger than 5 MB. Stored in `%APPDATA%\Quill\undo\<hash>.undo`, atomically written, auto-pruned at 30 days.
- **Crash-safe autosave**: snapshots write to `…snap.tmp` and rename to `…snap` on flush so a power loss mid-write cannot corrupt the recovery store.

### 5.40 Paragraph, line, and footnote refinements

- **Join paragraph** (`Ctrl+Shift+J`): collapses a wrapped paragraph (the kind produced by plain-text email or older PDF extracts) into a single line, preserving sentence-internal spacing. Works on the current paragraph or selection. Idempotent.
- **Move line preserves selection**: `Alt+Up` / `Alt+Down` (line move, 5.18) keep the same logical selection range so the user does not lose context after moving.
- **Markdown heading auto-numbering** (`Tools → Toggle Heading Numbers`): adds `1.`, `1.1`, `1.1.1` prefixes across all headings, re-numbering in document order. Re-running removes them. Idempotent. Works in HTML, AsciiDoc, reStructuredText, Org, Typst as well.
- **Footnote helper**:
  - `Ctrl+Alt+.` (period) inserts a Markdown footnote pair at the cursor and jumps the cursor into the definition block; pressing `Ctrl+Alt+.` again returns to the reference site.
  - `Tools → Renumber Footnotes` reorders footnote labels into document order (1, 2, 3…), updating both references and definitions.
  - The same command works for reStructuredText auto-numbered footnotes (`[#]_`) and Pandoc-style inline notes.

### 5.41 Search-and-replace preview and saved searches

- **Replace preview**: when a Replace All would change more than 25 occurrences (threshold configurable), Quill shows a preview dialog listing up to the first 50 changes with line numbers and before/after text. Buttons: Replace All, Cancel, Replace Selected (in case the user unticks rows). Always shows the total count.
- **Saved searches**: a search term plus its options (case, whole word, regex, in-selection) can be saved under a name via `Find → Save This Search…`. `Ctrl+Shift+F3` opens the saved-search picker (stock `wx.ListBox`); Enter runs it as if F3 had been pressed. Stored in `%APPDATA%\Quill\saved-searches.json`, exportable/importable.

### 5.42 Sort and transform details

`Tools → Sort Selected Lines…` and the related transforms (5.18) are spec'd here in full:

- Direction: ascending or descending.
- Case sensitivity: on or off.
- Numeric mode: lexicographic (`item10` before `item2`) or natural-numeric (`item2` before `item10`).
- Date-aware mode: parse leading ISO-8601 or `dd/mm/yyyy` dates; sort chronologically.
- Header row: preserved as the first line if checked.
- Stable sort always; equal lines preserve their relative order.
- Remove Duplicate Lines: optional "keep first" vs. "keep last"; reports `Removed 13 duplicate lines, 287 remain`.
- Reverse Lines: simple reverse, preserves blank lines.

### 5.43 Save All with conflict detection and per-file format memory

- **Save All** (`Ctrl+Alt+S` reserved; default is `Ctrl+Shift+Alt+S` so it doesn't clash with Document Statistics) saves every modified document. If the external watcher detects that one or more files changed on disk since they were opened, Save All opens a per-file resolution dialog: Keep Mine, Take Theirs, Open Diff. Defaults to Keep Mine with no destructive action until the user confirms.
- **Per-file format memory**: Quill remembers per-path the user's last choices for encoding, line endings, wrap, indent width, tabs-vs-spaces, and spell-check language. On reopening the file those settings are restored. Setting toggle: `Settings → Files → Remember per-file format choices` (on by default). Storage in `%APPDATA%\Quill\file-prefs.json`, keyed by SHA-1 of the path.

### 5.44 Per-document scratchpad

- `Ctrl+Alt+N` opens a small non-modal Scratchpad window tied to the current document. The Scratchpad is a second `wx.TextCtrl` with its own save and word count.
- Each scratchpad is persisted at `%APPDATA%\Quill\notes\<hash>.md` keyed by document path.
- When the underlying document is moved or renamed, Quill detects the orphan note next time the document is opened and offers `Re-attach note to current document?` (Yes / No / Show note).
- Scratchpads use the same spell-check stack as their parent document but are excluded from accessibility audits.

### 5.45 Section folding (announce-only)

A folding model designed for screen-reader users: folded ranges are summarised aloud and never visually hidden in a way that confuses the cursor.

- `Ctrl+Shift+[` folds the section starting at the heading on or above the current line into a single summary line: `Section "Background" — 14 lines hidden`.
- `Ctrl+Shift+]` unfolds the section at the cursor.
- `Ctrl+Shift+K Ctrl+Shift+0` folds all sections to a given level (chord sequence); `Ctrl+Shift+K Ctrl+Shift+J` unfolds all.
- Folding state is per-session and never written to file.
- Find still finds matches inside folded ranges and automatically unfolds on jump.
- Outline Navigator (5.16) is the primary navigation tool; folding is the in-editor companion.

### 5.46 Spell-check ignore directives and manual bilingual flag

- **Per-document ignore directives**. Quill honours a magic comment that lists words to ignore in this document only:
  - HTML / Markdown: `<!-- quill: ignore-spell "frobnicate", "wibble" -->`
  - Plain text and code (using the file's comment marker): `# quill: ignore-spell frobnicate, wibble`
  - YAML / TOML front-matter: `quill_ignore_spell: [frobnicate, wibble]`
- The ignore set is merged into the active dictionary stack as a transient per-document layer.
- **Manual bilingual paragraph flag** (`Ctrl+Alt+B`): toggles a per-paragraph language override. The user types or picks a BCP-47 tag; the paragraph is marked in the sidecar `.quill.yml`; the spell-check stack swaps for that paragraph. Per-paragraph auto-detection remains in the backlog; this manual flow is reliable today.

### 5.47 Word boundary mode, trailing whitespace, case-change announcement

- **Word boundary mode** (`Settings → Editing → Word Boundary Mode`):
  - **Default**: Unicode word breaks (UAX #29). Best for prose.
  - **Whitespace**: only whitespace separates words. Best for log files.
  - **Programmer**: also breaks on `_`, `-`, `.`, and case transitions (`getFoo` is three "words": `get`, `Foo`, plus the case boundary). Best for code.
- The mode affects `Ctrl+Left`/`Right`, `Ctrl+Delete`/`Backspace`, double-click selection, word count, and the spell-check tokeniser.
- **Trailing whitespace announcement**: when the cursor lands on a line that ends with trailing whitespace, the status bar's Line/Column cell appends `(trailing whitespace)` and a screen-reader-friendly hint is available via Where Am I. No visual highlight; no extra speech while typing.
- **Case-change announcement guard**: when `Ctrl+U`, `Ctrl+L`, or `Ctrl+Shift+T` apply to the whole document because nothing was selected, the announcement explicitly says so and reminds the user `Press Ctrl+Z to undo full-document case change`.

### 5.48 Multi-format export and reading view

- **Export panel** (`File → Export…`): one dialog with target format choices: HTML, DOCX, plain text, Markdown, reStructuredText, and PDF (via Markdown → HTML → system print-to-PDF). Per-format options inline (heading numbering, table-of-contents inclusion, embedded CSS yes/no, page size for PDF).
- **Reading view** (`View → Toggle Reading View`): toggles the editor between source view and a clean reading representation for HTML and Markdown. Still a `wx.TextCtrl` — same accessibility, just a different render: links unwrapped to `text (url)`, headings prefixed by their level, lists rendered with consistent markers, code blocks framed by a horizontal rule. Editing is disabled in reading view (the cell announces this); toggle off to edit.

### 5.49 Welcome-back snapshot

- On launch, if the user closed Quill cleanly with N documents open last time, a single prompt offers `Reopen the 3 documents from your last session?` with Yes / No / Show me.
- "Show me" opens a small list of the documents (paths, last cursor positions) and lets the user pick a subset.
- Always opt-in per launch; the global "restore session" setting is separate and stays off by default.

### 5.50 Per-document keymap override (with explicit consent)

- A document's sidecar `.quill.yml` may declare a `keymap_override` block.
- Quill never applies it silently. On opening such a document, the user sees a one-time confirmation: `This document requests a different keymap. Apply for this document only?` with Yes / No / Always for this document. The decision is remembered per-document path.
- Overrides are scoped: they only apply while the document has focus, never global.
- A small lock icon appears in the document name status-bar cell (announced as `keymap override active`) whenever an override is in effect.

### 5.51 Settings export, import, and partitioned reset

- `Settings → Export…` writes a single zip containing settings, keymap, templates, snippets, personal dictionary, saved searches, and bookmarks. API keys are excluded; the user is told so explicitly in the dialog.
- `Settings → Import…` previews every change in a stock `wx.ListBox` and requires Enter to commit. Conflicts (e.g. a keymap rebind that contradicts the current keymap) are flagged inline.
- `Settings → Reset to Defaults…` opens a partitioned reset dialog with checkboxes for: Keymap, Appearance, Spell-check learning, Templates and snippets, Recent files, Bookmarks, Everything. Never silent; every reset shows a confirmation listing what will be lost.

### 5.52 Document fingerprint

- Every saved document has a SHA-256 fingerprint of its bytes shown in `File → Document Properties…` and copyable from a button.
- Useful for accessibility certification workflows where the user must prove they reviewed a specific version, and for forensic comparison.
- The fingerprint also surfaces in the diagnostics bundle (5.33) for any open document, scrubbed of path.

### 5.53 Unicode insert

- `Ctrl+Alt+U` opens a search dialog over the Unicode name database (`unicodedata` from the standard library). Type any part of a character name; matching characters appear in a stock `wx.ListBox` with code point, name, and the literal character.
- Categories shown as one-line filters: Letters, Marks, Numbers, Punctuation, Symbols, Separators, Other. Click or type the category prefix to scope.
- Pinned favourites for common needs: em-dash, en-dash, ellipsis, smart quotes, currency symbols, mathematical operators.
- Recent characters list keeps the last 20.

### 5.54 Idle-time prefetch

- When the user opens a file from a folder, Quill background-extracts the next and previous files alphabetically into the in-memory document cache so opening them feels instant.
- Bounded by available memory and by a hard cap of 50 MB total prefetch.
- Cancelled immediately on any other extraction or AI task.
- Opt-out switch in `Settings → General → Prefetch neighbouring files`.

### 5.55 Atomic on-disk stores

- All Quill-managed JSON stores (bookmarks, settings, keymap, recent, saved searches, file prefs, notes index) write to `<store>.tmp` and rename atomically.
- A `<store>.bak` is kept of the last good version. On startup, if the primary store fails to parse, Quill renames it to `<store>.broken-<timestamp>.json`, falls back to the `.bak`, and announces `Recovered <store> from backup`.
- This eliminates the worst class of "my bookmarks vanished after a crash" bugs.

### 5.56 First-run onboarding

A five-step welcome flow the first time Quill launches. Each step is a normal modal page (no carousel, no animation). Skip is always available; the chosen values are written through the same Settings code path as any later change.

1. **Profile**: System, Word-like, Vim, Emacs.
2. **Theme**: System, Light, Dark, High Contrast.
3. **Spell-check languages**: multi-select from the bundled launch set; the active document language is added automatically when later opened.
4. **AI provider**: Off (default), Ollama local, Ollama Cloud, OpenAI, Anthropic/Claude, OpenRouter, Gemini, or a custom OpenAI-compatible endpoint. (Azure OpenAI is not currently supported; it is a possible future addition — see AI-15.) Providers include sensible default hosts where possible; advanced custom mode allows manual endpoint override. If a provider is picked, the API-key dialog opens when required; the key is stored via Windows Credential Manager with a DPAPI-encrypted fallback (10.11). Network is never used without explicit per-action consent.
5. **Telemetry**: confirms it stays off (default). A short plain-language sentence explains what telemetry would collect if turned on later.

The onboarding completion writes `%APPDATA%\Quill\onboarding-complete.json`. Trust and privacy consent acknowledgement is stored separately in `%APPDATA%\Quill\trust-consent.json` and is versioned so policy text updates can require re-acknowledgement. Re-running `Help → Run Onboarding Again` reopens the flow without resetting anything else.

### 5.57 Privacy summary

- A single-screen plain-language statement of what Quill does and does not send over the network. Linked from `Help → Privacy Summary` and shown once during onboarding.
- Content is audited by the cognitive-accessibility plain-language linter (9.8): Flesch ≥ 60, controlled vocabulary, one idea per sentence.
- Says explicitly: documents never leave the machine without an explicit per-action confirmation; the only outbound calls v1.0 makes without confirmation are the manual update check and the optional crash-report upload (5.71), both opt-in.

### 5.58 Licenses screen

- `Help → Licenses` opens `THIRD-PARTY-NOTICES.md` (auto-generated at build time, 10.2.4) in the editor.
- The file lists every bundled component, its version, its license text, and a one-line use justification.
- Required for procurement; required by some bundled licenses.

### 5.59 Crash recovery transparency

When Quill detects an autosave snapshot newer than the on-disk file on launch:

- The recovery dialog names the file, the snapshot timestamp, the byte count, and offers four actions: **Recover**, **Compare with on-disk**, **Discard snapshot**, **Cancel** (decide later).
- **Compare with on-disk** opens the diff view (5.22) immediately.
- The dialog is screen-reader-friendly first: every value is a separate labelled `wx.StaticText` so it reads cleanly.
- Choosing Recover writes the snapshot as a new unsaved document; the on-disk file is **never** overwritten without an explicit Save.

### 5.60 Read-only document mode

- `View → Read-Only Mode` (`Ctrl+Shift+L` by default) toggles the editor's editability without touching file permissions.
- Toggle state is per-document; announced when toggled (`Read-only mode on` / `off`).
- Status bar's **Modified state** cell shows `Read-only` while on; attempts to type are silently ignored and a single discreet announcement (`Editor is read-only; press Ctrl+Shift+L to allow editing`) fires the first time per session.
- All navigation, Find, Outline, Read Aloud, Statistics, and Accessibility Audit continue to work.

### 5.61 File-related menu helpers

- `File → Reveal in File Explorer` opens Explorer with the current file selected.
- `File → Copy Full Path`, `File → Copy File Name` copy the corresponding string to the clipboard with a confirmation announcement.
- `File → Show Containing Folder in Quill` is deferred to v1.1 (depends on the folder panel).

### 5.62 Open Recent enhancements

- `File → Open Recent` includes per-entry **Pin / Unpin** and a top-level **Open All Pinned** action.
- Pinned items are not subject to the recent-list cap (default 10) and appear at the top of the submenu.
- Pinned entries are persisted in `recent.json` and survive Clear Recent (which only clears unpinned entries).

### 5.63 Document timeline

- `Tools → Document Timeline…` opens a chronological list (stock `wx.ListBox`) of every backup and autosave snapshot for the current document, with timestamp, size, and source (save backup vs. autosave snapshot).
- Each row has **Open in new tab**, **Compare with current**, and **Restore** (with confirmation) actions.
- The backing store already exists (5.13 + 5.39); this is the unified UI on top.
- Per-document, never global.

### 5.64 Sentence and paragraph navigation

- `Ctrl+Up` / `Ctrl+Down` already navigate by paragraph (standard wx behaviour).
- `Alt+Right` / `Alt+Left` move to the next / previous **sentence** and announce the sentence text (truncated to 200 characters around the cursor for braille and speech).
- Sentence detection uses the `regex` Unicode word-boundary tables plus a per-language abbreviation list (`Mr.`, `Dr.`, `e.g.`, etc.) that ships with each Hunspell language pack and is user-extendable in Settings.
- `Ctrl+Shift+Alt+Right` / `Ctrl+Shift+Alt+Left` extend the selection by sentence.

### 5.65 Word-count goal per document

- `File → Document Properties…` gains a **Word goal** integer field (0 disables).
- The status bar's **Word count** cell appends `(243 of 1500)` when a goal is set; on crossing the threshold Quill announces `Word goal reached: 1500 words`.
- The goal is stored alongside other metadata in the document container or in the `.quill.yml` sidecar.

### 5.66 Reading position memory per document

- On close, Quill records cursor line/column and scroll offset for the current document.
- On reopen, the cursor is restored; the status bar announces `Restored to line N` on first focus into the editor.
- Storage keyed by the document's path SHA-1 in `file-prefs.json` (10.5).
- Setting toggle `Settings → Editing → Restore reading position` (on by default).
- Independent of Welcome-Back snapshot (5.49); works even when only a single document is opened directly from Explorer.

### 5.67 Compare with clipboard

- `Tools → Compare With Clipboard` runs the unified-diff machinery (5.22) with the current document as `before` and the clipboard contents as `after`.
- Useful when reviewing a single suggestion pasted from chat or email.
- Refuses if the clipboard is empty or larger than 5 MB; explains why.

### 5.68 Insert from file

- `File → Insert From File…` inserts another file's text at the current cursor without opening it as a separate document.
- Uses the same format detection as Open; for non-text formats Quill extracts plain text and confirms before inserting.
- Files over 1 MB show a confirmation dialog with the byte count and the first line of content.

### 5.69 Selection-statistics direct shortcut

- `Ctrl+Alt+Shift+S` runs Document Statistics scoped to the current selection without first opening the full-document dialog.
- Same dialog as 5.19 but with the title prefixed `Statistics — Selection`.
- Reassignable like any other binding.

### 5.70 Sound notifications and QSP sound packs (opt-in)

QUILL plays short, screen-reader-respectful audio cues (earcons) at meaningful editing moments. The system is built around **QSP (QUILL Sound Packs)**: swappable bundles that map event IDs to audio files. Playback is non-blocking, fire-and-forget, and pre-buffered so there is no perceptible lag between event and sound. Earcons supplement speech; they never replace it. (This section absorbs the former `docs/wsp.md` sound-design notes and `docs/sound-packs.md` pack guide.)

#### 5.70.1 QSP format

A `.qsp` file is a ZIP archive whose root holds `manifest.json` and the referenced WAV files. During development a directory with the same layout is accepted; the loader treats a directory and a ZIP identically. The manifest is validated at load time against `quill/core/schemas/sound_pack.json`:

```json
{
  "format": "qsp",
  "version": "1",
  "name": "Ink",
  "author": "Jeff Bishop",
  "description": "Crisp synthesised earcons for focused writing.",
  "license": "CC0",
  "events": { "abbreviation_expanded": "expand.wav", "document_saved": "save.wav" }
}
```

Any event key absent from the manifest is silently skipped (no sound, no error), which allows minimal **partial packs** that cover only a subset of events. The QSP schema places no constraint on event-key names, so a Quillin can register additional event IDs and ship its own pack.

#### 5.70.2 Event taxonomy

Canonical event IDs are defined as a `StrEnum` in `quill/core/sound_events.py` (no `wx`, no platform code). Groups: **Editing** (`abbreviation_expanded`, `abbreviation_deleted`, `snippet_inserted`, `autocomplete_accepted`, `word_corrected`), **Document lifecycle** (`document_created/saved/closed`), **Navigation** (`heading_jumped`, `table_entered`, `list_entered`, `browse_mode_on/off`), **Search** (`search_found/not_found/wrapped`), **AI and transcription** (`ai_thinking_started`, `ai_response_received`, `ai_error`, `transcription_started/stopped/word_inserted`), **Connectivity** (`ssh_connected/disconnected`), **Compare** (`compare_enter_mode`, `compare_exit_mode`, `compare_next_difference`, `compare_previous_difference`, `compare_no_more_differences`), **Indentation tones** (`indent_level_0..7_up` / `_down`), and **System** (`error`, `warning`, `sound_on`, `sound_off`). The complete table with triggers is maintained in this section's source and surfaced to pack authors via the Sound Events dialog.

#### 5.70.3 Audio file requirements

- Format: **WAV** (PCM, 16-bit, 44100 Hz, mono) — plays from memory with no decode step, the key to zero-lag earcons.
- Duration: earcons 50–150 ms; state-change sounds (browse mode, SSH) up to 300 ms; nothing longer.
- Headroom: normalize to about −6 dBFS so the volume control stays meaningful.
- OGG/MP3 are not accepted for core events because codec init adds 20–80 ms of jitter on first play.
- Every scripted earcon in a bundled pack must be **acoustically unique** — no two events share an identical sound (audited byte-wise and by manifest mapping).

#### 5.70.4 Cross-platform backend

`quill/platform/sound_player.py` auto-detects the best backend at startup: (1) `_SoundLibBackend` (BASS via the MIT-licensed `accessibleapps/sound_lib`, all platforms, native mixing); (2) `_WinsoundBackend` (Windows stdlib, serialising queue); (3) `_NullBackend`. `sound_lib` is an optional extra (`pip install quill[audio]`); absent it, QUILL falls back to `winsound` on Windows or stays silent elsewhere. Any object satisfying the `_WavBackend` protocol (`play_wav(bytes)`, `shutdown(timeout)`) can be injected, which is how tests use a synchronous recording backend.

#### 5.70.5 Module layout and posting

`sound_events.py` (enum) → `sound_pack.py` (QSP loader + validator; reads every WAV into bytes at load, zero disk I/O at play time) → `sound_player.py` (`SoundPlayer`: 80 ms per-event cooldown, mute toggle, per-event disable list) → `quill/ui/sound_manager.py` (singleton wired to settings and a custom wx event). Any module posts a sound without importing `wx`:

```python
from quill.core.sound_events import SoundEvent
from quill.ui.sound_manager import post_sound
post_sound(SoundEvent.ABBREVIATION_EXPANDED)   # thread-safe, < 1 ms, no-op if disabled
```

#### 5.70.6 Indentation tones and overlay packs

For code, an **indent-tone pack** maps the 16 `indent_level_N_up/down` events to pitched tones so the caret crossing indent levels rises and falls in pitch. Four scales ship — pentatonic, whole-tone, diatonic, chromatic — generated by `scripts/gen_indent_tones.py`. An indent-tone pack **overlays** a primary earcon pack, so the user can combine, say, the Ink earcons with pentatonic indent tones. The `indent_tone_scale` setting (empty = off) selects the scale; blank lines stay silent and hold the previous level.

#### 5.70.7 Settings, packs, and Quillins

Settings (group `accessibility`): `sound_enabled` (bool), `sound_pack_path` (text; empty = bundled **Ink** pack), `sound_volume` (0–100), `sound_events_disabled` (comma-separated IDs), `indent_tone_scale` (choice). A global mute is bound to the `sound.toggle_mute` keymap action. The bundled **Ink** pack ships in the wheel at `quill/assets/sound_packs/ink/` (generated by `scripts/gen_ink_sounds.py`). A Quillin manifest may declare a `sound_pack` directory and `sound_events` map; the runner registers those IDs with `SoundManager` at load time, and the user can silence them individually via `sound_events_disabled`.

#### 5.70.8 Safe mode

When `QUILL_SAFE_MODE=1`, `SoundPlayer.play()` is a no-op, keeping safe mode strictly minimal-resource.

### 5.71 Quiet mode

- `View → Quiet Mode` (`Ctrl+Alt+Q` by default) is a single toggle that:
  - hides the status bar (still reachable via F6 announcement only),
  - suppresses non-critical announcements (autosave summary, idle-prefetch chatter, Tip of the Day),
  - sets audio cues volume to zero for the session,
  - leaves all critical announcements intact (errors, save failures, AI completion).
- Announced on toggle (`Quiet mode on` / `off`).
- Useful for high-focus writing sessions; state is per-session and not persisted.

### 5.72 Temporary trust for untrusted-location opens

- The Trusted Locations prompt (5.31) gains a third button: **Open this time only**.
- The file opens; the folder is **not** added to trusted locations.
- Useful for one-off opens from Downloads or temp folders without expanding the trust footprint.

### 5.73 Settings search

- A search field at the top of the Settings dialog (`Ctrl+F` when focus is in Settings).
- Indexes setting key, label, description, and a synonym list maintained alongside each setting.
- As the user types, the tree filters to matching settings; the first match is announced.
- `Esc` clears the filter; `Tab` moves to the tree.
- The synonym list is gettext-translated alongside labels.

### 5.74 In-app changelog and update transparency

- `Help → Release Notes` opens a Markdown document with one section per version. Auto-generated from `CHANGELOG.md` at build time.
- The manual update dialog (5.34, 10.12) links to the release notes for the version it is offering, shows the published date when the feed provides it, and lets the user **Skip this version**, **Download**, or decide **Later**.
- Past release notes remain reachable through the document's own outline (5.16).

### 5.75 Crash-report opt-in (per recovery)

- When Quill recovers from a crash, the recovery dialog includes an opt-in checkbox: **Send crash details to the Quill team (no document content)**.
- If checked, the diagnostics bundle (5.33) is uploaded over HTTPS to a host shown explicitly in the dialog before send; the upload is cancellable and shows a progress announcement.
- Off by default; the choice is **remembered per recovery session only**, never globally — this prevents accidental long-term opt-in.
- Crash reports include logs, environment, and the last 50 commands, never document content or API keys.

### 5.76 Interactive compare mode

Quill provides two complementary comparison workflows: an accessible interactive compare session and a generated diff report.

- **Compare commands**: `Tools → Compare Documents…`, `Tools → Compare With File…`, `Tools → Compare Open Documents…`, `Tools → Compare Selection With Clipboard`, plus `Tools → Compare Options…`.
- **Core navigation**: `F8` next difference, `Shift+F8` previous difference, `Ctrl+F8` announce current difference, `Alt+F8` open Difference List, `Ctrl+Alt+F8` toggle synchronized compare navigation.
- **Interactive session**: focus stays in the active editor; moving to a difference places the cursor on the changed line and announces both sides in plain language.
- **Difference List**: a stock list control containing all differences with document names, line numbers, type, and a short preview; Enter jumps to the selected difference.
- **Compare options**: ignore leading/trailing spaces, all whitespace, blank lines, line endings, case, punctuation, repeated spaces, Markdown heading markers, HTML tag differences, and normalized Unicode.
- **Difference summary**: users may create a plain-text summary document listing all differences, options used, and short before/after excerpts.
- **Diff report**: Quill may also generate a unified-diff document in a new editor tab. Diff hunks remain navigable with `Ctrl+]` and `Ctrl+[`.
- **Extracted document compare**: PDF, DOCX, EPUB, OCR, and repaired text compare against Quill’s extracted text representation, with a warning that extraction quality may affect results.
- **Feature profiles**: interactive compare is on in Writer, Reader and Student, Office and Admin, Accessibility Professional, Developer and Power Text, and Full Quill; it is quiet in Essential.

### 5.58 Ask Quill — on-device AI chat (WebView)

Ask Quill is a conversational assistant that runs entirely on the user's machine — no cloud, no API keys. It can answer questions, write or rewrite text for the document, and run Quill commands, but it is screen-reader-first and approval-gated: nothing touches the document until the user approves it. This is the crawl-before-run 1.0 surface; a deeper native integration is future work.

**On-device backends (platform-selected).** `make_default_backend()` picks the backend by platform — Apple Foundation Models on macOS, and **llama.cpp (`llama-cpp-python`, CPU, GGUF)** on Windows and Linux. There is no server and no GPU requirement. On Windows the model runs in-process on the CPU.

- **Model manager (RAM-tiered, auto-download).** On first use the backend resolves a model: `QUILL_LLAMA_MODEL` (explicit `.gguf` path) → an existing `*.gguf` in `<app data>/models` → otherwise it downloads the RAM-appropriate model with progress announced. Machines under ~8 GB RAM get **Llama 3.2 1B**; otherwise **Phi-4-mini (Q4)**.
- **Model is a setting, not a chore.** The model choice is exposed in the AI Model settings dialog (dropdown + Download Now) and during onboarding — users are never asked to "drop a GGUF." Onboarding first asks **"Do you want to use AI?"**; the model controls only appear if they say yes. Model descriptions avoid em-dashes.
- **Graceful CPU fallback.** If the prebuilt llama.cpp hits an unsupported CPU instruction (`STATUS_ILLEGAL_INSTRUCTION 0xC000001D` — e.g. AVX2 missing under x64-on-ARM emulation such as Parallels on Apple Silicon), the backend converts the `OSError` into a plain-language message explaining that the CPU lacks AVX2 and suggesting a no-AVX / native build, instead of crashing.

**The whole chat lives in a WebView (Edge WebView2 on Windows).** Transcript, suggestions, _and the message edit field_ are all rendered as HTML in `wx.html2.WebView` — which is **Edge WebView2** on Windows (WKWebView on macOS, WebKitGTK on Linux). We deliberately render in the WebView rather than a plain list box + separate text field because it gives us formatted Markdown (the assistant's headings, lists, and code render properly) together with the browser engine's native, mature accessibility, and keeps the user in one place. `wx.html2.WebView` is a factory-created native control and cannot be meaningfully subclassed, so accessibility is driven by the **HTML we render**, via a thin wrapper (`AccessibleWebView`):

- An **ARIA live region** (`<main role="log" aria-live="polite">`) so each new message is announced automatically by NVDA / JAWS / Narrator without the user moving focus.
- An assertive `role="status"` region for transient state ("Quill is responding", "Quill responded").
- Each message is an `<article>` with a heading (the speaker), so users can navigate the transcript by heading.
- **The edit field is in the page** — a labelled `<textarea>` with a Send button. Enter sends, Shift+Enter inserts a newline. Submissions post back to Python over a **script-message bridge** (`window.quill.postMessage` ↔ `EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED`) which drives the on-device assistant directly. The wx text field only appears in the list-box fallback when no WebView backend exists.
- **Suggested prompts disappear after the first message** (like Apple Intelligence): they show on open so the user has a starting point, then hide themselves once the conversation begins so they never sit in the way of the chat.
- `lang`, viewport, readable type, and high-contrast / `forced-colors` CSS.
- The greeting is **baked into the initial page** so there is no "empty then rendered" flash on open. Messages and state changes that arrive before the page finishes loading are queued and replayed on the `LOADED` event.

**Focus lands in the web view's edit field on open (screen-reader behavior).** When the chat opens, focus is moved directly into the in-page message field (`AccessibleWebView.focus()` → focuses the `<textarea>`, via `wx.CallAfter`) rather than onto surrounding chrome — so the user "jumps into the web view" ready to type, and the screen reader starts inside the live conversation. After a reply we do **not** steal focus back (the live region already announced it); after an approval we return focus to the edit field. (Implemented in `AskQuillChatDialog.show()` / `_focus_composer()`.)

**Prism announcements (screen-reader-first).** In addition to the WebView's ARIA live region, Quill uses the **Prism (`prismatoid`) bridge on Windows** to send response text straight to the active screen reader, so the user hears new replies even without alt-tabbing to the chat. Prism never speaks over a running screen reader — its SAPI / pyttsx3 fallback is suppressed whenever a screen reader is detected.

**Approval before anything is applied.** Each turn the assistant _decides_ (`answer` / `insert` / `replace` / `run`) but never edits the document automatically. Insert/replace text and command runs are shown as a proposal with an Approve / Discard bar; focus moves to **Approve** and the screen reader is told a change is proposed. Only on Approve does Quill insert, replace the selection, or run the command. There is also Copy Last Response and labeled suggestion prompts.

**Discoverability and reliability.** Ask Quill lives under a top-level **AI** menu (Alt+I) alongside the "Use Artificial Intelligence" toggle and AI Model settings. Generation runs off the UI thread. The single-instance lock self-heals (PID + creation-time identity) so a stale lock from a crash never blocks launch.

### 5.77 Copy Tray — twelve-slot persistent clipboard

Copy Tray gives users twelve independently addressable clipboard slots that survive application restarts. Each slot holds text explicitly placed there; slots are written atomically to disk on every change.

**Motivation.** The system clipboard holds one item and is shared across every running application. Screen-reader users who work across multiple documents, do research from multiple sources, or paste recurring fragments (signatures, disclaimers, code boilerplate) lose clipboard contents constantly because any copy from any app overwrites it. Copy Tray is a private, persistent alternative.

**Core operations.**

- **Copy to slot N** — copies the current selection to slot N (1–12). Reports the slot number, optional label, and a text preview through the screen-reader bridge.
- **Paste from slot N** — inserts the slot's text at the cursor (or replaces the selection). Reports slot number and label. Supports multi-press: single=paste, double=peek, triple=open dialog.
- **Copy to Next Empty Slot** (`edit.copy_to_next_slot`) — copies the selection to the first unoccupied, unpinned slot in order 1–12. Announces which slot was used. If all slots are occupied, announces this rather than silently overwriting.
- **Search Tray Slots** (`edit.search_tray_slots`) — opens a minimal search dialog. User types a query; QUILL searches all slot text and labels and announces matches. The user can press a digit key to paste that slot directly.
- **Open Copy Tray dialog** — shows all twelve slots with slot number, optional label, and a text preview. Inline editing of content and label; auto-save on slot change. Includes Pin/Unpin button.
- **Set label** — names a slot with a short string. Labels are spoken in all subsequent announcements, visible in the dialog, and shown in the Paste from Tray submenu alongside a text preview.
- **Pin / Unpin** — marks a slot as pinned from the dialog. Pinned slots are never overwritten by next-empty routing and are announced with a "pinned" prefix.
- **Clear All Tray Slots** — empties all twelve slots after a Yes/No confirmation defaulting to No.

**Multi-press paste.** The paste chord supports three levels of intent:

| Press count | Behaviour |
| --- | --- |
| Single | Paste slot content at cursor |
| Double | Peek: announce slot content without pasting |
| Triple | Open Copy Tray dialog focused on that slot |

The press window is configurable via `multi_press_window_ms` (default 400 ms, range 100–1000 ms; found in `App > Preferences > Editing`). This lets expert users check what a slot holds before committing — useful for a crowded tray where memory may be unreliable.

**Paste submenu slot labels.** The `Edit > Copy Tray > Paste from Tray` menu shows each slot's label and a text preview inline (e.g. "1  signature — Hi, I wanted to follow..."). Screen readers read both columns when navigating the submenu.

**Status bar cell.** The `copy_tray_slots` status bar cell shows `Slots: X/12` (occupied count). Clicking it opens the Copy Tray dialog.

**Keyboard defaults.**

| Action | Default binding |
| --- | --- |
| Paste from slot 1–9 | `Ctrl+Shift+1` through `Ctrl+Shift+9` |
| Paste from slot 10 | `Ctrl+Shift+0` |
| Paste from slot 11 | `Ctrl+Shift+-` |
| Paste from slot 12 | `Ctrl+Shift+=` |
| Copy to slot 1–9 | `Ctrl+Shift+Grave, Shift+1` through `Ctrl+Shift+Grave, Shift+9` |
| Copy to slot 10 | `Ctrl+Shift+Grave, Shift+0` |
| Copy to slot 11 | `Ctrl+Shift+Grave, Shift+-` |
| Copy to slot 12 | `Ctrl+Shift+Grave, Shift+=` |
| Open Copy Tray dialog | `Ctrl+Shift+Grave, X` |

The paste bindings use the number row directly for maximum speed. The copy bindings use the QUILL-key prefix to distinguish from heading shortcuts. All bindings are reassignable via the Keymap Editor.

**Storage.** `copy_tray.json` in the QUILL user data directory. Atomic write (`os.replace`). Version-tagged JSON; corrupt files fail silently (fresh state, no crash).

**Accessibility guarantees.** Every operation announces through the screen-reader bridge: "Copied to slot 1", "Pasted from slot 3 (signature)", "Slot 5 is empty", "Slot 2: by the way" (peek). The dialog list receives focus on open. Empty and non-empty slots are announced distinctly. The clear-all confirmation defaults to No.

**Implementation map.** `quill/core/copy_tray.py` (pure model, mypy-clean; `TraySlot` with `pinned` field, `pin_slot`, `unpin_slot`, `first_empty_slot`, `search_slots`), `quill/core/multi_press.py` (MultiPressDispatcher, wx-free), `quill/ui/main_frame_copy_tray.py` (mixin: multi-press wiring, `copy_to_next_slot`, `search_tray_slots`, `_TraySearchDialog`, `_update_paste_tray_labels`), `quill/ui/copy_tray_dialog.py` (dialog with Pin/Unpin button), `quill/core/keymap.py` (24 slot commands + 4 management commands). Menu: `Edit > Copy Tray` submenu including "Copy to Next Empty Slot" and "Search Tray Slots...".

---

### 5.78 Abbreviation Expansion — TextExpander-style bare-word shortcuts

Abbreviation Expansion replaces short trigger words with longer text automatically as you type. It complements the snippet system (which requires an explicit trigger prefix) by firing on any bare word followed by a delimiter.

**Motivation.** Typing common phrases repeatedly is fatiguing and slow. TextExpander and similar tools are widely used but require separate purchase and licensing. QUILL's built-in abbreviation engine gives screen-reader users the same productivity gain with no external dependency and full keyboard control over every setting.

**How it works.** When the user types a trigger word (e.g. `btw`) followed by any delimiter character — space, period, comma, semicolon, colon, exclamation mark, question mark, closing bracket, closing brace, tab, or newline — QUILL:

1. Detects the trigger at the cursor.
2. Looks up the trigger in the library (longest match first; case-insensitive by default).
3. Replaces the trigger with the expanded text.
4. Positions the cursor as specified (at `${cursor}` if present, otherwise after the expansion).
5. Optionally plays a configured sound.
6. Announces the expansion through the screen-reader bridge.

**Default library.** Fifteen built-in abbreviations ship out-of-the-box: `afaik` → as far as I know, `afaict` → as far as I can tell, `asap` → as soon as possible, `atm` → at the moment, `btw` → by the way, `fwiw` → for what it's worth, `imo` → in my opinion, `imho` → in my humble opinion, `irl` → in real life, `omw` → on my way, `tbh` → to be honest, `tbc` → to be confirmed, `tbd` → to be determined, `ttyl` → talk to you later, `wrt` → with regard to. These are declared as `_BUILTINS` in `abbreviations.py`.

**Variables.** Expansion bodies support:

| Variable | Value |
| --- | --- |
| `${cursor}` | Cursor position after expansion |
| `${date}` | Current date (e.g. June 11, 2026) |
| `${time}` | Current time (12-hour, e.g. 02:30 PM) |
| `${clipboard}` | System clipboard text at expansion time |

**Keyboard defaults.**

| Action | Default binding |
| --- | --- |
| Expand abbreviation at cursor (manual) | `Ctrl+Shift+Grave, A` |
| Manage Abbreviations... | `Ctrl+Shift+Grave, Shift+A` |
| Toggle expansion on/off | `Ctrl+Shift+Grave, E` |

**Settings.** Four settings in `Editing` preferences:

- `abbreviation_expansion` (bool, default True) — master on/off.
- `abbreviation_expansion_sound` (bool, default False) — play a sound on expansion.
- `abbreviation_expansion_sound_file` (text) — path to a `.wav` file; blank = system default beep.
- `multi_press_window_ms` (int, default 400, range 100–1000) — time window for double/triple press detection across all multi-press chords (copy tray peek, command palette re-run, etc.).

**Status bar.** The `abbreviations` status bar cell shows `ABR: On` or `ABR: Off`. Clicking it toggles expansion. Hidden by default; add via status bar settings.

**Storage.** `abbreviations.json` in the QUILL user data directory. Atomic write. Default library written on first launch if file is absent.

**Interaction with snippets.** Abbreviation expansion fires before snippet expansion in `_on_text_changed`. If an abbreviation match is found, snippet expansion is skipped for that keystroke. The `;`-prefix snippet trigger is disjoint from bare-word abbreviation triggers so conflicts are practically impossible.

**Accessibility guarantees.** Every expansion announces "Expanded: \<preview\>" through the screen-reader bridge. Manual trigger (`Ctrl+Shift+Grave, A`) announces "Expanded to: \<preview\>" or "No abbreviation match". Toggle announces "Abbreviation expansion on/off".

**Abbreviation Manager dialog.** `quill/ui/abbreviation_manager_dialog.py` — A11Y-4 compliant, registered in the dialog inventory. Features: search field (filters the list in real time), Import button (merges a JSON file, skips duplicate IDs, announces count), Export button (saves full library to a JSON file). Disabled abbreviations shown with "(disabled)" suffix.

**`AbbreviationLibrary` class API** (all methods on `quill/core/abbreviations.AbbreviationLibrary`):

- `add(abbr, expansion, **kwargs) -> Abbreviation` — adds a new abbreviation, generates a UUID.
- `remove(id) -> None` — removes by ID.
- `enable(id) / disable(id) -> None` — toggle without deletion.
- `update(id, **fields) -> Abbreviation` — updates one or more fields; uses `object.__setattr__` for `slots=True` dataclass.
- `all() -> list[Abbreviation]` — full library in insert order.
- `enabled_only() -> list[Abbreviation]` — only enabled entries.
- `find_by_trigger(text, case_sensitive) -> Abbreviation | None` — looks up by trigger word.

**Implementation map.** `quill/core/abbreviations.py` (pure model, mypy-clean: `Abbreviation` dataclass, `AbbreviationLibrary`, `try_expand`, `resolve_expansion`, `_BUILTINS`), `quill/ui/main_frame_abbreviations.py` (`AbbreviationsMixin`), `quill/ui/abbreviation_manager_dialog.py` (management dialog with search + import/export). Menu: `Insert > Expand Abbreviation`, `Insert > Manage Abbreviations...`, `Insert > Toggle Abbreviation Expansion`.

---

### 5.79 Ask AI — lightweight in-editor AI chat

Ask AI is a modal dialog that lets users send a prompt to a configured AI provider and read the response without leaving QUILL. No document text is changed; the dialog is purely informational.

**Motivation.** Screen-reader users frequently need to ask a quick question while writing — define a term, check a fact, explore a phrasing option — and switching to a browser or a separate AI client breaks flow, especially when using NVDA or JAWS where switching applications involves extra navigation. Ask AI keeps the interaction entirely within the QUILL keyboard model.

**Entry point.** `Tools > AI Assistant > Ask AI...` (`Alt+Q` default chord). The Command Palette entry is "Ask AI". The binding is user-reassignable.

**Providers.** Three providers are supported. QUILL detects which keys are configured and only shows available providers.

| Provider | Auth | Model discovery |
| --- | --- | --- |
| OpenRouter | API key (DPAPI-encrypted) | `GET /api/v1/models`, cached per session |
| OpenAI | API key (DPAPI-encrypted) | `GET /v1/models`, filtered to `gpt-*`/`o*` families |
| Ollama | None (local) | `GET /api/tags`; greyed out if service not running |

**Smart focus.** When the dialog opens, focus lands in the Prompt field if the provider and model are already configured. If not yet configured, focus starts on the Provider choice so the user is guided to set it up first.

**Dialog layout.**

```
Provider:  [OpenRouter v]
Model:     [claude-3-5-sonnet v]
Prompt:    [multiline — Ctrl+Enter to send]
[Send]  [Clear]  [Close]
```

The response opens in a separate read-only dialog (model label at top, scrollable text area, Copy to Clipboard, Close). Closing the response dialog returns focus to the Ask AI dialog so the user can ask a follow-up without reopening.

**Settings** (in `Preferences > AI`):

| Setting | Type | Default | Description |
| --- | --- | --- | --- |
| `ai_chat_default_provider` | str | `"openrouter"` | Last-used provider |
| `ai_chat_default_model` | str | `""` | Last-used model |
| `ollama_base_url` | str | `"http://localhost:11434"` | Ollama endpoint (override for remote Ollama) |

**Keys stored in Windows Credential Manager** (never in `settings.json`): `quill-openrouter-api-key`, `quill-openai-api-key`.

**Safe Mode.** The Ask AI menu item and dialog are disabled when `QUILL_SAFE_MODE=1`.

**Network egress.** Audited in `network_egress_audit.py`: `openrouter_chat`, `openai_chat`, `ollama_chat`, `openrouter_models`, `openai_models`, `ollama_models`. Timeout: 60 s for chat, 10 s for model list.

**Implementation map.** `quill/core/ai_chat.py` (provider abstraction: `send_prompt`, `list_models`), `quill/ui/ai_chat_dialog.py` (Ask AI dialog + AI Response dialog, A11Y-4 hardened, registered in dialog inventory).

---

### 5.80 Check Grammar with AI

Check Grammar with AI sends the current selection (or full document if nothing is selected) to the configured AI model with a grammar-review prompt and displays the result in the AI Response dialog. No edits are applied automatically.

**Entry point.** `Edit > Grammar > Check Grammar with AI`. Command Palette: "Check Grammar with AI". User-assignable binding; no default chord.

**Default prompt.**

```
You are a grammar and style editor. Review the following text and list
only the corrections needed. For each correction, give: the original
phrase, the corrected phrase, and a one-sentence reason. Do not rewrite
the whole passage. If the text is correct, say "No issues found."

Text:
{selection}
```

When Phase 3 (§5.81) is active, the command uses the user's "Check Grammar" prompt from the Prompt Library instead, so the instruction text is fully customisable.

**Model selection.** Uses `settings.ai_prompt_default_model` when set, otherwise falls back to `settings.ai_chat_default_model`. This lets users choose a different (e.g. more capable) model for grammar review than for casual chat.

**Implementation.** Single method `check_grammar_with_ai()` in `MainFrame`. Runs on a background thread (`threading.Thread`, daemon=True); UI updates via `wx.CallAfter`. Command id: `tools.check_grammar_ai`.

---

### 5.81 AI Prompt Library

The Prompt Library is a named, user-expandable collection of AI instructions. Each prompt operates on the current selection or document: the user picks a prompt, QUILL sends the text and the prompt to the AI, and a response dialog shows the result. No document text changes without explicit action.

**Motivation.** Power users accumulate a personal set of AI instructions they run repeatedly — improve clarity, vary sentence rhythm, convert to bullets, generate an outline. Without a library, these prompts must be retyped or pasted from an external file each time. The Prompt Library turns these into first-class named commands, accessible from the keyboard, the command palette, and the dialog.

**Entry point.** `Tools > AI Assistant > Prompt Library...`. Command Palette: "Prompt Library". User-assignable binding.

**Prompt object fields.**

| Field | Description |
| --- | --- |
| `name` | Short display name ("Improve clarity") |
| `text` | Instruction text, with `{selection}`, `{document}`, `{title}` variables |
| `category` | Editing, Writing, Structure, Research, or Custom |
| `is_builtin` | True for shipped defaults — editable but not deletable |
| `id` | UUID, stable across renames |
| `shortcut` | Optional keyboard chord bound to this prompt |
| `enabled` | False to hide from menus without deleting |
| `source` | "builtin", "user", or Quillin id |

**Built-in prompts (12).** Shipped defaults, always present, user-editable:

- Editing: Check Grammar, Improve Clarity, Fix Grammar, Make Concise, Active Voice, Formal Tone, Conversational Tone
- Writing: Continue from Here
- Structure: Convert to Bullet Points
- Research: Define This Term, Find Counterarguments
- Custom: (none shipped; user-created)

**Prompt Library Dialog.** Split layout: left panel shows a searchable list of all prompts (filtered by the search field in real time); right panel shows the selected prompt's text and an optional input override. Buttons: Run with AI, New Prompt, Edit, Disable/Enable, Delete, Import .pqp, Export .pqp, Close. A11Y-4 hardened, registered in the dialog inventory.

**Settings.**

| Setting | Type | Default | Description |
| --- | --- | --- | --- |
| `ai_prompt_default_model` | str | `""` | Model used for prompt runs. Blank inherits `ai_chat_default_model`. |

**Storage.** `%APPDATA%\Quill\prompts.json` — atomic write, schema-validated. Built-in prompts are not persisted; only user additions and overrides to built-ins are stored.

**Quillin bridge.** A Quillin may ship a `prompts.json` file alongside its manifest. QUILL loads it automatically when the Prompt Library opens, adding those prompts to the library for the session (not persisted to disk). The bundled `ai-writing-prompts` Quillin ships 7 additional prompts this way: Expand This, Vary Sentence Rhythm, Make More Vivid (Writing); Write a Title, Generate Outline (Structure); Suggest Supporting Evidence (Research); Plain Language (Editing).

**Implementation map.** `quill/core/prompt_library.py` (`Prompt` dataclass, `PromptLibrary` CRUD, `.pqp` import/export, Quillin prompt loading), `quill/ui/prompt_library_dialog.py` (Prompt Library dialog), `quill/quillins_bundled/ai-writing-prompts/` (bundled prompt pack).

---

### 5.82 Prompt Quill Pack (.pqp) — shareable prompt collections

A `.pqp` (Prompt Quill Pack) file is a JSON document that packages a named collection of prompts for sharing or backup.

**File format.**

```json
{
  "schema": "quill.prompt-pack/1",
  "name": "My Writing Prompts",
  "prompts": [
    {
      "name": "Make Punchy",
      "text": "Rewrite this as a punchy one-liner: {selection}",
      "category": "Editing"
    }
  ]
}
```

**Import.** Via the Import .pqp button in the Prompt Library dialog. Prompts whose name already exists in the library are skipped; the count of newly added prompts is announced.

**Export.** Via the Export .pqp button. Exports all user-defined prompts (or a selected subset). Built-in prompts can optionally be included when the user has edited them.

**Use case.** A writing team can share a `.pqp` file containing their house-style prompts. A power user can back up their library and restore it on a new machine. A Quillin author can distribute prompts as a `.pqp` for users who prefer not to install a Quillin.

---

### 5.83 Quillin Manager — install, update, and remove extensions

The Quillin Manager (`Tools > Quillins`) lets users discover, enable, disable, and uninstall Quillins. As of this version it also supports installing a new Quillin directly from a local folder.

**Install from Folder.** The Install from Folder button opens a system folder picker. QUILL reads the selected folder's `manifest.json`, validates it, copies the directory into the per-user extensions root (`%APPDATA%\Quill\extensions\<id>\`), enables the Quillin, and refreshes the list. If an extension with the same id is already installed, it is replaced. Path containment is enforced: a crafted extension id cannot install files outside the extensions root.

**Remove.** Selecting an extension and pressing Remove deletes its directory and removes its state entry. Confirmation is required.

**Enable/Disable.** Toggle without uninstalling. A disabled Quillin's prompts and commands are not loaded.

**Manifest display.** Selecting a Quillin shows its name, version, author, description, declared capabilities, and any validation errors. This gives users the information they need to make an informed trust decision before enabling.

**Security model (SEC-8).** Third-party Quillin *discovery* (auto-scanning the extensions root) is locked off for QUILL 1.0 (`core.third_party_plugins` feature flag is `locked_off`). Install from Folder is the only way to add a third-party Quillin. The user must explicitly choose the folder, providing informed consent equivalent to "install this extension". Bundled Quillins (shipped inside the QUILL install tree) are always discovered and are not affected by the SEC-8 lock.

**Implementation map.** `quill/core/quillins/loader.py` (`install_extension`, `remove_extension`, `set_enabled`), `quill/ui/main_frame_quillins.py` (`QuillinsManagerMixin` — manager panel, Install from Folder button and handler).

---

### 5.84 Skill Quill Pack (.sqp) — multi-step AI workflows in plain text

A `.sqp` (Skill Quill Pack) file is a Markdown document with YAML front matter where level-1 headings define sequential AI steps. It extends `.pqp` prompt packs from single instructions to multi-step workflows with parameters, variable chaining, and conditional branching.

**Motivation.** Many real AI tasks are not single-shot prompts. Research then draft. Analyse then rewrite. Detect intent then branch. Encoding this logic in JSON means writing a DSL nobody can author without tooling. Writing it in Markdown means any user can open the file, read every step, and edit it — no schema browser, no visual designer. The skill is the document.

**Key design choices:**
- No streaming — each step sends a full prompt and receives a full response before the next step runs. This makes step outputs reliable as inputs to subsequent steps.
- Synchronous execution from the caller's perspective; threading is the UI layer's responsibility.
- Depth limit of 2 for nested skill calls to keep execution predictable.

**File format (`quill.skill/1`).**

```markdown
---
schema: quill.skill/1
name: Research and Draft
description: Extracts topic, gathers facts, drafts a paragraph.
author: QUILL Project
version: 1.0.0
parameters:
  - name: tone
    label: Tone
    type: choice
    choices: [formal, conversational, neutral]
    default: neutral
---

# Step 1: Extract topic

Identify the main topic in: {selection}

# Step 2: Research

List five facts about "{step1.output}".

# Step 3: Draft

Write a {parameters.tone} paragraph weaving in those facts.
Facts: {step2.output}

```output
format: text
label: Drafted paragraph
accept_into: selection
```
```

**Special blocks inside steps:**

| Block type | Purpose |
| --- | --- |
| `` `input` `` | Appends literal data to the prompt text |
| `` `condition` `` | Branches execution: `if: "X" contains "Y" / then: step3 / else: step4` |
| `` `output` `` | On last step: `format` (text/list/json), `label`, `accept_into` (selection/clipboard/none) |
| `` `use-prompt` `` | Delegates to a named prompt from the Prompt Library |
| `` `use-skill` `` | Calls another skill (depth-bounded) |

**Variables.** `{selection}`, `{document}`, `{title}`, `{clipboard}`, `{stepN.output}`, `{parameters.name}`.

**Validation tool.** `python -m quill.tools.sqp_validator <path>` validates one file or a directory. Exit 0 clean, exit 1 errors, `--strict` also checks for missing metadata.

**Bundled skills.** The `ai-writing-skills` Quillin ships four sample skills: Accessible Rewrite, Research and Draft, Meeting Notes to Action Items, Argument Strengthener.

**Implementation map.**

| File | Role |
| --- | --- |
| `quill/core/skill_pack.py` | `SkillPack` dataclass, `.sqp` parser, validator, synchronous runner |
| `quill/tools/sqp_validator.py` | CLI validator |
| `quill/quillins_bundled/ai-writing-skills/` | Four bundled `.sqp` skill files |
| `tests/unit/core/test_skill_pack.py` | 23 tests: parsing, validation, runner, branching, bundled files |

---

### 5.85 Portable API key store

By default QUILL stores AI provider keys in the Windows Credential Manager, which ties them to the current Windows user account. Portable mode offers an alternative: a DPAPI-encrypted file (`keys.enc`) in the QUILL data directory, activated by setting `QUILL_PORTABLE=1`.

**Motivation.** Some users run QUILL from a self-contained folder on a network share or external drive. They want all QUILL data — settings, data files, and keys — to live in one directory without requiring Credential Manager access on each machine. A DPAPI-encrypted file achieves this: everything stays in the folder, and the file is protected by the Windows user-account key.

**Access priority chain (highest wins):**

1. Environment variable (`QUILL_OPENROUTER_KEY`, `QUILL_OPENAI_KEY`, `QUILL_OLLAMA_KEY`, `QUILL_ASSISTANT_KEY`) — for CI pipelines and developer overrides.
2. Portable file store (`keys.enc`) — when `QUILL_PORTABLE=1` is set.
3. Windows Credential Manager — default for standard installations.

**Activation.** Set `QUILL_PORTABLE=1` in the process environment before launching QUILL. No other configuration is needed. The `keys.enc` file is created automatically in `app_data_dir()` on first key save.

**Security properties.** The file is encrypted with Windows DPAPI using a QUILL-specific entropy token. It is decryptable only on the same Windows machine by the same user account that encrypted it. Moving `keys.enc` to a different machine or a different Windows account will fail to decrypt; the user must re-enter their keys.

**Implementation map.**

| File | Role |
| --- | --- |
| `quill/platform/windows/credential_store.py` | Unified load/save/delete with env-var, portable file, and Credential Manager backends |
| `quill/platform/windows/dpapi.py` | DPAPI `protect_secret`/`unprotect_secret` (existing) |
| `quill/ui/ai_chat_dialog.py` | `_load_api_key`/`_save_api_key` updated to use credential_store |
| `quill/core/assistant_ai.py` | `_load/save/delete_api_key_from_credential_manager` updated to use credential_store |

---

## 6. Spell checking deep dive

### 6.1 The TinySpell question

TinySpell is a small, fast Windows spell-checker that watches the clipboard or current input field and alerts on misspellings. It is genuinely useful for many users. So the question is: should Quill integrate tightly with TinySpell, or build its own engine?

We have chosen to **build our own engine**, tightly integrated into Quill, for the following reasons:

1. **Screen-reader fidelity.** TinySpell speaks through its own UI surfaces and conventions. Quill needs total control over how misspellings are announced, navigated, and corrected so that NVDA, JAWS, and Narrator hear the same predictable patterns. A loose integration would create a second source of speech that competes with our own.
2. **Document context.** TinySpell works across applications and therefore cannot use document-level context (heading structure, surrounding paragraph, language metadata, per-document dictionary). Quill knows exactly what document the cursor is in and can do much better.
3. **Per-document and per-paragraph language detection.** Multi-language documents need language switches mid-stream. An external tool will not know.
4. **Suggestion ranking that learns.** TinySpell's suggestion order is fixed. Quill ranks suggestions using the user's own writing and the surrounding sentence, which is the single biggest quality-of-life upgrade in modern spell check.
5. **Offline guarantee.** Quill commits to spell check working with zero network. An external dependency complicates that guarantee.
6. **Distribution.** Bundling TinySpell would create a licence and update story we do not control.
7. **Keymap and palette parity.** Every Quill action is in the palette and reassignable. Spell-check commands must be too.

We will, however, ship a small **TinySpell interop plugin** for v1.1 for users who already rely on TinySpell elsewhere and want a unified personal dictionary. That plugin imports/exports the personal dictionary file and otherwise stays out of the way.

### 6.2 Engine architecture: "Quill Spell"

Quill Spell is a layered local engine:

- **Layer 1: Tokeniser.** Unicode-aware word splitter that understands code (CamelCase, snake_case, kebab-case), contractions, hyphenation, URLs, emoji, file paths, and Markdown/HTML syntax tokens. It hands the next layer a stream of `(word, span, context_kind)` tuples where `context_kind` is one of `prose`, `code`, `identifier`, `url`, `markup`, `path`.
- **Layer 2: Dictionary stack.** A priority-ordered stack of dictionaries: per-document, per-project (if applicable), user personal, language-base (Hunspell), plus optional jargon packs (medical, legal, technical, scientific). The first dictionary that accepts the word wins.
- **Layer 3: Hunspell backend.** Bundled via `cyhunspell`. Dictionaries shipped: en-US, en-GB, en-CA, en-AU, es-ES, es-MX, fr-FR, de-DE, pt-BR, pl-PL, ja-JP (with MeCab). Others available via a one-click downloader.
- **Layer 4: Suggestion engine.** Combines Hunspell's edit-distance suggestions with a character-level n-gram model and a small contextual reranker (a tiny on-device transformer; runs on CPU in <10 ms per call). Top 5 suggestions, ranked by combined score.
- **Layer 5: Learning loop.** When the user accepts a suggestion, the engine increments its frequency. When the user adds a word, it goes to the appropriate dictionary (with a prompt asking which). When the user repeatedly rejects a suggestion in favour of another, the reranker learns the preference. Learning is 100 percent local and resettable.
- **Layer 6: Context awareness.** The tokeniser tells the engine when it is inside a code fence, an inline code span, a URL, or a Markdown link target. Those regions are skipped by default. Settings let the user enable code spell checking with a programming-aware dictionary.

### 6.3 User experience

- **Status indicator.** The status bar shows the active dictionary stack as a short label, for example `en-GB + tech + personal`.
- **F7 full review.** Modal Spell Check dialog with: misspelled word, surrounding sentence with the word highlighted and announced, suggestions list, replacement edit, Change, Change All, Ignore, Ignore All, Add to (with submenu for which dictionary), Finish, Cancel. The word is spoken and then spelled letter by letter.
- **Ctrl+; quick fix.** Jumps to the next misspelling, opens a small modal list of the top 5 suggestions. Numbers 1 through 5 accept the corresponding suggestion. Enter accepts the highlighted one. `A` adds to dictionary. `I` ignores once. `Esc` cancels.
- **Background pass.** A debounced background tokenise runs as the user types. Results live in a sidecar model. No visual squiggles. The screen reader is never interrupted by background work.
- **Mode toggle.** `Alt+F7` toggles as-you-type checking for the current document.
- **Per-document language.** A YAML-style sidecar (`<doc>.quill.yml`) can pin language and dictionaries. Detected automatically from a magic comment on the first line if present.
- **Magic touches.**
  - When you add a word, Quill says "Added <word> to your personal dictionary" or "Added <word> to this document's dictionary" so you always know where it went.
  - When you reject the same suggestion three times for the same misspelling, Quill quietly asks once whether you want to add the rejected word to your personal dictionary.
  - When pasting a large block of text, the spell pass is queued at a lower priority so the paste itself is instant.
  - When entering a code fence in Markdown, the engine switches automatically to identifier mode and stops complaining about variable names.

---

## 7. Command palette deep dive

The command palette is modelled directly on Visual Studio Code's, adapted for screen readers.

### 7.1 Opening and dismissing

- `Ctrl+Shift+P` opens the palette in command mode.
- `F1` does the same.
- Each prefix shortcut (below) opens the palette pre-seeded with that prefix.
- `Esc` closes without action.
- `Enter` runs the selected entry (and remembers it).
- `Tab` from the input moves into the list. `Shift+Tab` returns to the input.

### 7.2 Prefix modes

A single edit field, one list. The first character of the input may be a mode prefix:

| Prefix | Shortcut to open directly | Meaning |
| --- | --- | --- |
| (none) or `>` | `Ctrl+Shift+P` | Run a command |
| `?` | `Ctrl+Shift+?` | Show help for all prefixes |
| `:` | `Ctrl+G` (when no page markers) | Go to line |
| `@` | `Ctrl+R` | Jump to bookmark in current document |
| `#` | `Ctrl+T` | Jump to bookmark across all open documents |
| `!` | `Ctrl+Shift+M` | Show issues (spell check, bookmark, format) |
| `<` | `Ctrl+E` | Open a recent file |
| `~` | `Ctrl+Shift+O` | Switch open document |
| `=` | (palette only) | Open a setting |

These prefixes are themselves reassignable (see [section 8](#8-keymap-and-keystroke-reassignment)).

### 7.3 Matching

- Fuzzy subsequence match across the visible label.
- Each match scored by: subsequence tightness, prefix bonus, word-boundary bonus, recency, frequency.
- Top 100 results displayed, lazily.
- Ties broken alphabetically.

### 7.4 Rows

Each row in command mode shows three regions, all announced as one string by the screen reader (with internal punctuation chosen to read well):

```text
<Command title> — <current keybinding or "unassigned"> — <source>
```

For example:

```text
Improve Reading Order with AI — unassigned — Quill
Spell Check Document — F7 — Quill
Find Next — F3 — Quill
Pandoc: Convert to DOCX — Ctrl+Alt+P — Plugin: Pandoc Bridge
```

### 7.5 Inline keybinding edit

While the palette is open and a command is highlighted:

- `Right Arrow` enters keybinding edit mode for that command.
- A small inline edit prompt says "Press the new shortcut, or Escape to cancel, or Delete to unassign."
- The next keystroke (chord or sequence) becomes the binding.
- Conflicts are detected immediately and announced (see [section 8.4](#84-conflict-handling)).
- `Enter` commits, `Esc` cancels.

### 7.6 Recently used and pinned

- The most recently run 10 commands always appear at the top when the palette opens fresh, before any typing.
- Users can pin commands with `Shift+Enter` from the palette. Pinned commands always appear above recents.

### 7.7 Help

- `?` plus Enter, or `Ctrl+Shift+?`, shows a "How to use the Command Palette" topic in the palette itself: a list of prefixes, their meanings, and their shortcuts, each line runnable with Enter to invoke an example.
- Where Am I (`Ctrl+Shift+I`) in the palette announces: current mode, number of matches, selected entry, current binding.

### 7.8 Accessibility specifics

- The palette is a non-modal top-level `wx.Frame` over the main window with focus capture. Underlying widgets are a `wx.SearchCtrl` and a `wx.ListBox`. Both are stock controls, so all screen readers get correct announcements without scripts.
- Each list update fires a single accessibility event with the count of results; we do not spam announcements as the user types.
- Live region is set on the help/result line below the list for status messages such as "Keybinding updated" and "Conflict with Find Next."

---

## 8. Keymap and keystroke reassignment

Every Quill action is identified by a stable command id (`quill.editor.save`, `quill.palette.open`, `quill.spell.checkDocument`, etc.) and may have zero, one, or many keybindings.

### 8.1 Where keystrokes live

Three layers, in priority order:

1. **User keymap** (`%APPDATA%\Quill\keymap.json`). User edits win.
2. **Profile keymap** (optional, shipped alternatives). For example, "Word-like", "Vim-friendly", "Emacs-friendly". The user picks one as the base.
3. **Default keymap** (built into Quill).

The effective keymap is the merge of these three, with user > profile > default.

### 8.2 Keyboard settings page

`Ctrl+,` then "Keyboard" (or palette `=keyboard`).

The page contains:

- A **profile selector**: System (defaults), Word-like, Vim-friendly, Emacs-friendly, Custom.
- A **search field** that filters the table below.
- A **bindings table** (`wx.ListCtrl` in report mode, fully accessible) with columns:
  - Command title
  - When (context: editor, palette, dialog, global)
  - Keybinding
  - Source (default, profile, user)
  - Conflicts (a short marker if any)
- **Buttons**: Add, Change, Remove, Reset to default, Reset all to profile, Import, Export.
- A **"Press a key" capture field** for visual users who want to find what a chord does today.

### 8.3 Editing a single binding

Three equivalent ways:

1. From the command palette: highlight a command and press `Right Arrow`.
2. From the Keyboard settings page: select the row and press `Change` (or `Enter`).
3. From the menu bar: every menu item has a context-menu entry "Change keybinding".

In all three, the same small "Press the new shortcut" capture dialog appears. It:

- Captures any chord or two-key sequence (VS Code style, e.g. `Ctrl+K Ctrl+S`).
- Announces the captured keystroke as it is built.
- Refuses to capture purely modifier keys.
- Refuses to capture keystrokes reserved by the OS or by the active screen reader (NVDA, JAWS, Narrator) and explains which one it conflicts with.

### 8.4 Conflict handling

When a keystroke is already used:

- The dialog announces the conflict: "Ctrl+G is currently used by Go To Line in editor context."
- Three choices, each on its own button: **Replace** (the old command becomes unbound and the new one is bound), **Add** (both commands have this binding; the active "when" context disambiguates), **Cancel**.
- "Add" is only offered when contexts are distinct. Same-context dual binding is not allowed for safety.

### 8.5 "When" contexts

Each command declares which contexts it is valid in:

- `editor` — focus is in the main editor.
- `palette` — focus is in the command palette.
- `dialog` — focus is in any Quill dialog.
- `global` — anywhere in the app.
- `format:md` — editor focus, current document is Markdown.
- `format:pdf` — editor focus, current document was extracted from PDF.
- `selection` — there is a non-empty selection.

Contexts can be combined with `&&` in advanced editing.

### 8.6 Profiles in detail

- **System**: clean, modern Windows conventions (default).
- **Word-like**: brings Quill close to Microsoft Word for users migrating from there.
- **Vim-friendly**: a modal layer overlaid via plugin, off by default in the profile selector but available to install.
- **Emacs-friendly**: chord-heavy bindings (`Ctrl+X Ctrl+S` etc.), again via the chord engine.

### 8.7 Storage format

`keymap.json` is plain JSON, human readable, version controlled friendly:

```json
{
  "version": 1,
  "profile": "System",
  "bindings": [
    { "command": "quill.editor.save", "key": "Ctrl+S", "when": "editor" },
    { "command": "quill.palette.open", "key": "Ctrl+Shift+P", "when": "global" },
    { "command": "quill.spell.checkDocument", "key": "F7", "when": "editor" },
    { "command": "quill.editor.gotoLine", "key": "Ctrl+G", "when": "editor && !format:pdf" }
  ]
}
```

### 8.8 Import, export, sync

- Export the active keymap to a single JSON file.
- Import from a file (with a preview dialog showing every change).
- Sync via a user-chosen folder (OneDrive, Dropbox, Syncthing). Quill watches the file and reloads on change, announcing "Keymap reloaded from disk."

### 8.9 Safety net

- A "Reset all keybindings" button exists at the bottom of the Keyboard settings page.
- Recovery: if `keymap.json` is corrupt, Quill renames it to `keymap.broken-<timestamp>.json` and falls back to defaults, announcing what happened.

---

## 9. Accessibility, WCAG 2.2 AA conformance, and certification

Accessibility is not a feature set; it is the product's contract with its users. This section is the canonical reference for what "accessible" means for Quill, how it is engineered, how it is tested, how regressions are caught, and how a Voluntary Product Accessibility Template (VPAT) Accessibility Conformance Report (ACR) is generated for procurement.

### 9.1 Compliance posture and target standards

Quill targets the following standards in full at v1.0 release:

- **WCAG 2.2 Level AA** (W3C Recommendation, October 2023). All Level A and AA Success Criteria that apply to a native desktop application are conformed to.
- **WCAG 2.2 Level AAA** for criteria reasonably achievable in a text editor (contrast 7:1 in High Contrast theme; reading-level alternatives; consistent help).
- **US Section 508** (revised 2018 ICT Refresh, which incorporates WCAG 2.0 AA). Conformance is established by demonstrating WCAG 2.2 AA conformance, which is a superset.
- **EN 301 549 v3.2.1** (European harmonised standard, including chapters 5, 6, 7, 9, 11, and 12 as applicable).
- **ARIA 1.2 / WAI-ARIA Authoring Practices** patterns are honoured wherever Quill exposes ARIA-equivalent semantics through MSAA/UIA (combobox patterns for the palette, treeview patterns for the Outline Navigator, listbox patterns for issue panels).
- **Microsoft's Accessibility Insights for Windows** baseline (every CI build is run through Accessibility Insights and must produce zero errors and zero warnings on covered axes).

**Screen-reader coverage across platforms.** On Windows, Quill targets **NVDA (primary), JAWS, and Narrator**; on **macOS** it targets **VoiceOver**. Quill routes its own announcements to the active platform screen reader and never speaks over it (on macOS it defers to VoiceOver rather than falling back to a separate speech engine). Embedded web content -- the Ask Quill chat, the Markdown/HTML preview, the About box, and the update/consent dialogs -- is driven through semantic HTML/ARIA so it reads as a real web document under NVDA, JAWS, and VoiceOver alike (see the accessible-WebView approach in section 10).

### 9.2 Conformance posture statement (will appear in the ACR)

> Quill 1.0 **supports** WCAG 2.2 Level A and Level AA across all functionality intended for end users. It **partially supports** Level AAA criteria 1.4.6 (Contrast Enhanced) and 2.4.10 (Section Headings). Quill does not include audio-only or video-only media; criteria specific to such media are **not applicable**.

### 9.3 WCAG 2.2 AA conformance matrix

The following matrix lists every Level A and AA Success Criterion, how Quill meets it, and where it is tested. Each row is a contract: a CI test exists for every “Tested by” entry, and a regression fails the build.

#### Principle 1: Perceivable

| SC | Title | Level | How Quill meets it | Tested by |
| --- | --- | --- | --- | --- |
| 1.1.1 | Non-text Content | A | Every icon-bearing button has a `wx.Window.SetName`/`SetHelpText` pair; the Accessibility Auditor (5.20) requires alt text on every image in user documents | UI a11y harness; auditor unit tests |
| 1.2.x | Time-based Media | A/AA | Not applicable; Quill ships no audio/video | n/a |
| 1.3.1 | Info and Relationships | A | Every label is associated with its control via parent-sizer convention plus explicit `SetLabel`; menu structure is exposed as MSAA tree; status-bar cells expose name+role+value+description | UI a11y harness verifies MSAA tree; snapshot tests |
| 1.3.2 | Meaningful Sequence | A | Tab order is explicit and deterministic per dialog; tested with `pywinauto` walking each dialog | Tab-order snapshot tests |
| 1.3.3 | Sensory Characteristics | A | No instruction uses shape, position, sound, or colour alone; all hints are text in tooltips and Where Am I | Manual checklist; copy review |
| 1.3.4 | Orientation | AA | Window orientation is user-controlled; no orientation lock | n/a (desktop) |
| 1.3.5 | Identify Input Purpose | AA | Settings fields use semantic `name` attributes mappable to autofill purposes where the OS supports them | Settings inventory |
| 1.4.1 | Use of Colour | A | Modified state is text (`[modified]`), not colour; issue severity uses prefix words (`Error:`, `Warning:`); diff hunks use `+`/`-` prefixes | Theme tests; copy review |
| 1.4.2 | Audio Control | A | Read Aloud has explicit start/pause/stop and a status cell; can be silenced at any time without affecting the SR | Manual + UI test |
| 1.4.3 | Contrast (Minimum) | AA | All bundled themes meet 4.5:1 for normal text, 3:1 for large text and UI components; verified by an automated contrast checker run against every theme | Contrast CI job |
| 1.4.4 | Resize Text | AA | Editor font 10–48pt via `Ctrl++`/`Ctrl+-`/`Ctrl+0`; dialog text scales with Windows DPI (100–400%) without loss of function or clipping | DPI smoke tests at 100/125/150/175/200/300/400 |
| 1.4.5 | Images of Text | AA | Quill never renders text as an image; all UI text is real text in stock controls | n/a |
| 1.4.10 | Reflow | AA | Window contents reflow to 320 CSS px equivalent (320 device-independent pixels); status-bar cells overflow into a roll-up; menu falls back to compact mode | Reflow tests at minimum window size |
| 1.4.11 | Non-text Contrast | AA | All UI components and graphical objects (focus rings, status-bar separators, toggle states) meet 3:1 against adjacent colours | Contrast CI job covers component states |
| 1.4.12 | Text Spacing | AA | Editor honours user spacing overrides (line height up to 1.5x, paragraph spacing up to 2x font size, letter spacing up to 0.12em, word spacing up to 0.16em) without truncation or overlap | Spacing test fixture |
| 1.4.13 | Content on Hover or Focus | AA | Tooltips are dismissible (Esc), hoverable, and persist until input moves away | Hover tests |

#### Principle 2: Operable

| SC | Title | Level | How Quill meets it | Tested by |
| --- | --- | --- | --- | --- |
| 2.1.1 | Keyboard | A | Every action is reachable from the keyboard; drag-and-drop is explicitly omitted from required flows | Keyboard parity matrix test |
| 2.1.2 | No Keyboard Trap | A | Every dialog has an Escape route; F6 cycles regions; modal dialogs have an explicit Cancel | Trap detection in pywinauto suite |
| 2.1.4 | Character Key Shortcuts | A | Single-character shortcuts (like F3) are bound only to commands that re-fire safely; users can rebind all of them; no single-letter shortcuts in editor focus | Keymap audit |
| 2.2.1 | Timing Adjustable | A | The only time-bound interaction is read-aloud, which the user controls; no idle timeouts in v1.0 | Manual review |
| 2.2.2 | Pause, Stop, Hide | A | Read Aloud has Pause/Stop; the only moving thing in the UI is a progress indicator that the user can cancel | Manual review |
| 2.3.1 | Three Flashes or Below Threshold | A | Quill has no flashing UI | n/a |
| 2.4.1 | Bypass Blocks | A | F6 region cycling, command palette, outline navigator | Navigation tests |
| 2.4.2 | Page Titled | A | Window title always identifies the active document and Quill | Title test |
| 2.4.3 | Focus Order | A | Focus order matches reading order; no surprise focus jumps; recent locations history surfaces movement | Tab-order snapshot tests |
| 2.4.4 | Link Purpose (In Context) | A | Insert Link dialog enforces meaningful display text; auditor flags generic link text | Auditor tests |
| 2.4.5 | Multiple Ways | AA | Outline Navigator, command palette `@`/`#`/`<`/`~`, Find, menu Navigate submenu | Navigation tests |
| 2.4.6 | Headings and Labels | AA | Settings tree and dialog sections use descriptive headings; auditor requires the same in user docs | Copy review; auditor tests |
| 2.4.7 | Focus Visible | AA | Native Windows focus indicators are preserved (no custom drawn focus); High Contrast theme amplifies the system focus ring | Focus visibility audit |
| 2.4.11 | Focus Not Obscured (Minimum) | AA (new in 2.2) | Quill does not float overlays that obscure focus; the palette and modal dialogs receive focus and are larger than the focused control | Focus-not-obscured check |
| 2.4.12 | Focus Not Obscured (Enhanced) | AAA | Same as 2.4.11; Quill conforms by construction | (auto) |
| 2.4.13 | Focus Appearance | AAA | Native Windows focus ring is honoured; High Contrast theme exceeds the 2px solid / 3:1 contrast target by relying on the OS focus rectangle | Manual verification |
| 2.5.1 | Pointer Gestures | A | No multi-point or path-based gestures required | n/a |
| 2.5.2 | Pointer Cancellation | A | Buttons activate on up-event; cancel by moving off before release | Native button behaviour |
| 2.5.3 | Label in Name | A | Accessible name begins with visible label text for every control | UI a11y harness |
| 2.5.4 | Motion Actuation | A | No motion-actuated functions | n/a |
| 2.5.7 | Dragging Movements | AA (new in 2.2) | No required drag; every drag-equivalent action has a keyboard alternative | Keyboard parity matrix |
| 2.5.8 | Target Size (Minimum) | AA (new in 2.2) | All clickable targets at least 24x24 CSS px including status-bar cells; verified per-theme | Layout tests |

#### Principle 3: Understandable

| SC | Title | Level | How Quill meets it | Tested by |
| --- | --- | --- | --- | --- |
| 3.1.1 | Language of Page | A | The application's UI language is declared via `wx.Locale` and exposed to MSAA | Locale tests |
| 3.1.2 | Language of Parts | AA | Per-document language metadata (5.38) and the spell-check language stack indicator (5.1b) expose document language to user and AT | Metadata tests |
| 3.2.1 | On Focus | A | Focus changes never trigger unexpected context changes | Focus tests |
| 3.2.2 | On Input | A | Form inputs require explicit confirmation; no auto-submit on change | Form tests |
| 3.2.3 | Consistent Navigation | AA | Menu structure, palette prefixes, and status-bar layout are identical across every document and dialog | Snapshot tests |
| 3.2.4 | Consistent Identification | AA | The same icon and label is used for the same action everywhere | Inventory test |
| 3.2.6 | Consistent Help | A (new in 2.2) | Help menu position and Help item names are identical across every window | Snapshot tests |
| 3.3.1 | Error Identification | A | Every error message names the field and the rule violated; never just a code | Error message inventory |
| 3.3.2 | Labels or Instructions | A | Every input has a visible label; complex fields include placeholder hints that are also exposed as MSAA description | Label inventory |
| 3.3.3 | Error Suggestion | AA | Field errors include the value the user typed and a concrete fix suggestion | Error message inventory |
| 3.3.4 | Error Prevention (Legal, Financial, Data) | AA | Destructive operations (Replace All > 25 occurrences, Restore Backup, Reset Settings) always show a confirmation; backups exist for restores | Confirmation matrix test |
| 3.3.7 | Redundant Entry | A (new in 2.2) | Previously entered values (search history, recent files, settings) are available without re-entry | Persistence tests |
| 3.3.8 | Accessible Authentication (Minimum) | AA (new in 2.2) | The only authentication is the AI provider API key, which is paste-and-store via DPAPI; no cognitive-test puzzle | n/a |

#### Principle 4: Robust

| SC | Title | Level | How Quill meets it | Tested by |
| --- | --- | --- | --- | --- |
| 4.1.1 | Parsing | A (obsolete in 2.2) | (Marked obsolete; included for completeness.) | n/a |
| 4.1.2 | Name, Role, Value | A | Every control exposes name, role, value, state, and where applicable description via MSAA and UIA. Custom status-bar cells implement this explicitly via `wx.Accessible` subclasses | UI a11y harness (Inspect.exe parity) |
| 4.1.3 | Status Messages | AA | All asynchronous announcements (saved, replaced N, found on line N, AI progress) are sent via the live-region pattern and through the SR-agnostic announcement channel (9.6) | Live region tests |

### 9.4 Screen-reader compatibility matrix

| Reader | Versions covered | Quill support level | Notes |
| --- | --- | --- | --- |
| NVDA | 2024.x, 2025.x, 2026.x stable + current beta | First-class (reference platform) | All flows fully announced; no required scripts |
| JAWS | 2024, 2025, 2026 latest | First-class | Small optional script provides live-region parity for non-standard status-bar cell updates; ships in the installer |
| Narrator | Windows 11 24H2 and later | First-class | Uses UIA path; covered by the standard MSAA wiring |
| Windows Magnifier | Current | Supported | Focus following works because of stock controls |
| ZoomText / Fusion | Current | Supported | Tested but not officially certified at v1.0 |
| Dolphin SuperNova | Current | Best effort | Tested at major releases; defects escalated |

### 9.5 Screen-reader announcement architecture

Quill speaks to the user through three independent channels, all of which deliver the same content. This is what "never goes quiet when you needed it to speak" means in code.

1. **Stock control announcements** — wx widgets carry their own MSAA/UIA semantics; the SR speaks them automatically on focus and value change.
2. **Live region channel** — a hidden `wx.StaticText` per top-level window acts as an ARIA-like live region. Quill sets its text, fires an MSAA `EVENT_OBJECT_LIVEREGIONCHANGED` and a UIA `Notification` event with kind `Other` and priority `Standard` or `High` as appropriate. NVDA and Narrator pick this up natively; JAWS reads it through the bundled optional script.
3. **Direct SR APIs (graceful degradation)** — when a detected SR is running, Quill may use its direct API for higher-priority announcements (NVDA's `nvdaControllerClient.dll` `nvdaController_speakText`, JAWS' `jfwapi.dll` `JFWSayString`, Narrator via UIA notification). This is used only when the live region path is too slow for time-sensitive feedback (find result during F3 chaining, spell-check next misspelling). The direct call is preferred only when (a) a registered SR is detected and (b) the user has not opted out in Settings → Reading.

All three channels are funnelled through a single `quill.a11y.announce(text, *, priority='normal', interruptible=True)` function, so there is exactly one code path to test.

Quill exposes an explicit announcement backend selector in Settings and command surfaces. Supported modes are `auto`, `legacy`, `prism`, and `sounds`, with `auto` as default. `auto` chooses the best backend for the current screen-reader/runtime context and falls back deterministically when a backend is unavailable.

### 9.5.1 Announcement backend provenance

The `prism` backend in Quill is derived from the architecture and behavior patterns published in the open-source Prism project:

- Source: <https://github.com/ethindp/prism>
- Scope borrowed: screen-reader announcement abstraction approach, backend-oriented dispatch model, and parity-focused announcement reliability goals.
- Quill adaptation: integrated into Quill's existing `quill.a11y.announce(...)` funnel and profile/feature controls, while preserving Quill's own command, diagnostics, and privacy conventions.

### 9.6 Keyboard accessibility gates

- **Keyboard parity matrix**: every menu item, every status-bar cell, every palette command, every dialog button has a keyboard equivalent. CI generates the matrix from the command registry and fails the build if any entry lacks an accessible keystroke.
- **No keyboard traps**: pytest-pywinauto test traverses every modal and non-modal window and asserts that Escape, Tab, and Shift+Tab always exit or cycle.
- **Single-character shortcut policy**: single-character shortcuts (F3, F7, etc.) are only bound to commands marked `repeatable`. Editor focus never binds a single printable character because that would steal typing.
- **Two-key chord policy**: the default keymap uses at most six two-key chords; profiles can use more; the user can rebind all.
- **Screen-reader chord guard** (5.8.4): when the user captures a new keystroke, Quill checks it against a curated static list of well-known NVDA, JAWS, and Narrator chords and refuses the capture with an explanation.

### 9.7 Visual accessibility gates

- **Themes**: System (follows Windows), Light, Dark, High Contrast (follows Windows High Contrast tokens), Custom (user-defined token map).
- **Contrast**: every theme is verified by an automated contrast checker (`a11y/contrast.py` using the WCAG relative-luminance formula) against every text/background and component-state pair; build fails on any pair below 4.5:1 text or 3:1 component.
- **Font scaling**: editor font 10–48pt; dialog text follows Windows DPI; all layouts tested at 100%, 125%, 150%, 175%, 200%, 300%, 400%.
- **Reflow**: minimum supported window size 800x600; all dialogs scrollable at that size; status-bar cells overflow into the roll-up cell.
- **Motion**: respects Windows “Show animations” setting; no animations in any case; progress indicators use a determinate or simple textual percentage.
- **Focus visibility**: native Windows focus rectangle is preserved; High Contrast theme amplifies; no custom-drawn focus.
- **Cursor**: caret blink rate respects Windows; thickness respects Windows; no custom carets.
- **Spacing**: 1.4.12 user overrides honoured (see matrix).
- **Target size**: every clickable target ≥ 24x24 device-independent pixels; status-bar cells ≥ 28x24.

### 9.8 Cognitive accessibility gates

- **Consistent vocabulary**: a controlled vocabulary document drives every string (e.g. "document" not "file" or "buffer"; "selection" not "highlight"); enforced by a linter over translation source files.
- **Plain-language baseline**: UI strings target a Flesch reading ease of 60 or higher; Tools (the Document Statistics engine) is used in CI to grade the UI string corpus.
- **Confirmations on destructive actions**: every destructive action prompts; default button is the safe option (Cancel, Keep Mine, etc.); the destructive button is never the default.
- **Undo for everything possible**: every editor mutation is undoable; settings and keymap changes support “Undo last change” for 30 seconds via a Notifications-cell message.
- **One-key escape**: Esc closes any palette or dialog without side effects.
- **Tooltips with intent, not jargon**: every button tooltip names the action and the result, not the implementation.
- **No autoplay**: no audio, video, or animation starts without explicit user action.

### 9.9 Accessibility testing pipeline

Three layers run on every PR and every release branch.

1. **Static / lint layer (every PR)**
   - Controlled-vocabulary linter over `*.po` translation sources.
   - Plain-language linter (Flesch ≥ 60) over UI strings.
   - Keymap audit (no editor-focus single printable letters; all commands have ids).
   - Theme contrast checker.
   - Tab-order snapshot diff (changes require an explicit reviewer approval).
   - Command registry coverage (every command has a name, description, default keybinding or explicit `unbound`, and a help topic).
2. **Headless UI layer (every PR, runs on a Windows runner)**
   - `pytest` + `pywinauto` boots the app and walks every dialog, modal, and palette mode.
   - Inspect.exe parity: a custom UIA dumper records the tree for each window; the dump is diffed against a golden snapshot.
   - Accessibility Insights for Windows CLI is run; build fails on any error.
   - DPI smoke tests at 100/150/200%.
3. **SR-in-the-loop layer (every release branch and nightly)**
   - A custom SAPI 5 speech driver records every utterance into a transcript file.
   - NVDA is launched with the recording driver via NVDA's command-line; Quill is driven through a scripted scenario set (open, find, F3 chain, palette, outline jump, spell check fix, keymap rebind, restore backup, AI confirm-and-cancel).
   - The recorded transcript is diffed against a golden transcript per scenario per SR. The harness is in v1.1 of the project plan but the scenario scripts and golden transcripts are produced manually for v1.0.
   - JAWS scenarios run separately when a JAWS-enabled runner is available; Narrator runs via UIA notifications.

No PR merges with any of these failing. A failure can be waived only by the accessibility lead, with an issue link and an expiry date.

### 9.10 VPAT / ACR generation

- The conformance matrix in 9.3 is the source of truth.
- A script (`tools/gen_vpat.py`) renders the matrix into an ITI VPAT 2.5 Rev INT form (the ICT industry-standard template) and a Word document, plus a markdown ACR for the website.
- The ACR is published with every release and links each row back to the corresponding test.
- VPATs cover WCAG 2.2, Section 508, and EN 301 549.

### 9.11 Certification path

- v1.0 self-certifies WCAG 2.2 AA, Section 508 (revised), and EN 301 549 v3.2.1 via the ACR.
- An independent third-party audit (target: TPGi, Deque, or Level Access) is commissioned for v1.0 release. Findings are tracked publicly in a `compliance/` folder of the repository.
- Outstanding findings have target dates and a public regression register.

### 9.12 Gated regressions (CI must-pass list)

A build is blocked when any of the following regresses:

- Any cell in the WCAG matrix transitions from passing to failing.
- Any tab-order snapshot diff is unreviewed.
- Any contrast pair drops below threshold in any bundled theme.
- Any command in the registry loses a name, description, or keymap entry.
- Any dialog gains a keyboard trap.
- Any user-facing string fails the controlled-vocabulary or plain-language linter without an explicit waiver.
- Any custom control is introduced into the editor or palette path without an `wx.Accessible` subclass that passes the Inspect.exe parity test.
- Any SR transcript diff exceeds tolerance.

### 9.13 Dialog estate governance (DLG-3)

Every dialog in Quill is the single highest-risk accessibility surface in the UI: controls that do not work, focus landing on the wrong control, and rendering breakage all live in dialogs and are otherwise invisible to a source-only review. DLG-3 is the flagship structural-health refactor that makes the dialog estate correct by construction, source-of-truth, and machine-gated. It folds in and supersedes the earlier batch ambitions (the form-conversion wave and the individual AI-tool conversions).

**Surface policy (the non-negotiable standard).** Every dialog surface is exactly one of three sanctioned classifications, and no other dialog framework or bespoke modal surface may be introduced:

1. **`native`** — stock wx one-shot dialogs (`wx.MessageDialog`, `wx.RichMessageDialog`, `wx.MessageBox`, `wx.SingleChoiceDialog`, `wx.MultiChoiceDialog`, `wx.TextEntryDialog`, `wx.FileDialog`, `wx.DirDialog`, `wx.FindReplaceDialog`, `wx.ProgressDialog`, About). Native-first is the default for confirms, choices, simple text input, and file/folder selection.
2. **`web`** — sanctioned accessible web surfaces (`show_web_form`, the markdown/HTML preview dialog, the accessible chat view) used only where rich rendering, chat interaction, or dynamic multi-field forms are genuinely required, always with a native fallback.
3. **`hardened_custom`** — a `wx.Dialog` container composed _only_ of stock native controls (`wx.ListBox`, `wx.TextCtrl`, `wx.SearchCtrl`, `wx.CheckListBox`, `wx.Notebook`, `wx.Button`, …). These are "enhanced-native": real OS widgets in a dialog frame. No custom-drawn or owner-drawn controls are permitted in any dialog.

**Source-of-truth inventory.** The authoritative dialog inventory is generated from source, not from a checklist. `quill/tools/dialog_inventory.py` AST-scans all of `quill/**/*.py` and records every dialog surface under a stable, line-independent key (`<module>::<enclosing_qualname>::<kind>`) with its sanctioned classification. The committed snapshot is `tests/unit/ui/fixtures/dialog_inventory.json`, and two gates enforce it: `tests/unit/ui/test_dialog_inventory.py` fails on any new, moved, removed, or reclassified dialog or unsanctioned surface; and a registry cross-check inside the A11Y-4 banned-pattern gate fails the build on any unregistered or misclassified dialog. Adding a dialog forces a deliberate `python -m quill.tools.dialog_inventory --write` whose classification is reviewed in the diff. The manual companion checklist `dialogs.md` maps each shipped dialog to its keyboard command or menu path and is kept in sync, but it is not the inventory authority.

**Per-dialog accessibility interaction contract.** Every dialog must satisfy all of: deterministic initial focus on open; complete Tab / Shift+Tab traversal; an explicit default action (Enter); Escape/close always exits; preserved modal-result semantics; focus return to the initiating editor/control on close; the screen reader announces the title and every actionable control; and no trap, freeze, or silent state. Modal show is routed through the shared `dialog_contract` helpers (`apply_modal_ids`, `show_modal_dialog`), and raw `wx.Dialog(...)` always has a `Destroy()` (or `with` form) lifecycle and uses `wx.EXPAND` button sizers, never `wx.ALIGN_RIGHT`.

**Control-surface completeness.** For every dialog, every control surface is audited and explicitly dispositioned as **keep** (already excellent, evidence linked), **harden** (focus/tab/label/default/announcement improvements), or **replace** (native or sanctioned-web equivalent). No unlabeled, untabbable, unannounced, or ambiguous control remains.

**"Every dialog touched" definition.** A dialog counts as touched only when it has all three of: (1) a classification in the registry (`native`, `web`, or `hardened_custom`); (2) explicit conformance evidence (a focused source-contract test or behavior test); and (3) a confirmed `dialogs.md` mapping, updated if its naming, binding, or path changed. The authoritative inventory is generated from source — including non-`quill/ui` surfaces such as the startup storage chooser in `quill/__main__.py` and the nested describe-image source/file pickers in `quill/ui/main_frame_image.py` — so checklist-only review can never miss a surface. The exit criterion is 100% source coverage, not a fixed legacy count; the count is expected to rise as source-discovered dialogs are folded in.

**High-risk clusters (sequenced first).** The concentration of lifecycle/focus risk is known and drives wave order: (1) `main_frame.py` modal sprawl (largest concentration); (2) `assistant_tools.py` (high interaction complexity, async actions, many custom dialog classes); (3) the startup/onboarding chain (`run_startup_wizard`, first-run prompts, trust consent, web-preview handoff); (4) sticky notes (historical focus-landing issues); and (5) mixed rendering surfaces (native + web + fallback) where behavior parity must be explicitly pinned. Already in place and relied upon: the shared `dialog_contract.py` modal helpers, the banned-pattern gate's existing `wx.ALIGN_RIGHT` and raw-`wx.Dialog` destroy-path checks, and the existing behavior tests for preview, web-form, and onboarding navigation.

**Execution waves.** DLG-3 proceeds as: Phase 0 — authoritative source-generated registry + gates (delivered); Phase 1 — strengthened A11Y-4 static guard (delivered); Phase 2 — native conversion wave for hand-rolled dialogs that are really a single confirm / choice / text prompt, replaced with the stock one-shot equivalent, preserving all user-facing wording and outcomes; Phase 3 — enhanced-native standardization wave converging the genuinely multi-control dialogs onto one focus/default/lifecycle grammar via the shared contract (never flattened into one-shots where that would lose live search, lists, or streaming); Phase 4 — web-surface standardization only where rich rendering or dynamic forms are justified, with native-fallback parity and no raw HTML dumped into document tabs in onboarding/welcome paths; Phase 5 — startup/onboarding hardening (wizard, first-run, trust consent, crash recovery) for deterministic focus across chained modals, preserving the explicit-consent requirements and retiring the screen-reader startup-crash path; Phase 6 — assistant/AI tool dialog consolidation (`assistant_tools.py`, `ai_model_panel.py`, `style_panel.py`, `assistant_panel.py`) onto the same modal/focus/error contract with safe async/"busy" semantics; Phase 7 — CQ-16 characterization expansion around dialog-launch command paths (return values and side effects) before any CQ-1 decomposition; Phase 8 — manual NVDA baseline, JAWS spot (startup, assistant, sticky notes, watch profiles), and Narrator sanity passes across `dialogs.md`, each row carrying pass/fail evidence.

**Dialog-by-dialog coverage map (no section exempt).** Every checklist family in `dialogs.md` is in scope with a default disposition: file/session dialogs (native-flow normalization + modal/focus hardening); settings/customization/dialog-launch surfaces (enhanced-native consistency — menu editor, settings, command palette); navigation dialogs (keep stock/input surfaces, harden bookmark/list/tree flows); text-analysis dialogs (normalize spell/lookup/thesaurus list workflows); accessibility-tools dialogs (focus/read-order consistency in results dialogs); intake/report dialogs (standardized preview/report modals); read-aloud/OCR dialogs (keep the OCR review contract, harden nested chooser flows); sticky-notes dialogs (retain web-form where justified, harden vault/list/editor transitions); external-tools/format dialogs (enhanced-native standard patterns); compare dialogs (consistent list/option/preview focus); keymap dialogs (stock controls + predictable nested edit flow); appearance/backup/import dialogs (import/export previews and file-picker transitions hardened); watch-folder dialogs (nested editor/browse/preview paths hardened); notifications dialog (standardized close/default semantics); formatting dialogs (preserve `show_web_form` for Insert Link, harden list/YAML nested flows); macros dialogs (text-entry + management standardization); AI/assistant dialogs (the DLG-2 conversions folded in); BITS speech dialogs (provider/model/status contract hardening); feature/profile dialogs (profile-switch, health, and management consistency); help/startup/support dialogs (wizard/about/diagnostics/report-bug rendering and focus safety); selection-action dialogs (action-chooser semantics hardened); nested/secondary dialogs (explicit coverage for each path launched from a parent); power-tools dialogs (stock prompt/confirm consistency); and startup-only dialogs (crash recovery + untrusted-location remain top-priority hardened native flows).

**Conversion decisions (definitive).** Keep `native`: simple confirms and binary prompts, and stable stock file/folder/select/text prompts. Keep sanctioned `web`: markdown/HTML preview and rich rendered content, explicit multi-field forms where `show_web_form` is already stable and fallback-backed, and chat-centric surfaces with native fallback. Harden `hardened_custom` (not a web rewrite by default): complex list/CRUD/picker dialogs where stock controls are appropriate and lower-risk than a web migration, and interaction-heavy assistant panels that are not rich-rendering-centric. No untouched custom paths: any retained custom dialog must carry a written rationale plus a contract test.

**Operational mandates (enforcement, not intent).** Machine-enforced checks that must pass before merge: the expanded A11Y-4 banned-pattern gate with zero violations; the dialog-registry completeness check (no orphan dialogs); the source-contract tests for touched dialogs; the characterization checks for dialog-launch command paths; and the project-wide source-scan check (no dialog constructor or call-site outside the inventory). "Manual QA later" is never a substitute for these gates. Manual accessibility verification is release-blocking per touched family: a keyboard-only pass (open, traverse, act, cancel, close, focus return), a screen-reader pass (NVDA baseline; JAWS/Narrator spot by risk), a nested-flow pass (child dialogs launched from parents), and a fallback-parity pass (web-backed dialogs validated in native fallback). Every dialog change records its impacted dialog id(s), the control surfaces touched, the classification decision, the tests added/updated, and the manual verification result; missing evidence means the change is incomplete.

**Anti-regression controls.** No mixed ad-hoc modal patterns may be introduced during the refactor; no dialog merges without a classification and test evidence; and no `dialogs.md` drift is allowed in a PR. The source-of-truth rule is absolute: before closing any dialog work item, run the inventory scanner across the entire `quill` package, and if scanner output and the committed registry disagree, the work is incomplete regardless of checklist status.

**Definition of done.** DLG-3 is done only when: 100% of source-scanned dialogs are touched and classified (not just a legacy checklist count); simple confirm/message/choice/text flows are native one-shots; rich/input flows use only sanctioned web surfaces with fallback parity; every control in every dialog is inventoried and dispositioned (`keep`/`harden`/`replace`); any retained `hardened_custom` dialog has an explicit rationale and at least one focused source-contract or behavior test; the strengthened A11Y-4 guard blocks contract regressions; the startup wizard and first-run chains are stable and non-crashing with a screen reader active on Windows and macOS; and `dialogs.md` is synchronized with the final command paths and nested flows.

---

## 10. Technical infrastructure

This section is the canonical engineering blueprint for Quill. It defines the module structure, every dependency (pinned, licensed, justified), the per-feature technical specifications, the threading and concurrency model, the data layout, the build and packaging pipeline, supply-chain integrity, observability, the plugin runtime, the update mechanism, the security architecture, the development workflow, and the coding standards.

### 10.1 Module map and responsibilities

```text
quill/
  core/                       Pure-Python; no UI imports
    document.py               Document model: text buffer, line index, encoding, line endings, dirty state
    history.py                Undo/redo coalescing; persistent-undo serialisation
    bookmarks.py              Bookmark store with text re-anchoring
    locations.py              Recent locations ring + Mark ring
    backups.py                Backup manager, autosave, crash recovery
    settings.py               Settings load/save, schema validation, partitioned reset
    keymap.py                 Three-layer keymap (default · profile · user), chord engine, conflict detection
    commands.py               Command registry (id, title, description, when, default key, handler ref)
    palette.py                Palette scoring, prefix modes, recency/frequency
    sessions.py               Session save/restore, welcome-back snapshot
    fingerprint.py            SHA-256, atomic write helpers
    paths.py                  AppData layout helpers; sandbox roots
    events.py                 Internal event bus (sync; cross-thread queue)
    a11y/
      announce.py             Three-channel announcement funnel
      regions.py              Live region helpers
      transcript.py           In-process transcript capture (test-only)
    spell/
      engine.py               Public API: check_word, suggest, learn
      tokeniser.py            Unicode + code-aware tokeniser
      dictionary_stack.py     Priority stack (per-doc, per-project, personal, language, jargon)
      hunspell_backend.py     cyhunspell wrapper, thread-safe
      reranker.py             v1.1 experimental contextual reranker (interface only in v1.0)
      ignore.py               In-document ignore directives parser
  io/                         Format readers and writers; each module exports `read(path)`/`write(doc, path)`
    txt.py md.py html.py rst.py adoc.py org.py tex.py typst.py
    docx.py pptx.py xlsx.py odt.py odp.py ods.py rtf.py epub.py
    pdf.py                    Tier-1 pipeline + Tesseract fall-back
    subtitles.py              srt vtt sbv ass ttml scc stl cap
    code/                     One module per language family for tokenisation hints
    config/                   json yaml toml ini xml csv tsv
    email.py ics.py vcf.py rss.py atom.py opml.py jsonfeed.py
    daisy.py braille.py       BRF, BRL reading; back-translation deferred
    notebook.py               ipynb linearisation
    sqlite_view.py            Read-only schema + sample rows
    ocr.py                    Tesseract bridge
    detect.py                 Format auto-detect by magic + extension + sniff
    remote_transport.py       ABC + error hierarchy + chunked_copy + merge_headers
    http_transport.py         HTTPS download (verified TLS, _MAX_BYTES cap, progress)
    ftp_transport.py          FTP/FTPS open and save
    sftp_transport.py         SFTP open and save (paramiko, trust-first-use honoured)
    webdav_transport.py       WebDAV open and save (depth-1 PROPFIND, safe XML)
    s3_transport.py           Amazon S3 (and any S3-compatible) open and save
    s3_sigv4.py               Manual AWS SigV4 signer (boto3 fallback)
  ai/
    base.py                   Provider interface
    openai.py azure.py anthropic.py ollama.py
    pipeline.py               PDF reading-order pipeline, document reading-order pipeline
    safety.py                 Per-action consent, size caps, redaction
  ui/                         wxPython shell
    app.py                    wx.App, single-instance, theme loader
    frame.py                  Main wx.Frame; F6 region cycler
    editor.py                 wx.TextCtrl host + line/column tracker + selection helpers
    statusbar.py              Custom-layout wx.StatusBar with focusable cells
    menubar.py                Menu construction; live keybinding labels
    palette.py                Command palette frame
    keymap_editor.py          Settings page + inline rebinding capture dialog
    outline.py                Outline Navigator (wx.TreeCtrl)
    audit.py                  Accessibility Audit panel
    table_mode.py             Markdown/HTML table navigation overlay
    spell_panel.py            Spell-check dialog + quick-fix popup
    settings.py               wx.Treebook settings root
    dialogs/                  Find, Replace, FindAll, GoToLine, Bookmarks, Backups, OpenURL, UnicodeInsert, etc.
    accessible/               wx.Accessible subclasses for custom regions
    themes/                   Bundled theme token maps
    locale/                   gettext .po / .mo bundles
  platform/
    windows/
      shell.py                File associations, Jump List, ICustomDestinationList
      dpapi.py                Windows DPAPI key storage
      sr_detect.py            Active screen-reader detection
      sr_announce.py          NVDA / JAWS / Narrator direct-API bridges
      single_instance.py      Named-mutex + IPC port
      high_contrast.py        Windows High Contrast token translation
      tts.py                  SAPI 5 + OneCore enumeration for Read Aloud
  plugins/                    v1.1 plugin loader, manifest, sandbox; v1.0 ships the loader skeleton only
    api.py                    Stable interface re-exports
    manifest.py               JSON schema validation
  tools/                      Internal CLI tools (not shipped to users)
    gen_keymap_reference.py   Builds the Keyboard Reference markdown
    gen_vpat.py               Builds the VPAT/ACR
    a11y_audit.py             Local accessibility audit runner
  tests/
    unit/  integration/  a11y/  perf/  fixtures/
```

### 10.2 Complete dependency manifest

Every direct dependency is listed below with the pinned version range Quill 1.0 will ship against, the license, the reason it is in the tree, and any constraints. Pins are tight in production builds and loose in development.

#### 10.2.1 Runtime, Python

| Package | Version | License | Role | Notes |
| --- | --- | --- | --- | --- |
| `python` | 3.12.x | PSF | Runtime | Frozen with PyInstaller; 3.13 supported as soon as wxPython publishes wheels |
| `wxPython` | 4.2.2+ | wxWindows Library Licence | UI toolkit | Stock controls only; no `wx.lib.agw` controls in the writing path |
| `pywin32` | 308+ | PSF-style | Windows shell, DPAPI, COM | Required for file associations, Jump List, DPAPI |
| `comtypes` | 1.4+ | MIT | UIA notifications, SAPI 5 | Used by `quill.platform.windows.sr_announce` and `tts` |
| `wxasync` | 0.49+ | MIT | asyncio + wx integration | Runs AI HTTP calls and background OCR without blocking UI |
| `httpx` | 0.27+ | BSD-3 | HTTP for AI providers and Open from URL | Async; respects per-action consent |
| `charset-normalizer` | 3.3+ | MIT | Encoding auto-detect | Used by `io.detect` and editor encoding picker |
| `python-docx` | 1.1+ | MIT | DOCX read/write | Round-trips heading styles for export |
| `mammoth` | 1.7+ | BSD | DOCX → HTML/Markdown extraction | Used as fall-back when python-docx output is too raw |
| `python-pptx` | 1.0+ | MIT | PPTX read | Slides + speaker notes |
| `openpyxl` | 3.1+ | MIT | XLSX read (as table) | Sheets become sections |
| `odfpy` | 1.4+ | LGPL-2.1+ | ODT/ODP/ODS read | LGPL is acceptable as a dynamically loaded library |
| `ebooklib` | 0.18+ | AGPL-3 with linking exception | EPUB read | Only used as library; no AGPL linkage concerns |
| `beautifulsoup4` | 4.12+ | MIT | HTML/XHTML/SVG parsing | With `lxml` parser |
| `lxml` | 5.2+ | BSD-3 | XML/HTML parsing backend | |
| `markdown-it-py` | 3.0+ | MIT | Markdown parsing & rendering | With `mdit-py-plugins` for tables, footnotes, deflists |
| `mdit-py-plugins` | 0.4+ | MIT | Markdown extensions | |
| `docutils` | 0.21+ | Public Domain / BSD | reStructuredText parsing & outline | |
| `pdfplumber` | 0.11+ | MIT | PDF text & layout, tier-1 path A | |
| `pypdfium2` | 4.30+ | Apache-2.0 / BSD | PDF text, tier-1 path B | Native PDFium binary |
| `pdfminer.six` | 20240706+ | MIT | PDF text fallback path C | Used when A and B both score badly |
| `pikepdf` | 9.0+ | MPL-2.0 | PDF metadata + password handling | Wraps QPDF |
| `Pillow` | 10.4+ | HPND | Image handling for OCR and SVG raster fall-back | |
| `cyhunspell` | 2.0+ | MPL-2.0 | Hunspell binding for spell check | Hunspell dictionaries bundled per language |
| `regex` | 2024.7+ | Apache-2.0 / PSF | Unicode regex for find/replace | Replaces stdlib `re` where Unicode classes matter |
| `rapidfuzz` | 3.9+ | MIT | Palette and command fuzzy matching | |
| `unicodedata2` | 15.1+ | Apache-2.0 | Up-to-date Unicode tables | Powers Unicode Insert and tokeniser |
| `pyyaml` | 6.0+ | MIT | YAML read/write for sidecars and front-matter | `safe_load` only |
| `tomli` / `tomllib` | stdlib for read; `tomli-w` 1.0+ for write | MIT | TOML | |
| `jsonschema` | 4.23+ | MIT | Settings, keymap, plugin manifest validation | |
| `platformdirs` | 4.2+ | MIT | AppData/log directory discovery | |
| `keyring` | 25+ | MIT | Optional secondary credential storage | DPAPI is primary |
| `cryptography` | 43+ | Apache-2.0 / BSD | DPAPI fallback + signed manifest verification | |
| `pygments` | 2.18+ | BSD | Syntax tokenisation for code-aware spell check and tokeniser | Tokens only; no styling |
| `chardet` | 5.2+ | LGPL-2.1 | Encoding detection secondary | charset-normalizer is primary |
| `liblouis` (Python bindings) | 3.31+ | LGPL-2.1+ | Braille back-translation — deferred to v1.1 | Listed for reference |
| `python-magic` (or `puremagic`) | 0.4.27+ | MIT | Magic-number sniffing for `io.detect` | `puremagic` preferred (pure-Python) |

#### 10.2.2 Native binaries bundled

| Binary | Version | License | Use |
| --- | --- | --- | --- |
| Tesseract OCR | 5.4+ | Apache-2.0 | OCR for image PDFs and image documents |
| Hunspell dictionaries (en-US, en-GB, es-ES, fr-FR, de-DE, pt-BR, pl-PL, ja-JP) | latest | varies (mostly LGPL / Apache / public domain) | Spell-check dictionary stack |
| PDFium | bundled with `pypdfium2` | Apache-2.0 / BSD | PDF rendering and text |
| QPDF | bundled with `pikepdf` | Apache-2.0 / Clarified Artistic | PDF transformations |

LibreOffice, Calibre, Ghostscript, and unrar are **not** bundled; they are optional plugin dependencies (v1.1).

#### 10.2.3 Build and dev tooling

| Tool | Version | Role |
| --- | --- | --- |
| `uv` | 0.4+ | Fast dependency resolution; lockfile |
| `ruff` | 0.6+ | Lint + format |
| `mypy` | 1.11+ | Static type-checking (strict in core, gradual in ui) |
| `pytest` + `pytest-asyncio` | latest | Test runner |
| `pytest-wx` / custom fixtures | latest | wxPython test fixtures |
| `pywinauto` | 0.6.8+ | UI automation tests |
| `Accessibility Insights for Windows` (CLI) | latest | A11y audit in CI |
| `PyInstaller` | 6.10+ | Frozen build |
| `Inno Setup` | 6.3+ | Installer authoring |
| `signtool` (Windows SDK) | latest | EV code signing |
| `pip-audit` and `osv-scanner` | latest | Supply-chain vulnerability scan |
| `cibuildwheel` | latest | Multi-Python wheel builds for any C-extension we author |

#### 10.2.4 License posture

- Quill itself is **MIT-licensed** (default; final decision still tracked in Open Questions).
- LGPL components (`odfpy`, `chardet`, `liblouis`) are linked dynamically; we publish the license texts and a `THIRD-PARTY-NOTICES.md` in the installer.
- MPL-2.0 components (`cyhunspell`, `pikepdf`) are linked dynamically; modifications to those files (if any) are published.
- AGPL components (`ebooklib`) are used as a library; we do not host a network service that exposes their interface to end users, which keeps us outside the AGPL trigger.
- All licenses are aggregated automatically into `THIRD-PARTY-NOTICES.md` by `tools/gen_notices.py` at build time; the build fails if any new package lacks a license entry.

### 10.3 Per-feature technical specifications

Each feature in section 5 has an engineering spec here. The full table is large; the canonical form lives in `docs/QUILL-PRD.md` once development begins. The table below is the v1.0 commitment.

| Feature | Module(s) | Key APIs / Libraries | Threading | Storage | A11y wiring |
| --- | --- | --- | --- | --- | --- |
| Editor surface (5.2) | `ui.editor` | `wx.TextCtrl` with `wx.TE_MULTILINE \| wx.TE_RICH2 \| wx.TE_NOHIDESEL \| wx.TE_AUTO_URL` | UI thread | In-memory document buffer | Native stock control; MSAA edit role |
| Outline Navigator (5.16) | `ui.outline`, `io.*` outline emitters | `wx.TreeCtrl`, `markdown-it-py`, `beautifulsoup4`, `docutils`, `python-docx`, `pdfplumber` outline, `ebooklib` nav, `pikepdf` outlines | Outline build on worker; `wx.CallAfter` to populate | Per-document outline cache `outline_cache/<hash>.json` | TreeCtrl exposes hierarchical structure to AT |
| Jump-by-structure (5.17) | `ui.editor`, `core.commands` | Same outline producers | UI thread (cheap) | n/a | Announces via `a11y.announce` |
| Line/block ops (5.18) | `ui.editor`, `core.history` | wx editor primitives | UI thread | Undo via `core.history` | Announcements per action |
| Statistics (5.19) | `core.document`, `core.metrics` | pure Python; `pyphen` optional for syllables (deferred) | Worker for large docs | n/a | Dialog with one `wx.StaticText` per metric |
| A11y Auditor (5.20) | `core.audit`, `io.*` audit emitters | `markdown-it-py` AST, `beautifulsoup4`, `python-docx`, `pikepdf` | Worker thread | Per-doc ignore list in sidecar | List dialog; severity prefix in text |
| Table Mode (5.21) | `ui.table_mode`, `io.md` table tokens | `markdown-it-py` tables, BS4 for HTML | UI thread | n/a | Announces column header on entry |
| Editor essentials (5.22) | `ui.editor`, `core.document` | `charset-normalizer`, stdlib `io` | I/O off-thread | Per-doc prefs in `file-prefs.json` | Encoding/EOL cells in status bar |
| Open from URL (5.27) | `ui.main_frame.open_url`, `io.http_transport` | `urllib.request`, `quill.core.net.verified_ssl_context` | I/O off-thread; result lands in temp file | Per-session temp file | Confirms host and Content-Length before download; announces on completion |
| Remote Sites (5.27a) | `ui.remote_sites_dialog`, `core.remote_sites`, `io.remote_transport`, `io.{http,ftp,sftp,webdav,s3,s3_sigv4}_transport` | `urllib` (HTTPS, WebDAV, S3), stdlib `ftplib` (FTP/FTPS), `paramiko` (SFTP), `defusedxml` (S3 + WebDAV XML), `quill.core.safe_xml`, `quill.core.net.verified_ssl_context` | I/O off-thread; UI marshals through `wx.CallAfter` | Sites in `%APPDATA%\Quill\remote-sites.json`; passwords in Windows Credential Manager / DPAPI file / Keychain | Native `wx.ListCtrl` directory pane; announces host and size; read-only by default |
| Menu bar (5.1a) | `ui.menubar`, `core.commands` | `wx.MenuBar` | UI thread | n/a | Menu items show live keybindings; mnemonics |
| Status bar (5.1b) | `ui.statusbar`, `ui.accessible.statusbar_cell` | Custom `wx.StatusBar` layout with focusable buttons; `wx.Accessible` subclass | UI thread with debounced events | n/a | Each cell exposes name/role/value/description via MSAA + UIA |
| Command palette (§7) | `ui.palette`, `core.palette` | `wx.SearchCtrl` + `wx.ListBox`; `rapidfuzz` | Match on UI thread (≤30 ms) | Recents in `palette-recent.json` | Combobox-style; live region for status |
| Keymap (§8) | `core.keymap`, `ui.keymap_editor` | Custom chord engine; `wx.AcceleratorTable` per context | UI thread | `keymap.json`; `.tmp`+rename | Capture dialog announces every keystroke |
| Spell check (§6) | `core.spell.*` | `cyhunspell`, custom tokeniser | Background pass on worker; quick-fix on UI | `personal.dic`, `<doc>.quill.yml` | Dedicated panel + quick-fix popup |
| Find/Replace (5.7) | `ui.dialogs.find`, `core.document` | `regex` module | Worker for very large docs | `search-history.json` | Announces structured one-liner per match |
| Bookmarks (5.10) | `core.bookmarks` | pure Python; SHA-1 of path | UI thread | `bookmarks/<hash>.json` | List dialog; re-anchor on jump |
| Backups + autosave (5.13, 5.39) | `core.backups` | stdlib | I/O thread; debounced | `backups/`, `autosave/`, `.tmp`+rename | Recovery prompt at launch |
| Read Aloud (5.25) | `platform.windows.tts`, `ui.read_aloud` | SAPI 5 via `comtypes`; OneCore via Windows.Media.SpeechSynthesis WinRT | Background voice thread | n/a | Uses a _secondary_ voice; never blocks SR |
| Open from URL (5.27) | `ui.dialogs.open_url`, `ai.safety` | `httpx` async | asyncio via `wxasync` | Temp file | Consent dialog announces host + size |
| AI reading-order (5.5, 5.4 tier 3) | `ai.pipeline`, `ai.openai/azure/anthropic/ollama`, `ai.safety` | `httpx` async; per-provider SDK shapes | asyncio via `wxasync` | Nothing stored | Progress announced every 20 s |
| OCR (5.4) | `io.ocr`, `pytesseract` | Tesseract binary | Worker process per page | n/a | Progress announced |
| Diff/Compare (5.22) | `core.diff` | stdlib `difflib`, `regex` | Worker | n/a | Diff opens as a normal document |
| Notifications centre (5.35) | `core.events`, `ui.notifications` | Internal event bus | UI thread | In-memory | Cell + dialog |
| Sessions (5.22, 5.49) | `core.sessions` | pure Python | I/O thread | `sessions/last.json` | Prompt at launch |
| Templates + snippets (5.22) | `core.templates` | pure Python | UI thread | `%APPDATA%\Quill\templates`, `snippets/` | List dialogs |
| Atomic stores (5.55) | `core.fingerprint`, `core.paths` | stdlib `os.replace` | All write paths | All JSON stores | Recovery announcements |
| Plugin loader skeleton (v1.0; full plugin runtime v1.1) | `plugins.api`, `plugins.manifest` | `importlib.metadata`, `jsonschema` | UI thread on load; isolated thread per task | `%APPDATA%\Quill\plugins\` | Manifest must declare UI surfaces |

### 10.4 Threading and concurrency model

- **UI thread**: owns all wx widgets and the editor buffer. Never blocks for more than 16 ms.
- **I/O thread pool** (`concurrent.futures.ThreadPoolExecutor`, default 4): file open, save, autosave, backup writes, settings persistence, bookmark writes, fingerprint compute.
- **Compute thread pool** (default 2): spell-check background pass, outline build for very large documents, document statistics for >1 MB, accessibility audit for >100 KB.
- **asyncio loop** (via `wxasync`): all HTTP I/O (AI providers, Open from URL, update check). Cancellable per task.
- **OCR worker process**: Tesseract runs in a child process per OCR job, isolated to avoid GIL contention and crash blast radius.
- **Marshalling**: any callback into wx uses `wx.CallAfter` or `wx.CallLater`. No direct cross-thread wx calls.
- **Cancellation**: every long-running task accepts a `quill.core.events.CancelToken`. Cancellation is checked at fixed safe points (every page, every 1 MB of read, every HTTP chunk).
- **Backpressure**: the I/O pool uses bounded queues; new tasks wait, never spawn-and-forget.
- **No threading.Lock around shared mutable state in `core`**. The document model is owned by the UI thread; workers receive snapshots and return new snapshots; `wx.CallAfter` merges. This invariant is enforced by lint (`ruff` custom rule) that flags `threading.Lock` outside `platform/`.

### 10.5 Data layout (canonical)

```text
%APPDATA%\Quill\
  settings.json             Validated by jsonschema; .bak kept
  keymap.json               Validated; .bak kept; quarantine on corrupt
  recent.json               Last N files; default 10
  recent-locations.json     Per-session ring; ephemeral
  saved-searches.json       Saved search filters
  search-history.json       Last 100 search/replace terms; clearable
  file-prefs.json           Per-path encoding/EOL/wrap/indent/language memory
  sessions\
    last.json               Session restore data
    <name>.json             Named sessions
  bookmarks\
    <sha1-of-path>.json     Per-document bookmark store
  backups\
    <sha1-of-path>\
      <iso-timestamp>.bak   Save backups
  autosave\
    <session-id>\
      <doc-id>.snap         Crash recovery snapshots
      <doc-id>.snap.tmp     In-flight
  undo\
    <sha1-of-path>.undo     Persistent undo (opt-in)
  notes\
    <sha1-of-path>.md       Per-document scratchpad
  remote-sites.json         Saved FTP/SFTP/HTTPS/WebDAV/S3 sites
  credentials\              DPAPI-protected password store fallback
  outline_cache\
    <sha1-of-path>.json     Cached outline; invalidated on document mtime change
  dictionaries\
    personal.dic
    <lang>.aff / <lang>.dic
    jargon\<name>.dic
  spell-learning\
    learning.sqlite         Per-user learning (frequencies, rejection counts)
  templates\<name>.tpl
  snippets\<lang>.json
  plugins\<plugin>\
  logs\quill-YYYY-MM-DD.log Rotating logs, 14-day retention
  diagnostics\               Output dir for Save Diagnostics
  trusted-locations.json
  notifications.json         Pending notifications
```

All JSON files validate against schemas in `quill/core/schemas/`. All writes are atomic (`tempfile.NamedTemporaryFile` in the same directory + `os.replace`).

### 10.6 Packaging, signing, supply chain

- **Frozen build**: PyInstaller with one-folder layout (faster start than one-file). UPX disabled (no compression; SmartScreen friendliness, debug symbols intact).
- **Installer**: Inno Setup 6 with per-user (`{userappdata}`) default, system-wide optional. Components: Core, Tesseract OCR (English by default; additional languages downloadable post-install), Hunspell dictionaries (launch-language set by default), JAWS script (optional). License screen lists `THIRD-PARTY-NOTICES.md`.
- **Portable zip**: identical layout without registry writes; uses `%APPDATA%` per Windows convention.
- **Signing**: EV code-signing certificate; `signtool` signs every `.exe`, `.dll`, and the installer; timestamps via DigiCert RFC 3161 timestamp server. SmartScreen reputation built before public launch.
- **Reproducible builds**: the build pipeline pins every dependency via `uv` lockfile; the lockfile is committed; the build container is pinned to a SHA-tagged Windows image.
- **SBOM**: a CycloneDX 1.5 SBOM is generated per build (`tools/gen_sbom.py` using `pip-audit --format=cyclonedx`) and attached to the GitHub release.
- **Supply-chain scanning**: every PR runs `pip-audit` and `osv-scanner`; CRITICAL or HIGH vulnerabilities fail the build.
- **Provenance**: GitHub Actions runs with OIDC; artefacts are signed with Sigstore `cosign` and the `cosign.bundle` is published next to each release artefact.
- **Update channel**: a signed JSON manifest (Ed25519 signature; key pinned in the app) lists current stable, beta, and security-only releases with SHA-256s. Quill checks on launch only when the user has opted in (manual `Check for Updates` is always available).
- **Footprint**: realistic target is 180–220 MB installed with English Tesseract data and English/UK + Spanish/French/German Hunspell dictionaries. A **Quill Lite** option ships at ~90 MB and downloads dictionaries and Tesseract on first use.

### 10.7 Build and dev environment

- **Python 3.12** pinned via `uv python install`.
- **Lockfile**: `uv.lock` committed; `uv sync` reproduces the dev environment exactly.
- **Dev install**: `uv sync --all-extras` plus `pre-commit install` for hooks.
- **Pre-commit**: ruff format, ruff lint, mypy on `core/` and `io/`, controlled-vocabulary linter, contrast checker, tab-order snapshot check, license-notice generator.
- **Local accessibility audit**: `python -m quill.tools.a11y_audit` launches Quill under pywinauto and runs the static + headless layers in under five minutes.
- **Local SR scenario**: `python -m quill.tools.sr_scenario --scenario find_chain --reader nvda` launches NVDA against Quill, replays a scenario, and writes a transcript to `out/`.

### 10.8 Continuous integration and delivery

- **Provider**: GitHub Actions.
- **Matrix**: Windows 10 22H2, Windows 11 24H2; Python 3.12; wxPython current stable.
- **Jobs**:
  1. **Lint** (ruff, mypy, jsonschema validation of bundled schemas).
  2. **Unit tests** (`pytest tests/unit -n auto`).
  3. **Integration tests** (`pytest tests/integration`); covers every format reader and writer against a fixture corpus stored in Git LFS.
  4. **A11y static** (controlled vocab, plain language, keymap audit, contrast checker, tab-order snapshot diff).
  5. **A11y headless** (`pytest tests/a11y` via pywinauto + Accessibility Insights CLI).
  6. **Perf smoke** (`pytest tests/perf`, asserts the targets in §11).
  7. **Build** (PyInstaller, Inno Setup, signtool, Sigstore cosign).
  8. **Supply chain** (pip-audit, osv-scanner, SBOM generation).
  9. **SR scenario nightly** (NVDA scenarios on a self-hosted runner).
- **Release branch**: `release/x.y` triggers a full build + sign + publish to GitHub Releases and the auto-update manifest.
- **Triage SLA**: SR transcript diffs reviewed within 24 hours.

### 10.9 Observability

- **Logging**: stdlib `logging`, rotating file handler, INFO level by default. Log records contain action name, outcome, duration; never document content; paths are hashed.
- **Crash handler**: a `faulthandler`-based hook writes a `quill-crash-YYYY-MM-DDTHHMMSS.dump` with the Python traceback and a redacted environment snapshot. On next launch Quill offers to include the crash in a diagnostics bundle for support; never auto-sends.
- **Metrics**: opt-in only; counters per feature use; transported by `httpx` to a self-hosted endpoint over TLS; cleartext example shown before opt-in.
- **Event bus**: an internal sync event bus (`core.events`) records the last 50 commands and notable lifecycle events; these are what Help → Save Diagnostics ships.

### 10.10 Plugin runtime (v1.0 surface, v1.1 full)

- **v1.0**: the plugin loader skeleton exists; only first-party plugins (JAWS script, additional Hunspell dictionaries) are loadable. The full third-party plugin runtime ships in v1.1.
- **Manifest** (`plugin.json`): id, name, version, license, capabilities (`commands`, `format_reader`, `format_writer`, `palette_entry`, `settings_page`, `keybinding_default`, `statusbar_cell`), requested permissions (`network: never|on_action`, `filesystem: read|write`, `subprocess: none|listed`).
- **Discovery**: `%APPDATA%\Quill\plugins\<id>\plugin.json` plus `entry_points` group `quill.plugins` (for pip-installed plugins).
- **Lifecycle**: load → register → enable; disabled plugins keep their settings.
- **Sandboxing (v1.1)**: each plugin runs in its own thread; network and subprocess calls require an explicit per-action consent or a setting that whitelists the plugin's manifest-declared hosts; UI surfaces created by plugins must pass the same accessibility static checks as core.
- **Versioning**: plugins declare the Quill API version they target; the loader rejects mismatched majors.

### 10.11 Security architecture

- **Secrets**: AI provider keys and remote site passwords are stored via Windows Credential Manager where available, with DPAPI-encrypted fallback (`platform.windows.dpapi`) when vault APIs are unavailable; never in plain text on disk; never logged; never in diagnostics bundles. macOS builds use the Keychain facade at `platform.macos.keychain`.
- **Document data**: never leaves the machine without per-action consent.
- **Network calls**: an internal `ai.safety.consent(action, host, size_estimate)` gate is required before any network call; the call records what was sent (action name, host, size only) in the audit log. Remote I/O is inventoried in `quill/tools/network_egress_audit.py`; a new transport call site without a written rationale is a CI failure.
- **Untrusted XML**: S3 and WebDAV listings are routed through `quill.core.safe_xml.fromstring`. Documents that declare a DTD or custom entity (billion-laughs, XXE) are refused with a friendly `RemoteTransportError` and never reach the parser.
- **Updates**: manifest signature verified with a pinned Ed25519 public key; artefact SHA-256 verified before install.
- **File handling**: file dialogs use the OS dialog (`wx.FileDialog`) so the user controls disclosure scope; the trusted-locations system (5.31) prevents silent opening of suspicious files.
- **Path traversal**: every settings/keymap/plugin path is normalised and validated; no `..` segments accepted.
- **JSON parsing**: bounded depth and size via custom decoder hooks; refuses to parse settings files over 10 MB or beyond depth 32.
- **YAML parsing**: `safe_load` only.
- **Subprocess**: limited to Tesseract and (post-v1.1) plugin-declared binaries; arguments are always passed as lists; no `shell=True`.
- **Threat model**: a malicious document might try to (a) crash the parser, (b) request a keymap override to bind dangerous keys, (c) trigger an outbound network request. (a) parsers are fuzz-tested with `atheris`; (b) keymap overrides require explicit consent (5.50); (c) network is gated.
- **Responsible disclosure**: a `SECURITY.md` file documents the disclosure email and PGP key.

### 10.12 Update mechanism

- v1.0 ships **manual update check**: `Help → Check for Updates…` fetches the signed manifest, verifies it, compares versions, offers to download the next stable.
- The download is verified (SHA-256) and Sigstore-attested; the installer is signed; the user runs it.
- The asset download streams in fixed-size chunks and reports progress through an accessible callback, so screen-reader users hear coarse, non-spammy progress announcements (for example 25/50/75 percent) instead of a silent wait.
- After a successful download Quill presents an **Update downloaded** dialog offering, as available, **Install now…** (Windows `.exe`/`.msi`), **Open the containing folder**, or **Close**. Install-now runs the in-app pre-update health check first.
- The update-available dialog includes a **Skip this version** action; a skipped version is remembered and suppressed on silent launch checks until a newer version appears or the user checks manually.
- Silent launch checks are throttled to at most once per 24 hours (recorded via the last-check timestamp); a manual `Check for Updates` always runs regardless of the throttle.
- A small in-app pre-update health check ensures the user's editor has no unsaved documents before launching the installer.
- Auto-update lands in v1.1 with a Squirrel-style delta channel.

### 10.13 Internationalisation infrastructure

- All UI strings flow through `gettext`; the `_()` callable is the sole permitted lookup.
- `.po` source files live under `quill/ui/locale/<lang>/LC_MESSAGES/quill.po`; `.mo` are compiled at build time.
- Pluralisation uses `ngettext`.
- Date/number formatting uses `babel`.
- Bidirectional text in user documents is rendered by the OS edit control; full RTL UI is v1.2.
- A translation portal (Weblate or Crowdin) is set up at v1.0 beta; community translators are credited in About and release notes.
- Translation operations follow a documented contributor plan with:
  - gettext `POT -> PO -> MO` workflow,
  - translator comments and placeholder-preservation rules,
  - beta translation push and pre-release string freeze,
  - CI quality gates for extraction, syntax, compile, and placeholder validation.
- Contributor process and policy reference: `docs/translating.md`.

### 10.14 Performance budgets and instrumentation

All performance targets in §11 are enforced by `tests/perf/`. Each test asserts against a budget; regressions over 15% fail the build. Microbenchmarks live next to the code they measure. Real-world startup time is measured by a stopwatch fixture that uses Windows' high-resolution timer.

### 10.15 Coding standards and review

- **Style**: ruff format (PEP 8 with relaxed line length 100).
- **Typing**: strict mypy in `core/` and `io/`; gradual in `ui/`; types required on all public functions.
- **Docstrings**: Google style; every public API has one.
- **Imports**: absolute; no wildcard imports; `wx` may only be imported from `quill.ui` and `quill.platform.windows`.
- **Public API stability**: `quill.core`, `quill.io`, `quill.plugins.api` follow semver; breaking changes require a major bump and a deprecation cycle of one minor version.
- **PR review**: two approvals required; one must be from a maintainer; any change to `ui/`, `core/a11y/`, or `core/keymap.py` additionally requires sign-off from the accessibility lead.
- **Issue triage SLA**: P0 (data loss, crash on launch, accessibility regression) within 24 h; P1 (function broken) within 5 business days; P2 within the next release.

### 10.16 Module ownership and SOLID boundaries

- `core/*` knows nothing about `wx`; tested without UI; can be reused by a future TUI or web front-end.
- `io/*` modules each export `read(path) -> Document`, optionally `write(doc, path)`, and `outline(doc) -> Outline | None`; no other contracts.
- `ui/*` modules consume the command registry and the document model; UI components never read from disk directly.
- `platform/windows/*` is the only place where `pywin32`, `comtypes`, or registry access is allowed.
- `ai/*` modules conform to a single `Provider` ABC with `complete`, `improve_reading_order`, `cancel`, `estimate_cost` methods.
- `plugins/api.py` is the only file plugins import from; everything else is internal.

### 10.17 Magic, by construction

The engineering choices above add up to the user-visible magic the product promises:

- Stock controls everywhere keep MSAA/UIA pristine; speech is correct without scripts.
- Atomic writes plus `.bak` plus autosave plus persistent undo make "I lost work" almost impossible.
- A single announcement funnel keeps speech behaviour identical across NVDA, JAWS, and Narrator.
- Pinned, audited dependencies and reproducible builds keep "works on my machine" out of the loop.
- A small command registry plus a three-layer keymap plus a discoverable palette mean every feature is reachable, learnable, and rebindable.
- A WCAG matrix wired to CI means accessibility cannot quietly regress; if it slips, the build fails.

---

## 11. Performance targets

- Cold start to blank document: under 1.5 seconds on a 2020-era laptop.
- Open a 200-page text-based PDF (local extraction): under 6 seconds.
- Open a 1 MB Markdown file: under 250 ms.
- Find first match in a 1 MB document: under 100 ms.
- Spell check full document (50 000 words, en-GB): under 1.2 seconds.
- Quick-fix suggestion ranking per misspelling: under 10 ms.
- Command palette open + first results visible: under 50 ms.
- Memory at idle with one empty document: under 150 MB.
- Autosave write: under 50 ms, non-blocking.

---

## 12. Privacy and security

- Local first. Nothing leaves the machine without an explicit per-action confirmation.
- AI provider keys stored via Windows Credential Manager when available, with DPAPI-encrypted fallback; never plain text.
- **Remote site passwords** (FTP, SFTP, WebDAV, S3) follow the same three-tier ladder: **Windows Credential Manager → DPAPI-protected JSON under `%APPDATA%\Quill\` → macOS Keychain facade**. Plain-text on disk is never the path of last resort.
- Logs never include document content. Logs include action names and outcomes only.
- Spell-check learning data stays on disk under the user profile and can be wiped from a single button.
- Crash reports are opt-in and scrubbed of paths and content.
- All file dialogs use the OS dialog so the user controls disclosure.
- **Remote I/O gating.** Every outbound call site is inventoried in `quill/tools/network_egress_audit.py` with a written rationale. A new transport call that is not added to that inventory is a CI failure. Cloud endpoints (S3, HTTPS, WebDAV-over-HTTPS) must use TLS; FTPS is enforced when available. Verified TLS context (`quill.core.net.verified_ssl_context`) is used for every HTTPS request.
- **Untrusted-XML protection.** S3 and WebDAV listings are parsed through `quill.core.safe_xml.fromstring`, which routes through `defusedxml` and refuses any document that declares a DTD or custom entity. The transport layer translates both parse errors and unsafe-XML refusals into a typed `RemoteTransportError` so the screen reader announces a single, friendly message.
- Network calls show host, payload size, and estimated cost (where the provider supplies it) before sending.
- Startup includes a trust/privacy/responsible-AI consent acknowledgement before guided onboarding continues.

---

## 13. Internationalisation and localisation

- All UI strings wrapped in `_()` from `gettext`.
- Initial languages: English (US), English (UK), Spanish, French, German, Brazilian Portuguese, Polish, Japanese.
- Right-to-left support deferred to v1.2.
- Spell-check dictionaries shipped for the initial languages plus a downloader for others.

---

## 14. Telemetry

- Off by default. The setting is presented in plain language, with an example payload shown verbatim before opt-in.
- If enabled, anonymised counters only: feature used, error counts.

---

## 15. Success metrics

- Time to open a typical PDF and reach the first searchable word.
- Number of screen-reader announcement regressions per release (target: zero).
- Crash-free sessions per week (target: 99.5 percent).
- User-reported "I lost work" incidents (target: zero, hard).
- Spell-check first-suggestion acceptance rate after 30 days of use (target: above 70 percent).
- Command palette task completion time vs menu navigation (target: at least 2x faster for top 20 commands).
- Adoption: monthly active users among the NVDA add-on community.
- Qualitative: 20+ unsolicited testimonials in the first 6 months saying "this feels calm."

---

## 16. Release plan

v1.0 is locked to features we can build and ship at the highest quality bar with no novel research dependencies and no fragile third-party requirements. Anything that requires unproven libraries, brittle parsers, ML training, or external binaries beyond the bundled set is deferred to the backlog in [section 17](#17-backlog-and-deferred-items).

Every v1.0 feature in the list below is **Confidence A**: a defined library exists, a known engineering path is mapped, accessibility behaviour is predictable, and a working prototype can be produced in a single sprint.

### 16.1 v0.9 alpha (internal, 6 weeks)

- Application shell, multi-document, menu bar, status bar.
- Editor with full standard editing, undo/redo, word delete, case conversion, line operations (5.18), smart paste.
- Open and save: `txt`, `md` and family, `html`/`htm`/`xhtml`, all source-code and config text formats, all subtitle text formats, `json`/`yaml`/`toml`/`xml`/`csv`/`tsv`, `rst`, `adoc`, `org`, `tex`, `bib`, `typ`.
- Recent files; Settings skeleton; Backups and autosave.
- Find and replace (case, whole word, regex) with announcement of context line.
- Command Palette with command and recent-files modes; keymap editor read-only.
- NVDA announcement plumbing; baseline JAWS and Narrator behaviour via stock controls.

### 16.2 v1.0 beta (8 weeks after 0.9)

Adds, in order of priority:

- **Quill Spell** with Hunspell baseline plus the dictionary stack (personal, per-document, per-language). Suggestion ranking is the Hunspell ranking. The contextual reranker is deferred to v1.1 experimental.
- Bookmarks with re-anchoring, Outline Navigator (5.16), jump-by-structure (5.17), Where Am I.
- DOCX read/write, XLSX read (as table), PPTX read, RTF read, ODT read, ODS read (as table), ODP read.
- EPUB read.
- PDF reading: **tier 1 local extraction only** (layered `pdfplumber` + `pypdfium2`, scored per page) plus PDF embedded bookmarks. Tier 2 "enhanced local" is removed from v1.0; tier 3 AI is moved to v1.0 release.
- Markdown preview-as-HTML, export to HTML, export to DOCX; HTML preview.
- Word count and document statistics (5.19); Accessibility Auditor (5.20); Table Mode (5.21); Editor Essentials (5.22).
- File associations and "Open with Quill" verb; Jump List integration (5.32).
- Full Command Palette with all prefixes; full Keymap editor with profiles and inline rebinding.
- Sessions, templates, snippets; Welcome-back snapshot (5.49).
- Encoding picker, EOL conversion, external-change watcher, reload from disk; per-file format memory (5.43).
- Compare with File (diff view); Save All with conflict detection (5.43).
- Link tools (5.37): Insert link `Ctrl+K`, Follow link `Ctrl+Enter`, quote indent/dedent.
- Search refinements (5.41): replace preview for >25 occurrences, saved searches.
- Recent locations history (5.23), Mark ring (5.24), Format-aware bracket nav (5.28), Format menu (5.29).
- Atomic on-disk stores (5.55) from day one.
- Onboarding flow (5.56), Privacy Summary (5.57), Licenses screen (5.58).
- Read-only mode (5.60); File menu helpers — Reveal in Explorer, Copy Path, Copy Name (5.61); Open Recent pin/unpin (5.62).
- Settings search (5.73); In-app changelog (5.74).

### 16.3 v1.0 release (4 weeks after beta)

Adds and hardens:

- DAISY 2.02 and 3 reading; BRF and BRL reading (no braille back-translation in v1.0; see backlog).
- SVG text mode; SQLite schema + sample row view (read-only).
- ICS, VCF, EML reading (RFC 822 standard email files); RSS, Atom, OPML, JSON Feed.
- Notebook (`.ipynb`) linearisation, read-only.
- Image OCR via local Tesseract (English by default; downloader for additional languages). Multi-page TIFF supported. Other image formats are deferred to plugins (see backlog).
- AI-assisted reading order (opt-in, requires user-supplied API key, transparent confirmations, progress announced).
- Optional JAWS script for live-region parity.
- Full localisation for launch languages: English (US), English (UK), Spanish, French, German, Brazilian Portuguese, Polish, Japanese.
- Signed Inno Setup installer plus portable zip. Manual update check with signed manifest (no auto-update in v1.0).
- Format Support settings page that lists every format, the engine handling it, the confidence grade (A/B/C), and whether a helper plugin can raise the grade.
- CI suite: unit tests for `quill.core`, integration tests for file readers/writers, accessibility checks for stock-control composition (no NVDA speech-viewer harness in v1.0; see backlog).
- Document Properties and front-matter editor (5.38); Document fingerprint (5.52).
- Read Aloud (5.25); Number Lines (5.26); Open from URL (5.27); Bookmark export/import (5.30); Trusted locations (5.31); Diagnostics and bug reporting (5.33); Welcome and Keyboard Reference (5.34); Notifications centre (5.35); What-changed-on-save (5.36, opt-in).
- Autosave control + persistent undo (5.39); Join paragraph + heading auto-numbering + footnote helper (5.40); Sort and transform details (5.42); Per-document scratchpad (5.44); Section folding announce-only (5.45); Spell-check ignore directives + manual bilingual flag (5.46); Word boundary mode + trailing whitespace + case-change announcement (5.47); Multi-format export + reading view (5.48); Per-document keymap override (5.50); Settings export/import/partitioned reset (5.51); Unicode insert (5.53); Idle-time prefetch (5.54).
- Crash recovery transparency (5.59); Document timeline (5.63); Sentence/paragraph nav (5.64); Word-count goal (5.65); Reading position memory (5.66); Compare with clipboard (5.67); Insert from file (5.68); Selection statistics shortcut (5.69); Audio cues opt-in (5.70); Quiet mode (5.71); Temporary trust (5.72); Crash-report opt-in (5.75).

### 16.4 v1.1

Plugin system; TinySpell interop plugin (dictionary sync only); additional AI providers; Pandoc bridge; Whisper transcription importer; LibreOffice headless bridge plugin (raises legacy `.doc`, `.ppt`, `.xls`, `.wpd`, iWork, OneNote quality from C to A); Calibre bridge plugin (raises `azw3`, `mobi`, `fb2`, `lit` to A); braille back-translation via liblouis; auto-update; spell-check contextual reranker (opt-in experimental); DjVu, comics, WARC, MSG/PST/MBOX.

### 16.5 v1.2

Right-to-left UI; additional languages; optional split view (still standard controls); reading-order learning per document; contextual reranker promoted to default; per-paragraph language detection; project workspaces and Find in Folder; chat-export readers (WhatsApp, Telegram, Slack, Discord, Teams, Zoom, Otter, ChatGPT) as plugins.

---

## 17. Backlog and deferred items

Everything below is intentionally out of v1.0. Each item is either yellow (achievable but requires more engineering than the v1.0 quality bar permits in time) or red (depends on unstable third-party formats, large native dependencies, or research-flavoured uplift we will not promise without measurement).

The organising principle is simple: **v1.0 ships only Confidence A. Confidence B and C land in v1.1–1.3 behind opt-in plugins and feature flags, with quality grades shown to the user.**

### 17.1 Format support deferred to plugins (v1.1+)

| Format | Why deferred | Target plugin |
| --- | --- | --- |
| Legacy Word `.doc`, PowerPoint `.ppt`, Excel `.xls` | Need headless LibreOffice for high quality; LibreOffice is a ~300 MB dependency | LibreOffice Bridge |
| WordPerfect `.wpd`, Works `.wps`, Windows Write `.wri`, StarOffice | Python bindings flaky on Windows; covered well by headless LibreOffice | LibreOffice Bridge |
| Apple iWork `.pages`, `.key`, `.numbers` | Modern iWork is a proprietary IWA archive; coverage is partial | iWork Bridge (best-effort) |
| OneNote `.one` | Closed format, no stable open library | OneNote Bridge via Microsoft Graph (requires sign-in) |
| Kindle `.azw3`, `.mobi`, FB2, LIT, LRF, PRC, PDB, TCR | Best handled by Calibre's conversion engine | Calibre Bridge |
| Kindle `.kfx` | DRM-protected by design; Quill will not break DRM | Calibre Bridge (user must already have a DRM-stripped copy) |
| DjVu | Native `djvulibre` dependency; installer weight | DjVu Plugin |
| Comics `cbz`, `cbr` | RAR (`cbr`) requires non-free `unrar.dll` | Comics Plugin |
| PostScript `ps`, `eps` | Needs Ghostscript native binary | PostScript Plugin |
| XPS, OXPS | Niche; needs additional reader | XPS Plugin |
| MSG, PST, MBOX | `libpff` works but coverage on encrypted/corporate PSTs is uneven | Mail Bridge |
| Web archives WARC, WACZ, `.webarchive` | Format zoo; useful but not ubiquitous | Web Archive Plugin |
| Parquet, Feather | Niche analyst use; large native deps | Data Files Plugin |
| EVTX, ETL | Native Windows log formats; niche audience | Logs Plugin |
| HEIC, AVIF, JP2 | Native binary dependencies (`pillow-heif`, `pillow-avif-plugin`) | Modern Images Plugin |
| Chat exports (WhatsApp, Telegram, Slack, Discord, Teams, Zoom, Otter, ChatGPT) | Export formats churn 2–4 times per year; requires ongoing maintenance | Chat Exports Plugin (independently versioned) |
| OneNote, Evernote `.enex`, Bear, Simplenote | Mixed formats; per-app quirks | Notes Bridge Plugin |
| Audio + transcript pair playback | Needs media playback; out of scope for core editor | Audio Transcript Plugin |

### 17.2 Features deferred

- **Spell-check contextual reranker.** Ships as opt-in experimental in v1.1 once measured uplift over Hunspell-alone is demonstrated on a labelled corpus.
- **Per-paragraph automatic language detection** for the spell-check dictionary stack. Short paragraphs and code-mixed text make this unreliable today.
- **Tier-2 "enhanced local" PDF extractor.** No pure-Python local layout analyser meets the bar. v1.0 ships tier 1 (local) and tier 3 (opt-in AI). A real tier 2 returns when there is a credible local model.
- **PDF heading synthesis from font-size analysis** when no embedded bookmarks exist. Available as an opt-in experimental switch but not promoted in v1.0.
- **Auto-update.** v1.0 ships manual update check with signed manifest. Squirrel-style auto-update lands in v1.1.
- **NVDA speech-viewer CI harness.** No supported automation API; we will build a test driver in v1.1.
- **Dynamic screen-reader shortcut introspection.** v1.0 uses a curated static list of well-known NVDA, JAWS, and Narrator chords; explains conflicts using that list. Dynamic introspection of user-customised SR bindings remains out of scope (no public API).
- **Right-to-left UI.** v1.2.
- **Project workspaces and Find in Folder.** v1.2.
- **Multi-cursor / column selection.** Not planned; conflicts with screen-reader navigation patterns.
- **History panel (visual undo stack).** Backlog.
- **Macro recording and playback.** Backlog.
- **Linked-notes / wikilink editor (Obsidian-style).** Backlog.
- **Per-file-class backup retention policy.** v1.0 ships a single global retention rule (5.13). v1.1 introduces per-format-class defaults (e.g. 100 backups for source code, 25 for long-form documents) once we have telemetry on user save patterns.
- **Single-line compose box mode.** A small, screen-reader-optimised composer dialog whose Enter sends back to the main editor at the cursor. Useful for slow-speech users; needs user testing to confirm it is worth the surface area. Backlog for v1.1.
- **Advanced model lifecycle in core app flow.** Quill now ships a local Writing Assistant shell, prompt presets, generated tool catalog, assistant onboarding, AI Hub entry point, Prompt Studio custom templates, Agent Center guided plans, AI connection preferences, connection verification/model discovery actions, searchable model selection, provider-aware guided recommendations, AI menu status-detail feedback, and sandboxed Python runner. Connection diagnostics use a structured error taxonomy that separates authentication failure (HTTP 401) from permission/access denial (HTTP 403), rate limiting, warm-up/not-ready states, local-server-not-running, and unreachable endpoints, with a bounded warm-up retry/backoff so a model that is still loading is reported as warming up rather than failed. The status taxonomy is matched on numeric status codes rather than substring matching, so host ports such as `localhost:11403` cannot be misread as a 403. Broader built-in model catalog lifecycle and background prefetch policy remain future work.

### 17.4 Explicitly out of scope for Quill (any version unless re-evaluated)

Quill is opinionated about what it is _not_. The following are intentionally and permanently out of scope unless a future PRD revision re-opens the question.

- **Visual word-processor styling in the editor.** No bold/italic/colour as direct formatting. Quill is screen-reader-first; users who want WYSIWYG should use Word. Markdown supports inline emphasis textually.
- **Real-time collaborative editing.** Not in v1.x. The architecture does not preclude it; we are not committing to it.
- **Cloud-sync of documents.** Sync is for keymap and settings only (8.8). Document storage stays on the user's machine and chosen cloud-drive folder.
- **Mobile, web, macOS, or Linux ports.** Cross-platform is post-v2 at earliest. The `core/` layer has no `wx` so it remains _possible_, not _committed_.
- **Voice input / dictation.** Use Windows dictation; Quill does not reinvent the mic/STT stack. An opt-in Hey QUILL command layer may sit on top of dictation and dispatch existing Quill commands, but it stays silent and only listens while dictation is active.
- **AI authoring assistant.** The current build exposes a local Writing Assistant shell, prompt presets, Prompt Studio reusable prompt templates, Agent Center guided profiles, AI Hub launch surface, AI connection preferences (Ollama local/cloud, OpenAI, Claude, OpenRouter, Gemini, custom OpenAI-compatible), provider verification/model discovery, searchable model filtering, status-detail accessibility announcements, and a sandboxed Python tool. The quick writing actions (Rewrite Selection, Summarize Selection, Continue Writing, Fix Grammar) each guard on the AI-enabled setting regardless of entry point (menu, command palette, or keybinding) and fall back to a sensible scope when there is no selection (paragraph at cursor for rewrite/grammar, whole document for summarize), announcing the chosen scope and word count. The AI status line also detects a saved key that cannot be decrypted on the current device (for example after a portable install is moved to another Windows account) and prompts the user to re-enter the key rather than reporting a generic authentication error. Longer-horizon autocomplete policy tuning and richer model-catalog management remain future work.
- **Project workspaces and Find in Folder.** Deferred to v1.2 (see 17.2).
- **Embedded media playback inside documents.** Out of scope for the editor.
- **PDF form filling and signing.** Out of scope.
- **Macro recording and playback.** Out of scope for v1.x.
- **Bundled font installation.** Quill uses system fonts only.
- **Telemetry by default.** Telemetry is and remains opt-in, off out of the box.
- **Anything that breaks DRM.** Quill will not include or escalate to tooling that removes DRM from any file, including KFX.

### 17.3 Confidence grades shown to the user

The Format Support settings page displays a grade per format:

- **Grade A**: bundled engine, high coverage, extensively tested. (All v1.0 in-box formats.)
- **Grade B**: bundled engine with known edge cases, or plugin with a stable upstream. Quality is good, occasional fallbacks expected.
- **Grade C**: plugin required to read at all, or the upstream format itself is unstable. Best-effort.

Grade is displayed prominently in the Open dialog when the user picks a file of a non-A format, with one line of context (“Kindle `.azw3` requires the Calibre Bridge plugin; current grade B with Calibre installed”) so expectations are set before the user hits Enter.

---

## 18. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Custom wx behaviour breaks a screen reader on a Windows update | Strict policy of stock controls; CI accessibility tests; rapid patch process |
| PDF extraction quality varies wildly | Layered extractors with scoring; manual escalation tiers; opt-in AI repair |
| AI provider API drift or pricing change | Provider-agnostic interface; user supplies key |
| Plugins introduce accessibility regressions | Manifest must declare UI surfaces; review checklist; plugins disabled by default |
| Custom spell engine underperforms TinySpell/Word | Layered architecture; Hunspell baseline; learning loop; published benchmarks |
| Keymap conflicts with screen-reader shortcuts | Explicit detection at capture time; refuse to capture conflicting chords with clear explanation |
| Localisation lags | Ship English first; community translation site; per-language readiness gates |
| Users expect bold and italic | Clear positioning; markdown supports inline emphasis textually; v1.x evaluation only after stable base |

---

## 19. Open questions

1. License: MIT for maximum adoption, or GPL to keep derivatives open. Leaning MIT.
2. Branding: Quill is a placeholder. Final name to be chosen with community input.
3. Should the contextual reranker be opt-in given memory cost?
4. JAWS scripts: ship a small one for live-region parity, or rely on `wx.Accessible` alone?
5. Hosting model for the community plugin registry.
6. Two-key chord sequences in default keymap: how many should we ship by default, given screen-reader users often prefer single chords?

---

## 20. Why this can be magical

The magic is not in any single feature. It is in the absence of friction:

- The window opens and the cursor is in the right place.
- Save just works. Save As appears exactly when it should.
- A PDF that was unreadable an hour ago becomes a clean searchable document with one keystroke.
- A bookmark you set last week still lands on the right paragraph after the document grew by three pages.
- The command palette knows the word you half remembered, and it tells you which key triggers it so you can learn the keystroke next time.
- If a keystroke does not suit you, you change it from the same palette without leaving the flow.
- Spell check is fast, local, and gets better the longer you use it. It never sends your writing anywhere.
- The screen reader never says anything you did not need to hear, and never goes quiet when you needed it to speak.
- When the power dies, the next launch returns your work.

Quill aims to feel like a very good fountain pen: simple in the hand, faithful on the page, and quietly delightful every time you reach for it.

---

## 21. Project delivery TODO (living checklist)

Last updated: 2026-06-02

Todo counts: **160 v1.0 items** | **160 completed** | **0 remaining** (v1.0 scope); post-1.0 foundation work tracked in 21.17+ below.

This is the implementation checklist for v1.0.0 and immediate post-1.0 foundations. It is intentionally granular and is updated in-place as work lands. The current shipping build is **0.1.5 Beta**; it implements the full v1.0 checklist (21.1–21.16) plus the post-1.0 foundation work recorded in 21.17 and later. Items still in progress are listed with `- [ ]`.

### 21.1 Application shell and document lifecycle

- [x] Bootstrap wxPython app shell with menu bar, editor, status bar.
- [x] Add optional system-tray mode (send to tray, restore, tray menu exit).
- [x] Implement true multi-document model (tabs/window document switcher).
- [x] Implement document close semantics (close tab, prompt/save/discard, frame-close handling).
- [x] Implement recent-document keyboard cycling (`Ctrl+Tab`, `Ctrl+Shift+Tab`) baseline.
- [x] Implement single-instance handoff IPC (open-in-existing-instance on second launch).
- [x] Implement F6/Shift+F6 region cycling across all declared regions.
- [x] Show live caret position in status bar (`Ln`, `Col`).
- [x] Add configurable status bar item layout (reorder + hide/show) through Status Bar Settings.
- [x] Show insert/overwrite mode in the status bar (`INS` / `OVR`).
- [x] Implement full status-bar interactive cell model from section 5.1b.
- [x] Add Save All command.
- [x] Add Reload from Disk command.
- [x] Add Restore Backup dialog with backup history selection.
- [x] Add sessions submenu for switching open documents.
- [x] Implement complete file menu set (sessions submenu, print/page setup).
- [x] Add Open Recent → Clear Recent Files action.
- [x] Add Save As Plain Text command.

### 21.2 Core editing and formatting

- [x] Open/save/save-as for plain text and markdown.
- [x] Soft-wrap toggle command and persisted preference.
- [x] Case transforms (upper/lower/title/sentence/toggle).
- [x] Line operations (move up/down, duplicate, delete, join).
- [x] TextMonkey-style cleanup transforms.
- [x] Sort selected lines ascending/descending.
- [x] Reverse lines.
- [x] Remove duplicate lines.
- [x] Trim trailing whitespace.
- [x] Normalize whitespace.
- [x] Convert indentation between tabs and spaces.
- [x] Markdown/HTML formatting commands: bold, italic, heading 1-6 with `Ctrl+Alt+1..6`.
- [x] Selection-aware tag wrapping (insert paired markers around highlighted text).
- [x] HTML tag picker with attribute entry.
- [x] Markdown tagging picker (code block, lists, link/image, table, footnote snippets).
- [x] Toggle line comment command.
- [x] Toggle block comment command.
- [x] Indent/outdent commands.
- [x] Insert list submenu commands (bullet/numbered/task) as dedicated menu actions.
- [x] Insert table workflow (guided table builder dialog).
- [x] Insert code block command with optional language hint support for Markdown/HTML.
- [x] Insert footnote command (baseline snippet insertion for Markdown/HTML).
- [x] Select line/paragraph/block and mark-ring operations.
- [x] Select to start/end of line and start/end of document commands.
- [x] Extend Selection mode toggle (`F8`) with movement-key range growth (Word-style shiftless selection).
- [x] Context menus in editor, status bar, and frame surface with right-click and Application/Menu-key invocation.
- [x] Add heading-level adjust commands (`Alt+Shift+Left` / `Alt+Shift+Right`) for Markdown/HTML headings.

### 21.3 Navigation, search, structure, and links

- [x] Go To Line with optional column target (`line,column`).
- [x] Go To Page baseline command (using form-feed page markers).
- [x] Find and Replace All.
- [x] Persistent search history.
- [x] Insert Link and Follow Link commands.
- [x] Set Bookmark and Go To Bookmark baseline commands.
- [x] Find Next / Find Previous command set (F3 / Shift+F3).
- [x] Find All Matches command (Alt+F3 baseline dialog).
- [x] Heading/block navigation commands.
- [x] Outline Navigator (tree model + jump + optional pinned mode).
- [x] Recent locations back/forward ring.
- [x] Match bracket and structural navigation.

### 21.4 Metrics, spell, and tools

- [x] Word count and baseline document stats.
- [x] Spell-check dialog and dictionary stack UX.
- [x] As-you-type spell check toggle + next misspelling flow.
- [x] Add-to-dictionary scopes (personal/document/project).
- [x] Accessibility Audit command and results panel.
- [x] Link inventory and alt-text catalog tools.
- [x] Compare-with-file diff workflow and interactive compare mode.
- [x] Read-aloud controls and voice selection.

### 21.4a Trust and verification

- [x] Document intake report on open.
- [x] Copy With Source command with source reference text.
- [x] Extraction quality review for PDF-derived documents.
- [x] Bad extraction support package command.
- [x] Context-sensitive "What Can I Do Here?" help.
- [x] Safe mode startup for troubleshooting.
- [x] Portable mode clarity and first-run storage choice.
- [x] Golden document corpus for release verification.

### 21.4b Power search

- [x] Plain text, whole word, regular expression, and wildcard search modes.
- [x] Plain-language regex error reporting.
- [x] Regex helper with common tokens and explanations.
- [x] Replace-all preview before apply.

### 21.5 Persistence, safety, and recovery

- [x] Persistent settings store.
- [x] Persistent keymap store.
- [x] Persistent recent files.
- [x] Backup snapshots on save.
- [x] Autosave snapshots.
- [x] Crash recovery flow at startup.
- [x] Persistent undo model (optional mode).
- [x] Trusted locations system and file trust prompts.
- [x] Notification center persistence model.

### 21.6 Command palette and keymap system

- [x] Command registry and command palette dialog.
- [x] Live keybinding labels in menu entries.
- [x] Runtime accelerator table generation from keymap.
- [x] Palette prefix modes (`>`, `?`, `:`, `~`) and scoped command sets.
- [x] Palette fuzzy ranking with frequency/recency tie-breakers.
- [x] Keymap editor UI with conflict detection and capture dialog.
- [x] Import/export/reset keymap workflows.

### 21.7 Format support and I/O coverage

- [x] Base text/markdown read-write path.
- [x] HTML read-write path.
- [x] DOCX read path (plus text-focused export path).
- [x] PDF tier-1 extraction path with quality scoring.
- [x] OCR bridge path and user-facing consent/progress UX.
- [x] EPUB/RTF/ODT baseline readers.
- [x] EPUB navigator dialog with chapter tree, preview pane, and chapter-open flow back into editor.
- [x] Config/data format readers (JSON/YAML/TOML/XML/CSV/TSV).
- [x] Notebook and SQLite read-only renderers.
- [x] Open from URL flow with safety checks.
- [x] Open from URL baseline (HTTP/HTTPS text fetch; advanced safety checks pending).

### 21.8 Accessibility and UX hardening

- [x] Screen-reader announcement bridge baseline.
- [x] Region entry/exit announcement consistency across all dialogs and panels.
- [x] Accessibility transcript capture for test harnesses.
- [x] Keyboard trap audit and tab-order snapshots.
- [x] Contrast and low-vision theme validation.
- [x] Controlled vocabulary + plain-language linting hooks.

### 21.9 Windows integration

- [x] Shell integration (Open With, file associations, jump list).
- [x] DPAPI key storage for provider credentials.
- [x] Screen-reader detection and adaptive hints.
- [x] High-contrast token mapping with Windows settings sync.
- [x] Installer flow (Inno Setup) and portable build variant.

### 21.10 AI, OCR, and optional network features (deferred to v1.1)

Deferred to v1.1:

- AI provider abstraction and per-provider adapters.
- Explicit consent-gated network action layer.
- Reading-order repair pipeline (opt-in).
- Task progress and cancellation UX for long-running operations.
- [x] Signed update manifest fetch and verification.

### 21.11 Engineering quality gates and release

- [x] Python project scaffold, lint/type/test tooling baseline.
- [x] Core unit-test suite for implemented modules.
- [x] Integration test corpus and runner wiring.
- [x] Accessibility test suite and CI automation.
- [x] Performance smoke suite aligned to section 11 thresholds.
- [x] SBOM generation, vulnerability scanning, and provenance artefacts.
- [x] Build/sign/release pipeline for Windows artefacts.
- [x] Third-party notices generation and license gate.

### 21.12 Documentation and readiness

- [x] Engineering docs baseline (`docs/QUILL-PRD.md`).
- [x] Roadmap mapping and architecture/module contracts.
- [x] PRD updates for HTML/Markdown tag picker and formatting shortcuts.
- [x] User guide and keyboard reference auto-generation pipeline.
- [x] Accessibility conformance report (ACR/VPAT) generation toolchain.
- [x] Diagnostics bundle specification and support runbook.

### 21.13 Profile safety and recovery

- [x] Add a "Why Don’t I See a Feature?" help command.
- [x] Add profile switch preview and change summary text.
- [x] Add undo for the last profile change.
- [x] Add emergency reset to the Essential profile from launch and recovery.
- [x] Add profile health checks to Quill Doctor and diagnostics.
- [x] Add CI coverage gates for feature IDs across commands and surfaces.
- [x] Add profile-aware keyboard reference views.
- [x] Add profile-aware welcome guide content.
- [x] Add privacy, network, dependency, and maturity labels for features.
- [x] Add profile import safety validation and locked feature protection.
- [x] Add "Show what changed" reporting after profile switches.
- [x] Add feature-flag coverage tests for new commands and surfaces.

### GLOW implementation roadmap

This roadmap is the GLOW-branded implementation order for the shared document-intelligence work now being folded into Quill.

1. **CSV Mode first.** Finish the accessible grid editor, the default-choice prompt, remembered CSV preference, and the ability to return to normal text editing at any time.
2. **Word support next.** Complete MarkItDown-first Word intake, semantic diagnostics, and review/fix hooks for `.docx` and legacy `.doc` flows.
3. **PowerPoint support next.** Finish slide linearisation, speaker-notes extraction, and reading-order diagnostics for `.pptx` and legacy `.ppt` flows.
4. **Then the rest of the document families.** Extend the same shared path to PDF refinement, EPUB/pages tuning, legacy Office fallbacks, version transparency, and provenance reporting.

The governing rules remain the same throughout the roadmap: local-first processing, no silent network calls, explicit consent for outbound content, and deterministic extraction before higher-level analysis.

### 21.14 Feature registry and profiles

- [x] Add a central feature registry module with metadata and dependency graphs.
- [x] Add layered feature-profile loading and merging.
- [x] Add shipped profile definitions for Essential, Writer, Reader and Student, Office and Admin, Accessibility Professional, Developer and Power Text, Low Vision, Braille and Screen Reader Power User, and Full Quill.
- [x] Add a Profiles and Features settings page.
- [x] Add first-run profile selection onboarding.
- [x] Add command, menu, status-bar, settings, help, and format-handler feature ID gating.
- [x] Add dependency enforcement when enabling and disabling features.
- [x] Add profile import/export storage with schema validation.
- [x] Add locked safety rules that cannot be overridden by user profiles or imports.
- [x] Add feature metadata labels for risk, maturity, privacy, and network impact.
- [x] Add profile comparison preview in the Profiles and Features page.

### 21.15 Macro and compare expansion

- [x] Implement macro command capture across menu/shortcut/palette execution (excluding macro control commands and playback recursion).
- [x] Complete macro management UX and persistence polish for Start/Stop/Play/Manage workflows.
- [x] Expand interactive compare commands (next/previous/current/list/sync toggle/options) beyond diff-tab-only hunk navigation.
- [x] Add multi-document interactive compare support (3+ open docs) with structured announcements.
- [x] Add compare summary and copy/export actions (copy current/all differences, save markdown summary).
- [x] Audit transform/convert menu placement and command-ID consistency after Convert-menu migration.
- [x] Synchronize PRD checklist details with implemented macro and compare scope.
- [x] Run macro/compare regression suite and resolve resulting failures.

### 21.16 wx stability and hang resistance

- [x] Add a `quill.stability` package for logging, diagnostics, dispatch, heartbeat, task management, safe subprocesses, guarded regex, memory tracing, safe mode, and feature contracts.
- [x] Configure startup logging through a queue-backed listener so the wx main thread never blocks on file I/O.
- [x] Enable faulthandler at startup and keep a manual thread-stack dump path available from the CLI.
- [x] Add a `wx.Timer` heartbeat and watchdog that detect stalled UI loops.
- [x] Centralize worker-to-UI handoff through `wx.CallAfter`, custom wx events, and a coalesced progress reporter.
- [x] Route user-supplied regex through timeout-aware matching helpers.
- [x] Add a safe subprocess helper with explicit timeouts.
- [x] Add optional tracemalloc support and diagnostic bundle support for freeze reports.
- [x] Add a Safe Mode configuration path and startup flag handling.
- [x] Add feature contract validation for risky features.

### 21.17 Watch Profiles automation engine

- [x] Replace the legacy single-folder watcher with a multi-profile `quill.core.watch_service` facade (wx-free).
- [x] Add `watch_profiles`/`watch_profile_store` with schema-validated, independently enabled named profiles.
- [x] Add `watch_queue`/`watch_worker` so watch processing runs off the UI thread and marshals results through `wx.CallAfter`.
- [x] Add `watch_actions` for per-profile actions (open in editor, run intake action).
- [x] Add the accessible Watch Queue Monitor (queued/in-progress/completed/failed, with retry) under the Watch menu.
- [x] Surface watch status and failures through the existing status/notification channel; no silent failures.

### 21.18 Settings home and feature profiles UI

- [x] Add a registry-driven tabbed Settings dialog rendered from `quill.core.settings_registry`.
- [x] Add a settings search box (SET-6) that jumps to a matching control across pages.
- [x] Add Reset to Factory Defaults and profile Import paths that re-apply settings consistently (theme, spellcheck, wrap, tabs, menus).
- [x] Add feature-profile export/import (`.qpf`) with schema validation and locked-safety enforcement.

### 21.19 Update experience enhancements

- [x] Enhance the in-app update checker with manual Check for Updates, throttled background checks, and a skip-this-version option.
- [x] Add accessible streaming download progress announcements and a post-download Install/Open/Close dialog (reveal in folder, launch installer).
- [x] Record `skipped_update_version` and `last_update_check` in settings (documented in sections 5.74 and 10.12).

### 21.20 Foundation work in progress (post-1.0)

- [x] Wire the `quill.core.menu_customization` model into an accessible Menu Editor UI for **top-level** menus: reorder, rename, show/hide, and one Reset to Factory Defaults, opened from Edit > Customize Menus... (`app.menu_editor`). The build applies the saved customization through a post-build transform pass on the menu bar that bails out untouched if anything looks unexpected.
- [ ] Extend the Menu Editor to per-item reordering/hiding and editor context-menu entries (the `quill.core.menu_customization` model already supports both; the remaining work is the item-level UI and a stable item-key binding in the menu build).

### 21.21 AI chat, Prompt Library, and Quillin Manager (Phase 2/3)

- [x] Add `ask_ai` dialog with provider selection (OpenRouter, OpenAI, Ollama), model list, and prompt field. Smart focus: prompt field when configured, provider choice when not. A11Y-4 hardened.
- [x] Add `check_grammar_with_ai()` command — sends selection or full document to AI; uses `ai_prompt_default_model` setting (falls back to `ai_chat_default_model`). Runs off UI thread.
- [x] Add AI Prompt Library (`quill/core/prompt_library.py`) with 12 built-in prompts, full CRUD, enable/disable, per-prompt optional shortcut, and `.pqp` import/export.
- [x] Add Prompt Library dialog (`quill/ui/prompt_library_dialog.py`) — searchable list, run with AI, new/edit/delete prompts, import/export `.pqp`.
- [x] Add `ai_prompt_default_model` setting in `Preferences > AI`.
- [x] Add bundled Quillin `ai-writing-prompts` with 7 prompts contributed to the Prompt Library at load time (no capability declaration needed; prompts.json sidecar pattern).
- [x] Add `install_extension()` to `quill/core/quillins/loader.py` with path-containment enforcement.
- [x] Add Install from Folder button to Quillin Manager; uses `wx.DirDialog` + `install_extension()`.
- [x] Add `.pqp` (Prompt Quill Pack) file format: `{"schema": "quill.prompt-pack/1", "name": "...", "prompts": [...]}`.
- [x] API keys stored exclusively in Windows Credential Manager (`quill-openrouter-api-key`, `quill-openai-api-key`, `quill-ollama-api-key`); never in `settings.json`.
- [x] Add `.sqp` (Skill Quill Pack) file format: `quill.skill/1` schema; YAML front matter + Markdown steps; parameters, condition branching, output blocks, use-prompt/use-skill delegation.
- [x] Add `quill/core/skill_pack.py`: parser, validator (`validate_skill`), synchronous runner (`run_skill`); no streaming by design.
- [x] Add `quill/tools/sqp_validator.py`: CLI validator with `--strict` mode.
- [x] Add bundled `ai-writing-skills` Quillin with 4 sample skills (Accessible Rewrite, Research and Draft, Meeting Notes to Action Items, Argument Strengthener).
- [x] Add `tests/unit/core/test_skill_pack.py`: 23 tests covering parsing, validation, runner, condition branching, depth limit, and all bundled files.
- [x] Add `quill/platform/windows/credential_store.py`: unified credential access with env-var, portable DPAPI file, and Credential Manager backends. Activated by `QUILL_PORTABLE=1`. Update `ai_chat_dialog.py` and `assistant_ai.py` to use it.

---

## §22. Startup Wizard — Personalise QUILL

### §22.1 Overview

The Startup Wizard is a first-run wizard that lets every user shape QUILL to their work and accessibility needs before the main frame appears. It is also re-runnable at any time via Help > Personalise QUILL. Features the user disables are completely hidden — no menus, no commands, no phantom shortcuts.

The wizard (`SetupWizardDialog` in `quill/ui/setup_wizard_pages.py`) is a single `wx.Dialog` hosting nine `wx.Panel` pages shown one at a time with Back / Next / Finish navigation. Choices are held in pending state and applied to `Settings`/`FeatureManager` atomically only when the user clicks Finish, so backing out changes nothing. Every page heading is a real control with an accessible name; focus on page change lands on the first interactive control.

### §22.2 The Nine Pages (as built)

1. **Welcome** — introductory text; no configuration.
2. **Keyboard and Sound** — keyboard pack and whether QUILL plays sounds for mode changes.
3. **Feature Profile** — choose Essential, Writer, Developer and Power Text, Accessibility Professional, or Full QUILL.
4. **Remote Access** — enable/disable the FTP / SFTP / WebDAV / S3 open and save features.
5. **AI Assistance** — enable/disable AI features (API key added later).
6. **Reading and Accessibility** — Read Aloud and the spoken-announcement verbosity (Minimal / Normal / Verbose).
7. **Writing Tools** — spell check as you type, word prediction and tag IntelliSense, and curly-quote autoformatting.
8. **Startup Behaviour** — start with no document open, check for updates on startup, and system tray icon.
9. **Summary** — review every decision; Finish applies them.

Planned wizard additions not yet present (tracked in `docs/planning.md`): an interface-language selector page, a watch-folder onboarding step, a GLOW consent step, and dedicated Quillins / Power Tools / Notebook / keyboard-profile pages.

### §22.3 Feature Gating via FeatureManager

`quill/core/feature_flags.py` defines a frozen `FeatureFlags` dataclass and `is_enabled(flag: str) -> bool`. The wizard writes a `feature_flags` block into `settings.json` via `write_json_atomic`. `MainFrame.__init__` loads flags before building menus, the command registry, and keybindings.

The two network-capable gated features are:

- `core.remote` — SSH/SFTP remote editing. When disabled, the Remote menu and all SSH commands are absent.
- `future.ai` — AI writing assistance. When disabled, Ask Quill, Prompt Library, Skill Library, grammar check, and all AI commands are absent.

Commands with `feature_tag = None` are always present (core editing). Commands whose tag is disabled are excluded from the command palette search and their keyboard bindings are not registered, so `Ctrl+?` discovery shows no ghost shortcuts.

### §22.4 First-Run Detection and Re-run

`setup_wizard_completed` in `settings.json` (type bool, default False) controls first-run detection. When the field is absent or False, `MainFrame.__init__` runs `run_setup_wizard(parent=None)` before any UI is shown, then reloads settings before building menus.

Re-run opens the wizard in update mode with all pages pre-filled. Changed flags trigger `_apply_feature_flags()`, which rebuilds the affected menu groups, refreshes the command palette, re-applies the keymap profile, and announces the change — no restart required.

### §22.5 Settings Additions

| Field | Type | Default | Description |
|---|---|---|---|
| `setup_wizard_completed` | bool | False | Suppresses wizard on next launch |
| `feature_flags_ai` | bool | True | Master switch for all AI features |
| `feature_flags_remote` | bool | True | Master switch for remote editing |
| `feature_flags_quillins` | bool | True | Master switch for Quillins |
| `feature_flags_power_tools` | bool | True | Master switch for Power Tools |
| `feature_flags_notebook` | bool | True | Master switch for Notebook workspace |
| `keymap_profile` | str | "default" | Active keyboard profile name |

### §22.6 Implementation Status

**SHIPPED.** Phases 1-3 complete: `setup_wizard.py`, `setup_wizard_pages.py`, `feature_flags.py`, `feature_registry.py`, and `check_feature_tags.py` CI gate are all in production. Phase 4 (additional keymap profiles beyond the shipped defaults) is in progress.

---

## §23. Context-Sensitive Help System

### §23.1 Overview

QUILL provides three help keystrokes that give the user immediate, contextual assistance without leaving the keyboard:

| Key | Command | Behaviour |
|---|---|---|
| F1 | Help on This Control | Shows a small dialog describing the focused control |
| Ctrl+F1 | Open User Guide | Opens docs/html/USER_GUIDE.html in the system browser |
| Shift+F1 | What Can I Do Here? | Document-type context report (enhanced) |

`F1` always returns something useful. There are three fallback levels: (1) named schema topic via `ctrl.GetName()`, (2) generic description by `ctrl.GetClassName()`, (3) control name + tooltip + prompt to open the User Guide.

### §23.2 Architecture

```
quill/core/help/topics.json          schema: topic id, title, body, keystrokes, user_guide_section
quill/core/help/renderer.py          render_live(), render_doc(), generate_markdown()
quill/ui/context_help.py             ContextHelpDialog, ContextHelpMixin, describe_focused()
quill/tools/build_docs.py            generates docs/CONTROL_REFERENCE.md from topics.json
quill/tools/check_help_coverage.py   CI gate: stale entries fail; coverage gaps warn
```

Topic IDs are derived from `ctrl.GetName()`. Dialog controls are prefixed with the dialog's accessible name: `connect_to_ssh_server.host_or_ip_address`. This works because the dialog contract already requires every interactive control to carry a meaningful `SetName()`.

`ContextHelpMixin` is added to `MainFrame`'s MRO. It tracks the last-focused control via `EVT_CHILD_FOCUS` so that navigating to `Help > Help on This Control` via the menu bar still describes the correct control.

### §23.3 ContextHelpDialog Screen-Reader Design

The dialog contains a single read-only `wx.TextCtrl` (multi-line, no border, dialog background colour) with combined title and body text, plus a Close button. Using one TextCtrl means NVDA reads the dialog title then the entire content line by line on open, without the user tabbing between controls first. Focus lands on the TextCtrl. Closing the dialog restores focus to the described control.

The dialog is registered in `dialog_inventory.json`. `affirmative_id = wx.ID_CLOSE`. Escape also closes it.

### §23.4 Topics Coverage

The schema (`quill/core/help/topics.json`) currently contains 109 topics covering:

- Main editor surface, status bar, document tabs
- All major dialogs: Find/Replace, Spell Check, AI Assistant, Remote/SSH, Preferences pages
- Startup Wizard pages (F1 on any wizard control explains the effect of each choice)
- Feature profiles, keyboard packs, read-aloud settings, GLOW workflows

Full coverage target is 250 topics (all `SetName()` calls in `quill/ui/`).

### §23.5 CI Gate

`quill/tools/check_help_coverage.py` enforces two rules:

- **Blocking:** A topic ID in `topics.json` has no matching `SetName()` call in `quill/ui/`. Stale entries describe UI that no longer exists.
- **Warning (non-blocking until `--strict`):** A `SetName()` call in `quill/ui/` has no matching topic. Coverage gap printed to stdout during the authoring sprint.

### §23.6 Implementation Status

**SHIPPED.** Phase A (infrastructure: `topics.json`, `renderer.py`, `context_help.py`, F1/Ctrl+F1/Shift+F1 wiring) complete. Phase B (schema authoring sprint, 109 of 250 topics complete) in progress. Phase D (coverage gate) complete. Phases C (documentation HTML build) and E (user guide restructure) in progress.

---

## §24. Translation and Community Localization

### §24.1 Overview

QUILL uses GNU gettext for all user-visible strings, with Babel for POT extraction and Crowdin for community translation management. The design follows the NV Access NVDA translation model, which has produced high-quality, screen-reader-tested translations across 50+ languages.

Speech announcement strings are first-class translation targets. They are marked with `#. SPEECH:` extracted comments in the POT file so translators can filter them for review and test them with a native screen reader in the target language.

### §24.2 Pipeline

```
quill/core/i18n.py          _(), ngettext(), lazy_gettext(), init_locale()
babel.cfg                   Babel extraction configuration
quill/locale/quill.pot      Master string template (auto-generated by pybabel extract)
quill/locale/{lang}/LC_MESSAGES/quill.po   Per-language translation (community, via Crowdin)
quill/locale/{lang}/LC_MESSAGES/quill.mo   Compiled binary (generated by pybabel compile)
quill/tools/check_translation.py           CI gate
```

`init_locale()` is called in `MainFrame.__init__` before any UI string. The `language` setting (BCP 47 tag, default empty = OS locale) controls the active locale. A startup-wizard language selector (shown when more than one `.mo` file is present) is planned; the shipped wizard does not yet include it.

### §24.3 Crowdin Components

Three Crowdin components manage translation content:

1. **UI strings** — source `quill/locale/quill.pot`, target `quill/locale/{lang}/LC_MESSAGES/quill.po`
2. **Context-sensitive help** — source `quill/core/help/topics.json`, target `quill/core/help/topics_{lang}.json`
3. **Quillin manifests** — source each bundled `manifest.json`, target `manifest_{lang}.json`

Auto-PR on approved translation; PRs land on `main` after the CI gate passes.

### §24.4 Four-Tier Role Model

| Role | Responsibilities |
|---|---|
| Translator | Suggests translations in Crowdin |
| Proofreader | Approves or rejects suggestions for their language |
| Language Coordinator | Manages proofreaders, owns language quality, reviews PRs |
| Translation Coordinator | Project-level; runs translation calls, onboards teams, resolves disputes |

The Translation Coordinator is a named maintainer role in `MAINTAINERS.md`.

### §24.5 Language Priority

- **Tier 1 (target: ship with QUILL 1.0):** French (fr), German (de), Spanish (es)
- **Tier 2 (close follow-on):** Portuguese/Brazilian Portuguese (pt_BR), Japanese (ja), Italian (it)
- **Tier 3 (RTL, requires layout work):** Arabic (ar), Hebrew (he)

Completeness thresholds: 90% for established languages, 70% for a language's first release. Languages below threshold are excluded from that release's language selector.

### §24.6 CI Gate

`quill/tools/check_translation.py` checks: POT currency (dry-run pybabel extract + diff), completeness threshold per language, mnemonic `&` preservation, placeholder `{n}` / `%(count)s` preservation, and no empty translated strings.

### §24.7 Implementation Status

**Phase 1 infrastructure complete:** `quill/core/i18n.py`, `babel.cfg`, `check_translation.py` gate, `language` setting, and `init_locale()` call are all in production. **Phase 2 (string marking sprint)** is in progress — sweeping all user-visible strings in `quill/ui/` and `quill/core/` to wrap them with `_()`. Pilot languages (fr, de, es) are pending community formation and a named Translation Coordinator.

---

## §25. GitHub Remote File Access

### §25.1 Overview

QUILL provides first-class GitHub repository browsing, remote file opening, and file commit-back through **File > Open from Remote > GitHub Repository...** This lets users open files from any public or private GitHub repository without requiring the GitHub CLI, GitHub Desktop, local Git, VS Code, or command-line interaction.

The implementation uses **PyGithub** behind QUILL's own `RemoteProvider` abstraction (`quill/core/github/provider.py`), which keeps the UI layer stable if the backend changes (e.g. direct REST, GitLab, Bitbucket).

### §25.2 Menu Structure

Added to the existing **File > Open from Remote** submenu:

```
File > Open from Remote
  ...FTP / SFTP / WebDAV / S3 items (existing)...
  ---
  GitHub Repository...
  GitHub File URL...
  Save to GitHub...
  ---
  Manage Remote Sites...   (existing)
  Manage GitHub Accounts...
```

All four GitHub commands are also available through the Command Palette.

### §25.3 Feature Flag

Feature ID: `core.github_remote`  
Category: `core`  
Privacy: `network after confirmation`  
Dependencies: `core.remote`  
Optional dep: `pip install "quill[github]"` (installs PyGithub >= 2.0)

When the flag is off, all four GitHub menu items are absent. When PyGithub is not installed, QUILL shows a friendly message with the install command.

### §25.4 Authentication

**First-run consent.** The first time the user opens a GitHub feature, a one-time consent dialog explains that QUILL will connect to api.github.com for the user's chosen repositories. Consent is stored in `github_consent.json` in the user data directory.

**Anonymous access.** Public repositories are browsable without a token. Rate limits are lower (60 requests/hour vs 5,000 with auth).

**Personal Access Token.** The user pastes a token with at minimum `public_repo` scope (add `repo` for private repositories). The token is stored in **Windows Credential Manager** under the target name `quill-github-token` using DPAPI. Never stored in `settings.json` or any plaintext file.

**Token management.** File > Open from Remote > Manage GitHub Accounts... lets the user view the stored identity, add/replace the token, and sign out (deletes the stored token).

### §25.5 Repository Browser

A native `wx.Dialog` with:

- **Account label** (signed-in identity or "Anonymous").
- **Repository field** (`owner/repo` text entry) + **Load** button. Enter key also triggers Load.
- **Branch/tag choice** (populated after Load; defaults to the repository's default branch).
- **Current path label** (breadcrumb).
- **File list** (`wx.ListCtrl`, single-select, columns: Name / Type / Size). Directories appear first, sorted A-Z; files follow, sorted A-Z.
- **Status label** (loading state, error messages, item count).
- **Buttons**: Open File, Go Up, Refresh, Copy URL, Cancel.

Keyboard shortcuts:
- Enter on a folder: navigates into it.
- Enter on a file: same as Open File.
- Backspace: go up one level (when not at root).
- F5: refresh.

All controls have accessible names. Long operations (repository load, directory listing, file fetch) run on daemon threads; the dialog remains interactive during loading.

### §25.6 GitHub File URL

**File > Open from Remote > GitHub File URL...** accepts a pasted `https://github.com/owner/repo/blob/branch/path` URL and opens the file directly without requiring the user to navigate the browser. Useful for sharing links.

### §25.7 Save to GitHub

**File > Open from Remote > Save to GitHub...** is available when the active document was opened from GitHub. QUILL prompts for a commit message, then commits the current document text to the same repository, branch, and path using the GitHub API (`update_file`). The file SHA is tracked for optimistic concurrency; if the file has changed remotely since it was opened, GitHub returns a 409 and QUILL shows a clear error.

Requirements: the stored token must have `repo` (write) scope on the target repository.

This command is intentionally not wired to the regular Save shortcut. The user must invoke it explicitly from the menu or Command Palette to avoid accidental commits.

### §25.8 Remote Origin Metadata

When a file is opened from GitHub, QUILL stores a `RemoteOrigin` dataclass keyed by the local temp path:

```python
RemoteOrigin(
    provider="github",
    account_id="github:login",
    repository="owner/repo",
    ref="main",
    path="docs/example.md",
    sha="abc123...",
    url="https://github.com/owner/repo/blob/main/docs/example.md",
    opened_at="2026-06-12T..."
)
```

The tab's `source_label` is set to `GitHub: owner/repo (branch)` and shown in the title bar.

### §25.9 Security Properties

- No network access until the user explicitly opens a GitHub feature and accepts the consent dialog.
- Tokens stored via DPAPI; never logged, never in diagnostic bundles.
- File size limit: 1 MB (GitHub API limit for the contents endpoint). Files exceeding this are rejected with a clear error.
- Save-back requires explicit user action and a commit message.
- No silent background syncing or polling.

### §25.10 Implementation Files

| File | Purpose |
|------|---------|
| `quill/core/github/__init__.py` | Package marker |
| `quill/core/github/models.py` | `RemoteAccount`, `RemoteRepository`, `RemoteRef`, `RemoteNode`, `RemoteFile`, `RemoteOrigin`, `BrowseResult` |
| `quill/core/github/provider.py` | Abstract `RemoteProvider` interface |
| `quill/core/github/github_provider.py` | `GitHubRemoteProvider` (PyGithub) |
| `quill/core/github/token_store.py` | Credential Manager token storage |
| `quill/core/github/consent.py` | One-time consent state |
| `quill/ui/github_dialogs.py` | Consent, sign-in, manage-accounts, repository browser dialogs |
| `quill/ui/main_frame_github.py` | `GitHubRemoteMixin` — orchestration and threading |

### §25.11 Implementation Status

**SHIPPED** (2026-06-12). All five implementation phases complete:
- Phase 1: Core service layer and models.
- Phase 2: Authentication (token + anonymous).
- Phase 3: Repository browser dialog.
- Phase 4: Remote document integration (origin metadata, title, save-back).
- Phase 5: Gate compliance (banned patterns, dialog inventory, module size budget, mypy overrides).


---

# Appendix: Engineering documentation

_Folded in from the former docs/QUILL-PRD.md on 2026-06-13._

# QUILL engineering documentation

_Consolidated from the former docs/engineering/ folder on 2026-06-13. Each section preserves the original document in full._


---

<!-- Source: docs/engineering/thread-safety.md -->

# Thread-safety invariants

This note documents the concurrency invariants for Quill's module-level and
shared caches (CQ-17). It is the canonical reference for how the lazily-loaded
caches stay correct when several threads touch them at once — the writing thread,
the file-I/O and compute pools, and watch-folder worker threads.

## Concurrency model recap

- The UI thread owns the wxPython widgets and the editor buffer.
- File I/O and heavier compute run on worker threads / thread pools.
- Cross-thread UI updates marshal back through `wx.CallAfter` / `wx.CallLater`.

Because a lazily-loaded cache can be touched from more than one of these threads
on first use, each such cache is guarded by a lock. There are no unguarded
module-level mutable caches in `quill/core`.

## Pattern 1 — module-level lazy caches (double-checked locking)

Read-mostly data that is expensive to build once and then never changes uses a
module-level `threading.Lock` plus double-checked locking: an unlocked fast-path
read of the cached value, then the lock, a re-check, and population under the
lock. The cached value is always an immutable snapshot (a `frozenset`, or a dict
that is never mutated after publication), so readers that win the fast path never
observe a half-built structure.

| Cache | Module | Lock | Cached state |
| --- | --- | --- | --- |
| Word-list fallback | [quill/core/spellcheck.py](../../quill/core/spellcheck.py) | `_BACKEND_LOCK` | `_WORDLIST_CACHE` (`frozenset`) |
| Enchant dictionary handle | [quill/core/spellcheck.py](../../quill/core/spellcheck.py) | `_BACKEND_LOCK` | `_ENCHANT_DICT`, `_ENCHANT_TRIED` |
| Thesaurus index | [quill/core/thesaurus.py](../../quill/core/thesaurus.py) | `_LOAD_LOCK` | `_INDEX` (dict, never mutated after build), `_LOAD_ERROR` |

Invariants for this pattern:

1. The cache slot is only ever written while holding the lock.
2. Once published, the cached object is treated as immutable. To refresh it,
   replace the whole slot under the lock; never mutate in place.
3. The fast-path read outside the lock is safe because it reads a single
   reference that is either `None` (not yet built) or a fully-built snapshot.
4. A failed load still publishes a definitive result (an empty cache plus an
   error string) so the expensive attempt is not retried on every call.

## Pattern 2 — per-instance mutable-set caches

Caches that are genuinely mutated over time hold a per-instance
`threading.Lock` and take it around every read and write of the shared mutable
state.

| Cache | Module | Lock | Shared state |
| --- | --- | --- | --- |
| Watch-folder seen-set | [quill/core/watch_folder.py](../../quill/core/watch_folder.py) | `self._lock` | `self._seen_files` (`set[str]`) |

Invariants for this pattern:

1. Every access to the mutable set — `clear`, membership test, and `add` — is
   performed inside `with self._lock`.
2. The lock is held only for the brief set operation, never across slow work
   such as file I/O or dispatching an action, so worker threads do not serialise
   behind each other.

## Stability helpers

The stability layer follows the same per-instance discipline: the task manager
([quill/stability/task_manager.py](../../quill/stability/task_manager.py)), the
wx dispatch queue ([quill/stability/wx_dispatch.py](../../quill/stability/wx_dispatch.py)),
and the heartbeat ([quill/stability/wx_heartbeat.py](../../quill/stability/wx_heartbeat.py))
each own a `threading.Lock` and take it around their shared bookkeeping.

## Rule for new caches

Any new module-level or shared cache must adopt one of the two patterns above:
a double-checked `Lock` with an immutable published snapshot for read-mostly
data, or a per-instance `Lock` taken around every access for mutable state. Do
not add an unguarded module-level mutable cache to `quill/core`.


---

<!-- Source: docs/engineering/docs-artifacts-pipeline.md -->

# Docs-artifact regeneration pipeline

This note documents how Quill keeps each `docs/**/*.md` source in sync with its
rendered `.html` and `.epub` artifacts, and how the GitHub Actions workflows that
enforce and automate that stay correct. It is the canonical reference for the
[Docs artifacts](../../.github/workflows/docs-artifacts.yml) workflow, the
docs-parity guard ([scripts/check_docs_artifacts.py](../../scripts/check_docs_artifacts.py)),
and the `workflow-lint` gate in [PR CI](../../.github/workflows/pr-ci.yml).

## What the pipeline guarantees

Every Markdown file under `docs/` ships alongside a matching HTML and EPUB build,
so readers who consume the published artifacts never see a stale rendering of a
source that has since changed. Two mechanisms cooperate:

- A **parity guard** that fails CI when an edited `docs/**/*.md` is missing an
  updated `.html` or `.epub` sibling in the same change.
- An **auto-regeneration workflow** that rebuilds artifacts for changed sources
  and, on a same-repo pull request, pushes them back to the PR branch so the
  author does not have to install Pandoc.

## The parity guard

[scripts/check_docs_artifacts.py](../../scripts/check_docs_artifacts.py) diffs a
base and head ref, and for every changed `docs/**/*.md` source that still exists,
requires that both its `.html` and `.epub` siblings also changed in that range.
It recurses into subdirectories (`docs/planning`, `docs/qa`, ...), not just the
top level. The guard runs as the "Verify docs artifacts are regenerated" step in
[Accessibility CI](../../.github/workflows/accessibility-ci.yml) and is a
required check.

## The auto-regeneration workflow

[Docs artifacts](../../.github/workflows/docs-artifacts.yml) triggers only when a
`docs/**.md` source changes. It has two design constraints that drove its
current shape, both learned from real failures.

### Constraint 1 — EPUB output is non-deterministic

Pandoc embeds a fresh UUID and build timestamp in every EPUB, so regenerating an
unchanged source produces different bytes each run. HTML output, by contrast, is
deterministic. A naive "regenerate everything and commit the diff" approach
therefore reports false staleness on every run and fails forever.

The workflow handles this by:

1. Scoping regeneration to only the Markdown that changed in the push/PR range
   (mirroring the parity guard), not the whole tree.
2. Always rebuilding the **deterministic HTML**, but generating an EPUB **only
   when it is missing** — never rewriting an existing one, so the random-UUID
   churn cannot manifest.
3. Basing the "is this stale?" decision on deterministic HTML drift plus
   genuinely untracked new files, never on EPUB byte differences.

### Constraint 2 — `main` is a protected branch

The workflow cannot push regenerated artifacts to `main`: branch protection
requires changes to arrive through a pull request, so a direct push is rejected
(`GH006: Protected branch update failed`). Attempting it was the original chronic
failure. The reconcile step now branches on context:

- **Same-repo pull request:** commit the regenerated artifacts and push them back
  to the PR's source branch, so the eventual merge into `main` is already in sync.
- **Push to `main`, or a fork PR:** do not attempt a push. Fail loudly with the
  exact diff and a "regenerate locally" message, so a human regenerates the
  artifacts and brings them in through a pull request.

### Regenerating locally

When the workflow or the parity guard reports a stale artifact, regenerate it
with the same Pandoc invocations CI uses:

```bash
pandoc <source>.md -f gfm -t html5 -s -o <source>.html
pandoc <source>.md -f gfm -t epub3      -o <source>.epub
```

Commit both artifacts with the source (through a pull request for `main`).

## Workflow linting (`workflow-lint`)

The `workflow-lint` job in [PR CI](../../.github/workflows/pr-ci.yml) runs
[actionlint](https://github.com/rhysd/actionlint) (pinned to a specific image)
over every workflow on each push and pull request. It statically validates YAML
structure, action input contracts, and shell-safety patterns.

This gate exists because a real script-injection vector slipped into the docs
workflow: an untrusted `${{ github.head_ref }}` was interpolated directly into an
inline `git push` script, where a crafted branch name could execute arbitrary
shell. The fix — and the rule the gate now enforces automatically — is to pass
workflow context through the step `env:` block and reference it as a shell
variable, never to expand untrusted `${{ github.* }}` values inline.

## Verifying the workflow logic

Because the reconcile logic is shell rather than Python, it is validated two ways:

1. **Static analysis** with actionlint, now wired into CI as `workflow-lint`.
2. **Behavioral simulation** against a throwaway git repository with a bare remote
   whose `pre-receive` hook rejects writes to `main` (simulating branch
   protection) and a mock `pandoc` that mirrors the measured behavior
   (deterministic HTML, random-bytes EPUB). The simulation exercises the
   in-sync, fail-loud, recursive-subdirectory, missing-EPUB, no-churn, and
   PR-push-back paths.

When changing the reconcile logic, re-run actionlint locally and re-run the
behavioral simulation before relying on CI.


---

<!-- Source: docs/engineering/macos-build.md -->

# Building Quill for macOS

The macOS build reuses the cross-platform wxPython core plus the
`quill/platform/macos/` adapters. See issue #42 for the full plan.

## Prerequisites

- macOS 12+ (Apple Silicon or Intel), Python 3.11+
- `pip install -e ".[ui,macos]"` (wxPython, pyttsx3, pyobjc, py2app)
- For distribution: an Apple **Developer ID Application** certificate and a
  `notarytool` keychain profile (`xcrun notarytool store-credentials`).

## Build

```bash
python scripts/setup_macos.py py2app   # -> dist/Quill.app
```

## Sign, notarize, package

```bash
export IDENTITY="Developer ID Application: Your Name (TEAMID)"
export NOTARY_PROFILE="quill-notary"
./scripts/build_macos.sh              # -> dist/Quill.dmg (signed, notarized, stapled)
```

## Platform adapters (macOS)

- App entry point: `quill/platform/macos/macos_app.py` (py2app bundle main)
- Screen reader detect: `quill/platform/macos/sr_detect.py` (VoiceOver)
- Increase Contrast: `quill/platform/macos/high_contrast.py`
- Secrets: `quill/platform/macos/keychain.py` (Keychain, replaces DPAPI)
- Announcements: `quill/platform/macos/announce.py` (VoiceOver via NSAccessibility; needs pyobjc)
- File types: `quill/platform/macos/shell_integration.py` (CFBundleDocumentTypes)
- OS dispatch: `quill/platform/dispatch.py`

## Remaining integration (tracked in #42)

- Route the app's announce handler to `macos.announce.announce` on macOS (ties to #29).
- Migrate secret/high-contrast/screen-reader call sites to `quill.platform.dispatch`.
- Verify the app launches under VoiceOver; keyboard-only QA.


---

<!-- Source: docs/engineering/security-advisory-workflow.md -->

# Security Advisory Workflow

This runbook defines how QUILL handles private vulnerability coordination.

## Intake

1. Receive report through `SECURITY.md` private channel.
2. Acknowledge receipt and open a private advisory in GitHub Security Advisories.
3. Classify severity and affected versions.

## Triage

1. Reproduce issue in a controlled environment.
2. Assess exploitability, user impact, and affected surfaces.
3. Record mitigation options and patch strategy.

## Patch and validation

1. Implement fix on a private branch when needed.
2. Validate with standard checks:
   - `ruff check .`
   - `pytest -q`
3. Add regression tests where appropriate.

## Disclosure

1. Coordinate disclosure date with reporter when possible.
2. Publish patched release and advisory details.
3. Include clear upgrade/mitigation guidance for users.

## Post-incident actions

1. Add follow-up hardening tasks.
2. Update security checks/process docs if gaps were found.


---

<!-- Source: docs/engineering/dialog-estate-report.md -->

# QUILL Dialog Estate Report (DLG-3)

_Last updated: 2026-06-04_

This report is the human-readable companion to the machine-enforced dialog
governance described in **PRD §9.13 (Dialog estate governance)** and tracked in
`docs/planning/ROADMAP.md` as DLG-3.0 through DLG-3.8. It records where the dialog-unification
work stands after the triage and Phase 3 hardening pass.

## Headline

- **154** dialog surfaces inventoried across `quill/**/*.py`.
- Classification: **100 native**, **49 hardened_custom**, **5 web**.
- Triage of all 49 `hardened_custom` surfaces: **0 convert / 48 harden / 1 keep-web**.
- **All 49** `hardened_custom` dialogs now wire the shared `dialog_contract`
  (`apply_modal_ids` + an accessible show path), enforced by a new AST guard.

## How the estate is governed

| Mechanism | File | Role |
| --- | --- | --- |
| Source-generated inventory | `quill/tools/dialog_inventory.py` | AST-scans every `wx.Dialog(...)`, stock wx dialog, and `show_web_form(...)`; assigns a stable key `<module>::<enclosing_qualname>::<kind>` and a sanctioned classification. |
| Committed snapshot | `tests/unit/ui/fixtures/dialog_inventory.json` | The source of truth; CI fails if the live scan disagrees. |
| Inventory gate | `tests/unit/ui/test_dialog_inventory.py` | Fails on any new, moved, removed, or reclassified surface. |
| Banned-pattern gate | `quill/tools/check_banned_patterns.py` | Cross-checks every surface against the snapshot; fails on unregistered/misclassified dialogs (Security CI). |
| Shared contract helpers | `quill/ui/dialog_contract.py` | `apply_modal_ids(...)` (affirmative/escape IDs) and `show_modal_dialog(...)` (region + announcement hooks). |
| **Hardening guard (new)** | `tests/unit/ui/test_dialog_hardening_contract.py` | AST-asserts every `hardened_custom` surface wires `apply_modal_ids` + an accessible show/`ShowModal`/`Show` path. Blocks future drift at author time. |

## Triage outcome

A live audit on the Windows wx 4.2.5 (Phoenix, wxWidgets 3.2.9) runtime, plus a
source scan for custom-drawn paint code
(`EVT_PAINT` / `wx.lib.agw` / `OnPaint` / `wx.PaintDC` / owner-draw / `wx.html2`),
returned **zero** custom-drawn dialogs. Every `hardened_custom` surface is already
a stock-widget `wx.Dialog` container (ListBox, TextCtrl, SearchCtrl, TreeCtrl,
multi-action button rows). "Convert to native" is therefore, in the literal wx
sense, already true — the genuine work is **contract hardening**, not rewrites.

| Bucket | Count | Meaning |
| --- | --- | --- |
| Convert (flatten to a stock one-shot) | **0** | No dialog is a lossless single confirm/choice/text entry; flattening any would drop live search, lists, previews, or multi-action rows. |
| Harden (enhanced-native onto one contract) | **48** | Genuinely multi-control native dialogs that converge on one focus/default/lifecycle grammar via `dialog_contract`. |
| Keep web | **1** | `AskQuillChatDialog` (rich streaming chat surface) stays on the sanctioned web surface. |

## Phase status

| Phase | Item | Status | Notes |
| --- | --- | --- | --- |
| 0 | Source-generated registry + gates | **Done** | Inventory engine + snapshot + two gates shipped. |
| 1 | Strengthened A11Y-4 dialog-contract guard | **Done** | `_check_dialog_registry` + Dialog Excellence Mandates. |
| T | Triage all 49 `hardened_custom` dialogs | **Done** | 0 convert / 48 harden / 1 keep-web. |
| 2 | Native conversion wave (flatten to one-shot) | **Done (no applicable work)** | Triage found zero lossless conversion candidates; honest no-op. |
| 3 | Enhanced-native contract standardization | **Done** | All 49 wire the shared contract; new AST guard prevents drift. |
| 4 | Web-surface standardization | **Todo** | Confirm the 5 web surfaces have native-fallback parity and no raw HTML in onboarding tabs. |
| 5 | Startup/onboarding hardening | **Todo** | Deterministic focus across chained startup modals; consent preserved. |
| 6 | Assistant/AI dialog consolidation (folds DLG-2) | **Todo** | `assistant_tools.py`/`ai_model_panel.py`/`style_panel.py`/`assistant_panel.py` async/"busy" semantics. |
| 7 | CQ-16 characterization around dialog-launch paths | **Todo** | Return-value/side-effect regression tests before any CQ-1 split. |
| 8 | Manual NVDA/JAWS/Narrator SR pass | **Todo** | Requires a live Windows screen-reader runtime; cannot be machine-verified. |

## Phase 3 — what changed

A machine-derived AST audit of every `hardened_custom` scope found **5** surfaces
that did not fully wire the shared contract. Four were brought onto it; the fifth
was already correct.

| Dialog | Module | Action |
| --- | --- | --- |
| `_present_quill_key_help` | `quill/ui/main_frame.py` | Added `apply_modal_ids(ID_OK, ID_OK)`; routed direct `ShowModal()` through `_show_modal_dialog` (adds region/announce hooks). |
| `_offer_crash_recovery` | `quill/ui/main_frame.py` | Added `apply_modal_ids(ID_YES, ID_NO)` alongside existing `SetDefaultItem`/`SetEscapeId`. |
| `_present_quick_nav` | `quill/ui/main_frame.py` | Added `apply_modal_ids(ID_OK, ID_CANCEL)`; routed direct `ShowModal()` through `_show_modal_dialog`. |
| `_choose_searchable_option` | `quill/ui/main_frame.py` | Added `apply_modal_ids(ID_OK, ID_CANCEL)` + deterministic `search.SetFocus()`. |
| `show_watch_folder_status` | `quill/ui/main_frame.py` | No change — correctly-hardened **modeless** monitor (`Show()` + `EVT_CLOSE` → `Destroy`); the contract audit's "missing show" was a false positive for modeless windows. |

No dialog was flattened; live search, lists, and preview panes are preserved.

## Tests and validation

- `tests/unit/ui/test_dialog_hardening_contract.py` — new durable guard (2 tests).
- `tests/unit/ui/test_dialog_contract.py`, `test_dialog_inventory.py` — green.
- `tests/unit/ui/test_main_frame_navigation.py`, `test_main_frame_quill_key.py`,
  `test_main_frame_share_dialogs.py` — 113 passed (exercise the edited methods).
- `ruff format` + `ruff check` — clean.
- Banned-pattern gate — no violations.
- Dialog inventory — unchanged at 154 surfaces (100/49/5); no reclassification.

## Honest remaining work

- **Phases 4–7** are real engineering still to do (web parity, startup focus
  chains, assistant/AI async semantics, CQ-16 characterization).
- **Phase 8** is a manual NVDA/JAWS/Narrator pass that **cannot** be
  machine-verified; it needs a human tester on a live Windows screen-reader
  runtime, with each `dialogs.md` row carrying pass/fail evidence.


---

<!-- Source: docs/engineering/installer-evaluation.md -->

# Windows installer evaluation and rethink

This document evaluates the QUILL Windows installer (Inno Setup), grounded in
what QUILL actually ships, and records the changes made plus a forward-looking
vision. The `.iss` is generated by `build_inno_setup_script()` in
`scripts/build_windows_distribution.py`; edit the generator, never the emitted
`installer/quill.iss` (a test enforces they stay in sync).

## What QUILL actually installs

From `scripts/build_windows_distribution.py` and the portable bundle layout:

- A private embedded Python runtime (`python/`, amd64, pinned 3.12.x) with
  wxPython, pyttsx3, and the other runtime wheels preinstalled, plus the
  vendored `quill-glow-core` contract wheel. End users install no Python.
- The `quill` package source, the `run-quill.cmd` launcher, `manifest.json`,
  `README.txt`.
- Docs: `docs/userguide.html` and `docs/userguide.md` (PRD and engineering docs
  are published to GitHub Pages instead of bundled).
- Optional tools under `tools/`, included only when the build was run with the
  matching `--*-dir` / `--bundle-*` flag:
  - `tools/pandoc` (document conversion)
  - `tools/speech/{dectalk,espeak-ng,kokoro,piper,openvoice}` (Read Aloud
    engines; DECtalk further split into per-voice subfolders)
  - `tools/nodejs` (portable Node for Node Quillins and the QDC TypeScript
    console)

The installer mirrors this with opt-in [Components] and `skipifsourcedoesntexist`
so a build that omits a tool still produces a valid installer.

## What the installer already does well

- Per-user by default (`PrivilegesRequired=lowest`) with an elevation override
  dialog, so a standard user can install without an admin prompt.
- Non-destructive file associations: registers only under `OpenWithList` and
  `SystemFileAssociations` (HKCU), never seizing a user's chosen default app.
- Send-to-Quill right-click verbs (OCR, Open, Read aloud) generated from the
  single `quill.core.shell_verbs` registry, so the installer, the runtime
  registry writer, the CLI `--action` map, and the Settings toggles cannot
  drift. All opt-in and `uninsdeletekey`-clean.
- Screen-reader-accessible decisions made through native `MsgBox`/`Exec`
  dialogs rather than custom wizard pages.
- Honest uninstall: prompts (defaulting to No) before removing the user's
  `%APPDATA%\Quill` data, instead of silently keeping or wiping it.
- `CloseApplications=force` to avoid in-use-binary upgrade failures.
- Optional Node bootstrap via winget when the Node component is selected but no
  portable Node was bundled, with a graceful failure message.
- Solid LZMA2 compression.

## Gaps found

1. No architecture directives. The bundle is amd64, but the script never set
   `ArchitecturesAllowed` / `ArchitecturesInstallIn64BitMode`, so on a 64-bit OS
   it installed into the 32-bit `Program Files (x86)` and would even attempt to
   run on a 32-bit Windows it can never support.
2. No minimum OS. The zero-install OCR backend (`Windows.Media.Ocr`), the winget
   Node bootstrap, and modern wxPython all require Windows 10+, but the installer
   would run on Windows 7/8.1 and then fail at runtime.
3. No association-cache refresh. The fileassoc/shellverbs tasks write Explorer
   keys, but `ChangesAssociations` was not set, so Explorer would not refresh
   icons/Open-With menus until the next shell restart.
4. A dead component. `aiassistant` ("Install the Writing Assistant setup
   guide and AI connection shortcut") gated no `[Files]` payload at all -- it
   installed nothing. Showing it implies a choice that does not exist.
5. Add/Remove Programs icon. `UninstallDisplayIcon` pointed at `run-quill.cmd`,
   which has no icon, so ARP showed a blank/generic glyph.

## Changes made in this pass

All in `build_inno_setup_script()` (and `installer/quill.iss` regenerated, test
updated):

- Added `ArchitecturesAllowed=x64compatible` and
  `ArchitecturesInstallIn64BitMode=x64compatible` (covers x64 and ARM64-via-
  emulation; requires Inno Setup 6.3+).
- Added `MinVersion=10.0` to require Windows 10/11.
- Added `ChangesAssociations=yes` so Explorer refreshes after the assoc tasks.
- Removed the dead `aiassistant` component; documented that the Writing
  Assistant ships with the core bundle.
- Pointed `UninstallDisplayIcon` at `{app}\python\pythonw.exe` (a file that
  carries a real icon), falling back gracefully when no bundled runtime exists.

These are correctness and honesty fixes that do not change the bundle contents
or the opt-in model.

## Forward-looking vision (not yet implemented)

Deliberately deferred because each needs an asset, a signing identity, or a
product decision:

- Branded icon. Ship a real `quill.ico`, wire `SetupIconFile`, give every
  shortcut an `IconFilename`, and use it for ARP. Today there is no `.ico` in
  the repo, so this is blocked on an art asset.
- Code signing. Sign `Quill-Setup-<version>.exe` (and ideally the launcher) so
  SmartScreen and AT users see a verified publisher. This is a release-pipeline
  and certificate decision, configured at `ISCC` compile time, not in the
  script body.
- In-installer voice acquisition. Today bundled speech engines must be present
  at build time. A "download recommended Read Aloud voice now?" post-install
  step (mirroring the winget Node flow, with explicit consent and a checksum)
  would let a lean installer fetch Piper/Kokoro on demand.
- Update channel. The app already vendors an autoupdate library; the installer
  could register an update feed URL and an `AppMutex` so in-app updates close
  the running instance cleanly. Needs the app to expose a known mutex name.
- Repair / modify entry. Expose component add/remove without a full reinstall.
- Optional first-run accessibility prep: offer to launch QUILL straight into the
  "Personalise QUILL" wizard with the user's detected screen reader.

## Build and verify

```powershell
# Regenerate the committed installer script after editing the generator:
python -c "from scripts.build_windows_distribution import build_inno_setup_script; from pathlib import Path; Path('installer/quill.iss').write_text(build_inno_setup_script('0.5.0'), encoding='utf-8')"

# Full distribution build (bundled Python + optional tools), then compile:
python scripts/build_windows_distribution.py --bundle-python --compile-installer

# Guard tests:
python -m pytest tests/unit/scripts/test_build_windows_distribution.py -q
```


---

<!-- Source: docs/engineering/blocked-items-completion-guide.md -->

# Blocked-items completion guide — the exact path to Done on the environment-gated 1.0 features

Status as of 2026-06-03. A small set of QUILL 1.0 items are honestly "In progress"
or "Todo" in `docs/planning/ROADMAP.md` because they are genuinely blocked on something that cannot
be produced or verified from a non-live development environment: there is no live AI
provider endpoint and no Windows 11 packaged-install cycle available here. None is
faked Done.

This document is the precise, file-by-file runbook for what a maintainer (on a real
Windows 11 machine with live provider credentials) must do to drive each remaining
item to verified Done. Nothing here is hand-waving: every step names the file,
function, and acceptance test. It is the operational companion to the `docs/planning/ROADMAP.md`
tracker — the tracker records *what* remains; this guide records *exactly how* to
finish it.

> This guide was previously the working file `zfix2.md`. It is preserved here under
> a descriptive name so the completion steps survive scratch-file cleanup.

---

## Summary table

| ID | Title | State now | What's already built & tested | What only you can finish | Effort |
| --- | --- | --- | --- | --- | --- |
| AI-19 | Accessible subscription sign-in (OAuth device flow) | In progress | The full RFC 8628 device-flow state machine (`device_login.py`), fully unit-tested with an injected poster | Real HTTPS poster, consent dialog, DPAPI token storage, AIBackend wiring, live end-to-end run | M |
| SHELL-2 | Structured-Markdown OCR verb (AI pass) | In progress | The assistant `structure` operation + `_apply_ocr_structuring` worker wiring, unit + contract tested | One live-key run to verify quality/threading on real OCR output; quality tuning | S |
| SHELL-3 | Windows 11 modern context menu (IExplorerCommand) | Todo | The classic Explorer verb path (SHELL-1) ships and is verifiable | A compiled `IExplorerCommand` COM handler + sparse MSIX package + installer registration + real install/uninstall verification | M–L |

When all three reach Done, **Tier 2 is golden (60/60)** and the QUILL 1.0 subtotal
drops by three remaining.

---

## AI-19 — Accessible subscription sign-in (no pasted API key)

### What already exists (do not rebuild)

- `quill/core/ai/device_login.py` — a complete, wx-free, strict-typed OAuth 2.0
  Device Authorization Grant (RFC 8628) state machine. Public API:
  - `DeviceFlowConfig`, `DeviceCodeGrant`, `PollResult` (frozen dataclasses).
  - `request_device_code(config, *, poster)` — starts the flow.
  - `poll_once(config, grant, *, poster)` — classifies one poll into
    pending / slow_down / authorized / denied / expired / error.
  - `run_device_login(...)` — drives the full polling loop honoring `interval`,
    backing off on `slow_down`, stopping at `expires_in`.
  - `announce_device_code(grant)` — the screen-reader instruction string.
  - `describe_login_result(result)` — the spoken outcome.
  - Every network exchange is an **injected** `poster`, so the engine is already
    tested without a live endpoint (7 tests) and adds no new egress site.
- `quill/platform/windows/credential_manager.py` — DPAPI-backed Windows Credential
  Manager storage already exists:
  - `credential_manager_available()`, `load_generic_credential(target_name)`,
    `save_generic_credential(...)`, `delete_generic_credential(target_name)`,
    `StoredCredential`.
- `quill/core/assistant_ai.py` — `AssistantConnectionSettings` (the saved provider
  connection, including `api_key`), `load_assistant_connection_settings()`, and
  `_build_auth_headers(provider, host, api_key)` is where the credential is
  consumed for outbound requests.

### Exact remaining work (Windows + live provider only)

1. **Real HTTPS poster.** Add a `urlopen`-based poster (TLS-verified) that satisfies
   the `Poster` protocol in `device_login.py`. Put it in a new
   `quill/platform/windows/` or `quill/core/ai/` module (keep `device_login.py`
   itself poster-free so the GATE-9 egress inventory stays explicit — register the
   new `urlopen` site in the egress audit).
   - Acceptance: a unit test that the poster issues a POST with the correct
     `application/x-www-form-urlencoded` body and parses a JSON reply; TLS
     verification is on (no `ssl._create_unverified_context`).

2. **Consent / progress dialog `DeviceLoginDialog`** in `quill/ui/`.
   - Shows: the device code, the verification URL, and the expiry; an
     "Open in browser" button; an "I've authorized — continue" button; a Cancel
     path. Must follow the A11Y-4 dialog contract (outer sizer, default button,
     `Destroy` on close, focus return to editor).
   - Speaks `announce_device_code(grant)` on open and `describe_login_result(...)`
     on completion.
   - Acceptance: a source-contract test (the cloud-safe bar) asserting the dialog
     uses `show_modal_dialog`, shows code/URL/expiry, and wires the three buttons;
     add a row to `dialogs.md` with the menu path that opens it.

3. **DPAPI token storage.** On `authorized`, persist the returned token via
   `save_generic_credential(target_name="Quill/<provider>/oauth", ...)`. Never log
   the token; never write it to the JSON connection file in plaintext.
   - Acceptance: round-trip test through the credential manager (save → load →
     delete) under a `target_name` namespaced per provider.

4. **AIBackend wiring.** Teach `assistant_ai.py` / the provider backend to resolve
   credentials as: device-login token (if present in DPAPI) → else pasted
   `api_key`. The provider must then send the device-login token in
   `_build_auth_headers`.
   - Acceptance: a unit test that, given a stored device-login token and an empty
     pasted key, the auth header carries the token; given both, the device-login
     token wins (or whatever precedence you choose — document it).

5. **Surface the entry point.** Add a "Sign in with your <provider> account" button
   to the AI provider configuration surface (the assistant setup) that launches the
   flow. Gate behind `FeatureManager` like every other AI surface.

6. **Live end-to-end verification** (the actual blocker). On a real Windows machine
   with a provider that genuinely offers an OAuth **device authorization grant** for
   API access:
   - Start the flow → QUILL shows the code + URL → you authorize in the browser →
     QUILL polls and retrieves the token → the token is used for subsequent AI
     requests → **no pasted key required**.
   - Confirm the whole flow is keyboard- and screen-reader-accessible at every step
     (NVDA/JAWS/Narrator parity).
   - **Reality check:** confirm your target provider actually exposes a public
     device-authorization endpoint for API tokens. Several major API providers do
     **not** (they issue API keys from a dashboard instead). If yours doesn't, AI-19
     cannot be honestly closed against that provider — pick one that does (or keep
     the engine ready and mark AI-19 Done only once one real provider validates it).

### Done definition for AI-19

A blind user signs in with an existing subscription via the device flow, with no
visible 51-character secret, the token is stored in DPAPI, and at least one real
provider serves AI responses using that token — all keyboard/screen-reader
accessible and registered in the GATE-9 egress audit.

---

## SHELL-2 — Structured-Markdown OCR verb (AI structuring pass)

### What already exists (built and tested this session)

- `quill/core/ai/assistant.py` — new `structure` operation in `_OPERATION_PROMPTS`:
  reflows raw OCR text into clean Markdown (joins scan-broken lines, groups
  paragraphs, infers headings/lists/tables) and **forbids** summarizing, adding, or
  inventing content. Reuses the existing chunking, `_wrap`, and backend, so large
  scans are handled. Unit-tested in `tests/unit/core/ai/test_structure_operation.py`
  (registration, OCR text reaches the model, the no-summarize instruction).
- `quill/ui/main_frame_image.py` — `_run_ocr_on_path(..., structured: bool = False)`
  and a new `_apply_ocr_structuring(...)` helper that, **inside the existing OCR
  worker thread** (off the UI thread, sharing the progress dialog), structures the
  recognized text via the assistant when one is available and reports available, and
  otherwise degrades safely to plain OCR with a status note saying why. The review
  dialog title and the insert status line reflect whether the structured pass ran.
- `quill/ui/main_frame.py` — `_handle_shell_request` passes
  `structured=action == "ocr-structured"`.
- Source-contract tests in `tests/unit/ui/test_ocr_review_dialog.py` assert the
  worker wiring and the structured-verb dispatch.

### Exact remaining work (needs a live AI key)

1. **One live run.** On Windows with a configured, available assistant backend:
   right-click an image/PDF → "OCR with Quill (structured Markdown)". Confirm the
   recognized text comes back as structured Markdown (headings/lists/paragraphs),
   inserted into the editor, with the "Structured OCR text inserted" status.
2. **Quality tuning.** Inspect the output on harder inputs — multi-column PDFs,
   tables, headers/footers, page numbers. If the model summarizes or drops content,
   tighten the `structure` prompt in `_OPERATION_PROMPTS` (it is the single source
   of truth) and re-run. No code path changes needed — only the prompt string.
3. **Threading/latency check.** Confirm the off-thread `assistant.transform(...)`
   call is thread-safe with your backend and that the progress dialog stays
   responsive (the worker already runs off the UI thread; verify no backend
   requires UI-thread affinity). If a backend needs main-thread marshaling, route
   the structuring call through `wx.CallAfter`-bounded handoff instead.

### Done definition for SHELL-2

The structured verb produces faithful structured Markdown from real OCR output on a
live backend, with no content loss, responsive UI, and accessible status
announcements. Then flip SHELL-2 to Done in `ROADMAP.md` (tracker + both living
lists + a dated activity-log entry) and regenerate `docs/planning/ROADMAP.html` and
`docs/planning/ROADMAP.epub`.

---

## SHELL-3 — Windows 11 modern context menu (IExplorerCommand) + installer

### What already exists

- `quill/platform/windows/shell_integration.py` — the **classic** (pre-Win11)
  `HKCU\Software\Classes\SystemFileAssociations\<ext>\shell\Quill.<verb>` verb path
  ships in SHELL-1 and is buildable and verifiable locally. On Windows 11 these
  verbs appear under "Show more options" (the legacy menu).

### Why this can't be finished from here

The Windows 11 **primary** context menu (the non-"Show more options" menu) only
shows verbs provided by a registered `IExplorerCommand` COM handler packaged in a
sparse/MSIX package. That requires a compiled in-proc COM component and a real
package install — none of which a pure-Python repo can produce or verify in this
environment.

### Exact remaining work (real Windows 11 + packaging toolchain)

1. **Build the `IExplorerCommand` handler.** A compiled in-proc COM server (C++/WinRT
   or Rust, or a packaged .NET COM component) that implements `IExplorerCommand`
   (and `IExplorerCommandState` / `IEnumExplorerCommand` for the submenu). It must
   surface the **same** verbs as the core registry — drive its labels/actions from
   `quill/core/shell_verbs.py` (`default_shell_verbs()`, `verb_for_action`,
   `verbs_for_extension`) so there is exactly one source of truth. Each invoked verb
   launches `quill --action <verb> "<path>"` (reuse `verb_launcher_command(action)`
   from `shell_integration.py`).
   - Submenu shape: a top "Send to Quill" flyout enumerating Open / OCR / OCR
     structured Markdown / Read aloud, filtered by file extension via
     `verbs_for_extension`.

2. **Sparse package + registration.** Author a sparse MSIX package manifest that
   declares the `IExplorerCommand` handler under the relevant
   `windows.fileTypeAssociation` / `desktop4:FileExplorerContextMenus` extension, and
   register/unregister it on install/uninstall.

3. **Installer wiring.** Wire the package register/unregister into the QUILL
   installer (`installer/quill.iss` and/or `scripts/build_windows_distribution.py`)
   so a normal install adds the modern menu and uninstall removes it cleanly. Keep
   the classic-menu fallback for non-packaged/portable installs.

4. **Live install/uninstall verification.** On Windows 11: install → confirm the
   verbs appear in the **primary** right-click menu (not just "Show more options")
   for the correct file types → run each verb → confirm uninstall removes them with
   no orphaned registry/package state. Confirm keyboard and Narrator accessibility of
   the menu entries.

### Done definition for SHELL-3

QUILL's "Send to Quill" verbs appear in the Windows 11 primary context menu via a
registered `IExplorerCommand`, driven by the same `shell_verbs.py` registry,
installed and removed cleanly by the installer, and verified on a real Win11 box.
Then flip SHELL-3 to Done in `docs/planning/ROADMAP.md` and regenerate
`docs/planning/ROADMAP.html` and `docs/planning/ROADMAP.epub`.

---

## Per-change discipline reminder (applies to all three)

- Format then lint only the **specific** changed files: `ruff format <files>`,
  `ruff check <files>`. Do not run whole-tree format (it reflows unrelated drift).
- Strict `mypy` on any changed `quill/core` / `quill/io` file — must report
  "Success: no issues found"; those layers stay wx-free.
- Add at least one behavior test (or source-contract test where wx can't load) per
  change; keep the targeted `pytest` green.
- After editing `docs/planning/ROADMAP.md`: update the **tracker totals**, **both living lists**,
  and add a **dated activity-log entry**, then regenerate the artifacts with
  `pandoc -s docs/planning/ROADMAP.md -o docs/planning/ROADMAP.html` and
  `pandoc -s docs/planning/ROADMAP.md -o docs/planning/ROADMAP.epub`, committing all three together.
- New user-facing dialog (e.g. `DeviceLoginDialog`) → add a row to `dialogs.md`.
- New public `MainFrame` method → regenerate the surface fixture with
  `python -m quill.tools.ui_surface --write`.
- Stage **specific files only**. Never `git add -A`.

---

## Appendix A (merged from former zfix4) — SHELL-3 live verification & issue status

This appendix preserves the full SHELL-3 live-verification checklist and intake issue
status that previously lived in `zfix4.md`.

### Part 1 — SHELL-3 verification steps

#### What already shipped (commit `1d3bfc4`, on `main`)

- `build_shell_verb_registry_lines()` in
  `scripts/build_windows_distribution.py` generates the Inno `[Registry]`
  verb keys directly from `quill.core.shell_verbs.default_shell_verbs()`.
- A new opt-in `[Tasks]` checkbox, `shellverbs`, gates every verb key; all
  keys carry `uninsdeletekey` for clean uninstall.
- The committed `installer/quill.iss` is regenerated to include the verbs.
- Six contract tests in
  `tests/unit/scripts/test_build_windows_distribution.py` assert per-verb /
  per-extension coverage, opt-in + uninstall-clean flags, the launch command
  shape, and end-to-end presence in the generated `.iss`.

These are all green (ruff + strict mypy + pytest). **What remains is purely a
live Windows install/uninstall pass — it cannot be done in a non-live
environment and is the only thing standing between SHELL-3 and Done.**

#### Prerequisite: install the Inno Setup 6 compiler (ISCC)

The build box does **not** currently have ISCC. Install it once:

```powershell
winget install --id JRSoftware.InnoSetup --source winget
```

Confirm it resolves (either of these should print a path):

```powershell
Get-Command ISCC.exe -ErrorAction SilentlyContinue
@("C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
  "C:\Program Files\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ }
```

#### Step 1 — Build the portable bundle + installer

From the repo root, with the venv active:

```powershell
# Build the portable tree, regenerate installer/quill.iss, and compile the
# installer in one pass. --bundle-python makes the result self-contained.
python -m scripts.build_windows_distribution --bundle-python --compile-installer
```

Expected: `windows-distribution\installer\Quill-Setup-<version>.exe` (and/or
`...\Output\Quill-Setup-<version>.exe`) is produced. If `--compile-installer`
is not wired as a flag in your build, compile manually:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
  windows-distribution\installer\quill.iss
```

#### Step 2 — Install with the "Send to Quill" verbs enabled

1. Run `Quill-Setup-<version>.exe`.
2. On the **Select Additional Tasks** page, **check**
   *"Add 'Send to Quill' actions (OCR, Open, Read aloud) to the file
   right-click menu"* (it is unchecked by default, by design).
3. Finish the install.

Accessibility check while you are here: the task checkbox label must be read
clearly by your screen reader, and the wizard must not auto-close before the
final status is announced (it is configured `CloseApplications=force`,
`RestartApplications=no`).

#### Step 3 — Verify the verbs appear and run (the core test)

The classic registry verbs surface under **"Show more options"** on
Windows 11, and directly in the **Shift+F10** keyboard context menu.

1. In **File Explorer**, navigate to a test **`.png`** (or `.jpg`, `.tif`).
2. Give it focus and press **Shift+F10** (keyboard context menu).
   - On Win11 you may need to arrow to **"Show more options"** first.
3. Confirm these items are present and screen-reader friendly:
   - **OCR with Quill**
   - **OCR with Quill (structured Markdown)** — only meaningful when AI is on
   - **Read aloud in Quill**
   (For a `.txt`/`.md`/`.html` file you should instead see **Open in Quill**
   and **Read aloud in Quill**.)
4. Activate **OCR with Quill**.
5. Confirm: a running QUILL instance is reused (or one launches), focus lands
   on the **OCR review dialog**, and an announcement states what happened.
6. Repeat once for a **`.pdf`** to confirm document handling.

> If a verb does **not** appear, the most likely causes are: the `shellverbs`
> task was left unchecked at install, or another app owns an overriding
> per-extension association. Re-run the installer and confirm the task is
> ticked. The keys are written to **HKCU** (never HKLM), so no elevation is
> needed and no other user is affected.

#### Step 4 — Confirm the registry keys exist (optional, precise)

```powershell
# Should list a "Quill.ocr" subkey with a (default) value of "OCR with Quill"
reg query "HKCU\Software\Classes\SystemFileAssociations\.png\shell\Quill.ocr" /ve
reg query "HKCU\Software\Classes\SystemFileAssociations\.png\shell\Quill.ocr\command" /ve
```

The `\command` default value should be:
`"<install>\run-quill.cmd" --action ocr "%1"`.

#### Step 5 — Uninstall and confirm clean removal

1. Uninstall QUILL (Settings → Apps, or the Start-menu uninstaller).
2. When prompted about removing personal data, either choice is fine for this
   test (that prompt covers `%APPDATA%\Quill`, not the shell verbs).
3. Re-run the `reg query` commands from Step 4 — both must now return
   **"ERROR: The system was unable to find the specified registry key"**,
   proving `uninsdeletekey` cleaned up the verbs.
4. Re-check **Shift+F10** on the test `.png`: the Quill verbs must be gone.

#### Step 6 — Flip SHELL-3 to Done

Once Steps 1–5 pass on real hardware:

- In `docs/planning/ROADMAP.md`: change the **SHELL-3** row Status from `In progress` to
  `Done`, move `SHELL-3` out of the two living *Work-in-progress* lists into
  the *Completed* Tier 2 list, and update the tracker totals
  (Tier 2 becomes `60 | 58 | 2 | AI-19, SHELL-2`; bump the 1.0 subtotal and
  grand total Done counts by 1).
- Add a dated activity-log entry recording the live verification pass.
- Regenerate the artifacts: `pandoc -s docs/planning/ROADMAP.md -o docs/planning/ROADMAP.html`
  and `pandoc -s docs/planning/ROADMAP.md -o docs/planning/ROADMAP.epub`.
- Stage `docs/planning/ROADMAP.md` + `docs/planning/ROADMAP.html` + `docs/planning/ROADMAP.epub` only and commit.

### Part 2 — What's left, issue by issue

#### Umbrella #113 — Open & OCR from the file manager

**Status: substantially delivered on Windows; keep open as the umbrella.**
The shared groundwork it asked for is done: the action-bearing entry point
(`quill --action <verb> "<path>"`), routing through the existing
single-instance IPC, the qualifying file-type sets, and the initial action
set (Open, OCR, Read aloud) all ship via SHELL-1. Close this only when its
three sub-issues are resolved.

#### #114 — Windows Explorer context menu

**Status: classic/Show-more-options path is code-complete and tested; needs
the Part 1 live pass to call done. One sub-item is intentionally deferred.**

| Sub-item from #114 | Status |
| --- | --- |
| Classic registry verbs (`SystemFileAssociations\<ext>\shell\…`) per image ext + `.pdf` | **Done in code** (SHELL-1 runtime writer + SHELL-3 installer registration) |
| Verb invokes shared `--action` entry point over single-instance IPC | **Done** (SHELL-1) |
| Installer registration + clean uninstall | **Done in code** (SHELL-3); **needs live verify** (Part 1) |
| Reachable via Shift+F10; clear labels; focus + announcement after invoke | **Done in code**; confirmed by the Part 1 manual pass |
| **Modern Win11 menu via `IExplorerCommand` (packaged COM)** | **Deferred to QUILL 2.0** — the OS gates the primary menu behind compiled COM + package identity (sparse/MSIX). Out of scope for 1.0. |

**To finish #114 for 1.0:** run Part 1, then post a status comment noting the
modern-menu `IExplorerCommand` piece is tracked as a 2.0 follow-up, and close.

#### #115 — macOS Finder integration

**Status: Blocked, correctly. Not a 1.0 item.**
Depends on the macOS port (#42), which is not done. The OCR engine work it
describes (Apple Vision backend) also lands with the macOS port. No action now.

#### #116 — Structured OCR (AI-gated)

**Status: functionally delivered (SHELL-2), pending one live-AI verification;
the geometry/bounding-box enhancement is an optional follow-up.**

| Sub-item from #116 | Status |
| --- | --- |
| Gate behind AI + explicit `ocr_structured` opt-in setting | **Done** (SHELL-1/SHELL-2) |
| Dedicated `transform`-style op returning structured Markdown | **Done** — assistant `structure` operation |
| Feed structured result into the OCR review dialog | **Done** — `_apply_ocr_structuring` in the OCR worker |
| Plain-text behavior unchanged when AI off | **Done** — degrades safely with a status note |
| **Capture layout geometry (bounding boxes) for tables/columns** | **Not started** — optional quality enhancement; `OcrLine` has no boxes yet. Nice-to-have, can be a 2.0 follow-up. |

**To finish #116 for 1.0:** one live-key end-to-end run + structuring-quality
tuning on real multi-column / table OCR output (this is the SHELL-2 remainder),
then close noting the geometry enhancement is a future improvement.

---

## Open Tier 2 roadmap items (the honest blockers)

After SHELL-1 (Done) and this SHELL-3 work, Tier 2 stands at **57 of 60**.
The three open items and what each genuinely needs:

| ID | What's left | Blocker class |
| --- | --- | --- |
| **SHELL-3** | The Part 1 live install → right-click → run → uninstall pass | Windows runtime + Inno Setup install cycle |
| **SHELL-2** | One live-AI run + prompt-quality tuning on real OCR; then flip to Done | Configured/available AI backend |
| **AI-19** | Real HTTPS device-login poster, `DeviceLoginDialog`, DPAPI token storage, AIBackend wiring, live sign-in (RFC 8628 state machine already built + tested) | Live provider OAuth device endpoint + Windows runtime |

**Closest to Done:** SHELL-3 and SHELL-2 — each needs a single live pass with
no further code. AI-19 still needs real code plus a live provider.

### Explicitly out of scope for 1.0 (do not work on)

- Win11 modern primary-menu `IExplorerCommand` sparse package (the deferred
  half of #114) — 2.0.
- OCR bounding-box geometry capture (the deferred half of #116) — 2.0.
- macOS Finder (#115) — blocked on the macOS port (#42).


---

# Appendix: Accessibility documentation

_Folded in from the former docs/QUILL-PRD.md on 2026-06-13 (ACR/VPAT conformance report + announcement-grammar style guide)._

# QUILL accessibility documentation

_Consolidated from the former docs/accessibility/ folder on 2026-06-13. Each section preserves the original document in full._


---

<!-- Source: docs/accessibility/acr-vpat.md -->

# Accessibility Conformance Report (ACR)

## Report details

- Product: **Quill**
- Version: **1.0.0**
- Report date: **2026-05-28**
- Contact: **<accessibility@quill.local>**

## Standards and guidelines

- WCAG 2.1 Level A: _To be assessed_
- WCAG 2.1 Level AA: _To be assessed_
- Section 508: _To be assessed_

## VPAT summary table

| Criteria | Conformance Level | Remarks |
| --- | --- | --- |
| 1.1.1 Non-text Content | Supports / Partially Supports / Does Not Support | _Fill in evidence_ |
| 1.3.1 Info and Relationships | Supports / Partially Supports / Does Not Support | _Fill in evidence_ |
| 2.1.1 Keyboard | Supports / Partially Supports / Does Not Support | _Fill in evidence_ |
| 2.4.3 Focus Order | Supports / Partially Supports / Does Not Support | _Fill in evidence_ |
| 4.1.2 Name, Role, Value | Supports / Partially Supports / Does Not Support | _Fill in evidence_ |

## Assessment notes

- Add screen-reader coverage notes (NVDA, Narrator, JAWS).
- Add keyboard-only walkthrough findings.
- Add known limitations and remediation targets.


---

<!-- Source: docs/accessibility/announcement-style-guide.md -->

# Announcement style guide

This guide defines the shared grammar for every status message and
screen-reader announcement in Quill. A single predictable shape lets users of
NVDA, JAWS, and Narrator parse an outcome in one pass and builds trust that the
app always reports what it just did.

The grammar is implemented in [quill/core/announcements.py](../../quill/core/announcements.py)
(`format_announcement`, `format_progress`, `pluralize`). Use those helpers
rather than hand-building strings, and keep this document in sync with them.

## The grammar

```text
<Verb> <object>[, <count> <unit>(s)][, <detail>].
```

- **Verb.** The action. Use past tense for outcomes ("Rewrote", "Saved",
  "Replaced") and present participle for progress that precedes a slow action
  ("Rewriting", "Summarizing").
- **Object.** What was acted on: "paragraph", "document", "selection". Optional
  for verb-only outcomes such as "Copied".
- **Count and unit.** An optional quantity with an automatically pluralized
  unit and a thousands separator: "42 words", "1 word", "1,200 words",
  "2 matches".
- **Detail.** An optional trailing clause, its own comma segment.
- The sentence is capitalized and ends with a period (unless it already ends in
  `.`, `!`, or `?`).

## Examples

| Situation | Announcement |
| --- | --- |
| Rewrote the paragraph at the cursor | Rewrote paragraph, 42 words. |
| Summarized the whole document | Summarized document, 1,200 words. |
| Saved the file | Saved document. |
| Copied with no measurable object | Copied. |
| Replaced a one-word selection | Replaced selection, 1 word. |
| Nothing was selectable to act on | Nothing to rewrite. |
| Starting a slow rewrite | Rewriting paragraph, 42 words. |

## Rules

1. **Always report the outcome.** Every action that changes the document or
   state announces what happened, including the scope it chose when there was
   no selection (paragraph at the cursor, or the whole document).
2. **State the scope and count for content actions.** When an action operates on
   a body of text, include the object and the word count so the user knows the
   size of what changed.
3. **Say so when nothing happened.** If there is nothing to act on, announce it
   ("Nothing to rewrite.") instead of staying silent or sending an empty
   request.
4. **Keep it one short sentence.** No nested clauses beyond a single optional
   detail segment. Screen-reader users should not have to wait through a
   paragraph.
5. **No raw punctuation tricks.** Do not pad with parentheses or trailing
   ellipses; the helpers produce a clean sentence.
6. **Reuse the helpers.** Do not duplicate phrasing logic. Import
   `format_announcement` / `format_progress` from `quill.core.announcements`.

## Verb reference (common actions)

| Action | Progress verb | Outcome verb |
| --- | --- | --- |
| Rewrite | Rewriting | Rewrote |
| Summarize | Summarizing | Summarized |
| Fix grammar | Checking grammar in | Fixed grammar in |
| Continue writing | Continuing | Continued |
| Save | Saving | Saved |
| Replace | Replacing | Replaced |
| Copy | Copying | Copied |


---

# Appendix: QA test plan

_Folded in from the former docs/QUILL-PRD.md on 2026-06-13._

# QUILL QA documentation

_Consolidated from the former docs/qa/ folder on 2026-06-13. Each section preserves the original document in full._


---

<!-- Source: docs/qa/final-qa-test-plan.md -->

# QUILL 1.0 final-QA test plan

Status: living document — execution owned by the maintainer for the Tier 6
release gate (DLG-3.8). This is the authoritative manual and exploratory test
plan for the QUILL 1.0 release. It complements, and does not replace, the
machine-enforced gate ladder (PR CI, Security CI, Accessibility CI) and the
`dialogs.md` manual dialog regression checklist.

## 1. Purpose and scope

This plan defines the final, human-executed quality pass required before QUILL
1.0 ships. Its job is to verify, on a real Windows runtime with real assistive
technology, the behaviours that static analysis and headless unit tests
**cannot** prove: screen-reader announcements, focus journeys, audio output,
OCR against live images, the device-login network round trip, and the felt
quality of the writing experience.

In scope:

- Every user-facing dialog enumerated in `dialogs.md`.
- Keyboard operability and focus management across the whole shell.
- Screen-reader parity (NVDA, JAWS, Narrator) for announcements and navigation.
- The QUILL key, browse mode, and Quick Nav surfaces.
- File, session, and document lifecycle (open, edit, save, recover).
- AI / assistant tool flows, including consent gating and async "busy" states.
- OCR capture and review.
- Startup, onboarding, trust-consent, and crash-recovery paths.
- Read-aloud / speech output.
- Installer and first-run on a clean machine.
- Performance and stability under realistic documents.

Out of scope for 1.0 (deferred to 2.0, tracked in `ROADMAP.md`): axe-core / Nu
Html Checker validation, BITS Whisperer, the GLOW watch-action binding
(WATCH-8), and the Accessibility Agents workstream.

## 2. Test environments

Run the full pass on at least one machine from each row. Record the exact build
identifier (version + commit) on every result.

| Environment | OS | Screen reader | Notes |
| --- | --- | --- | --- |
| Primary | Windows 11 (latest) | NVDA (latest stable) | Baseline for every case |
| Secondary | Windows 11 (latest) | JAWS (latest) | Spot-check the high-traffic surfaces |
| Sanity | Windows 10 + Windows 11 | Narrator | Confirm no hard breakage |
| Clean-install | Fresh Windows VM, no Python | (NVDA) | Installer + first-run only |
| High contrast | Windows 11, High Contrast on | NVDA | Visual + announcement parity |

Build under test: record `version` from About Quill and the commit SHA. A pass
is only valid against a single, named build.

## 3. Entry and exit criteria

Entry criteria (all must hold before a final-QA pass begins):

- All required CI gates are green on `main`: PR CI, Security CI, Accessibility
  CI, GATE-6 (public surface), GATE-11 (module size), A11Y-4 (banned patterns
  and dialog registry), and the DLG-3 `dialog_inventory.json` snapshot.
- `dialogs.md` and the `dialog_inventory.json` snapshot agree with the source
  (run `python -m quill.tools.dialog_inventory` and confirm no diff).
- The build installs cleanly on the clean-install environment.

Exit criteria (all must hold to sign off 1.0):

- Every section below has a recorded result against the named build.
- Every `dialogs.md` row carries pass/fail evidence (see §5).
- No open Critical or High severity defect (see §11).
- Each known limitation is documented in the ACR/VPAT and release notes.

## 4. Severity model

| Severity | Definition | Release impact |
| --- | --- | --- |
| Critical | Data loss, crash, silent network egress, or a screen-reader user cannot complete a core task | Blocks release |
| High | A core task is severely degraded, or an announcement/focus contract is broken | Blocks release unless explicitly waived |
| Medium | A non-core task is degraded, or an announcement is imprecise | Fix or document before release |
| Low | Cosmetic, or a minor wording nit | Track for a follow-up |

## 5. Evidence capture

For every test case record: build id, environment row, screen reader + version,
pass/fail, and a one-line observation. For dialog cases, capture the exact
announced title and the announced text of the default and cancel actions. For
failures, capture: reproduction steps, expected vs actual announcement/focus,
severity, and a linked issue.

Store the completed evidence alongside this plan (a dated copy of the filled
`dialogs.md` plus a results sheet) so each release has a durable record.

### 5.1 Evidence artifacts to record alongside the build id

For every pass, record the following alongside the build identifier in the
results sheet. They are the machine-checked receipts that the build under
test actually agrees with the in-repo enforcement gates.

- **`dialog_inventory.json` mtime** (`tests/unit/ui/fixtures/dialog_inventory.json`):
  the snapshot must be regenerated by `python -m quill.tools.dialog_inventory --write`
  whenever a dialog is added, moved, or removed. If the in-source AST scan
  disagrees with the committed snapshot, `tests/unit/ui/test_dialog_inventory.py`
  fails the build; a stale snapshot in a 1.0 release tag is a release-blocker.
- **`module_size_budgets.json` `_rebaseline_*` keys** (`quill/tools/module_size_budgets.json`):
  if any `_rebaseline_<module>` key is set, the corresponding `quill/**/*.py`
  file is allowed to exceed the default 600-line cap. Record the rebaseline
  set in the results sheet so reviewers can audit each oversized module by
  hand.
- **`wxPython` runtime version** (`python -c "import wx; print(wx.__version__)"`):
  QUILL supports `wxPython 4.2.x` with `wxWidgets 3.2.x`. A test pass on
  wx 4.1 or wxWidgets 3.0 is not a 1.0 result.
- **Public surface fixture** (`tests/unit/ui/fixtures/main_frame_public_surface.json`):
  regenerate with `python -m quill.tools.ui_surface --write` if any
  `MainFrame` public method is added or removed. The fixture is the
  GATE-6 characterization receipt.
- **`quill-glow-core` engine hash** (if GLOW is exercised on the build):
  the shared engine in `quill/core/glow.py` is the cross-platform spine;
  record the engine version any time a GLOW surface is in the pass.

If any of the five artifacts above changed during the pass, the diff must
be present in the commit history of the release branch; a release tag
without these diffs is not a clean 1.0.

## 6. Dialog estate pass (covers DLG-2, DLG-3.6, DLG-3.8)

The authoritative list is `dialogs.md` (sections A–X). Do not duplicate it here;
execute it directly. The contract every dialog must satisfy is the A11Y-4
contract restated at the top of `dialogs.md`:

1. It opens from the listed command or menu path.
2. Tab and Shift+Tab reach every control in a sensible order.
3. The screen reader announces the dialog title and each control.
4. Enter activates the default action; Escape and the close button cancel.
5. On close, focus returns to the editor.
6. The dialog never traps, freezes, or goes silent.

Screen-reader coverage matrix for the dialog estate:

| Surface group (`dialogs.md`) | NVDA | JAWS | Narrator |
| --- | --- | --- | --- |
| A. File / session | Full | Spot | Sanity |
| B. Settings, palette, menu editor | Full | Spot | Sanity |
| C. Navigate (Go To, Outline, bookmarks) | Full | — | Sanity |
| D–F. Text analysis, accessibility, intake | Full | — | Sanity |
| G. Read aloud + OCR (incl. OCR Review) | Full | Spot | Sanity |
| H. Sticky notes | Full | Spot | Sanity |
| I–P. Formats, compare, keyboard, macros | Full | — | Sanity |
| Q. AI and assistant (DLG-2 / DLG-3.6) | Full | Spot | Sanity |
| R. BITS Whisperer | Out of scope for 1.0 | — | — |
| S–T. Help, features, startup, support | Full | Spot | Sanity |
| U. Selection and QUILL key | Full | — | Sanity |
| V. Nested and secondary dialogs | Full | — | Sanity |
| W. Power Tools | Full | — | Sanity |
| X. Startup-only (crash recovery, trust) | Full | Spot | Sanity |

"Full" = exercise the complete A11Y-4 contract. "Spot" = open, confirm title +
default + Escape + focus return. "Sanity" = open and confirm it is not silent or
trapped. JAWS spot priority: startup, the assistant/AI tools, sticky notes, and
watch profiles (the surfaces with live lists, async work, and chained modals).

Special attention for the AI/assistant tools (Q) — the DLG-2 / DLG-3.6
acceptance the maintainer is signing off:

- Each long-running action disables its trigger before work starts and
  re-enables on completion.
- "Busy" state is announced; the surface never appears hung.
- Results marshalled back to the UI thread are announced once, not duplicated.
- A worker exception surfaces as an announced error, not a silent failure.
- No cloud/AI action runs without an explicit, per-action consent.

## 7. Keyboard and focus pass

- Tab order is sensible and complete on the main shell and every dialog.
- No keyboard trap anywhere; Escape always has a defined meaning.
- The QUILL key prefix (`Ctrl+Shift+Grave` by default) enters, announces, times
  out, and is remappable; the old default stops working after a remap.
- Browse mode enters, announces, navigates by element, and times out.
- Quick Nav / Heading Organizer / Outline Navigator move the caret and announce.
- Status-bar cells are reachable, announce their value, and expose their menu.
- Focus returns to the editor after every modal closes.

## 8. File, session, and document lifecycle

- Open, edit, save, Save As, and encoding selection round-trip correctly.
- Dirty-state title suffix appears and clears accurately.
- Prompt-to-save offers Save / Don't Save / Cancel and honours each.
- Multi-tab switch wraps correctly and is announced.
- Session save/open restores the working set.
- Atomic writes: a forced failure mid-save never corrupts the original file;
  `.bak` / recovery behaves per the data-layout contract.
- Restore Backup recovers a prior version.

## 9. AI, consent, and privacy pass

- No outbound document content without an explicit, visible, per-action consent.
- The consent surface states what will be sent and to where before sending.
- A declined consent cancels the action and announces the cancellation.
- API keys are stored via DPAPI; "Forget API Key" clears them and confirms.
- The device-login round trip (AI-19) completes against the live endpoint on a
  real network (cannot be verified headless).
- No document text appears in any log file after an AI action.

## 10. OCR pass (OCR-1, OCR-3)

Requires a live display, clipboard, and OCR engine, so it cannot be verified
headless.

- OCR Image, OCR Clipboard Image, and OCR Screen Capture each produce text.
- The screen-capture target chooser offers whole screen vs active window.
- OCR Review opens after completion, is fully keyboard/SR operable, and inserts
  the accepted text at the caret.
- A failed or empty OCR announces a clear outcome, not silence.

## 11. Startup, onboarding, and recovery pass

- First run shows onboarding; consent is recorded only on explicit accept.
- A declined trust-consent at startup closes the app rather than continuing.
- Each deferred startup step is isolated: a forced failure in one step logs to
  `logs/startup-errors.log` and keeps QUILL open.
- Crash Recovery appears after an unclean exit and restores or discards per the
  user's choice.
- The Untrusted Location Warning appears for files from untrusted folders.

## 12. Read-aloud and speech pass

- Read Aloud Voice Settings and Read Aloud Settings apply and persist.
- Generate Speech Audio produces a file and announces completion.
- Voice selection chain falls back gracefully when an engine is unavailable.

## 13. Installer and first-run pass (clean machine)

- The installer runs to completion on a fresh Windows VM with no Python.
- Single-instance behaviour holds (a second launch focuses the first).
- First launch reaches a usable editor with a screen reader running.
- Uninstall removes the app and leaves user data per the documented policy.

## 14. Performance and stability pass

- Open and edit a large document (target sizes per the PERF acceptance rows)
  without UI-thread stalls; cross-thread updates marshal through `wx.CallAfter`.
- Typing latency stays within the documented budget on the primary environment.
- No memory growth over a sustained editing session.
- The diagnostics bundle (Save Diagnostics) collects without document content.

## 15. High-contrast and visual pass

- High Contrast mode renders every surface legibly; nothing disappears.
- Focus indicators remain visible.
- Contrast validation tooling reports the shipped theme as compliant.

## 16. Localization sanity

- The shipped locales load; no layout breaks truncate a control's name.
- Announcements remain grammatical in each shipped locale.

## 17. Sign-off

Final sign-off is recorded by the maintainer against a single named build when
every section has evidence, `dialogs.md` is fully ticked for that build, and no
open Critical or High defect remains. This sign-off closes DLG-3.8 and, with it,
the deferred SR-verification criteria of DLG-2 and DLG-3.6.

| Role | Name | Build | Date | Result |
| --- | --- | --- | --- | --- |
| Maintainer (SR sign-off) | | | | |


---

# Appendix: Deployment

_Folded in from the former docs/QUILL-PRD.md on 2026-06-13._

# QUILL Deployment Guide

Covers distribution, update packaging, pack distribution, and release best practices.

## Table of Contents

- [Release types](#release-types)
- [Building a Windows release](#building-a-windows-release)
- [Update mechanism overview](#update-mechanism-overview)
- [Update feed format](#update-feed-format)
- [Building an update archive](#building-an-update-archive)
- [Bootstrapper binaries](#bootstrapper-binaries)
- [Update ZIP scripts](#update-zip-scripts)
- [Hosting the feed](#hosting-the-feed)
- [Publishing a release](#publishing-a-release)
- [Pack distribution](#pack-distribution)
- [Version numbering](#version-numbering)
- [Testing updates locally](#testing-updates-locally)
- [Rollback](#rollback)
- [Best practices](#best-practices)

---

## Release types

| Type | Description | Tag pattern |
|------|-------------|-------------|
| Beta | Pre-release for wider testing | `v0.5.0-beta.1` |
| Stable | Production release | `v1.0.0` |
| Hotfix | Critical-only patch | `v1.0.1` |

All three go through the same `windows-release` workflow. Mark betas as
`prerelease: true` in the GitHub release (already the default in the
workflow).

---

## Building a Windows release

The build workflow (`windows-release.yml`) runs on `push` to a `v*` tag.
To trigger it manually:

```powershell
git tag v0.5.0-beta.1
git push origin v0.5.0-beta.1
```

The workflow produces three artifacts:

- `quill-installer` — Inno Setup `.exe` installer
- `quill-portable` — standalone folder, no installer required
- `quill-release-artifacts` — checksums, SBOM, update feed stub

To build locally (requires Inno Setup 6 and Python 3.12):

```powershell
pip install -e .[ui,spellcheck,dev]
python scripts/build_windows_distribution.py `
    --bundle-python `
    --compile-installer `
    --iscc-path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
    --output-dir windows-distribution
```

---

## Update mechanism overview

QUILL uses the AccessibleApps `autoupdate` library (vendored at
`quill/_vendor/autoupdate/`) for incremental over-the-air updates.

The flow:

1. `QuillUpdateManager.check_for_updates()` is called (on startup or from
   Help > Check for Updates).
2. The manager fetches the update feed JSON from a hosted endpoint.
3. If the feed version is newer than the running version, the user is
   prompted via `_on_update_available`.
4. If accepted, the update ZIP is downloaded with progress announcements.
5. The ZIP is extracted to a temp directory.
6. The platform bootstrapper (`bootstrap.exe` on Windows) is moved out of
   the extracted tree and executed.
7. The bootstrapper waits for QUILL to exit, then copies the new files over
   the installation and restarts the app.

The manager announces all state changes through the screen-reader bridge
(`prism_bridge.announce`) so users with NVDA/JAWS/Narrator hear every step
without watching the UI.

---

## Update feed format

The feed is a single JSON file served over HTTPS. Example:

```json
{
  "current_version": "0.5.0",
  "description": "Accessibility improvements and bug fixes. See the release notes for details.",
  "published_at": "2026-06-12T14:00:00Z",
  "downloads": {
    "Windows": "https://releases.example.com/quill-0.5.0-windows.zip",
    "Darwin":  "https://releases.example.com/quill-0.5.0-macos.zip",
    "Linux":   "https://releases.example.com/quill-0.5.0-linux.zip"
  }
}
```

Field notes:

- `current_version` — the version string clients compare against their
  running version. See [version numbering](#version-numbering) for the
  comparison rules.
- `description` — shown to the user in the update prompt. Keep it one or
  two sentences; longer notes belong in the release notes URL.
- `downloads` — key is the `platform.system()` return value (`Windows`,
  `Darwin`, `Linux`). A client whose platform is not present skips the
  update silently.

Generate the feed with the bundled script:

```powershell
python scripts/generate_app_updater_feed.py `
    --version "0.5.0" `
    --windows-url "https://github.com/Community-Access/quill/releases/download/v0.5.0/quill-0.5.0-windows.zip" `
    --macos-url   "https://github.com/Community-Access/quill/releases/download/v0.5.0/quill-0.5.0-macos.zip" `
    --linux-url   "https://github.com/Community-Access/quill/releases/download/v0.5.0/quill-0.5.0-linux.zip" `
    --description "Accessibility improvements and bug fixes." `
    --output docs/site/updates/.quill-app-updater-v1.json
```

Commit and push; the GitHub Pages workflow publishes it automatically.

---

## Building an update archive

The update ZIP must contain:

```
quill/                   all application Python files
quill-data/              data files (words_alpha, thesaurus, schemas, quillins)
bootstrap.exe            Windows bootstrapper (see below)
```

The bootstrapper **must be at the root of the ZIP** (not in a subdirectory)
so `move_bootstrap` can find it. The rest of the layout must match the
structure that `bootstrap.exe` expects when copying files over the existing
installation.

Use `scripts/build_update_zip.py` to produce the update ZIP automatically.
It handles delta computation, bootstrapper placement, and `UPDATE_MANIFEST.json`
generation. See [Update ZIP scripts](#update-zip-scripts) for full usage.

> The bootstrapper binaries are not checked into this repo because they are
> native executables maintained upstream. Run `scripts/fetch_bootstrappers.py`
> to download them, or see
> `quill/_vendor/autoupdate/bootstrappers/README.txt` for manual instructions.

---

## Bootstrapper binaries

The bootstrapper (`bootstrap.exe` on Windows, `bootstrap-mac.sh` on macOS,
`bootstrap-lin.sh` on Linux) is built and maintained by the AccessibleApps
project:

    https://github.com/accessibleapps/app_updater

To obtain the binaries for a release build, use the bundled fetch script:

```powershell
python scripts/fetch_bootstrappers.py
```

This downloads all three bootstrappers from the upstream repo, verifies
their SHA-256 hashes, and records checksums in
`quill/_vendor/autoupdate/bootstrappers/checksums.sha256`. Re-running is
idempotent — files with matching checksums are skipped.

The binaries are not required for development or running tests. They are
only needed when building a distributable package that supports in-place
updates.

Add the `bootstrappers/` directory to the Windows installer via the Inno
Setup script generated by `build_windows_distribution.py`. The script
already includes a `[Files]` directive for the bootstrapper; verify it
points to the correct path before compiling.

---

## Update ZIP scripts

Three scripts in `scripts/` automate the update ZIP pipeline. All three are
stdlib-only and require no extra dependencies beyond what `pip install -e .`
already installs.

### `scripts/fetch_bootstrappers.py`

Downloads `bootstrap.exe`, `bootstrap-lin.sh`, and `bootstrap-mac.sh` from
the AccessibleApps upstream repo and writes a `checksums.sha256` file for
verification. Binaries land in `quill/_vendor/autoupdate/bootstrappers/` and
are excluded from git.

```powershell
# Download (idempotent — skips files whose SHA-256 matches the recorded checksum)
python scripts/fetch_bootstrappers.py

# Force re-download regardless of checksum
python scripts/fetch_bootstrappers.py --force

# Verify existing files without downloading
python scripts/fetch_bootstrappers.py --verify-only
```

The CI `build` job runs this automatically before compiling the installer.

### `scripts/generate_file_manifest.py`

Walks `quill/` and records the SHA-256 hash, size, and install path of every
distributable file. Output is `docs/site/updates/manifests/manifest-{version}.json`.
The manifest feeds `build_update_zip.py` to compute deltas.

```powershell
# Generate manifest for the current source tree
python scripts/generate_file_manifest.py --version 0.5.0

# Generate and compare against a previous release
python scripts/generate_file_manifest.py --version 0.5.0 --compare-to 0.4.9
```

Excluded from the manifest: `quill/tools/`, `__pycache__/`, `*.pyc`, `*.pyo`.
The `--compare-to` flag prints changed, added, and deleted file counts and a
net size delta — useful for sanity-checking before cutting a release.

### `scripts/build_update_zip.py`

Produces the update ZIP consumed by the autoupdate bootstrapper. By default
it runs in delta mode: only files whose SHA-256 changed since the previous
manifest are included, keeping update ZIPs lean.

```powershell
# Delta update (auto-detects base version from available manifests)
python scripts/build_update_zip.py --version 0.5.0

# Force full update
python scripts/build_update_zip.py --version 0.5.0 --mode full

# Specify base version explicitly
python scripts/build_update_zip.py --version 0.5.0 --mode delta --base-version 0.4.9

# Target a non-Windows platform
python scripts/build_update_zip.py --version 0.5.0 --platform macos
```

The ZIP always contains:

- `bootstrap.exe` (or platform equivalent) at the root
- `UPDATE_MANIFEST.json` at the root — lists which files were changed, added,
  or deleted
- Changed/added files under `python/Lib/site-packages/` (the portable
  distribution layout)

If no previous manifest exists, the script falls back to full mode
automatically.

### Running the full pipeline

```powershell
# 1. Fetch bootstrappers (once per release machine)
python scripts/fetch_bootstrappers.py

# 2. Generate the manifest for this version
python scripts/generate_file_manifest.py --version 0.5.0

# 3. Build the delta update ZIP
python scripts/build_update_zip.py --version 0.5.0

# Output: release-artifacts/quill-0.5.0-update-windows.zip
```

The CI `build` job runs all three steps automatically on each `v*` tag push.

---

## Hosting the feed

### GitHub Pages (default)

The update feed lives at:

    docs/site/updates/.quill-app-updater-v1.json

The `github-pages` workflow publishes the entire `docs/site/` tree on every
push to `main`. The feed URL used by `QuillUpdateManager` should be:

    https://community-access.github.io/quill/updates/.quill-app-updater-v1.json

Update `UPDATE_FEED_ENDPOINT` in `quill/core/settings_specs.py` (or
wherever the URL is configured) before the first beta that ships the update
check.

### Keeping the feed up to date

Workflow: after every release, regenerate the feed, commit it, and push.
The Pages deployment runs automatically:

```powershell
python scripts/generate_app_updater_feed.py --version "0.5.1" ...
git add docs/site/updates/.quill-app-updater-v1.json
git commit -m "chore: update feed to 0.5.1"
git push
```

Do not update the feed until all platform ZIPs are uploaded and their URLs
are stable. Clients check the feed on startup; a partial update (feed
updated before ZIPs are live) will offer a broken download to users.

---

## Publishing a release

1. Bump the version in `pyproject.toml` and commit.
2. Tag the commit: `git tag v0.5.0 && git push origin v0.5.0`
3. The `windows-release` workflow runs automatically:
   - runs tests (with `--ignore` for the two known-hanging tests)
   - builds the installer and portable ZIP
   - uploads artifacts
   - creates a GitHub release draft
4. Download the portable ZIP artifact, add the bootstrapper at the root,
   re-upload as the final update ZIP to the GitHub release.
5. Generate the update feed pointing at the final ZIP URLs.
6. Commit and push the feed; Pages deploys within minutes.
7. Announce the release (release notes, mailing list, etc.).

---

## Pack distribution

Packs (Quillins) are distributed as `.zip` archives containing a
`manifest.json` validated against `quill/core/schemas/extension.json`.

### Creating a pack

```powershell
# Directory structure:
my-pack/
  manifest.json
  README.md
  LICENSE
  <script-or-data files>

# Validate before distributing:
python -m quill.tools.quillin_lint my-pack --strict

# Package:
Compress-Archive -Path my-pack -DestinationPath my-pack-1.0.zip
```

### Distributing a pack

Packs can be distributed through any channel — GitHub Releases, a personal
website, email. Users install them via Tools > Quillin Manager > Install
from File.

For packs that should ship bundled with QUILL, place them in
`quill/quillins_bundled/` and submit a pull request. Bundled Quillins are
linted in CI with `--strict` and require a `README.md`, a `LICENSE`, and a
`manifest.json` with a `justification` for each capability requested.

### Pack versioning

Pack versions are free-form strings in `manifest.json`. There is no
automatic update mechanism for packs; users re-install a newer `.zip` to
upgrade.

---

## Version numbering

QUILL uses semantic versioning (`MAJOR.MINOR.PATCH`). The vendored autoupdate
library (`quill/_vendor/autoupdate/autoupdate.py`) compares versions with a
tuple-based integer comparison:

```python
tuple(int(x) for x in str(v).split("."))
```

This correctly orders `1.9` before `1.10`. The upstream library used a plain
string comparison (`"1.9" > "1.10"` evaluates True — wrong). The fix is
in `_version_tuple()` in the vendored copy; the upstream issue should be
tracked at https://github.com/accessibleapps/app_updater if a PR is
contributed.

---

## Testing updates locally

To test the full update pipeline without publishing a real release:

1. Start a local HTTP server:

   ```powershell
   python -m http.server 8765 --directory /path/to/test-assets
   ```

2. Create a test feed at `/path/to/test-assets/feed.json`:

   ```json
   {
     "current_version": "99.0.0",
     "description": "Local test update",
     "downloads": { "Windows": "http://localhost:8765/test-update.zip" }
   }
   ```

3. Create `test-update.zip` containing the app files and `bootstrap.exe`.

4. Override the feed URL in a dev settings file (do not commit):

   ```python
   # quill/core/settings.py — temporary, revert before committing
   update_feed_endpoint = "http://localhost:8765/feed.json"
   ```

5. Run QUILL and trigger Help > Check for Updates.

The screen reader should announce "Quill 99.0.0 is available", then
progress during download, then "Update ready. Quill will restart...".

For CI-safe automated tests, see `tests/unit/ui/test_update_manager.py`.
All HTTP is mocked; the bootstrapper execution step is always stubbed.

---

## Rollback

To roll back to a previous version after a bad release:

1. Update the feed to point at the previous version's ZIP:

   ```powershell
   python scripts/generate_app_updater_feed.py `
       --version "0.4.9" `
       --windows-url "https://.../quill-0.4.9-windows.zip" ...
   ```

2. Commit and push. Clients on 0.5.0 will be offered the 0.4.9 update on
   their next startup check.

   Note: `"0.4.9" > "0.5.0"` is false under string comparison, so the
   rollback feed will **not** be offered automatically. You must either:

   - Republish as a higher version number (e.g., `0.5.1-hotfix`) containing
     the older code, or
   - Ask users to reinstall manually.

   This is a known limitation of string-comparison versioning. Plan hotfix
   releases as forward increments.

---

## Best practices

**Do not update the feed before the ZIPs are live.** Users who start QUILL
in the window between feed publication and ZIP upload will get a failed
download.

**Keep description text short.** The description is read aloud by the
screen reader when the update dialog opens. Two sentences maximum; link to
the full release notes instead of embedding them.

**Sign the ZIPs.** The autoupdate library downloads and extracts ZIPs
without verifying a signature. For the beta, this is acceptable. Before
1.0, add SHA-256 checksums to the feed and verify them in
`QuillUpdateManager` before calling `extract_update`.

**Test the bootstrapper on a clean machine before each major release.**
The bootstrapper is a native binary that replaces files on disk. Run it
manually on a clean install once per release cycle to confirm the file-copy
logic matches the new distribution layout.

**Announce update availability through the screen reader, not a modal.**
The current `_on_update_available` implementation returns `True` without
showing a dialog. Before 1.0, replace this with a non-modal notification
bar (or a simple Yes/No dialog that is immediately reachable with Tab).
Never block QUILL startup on an update prompt.

**Staged rollout.** For major versions, serve the new feed to a fraction of
users first. This is not natively supported by autoupdate; implement it by
hosting multiple feed URLs (e.g., `/updates/beta.json` and
`/updates/stable.json`) and shipping beta builds that point at the beta
feed.


---

# Appendix: AccessibleApps integration

_Folded in from the former docs/QUILL-PRD.md on 2026-06-13._

# AccessibleApps Integration Strategy for Quill

## Overview

Quill now integrates multiple libraries from AccessibleApps (MIT-licensed) to accelerate accessibility improvements, enable incremental updates, and provide battle-tested UI components across Windows, macOS, and Linux.

## Components Integrated

### 1. **app_updater** (Incremental Updates)
**Status**: Implemented (production-ready)  
**Files**: 
- `scripts/generate_app_updater_feed.py` — generates JSON feed in autoupdate format
- `quill/ui/update_manager.py` — callback integration with screen-reader announcements
- `pyproject.toml` — autoupdate dependency added to core

**What it enables**:
- Micro-updates: Ship patches as small ZIPs containing only changed files, not full reinstalls.
- Automatic bootstrapper: Platform-specific scripts (`bootstrap.exe`, `bootstrap-mac.sh`, `bootstrap-lin.sh`) apply updates atomically after app exit and restart.
- Accessible UX: Update checks and progress announced via screen reader with explicit user consent.
- Security: Feeds can be cryptographically signed (Ed25519/RSA) and verified client-side.

**Developer notes**:
- Call `UpdateManager.check_for_updates()` from Help menu or startup checks.
- Callbacks route through `prism_bridge.announce()` for screen-reader compatibility.
- CI must produce ZIP update packages in release pipeline (full installer flow unchanged).
- Test bootstrapper atomicity on Windows (NVDA/Narrator) and macOS (VoiceOver).

---

### 2. **smart_list** (Virtual Lists)
**Status**: Optional (integration in progress)  
**Files**: 
- `pyproject.toml` — smart_list added to `[project.optional-dependencies.ui]`
- Prototype: `quill/ui/smartlist_adapter.py` (to be created)

- Virtual scrolling for large outlines/lists (millions of items without memory blowup).
- Accessible DataView on macOS, ListView on Windows/Linux — unified API across platforms.
- Model-based columns via attribute, dict key, or callable — maps naturally to Quill document models.
- Windows IAT hook bypass for UIA enumeration delays on virtual lists >100K items.

**Developer notes**:
- Keep smart_list use confined to `quill/ui` (it imports `wx`).
- Prototype: wrap SmartList/VirtualSmartList in an adapter that matches Quill's existing list interface.
- Test with NVDA/Narrator (Windows) and VoiceOver (macOS) for focus and announcement behavior.
- Intended for outline navigator and large-document list views.

---

### 3.5. **html_to_text** (HTML Paste Cleaning)
**Status**: Fully integrated (production-ready)  
**Files**: 
- `quill/ui/html_paste_cleaner.py` — HTML detection and cleaning logic
- `quill/ui/main_frame.py` — integrated into magic_paste() function
- `tests/unit/ui/test_html_paste_cleaner.py` — 21 comprehensive tests
- `quill/core/settings.py` — `auto_clean_html_paste` setting (currently defaults to `False`)
- `pyproject.toml` — html_to_text added to `[project.optional-dependencies.ui]`

**What it enables**:
- Automatic HTML detection from web browser pastes (blog posts, emails, articles).
- One-click conversion to clean plain text while preserving structure (headings, links, lists).
- Optional auto-clean mode via Settings → Paste (currently opt-in for user safety).
- Fallback regex-based cleaning if html_to_text library is unavailable.
- No silent stripping; user controls every paste action via Magic Paste picker.

**Workflow**:
1. User copies HTML from web browser or email client.
2. User presses Ctrl+Shift+V (Magic Paste).
3. Quill detects HTML and shows picker:
   - "Paste HTML as clean text" (recommended)
   - "Paste HTML as-is" (original raw HTML)
   - "Paste as plain text" (fallback)
4. User chooses; clean version is inserted immediately.

**Developer notes**:
- `analyze_paste(text) → HtmlPasteContext`: Fast heuristic detection (doesn't require html_to_text import to detect).
- `clean_html(html) → str`: Uses html_to_text if available; falls back to regex stripping.
- Heuristic detects HTML tags but avoids false positives (code samples, email footers).
- All 21 tests passing: detection, cleaning, fallback, edge cases, integration scenarios.
- Screen-reader integration: Status bar announces cleanup (e.g., "Pasted cleaned HTML (350 chars)").

---

### 4. **accessible_output2** (Braille + Speech Fallback)
**Status**: Optional (recommended for later)  
**Files**: None yet — planned as fallback in `quill/platform/windows/prism_bridge.py`

**What it enables**:
- Braille output when Prism backend doesn't support it.
- Fallback speech when Prism runtime is unavailable (graceful degradation).
- Mature support for NVDA, JAWS, Narrator via multiple speech backends.

**Developer notes**:
- Do NOT add as a hard dependency; keep Prism as the primary backend.
- Create an optional adapter `quill/platform/windows/accessible_output_adapter.py` that:
  - Detects accessible_output2 availability at import time.
  - Exposes `speak(message, interrupt)` matching Prism's interface.
  - Falls back to `accessible_output2` if Prism probe fails or braille is needed.
- This is a future enhancement after Prism stabilizes and user demand for braille surfaces.

---

### 4. **app_elements** (Common Dialogs)
**Status**: Candidate for selective adoption  
**Files**: None yet — audit and wrap per-component

**What it enables**:
- Pre-built about boxes, standard dialogs, and reusable UI elements.
- Reduces boilerplate for non-editor UI.

**Developer notes**:
- Do NOT wholesale-import; audit each component for Quill's dialog contracts (default buttons, focus return, accessible names).
- Create wrappers in `quill/ui/app_elements_compat.py` that enforce Quill dialog rules.
- Use selectively for About dialog, license viewer, and settings panels.

---

### 5. **platform_utils** (Clipboard, Paths, Stdout)
**Status**: Candidate for later  
**Files**: None yet

**What it enables**:
- Cross-platform clipboard, path normalization, stdout capture — small utilities to reduce boilerplate.

**Developer notes**:
- Low-risk adoption for small utilities.
- Can be integrated incrementally if Quill's platform layer needs it.

---

## Update Process: How It Works

### 1. **Release Pipeline**
```
quill/version.py → scripts/generate_app_updater_feed.py
                  ↓
                  Produces: docs/site/updates/.quill-app-updater-v1.json
                  Format: { "current_version", "description", "downloads": { "Windows": "...", "Darwin": "...", "Linux": "..." } }
```

### 2. **User Workflow (Automatic or Manual)**
```
User: Help → Check for Updates
       ↓
quill/ui/update_manager.py: UpdateManager.check_for_updates()
       ↓
autoupdate library:
  - Downloads update ZIP to staging directory
  - Announces progress via quill.platform.windows.prism_bridge.announce()
  - Calls update_complete_callback() when ready
       ↓
Platform bootstrapper (after app exit):
  - Waits for Quill process to exit
  - Replaces old files with new files from ZIP
  - Restarts Quill
```

### 3. **Micro-Update Example**
```
Release 1.0.0: Full installer (30 MB)
Release 1.0.1: Micro-update ZIP (2 MB)
  - One file changed (bug fix in core)
  - User downloads 2 MB instead of 30 MB
  - Update applied atomically on next startup
```

---

## Attribution & Licensing

All AccessibleApps libraries are **MIT-licensed**. Attribution is documented in:
- `CONTRIBUTING.md` — "Acknowledgments and Attribution" section
- Individual module docstrings (e.g., `quill/ui/update_manager.py`)
- Release notes (when a library is integrated into a shipped version)

---

## Next Steps

### Immediate (v1.0)
1. ✅ Integrate `app_updater` feed generator and update callbacks.
2. ✅ Document update process in user guide and PRD.
3. ✅ Add AccessibleApps attribution to CONTRIBUTING.md.
4. ✅ Fully integrate `html_to_text` with Magic Paste HTML detection and cleaning (21 tests passing).
5. Test app_updater flow locally on Windows (bootstrapper atomicity).
6. Set up CI to produce ZIP update packages alongside full installers.

### Short-term (v1.1 – v1.5)
1. Wire html_to_text auto-clean setting into UI (Settings → Paste → Auto-clean HTML).
2. Prototype and integrate `smart_list` for outlines and large lists.
3. Test `smart_list` on macOS (DataView) and Windows (ListView) with screen readers.
4. Consider selective `app_elements` adoption for dialogs.
5. Evaluate `accessible_output2` braille support if user demand arises.

### Future
- Optional: Add `platform_utils` for clipboard and cross-platform utilities.
- Optional: Integrate `html_to_text` for import/export workflows.
- Optional: Evaluate `opml_lib` if Quill adds outline import/export.

---

## Testing Checklist

Before shipping any AccessibleApps-integrated feature:

- [ ] Source license and README verified (MIT, no unforeseen restrictions).
- [ ] Dependency audit (no heavy transitive deps added).
- [ ] Platform testing: Windows (NVDA, Narrator), macOS (VoiceOver), Linux (Orca).
- [ ] Accessibility: No double-talk; focus management correct; braille (if applicable).
- [ ] Threading: UI updates via `wx.CallAfter` (if applicable); no blocking on main thread.
- [ ] Packaging: New dependencies added to `pyproject.toml` with version pins and platform guards.
- [ ] Docs: User guide updated; CONTRIBUTING.md updated; module docstrings reference upstream.

---

## Contact & Contributions

Questions about AccessibleApps libraries? Open an issue or discussion in this repo. Pull requests that improve integration, fix bugs, or add tests are welcome.

Links:
- AccessibleApps: https://github.com/accessibleapps/
- app_updater: https://github.com/accessibleapps/app_updater (MIT)
- smart_list: https://github.com/accessibleapps/smart_list (MIT)
- accessible_output2: https://github.com/accessibleapps/accessible_output2 (MIT)


---

# Appendix: Native RTF editing and Ulysses study (design)

_Folded in from the former docs/QUILL-PRD.md on 2026-06-13._

# QUILL: Native RTF Editing and a Ulysses Competitive Study

Two forward-looking proposals in one place. Part One asks what it would take for
QUILL to host a real rich-text editing surface so a writer can choose between
plain-text-first writing and live rich editing. Part Two studies Ulysses, the
Apple Design Award winning writing app for Mac, iPad, and iPhone, and recommends
which of its ideas QUILL should adopt without compromising its accessibility-first
soul.

Both parts are written to be ambitious. They are also written honestly: where an
idea collides with a non-negotiable QUILL principle, the collision is named and a
safer path is offered.

---

## Part One: Native RTF Editing as an Optional Surface

### The idea in one sentence

Let a writer open Preferences and choose their editing surface: keep the current
plain-text-first editor (a `wx.TextCtrl` over Markdown-style markup), or switch to
a native rich-text surface (a hosted `wx.RichTextCtrl`) where bold, italic,
headings, lists, and links are shown as formatted text rather than as markup
characters, and `.rtf` files open and save with no markup translation at all.

### Why this is different from what exists today

QUILL already supports RTF as a *file format*. The io-layer round-trip delivered
under EDS-21 reads RTF into Markdown-style markup and writes that markup back out
to valid RTF. See [quill/io/rtf.py](quill/io/rtf.py). That work is real and it
stays valuable. What it deliberately does not do is change the editing surface:
when you open an `.rtf` today, you edit markup in a plain-text control, and the
formatting is a translation, not a live object.

This proposal is about the surface itself. It introduces a second, opt-in editor
control where formatting is native and visible, and where RTF is the document's
true in-memory representation rather than a serialized export of markup.

### The headline tension, stated plainly

QUILL's founding principle is screen-reader-first, plain-text-first writing on
stock controls. The PRD and the repository conventions are explicit that the
writing path should use `wx.TextCtrl` and avoid custom-drawn or heavily
rich-formatted editor controls, because plain stock controls give the most
predictable, best-tested screen-reader experience across NVDA, JAWS, and
Narrator.

A `wx.RichTextCtrl` is a richer, more complex control. On Windows its
accessibility exposure is good but not identical to a plain edit control, and on
macOS and Linux the wx rich-text implementation behaves differently again. So the
core design question is not "can we host an RTF control" (we can) but "can we host
it without weakening the accessibility guarantee that defines QUILL." The answer
this proposal defends: yes, but only as an explicit, clearly-announced,
non-default choice, with the plain-text surface remaining the supported default
and the rich surface treated as a power-user mode with its own honest
accessibility disclosure.

### What "magical" looks like here

The magic is not the formatting. Every word processor has formatting. The magic
is making a rich surface feel as calm, legible, and screen-reader-honest as the
plain surface, and letting a writer move between the two without ever losing a
word.

- One document, two lenses. The same file can be viewed as markup or as live
  formatting, and switching lenses is a single command with a spoken summary of
  what changed and what, if anything, cannot survive the switch.
- A spoken formatting model. When the caret enters bold text, QUILL says "bold"
  the way it already announces actions, so formatting is something you hear, not
  only something sighted users see. This is the feature Microsoft Word and
  Ulysses never built for screen-reader users, and it is where QUILL can lead.
- Honest fidelity. Before any potentially lossy conversion, QUILL tells you in
  plain language what will be preserved and what will be flattened, and offers to
  keep a sidecar copy. No silent data loss, ever.

### Architecture: where this lives

QUILL's layering rules are strict. `quill/core` and `quill/io` must stay free of
`wx`. All widget code lives in `quill/ui` and `quill/platform`. This proposal
respects that boundary completely.

- A new editor-surface abstraction in `quill/ui` (for example
  `quill/ui/editor_surface.py`) defines a small protocol that both the plain-text
  surface and the rich surface implement: get and set the document text, get and
  set selection, apply and query inline formatting, report the caret context, and
  emit change and caret events. The rest of `quill/ui/main_frame.py` talks to the
  surface through this protocol instead of touching `self.editor` directly.
- The plain-text surface wraps today's `wx.TextCtrl` and is the default.
- The rich surface wraps a `wx.RichTextCtrl` and is selected only when the writer
  opts in.
- A pure, `wx`-free RTF formatting model can live in `quill/io` (extending the
  existing `quill/io/rtf.py`) so that conversion logic stays testable on Linux CI
  where `wx` cannot be imported. The control reads and writes through that model.

This is the single most important design decision: introduce a surface protocol
so the two controls are interchangeable from the application's point of view. Without
it, every one of the command surfaces below would need a branch for "is this the
rich control or the plain control." With it, each command asks the surface to do
the work and the surface knows how.

### Impact across every command surface

This is the heart of the proposal. The instruction to "keep in mind all command
surfaces that could be impacted" is taken literally. The table below inventories
the real call sites discovered in the codebase and rates the work each one needs
to support a rich surface. The plain-text surface keeps working unchanged in every
row; the rating describes the rich-surface effort.

Effort key: Low means the existing logic works through the surface protocol with
little change. Medium means the command needs a rich-aware path. High means the
command needs genuine new design because formatting changes its meaning.

| Command surface | Representative call sites | Rich-surface effort | Why |
| --- | --- | --- | --- |
| Editor creation and event binding | `_create_document_tab`, `_bind_editor_events`, `_on_editor_char_hook` in [quill/ui/main_frame.py](quill/ui/main_frame.py) | High | The control is constructed here; this is where the surface protocol and the two implementations plug in. Smart-quote and dash autoformat must be re-expressed against the rich surface. |
| Dirty-state and document buffer | `_on_text_changed`, `document.set_text(...)`, [quill/core/document.py](quill/core/document.py) | Medium | The buffer is no longer just a string. The Document model needs a representation that can hold formatting (or a paired markup-plus-format view) without `core` importing `wx`. |
| Selection (expand, shrink, select all) | selection helpers in [quill/ui/main_frame.py](quill/ui/main_frame.py), [quill/core/selection.py](quill/core/selection.py), [quill/core/set_ops.py](quill/core/set_ops.py) | Medium | Offsets differ between a markup string and a formatted run model; selection math must move behind the surface protocol. |
| Clipboard (cut, copy, paste) and context menu | editor context-menu wiring, `_copy_text_to_clipboard`, `copy_with_source`, [quill/platform/windows/clipboard.py](quill/platform/windows/clipboard.py), [quill/ui/main_frame_power_tools.py](quill/ui/main_frame_power_tools.py) | High | Rich paste must decide between formatted paste and paste-as-plain, and copy should offer RTF and plain flavors. This is also a security surface: pasted RTF must be sanitized. |
| Navigation (go to line, bookmarks, headings, outline) | `go_to_line`, `_navigate_heading`, `open_heading_organizer`, bookmark commands, [quill/core/outline.py](quill/core/outline.py), [quill/core/structure_nav.py](quill/core/structure_nav.py) | Medium | Headings are styles in a rich document, not `#` prefixes. Outline and heading navigation must read paragraph styles instead of scanning markup. |
| Find and replace | `find_text`, `_open_find_replace`, replace-all and replace-in-files, [quill/core/search.py](quill/core/search.py), [quill/core/regex_ops.py](quill/core/regex_ops.py) | Medium | Search runs over plain text extracted from the rich model; match offsets map back to formatted runs. Replace must preserve surrounding formatting. |
| Spellcheck | `open_spell_check_dialog`, as-you-type toggle, [quill/core/spellcheck.py](quill/core/spellcheck.py) | Medium | Word extraction and squiggle placement work on runs rather than a flat string; correction must not drop a run's formatting. |
| Markup and formatting commands | `format_bold`, `format_italic`, `format_heading`, heading-level commands, [quill/core/format_ops.py](quill/core/format_ops.py), [quill/core/autoformat.py](quill/core/autoformat.py) | High | On the plain surface these insert characters; on the rich surface they toggle native attributes. This is the clearest case for the surface protocol to own two implementations of one command. |
| Autosave | `_maybe_autosave`, [quill/core/autosave.py](quill/core/autosave.py) | Low | Autosave serializes the document; it needs the rich serializer but the trigger logic is unchanged. |
| Backups and recovery | `restore_backup`, [quill/core/backups.py](quill/core/backups.py), [quill/core/recovery.py](quill/core/recovery.py) | Medium | Backups must store enough to restore formatting; recovery must round-trip the rich representation atomically. |
| Undo and redo, including persistent undo | `undo`, `redo`, persistent-undo load and flush, [quill/core/undo_store.py](quill/core/undo_store.py) | High | The rich control has its own undo stack. Reconciling it with QUILL's persistent, cross-session undo is the subtlest engineering problem in the whole proposal. |
| Word count and statistics | `show_word_count`, [quill/core/metrics.py](quill/core/metrics.py) | Low | Metrics run on extracted plain text. |
| Read-aloud and text-to-speech | read-aloud commands and progress handlers, [quill/core/read_aloud.py](quill/core/read_aloud.py) | Medium | Read-aloud reads plain text; an opportunity is to announce formatting boundaries (entering and leaving bold) as a spoken cue. |
| Dictation | dictation commands and handlers, [quill/core/dictation.py](quill/core/dictation.py), [quill/platform/windows/dictation.py](quill/platform/windows/dictation.py) | Medium | Inserted dictated text must land in the rich model with the caret's current formatting. |
| Screen-reader announcements | [quill/core/announcements.py](quill/core/announcements.py), [quill/core/a11y_regions.py](quill/core/a11y_regions.py), [quill/platform/sr_announce.py](quill/platform/sr_announce.py) | High | The defining work. The announcement grammar must grow a vocabulary for formatting so the rich surface is as legible by ear as the plain surface. |
| Soft wrap | soft-wrap toggle and apply, [quill/core/wrap_ops.py](quill/core/wrap_ops.py) | Low | The rich control wraps natively; the toggle maps to a control style. |
| QUILL-key command system | [quill/ui/main_frame_quill_key.py](quill/ui/main_frame_quill_key.py), [quill/core/commands.py](quill/core/commands.py), [quill/core/keymap.py](quill/core/keymap.py) | Medium | Every editor command dispatched through the QUILL key must resolve against the active surface; the dispatch indirection already exists, so this is wiring, not redesign. |
| Dialog estate | Preferences hub, the new surface picker, [dialogs.md](dialogs.md), [tests/unit/ui/fixtures/dialog_inventory.json](tests/unit/ui/fixtures/dialog_inventory.json) | Medium | A surface-choice control and any fidelity-warning dialogs must be registered and classified under the DLG-3 dialog inventory gate. |

### Cross-cutting impacts beyond individual commands

- Settings and the Preferences hub. A new setting, for example
  `editor_surface` with values `plain` and `rich`, registered in
  [quill/core/settings_registry.py](quill/core/settings_registry.py) and surfaced
  as a category in the new Preferences hub. Switching surfaces should be possible
  per document and as a default.
- The Document model. Today the buffer is text. A rich surface needs a
  representation that carries formatting. The least invasive design keeps markup
  as the canonical text and attaches a formatting overlay, so plain-text features
  keep working on the canonical text and the rich control renders the overlay.
- Security. RTF is a historically dangerous format (object packager and embedded
  object abuse, remote image fetches). Any native RTF surface must parse defensively,
  refuse embedded executables and OLE objects, and honor QUILL's no-silent-network
  rule by never fetching a remote resource referenced in an RTF without explicit
  consent. This aligns with the existing egress-audit posture.
- Testing and CI. Because `wx` cannot be imported on Linux CI, the conversion and
  formatting model must live in `quill/io` with pure unit tests, and the control
  itself must be covered by the existing source-contract testing style plus the
  dialog-inventory and public-surface gates. The wx-freedom of `core` and `io`
  must not regress.
- Performance. The PRD sets latency budgets for the editor. A rich control over a
  large document has different performance characteristics; large-file behavior
  must be measured against the existing performance gates before this ships.

### A staged, honest delivery plan

1. Surface protocol first. Refactor `main_frame` so all editor access goes
   through an editor-surface protocol, with the existing `wx.TextCtrl` as the only
   implementation. No user-visible change. This de-risks everything that follows
   and is independently valuable.
2. Rich model in `quill/io`. Extend the RTF model so a formatted document can be
   represented, converted, and tested without `wx`.
3. Read-only rich preview. Ship a rich *view* of a document before a rich
   *editor*. Lower risk, immediately useful, and it exercises the announcement
   grammar for formatting.
4. Opt-in rich editor. Introduce the `wx.RichTextCtrl` surface behind a feature
   flag and the new setting, defaulting off, with a frank accessibility note in
   the picker.
5. Fidelity and safety polish. Lossy-conversion warnings, sidecar preservation,
   RTF sanitization, and the spoken formatting vocabulary.

### Opening files: the moment the design lives or dies

Everything above is plumbing. The place a writer actually meets this design is the
instant they open a file. If that moment is confusing ("why is this file showing
markup characters?" or "why did my headings turn into hash marks?"), the feature
fails no matter how elegant the internals are. So the open and save experience
deserves its own design, and it can be genuinely magical.

#### The one principle that prevents all confusion

The file chooses the surface, the writer can override, and QUILL always says which
lens you are in. Stated as three promises:

- A file opens in the surface that fits its nature, automatically.
- The writer can flip to the other lens at any time with one command, on a
  per-document basis, without losing a word.
- QUILL announces the active surface on open and on every switch, so a
  screen-reader user is never guessing.

That last promise is the accessibility heart of it. The status bar shows the lens
("Plain" or "Rich"), and the announcement grammar speaks it: "Opened report.rtf,
Rich text lens."

#### How each kind of file behaves on open

There is no separate "open as plain" versus "open as rich" file picker. There is
one Open command. QUILL inspects what you opened and does the obvious right thing,
then tells you what it did.

| You open | Default surface | What QUILL says and offers |
| --- | --- | --- |
| A plain text file (`.txt`, `.md`, `.markdown`, code) | Plain | Opens exactly as today. No change whatsoever for existing users. |
| An `.rtf` file, with the rich surface available | Rich | "Opened in Rich text lens." A single command flips to Plain to see or edit the underlying markup. |
| An `.rtf` file, with the rich surface turned off | Plain (markup) | Behaves like today's EDS-21 round-trip, and offers a one-key "Open in Rich text lens" if the writer wants formatting. |
| A rich format QUILL can import (`.docx`, `.odt`, `.pages`) | Plain by default, Rich if opted in | QUILL says how it imported and whether formatting was simplified, with a link to view details. |
| A non-text file (`.pdf`, image for OCR, spreadsheet) | Plain (extracted text) | Unchanged; these are read or extracted into text and never pretend to be rich documents. |

The key insight: the writer's default-surface preference is a *fallback*, not a
mandate. An `.rtf` is inherently a rich document, so it opens rich when rich is
available, even if the writer's default is plain, because that is the least
surprising thing. The preference only decides the ambiguous cases.

#### Making the choice effortless, not a chore

A few touches turn a potential annoyance into something that feels considerate:

- Remember per file. If you opened `journal.rtf` in Plain last time, QUILL
  reopens it in Plain and says so. The decision is sticky per document, stored in
  the same schema-validated JSON used for other per-document state, so you only
  ever decide once.
- One command to flip lenses. A single QUILL-key command, "Switch editing lens,"
  toggles Plain and Rich for the current document, announces the new lens, and
  keeps the caret on the same word. No dialog, no reload.
- No dead ends. Every flip is reversible and lossless within a session, because
  the canonical markup-plus-overlay model holds both views at once. You can move
  back and forth freely while you decide which you prefer for this file.
- Speak the consequence before a lossy save, never after. If saving the current
  lens to the chosen file type would drop something (for example, saving a richly
  formatted document down to `.txt`), QUILL says exactly what will be flattened and
  offers to keep a sidecar copy in a faithful format. This reuses the no-silent-loss
  promise from the fidelity stage.

#### Saving: the mirror image, equally calm

Saving follows the same "least surprise, always announced" rule.

- Save keeps the file's own format. An `.rtf` saves as RTF, a `.md` saves as
  Markdown, regardless of which lens you were editing in, because the lens is a
  *view*, not the file's identity.
- Save As is where format genuinely changes, and that is the right place for a
  clear, accessible format picker with a spoken fidelity note ("Saving as plain
  text will remove bold, italic, and headings. Keep a Rich copy too?").
- The dirty-state, autosave, and backup machinery all operate on the canonical
  model, so switching lenses never marks a document dirty by itself and never
  risks a recovery that loses formatting.

#### Why this is magical and not just tolerable

The ordinary version of this feature forces a mode decision on the user and then
punishes wrong guesses with lost formatting. The QUILL version removes the
decision in the common cases, makes it one reversible keystroke in the rare cases,
keeps both views of the document alive at once so nothing is ever lost, and speaks
every state and consequence aloud so a blind writer navigates it with exactly the
same confidence as a sighted one. A writer opens their file and it simply looks
right, sounds right, and saves right. That is the magic: the two surfaces feel like
one calm editor that happens to know when to show formatting.

### Recommendation

Pursue it, but as a protocol-first refactor that delivers value at every stage,
and keep the plain-text surface the default and the fully-supported path. The
rich surface should be a celebrated power-user choice, not a replacement, and its
accessibility story should be told honestly at the moment of opt-in. Done this
way, QUILL becomes the rare app that offers live rich editing and still treats
plain-text, screen-reader-first writing as first class. That is the magic: not
catching up to word processors, but giving blind and low-vision writers a rich
surface that finally speaks formatting out loud.

---

## Part Two: Competitive Study, Ulysses

### Why Ulysses is the right mirror for QUILL

Ulysses is a mature, respected, markup-first writing app for Mac, iPad, and
iPhone, in active development since 2003 and an Apple Design Award winner. Like
QUILL, it bets on markup rather than visual rich editing, keeps the writer's
hands on the keyboard, and produces clean text as output. That shared philosophy
makes it the most instructive comparison: where Ulysses is strong, it validates
QUILL's direction; where QUILL is strong, it shows QUILL's distinct advantage.

The comparison below reflects Ulysses as described on its official site and
feature pages.

### Side-by-side at a glance

| Dimension | Ulysses | QUILL |
| --- | --- | --- |
| Core philosophy | Markup-first, distraction-free, keyboard-driven | Markup-first, screen-reader-first, keyboard-driven |
| Platforms | Mac, iPad, iPhone (Apple only) | Windows first, with a macOS path |
| Accessibility stance | General Apple platform accessibility | Accessibility is the product thesis: NVDA, JAWS, Narrator parity |
| Library and organization | Unified library, groups, filters, keywords | Tabs, profiles, bookmarks, headings outline, quick navigation |
| Writing goals | Deadlines, daily goals, character and word targets | Word count and statistics |
| Proofreading | Built-in grammar and style check, 20-plus languages | Spellcheck, with AI assistance as explicit opt-in |
| Export and publishing | PDF, Word, ebook, plus WordPress, Ghost, Medium, Micro.blog | Pandoc-backed multi-format export and conversion |
| Sync | Seamless first-party cloud sync across Apple devices | Local-first storage, privacy-first |
| Privacy posture | Cloud library by design | No silent network calls, explicit consent per action |
| AI | Limited | Opt-in assistant, branchable sessions, local-first options |

### What Ulysses does that QUILL can learn from

These are the ideas worth bringing into QUILL, each reframed through QUILL's
accessibility-first, privacy-first, plain-text-first lens so it arrives as a QUILL
feature rather than a transplant.

#### Writing goals you can hear

Ulysses lets a writer set a deadline and a daily or per-document target and watch
progress fill toward it. QUILL has word count and statistics but not goals as a
first-class, motivating object. The magical QUILL version is a *spoken,
glanceable* goal: set a target by voice or command, and QUILL announces progress
on demand and at milestones ("halfway to your 800 words", "goal met") through the
existing announcement grammar, with an optional status-bar field. This turns a
visual progress bar into something a blind writer experiences exactly as richly as
a sighted one.

#### Keywords as a navigation and filtering layer

Ulysses attaches keywords to sheets and filters the library by them. QUILL has
headings, bookmarks, and profiles, but not lightweight, user-defined tags that cut
across documents. A QUILL keyword system, stored in schema-validated JSON and fully
keyboard and screen-reader navigable, would let a writer mark passages or files
("research", "todo", "chapter-3") and then jump or filter by tag through the quick
navigation surface. The magic is making tags audible and command-driven rather
than a mouse-driven sidebar.

#### A unified, navigable library

Ulysses keeps every text in one searchable library that syncs everywhere. QUILL is
file-and-tab oriented. Without abandoning local-first files, QUILL could offer an
optional library *view*: a single accessible list or tree across a writer's
project folders, with type-ahead, keywords, and goals visible, built from the same
stock-control, first-letter-navigable patterns QUILL already favors. It is the
Edge-style list pattern QUILL just adopted for Preferences, applied to a writer's
whole corpus.

#### Built-in style and grammar assistance, on QUILL's terms

Ulysses ships an integrated proofreader across many languages. QUILL has
spellcheck and an opt-in AI assistant. The recommendation is not to bolt on a
cloud grammar service; it is to make style and grammar suggestions a *local-first,
consent-gated* capability that announces each suggestion and never sends text
anywhere without explicit per-action consent, consistent with QUILL's egress rules.
Ulysses proves writers want this; QUILL can offer it without surrendering privacy.

#### Frictionless, beautiful export with live preview

Ulysses turns text into polished PDF, Word, and ebooks with on-the-fly style
switching and live preview. QUILL already has strong Pandoc-backed export. The
borrowable idea is the *experience*: a single command that previews the chosen
output format and lets the writer switch styles before exporting, with the preview
itself accessible. QUILL's advantage is that its preview can be screen-reader
legible, which a purely visual preview is not.

#### Distraction-free focus as an announced mode

Ulysses is built around a calm, distraction-free interface. QUILL can offer a
focus mode that does more than hide chrome: it can announce entry and exit, mute
non-essential notifications, and optionally narrow read-aloud to the current
paragraph, making focus a multi-sensory state rather than a visual one.

### What QUILL should deliberately not copy

- Apple-only reach. Ulysses is Apple-exclusive. QUILL's Windows-first,
  screen-reader-first mission is its differentiation; that should not change to
  chase Ulysses' aesthetic.
- Cloud-library-by-default. Ulysses assumes a synced cloud library. QUILL's
  local-first, no-silent-network posture is a feature, not a gap. Any library or
  sync work must stay opt-in and consent-gated.
- Subscription-shaped feature gating. Pricing strategy is out of scope here, but
  QUILL should not let a feature's design be distorted by a paywall the way some
  Ulysses capabilities are.

### Where QUILL already beats Ulysses

It is worth naming QUILL's lead so the roadmap protects it.

- Screen-reader-first design. Ulysses inherits platform accessibility; QUILL is
  engineered around it, with a shared announcement grammar and parity across NVDA,
  JAWS, and Narrator.
- Privacy by architecture. No silent network calls and explicit per-action
  consent are guarantees Ulysses does not make.
- Branchable AI writing sessions. QUILL's resumable, forkable session tree is a
  genuinely novel capability with no Ulysses equivalent.
- Windows reach. QUILL serves a platform and an audience Ulysses does not.

### Recommended priorities from this study

In rough order of value-to-effort for QUILL's audience:

1. Spoken writing goals, building on the existing metrics and announcement
   surfaces. High value, modest effort, distinctly QUILL.
2. Keyword tags with audible navigation and filtering, reusing the quick
   navigation and schema-validated JSON storage patterns.
3. An optional accessible library view across project folders, reusing the
   first-letter-navigable list pattern.
4. Consent-gated, local-first style and grammar suggestions that announce each
   finding.
5. An accessible export preview with on-the-fly style switching.
6. An announced, multi-sensory focus mode.

Each of these takes a proven Ulysses idea and re-expresses it as something a blind
or low-vision writer experiences fully, which is exactly the territory where QUILL
should aim to be not just competitive but singular.

---

## Part Three: Compose Mode, a Workshop for Assembling Documents

### The idea in one sentence

Add an optional Compose mode where a document is built from a list of parts (call
them segments, QUILL's answer to Ulysses sheets), each part holding a chunk of
writing or a pulled-in source, where the writer reorders parts, promotes and
demotes their heading levels, and merges them into one finished document, while a
live HTML preview shows the assembled whole in real time, and the parts can be
written in Markdown, RTF, or HTML.

This is the writing-as-architecture idea that David Hewson praised in Ulysses
("shuffle around the many different parts and scenes"), rebuilt so a screen-reader
user can architect a document by ear with exactly the same fluency as by eye.

### What a writer actually does in Compose mode

Picture a long piece: a report, a thesis chapter, a book section. Instead of one
unbroken file, the writer sees an accessible list of parts:

- Introduction
- Background (pulled from `research-notes.md`)
- Method
- A quoted source (pulled from an `.rtf` a colleague sent)
- Findings
- Conclusion

Each part is a real, editable unit. The writer can:

- Reorder parts. Move "Method" above "Background" and the whole document
  reflows, the preview updates, and QUILL announces "Moved Method to position 3 of
  6."
- Re-level headings. Promote a part so its heading becomes a top-level section,
  or demote it so it nests under the part above. QUILL announces "Background is
  now heading level 2, nested under Introduction."
- Pull sources together. Add a part that references another file (Markdown, RTF,
  or HTML) so material from many places is gathered into one outline without
  copy-paste drift. The source can be embedded (frozen copy) or linked (kept in
  sync), and QUILL says which.
- Mix formats per part. One part can be Markdown, the next RTF, the next HTML.
  Compose mode normalizes them through QUILL's existing conversion layer so the
  assembled document is coherent.
- Merge to a single document. When the architecture is right, "Flatten to
  document" produces one ordinary file in the writer's chosen format, with heading
  levels already correct.

### The structure tree: the document as a navigable outline

A flat list of parts is good; a tree is magical, and it is the natural fit for
QUILL because the codebase already proves the pattern. QUILL ships an accessible
tree-navigator (`_NavigatorNode` and `_show_tree_navigator` in
[quill/ui/main_frame.py](quill/ui/main_frame.py)) used today for the heading
outline, EPUB chapters, and the misspelling list, and a tree-based *structure
editor* (the YAML editor) that already performs add-child, add-sibling, rename,
and delete on a `wx.TreeCtrl` with a live preview beside it. Compose mode should
reuse this exact, battle-tested pattern rather than invent a new surface.

Represented as a tree, the part list becomes the document's true shape:

- Introduction
- Method
  - Participants
  - Materials
- Background
- Findings
  - Quantitative
  - Quoted source (from a colleague's RTF)
- Conclusion

A `wx.TreeCtrl` is a first-class accessible control (it sits in the dialog
contract's preferred-focus list), and on Windows, macOS, and Linux it gives blind
writers what sighted writers get from an indented outline: nesting they can feel.

- Arrow keys walk the structure. Up and down move between parts, right expands a
  part to hear its children, left collapses to hear just the section. Screen
  readers announce level and position natively ("Method, level 1, expanded, 2 of
  6; Participants, level 2, 1 of 2").
- Collapsing a branch hides a whole sub-section so a writer can think at the
  chapter level, then expand to drop into detail, the outliner's core joy.
- The tree is the document. Reordering a node reorders the prose; promoting a node
  re-levels its heading; moving a parent carries its children. There is no
  separate outline to drift out of sync.
- Each node speaks its essentials on focus: title, heading level, child count,
  word count, format (Markdown, RTF, or HTML), and link-or-embedded state, all in
  the shared announcement grammar.

The rich context menu described next hangs directly off this tree, and the live
HTML preview sits beside it exactly as the YAML editor places a preview beside its
structure tree, so moving a node and hearing the reflowed result is one gesture.

### The live HTML preview, made accessible

A real-time HTML preview is the visual half of the magic. The accessible half is
making that preview meaningful without sight.

- The preview renders the assembled document as HTML and updates as parts move or
  change, reusing QUILL's existing HTML preview path.
- Crucially, the preview is screen-reader legible: it is presented as structured,
  navigable text (headings, lists, links exposed as real semantics), not as an
  opaque image of a page, so a screen-reader user can read the assembled result by
  heading and by element just like the final document.
- A spoken structure summary is one keystroke away: "6 parts, 4 top-level
  headings, estimated 2,300 words, reading order: Introduction, Method,
  Background..." so the writer hears the shape of the whole before diving in.
- Preview and parts stay in sync both ways: jumping to a heading in the preview
  offers to jump to the part that produced it, closing the loop between the
  architecture view and the reading view.

### Why this is delightful, not just powerful

- Nothing is lost while you experiment. Reordering and re-leveling operate on the
  part list, never by destructively cutting and pasting text, so every arrangement
  is reversible and the writer can try three structures in a minute.
- The outline is the document. There is no separate, drifting outline pane to
  maintain; the part list *is* the outline, and editing the outline edits the
  document.
- It speaks architecture. Every structural action has a spoken outcome in the
  shared announcement grammar, so "move this section earlier" is a confident,
  audible act rather than a fragile drag.
- It meets writers where their material is. Markdown notes, an RTF from a
  colleague, an HTML snippet from the web can all become parts without first being
  converted by hand.

### The right-click that builds a document: a rich, spoken context menu

Reordering and re-leveling should not require remembering commands. The fastest,
most direct way to architect a document is to act on the part you are standing on,
and the context menu is where that lives. In Compose mode, invoking the context
menu on a part (by right-click, by the keyboard context-menu key, or by QUILL's
own context command) opens a structure menu that is the command center for the
whole assembly. Every item is keyboard reachable, every item announces its
outcome, and destructive items confirm.

The menu is organized so the most common architectural moves are at the top:

| Menu item | What it does | What QUILL announces |
| --- | --- | --- |
| Move Up / Move Down | Swaps this part with its neighbor | "Moved Method up to position 2 of 6." |
| Move to Top / Move to Bottom | Jumps this part to the start or end | "Moved Conclusion to the end, position 6 of 6." |
| Move to Position... | Accessible entry to type or pick an exact slot | "Moved Background to position 3 of 6." |
| Promote (heading level up) | Raises this part's heading one level, outdenting it | "Background is now heading level 1, a top-level section." |
| Demote (heading level down) | Lowers this part's heading one level, nesting it | "Background is now heading level 3, nested under Method." |
| Make Top-Level Section | Sets this part to heading level 1 in one step | "Introduction is now a top-level section." |
| Group Under Previous | Nests this part (and re-levels it) beneath the part above | "Grouped Findings under Method." |
| Promote With Children / Demote With Children | Re-levels this part and everything nested under it together | "Promoted Method and its 3 sub-parts." |
| Change Format... | Switches this part between Markdown, RTF, and HTML | "Changed Background to HTML." |
| Convert Link to Embedded Copy | Freezes a linked source so it stops tracking the original | "Background is now an embedded copy." |
| Refresh Linked Source | Re-pulls a linked source's latest content | "Refreshed Background from research-notes.md." |
| Split Part Here / Merge With Previous | Breaks one part into two at the caret, or fuses two | "Split into Method and Method, part 2." |
| Duplicate Part | Copies the part as a new sibling | "Duplicated Findings." |
| Rename Part | Accessible text entry for the part's outline label | "Renamed to Literature Review." |
| Add Keyword to Part... | Tags this part (see Part Four) | "Added keyword research to this part." |
| Preview This Part | Jumps the live HTML preview to this part | "Previewing Findings." |
| Flatten From Here... | Merges this part and those after it into a document | spoken summary of the flattened result |
| Remove Part | Deletes the part (with confirm) | "Removed Background. 5 parts remain." |

#### What makes this context menu magical rather than ordinary

- It speaks position and consequence, always. Every move and re-level reports the
  new position out of the total and the resulting heading relationship, so a
  screen-reader user never has to re-read the list to discover what happened. The
  menu is a place where you act and immediately *hear* the new shape.
- It re-levels structurally, not cosmetically. Promote and Demote understand
  nesting: "Promote With Children" lifts an entire subtree so a writer can move a
  whole sub-section up a level in one act, and QUILL announces how many parts moved
  with it. This is the difference between editing an outline and merely nudging
  text.
- It is context-aware. Items that cannot apply are absent or clearly disabled with
  a spoken reason: "Move Up unavailable, Introduction is already first." "Refresh
  Linked Source unavailable, this part is an embedded copy." No dead clicks, no
  silent no-ops.
- It mirrors keyboard commands exactly. Every menu item has a QUILL-key binding so
  power users never need the menu, and the menu never hides a capability the
  keyboard lacks. The context menu and the command system are two doors to one
  room.
- It keeps focus sane. After a move, focus stays on the part that moved (now in its
  new position) so repeated presses of "Move Up" walk a part smoothly toward the
  top, each step announced, exactly the predictable behavior the repository's
  dialog and focus rules require.
- It confirms only what is destructive. Reordering and re-leveling are instantly
  reversible and never prompt; Remove Part and a flatten that would overwrite a
  file confirm through a native accessible dialog. Friction lands only where loss
  is possible.

#### Beyond the single part: acting on a selection

The magic compounds when the writer selects several parts in the list. The same
context menu then operates on the whole set, spoken as a set: "Move 3 parts up,"
"Demote 3 parts," "Group 3 parts under Introduction," "Add keyword research to 3
parts." A scattered draft becomes a structured manuscript in a handful of audible,
reversible gestures, all from the one context menu every editor estate already
makes feel familiar.

This context menu must, like all QUILL dialogs and menus, be registered and
classified under the DLG-3 dialog and menu estate, with no menu items mutated while
the menu is open (deferring label and enable updates until close), per the
repository's dialog and menu lessons.

### How Compose mode fits QUILL's architecture

This respects the same boundaries as the rest of this document.

- The part-list model, reordering, heading-level math, and the flatten-to-document
  logic are pure and live in `quill/core` and `quill/io`, free of `wx` and fully
  unit-testable on Linux CI. They build directly on the existing outline, heading,
  and conversion modules ([quill/core/outline.py](quill/core/outline.py),
  [quill/core/heading_styles.py](quill/core/heading_styles.py),
  [quill/io/pandoc.py](quill/io/pandoc.py), and the RTF and HTML io paths).
- The Compose surface itself (the accessible part list, the editor for the
  selected part, and the live preview) lives in `quill/ui`, built from stock,
  first-letter-navigable list controls, the same patterns QUILL already favors.
- It honors FeatureManager as an opt-in mode, the dialog-inventory gate for any
  new dialogs, and the no-silent-network rule for any linked remote source.
- A composition is persisted as schema-validated JSON (the ordered part list with
  each part's source, format, embed-or-link choice, and heading level), with atomic
  writes and backup or recovery parity, so an assembly is as robust as any other
  QUILL document.

### Honest constraints

- Mixed-format flattening is only as faithful as the conversions beneath it; the
  same no-silent-loss warnings from Part One apply when a part's formatting cannot
  survive the chosen output format.
- A real-time preview of a large multi-part document must respect QUILL's
  performance budgets; the preview should update incrementally rather than
  re-rendering the world on every keystroke.
- Linked (live) sources introduce freshness and trust questions; linked external
  content must follow the existing untrusted-location and egress-consent rules.

---

## Part Four: Accessible Keywords for Screen-Reader Users

Keywords (tags) recur through this document as a borrowed Ulysses strength. They
are only worth building if they are fully usable by ear, so they deserve their own
design. The goal: tagging and tag-navigation that a screen-reader user performs as
fluently as a sighted user clicks a colored label.

### What a keyword is in QUILL

A keyword is a short, user-defined label ("research", "todo", "chapter-3",
"verify") attached to a whole document or to a specific part or passage. Keywords
are stored in schema-validated JSON alongside other per-document state, never
embedded invisibly in the prose, so they never pollute the text a screen reader
reads.

### Assigning keywords by ear

- A single command, "Add keyword," opens an accessible entry with type-ahead over
  existing keywords, so the writer reuses "research" rather than inventing
  "reserach". The field announces matches as they narrow.
- Assigning announces the outcome: "Added keyword research to this section. This
  section now has two keywords: research, verify." The writer always hears the
  resulting state, not just the action.
- Removing is symmetric and equally spoken: "Removed todo. One keyword remains:
  research."
- Keywords on a passage are anchored to that passage's position, and QUILL speaks
  where they live ("keyword verify spans the selected sentence") so they are never
  invisible floating state.

### Hearing which keywords are present

The hardest part of tags for a screen-reader user is usually discovery: sighted
users see colored chips at a glance. QUILL replaces the glance with sound and
structure.

- On entering a tagged document or part, QUILL can announce its keywords as part
  of the context, configurably, for example "Findings, keywords: research,
  verify."
- A "Read keywords here" command speaks the keywords at the caret on demand,
  so the information is available the instant it is wanted and silent when it is
  not.
- A status-bar field can carry the current location's keyword count, and reading
  that field aloud is already a supported QUILL action.

### Navigating by keyword

This is where keywords become a navigation superpower rather than mere labels.

- "Go to keyword" opens an accessible, first-letter-navigable list of all
  keywords with their occurrence counts ("research, 7; todo, 3; verify, 2").
  Choosing one lists every place it appears, each entry spoken with its document,
  section, and a short context snippet.
- "Next keyword" and "Previous keyword" jump between occurrences of a chosen tag
  the way heading navigation jumps between headings, each landing announced with
  its surrounding context.
- A keyword filter can scope the accessible library view and Compose mode part
  list to just the tagged items ("showing 7 parts tagged research"), turning a
  sprawling project into a focused working set, entirely by keyboard and entirely
  spoken.

### Why this is the accessible version Ulysses never built

Ulysses keywords are fundamentally visual: chips you scan and click. QUILL's
keywords are spoken objects you can add, hear, filter, and jump through without
ever seeing them. Every keyword action has an audible outcome, every keyword
location is announced rather than implied, and discovery is a command away instead
of a visual scan. That is the through-line of this entire document applied once
more: take a feature the industry built for the eye and make QUILL the place where
it finally speaks.

---

## Part Five: Embedded Grammar Checking, and How It Understands Language

Grammar checking is the most technically ambitious idea in this document, and the
honest framing matters: spelling asks "is this token a word?" while grammar asks
"is this sentence well-formed, and why?" The second question requires the software
to understand the *structure* of language, not just a wordlist. This part explains
how QUILL would gain that understanding, how it would surface findings through the
same accessible machinery QUILL already uses for spelling, and where the real
complexity and the honest limits lie.

### Spelling is the proven template to build on

QUILL already has the right shape. [quill/core/spellcheck.py](quill/core/spellcheck.py)
is a pure, `wx`-free pipeline: `list_misspellings` returns typed `Misspelling`
records with `start` and `end` offsets, `next_misspelling` and
`previous_misspelling` walk them efficiently from the caret, `misspelling_at_position`
identifies the issue under the cursor, and `suggest_words` offers fixes. The UI
layer turns those records into navigation, a context menu, and the misspelling tree
navigator. Grammar checking should mirror this contract exactly: a pure core engine
that returns typed issue records with offsets, a category, an explanation, and
suggested rewrites, and a UI that reuses QUILL's existing navigation, dialog, and
announcement surfaces. If grammar issues look like richer misspellings to the rest
of the app, the integration cost collapses.

### How a computer understands grammar and parts of speech

This is the core of your question. There is no single trick; there is a pipeline,
and QUILL can choose how far down it to go based on cost and accuracy. Each stage
turns raw text into more structure than the last.

1. Tokenization and sentence segmentation. Split text into sentences and words,
   handling abbreviations, decimals, and punctuation. QUILL already has word and
   line tokenizing patterns to build on.
2. Part-of-speech tagging. Label each token with its grammatical category: noun,
   verb, adjective, determiner, preposition, and finer tags (singular noun, past
   tense verb, comparative adjective). This is how the software knows that in
   "the dog runs," "dog" is a singular noun and "runs" is a singular present-tense
   verb, which is what lets it judge subject-verb agreement. POS tagging is a
   solved, well-understood task: a tagger is trained on large hand-labeled corpora
   and learns the probability of each tag given the word and its neighbors.
3. Morphological analysis. Determine number (singular or plural), tense, and
   person from word forms, so the checker can compare "dog/dogs" or "run/runs/ran."
4. Shallow or full parsing. Group tagged words into phrases (noun phrase, verb
   phrase) and, in fuller form, build a dependency tree linking each word to the
   word it modifies or agrees with. The dependency link between subject and verb is
   precisely what an agreement rule inspects.
5. Rule and model checking. With tags and structure in hand, the checker applies
   rules ("a singular subject takes a singular verb"; "this preposition does not
   fit this verb") and statistical signals (this n-gram is improbable) to flag
   likely errors and propose fixes.

The crucial idea: parts of speech are the bridge. Once every word carries an
accurate grammatical tag and the words are linked into phrases, most common grammar
checks become tractable rules over that tagged structure rather than guesses over
raw characters.

### Don't build the engine, adopt one: the open-source options

The first instinct, a hand-written ruleset, is a trap. Real grammar checking is
years of linguistic work, and several mature open-source engines already exist.
The honest job is to pick the one whose language understanding, license, runtime,
and privacy posture fit QUILL, then wrap it. The survey below reflects each
project as of mid-2026.

| Engine | Language stack | License | Offline and private | Coverage | Honest fit for QUILL |
| --- | --- | --- | --- | --- | --- |
| Harper (Automattic) | Rust core, callable from Python via a PyO3 binding | Apache-2.0 | Yes, fully local by design | English only today; real POS tagging (its `harper-brill` tagger) and many rules | Strongest fit. No Java, no VM, milliseconds per lint, roughly one-fiftieth of LanguageTool's memory. Cost: a compiled native dependency to bundle and sign per platform, and English-only for now. |
| LanguageTool | Java engine, driven from Python by `language_tool_python` | Engine LGPL 2.1+; Python wrapper GPL-3.0 | Yes, but only via a bundled local Java server; the public-API mode sends text off device and must never be used in QUILL | 25-plus languages, thousands of rules, optional large n-gram data | Most complete and multilingual, but requires bundling a Java 17+ runtime and managing a local server subprocess, a heavy footprint for a Python and wxPython app. The GPL-3.0 wrapper and remote-API default are both cautions. |
| spaCy | Pure Python and Cython | MIT | Yes, fully local | Excellent POS tagging and dependency parsing, many languages | Not a grammar checker; it is the structural toolkit you would build rules on top of. Useful if QUILL ever wants its own multilingual structural layer, but it is a build-it-yourself path, not a finished checker. |
| proselint | Pure Python | BSD | Yes, fully local | Style and usage advice, not true grammar | Lightweight and trivially embeddable, but it lints style, not subject-verb agreement; a complement, not the engine. |
| Consent-gated AI | QUILL's existing AI path | n/a | No, sends text off device | Broadest coverage and fluent rewrites | Best raw coverage and style help, but it must be strictly opt-in per QUILL's no-silent-network rule; latency, cost, and non-determinism apply. |

A note on what each actually understands. Harper, LanguageTool, and spaCy all do
genuine part-of-speech tagging and some structural analysis, which is what lets
them catch agreement and tense errors rather than just typos. proselint does not;
it pattern-matches style. A hand-rolled QUILL ruleset would sit below all of them
and is not worth building when Harper exists.

### The recommended path: Harper first, with honest caveats

For QUILL specifically, the leading candidate is Harper. It is open source
(Apache-2.0), offline and privacy-first by design, fast and light enough to run
live in an editor, and it does real POS tagging, which is exactly the
parts-of-speech understanding the checker needs. Crucially for QUILL, it needs no
Java and no virtual machine.

The caveats must be stated plainly, because they drive the engineering:

- Harper is written in Rust, not Python. It is callable from Python through a
  PyO3 binding (`harper-python`, published on crates.io under Apache-2.0), but
  under the hood QUILL would load a compiled native extension and ship a
  per-platform wheel or binary that has to be built and code-signed alongside the
  app. This is the same class of work as any native dependency, just without a
  JVM.
- At the time of writing, the `harper-python` crate is confirmed, but a prebuilt
  PyPI wheel under that name could not be verified; QUILL should confirm the exact
  Python distribution, its API, and platform wheel availability before depending on
  it, and be ready to build the binding from the Rust crate if needed.
- Harper is English-only today. Writers needing other languages would fall back to
  the (heavier, multilingual) LanguageTool engine or to consent-gated AI.

The staged recommendation, then, is engine-led rather than rule-led: wrap Harper
as the default local, private grammar engine behind a feature flag; offer
LanguageTool as an opt-in heavyweight for writers who need its breadth of
languages and rules, bundling its Java server only when enabled; and expose deep,
fluent AI grammar only through QUILL's existing consent gate. spaCy stays in
reserve as the toolkit if QUILL ever wants to grow its own multilingual structural
checks.

### Why this is genuinely complex, stated plainly

You called grammar complex, and that is correct. The honest difficulties:

- Ambiguity is everywhere. "Time flies" can be a noun and verb or an adjective and
  noun; many words are several parts of speech, and the tagger must use context.
- Real grammar needs structure, not just words. Subject-verb agreement can span a
  long clause ("The list of items *is* on the desk," not "are"), so a checker that
  ignores phrase structure gets it wrong.
- False positives erode trust fast. A grammar checker that nags about correct
  sentences is worse than none; tuning for precision over recall matters more than
  raw coverage.
- Language and dialect specificity. Rules and models are per-language, and even
  within English the conventions differ; QUILL must let the writer set the variety.
- Performance under live editing. Re-checking a large document on every keystroke
  is infeasible; the engine must check incrementally around edits, exactly as the
  spelling scanner already works outward from the caret.

### Surfacing grammar through QUILL's existing accessible machinery

Here the earlier request for "keyboard commands, a dialog, and more to help with
all of the document interaction" is answered directly. Grammar reuses every
spelling surface, so a screen-reader user already knows how to drive it.

- Keyboard commands. "Next grammar issue" and "Previous grammar issue" walk
  findings from the caret, each landing spoken with its category and a short
  explanation ("subject-verb agreement, line 12: the subject *list* is singular,
  so use *is*"). "Explain grammar issue here" speaks the full rationale on demand.
  "Apply suggested fix" and "Apply fix and continue" accept a rewrite and move on.
  "Ignore once" and "Ignore this rule" tune the noise. All bind through the
  QUILL-key system and appear in the command palette.
- A grammar dialog. A dedicated, accessible review dialog (native or QUILL's web
  surface, registered under the DLG-3 dialog estate) walks issues one at a time
  with the sentence in context, the category, the plain-language explanation, the
  parts of speech it is reasoning about ("*list*: singular noun; *are*: plural
  verb"), and a list of suggested rewrites the writer can choose from, with Apply,
  Skip, Ignore, and Ignore Rule. This mirrors the existing spell-check dialog so it
  is instantly familiar.
- A grammar tree navigator. The same `_NavigatorNode` tree that lists misspellings
  lists grammar findings grouped by category (Agreement, Tense, Punctuation, Word
  choice), each node spoken with its location and an excerpt, each Enter jumping to
  the occurrence. A writer can survey every structural concern in the document by
  ear, then fix them in order.
- As-you-type, like spelling. An optional live mode flags issues incrementally
  around edits and announces them with the restraint QUILL already applies to
  spelling, never interrupting flow, always available on demand.
- The context menu. Right-clicking a flagged span offers the suggested fixes,
  Explain, Ignore, and Ignore Rule inline, exactly as spelling suggestions appear
  in the editor context menu today.
- Honest, spoken explanations. The defining QUILL difference: every finding is
  explained in plain language and, when useful, names the parts of speech it
  reasoned about, so a writer does not just hear *that* something is wrong but
  *why*, and learns from it. That is grammar checking that teaches, by ear.

### Architecture and where it lives

- The grammar layer is wrapped behind a pure, `wx`-free adapter in `quill/core`
  (for example `quill/core/grammar.py`) that returns typed issue records exactly as
  `spellcheck.py` returns `Misspelling` records, so the rest of the app never sees
  which engine produced a finding. Swapping Harper for LanguageTool or AI is an
  adapter change, not an app change.
- The engine itself (the Harper native binding, or an optional bundled
  LanguageTool server) lives at the platform boundary, loaded lazily with the same
  cache-locking discipline the spelling wordlist uses and with background preload
  so the first check never stalls the editor. Because the engine is native and
  cannot be imported on Linux CI, the adapter is tested against a fake engine, and
  the record-shaping logic stays pure and fully unit-tested, mirroring how QUILL
  already keeps wx and other heavy dependencies out of `core` tests.
- All UI (commands, dialog, tree navigator, context menu, announcements) lives in
  `quill/ui` and reuses existing surfaces, so the new code is mostly the adapter
  plus thin wiring.
- The optional AI engine routes only through the existing consent-gated AI path and
  the egress audit; no grammar engine may make a silent outbound call, which also
  means LanguageTool's public-API mode is forbidden and only its bundled local
  server is permitted.
- Feature-flagged through FeatureManager so grammar (and each engine) can be
  enabled per profile.

### Recommendation

Do not hand-roll a grammar checker; adopt a real engine and treat grammar as
"spelling, with structure." The leading choice for QUILL is Harper: open source
(Apache-2.0), offline, privacy-first, fast enough to run live, real POS tagging,
and no Java. Accept its honest costs (a Rust native binding to package per
platform, English-only for now, and a Python distribution to verify) and wrap it
behind a pure `quill/core` adapter that emits the same typed records as
spellcheck. Offer LanguageTool as an opt-in multilingual heavyweight (bundled
local Java server only, never its remote API), keep spaCy in reserve as a
structural toolkit, and expose fluent AI grammar only through QUILL's existing
consent gate. Whichever engine answers, make the finding *speak its reasoning*,
parts of speech included, so QUILL becomes not just a grammar checker but the rare
one a blind writer can fully hear, interrogate, and learn from.

---

## Closing note

Part One argues QUILL can host a rich surface without betraying its plain-text,
screen-reader-first heart, provided it refactors to an editor-surface protocol
first and keeps the rich control an honest, opt-in power mode. Part Two argues the
best ideas in the category's most admired markup app, Ulysses, can each be brought
into QUILL in a form that is more accessible than the original. Part Three proposes
Compose mode, a workshop that assembles a document from reorderable, re-levelable
parts across Markdown, RTF, and HTML with a live, screen-reader-legible HTML
preview and a rich spoken context menu for architecting structure by ear. Part
Four designs keywords as spoken objects a writer can add, hear, filter, and jump
through without ever seeing a chip. Part Five shows how grammar checking can
understand parts of speech and sentence structure, in tiers from a private local
ruleset to opt-in AI, and surface every finding, reasoning included, through the
same accessible commands, dialog, and tree QUILL already uses for spelling.

The throughline of all five is one ambition: take features the rest of the
industry built for the eye, and make QUILL the place where they finally speak.
