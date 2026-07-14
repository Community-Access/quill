# Journal Stamp

**Bundled QUILL Quillin** — `com.quill.journalstamp`

The reference implementation of the `document_events` contribution model introduced in QUILL 0.6.0. Demonstrates all three document lifecycle hooks: `document.created`, `document.after_save`, and `document.loaded_from_session`.

## What it does

### Date header on new documents

When you create a new document inside a folder whose path contains `journal`, `diary`, or `notes` (configurable), Journal Stamp automatically inserts a formatted date header and announces it. The format is fully configurable: long English, ISO 8601, US style, or a custom strftime pattern.

### Word count after every save

After every save, Journal Stamp speaks your word count. If you have set a daily word goal, it tells you how many words remain. Set it to 0 to hear just the count. Set the mode to Off to silence it entirely.

### Session restore notice

When QUILL restores a document from a crash or previous session, Journal Stamp briefly announces the document name so you know exactly where you landed.

## Settings

Configure from **Preferences** (Ctrl+Comma) → **Journal Stamp**:

- **Date Header tab** — format (Long, ISO, US, Custom), separator style, and folder keyword filter.
- **Word Count tab** — when to announce (always, only when a goal is set, or never) and daily word goal.
- **Session Restore tab** — toggle the restore announcement on or off.

## Capabilities

- `document.events` — subscribes to document lifecycle events
- `editor.write` — inserts the date header
- `editor.read` — reads the document text for word counting
- `ui.announce` — speaks headers, word counts, and restore notices
- `settings.own.read` / `settings.own.write` — reads and persists settings

## License

MIT. Copyright (c) Blind Information Technology Solutions (BITS) and Community Access.
