# Status Scribe

**Bundled QUILL Quillin** — `com.quill.statusscribe`

Adds a live word-count cell to the QUILL status bar. The cell updates after every save and whenever you switch tabs, so you always know your document size at a glance — without having to run a command or look at a menu.

## What it does

### Status bar cell

A "Words: N" cell appears in the status bar. The cell is refreshed:

- After every save (`document.after_save`)
- When you activate a new tab (`document.activated`)
- Immediately when you change the count mode in Preferences

### Count modes

Configure from **Preferences** (Ctrl+Comma) → **Status Scribe**:

- **Words** — total whitespace-delimited words (default)
- **Characters** — total character count including spaces
- **Sentences** — approximate sentence count based on `.`, `!`, `?` punctuation

### Optional voice announcement

Optionally speak the count aloud after every save, at a configurable screen reader priority (quiet / normal / urgent).

### Lifecycle logging

Status Scribe uses `api.log()` to write developer messages to the QUILL Developer Console. Open it via **Tools > Developer Console** (or set `QUILL_DEV_BUILD=1`). Messages show when the Quillin activates, deactivates, and every time the count refreshes.

## Capabilities

- `document.events` — subscribes to after_save, activated, quillin.enabled, quillin.disabled, settings.changed
- `editor.read` — reads document text to count
- `ui.announce` — speaks the count when announce-on-save is enabled
- `ui.status` — contributes the live status bar cell
- `ui.command` — registers the internal refresh handler
- `settings.own.read` / `settings.own.write` — reads and persists count-mode preferences
- `ui.log` — routes `api.log()` calls to the Developer Console

## License

MIT. Copyright (c) Blind Information Technology Solutions (BITS) and Community Access.
