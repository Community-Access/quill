# What the Station Played: song history from a station's own playlist

Branch `feat/br-hist`, 2026-11-07. The idea, the endpoint list and the edge cases come from
BlindRadio by serrebidev (MIT), `crates/blindradio-core/src/sources/played.rs` and
`docs/radio-sources-research-2026-11-04.md`. No code was copied; every parser was written
against live answers fetched by hand on 2026-11-07, and the test fixtures are cut down from
those answers.

## What was built

- `quill/core/radio/station_playlist.py` (wx-free, strict-typed): `match_source(stream_url)`
  picks the published-playlist source from the stream address only (host and path, never the
  station name), `fetch_station_playlist(stream_url)` asks it and returns the songs newest
  first. One egress site, `_fetch`: HTTPS only, verified TLS, 12 s timeout, 2 MB cap, Safe
  Mode refused. A 404 or 410 is "no list", not a failure.
- `quill/core/radio/station_playlist_parsers.py`: one pure parser per source, `PlayedSong`,
  `parse_time`. Split from the above for GATE-11.
- `quill/core/radio/radio_paradise.py`: `PLAYLIST_CHANNELS` and `playlist_channel(url)`, the
  stream-name to `chan` table, beside the channels it already knew.
- `quill/ui/radio/station_playlist_commands.py`: the `radio.station_playlist` command.
- `quill/ui/radio/station_playlist_dialog.py`: the window (modal `wx.Dialog`).
- Playback menu row (after Song History and Lyrics), command palette entry, F1 purpose.

Sources and how each is matched:

| Source | Stream address | Asks |
| --- | --- | --- |
| AzuraCast | any host, path `/listen/<shortcode>/<file>` | `https://<host>/api/nowplaying/<shortcode>`; kept only when `station.shortcode` matches |
| KEXP | `kexp*.streamguys1.com`, `live-*.kexp.org` | `api.kexp.org/v2/plays/?limit=50&ordering=-airdate`; airbreaks skipped |
| BBC | `as-hls-??-live.akamaized.net`, `*.bbci.co.uk`, `*.bbcmedia.co.uk`; first `bbc_...` path segment | `rms.api.bbc.co.uk/v2/services/<id>/segments/latest?limit=10`; music segments only |
| Radio Paradise | `stream.radioparadise.com` | `nowplaying_list_v2022?chan=N&list_num=50` |
| Live365 | `streaming.live365.com/<a12345>` | `api.live365.com/station/<id>`; `current-track` then `last-played`, Live365's own ad breaks skipped |
| laut.fm | `stream.laut.fm/<name>`, `<x>.stream.laut.fm/<name>` | `api.laut.fm/station/<name>/last_songs` |
| Triton | `*.streamtheworld.com`; mount is the last path segment's stem | `np.tritondigital.com/public/nowplaying?mountName=..&numberToFetch=50&eventType=track`, trying the mount, then without `_SC`, then without `AAC` |

Notes on the existing modules: `laut_fm.py` did not read `last_songs`, and `triton.py` parses
mounts from player pages, not stream URLs, so neither had code to reuse beyond
`live365.live365_station_id`, which is reused. AzuraCast is asked over HTTPS whatever the stream
used. BBC times arrive only as phrases ("3 Minutes Ago"); rows show the phrase, not an invented
clock time. A Radio Browser relay of a BBC stream on a bare IP is deliberately not matched.
Online Radio Box, Airable and vTuner were not added.

## Keys added

- `radio.station_playlist`: Alt+Shift+H in Quill Radio (`APP_KEYMAPS["radio"]`). Free on the
  Radio bar (checked by walking the real menu bar); H pairs it with Song History's Ctrl+Shift+H.
  Menu label "What the Station Playe&d..." on Playback. Not on QUILL's embedded radio menu (see
  below); reachable there from the command palette.

## Settings added

None.

## Egress rows added

- `core/radio/station_playlist.py::_fetch` in `quill/tools/network_egress_entries_radio.py`.

## User-guide text (Quill Radio, after the Song History section)

### What the Station Played

