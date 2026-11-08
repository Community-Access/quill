# Time-shift: song marks, adaptive cushion, per-station length

Branch `feat/br-shift`. Three ideas from BlindRadio by serrebidev (MIT,
Copyright (c) 2026 serrebidev), chosen in `docs/design/blindradio-review-2026-11-07.md`
(items 2, 3 and 6). No BlindRadio code was copied; the behaviour and the numbers
(15-second first-title rule, 3-second restart rule, cushion steps 3, 9, 15 and the
clean minute) come from its `segments.rs`, `stream.rs`, user guide and CHANGELOG 0.2.2.

## What was built

### 1. Song marks in the time-shift buffer

- `quill/core/radio/song_marks.py` (wx-free, strict): `SongMarks` keeps
  `(position, title)` marks on mpv's stream timeline. Blank and noise titles
  (`song_history.is_noise_title`, so "Live", "Advertisement" or the station's own
  name) mark nothing. A repeat of the title already at that point is no news. A
  second sighting of one title within 60 seconds moves the mark earlier, never
  later. A first title within 15 seconds of the buffer's start is marked at the
  start. Marks whose audio has left the buffer are pruned. `songs()`, `pick()`
  (previous, current, next, all) and `jump()` (Previous restarts a song more than
  3 seconds in, otherwise goes to the one before; Next past the last goes back to
  live) are pure.
- Two sources of titles, both feeding the same marks:
  - **mpv itself.** mpv's ICY and HLS metadata are timed: the demuxer files each
    title change with its timestamp and hands it over when playback reaches it
    (`demux/demux.c`, `add_timed_metadata`). So when the engine's title changes,
    `time-pos` is where that song starts. The engine checks once a second
    (`quill/ui/radio/mpv_live_extras.py`, every fifth 200 ms poll).
  - **The out-of-band title reader** (ICY tap, status page), through the one choke
    point `_radio_apply_track_title`. It describes the live edge, so it is marked at
    `demuxer-cache-time`; the merge rule keeps mpv's exact position when both report
    the same song.
- Marks are per session: the engine clears them on every load, so a station change
  (or a reconnect) starts a fresh list. The station name for the noise check is set
  before each load (`engine_selection.prepare_station`).
- Commands (`quill/ui/radio/song_marks_ui.py`, menu rows in
  `quill/apps/radio_timeshift_menu.py`, Playback menu right after Back to Live):
  - Previous Song, Next Song: seek to the song's start and say "Title by Artist.
    N minutes behind live." After the last song, Next does Back to Live ("Back to
    live."). At the edges: "This is the oldest song in the buffer." / "You are
    listening live; there is no next song yet."
  - Which Song Is This?: "Title by Artist, 50 seconds in, song 2 of 3 in the
    buffer. 1 minute 50 seconds behind live."
  - Playback > Save Songs from the Buffer > Save This Song, Save the Previous Song,
    Save the Next Song, Save All Songs in the Buffer. Each song goes to its own
    file in the recordings folder (Recording Settings' destination, or the default
    Quill Radio Recordings folder), named with the recorder's filename pattern for
    the station and the time the song went out, then " - " and the song as the
    song splitter names it (`recording_split.song_file_name`), made unique with the
    recorder's `uniquify`, so nothing is overwritten. The audio is copied out of the
    buffer with mpv's `dump-cache` exactly as the station sent it (no decode, no
    re-encode); the extension follows mpv's `audio-codec-name` (mp3, aac, opus,
    ogg, flac, anything else .mka). The dump runs on the task manager, so the window
    stays free. The song still playing is saved as far as it has got.
  - Refusals are spoken: nothing playing; the Windows Media engine (the existing
    "needs the mpv playback engine" sentence); a finished recording ("This is a
    recording, not live radio, so it has no song marks."); no marks yet.

### 2. Adaptive cushion

- `quill/core/radio/cushion.py` (wx-free, strict): `CushionPolicy` with a clock.
  Each underrun goes one step deeper (3, 9, 15 seconds); one clean minute after
  playback comes back restores the normal 1 second; time spent stalled is not
  clean; a new station resets it.
- mpv mapping: `cache-pause-wait`, the number of seconds the cache must hold
  before playback resumes after "buffering". Verified against mpv's sources:
  `player/playloop.c` reads `opts->cache_pause_wait` on every cache update, so
  writing the property takes effect at the next stall without a reload. The
  manual (`DOCS/man/options.rst`) confirms the semantics. `cache-secs` and
  `demuxer-readahead-secs` were considered and rejected: they limit read-ahead,
  and with the cache on Quill Radio already reads as far ahead as the byte cap
  allows, so raising them would change nothing.
- The trigger is the `paused-for-cache` edge the engine poll already watched for
  its buffering announcement. The engine writes `cache-pause-wait=1.0` on every
  load, because an option set at runtime survives a load.
- Nothing is announced. The existing buffering announcement already covers the
  stall; the cushion only makes the next stretch longer.

### 3. Per-station time-shift length

- `FavoriteStation.timeshift_minutes` (default -1, follow Preferences), stored in
  `radio_favorites.json` with the station's other per-station settings (volume,
  Sound Enhancements). Unknown or corrupt values follow Preferences.
