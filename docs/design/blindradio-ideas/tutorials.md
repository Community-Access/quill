# Tutorials for the BlindRadio ideas

Branch `feat/br-tutorials`. Six guided lessons in Quill Radio's Help > Tutorials
(Ctrl+Alt+F1) for the features on `feat/radio-blindradio-ideas`. The features
come from BlindRadio by serrebidev (MIT, Copyright (c) 2026 serrebidev); each
new lesson module credits the idea in its docstring and its closing paragraph.
No BlindRadio text was copied. Dial tuning is not covered; it is being built
separately.

## What was built

Three new content modules in `quill/core/radio/tutorials/`, wired into
`CATALOGUE` in `__init__.py`:

| Lesson (slug) | Track | Minutes | Steps | Module |
| --- | --- | --- | --- | --- |
| Go straight to a broadcaster, or a public station (`networks-and-iprd`) | Finding | 6 | 7 | `networks.py` |
| Ask the station what it played (`what-the-station-played`) | Living with it | 5 | 6 | `songs_on_air.py` |
| Keep a list of what you heard on ListenBrainz (`scrobble-to-listenbrainz`) | Living with it | 4 | 5 | `songs_on_air.py` |
| AcoustID or AudD: which one names the song (`choose-audd`) | Living with it | 3 | 4 | `songs_on_air.py` |
| Jump between songs, and save one (`jump-between-songs`) | Living with it | 6 | 6 | `time_shift.py` |
| Give one station a time-shift length of its own (`station-timeshift-length`) | Living with it | 3 | 4 | `time_shift.py` |

27 minutes and 32 steps added. New totals: **50 lessons, 330 steps, about 292
minutes** (was 44 lessons, 298 steps, 265 minutes).

Order: the Networks lesson sits after "Find stations by name, tag and country"
and before "Add a station nobody lists". The five living lessons sit after
"Sleeping, waking, and being left alone" and before "Shape the sound".

Commands named (all real ids, keys from `APP_KEYMAPS["radio"]`):
`radio.browse` (Ctrl+B), `radio.station_playlist` (Alt+Shift+H),
`radio.identify_song` (Ctrl+K), `radio.previous_song` (Alt+Shift+Left),
`radio.which_song` (Alt+Shift+W), `radio.next_song` (Alt+Shift+Right),
`radio.save_current_song` (Ctrl+Alt+F8), `radio.save_previous_song`
(Ctrl+Alt+F6, with Ctrl+Alt+F7 and Ctrl+Alt+F5 as literals),
`radio.station_timeshift` (Alt+Shift+T), `radio.toggle_playing_favorite`
(Ctrl+Shift+F), `radio.play_pause` (Ctrl+P). Preferences is written as the
literal Ctrl+, as the existing settings lesson does.

Step detection, using only the existing checks: `window:Browse Stations` when
Browse opens, `playing` when a station starts (Networks, What the Station
Played, both time-shift lessons), `favorite-added` for making a station a
favorite. What the Station Played and the Preferences window are modal, not
peer windows, so no window check is possible there, as with the other modal
surfaces. No new check ids were added.

The scrobbling and AudD lessons need no account: the token boxes are named and
left empty, and the last step offers Escape. The scrobbling lesson's note says
what OK with the check box on and no token says ("ListenBrainz is on, but there
is no user token yet.").

Generated: `standalone/radio/docs/tutorials.md` (by
`python -m quill.tools.build_tutorials_reference --app radio --write`), and its
`tutorials.html` and `tutorials.epub`, rendered with the same Pandoc invocation
and accessible template as `standalone/radio/scripts/render_docs.ps1`, for that
one file only. Pandoc 3.12.1 was used.

## Count text for the integrator

`standalone/radio/README.md`, line 21. Replace:

> 44 guided tutorials (Ctrl+Alt+F1)

with:

> 50 guided tutorials (Ctrl+Alt+F1)

`standalone/radio/docs/userguide.md`, "Learning by doing: the tutorials"
(about line 123). Replace:

> Quill Radio comes with 44 short guided lessons.

with:

> Quill Radio comes with 50 short guided lessons.

`standalone/radio/docs/userguide.md`, Chapter 16 "Tutorials" (about line 7188).
Replace:

> opens 44 guided lessons, 298 steps in

with:

> opens 50 guided lessons, 330 steps in

The historical counts in `announcement-3.0.md` and `release-notes-3.0.md` (41
lessons) describe that release and should stay. `docs/design/wordpress.md`'s
"44 lessons" is QUILL's own set, not Radio's.

## User-guide text to add (lesson pointers)

Chapter 6, the paragraph that starts "The **Finding something to listen to**
track". Replace its lesson list with:

> The **Finding something to listen to** track of the tutorials walks through
> all of this: **Wander the browse tree**, **Search every directory at once**,
> **Find a station by its web address**, **Find stations by name, tag and
> country**, **Go straight to a broadcaster, or a public station**, **Add a
> station nobody lists**, **The catalog on your own disk** and **When a station
> will not play**.

Chapter 4, at the end of "Jumping between songs in the buffer" (before "Saving
songs from the buffer" or after it):

> The tutorial **Jump between songs, and save one** walks through this, and
> **Give one station a time-shift length of its own** covers the length.

Chapter 5, at the end of "What the Station Played, step by step":

> The tutorial **Ask the station what it played** walks through this.

Chapter 5, at the end of "Choosing AudD instead of AcoustID":

> The tutorial **AcoustID or AudD: which one names the song** explains the
> choice without changing anything.

Chapter 5, at the end of the ListenBrainz steps in "Scrobbling":

> The tutorial **Keep a list of what you heard on ListenBrainz** shows you
> where everything is, and needs no account to follow.

## CHANGELOG line

> Six new guided lessons in Help > Tutorials: the Networks and IPRD branches,
> What the Station Played, jumping between songs and saving one, a time-shift
> length for one station, scrobbling to ListenBrainz, and choosing AudD for
> Identify This Song. There are now 50.

## PRD text

> The tutorial catalogue (`quill/core/radio/tutorials/`) teaches the BlindRadio
> features in six lessons: `networks-and-iprd` (finding track) and
> `what-the-station-played`, `scrobble-to-listenbrainz`, `choose-audd`,
> `jump-between-songs` and `station-timeshift-length` (living track). The
> scrobbling and AudD lessons are completable without an account.

## Keys, settings, egress

None added. No new commands, settings, network calls or check ids.

## Not done or not verified

- The "hear" lines were written from the code's announcement strings and the
  user guide; they were not checked against JAWS or NVDA live. Two are
  approximate: the Networks folder row (the exact wording of a channel count,
  written as "how many channels it holds") and the Preferences group controls
  (written as a screen reader would read a check box and an edit box).
- The Networks lesson tells the listener to arrow down to the branch; the tree
  order puts Networks about twenty rows down.
- The user guide and README were not edited; the text above is for the
  integrator.
