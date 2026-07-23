# Podcast Feed Authentication (Username/Password) -- Design

Date: 2026-07-16
Status: approved for planning
Ships in: quill package (`quill.core.podcasts` / `quill.ui.podcasts`), so QUILL,
QUILL Cast, and any future wrapper get it identically.

## 1. Problem

Private and premium podcast feeds (Patreon, Supporting Cast, self-hosted
members-only shows) protect the RSS document -- and usually the audio
enclosures -- with HTTP Basic auth. `feed_reader._fetch_feed_bytes` already
accepts `username`/`password` and sends a preemptive `Authorization: Basic`
header, but nothing in the product calls it: there is no credential storage,
no UI to enter credentials, and downloads, streaming, transcripts, and
chapters ignore auth entirely. Subscribing to a private feed today fails with
a generic "Could not reach that feed" error.

## 2. Goals

- Subscribe to, refresh, download from, and stream Basic-auth-protected feeds.
- Store passwords in the platform secret store, never in plaintext files.
- Keyboard-first, screen-reader-first credential entry, consistent with the
  existing dialog contract.
- Distinguish "wrong credentials" from "network down" in every error message.

## 3. Non-goals

- OAuth, token, or cookie-based feed auth.
- Per-episode credentials (one username/password per show).
- Credential sync between machines (portable DPAPI store is machine-locked;
  documented, not solved).
- Exporting credentials via OPML (deliberately never).

## 4. Decisions (settled with the user, 2026-07-16)

- D-1 **Full coverage, same-host only.** Stored credentials are sent on feed
  refresh, episode downloads, streaming playback, transcript fetch, and
  chapter fetch -- but only when the request URL's host matches the feed
  URL's host. Requests to any other host (third-party CDNs, tokenized
  enclosure URLs) get no Authorization header, preventing credential leakage.
- D-2 **Prompt on 401 plus settings.** Add by Feed URL detects an auth
  failure and opens a credentials prompt, then retries. Existing shows
  manage credentials in the per-podcast settings dialog. Background refresh
  never opens modal prompts; it announces an actionable error instead.
- D-3 **Documented in both repos.** QUILL Cast's PRD, user guide, changelog,
  and README, plus QUILL's podcasts tutorial and release notes.

## 5. Storage design

- **Username** is not treated as a secret. New field on `PodcastShow`
  (`quill/core/podcasts/models.py`): `feed_username: str = ""`, persisted in
  `podcasts.json` via `to_dict`/`from_dict` like every other field. A
  non-empty `feed_username` is the flag that a show is credentialed.
- **Password** goes through the existing unified secret store
  (`quill/platform/windows/credential_store.py: load_secret / save_secret /
  delete_secret`) under the credential name `quill-podcast-feed:<show_id>`.
  That store already routes to Windows Credential Manager (installed), the
  DPAPI-encrypted `keys.enc` (portable, `QUILL_PORTABLE=1`), and the macOS
  login Keychain -- no new storage code.
- Passwords never appear in `podcasts.json`, OPML export, logs, or crash
  reports. Deleting a show deletes its credential; clearing the username
  clears the stored password too (no orphaned secrets).

### Portable caveat (documented, not fixed)

DPAPI is bound to the Windows user account and machine. A portable stick
moved to another PC keeps subscriptions but cannot decrypt stored feed
passwords; the user re-enters them once. The refresh error path (section 8)
already gives the recovery instruction.

## 6. New core module: `quill/core/podcasts/feed_auth.py`

Small, wx-free, strict-typed. Public API:

- `save_feed_password(show_id: str, password: str) -> None`
- `load_feed_password(show_id: str) -> str`
- `delete_feed_password(show_id: str) -> None`
- `auth_for_url(show: PodcastShow, url: str) -> tuple[str, str]` -- returns
  `(feed_username, password)` only when `show.feed_username` is non-empty AND
  `urlsplit(url).hostname` equals the feed URL's hostname (case-insensitive,
  exact match, no subdomain fudging); otherwise `("", "")`. This is the one
  same-host gate every call site uses.
- `basic_auth_header(username: str, password: str) -> str` -- moved/shared
  from `feed_reader._basic_auth_header` so download/transcript/chapter
  fetchers build the identical header.

## 7. Wiring (all inside existing reviewed egress sites; no new egress)

- `feed_reader.py`: already takes `username`/`password`. Add explicit
  `urllib.error.HTTPError` handling: 401/403 raises a new
  `FeedAuthError(FeedReaderError)` with a message naming the fix; other
  statuses keep the current generic message. `fetch_and_parse_feed` callers
  (`ui/podcasts/add_podcast_dialog.py`, `ui/main_frame_podcasts.py`
  `refresh_podcast_feed`) load credentials via `auth_for_url` and pass them.
