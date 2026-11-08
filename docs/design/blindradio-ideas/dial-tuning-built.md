# Dial tuning: what was built

Built on `feat/br-dial` on 2026-11-08, to the design agreed with Jeff on 2026-11-07
(`docs/design/blindradio-ideas/dial-tuning.md`). The idea comes from BlindRadio by
serrebidev (MIT), github.com/serrebidev/blindradio, doc/readme.md "Dial tuning" and its
"FM Sound Between Stations" setting. No BlindRadio code, data or audio was copied.

## What was built

- **The policy**, wx-free and strict-typed: `quill/core/radio/dial_tuning.py`. Which
  rows tune, the settle timer (with held-arrow detection), neighbour selection, the
  metered stop, the recording pause, the dead-station timer, and the "passing through"
  question every bookkeeping hook asks. Driven by an injected clock.
- **The hiss**: `quill/core/radio/dial_hiss.py` synthesizes a two-second loopable clip
  from a seeded generator, cross-faded at the seam, in two fixed levels. The shipped
  files are `quill/assets/audio/dial_hiss_low.wav` and `dial_hiss_medium.wav`; a test
  checks them byte for byte against the code. Played by
  `quill/ui/radio/dial_hiss_player.py` through `winsound` (an async loop on a file).
- **Warm neighbours**: `quill/ui/radio/dial_warm_pool.py`. At most two muted mpv
  players beside the main one, made once and reused. Promotion hands a warm engine to
  the controller and gives the controller's old engine back to the pool.
- **The glue**: `quill/ui/radio/dial_tuning_ui.py` (one `DialTuningUI` per app, on the
  controller as `_dial_tuning`), list hooks for the Favorites tree, the Browse
  Stations tree (window and main view) and Search Stations' results list.
- **Commands and menu**: `quill/ui/radio/dial_tuning_commands.py`. Playback menu rows,
  command palette entries, and Go to Playing Station.
- **Preferences**: `quill/apps/radio_preferences_dial.py`, a "Tune as I move through
  stations" box. The shared `PreferenceChoice` gained `after_checks` so a box can lead
  with the check box that switches the rest on.

### Behaviour, as built

