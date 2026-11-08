# Scrobbling and AudD song recognition

Branch `feat/br-scrob`. Two ideas from BlindRadio by serrebidev (MIT,
https://github.com/serrebidev/blindradio), both chosen in
`docs/design/blindradio-review-2026-11-07.md` (items 4 and 5). Both are off by
default and send nothing until the listener turns them on and signs in or
pastes their own token. No BlindRadio code was copied; the request shapes, the
last.fm signature and the one-minute rule follow its `scrobble.rs` and
`recognize.rs`, checked against the official API documentation.

## What was built

### Scrobbling

- Songs heard for a minute or more are sent to ListenBrainz, last.fm and
  Libre.fm, each switched on separately in Preferences, Scrobbling group.
- **The rule is one minute, and that is deliberate.** last.fm's own rule is
  "longer than 30 seconds, and played for half its length or 4 minutes,
  whichever comes first"; ListenBrainz asks for the same half-or-4-minutes.
  Both need the song's length, and radio almost never sends one. So Quill
  Radio uses BlindRadio's rule: a minute heard. It is longer than 30 seconds
  and shorter than 4 minutes, so it never sends a song last.fm would call too
  short, and it never waits for a length nobody knows.
- **Heard, not broadcast.** Titles are kept as a broadcast timeline; the clock
  that counts is the playhead (now minus how far behind live playback is, read
  from the mpv engine). A pause adds nothing, rewinding adds nothing, jumping
  ahead adds no more than real time. A listen is stamped with when hearing
  began. Up to six hours of timeline is kept, past the longest time-shift
  buffer.
- Noise titles (`song_history.is_noise_title`: the station's own name, Live,
  advert markers) and titles without an artist are never sent; a noise title
  still ends the song before it.
- Hooked at `song_history_commands.record_song`, the one choke point every
  title change already goes through (ICY, the engine, the status page), so
  scrobbling and Song History never disagree. It runs even when Song History
  is off. A 5-second wx timer runs only while a song is followed and stops
  when nothing plays.
- ListenBrainz: `POST /1/submit-listens` with `Authorization: Token ...`;
  `single` for one listen, `import` for several, `playing_now` for the song
  just started (never retried).
- last.fm and Libre.fm: the desktop sign-in flow. `auth.getToken` on a
  worker, the browser opens the service's own "allow Quill Radio?" page, a
  message box waits until the listener comes back and chooses OK, then
  `auth.getSession` on a worker. The password is never typed into Quill
  Radio. `track.scrobble` in batches of up to 50 with `chosenByUser=0` (what
  last.fm asks a radio player to send), `track.updateNowPlaying` when a song
  starts (never retried). Libre.fm uses `https://libre.fm/2.0/` and
  `https://libre.fm/api/auth/`.
- Pressing Sign In again while signed in offers to sign out (No is the
  default).
- **Failed submissions wait in a queue on disk** (`radio_scrobble_queue.json`
  in the data folder, atomic writes): 500 songs per service at most (newest
  kept), dropped after 14 days (last.fm ignores older scrobbles), retried after
  1, 2, 4 ... minutes up to an hour. Error 9 and HTTP 401 hold the songs until
  the listener signs in again and say so once per session; 11, 16, 29, 429 and
  5xx retry; anything else drops the batch, because it will never be accepted
  as written. All sending runs on the task manager; the queue file is written
  on the worker, never on the UI thread.
- Nothing runs in Safe Mode.

### The last.fm application key

last.fm needs an API key and shared secret for the application. None is
invented or committed. QUILL already ships build-time credentials through
gitignored generated modules (`tools/generate_podcast_index_key.py`,
`tools/generate_youtube_oauth_client.py`), so this follows that:

- `tools/generate_lastfm_api_key.py` writes the gitignored
  `quill/_lastfm_api_key.py` from `QUILL_LASTFM_API_KEY` /
  `QUILL_LASTFM_SHARED_SECRET` (or the `_FILE` variants). Lenient: with
  nothing set it writes an empty pair, or keeps a pair already written.
- Called leniently from `scripts/build_windows_distribution.py` and
  `standalone/runtime/build_runtime.ps1`.
- The listener can always paste their own pair into Preferences (last.fm API
  key and last.fm shared secret boxes), and their own pair wins, the way the
  Podcast Index credential works. With neither, Sign In says what is missing,
  and a Get a last.fm API Account button opens
  https://www.last.fm/api/account/create.
- Libre.fm uses the same pair. GNU FM has historically accepted any client
  key, so a build could drop that requirement for Libre.fm alone; I did not
  verify that against libre.fm live, so it is not relied on.

**Someone has to register the application** at
https://www.last.fm/api/account/create and put the pair into the release
build environment. Until then, last.fm and Libre.fm need the listener's own
pair.

### AudD recognition

- Preferences, Song recognition group: a Song recognition service choice
  (AcoustID, the default, or AudD) and an AudD API token box. The AcoustID key
  box moved into the same group.
- Identify This Song is unchanged for AcoustID. With AudD chosen it needs only
  the token (no fpcalc), takes a 20-second clip from the buffer already playing
  (the same `dump_recent_audio` sample AcoustID uses, shorter), and posts it as
  multipart to `https://api.audd.io/` with the token. The clip is capped at
  AudD's 10 MB limit and deleted afterwards.
- AudD's answer maps into the same `acoustid.Match` AcoustID returns (title,
  artist, a new optional `album` field, score 1.0 because AudD gives none).
  The sentence names AudD and never says a percentage: "AudD says: Constant
  Craving by k.d. lang, from Ingenue."