- `timeshift.resolve_minutes`, `normalise_station_minutes`, `station_choices`,
  `label_for` (pure).
- `engine_selection.prepare_station` configures the engine with the station's
  length before every load (and on the engine-fallback path), which is when mpv
  reads `demuxer-max-back-bytes` and the disk-cache options.
- Playback > Time-Shift Length for This Station... (Alt+Shift+T) acts on the
  playing station's favorite, else the favorite selected in the tree, and offers
  "Same as Preferences (1 hour, on disk)" plus every length. A station that is
  not a favorite is told to add it first.

## Keys added (Quill Radio, `APP_KEYMAPS["radio"]`)

The rows live in `quill/core/radio/song_marks.SONG_MARK_KEYS` and are spread into
`APP_KEYMAPS["radio"]` with one line, because `app_keymaps.py` sat on the 600-line
default cap. It now has a budget entry of 602 (`_rebaseline_2026_11_07_song_marks`),
and `radio_menu_bar.py`'s budget came down from 639 to 629.

| Command | Key |
| --- | --- |
| Previous Song (`radio.previous_song`) | Alt+Shift+Left |
| Next Song (`radio.next_song`) | Alt+Shift+Right |
| Which Song Is This? (`radio.which_song`) | Alt+Shift+W |
| Save All Songs in the Buffer (`radio.save_all_songs`) | Ctrl+Alt+F5 |
| Save the Previous Song (`radio.save_previous_song`) | Ctrl+Alt+F6 |
| Save the Next Song (`radio.save_next_song`) | Ctrl+Alt+F7 |
| Save This Song (`radio.save_current_song`) | Ctrl+Alt+F8 |
| Time-Shift Length for This Station (`radio.station_timeshift`) | Alt+Shift+T |

BlindRadio uses Shift+F6/F7 and Ctrl+F5-F8. Here Shift+F6 is the status-bar
region key's reverse and Ctrl+F5/Ctrl+F8 were taken, so the saves keep
BlindRadio's order on Ctrl+Alt+F5-F8.

## Settings added

None in `Settings` or `RadioHistory`. One per-favorite field,
`timeshift_minutes`, in the favorites file.

## Egress rows added

None. Everything works on audio already buffered; no new connection.

## User guide text (add after "Rewinding live radio, and going back to live")

> ### Jumping between songs in the buffer
>
> While the time-shift buffer runs, Quill Radio marks where each song starts,
> every time the station sends a new title. Stations that name what they play are
> divided up with nothing to set. Announcements like "Live" or the station's own
> name mark nothing, so the song before keeps the time.
>
> - **Previous Song** (Alt+Shift+Left) goes back to the start of the song you are
>   in, or to the one before if it only just began.
> - **Next Song** (Alt+Shift+Right) goes on to the next one. After the last song it
>   goes back to live.
> - **Which Song Is This?** (Alt+Shift+W) tells you the song, how far into it you
>   are, and how far behind live.
>
> Each jump says the song and how far behind live you now are.
>
> **Playback > Save Songs from the Buffer** writes songs to their own files in your
> recordings folder: **Save This Song** (Ctrl+Alt+F8), **Save the Previous Song**
> (Ctrl+Alt+F6), **Save the Next Song** (Ctrl+Alt+F7) and **Save All Songs in the
> Buffer** (Ctrl+Alt+F5). Each file is named like a recording, with the station,
> the time the song played and its title, and an earlier file is never
> overwritten. The audio is kept exactly as the station sent it. The song still
> playing is saved as far as it has got, and the oldest song starts where the
> buffer does.
>
> Song marks need the mpv playback engine and a station that sends titles. The
> marks start again whenever you change station. A mark can be a second or two
> either side of the real change, and a title the station sends late is marked
> late.
>
> **A station of its own length.** Some stations are worth keeping five hours of,
> and some are not worth keeping at all. Play the station (or select it in your
> favorites) and choose **Playback > Time-Shift Length for This Station**
> (Alt+Shift+T). Pick a length, or **Same as Preferences** to follow the
> Time-shift buffer setting again. It takes effect the next time the station
> starts. Only favorites can keep their own length.

And in the "stutters" troubleshooting entry, or after the buffer paragraph:

> If a station keeps running dry and stuttering, Quill Radio waits a little longer
> before it plays again each time: three seconds, then nine, then fifteen, so you
> hear long clean stretches instead of a stutter every few seconds. After a
> minute without trouble it goes back to normal, and changing station starts
> fresh.