- Ships off (`dial_tuning = False`). Every part is a setting.
- Tunes only in Favorites (main window, and Browse's Favorites branch), Browse folders
  of stations, Networks and Search Stations' results. Never a folder, a podcast or
  episode (`is_recording`), YouTube, Spotify, Local Media, TV, the on-demand Browse
  sources (Apple, Podcast Index, Archive, LibriVox, Gutenberg, AudioPub, Audius,
  Mixcloud, ccMixter), or a row that has to be resolved over the network first
  (TuneIn, Apple).
- Focus must rest on a station row for the chosen wait. Rows arriving less than 150 ms
  apart are a held key: nothing plays until it stops, even with Instant (Instant does
  play the first press, and the first repeat after the keyboard's repeat delay, because
  a key-up is not visible to the app).
- Only when the list itself has focus: a row selected by code (a reload, Go to Playing
  Station) never tunes.
- Nothing is spoken on a move (GATE-13); the reader reads the row. While a station is
  only passed through, the player's connecting, playing and error earcons are quiet
  (`RadioPlayerController.dial_quiet`), its "Could not play" sentence is not spoken, and
  its RadioBrowser click is not sent.
- Enter on the tuned station commits it: a fresh connection (so a fresh time-shift
  buffer, with the station's own buffer length), Recently Played, Song History,
  Listening Statistics and scrobbling from then on, and "Playing <station>." as every
  other Play says. Enter on any other row does what it always did.
- Stations only passed through are not added to Recently Played, Song History,
  Listening Statistics or scrobbling, and their volume is not written to the favorite.
- Leaving the list keeps the station playing and lets the neighbours go. A settle still
  pending when focus leaves is cancelled.
- While a recording runs, moving tunes nothing, and "Tuning as you move is paused while
  you record. Press Enter to play a station." is said once, the first time you move.
- A dead station: the hiss stops at once when the connection fails, or after 5 seconds
  with no audio; 3 seconds later "<station> is not answering." is said once.
- At most three mpv players. Neighbours are warmed only once the current station is on
  the air (moving quickly opens nothing), after-first, and let go when they stop being
  neighbours, when the station fails, when focus leaves the list, when playback moves
  on outside the dial, or when the feature is turned off. They are muted, carry no
  Sound Enhancements graph, buffer in memory only (no disk, no cache sweep), and are
  never recorded.
- Promotion keeps the main player's output device, volume (with Volume Boost), Sound
  Enhancements graph, per-station enhancement override, the station's time-shift length
  (configured; it applies from the next load, which is what Enter does) and resets the
  song marks. It is used only when the controller is on mpv with no exact-OptiLab relay;
  otherwise the ordinary play path runs.
- The hiss plays at a fixed level during a dial connect, including the reconnect after
  Enter. Mute silences it.
- "Remember each station's volume while tuning" is off by default: tuned stations,
  and the commit after Enter, keep the volume you are hearing. On, each comes in at its
  own remembered level. Quill Radio's existing per-favorite volume memory is unchanged
  for every other play.
- Teardown on exit: `run_radio_shutdown` stops the hiss and terminates every warm
  engine before the player.

## Keys added

| Key | Command | Menu |
|---|---|---|
| Alt+Shift+U | `radio.dial_tuning`, Tune as I Move Through Stations (check item) | Playback |
| Alt+Shift+P | `radio.go_to_playing_station`, Go to Playing Station | Playback |

Both live in `quill.core.radio.dial_tuning.DIAL_KEYS`, spread into
`APP_KEYMAPS["radio"]`. Both are on the command palette.

## Settings added

All on `RadioHistory` (`radio_history.json`), all in Preferences under "Tune as I move
through stations". The data-format gate recorded the shape change as additive and
compatible.

| Field | Default | Preferences row |
|---|---|---|
| `dial_tuning` | False | Tune as I move through stations |
| `dial_keep_neighbours` | True | Keep the next and previous stations connected |
| `dial_metered_stop` | True | Stop keeping them connected on a metered connection |
| `dial_hiss` | True | Play a soft hiss between stations |
| `dial_remember_volume` | False | Remember each station's volume while tuning |
| `dial_wait_ms` | 350 | Wait before tuning: Instant, 200 ms, 350 ms, 500 ms, 1 second |
| `dial_hiss_level` | "low" | Hiss level: Low, Medium |

Metered detection reuses `quill/core/net_metered.py` (WinRT `NetworkCostType`); an
unknown answer is treated as not metered, and the answer is cached for 30 seconds.

## Network egress

No new destination and no new egress call site. Warm neighbours open the same station
stream URLs the player already opens, through mpv (which the AST audit does not see,
as for every radio stream). They are opened only after the listener has turned dial
tuning on, only for the two stations either side of the one they rested on, and never
on a metered connection unless the listener allows it. For the integrator, a paragraph
for the manually documented section of `network_egress_audit.py` if wanted:

> `quill/ui/radio/dial_warm_pool.py::WarmPool.keep` -- dial tuning's warm neighbours:
> up to two muted mpv connections to the station streams either side of the one the
> listener rests on, the same URLs the player opens. Off by default (Preferences > Tune
> as I move through stations); not on a metered connection unless the listener
> unchecks that row; closed when they stop being neighbours.

## Third-party and own-asset notices

The hiss is QUILL's own generated asset. A `components.json` entry in the "fonts-sounds"
group, beside the page-turn sound:

- id `dial-hiss`, name "Dial tuning hiss (quill/assets/audio/dial_hiss_low.wav and
  dial_hiss_medium.wav)", version "generated by quill/core/radio/dial_hiss.py",
  licence MIT (QUILL project), Copyright (c) 2026 Jeff Bishop, what: "An original
  synthesized soft noise loop played between stations while dial tuning connects; no
  sampled audio is used.", products radio, delivery bundled.

BlindRadio's MIT notice is already in the notices; its entry can say the dial tuning
idea is used too (no code or data from it is in this feature).

## User guide text

For the Radio user guide, in the chapter on finding and playing stations, after the
time-shift sections:

> ### Tuning as you move through stations
>
> Quill Radio can play the station you stop on as you move through a list, the way
> turning a radio dial does. It is off until you turn it on, so your arrow keys work
> as they always have.
>
> 1. Press **Alt+Shift+U** (**Playback > Tune as I Move Through Stations**). Quill
>    Radio says it is on. Press it again to turn it off.
> 2. Arrow through your favorites, a Browse folder, Networks or your search results.
>    When you stop on a station for about a third of a second, it starts playing.
>    Holding an arrow plays nothing until you let go.
> 3. While a station connects you hear a soft hiss, like a dial between stations. If a
>    station does not answer, the hiss stops and Quill Radio tells you, once.
> 4. Press **Enter** on the station you want to stay with. It plays for real: it starts
>    a fresh time-shift buffer and goes into Recently Played.
>
> Stations you only pass on the way are not added to Recently Played, Song History or
> Listening Statistics, and are not scrobbled. Podcasts, YouTube, audiobooks and
> folders never play as you move.
>
> When you leave the list, the last station keeps playing. Press **Alt+Shift+P**
> (**Playback > Go to Playing Station**) to come back to its row.
>
> While you are recording, moving does not change the station. Quill Radio says so the
> first time you move; press Enter if you do want to change it.
>
> Good to know:
>
> - To make the next step quicker, the stations either side of the one you are on stay
>   connected with the sound off. That uses up to two extra streams. On a metered
>   connection, such as a phone hotspot, Quill Radio does not do this.
> - Mute silences the hiss too.
> - Every part of this is in **Preferences**, under **Tune as I move through
>   stations**: how long to wait (Instant, 200 milliseconds, 350, 500, or a second),
>   whether to keep the next and previous stations connected and whether to stop on a
>   metered connection, the hiss and how loud it is (Low or Medium), and whether each
>   station you tune to comes in at its own remembered volume. That last one is off, so
>   the volume stays where it is as you move.
> - Keeping stations connected and the quick step need the mpv playback engine. With
>   Windows Media, stations still play as you move, each one connecting when you stop.
>
> Tuning as you move follows an idea from BlindRadio by serrebidev.

Add to the guide's key table: Alt+Shift+U, Tune as I Move Through Stations;
Alt+Shift+P, Go to Playing Station. Add to the Preferences section: the box and its
seven rows, as above.

## PRD text

Replace 31.6 "Dial tuning (designed, not built)" with:

> ### 31.6 Dial tuning (radio.dial_tuning, Alt+Shift+U)
>
> `quill/core/radio/dial_tuning.py`, `dial_hiss.py`, `quill/ui/radio/dial_tuning_ui.py`,
> `dial_warm_pool.py`, `dial_hiss_player.py`, `dial_tuning_commands.py`,
> `quill/apps/radio_preferences_dial.py`. Design: `docs/design/blindradio-ideas/dial-tuning.md`.
>
> - **R-DIAL-OFF.** Ships off; seven `RadioHistory` settings (`dial_*`), all in
>   Preferences under "Tune as I move through stations". Alt+Shift+U toggles and says
>   the new state.
> - **R-DIAL-ROWS.** Only live station lists tune: Favorites, Browse folders of stations,
>   Networks, Search results (Recently Played too, should it become a list; today it is
>   a menu). Never folders, `is_recording` rows, YouTube, Spotify, rows needing a
>   resolve, or the on-demand Browse roots (`ON_DEMAND_SOURCES`). Only while the list
>   has focus.
> - **R-DIAL-SETTLE.** Plays after the wait (default 350 ms); rows under 150 ms apart are
>   a held key and defer the tune.
> - **R-DIAL-QUIET.** Nothing spoken on a move. While passing through: no state earcons,
>   no failure sentence, no RadioBrowser click.
> - **R-DIAL-COMMIT.** Enter on the tuned station reconnects (fresh time-shift buffer)
>   and from then on it is an ordinary play. Passed-through stations are kept out of
>   Recently Played, Song History, Listening Statistics, scrobbling and per-favorite
>   volume.
> - **R-DIAL-WARM.** At most three mpv players. Up to two neighbours (after first),
>   warmed once the current station plays, muted, no filter graph, in-memory buffer,
>   never recorded; let go when no longer neighbours, on failure, on leaving the list,
>   on playback elsewhere, or when turned off; not on a metered connection when
>   `dial_metered_stop`. Promotion swaps engines and carries device, volume, Sound
>   Enhancements, time-shift length and a song-marks reset; only on mpv without the
>   exact-OptiLab relay.
> - **R-DIAL-REC.** While recording, moving tunes nothing; said once per recording.
> - **R-DIAL-DEAD.** Hiss stops on failure or after 5 s silent; "<station> is not
>   answering." 3 s later, once.
> - **R-DIAL-HISS.** Generated loop, two fixed levels, `winsound` on the default device;
>   Mute silences it.
> - **R-DIAL-GOTO.** Go to Playing Station (Alt+Shift+P) selects the playing station's
>   row in Browse (when it is the main view) or Favorites, else says it is in no list.

## CHANGELOG line

For the Radio changelog's "Ideas from BlindRadio" list (and QUILL's, if it carries the
list):