- `download_queue.py`: `enqueue(...)` and `DownloadItem` gain an optional
  `auth_header: str = ""`; `_fetch_chunked` adds it as the `Authorization`
  header when non-empty. The enqueue call sites (manager dialog, Always
  Sync backfill, download-all) compute it with
  `auth_for_url(show, episode.audio_url)`.
- `transcripts.py` / `chapters.py`: fetch functions gain the same optional
  `auth_header` parameter; call sites pass the gated header.
- **Streaming playback** (`ui/podcasts/player_controller.py` and the Sound
  Enhancements ffmpeg relay): when `auth_for_url` yields credentials for the
  enclosure URL, the URL handed to the engine is rewritten to
  `https://user:pass@host/...` (percent-encoded userinfo; both mpv and
  ffmpeg support it). Any log line or announcement that carries a playback
  URL is redacted of userinfo (helper `redact_url_userinfo`, used at the
  logging call sites; `stability/redaction.py` gains the same pattern for
  crash reports).
- `opml.py`: unchanged; a test pins that export contains no username.
- `tools/network_egress_audit.py`: entry for `_fetch_chunked` etc. updated
  only if the audit keys on signatures; no new egress sites are introduced.

## 8. UI and error handling

- **Add Podcast dialog** (`add_podcast_dialog.py`): on `FeedAuthError` from
  Add by Feed URL (or Subscribe to Selected), open a small modal "Feed
  Credentials" dialog -- username field, masked password field
  (`wx.TE_PASSWORD`), OK/Cancel, routed through the shared dialog contract
  (modal ids, focus on username, announced title). OK retries the fetch with
  the credentials; success saves username to the show and password to the
  secret store, then continues the normal subscribe path. Cancel restores
  the status line with the auth error. A second 401 re-opens the prompt with
  the username prefilled and a "wrong username or password" status.
- **Show context menu** (Manager tree in `manager_dialog.py`; QUILL Cast's
  main library tree mirrors it): new "Feed Credentials..." item opening the
  same Feed Credentials dialog -- username prefilled, masked password field
  (blank means unchanged), and a "Clear Credentials" button that empties
  both and deletes the stored secret. Saving with a new password overwrites
  the secret. The item is absent for local shows (no feed). Note:
  `podcast_settings_dialog.py` is global defaults only, so it is NOT the
  home for per-show credentials; the context menu is where every other
  per-show action already lives.
- **Background refresh** (`refresh_podcast_feed`, refresh-all): a
  `FeedAuthError` never prompts. It announces and status-lines:
  "<Show>: feed sign-in failed. Update credentials in Podcast Settings."
  Downloads hitting 401 surface the same wording through the existing
  download-error path.
- All new controls have accessible names; every outcome (saved, cleared,
  retry failed) is announced. No color-only or unlabeled state anywhere.

## 9. Tests

Core (wx-free, fast):

- `auth_for_url`: same host -> credentials; different host, subdomain,
  no-username, local show -> `("", "")`.
- `feed_reader`: 401 -> `FeedAuthError`; 200-with-creds sends the expected
  `Authorization` header (mocked opener); other HTTP errors keep
  `FeedReaderError`.
- `download_queue._fetch_chunked`: `auth_header` present/absent on the
  request (mocked opener).
- `models`: `feed_username` round-trips `to_dict`/`from_dict`; absent key
  defaults to `""`.
- `opml`: export of a credentialed show contains no username/password.
- `feed_auth` store round-trip against the portable file store
  (`QUILL_PORTABLE=1` in a temp dir).
- URL userinfo redaction helper.

Existing egress-audit and persistence-audit gates must stay green.

## 10. Documentation deliverables

quill-cast repo:

- `docs/prd.md`: "Since 1.0" entry for Private Feeds; a security requirement
  line (password storage rule, same-host rule) in the appropriate section.
- `docs/userguide.md`: new "Private feeds (username and password)" section
  under Subscriptions -- subscribing, the 401 prompt, changing/clearing
  credentials in Podcast Settings, the portable-stick caveat; plus a
  Troubleshooting entry for "feed sign-in failed".
- `CHANGELOG.md` entry; `README.md` feature bullet.
- Regenerate html/epub via `scripts/render_docs.ps1`.

quill repo:

- `docs/tutorials/10-podcasts.md`: private-feeds section (same content,
  QUILL menu paths).
- Upstream changelog/release-notes entry per that repo's convention.

## 11. Out of scope, restated

OAuth/token auth, per-episode credentials, cross-machine credential sync,
credentials in OPML, auto-detecting auth for iTunes search results (search
returns public feeds; a 401 there flows through the same prompt anyway).
