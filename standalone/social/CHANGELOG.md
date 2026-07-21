# Changelog

All notable changes to QUILL Social are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
semantic versioning once it reaches a stable release.

## [0.3.0] - 2026-07-19

Made the full roadmap reachable from the app and wired live network sign-in.
409 tests passing, ruff-clean.

### Added — every service now reachable in the shell

- New **Studio** menu: Drafts (open a draft back into the composer), Agenda /
  Calendar, Queue schedule, Approvals.
- **Tools** menu now opens the real Safety Center, Notification policies, Plugin
  manager, and Outbox dialogs (plus Insights and AI summary).
- **Item** menu gains Play media (accessible player with transcript sync) and
  keeps Accessibility check / Send to QUILL.
- All of the above are also searchable in the command center.
- Accessible dialogs for each area (`ui/studio.py`, `ui/manage.py`,
  `ui/media_player.py`): every control labelled and named, report-mode lists,
  keyboard-complete, no mouse-only paths.

### Added — deeper composer (PRD 15)

- Media attachments with per-attachment alt-text editing, a poll builder
  (options, single/multiple, duration), a schedule date/time, and a template
  picker sourced from the saved-reply library. The composition report reflects
  media, alt-text gaps, and poll options live.

### Added — live network sign-in (PRD 22, 23, 24, 31)

- Mastodon, Bluesky, and GitHub adapters now have real dual-mode
  implementations: with a client (built by the registry from a stored
  credential, or injected in tests) they call the network and map responses into
  the domain model; with no client/credential they keep the clear "not enabled"
  boundary. Response→model mapping is pure and unit-tested with fixtures, without
  importing the optional SDKs.
- `registry.adapter_for(account, credentials=None)` resolves the account's secret
  at the boundary and builds a connected client (lazy SDK import). Secrets are
  stored in the OS credential vault (Windows Credential Manager via `keyring`);
  the database only ever holds a reference.
- Add Account collects an access token / app password and stores it securely.

### Added — live local scheduler

- A `wx.Timer` drives the local scheduler every 30 seconds while the app is
  open, so due plans actually publish (with the same backoff and
  transient-vs-review policy), and the timeline refreshes with an announcement.

## [0.2.0] - 2026-07-18

Full roadmap build: every PRD phase and priority (P0–P2, phases 0–8) now has a
tested implementation. See [docs/PHASES.md](docs/PHASES.md) for the phase→module
map. 363 tests passing, ruff-clean, 57 package modules.

### Added — Phase 3 organization, safety, analytics

- **Moderation / Safety Center** (`services/moderation.py`, PRD 27): local
  filters (text/regex/author/domain/network/type/media/language/label/time) with
  hide/warn/collapse/mute-speech/replace-slurs/require-reveal actions, mutes,
  blocks, domain blocks, reports that exclude private notes by default, and a
  slur-to-placeholder helper.
- **Notifications** (`services/notifications.py`, PRD 25): categories, per
  account/category policies, duplicate grouping, quiet hours (midnight-crossing),
  focus modes, and plain-language digests; critical categories bypass quiet hours.
- **Templates / saved replies** (`services/templates.py`, PRD 13.5): variables,
  network variants, signatures, and a persisted library.
- **Analytics** (`services/analytics.py`, PRD 33): measured metrics as accessible
  data tables, CSV/Markdown export, and period comparison kept separate from
  measurement.

### Added — Phase 4 publishing studio

- Queue schedules with DST-correct slot math (`services/queue_schedule.py`),
  accessible agenda/day/week/month calendar with conflict detection
  (`services/calendar.py`), optimal-time suggestions that avoid false certainty
  (`services/optimal_time.py`), an approval workflow with a role matrix and audit
  trail (`services/approvals.py`), recurring content with safeguards
  (`services/recurring.py`), and CSV/TSV/JSON/Markdown bulk import with dry-run
  and duplicate detection (`services/bulk_import.py`).

### Added — Phase 5 media and ecosystem

- Media engine interface with a deterministic null backend and an mpv boundary,
  player state machine with position memory / A-B loop / queue
  (`services/media.py`); transcripts with SRT/VTT/TXT/Markdown import-export,
  search, and time-point quotes (`services/transcripts.py`); the QUILL ecosystem
  bridge as inspectable intents for QUILL / Radio / Cast / Audio Studio / Beacon
  (`services/ecosystem.py`); and QUILL Longform with a safe Markdown→semantic-HTML
  renderer and teaser-thread generation (`services/longform.py`).

