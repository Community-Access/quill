# BRF Tools

**Bundled QUILL Quillin** — `com.quill.brftools`

User-configurable preferences for braille translation, page handling, and status bar display. Requires the QUILL Braille Pack. This is also the reference implementation of a multi-tab declarative-only Quillin preferences page — no handler code, no capabilities beyond settings access.

## What it does

BRF Tools contributes a four-tab preferences page. Open it from **Preferences** (Ctrl+Comma), navigate to **BRF Tools**, and press Enter:

- **Translation** — default translation profile (UEB Grade 2, UEB Grade 1, Standard American Legacy) and back-translation result label behavior.
- **Page Handling** — cells per line, lines per page, line-length warnings, and line-ending normalization for embossers that require CRLF.
- **Status Bar** — which fields appear in the braille status cell (page, line, cell, print page) and status verbosity (Brief, Normal, Detailed).
- **Advanced** — translation command logging and timeout settings for diagnosing liblouis table problems.

## What it requires

The QUILL Braille Pack (liblouis 3.38.0, optional installer component). BRF Tools loads regardless, but its settings only affect behavior when the Braille Pack is present and a BRF document is open.

## Capabilities

- `settings.own.read` — reads its own settings to configure braille behavior
- `settings.own.write` — writes its own settings when the user changes a preference

No handler code. No `editor.read` or `editor.write`. No network access.

## License

MIT. Copyright (c) Blind Information Technology Solutions (BITS) and Community Access.
