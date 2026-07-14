# Smart Insert

**Bundled QUILL Quillin** — `com.quill.smartinsert`

Typed templates, log entries, BRF test content, and smart triggers for everyday writing tasks. Also the reference implementation of the Quillin abbreviations, smart triggers, and preferences contribution model introduced in QUILL 0.6.0.

## What it does

### Abbreviations

Type any of these followed by a space, period, comma, or other delimiter:

| Trigger | Inserts |
| --- | --- |
| `qbug` | Bug report template |
| `qmeet` | Meeting notes template with today's date |
| `qlog` | Date and time timestamp |
| `qtodo` | Three-item to-do checklist |
| `qbrf` | Predictable BRF test document |

### Smart triggers

Type any of these alone on a line and press Enter:

| Trigger | Inserts |
| --- | --- |
| `=bug()` | Bug report template |
| `=meeting()` | Meeting notes template |
| `=journal()` | Journal entry with today's date |
| `=todo(5)` | Five-item to-do checklist (number is optional) |
| `=logentry()` | Timestamp formatted by your Log Mode settings |
| `=brftest()` | Multi-page BRF test document |
| `=rand(3,4)` | Three paragraphs, four sentences each |

### Settings

Configure from **Preferences** (Ctrl+Comma) → **Smart Insert**:

- **General** — large-insertion threshold and default to-do list length
- **Log Mode** — timestamp format and custom strftime pattern
- **Smart Triggers** — enable/disable individual triggers
- **Abbreviations** — enable/disable individual abbreviations
- **BRF Testing** — page count, lines per page, test line text

## Capabilities

- `editor.write` — inserts text at the cursor
- `ui.announce` — speaks the result of every action
- `ui.command` — registers Python handlers
- `settings.own.read` / `settings.own.write` — reads and writes its own settings

## License

MIT. Copyright (c) Blind Information Technology Solutions (BITS) and Community Access.
