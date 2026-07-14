# QUILL 0.7.0 Beta 1 — Meet You Where You Are

QUILL 0.7.0 is a community release. Yes, it is a major step forward for screen-reader-first writing, editing, AI-assisted authorship, automation, braille, code review, and extension-powered workflows. The bigger story is **who is helping QUILL become what it is becoming**.

Kelly Ford, Taylor Arndt, Shane Popplestone, Michael Babcock, and many others have helped lift this project. Some are testing. Some are contributing code. Some are filing issues, describing real-world workflows, stress-testing accessibility, and improving design direction. All of that matters.

> "I started QUILL, but the community is lifting it to levels I could never reach alone. This release is about meeting people where they are, then giving them a path to grow." — Jeff Bishop

## What is in this release

- **Meet People Where They Are** — a complete reimagining of first-run setup. A redesigned startup wizard asks what kind of writing you do and shows a plain-English, screen-reader-readable preview of exactly what you will get. Seven intent profiles replace the old nine technical ones in the wizard. Menus, the Command Palette, and the Go to Anything dialog all reflect your chosen profile instantly — commands for features you have not enabled simply do not appear. Pressing Cancel on first run starts you in the simplest possible editor rather than leaving you with raw defaults.
- **Insert Automation** turns typed abbreviations, smart triggers, `.LOG` files, document directives, and append anchors into one safe automation system.
- **The Quillin Extension Platform** now supports settings pages, searchable preferences, tabs, document events, lifecycle events, status-bar cells, dependencies, network allowlists, command descriptions, developer logging, announcement priority, scaffolding tools, and stronger validation.
- **AI Writing Toolkit** ships a complete, keyboard-first AI writing layer: grammar check, AI Thesaurus (Ctrl+Alt+Shift+H), rewrite, summarize, expand, generate table of contents, Document Q&A, translation, and AI read-aloud. Every feature supports six providers — Anthropic Claude, OpenAI, Google Gemini, OpenRouter, Ollama, and custom endpoints. Custom per-task instructions let you shape how the AI behaves for each task. Prompt caching keeps costs down automatically: Claude marks system prompts as cacheable, OpenAI caches prefixes over 1024 tokens, and local Ollama models cache in-process. No mouse required for any of it.
- **Braille Mode** opens and edits braille text files while preserving bytes, form feeds, line endings, and layout. It adds braille-aware status, page navigation, page tools, and optional liblouis-powered translation through the QUILL Braille Pack.
- **Compare Mode** is now a first-class keyboard-driven workflow with difference navigation, speech announcements, and optional sound cues.
- **Code-aware editing** adds language profiles, token movement, manual language selection, and optional indentation tones.
- **Text encoding tools** help you find non-ASCII characters, jump to them, convert them to HTML entities, and save copies in narrower encodings without silent data loss.
- **Word and RTF export** lets you save documents as `.docx` or rich text through Pandoc, preserving real Word heading structure when the source contains structure.
- **Pandoc Import / Export and Batch Conversion (issue #262)** extends that foundation with a curated Tier-1 format list (Markdown, CommonMark, GFM, HTML, DOCX, ODT, RTF, plain text, CSV/TSV, EPUB, LaTeX, plus PDF export), a four-page batch wizard, and live progress in the Status Page.
- **Citation insertion** formats MLA 9, Chicago 17, and APA 7 citations from a simple labelled form.
- **The Snippet Gallery** (Insert > Snippet Gallery... or QUILL key, Shift+G) collects parameterized templates from all enabled Quillins into one browseable picker. Smart Insert ships three built-in entries.
- **The Vision Prompt Library**, contributed by Kelly Ford, gives Describe Image with AI twelve evaluated prompt styles and a full management dialog.
- **Math Equations**, contributed by Robert Danaraj, adds Insert > Insert Equation... (Ctrl+Shift+E) for LaTeX and MathML insertion, with Browser Preview and HTML export rendering via MathJax 3. Delivered as a sandboxed Quillin rather than a core patch.
- **The Dynamic Keyboard Reference** now reflects the active command registry, your current bindings, and QUILL key layers.
- **Sound notifications** and **indentation tones** add optional non-speech feedback without making existing setups noisier.
- **Major accessibility and startup fixes** make bug reporting, JAWS focus, image description, first run, the user guide, update notifications, and macOS setup more reliable.

## EdSharp port

A foundational piece of QUILL for All is the **EdSharp port** — a screen-reader-safe rendering of Ed Sharp's classic keyboard-driven editing layer. EdSharp users will recognize heading shortcuts (`Ctrl+1` through `Ctrl+6`), section-move (`Alt+Shift+Up` / `Alt+Shift+Down`), list toggle (`Ctrl+Shift+L`), and the new **Section status cell** that announces the current heading depth and lets you jump by section number from the status bar. The port is wired into the existing QUILL command system, so every shortcut is rebindable through the Keyboard Manager.

## QUILL Key branding and menu label clarity

The QUILL Key is the editor's signature feature — a `Ctrl+Shift+\`` prefix that opens the chord language for power-user workflows. In 0.7.0 Beta 1 the user-visible chord now reads `QUILL Key + <key>` everywhere it appears: every menu, the About > Keyboard Reference, the cheat sheet, and the status bar. The stored binding (`Ctrl+Shift+Grave`) is unchanged; only the display label moves. A new CI audit gate (`menu_lint`) flags any menu or context-menu item that has a binding but no visible label (or vice versa), so blank menu slots cannot slip through.

## Day-to-day fixes

- Bug report dialog now accepts typing immediately (#244).
- JAWS focus after launch no longer falls silent (#259).
- Describe Image with AI works again (#265).
- First-run wizard is reachable on every install path (#266).
- The user guide opens safely without locked-down plugins.
- Update notifications are more reliable.
- macOS builds install and store keys correctly.

## Installation

This release ships three artifacts:

- **`Quill-for-All-Setup-0.7.0 Beta 1.exe`** — the Windows installer for QUILL for All. Run it as Administrator.
- **`Quill-Portable-v0.7.0-beta.1.zip`** — the Windows portable bundle with embedded Python and all bundled tools (Pandoc, DECtalk, eSpeak-NG, Piper, Kokoro). Extract and run `run-quill.cmd`.
- **`Quill-macOS-0.7.0-beta.1.dmg`** — the macOS disk image for macOS 12 or later (Apple Silicon and Intel). Open the DMG and drag QUILL to Applications.

The portable zip is for users who cannot or prefer not to install on Windows.

## Running from source

If you prefer to run from source, see the [Running QUILL 0.7.0 from source](https://github.com/Community-Access/quill/blob/main/docs/release%20notes/release0.7.0.md#running-quill-070-from-source) section of the full release notes.

## Upgrading from 0.5.0

If you are upgrading from QUILL 0.5.0, read **What works differently now** in the full release notes. It lists the few places where menus, habits, or installer choices changed. The full notes are in this repository under [`docs/release notes/release0.7.0.md`](https://github.com/Community-Access/quill/blob/main/docs/release%20notes/release0.7.0.md) and cover every implementation detail, including the full Quillin platform specification, AI provider configuration, and per-feature keyboard shortcuts.

## Closing

> "We are building something free, cross-platform, assistive-technology friendly, and community-driven. Wait until you see what contributions are coming next." — Jeff Bishop

To everyone testing, contributing code, suggesting workflows, challenging the design, sharing feedback, building community, and cheering QUILL on: thank you. The product is better because of you.

— The QUILL team