Song History is what Quill Radio heard while you listened. Many stations also publish their
own list of what they played, with the time each song started, and that list goes back further
than you have been listening. Press Alt+Shift+H, or choose Playback, What the Station Played,
to see it for the station you are on.

Quill Radio works out from the station's stream address whether it publishes such a list. It
can read the lists from KEXP, the BBC, Radio Paradise, Live365, laut.fm, stations streamed by
Triton Digital (StreamTheWorld), and stations run on AzuraCast. If the station is not one of
those, Quill Radio says so and asks nobody anything.

The list opens newest first. Each song says when it started, or "playing now" for the one on
the air; the BBC only says how long ago, so its songs read "3 minutes ago". Below the list,
"Where this list comes from" names who published it. From a song you can Copy it, Send it to
the Clip Library, look up Song Details or find its Lyrics, the same as in Song History.

Nothing is fetched until you ask, and it is off in Safe Mode.

## PRD text (Quill Radio PRD, song history section)

**What the Station Played (radio.station_playlist, Alt+Shift+H).** A station's own published
playlist, beside Song History and never merged with it. The source is chosen from the stream
URL only, by exact host and path pattern, never by station name: AzuraCast
(`/listen/<shortcode>/`, answer kept only when its shortcode matches), KEXP, BBC (service id
from the stream path, ten rows, relative times kept as phrases), Radio Paradise (channel from
the stream name), Live365, laut.fm and Triton (mount tried as given, without `_SC`, then
without `AAC`). One user-initiated GET on the task manager, HTTPS only, 12 s timeout, 2 MB cap,
refused in Safe Mode. The window states its provenance and offers Copy, Send to Clip Library,
Song Details and Lyrics through Song History's own code. A station with no published list is
told so in one sentence with no request made. Idea and endpoint list from BlindRadio by
serrebidev (MIT).

## CHANGELOG line

- Quill Radio: Playback > What the Station Played (Alt+Shift+H) shows the station's own
  published playlist, with start times, for KEXP, BBC, Radio Paradise, Live365, laut.fm,
  Triton/StreamTheWorld and AzuraCast stations. Idea from BlindRadio by serrebidev.

## Third-party notice text

No code or data was copied, so no licence text is required. Suggested acknowledgement line:
"The station-playlist sources in Quill Radio follow BlindRadio by serrebidev
(https://github.com/serrebidev/blindradio, MIT, Copyright (c) 2026 serrebidev)."

## Tests

- `tests/unit/core/radio/test_station_playlist.py`: matching (positive and negative),
  Triton mount normalisation, time formats, every parser from hand-written fixtures in
  `tests/unit/core/radio/fixtures/station_playlist/`, the fetch loop with `_fetch` faked.
- `tests/unit/ui/test_radio_station_playlist.py`: the command end to end against a host
  double (nothing playing, no source, Safe Mode, success, empty, failure), the window's
  Copy / Clip Library / Song Details / Lyrics, row labels, key, palette and F1.
- `tests/unit/ui/test_radio_lyrics_wiring.py` updated for the third Playback row.

## Not done or not verified

- Not on QUILL's own embedded radio menu (`main_frame_menu.py`, where Song History ships
  unbound); the command palette reaches it there. The integrator may want a menu row.
- The window is modal, not a peer window like standalone Song History. Lyrics opened from it
  shows its window behind the modal one until it closes, as Song History's modal form does.
- No in-window Refresh, and no "search" action: Song History has none to reuse.
- No live JAWS or NVDA check.
- Gates: `platform_report` and the long radio suite were not run (skipped at the
  coordinator's request; the integrator runs them). Regenerated on this branch: keyboard
  reference, F1 help reference, radio help inventory, dialog inventory, surface reachability.
  The menu-accelerator gate for Radio timed out once while building the frame on a busy
  machine (a hang in `tree.SetFocus`, not an assertion); Alt+Shift+H was checked free by
  walking the real Radio menu bar before it was added. Re-run
  `tests/unit/ui/test_menu_accelerators.py` after merging.
- Triton coverage depends on the station: news and talk mounts (KUOW, for one) answer an
  empty list, which the window reports as "lists no recent songs right now".