- AudD errors 900 (token not accepted) and 901 (free limit, no token) are their
  own sentences; 300 (too short) is "no match". No automatic polling: AudD is
  only ever asked when the listener presses Identify This Song.

### Secrets

Every token and session key is kept in the Windows credential store
(DPAPI-sealed to the user) through the new `quill/core/radio/radio_credentials.py`,
the same store the AcoustID key uses; nothing is in a settings file, so a
synced or exported data folder carries none of them. Session keys carry the
account name in the credential's user-name field. `tests/conftest.py` has a new
autouse fixture, `radio_credential_store`, so no test reaches the real store.

## Files

New:

- `quill/core/radio/scrobble_tracker.py` - the one-minute rule and the playhead model.
- `quill/core/radio/scrobble_queue.py` - the retry queue.
- `quill/core/radio/scrobble_http.py` - the one scrobbling egress site.
- `quill/core/radio/listenbrainz.py`, `quill/core/radio/lastfm.py` - the services.
- `quill/core/radio/scrobbling.py` - accounts, sending what is due, now playing.
- `quill/core/radio/radio_credentials.py` - credential-store access.
- `quill/core/radio/audd.py` - AudD request and answer.
- `quill/ui/radio/scrobble_commands.py` - the title hook, the timer, the workers.
- `quill/ui/radio/scrobble_signin.py` - the browser sign-in.
- `quill/apps/radio_preferences_scrobble.py` - the Preferences rows.
- `quill/tools/network_egress_entries_radio_listening.py` - the two egress rows.
- `tools/generate_lastfm_api_key.py` - the build-time key module.
- Tests: `tests/unit/core/radio/test_scrobble_tracker.py`,
  `test_scrobble_queue.py`, `test_scrobble_services.py`,
  `test_audd_recognition.py`, `tests/unit/ui/test_radio_scrobble_ui.py`,
  `tests/unit/tools/test_generate_lastfm_api_key.py`.

Changed: `song_recognition.py` (service choice, AudD path), `acoustid.py`
(`Match.album`), `history.py` / `history_store.py` (four settings),
`song_identify_commands.py`, `song_history_commands.py` (the hook),
`radio_preferences.py` / `radio_preferences_listening.py` (rows),
`app_preferences_dialog.py` (`text_value`, so Sign In reads the key boxes
before OK), `network_egress_entries.py`, `.gitignore`, the two build scripts,
`tests/conftest.py`.

## Keys added

None. Identify This Song keeps its existing command and chord. The new
Preferences rows have no access keys: that dialog has no free letter left,
and GATE-14 prefers no mnemonic to a duplicate.

## Settings added

In `RadioHistory` (`radio_history.json`):

