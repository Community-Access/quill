# QUILL for All

[![Contributors](https://contrib.rocks/image?repo=Community-Access/quill)](https://github.com/Community-Access/quill/graphs/contributors)

**QUILL for All** is an open-source, accessibility-focused editor from
Community Access.

QUILL for All helps people write, edit, convert, compare, and publish
documents in a screen-reader-friendly environment.

**QUILL** stands for **Quality, Usable, Inclusive, Lightweight, Literate**.

**QUILL for All: A quality, usable, inclusive, lightweight, and literate editor built for everyone who writes, codes, learns, and creates.**

## The Quillin Hub

Expand your editor's powers with the [Quillin Hub](https://hub.quillforall.org). Discover a curated gallery of community-created extensions -- from research tools to accessibility auditors -- all verified for security and WCAG 2.2 AA compliance.

## What Quill is


Quill is a screen-reader-first writing and document environment for **Windows and macOS**, focused on practical keyboard workflows, stable editing, and accessible diagnostics/support flows.

Quill is designed to stay focused and useful:

- **Quality** -- dependable, polished, and serious enough for real work.
- **Usable** -- built around practical keyboard, screen reader, and low-friction editing needs.
- **Inclusive** -- designed from the beginning for blind users, screen reader users, keyboard users, and people with different skill levels.
- **Lightweight** -- fast, focused, not bloated, and friendly to people who just want to write or edit.
- **Literate** -- about words, code, Markdown, documents, learning, and thoughtful communication.

## Current release line

Current release line: **0.7.0**

Highlights since 0.5.0 include:

- Insert menu with searchable Markdown/HTML insertion.
- Word Prediction with `Ctrl+.` plus HTML/Markdown tag IntelliSense.
- New snippet system with `Ctrl+Shift+Grave, S` insertion, trigger expansion, and starter packs.
- Release-safety default: Word and CSV open in the normal plain-text editor surface.
- Structured Word view and CSV grid code paths remain in-repo behind an internal gate for continued verification.
- Expanded structured intake for `.doc`/`.docx`, `.ppt`/`.pptx`, `.xlsx`/`.xls`, `.pages`, and low-confidence PDF fallback via MarkItDown when available.
- Writing Assistant shell with prompt presets, generated tool suggestions, and a restricted Python runner (import allowlist, resource limits, confirmation required — not a security boundary; see the user guide).
- AI Connection workflow from both Preferences and the AI menu, with provider-aware host defaults.
- Verify Connection, List Models, and Recommend Model actions in AI Connection settings.
- AI menu status line with plain-language detail (`Ready` or `Needs attention`) and immediate accessible feedback.
- BITS Whisperer rollout surfaces for provider onboarding, readiness checks, status-page live updates, and guarded download queue controls.
- General Preferences controls for AI enable state, BW Safe Mode Lock, auto-open status behavior, and refresh cadence.
- Optional Ollama cloud key mode over HTTPS (no local Ollama required for cloud endpoint access).
- In-App Preview and Side-by-Side Preview with a dedicated Focus Preview command.
- Heading styling tools to apply font family, size, and alignment to current-level or all headings in Markdown/HTML.
- Heading Organizer (`Ctrl+Shift+Grave, O`) with keyboard-driven heading level changes, section reordering, and accessibility validation.
- QUILL Quick Nav mode (browse-style cursor navigation) activated with `Ctrl+Shift+Grave`, with mnemonic single-key movement for links, lists, list items, tables, block quotes, bookmarks, code blocks, table of contents, headings, heading levels (`1` through `6`), paragraphs, sentences, and blocks.
- Watch Folder automation under **Tools -> Dictation** to auto-open newly dropped supported files.
- Unified first-run **Personalise QUILL** wizard (re-runnable from **Help -> Personalise QUILL**) covering keyboard pack, feature profile, remote access, AI, reading/accessibility, writing tools, and startup behaviour.
- Search menu simplification with replace-all inside the Replace dialog.
- Unified diagnostics-backed support flow under **Help -> Report a Bug**.
- Menu IA refinement, including **Insert** before **View** and **Search** after **View**.
- Documentation refresh with regenerated Markdown/HTML/EPUB artifacts.

AI quick start:

1. Open `AI -> AI Connection...`.
2. Choose provider (`Ollama (local)`, `Ollama Cloud (API key)`, or `Custom HTTP`).
3. Enter host/model/key as needed.
4. Save settings; Quill auto-verifies and updates the AI status line.
5. Use **List Models** to choose a provider-returned model.

Ollama Cloud onboarding is available in this same flow. If you have an API key, Ollama Cloud offers a free personal-use tier with lower usage limits.

Snippet workflow quick start:

1. Press `Ctrl+Shift+Grave, S` to open **Insert Snippet**.
2. Type to filter by snippet name, trigger, or body text.
3. Use arrow keys to choose, press Enter to insert, and fill placeholders when prompted.

Related commands:

- `Ctrl+.`: Word Prediction (words, HTML tags, Markdown tags).
- `Ctrl+Shift+Grave, Shift+S`: Manage snippets (create, edit, delete, import/export, starter packs).
- `Preferences -> Install Starter Snippet Packs`: install sample packs for writing, developer flow, and accessibility/support notes.

Watch Folder quick start:

1. Open `Preferences -> Watch Folder Automation`.
2. Choose a folder where you will drop supported Quill files.
3. Enable watch folder monitoring.
4. Turn on auto-start if you want it running every launch.
5. Drop supported files into the folder; Quill opens them automatically.

QUILL Quick Nav quick start:

1. Press `Ctrl+Shift+Grave` to enter QUILL Quick Nav mode.
2. Press `H` for next heading, or `Shift+H` for previous heading.
3. Press `1` through `6` for next heading at that level, or `Shift+1` through `Shift+6` for previous heading at that level.
4. Press `A` for links, `L` for lists, `I` for list items, `T` for tables, `Q` for block quotes, `B` for bookmarks, and `'` for code blocks.
5. Press `C` to open table of contents, `P` for paragraphs, `S` for sentences, and `Tab` for blocks. Use `Shift` with any movement key to reverse direction.
6. Press `]` to jump to the first line after the current list or table. Press `[` to jump to the line above it.
7. In `Preferences -> General`, use **Preload QUILL browse cache in background**. It is on by default; if off, Quill builds the cache the first time you use Quick Nav.
8. Press `Esc` to leave QUILL Quick Nav mode.

How tracking works for Markdown and HTML:

- Quill builds a per-document navigation index in memory and reuses it while the text and markup type stay unchanged.
- Headings are indexed from parsed Markdown and HTML heading structures.
- List-item anchors are indexed from Markdown list syntax and from HTML `<li>` tags.
- Paragraph anchors are indexed by blank-line paragraph boundaries for text/Markdown and by block-level tags in HTML (`p`, `li`, `blockquote`, `pre`, `h1` to `h6`, `td`, `th`).
- Sentence anchors are indexed from sentence-ending punctuation boundaries.
- The index is invalidated on document edits, full-text replacements, and tab switches.
- Quick Nav movement is cursor-only and non-editing by design.

## Platforms and on-device AI

- **Cross-platform.** Quill runs on **Windows and macOS** from one codebase. The macOS build ships as a signed, notarized `.app`; screen-reader announcements route to **VoiceOver** on macOS and to NVDA/JAWS/Narrator (via Prism) on Windows.
- **Ask Quill chat.** An on-device AI chat (**AI -> Ask Quill Chat**) rendered as a fully accessible WebView document: each turn is a heading you can navigate, new replies are announced, the message box lives in-page, and Escape closes it. Verified in **NVDA, JAWS, and VoiceOver**.
- **On-device AI, no cloud required.** macOS uses **Apple Foundation Models** (Apple Intelligence); Windows/Linux use **llama.cpp** (CPU, GGUF). You can optionally connect **Ollama (local)**, **Ollama Cloud (API key)**, or a custom HTTP endpoint. The assistant defaults to answering in chat and never edits your document without approval.
- **Accessible WebView, preview, and dialogs** are built on the open-source [`wx-accessible-webview`](https://github.com/Community-Access/wx-accessible-webview) library (extracted from Quill), which also powers the live Markdown/HTML preview, the About dialog, and the update/consent dialogs.
- **Train Writing Style** (**AI -> Train Writing Style...**) conditions the assistant on your own writing.

## Project layout

- `quill/` -- application code.
  - `quill/core/` -- core logic and document operations.
  - `quill/ui/` -- wxPython interface and dialogs.
  - `quill/platform/windows/` -- Windows integration points.
  - `quill/platform/macos/` -- macOS integration (VoiceOver announcements, Keychain, high-contrast, screen-reader detection).
  - `quill/core/ai/` -- on-device assistant backends (Apple Foundation Models, llama.cpp) and the Ask Quill agent.
- `docs/` -- product docs and generated artifacts.
  - `QUILL-PRD.md` (+ `.html`, `.epub`)
  - `userguide.md` (+ `.html`, `.epub`)
  - `announcement.md` (+ `.html`, `.epub`) -- the 0.5.0 product announcement
  - `engineering.md`, `planning.md`, `accessibility.md`, `features.md`, `qa.md` -- consolidated reference docs (each `+ .html`, `.epub`)
- `tests/` -- unit/integration/accessibility/performance tests.
- `scripts/` -- release, validation, and maintenance helpers.

## Run Quill locally

Runs on **Windows and macOS** (Python 3.12).

1. Install Python 3.12.
2. Install dependencies:
   - `pip install -e ".[ui,dev]"`
   - On-device AI for Ask Quill: add `ai` on Windows/Linux (`pip install -e ".[ui,ai]"`, pulls llama.cpp). macOS uses Apple Foundation Models — no extra needed.
3. Launch:
   - `python -m quill`  (on Windows, `pythonw -m quill` for no console window)

To build a signed, notarized macOS app, see `scripts/build_macos.sh` and `docs/QUILL-PRD.md`.

Optional launch flags:

- `--safe-mode`
- `--reset-profile`
- `--version` (prints version and exits without launching UI)
- `--line N --column M` (place cursor for the first startup file)
- `--new-window` (force a new process instead of forwarding to existing instance)
- `--wait` (when forwarding to an existing instance, wait until it exits)
- `--diagnostics`
- `--dump-stacks`

Examples:

- `python -m quill --version`
- `python -m quill notes.md --line 120 --column 1`
- `python -m quill --new-window notes.md`

## Development checks

- Lint: `ruff check .`
- Tests: `pytest tests/unit/ tests/stability/ -q`

## Documentation workflow

Generate docs artifacts from `docs/*.md` with Pandoc:

- HTML: `pandoc docs\\<name>.md -f gfm -t html5 -s -o docs\\<name>.html`
- EPUB: `pandoc docs\\<name>.md -f gfm -t epub3 -o docs\\<name>.epub`

Artifact parity guard:

- `python scripts/check_docs_artifacts.py`

This fails when a `docs/*.md` source changed but matching `.html`/`.epub` files were not updated.
The installer ships the user-facing guides, while the GitHub Pages docs hub exposes the
PRD and engineering docs for anyone who wants the deeper implementation detail.

## One-command release readiness

Run the full release readiness flow:

- `python scripts/release_readiness.py`

This runs:

1. Lint (`ruff check .`)
2. Dependency audit (`pip-audit --strict`)
3. Tests (`pytest -q`)
4. Docs rebuild for `docs/*.md` (HTML + EPUB)
5. Docs artifact parity check
6. Release corpus verification

## CI and release automation

- CI workflow: `.github/workflows/accessibility-ci.yml`
- Security workflow: `.github/workflows/security-ci.yml`
- Windows release workflow: `.github/workflows/windows-release.yml`
- Docs site workflow: `.github/workflows/github-pages.yml` (publishes the docs hub and updates feed)

## Support and issue reporting

Use **Help -> Report a Bug** inside Quill. The flow supports diagnostics bundle generation, report preview, clipboard copy, and browser handoff to support submission.

## Contributing

Community contributions are welcome.

- Read **[CONTRIBUTING.md](CONTRIBUTING.md)** for setup, workflow, and PR expectations.
- Read **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** before participating.
- Read **[SECURITY.md](SECURITY.md)** for private vulnerability reporting.
- Read **[PRIVACY.md](PRIVACY.md)** for data handling and retention behavior.
- Read **[RESPONSIBLE_AI_USE.md](RESPONSIBLE_AI_USE.md)** for ethical and accountable AI use requirements.
- Read **[GOVERNANCE.md](GOVERNANCE.md)** for project decision model.
- Read **[MAINTAINERS.md](MAINTAINERS.md)** for maintainer responsibilities.
- Contributor graph: **[contrib.rocks / QUILL](https://contrib.rocks/image?repo=Community-Access/quill)**

## Community discussions

- Use GitHub Discussions for Q&A and feature ideation.
- Use GitHub Issues for confirmed bugs and scoped feature requests.

## Release governance

- Release process and branch policy: **[RELEASE.md](RELEASE.md)**
- Security advisory runbook: **[docs/QUILL-PRD.md](docs/QUILL-PRD.md)**

## License

MIT. See `LICENSE`.

## Legal and Trademark Notices

QUILL for All is an independent open-source project by Community Access.
It is not affiliated with, sponsored by, or endorsed by Quill.js,
QuillBot, Quill.org, or any other similarly named product, project,
company, or organisation.

All trademarks are the property of their respective owners.

See [TRADEMARKS.md](TRADEMARKS.md), [NOTICE](NOTICE), and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for more information.
