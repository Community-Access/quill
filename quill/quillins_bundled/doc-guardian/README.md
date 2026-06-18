# Document Guardian

**Bundled QUILL Quillin** — `com.quill.docguardian`

A reference implementation showing `document.before_close`, `document.before_save`, and `document.after_save` event handlers. Document Guardian watches your documents and speaks up when something is worth knowing before it is too late.

## What it does

### Close Guard (document.before_close)

Before any tab closes, Document Guardian checks whether the document looks like it might be unfinished:

- If the document has never been saved and has fewer words than your threshold (default: 3), it speaks a warning so you can press Ctrl+Z if the close was accidental.
- If the document contains your TODO marker text (default: `TODO`), it warns you regardless of word count.
- Already-saved files are only checked for the TODO marker, not word count.

Document Guardian does not block or cancel the close — it just makes sure you heard the situation.

### Save Stamp (document.before_save)

If you keep a line beginning with `Updated:` in your plain-text notes, Document Guardian will update it with the current date and time before every save. Disabled by default. When enabled, it looks for the first line starting with `Updated:` and replaces it. If no such line exists, it leaves the document unchanged.

### Save Confirmation (document.after_save)

After every save, speaks the file name and size. Useful when saving to a network drive or an external device where you want confirmation that the file actually landed. Disabled by default.

## Settings

Configure from **Preferences** (Ctrl+Comma) → **Document Guardian**:

- **Close Guard tab** — enable/disable, word count threshold, and TODO marker text.
- **Save Stamp tab** — enable/disable, and timestamp format (Long, ISO 8601, date-only).
- **Save Confirmation tab** — enable/disable the after-save path-and-size announcement.

## Capabilities

- `document.events` — subscribes to before_close, before_save, and after_save
- `editor.read` — reads document text to count words and find TODO markers
- `editor.write` — rewrites the Updated: line before save
- `ui.announce` — speaks warnings, stamps, and save confirmations
- `settings.own.read` / `settings.own.write` — reads and persists settings

## License

MIT. Copyright (c) Blind Information Technology Solutions (BITS) and Community Access.