| Setting | Default | Meaning |
| --- | --- | --- |
| `scrobble_listenbrainz` | false | Send songs heard to ListenBrainz |
| `scrobble_lastfm` | false | Send songs heard to last.fm |
| `scrobble_librefm` | false | Send songs heard to Libre.fm |
| `recognition_service` | `acoustid` | `acoustid` or `audd` |

In the Windows credential store (never a file): `quill:radio:listenbrainz:token`,
`quill:radio:lastfm:api-key`, `quill:radio:lastfm:secret`,
`quill:radio:lastfm:session`, `quill:radio:librefm:session`,
`quill:radio:audd:token`. New data file: `radio_scrobble_queue.json`.

## Egress rows added

`quill/tools/network_egress_entries_radio_listening.py`:

- `core/radio/scrobble_http.py::post` - ListenBrainz submit-listens, last.fm
  and Libre.fm 2.0 API (sign-in, scrobble, now playing). Artist, title, album
  and time heard, plus the listener's own token or session key. Off by
  default, worker only, HTTPS only, refused in Safe Mode.
- `core/radio/audd.py::_post` - one multipart POST to api.audd.io with the
  listener's token and about 20 seconds of audio, only from Identify This Song
  with AudD chosen.

## User guide text (to add)

Under Identify This Song:

> ### Choosing AudD instead of AcoustID
>
> Identify This Song asks AcoustID by default. AcoustID is free, and all it is
> sent is a fingerprint of the audio, which cannot be played back. If you have
> an AudD account, you can ask AudD instead: it copes better with live radio,
> where a presenter talks over the start of a song or one song runs into the
> next. To use it, open Preferences, find the Song recognition group, set Song
> recognition service to AudD, and paste your AudD API token (from
> dashboard.audd.io) into the AudD API token box.
>
> Be clear about the difference. AudD is sent about twenty seconds of the
> audio itself, together with your token. Quill Radio only does that when you
> choose Identify This Song; it never listens on its own. To go back, set Song
> recognition service to AcoustID.

A new section, Scrobbling:

> ## Scrobbling: keeping a list of what you heard
>
> Quill Radio can add the songs you hear to your listening history on
> ListenBrainz, last.fm or Libre.fm. This is called scrobbling. It is off until
> you turn it on.
>
> Scrobbling sends the artist, title and album of each song you hear for a
> minute or more, and the time you heard it, to the services you turn on, and
> only when you turn one on and sign in or paste your token. Nothing about the
> station or about you is sent.
>
> **ListenBrainz.** Open Preferences, find the Scrobbling group, and paste your
> user token from listenbrainz.org/settings into the ListenBrainz user token
> box. Check Send the songs I hear to ListenBrainz, then choose OK.
>
> **last.fm and Libre.fm.** In the same group, choose Sign In to last.fm (or
> Sign In to Libre.fm). Your web browser opens that service's own page, asking
> whether Quill Radio may scrobble for you. Sign in there if it asks and choose
> Yes, allow access. Then come back to Quill Radio and choose OK in the box that
> is waiting. You type your password on the service's page, never into Quill
> Radio. Then check Send the songs I hear to last.fm (or Libre.fm) and choose
> OK. To sign out, choose the Sign In button again; it offers to sign you out.
>
> If Sign In says it needs an API key, this copy of Quill Radio did not come
> with one. Choose Get a last.fm API Account, make a free account there, and
> paste its API key and shared secret into the two boxes above the buttons.
> Libre.fm uses the same pair.
>
> **What counts as heard.** A song counts once you have heard a minute of it.
> last.fm's own rule is half the song or four minutes, but that needs the
> song's length, and radio stations almost never send one. If you pause or
> rewind with the time-shift buffer, the song counts when you actually hear
> it, and the time you were paused does not count. The station's own name,
> "Live", adverts, and titles with no artist are never sent.
>
> If the internet drops or a service is busy, the songs wait and are sent
> later, for up to two weeks. If a service stops accepting your sign-in, Quill
> Radio tells you once, and the songs wait until you sign in again. Nothing is
> sent in Safe Mode.

## PRD text (to add)