Keyboard table rows (guide's Appendix):

> | Previous song, next song in the buffer | Alt+Shift+Left / Alt+Shift+Right |
> | Which song is this? | Alt+Shift+W |
> | Save this, previous, next, all songs | Ctrl+Alt+F8 / F6 / F7 / F5 |
> | Time-shift length for this station | Alt+Shift+T |

## PRD text (Radio PRD, live time-shift section)

> **Song marks (R-TS-MARKS).** Every non-noise title change while the time-shift
> buffer runs marks the buffer. Sources: mpv's timed metadata (marked at
> `time-pos`) and the out-of-band title reader (marked at the live edge); two
> sightings of one title within 60 s keep the earlier position. Previous Song
> restarts a song more than 3 s in, else goes to the one before; Next Song past the
> last returns to live. Save This/Previous/Next/All write each song with mpv
> `dump-cache` (no re-encode) to the recordings folder, named by the recorder's
> pattern plus the song name, never overwriting. After a jump the app speaks the
> title and the distance from live and nothing else (GATE-13). Marks are cleared on
> every load. Idea: BlindRadio (MIT).
>
> **Adaptive cushion (R-TS-CUSHION).** On each `paused-for-cache` stall,
> `cache-pause-wait` steps 3, 9, 15 s; one clean minute restores 1 s; every load
> resets it. Not announced. Policy in `quill/core/radio/cushion.py`. Idea:
> BlindRadio (MIT).
>
> **Per-station length (R-TS-STATION).** A favorite may override the global
> time-shift length (`timeshift_minutes`, -1 follows Preferences); applied before
> each load. Idea: BlindRadio (MIT).

## CHANGELOG line

> - Quill Radio marks each song in the time-shift buffer: jump to the previous or
>   next song (Alt+Shift+Left/Right), ask which song you are in (Alt+Shift+W), and
>   save this, the previous, the next or every buffered song to its own file
>   (Ctrl+Alt+F5 to F8). Stations that keep running dry now refill a deeper cushion
>   (3, 9, then 15 seconds) and earn the normal one back after a clean minute. Each
>   favorite can keep its own time-shift length (Alt+Shift+T). Ideas from BlindRadio
>   by serrebidev.

## Third-party notice text

No code or data was copied, so no notice is strictly required. If the integrator
credits ideas in THIRD_PARTY_NOTICES, this is the line:

> Quill Radio's song marks, adaptive cushion and per-station time-shift length
> follow ideas from BlindRadio (https://github.com/serrebidev/blindradio),
> Copyright (c) 2026 serrebidev, MIT License. No BlindRadio code is included.

## Tests

- `tests/unit/core/radio/test_song_marks.py`: marking, noise skipping, merging,
  first-title rule, pruning, songs, pick and jump at every edge, offsets,
  extensions.
- `tests/unit/core/radio/test_cushion_policy.py`: steps, ceiling, clean minute,
  stalls not counting as clean, restart of the count, reset, with a fake clock.
- `tests/unit/core/radio/test_timeshift_per_station.py`: resolution, choices,
  favorites round trip, corrupt and pre-field files.
- `tests/unit/ui/test_radio_mpv_live_extras.py`: the engine side over a fake mpv
  client (timed title marks, once-a-second check, live-edge marks, pruning, load
  reset, cushion writes, seek and dump).
- `tests/unit/ui/test_radio_song_marks_commands.py`: every new handler, with a
  fake controller and fake mpv, including what is spoken, saves, refusals, the
  per-station dialog (accept and cancel), and the engine receiving the station's
  length.

## Not done or not verified

- Gates run here: the menu-accelerator gate (all 20 pass, including access letters),
  module-size budget, dialog inventory, surface reachability, keyboard reference,
  ruff and scoped mypy on the core modules. `platform_report` and the full radio
  suite were not run (the integrator runs them after the merge).

- Not heard live: no listening test against a real station with JAWS or NVDA.
  In particular the claim that mpv's title change arrives in step with the
  playhead comes from reading mpv's demuxer source; on a station whose ICY title
  lags its audio, marks lag the same way.
- While you are behind live, songs between you and the live edge are known only
  from the out-of-band title reader, which polls every 30 seconds, so those marks
  can be up to 30 seconds late until playback reaches them and mpv's own sighting
  moves them earlier.
- Saves are always in the station's own format. The recorder's chosen format
  (for example MP3 at a set bitrate) is not applied; re-encoding would mean an
  ffmpeg pass over each saved file.
- `dump-cache` of a very long span can briefly hold up mpv while it writes (mpv's
  manual says so). It runs off the UI thread, so the window stays responsive, but
  audio may hiccup while Save All writes a long buffer.
- The QUILL editor's Media > Internet Radio menu did not get the song commands;
  only Quill Radio did.
- The per-station length is reachable from the Playback menu only, not from the
  favorites tree's context menu.