### Added — Phase 6 AI assistance

- `services/ai/`: a provider gateway with disclosure and a deterministic mock
  provider; prompt-injection defense that fences untrusted social text as data,
  detects injection, and redacts secrets; writing tools that always return draft
  proposals; understanding tools whose summaries always list their sources; and a
  heuristic accessibility assistant. AI never publishes and is fully optional.

### Added — Phase 7–8 GitHub, plugins, resilience, security

- GitHub adapter + deterministic MockGitHub (`adapters/github.py`) and social↔
  GitHub bridge that excludes private notes and turns releases/PRs into campaigns
  and threads (`services/github_bridge.py`); a plugin system with manifest
  validation, permission enforcement, safe mode, and crash isolation
  (`services/plugins.py`, `plugins/`); an offline outbox that never silently
  publishes expired posts, plus a circuit breaker (`services/outbox.py`); a
  credential store that persists references not tokens, and redacted diagnostic
  bundles (`security/`).

### Added — UI integration

- New navigation feeds for GitHub (notifications, issues, PRs, discussions,
  releases); Tools menu entries and command-center commands for Insights,
  Safety Center, and AI summary; Item menu entries for Accessibility check and
  Send to QUILL; and a reusable accessible text-report dialog.

## [0.1.0] - 2026-07-18

The P0 foundational slice: a self-contained engine plus an accessible wxPython
shell that runs against local storage and a deterministic mock network, so the
whole experience works before any credential is entered.

### Added

- **Layered architecture** (PRD 29): wx-free `model`, `capabilities`, `db`,
  `keymap`, `fields`, `whereami`, `a11y`, `adapters/`, and `services/`, with the
  wxPython shell as a thin presentation layer on top.
- **Accessible shell** (`ui/app.py`): navigation tree, configurable item list
  with field-by-field Left/Right reading, details pane, status-bar announcer,
  and full keyboard/menu/command-center dispatch. Focus is preserved across
  refreshes.
- **Capability registry** (PRD 6.3, 11.4): per-account capabilities seeded per
  network (Mastodon, Bluesky, GitHub, mock) with a live-probe refine path. The
  UI adapts to what each account supports.
- **Network adapters** (PRD 22, 23): a common `NetworkAdapter` contract; a
  deterministic in-memory `MockNetwork` that drives the P0 experience; Mastodon
  and Bluesky descriptors that declare capabilities and mark the boundary where
  a live client is required.
- **Intelligent thread splitter** (PRD 16.1): paragraph/sentence/word boundary
  preference, never breaks links/mentions/hashtags/Markdown links/inline code,
  `1/n` numbering reserved out of the limit, pluggable counter with a Mastodon
  URL/mention weighting.
- **Thread publisher** (PRD 16.2): ordered reply-chain publishing that pauses on
  the first failure without republishing successes, with repair/resume and
  per-segment idempotency keys.
- **Scheduler** (PRD 18.8, 18.12): a state machine with a validated transition
  table, exponential backoff for transient errors, and a stop-and-review policy
  for validation/permission/privacy failures. One plan per account so a failure
  on one destination never blocks or duplicates the others.
- **Composer model** (PRD 15.3, 15.6): live per-network character counts, thread
  segment counts, and capability/accessibility checks.
- **Local-first store** (PRD 30): SQLite with WAL and FTS5, re-fetch that
  preserves local read/flag/folder state, and cache pruning that never removes
  drafts, notes, schedules, folders, or bookmarked posts.
- **Catch-up** (PRD 12.6) and **smart folders** (PRD 13.2): repost and
  cross-network collapse, people/conversation grouping, and inspectable rules.
- **Command center, Where Am I, context help, remappable keymap** (PRD 10).
- **Accessibility settings** (PRD 28): verbosity, high contrast, text scale, and
  social-specific speech toggles, persisted next to the database.
- **Headless CLI** (`quill-social-cli`): `accounts`, `refresh`, `search`,
  `split`.
- **Test suite**: 119 tests across the domain, services, adapters, persistence,
  and a guarded wx smoke test; ruff-clean.

### Known limitations

- Live Mastodon/Bluesky sign-in, QUILL Cloud scheduling, AI, GitHub, media
  playback, and QuilleSync are architected for but not enabled in this slice.
