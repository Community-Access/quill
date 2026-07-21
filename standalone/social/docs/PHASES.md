# QUILL Social — phase completion map

This maps every phase and priority in the PRD (sections 36–37) to the code that
implements it. The whole roadmap is built as tested, wx-free logic with an
accessible wxPython shell on top; anything that needs a live external service
(Mastodon/Bluesky/GitHub sign-in, an AI provider, libmpv, a cloud scheduler, an
OS credential vault) sits behind an interface with a deterministic default, so
the app runs and every test passes with no credentials and no network.

Totals: 57 package modules, 41 test files, **363 tests passing**, ruff-clean.

## Priorities

### P0 — Foundational release (PRD 36)

| Area | Module(s) |
| --- | --- |
| Accessible wx shell | `ui/app.py`, `ui/announce.py`, `ui/commands.py`, `ui/composer.py` |
| Mastodon + Bluesky (capability-driven) | `adapters/{base,mastodon,bluesky,mock,registry}.py`, `capabilities.py` |
| Multiple accounts, capability registry | `model.py` (Account/Workspace), `capabilities.py` |
| Timelines, threads, profiles, details | `db.py`, `fields.py`, `ui/app.py` |
| Compose/reply/quote/repost/like/bookmark | `services/composer.py`, `ui/composer.py`, `ui/app.py` |
| Media + alt text, content warnings, visibility, polls | `model.py`, `services/composer.py` |
| Intelligent thread splitting | `services/thread_splitter.py` |
| Search, folders, saves, drafts | `db.py` (FTS5), `services/smartfolder.py` |
| Native + local scheduling | `services/scheduler.py`, `services/thread_publisher.py` |
| Command center, Where Am I, help, remappable keys | `ui/commands.py`, `whereami.py`, `keymap.py` |
| Secure credentials | `security/credentials.py` |

### P1 — Power release (PRD 36)

| Area | Module(s) |
| --- | --- |
| Full campaigns and queues | `services/queue_schedule.py`, `services/calendar.py`, `model.py` (Campaign) |
| Approvals | `services/approvals.py` |
| Cross-network variants | `services/composer.py` (per-network variants), `services/thread_splitter.py` |
| Smart folders | `services/smartfolder.py` |
| AI | `services/ai/{gateway,prompt_guard,writing,understand,accessibility}.py` |
| Transcription orchestration | `services/transcripts.py` |
| Full moderation center | `services/moderation.py` |
| GitHub | `adapters/github.py`, `services/github_bridge.py` |
| QUILL ecosystem integration | `services/ecosystem.py`, `services/longform.py` |
| Analytics | `services/analytics.py` |

### P2 — Community and scale (PRD 36)

| Area | Module(s) |
| --- | --- |
| Team workspaces + approvals/roles | `services/approvals.py` (role matrix) |
| QUILL Longform hosting | `services/longform.py` |
| Advanced automation / recurring | `services/recurring.py` |
| Plugin system | `services/plugins.py`, `plugins/` |
| Additional networks via adapters | `adapters/base.py` contract, `adapters/registry.py` |

## Implementation phases (PRD 37)

- **Phase 0 Foundations** — adapter contracts (`adapters/base.py`), threat-model
  seams (`security/`, `services/ai/prompt_guard.py`), accessible-control proof
  (`ui/`), media proof (`services/media.py`).
- **Phase 1 Reader** — accounts, timelines, notifications, caching, reading
  positions, details, threads (`db.py`, `ui/app.py`, `services/catchup.py`).
- **Phase 2 Composer** — media, alt text, polls, CWs, visibility, thread gates,
  splitting, capability validation (`services/composer.py`, `ui/composer.py`).
- **Phase 3 Organization** — folders, smart folders, saves, notes, templates,
  search, catch-up (`services/smartfolder.py`, `services/templates.py`, `db.py`).
- **Phase 4 Publishing Studio** — drafts, queues, agenda/calendar, scheduling,
  campaigns, approvals, recurring, bulk import, retries, analytics foundation
  (`services/{queue_schedule,calendar,optimal_time,approvals,recurring,bulk_import,scheduler,analytics}.py`).
- **Phase 5 Media + Ecosystem** — player, transcripts, chapters, QUILL / Radio /
  Cast / Audio Studio / Beacon / Sync bridge, longform
  (`services/{media,transcripts,ecosystem,longform}.py`).
- **Phase 6 AI** — provider gateway, writing tools, summaries, descriptions,
  transcription orchestration, accessibility checks, prompt-injection defenses
  (`services/ai/`).
- **Phase 7 GitHub + Teams** — GitHub views, issue/discussion workflows, release
  campaigns, shared-workspace roles (`adapters/github.py`,
  `services/github_bridge.py`, `services/approvals.py`).
- **Phase 8 Cross-Platform** — platform data dirs (`paths.py`, macOS/Windows),
  plugin system (`services/plugins.py`), offline resilience
  (`services/outbox.py`), diagnostics (`security/diagnostics.py`).

## What is a documented live boundary (not a gap)

These are implemented as interfaces with deterministic defaults and an
`available()` probe; wiring the real dependency does not change the schema or UI:

- Live Mastodon/Bluesky/GitHub network calls (adapters raise a clear error and
  expose a capability probe until a client + OS-stored token is configured).
- A real AI provider (the gateway ships a deterministic `MockProvider`).
- libmpv playback (`MpvMediaEngine` boundary; `NullMediaEngine` is the default).
- QUILL Cloud scheduling (the local + native tiers are complete; the cloud tier
  is an interface).
- OS credential vault (`WindowsCredentialManagerStore` boundary;
  `InMemoryCredentialStore` default). The database only ever stores references.