> - **Scrobbling (2026-11-07; `core/radio/scrobble_tracker.py`,
>   `scrobble_queue.py`, `scrobbling.py`, `listenbrainz.py`, `lastfm.py`,
>   `ui/radio/scrobble_commands.py`, `scrobble_signin.py`).** From BlindRadio
>   by serrebidev (MIT). ListenBrainz (user token), last.fm and Libre.fm
>   (desktop sign-in through the browser), each off by default. A song counts
>   after a minute heard, because radio gives no length for last.fm's
>   half-or-four-minutes rule. The playhead, not the broadcast, is the clock:
>   time-shifted listening counts when heard, a pause adds nothing. Fed from
>   the `record_song` choke point; a 5-second timer runs only while a song is
>   followed. Failed scrobbles wait in a capped on-disk queue (500 per
>   service, 14 days, backoff to an hour); a lost sign-in is said once.
>   Tokens and session keys live in the credential store. The last.fm app key
>   ships as a gitignored build-time module (`tools/generate_lastfm_api_key.py`)
>   and the listener's own pair wins. Egress: `scrobble_http.py::post`.
> - **AudD recognition (2026-11-07; `core/radio/audd.py`).** From BlindRadio
>   by serrebidev (MIT). A second service for Identify This Song, chosen in
>   Preferences; AcoustID stays the default. Sends a 20-second clip from the
>   playing buffer with the listener's own token, only on the command; the
>   answer maps into AcoustID's `Match`. Egress: `audd.py::_post`.

## CHANGELOG line

> - Quill Radio: scrobble the songs you hear to ListenBrainz, last.fm or
>   Libre.fm (off until you turn it on and sign in), and choose AudD instead of
>   AcoustID for Identify This Song with your own token. Both ideas come from
>   BlindRadio by serrebidev.

## Third-party notice text

No BlindRadio code or data was copied, so no MIT notice is strictly required.
If the integrator wants the credit there too:

> Quill Radio's scrobbling and AudD recognition follow ideas from BlindRadio,
> Copyright (c) 2026 serrebidev, MIT License,
> https://github.com/serrebidev/blindradio.

## Tests and gates run

- New tests (60) plus the existing Identify This Song, song recognition,
  preference-group, resume-preference and network-egress audit tests: 166
  passed (`python -m pytest <those files> -q`).
- `ruff check .` and `ruff format --check` clean; `mypy` on the new
  `quill/core/radio` modules clean.
- `python -m quill.tools.data_format_audit`: `radio.history` recorded as an
  additive, compatible change (four new optional keys).
- **Not run, at the coordinator's request:** `python -m quill.tools.platform_report`
  and the full radio suite. Gates most likely to need a look after the merge:
  dialog inventory and F1 help audit (no new dialog classes; the rows are in
  the shared Preferences dialog, which sets `SetHelpText` on every control),
  surface reachability (`scrobble_signin` shows only message boxes),
  settings documentation inventory, and module size (`radio_preferences.py`
  is 564 lines, under the 600 default cap).

## Not done or not verified

- **No live request was made** to ListenBrainz, last.fm, Libre.fm or AudD; all
  behaviour is checked against hand-written fixtures from the official docs.
  The first real sign-in and scrobble should be tried by hand with a test
  account, ideally under JAWS and NVDA, including the "come back and choose
  OK" box.
- The application has not been registered with last.fm; until it is, the
  listener must paste their own API key and secret.
- AudD's exact error JSON (`{"status":"error","error":{"error_code":...}}`) is
  from memory of the API and the docs' error list; worth one live check with
  a wrong token.
- The AudD clip is the raw stream data mpv's `dump-cache` writes (MP3, AAC or
  Ogg, depending on the station), sent as `application/octet-stream`. AudD
  accepts common formats, but an HLS station's dump has not been tried.
- Time-shift is read from the mpv engine. On the classic engine there is no
  time-shift, so the playhead is live, which is right. The engine-title
  fallback (mpv `media-title`) may already describe the playhead rather than
  live when shifted; then a shifted song would count late, never wrongly.
- Retries happen only while a station is playing (the timer stops when nothing
  plays); songs queued at exit are sent the next time a station plays.
- The internet radio inside QUILL (the editor) runs the same hook, since it
  shares `song_history_commands.record_song`, but QUILL has no Preferences
  rows for scrobbling. It scrobbles only if its `RadioHistory` has a service
  turned on; I did not check whether that is the same file Quill Radio writes.
