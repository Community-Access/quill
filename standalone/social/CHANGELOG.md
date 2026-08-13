# Changelog

All notable changes to QUILL Social are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
semantic versioning once it reaches a stable release.

## [Unreleased]

QUILL Social became a feed reader as well as a social client, and grew an
installer of its own.

### Added — QUILL Social has an application icon

- **An icon of its own, for the app and the installer.** QUILL Social shipped
  with none at all, so the build wore PyInstaller's generic default -- the same
  generic default as any other unbranded Python app, which in a taskbar or an
  Alt+Tab list is indistinguishable from software the listener never installed.
  Its icon is now two overlapping speech bubbles on a plum tile, sharing the
  QuillVille family's rounded tile shape and amber accent. The overlap is the
  point: QUILL Social is feeds and conversations from several places at once,
  and a single bubble would have said "messaging". `Setup.exe` carries it too.

### Added — the documentation is reachable from inside the app

- **Help > User Guide**, **Help > Keyboard Reference**, and **Help >
  Product Requirements** open the documents QUILL Social already installs
  beside itself. Until now the Help menu offered only the in-app shortcut list
  and About, so the user guide the installer places in `docs\` -- and puts a
  Start-menu shortcut to -- could not be opened from the app at all. They open
  in your browser, where a screen reader already has heading, link and
  find-in-page navigation, and they need no internet connection.
- The in-app shortcut list is now named **Keyboard Guide (shortcuts)** rather
  than just "Help", because it and the User Guide are different things: it
  lists the shortcuts *currently in effect*, including any you have remapped,
  while the Keyboard Reference documents the shipped defaults. `F1` still opens
  it.
- The Start-menu **User Guide** shortcut now opens the HTML copy rather than
  the Markdown one. A stock Windows install has no default handler for `.md`,
  so that shortcut could open nothing at all; both formats are installed.

### Added — RSS, Atom and JSON Feed reading

- A full **feed reader**, built on the same store, list, and announcer the
  social timeline already used. New `adapters/rss.py` parses RSS 2.0, Atom,
  RSS 1.0, and JSON Feed 1.0/1.1 with the standard library alone -- no new
  dependency. Entries map to the same item model, so everything the app
  already does (read state, bookmarks, search, folders, field-by-field
  reading) works on articles unchanged.
- **Subscriptions** with per-feed settings: title, refresh cadence, retention
  in days (0 = keep forever), announce-new-articles, fetch-full-article, and
  keyword rules. Subscribing is idempotent by URL; unsubscribing removes the
  feed's cached items with it.
- **Feed discovery**: paste a site address rather than a feed address and the
  app reads the page's `<link rel="alternate">` tags, then probes the ten
  usual feed paths, and offers what it found.
- **Nested folders** for feeds, to any depth, with live unread counts spoken
  in each tree node's own label (`News (12 unread)`) rather than shown only
  in colour. Counts update in place, so marking a folder read never moves
  your focus.
- **Smart folders** are now reachable: a `Smart Folders` group in the
  navigation tree plus New / Edit / Delete dialogs. Rules cover keyword,
  author, unread-only, has-media, bookmarked-only, and a minimum engagement
  threshold; an all-blank rule is refused rather than silently matching
  everything.
- **OPML import and export**, nested folders included, so a library moves in
  and out of other readers intact.
- **Per-feed keyword rules**, applied to new articles in list order,
  first match wins: **hide** (never stored), **mark read** (stored already
  read, and not counted as new), or **star** (stored flagged, and protected
  from retention pruning).
- **Full-article fetch** for feeds that only publish a summary: the article
  page is fetched, narrowed to its `<article>` or `<main>` content, stripped
  of navigation chrome, and used in place of the truncated body -- but only
  when the result is genuinely longer. Capped at 20 articles per refresh so
  a large backlog cannot stall a tick.
- **Background auto-refresh** on the existing 30-second timer, running on its
  own thread with its own database connection so the window never freezes.
  Feeds are refreshed only when their own interval has elapsed, a feed set to
  "Manual only" is never refreshed automatically, and a failure backs off that
  one feed instead of aborting the batch. New articles are announced politely
  ("N new article(s).") without stealing focus. Manual F5 now runs feeds
  through the same path, so rules, full-text, and retention apply either way.
- **Conditional polling**: feeds are fetched with `If-None-Match` and
  `If-Modified-Since` and a 304 skips parsing entirely, with transparent
  gzip/deflate handling. Feed fetches are HTTPS-only, TLS-verified, size-
  capped, and reject DOCTYPE and ENTITY declarations.
- **Articles render as accessible plain text**, never HTML and never a web
  view: scripts, styles, and embedded frames are discarded outright, block
  elements become line breaks, list items become "- ", links read as
  `text (url)`, and images read as `[Image: alt]`.
- **Reading-position memory**: reopening a feed or folder puts focus back on
  the article you were last on, or on the first unread one.
- **Mark all read**, scoped to the current view, with a real **undo**
  (Ctrl+Z) that restores exactly the items that changed, and an announcement
  that says how many.
- Unread rows are shown in bold as a secondary low-vision cue; read state is
  still spoken, never colour-only.

### Added — Lemmy, and adapter groundwork for more

- **Lemmy** joins the Add Account network list. Reading a community works
  from the public instance with no credential at all; the Add Account dialog
  says so, and says that posting and voting arrive later.
- Mastodon-compatible servers -- Pixelfed, GoToSocial, Firefish, Sharkey,
  Iceshrimp -- are now recognised and reuse the Mastodon adapter and its
  browser sign-in flow. Pixelfed, GoToSocial, and Firefish appear in the Add
  Account network list.
- Per-network **guidance text** in the Add Account dialog explains, in plain
  language, what each network is and what you need to connect to it.
- Read-only adapters for **Hacker News**, **OPDS book catalogues**, and
  **Telegram** channels are implemented and tested but not yet reachable:
  there is no way to add an account for them, and Telegram's api-id/api-hash
  sign-in is still to come. Groundwork only.

### Added — Listen to your queue

- **Listen**: continuous, hands-free read-aloud of the unread articles in the
  current view, auto-advancing from one to the next -- your reading list as a
  podcast. Between articles it speaks a short handoff ("Title, from Feed.").
- Transport controls for listening: play/pause, next article, previous
  article, and stop. Transport confirmations ("Paused", "Playing", "Stopped",
  "End of the listen queue.") go through the screen-reader announcement
  channel rather than the reading voice, so nothing is ever said twice at
  once.
- Narration uses Windows SAPI 5 and runs off the UI thread. If no speech
  engine is available the app says so instead of failing.

### Added — Find

- **Find Text**, **Find Next** (F3), and **Find Previous** (Shift+F3) on the
  Tools menu, with a Find dialog that has a real Direction radio group
  (Forward / Backward).

### Added — menus and dialogs

- New **Feeds** menu: Add Feed... (Ctrl+Shift+N), New Folder..., Feed
  settings... (Ctrl+Shift+P), Mark all read (Ctrl+Shift+K), Undo mark all
  read (Ctrl+Z), New smart folder..., Edit smart folder..., Delete smart
  folder, Import OPML..., Export OPML..., Unsubscribe from feed.
- New **Listen** menu: Listen to this view (Ctrl+Shift+L), Play / Pause,
  Next article, Previous article, Stop listening.
- New dialogs -- Add Feed, New Folder, Feed settings, New/Edit Smart Folder,
  Find Text -- each with every control labelled and named, keyboard-complete,
  and no checkboxes inside a list. The Add Feed dialog's status line is
  spoken as well as displayed, and focus moves to the results list when
  feeds are found.

### Added — packaging

- A QUILL Social installer: per-user by default, x64, with **Full /
  Compact / Custom** setup types, a fixed program component, and an optional
  **Documentation** component that also gates the Start-menu User Guide
  shortcut. An optional desktop icon, off by default. Upgrades wipe the
  app's own internal tree first so a renamed module cannot leave a stale
  copy behind, and uninstalling never deletes your data.
- A release build script producing the staged app folder, a portable zip
  with its own `data` folder, and the installer in one pass.
- Rendered HTML documentation now uses a shared accessible template: a
  language attribute, a descriptive page title taken from the document's own
  heading, a skip link, and a `main` landmark.

### Changed

- One server was removed from the Add Account instance-preset list.
- The item store gained scoped bulk read-state changes, so marking a view
  read reports an accurate count and can be undone exactly; per-feed
  retention pruning never touches bookmarked or flagged items.

### Known issues

- **Ctrl+F is claimed twice.** Tools > Find Text and Item > Favourite both
  bind Ctrl+F. Use F3 and Shift+F3, or the Tools menu, to reach Find
  reliably.
- The new Feeds, Listen, and Find commands are menu-only: they are not in
  the command center and are not remappable in Preferences.
- The F1 help dialog and the User Guide have not been updated for any of the
  above.

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
