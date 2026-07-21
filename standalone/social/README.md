# QUILL Social

**Accessibility-first social reading, publishing, and community workspace for Mastodon and Bluesky.**

Part of the QUILL family (QuillBeacon, QUILL Radio, QUILL Cast, QUILL Audio Studio, QuilleSync). QUILL Social is designed first for a blind keyboard and screen-reader user: every core action is reachable by keyboard, every important state is available as text, and reading, drafting, organizing, splitting, and scheduling all work locally before a single credential is entered.

Tagline: *Every conversation within reach.*

## What this build is

This repository implements the **full PRD roadmap** ([product requirements](docs/QUILL_Social_PRD_Working_Draft.md)) — every priority (P0–P2) and phase (0–8). See [docs/PHASES.md](docs/PHASES.md) for the phase→module map. It is a self-contained engine plus an accessible wxPython shell, following the same pattern as QuillBeacon and QUILL Audio Studio (a package that vendors its own dependency closure so it builds and runs from one repo). The production target moves the engine onto `quill.ui.app_shell.AppShellFrame` (PRD section 44).

Everything runs against local storage and deterministic mock backends, so you can try the whole experience — timelines, threading, composing, splitting, scheduling, campaigns, moderation, analytics, AI, GitHub, media — with no account, no AI key, and no network. **363 tests pass, ruff-clean.**

### Implemented

- **Accessible three-pane shell** — navigation tree, item list, details. Up/Down move between posts; Left/Right read the configured fields of the focused post; Enter opens details. Focus is never stolen by a refresh. Command center, Where Am I, context help, remappable keymap.
- **Capability-driven architecture** — the UI adapts to what each account supports instead of assuming every network is the same. Mastodon, Bluesky, and GitHub ship as capability descriptors with a live-probe path; deterministic mock backends make everything runnable.
- **Intelligent thread splitting** — paragraph/sentence/word boundaries, never breaks links/mentions/hashtags/Markdown/code, `1/n` numbering reserved out of the limit, Mastodon URL/mention weighting.
- **Publishing studio** — scheduler + thread publisher state machines (pause-on-failure, repair/resume, idempotency, backoff), DST-correct queue schedules, accessible agenda/calendar with conflict detection, approvals with a role matrix and audit trail, recurring content with safeguards, CSV/TSV/JSON/Markdown bulk import, and optimal-time suggestions.
- **Local-first SQLite** — WAL, FTS5 search, a generic document store, and re-fetch that preserves local read/flag/folder state. Pruning never touches drafts, notes, schedules, folders, or bookmarks.
- **Moderation & safety** — local filters (text/regex/author/domain/…), mutes, blocks, reports that exclude private notes, and a slur-to-placeholder helper.
- **Notifications** — categories, per-account/category policies, duplicate grouping, quiet hours, focus modes, and plain-language digests.
- **AI assistance** (optional, never publishes) — provider gateway with disclosure and a deterministic mock provider, prompt-injection defense, writing tools that return drafts, source-cited summaries, and a heuristic accessibility assistant.
- **Media & ecosystem** — media engine interface (mpv boundary) with a null backend, transcripts (SRT/VTT/TXT/MD), the QUILL/Radio/Cast/Audio Studio/Beacon bridge as inspectable intents, and QUILL Longform (safe Markdown→HTML, teaser threads).
- **GitHub** — issues, PRs, discussions, releases, notifications, plus social↔GitHub (issue drafts with attribution and no private notes, releases→campaigns).
- **Analytics** — measured metrics as accessible data tables with CSV/Markdown export and period comparison.
- **Resilience & extensibility** — offline outbox that never silently publishes expired posts, circuit breaker, plugin system (manifest validation, permissions, safe mode, crash isolation), credential store that persists references not tokens, and redacted diagnostics.
- **Headless CLI** — `quill-social-cli` for `accounts`, `refresh`, `search`, and `split`.

### Live network sign-in

The Mastodon, Bluesky, and GitHub adapters have real dual-mode implementations. Add an account with an access token / app password (stored in the OS credential vault via `keyring` — the database only holds a reference) and, when the network's client library is installed, the adapter calls the live service and maps responses into the domain model. With no client or credential it keeps a clear "not enabled" boundary and the app runs on the mock backends. The local scheduler runs on a timer while the app is open, so scheduled posts actually publish.

### Remaining documented boundaries

Implemented as interfaces with deterministic defaults and an `available()` probe — wiring the real dependency changes no schema or UI: a real AI provider, libmpv playback, and QUILL Cloud scheduling. See [docs/PHASES.md](docs/PHASES.md).

## Running from source

Requires Python 3.12+ and wxPython.

```
pip install -e .
quill-social            # launch the accessible shell
run-quill-social.bat    # Windows: launch with a portable data folder
```

The first launch seeds a demo account so the timeline is immediately usable. Use **File > Add Account** to register a Mastodon or Bluesky account (live sign-in lights up when the `networks` extra is installed).

### Headless CLI

```
quill-social-cli accounts
quill-social-cli refresh
quill-social-cli search accessibility
quill-social-cli split "a long post..." --limit 300
```

## Keyboard model

| Key | Action |
| --- | --- |
| Up / Down | Previous / next post |
| Left / Right | Read previous / next field of the focused post |
| Enter | Open the post in Details |
| Ctrl+N | Compose |
| Ctrl+R | Reply |
| Ctrl+Shift+R | Boost / repost |
| Ctrl+Q | Quote |
| Ctrl+F | Favourite |
| Alt+B | Bookmark |
| Ctrl+G | Open conversation |
| Ctrl+Shift+C | Command center |
| Ctrl+Shift+I | Where Am I |
| F5 | Refresh |
| F1 | Help |

All shortcuts are remappable (Preferences).

## Development

```
pip install -e ".[dev]"
pytest          # 363 tests, wx-free domain + guarded UI smoke
ruff check .
```

Architecture notes live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

MIT. See [LICENSE](LICENSE).