> - **Tune as you move through stations** (Alt+Shift+U, 2026-11-08). Off until you turn
>   it on. The station you stop on in Favorites, Browse, Networks or Search plays after
>   a moment, with a soft hiss while it connects; the stations either side stay
>   connected so the next step is quick. Enter keeps the station; stations you only
>   pass are not added to Recently Played or Song History. Go to Playing Station
>   (Alt+Shift+P) finds its row again. Every part is in Preferences.

The opening line of that section says "Six things arrive together"; it becomes seven.

## Not done, or not verified

- **Not heard on a real machine.** Everything is tested with a fake engine pool, a
  fake hiss backend and a fake clock; nothing was run against libmpv, a real station,
  JAWS or NVDA. Worth a live check: the hiss level against speech, the loop seam by ear,
  promotion on a real mpv (no audible gap, the muted neighbour really silent), and how
  each screen reader reads the Preferences box.
- **The hiss plays on the default output device**, not the radio's chosen device, and a
  `winsound` earcon (only when sound_lib is absent) stops it.
- **Recently Played is a menu, not a list**, so it does not tune. The policy accepts a
  `recent` list kind for the day it becomes one.
- **Rows that must be resolved first** (TuneIn, Apple) never tune: tuning them would be
  a network round trip per row passed.
- **A station you rest on without pressing Enter** is never counted, however long you
  listen. An automatic commit after a dwell time is a possible follow-up; it was not in
  the agreed design, so it is not built.
- **Go to Playing Station** looks in Browse only when Browse is the main view, and in
  Favorites otherwise. It does not search Search Stations' results or a separate Browse
  window.
- **Instant** plays the first press and the first key repeat of a held arrow, because
  the app cannot see a key-up.
- The Quill Radio user guide, PRD, changelogs, What's New and third-party notices were
  not edited (by instruction); their text is above.
