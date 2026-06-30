# Quill User Guide

**QUILL** stands for **Quality, Usable, Inclusive, Lightweight, Literate**.

**QUILL: A quality, usable, inclusive, lightweight, and literate editor built for everyone who writes, codes, learns, and creates.**

Quill is a screen-reader-first writing and reading environment for Windows. It is designed to feel calm, predictable, deeply keyboard-friendly, and respectful of your focus. It is also ambitious. Quill is not only a place to write plain text. It is a place to open difficult documents, inspect structure, navigate long material, compare revisions, prepare content for Markdown or HTML, and work with accessibility and extraction issues without leaving the editor.

This guide is aligned to Quill 0.7.0 Beta, built by Blind Information Technology Solutions (BITS) together with Community Access.

This guide is written as a companion, not a reference wall. Read it from the beginning if you are new to Quill. Dip into the sections that matter most if you already know what kind of work you want to do.

Quill is also in beta. Expect polish, depth, and real daily utility. Also expect rough edges, unfinished flows, and the occasional surprise. If you find something confusing or broken, that is useful information. Quill is becoming stronger because real people are trying it on real work.

## Table of Contents

- [Start Here](#start-here)
- [What Quill Feels Like](#what-quill-feels-like)
- [Your First Session](#your-first-session)
- [Getting Around QUILL](#getting-around-quill)
- [Command-Line Launching](#command-line-launching)
- [The Main Window](#the-main-window)
- [The Menu Bar Reference](#the-menu-bar-reference)
- [Writing and Editing](#writing-and-editing)
  - [Import and Export](#import-and-export)
  - [Batch Conversion](#batch-conversion)
- [Search, Replace, and Deep Navigation](#search-replace-and-deep-navigation)
- [QUILL Quick Nav Mode](#quill-quick-nav-mode)
- [Formatting and Markup Work](#formatting-and-markup-work)
- [Tools for Reading, Review, and Inspection](#tools-for-reading-review-and-inspection)
- [Accessibility and Low-Vision Features](#accessibility-and-low-vision-features)
- [Quill on macOS](#quill-on-macos)
- [Profiles, Keyboard Packs, and Customization](#profiles-keyboard-packs-and-customization)
- [Trust, Recovery, Sessions, and Safety](#trust-recovery-sessions-and-safety)
- [Working with Different Document Types](#working-with-different-document-types)
  - [Plain text](#plain-text)
  - [Markdown](#markdown)
  - [HTML](#html)
  - [RTF](#rtf)
  - [CSV and TSV](#csv-and-tsv)
  - [Word (.docx and .doc)](#word-docx-and-doc)
  - [EPUB](#epub)
  - [PowerPoint (.pptx and .ppt)](#powerpoint-pptx-and-ppt)
  - [Excel-style spreadsheets (.xlsx and .xls)](#excel-style-spreadsheets-xlsx-and-xls)
  - [PDF and OCR-derived text](#pdf-and-ocr-derived-text)
  - [Remote files (FTP, SFTP, HTTPS, WebDAV, S3)](#remote-files-ftp-sftp-https-webdav-s3)
  - [GitHub Remote Files](#github-remote-files)
- [Braille Mode (BRF, BRL, PEF, UEB)](#braille-mode-brf-brl-pef-ueb)
- [Help, Learning, and Daily Confidence](#help-learning-and-daily-confidence)
  - [Context-Sensitive Help (F1)](#context-sensitive-help-f1)
  - [Personalising QUILL](#personalising-quill)
  - [Recent Fixes in 0.7.0 Beta 2](#recent-fixes-in-070-beta-2)
- [Translation and Community Localization](#translation-and-community-localization)
  - [How the Translation Pipeline Works](#how-the-translation-pipeline-works)
  - [Contributing Translations](#contributing-translations)
  - [Translation Roles and Responsibilities](#translation-roles-and-responsibilities)
  - [Speech String Guidelines](#speech-string-guidelines)
- [Checking for Updates](#checking-for-updates)
- [Beta Feedback and Bug Reporting](#beta-feedback-and-bug-reporting)
- [A Fast Shortcut Tour](#a-fast-shortcut-tour)
- [Control Reference](#control-reference)
- [Glossary of QUILL Terms](#glossary-of-quill-terms)

## Start Here

If you only have five minutes, do this:

1. The first time QUILL starts, the **Personalise QUILL** wizard offers to set up your keyboard layout, profile, and optional features in about two minutes. Complete it or dismiss it; you can re-run it from **Help → Personalise QUILL** at any time.
2. Press `Ctrl+N` to create a new document, or press `Ctrl+O` to open one.
3. Type a few lines.
4. Press `Ctrl+Shift+P` to open the Command Palette. Type `guide`, `spell`, `compare`, or `glow` and notice how quickly Quill turns intent into action.
5. Press `F6` to move into the status bar and hear how Quill treats even the bottom of the window as a working surface.
6. Press `F7` for spell check, `Ctrl+F` to search, or `Ctrl+K` to insert a link.
7. Press `F1` on any control to hear what it does and see its keyboard shortcuts.

If you ever feel lost, press `F1` for immediate help on the focused control, or use **Help → What Can I Do Here?** for document-context guidance. Think of those commands as the editor quietly putting a mentor beside you.

## What Quill Feels Like

Quill is built around a few promises.

- The keyboard is never second-class.
- Screen readers are not an afterthought.
- Every major action is reachable from the menu, the palette, and the command system.
- Documents open locally and stay local unless you explicitly choose a network-aware action.
- The editor should tell you what changed, where you are, and what is possible next.

In practice, that means Quill spends a lot of attention on focus movement, meaningful status updates, discoverable commands, and native Windows controls. It also means Quill tries to reduce fear. When you open a recovered draft, compare two files, or inspect extraction quality, the point is not to feel clever. The point is to feel safe.

## Your First Session

Imagine your first meaningful visit to Quill.

You launch the app. There is no splash screen. The window appears quickly, with a menu bar, an editor, and a status bar. If Quill detects a screen reader, it adjusts its hints and announcement style. If Quill notices an earlier crash or autosave state, it offers recovery instead of silently hoping you forgot.

From there, a natural first session looks like this:

1. Open a file with `Ctrl+O` or create one with `Ctrl+N`. Turn on **Settings > General > Use simple file open dialog** if you prefer a smaller, screen-reader-friendly file picker.
2. Read or write in the editor.
3. Use `Ctrl+Shift+P` to explore commands without memorizing everything.
4. Use the **Navigate** menu to jump by line, heading, block, region, or page.
5. Use the **Tools** menu for spelling, word count, extraction review, compare, macros, and regex help.
6. Open **Help → Open Keyboard Reference** to see the exact shortcuts that exist in your current configuration. This reference is generated dynamically, so it always reflects your current feature profile and any custom keybindings.

That first session matters because it teaches the most important Quill habit: you do not need to hunt. If an action exists, Quill wants you to be able to reach it from where you already are.

## Getting Around QUILL

QUILL is designed so you never need to memorize an action to reach it.

### F1 — help on the focused control

Press `F1` on any focusable control — a dialog field, a button, a menu item, the editor itself — and a small help dialog opens. It tells you what the control does and what keyboard shortcuts apply to it. The full text lands in one read-only field so your screen reader announces everything in one pass when the dialog opens.

- `F1` — help on the focused control
- `Ctrl+F1` — open the full User Guide
- `Shift+F1` — open "What Can I Do Here?" for the active document context

See [Context-Sensitive Help (F1)](#context-sensitive-help-f1) for full details.

### The QUILL key

The **QUILL key** is `Ctrl+Shift+Grave` (the back-tick/grave key above Tab). It is a layered prefix chord that opens most of QUILL's power features without ever leaving the keyboard.

> **Heads up: the chord reads as `QUILL Key + <key>` everywhere you see it.** Menus, the About > Keyboard Reference page, the QUILL Key Help dialog, the cheat sheet, and the status bar all show the chord in the branded form (`QUILL Key + S`, `QUILL Key + Shift+O`, and so on). The stored binding is still `Ctrl+Shift+Grave, <key>` — only the user-visible label moves. The display rewrite is one function (`format_binding_for_display`), so the entire product speaks the same label and a rebrand in `quill/branding.py` follows everywhere.

It operates in two primary layers:
1. **Prefix Mode (One-shot).** Press it once and QUILL arms a short-lived prefix. The next key you press runs a chord command (like `G` for Go to Anything or `M` for Markdown paste), and then the prefix expires.
2. **Browse Mode (Locked).** Press the QUILL key twice in a row, and QUILL locks **Quick Nav (Browse) mode** on. In this mode, single-letter keys (like `H` for headings, `P` for paragraphs, or `S` for sentences) move the cursor through the document structure. This mode stays active until you press `Esc`.

The QUILL key is its own tiny language: every chord is data-driven from the keymap, which means every chord is fully remappable in **Preferences → Keyboard → Keymap Editor**. The full cheat sheet is one keystroke away (`QUILL Key + ?`).

**QUILL key sound.** When the QUILL key is pressed and the prefix arms, QUILL plays a short two-tone earcon (`quill_key_pressed`) — a quick double-ping distinct from all other sounds — so you get instant audio confirmation without waiting for speech. This earcon is included in all bundled sound packs and can be toggled individually in **Tools → Reading & Dictation → Sound Events...**.

**Detection note.** On some keyboards or drivers, Windows reports the grave/back-tick key differently than expected. QUILL now uses three independent detection strategies (character code, Windows virtual key VK_OEM_3, and physical scan code 0x29) so the key is recognized on any layout.

**Reassigning chord commands.** Open **Preferences → Keyboard → Keymap Editor**, find the command you want to move, and type a new chord binding in the form `Ctrl+Shift+Grave, X` (replacing `X` with the key you want). The Keymap Editor stores chords in this `Ctrl+Shift+Grave, X` grammar; menus and the cheat sheet display them as `QUILL Key + X`. Conflict detection prevents accidental double-bindings.

### The Keyboard Manager: search, record, and diagnose

The Keymap Editor is built for fast, confident customisation, however you think about shortcuts:

- **Search two ways from one box.** Type part of a command's name to filter the list. Or type a *shortcut* — `ctrl+alt+m`, `Control + Shift + K`, even a QUILL chord like `quill, s` — and the editor flips to reverse lookup, telling you exactly which command that key is assigned to, or that it is "unassigned and available." You do not have to remember whether a key is free; ask it.
- **Forgiving spelling.** Modifiers can be written however you like: `control`, `ctrl`, or `ctl`; in any order (`shift+ctrl+k` equals `ctrl+shift+k`); in any case. QUILL normalises what you type and stores the tidy form, so `mac`-style `Cmd` stays distinct from `Ctrl` and is never confused with it.
- **Record Keys.** Prefer to *press* the combination rather than spell it? Choose **Record Keys**, press the chord, and QUILL fills it in for you.
- **Honest conflicts with one-step reassignment.** If you assign a key that is already taken, QUILL names the command that owns it — by its friendly title, not an internal id — and offers to move the key here, freeing it on the other command. No silent clobbering, no guessing.
- **Diagnostics and self-heal.** **Run Diagnostics** audits your whole keymap and reports duplicate shortcuts, bindings for commands that no longer exist, unreadable bindings, and any key that is "assigned but inert" (one the editor cannot actually fire). For the repairable problems it offers a one-click **Heal** that removes the bad entries and re-applies your keymap so menus and shortcuts line up again.

Default QUILL-key chords:

- `QUILL Key + N` — enter Quick Nav (browse) mode for the next action. If the `browse_mode_sticky` setting is on, the mode stays locked until `Esc`; otherwise it expires on the QUILL-key timeout. Press the QUILL key again (without a chord) to lock it on regardless of the setting.
- `QUILL Key` (pressed twice) — lock Quick Nav mode on until `Esc`. This is the most common path: first press arms the prefix, second press locks browse mode.
- `QUILL Key + G` — open **Go to Anything** (Quick Nav search).
- `QUILL Key + M` — paste the rich HTML clipboard as Markdown at the cursor.
- `QUILL Key + V` — open the browser preview for the current document.
- `QUILL Key + Shift+O` — open from remote (FTP / SFTP / HTTPS / WebDAV / S3 / GitHub).
- `QUILL Key + W` — save to remote.
- `QUILL Key + Shift+M` — manage saved remote sites.
- `QUILL Key + A` — selection actions when text is selected (also expands an abbreviation manually mid-word).
- `QUILL Key + Shift+A` — open the abbreviation manager.
- `QUILL Key + E` — toggle abbreviation expansion on or off.
- `QUILL Key + X` — open the Copy Tray dialog.
- `QUILL Key + Shift+1`–`Shift+9`, `Shift+0`, `Shift+-`, `Shift+=` — copy the selection to slots 1–12 of the Copy Tray.
- `QUILL Key + ?` — show the QUILL key cheat sheet.
- `QUILL Key + Esc` — cancel the prefix without firing any command.

### Command Palette

`Ctrl+Shift+P` opens the Command Palette — a searchable list of every registered command. Type any part of a command name to filter. Press Enter to run it. This is the fastest way to reach any action without memorizing its key or menu path. Searching `guide`, `spell`, `compare`, or `glow` from the palette is a good first practice.

### Navigation anchors

The status bar (`F6` to focus it) is a working surface, not decoration. Each cell announces meaningful information and most cells open a related dialog when you press Enter or click. `Shift+F6` moves focus back to the editor.

Reach any menu from the keyboard: `Alt+F` for File, `Alt+E` for Edit, `Alt+V` for View, `Alt+T` for Tools, `Alt+H` for Help. All menu items have keyboard mnemonics.

The Navigate menu groups document-level movement: go to line, go to heading, go to entry in notebook, heading organizer, outline navigator, back and forward location history, and structural next/previous. When you need to move across a large document, start there.

### The Simple File Open dialog

QUILL can open files through either the standard Windows file open dialog or a keyboard-friendly **Simple File Open** dialog that lists files in a focused list, with a small filter, recent locations, and a hidden-files toggle. Both dialogs are reached from the same place — **File > Open...** or `Ctrl+O` — and the active dialog is chosen by **Settings > General > Use simple file open dialog**. The setting is off by default; turn it on if you prefer a minimal, screen-reader-friendly picker.

The Simple File Open dialog has:

- A **Path** field at the top showing the current folder. Type a path and press Enter to navigate (folders) or open (files). Use **Ctrl+L** to focus the path field from anywhere in the dialog.
- A **Filter** dropdown with the file types the dialog will show. The default, **Supported files**, includes plain text, Markdown, HTML, and Rich Text. Switch to **Plain text**, **Markdown**, **HTML**, or **Rich Text** to narrow further, or to **All files** to see everything.
- A **Files** list of folders and files in the current directory. Folders are prefixed with `[dir]`. Use the **Up** button (or press Backspace in the list) to go to the parent folder.
- A **Hidden** toggle to show or hide files whose names start with a dot or whose Windows hidden attribute is set. **Ctrl+H** toggles this from the path field or the file list.
- A **Recent** button that opens a popup listing recently opened files for one-click re-open.
- A **Use Windows Dialog** button that opens the standard Windows file dialog for one invocation. The setting does not change; the next time you press `Ctrl+O` you are back in the simple dialog. Use this when an edge case (a long file path, a custom file association) calls for the native picker.
- An **Open** button and a **Cancel** button. Press Enter to open the selected file, Escape to cancel.

The status line below the list announces the current directory, the number of visible entries, and any errors. Permission-denied and not-a-directory errors keep the dialog open so you can correct the path and try again.

## Command-Line Launching

Quill supports command-line startup options for scripted workflows and direct navigation.

Supported options:

- `--help`: show command help and exit.
- `--version`: print QUILL version and exit without launching the UI.
- `--safe-mode`: launch with optional state disabled.
- `--reset-profile`: reset feature profile store before launch.
- `--diagnostics`: start with diagnostics tracing enabled.
- `--dump-stacks`: write a thread-stack dump and exit.
- `--line N`: 1-based line for the first startup file.
- `--column M`: 1-based column for the first startup file.
- `--goto FILE[:LINE[:COL]]`: open a file at an optional 1-based line and column in one argument. This is the compact form of `--line`/`--column`, handy when an external tool (a linter, a search result, a build error) hands you a `file:line:column` string. Example: `--goto main.kt:27:5`.
- `--diff LEFT RIGHT`: open two files directly in compare mode, landing on the first difference without opening each file by hand.
- `--new-window`: force a new process instead of forwarding to an existing instance.
- `--wait`: when forwarding to an existing instance, wait for that instance to close.

Examples:

- `python -m quill --version`
- `python -m quill notes.md --line 40 --column 5`
- `python -m quill --goto main.kt:27:5`
- `python -m quill --diff old-draft.md new-draft.md`
- `python -m quill --new-window notes.md`

## The Main Window

Quill keeps its main window intentionally simple.

### Menu bar

The menu bar follows the Windows and Office order you likely expect:

- File
- Edit
- View
- Insert
- Format
- Navigate
- Search
- Tools
- Window
- Help

The menu bar is exhaustive rather than decorative. If Quill can do something, there is almost certainly a menu path for it.

### Editor surface

The editor is the heart of Quill. It is where writing happens, where extracted text lands, where reports open as ordinary tabs, and where compare summaries feel like first-class documents rather than pop-ups.

The editor supports:

- plain text writing
- Markdown-aware authoring
- HTML-aware authoring
- structural navigation
- selection helpers
- text cleanup
- spell and thesaurus workflows
- link insertion and link following
- compare-driven review

### Tabs and document switching

Quill is multi-document. Each open file lives in a notebook tab. You can:

- move between documents with `Ctrl+Tab` and `Ctrl+Shift+Tab`
- close the active document with `Ctrl+W`
- use the tab context menu to close one tab, close other tabs, or close tabs to the right
- reveal a saved document in File Explorer directly from the tab context menu

Quill also opens generated artifacts as tabs. The welcome guide, keyboard reference, and compare summary all feel like normal working tabs. That is deliberate. Artifacts should stay close to the work that created them.

### Status bar

The status bar is interactive. It is not just a strip of passive text.

Use `F6` to move into it. Once there, you can move between cells and activate them. Depending on your layout and current state, the status bar can surface:

- current message
- line and column
- word count
- insert or overwrite mode
- tab mode (whether the Tab key indents the line or inserts a tab character)
- selection size
- encoding
- line endings
- spell-check state
- background task state
- notifications
- read-aloud state
- autosave timing
- current search term
- file path or unsaved state

You can reorder or hide status items through **Tools → Customize & Support → Status Bar Layout...**.
Right-click a focused status cell to **Activate**, **Hide this item**, or open **Status bar settings...**. On the **Notifications** (or **Background Tasks**) cell the context menu also offers **Clear All Notifications**, which empties the notification list in one step without opening the dialog.
Use **Restore Defaults** in status bar settings to reset visibility and order.
When title mode is set to full path, Quill automatically hides the duplicate file-path status cell.

### Region cycling

Use `F6` and `Shift+F6` to move between major regions. Quill treats region movement as a first-class accessibility feature. If you write, inspect, and navigate entirely from the keyboard, this becomes second nature quickly.

When **Show Tab Control** is on (View menu) and at least one document is open, the document tab bar joins the F6 rotation as the **Document Tabs** region, so the tab strip is reachable from the keyboard rather than being skipped. The cycle is Editor → Document Tabs → (Preview, when split open) → Status Bar. From the tab bar, the left and right arrows move between tabs, and Enter, Space, or Tab returns focus to the editor on the selected document.

### Tab key: indent or insert a tab character

By default the **Tab** key runs Quill's smart line indent: it adds one indentation level to the current line (or every line in the selection) at the start of the line, and **Shift+Tab** outdents. On a Markdown list item Tab and Shift+Tab nest and promote the item. Each of these actions is spoken, so a screen reader confirms the indent even though the caret stays in place.

If you would rather have Tab type a literal tab character at the cursor — the way a plain text editor behaves — toggle **Tab Mode** with the **QUILL Key + U** chord (this is Quill's equivalent of the VS Code "Tab key" toggle; Ctrl+M itself is reserved for the mark ring, and Ctrl+Alt+ chords are avoided as screen-reader-hostile). The current mode is shown in the **Tab Mode** status-bar cell (**Indent** or **Tab char**), mirrored by the checkable **Format → Tab Key Inserts Tab Character** menu item, and the new mode is announced when you switch. While Tab Mode is set to insert a tab character, Shift+Tab still outdents so a stray indent can be removed without leaving the mode. The setting applies to the current session.

**How the indent is spoken, and how wide it is.** When you indent with Tab (or outdent with Shift+Tab), Quill speaks the line's *new* indentation depth — for example "4 spaces", "8 spaces", or "1 tab" — so you always know how deep the line sits, not just that it moved. Two settings control the indentation itself: **Number of spaces per indent level** (Settings; 1–8, default 4) sets the width, and **Insert tab characters instead of spaces** (Settings) switches between space and tab indentation — the spoken depth follows whichever you choose. If you prefer the shorter "Indented lines" message, turn off **Announce indentation depth on Tab** (Settings → Accessibility).

## The Menu Bar Reference

This section walks the entire menu bar in the order you will encounter it.

### File

The **File** menu is the full document lifecycle.

- **New** creates a blank document.
- **Open...** opens a document from disk.
- **Open Recent** returns quickly to recently used files. If you turn on **Drop missing recent files automatically** in Settings (General), entries whose file has been deleted from a fixed internal drive are removed from the list. Files on USB, removable, or network drives are always kept, so unplugging a drive never clears its history.
- **Open from URL...** downloads a document or text resource through an explicit safety flow that confirms host and expected size.
- **Open from Remote**, **Save to Remote**, **Save Copy to Remote**, and **Manage Remote Sites...** (in the *Open from Remote* submenu) open, save, and administer saved sites over **FTP, SFTP, HTTPS, WebDAV, and Amazon S3 (or any S3-compatible service)**. Each remote operation is explicit, runs over a verified TLS context, announces host and expected size, and never writes to disk before you confirm.
- **Snapshots** lets you save and reopen groups of documents as a single workspace snapshot, similar to lightweight workspaces in Visual Studio Code.
- **New from Clipboard** opens a new document seeded with the current clipboard text.
- **Save** writes the current document.
- **Save As...** writes to a new path, converting the document to the file type you choose in the dialog. Quill keeps your text as portable Markdown-style markup, so picking **Rich Text Format (\*.rtf)** writes real RTF, **HTML (\*.html)** writes a standalone web page, and **Text (\*.txt)** writes clean prose with the markup removed. Choosing **Markdown (\*.md)** keeps the markup verbatim. The file's extension always decides the format; if you type a name without an extension, the selected type supplies one. When Save As changes the format, Quill can reload the file so the editing surface matches it — for example, opening a freshly saved `.rtf` in the Rich text editor. By default it asks first with a Yes/No prompt (reloading replaces the editor contents with the saved file); set **Settings → Editing → Reload after Save As to match the format** to *Reload automatically* or *Keep current surface* to skip the prompt.
- **Save All** writes every modified open document.
- **Save As Plain Text...** exports a clean plain-text version. Because plain text has no links, **Settings → Editing → Links in plain-text export** controls how Markdown links are written: keep the link text and its URL (the default, so you never lose where a link pointed), the link text only, the URL only, or the original Markdown link. This setting also applies whenever Save As writes a `.txt` file. If the document carries hidden formatting (fonts, colours, alignment), Quill offers to keep it with an **Illumination** — see below.

##### Keeping formatting in a plain-text file: Illuminations

A plain `.txt` file has nowhere to store fonts, colours, or alignment, so saving formatted text as plain text normally drops the formatting. Quill gives you a choice, named after the decorative layer a scribe paints over a manuscript: an **Illumination** is a small companion file, `yourfile.txt.illumination`, that holds the formatting beside the clean text. Your `.txt` stays genuinely plain — readable in Notepad, e-mail, or anywhere — and when you reopen it *in Quill*, the matching Illumination restores every font, colour, and alignment exactly.

What happens when you save formatted text as plain text is set by **Settings → Editing → Saving formatted text as plain text**:

- **Ask each time** (the default) — Quill asks whether to keep your formatting (by saving as Markdown, Word, or RTF instead), to save the plain `.txt` **plus** an Illumination, or to save plain text only and drop the formatting.
- **Always save an Illumination sidecar** — Quill writes the clean `.txt` and the `.illumination` companion every time, no prompt.
- **Save plain text and drop the formatting** — the classic lossy save; the `.txt` is clean and any old Illumination beside it is removed.

A few things worth knowing: the Illumination travels as a *separate file*, so if you copy or e-mail only the `.txt`, the formatting won't come along — keep the pair together (or use Markdown/Word/RTF, which carry formatting inside one file). And if you edit the `.txt` in another program, Quill notices the text no longer matches the Illumination and opens it as plain text rather than re-applying formatting to the wrong words. If you'd rather a single self-contained file that preserves everything, save as **Markdown** (which keeps the formatting inline) or **Word/RTF** (which turn it into native formatting).
- **Reload from Disk** throws away in-memory edits and reloads the file from storage after confirmation.
- **Restore Backup...** lets you restore a saved backup version.
- **Page Setup...** and **Print...** support paper and print workflows.
- **Run Current File** executes the saved file with its associated tool, and **Open Target at Cursor** opens the path or link under the caret.
- **Rename Current File...** and **Delete Current File...** manage the file on disk from inside the editor.
- **Close Document** closes the current tab.
- **Exit** closes the application.

The File menu is also where Quill quietly proves that it respects risk. Reload is explicit. Backup restore is explicit. URL opening is explicit. Nothing important is hidden behind a side effect.

### Edit

The **Edit** menu is where writing muscles live.

Standard clipboard commands are here:

- Undo
- Redo
- Cut
- Copy
- Paste
- Copy With Source
- Select All

Quill then goes further with selection- and navigation-aware editing:

- **Find...**, **Replace...**, **Find Next**, **Find Previous**, and **Find All Matches** all live here. Replace includes a **Replace All** action in its dialog, so bulk replacement stays in one place.
- **Word Prediction...** opens inline word and tag suggestions.
- **Extend Selection Mode** turns selection growth into a dedicated mode.
- **Selection** submenu includes Select Line, Select Paragraph, Select Block, Select to Start or End of Line, Select to Start or End of Document, and a nested **Recent Marks (Ring)** group (set a temporary mark, jump to previous marks, swap cursor and mark, list recent marks).
- **Follow Link** opens the link under the caret. (Link *insertion* now lives in the **Insert** menu.)
- **Paste HTML as Markdown** converts rich clipboard HTML to Markdown as it pastes.
- The deletion group — **Delete to Line Start**, **Delete to Line End**, **Delete to Document Top**, **Delete to Document Bottom**, and **Delete Paragraph** — removes text relative to the cursor.

**Preferences...** and **Customize Menus...** live with the rest of Quill's configuration under **Tools -> Customize & Support**.

### View

The **View** menu controls how Quill presents your document on screen without changing your content.

- **Toggle Soft Wrap** changes line wrapping without modifying the file.
- **Auto Side-by-Side Preview** opens a live preview beside the editor automatically.
- **Show Tab Control** toggles the visible document tab strip.
- **Wrap Find Searches** controls whether Find wraps past the end of the document.
- **Start With No Document Open** makes Quill open into an empty workspace instead of a starter document.
- **Preview...**, **Preview Side by Side**, **Focus Preview**, and **Browser Preview...** open rendered views of the current document.

Preference-style toggles that used to live here — theme/dark mode, system-tray mode, title-bar path style, dirty-title style, persistent undo, spell-check-as-you-type, and word-prediction-as-you-type — now live in the registry-driven **Settings** dialog (**Tools -> Customize & Support -> Preferences...**), where they are persisted in one place.

### Insert

The **Insert** menu adds structured content at the cursor.

- **Insert Link...** creates a format-aware link.
- **Heading** submenu: insert Heading 1 through 6, **Decrease Level** / **Increase Level**, and **Style Headings...** (font, size, alignment) for the current level or all levels.
- **List** submenu: **Bullet**, **Numbered**, **Task**, **List Manager...**, and **Structured List Studio...** (F2).
- **Insert Code Block**, **Insert Footnote**, **Insert Table...**, **Insert HTML Tag...**, and **Insert Markdown Tag...**.
- **Insert Snippet...** and **Manage Snippets...** for reusable text with placeholders.
- **Special Character...** (`Shift+F2`) opens a symbol picker. (This moved from F2,
  which now opens the Structured List Studio; both keys are remappable.)
- **Date and Time** submenu inserts a date, time, or both at the cursor. The bundled `com.quill.bundled.insert-tools` Quillin owns this submenu; it is the canonical home for date and time snippets. See [Date and Time submenu](#date-and-time-submenu) below.
- **File Content...** inserts the contents of another file at the cursor.
- **Insert Equation...** (`Ctrl+Shift+E`) opens a two-step prompt for inserting a LaTeX or MathML equation. Type the formula in LaTeX notation — for example `E=mc^2` or `\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}` — or paste a MathML fragment. If the input is LaTeX, a second step asks whether to display it inline (`$...$`) or as a block (`$$...$$`). If a LaTeX equation is already selected when you press `Ctrl+Shift+E`, the delimiters are stripped and the bare formula pre-fills the prompt. MathML input (starting with `<math`) is inserted verbatim without a mode step. Browser Preview and HTML export render equations using MathJax 3.

Quill treats Markdown and HTML as working surfaces, not special-purpose export formats, so tag insertion lives here beside the structural inserts.

#### Word prediction and snippets

Quill separates live prediction from snippet insertion so the hotkeys feel like a modern editor:

1. Press `Ctrl+.` to open **Word Prediction** (also on **Edit -> Word Prediction...**).
2. Type to surface matching document words, HTML tags, and Markdown tags.
3. Use arrow keys to choose a result and press Enter to insert it.

For setup and maintenance:

- Press `Ctrl+Shift+Grave, S` for **Insert Snippet**.
- Press `Ctrl+Shift+Grave, Shift+S` for **Manage Snippets** (create, edit, delete, import, export, and starter packs).
- Open **Preferences -> Install Starter Snippet Packs** to install sample libraries for daily writing, developer flow, and support/accessibility notes.
- In **General Preferences**, toggle **Word prediction and tag IntelliSense** or **Expand snippet triggers while typing** as needed.

Snippets support placeholders such as `${input:name}`, `${choice:a|b}`, `${date}`, `${time}`, and `${cursor}`.

#### Date and Time submenu

**Insert -> Date and Time** is a submenu, not a single command. The bundled `com.quill.bundled.insert-tools` Quillin owns it and contributes three snippet-backed items:

- **Insert Date** — inserts today's date at the cursor using the project's current `${date}` format.
- **Insert Time** — inserts the current time at the cursor using `${time}`.
- **Insert Date and Time** — inserts both, separated by a single space.

The submenu is built by routing Quillin contributions whose `parent` is `Date and Time`. If you disable the bundled `insert-tools` Quillin, the submenu is still present but its items go with it. Enable or disable it from **Preferences -> Quillins** if you want to replace these with your own date/time snippets.

#### Format

The **Format** menu handles presentation and markup-aware editing of existing text.

Case operations live in the **Change Case** submenu:

- Upper Case
- Lower Case
- Title Case
- Sentence Case
- Toggle Case

Comment and indentation tools:

- Toggle Line Comment
- Toggle Block Comment
- Indent
- Outdent

Line operations:

- Move Line Up
- Move Line Down
- Duplicate Line
- Delete Line
- Join Lines

Inline emphasis:

- Bold
- Italic

**Rich formatting with hidden codes (new in 0.8.1 Beta 1).** Beyond Bold and Italic, the Format menu now applies real document formatting that stays invisible in your editor: **Underline**, **Strikethrough**, **Superscript**, **Subscript**, **Font** (family), **Size** (point size), **Text Colour**, **Highlight**, and paragraph **Alignment** (Left / Centre / Right / Justify), line spacing, indent, and named styles. The idea is *hidden codes*: your editing buffer stays clean, fast, plain text — the formatting is stored as invisible markup, never as on-screen clutter — and is materialised into real formatting only when you export. So you read and edit clean prose, and the document still becomes a properly formatted Word, RTF, or HTML file on save.

- **Apply it** from the Format menu's Font / Size / Align / Colour / Highlight items, or from the accessible **Font...** dialog, which gathers font family, point size, colour, and highlight in one place. With text selected, the formatting applies to the selection; with no selection it applies as you type.
- **Hear what's there.** Because the codes are hidden, **Describe Formatting at Cursor** speaks exactly what is in effect at the caret — for example "Arial, 14 point, centred, bold". Turn on **Announce formatting on caret move** (Settings → Accessibility) to hear formatting changes as you arrow through a document.
- **It exports faithfully.** On **Save As** (or Export) to **Word (.docx)**, **Rich Text (.rtf)**, or **HTML**, the hidden codes become real formatting — font, size, colour, highlight, alignment, and the rest. Word export uses a native writer when the optional `python-docx` component is present and falls back to Pandoc otherwise. If a target format genuinely cannot carry something, Quill tells you before you commit rather than dropping it silently; saving to plain text drops the formatting with the same honest warning.

Everything that makes Quill fast still works on the same clean text: undo, search, the outline, word counts, read-aloud, and the AI tools all operate on your prose, not on markup.

The **Transform Lines** submenu gathers every line and text transform in one place: **Number Lines...**, **Number Lines (Advanced)...**, **Hard-Wrap Lines...**, **Sort Lines Ascending**, **Sort Lines Descending**, **Reverse Lines**, **Remove Duplicate Lines**, **Trim Trailing Whitespace**, **Normalize Whitespace**, **Convert Indentation to Spaces**, and **Convert Indentation to Tabs**. **Number Lines (Advanced)...** adds a starting number, increment, digit or Roman-numeral style, zero-padding width, a custom suffix, and left or right alignment, for cases the simple version doesn't cover.

### Navigate

The **Navigate** menu is one of Quill's strongest differentiators. It assumes you may need to move through large, dense, or extracted material without visual scanning.

Core location commands:

- **Go To Line...**
- **Go To Page...**
- **Back Location** (default: `Alt+Left` on Windows, `Cmd+[` on macOS — see [Recent Fixes](#recent-fixes-in-070-beta-2) for why the macOS chord changed in 0.7.0 Beta 2)
- **Forward Location** (default: `Alt+Right` on Windows, `Cmd+]` on macOS — see [Recent Fixes](#recent-fixes-in-070-beta-2))

Structural movement commands:

- **Next Heading**
- **Previous Heading**
- **Next Block**
- **Previous Block**
- **Outline Navigator...**
- **Heading Organizer...** (`Ctrl+Shift+Grave, O`) for heading-level edits, section reorder, and heading validation
- **Match Bracket**
- **Next Structure**
- **Previous Structure**
- **Next Region**
- **Previous Region**

Bookmark and position commands:

- **Set Bookmark...**
- **Go To Bookmark...**
- **List Bookmarks...**
- **Go to Percent...**
- **First Non-Blank**
- **Last Non-Blank**

Bookmarks are **per document and persist between sessions**: each named jump point
is remembered for the specific file it was set in, so when you reopen that document
its bookmarks are still there. QUILL also remembers your **last cursor position** in
each saved document and returns you to it when you reopen the file. (Untitled, never-
saved documents keep their bookmarks for the current session only, since there is no
file to attach them to yet — saving the document makes them persistent.)

#### Inline notes (sticky comments)

Inline notes are private comments you attach to a line or a selection — for queries,
reminders, and running commentary while you draft. They live under **Tools → Writing**
and have four commands (default keys shown; all remappable in the Keymap Editor):

- **Add Inline Note...** (`Alt+Shift+I`) — note the selected text, or the current line
  if nothing is selected. Type the note and Save.
- **Next Inline Note** (`Alt+Shift+J`) and **Previous Inline Note** (`Alt+Shift+G`) —
  move the cursor to the next / previous noted text; QUILL announces the note.
- **Speak Inline Note** (`Alt+Shift+H`) — read aloud the note at the cursor. **Press it
  again quickly** (a double-press) to open the note to view, edit, or delete it.

Inline notes are **anchored to your content**: each remembers the exact text it was
placed on (plus a little surrounding context), so it **follows that text as you edit**
and is **restored when you reopen the document** (per document, saved between
sessions, just like bookmarks). If the text a note was on is later deleted, the note
is kept rather than silently lost. Untitled documents keep their notes for the
session until you save. Notes are private to you and never written into the document
itself.

If your work involves transcripts, legal text, long Markdown notes, HTML source, or extracted PDFs, spend time here. This is the menu that turns Quill from a text box into a navigable workspace. (Find Next, Find Previous, and Find All Matches now live in **Edit**, beside Find and Replace.)

### Search

The **Search** menu is the across-files and pattern hub. In-document Find and Replace live in **Edit**; this menu covers multi-file and regular-expression work.

- **Search in Files...** and **Replace Across Files...** search and replace across a folder of documents.
- **Count Regex Matches...** and **Extract Regex Matches...** report or pull out every match of a regular expression.
- **Lines in First Block Only** and **Lines Common to Both Blocks** filter lines by block membership (set operations between two marked blocks).

### Tools

The **Tools** menu is Quill's workshop. It contains high-value actions that are not best understood as raw editing.

#### Discovery and command access

- **Command Palette...**

The palette is one of the fastest ways to learn Quill. It supports query modes:

- normal search or `>` for general command search
- `:` to search command IDs
- `?` to favor bound commands
- `~` to emphasize recently used commands

The palette also learns from usage. Commands you use more often rise naturally.

#### Writing and language

- **Word Count...**
- **Spell Check...**
- **Next Misspelling**
- **Thesaurus...**
- **Dictionary Status...**
- **AI Hub...**
- **Writing Assistant...**
- **Prompt Studio...**
- **Agent Center...**
- **Rewrite Selection**
- **Summarize Selection**
- **Continue Writing**
- **Fix Grammar**
- **Run Python...**
- **Quill Eraser...**
- **Quill Eraser on Selection...**

The Writing Assistant shell ranks Quill commands from your prompt, offers preset prompts for rewrite/summarize/continue/grammar flows, and **Run Python...** executes a restricted-Python transform against the current document text and selection. This restriction is an import allowlist and resource limits, not a security boundary — only run Python code you trust or wrote yourself. Prompt Studio lets you build reusable custom prompts with template variables, and Agent Center generates guided task plans that you can review before sending to the Writing Assistant.

The quick writing actions work with or without a selection:

- **Rewrite Selection** and **Fix Grammar** act on your selection if you have one; otherwise they use the paragraph at the cursor.
- **Summarize Selection** acts on your selection if you have one; otherwise it summarizes the whole document.
- **Continue Writing** uses your selection as the lead-in if you have one; otherwise it continues from the full document.
- Quill announces the scope it chose, for example "Rewrite paragraph (42 words)", so you always know what the action will change.
- If there is nothing to act on, Quill says so (for example "Nothing to rewrite") instead of sending an empty request.
- If AI is turned off, these actions announce "AI is turned off. Enable 'Use Artificial Intelligence' in the AI menu." and do nothing else.

Use **AI > AI Hub...** for a single control surface that links provider verification, model discovery, Prompt Studio, Agent Center, and Writing Assistant.

Trust and privacy baseline:

- On first run, Quill shows a trust and privacy consent acknowledgement.
- Quill does not persist AI chat session transcripts by default.
- Cloud requests happen only when you explicitly invoke an AI action.
- API keys are stored in Windows Credential Manager when available, with DPAPI-encrypted fallback storage.

AI connection flow:

1. Open **AI Hub** and choose provider (`Ollama (local)`, `Ollama Cloud`, `OpenAI`, `Claude`, `OpenRouter`, `Google Gemini`, or `Custom OpenAI-compatible`).
2. Confirm host URL and model.
3. Enter key only when your endpoint requires authentication.
4. Use **Verify Connection** to test endpoint and credentials.
5. Use **List Models** to fetch endpoint models, then use the search box to filter quickly.
6. Use **Recommend Model** to pick a model profile aligned to your hardware/task framing.
7. Save settings. Quill auto-runs verification and updates the AI status line in the AI menu.

Most cloud providers are pre-configured with default host URLs so setup is key-first, not URL-first. For advanced OpenAI-compatible endpoints, use Custom and override host/model explicitly.

Quill stores optional keys in the Windows Credential Manager, with a DPAPI-encrypted file as a fallback, and announces the verification result in plain language for immediate screen-reader feedback.

Connection status messages tell you exactly what to do next:

- "Authentication failed. Check your API key." means the key was rejected (HTTP 401). Re-enter the key.
- "Access denied. Your API key is valid but lacks permission for this model or region." means the key works but is not allowed for that model, region, or billing tier (HTTP 403). Check the provider's model access, billing, or quota.
- "The AI provider is warming up. Try again in a moment." means the model is still loading. Quill retries briefly on its own before reporting this.
- "The local AI server is not running. Start Ollama and try again." means Quill could not reach your local endpoint.
- "Rate limited by the AI provider. Wait a moment and try again." means you sent requests too quickly.
- "Your saved API key could not be unlocked on this device. Open AI Connection and enter the key again." appears in the AI status line when a saved key cannot be decrypted, which can happen after moving a portable install to a different Windows account or machine. Open AI Connection and re-enter the key.

For policy details, see the repository's `PRIVACY.md` and `RESPONSIBLE_AI_USE.md`.

These help you stay inside the editor instead of breaking flow for small writing chores.

### Ask Quill Chat setup (on-device AI)

Ask Quill Chat (**AI > Writing Assistant...**) is a message-style assistant that can answer, draft text, propose edits, and run Quill commands with approval before changes are applied.

Runtime backends:

- Windows and Linux: `llama.cpp` (`llama-cpp-python`, GGUF model)
- macOS (Apple Silicon, macOS 26+): Apple Foundation Models

Setup:

1. Install dependencies: `pip install -r requirements.txt`
2. Put a `.gguf` model in `%APPDATA%\\Quill\\models\\` (Windows) or set `QUILL_LLAMA_MODEL` to a full path.
3. Open **AI > Writing Assistant...** and send a prompt.

Accessibility:

- The whole conversation renders as an accessible WebView document: each turn is a heading (speaker) you can jump between, new replies are announced automatically, and the message box lives inside the page. Press `Escape` to close the chat. Verified in NVDA, JAWS, and VoiceOver.
- You can also connect optional providers (Ollama local/cloud, or a custom endpoint) instead of the on-device model.

Choosing the provider and model from the chat:

- A bar at the top of Ask Quill always shows the **active provider and model** so you know what is answering.
- Select **Change provider or model** to reveal the inline picker. Choose a provider and model, enter a key if needed, and **Save** — this also sets that choice as the default, so the next chat uses it.

Putting chat content into your document:

- The **Insert into document** controls at the bottom let you drop chat content straight into the editor.
- Choose the **scope** — **Last response** or **Entire transcript** — and the **format** — **Plain text**, **Markdown**, or **HTML** — then select **Insert**. The whole transcript includes the speaker labels; the last response is inserted as just its content.
- **Copy Last Response** copies the most recent reply to the clipboard.

Behavior notes:

- The assistant answers in chat by default; greetings and questions are never turned into document edits.
- Proposed actions (insert, replace, run a command) use an explicit `Approve` or `Discard` step before anything changes your document.
- If model/runtime is unavailable, Quill reports this clearly and does not apply destructive changes.
- **Train Writing Style** (**AI > Train Writing Style...**) lets you teach the assistant your own writing style from samples or the current document.

### The AI Hub (one place to configure every provider)

The **AI Hub** is now the single place to set up and manage AI. The former
separate **AI Model and Connection** and **Forget API Key** menu items were
merged into it, so there is one home for providers, models, keys, and testing.
Open it from `AI > AI Hub...`.

The Hub lets you work through every provider, each with its own key and default
model — switching providers never loses another provider's configuration:

1. Choose a provider: `Ollama (local)`, `Ollama Cloud`, `OpenAI`, `Claude`,
   `OpenRouter`, `Google Gemini`, or a `Custom OpenAI-compatible` endpoint.
2. The host, default model, and that provider's saved key fill in automatically.
   Cloud hosts are prefilled, so setup is usually just a key and a model.
3. Enter the API key (only cloud providers need one). It is stored securely on
   this device and kept per provider.
4. **Verify Connection** checks the endpoint and credentials.
5. **List Models** fetches the endpoint's models with a search filter;
   **Recommend Model** suggests a model tuned to your hardware or task.
6. **Test Chat** sends a tiny prompt and confirms the selected provider and model
   actually answer — quick quality confirmation before you rely on them.
7. **Forget this provider's key** clears just that one provider's key.
8. **On-device model...** opens the local model (GGUF) settings for llama.cpp.
9. Save (OK). The chosen provider/model becomes active immediately and Quill
   announces plain-language verification feedback (ready, auth failure, timeout,
   or endpoint unreachable).

Use `Prompt Studio` to save reusable templates and `Agent Center` to generate
guided task prompts. Ollama Cloud's free personal-use tier (with lower limits) is
available here too.

For release-safe beta validation, Word and CSV open in the normal plain-text
editor surface; AI connection and chat flows remain available.

### AI Language Tools

QUILL's AI language tools extend the standard AI Assistant with document-aware
language actions you invoke directly from the AI menu.

#### Spelling Review (F7)

**F7** starts QUILL's guided local spelling review — no AI provider, no network
connection, nothing uploaded.

- **Scope.** If you have text selected, QUILL checks only the selection. With
  no selection, QUILL reviews the entire document starting at your caret.
- **Dialog.** The **Spelling Review** dialog opens with focus in a read-only
  **Context** field. The misspelled word is selected within the surrounding
  sentence so you can hear it in context, navigate it character by character
  with arrow keys, or copy the text — just like a read-only document.
- **Tab order.** Context → Change to → Suggestions → Change → Change All →
  Ignore Once → Ignore All → Add to Dictionary → Undo Last → Close.
- **Suggestions** — arrow through spelling recommendations; selecting one
  fills **Change to** automatically.
- **Change** replaces the current occurrence and advances to the next issue.
  Pressing **Enter** in the **Change to** field also triggers Change.
- **Change All** replaces every remaining occurrence in scope, preserving
  capitalisation (`teh → the`, `Teh → The`, `TEH → THE`).
- **Ignore Once** skips this occurrence. **Ignore All** skips all occurrences
  for the current session only.
- **Add to Dictionary** adds the word to your personal dictionary permanently.
- **Undo Last** reverses the most recent spelling action without closing the
  dialog. It is disabled when nothing has been done yet.
- **Alt+W** returns focus to Context and reselects the current word at any
  point — useful after arrowing around the context text.
- When all issues have been handled, QUILL shows a summary (changed, ignored,
  added to dictionary) and returns focus to the editor.

**Verbosity settings** (`Settings > Spelling Review`):

- **Concise** — progress numbers and action results only.
- **Balanced** *(default)* — issue type, current word, progress, and results.
- **Detailed** — adds control hints and scope reminders.
- **Spell word aloud** — after announcing the misspelling, QUILL reads it
  letter by letter. The pause before spelling starts is configurable.

#### Spell check a document before saving

Turn on **Settings → Editing → Spell check a document before saving** (off by
default) and QUILL opens the same Spelling Review (F7) automatically whenever you
save, so you can correct misspellings before the file is written. Review or skip
the issues as usual; the save then proceeds with your corrections. This applies
to **Save** and **Save As** for the document you are editing.

#### Spell-check language

**Tools → Spell Check Language...** chooses the language the spell checker validates
against — it affects both the F7 review and check-as-you-type. **English (United
States)** ships built in and works offline immediately. Other languages are
downloaded on demand: pick, for example, **Spanish (Spain)** or **French (France)**
and QUILL fetches that dictionary the first time from its own verified source
(checksum-checked, with a cancelable progress window), then it works offline like
English. Your choice is remembered between sessions. If you are offline or the
download is cancelled, English keeps working and nothing else is affected. The
downloaded dictionaries are stored under your QUILL data folder, so reinstalling or
upgrading QUILL never makes you fetch them again.

**Editor shortcuts** (without opening the dialog):

| Key | Action |
|---|---|
| `F7` | Open Spelling Review dialog |
| `Ctrl+F7` | Jump to next misspelling in editor |
| `Ctrl+Shift+F7` | Jump to previous misspelling in editor |
| `Shift+F7` | Thesaurus |

#### AI Spell Check

QUILL can also send your document to your configured AI provider for a
cloud-assisted spelling check. An AI connection must be configured and turned on;
no text is sent until you invoke the command.

- **AI Spell Check** (`AI > AI Spell Check...`) sends your document to your
  configured AI provider and returns a list of corrections. A review dialog
  lets you accept, skip, or override each suggestion before any change is made.
- **AI Spell Check Interactive** (`AI > AI Spell Check Interactive...`) works
  paragraph by paragraph. Corrections for each paragraph are fetched in the
  background while you review the previous one, keeping the dialog responsive
  on long documents.

#### AI Grammar and Style Check (Ctrl+Alt+Shift+G)

`AI > AI Grammar and Style Check...` (`Ctrl+Alt+Shift+G`) analyses the document for grammar,
punctuation, clarity, style, and word choice. Issues appear in a list grouped
by category. You can:

- Filter to a single category (Grammar, Punctuation, Clarity, Style, Word Choice).
- Accept or skip individual issues.
- Accept or skip an entire category at once.
- Accept all remaining issues.
- Press Apply and Close to apply accepted fixes as a single undo step.

#### Translate Selection and Translate Document (Ctrl+Alt+Shift+T)

`AI > Translate Selection...` (`Ctrl+Alt+Shift+T`) and `AI > Translate Document...`
translate your text into a language you choose from the dialog.

**Providers:**

- **AI Assistant** (default): uses your configured cloud or local LLM. Works
  with any provider that can follow instructions (OpenAI, Claude, Gemini,
  Ollama, and compatible endpoints).
- **LibreTranslate**: a free, open-source translation engine that can run
  entirely on your own machine — no internet connection required once installed.

  Install LibreTranslate locally:
  ```
  pip install libretranslate
  libretranslate
  ```
  Then enter `http://localhost:5000` as the URL in the translation dialog.
  This is the most private option: your text never leaves your machine.

After translation:
- Copy to Clipboard: copies the result without changing your document.
- Replace Original: replaces the selection or document with the translation.
- Open as New Document: opens the translation as a new unsaved document tab.

#### Transcribe Audio File

`AI > Transcribe Audio File...` opens a file picker and sends the chosen audio
file to OpenAI Whisper for transcription. Supported formats: MP3, MP4, M4A,
WAV, WEBM, OGG, FLAC (maximum 25 MB).

Options:

- **Language**: auto-detect or pick a specific language for better accuracy.
- **Speaker diarization** (uses Deepgram): identifies who is speaking when.
  The transcript labels each turn with Speaker 1, Speaker 2, and so on, plus
  timestamps. Requires a Deepgram API key configured in AI Hub.
- **Translate to English**: transcribes audio in any language and returns an
  English translation in one step (Whisper translation mode).

When the transcript is ready, QUILL asks **"What would you like me to make of
this?"** and offers a short, context-aware list of **Transcript Actions** (see
the next section). Choose one and QUILL turns the transcript into a finished
document — meeting minutes, action items, study notes, a clean draft — and opens
it for you to review and edit. Or choose **"Just keep the transcript"** to land
in the viewer dialog, where you can copy, insert at the cursor, or open the
transcript as a new document. If AI is turned off, you go straight to the viewer.

`AI > Translate Audio File to English...` goes directly to the Whisper
translation flow, bypassing the language selection step.

#### Transcript Actions — turning sound into a finished document

A transcript is rarely the thing you actually need; the *minutes*, the *action
items*, or the *clean draft* are. **Transcript Actions** make that last step one
keystroke. They are reachable in two places:

- **Right after transcription**, in the "What would you like me to make of this?"
  chooser described above.
- **Anytime**, on the text you are already looking at, via
  `AI > Transcribe Audio > Transcript Actions...`. Paste any transcript or notes
  (or select part of your document) and pick an action.

The built-in actions are:

- **Meeting Minutes** — attendees, decisions, action items with owners, follow-ups.
- **Action Items** — every task and commitment as a numbered, actionable list.
- **Executive Summary** — a concise briefing for leadership.
- **Interview Notes** — questions, responses, strengths, concerns, an assessment.
- **Study Notes** — a lecture or talk turned into organized notes.
- **Q&A Extraction** — every question and its answer in clean Q&A format.
- **Clean Up & Draft** — spoken rambling turned into a clean, readable draft.
- **Follow-Up Email** — a warm, ready-to-send recap with next steps.
- **Key Quotes** — the most notable verbatim quotes, with who said them.
- **Decisions Log** — just the decisions made, each with its rationale and owner.

QUILL orders the list for the recording in front of you — a multi-speaker meeting
leads with Minutes and Action Items, a single voice with Clean Up & Draft — but
every action is always available. The finished document opens in a new window so
your original transcript is never overwritten. Transcript Actions use whichever AI
provider you have configured in the AI Hub.

### Setting up AI — the gentle wizard

The first item in the `&AI` menu is **Set Up AI...** (labeled "start here" until
you've done it). It opens a short, friendly wizard that gets you from nothing to a
working AI in seconds, with no jargon:

1. **Welcome** — a plain-language note on what QUILL's AI does and that it is
   optional, previewed, and private by default.
2. **How would you like AI to run?** — one choice:
   - **On your device with Ollama** — private and free; runs on your computer with
     no account or key. QUILL connects to a local Ollama install.
   - **Use an AI account** — the most capable models; connect Claude, OpenAI,
     Gemini, OpenRouter, or Ollama Cloud with a key you paste once and QUILL stores
     securely on this device.
   - **Not right now** — keep AI off; set it up any time later.
3. **Connect** — for an account, pick a provider, paste your key, and **Test
   connection** before continuing. For on-device, QUILL points itself at Ollama.
4. **You're all set** — a short summary of what you can now do, and a **Keep it
   simple** checkbox that turns on **Basic mode**.

QUILL also offers this wizard at the moment you reach for AI before it's set up — for
example, choosing to make minutes from a transcript — so you are never stuck at a
dead end. You can re-run **Set Up AI** any time to change providers or switch modes.

**Basic mode** keeps the AI menu small for newcomers: the everyday features (Ask
Quill, Transcribe, Proofread, Translate, Read Aloud, the AI Library) stay, while the
power-user, agentic entries ("What can I do here?", "Rewrite & Improve", and "Run
Agent") are hidden until you're ready. Turn them on any time with **Show advanced AI
features** near the bottom of the AI menu. Existing users keep the full menu — Basic
mode applies only if you choose it.

### The AI Library — Prompts, Skills, and Agents in one place

`AI > AI Library...` is the single home for everything QUILL can do with AI on
your writing. It has three tabs, all sharing the same buttons (Run, Edit,
Enable/Disable, Import, Export):

- **Prompts** — single instructions you run on the current selection or document
  ("Rewrite warmly", "Summarize"). New, Edit, Delete, and Promote a prompt into a
  Skill.
- **Skills** — multi-step workflows saved as shareable `.sqp` packs. Run them,
  Import/Export them, Remove them, and Promote a Skill into an Agent.
- **Agents** — the catalog of tool-using agents (Writing Companion, Reviewer,
  Code Doctor, and more) plus any you have saved yourself. Run them through the
  reviewed gateway, or Validate one against the agent standard.

The three are points on one continuum of saved AI intent. **Promote** lets a
Prompt grow into a Skill and a Skill grow into an Agent, so you can start simple
and add power only when you need it. Anything you build is yours to Export and
share, and a teammate can Import it.

#### Build an AI Action (no syntax required)

On the Skills tab, **Build Action...** opens a friendly, form-based builder — the
easiest way to teach QUILL something new:

1. **Name** your action ("My Monday standup notes").
2. **Start from** a built-in example (Meeting Minutes, Action Items, and the rest)
   or a blank page. Choosing an example fills in the instructions for you to adjust.
3. **Describe what you want in plain language.** That is the whole "programming" —
   no Markdown, no metadata, no syntax.
4. **Attach a reference** (optional) — an agenda, your house style, or a past good
   example — and QUILL will match its format and terminology. "Make minutes that
   look like last month's."
5. **Save.** Your action becomes a real Skill in the Library, ready to Run on any
   document, adjust later, Promote to an Agent, or share.

### Automate transcription with watch folders

A watch folder turns "drop a file here and it just gets handled" into a rule you
set once. In `Tools > Watch Folders`, a transcribe profile can now **chain an AI
Action onto each recording**:

- Point a profile at a folder (for example, *Meetings*).
- Choose a transcribe action (offline or OpenAI Whisper).
- Under **Then make**, pick a Transcript Action — say, *Meeting Minutes*.

From then on, every recording that lands in that folder is transcribed *and* the
minutes document is written next to it automatically, named like
`standup-meeting-minutes.md`. If AI is off or no provider is configured, you still
get the transcript — the action step is simply skipped with a note, never an error.
Watch folders respect Do Not Disturb and run quietly in the background.

### Offline transcription (Tools > Speech)

QUILL can also transcribe **entirely on your computer**, with no cloud account
and without uploading your audio. **No AI account or key is required** — you do
not need to enable Artificial Intelligence to use these features. They live under
**Tools > Speech**:

- **Manage Speech Models...** lists local speech models with their download size,
  accuracy, and speed, and helps you pick one that will actually run well on your
  computer. The dialog opens with a one-line summary of your machine (RAM, and
  whether a GPU was found). Each model shows roughly how much memory it needs; a
  model that is too big for your RAM is flagged, the best fit for your computer is
  marked **"Recommended for your computer,"** and a larger model warns you when no
  GPU is present (it will be slow on the CPU).
  - **Choosing what to do.** Pick a model, then choose an action: **Download this
    model** if it is not installed, or **Remove this model from my computer** if it
    is. (Deletion is now an explicit choice, so it is easy to find.) Before a
    download starts, QUILL warns you if there is not enough free disk space.
  - **Downloads run in the background and show progress.** A download no longer
    freezes QUILL: it runs while you keep working, shows a **percentage** in a
    progress window you can **Cancel** at any time, and announces progress as it
    goes. Cancelling cleans up the partial file. Models come over a secure
    connection from the Hugging Face Hub and are stored on your computer.
    Downloading is disabled in Safe Mode.
- **Transcribe Audio or Video (Offline)...** asks for an audio or video file and a
  transcript format — **plain text, Markdown, or HTML** — then transcribes locally
  and opens the result as an editable draft document. The work runs in the
  background so you can keep editing; QUILL announces when it is done and how many
  words were produced.
- **Supported formats.** You can pick MP3, M4A, AAC, FLAC, OGG, Opus, WMA, WAV,
  MP4, M4V, MOV, MKV, WebM, or AVI. If **ffmpeg** is installed, QUILL converts the
  file automatically before transcribing — you do not have to make a WAV yourself.
  QUILL does not ship ffmpeg, but it can fetch it for you: **Tools > Speech >
  Download FFmpeg...** downloads the official build (about 110 MB,
  with a cancelable progress bar) and sets it up; or install it yourself once (for
  example, `winget install Gyan.FFmpeg`) and QUILL finds it on your PATH. ffmpeg
  is open-source (GPL/LGPL) and fetched directly from the official builder; QUILL
  never bundles or redistributes it. Without ffmpeg, the whisper.cpp engine needs
  a 16 kHz mono WAV, while the Faster Whisper engine handles the other formats on
  its own.
- **Download Offline Speech Engine...** The private, on-device speech engine
  (whisper.cpp) is not bundled in the installer; the first time you use offline
  dictation or transcription, QUILL **offers to download it for you** (about 8 MB,
  checksum-verified, with a cancelable progress bar; disabled in Safe Mode). You
  can also fetch it any time from **Tools > Speech > Download Offline Speech
  Engine...**, or from the all-in-one **Help > Download Optional Components** list
  (below). If you are **upgrading** from a version that bundled the engine, your
  existing copy is kept and keeps working — nothing to download.

#### Download Optional Components (Help menu)

To keep the installer small, QUILL fetches several large or optional pieces only
when you want them. **Help > Download Optional Components...** is the single place
to see and get them all. It lists each component — the **offline speech engine**
(whisper.cpp), **Kokoro** neural voices, **eSpeak NG** and **DECtalk** voices, the
**FFmpeg** audio-export helper, and any non-English **spell-check dictionaries** —
and shows for each whether it is **Installed** or **Available to download**, along
with its approximate size. Select a component and choose **Download** to fetch it;
each download is checksum-verified and shows its own progress. Everything here is
optional — the base app, and Windows' built-in SAPI 5 voices, work without any of
it — so download only what you need.
- **Speaker attribution.** If you download the "Small English with speaker
  detection" model (in Manage Speech Models), QUILL marks **who is speaking when**
  — each turn is labelled "Speaker 1", "Speaker 2", and so on in the transcript
  (shown in bold in Markdown and HTML). Speaker detection identifies separate
  turns; it does not name the people.
- **Generate Captions (Offline)...** transcribes a file with timestamps and saves
  the result as **SRT** or **VTT** caption files.
- **Dictate (Offline)** speaks straight into your document. Run it (or press
  **QUILL Key + Shift + D**) to start: QUILL plays a distinct start tone and shows
  "Dictation listening" in the status bar. Run it again to stop; QUILL plays a stop
  tone, transcribes what you said in the background, and inserts the text at your
  cursor as a single undoable edit (the status bar shows the word count).
- **Dictation Microphone...** chooses which microphone dictation uses, or the
  system default.

##### Hold-to-Dictate and Locked Dictation (F9 / Ctrl+F9)

Two keyboard-only ways to dictate without opening a dialog or leaving the editor.
Both use the same on-device Whisper engine and microphone as **Dictate (Offline)**,
so nothing is uploaded.

- **Hold-to-Dictate — hold F9.** Press and hold **F9**, speak, and release. QUILL
  transcribes and inserts the text at the cursor as one undoable edit. A short tone
  marks the start and (after the microphone closes) the stop. Best for a phrase or
  a sentence.
- **Locked Dictation — Ctrl+F9.** Press **Ctrl+F9** to start a continuous session
  without holding a key; QUILL announces "Locked dictation on." Press **Ctrl+F9**
  again to finish and insert.
- **Stopping safely.** While recording, **Escape** stops and keeps your speech for
  transcription; **Shift+Escape** cancels and discards it. A locked session also
  stops automatically after five minutes, and stops and preserves your audio if
  QUILL loses focus.
- **Pause and status.** **Ctrl+Shift+F9** pauses or resumes a locked session;
  **Alt+F9** speaks the current state without changing it.
- **Nothing is lost.** Audio is saved to a recovery folder before transcription
  starts, and a transcript that cannot be safely inserted is kept for review.
- **Dictation Settings.** **Tools > Speech > Hold & Locked Dictation > Dictation
  Settings…** exposes the knobs the dictation engine reads: the Locked-Dictation
  time limit, the minimum hold needed to start (so an accidental F9 tap is ignored),
  stop-and-keep-speech when QUILL loses focus, intelligent insertion spacing, and a
  reset that shows the one-time first-use hint again.
- **Dictation History & Review.** **Tools > Speech > Hold & Locked Dictation >
  Dictation History & Review…** lists every recording whose transcript was never
  inserted — crash orphans and transcripts that couldn't be placed safely — so you
  can **insert** one at the cursor, **copy** it, or **discard** it (Enter inserts the
  selected row). If anything is awaiting review at startup, QUILL announces it and
  points you here, so dictated speech is never silently lost.
- **Distinct sound, one-time hint.** Locked Dictation plays its own earcons so a
  hands-free session sounds different from a press-and-hold one, and the very first
  time you dictate QUILL speaks a brief one-time hint about the keys.
- **Remappable.** F9, Ctrl+F9, and the rest are defaults; change them in the Keymap
  Editor (**Settings > Keyboard**). You need an offline speech model installed
  (**Tools > Speech > Manage Speech Models**) and the optional
  microphone-capture support; in Safe Mode dictation is disabled.
- **Hugging Face Token...** is optional. QUILL's speech models are open-source
  (MIT) and need **no Hugging Face account** to download. But if you fetch many
  models and hit Hugging Face's rate limits, a free access token raises them. The
  first time you open this, QUILL explains the steps — sign in or sign up at
  huggingface.co, open **Settings > Access Tokens**, create a token with the
  **Read** role — and offers to open the token page in your browser; then you
  paste the token. It is entered masked and stored in Windows Credential Manager
  (never in a settings file); leave the box blank to remove a saved token.

**Choosing a speech engine.** QUILL ships with the **whisper.cpp** engine and
uses it by default — nothing extra to install. You can add two more optional
engines, each by installing its dependency:

- **Faster Whisper** (`fasterwhisper` dependency) — a higher-throughput
  multilingual engine that runs in-process and uses your **GPU** automatically
  when one is present.
- **Vosk** (`vosk` dependency) — a **very low-resource, CPU-only English** engine
  that runs on a ~40 MB model with no GPU. Ideal for older or constrained
  machines where the other engines are impractical. Models download from
  alphacephei.com (verified HTTPS, integrity-checked) via Manage Speech Models.

When more than one engine is available, **Manage Speech Models** first asks which
**Speech Engine** to use; QUILL remembers your choice and applies it to
transcription, captions, and dictation. Each engine has its own models, so
download a model after switching. All engines run **entirely on your computer**.
Note that Faster Whisper does not label speakers — for speaker attribution, use
the whisper.cpp speaker-detection model.

The offline speech **engine ships with QUILL**: enable the *offline speech engine
(whisper.cpp)* component in the installer, or place the executable under
`tools\speech\whispercpp` in a portable copy — you do not need to install anything
separately or change your PATH. Then download a model from Manage Speech Models.
Offline **dictation** also needs microphone-capture support (the optional
`sounddevice` package); if it is missing, QUILL tells you and you can still use
Windows dictation. Because automatic transcription is never perfect, results are
always a draft to review.

##### Cloud transcription providers (optional, via Quillins)

The offline engines above keep everything on your machine. If you want a cloud
provider as well — for example **OpenAI Whisper** for its accuracy — install the
**OpenAI Whisper Transcription** Quillin (a bundled extension) and configure an
OpenAI API key in AI Hub. It then appears as a provider in Manage Speech Models.

Cloud providers are **opt-in and never silent**: audio is uploaded only when you
explicitly transcribe a file with that provider, never offline and never in Safe
Mode. The Watch Folder offline transcription automation always uses the
on-device engines only, so a cloud provider can never auto-upload your audio.
Extensions that add a provider ship no code and request no network permission —
QUILL itself performs the upload through its audited network path, so the
extension never sees your audio or your key. (Developers: see the Quillin guide,
"Transcription providers".)

#### Read Aloud with AI Voice (OpenAI, Google Gemini, or ElevenLabs)

`AI > Read Selection Aloud (AI Voice)` and `AI > Read Document Aloud (AI Voice)`
use a cloud text-to-speech service to speak your text in a natural, expressive
voice. This complements the on-device Read Aloud (which uses local voices like
SAPI 5, Piper, Kokoro, eSpeak, or DECtalk) with high-quality cloud voices.

Choose the provider, model, and voice under **Settings > Read Aloud**:

- **OpenAI** — 11 voices (Alloy, Ash, Ballad, Coral, Echo, Fable, Nova, Onyx,
  Sage, Shimmer, Verse) with `tts-1` (fast) or `tts-1-hd` (higher quality).
- **Google Gemini** — 30 voices (Kore, Puck, Aoede, Fenrir, Zephyr, and more)
  with Gemini 2.5 Flash (fast) or Pro (higher quality).
- **ElevenLabs (export only)** — premium, audiobook-grade narration with
  Multilingual v2 (high quality) or Turbo v2.5 (fast). ElevenLabs is used for
  **audio export**, not live reading; it needs the optional `elevenlabs` package
  (`pip install quill[elevenlabs]`) and an **ElevenLabs API key** credential (the
  same key the ElevenLabs transcription provider uses).

Add the matching API key for your chosen provider in AI Hub (ElevenLabs uses your
stored "ElevenLabs API key" credential).

- `AI > Stop AI Reading` cancels playback of the current TTS session.
- `AI > Export Document as Audio...` renders the full document to a file you
  choose — MP3 for OpenAI and ElevenLabs, WAV for Gemini. The status bar shows an
  estimated cost before the export runs. (If you pick ElevenLabs for *live*
  reading, QUILL reminds you it is export-only for now.)

Long documents are split only on sentence boundaries (never mid-word), so the
synthesized audio never cuts off at an awkward spot; Gemini exports add a short
trailing pause so the final sentence is not clipped.

Privacy: text is sent to the provider you select (`api.openai.com` or
`generativelanguage.googleapis.com`) in sentence-aware chunks. No audio is
stored by QUILL. See AI Privacy Reference for opt-out options.

#### AI Thesaurus (Ctrl+Alt+Shift+H)

`AI > AI Thesaurus...` (`Ctrl+Alt+Shift+H`) looks up synonyms for the selected word
using your configured AI provider. Unlike a static thesaurus, it reads the
sentence the word appears in and returns synonyms that match the actual meaning
in context.

To use it:
1. Place the cursor on a word, or select it.
2. Press Ctrl+Alt+Shift+H or choose AI > AI Thesaurus.
3. The dialog opens with the word pre-filled and synonyms loading.
4. Arrow through the list; each item shows the synonym and a brief usage note.
5. Press Enter or click Replace Word to substitute the word in your document.
6. Type a different word in the search box to look up another without closing.

Privacy: only the word (up to 80 characters) and the surrounding sentence (up
to 400 characters) are sent. The full document is never sent for thesaurus
lookups.

#### Document Q&A

`AI > Document Q&A...` opens a persistent (non-modal) dialog where you can ask
questions about your current document or a PDF/text file you choose.

- The dialog stays open while you work. Switch back to your document or other
  windows at any time.
- Ask follow-up questions; the conversation accumulates a history of Q&A pairs.
- The AI answers only from the document text (grounded responses only).
- Documents longer than 80 000 characters are analysed at the first 80 000;
  a notice is shown in the dialog.
- Answers include a source excerpt highlighting where in the document the
  answer comes from.
- Copy or Insert inserts the answer text at the cursor.

To analyse a PDF, click Browse File and select the file. The text is extracted
automatically (no internet connection required for extraction).

#### Agentic Document Tasks

The AI menu includes quick agentic actions that run a one-shot AI task on your
document or selection and show the result:

| Command | What it does |
|---------|-------------|
| AI > Rewrite Selection | Rewrites the selected text for clarity. |
| AI > Summarize Selection | Produces a concise summary. |
| AI > Expand Selection | Develops a brief outline or passage into fuller prose. |
| AI > Generate Table of Contents | Analyses the document and returns a hierarchical TOC in Markdown list format. |

All four open an Agent Result dialog where you can:
- View the output with a step log (if a refine pass was run).
- Insert at Cursor: inserts the result without replacing anything.
- Replace Selection: replaces the current selection with the result.
- Copy: copies the output to the clipboard.
- Re-Run: reruns the same task (useful if the first output was not right).

#### AI Hub

`AI > AI Hub...` is the central configuration panel for all AI settings.
It has five tabs:

- **Provider**: choose your AI provider (Ollama, OpenAI, Claude, Gemini,
  OpenRouter, or custom), enter your API key, set the model and host URL,
  and test the connection.
- **On-Device**: configure Ollama for fully local AI. Includes recommended
  models and the Ollama base URL.
- **Audio Services**: enter your Deepgram API key for speaker diarization,
  and set the default maximum number of speakers.
- **Instructions**: read, customise, and share the built-in system prompt for
  every AI task. See Custom Instructions below.
- **Advanced**: privacy consent summary listing every action that sends data,
  safe mode documentation, and a Reset AI Settings button.

For the full provider setup experience (per-provider key management, model
listing, and verification), use the Full Connection Settings button in the
Provider tab.

#### Custom Instructions (AI Hub > Instructions tab)

Every AI task in QUILL has a built-in default system prompt that tells the AI
how to behave. The **Instructions** tab in AI Hub lets you read, customise, and
share these prompts.

**What custom instructions are:**
Each instruction set is a plain-text system prompt that is automatically
prepended to every AI call for that task. For example, the spell check
instruction tells the AI to preserve technical terms and not flag British
spellings. You can extend, replace, or turn off these instructions.

**How to edit them:**

1. Open `AI > AI Hub...` and go to the **Instructions** tab.
2. Select a task from the list on the left (e.g. "AI Spell Check").
3. The built-in default appears in the lower panel for reference.
4. Type your custom instructions in the editor above it.
   - Leave the editor empty to use the built-in default.
   - Tasks with a custom override show a `*` in the list.
5. Use **Copy Default to Editor** to start from the built-in default and
   modify it rather than writing from scratch.
6. Use **Reset to Default** to discard your changes and go back to the
   built-in default.
7. Uncheck **Enable custom instructions for this task** to disable all
   instruction injection for that task (the AI gets the base prompt only).
8. Click **OK** to save. Changes take effect immediately.

**Built-in defaults — what each task gets:**

| Task | Default instruction focus |
|------|--------------------------|
| Ask Quill / Chat | Calm, direct expert partner; insert-only text returns without preamble |
| AI Spell Check | Copy editor: genuine errors only, preserve technical terms and consistent spellings |
| Grammar and Style | Professional editor: actionable issues, preserve author voice |
| Rewrite | Improve clarity without erasing author voice; no added content |
| Summarize | One-fifth length, same register, core argument only |
| Expand | Develop into richer prose, match tone exactly |
| Table of Contents | Explicit headings only, Markdown hierarchy, no invented structure |
| Translate | Natural expression over literal fidelity, preserve formatting |
| AI Thesaurus | Contextual synonyms ranked by interchangeability, register noted |
| Document Q&A | Grounded answers only; "not in document" stated explicitly |
| Research Agent | Key points, assumptions, gaps, and suggested next actions |
| Accessibility Tune-Up | Plain language, short sentences, descriptive text suggestions |

**Sharing instructions:**
Custom instructions are stored in `<AppData>/Quill/ai_custom_instructions.json`.
You can copy this file between machines or share individual task prompts with
other QUILL users.

#### How custom instructions reduce cost: prompt caching

QUILL sends every custom instruction as a separate system message, not mixed
into the document text. This lets your AI provider cache the stable instruction
prefix across requests, so you are not billed for re-sending the same
instructions on every call.

- **Anthropic Claude**: QUILL marks the system message with
  `cache_control: ephemeral` and sends the required beta header. Claude caches
  the prefix for five minutes. Each cache hit is billed at approximately 10% of
  the normal input token cost. If you run several AI tasks in a session, the
  instruction text is typically served from cache on every call after the first.
- **OpenAI (GPT-4o and later)**: caching is fully automatic. OpenAI caches
  prompt prefixes that exceed 1024 tokens and re-uses them within a session
  at approximately 50% of the normal input cost. Because the system message is
  always the same stable text, it qualifies for caching whenever the threshold
  is reached.
- **Ollama / local models**: caching is handled internally by the model server.
  No special setup is needed; the system message is sent once per connection.
- **Gemini**: system instructions are sent via the dedicated
  `systemInstruction` field. Caching behaviour depends on Google's current
  context-caching policy.

You do not need to configure anything to benefit from caching. As long as at
least one custom instruction is enabled (or the built-in defaults are active),
QUILL automatically uses the caching path for every supported provider.

### AI Privacy Reference

Every AI action in QUILL is explicit — nothing runs in the background without
your request. This section describes exactly what each action sends and where.

| Action | Data sent | Service | Opt-out |
|---|---|---|---|
| AI Spell Check | Document text (chunked at ~60 000 chars) | Your configured AI provider | Do not invoke the action |
| AI Grammar Check | Document text (chunked at ~40 000 chars) | Your configured AI provider | Do not invoke the action |
| Translate (AI provider) | Selected text or full document | Your configured AI provider | Use LibreTranslate instead |
| Translate (LibreTranslate) | Selected text or full document | Your LibreTranslate server (default: localhost) | — |
| AI Thesaurus | Word being looked up + one sentence of context (no full document) | Your configured AI provider | Do not invoke the action |
| Rewrite / Summarize / Expand / TOC | Selected text or full document | Your configured AI provider | Do not invoke the action |
| Document Q&A | Document text (up to 80 000 chars) + question | Your configured AI provider | Do not invoke the action |
| Read Aloud (AI Voice) | Selected text or document (split on sentence boundaries) | OpenAI (`api.openai.com`), Google Gemini (`generativelanguage.googleapis.com`), or ElevenLabs (`api.elevenlabs.io`, audio export only), per your Settings > Read Aloud choice | Use a local voice (SAPI 5, Piper, Kokoro, eSpeak, DECtalk) |
| Transcribe Audio | Audio file bytes (up to 25 MB) | OpenAI Whisper (`api.openai.com`) | Transcribe locally with a Quillin extension |
| Speaker Diarization | Audio file bytes (up to 2 GB) | Deepgram (`api.deepgram.com`) | Disable diarization in the transcription dialog |

**What QUILL never does:**

- QUILL does not send data in the background. Every AI call is triggered by a
  specific, intentional user action.
- QUILL does not log your document content, API keys, or AI responses to any
  Anthropic or QUILL telemetry endpoint. QUILL has no telemetry.
- API keys are stored only on your device (Windows Credential Manager with
  DPAPI fallback). They are never sent to a QUILL server.
- The crash reporter (Help > Save Diagnostics) redacts API keys, file paths,
  and any text that looks like a secret before writing the diagnostic bundle.

**On-device alternatives:**

If you prefer to keep your text on your machine entirely:
- Use **Ollama (local)** as your AI provider. All spell check, grammar, and
  translation requests go only to your local Ollama instance.
- Use **LibreTranslate** (local install) for translation.
- Use **Piper** or **Kokoro** for Read Aloud — these are local voice engines.
- Avoid the Transcribe and Diarize actions, which require cloud services.

#### Reading & Dictation

- **Read Aloud** submenu for start or pause, stop, and voice selection
- **Stop Reading** stops current read-aloud immediately
- **Say Selected** reads the current selection aloud
- **Read All** reads from the cursor to the end of the document
- **Move cursor to follow Read Aloud** (Settings → Read Aloud) makes the cursor select each sentence as it is read, so the caret tracks what you hear and stops where the reading stopped. It is **off by default**: with a screen reader running, moving the selection makes the screen reader announce "selected" over the Read Aloud voice. Sighted and low-vision users who want the cursor to follow the reading can turn it on.
- **Dictation** submenu for Windows dictation, plus an opt-in **Hey QUILL Commands** toggle that lets dictation phrases trigger Quill commands instead of inserting text.
- **OCR Image...** converts an image to text via optical character recognition.

#### Watch Folder

- **Watch Folder Monitoring (in Settings)...** toggles automatic opening of supported files dropped into a configured folder.
- **Watch Folder Profiles...** configures folder path, subfolders, startup behavior, and polling behavior.
- **Watch Folder Queue...** shows current runtime state and active configuration.

Each watch profile runs one action on every file it claims. Besides opening,
moving, copying, converting, running a macro or a sandboxed transform, and OCR,
a profile can **transcribe arriving audio**: any audio or video file dropped
into the folder is transcribed on your machine with the offline speech engine
and a transcript is written next to it — nothing is uploaded. Choose the
**Transcript format** in the profile: plain **Text** (`.txt`), **SubRip captions**
(`.srt`), **WebVTT captions** (`.vtt`), or **Markdown** (`.md`). The caption
formats carry timestamps; if the engine returns no timed segments they fall back
to plain text so you never get an empty caption file. It needs no consent; if no
speech model is installed yet, the profile tells you to download one from
**Tools → Speech → Manage Speech Models**. (A separate
**Transcribe audio (OpenAI Whisper)** action is available for cloud transcription
when you have enabled AI and configured a key.)

Read Aloud is particularly useful for proofreading by ear. OCR Image handles image-to-text work with an explicit consent and progress flow.
Dictation uses Windows' own speech input. **Hey QUILL Commands** is a checkable menu item (Reading → Dictation): activate it to turn the feature on or off directly — Quill remembers the setting and announces "Hey QUILL voice commands on" or "off". When it is enabled, Quill stays silent and only listens while dictation is active, then runs the matching action after the wake phrase.
Watch Folder automation is best for "drop and open" workflows: copy supported files into one
folder and let Quill open them in the background.

#### Comparison

- **Compare with File...**
- **Compare Open Documents**
- **Next Difference** / **Previous Difference**
- **Announce Current Difference**
- **Difference List...**
- **Toggle Synchronized Navigation**
- **Compare Options...**
- **Create Difference Summary**
- **Copy Current Difference** / **Copy All Differences**

Quill's compare model is practical and local. It supports file-to-file review, multi-document review, summary generation, and synchronized movement through differences.

When a comparison is open you can move through it from the keyboard: **Ctrl+Alt+Shift+.** for the next difference, **Ctrl+Alt+Shift+,** for the previous one, and **Ctrl+Alt+Shift+D** to read the current difference. The compare dialog is a keyboard-first list you can review with a screen reader, one difference at a time.

If you use a sound pack, compare mode also plays short earcons: one when a comparison opens, one when it closes, distinct ticks for moving to the next or previous difference, and a soft "blocked" tone when you reach the first or last difference with nothing further to show. You can turn any of these on or off individually in **Tools → Reading & Dictation → Manage Sound Events...** under the Compare section. See [Sound notifications and earcons](#sound-notifications-and-earcons).

#### Braille

- **Status** — Read Braille Status, Read Detailed Braille Status, Read Current Line and Cell, Read Current Braille Page, Read Current Print Page, Read Progress Summary.
- **Navigation** — Go to Braille Page…, Next Braille Page, Previous Braille Page.
- **Page Tools** — Insert Braille Page Break, Remove Braille Page Break, Recalculate Page Map, Normalize Line Endings (placeholder).
- **Translation** (requires the optional QUILL Braille Pack) — a dynamic submenu organized into UEB (Contracted and Uncontracted), Standard American English Legacy (Contracted and Uncontracted), and More Languages (populated from the installed pack). Hidden when the pack is absent or in Safe Mode.

See [Braille and BRF Support](#braille-and-brf-support) for full details on translation and the Universal BRF Pack.

#### Advanced

The **Advanced** submenu (Tools > Advanced) is the expanded home for automation utilities, developer tools, and editor-behavior power toggles.

**Editor utilities:**

- **Toggle Read-Only Guard** — prevents accidental edits to a document you are reviewing.
- **Toggle Clipboard Collector** / **Collect Clipboard Now** — accumulates clipboard entries into a running log.
- **Toggle Key Describer** — announces key names instead of performing actions; useful for documenting keystrokes.
- **Toggle Indentation Announcements** / **Infer Indentation...** — announces indentation level changes as you navigate.

**Macros:**

- **Start Recording** / **Stop Recording** — capture a sequence of editing commands.
- **Play Last Macro** — replay the last recorded sequence.
- **Manage Macros...** — name, edit, and organize saved macros.

Macros are ideal for repetitive cleanup: record once, replay as many times as needed.

**Authoring utilities:**

- **Regex Helper...** — full accessible dialog with recipe presets, plain-language pattern explanations, editable sample text, match previews with offsets, and one-step copy-to-Find-Replace.
- **Pandoc Conversion Wizard...** — converts supported source files into Markdown, HTML, or plain text that opens directly as a Quill tab.
- **External Tools and Format Support...** — explains what each supported helper unlocks, whether Quill can already see it, and the best first-touch setup path.
- **YAML Structure Editor...** — inspects and edits YAML front matter and structure files.

**Document Intake:**

- **Document Intake Report...** — answers how good an extraction was and whether the source likely contained structure that did not survive.
- **Review Extraction Quality...** — walks through extraction quality signals interactively.
- **Report Bad Extraction...** — escalates a source for manual cleanup or re-extraction.

These commands matter when Quill is acting as a trusted reader for imported formats. They help answer questions like: Is this document safe to quote from directly? Do I need to escalate for manual cleanup?

**Shell Integration:**

- **Install Shell Integration...** — registers Quill as a shell context-menu handler and protocol handler.
- **Remove Shell Integration** — unregisters shell extensions.

#### Accessibility

- **Accessibility Audit...**
- **Keyboard Trap & Tab-Order Snapshot...**
- **Validate Contrast...**
- **Link Inventory & Alt-Text Catalog...**
- **Speak Cursor Address**, **Speak Document Status**, and **Speak Selection Length** announce the caret position, document state, and selection size to your screen reader.

These tools help review the editor experience itself, the current document's link surface, and low-vision presentation issues.

#### Customize & Support

- **Preferences...**
- **Customize Menus...**
- **Profiles and Features...**
- **Status Bar Layout...**
- **Export and Back Up...** / **Import or Restore...**
- **Keymap Editor...** / **Export Keymap...** / **Import Keymap...** / **Reset Keymap**
- **Show Notifications**
- **Save Diagnostics...**
- **Open Logs Folder** / **Open Diagnostics Folder**
- **Report a Bug...**
- **Check for Updates**

Customize & Support merges the former separate Support and Customize submenus. All configuration and support paths live in one place, which is where both users and support staff expect to find them.

### Window

The **Window** menu is small but useful.

- **Next Document** (`Ctrl+Tab`) — move to the next open document.
- **Previous Document** (`Ctrl+Shift+Tab`) — move to the previous open document.
- **Go to Document 1–10** (`Alt+1` … `Alt+9`, and `Alt+0` for the tenth) — jump
  straight to a document by its position instead of cycling. If no document is
  open at that position, QUILL says so and stays where you are. Like every
  shortcut, these are remappable in the Keymap Editor.
- **Send to System Tray** — hide QUILL to the notification area without closing it.
- **1: filename.txt (active)**, **2: other.md**, … — every open document appears directly on the menu, numbered. Press `Alt+W` to open the Window menu and then the number key to jump straight to that document. The active document is marked. The list updates automatically when you open or close a file, and updates the name immediately when you save an untitled document.

When you are juggling multiple notes, extracted files, and audit previews, these commands keep the workspace feeling controlled.

### Help

The **Help** menu is where Quill becomes a guide.

- **Open User Guide** opens this guide as an in-app document.
- **Open Welcome Guide** opens a lighter, profile-aware getting-started document.
- **Open Keyboard Reference** generates the current live shortcut reference from the active command registry.
- **Save Diagnostics...** writes a local diagnostics bundle you can review before sharing.
- **What Can I Do Here?** gives context-aware assistance.
- **Why Don't I See a Feature?** explains profile-driven feature visibility.
- **Feature Profiles** commands let you switch profile, run health checks, undo the last profile change, reset to Essential, and run onboarding.
- **Personalise QUILL...** (the first-run setup wizard) can be rerun at any time to adjust your keyboard pack, feature profile, remote access, AI, reading and accessibility, writing tools, data location, and startup behaviour.
- **Report a Bug...** opens an in-app review screen, copies the environment summary to the clipboard, and then opens the Community Access support-hub issue form.
- **Check for Updates...** verifies the signed update manifest, offers the download, and can close Quill so setup can run immediately. If you are running the **portable** build, QUILL recognises this and offers the portable `.zip` for the new version instead of pushing the installer at you — it downloads to your updates folder with an **Open folder** button so you can swap it into place. Installed copies keep receiving the installer.
- **About Quill** shows version, publisher details, and linked third-party dependency attribution with license and version metadata.
- **Open Third-Party Notices** opens a full notices document with dependency tables and bundled license texts.

If you only remember one thing about Help, remember this: it is a working surface, not a dead-end menu. The welcome guide teaches the basics, the keyboard reference reflects your live bindings, the user guide gives the full map, diagnostics package the current state, and the bug-report action turns that state into a support-ready starting point.

Menu stability note: Quill now defers internal menu-state updates while native menus are open, then applies them after menu close. This prevents rapid-arrow navigation churn and keeps Help menu navigation stable.

> **0.7.0 Beta 2 (macOS):** the **Help** menu is now registered as
> the macOS system Help menu, so the conventional `Cmd+?` shortcut
> works. See [Recent Fixes](#recent-fixes-in-070-beta-2) for the full
> list.

### How to report a problem from inside Quill

Use this path when Quill is behaving unexpectedly or when you want to send the team a feature request.

1. Open **Help -> Report a Bug...**. Focus lands on the Summary field, ready to type.
2. Optionally fill in your name and contact email. Quill remembers these and pre-fills them next time, so you only enter them once.
3. Pick your screen reader from the list (None, JAWS, NVDA, Narrator, VoiceOver, or Other). Quill pre-selects the one it detects. The choice is included in the report so the team can reproduce screen-reader-specific issues.
4. Read the in-app report summary Quill prepares for you.
5. Choose whether to include diagnostics, and whether to include plain file paths.
6. If diagnostics are included, save the diagnostics bundle to a location you can find again easily.
7. Choose **Open Support Form**.
8. When the Community Access support page opens, describe the problem, what you expected, and what actually happened.
9. Attach the diagnostics zip if it is relevant to the issue.

This unified flow keeps support reporting in one place. If you only need diagnostics, **Help -> Save Diagnostics...** remains available as a standalone export command.

### When QUILL crashes: the new crash-submit dialog

When an unhandled exception closes QUILL, a dialog now appears during the beta phase so you can review a redacted summary and choose whether to send it to the developers.

1. A native dialog appears with the heading **Report Crash**.
2. The dialog opens with a read-only **Report preview** panel showing the redacted summary: the last 10 commands you ran, the active document's name and encoding, the platform and screen-reader information, and the last 12 frames of the traceback. Personal data and credential-shaped strings are scrubbed before the preview is rendered.
3. Three free-text fields are ready to type into: **What were you doing when this happened?**, **What command do you think triggered it?**, and **Expected behaviour**. Each field is redacted before the report is built, so a path or token you paste by accident never leaves your machine.
4. Three buttons:
   - **Don't send** (the default button) -- close the dialog, leave the local crash file in place, send nothing. Escape is also bound to this button.
   - **Copy to clipboard** -- put the same redacted summary on the system clipboard so you can paste it into a manual report.
   - **Send report** -- submit the redacted summary to the project's public issue tracker. This requires a configured GitHub token; if the token is absent the report is copied to the clipboard instead, and nothing is submitted silently.
5. The local crash file is always saved to `app_data_dir()/crash-reports/`, regardless of which button you choose. You can find it later from **Help -> Open Diagnostics Folder**.

If you do not want the dialog at all, turn it off in **Preferences -> General -> Offer to send crash reports automatically**. The local crash file is still saved; the dialog is the only opt-in here.

## Writing and Editing

Quill's editing model is fast once you stop thinking of it as only a textbox.

### Everyday editing

Use the familiar commands first:

- `Ctrl+Z` to undo
- `Ctrl+Y` to redo
- `Ctrl+X`, `Ctrl+C`, `Ctrl+V` to move text
- `Ctrl+A` to select everything

Quill adds two especially useful ideas on top of that.

### Repeat Next Command

When you need to do the same thing several times — move down twenty lines, delete ten words, insert forty dashes, or replay a macro — you do not have to press the key over and over. Choose **Edit → Repeat Next Command…**, type how many times, and the *next* command you run repeats that many times. Then the count clears automatically, so ordinary editing carries on as normal.

A few details:

- It works with almost any command, including movement, deletion, insertion, and a recorded macro.
- The count is capped at 1000, so a slip of the finger can never run away.
- It ships without a keyboard shortcut. If you use it often, assign one in **Preferences → Keyboard → Keymap Editor** (search for "Repeat Next Command").

This is the keyboard-first "Repeat" idea from the classic WordPerfect Editor, brought into QUILL.

### Restore Deleted Text

Undo (`Ctrl+Z`) puts the last edit back exactly where it was. Sometimes you want the opposite: you deleted a sentence, and now you want to drop it somewhere *else*. **Edit → Restore Deleted Text…** remembers the last three blocks you removed with QUILL's structured delete commands — delete to start or end of line, delete to start or end of document, and delete paragraph — and lets you pick one from a list and re-insert it at the cursor.

- The list shows each deletion newest-first with a short preview and its length, so you can tell them apart by ear.
- If there is only one remembered deletion, it is restored immediately with no list.
- Like Repeat Next Command, it ships unbound; assign a shortcut in the Keymap Editor if you like (search for "Restore Deleted Text").

This is the modern, place-it-anywhere form of the classic Editor's "Cancel" buffer.

### Copy Tray

Copy Tray is **twelve** independently addressable clipboard slots that survive application restarts. Each slot holds text you copy there explicitly. Unlike the system clipboard — shared across every application and reset on every copy — Copy Tray slots belong exclusively to QUILL and hold their contents until you replace or clear them.

**Pasting from a slot is a single chord: hold `Ctrl+Shift` and press a number key.**

| Key | What happens |
| --- | --- |
| `Ctrl+Shift+1` through `Ctrl+Shift+9` | Paste from slots 1–9 |
| `Ctrl+Shift+0` | Paste from slot 10 |
| `Ctrl+Shift+-` | Paste from slot 11 |
| `Ctrl+Shift+=` | Paste from slot 12 |

**Copying to a slot uses the QUILL key prefix followed by the same key with Shift:**

| Key | What happens |
| --- | --- |
| `Ctrl+Shift+Grave, Shift+1` through `Shift+9` | Copy selection to slots 1–9 |
| `Ctrl+Shift+Grave, Shift+0` | Copy selection to slot 10 |
| `Ctrl+Shift+Grave, Shift+-` | Copy selection to slot 11 |
| `Ctrl+Shift+Grave, Shift+=` | Copy selection to slot 12 |

**Multi-press paste.** Press the paste chord multiple times quickly:

- **Single press** — paste the slot's content at the cursor (standard behaviour).
- **Double press** — peek: QUILL announces the slot's content without pasting it. Useful to check what a slot holds before committing to a paste.
- **Triple press** — open the Copy Tray dialog directly, focused on that slot.

**Copy to Next Empty Slot.** `Edit > Copy Tray > Copy to Next Empty Slot` copies the selection to the first unoccupied (and unpinned) slot in order 1–12 and announces which one: "Copied to slot 4 (first empty)." If all twelve slots are occupied, QUILL tells you rather than silently overwriting anything.

**Search Tray Slots.** `Edit > Copy Tray > Search Tray Slots...` opens a small search dialog. Type any word or phrase; QUILL searches all slot text and labels and announces matching slots. Press the corresponding digit key to paste that slot directly, or Escape to cancel.

**Pinned slots.** From the Copy Tray dialog, any slot can be marked Pinned. Pinned slots:

- Are never overwritten by "Copy to Next Empty Slot" routing.
- Are announced with a "pinned" prefix: "Slot 1 (pinned — signature)".
- Persist the pin flag in `copy_tray.json` across restarts.

To pin or unpin a slot, open the Copy Tray dialog (`Ctrl+Shift+Grave, X`), select the slot, and use the Pin/Unpin button.

**Paste submenu slot labels.** The `Edit > Copy Tray > Paste from Tray` submenu shows the label and a text preview for every occupied slot: "1  signature — Hi, I wanted to follow..." Screen readers hear both the label and the preview when navigating the submenu.

**Open the tray dialog:** `Ctrl+Shift+Grave, X` (or `Edit > Copy Tray > Open Copy Tray...`).

The dialog lists all twelve slots. Each row shows the slot number, an optional label, and a preview of the stored text. Navigate with arrow keys. Buttons:

- **Paste** — insert the selected slot's text at the cursor. Also activated by double-clicking or pressing Enter on a row.
- **Paste from Clipboard** — store the system clipboard into the selected slot.
- **Pin / Unpin** — toggle the pin state for the selected slot.
- **Save Changes** — save edits made directly in the content area.
- **Clear Slot** — empty the selected slot.
- **Close** — close without pasting.

**Status bar.** The `Slots: X/12` cell in the status bar shows how many of the twelve slots are occupied. Click the cell to open the Copy Tray dialog. Add the cell via `Tools > Customize & Support > Preferences > Status Bar` if it is not visible.

**Tray icon access.** The system tray icon menu also includes a Copy Tray submenu listing all occupied slots. Click any slot entry to paste its content into the active editor. This makes QUILL's clipboard available from the tray without bringing the window to the front.

**Tips.**

- Keep a signature, disclaimer, or standard heading in slot 1 and pin it. One chord pastes it anywhere and "Copy to Next Empty Slot" will never overwrite it.
- Use labelled slots for a research session: slot 1 "intro quote", slot 2 "methodology note", slot 3 "source URL". Copy one fragment per slot as you read, then paste in order when drafting.
- Double-press any paste chord to hear what is in that slot without pasting — useful when navigating your tray by memory.
- Slots survive restarts. Build a small library of recurring fragments you reach for daily.
- All bindings are reassignable in the Keymap Editor (`Tools > Customize & Support > Preferences > Keyboard`).

### Import and Export

QUILL can convert between the formats the people around you actually use, without you leaving the editor. **File > Import** brings a non-QUILL document into QUILL as a new tab. **File > Export** saves the current buffer as a different file type. Both routes use Pandoc on a background thread, so the editor never freezes.

**Import (File > Import):** Markdown, CommonMark, GitHub-Flavored Markdown, HTML, Word documents (`.docx`), OpenDocument Text (`.odt`), Rich Text (`.rtf`), plain text, CSV / TSV tables, EPUB books, LaTeX / TeX.

**Export (File > Export):** the same set plus PDF and a **DAISY Talking Book** (both export only).

A few minutes of muscle memory covers most workflows:

- Pick **File > Import > Word Document**, choose a `.docx`, and a new Markdown tab opens with the document ready to edit.
- Pick **File > Export > EPUB Book**, choose a folder, and QUILL writes an EPUB next to your current file.
- Pick **File > Export > PDF** to publish a finished document.

**DAISY Talking Book export.** **File > Export > DAISY Talking Book** saves the current document as a DAISY 2.02 text-only talking book — the accessible book format read by DAISY software and by hardware players such as the Victor Reader Stream, Plextalk, and APH units. A DAISY book is a *folder* rather than a single file, so the name you choose becomes a folder holding `ncc.html`, `content.html`, and `book.smil`. Your headings become the player's navigation points, and Markdown styling is flattened to clean readable text. The book carries no audio, so a player reads it with its own text-to-speech; you can also open the folder in APH Book Wizard Producer to record or synthesize a full text-and-audio book. This export reads what is on screen, so you do not have to save first.

**Single-file keyboard path.** `File > Import` and `File > Export` are regular menu items — open the menu, arrow down, press Enter. There is no single shortcut for the whole list, because the format choice is the whole point of the command. The Command Palette (`Ctrl+Shift+P`) is the fastest path: type `import` or `export` and pick the format from the filtered list.

**Post-conversion prompt.** When the target format is editable in QUILL (Markdown, CommonMark, GFM, HTML, plain text, CSV / TSV) the editor asks whether to open the new file in a new window. Press **Yes** to open, **No** to keep working where you were. PDF, DOCX, EPUB, ODT, and RTF do not prompt because QUILL cannot edit them directly; a confirmation message tells you where the file landed and copies the path to the clipboard so you can paste it into File Explorer.

**Out of scope.** PDF *import* is intentionally not supported — Pandoc cannot do it reliably, and the dedicated braille and DAISY pipelines are the right tools for print-to-braille conversion. For every format Pandoc supports that is not in the Tier-1 list, open **Tools > Pandoc Conversion Center...** for the roadmap note.

### Batch Conversion

When you have a folder full of documents to convert, opening them one at a time is not the right tool. **File > Import > Batch Conversion...** (or **File > Export > Batch Conversion...** - both lead to the same wizard) opens a four-page wizard that converts a whole folder of files on a background thread. The chord is **QUILL key, B**.

**The wizard, page by page.**

1. **Introduction.** A short summary, then a live Pandoc version probe. If Pandoc is not installed, the page says so and Start stays disabled until you install Pandoc 3.x from <https://pandoc.org>.
2. **Folder and options.** A folder picker, an **Include subfolders** checkbox, an **Output layout** radio (Same folder as source, or Output subfolder per source folder), and an **Overwrite** radio (Ask each time, Never, Always). Defaults come from Settings, so the wizard respects your preferences the moment it opens. The last folder you used is remembered for next time.
3. **Format and profile.** A **Direction** radio (Import into QUILL, or Export from QUILL), a source-format list and a target-format list drawn from the Tier-1 set, and a profile picker for the seven built-in conversion profiles.
4. **Review and start.** A plain-text summary of the entire plan. Press **Start** to submit the batch and close the wizard.

**Output naming.** QUILL keeps the originating stem and replaces the extension. `report.docx` becomes `report.md` (or `report.html`, `report.epub`, ...). With **Output subfolder per source folder** (the default) the output lands in a new `Output/` folder inside the source folder; with **Same folder as source** it lands next to the input.

**Profiles.** The wizard's profile picker offers seven curated profiles. Each profile is a small set of Pandoc CLI flags plus a plain-language description that the screen reader reads aloud before you click Start.

- **Clean Word Document** — `report.md` becomes a polished Word document with no Markdown scaffolding in the output.
- **Accessible HTML Page** — a single HTML page with title block and `lang` metadata, ready for an accessibility audit.
- **EPUB Book** — a personal-publishing-ready EPUB with a table of contents and EPUB-3 metadata.
- **GitHub README** — GitHub-Flavored Markdown with no wrapper, ready to paste into a repository.
- **Print PDF** — a PDF with standard PDF metadata; Pandoc picks the right engine for your platform.
- **Instructor Handout** — a print-ready PDF with 1-inch margins and a numbered top-level section structure.
- **Plain Text for Screen Readers** — plain text with no HTML wrapper, no smart quotes, fixed 80-column width; the right choice for piping into a TTS engine.

**Overwrite behaviour.** The three-way policy keeps the screen reader out of the per-file prompt loop:

- **Ask each time** — QUILL lists every output that would clobber an existing file and asks once with a single yes/no. If you say no, the rest are skipped.
- **Never** — existing outputs are skipped automatically. The Status Page shows the count under *skipped* so the total still adds up.
- **Always** — existing outputs are overwritten without prompting. Useful for re-running a batch with the same plan.

**Live progress and completion announcement.** The batch runs on the background task pool. Open the Status Page (`Help > Status Page`) and the Tasks & Downloads tab shows live rows. The first row is `Batch conversion: scanning <folder>`, then one row per file as the work progresses.

When the batch finishes, QUILL speaks a single completion line through the announcement backend you have configured. The line names the converted / skipped / failed counts and the elapsed time:

> "Batch conversion complete. 12 of 14 files converted in 4.2 seconds. 2 skipped."

The spoken line respects the verbosity settings under **Preferences > Accessibility**; the Status Page row updates regardless so sighted and low-vision users see the same result. A short report dialog lists every file that produced warnings or failed, with the exact error string.

**Settings: defaults the wizard can override.** Three Settings entries let you choose defaults the wizard uses when it opens:

- **Include subfolders in batch conversion** — boolean, default `True`.
- **Overwrite behaviour for batch conversion** — Ask each time (default), Never, or Always.
- **Default output layout for batch conversion** — Output subfolder per source folder (default) or Same folder as source.

The wizard can override any of them per run. Preferences is the canonical place to change defaults; the wizard is a one-off override path.

**When to use the wizard, when to use single-file.** Use the single-file Import and Export menus for one document at a time. Use the wizard when you have a folder of documents to convert, when the work is the same for every file, and when you can let it run while you keep writing.

### Abbreviation Expansion

Abbreviation Expansion is a TextExpander-style feature. You type a short trigger word followed by any delimiter character (space, period, comma, and so on) and QUILL silently replaces the trigger with the full text.

**Off by default.** So that text never changes as you type without your knowledge, abbreviation expansion is **disabled by default** — turn it on when you want it (see *Enabling and disabling* below). Once on, your choice is remembered.

**Example:** type `btw ` (note the trailing space) and QUILL replaces it with `by the way `.

QUILL ships with fifteen built-in abbreviations covering common shorthand. You can add, edit, and disable any abbreviation, including the built-in ones.

**Built-in abbreviations.**

| Abbreviation | Expansion |
| --- | --- |
| `afaik` | as far as I know |
| `afaict` | as far as I can tell |
| `asap` | as soon as possible |
| `atm` | at the moment |
| `btw` | by the way |
| `fwiw` | for what it's worth |
| `imo` | in my opinion |
| `imho` | in my humble opinion |
| `irl` | in real life |
| `omw` | on my way |
| `tbh` | to be honest |
| `tbc` | to be confirmed |
| `tbd` | to be determined |
| `ttyl` | talk to you later |
| `wrt` | with regard to |

**Enabling and disabling.** Abbreviation expansion is **off by default**; enable it any of these ways (and toggle it the same ways later):

- Press `Ctrl+Shift+Grave, E` — or use `Insert > Toggle Abbreviation Expansion`.
- Click the **ABR: On / ABR: Off** cell in the status bar (if visible; add it via status bar settings).
- Change **Abbreviation expansion** in `Tools > Customize & Support > Preferences > Editing`.

**Managing abbreviations.** Open `Insert > Manage Abbreviations...` (or press `Ctrl+Shift+Grave, Shift+A`) to add, edit, and organise your abbreviations. Each abbreviation has:

- **Abbreviation** — the short trigger word, e.g. `btw`.
- **Expansion** — the full text to substitute, e.g. `by the way`.
- **Description** — optional note for your own reference.
- **Case sensitive** — when checked, only the exact-case trigger matches; otherwise any capitalisation of the trigger fires.
- **Enabled** — toggle individual abbreviations without deleting them.

The manager dialog includes a **Search** field at the top. Type any part of a trigger word or expansion text to filter the list in real time. Disabled abbreviations appear with a "(disabled)" suffix.

The manager also has **Import** and **Export** buttons for JSON round-trips. Export saves your full library to a file. Import merges a file into your library; abbreviations with duplicate IDs are skipped. QUILL announces how many were added on import.

**Manual trigger.** Press `Ctrl+Shift+Grave, A` (or `Insert > Expand Abbreviation`) to expand the word immediately before the cursor without typing a delimiter character. Useful when you want expansion mid-word or at end-of-document.

**Variables in expansions.** Expansions support these placeholders:

| Placeholder | Inserts |
| --- | --- |
| `${cursor}` | Places the cursor here after expansion |
| `${date}` | Current date (e.g. June 11, 2026) |
| `${time}` | Current time (e.g. 02:30 PM) |
| `${clipboard}` | Current system clipboard text |

**Multi-press window.** The double/triple press detection window is configurable in `Tools > Customize & Support > Preferences > Editing` as **Multi-press window (ms)** (default 400 ms; range 100–1000 ms). A larger window helps if you press keys slowly; a smaller window prevents accidental double-fires for fast typists.

**Sound feedback.** Optional: enable **Play sound on abbreviation expansion** in `Tools > Customize & Support > Preferences > Editing` and optionally point **Abbreviation expansion sound file** to a `.wav` file. Leave the path blank for the default system beep.

**Quillin-contributed abbreviations.** Installed Quillins can add their own abbreviations to the registry. These are listed in the Insert Automation Reference and can be disabled per-Quillin in the Quillin's own preferences page (open **Preferences**, Ctrl+Comma, then navigate to the Quillin by name). Your own abbreviations always take priority over Quillin-contributed ones; if two Quillins claim the same trigger, the conflict is visible in the Conflict Manager.

The bundled **Smart Insert** Quillin contributes five abbreviations by default:

| Trigger | Inserts |
| --- | --- |
| `qbug` | Bug report template (Title, Build, Screen reader, Windows version, Steps, Expected, Actual, Notes) |
| `qmeet` | Meeting notes template with today's date |
| `qlog` | Date and time timestamp |
| `qtodo` | Three-item to-do checklist |
| `qbrf` | Predictable BRF test document |

**Tips.**

- Use `${cursor}` to drop the cursor inside a template. For example, the abbreviation `sig` expanding to `Best regards,${cursor}Jeff` positions the cursor right after the comma.
- Use case-sensitive abbreviations sparingly — most triggers are lowercase and case sensitivity is rarely needed.
- Abbreviations fire before snippet expansion. If a word matches both, the abbreviation wins.
- Export your library regularly as a backup and to share abbreviations between machines.

### Insert Automation: Smart Triggers, Log Files, and Append Anchors

Insert Automation is the umbrella system that ties abbreviations, smart text triggers, `.LOG` file support, and document anchors together into one keyboard-first platform. Every action it takes is announced, undoable, and triggered only by an exact match — nothing runs in the background, nothing scans your file without being asked.

#### Smart Text Triggers

A smart text trigger is a typed command that begins with `=`, appears alone on the current line, and expands when you press Enter. Because they start with `=`, they can never accidentally fire inside a sentence.

The bundled **Smart Insert** Quillin contributes these triggers out of the box:

| Trigger | Inserts |
| --- | --- |
| `=bug()` | Bug report template |
| `=meeting()` | Meeting notes with today's date |
| `=journal()` | Journal entry with today's date |
| `=todo()` or `=todo(5)` | To-do checklist (5 items by default, or however many you specify) |
| `=logentry()` | Timestamp at the cursor, formatted by your Log Mode settings |
| `=brftest()` | Predictable multi-page BRF test document |
| `=rand(3,4)` | Three paragraphs of four readable sentences each |

**How to use.** Type the trigger alone on a line and press Enter. If the trigger matches, QUILL replaces the whole line with the generated text and announces what it inserted. If it does not match, nothing happens and the Enter key behaves normally.

**Large insertions.** If a trigger would produce more text than the configured threshold (default: 50 paragraphs), QUILL asks for confirmation before inserting anything. You can adjust the threshold in **Preferences → Smart Insert → General tab**.

**Enabling and disabling triggers.** Every trigger can be turned on or off individually in **Preferences → Smart Insert → Smart Triggers tab**. Disabling a trigger means the `=name()` text is simply left as-is rather than replaced.

#### `.LOG` File Compatibility

If the first line of a text file is `.LOG`, QUILL treats the file as a timestamped log — the same behavior Notepad has had for decades.

When you open a `.LOG` file QUILL:

1. Detects `.LOG` at the top of the file (in the first 4096 bytes).
2. Finds the best place to insert a new entry: a `QUILL-LOG-APPEND-HERE` anchor near the bottom of the file, or the end of the document if no anchor is present.
3. Inserts a fresh timestamp.
4. Places the cursor right after the timestamp so you can start typing immediately.
5. Announces "Log timestamp inserted. Type your entry."

Read-only files are never modified. `.LOG` in the middle of a file does not activate automatically. A UTF-8 BOM before `.LOG` is accepted.

**Timestamp format.** Configure the format under **Preferences → Smart Insert → Log Mode tab**:

- Long date and time (default): `Sunday, June 14, 2026 9:42 PM`
- Short: `06/14/2026 09:42 PM`
- ISO 8601: `2026-06-14T21:42:00`
- Date only, Time only, or a custom `strftime` pattern

**Custom format example.** Set Timestamp format to Custom, then enter `%Y-%m-%d %H:%M` to get `2026-06-14 21:42`.

#### Append Anchors

Any file can have a `QUILL-APPEND-HERE` marker near the bottom. When QUILL generates content that belongs at the end of the file — a log timestamp, a generated template, a BRF test block — it inserts the new content immediately before the anchor and leaves the anchor in place for next time.

This gives you a stable target that survives repeated use. Your footer notes, metadata, or closing instructions stay below the anchor; new content always lands above them.

A `.LOG` file can use the more specific `QUILL-LOG-APPEND-HERE` anchor to separate log-mode insertions from other generated content.

**To add an anchor.** Type `QUILL-APPEND-HERE` alone on a line near the bottom of your file. That is all — QUILL finds it automatically the next time content is generated for that file.

### Copy With Source

`Ctrl+Shift+C` copies the current selection, then appends a source reference that captures document context. If nothing is selected, Quill uses the current line. This is excellent for notes, review workflows, and evidence gathering.

### Selection bindings

**F8-based anchor selection**

Quill uses an anchor-based selection model:

| Key | Command | Purpose |
| --- | --- | --- |
| F8 | Start selection | Sets an invisible anchor at the cursor. |
| Shift+F8 | Complete selection | Selects from anchor to cursor and announces the span. |
| Ctrl+Shift+F8 | Reselect | Restores the most recent committed selection. |
| Alt+Shift+F8 | Go to start of selection | Moves the cursor to the selection start without changing it. |
| Ctrl+F8 | Copy all | Copies the full document. |
| Ctrl+Shift+A | Unselect all | Collapses the selection to the cursor. |
| Alt+F8 | Read all | Reads the document from the beginning. |

**Structural selection**

| Key | Command | Purpose |
| --- | --- | --- |
| (unassigned by default) | Select paragraph | Selects the paragraph at the cursor; announces scope and word count. Assign a key in the Keymap Editor or run it from the command palette. |
| Ctrl+Shift+B | Select block | Selects the indented block at the cursor. |
| Alt+Shift+Up | Expand selection | Grows the selection to the next structural unit (line to paragraph to block to document). |
| Alt+Shift+Down | Shrink selection | Reverses the last expand step. |

**Extend Selection Mode**

Extend Selection Mode makes movement commands extend the selection rather than move the cursor. Toggle it from the Selection menu (no default key; assign one in Preferences > Keyboard). When active, an **EXT** badge appears in the status bar.

**Mark ring**

The mark ring is a rolling stack of temporary jump points for in-session back-and-forth navigation:

| Key | Command | Purpose |
| --- | --- | --- |
| Ctrl+Shift+M | Set mark | Places a temporary mark at the cursor. |
| Ctrl+M | Pop mark | Jumps to the most recent mark and removes it from the ring. |
| Ctrl+Shift+X | Exchange point and mark | Swaps the cursor and the top mark position. |
| Alt+M | List marks | Shows all marks with line and column positions. |

**Named marks and review buffer**

Named marks are persistent within a session. Reach them via **Selection > Named Marks**:

- **Set Named Mark**: names and stores the current cursor position; announces line and column.
- **Jump to Named Mark**: choose from a list showing each mark's name and position; jumps on selection.
- **Open Review Buffer**: opens the active selection in a read-only dialog for non-destructive screen-reader paging. Requires a selection.

None of these have default key bindings. Assign them in Preferences > Keyboard, or use the Selection menu.

### Links

`Ctrl+K` inserts a format-aware link. `Ctrl+Enter` follows the link under the caret. In Markdown and HTML, this makes citation and cross-referencing much less tedious.

## Search, Replace, and Deep Navigation

Quill's search tools are both straightforward and layered.

### Standard search

- `Ctrl+F` opens search.
- `F3` finds next.
- `Shift+F3` finds previous.
- `Alt+F3` opens a find-all matches summary.
- `Ctrl+H` opens Replace; `Ctrl+Shift+H` replaces all.

### Search modes

Quill supports plain text, whole-word, wildcard, and regular-expression search. The Regex Helper explains the syntax when you need it. Search history is also preserved, so recurring search jobs get easier over time.

### Navigation that understands documents

Quill is excellent for large documents because it supports:

- line and page jumps
- block and heading movement
- bracket matching
- structural next and previous
- back and forward location history
- outline navigation
- bookmarks

When you combine this with marks and compare sessions, long-form review starts to feel much less fragile.

### Code-aware editing

When you open a source file, Quill loads a **language profile** based on the file extension. Recognised languages are HTML, Markdown, CSS, Python, JavaScript, TypeScript, C, C++, C#, PHP, Go, Rust, Kotlin, Shell, YAML, JSON, TOML, and SQL, with a plain-text fallback for everything else. The profile tells Quill how that language is tokenised so movement and announcements make sense for code.

- **Token navigation.** Move by code token rather than by word with **Next Token** and **Previous Token** in the Navigate menu. The caret lands on the next identifier, keyword, operator, or literal, which is far more predictable than character or word movement when you are reading code by ear.
- **Pairs with indentation tones.** Code-aware editing works well alongside the optional indentation tones described under [Sound notifications and earcons](#sound-notifications-and-earcons), so structure is carried by pitch while you move by token.

#### Setting the document language

Auto-detection follows the file extension, but you can **set the language yourself** for the current document — useful for an unsaved buffer, an unusual extension, or code you pasted into a plain `.txt` file. When you do, you get that language's full editing characteristics, not just token navigation:

- **Bold and Italic** insert the right markup (`<strong>`/`<em>` for HTML, `**…**`/`*…*` for Markdown).
- The **heading, table, list, and tag** menu items enable for HTML and Markdown.
- **Toggle Line/Block Comment** uses the language's comment syntax (`#`, `//`, `<!-- -->`, `-- `).
- **Heading and structure navigation, the outline, link insertion, and live preview** all follow the chosen language.

Three ways to set it, all equivalent:

- **Hotkey:** **Ctrl+Shift+L** opens the language picker (type-ahead; the current language is preselected).
- **Menus:** **Navigate → Set Document Language...** (the same picker), or **Format → Document Language**, a checkable list where you can switch with one keypress and see the active language at a glance.
- **Status bar:** the **Language** segment shows the current language — with **(set)** when you chose it yourself rather than it being detected — and pressing **Enter** on it opens the picker.

Choosing **Auto-detect from file** clears your override and goes back to following the file name. Setting a language is an *editing* aid: it never renames the file, so if you set HTML on a `.txt`, Quill reminds you to use **Save As** to save it as `.html`. The choice applies to the current tab and is not remembered after you close the file.

#### Automatic language detection (optional, off by default)

Quill can detect the language for you when you paste or type code into a plain `.txt` or untitled document. It is **off by default**; turn it on in **Settings → Editing → Auto-detect document language**, which offers four modes:

- **Off** — never detect (the default).
- **Hint in the status bar only** — quietly shows "Looks like HTML" in the status bar; nothing changes and nothing is spoken.
- **Suggest and announce, you confirm** — announces a dismissible suggestion ("This looks like HTML. Press Ctrl+Shift+L, then Enter, to set the document language."), and you decide.
- **Switch automatically** — sets the language for you and announces the change.

Detection runs a fraction of a second after you stop typing or pasting, looks at the content (the first several thousand characters), and is deliberately cautious: it only acts when it is confident, never guesses on ordinary prose, and **never** overrides a real file extension or a language you set yourself. It also learns lightly from the languages you use during a session. Unlike some editors, Quill never switches silently or relies on a visual-only hint — in every mode you either stay in control or hear what changed. (Braille files and pasted braille are not affected — braille has its own Braille Mode.)

### Abbreviation expansion (Emmet-style)

Three commands on the **Edit** menu expand compact markup abbreviations into full HTML or CSS, so you can write `ul>li.item$*3>a[href]{Item $}` instead of typing out a three-item list by hand.

- **Expand Abbreviation** expands the current selection in place, or — with no selection — the run of non-whitespace text immediately before the cursor. The expansion replaces that text in a single undo step, so one Undo reverts the whole thing.
- **Preview Abbreviation...** prompts for an abbreviation (pre-filled from the current selection, if any) and opens the result in a new tab without touching your document — a safe way to try something out.
- **Explain Abbreviation...** opens a plain-text, indented breakdown of what an abbreviation means — tag, id, classes, attribute names, and repetition counts — before you commit to expanding it. This is the fastest way to learn the grammar by ear rather than by trial and error.

The grammar supports the core Emmet operators: child (`>`), sibling (`+`), climb-up (`^`), grouping (`(...)`), multiplication (`*N`), and numbering (`$`, with `$$` for zero-padded numbers). Ids (`#id`), classes (`.a.b`), attributes (`[attr="value" bool-attr]`), and text content (`{...}`) all work the way you'd expect. Common tags pick up sensible default attributes when you don't specify them — `a` gets an empty `href`, `img` gets `src` and `alt` — and void elements like `br` and `img` never get a closing tag.

A handful of built-in snippets expand without going through the grammar at all: `!` for a full HTML5 skeleton, `!a11y` for an HTML5 skeleton with a skip link and `header`/`main`/`footer` landmarks already in place, `skiplink` for just the skip link, `form:a11y` for a labeled form field inside a fieldset, and `table:a11y` for a table with a caption and properly scoped header cells.

When the active document's file extension is `.css`, all three commands switch to CSS mode and expand a curated set of common shorthand instead — things like `d:f` for `display: flex;`, `pos:a` for `position: absolute;`, and box-model shorthand such as `m10-20` for `margin: 10px 20px;` or `mt-10` for `margin-top: -10px;`.

If an abbreviation can't be parsed, Quill reports exactly what it expected and where, on the status bar, rather than guessing or silently doing nothing.

### Quill Eraser

Quill Eraser (`Tools → Writing & Language → Quill Eraser...`) is a deterministic, rule-based text hygiene checker. It finds common mechanical writing problems — extra spaces, trailing whitespace, missing spaces after punctuation, excessive blank lines, and sentences that start with lowercase — and offers one-click fixes for each finding, with no AI or network call in the loop.

There is also a scoped version: `Quill Eraser on Selection...` runs only on the text you have selected. If nothing is selected, it offers to check the whole document.

#### What Quill Eraser checks

Each finding is reported with a confidence level (High, Medium, or Low) so you can prioritize what to fix.

| Rule | Confidence | What it catches |
|------|-----------|-----------------|
| Multiple spaces between words | High | Two or more spaces where one space belongs |
| Trailing spaces at end of line | High | Spaces or tabs at the end of a line |
| Space before punctuation | High | A space immediately before `,`, `.`, `!`, `?`, `;`, or `:` |
| Excessive blank lines | High | More consecutive blank lines than your configured maximum (default: 2) |
| Missing space after sentence punctuation | Medium | A sentence-ending `.`, `!`, or `?` directly followed by a letter |
| Missing space after comma, semicolon, or colon | Medium | A `,`, `;`, or `:` directly followed by a letter |
| Sentence starts with lowercase letter | Medium | A sentence or paragraph that begins with a lowercase character |

Quill Eraser never reports findings inside URLs, email addresses, file paths, code spans, decimal numbers, or times. When checking a Markdown file it also skips fenced code blocks, inline code, front matter, and link URLs.

#### Code files

If you open Quill Eraser on a code file (`.py`, `.js`, `.ts`, `.html`, and so on) a prompt appears. You can run safe trailing-whitespace checks only, or skip the check entirely. All prose-spacing rules are suppressed on code files unless you opt in to safe-only mode.

#### The review dialog

When Quill Eraser finds issues it opens a modeless review dialog. The dialog stays open while you work in the editor.

- The **findings list** shows each issue in order: confidence, type, and line number.
- Selecting a finding shows its detail in the pane below: what was found, what the fix is, and a plain-English description.
- **Apply Fix** applies the suggested fix and moves automatically to the next issue.
- **Ignore** hides the finding for this session without applying a fix.
- **Go to Issue** moves the cursor in the editor to the exact location so you can decide what to do yourself, with the issue text selected.
- **Previous / Next** navigate the list by keyboard.
- **Rescan** re-runs the engine after you have made manual edits.
- **Close** dismisses the dialog.

Every action is announced so screen-reader users always know what changed.

#### Settings

Four preferences in `Settings → Preferences → General` control Quill Eraser behaviour:

| Setting | Default | What it does |
|---------|---------|--------------|
| `hygiene_min_confidence` | `high` | Minimum confidence level to report. Set to `medium` or `low` to see more findings. |
| `hygiene_allow_double_space_after_period` | off | Suppresses the "multiple spaces" rule when exactly two spaces follow `.`, `!`, or `?` (two-space-after-period style). |
| `hygiene_max_blank_lines` | 2 | Maximum consecutive blank lines before a finding is raised. |
| `hygiene_rules_disabled` | (empty) | Comma-separated list of rule IDs to disable (e.g. `prose.lowercase_sentence_start,prose.missing_space_after_comma`). |

Rule IDs for the disabled list: `prose.multiple_spaces`, `prose.trailing_spaces`, `prose.space_before_punctuation`, `prose.excessive_blank_lines`, `prose.missing_space_after_sentence_punct`, `prose.missing_space_after_comma`, `prose.lowercase_sentence_start`.

## QUILL Quick Nav Mode

QUILL Quick Nav mode is a browse-style, cursor-only navigation layer for long documents. It is movement-only: it changes cursor location, never edits text.

There are two ways to enter Quick Nav mode:

- **Locked Quick Nav (the common path).** Press `Ctrl+Shift+Grave` twice in a row. The first press arms the QUILL-key prefix; the second press (QK-5) locks browse mode on, ignores the prefix timeout, and stays active until you press `Esc`. QUILL announces "QUILL browse mode locked. It stays active until you press Escape."
- **One-shot Quick Nav chord.** Press `Ctrl+Shift+Grave, N`. QUILL enters Quick Nav mode for the next move; if the `browse_mode_sticky` setting is on (SET-4), it stays locked until `Esc`; otherwise the mode expires when the QUILL-key timeout elapses.

Either way, once Quick Nav is active the mnemonic single-key bindings below work the same. The chord table at the top of the user guide and the cheat sheet (`Ctrl+Shift+Grave, ?`) are the live reference.

While the mode is active:

- `H` moves to the next heading.
- `Shift+H` moves to the previous heading.
- `1` through `6` move to the next heading at that specific level.
- `Shift+1` through `Shift+6` move to the previous heading at that specific level.
- `A` and `Shift+A` move by link anchor.
- `L` and `Shift+L` move by list container.
- `I` and `Shift+I` move by list item.
- `T` and `Shift+T` move by table.
- `Q` and `Shift+Q` move by block quote.
- `B` and `Shift+B` move by bookmark.
- `'` and `Shift+'` move by code block.
- `C` opens table of contents (Outline Navigator).
- `P` and `Shift+P` move by paragraph.
- `S` and `Shift+S` move by sentence.
- `Tab` and `Shift+Tab` move by block.
- `.` (period) repeats the last browse action.
- `]` jumps to the next line after the current list or table.
- `[` jumps to the line above the current list or table.
- `Esc` exits QUILL Quick Nav mode.

Behavior rules:

- This mode does not edit text.
- It only changes cursor location.
- If a target does not exist for the active surface, Quill announces that clearly.
- Find and replace commands return you to normal command flow automatically.
- After each move, Quill announces where you landed. **QUILL browse move detail**, in `Preferences -> Navigation`, controls how much detail that announcement gives: *Line and column* (default), *Line only*, or *Say nothing*.
- In `Preferences -> General`, **Preload QUILL browse cache in background** is on by default. If you turn it off, Quill builds the cache the first time you use Quick Nav.

How Quill tracks headings, lists, list items, paragraphs, and sentences:

- Quill creates a navigation index for the active document and reuses it until content or surface type changes.
- The index key is document text plus markup type, so unchanged documents do not pay repeated parse cost.
- Headings are parsed from Markdown and HTML heading structure.
- List-item anchors come from Markdown list markers and HTML `<li>` tags.
- Paragraph anchors come from blank-line boundaries in text/Markdown and block-level tags in HTML.
- Sentence anchors come from sentence-ending punctuation patterns.
- Table anchors come from Markdown table starts and HTML `<table>` tags.
- Block-quote anchors come from Markdown `>` quote starts and HTML `<blockquote>` tags.
- Code-block anchors come from Markdown fenced code boundaries and HTML `<pre>` or `<code>` tags.
- Bookmark anchors come from your in-memory bookmark positions.
- The index is invalidated after edits, full document replacement operations, and tab/document switches.

Performance note:

- Quick Nav avoids reparsing on every key press by caching artifact anchors.
- This keeps movement responsive on long Markdown and HTML files.

### QUILL key prefix actions

Pressing the QUILL key (`Ctrl+Shift+Grave`) once arms a short prefix. Follow it with:

- `N` to enter browse/Quick Nav mode. If the `browse_mode_sticky` setting is on, the mode stays locked until `Esc`; otherwise it expires on the QUILL-key timeout. (Press the QUILL key alone a second time to lock browse mode on regardless of the setting.)
- `G` to open Go to Anything (Quick Nav search). It lists every navigable
  element in the document — headings, links, lists, tables, block quotes,
  bookmarks, code blocks — with a category filter that shows a live count of
  each type. It also lists the document's **misspellings** and, when a search is
  active, the current query's **search hits** as their own navigable types, so
  you can jump straight to a misspelled word or a match from the same panel.
- `M` to **paste HTML clipboard content as Markdown** at the cursor. Quill reads the
  clipboard's rich HTML (the `HTML Format` flavour copied from web pages and word
  processors), converts headings, lists, links, bold/italic, code, and block quotes to
  Markdown, and inserts the result. If no rich HTML is present, the plain-text clipboard
  is treated as HTML. The active read-only guard is respected, so a read-only document is
  never modified.
- `A` for selection actions when text is selected.
- `F` to **speak the window title**, `P` to **speak the full file path** of the current document, and `Q` to **speak a short status summary**. These let you confirm where you are without leaving the editor, which is handy when several documents are open.
- `?` to show the QUILL key cheat sheet, or `Esc` to cancel the prefix.

## Formatting and Markup Work

Quill understands that many users work in plain text while still caring deeply about exported structure.

### Markdown and HTML awareness

Quill detects whether the current surface looks like Markdown, HTML, or plain text. It uses that to guide insertion helpers and enable the commands that make sense in context.

### Headings and lists

The heading tools do more than insert decoration. They help you maintain usable structure. The list tools speed up common authoring patterns without forcing you into a separate composer.

For inline heading control, press `Ctrl+Alt+1` through `Ctrl+Alt+6` to convert the current line to the matching heading level in Markdown and HTML surfaces. Press the same chord again on an already-matching heading to clear the level. The chord is documented in §10.2 of `docs/keybinding-standard.md` and overrides NVDA's switch-to-synth-1..6; if you use NVDA's synth switcher, you can rebind the QUILL heading chord via the Keymap Editor.

For section-level reorganisation in Markdown and HTML, press `Alt+Shift+Down` while the caret is on a heading to swap that section past its next sibling; `Alt+Shift+Up` swaps it with the previous sibling. The chord is gated on Markdown and HTML — plain-text documents announce the chord is unavailable and the move is skipped. Fenced code blocks are honored, so a `# fake` line inside a ``` fence is never promoted to a real sibling.

The previous `Alt+Shift+Up` / `Alt+Shift+Down` bindings (expand/shrink selection) live on `Ctrl+Shift+Grave, J` and `Ctrl+Shift+Grave, Shift+J` now; saved keymaps from older builds migrate automatically.

For list toggling, press `Ctrl+Alt+7` to insert or strip a bullet list, or `Ctrl+Alt+8` to insert or strip a numbered list. The chord inspects the caret's current line: if it is already a list item, the markers are stripped and the line returns to plain text; otherwise a new list is inserted at the caret. Numbered-list insertion honours the `list_auto_fill_numbers` setting (Preferences -> Editing -> Lists) — when the setting is on, every item gets `1. `, `2. `, `3. ` markers; when it is off, only the first item does. The chord is always available in markdown and HTML surfaces; plain-text documents announce the chord is unavailable and the action is skipped.

The status bar's `Section` cell reads `Section: Heading N (ordinal of total)` whenever the caret is on a heading in a Markdown or HTML document. The cell is hidden by default; turn it on via Preferences -> Status Bar. The cell is a no-op for plain-text documents and for carets on a non-heading line, and it inherits the same dead-widget guard as the other live-editor cells.

### Citations and bibliographies

For research writing, **Insert -> Insert Citation...** builds correctly formatted citations from details you type, so you do not have to wrestle with the punctuation and indentation rules by hand.

1. Choose the **source type**: Book, Journal article, or Website.
2. Choose the **style**: MLA 9, Chicago 17 (author-date), or APA 7.
3. Choose what to **insert**: the in-text citation, the full bibliography (Works Cited / References) entry, or both.
4. Fill in the source details — author(s), title, year, and the fields relevant to the source type. Separate multiple authors with a semicolon (for example `Jane Smith; John Doe`).
5. Choose **Insert**, and Quill places the correctly formatted citation at your cursor.

Quill applies the per-style rules for you — author order and "et al.", initials, italics, and where each comma and period belongs — so what lands in your document is ready to use. You supply the facts; Quill handles the formatting.

Markdown list editing now follows editor-standard behavior: `Enter` continues the current bullet/numbered/task item, and `Enter` on an empty list marker exits the list. When the caret is on a list item, `Tab` nests it and `Shift+Tab` promotes it. For larger reorganizations, use **Insert -> List -> List Manager...** (`Ctrl+Shift+Grave, L`) to move, promote/demote, add, edit, and delete list items from a tree view.

#### Structured List Studio (F2)

The **Structured List Studio** builds and edits lists by concept — item text, a
checked box, a term and its definition — and writes the correct Markdown or HTML
for you, so you never type `-`, `1.`, `[ ]`, `<ul>`, or `<dl>` by hand. Press
**F2** to open it (also at **Insert -> List -> Structured List Studio...**):

- With text selected, F2 turns the selection into a list — one item per line, or
  one per paragraph when blank lines separate them, detected automatically, with
  any existing bullet/number/task markers stripped. With nothing selected, it
  starts a new list.
- Choose the type — **Bulleted**, **Numbered**, **Checklist**, or **Definition
  (or description) list** — and the output format (**Markdown** or **HTML**). A
  read-only **Generated source** field shows exactly what will be inserted as you
  work, and the items/entries outline announces each item's text, number or checked
  state, and position.
- For definition lists, fill in the labelled **Term** and **Definition** fields;
  QUILL emits valid `<dl>`/`<dt>`/`<dd>` for HTML and a Pandoc-compatible syntax
  for Markdown. A term can hold several synonyms (one per line → multiple `<dt>`)
  and a definition several paragraphs (blank-line separated → multiple `<dd>`).
  Inserting the finished list is a single undoable edit.
- **Nest, reorder, and edit in place.** Indent / Outdent / Add child build nested
  lists, and Move up/down carries a whole subtree with its children. Press **F2**
  with the caret inside an existing list (no selection) to load that list back into
  the studio and rewrite just that block.
- **Convert and import safely.** Switching a list's type carries the content across
  and warns before dropping structure; **Import from clipboard** or **Import from
  file…** pulls text in with the live preview showing how it was interpreted; and on
  OK the studio reparses and validates the generated source, so a problem leaves
  your document unchanged with a clear message.
- When a Markdown **definition** list has no profile configured for the document,
  QUILL **asks** how to generate it — **embedded HTML** (the recommended portable
  choice), a specific **Markdown profile** (Pandoc / Markdown Extra / MultiMarkdown),
  or a plain **"Term: Definition"** list — rather than guessing a syntax your
  renderer may not support.
- Tune defaults and presets in **Insert -> List -> List Studio Settings...**: pick a
  shipped preset, adjust the high-value options (verbosity, markers, definition
  profile, loose lists), and export/import the configuration as JSON. Choose whether
  to save **for all documents** (the default the next F2 starts from) or **for this
  document only** (a per-document override of just the fields you changed). The
  document's format still picks the definition-list Markdown syntax automatically.

F2 was previously **Insert Special Character**, which is now **Shift+F2**; both
keys are remappable in the Keymap Editor.

For heading presentation control, open **Insert -> Heading -> Style Headings...**. You can style either all heading levels or the current heading level, then set font family, point size, and alignment. In Markdown documents, styled headings are written as HTML heading tags so the formatting is preserved.

For structure editing, open **Navigate -> Heading Organizer...** (`Ctrl+Shift+Grave, O`). The organizer lists each heading as level + title, supports keyboard promotion/demotion (`Tab` and `Shift+Tab`), lets you move sections up/down, rename headings, and validates heading order (start level, skipped levels, empty headings) before apply.

### Markdown profiles and table of contents

Markdown means different things to different writers: a poet wants every line break kept, a documentation author wants a table of contents, and a GitHub contributor wants task lists and strikethrough. **Format → Markdown** gives you a friendly way to talk about that without memorizing extension names:

- **Insert → Table of Contents** builds a table of contents directly from your document's headings — no AI involved, no network call, and the links always match the headings exactly because they are generated by parsing them, not by asking a model to summarize them. If your document has a `[TOC]` marker on its own line, the table of contents replaces it there; otherwise it is inserted right after your first heading. (If you would rather have an AI-written outline in its own words, that is still available as **AI → Generate Table of Contents** — the two commands are independent, and the AI one only appears when AI Assistance is enabled.)
- **Select Markdown Profile...** lets you choose a named profile — Standard Markdown, GitHub-Style Markdown, Documentation, Poetry and Lyrics, Accessible Publishing, Technical Writing, PRD and Release Notes, or Custom — instead of remembering which extensions a "documentation style" document needs. Quill announces what the profile turns on in plain language, for example "Markdown profile: Documentation. 5 extensions enabled."
- **Preserve Single Line Breaks** keeps every line break as a line break instead of letting Markdown collapse it into a flowing paragraph — turn this on for poetry, lyrics, speeches, and scripts where the line is part of the meaning.
- **Read Markdown Processing Status** announces your current profile and what it enables, without opening a dialog.
- **Select Citation Style...** chooses how the Author or Student profile prefers citations: Markdown footnotes (light weight, no new dependency) or full Academic bibliography entries through the existing **Insert → Insert Citation...** MLA / Chicago / APA form.

### Math Equations

**Insert → Insert Equation...** (`Ctrl+Shift+E`) inserts a mathematical formula at the cursor. The command is provided by the bundled `com.quill.bundled.math-equations` Quillin and supports two input formats.

**LaTeX** is the most common format for typeset mathematics. Type the formula using standard LaTeX notation and choose a display mode:

- **Inline** (`$...$`) — the equation appears within surrounding text. Example: `E=mc^2` becomes `$E=mc^2$`.
- **Block** (`$$...$$`) — the equation gets its own line with a blank line above and below. Example: `\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}` becomes `$$\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$`.

**MathML** is an XML-based format used in web publishing and accessible documents. If your input starts with `<math`, QUILL inserts it verbatim and skips the display mode step. Screen readers can read MathML directly without a visual rendering engine.

**Selection pre-fill:** If text is selected when you press `Ctrl+Shift+E`, QUILL checks whether the selection is a LaTeX equation. If it is, it strips the delimiters (`$` for inline, `$$` for block), pre-fills the prompt with the bare formula, and surfaces the detected display mode first in the choice list so you can confirm with one keypress.

**Rendering:** Browser Preview (`QUILL Key + V`) and HTML export inject a MathJax 3 script tag so equations render visually in any browser. The document source always contains the raw LaTeX or MathML, which your screen reader reads directly.

A collection of ten worked examples — quadratic formula, binomial theorem, integration by parts, Euler's identity, and more — is in `docs/math/latex_testing.md`.

### Tables, code blocks, and tags

Quill includes guided insertion for tables, code blocks, HTML tags, and Markdown snippets. This is especially useful for users who want structure but do not want to hand-type every opening and closing marker correctly every time.

### Cleanup and normalization

The cleanup commands under **Tools → Convert** are ideal for pasted material, transcripts, exports, and migration work. Use them when you need to turn messy text into something more stable and readable.

### Character encoding tools

Under **Format → HTML & Encoding**, Quill includes a full set of tools for the encoding friction that comes up when preparing text for the web, where one tool wants UTF-8 and the next insists on plain ASCII:

- **Show Non-ASCII Characters** opens a read-only report listing every character above plain ASCII, with its line and column, codepoint, Unicode name, and whether it converts cleanly to Latin-1 and to Windows-1252 (MS-ANSI). Reviewing that report with a screen reader replaces the old command-line trick of running a file through `iconv` with a sentinel string and hunting for what failed to convert.
- **Jump to Source Line** — while the Non-ASCII report is open and your cursor is on a character entry row (the format is `line:column` followed by a tab), invoke this command from **Format → HTML & Encoding → Jump to Source Line** to switch to the source document and land on the reported line. You can bind it to a key from the Keymap Editor for faster iteration.
- **Jump Back to Non-ASCII Report** — returns focus to the report tab after you have reviewed the character in the source. The round-trip lets you step through every flagged character without leaving the keyboard.
- **Convert Non-ASCII to HTML Entities** rewrites every non-ASCII character as its HTML entity — a named entity such as `&eacute;` where one exists, or a numeric `&#233;` otherwise — while leaving ordinary ASCII (including `&` and `<`) untouched. This is the reliable way to feed text to a tool, such as Pandoc, that refuses to handle high characters. Note that the older **Encode HTML Entities** command only escapes the five markup characters (`<`, `>`, `&`, `"`, `'`); this new command is the one that handles accents and symbols.
- **Decode HTML Entities** is the reverse direction: it turns entities such as `&eacute;`, `&amp;`, `&#233;`, and `&#xE9;` back into the real characters they represent — `é`, `&`, `é`, and `é` — using Python's standard entity table, so an unrecognized entity such as `&madeupword;` is left untouched rather than silently destroyed.
- **Re-encode As...** saves a copy of the document in a chosen encoding — UTF-8, UTF-8 with a byte-order mark, Latin-1, Windows-1252, or ASCII. Anything that does not fit a narrow target is written as a numeric HTML entity rather than a silent question mark, so the conversion is lossless and recoverable.
- **Analyze Encoding Requirements** answers "what is the smallest encoding I could save this in?" without committing to anything. It opens a short report: your current encoding, whether the document still fits it, and — if not — the simplest encoding in the order ASCII, Latin-1 / ISO-8859-1, Windows-1252 / MS-ANSI, UTF-8 that can hold every character losslessly.
- **Save Using Minimum Required Encoding...** saves a copy using exactly that encoding, so a document that only ever needed Latin-1 does not get forced into UTF-8 just because that is the modern default. You still choose UTF-8 explicitly any time you want it; Quill never switches you to it silently.
- **Remove Email Quote Markers**, **Strip Low ASCII Characters**, **Strip High ASCII Characters**, and **Convert to Hex Dump** round out the HTML & Encoding tools: the first strips leading `>` quote markers (including `Name>` style prefixes) left over from forwarded email threads; the next two remove control characters or non-ASCII characters respectively; and the hex dump opens a read-only offset/hex/ASCII view of the current selection (or the whole document) for inspecting exactly what bytes are present.
- **Convert OEM (DOS) to ANSI** and **Convert ANSI to OEM (DOS)** repair the classic codepage-mismatch problem where DOS-era text shows up as garbage in Windows, or the reverse, by reinterpreting the bytes between CP437 and Windows-1252.
- **Convert Line-Drawing Characters to ASCII** and **Strip Line-Drawing Characters** handle Unicode box-drawing characters (`─`, `│`, `┌`, and the rest of the U+2500–U+257F block) left over from old DOS-art or terminal output: the first maps them to plain `-`, `|`, and `+`; the second removes them outright.

### More search and analysis tools

- **Multi Replace...** under **Search** applies up to four search-and-replace pairs in a single pass, with an optional case-insensitive toggle, instead of repeating Find & Replace four times in a row.
- **Count Occurrences...** under **Search** reports how many times a string appears in the current selection or the whole document.
- **Line Statistics** under **Tools** scans the selection or document for lines that hold exactly one number and opens a short report — count, total, average, median, mode, and standard deviation. Lines that aren't plain numbers are skipped rather than causing an error.

## Tools for Reading, Review, and Inspection

Quill earns trust by making difficult files readable and inspectable.

### Describe Character at Cursor

Some characters look the same but are not: a curly "smart" quote versus a straight apostrophe, a no-break space versus an ordinary space, an invisible zero-width space that quietly breaks a search, or a stray byte-order mark pasted from the web. **Tools → Advanced → Describe Character at Cursor** opens an accessible dialog — in the same read-only style as F1 help, so your screen reader reads it all in one pass — describing exactly what sits under the cursor:

- its name (for example "No-break space" or "Right single quotation mark"),
- its Unicode code point in both hexadecimal and decimal,
- its category in plain language (uppercase letter, dash punctuation, control character, and so on), and
- a note for the invisibles that are easy to miss, plus a flag when the character is non-ASCII.

If the cursor is at the very end of the document, it tells you so rather than guessing. This is the screen-reader descendant of the classic "Reveal Codes" view. It ships without a shortcut; assign one in the Keymap Editor (search for "Describe Character") if you inspect text often.

### Reveal Codes

QUILL keeps formatting codes **hidden** so your editing buffer stays clean, fast plain text. **Reveal Codes** lets you see and hear every one of them on demand — the beloved WordPerfect feature, rebuilt for a screen reader. Press **Alt+F3** (or tick **View → Reveal Codes**) to open a pane below the editor that shows your document as an ordered stream of bracketed codes and text: `[Bold On]`, `[Font: Arial]`, `[Size: 14]`, `[Center]`, `[Heading 2]`, `[Link: …]`, `[Tab]`, `[¶ Hard Return]`, `[No-Break Space]`, `[Smart Quote]`, and so on. The editor itself does not change — Reveal Codes is a window onto the hidden scaffolding, not a different way of editing.

**Moving between the panes.** **F6** cycles through the regions — Editor → Reveal Codes (when shown) → Status Bar — and **Shift+F6** cycles back, exactly like switching windows. The two carets stay in sync: when you move in the Reveal Codes pane, the editor's cursor follows to the matching place, and when you move the editor cursor, the pane highlights the code or text you are on. So you can sit in the pane, arrow through the codes, and your place in the document tracks along.

**Hearing the codes.** Each code is its own labelled, individually-announced item — your screen reader says "bold on", "tab", "centred", "font Arial" as a single unit, never spelled out letter by letter. Within the pane you can:

- **Arrow up and down** to move through every code and text run in order.
- Jump **code to code** (skipping the plain text) to scan structure quickly.
- Jump from an opening code such as `[Bold On]` to its matching `[Bold Off]`, and hear how far the formatting reaches ("bold on, 12 characters").

**Two views and how chatty it is.** In **Settings → Editing** (or the View menu) choose:

- **Structured** (default) — one item per code in an accessible list. The clearest mode for a screen reader: discrete, labelled, unambiguous.
- **Flowed** — the codes rendered inline within the running text (`[Bold On]Hello[Bold Off]`), the closest match to the classic WordPerfect look and the most natural layout on a braille display.
- **Verbosity** — *quiet* (just the code name), *balanced* (adds an opening code's reach), or *detailed* (adds Unicode notes for invisibles).

Reveal Codes is **hidden by default** and costs nothing until you open it. Your choices of view and verbosity are remembered between sessions.

### Read Aloud

Read Aloud uses local voices with a deterministic support policy. The Windows system voice runs on **SAPI 5** and is always available offline with no download — it is the floor that keeps Read Aloud working immediately. **DECtalk**, **eSpeak NG**, **Piper**, and **Kokoro** (neural, offline) are available as explicit downloads from Speech Center, so base installs stay smaller. You can start, pause, stop, preview, and choose a voice. Speech onboarding announces current availability and recommended next actions before any download starts. For cloud voices, see [Read Aloud with AI Voice](#read-aloud-with-ai-voice-openai-or-google-gemini).

The **Kokoro** voice models (~120 MB), the classic **DECtalk** runtime (~2 MB), and the **eSpeak NG** engine with its voice data (~40 MB) are not bundled in the installer; the first time you choose one of these voices, QUILL downloads it for you from its own verified source (checksum-checked, with a cancelable progress window), and your other voices — including the always-present SAPI 5 system voice — keep working in the meantime. If you are **upgrading** from a version that bundled these, your existing copies are kept and keep working — you do not need to download anything.

To audition a voice in **Manage Voices**, select it and use the **Preview** button. If the voice is already downloaded, Quill synthesises the preview phrase with that voice's real model; if it is not downloaded yet (for example a Kokoro voice), Quill plays a short pre-recorded sample so you can still hear it before deciding to download. The rate, volume, pitch, and speed controls apply to real synthesis, so they stay dimmed until the voice is downloaded.

### Batch Export to Speech Audio

**Tools → Speech → Batch Export to Speech Audio** converts a whole folder of documents to speech audio in one pass. The conversion runs on a background task with per-file progress that you can cancel, and the same shared speech pipeline live Read Aloud uses — so the voice you audition is the voice you get.

In the dialog you choose:

- **Source folder** and whether to include subfolders, the **file types** to include (`.docx`, `.md`, `.html`/`.htm`, `.txt`), and optional **include/exclude filters** (semicolon- or comma-separated globs, matched against the file name and its path) plus a **maximum file size** to skip very large files.
- **Engine, voice, and pace** — any of the offline engines (SAPI 5, DECtalk, Piper, Kokoro, eSpeak NG), with a **Preview** button to hear the chosen voice first.
- **Output format** — **WAV** (always available) or, when `ffmpeg` is installed, **MP3, M4A, M4B (audiobook), Opus, FLAC, or OGG**. When `ffmpeg` is missing, compressed formats fall back to WAV with a per-file note rather than failing. MP3 has a selectable quality, and WAV can be conformed to a uniform sample rate / channel count.
- **Chapters** — turn a long document into a navigable, **chaptered** file. Choose **MP3** (ID3 chapter markers) or **M4B audiobook** (native MP4 chapter atoms — the Apple/audiobook format), both recognized by Apple Podcasts, Overcast, VLC, foobar2000, and others. Options include a **transition sound** between articles — a natural page-turn cue by default, or choose a different earcon from your active sound pack; whichever you use is matched to the audio format automatically so it always splices cleanly — whether each heading is spoken, and configurable pauses between articles and sentences plus an anti-clipping trailing pad. A very long section is split automatically on a safe sentence boundary so no single passage runs past the engine timeout, and the run report lists each document's chapter count.
- **Chapter mode** — keep the whole document as **one chaptered file**, or choose **Separate file per article** to write each heading-bounded section as its own `NNN - <heading>` audio file in a per-document folder.
- **Dry run** — instead of synthesizing, write a `<doc>.preview.txt` of the exact text that *would* be spoken (after cleanup, pronunciation correction, and polish) for each document, with the pronunciation-substitution count, so you can proofread what will be said before paying for slow synthesis.
- **Normalize loudness** — tick **Normalize loudness to audiobook (ACX) level** to bring every exported file to a consistent audiobook loudness, the same standard the Build Audiobook tool uses. QUILL measures each file and re-levels it (a two-pass process), without changing the chapters or their timing. Needs ffmpeg; if it's missing, the file is saved un-normalized with a note.
- **Combine empty headings** — when a heading has no body of its own (a "Part" heading immediately followed by a "Chapter" heading), fold it into the next article that *does* have text and join their titles ("Part One: Chapter 1"), so you don't hear an empty chapter. Off by default; turn it on with the **Combine empty headings into the next article** checkbox.
- **Also export in other languages (translated)** — produce a translated audiobook alongside the original. Choose a **language**, pick a **voice** for it, press **Add language**, and repeat for as many languages as you want; **Remove language** drops one. Voices are offered **local-first** (eSpeak speaks nearly every language offline, and any installed Windows voice for that language) followed by the **premium multilingual cloud voices — OpenAI, Gemini, and ElevenLabs** — which need the matching provider API key (the same key the AI Voice feature uses). Choose **Translate with: AI provider** (any AI provider you have configured) or **LibreTranslate** (runs locally). On Start, each document is translated and written as `<doc> (<Language>).<ext>` next to the original, with the same chapters, page-turn cue, and loudness. Pronunciation dictionaries can be scoped to a language so they only affect that language's narration. If a chosen cloud voice has no key configured, that language is skipped with a note rather than stopping the run.
- **You'll see the cost first for cloud runs.** Cloud translation and cloud narration are metered, so if your selections would use a paid cloud service, QUILL shows a **combined cost estimate** and asks you to confirm before it starts. Runs that use only local engines and LibreTranslate start straight away.
- **Round-robin voices** — read each article/heading in a *different* voice that cycles through a list you build. Pick a voice from the **Round-robin voices** combo box, press **Add voice**, and repeat; use **Move Up / Move Down / Remove** to set the order. Article 1 uses the first voice, article 2 the second, and so on, wrapping around. The list uses voices of the **engine you selected** (so everything stays one consistent audio quality); changing the engine clears it. Leave the list empty to use the single chosen voice as usual. Your combine and round-robin choices are remembered per project.
- **Audiobook metadata** — album, author/narrator, genre, and year stamped onto compressed files (each file's title comes from its heading or name, and its track number from its position).
- **If a file already exists** — **Skip** (cheap resume), **Overwrite**, or **Rename** so both are kept (`name (2).mp3`).
- **Output layout** — mirror the source folders or **flatten** into one folder, and optionally rename outputs with a **template** like `{index:03d} - {stem}` (→ `001 - chapter-one`).
- **Run report** — optionally write a `manifest.json` and `manifest.csv` listing every file's status, output path, duration, and any error.

A folder remembers its whole speech setup in `<folder>/.quill/speech-project.json` — engine, voice, output format, chapters, text cleanup, pronunciation dictionaries, metadata, and run policy — so you configure a project once and re-run it anytime. When you open the dialog for a folder you have tuned before, those settings **pre-fill automatically**, and your choices are **remembered when you press Start**; anything you change this run takes precedence over the saved profile, which takes precedence over your global defaults.

If a voice ever **fails to synthesize** — a broken system voice, a missing model, or a cloud voice the provider rejects — QUILL records it and **skips it on later runs**, so a single bad voice in a round-robin rotation can't keep stopping your batches.

### Export to Translated Speech Audio (one document)

**Tools → Speech → Export to Translated Speech Audio** is the single-document version of the translated export above: it translates and narrates **just the document you're editing**, without pointing at a folder. Pick the output format, choose **Translate with** (any configured AI provider, or local LibreTranslate), then add one or more **language + voice** targets the same way — local voices first, then the premium cloud voices. Press **Export** and QUILL writes `<doc> (<Language>).<ext>` next to your document. If the document has unsaved changes, QUILL offers to save first so your latest edits are the ones translated. As with the batch tool, a **combined cost estimate** is shown before any metered cloud run.

### Build Audiobook from a Folder

**Tools → Speech → Build Audiobook from Folder…** combines a folder of existing
audio files into one chaptered audiobook — the kind your audiobook or podcast app
navigates track by track. It complements Batch Export to Speech Audio: where that
converts documents to speech, this stitches a folder of audio (your own recordings,
or speech QUILL exported earlier) into a single master.

- Point it at a **folder of audio files**; each file becomes one **chapter**, in
  natural-sorted order, with the chapter title taken from the file name (a leading
  track number like `01 - ` is stripped).
- **Edit the chapters before building.** The dialog lists the chapters; you can
  **rename** the selected one (type a new title and press Rename or Enter), **move**
  it **up** or **down**, or **merge** it into the chapter above it (two files then
  play as a single chapter with one marker). The list is fully keyboard-operable.
- Choose **M4B audiobook** (native MP4 chapter atoms — the Apple/audiobook format)
  or **MP3** (ID3 chapter markers). Both are navigable in Apple Podcasts, Overcast,
  VLC, foobar2000, and others.
- Tick **Normalize loudness to ACX (Audible/audiobook) spec** to bring the master
  into the loudness range audiobook platforms require (RMS between -23 and -18 dB,
  peak under -3 dB). After the build, QUILL measures the result and reports whether
  it met the ACX window in the status bar.
- Fill in the book's **title, author, narrator, genre, and year**. A **cover image**
  in the folder (named like `cover.jpg`, `folder.png`, …) is picked up
  automatically, or browse for one.
- The build runs on a background task; the status bar reports when it is done.

**Tools → Speech → Manage Pronunciations…** lets you teach QUILL how to say specific words — names, brands, acronyms, and technical terms. Each entry is a substitution (literal or regular expression, optionally case-sensitive) that is applied as a silent text transform **before** synthesis, so a correction is heard **everywhere speech happens** — both batch export and live Read Aloud. Dictionaries can be **global** (all projects) or scoped to a single **project**, can target a specific engine, and you can **preview** an entry to hear the result. A small **starter dictionary** ships with common terms already covered.

### Text cleanup for speech

Real documents contain typography that makes speech engines stumble. QUILL's optional **text cleanup** pass (enable it in Read Aloud settings) deterministically fixes curly quotes, em/en dashes, ellipses, invisible spaces, ligatures, bullets, symbols, fractions, and emoji, and speaks **phone numbers, emails, and URLs** clearly — with a per-type choice to announce them, speak them, or speak-then-repeat an address so it is easy to catch. The cleanup runs first in the shared pipeline, so live Read Aloud and batch export sound the same.

### SSML Builder and SSML playback

For fine control over how a passage is spoken, the **SSML Builder** dialog composes `<speak>` markup — emphasis, pauses (`<break>`), say-as, phonemes, and prosody — from accessible controls with a read-only source preview, so you never hand-write the tags. Read Aloud plays this markup **natively on SAPI 5 and eSpeak NG**, so the pauses and emphasis take effect instead of being read aloud.

### EPUB Navigator

When you open an EPUB, the navigator gives you chapter-aware movement rather than forcing you to scroll blindly through one long extraction.

### OCR Image

OCR is explicit and local. You choose the image, confirm the action, and receive progress updates. This keeps OCR useful without making it invisible or surprising.

### Document intake and extraction quality

These commands are where Quill feels especially mature for accessibility-minded reading work. Rather than assuming every import is trustworthy, Quill gives you tools to ask whether the extraction is good enough, what may have been lost, and whether you should quote from the result directly.

## Verbosity and Announcements

QUILL lets you control what it announces and when, so the editor is as quiet or
as talkative as you want. Open **Verbosity Preferences** from the command palette
(`Ctrl+Shift+P`, type "verbosity") or assign it a shortcut in the Keyboard
Manager.

- **Profiles.** Pick a talkativeness level: **Beginner** (full context for every
  action), **Normal** (informative, the default), **Expert** (routine
  confirmations are suppressed, but errors always speak), or **Quiet** (speech
  and earcons off, leaving braille and the on-screen status bar). Switching
  profiles is announced.
- **Channels.** Choose which channels carry announcements — Speech, Braille,
  Sound — while **Visual** (the status bar) is always on and cannot be turned
  off, so you never lose the on-screen status of an action.
- **Quiet Mode** silences speech and earcons for a meeting or a shared room;
  **Meeting Mode** quiets sound further. A `[Q]` or `[M]` indicator shows when a
  mode is active, and the status bar keeps updating either way. **Undo Verbosity
  Change** steps back the last verbosity change. Toggle these from the Command
  Palette, or assign your own keys in the Keymap Editor; they have no default
  shortcut.
- **Less repetition, no floods.** Under **Preferences > Accessibility**,
  **Collapse repeated announcements** (on by default) stops QUILL from speaking the
  exact same announcement again when it repeats within a moment — for example when
  you hold a key at the top or bottom of a list. An optional **Announcement budget
  (per 5 seconds)** caps how many announcements are spoken in a burst (0 means no
  cap). Both affect only what is *spoken*; the status bar always shows every update,
  so nothing is ever hidden.
- **Trim specific cues.** Two announcement toggles under **Preferences >
  Accessibility** tailor what QUILL says. **Announce entering and leaving
  dialogs** (on by default) speaks "Entered" / "Exited *name* dialog" as dialog
  boxes open and close — turn it off if your screen reader already announces
  dialogs. **Announce indentation depth on Tab** (on by default) makes Tab and
  Shift+Tab speak the new depth ("4 spaces", "1 tab") instead of "Indented
  lines". Both affect only speech; the status bar still updates.
- **Re-read what QUILL just said — the Spoken Echo.** Speech is fleeting: an
  indent depth, a formatting description, a save result, or a "no matches"
  scrolls past the instant it is spoken. The **Spoken Echo** remembers the last
  twenty things QUILL announced and shows them, newest first, in a read-only
  dialog you can arrow through line by line, review by character, select, and
  copy. Open it any time with **Alt+Shift+E**, or from **Help > Show Spoken
  Echo** — it works after *any* announcement, including ones triggered by
  ordinary editing keys such as Tab, so you can hear "8 spaces", then open the
  Echo to read and copy it. If you are used to the screen-reader convention of
  pressing a reporting command twice, **double-pressing** an informational
  command — Describe Formatting, Document Summary, Context Help, or Announce
  Contrast — opens the Echo instead of re-speaking the same line. The dedicated
  Alt+Shift+E key is the universal path and always works; the double-press
  shortcut can be turned off under **Preferences > Accessibility > Double-press
  to show the Spoken Echo** (on by default). The Echo only records lines QUILL
  actually speaks, never your typing.
- **Braille display showing the first character in cell two?** QUILL's editor
  defaults to a rich-text control (so screen readers report its contents
  correctly), and some braille displays shift each line of a rich control one
  cell to the right — the same long-standing quirk you may remember from
  Microsoft Word. **Preferences > Accessibility > Editor control type (braille)**
  lets you change the native control: if your display shows the offset, set it to
  **Plain edit, like Notepad**, a simple control that the rich control was only
  ever needed in place of for *read-only* views (an editable plain control still
  reads correctly). RichEdit 2.0 is offered as a middle option. Changing the
  control type takes effect for documents opened afterward, so reopen your
  document or restart to compare. This affects only how the control is presented;
  your text is never changed.
- **Per-action templates.** Advanced users can edit exactly what each action
  says, using tokens like `{line}` and filters like `${ordinal:line}`, with live
  validation and preview. Templates can be saved to a library, shared as
  `.quill-verbosity-profile.json` files, or installed from a QUILL Verbosity Pack
  (`.qvp.json`) — all data-only, never code.
- **Preview Lab and History.** Preview how a profile sounds against canned
  scenarios before committing, and review, replay, copy, or ask "why did QUILL
  say that?" about recent announcements.
- **Safe Mode.** If a custom setup ever misbehaves, Safe Mode restores the
  built-in announcements without deleting your customizations.

These controls are screen-reader-first: QUILL speaks alongside your screen
reader, it does not replace it, so it never duplicates the typing echo or
punctuation settings your screen reader already provides.

**About QUILL's own voice.** When you run a screen reader, QUILL speaks through
it. QUILL also has its own built-in voice (Windows SAPI 5) used only as a
fallback for people who do not run a screen reader. If that built-in voice ever
fails to start, QUILL does not interrupt you about it while your screen reader is
doing the talking — it simply notes it quietly. If you do want QUILL's own voice
and it did not start, run **Tools > Retry TTS Engine**.

## Accessibility and Low-Vision Features

Quill is designed so accessibility is visible, not hidden.

### Region model

Use `F6` and `Shift+F6` to move between editor and other major regions. Quill announces those region transitions consistently.

### Keyboard trap and accessibility audit

The keyboard trap snapshot and accessibility audit commands are there to help verify the interface itself. This is useful both for users and for testers helping improve the product.

### Contrast and theme behavior

You can validate contrast, switch dark mode, and align with system behavior. This matters for users who need a predictable low-vision experience rather than a single visual theme.

### Status bar as an accessible control surface

Quill's status bar is navigable and interactive. This is a subtle but important design decision. It keeps useful information close while still making it reachable from the keyboard.

### Sound notifications and earcons

Quill can play short, non-speech audio cues — earcons — at meaningful editing moments, so your screen reader stays free for the text while sound carries the "something happened" signal. This is entirely optional and off by default for most events; speech is never replaced.

- **Sound packs (QSP).** A sound pack is a directory (or a `.qsp` zip) of WAV files with a `manifest.json` mapping event IDs to sounds. Quill ships the **Ink** pack of synthesised earcons, and uses it by default whenever you turn sound on. In the first-run **Keyboard and Sound** wizard page, the **Sound pack** control is now a simple **dropdown of the packs that ship with Quill** — just pick one (no hunting for a file). The dropdown defaults to Quill's own pack, so enabling sound always gives you working earcons out of the box.
- **Per-event control.** Open **Tools → Reading & Dictation → Sound Events...** to turn individual events on or off. Events are grouped — Earcons, Compare, and (when an indent-tone pack is loaded) Indentation tones — so you can keep, say, save and search cues while silencing others.
- **Indentation tones.** For code and other indented text, Quill can play a pitched tone as the caret crosses indent levels: the tone rises as you go deeper and falls as you come back out. Pick a musical scale (pentatonic, whole-tone, diatonic, or chromatic) under the **Indentation tones** setting, or leave it Off. Blank lines stay silent and hold the previous level.
- **Compare cues.** When a sound pack is active, compare mode plays distinct cues for opening and closing a comparison, moving to the next or previous difference, and bumping against the first or last difference. See [Comparison](#comparison).
- **Toggle everything.** **Toggle Sound Notifications** (in Reading & Dictation) turns all earcons on or off at once, and plays a short confirming "on" or "off" cue so you know which state you landed in.

Earcon events in the bundled Ink pack include: `quill_key_pressed` (QUILL key prefix armed), `abbreviation_expanded`, `abbreviation_deleted`, `snippet_inserted`, `autocomplete_accepted`, `document_saved`, `document_created`, `search_found`, `search_not_found`, `search_wrapped`, `heading_jumped`, `table_entered`, `browse_mode_on`, `browse_mode_off`, `ai_thinking_started`, `ai_response_received`, `ai_error`, `transcription_started`, `transcription_stopped`, `ssh_connected`, `ssh_disconnected`, `error`, `warning`, `sound_on`, `sound_off`, and the five compare events. Every scripted earcon in the bundled pack is a distinct sound, so two different events never sound identical. Pack authors can map any event ID to any WAV file; the full QSP format and event reference are documented in the product requirements document, under "Sound notifications and QSP sound packs."

### Startup speech is opt-in, not automatic

By default, QUILL speaks only the `QUILL Ready` line at startup. The other spoken lines that some users heard under 0.6.x — the Document Guardian activation cue and the screen-reader detection result — are now written to the status bar so sighted and low-vision users still see them, but the screen reader stays quiet unless you ask for more. Two settings under **Preferences → Accessibility** control the speech:

- **Speech channel (verbosity)** — the master gate. When off, every spoken announcement from built-in startup events and Quillin extensions is suppressed while the status bar keeps the same text. The setting defaults to on so first-run users still get the `QUILL Ready` line; turning it off gives you a fully quiet startup.
- **Speak screen-reader detection result at startup** — when on, speaks the `Detected screen reader: <name>. Adaptive hints enabled.` line after the probe finishes, but only if the verbosity gate is also on. The status bar always shows the result regardless.

Document Guardian has its own per-Quillin toggle for the activation and deactivation cue. Open **Preferences → Document Guardian → Lifecycle Announcements** and turn on **Speak activation and deactivation cues** if you want to hear `Document Guardian is now active.` when the Quillin starts (and `is now inactive.` when it stops). The setting defaults to off so first-run stays quiet; the status bar still records every enable and disable event for sighted and low-vision users.

## Quill on macOS

Quill runs on **macOS** as well as Windows, from one codebase, with feature parity as the goal.

- **VoiceOver-first.** On macOS, Quill routes its announcements to **VoiceOver** and never speaks over it. Headings, regions, and result messages behave the way they do on Windows with NVDA/JAWS.
- **On-device AI.** Ask Quill uses **Apple Foundation Models** (Apple Intelligence) on a supported Mac — no model download and no cloud. The on-device GGUF/llama.cpp picker is hidden on macOS because Apple's model is used instead; you can still connect Ollama or a cloud endpoint if you prefer.
- **Standard Mac behaviors.** Preferences and About use the standard macOS menu locations (`Quill -> Settings`, `Quill -> About Quill`).
- **Help menu registered as system Help.** The Help menu is registered as the macOS system Help menu, so the conventional `Cmd+?` Help shortcut works as expected (#613).
- **Back / Forward Location on macOS** uses `Cmd+[` and `Cmd+]` so it does not collide with VoiceOver's word-by-word `Option+Left` / `Option+Right` reading (#609). Windows keeps `Alt+Left` / `Alt+Right`.
- **Signed and notarized.** Release Mac builds are code-signed with a Developer ID certificate and notarized by Apple, so Gatekeeper opens them without warnings. The app ships as a `.app` (and disk image).
- **The accessible WebView** that powers the chat, the Markdown/HTML preview, the About box, and the update dialogs reads correctly under VoiceOver, just as it does under NVDA and JAWS on Windows.

## Profiles, Keyboard Packs, and Customization

Quill is customizable, but it tries to keep customization coherent.

### Feature profiles

Profiles shape which feature clusters are on, quiet, or off. This helps Quill stay calm for new users without stripping power from advanced users.

#### Choosing a profile

Each profile is a starting point, not a cage — switch any time from **Profiles and Features...**, and fine-tune individual features afterward without losing the rest of the profile's choices.

The first-run Personalise QUILL wizard offers seven of these as curated starting points, each with a plain-English preview of what you get. The full set of ten lives here in **Profiles and Features...**, including profiles the wizard does not surface directly, such as Reader and Student, Office and Admin, and Low Vision.

- **Essential** — the calmest possible editor. Just text, files, and the basics, with everything else a quiet opt-in away.
- **Writer** — everyday writing, formatting, and cleanup, with guided power features nearby when you reach for them. For papers, citations, and a table of contents, see Author or Student below.
- **Author or Student** — long-form writing with a table of contents, footnotes, and MLA / Chicago / APA citations, built for papers, theses, and class assignments. Choose footnote-style or full academic citations with **Format → Markdown → Select Citation Style...**.
- **Reader and Student** — reading, highlights, references, and light writing, tuned for working through someone else's material rather than producing your own.
- **Office and Admin** — reliable file work, sessions, cleanup, and printing for everyday office documents.
- **Developer and Power Text** — regular expressions, cleanup, inspection, and document-analysis tools surfaced up front.
- **Low Vision** — higher contrast, larger reading aids, and friendly inspection tools.
- **Braille and Screen Reader Power User** — screen-reader-friendly navigation with advanced text tools surfaced calmly rather than buried.
- **Accessibility Professional** — reading, inspection, trust, and accessibility diagnostics for auditing other people's documents.
- **Full Quill** — everything visible, including advanced and experimental paths, for people who would rather see it all than ask "why don't I see this?"

Use **Profiles and Features...** to:

- switch profiles
- quick-switch profiles from anywhere with `Alt+Shift+P`
- compare profiles
- undo the last profile change
- reset to Essential
- import and export profile data
- create custom profiles
- update a custom profile from your current feature/settings/keymap state
- delete custom profiles

Custom profiles support an explicit inheritance choice:

- **Inherit parent profile** keeps the selected built-in profile as the starting point.
- **Bare-bones start** opts out of inherited features and starts with only locked core safety features enabled.

### Fine-tuning individual features

**Help > Feature Profiles > Manage Individual Features** gives you per-feature control on top of your active profile. Use it when a profile is almost right but you want to add or remove one or two capabilities without creating a whole new profile.

The dialog shows a checkbox for each user-toggleable feature. A **Show** radio button at the top lets you choose between **All features** and **Disabled features only**. The disabled-only view filters the list down to features that are not currently on, so you can scan and enable specific capabilities without scrolling past everything that is already running.

When you arrow to a checkbox, a read-only description area at the bottom of the dialog explains what the feature does and what it depends on. Enabling a feature automatically enables its dependencies; disabling one turns off the features that depend on it, and QUILL tells you what changed in the status bar.

When you enable a feature in the disabled-only view, it disappears from the list immediately and focus moves to the next disabled item so you can keep going without losing your place.

### Keyboard packs

Quill now supports golden keyboard packs so the editor can feel familiar from day one. Available packs include:

- Quill Default
- Quill Writer
- Quill Navigation
- Quill Review
- Windows Notepad
- Notepad++
- VS Code
- Microsoft Word

Choose a pack in **Profiles and Features...**. If you later hand-edit shortcuts or import a custom keymap, Quill automatically switches the pack label to **Custom**.

### Keymap editor

Use the keymap editor when you want to rebind a single command. Quill detects conflicts and warns you before reassigning a binding already in use.

### Recommended shortcut updates

Occasionally a keyboard shortcut needs to be corrected for everyone — for example, **Find returns to `Ctrl+F`** after some pre-release builds had moved it to a QUILL-key chord. QUILL applies a correction like this **once**, and then never touches that binding again, so you are always free to rebind it afterward in the Keymap Editor.

If you would rather QUILL never change your shortcuts, turn off **Apply recommended keyboard-shortcut updates** in Settings. With it off, your bindings are left exactly as you set them, even across updates.

### Reset everything to factory defaults

To start over completely, choose **Tools → Customize & Support → Reset Everything to Factory Defaults...**. After a confirmation prompt (it defaults to "No"), this resets your settings, keyboard shortcuts, menu customizations, and feature profile to their originals in one step. Your documents, autosaves, and backups are never affected. Smaller, focused resets are also available: **Reset Keymap** (shortcuts only) and **Reset to Factory Defaults** inside Settings (settings only).

### Keyboard manager for QUILL Quick Nav

QUILL Quick Nav actions appear in Keymap Editor as dedicated entries:

- `QUILL Quick Nav: Link`
- `QUILL Quick Nav: List`
- `QUILL Quick Nav: List Item`
- `QUILL Quick Nav: Table`
- `QUILL Quick Nav: Block Quote`
- `QUILL Quick Nav: Bookmark`
- `QUILL Quick Nav: Code Block`
- `QUILL Quick Nav: Table of Contents`
- `QUILL Quick Nav: Paragraph`
- `QUILL Quick Nav: Sentence`
- `QUILL Quick Nav: Heading`
- `QUILL Quick Nav: Block`

Exact rebinding examples:

1. Open `Tools -> Customize & Support -> Keymap Editor...`.
2. Choose `QUILL Quick Nav: Link`.
3. Enter `K` if you want link jumps on `K` instead of `A`.
4. Choose `QUILL Quick Nav: Code Block`.
5. Enter `\`` (grave) if you prefer grave instead of apostrophe.

Notes:

- Conflicts are blocked by the keymap editor before saving.
- Quick Nav keys are interpreted only while QUILL Quick Nav mode is active.

### Status bar settings

If the current status bar is too busy or not informative enough, change it. You can reorder items and choose which ones stay visible.

### Settings you can change today

Quill's current settings and customization surface covers the things you are most likely to want to tune every day.

- theme behavior, including dark mode
- soft wrap
- recent files limit
- system tray mode
- persistent undo
- spell check as you type
- **spell check a document before saving** — when on, saving opens the Spelling Review (F7) first so you can correct the document before it is written. Off by default.
- line-number visibility
- whether Quill starts with no document open
- **suggest a filename from the first line** — when on, saving an untitled document pre-fills the Save dialog with a name taken from the first line (across formats; leading markup like a Markdown heading, quote, or list bullet is stripped). Off by default.
- read-aloud voice selection
- active feature profile
- active keyboard pack
- custom keybindings through the keymap editor
- status-bar order and status-bar visibility

Some of these live in the View menu for quick toggling; the preference-style toggles now live in the **Settings** dialog (**Tools -> Customize & Support -> Preferences...**). Others live in **Profiles and Features...**, **Status Bar Layout...**, **Keymap Editor...**, and the related customization commands under **Tools -> Customize & Support**.

## Trust, Recovery, Sessions, and Safety

Quill is serious about recovery and user control.

### Notebooks

A **Notebook** is a named collection of documents that belong together — a novel's chapters, a research project's notes, a software project's specs. Notebooks live in a single `.quillnotebook` file and keep track of which files are entries, where you left each caret, any goals you have set, and saved snapshots of which entries were open.

**Creating a Notebook.** Use **File > Notebook > New Notebook** to create an empty notebook and give it a name. Use **File > Notebook > New from Folder** to import an entire folder at once — Quill walks the folder recursively and creates one entry per supported file. You can filter by extension (the default set covers Markdown, plain text, HTML, and source code).

**Opening and navigating entries.** Once a Notebook is open, **Navigate > Go to Entry in Notebook** opens the tree navigator, which groups entries by subdirectory. Select an entry and press Enter (or click "Open Entry") to open that file. For headings, **Navigate > Go to Heading in Notebook** scans every entry file and presents a two-level tree.

**Entries panel.** Toggle **View > Show Entries Panel** to slide a docked panel into the left side of the window. The panel shows the notebook name, today's goal progress, a live filter field, and the full entries list. Type in the filter field to narrow by title.

**Goals.** Each Notebook can carry a daily word-count goal stored in its `.quillnotebook` file. When the goal is enabled, the **Notebook Goal** status-bar cell shows progress (for example, "1,234 / 500 words"). Reaching the target changes the label to "Goal reached."

**Snapshots.** A Snapshot is a named point-in-time record of which entries were open. Use **File > Notebook > Save Snapshot** to save one, and **File > Notebook > Manage Snapshots** to rename or delete saved snapshots. Snapshots are different from autosave recovery — they are explicit saves you make yourself, like commit checkpoints for your writing session.

**Snapshots vs Sessions.** The **File > Snapshots** menu (formerly "Workspace Snapshots") saves and restores the set of open documents in the editor — a lightweight workspace for any files, not tied to a Notebook. Notebook Snapshots store the open-entry state within a single Notebook.

### Sessions

Sessions in Quill are best understood as **workspace snapshots**. A session captures your currently open documents and active tab, then lets you reopen that exact working set later.

If you are familiar with VS Code workspaces, think of Quill sessions as a simpler, document-focused version of that idea:

- save your current workspace state
- reopen it from Recent Snapshots
- quickly switch among open documents in the current workspace group

This is useful when one writing task spans notes, references, drafts, and generated reports.

### Marks vs bookmarks (and the ring)

Quill has two jump systems on purpose:

- **Bookmarks** are named jump points. They are explicit, easy to list, and best for durable places you want to revisit by name.
- **Marks** are temporary jump points in a **ring**. The ring is a rolling stack of recent mark locations for fast back-and-forth movement while editing.

Use bookmarks for long-lived anchors; use marks when you are actively traversing and reshaping text.

### Autosave and backups

Quill autosaves at a timed interval and keeps backup snapshots. It avoids unnecessary duplicate autosave writes and keeps state management efficient.

### Recovery

If Quill closes unexpectedly, it can offer a recovery snapshot on the next launch. That is not a dramatic feature. It is a humane one.

### Persistent undo

When enabled, persistent undo stores undo history for saved files across sessions. Quill now throttles those writes so the feature stays practical on large documents.

### Trusted locations

Trusted locations reduce repeated prompts when you regularly work from the same folders. This is especially useful in document-review and institutional workflows.

### Safe mode

Safe mode opens Quill with optional state turned off. If you are troubleshooting a bad session or strange startup behavior, safe mode is a good first step.

### Notifications and updates

Quill keeps an internal notification center for update and workflow events. Update checks verify a signed manifest before offering a download.

### Your settings across updates

Quill remembers only the choices you have actually changed. When you update, your customizations are kept, brand-new options appear already set to a sensible default, and an improved default reaches you automatically unless you had changed that option yourself. The first launch after an update tidies your old settings file once and writes a backup to a `migration-backups` folder first, so the change is always reversible. Your documents, autosaves, and recovery data are never touched by this.

You control how Quill tells you this happened with the **Upgrade notice** setting (Administration): **Brief announcement** (the default — a short spoken and status-bar message), **Summary with Undo** (a small dialog listing what changed, including a one-click Undo for any shortcut correction), or **Silent**. A backup is saved regardless of the choice, and you can also undo a recent shortcut change at any time during the session with the **Undo Recent Shortcut Change** command.

### A clean start after an update

The first time you launch a freshly updated Quill, it clears out the old diagnostic clutter from earlier runs — previous log files and crash reports — so you begin with a clean slate instead of a backlog of past problems. This happens once, automatically, and never removes your documents or settings.

## Posting to Mastodon

Quill can publish straight from the editor to Mastodon — no separate app, no leaving your document.

- Press **QUILL Key + Shift+P** (or **Tools → Share → Post to Mastodon...**). Quill takes your current selection, or the whole document if nothing is selected, and opens a compose window.
- In the compose window you can edit the text, pick which account to post from, choose the visibility (Public, Unlisted, Followers only, or Direct), and watch a live character count. Press **Post** to publish; your post appears with "via QUILL" as its source.

### Adding a Mastodon account

The first time you post, Quill offers to add an account; you can also open **Tools → Share → Mastodon Accounts...** at any time.

1. Choose **Add Account...**, enter your server (for example `mastodon.social`) and a **friendly nickname** (this is what shows in the account picker).
2. Quill registers itself with your server and opens your browser to authorize. Sign in if needed, approve QUILL, and copy the authorization code your server shows you.
3. Paste that code back into Quill. Your account is saved.

You can add several accounts, give each its own nickname, **set a default**, or **remove** one (which deletes its saved sign-in from this computer). Your sign-in is stored securely in the Windows Credential Manager, never in a plain file.

**Proofread posts before sending.** In **Mastodon Accounts...**, select an account and tick **Spell-check posts before sending** to turn on per-account proofreading (off by default). When it is on, pressing **Post** for that account first opens the Spelling Review (F7) on the post text so you can fix misspellings, and the post is sent only after you finish or skip the review. The setting is per account, so you can enable it for some accounts and not others; existing accounts are unaffected until you turn it on.

## Working with Different Document Types

Quill is strongest today with plain text, Markdown, HTML, RTF, EPUB, and extracted text workflows. It also has intake and extraction review features for imported material such as PDF/OCR sources and structured import support for Office-style formats.

### Plain text

Plain text stays plain. Quill does not force hidden formatting into it.

### Markdown

Markdown gets structure-aware commands, list helpers, heading helpers, links, and code blocks.

### HTML

HTML gets tag insertion, structure-aware editing help, and link handling.

### RTF

RTF documents can use Quill's optional **Rich text lens**, a screen-reader-first rich editing surface. It is **off by default**: the standard plain-text editor stays Quill's writing path unless you opt in under Settings, Editing (the "Editor surface" choice). Turn it on and `.rtf` files open in the Rich text lens, which renders bold, italic, headings, bullets, and links natively. Your document text stays Quill Markdown underneath, so search, outline, metrics, autosave, and persistent undo keep working exactly as in plain-text mode. Press the editing-lens shortcut (`Ctrl+Shift+` ` then `K`) to switch losslessly between the rich view and the Markdown lens; no words are lost and the document is not marked changed by switching. When an RTF file contains unsafe embedded content (such as OLE objects) Quill strips it on open and tells you; remote fields are flagged for your consent rather than fetched silently.

### CSV and TSV

CSV and TSV files open through a choice flow: special CSV grid mode or normal text editor mode. You can remember your preferred default and still switch modes from inside the tab at any time. Grid mode is keyboard-friendly and designed for screen-reader users who need cell-level table editing without leaving Quill.

### Word (.docx and .doc)

Word documents open through a choice flow: structured Word view or normal text editor mode. You can remember your preferred default and still switch modes inside the tab.

Structured Word view is optimized for accessibility: it prioritizes readable structure and linearized table narration (headers and rows) for screen readers. Normal text mode keeps full Quill editing behavior for direct edits.

**Saving to Word.** You can also save any document *as* Word. In **File -> Save As...**, choose **Word Document (*.docx)** (or **Rich Text Format (*.rtf)**) from the file-type list, and Quill converts the current content to that format on save. Markdown and HTML structure — headings, lists, emphasis, links, simple tables — maps to real Word styles, so the result is navigable in Word, not just visually formatted. Saving plain text produces a correct but unformatted document, since plain text has no structure to carry.

### EPUB

EPUB gets navigator support and chapter-oriented reading.

### PowerPoint (.pptx and .ppt)

PowerPoint imports are structure-aware: slide titles become headings, slide bullets become nested list items, tables are rendered into tab-friendly text tables, and speaker notes are included when present.

### Excel-style spreadsheets (.xlsx and .xls)

Spreadsheet intake is text-first and structure-aware. Quill extracts sheets into readable table-oriented text so you can inspect and review content quickly. If optional converters are installed, extraction quality improves for legacy and mixed-format files.

### PDF and OCR-derived text

PDF and OCR work are where Quill's extraction review commands matter most. Treat those commands as quality checks, not optional extras.

### Remote files (FTP, SFTP, HTTPS, WebDAV, S3)

Quill can open, save, and copy to remote hosts the same way it works with local files. Remote I/O is explicit, audible, and reversible:

- **Open from Remote...** lists every site you have saved, lets you browse a remote directory, and downloads a file you choose. The download is announced with the host and expected size, lands in a temp file, and opens in a normal tab titled with a `(from site:path)` suffix. The document is **read-only** until you save it back through **Save Copy to Remote...** or copy it to local storage.
- **Save to Remote** writes the active document to a remote path you choose, on a site you have configured, with a tilde-backup next to the original. **Save Copy to Remote...** lets you keep the local file and write a copy without changing the source.
- **Manage Remote Sites...** adds, edits, and deletes saved sites for the five supported protocols. Each site's password is stored in **Windows Credential Manager** when available, then in a DPAPI-protected JSON file, with a macOS Keychain facade for cross-platform parity.
- All remote traffic uses a **verified TLS context**. Cloud endpoints (S3, HTTPS, WebDAV over HTTPS) must be HTTPS; FTP is allowed because the user opted in for LAN or legacy hosts.
- All remote operations are wired to the **network egress audit** (`quill/tools/network_egress_audit.py`) with explicit rationales, and S3 and WebDAV XML responses are parsed through `quill.core.safe_xml.fromstring` so an attacker cannot reach an external-entity expansion through a crafted listing.

Default keys: **QUILL key, then `Shift+O`** opens from remote; **QUILL key, then `W`** saves to remote; **QUILL key, then `Shift+M`** opens the site manager. All are remappable from Preferences > Keyboard.

### GitHub Remote Files

QUILL can browse GitHub repositories, open files from them, and save changes back to GitHub — all without installing Git, the GitHub CLI, or GitHub Desktop.

**Getting started**

The first time you open a GitHub feature, QUILL asks you to confirm that it may connect to GitHub. This is a one-time prompt. After that, QUILL remembers your choice.

You do not need a GitHub account to browse public repositories. For private repositories, you need a Personal Access Token (PAT).

**Creating a Personal Access Token**

1. Go to github.com and sign in.
2. Open Settings > Developer settings > Personal access tokens > Tokens (classic).
3. Click Generate new token.
4. Give it a name such as "QUILL" and select the `repo` scope (or `public_repo` if you only need public repositories).
5. Copy the token. You will only see it once.

QUILL stores your token securely in **Windows Credential Manager**. It is never saved in a text file.

**Opening the repository browser**

Open **File > Open from Remote > GitHub Repository...**

The browser has these parts:

- **Account** — shows your GitHub username, or "Anonymous" if no token is stored.
- **Repository** — type an owner/repo name such as `microsoft/vscode` and press Enter or click Load.
- **Branch or tag** — choose which version of the repository to browse. Defaults to the repository's default branch.
- **Current path** — shows where you are in the folder tree.
- **File list** — lists folders and files. Folders appear first.
- **Status** — shows progress messages and item counts.

Navigation:
- Press Enter on a folder to open it.
- Press Enter on a file to open it (same as clicking Open File).
- Press Backspace to go up one level.
- Press F5 to refresh the current folder.
- Tab through the buttons: **Open File**, **Go Up**, **Refresh**, **Copy URL**, **Cancel**.

**Opening a file by URL**

If you have a GitHub file URL (for example from a colleague), use **File > Open from Remote > GitHub File URL...**

Paste a URL in the form `https://github.com/owner/repo/blob/branch/path/to/file` and press Enter. QUILL fetches the file directly.

**Saving back to GitHub**

After you have opened a file from GitHub and made edits, use **File > Open from Remote > Save to GitHub...**

QUILL will ask for a commit message. Type a short description of your changes and press Enter. QUILL commits your changes to the same repository, branch, and file path using the GitHub API.

Notes:
- You need a token with write permission (`repo` scope) to save back.
- If the file was changed on GitHub since you opened it, QUILL will tell you to refresh and try again.
- This command does not run automatically when you press Save. You must choose it deliberately.

**Managing your GitHub account**

Use **File > Open from Remote > Manage GitHub Accounts...** to:

- See your current GitHub identity.
- Add or replace a token.
- Sign out and clear your stored token.

**File size limit**

GitHub's file API is limited to 1 MB. Files larger than that must be downloaded manually from github.com.

**Enabling the feature**

GitHub remote access is controlled by the feature flag `core.github_remote`. If it is not visible, open **File > Open from Remote** and check whether the GitHub items appear. If PyGithub is not installed, QUILL shows a message explaining how to install it: `pip install "quill[github]"`.

## Braille Mode (BRF, BRL, PEF, UEB)

QUILL opens and edits formatted braille text files — `.brf`, `.brl`, `.pef`, and `.ueb` — as plain NABCC (braille ASCII). The point is to let a braille proofreader move through a transcription the way it is actually laid out, in braille pages and cells, with speech that tells you exactly where you are.

**Opening a braille file.** Open any `.brf`/`.brl`/`.pef`/`.ueb` file the way you open anything else. QUILL reads it as braille text: a UTF-8 byte-order mark is stripped if present, and the file is scanned for any character that is not braille ASCII. Nothing is transformed on the way in — what you see is the file's bytes.

**Saving is byte-for-byte.** When you save a braille file, QUILL preserves it exactly: no trailing-space trimming, no line-ending normalization, and form feeds (the hard page breaks) are kept. If the text contains characters outside the braille-ASCII range, QUILL still saves them as-is and gives you a single, non-blocking spoken warning so nothing is silently changed. This means a round-trip — open, save — gives you back an identical file.

**Picking up where you left off.** When you reopen a braille file, QUILL puts your cursor back at your last position and tells you where you are — for example, "BRF file opened. 87 braille pages detected. Last position: braille page 12, line 14, cell 31." Your place (along with proofing progress and notes) is stored in a small companion file next to the braille file; the braille file itself is never modified. Restore is skipped when QUILL is in safe mode or when sidecar saving is turned off, and if the file was edited shorter elsewhere your cursor is clamped safely inside it.

**The braille status cell.** While a braille file is active, the status bar carries a braille cell that updates as you move: it reads like `BRF Pg 12/87 | Ln 14/25 | Cell 31/40 | Print 7`. That is the braille page, the line within the page, the cell within the line, and the print page. Print-page detection runs on every open and on every page-map recalculation, so the print segment is always populated when a print-to-braille anchor is available; on documents without anchors it reads `Print ?`.

**The Braille menu.** Braille commands live under **Tools > Braille**. Bindings are intentionally left unset so nothing collides with your screen reader or existing editor keys; you can assign your own in the keyboard customizer, or run them from the Command Palette.

- **Status** — Read Braille Status (respects your status verbosity), Read Detailed Braille Status (includes print page, continuation letter, running head, proofing state, and detection confidence), Read Current Line and Cell, Read Current Braille Page, Read Current Print Page, Read Progress Summary (how far through the document you are), Announce Running Head, Include Running Head in Status, and Omit Running Head from Status.
- **Navigation** — Go to Braille Page… (type a page number), Next Braille Page, Previous Braille Page, Go to Print Page… (type a print-page number from the detector's output), Next Print Page Change (jumps to the next detected print-page boundary), and Previous Print Page Change. Stepping past the first or last boundary tells you there is no more.
- **Page Tools** — Insert Braille Page Break (a form feed) and Remove Braille Page Break at the cursor, plus Recalculate Page Map (rebuild the page map after edits) and a placeholder for Normalize Line Endings.
- **Proofing** — track your proofreading progress without ever changing the braille file. Mark the current braille page Proofed, Needs Review, or clear its mark; Add a Proofing Note to the current page; Read a spoken Progress Summary (pages proofed, pages needing review, last proofed page, and estimated completion); List Proofed Pages or List Pages Needing Review (choosing a page jumps you to it); and Export a Proofing Report to a plain-text file. Progress is stored in a small companion file next to the braille file, so it travels with the document and never alters it. These commands tell you to save the file first if it has not been saved yet.
- **Validation** — check the layout of a braille file. **Validate BRF Layout** scans for ten kinds of problem — lines or pages that are too long, pages that look stuck (too short), missing page breaks, mixed line endings, characters that are not braille ASCII, malformed or missing page indicators, gaps or duplicates in page numbering, inconsistent running heads, and files that are Unicode braille rather than NABCC — and opens a Warnings List you can step through; choosing a warning takes you to it. **Next Warning** and **Previous Warning** move through the findings and announce "Warning N of M" with the message, and **Warnings Summary** speaks the total and the most common categories. Validation only reads the file; it never changes it.
- **Repair** — fix the two problems that stop a braille file from embossing cleanly. **Read Layout Metrics** speaks the diagnostic numbers in one pass: the cursor's cell and the current line length; the longest line in the file against your cells-per-line limit, with a spoken "page width exceeded" when it is over; the current and total braille pages; and the longest page against your lines-per-page limit, with a spoken "page depth exceeded" when it is over. **Go to Longest Line** and **Go to Longest Page** take you straight to the worst offender so you can repair it by hand — for a too-deep page, that usually means inserting a page break (Insert Braille Page Break) where one is missing. **Remove Trailing Spaces on This Line** and **Remove Trailing Spaces in Whole File** clear the trailing spaces that cause most page-width problems, while keeping every line ending and form feed intact. The cell and line limits come from your **Cells per line** and **Lines per page** settings under **Preferences → Braille**, so the diagnostics always match the page geometry you are transcribing for.

Every status, navigation, and layout command is safe to run on a non-braille document — it simply tells you "This is not a braille document" rather than doing anything. (Remove Trailing Spaces and Go to Longest Line work on any document's text.)

**Translation (Universal BRF Pack).** Forward and back translation between print text and braille require the optional **QUILL Braille Pack**. Instead of a simple set of tables, the pack uses a three-layer architecture: a full technical catalog of every available liblouis table, a set of user-facing profiles that map friendly names to the correct tables, and the translation runtime itself.

The pack is not bundled by default. When it is absent, the **Translation** submenu is hidden so you never see disabled items. When the pack is installed, the Translation submenu is dynamic and organized into sections:

- **UEB (Unified English Braille)** — Contracted (Grade 2), Uncontracted (Grade 1), Translate Selection to UEB, and Back-Translate UEB.
- **Standard American English (Legacy)** — Contracted (Grade 2) and Uncontracted (Grade 1) using the traditional North American English tables.
- **More Languages** — a submenu populated automatically from the installed pack's profile catalog. Languages with multiple profiles (for example, contracted and uncontracted variants) appear as their own sub-group. Examples include German, French, Spanish, Russian, Korean, and dozens more.

Forward translation opens the BRF result in a new document and tells you how many braille pages it produced. Back-translation always opens its result as a clearly labeled **draft** because no automatic back-translation is authoritative; it back-translates your **selection** when you have one selected (so you can recover the source text of a single passage) and the whole document otherwise, telling you which it used ("Back-translation draft from selection. N words. Review against the BRF."). Translation runs entirely out of process, so a liblouis failure can never take QUILL down; if it fails, QUILL announces the reason and does not open an empty document. The Translation submenu is also hidden in Safe Mode.

## Help, Learning, and Daily Confidence

Quill includes several layers of help because confidence does not come from memorizing everything.

- **F1** — context-sensitive help for the focused control. Works anywhere in the application.
- **Ctrl+F1** — opens this User Guide.
- **Shift+F1** — opens the document-context "What Can I Do Here?" panel.
- **Open Welcome Guide** when you want a lighter orientation.
- **Open User Guide** when you want the full map.
- **Open Keyboard Reference** when you want exact current bindings.
- **What Can I Do Here?** when you need immediate, contextual guidance.
- **Why Don't I See a Feature?** when a command seems to have disappeared.

That last command matters more than it first appears. It turns feature visibility from a mystery into an explanation.

### Context-Sensitive Help (F1)

Press `F1` on any focusable control in QUILL and a small dialog opens that describes:

1. **The dialog you are in** (when you are inside a dialog box) — the dialog name and a plain-language summary of what it does, so you always know your context.
2. **The focused control** — what the control is, how it works, and what keyboard shortcuts apply to it.

The entire text is in one read-only field so your screen reader announces everything in a single pass when the dialog opens, without you having to navigate past heading elements.

From the help dialog you can:

- Press **Escape** or **Enter on Close** to dismiss and return to where you were.
- Press **Tab to Open User Guide** to jump to the full documentation section for this control.

**How the three Help keys work together:**

| Key | What it does |
|-----|--------------|
| `F1` | Help on the currently focused control (context-sensitive) |
| `Ctrl+F1` | Open the full User Guide |
| `Shift+F1` | Open "What Can I Do Here?" for the active document context |

**Tips:**

- In the main editor, F1 shows editor shortcuts and writing tips.
- In dialogs (Preferences, Find/Replace, Spell Check, etc.), F1 identifies both the dialog and the specific setting.
- In the Personalise QUILL wizard, F1 on each control explains what each setting does and what you can change later.
- After using a menu and returning to the editor, QUILL remembers which control had focus last, so F1 still refers to the right control.

### Personalising QUILL

The **Personalise QUILL** wizard runs automatically the first time QUILL starts. You can re-run it at any time from **Help → Personalise QUILL**.

The wizard walks you through six short pages (five if you do not enable AI writing assistance on the Extras page):

1. **Welcome** — an introduction to what the wizard covers.
2. **Intent** — the most important page. A single question: *What kind of writing do you do?* A list of seven starting points is shown. Arrow up and down through the list. As you move, a large read-only text area below the list updates live to tell you, in plain spoken English, exactly what you will have if you choose that option. There are no feature IDs, no jargon about flags, and no list of what you will not get. Just what you get.
3. **Extras** — offers a few optional extras such as AI writing assistance, Braille Mode, and typing automation. Only the extras that are not already part of your base choice are shown. Each extra is a single checkbox. Checking one adds a sentence to the preview so you always know what you are committing to.
4. **AI Provider** — shown only if you enabled AI on the Extras page. Collects your provider and your API key. Supported providers are Anthropic (Claude), OpenAI (GPT), Google Gemini, OpenRouter (many models), and Ollama, which runs models on your own device or connects to an Ollama-compatible cloud host. The key is stored securely in the Windows Credential Manager, not in a settings file. You can skip this and set the key up later.
5. **Keyboard and Sound** — choose a keyboard pack and whether QUILL plays audio cues. QUILL auto-detects your screen reader and sets accessible defaults.
6. **Summary** — review all your choices before they are applied. The summary is plain text: your profile name, what features are active, which Quillins are enabled, your keyboard pack, and your sound setting. Use Back to revise any page. Nothing changes in QUILL until you press Finish.

> **0.7.0 Beta 2:** every wizard page now starts with a focusable
> heading, and the preview block is rendered as a read-only document
> so VoiceOver does not announce it as an editable text field. See
> [Recent Fixes](#recent-fixes-in-070-beta-2) for the full list.

**Important:** The wizard is transactional. Your choices are held in memory until you press Finish. If you close or cancel the wizard, no settings are changed.

**Profiles explained:** QUILL ships ten built-in feature profiles, each starting you at a different level of feature density and accessibility support (the first-run wizard surfaces seven of them as plain-English starting points). You can switch profiles at any time from **Tools → Customize & Support → Profiles and Features...** or by pressing `Alt+Shift+P`.

| Profile | Best for |
|---------|----------|
| Essential | New users, light daily writing, low-distraction setup |
| Standard | Most users — balanced feature set with AI and tools available |
| Power User | All features on; suited to advanced writing and extraction |
| Accessibility Focus | Screen-reader primary; maximises keyboard coverage and announcements |

### Recent Fixes in 0.7.0 Beta 2

The Beta 2 release includes a sweep of accessibility, macOS, and
crash-resistance fixes. Where the fix is invisible to the user, the
note says so; where the fix is user-visible, the note gives the
user-facing detail. The full list is in the [release notes](../release%20notes/release0.8.0-beta1.md).

- **#603 — closing the last document no longer crashes the caret
  handler.** Bug-fix; nothing to change. The crash surfaced as
  "QUILL encountered an unexpected error and needs to close" when
  you pressed `Ctrl+W` on a dirty document, picked "Don't Save,"
  and the next caret event was still queued against the destroyed
  editor widget. The fix is a defensive guard on the editor-read
  helper; you will not see the error dialog any more.
- **#605 — Help → Check for Updates opens cleanly.** Bug-fix; the
  dialog had a stale `ImportError` that surfaced as
  "QUILL encountered an unexpected error." Open Help → Check for
  Updates and the update channel selector appears as before.
- **#606 — Setup Wizard opens on a clean window, not on top of
  an "Untitled" tab.** Returning users (anyone who has already
  run the wizard) see the normal "Untitled" tab on launch;
  first-run users see the wizard on an empty notebook and an
  untitled document is created automatically after the wizard
  finishes.
- **#608 — `Cmd+Q` now quits QUILL on macOS.** The new default is
  `Ctrl+Q` (which maps to `Cmd+Q` on macOS), and Quote Lines has
  moved from `Ctrl+Q` to `Ctrl+Shift+Q` to make room.
  Unquote Lines moved from `Ctrl+Shift+Q` to `Ctrl+Shift+K` to
  keep the pair on the home row. A saved `keymap.json` that
  still has the old chords is rewritten on first launch, and the
  corrected value is persisted back so the next launch is clean.
- **#609 — `Option+Left` / `Option+Right` are no longer hijacked
  by Back / Forward Location on macOS.** On macOS, the new
  default for Back / Forward Location is `Cmd+[` and `Cmd+]`
  (the conventional macOS back / forward chord, matching Safari,
  Finder, and most other Mac apps). Windows users keep the
  existing `Alt+Left` / `Alt+Right`. A pre-#609 macOS user whose
  saved `keymap.json` still records the Windows chord has it
  rewritten to the new macOS chord on first launch, and the
  corrected value is persisted back so the next launch is clean.
- **#610 — Setup Wizard page heading is the first focusable
  element, and the preview is no longer announced as
  "edit text" by VoiceOver.** A screen-reader user now lands on
  the page heading on every wizard page, not on the read-only
  preview block. The preview itself is rendered as a read-only
  document (not a `TextCtrl`), so VoiceOver announces it as a
  document or static text rather than as an editable text field.
  Sighted users see the same styled preview they had before.
- **#611 — wizard Back and Next buttons are simply "Back" and
  "Next."** VoiceOver on macOS was reading the old labels
  ("`< Back`" and "`Next >`") as "less than Back" and "Next
  greater than." The buttons now read "Back" and "Next," which
  is what every screen reader announces and what every sighted
  user sees on the face of the button.
- **#612 — Read Aloud and Insert Snippet no longer fire on bare
  `R` and `S` keystrokes.** Bug-fix; the friendly chord label
  in the Tools and Insert menus was being parsed by wx as a
  real native keyboard accelerator, so the bare letters `R` and
  `S` got bound as modifier-less global shortcuts. The chord
  label is now shown as plain parenthetical text after the menu
  item name rather than as a wx accelerator, so the letters
  belong to your text again.
- **#613 — the Help menu is now recognised as the macOS system
  Help menu.** Bug-fix; the macOS `Cmd+?` Help shortcut now
  works (it was already wired in wx, but the OS only honours it
  for menus that are flagged as the system Help menu). Windows
  and Linux behaviour is unchanged.
- **#614 — AI Hub opens cleanly from the wizard and the editor
  caret handler no longer fires before a document is loaded.**
  Bug-fix; the AI Hub's tab labels and the first-run AI Hub
  button were both affected by the same `lazy_gettext` proxy
  issue, and the caret handler crashed silently on every
  keystroke before you had even selected a document.
- **#615 — JAWS, NVDA, Narrator, and VoiceOver now announce the
  QUILL version.** The window title now includes the full
  QUILL version (for example, "QUILL for All 0.7.0 Beta 2"),
  so every screen reader that announces the focused window —
  JAWS `Insert+T`, NVDA `+T`, Narrator `Caps+H`, VoiceOver —
  reads the version along with the document name. The
  `Ctrl+JAWSKey+V` path still reports only "Version" until a
  versioned launcher ships; the window title is the change you
  can hear today.
- **#616 — VoiceOver now reads the editor as a native text area
  on macOS.** Bug-fix; the editor's NSView now has its
  NSAccessibility role pinned to `NSTextView` so VoiceOver
  announces it as a normal, editable text area with full
  text-navigation semantics. Windows behaviour is unchanged.
- **#618 — Report a Bug dialog now speaks field names on macOS,
  opens in its own window so you can alt-tab to the editor, and
  no longer auto-opens a browser after submit.** Every field is
  bound to its label via the standard accessibility name, so
  VoiceOver reads "Summary, edit text" / "What happened, edit
  text" / etc. when you tab into a field. The dialog opens in a
  non-modal window by default. The report is always on your
  clipboard after submit; the auto-open-browser behaviour is
  now opt-in via Settings (Settings → "After you submit a bug
  report, automatically open the support form in your default
  browser").
- **#619 — `Ctrl+F4` on a dirty document no longer crashes when
  you pick "Don't Save."** Bug-fix; the close-path save prompt
  was queuing an `editor.SetFocus` via `CallAfter` that fired
  after the close had already destroyed the editor TextCtrl.
  The Save and Cancel paths are unchanged; the Save path still
  returns focus to the editor as before.
- **BR-013 follow-on — Print-page detector now classifies a
  right-margin continuation as high confidence and surfaces
  the trailing letter.** When a braille document uses a
  right-margin print-page number on line 1 and the next page
  carries the same digits with a trailing continuation letter
  (for example `7` on braille page 1 and `7a` on braille page
  2), the print page has not actually changed — the letter is
  the braille continuation marker. The Phase 2 detector used
  to score that pattern as `medium` confidence and silently
  drop the letter, so the detailed status read `Print 7`
  instead of `Print 7a`. The detector now matches the previous
  page's right-margin digits, classifies the boundary as
  `high` confidence, and reads the trailing letter back
  through to the status string. In practice: open a braille
  document with right-margin print-page numbers, move the
  caret across a continuation, and the status bar (and
  "Read Detailed Braille Status") reads the full `7a` form
  rather than just `7`.

## Translation and Community Localization

QUILL uses a standard GNU gettext pipeline (`POT → PO → MO`) for all user-visible strings, aligned with the model used by NV Access for NVDA. This means QUILL translation work feels familiar to anyone who has contributed to NVDA, JAWS scripts, or other accessibility-focused open-source software.

### How the Translation Pipeline Works

1. **Source strings are marked in code** with `_()` for regular strings, `ngettext()` for plural forms, and `lazy_gettext()` for strings that must be translated at display time rather than at import time.
2. **The POT file** (`quill/locale/quill.pot`) is the master template, generated automatically by `pybabel extract`. It contains every translatable string in the application.
3. **PO files** (`quill/locale/<lang>/LC_MESSAGES/quill.po`) contain the actual translations for each language. Translators work in PO files.
4. **MO files** are compiled from PO files by `pybabel compile` and are the binary files QUILL loads at runtime.
5. **QUILL selects the active language** at startup from your `language` setting (BCP 47 tag, e.g., `fr`, `es`, `pt-BR`). If blank, QUILL follows the operating-system language.

Speech strings — text that will be read aloud by a screen reader rather than displayed visually — are marked with a `# SPEECH:` comment in the source code. Translators should preserve the natural spoken rhythm of these strings, not just their semantic meaning.

### Switching QUILL's Display Language

Once a translation is installed, you can switch the language QUILL uses for its menus, dialogs, and spoken messages from inside the app:

1. Open **Tools > Writing and Language > Change Display Language...**
2. Choose a language from the list, or **System default** to follow your operating system. Only languages with a compiled translation (`.mo`) appear, so you never pick one that has nothing to show.
3. QUILL saves your choice and applies it to new spoken messages right away. Restart QUILL so every menu and dialog reloads in the chosen language.

If no translations are installed yet, QUILL tells you it is English-only for now; the command starts offering languages as soon as community translations ship.

### Contributing Translations

To contribute a translation:

1. **Fork the QUILL repository** and create a branch named `l10n/<lang>` (e.g., `l10n/fr`).
2. **Copy `quill.pot` to your language folder:** `quill/locale/fr/LC_MESSAGES/quill.po`
3. **Translate each `msgid` into a `msgstr`.** Leave `msgstr` empty for strings you have not yet translated; the English fallback will be used.
4. **Run the CI translation check** to verify placeholder integrity and completeness: `python -m quill.tools.check_translation`
5. **Open a pull request.** The Translation Coordinator reviews and merges approved translations.

**Tools that help:**

- [Poedit](https://poedit.net/) — free, accessible PO file editor with spell check.
- [Virtaal](https://virtaal.translatehouse.org/) — lightweight alternative.
- Crowdin (when QUILL's project is live) — browser-based collaborative translation with a review queue.

**Do not translate:**

- Placeholder tokens: `{name}`, `%(count)s`, `{path}` — leave these exactly as they are in the `msgid`.
- ARIA role names: `"dialog"`, `"button"`, `"listbox"` — these are passed to platform accessibility APIs unchanged.
- Internal command identifiers: `"file.open"`, `"glow.audit"` — these are not user-visible.
- File extensions and format names: `.docx`, `EPUB`, `PDF`.

### Translation Roles and Responsibilities

QUILL follows a four-tier model aligned with NV Access community practice:

| Role | Responsibilities |
|------|----------------|
| **Translator** | Translate strings from English into the target language. |
| **Proofreader** | Review translations for accuracy, tone, and natural language flow. |
| **Language Coordinator** | Own quality for one language; approve or request changes from translators and proofreaders. |
| **Translation Coordinator** | Oversee the whole translation project, manage Crowdin, coordinate string freeze, credit contributors. |

To become a translator or proofreader: open a GitHub issue with the label `translation` and state the language you want to work on.

### Speech String Guidelines

QUILL marks screen-reader-targeted strings with `# SPEECH:` in the source code. When translating these strings:

- **Prioritise spoken clarity over literal accuracy.** A string that reads well when spoken aloud is more important than a string that is grammatically perfect but awkward when heard.
- **Match the rhythm.** Short speech strings should stay short. QUILL's screen-reader users hear these strings dozens of times per session; brevity is a form of accessibility.
- **Preserve emphasis signals.** Where the English string uses word order or phrasing to signal importance (e.g., the key word comes first), try to mirror that in translation.
- **Test with a screen reader.** If possible, test your translated strings with NVDA or JAWS before submitting.
- **Ask if unsure.** Open a GitHub issue tagged `translation` and `speech` if you are uncertain how a speech string should be adapted.

String freeze happens before each release candidate. No new strings are added after freeze, and translators have a two-week window to complete their language before the release is built.

## Checking for Updates

Quill can check for and install updates automatically while you work.

### Manual update check

To check for updates now:

1. Press Alt+H to open the **Help** menu.
2. Press U for **Check for Updates**.
3. If a newer version is available, Quill will announce it and ask for permission to download.
4. If you accept, Quill downloads the update in the background and announces when it is ready.
5. The next time you close and reopen Quill, the update is applied automatically.

### Automatic update checks

You can enable Quill to check for updates on startup:

1. Press Alt+E to open the **Edit** menu.
2. Press Shift+S for **Settings**.
3. In the **Updates** section, enable **Check for updates on startup**.

When automatic checks are on, Quill will notify you quietly if a new version is available, and you can choose to download it when you are ready.

### Update size and speed

Quill uses incremental updates ("micro-updates"), which are much smaller than full reinstalls. Patches often download in seconds rather than minutes, and your settings, documents, and preferences are preserved.

### Staying on a release channel

By default, Quill checks the stable update channel and only offers released versions. To opt into beta versions and test new features early, enable **Beta channel** in **Settings → Updates**.

## Beta Feedback and Bug Reporting

Quill is ready for serious beta use, and Quill 0.5.0 Beta now ships a real in-app support starting point.

### What exists today

Today, Quill already has the foundations for careful support work:

- recovery state
- notifications
- extraction review
- bad-extraction package export for extraction-related issues
- a general-purpose **Save Diagnostics...** command that writes a local bundle
- a **Report a Bug...** command that lets you review the report in-app and then opens the Community Access support-hub form with environment context
- a diagnostics runbook and PRD-backed support model in the documentation set

### What still needs to improve

Today, Quill still does **not** yet ship a polished no-login secure upload path directly from the desktop app, and the support handoff still depends on a browser form after the in-app review step.

### Best beta-launch recommendation

Before the broadest public rollout, publish one secure feedback route that does not require GitHub login. The best release-quality path is still:

1. a BITS-controlled HTTPS feedback form
2. optional upload of a user-reviewed diagnostics bundle
3. a plain-language bug template with environment summary and reproduction steps
4. the current **Help -> Report a Bug...** handoff kept as the guided in-app bridge until the fuller route is live

Until that exists, use the current Help-menu path as the practical bridge. The important improvement in Quill 0.5.0 Beta is that Quill now helps users gather diagnostics locally, review what is being shared, and start a structured support report without forcing them to begin outside the tool.

## A Fast Shortcut Tour

If you want a compact set of shortcuts to remember first, start here:

- `Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `Ctrl+Shift+S`
- `Ctrl+Shift+P` for the Command Palette
- `Ctrl+F`, `F3`, `Shift+F3`, `Alt+F3`
- `Ctrl+G` and `Ctrl+Shift+G`
- `Ctrl+K` and `Ctrl+Enter`
- `Ctrl+Shift+Grave, L` for List Manager; `F2` for the Structured List Studio
  (`Shift+F2` for Insert Special Character)
- `F9` to hold-to-dictate, `Ctrl+F9` for Locked Dictation (`Alt+F9` speaks the
  dictation state)
- `F7`, `Ctrl+F7`, `Ctrl+Shift+F7`, `Shift+F7`
- `Ctrl+Shift+W` for Word Count
- `Ctrl+Tab` and `Ctrl+Shift+Tab`
- `F6` and `Shift+F6`
- `Alt+Z` for soft wrap

Then open **Help → Open Keyboard Reference** and let Quill teach you the rest from your actual active layout.

## Closing Thought

The best way to understand Quill is to use it on something real: a note you care about, an extracted PDF that needs trust review, an EPUB chapter you want to navigate, a Markdown file you want to clean up, or an HTML document you want to make more usable.

Quill is trying to feel like a skilled guide sitting just beside the editor, not standing in front of it. If it succeeds, you will notice something simple: you spend less time wondering what the application can do, and more time deciding what you want to do next.

## Quillins: Extensions

Quill supports **Quillins** — extensions that add commands, snippets, menus, abbreviations, smart triggers, settings pages, status bar cells, and document event handlers to the editor without requiring a full app restart. Each Quillin runs in its own worker process, which isolates faults (a runaway extension cannot crash or corrupt the editor) but is not a security sandbox — the worker is a plain Python interpreter, so the real boundary is code review and the Author Covenant, not technical enforcement. QUILL renders every control using accessible, screen-reader-friendly stock widgets — a Quillin never touches wxPython directly.

### Bundled Quillins

QUILL ships fourteen trusted, first-party Quillins enabled by default:

- **Smart Insert** (`com.quill.smartinsert`) — abbreviations and smart text triggers for everyday templates. Contributes `qbug`, `qmeet`, `qlog`, `qtodo`, and `qbrf` abbreviations, as well as `=bug()`, `=meeting()`, `=journal()`, `=todo()`, `=logentry()`, `=brftest()`, and `=rand()` smart triggers. Settings are under **Preferences → Smart Insert**.
- **BRF Tools** (`com.quill.brftools`) — preferences for braille translation defaults, page handling, status bar display, and diagnostics. Requires the QUILL Braille Pack. Settings under **Preferences → BRF Tools**.
- **Journal Stamp** (`com.quill.journalstamp`) — inserts a date header when you create a new journal document; announces your word count (and daily goal progress) after every save; announces session restores. Listens to `quillin.enabled` to log activation and `settings.changed` to hot-reload preferences. Settings under **Preferences → Journal Stamp**.
- **Document Guardian** (`com.quill.docguardian`) — warns before closing short or unfinished documents; optionally stamps an `Updated:` line before each save; optionally speaks the file name and size after each save. Uses `quillin.enabled`, `quillin.disabled`, and `quill.shutdown` lifecycle events. Settings under **Preferences → Document Guardian**, which has Close Guard, Save Stamp, Save Confirmation, and Lifecycle Announcements tabs. The Lifecycle Announcements tab controls whether the activation and deactivation cue is spoken; the setting defaults to off so first-run is quiet for screen-reader users.
- **Status Scribe** (`com.quill.statusscribe`) — adds a live word/character/sentence count to the status bar. The count updates after every save and when you switch tabs. Uses the `ui.log` capability to write developer messages to the Developer Console. Settings under **Preferences → Status Scribe**.
- **Text Tools** — advanced text transformations: line numbering, hard-wrap, regex match counting, and block filtering.
- **Insert Tools** — date, time, and date-and-time snippets in the **Insert → Date and Time** submenu.
- **Line Tools** — cursor-aware line operations.
- **Markdown Helpers** — syntax assistance for Markdown documents.
- **Insert Character** — a searchable character picker for Unicode symbols.
- **Word Count (Node)** — word count via the Node.js Quillin runtime, demonstrating that Quillins can be written in JavaScript as well as Python.
- **AI Writing Prompts** — additional prompt library entries contributed by the Quillin manifest.
- **AI Writing Skills** — pre-built `.sqp` skill files for rewriting, meeting-notes extraction, and research drafts.
- **Math Equations** — inserts LaTeX or MathML equations at the cursor via **Insert → Insert Equation...** (`Ctrl+Shift+E`); see Math Equations earlier in this guide.

### Quillin Preferences

Every enabled Quillin that declares settings appears as its own entry at the bottom of the Preferences hub (Ctrl+Comma). Navigate to the Quillin by name and press Enter to open its settings dialog.

**Settings tabs.** A Quillin with several groups of settings organizes them into tabs. Use the left and right arrow keys to move between tabs; Tab reaches the tab's controls. Changing tabs does not reset unsaved settings; all changes are applied when you press Save.

**Accessible labels.** Every labeled control (combo box, text field, numeric spinner) is preceded by its `StaticText` label in Windows Z-order so JAWS and NVDA announce the correct label when you Tab to a field. `wx.CheckBox` controls carry their own label text and are exempt.

### Document Events

Quillins can subscribe to document lifecycle events and run code automatically — no user action required. Fourteen events are available:

| Event | When it fires |
| --- | --- |
| `document.opened` | A file was opened from disk |
| `document.activated` | You switched to this tab |
| `document.before_save` | Right before saving |
| `document.after_save` | After a successful save |
| `document.before_close` | Before a tab closes |
| `document.after_close` | After a tab closes |
| `document.created` | A new blank document was created |
| `document.loaded_from_session` | A document was restored from a crash |
| `smart_trigger.entered` | A smart trigger was activated |
| `abbreviation.expanded` | An abbreviation was expanded |
| `quillin.enabled` | This Quillin was just enabled or QUILL started with it on |
| `quillin.disabled` | This Quillin was disabled in the Manager |
| `quill.shutdown` | QUILL is about to close |
| `settings.changed` | A setting owned by this Quillin changed |

Event subscriptions can be filtered by file extension, path pattern, or content. A journal Quillin can limit itself to `**/journal/**` paths; a `.LOG` handler can require the file to start with `.LOG`.

Each subscription carries an `enabled_by_default` field. When an author sets it to `false`, the handler starts inactive — useful for optional or potentially noisy behaviors. You can toggle any event on or off per-Quillin from the **Quillins Manager → Configure Events...** dialog.

Handlers call `api.announce()` to speak results; they must not block the UI thread.

**Reset controls.** Every preference page offers Reset options:

- **Reset this setting** — restores the single setting to its manifest default.
- **Reset this section** — restores all settings in the section.
- **Reset this Quillin** — restores all settings for the Quillin to their manifest defaults.

**Settings storage.** Each Quillin's settings are stored at `%APPDATA%\Quill\quillin_settings\<quillin-id>.json`, written atomically. Disabling a Quillin hides its preference page but keeps its stored settings. Uninstalling prompts you to keep or delete the data.

### The Quillins Manager

Open via **Tools → Quillins**. The Manager lets you:

- See every installed Quillin and its current status (enabled or disabled, or invalid with an error).
- Select a Quillin to review its details: name, version, author, description, categories, minimum required QUILL version, declared capabilities, network host allowlist, and the on/off status of each event subscription.
- **Enable** or **Disable** a Quillin without removing it. Changes take effect immediately.
- **Configure Events...** — opens a dialog listing every document event subscription for the selected Quillin with a checkbox next to each. Check to activate a handler, uncheck to stop it. The state is saved immediately and persisted across restarts.
- **Reload** — re-reads all Quillins from disk without restarting. Use this after editing a bundled Quillin during development.
- **Remove** — uninstall a Quillin (confirmation required). The extension directory is deleted from disk.
- **Install from Folder** — select a local folder containing a Quillin. QUILL validates its `manifest.json`, copies the folder into your per-user extensions directory, and enables it immediately. This is the supported path for installing third-party Quillins once the SEC-8 gate lifts.

When you select a Quillin, the details pane shows all declared capabilities (for example `fs.read`, `net`, `settings.own.read`, or `settings.own.write`), any `net_allowed_hosts` restrictions, and the current on/off state of each event subscription. Review capabilities before enabling a Quillin from an unknown source.

If a Quillin fails to load — because it requires a newer QUILL version (`min_quill_version`), a missing dependency (`requires`), or a manifest error — the error is shown in the details pane so you know what is blocking it.

### Authoring Quillins

For developers, Quillins are designed to be "screen-reader-first." They follow a strict capability model: a Quillin must declare the minimum set of permissions it needs, and any sensitive action (like writing to a file or changing a setting) is consent-gated at runtime.

Quillins can contribute:

- **Commands** — Python or Node.js handlers, or declarative snippets.
- **Menus** — items in the standard QUILL menu bar.
- **Hotkeys** — keyboard bindings that respect the QUILL key chord prefix.
- **Abbreviations** — typed shortcuts that expand after a delimiter.
- **Smart triggers** — `=name()` typed commands on the current line.
- **Sound events and sound packs** — custom earcons tied to Quillin-specific events.
- **Preferences** — structured settings pages with tabs, sections, validated controls, search keywords, and per-Quillin storage.
- **Document events** — lifecycle handlers that fire automatically when a document opens, saves, closes, is restored, or when the Quillin itself is enabled, disabled, or the app shuts down.
- **Status bar cells** — live cells that the host refreshes and displays in the QUILL status bar. Requires the `ui.status` capability.
- **Categories** — one or more taxonomy labels (`writing`, `accessibility`, `braille`, `productivity`, and more) for filtering in the Manager.
- **Dependencies (`requires`)** — declarations that another Quillin must be installed before this one loads. QUILL enforces these at discovery time.
- **Network host allowlist (`net_allowed_hosts`)** — when declaring the `net` capability, restrict outbound connections to a named list of hostnames or wildcard patterns. QUILL blocks connections to any unlisted host even if the user has granted blanket `net` consent.
- **Minimum version (`min_quill_version`)** — declare the oldest QUILL release the Quillin supports. QUILL rejects it at load time if the running version is too old.

See `docs/quillins.md` for the full authoring reference.

---

## AI Assistant

QUILL includes a built-in AI assistant. You can run it on-device (llama.cpp with a local GGUF model) or connect a provider: Ollama (local), Ollama Cloud, OpenAI, Claude, OpenRouter, Google Gemini, or a custom OpenAI-compatible endpoint. Providers are optional and selected explicitly. API keys are stored in the Windows Credential Manager by default, with a DPAPI-encrypted fallback, and never written to disk in plain text.

### Setting up an AI provider

Open **AI > AI Hub...** to configure your providers. The AI Hub is the single place for every provider's key, model, **Test Chat**, and per-provider key removal — the former **AI Model and Connection** and **Forget API Key** menu items were merged into it.

- **OpenRouter** — paste your API key into the OpenRouter API Key field. OpenRouter gives you access to many models (Claude, GPT-4o, Gemini, and more) with a single key.
- **OpenAI** — paste your OpenAI API key.
- **Ollama** — no key needed. Install Ollama on your machine (`ollama serve`) and QUILL detects it automatically at `http://localhost:11434`. Change the Ollama Base URL setting if you run Ollama on a different port or machine.

### Portable mode and key storage

By default QUILL stores AI provider keys in the **Windows Credential Manager**, which ties them to your Windows user account. If you run QUILL from a self-contained folder — for example on a network share or an external drive — portable mode puts all of your keys in that same folder alongside your other QUILL data.

**Activating portable mode.** The portable bundle ships with an empty `data\` folder next to `quill.exe`, and QUILL recognises that folder as the portable opt-in. No environment variable to set, no checkbox to tick — just run `quill.exe` from the bundle root. The Setup Wizard's **Data location** page detects the portable install and offers the portable radio button automatically. If you want to convert an installed build into a portable one, copy the install folder to a USB drive and create an empty `data\` folder at its root; QUILL will switch to portable mode the next time it starts from that folder.

The previous activation mechanism (`QUILL_PORTABLE=1`) is no longer required and is ignored: portable mode is a property of the bundle, not of the running environment.

When portable mode is on, keys are stored in a file called `keys.enc` inside the QUILL data directory. The file is encrypted with Windows DPAPI, so it is protected by your Windows user-account key.

**Limitations.** The encrypted file is tied to the Windows account that created it. Moving it to a different machine or a different Windows account will fail to decrypt; you will need to re-enter your keys there. Portable mode gives you a self-contained folder on the same machine — it does not give you cross-machine portability.

**Environment-variable overrides (for CI and developers).** You can supply keys directly via environment variables regardless of which mode is active. These always win and are never stored to disk:

| Provider | Environment variable |
| --- | --- |
| OpenRouter | `QUILL_OPENROUTER_KEY` |
| OpenAI | `QUILL_OPENAI_KEY` |
| Ollama Cloud | `QUILL_OLLAMA_KEY` |
| AI Assistant | `QUILL_ASSISTANT_KEY` |

You can also set a **Default model for prompt runs** (`ai_prompt_default_model`). Leave it blank to share the same model across Ask AI and the Prompt Library, or set a different model here if you want a more capable model for prompt-library work.

### Ask AI (quick one-off question)

`AI > Writing Assistant...` (Alt+Q) opens the message-style assistant where you can ask questions, draft text, propose edits, and run Quill commands with approval before changes are applied. The active provider and model are shown, and you can switch between providers and models in-dialog. Use **AI > Ask AI...** (Command Palette) for a simpler one-shot prompt-and-response dialog when you do not need insertion or follow-up.

- **Provider** and **Model** choices are pre-filled with the last values you used.
- If a provider and model are already configured, focus lands directly in the Prompt field so you can start typing immediately. If not yet configured, focus starts on the Provider choice to guide you through setup.
- Press **Ctrl+Enter** or the **Send** button to submit. QUILL announces "Sending..." and disables the button while the request is in flight.
- The response opens in a read-only dialog. Use cursor keys to read it, and **Copy to Clipboard** to copy the full text. Closing the response returns you to the Ask AI dialog so you can ask a follow-up.
- **Clear** resets the prompt field and refocuses it.

### Check Grammar with AI

`Edit > Grammar > Check Grammar with AI` sends the selected text (or the full document if nothing is selected) to your AI model with a grammar-review prompt. The response dialog lists corrections in the form "original phrase → corrected phrase — reason". No changes are applied automatically; you apply corrections yourself.

The default grammar instruction is: review the text and list only the corrections needed; do not rewrite the passage. If you want a different instruction, open the Prompt Library, find the "Check Grammar" built-in prompt, and edit its text — the command picks up your version automatically.

### Prompt Library

`AI > Prompt Library...` opens the full prompt management dialog.

**What it shows.** A searchable list of all prompts on the left (type in the search field to filter by name or category). The selected prompt's instruction text on the right. An optional input text field where you can type or paste text to use as the selection context.

**Running a prompt.**
1. Select a prompt from the list (or type in the search field to find it).
2. Optionally paste text into the input field. If blank, QUILL uses the current editor selection or full document.
3. Press **Run with AI**. The result opens in the AI Response dialog.

**Managing prompts.**

- **New Prompt** — opens a small dialog: enter a name, choose a category, and write the instruction text. Use `{selection}` where you want QUILL to insert the text.
- **Edit** — modify the name, category, or instruction of a selected user prompt. Built-in prompts can have their text overridden (the override is saved; the original is never deleted).
- **Disable/Enable** — hides or shows a prompt in the list without deleting it. Useful for built-ins you never use.
- **Delete** — removes a user-created prompt. Built-in prompts cannot be deleted.

**Importing and exporting prompt packs.**

QUILL uses `.pqp` (Prompt Quill Pack) files to share prompt collections.

- **Import .pqp** — opens a file picker; imports all prompts from the file. Prompts whose names already exist in your library are skipped.
- **Export .pqp** — saves all your user-defined prompts to a `.pqp` file you can share or back up.

A `.pqp` file is plain JSON with a human-readable structure:

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

**Built-in prompts.** QUILL ships 12 built-in prompts across five categories. These are always present and fully editable; they cannot be deleted.

| Category | Prompt names |
| --- | --- |
| Editing | Check Grammar, Improve Clarity, Fix Grammar, Make Concise, Active Voice, Formal Tone, Conversational Tone |
| Writing | Continue from Here |
| Structure | Convert to Bullet Points |
| Research | Define This Term, Find Counterarguments |

**Quillin-contributed prompts.** Quillins can ship a `prompts.json` file that adds prompts to the library. The bundled `ai-writing-prompts` Quillin contributes 7 additional prompts (Expand This, Vary Sentence Rhythm, Make More Vivid, Write a Title, Generate Outline, Suggest Supporting Evidence, Plain Language). These appear in the list and can be run like any other prompt; they are not persisted to your library file.

### Skill Library (.sqp skills)

Skills are multi-step AI workflows. Where a prompt is one instruction, a skill is a sequence of steps where each step can use the output of the step before it.

`AI > Skill Library...` opens the Skill Library dialog.

**What a skill looks like.** A skill has a name, a description, and a list of steps. Before running, QUILL shows a parameter dialog if the skill declares any parameters (such as tone, target reading level, or output format). Each step runs in order, sends its prompt to the AI, and stores the response for the next step to use.

**Bundled skills.** QUILL ships four skills in the `ai-writing-skills` Quillin:

- **Accessible Rewrite** — Analyses your text for plain-language issues (long sentences, passive voice, jargon), then produces a targeted rewrite. You choose the target reading level (Grade 6, 8, or 10). The rewritten text replaces the selection when you Accept.
- **Research and Draft** — Extracts the central topic from your selection, gathers five supporting facts, then drafts a paragraph at your chosen tone and length.
- **Meeting Notes to Action Items** — Reads meeting notes, extracts every action item with owner and deadline, checks for missed items, and produces a clean follow-up summary. Output goes to clipboard.
- **Argument Strengthener** — Identifies your argument's logical structure, finds weaknesses and counterarguments, then produces a strengthened version tailored to your chosen audience.

**Running a skill.**
1. Open **AI > Skill Library...**
2. Select a skill from the list.
3. Press **Run**. If the skill has parameters, a small dialog appears — fill in the choices and press OK.
4. QUILL announces "Running step 1 of N..." as each step executes.
5. When complete, the result dialog appears. Read the output, then press **Accept** to apply it (if the skill places output in the document) or **Copy** to copy to clipboard.

**No streaming.** Each step sends a complete prompt and waits for the full response before the next step begins. This makes step outputs reliable and readable between steps.

**Authoring and sharing skills.** A skill is a `.sqp` (Skill Quill Pack) file — a plain Markdown document with YAML front matter. Open any `.sqp` file in QUILL to read and edit it. Share skills by sharing the file. See `docs/quillins.md` §20 for the full authoring reference, and `docs/userguide.md` for a guided walkthrough.

**Validating a skill file.** Run `python -m quill.tools.sqp_validator yourskill.sqp` to check for errors before sharing or shipping.

## Control Reference

The Control Reference is a full listing of every focusable control in QUILL, organized by section. For each control it shows: what the control does, what keyboard shortcuts apply to it, and which section of this guide covers it in depth.

See [docs/CONTROL_REFERENCE.md](CONTROL_REFERENCE.md) for the full reference.

The reference is auto-generated from `quill/core/help/topics.json`. To regenerate it after adding new topics:

```powershell
python -m quill.tools.build_docs
```


---

# Appendix: QUILL Developer Console

_Folded in from the former docs/userguide.md on 2026-06-13._

# QUILL Developer Console (QDC) documentation

_Consolidated on 2026-06-13 from qdc-tutorial and "QUILL Developer Console and Automation". The scripting contract (docs/quillins.md) remains a standalone document because code references it by section number._

> **Status note (2026-06-13, supersedes the per-section "Planned for 1.1" lines below).**
> The QDC is implemented and reachable in 0.5.0 under the Developer and Power Text
> and Full QUILL profiles (Tools > Advanced > Developer Console). The Python
> console and the `q` scripting API are wired (`quill/core/scripting.py`,
> `quill/ui/main_frame_devtools.py`), including the facades `q.selection`, `q.doc`,
> `q.editor`, `q.settings`, `q.profile`, `q.bookmarks`, `q.quillins`, `q.macros`
> (+`q.begin_macro`/`q.end_macro`), `q.spell`, `q.diagnostics`, plus
> `q.a11y`/`q.commands`/`q.focus`/`q.support` and `q.describe_command`. The
> TypeScript console runs through a Node subprocess. Sections below that still say
> "Planned for 1.1" predate this and are being reconciled; treat this note as the
> current status. (Tracked in `docs/planning.md` Part 2 / map item P1-3.)


---

<!-- Source: docs/qdc-tutorial.md -->

# QUILL Developer Console Tutorial

Status: **Implemented in 0.5.0** (Developer and Power Text / Full QUILL profiles;
Tools > Advanced > Developer Console). The Python console and the `q` scripting
API are wired; the TypeScript console runs via a Node subprocess. See the status
note at the top of this document for the exact `q` surface. (Some passages below
were written against the original 1.1 plan and may describe a richer API than the
current build; the status note is authoritative.)

---

## What the QDC is

The QUILL Developer Console (QDC) is an embedded scripting surface for
developers, power users, and accessibility professionals. It lets you inspect
and automate the running editor without rebuilding or adding temporary menu
items.

The QDC is not for ordinary users. It is profile-gated and off by default for
Essential, Writer, and Reader profiles. It appears as a first-class feature for
Developer and Power Text profiles.

There are two consoles:

- **Python console** — runs in-process. Full access to the scripting API via `q`.
  Prompt: `>>>` (continuation `...`).
- **TypeScript console** — runs through a Node subprocess bridge. Async API via
  `quill`. Prompt: `ts>` (async pending `ts*>`).

Both are read through the same transcript window and announced through QUILL's
standard accessibility announcement path.

---

## Opening the console

Menu: `Tools > Advanced > Developer Console > Open Python Console`
or `Open TypeScript Console`.

Command palette: `quill.console.openPython` / `quill.console.openTypeScript`.

The console opens as a separate dialog. Press `Esc` to return focus to the
editor. The dialog stays open and preserves its namespace until you explicitly
close it.

---

## Console layout

The console has five areas, navigable with `F6`:

1. **Transcript** — read-only. Shows prompts, output, errors, and return values.
2. **Input** — single-line by default; `Shift+Enter` adds a newline for multi-line
   blocks.
3. **Language selector** — switch between Python and TypeScript.
4. **Status line** — current language, prompt state, active document, worker status.
5. **Buttons** — Run, Clear, Copy transcript, Save transcript, Insert snippet, Help, Close.

---

## Keyboard reference

| Key | Action |
| --- | --- |
| Enter | Execute current command |
| Shift+Enter | Insert newline (multi-line input) |
| Ctrl+Enter | Force execute multi-line block |
| Up / Down | Previous / next history (when cursor is at line boundary) |
| Ctrl+L | Clear transcript |
| Ctrl+Shift+C | Copy transcript |
| Ctrl+S | Save transcript |
| Ctrl+F | Find in transcript |
| F6 | Move between transcript, input, status, and buttons |
| Esc | Return focus to editor |
| F1 | Console help |
| Ctrl+Space | Trigger completion |

---

## Python console

### Available names

The following names are in scope when the console opens:

| Name | What it is |
| --- | --- |
| `q` | Primary QUILL scripting API — start here |
| `app` | Application-level read-mostly object |
| `commands` | Command registry facade |
| `doc` | Active document snapshot |
| `editor` | Active editor snapshot |
| `sel` | Current selection snapshot |
| `caret` | Current caret snapshot |
| `profile` | Active feature profile snapshot |
| `settings` | Safe settings facade |
| `diagnostics` | Diagnostics facade |
| `a11y` | Announcement / testing facade |
| `log` | Console-safe logger |
| `wx` | wx module (Developer profile only) |

`doc`, `sel`, and `caret` are read-only snapshots of state at the time they were
captured. They do not update automatically. Call `q.refresh_context()` to pull
current state, or they update automatically when the active document changes.

### Basic operations

Insert text at the cursor:

```python
>>> q.insert_text("Hello from QUILL.")
```

Replace the current selection:

```python
>>> q.replace_selection("Replacement text")
```

Jump to a line:

```python
>>> q.goto_line(42)
```

Run a built-in command by ID:

```python
>>> q.run_command("quill.document.wordCount")
```

Send a screen-reader announcement:

```python
>>> q.a11y.announce("Test announcement.")
```

### Inspecting state

Read the active document name:

```python
>>> doc.name
'notes.txt'
```

Read the current selection:

```python
>>> sel.text
'selected words here'
```

Read the caret position (1-based line and column):

```python
>>> caret.line, caret.column
(12, 5)
```

Search for commands by keyword:

```python
>>> commands.search("spell")
['quill.spell.check', 'quill.spell.addWord', 'quill.spell.nextError']
```

Get a diagnostic summary (useful for support tickets):

```python
>>> q.support.diagnostic_summary()
```

### Accessibility diagnostics

Read the last screen-reader announcements:

```python
>>> q.a11y.last_announcements()
['Title Case applied', '5 words selected']
```

Describe the currently focused region:

```python
>>> q.focus.describe()
'Editor: notes.txt, line 12, col 5, no selection'
```

### Multi-line blocks

Use `Shift+Enter` to add newlines, then `Enter` or `Ctrl+Enter` to execute:

```python
>>> def count_words(text):
...     return len(text.split())
...
>>> count_words(doc.text)
487
```

### Macro recording

Record a sequence of commands as a reusable macro:

```python
>>> q.begin_macro("Clean OCR text")
>>> q.run_command("quill.text.normalizeUnicode")
>>> q.run_command("quill.text.dehyphenateLines")
>>> q.run_command("quill.text.reflowParagraphs")
>>> q.end_macro()
Macro saved: "Clean OCR text"
```

---

## TypeScript console

The TypeScript console requires Node.js on PATH. If Node.js is not found, QUILL
announces the requirement and offers installation assistance.

### TypeScript prompt behavior

```text
ts> await quill.insertText("Hello.");
ts*>
Result: undefined
```

`ts>` is the ready prompt. `ts*>` means an async operation is in flight. Results
and errors appear in the transcript automatically.

### Available globals

| Global | What it is |
| --- | --- |
| `quill` | Async QUILL scripting proxy |
| `console` | Captured: `.log()`, `.warn()`, `.error()` appear in transcript |
| `setTimeout` / `clearTimeout` | Standard timer |
| `AbortController` | For cancellable operations |

### Basic operations

Insert text:

```ts
ts> await quill.insertText("Hello from TypeScript.");
```

Replace selection:

```ts
ts> await quill.replaceSelection("Replacement text");
```

Jump to a line:

```ts
ts> await quill.gotoLine(42);
```

Run a built-in command:

```ts
ts> await quill.runCommand("quill.markdown.normalizeHeadings");
```

### Inspecting state

```ts
ts> const doc = await quill.activeDocument();
ts> console.log(doc.name);
notes.txt
```

```ts
ts> const stats = await quill.documentStats();
ts> console.log(`${stats.words} words, ${stats.lines} lines`);
487 words, 38 lines
```

### Multi-line TypeScript

Use `Shift+Enter` to enter a multi-line block, `Ctrl+Enter` to execute:

```ts
ts> const text = await quill.getText();
ts> const words = text.trim().split(/\s+/).filter(Boolean);
ts> await quill.announce(`${words.length} words`);
```

### TypeScript type definitions

QUILL ships `quill-console.d.ts`. If you have Node.js and an IDE, copy it into
your project to get completion:

```ts
// quill is typed as:
interface QuillConsoleApi {
  insertText(text: string): Promise<void>;
  replaceSelection(text: string): Promise<void>;
  gotoLine(line: number): Promise<void>;
  runCommand(commandId: string, args?: Record<string, unknown>): Promise<unknown>;
  activeDocument(): Promise<QuillDocumentSnapshot>;
  documentStats(): Promise<QuillDocumentStats>;
  announce(text: string): Promise<void>;
}
```

---

## Screen-reader notes

- New output in the transcript is announced without stealing focus.
- Errors are announced with the prefix "Error".
- Return values are announced with the prefix "Result".
- Long output is summarized in the announcement; review the transcript with your
  screen reader for the full text.
- `Ctrl+Shift+C` copies the transcript at any time.
- The console uses QUILL's central Prism announcement path — the same one used
  by all other QUILL announcements.
- No custom-drawn controls are used.

---

## Console safety settings

`Tools > Advanced > Developer Console > Console Safety Settings`
or command `quill.console.openSafetySettings`.

Settings:

| Setting | Default | Notes |
| --- | --- | --- |
| Python console enabled | Profile-dependent | Off for Essential / Writer |
| TypeScript console enabled | Profile-dependent | Off except Developer profile |
| Require developer profile | On | Prevents accidental access in Writer profiles |
| Max execution time (Python) | 30 s | Hard kill after timeout |
| Max execution time (TypeScript) | 30 s | Worker restart after timeout |
| Allow `wx` module access | Developer profile only | Not available in any other profile |
| Remote console | Locked off | Not available in QUILL 1.x |

---

## Transcript commands

| Command | What it does |
| --- | --- |
| `quill.console.copyTranscript` | Copy entire transcript to clipboard |
| `quill.console.saveTranscript` | Save transcript to a file |
| `quill.console.clear` | Clear the transcript |
| `quill.console.saveInputAsSnippet` | Save the current input as a named snippet |
| `quill.console.insertSnippet` | Insert a saved snippet into input |
| `quill.console.runSelection` | Run selected text in the transcript as a command |
| `quill.console.runCurrentDocument` | Run the active QUILL document as a script |
| `quill.console.showContext` | Print current snapshot values to transcript |
| `quill.console.resetNamespace` | Reset the Python namespace (clears all variables) |
| `quill.console.restartTypeScriptWorker` | Kill and restart the Node worker |

---

## For Quillin authors: testing your extension in the QDC

The QDC is a useful live test surface for Quillin development. Open the Python
console while your Quillin is loaded and explore its manifest and command
registry entry:

```python
>>> from quill.core.quillins.loader import get_loader
>>> loader = get_loader()
>>> ext = loader.get_extension("com.example.myextension")
>>> ext.manifest
ExtensionManifest(id='com.example.myextension', runtime='python', ...)
>>> ext.manifest.contributes.commands
(ExtensionCommand(id='ext.myext.run', title='My Command', ...),)
```

Invoke a command directly through the command registry:

```python
>>> q.run_command("ext.myext.run")
```

Inspect what a command announced:

```python
>>> q.a11y.last_announcements()
['My command completed: 3 items processed']
```

For Node.js Quillins, the TypeScript console is the natural test surface:

```ts
ts> await quill.runCommand("ext.myext.nodeHandler");
ts> // Check the last announcement
ts> const ann = await quill.lastAnnouncement();
ts> console.log(ann);
```

---

## Implementation status (0.5.0)

The QDC is implemented and reachable under the Developer and Power Text and
Full QUILL profiles (Tools > Advanced > Developer Console). Shipped today:

- The Python console and console window (`quill/devtools/python_console.py`,
  `quill/devtools/console_window.py`) wired through `quill/ui/main_frame_devtools.py`.
- The TypeScript console via a Node subprocess (`quill/devtools/ts_console.py`,
  `quill/tools/ts_worker/worker.js`).
- The `q` scripting API (`quill/core/scripting.py`): the text/navigation/command
  methods plus the facades `q.selection`, `q.doc`, `q.editor`, `q.settings`,
  `q.profile`, `q.bookmarks`, `q.quillins`, `q.macros`
  (+`q.begin_macro`/`q.end_macro`), `q.spell`, `q.diagnostics`, and
  `q.a11y`/`q.commands`/`q.focus`/`q.support`, plus `q.describe_command`.

The scripting contract and its Implementation Status map live in
`docs/quillins.md`. Any passage above that still reads as "planned" predates
this build; the status note at the top of this document is authoritative.


---

<!-- Source: docs/QUILL Developer Console and Automation.md -->

# QUILL Developer Console and Automation API PRD

## Feature name

**QUILL Developer Console and Automation API**

## Status

Proposed for **QUILL 1.1**, with the Python console eligible for a 1.0 experimental/dev-preview flag if the command registry and announcement infrastructure are stable enough.

## Owner

Blind Information Technology Solutions (BITS) and Community Access

## Target platform

Windows 10 and Windows 11

## Target users

* QUILL developers
* QUILL power users
* Accessibility professionals
* Blind programmers and technical writers
* Macro authors
* Support/debugging users working with BITS or Community Access staff
* Future Quillins/plugin developers

## 1. Vision

QUILL should provide a screen-reader-first developer console that lets trusted users inspect and manipulate the running editor through a stable automation API.

The console is not an afterthought, a hidden debug hack, or a generic unsafe scripting surface. It is a first-class, accessible automation layer that exposes QUILL’s command system, document model, editor state, diagnostics, and accessibility announcement pipeline in a predictable way.

The goal is to let a developer or power user type commands such as:

```python
q.insert_text("Hello from QUILL.")
q.goto_line(42)
q.run_command("quill.document.wordCount")
q.run_command("quill.markdown.normalizeHeadings")
```

or, in TypeScript:

```ts
await quill.insertText("Hello from TypeScript.");
await quill.gotoLine(42);
const stats = await quill.documentStats();
console.log(stats.words);
```

Every editor-changing action must go through the QUILL command registry or official scripting API so undo, dirty-state tracking, accessibility announcements, status bar updates, telemetry, and tests remain consistent.

## 2. Problem statement

QUILL is becoming a rich writing and document environment with commands, macros, Quillins, profiles, diagnostics, document intake, spell checking, format conversion, and accessibility-aware UI behavior.

Without a developer console and automation API:

* Developers must debug by adding temporary logging or breakpoints.
* Support staff cannot easily inspect user state during troubleshooting.
* Power users cannot automate repetitive editor actions.
* Macro support risks becoming a separate one-off system instead of using the same command architecture as the rest of QUILL.
* Future Quillins may lack a simple interactive testing surface.
* Accessibility professionals cannot quickly inspect document state, selection state, command availability, profile gating, or announcement behavior.

QUILL needs an embedded, accessible command line for trusted local development and automation.

## 3. Goals

1. Provide an accessible Python console inside the running QUILL app.
2. Provide a TypeScript automation console through a controlled Node subprocess bridge.
3. Expose a stable `q` / `quill` scripting object instead of raw internal objects.
4. Route all mutations through the command registry or official scripting API.
5. Preserve undo/redo, dirty-state tracking, backups, status bar updates, and screen-reader announcements.
6. Make console results easy to review with NVDA, JAWS, Narrator, braille displays, and keyboard-only workflows.
7. Support command history, multi-line input, copy/paste, saved snippets, and transcript export.
8. Gate the feature behind profiles and explicit settings so it does not surprise ordinary users.
9. Make the console useful for macro development, plugin development, support diagnostics, and test automation.
10. Never enable remote execution by default.

## 4. Non-goals

1. QUILL will not provide a public remote execution service in v1.
2. QUILL will not allow untrusted scripts to run silently.
3. QUILL will not expose arbitrary internal object mutation as the recommended workflow.
4. QUILL will not make Python or TypeScript scripting required for normal use.
5. QUILL will not replace a full IDE, debugger, or terminal.
6. QUILL will not guarantee sandbox security for arbitrary malicious code in the local Python console.
7. QUILL will not let scripts bypass document protection, source-file safety, cloud-consent prompts, or profile safety rules.

## 5. User stories

### 5.1 Developer

As a QUILL developer, I want to open a console, inspect the active document, run commands, and test editor behavior without rebuilding or adding temporary menu items.

Example:

```python
q.doc.name
q.selection.text
q.goto_line(100)
q.run_command("quill.find.next")
```

### 5.2 Accessibility tester

As an accessibility tester, I want to inspect the focused region, active command, current screen-reader announcement backend, and the last announcements so I can diagnose what a user experienced.

Example:

```python
q.a11y.last_announcements()
q.a11y.announce("Testing announcement path.")
q.focus.describe()
```

### 5.3 Macro author

As a power user, I want to experiment with commands interactively and save successful sequences as a macro.

Example:

```python
q.begin_macro("Clean OCR text")
q.run_command("quill.text.normalizeUnicode")
q.run_command("quill.text.dehyphenateLines")
q.run_command("quill.text.reflowParagraphs")
q.end_macro()
```

### 5.4 Support technician

As a support technician, I want a user to run a safe diagnostic command and copy the output into an email or support ticket.

Example:

```python
q.support.diagnostic_summary()
```

### 5.5 TypeScript user

As a developer more comfortable with TypeScript, I want to run async commands against QUILL using a typed API and receive clear errors.

Example:

```ts
const doc = await quill.activeDocument();
await quill.gotoLine(25);
console.log(doc.name);
```

## 6. Feature placement

The feature appears in the following command surfaces:

### Tools menu

`Tools > Authoring and Automation > Developer Console`

Submenu items:

* Open Python Console
* Open TypeScript Console
* Open Console Transcript
* Save Current Console as Macro
* Manage Console Snippets
* Console Safety Settings
* Copy Diagnostic Summary

### Command palette

Commands:

* `quill.console.openPython`
* `quill.console.openTypeScript`
* `quill.console.clear`
* `quill.console.copyTranscript`
* `quill.console.saveTranscript`
* `quill.console.saveInputAsSnippet`
* `quill.console.insertSnippet`
* `quill.console.runSelection`
* `quill.console.runCurrentDocument`
* `quill.console.showContext`
* `quill.console.resetNamespace`
* `quill.console.restartTypeScriptWorker`
* `quill.console.openSafetySettings`

### Feature profiles

Default visibility:

| Profile                              | Python console | TypeScript console | Macro recording | Remote console |
| ------------------------------------ | -------------- | ------------------ | --------------- | -------------- |
| Essential                            | Off            | Off                | Off             | Locked off     |
| Writer                               | Quiet          | Off                | Quiet           | Locked off     |
| Reader and Student                   | Off            | Off                | Off             | Locked off     |
| Office and Admin                     | Quiet          | Off                | Quiet           | Locked off     |
| Accessibility Professional           | On             | Quiet              | On              | Locked off     |
| Developer and Power Text             | On             | On                 | On              | Locked off     |
| Braille and Screen Reader Power User | Quiet          | Quiet              | On              | Locked off     |
| Full Quill                           | On             | On                 | On              | Locked off     |

Remote execution remains unavailable unless an experimental developer build explicitly enables it.

## 7. UX requirements

### 7.1 Console window layout

The console is a standard wx dialog or frame using stock controls.

Required controls:

1. **Transcript output**

   * Read-only multi-line `wx.TextCtrl`
   * Receives command output, errors, return values, announcements, and command prompts
   * Supports select all, copy, find, and save transcript

2. **Command input**

   * Editable `wx.TextCtrl`
   * Single-line by default
   * Multi-line mode available with a toggle or `Shift+Enter`
   * Enter runs the current command when the command is complete

3. **Language selector**

   * Python
   * TypeScript
   * Future: command-only mode

4. **Status line**

   * Shows current language, prompt state, active document, and worker status

5. **Buttons**

   * Run
   * Clear
   * Copy transcript
   * Save transcript
   * Insert snippet
   * Help
   * Close

### 7.2 Keyboard behavior

Required shortcuts:

| Shortcut     | Action                                                                                    |
| ------------ | ----------------------------------------------------------------------------------------- |
| Enter        | Execute current command                                                                   |
| Shift+Enter  | Insert newline in multi-line input                                                        |
| Ctrl+Enter   | Force execute multi-line command                                                          |
| Up/Down      | Previous/next command history when input cursor is at boundary                            |
| Ctrl+L       | Clear transcript                                                                          |
| Ctrl+Shift+C | Copy transcript                                                                           |
| Ctrl+S       | Save transcript                                                                           |
| Ctrl+F       | Find in transcript                                                                        |
| F6           | Move between transcript, input, status, and buttons                                       |
| Esc          | Return focus to editor if console is non-modal; close if modal confirmation is not needed |
| F1           | Open console help                                                                         |
| Ctrl+Space   | Trigger completion if available                                                           |
| Tab          | Insert indentation in multi-line mode or move focus depending on setting                  |

### 7.3 Screen-reader behavior

The console must be fully usable with NVDA, JAWS, and Narrator.

Requirements:

* Every control has a clear accessible name.
* The transcript announces new output without stealing focus.
* Errors are announced with the prefix “Error”.
* Return values are announced with the prefix “Result”.
* Long output is not automatically spoken in full; the console announces a summary and lets the user review the transcript.
* The console supports a “copy last result” command.
* The console supports a “speak last result” command.
* The console uses QUILL’s central announcement path.
* Braille users can review the transcript as plain text.
* No custom drawn controls are allowed in the primary console workflow.

### 7.4 Prompt behavior

Python prompt:

```text
>>>
```

Continuation prompt:

```text
...
```

TypeScript prompt:

```text
ts>
```

Async TypeScript pending prompt:

```text
ts*>
```

The prompt itself is included in the transcript but not required in copied code unless the user chooses “Copy with prompts”.

## 8. Python console requirements

### 8.1 Execution model

The Python console runs in-process and uses Python’s embedded interpreter facilities.

The console maintains a persistent namespace for the session. Hiding the console does not destroy the namespace unless the user explicitly resets it.

### 8.2 Default namespace

The following names are available by default:

```python
q              # Primary QUILL scripting API
app            # Application-level read-mostly object
frame          # Main frame, available for debugging
commands       # Command registry read/execute facade
doc            # Active document snapshot
editor         # Active editor snapshot
sel            # Current selection snapshot
caret          # Current caret snapshot
profile        # Active feature profile snapshot
settings       # Safe settings facade
diagnostics    # Diagnostics facade
a11y           # Announcement/testing facade
log            # Console-safe logger
wx             # wx module, developer profile only
```

### 8.3 Snapshot refresh

The console updates snapshot variables when:

* The console opens.
* The active document changes.
* The user runs `q.refresh_context()`.
* A command changes editor state.
* The user chooses “Refresh Console Context”.

Snapshot variables such as `doc`, `sel`, and `caret` are safe read-only snapshots unless explicitly documented otherwise.

### 8.4 Python examples

```python
q.insert_text("Hello from QUILL.")
```

```python
q.replace_selection("Replacement text")
```

```python
q.goto_line(42)
```

```python
q.run_command("quill.document.wordCount")
```

```python
q.a11y.announce("This is a test announcement.")
```

```python
q.diagnostics.document_summary()
```

```python
q.commands.search("spell")
```

## 9. TypeScript console requirements

### 9.1 Execution model

The TypeScript console runs out-of-process through a Node worker.

Python QUILL process:

* Owns the editor, document model, command registry, and UI thread.
* Sends TypeScript code to the Node worker.
* Receives JSON-RPC-style command requests from the worker.
* Executes approved commands on the wx main thread.
* Returns structured results or errors.

Node TypeScript worker:

* Receives TypeScript code.
* Transpiles it to JavaScript.
* Executes it with a limited `quill` proxy object.
* Sends editor actions back to Python as structured requests.
* Captures `console.log`, warnings, errors, and return values.

### 9.2 TypeScript global API

The TypeScript console exposes:

```ts
quill
console
setTimeout
clearTimeout
AbortController
```

The TypeScript worker must not expose unrestricted filesystem, network, process, or shell access through the default console environment.

### 9.3 TypeScript examples

```ts
await quill.insertText("Hello from TypeScript.");
```

```ts
await quill.replaceSelection("Replacement text");
```

```ts
await quill.gotoLine(42);
```

```ts
const stats = await quill.documentStats();
console.log(`${stats.words} words`);
```

```ts
await quill.runCommand("quill.markdown.normalizeHeadings");
```

### 9.4 Type definitions

QUILL ships a `quill-console.d.ts` type definition file so TypeScript users get completion and documentation.

Example:

```ts
interface QuillConsoleApi {
  insertText(text: string): Promise<void>;
  replaceSelection(text: string): Promise<void>;
  gotoLine(line: number): Promise<void>;
  runCommand(commandId: string, args?: Record<string, unknown>): Promise<unknown>;
  activeDocument(): Promise<QuillDocumentSnapshot>;
  documentStats(): Promise<QuillDocumentStats>;
  announce(text: string, options?: AnnouncementOptions): Promise<void>;
}
```

### 9.5 Worker lifecycle

The TypeScript worker starts only when the TypeScript console is opened.

The worker stops when:

* QUILL exits.
* The user closes the console and worker idle timeout expires.
* The user chooses “Restart TypeScript Worker”.
* The worker exceeds memory or time limits.
* The worker crashes.

Worker crashes must not crash QUILL.

## 10. QUILL scripting API

### 10.1 API principles

The scripting API is the official automation surface.

Rules:

1. Mutations go through the command registry.
2. Undo/redo must work.
3. Dirty state must update.
4. Status bar must update.
5. Screen-reader announcements must happen.
6. Profile and feature gates must be respected.
7. Cloud/network actions must still ask for consent.
8. Protected originals must stay protected.
9. Commands must return structured results.
10. Errors must be plain-language first, traceback second.

### 10.2 Python API shape

```python
class QuillScriptAPI:
    def insert_text(self, text: str) -> None: ...
    def replace_selection(self, text: str) -> None: ...
    def selected_text(self) -> str: ...
    def document_text(self) -> str: ...
    def set_document_text(self, text: str) -> None: ...
    def goto_line(self, line: int) -> None: ...
    def goto_offset(self, offset: int) -> None: ...
    def run_command(self, command_id: str, **kwargs): ...
    def command_exists(self, command_id: str) -> bool: ...
    def list_commands(self, query: str | None = None) -> list[CommandInfo]: ...
    def active_document(self) -> DocumentSnapshot: ...
    def document_stats(self) -> DocumentStats: ...
    def refresh_context(self) -> None: ...
```

### 10.3 TypeScript API shape

```ts
interface QuillApi {
  insertText(text: string): Promise<void>;
  replaceSelection(text: string): Promise<void>;
  selectedText(): Promise<string>;
  documentText(): Promise<string>;
  setDocumentText(text: string): Promise<void>;
  gotoLine(line: number): Promise<void>;
  gotoOffset(offset: number): Promise<void>;
  runCommand(commandId: string, args?: Record<string, unknown>): Promise<unknown>;
  commandExists(commandId: string): Promise<boolean>;
  listCommands(query?: string): Promise<CommandInfo[]>;
  activeDocument(): Promise<DocumentSnapshot>;
  documentStats(): Promise<DocumentStats>;
  refreshContext(): Promise<void>;
}
```

### 10.4 Safe facades

The console exposes safe facades instead of raw internals wherever possible.

Required facades:

* `q.documents`
* `q.editor`
* `q.selection`
* `q.commands`
* `q.bookmarks`
* `q.search`
* `q.spell`
* `q.markdown`
* `q.text`
* `q.a11y`
* `q.diagnostics`
* `q.profile`
* `q.settings`
* `q.support`
* `q.macros`
* `q.quillins`

## 11. Command registry integration

Every console-callable command must declare metadata:

```python
Command(
    id="quill.editor.insertText",
    title="Insert Text",
    description="Insert text at the current caret position.",
    handler=insert_text_handler,
    default_key=None,
    when="editorFocus",
    scriptable=True,
    mutates_document=True,
    undo_group="typing",
    requires_consent=False,
    profile_feature="developer.console",
)
```

Required metadata fields for scriptable commands:

* `id`
* `title`
* `description`
* `scriptable`
* `mutates_document`
* `undo_group`
* `requires_consent`
* `profile_feature`
* `privacy_label`
* `network_label`
* `return_schema`
* `argument_schema`

The console refuses to run commands marked `scriptable=False` unless developer unsafe mode is enabled.

## 12. Macro integration

The console is the fastest path to creating and testing macros.

Requirements:

* Users can save selected console history as a macro.
* Macros are stored as command sequences by default, not arbitrary Python code.
* Python macros are developer-profile-only.
* TypeScript macros are developer-profile-only.
* Command-sequence macros are allowed in more profiles.
* Macro execution shows a preview when it will modify the document.
* Macro execution is one undo group unless the macro author explicitly splits undo groups.
* Macro failures stop execution and announce the failed step.

Example command-sequence macro:

```json
{
  "name": "Clean OCR text",
  "steps": [
    {"command": "quill.text.normalizeUnicode"},
    {"command": "quill.text.dehyphenateLines"},
    {"command": "quill.text.reflowParagraphs"}
  ]
}
```

## 13. Security and safety

### 13.1 Local trust model

The Python console is trusted local code execution.

QUILL must clearly warn users:

```text
The Developer Console can run code inside QUILL.
Only run commands you understand or received from a trusted source.
```

This warning appears:

* The first time the console opens.
* When enabling the feature from Settings.
* When pasting multi-line code from the clipboard.
* When attempting to enable unsafe developer mode.

### 13.2 Remote execution

Remote execution is locked off by default.

Requirements:

* No listening socket in stable builds.
* No hidden remote console.
* No command-line flag that silently enables remote execution.
* Experimental remote console, if ever added, must bind to localhost only by default.
* Remote console must require an explicit one-time token.
* Remote console must show a persistent status bar warning.
* Remote console must auto-disable on restart unless the user explicitly chooses otherwise.

### 13.3 Dangerous operations

The console must prompt or block for:

* Running shell commands
* Reading arbitrary files outside allowed locations
* Writing arbitrary files outside QUILL-controlled flows
* Sending document content to network services
* Installing Quillins
* Changing profile safety rules
* Disabling backups or crash recovery
* Accessing protected source documents
* Running pasted multi-line code

### 13.4 TypeScript worker limits

Default limits:

| Limit                  | Default                     |
| ---------------------- | --------------------------- |
| Execution timeout      | 30 seconds                  |
| Idle timeout           | 10 minutes                  |
| Memory warning         | 256 MB                      |
| Memory hard limit      | 512 MB                      |
| Output flood threshold | 100 KB                      |
| Max transcript size    | 5 MB before rotation prompt |

Long-running TypeScript scripts must support cancellation.

## 14. Accessibility requirements

The console must pass QUILL’s normal accessibility gates.

Required tests:

* NVDA reads console controls correctly.
* JAWS reads console controls correctly.
* Narrator reads console controls correctly.
* F6 cycles through console regions.
* Escape behavior is predictable.
* New output does not steal focus.
* Long output is summarized.
* Errors are reviewable character-by-character.
* Braille display review works through the transcript control.
* High contrast mode remains readable.
* Large font mode does not clip prompts or buttons.
* Keyboard-only users can run, copy, save, clear, and close.
* No console action traps focus.

## 15. Error handling

Errors appear in three layers:

1. Plain-language summary
2. Actionable suggestion
3. Technical details, expandable or copyable

Example:

```text
Error: Unknown command "quill.markdown.fixHeading".
Suggestion: Run q.commands.search("heading") to find matching commands.
Details: CommandNotFoundError: quill.markdown.fixHeading
```

Python tracebacks are available but collapsed behind “Show technical details” unless the active profile is Developer and Power Text.

TypeScript stack traces are captured and mapped to the user’s submitted code when possible.

## 16. Logging and transcripts

The console keeps a local transcript of:

* Commands entered
* Results
* Errors
* Warnings
* Announcements triggered by console commands
* Worker lifecycle events
* Macro recording markers

Privacy requirements:

* Transcripts are not sent anywhere automatically.
* Document text is included only when commands print or return it.
* “Copy diagnostic summary” redacts document content by default.
* Users can save transcripts manually.
* Support packages ask before including transcript content.

## 17. Settings

Settings page: `Settings > Developer Console and Automation`

Settings:

* Enable Developer Console
* Enable Python Console
* Enable TypeScript Console
* Show first-run safety warning again
* Require confirmation before pasted multi-line execution
* Require confirmation before document-wide mutation
* Allow script access to raw wx objects
* Allow shell commands
* Allow filesystem access
* TypeScript worker path
* TypeScript worker timeout
* Transcript retention
* History retention
* Clear history on exit
* Enable completions
* Enable result announcements
* Output verbosity: concise, normal, verbose
* Unsafe developer mode

Dangerous settings are available only in Developer and Power Text or Full Quill profiles.

## 18. Data storage

Suggested files:

```text
%APPDATA%\Quill\console\
  history.jsonl
  snippets.json
  transcripts\
  types\
    quill-console.d.ts
  ts-worker\
    worker.js
```

Portable mode stores the same structure next to the portable QUILL configuration directory.

History entries contain:

```json
{
  "timestamp": "2026-06-10T00:00:00Z",
  "language": "python",
  "input": "q.document_stats()",
  "success": true
}
```

History must not store command output by default.

## 19. Technical architecture

### 19.1 New modules

```text
quill/
  core/
    scripting.py              Official QuillScriptAPI facade
    script_context.py         Active console context snapshots
    script_permissions.py     Console permission checks
    script_results.py         Structured result and error models
  devtools/
    console_window.py         wx console UI
    python_console.py         Embedded Python console
    ts_console.py             Python-side TypeScript bridge
    ts_worker_protocol.py     JSON-RPC message schema
    completions.py            Completion provider
    history.py                Console history manager
    snippets.py               Snippet manager
    transcripts.py            Transcript manager
  tools/
    ts_worker/
      worker.ts               TypeScript worker source
      worker.js               Built worker
      quill-console.d.ts      Type definitions
```

### 19.2 Threading model

Rules:

* UI mutations must run on the wx main thread.
* Console input handling may occur in the UI thread only for quick commands.
* Long commands must run as background tasks.
* TypeScript worker communication runs asynchronously.
* Results are marshaled back to the UI through QUILL’s event queue or `wx.CallAfter`.
* Command cancellation must be supported for long-running tasks.

### 19.3 Command execution flow

```text
User enters command
    ↓
Console parser receives input
    ↓
Python console or TypeScript worker executes code
    ↓
Code calls q / quill API
    ↓
API validates permission, profile, and command metadata
    ↓
Command registry executes command
    ↓
Document/editor/status/a11y systems update
    ↓
Structured result returns to console
    ↓
Transcript updates and concise result is announced
```

## 20. Completion and help

The console should provide discoverability without requiring users to memorize APIs.

Completion sources:

* `q` methods
* command ids
* active document properties
* macro names
* snippet names
* settings keys
* feature ids

Help commands:

```python
q.help()
q.help("insert_text")
q.commands.search("bookmark")
q.describe_command("quill.editor.gotoLine")
q.examples("markdown")
```

TypeScript equivalents:

```ts
await quill.help();
await quill.commands.search("bookmark");
await quill.describeCommand("quill.editor.gotoLine");
```

## 21. Testing strategy

### 21.1 Unit tests

* `QuillScriptAPI.insert_text` routes through command registry.
* `replace_selection` creates one undoable operation.
* `goto_line` rejects invalid line numbers with plain-language errors.
* `run_command` refuses non-scriptable commands.
* Profile gates hide or reject console commands properly.
* Permission checks block dangerous operations.
* Snapshot refresh updates document, selection, and caret state.
* TypeScript protocol serializes and deserializes results correctly.
* Worker crash returns a structured error.

### 21.2 Integration tests

* Open Python console, run `q.insert_text`, verify document changes.
* Run document-wide command, verify undo restores prior state.
* Run command that announces result, verify announcement transcript.
* Open TypeScript console, run `await quill.insertText(...)`.
* Restart TypeScript worker and verify QUILL stays alive.
* Save console history as macro and run macro.
* Copy diagnostic summary and verify redaction.
* Paste multi-line code and verify confirmation prompt.

### 21.3 Accessibility tests

* NVDA reads transcript and input controls.
* JAWS reads transcript and input controls.
* Narrator reads transcript and input controls.
* F6 region cycling works.
* Escape returns focus predictably.
* High contrast and large fonts work.
* Long output does not cause speech flood.
* Error details are reachable and copyable.

### 21.4 Security tests

* Remote execution is not listening in stable builds.
* TypeScript worker cannot directly access unrestricted shell by default.
* Console cannot bypass network consent.
* Console cannot silently overwrite protected source documents.
* Pasted multi-line execution triggers confirmation.
* Unsafe developer mode cannot be enabled by imported profile alone.

## 22. Success criteria

The feature is successful when:

1. A developer can open the Python console and inspect/manipulate the active document through `q`.
2. A TypeScript user can run async editor commands through `quill`.
3. All document mutations are undoable.
4. Screen-reader users can operate the console without custom scripts.
5. Console commands respect profile, permission, and consent rules.
6. Long or failed commands do not crash QUILL.
7. TypeScript worker crashes do not crash QUILL.
8. Support diagnostics can be copied without leaking document content by default.
9. Macro creation can reuse console command history.
10. CI covers unit, integration, accessibility, and safety behavior.

## 23. MVP scope

### MVP: Python Developer Console

Included:

* Python console window
* `q` scripting API
* Command registry execution
* Transcript output
* History
* Clear/copy/save transcript
* Basic completions
* Plain-language errors
* First-run safety warning
* Profile gating
* Undo-aware document mutations
* Accessibility tests with NVDA

Not included in MVP:

* TypeScript console
* Macro recording from history
* Advanced snippets
* Remote execution
* Raw wx unsafe mode
* Plugin authoring APIs

### MVP+1: TypeScript Console

Included:

* Node worker bridge
* TypeScript transpilation
* `quill` async proxy
* Type definitions
* Worker restart
* Worker timeout and memory limits
* Console output capture
* TypeScript examples

### MVP+2: Macro and Quillin authoring

Included:

* Save console history as macro
* Snippet manager
* Quillin test harness
* Command-sequence macro editor
* Console-based plugin diagnostics

## 24. Open questions

1. Should Python console be included in QUILL 1.0 as hidden experimental functionality?
2. Should the console be modal, non-modal, or dockable?
3. Should command history persist by default or require opt-in?
4. Should TypeScript support be bundled or require Node detection?
5. Should a minimal embedded JS engine be considered later for users who do not have Node?
6. Should console snippets sync with macros, or remain separate?
7. Should support technicians have a restricted “diagnostics-only console” mode?
8. Should unsafe developer mode require a launch flag in addition to a setting?
9. Should QUILL ship sample scripts for OCR cleanup, Markdown repair, and diagnostics?
10. Should console transcript export support Markdown, plain text, and JSON?

## 25. Example first-run warning

```text
Developer Console

This console can run commands inside QUILL and may change the current document.
Only run commands you understand or received from a trusted source.

Recommended:
- Use q.run_command(...) or documented q methods.
- Do not paste code from unknown sources.
- Save your document before running document-wide commands.

[Open Console] [Cancel] [Learn More]
```

## 26. Example diagnostic summary command

Python:

```python
q.support.diagnostic_summary()
```

Output:

```text
QUILL diagnostic summary
Version: 1.1.0-dev
Profile: Developer and Power Text
Active document: chapter-7.md
Modified: yes
Documents open: 3
Screen reader detected: NVDA
Announcement backend: auto
Python console: enabled
TypeScript console: available
Last command: quill.editor.gotoLine
Last error: none
Document content included: no
```

## 27. Definition of done

This feature is done when:

* The Python console is fully keyboard accessible.
* The Python console exposes the official `q` scripting API.
* TypeScript console runs through a subprocess bridge and cannot crash QUILL.
* All editor mutations go through the command registry or scripting API.
* Undo/redo, dirty-state, status bar, and accessibility announcements remain correct after console-driven changes.
* Profile gating and safety settings work.
* First-run safety warnings are present.
* Console history, transcript copy, and transcript save work.
* Dangerous actions require confirmation or are blocked.
* Automated tests cover command execution, accessibility, worker failure, permissions, and undo behavior.
* User documentation explains examples, risks, and safe patterns.


---

# Appendix: Skills tutorial

_Folded in from the former docs/userguide.md on 2026-06-13._

# Writing Skills for QUILL — A Tutorial

This guide teaches you to write, validate, and share `.sqp` (Skill Quill Pack) files.
A skill is a multi-step AI workflow written in plain Markdown. If you can write a
prompt, you can write a skill.

---

## 1. What is a skill?

A QUILL prompt is one instruction. A skill is a conversation — a series of instructions
where each step can see what the previous step produced.

You might use a skill when:

- You want to analyse your text first, then act on the analysis.
- You want to gather information in one step and draft with it in the next.
- You want to check a condition (is this a question or a statement?) and take a
  different path depending on the answer.
- You want to repeat the same sub-task at a higher quality by giving the model
  context it built in an earlier step.

---

## 2. Your first skill

Create a file called `my-first-skill.sqp` and open it in QUILL.

```markdown
---
schema: quill.skill/1
name: Explain Then Simplify
description: Explains the selected text in plain terms, then simplifies it further.
author: Your Name
version: 1.0.0
---

# Step 1: Explain

Explain the following text as if the reader has no prior knowledge. Use simple
vocabulary and short sentences. Aim for 50-80 words.

Text to explain:
{selection}

# Step 2: Simplify further

The explanation below is good, but we need it even simpler. Rewrite it so a
twelve-year-old would understand it immediately. Keep the core meaning.

Explanation to simplify:
{step1.output}

```output
format: text
label: Plain-language explanation
accept_into: clipboard
```
```

Save the file, then validate it:

```powershell
python -m quill.tools.sqp_validator my-first-skill.sqp
```

You should see:

```
my-first-skill.sqp: OK
```

---

## 3. Adding parameters

Parameters let users choose options before the skill runs. QUILL shows a small dialog
collecting the choices before step 1 begins.

Add a reading-level choice to the skill above:

```markdown
---
schema: quill.skill/1
name: Explain Then Simplify
description: Explains and simplifies selected text at a chosen reading level.
author: Your Name
version: 1.0.0
parameters:
  - name: level
    label: Target reading level
    type: choice
    choices: [Grade 4, Grade 6, Grade 8]
    default: Grade 6
---

# Step 1: Explain

Explain the following text so it is accessible at {parameters.level} reading level.
Use simple vocabulary and short sentences. Aim for 50-80 words.

Text to explain:
{selection}

# Step 2: Simplify further

Rewrite the explanation below to be even clearer. Target: {parameters.level}.
Keep the core meaning intact.

{step1.output}

```output
format: text
label: Plain-language explanation
accept_into: clipboard
```
```

Now the parameter `{parameters.level}` is available in both steps. The value
comes from the user's choice in the dialog.

**Parameter types.**

| Type | UI control | Example |
| --- | --- | --- |
| `text` | Single-line text field | A keyword or name |
| `multiline` | Multi-line text area | A block of context |
| `choice` | Drop-down list | Reading level, tone, language |
| `bool` | Checkbox | Include citations: yes/no |
| `number` | Numeric field | Word count target |

---

## 4. Using the input block

Long texts can clutter the prompt. The `input` block appends data after the
instruction text, keeping the step prose readable:

```markdown
# Step 1: Extract key claims

Read the following document and list the five most important claims it makes.
Number each claim. One sentence per claim.

```input
{document}
```
```

Without the `input` block you would write:

```markdown
# Step 1: Extract key claims

Read the following document and list the five most important claims it makes.
Number each claim. One sentence per claim.

Document:
{document}
```

Both are equivalent; the `input` block is just cleaner when the data is long.

---

## 5. Conditional branching

Use a `condition` block to route execution based on a step's output.

```markdown
# Step 1: Detect intent

Read the following text. Is it asking a question, or making a statement?
Answer with exactly one word: "question" or "statement".

```input
{selection}
```

```condition
if: "{step1.output}" contains "question"
then: step2
else: step3
```

# Step 2: Answer the question

Answer this question clearly and concisely:
{selection}

```output
format: text
label: Answer
accept_into: clipboard
```

# Step 3: Expand the statement

Expand the following statement into a full paragraph with supporting detail:
{selection}

```output
format: text
label: Expanded statement
accept_into: clipboard
```
```

**How it works.** After step 1 runs, QUILL checks the condition: if the output
contains "question", it jumps to step 2. Otherwise, it jumps to step 3. Whichever
step runs last is the one that produces the output.

**Supported operators.**

| Operator | Matches when |
| --- | --- |
| `contains` | Subject contains value (case-insensitive) |
| `equals` | Subject exactly matches value (case-insensitive) |
| `starts_with` | Subject starts with value |
| `ends_with` | Subject ends with value |
| `length_gt` | Subject length > number |
| `length_lt` | Subject length < number |
| `is_empty` | Subject is blank |

---

## 6. Controlling the output

The `output` block on the last step controls what happens to the result.

```markdown
```output
format: text
label: Rewritten paragraph
accept_into: selection
```
```

**`format`:** `text` (default), `list` (AI should return a bulleted or numbered
list), `json` (AI should return valid JSON).

**`accept_into`:** What happens when the user presses Accept in the result dialog.
- `selection` — replaces the current editor selection.
- `clipboard` — copies to clipboard.
- `none` — shows read-only (default).

The `label` appears in the result dialog header so the user knows what they are
reviewing.

---

## 7. A complete example — Accessible Rewrite

Here is the bundled "Accessible Rewrite" skill in full, with commentary.

```markdown
---
schema: quill.skill/1
name: Accessible Rewrite
description: Rewrites selected text for plain-language accessibility.
author: QUILL Project
version: 1.0.0
parameters:
  - name: reading_level
    label: Target reading level
    type: choice
    choices: [Grade 6, Grade 8, Grade 10, No target]
    default: Grade 8
---

# Step 1: Analyse accessibility issues

Review the following text for plain-language accessibility issues. List the
problems as a numbered list. Focus on: sentence length (over 25 words), passive
voice, unexplained jargon or acronyms, abstract nouns where concrete ones would
serve better, and complex nested clauses. Be concise — one clear problem per
line. If the text has no issues, say "No issues found."

```input
{selection}
```

# Step 2: Rewrite for accessibility

Rewrite the text below to fix the issues identified in Step 1. Requirements:
- Target reading level: {parameters.reading_level}
- Preserve all factual content
- Do not add new information

Original text:
{selection}

Issues to fix:
{step1.output}

```output
format: text
label: Rewritten text
accept_into: selection
```
```

**Step 1** analyses the text and produces a numbered list of issues.
**Step 2** uses `{step1.output}` (the issue list) as context alongside the
original text, so the model knows exactly what to fix. The output replaces the
selection when the user presses Accept.

---

## 8. Validating your skill

Always run the validator before sharing:

```powershell
python -m quill.tools.sqp_validator my-skill.sqp
```

For extra checks:

```powershell
python -m quill.tools.sqp_validator my-skill.sqp --strict
```

`--strict` also warns if `description` or `author` are missing.

**Common errors and how to fix them.**

| Error | Cause | Fix |
| --- | --- | --- |
| `schema must be 'quill.skill/1'` | Missing or wrong schema | Add `schema: quill.skill/1` to front matter |
| `front matter must include 'name'` | No `name:` field | Add `name: My Skill` |
| `must have at least one step` | No `# Heading` lines | Add at least one `# Step N:` heading |
| `{step3.output} references a step that hasn't run yet` | Forward reference | Steps can only reference outputs from earlier steps |
| `unknown parameter 'tone'` | Used `{parameters.tone}` but didn't declare it | Add `tone` to the `parameters` list in front matter |
| `output format 'xml' is invalid` | Bad `format:` value | Use `text`, `list`, or `json` |

---

## 9. Sharing skills

A `.sqp` file is a plain text file — share it the same way you share any document.

**Via the Skill Library.** When someone receives your `.sqp` file, they import it
through `AI > Skill Library > Import .sqp`.

**Via a Quillin.** If you maintain a Quillin, add your `.sqp` files to the Quillin
directory. QUILL discovers them automatically at Skill Library load time.

**As a standalone file.** A `.sqp` file is self-contained. The recipient can also
open it in QUILL's editor to read, understand, and customise every step.

---

## 10. Skill authoring tips

**Keep step instructions specific.** "List the five most important claims" is
better than "What are the claims?" The model follows precision.

**Name outputs explicitly.** Instead of "Summarise the following", write "Write a
one-sentence summary of the following text. Return only the summary sentence,
no preamble." This ensures `{step1.output}` contains exactly what you expect.

**Test with short text first.** Paste two or three sentences into the editor,
select them, and run the skill. Short inputs are faster and errors are easier to
trace.

**Use `input` blocks for long data.** If your selection might be a full document,
put `{document}` in an `input` block rather than inline in the prompt. The step
reads more cleanly.

**Put conditions after a clean-detection step.** If you are branching on whether
text is a question, a statement, a list, or something else, dedicate step 1 to
just that classification. Ask for a single-word answer. The more constrained the
output, the more reliably the condition evaluates.

**Use the output block's `accept_into` intentionally.** If the skill rewrites the
selection, use `accept_into: selection`. If it produces supplementary content
(meeting summary, outline), use `accept_into: clipboard` so the user can paste
where they choose. Use `none` for informational skills (grammar analysis,
readability score) where the result is read but not inserted.

---

## Reference card

**Front matter fields.**

| Field | Required | Default |
| --- | --- | --- |
| `schema: quill.skill/1` | yes | — |
| `name: ...` | yes | — |
| `description: ...` | recommended | `""` |
| `author: ...` | recommended | `""` |
| `version: ...` | no | `1.0.0` |
| `parameters: [...]` | no | `[]` |

**Variables.**

| Variable | Value |
| --- | --- |
| `{selection}` | Selected editor text (full document if nothing selected) |
| `{document}` | Full document text |
| `{title}` | Document title |
| `{clipboard}` | Clipboard text at skill-start time |
| `{stepN.output}` | Output from step N (must be a lower-numbered step) |
| `{parameters.name}` | Value of a declared parameter |

**Fenced block types.**

| Block | Where | Purpose |
| --- | --- | --- |
| `` `input` `` | Any step | Appends data to the prompt |
| `` `condition` `` | Any step | Branch to `then`/`else` step after this step runs |
| `` `output` `` | Last step | Controls format, label, accept_into |
| `` `use-prompt` `` | Any step | Delegates to a named Prompt Library prompt |

**Condition operators.** `contains`, `equals`, `starts_with`, `ends_with`,
`length_gt`, `length_lt`, `is_empty`.

**Output formats.** `text`, `list`, `json`.

**Output accept_into values.** `selection`, `clipboard`, `none`.


---

# Appendix: Feature notes (Copy Tray)

_Folded in from the former docs/userguide.md on 2026-06-13._

> **Historical note:** this appendix preserves the original nine-slot Copy
> Tray design document. Copy Tray now has **twelve** slots and the Open Copy
> Tray chord is `Ctrl+Shift+Grave, X`; see the "Copy Tray" section above for
> current behavior and bindings.

# QUILL feature documentation

_Consolidated from the former docs/features/ folder on 2026-06-13. Each section preserves the original document in full._


---

<!-- Source: docs/features/copy_tray.md -->

# Copy Tray

## Overview

Copy Tray gives you nine independently addressable clipboard slots. Each slot
holds a piece of text that you copy there explicitly. Slots survive application
restarts — their contents are written to disk automatically so nothing is lost
when you close and reopen QUILL.

Unlike the system clipboard, which is shared with every other application and
holds only the most recently copied item, Copy Tray slots are exclusive to
QUILL and hold their contents until you explicitly replace or clear them. This
makes Copy Tray well suited for accumulating related fragments across a long
editing session: quotes from multiple sources, code snippets, address blocks,
standard disclaimers, or any text you paste repeatedly.

## Keyboard Access

### Paste from a slot

Hold `Ctrl+Shift` and press a number key. That is all.

| Key | Action |
| --- | --- |
| `Ctrl+Shift+1` | Paste from slot 1 at cursor |
| `Ctrl+Shift+2` | Paste from slot 2 at cursor |
| `Ctrl+Shift+3` | Paste from slot 3 at cursor |
| `Ctrl+Shift+4` | Paste from slot 4 at cursor |
| `Ctrl+Shift+5` | Paste from slot 5 at cursor |
| `Ctrl+Shift+6` | Paste from slot 6 at cursor |
| `Ctrl+Shift+7` | Paste from slot 7 at cursor |
| `Ctrl+Shift+8` | Paste from slot 8 at cursor |
| `Ctrl+Shift+9` | Paste from slot 9 at cursor |

If a selection is active when you paste, the pasted text replaces it.
If the slot is empty, QUILL announces "Slot N is empty".

### Copy to a slot

Hold the QUILL key (`Ctrl+Shift+Grave`), release, then press `Shift+digit`.
The QUILL-key bare digits 1-6 are heading shortcuts; adding Shift is a distinct
binding with no conflict.

| Key | Action |
| --- | --- |
| `Ctrl+Shift+Grave, Shift+1` | Copy selection to slot 1 |
| `Ctrl+Shift+Grave, Shift+2` | Copy selection to slot 2 |
| `Ctrl+Shift+Grave, Shift+3` | Copy selection to slot 3 |
| `Ctrl+Shift+Grave, Shift+4` | Copy selection to slot 4 |
| `Ctrl+Shift+Grave, Shift+5` | Copy selection to slot 5 |
| `Ctrl+Shift+Grave, Shift+6` | Copy selection to slot 6 |
| `Ctrl+Shift+Grave, Shift+7` | Copy selection to slot 7 |
| `Ctrl+Shift+Grave, Shift+8` | Copy selection to slot 8 |
| `Ctrl+Shift+Grave, Shift+9` | Copy selection to slot 9 |

You must have text selected. QUILL announces the slot number and a text
preview: "Copied to slot 2".

### Management

| Key | Action |
| --- | --- |
| `Ctrl+Shift+Grave, X` | Open Copy Tray dialog |

All bindings are reassignable in `Tools > Customize & Support > Keymap Editor` or the Command
Palette.

## Using the Edit Menu

All commands are available in `Edit > Copy Tray`. The submenu contains:

- `Copy to Slot 1` through `Copy to Slot 9` — copy the current selection
- `Paste from Slot 1` through `Paste from Slot 9` — paste at the cursor
- `Open Copy Tray...` — open the management dialog
- `Clear All Tray Slots` — clear all slots after confirmation

## Using the System Tray Icon

Right-click the QUILL icon in the system notification area (bottom-right
taskbar area). The context menu includes a **Copy Tray** submenu that lists
every occupied slot with its label (if any) and a text preview. Clicking a slot
pastes its content into the currently active QUILL document. This lets you
paste from the tray without bringing the main window to the front.

## Using the Dialog

Open the dialog with `Ctrl+Shift+Grave, X`, `Edit > Copy Tray > Open Copy
Tray`, or the Command Palette (`edit.open_copy_tray`). The dialog shows all
nine slots in a list. Each row displays:

- The slot number
- An optional label
- A preview of the stored text (empty slots show `(empty)`)

Navigate the list with the arrow keys. The following buttons appear below the
list:

- **Paste** (Enter or double-click) — paste the selected slot's text at the
  cursor position and close the dialog. Disabled when the selected slot is
  empty.
- **Copy Selection Here** — copy the current editor selection into the selected
  slot and refresh the list. Disabled when no text is selected in the editor.
- **Set Label...** — open a text-entry prompt to name the selected slot. Labels
  appear in all slot listings and in screen-reader announcements.
- **Clear Slot** — empty the selected slot. Disabled when already empty.
- **Close** (Escape) — close the dialog without pasting.

## Labelling Slots

Slot labels are optional but recommended for any slot you use regularly. A
label makes the slot identifiable in the dialog and in every spoken
announcement. Labelling slot 1 "signature" means you will hear "Pasted from
slot 1 (signature)" instead of "Pasted from slot 1".

To set a label:

1. Open the Copy Tray dialog.
2. Select the slot you want to label.
3. Press `Set Label...`.
4. Type the label and press Enter.

Labels are persisted alongside slot text and survive restarts.

## Accessibility Notes

- Every Copy Tray operation announces its result through QUILL's screen-reader
  interface. Copy, paste, clear, and label operations all produce spoken
  feedback.
- The slot list in the dialog receives initial focus when the dialog opens.
- Slot labels, when set, are included in every announcement.
- Empty slots are clearly identified as `(empty)` in all contexts.
- The `Clear All Tray Slots` confirmation dialog defaults to No to prevent
  accidental data loss.
- The `Ctrl+Shift+N` paste scheme is designed for screen reader users: one
  familiar chord activates slot N instantly, no menu navigation required.

## Tips

- **Research accumulator.** Assign each tray slot to a document section. Copy
  a relevant excerpt to each slot as you read through a source, then paste
  them in order when drafting.
- **Code boilerplate.** Keep import blocks, standard headers, and closing
  patterns in labelled slots for one-chord insertion.
- **Cross-document paste.** Copy a phrase to a tray slot, switch documents,
  paste from the tray — the system clipboard is untouched.
- **Persistent library.** Slots survive restarts. Build a set of standard
  fragments you reach for daily.
- **System tray access.** Paste into any QUILL document directly from the
  notification-area icon without bringing the window to the front.


---

# Appendix: Copy Tray design notes

_Folded in from the former docs/copy_tray_notes.md on 2026-06-13._

> **Historical note:** this appendix describes Copy Tray as originally built
> with nine slots. Copy Tray now has **twelve** slots (`Ctrl+Shift+1..9, 0,
> -, =`); see the "Copy Tray" section above for current behavior and
> bindings.

# Copy Tray: What Was Built and How It Feels

## What Was Built

Copy Tray is a nine-slot persistent clipboard integrated across QUILL's menu
bar, keyboard layer, dialog system, and system tray icon. Every slot holds text
that survives application restarts.

### Core model (`quill/core/copy_tray.py`)

A pure Python model with no wx dependency. `CopyTray` owns nine `TraySlot`
instances. Each slot has `text`, `label`, and `copied_at`. The model reads and
writes `copy_tray.json` in the QUILL data directory using `write_json_atomic`
(temp file + `os.replace`). A corrupt file causes a silent fresh start; it
never raises to the UI.

### UI mixin (`quill/ui/main_frame_copy_tray.py`)

`CopyTrayMixin` is mixed into `MainFrame`. Methods:

- `copy_to_tray_slot(n)` — copies the editor selection to slot n; announces
  slot number and text preview.
- `paste_from_tray_slot(n)` — inserts slot n text at cursor (or replaces
  selection); announces slot number and label.
- `open_copy_tray()` — opens the management dialog; pastes if the user chooses
  Paste and returns to the editor.
- `clear_all_tray_slots()` — Yes/No confirmation (default No); clears all nine
  slots on Yes.

### Dialog (`quill/ui/copy_tray_dialog.py`)

A resizable wx.Dialog with a ListBox and five action buttons. Each list row
shows slot number, optional label, and a 60-character preview. The list
receives focus on open. Buttons: Paste (Enter), Copy Selection Here, Set
Label..., Clear Slot, Close (Escape). Double-click pastes. Button states
update on every selection change: Paste and Clear Slot are disabled on empty
slots; Copy Selection Here is disabled when no editor text is selected.

### Keyboard bindings (`quill/core/keymap.py`)

| Key | Action |
| --- | --- |
| `Ctrl+Shift+1` through `Ctrl+Shift+9` | Paste from slot 1-9 |
| `Ctrl+Shift+Grave, Shift+1` through `Ctrl+Shift+Grave, Shift+9` | Copy selection to slot 1-9 |
| `Ctrl+Shift+Grave, X` | Open Copy Tray dialog |

The paste bindings use the number row with `Ctrl+Shift`. These keys were
confirmed free across the entire QUILL keymap. QUILL-key bare digits 1-6 are
heading shortcuts; adding Shift produces a distinct chord with no conflict.

All 20 commands (`edit.open_copy_tray`, `edit.clear_all_tray_slots`,
`edit.copy_to_tray_1..9`, `edit.paste_from_tray_1..9`) are registered in
the keymap and appear in the Command Palette. All are reassignable in the
Keymap Editor.

### Menu integration (`quill/ui/main_frame_menu.py`)

`Edit > Copy Tray` submenu with:
- Copy to Slot 1-9
- Paste from Slot 1-9
- Open Copy Tray...
- Clear All Tray Slots

The 18 per-slot items use dedicated `wx.NewIdRef()` IDs (`_id_copy_tray_slots`
and `_id_paste_tray_slots` arrays). Management commands are recirculated from
the power tools manifest via `_append_power_tools_copy_tray_items`.

### Power tools manifest (`quill/ui/main_frame_power_tools_menu.py`)

New `"copy_tray"` group with `edit.open_copy_tray` and
`edit.clear_all_tray_slots`. New recirculation helper
`_append_power_tools_copy_tray_items`. The 18 individual slot commands are also
registered in the manifest for Command Palette discoverability.

### System tray integration (`quill/ui/main_frame.py`)

The `_on_tray_right_click` method now builds a **Copy Tray** submenu listing
every occupied slot with its label (if any) and a 50-character text preview.
Clicking a slot calls `_tray_paste_slot(n)`, which restores the main window if
it is hidden, then pastes the slot content. If all slots are empty, the submenu
shows "(all slots empty)" as a disabled item. "Open Copy Tray..." is always
present at the bottom of the submenu.

### Documentation

- `docs/userguide.md` — complete feature reference with keyboard
  tables, dialog walkthrough, accessibility notes, and workflow tips.
- `docs/QUILL-PRD.md` — section 5.77 added with motivation, operations table,
  keyboard defaults, storage spec, accessibility guarantees, and implementation
  map.
- `docs/userguide.md` — "Copy Tray" section added in Writing and Editing,
  before "Copy With Source", with full keyboard tables and a tips block.

---

## The User Experience

### First encounter

You open QUILL to write a long document while researching from several other
sources. You read a quote you want to use, select it, and press
`Ctrl+Shift+Grave, Shift+1`. QUILL says "Copied to slot 1". You read another
fragment. `Ctrl+Shift+Grave, Shift+2`. "Copied to slot 2". A third. Slot 3.

You switch to your draft. Where you want the first quote, press `Ctrl+Shift+1`.
QUILL says "Pasted from slot 1" and the text is there. The system clipboard was
never disturbed. The other two quotes are still in their slots.

You close QUILL. Come back tomorrow. Slots 1, 2, and 3 still hold their
contents.

### Using labels

After a few days you decide to give slot 1 a permanent home: your email
signature. You open `Ctrl+Shift+Grave, X`, navigate to slot 1, press Set
Label..., type "signature", press Enter. Now when you paste, QUILL says "Pasted
from slot 1 (signature)". The slot is identifiable without looking at a screen.

### From the system tray

QUILL is minimized to the system tray while you read in another browser. You
right-click the QUILL icon. The menu shows:

```
Show Quill
Copy Tray  >
  1.  signature — Hi, I wanted to follow up...
  2.  Hello world...
  3.  import sys, os, pathlib...
  ...
  Open Copy Tray...
Sticky Notes...
Exit Quill
```

You click slot 3. QUILL restores its window and pastes the import block at
your cursor. You minimize again.

### Screen reader workflow

Press `Ctrl+Shift+5`. QUILL says "Slot 5 is empty." You know immediately
without opening a dialog or reading the screen. Select some text, press
`Ctrl+Shift+Grave, Shift+5`. "Copied to slot 5." Move elsewhere. Press
`Ctrl+Shift+5`. "Pasted from slot 5." Everything happened through voice, at
typing speed, with standard modifier+number chords.

---

## Future Directions: Double-Tap and Beyond

The user asked whether pressing a key twice quickly could trigger an alternative
action. For Copy Tray, the natural double-tap behaviour would be:

- **Single `Ctrl+Shift+N`** — paste from slot N immediately.
- **Double `Ctrl+Shift+N`** (two presses within ~300ms) — peek: QUILL speaks
  what is in slot N *without pasting* ("Slot 3: Hello world..."). This lets
  a screen-reader user verify a slot's content before committing to paste.

Implementing double-tap detection requires a timer in the QUILL-key prefix
state machine, a 300ms debounce, and a clear screen-reader announcement
pattern. It is architecturally clean and would make the Copy Tray even more
efficient for screen-reader-only workflows. This is noted here as a planned
enhancement, not yet implemented.

Other places in QUILL where double-tap patterns could add value:

- **Double QUILL key** (two presses of `Ctrl+Shift+Grave`) = open Copy Tray
  dialog, similar to how Windows `Win+V` opens clipboard history.
- **Double `F3`** = repeat the last Find All and jump to the next cluster of
  matches.
- **Double `Ctrl+Z`** = undo back to the last explicit save point.
- **Double `Ctrl+G`** = return to the previous location (ping-pong navigation).
- **Double `Escape`** = collapse all side panels and return focus to the editor.

These should be evaluated selectively — double-tap timing is sensitive and can
interfere with rapid typists. The patterns with the clearest benefit and the
lowest collision risk are: Copy Tray peek and QUILL-key-double-press for the
tray dialog.

---

## Acknowledgments

QUILL's accessibility design draws on the work of earlier screen-reader-first
editors. In particular, the keyboard-first compare workflow and the F8 anchor
selection model were inspired by the approaches pioneered in EdSharp and Boxer.
We are grateful to those projects and their authors for showing what
accessible, keyboard-driven editing can be.

---

## Glossary of QUILL Terms

This glossary defines the jargon used throughout the QUILL interface, menus, and documentation. Terms appear roughly in order of how often you will encounter them as a new user.

**Abbreviation**
A short trigger word or phrase that QUILL automatically expands into longer text as you type. For example, typing `brb` could expand to "be right back". Abbreviations are managed in the Abbreviation Manager (`Ctrl+Shift+Grave, Shift+A`). Unlike snippets, abbreviations expand automatically without a separate insertion step and do not support interactive placeholders.

**Agent / Agent Center**
An AI-assisted workflow that generates a multi-step task plan based on a goal you describe. The Agent Center shows you each step before it runs so you can review and approve. Agents build on the Writing Assistant and Prompt Studio infrastructure and require an AI provider to be configured.

**Browse Mode / Quick Nav Mode**
A temporary navigation state that makes the QUILL key prefix commands available one at a time. Press the QUILL key (shown as `Ctrl+Shift+Grave` in the keymap grammar, displayed as `QUILL Key` everywhere else) once to arm Quick Nav for the next key you press. Press it twice to lock Browse Mode on until you press Escape. In Browse Mode, letter keys and arrow keys invoke navigation commands rather than inserting characters, similar to the virtual cursor mode in screen readers.

**Command Palette**
A searchable pop-up listing every registered QUILL command with its current keyboard shortcut. Open with `Ctrl+Shift+P`. Type any part of a command name to filter the list, then press Enter to run it. The fastest way to reach any action without memorising menu paths or key bindings.

**Copy Tray**
A multi-slot clipboard within QUILL that holds up to twelve named text snippets at once. Unlike the Windows clipboard (which holds only one item), the Copy Tray lets you copy different pieces of text to individual numbered slots (`Ctrl+Shift+Grave, Shift+1` through `Shift+9`, `Shift+0`, `Shift+-`, `Shift+=`) and paste from any slot. Open the Copy Tray dialog with `Ctrl+Shift+Grave, X` or `Win+V`-style double QUILL-key press.

**Document Tab**
A single open file or generated artifact inside the QUILL editor area. QUILL is a tabbed editor; each file, compare summary, or AI output opens as its own document tab. Tabs are announced by name when you switch between them (`Ctrl+Tab`).

**Keymap / Keyboard Pack (.kqp)**
The mapping of keyboard shortcuts to QUILL commands. The keymap is fully editable in **Preferences → Keyboard**. You can export your keymap as a `.kqp` file (Keyboard Pack) to share it with others or import one provided by the community. Resetting the keymap restores factory defaults without affecting other preferences.

**Macro**
A recorded sequence of QUILL actions that you can replay on demand. Record a macro from **Tools → Macros → Start Recording**, perform the steps you want to automate, then stop recording. Play it back later to repeat the sequence exactly. Macros are ideal for repetitive cleanup tasks.

**Profile (Feature Profile)**
A named set of feature flags that controls which QUILL capabilities are visible and enabled. QUILL ships with profiles such as Writing, Developer, and Accessibility. Profiles hide features not relevant to a particular workflow, keeping menus and option dialogs focused. Switch profiles or edit them in **Preferences → Profiles and Features**.

**Prompt Studio**
A built-in tool for creating and saving reusable AI prompt templates with named input variables. A Prompt Studio template might be "Rewrite for Plain Language: ${input:text}" — you fill in the variable each time you run the prompt. Prompts are stored as `.pqp` files and can be imported and exported.

**Quillin (Extension)**
A plug-in for QUILL, also called an extension. Quillins run in a separate worker process (fault isolation — a crashed extension cannot take down the editor) but are not a security sandbox; enforcement relies on code review and the Author Covenant. Quillins can add new commands, menu items, custom AI prompts, or automation scripts. Each Quillin has a `manifest.json` that describes its capabilities. QUILL ships with several bundled Quillins (word count, AI writing prompts) and supports user-installed ones. The Quillin Manager is in **Preferences → Extensions**.

**Recovery / Session Recovery**
QUILL silently auto-saves your work at intervals. If QUILL closes unexpectedly (crash, power loss, accidental close), it detects the unsaved state on next launch and offers to restore the last known version. Recovery files are stored separately from your saved files so a corrupted recovery never overwrites your original. Manage recovery in **File → Recover Document**.

**Remote Site**
A connection configuration for a server QUILL can connect to directly to open and save files. Supported protocols are FTP, SFTP, HTTPS (WebDAV), and S3-compatible object storage. Sites are named and saved in **File → Remote Sites → Manage Remote Sites** so you do not have to re-enter credentials each time. Each site stores host, port, protocol, credentials (encrypted on Windows via DPAPI), and a default path.

**Safe Mode**
A startup mode that disables AI, Watch Folder, and Quillin extensions. Useful when a Quillin or AI provider is causing problems and you need a clean environment. Launch with `--safe-mode` on the command line or set `QUILL_SAFE_MODE=1` in the environment. In Safe Mode, a status bar indicator tells you which features are disabled.

**Session (AI Session)**
A persistent conversation thread between you and an AI provider inside QUILL. Sessions have a name, a provider, a model, and a message history. You can have multiple named sessions and switch between them. Sessions are stored locally and can be exported. The Writing Assistant always runs inside a session.

**Skill / Skill Library**
A named, reusable AI workflow defined as a series of steps (prompts, transforms, and conditions). Skills are more structured than single prompts: each step in the skill can feed its output into the next. The Skill Library (`AI → Skill Library`) lets you browse, run, and author skills. Skills are stored as `.json` files.

**Snippet**
A reusable block of text with optional interactive placeholders that you insert manually at the cursor position. Snippets support variables such as `${input:name}` (a prompted text field), `${choice:a|b}` (a pick-list), `${date}`, `${time}`, and `${cursor}` (where the cursor lands after insertion). Insert with `Ctrl+Shift+Grave, S`; manage with `Ctrl+Shift+Grave, Shift+S`. Compare with abbreviations, which expand automatically.

**Sound Pack**
A collection of audio files that QUILL uses for non-speech feedback: key sounds, navigation tones, alert chimes, and (optionally) indentation-level tones for coding. Sound Packs are loaded from a named directory and can be swapped in Preferences. The default pack uses synthesised bell tones; custom packs can use any WAV files following the naming convention.

**Template**
A pre-written document structure that you can use as a starting point for new files. Templates are plain text or Markdown files stored in a designated folder. Opening a template creates a new untitled document pre-filled with the template content. Manage templates in **File → New from Template**.

**Watch Folder**
A directory that QUILL monitors in the background. Any supported file dropped into the watch folder is automatically opened as a new document tab (or processed according to per-folder rules). Useful for transcription pipelines, dictation outputs, and batch review workflows. Configure in **Tools → Watch Folder**.

**WebView / Side Preview**
The rendered HTML preview pane that appears alongside the editor when you press `F6` (or enable it via **View → Side Preview**). The preview is powered by Microsoft Edge WebView2 and renders Markdown, HTML, and plain text in real time as you type. The preview is read-only and does not affect the document.

**Welcome Guide**
A lightweight, profile-aware getting-started document that opens inside QUILL as a document tab. Unlike the full User Guide (which opens in your browser), the Welcome Guide adapts its content to show only the features enabled in your current profile. Open it from **Help → Open Welcome Guide**.

**Writing Assistant**
QUILL's AI writing panel. The Writing Assistant accepts a goal described in plain language and ranks relevant QUILL commands, offers preset rewrite/summarize/continue/grammar flows, and can execute a restricted Python transform (import allowlist and resource limits, not a security boundary) against the current document. It runs inside an AI Session and requires an AI provider to be configured in Preferences.

**QUILL Key**
The keyboard shortcut `Ctrl+Shift+Grave` (the backtick/grave key above Tab). Pressing it once arms a one-shot prefix; pressing it twice locks Quick Nav Mode on. The QUILL key is the entry point to most of QUILL's power features. Every chord is announced when pressed and is remappable in **Preferences → Keyboard**. The chord is shown to the user as `QUILL Key + <key>` everywhere in the editor (menus, Keyboard Reference, status bar, cheat sheet). The stored binding is `Ctrl+Shift+Grave, <key>` in `DEFAULT_KEYMAP` / `keymap.json` / the Keymap Editor; only the display layer rewrites the prefix, through `quill.core.keymap_format.format_binding_for_display`. The constant `QUILL_KEY_LABEL` in `quill/branding.py` is the single source of truth for the brand, so a future rebrand touches one file.
