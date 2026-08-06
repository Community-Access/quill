# Quill Radio — the public standalone app (version 2.2.0)

Quill Radio is a screen-reader-first Internet-radio player that ships alongside
QUILL 1.0.0 as its own Windows program. It is the same radio engine QUILL uses,
run as a small standalone window: a favorites tree, one transport button, a
volume slider, and an arrow-navigable status bar. It plays live stations,
records them (now and on a schedule), keeps favorites in folders, and backs the
whole lot up.

This section is for a tester **who has never opened Quill Radio**. Finish
**Part 0** (`00-getting-started.md`) first so your screen reader is running and
you know the Pass/Fail boxes. Read §2–§3 of `README.md` for the scenario layout
and the Works / Surface-exact / Accessible axes.

Surface reference (command id + label + shortcut) is
`../../planning/signoff/SIGNOFF-radio.md`; the dialog list is the **RADIO
(public)** block of `../../planning/signoff/SIGNOFF-dialogs.md`. Quill Radio's
Weather menu is the same surface documented in `app-weather.md` — this section
only proves it is *present and reachable* here and cross-references that section
for the weather features themselves.

**Preconditions that gate whole scenarios (mark Blocked and say which):**

- **Network.** Live stations play over the internet. With no network, station
  playback, Browse/Search, and Radio Reading Services are **Blocked**.
- **FFmpeg.** Recording needs the bundled **FFmpeg**. A build missing it puts a
  spoken pointer to **Help ▸ Get FFmpeg…** in front of you instead of recording —
  if you cannot install it, mark the recording scenarios **Blocked**.
- **mpv / libmpv.** Live rewind/forward, Volume Boost, and per-app output-device
  routing need the **mpv** playback engine. On the classic Windows Media engine
  those announce a pointer to **Preferences ▸ Playback engine** instead — that is
  **N/A** for that engine, not a fail.

Common inputs used below: a **station name to search** (e.g. `jazz`), a scratch
folder you can write to for recordings and backups, and about an hour with
headphones.

---

## RADIO-01 — Launch Quill Radio for the first time

*What & why.* The first launch must open a real, focused, announced window with
no crash — and, being an appliance, it may come up already playing your last
station. This mirrors GS-04 for the standalone app.

**Before you start**
- QUILL 1.0.0 installed (system installer) or the portable folder extracted.
  Screen reader running (GS-01).
- Nothing else open. This is your very first launch, so nothing will resume yet.

**Do this**
1. Launch **Quill Radio**: from the **Start menu** press **Enter** on the
   **Quill Radio** entry, or run **`QuillRadio.exe`** in the portable folder.
2. Wait a few seconds for the window to appear. Do not click anything.
3. Listen to what takes focus. Press **Tab** once or twice to hear the first
   controls.

**You should see and hear**
- A window titled **Quill Radio** opens and **comes to the foreground**; there is
  **no crash or error dialog**. The screen reader announces the window.
- Keyboard focus lands on the **Favorite stations** tree (announced as a tree
  view). A first launch has none yet, so it is empty. Near it are a **Now
  playing** line reading **"Radio: stopped"**, a **Play (Ctrl+P)** button, an
  **Add to Favorites** button (disabled while nothing plays), a **Record**
  button, a **Browse Stations…** button, and a **Volume, percent** slider.
- Press **Alt** — the menu bar opens (Station, Playback, and, unless gated off,
  Record and Weather, then View, QuillVille, Quillins, Window, Help). The first
  **Alt** opens the app menu, not the window's system menu.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-02 — Get your bearings: the Quill Radio window

*What & why.* Later scenarios say "focus returns to the favorites tree" or "check
the status bar." Learn those places now so the rest of the section makes sense.

**Before you start**
- Quill Radio open (RADIO-01), nothing playing.

**Do this**
1. Press **F6**. It moves focus into the **status bar** along the bottom; press
   **F6** again to hand focus back to the favorites tree (it says **"Returned to
   favorite stations"**).
2. Press **Alt**, then **Right Arrow** across the whole menu bar once, just to
   hear the menu names. Press **Escape** to leave the menu bar.
3. **Tab** through the main panel: Favorite stations tree, Play button, Add to
   Favorites button, Record button, Browse Stations button, Volume slider.

**You should see and hear**
- **F6** toggles between the favorites tree and the named **Status bar**; each is
  announced. The menu bar lists the expected menus. Every control in the panel is
  reachable by **Tab** with a spoken name (the Play button reports its
  Ctrl+P shortcut). Escape from the menu bar returns you to the tree.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-03 — Browse Stations (`radio.browse`, Station ▸ Browse Stations…)

*What & why.* The search-free way to wander every source — each source is a
branch you expand to reveal its stations. This is the "just show me what's on"
view and the fastest path to your first favorite.

**Before you start**
- Quill Radio open; network available (else **Blocked**).

**Do this**
1. Press the **Browse Stations…** button, or **Station menu (Alt, S) ▸ Browse
   Stations…**.
2. In the **Stations (expand a source to browse it)** tree, arrow to a source
   (e.g. **Popular Stations** or **SomaFM**) and press **Right Arrow / Enter** to
   expand it; wait for it to load.
3. Arrow onto a station and press **Enter** (or the **Play** button) to play it.
4. Press **Add to Favorites**. Then try the **Find in this folder** field: type a
   word and press **Enter**.
5. Press **Escape** or **Close**.

**You should see and hear**
- The tree is announced ("Station sources; expand one to browse its stations,
  Enter plays, Shift+F10 opens all actions"). Expanding a source says
  **"Loading…"** then **"N item(s)."** A read-only **details** area reflects the
  highlighted station.
- Enter/Play announces **"Playing {station}"**; the **Play** button flips to
  **Stop** for the playing station; Add to Favorites says **"Added {name} to
  Favorites"** (and toggles to Remove from Favorites). Find says **"N match(es)
  in {folder}."** **Shift+F10** opens Play/Stop, Add/Remove Favorites, Copy
  Stream Link, Open Website, Report Bad Station.
- **Close leaves the station playing** and says **"Exited Browse Stations"**;
  focus returns to the button/menu that opened it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-04 — Search Stations (Station ▸ Search Stations…)

*What & why.* The field-based finder: search by name, tag/genre, and country,
then play or favorite a result — for when you know what you're looking for.

**Before you start**
- Quill Radio open; network available (else **Blocked**). Search term: `jazz`.

**Do this**
1. **Station menu ▸ Search Stations…**. Focus lands in the **Station name** box.
2. Type **`jazz`**; optionally Tab to **Tag/genre** or **Country**; press the
   **Search** button (or Enter).
3. **Tab** to the **Station results** list; arrow through results, hearing each.
4. Press **Play**, then **Add to Favorites**. Try **More Stations** for the next
   page. Close with **Escape**.

**You should see and hear**
- Fields are labelled (Station name, Tag/genre (optional), Country (optional),
  default **"(Any country)"**). Search announces a summary: **"N station(s)
  found."** or **"No stations found. Try a different name, tag, or country."**
- The results list is announced with Name/Country/Format/Source columns; the
  details pane and a **Radio volume** slider + **Mute** toggle are present. Play
  says **"Playing {name}"**; favoriting says **"Added {name} to Favorites"**;
  More says **"Added N more; M stations now."** or **"No more stations."**
- Close says **"Exited Search Stations"** and leaves playback running.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-05 — Add Custom Station (`radio.add_custom_station`, Station ▸ Add Custom Station…)

*What & why.* Add a station the directories don't list, by pasting its stream
link — and test it before saving so you never save a dead link.

**Before you start**
- A direct stream URL you trust (staged in your notebook), e.g. an `http(s)://…`
  link ending in a stream. Name it **`My Test Station`**.

**Do this**
1. **Station menu ▸ Add Custom Station…** (also reachable as a button inside
   Browse/Search).
2. Type the **Station name** `My Test Station` and the **Stream URL**; optionally
   a **Homepage** and **Tags**.
3. Press the **Test** button and listen. Then press **OK** to save.

**You should see and hear**
- Labelled fields: Station name, Stream URL, Homepage (optional), Tags (optional,
  comma-separated), and a **Status** line. **Test** says **"Testing {name} —
  listen for it to start playing."** Missing fields report **"A station name and
  a stream URL are both required."**; a non-http URL reports it must start with
  `http://` or `https://`.
- **OK** saves the station (it appears in your favorites/list); **Cancel** /
  **Escape** discards with no change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-06 — Find Streams from a Website (`radio.find_streams`, Station ▸ Find Streams from a Website…)

*What & why.* Point Quill Radio at a station's web page and it fetches **that one
page** and scans it for playable stream links — nothing else is contacted.

**Before you start**
- A station's website address (staged). Network available (else **Blocked**).

**Do this**
1. **Station menu ▸ Find Streams from a Website…**.
2. Type the **Website address** and press the **Scan** button.
3. Arrow the **Candidates found** list; press **Test** on a candidate (it toggles
   to **Stop Test**). Press **Use This Link…** to hand it to Add Custom Station.
4. Close with **Escape**.

**You should see and hear**
- An intro states only that one page is fetched. After Scan, the status is
  announced: **"N candidate link(s) found."** or **"No stream-shaped links were
  found on that page."** or **"Could not scan that page: {error}"**. The
  Candidates list has **Link** and **Why it was flagged** columns. Test says
  **"Testing {name}"**; Stop Test says **"Test stopped"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-07 — Update Radio Reading Services (Station ▸ Update Radio Reading Services…)

*What & why.* Refresh the directory of Radio Reading Services (audio for people
who can't read print) from the network, then hear the new total.

**Before you start**
- Quill Radio open; network available (else **Blocked**). Note: in **Safe Mode**
  (`--safe-mode`) this is refused by design.

**Do this**
1. **Station menu ▸ Update Radio Reading Services…**.
2. Wait for the background refresh to finish.

**You should see and hear**
- It says **"Updating Radio Reading Services…"** then, on success, **"Radio
  Reading Services updated: N services."** A network failure comes back as
  **"Could not update Radio Reading Services. {reason}"** — never a silent
  failure. In Safe Mode it says the service is off and to restart without Safe
  Mode. (The services themselves then appear as a source in Browse Stations.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-08 — Import Stations from Playlist (Station ▸ Import Stations from Playlist…)

*What & why.* Bring a whole `.m3u`/`.m3u8` playlist of stations into your
favorites at once, choosing a folder and handling any duplicates.

**Before you start**
- An `.m3u` or `.m3u8` file with one or more stations, on disk.

**Do this**
1. **Station menu ▸ Import Stations from Playlist…**.
2. In the file dialog, pick your playlist and confirm.
3. In **Import Stations**, choose the **Target folder** (leave on **"(Top
   level)"** or type a new path like `News/Local`); confirm with **OK**.
4. If duplicates are found, choose whether to skip or import them.

**You should see and hear**
- The file dialog is keyboard-navigable. The target dialog offers a **Target
  folder** combo ("(Top level)" plus existing folders) and explains you can type
  a nested path. An empty playlist says **"No radio stations were found in that
  playlist."** Duplicates raise a choice ("Skip the N already in your favorites"
  vs "Import everything…"). On success it says **"Imported N stations into {the
  folder / your favorites}."** and the favorites tree updates.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-09 — Export Favorites to Playlist (Station ▸ Export Favorites to Playlist…)

*What & why.* Write your favorites out to an `.m3u` playlist to share or back up.

**Before you start**
- At least one favorite saved (do RADIO-03/05 first). A folder to write to.

**Do this**
1. **Station menu ▸ Export Favorites to Playlist…**.
2. In the file dialog, accept the default name **`quill-radio-favorites.m3u`** (or
   rename) and save.

**You should see and hear**
- A save dialog titled **"Export favorites to a playlist"** with an M3U filter. On
  success it says **"Exported N station(s) to {name}."**; a write error says
  **"Could not write the playlist: {reason}."** With no favorites yet, it says so
  ("You have no favorite stations to export yet…") instead of writing an empty
  file.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-10 — Play and Stop (`radio.play_pause` / `radio.stop`, Ctrl+P)

*What & why.* The core of a radio: start and stop a station. One button and one
menu item carry both — it reads **Play** when idle and **Stop** while playing.

**Before you start**
- At least one favorite saved. Network available (else **Blocked**).

**Do this**
1. In the favorites tree, arrow to a station and press **Enter** (or select it and
   press **Ctrl+P**, or the **Play** button, or **Playback menu (Alt, P) ▸ Play**).
2. Let it connect and play. Press **Ctrl+P** (or the button) again to **Stop**.

**You should see and hear**
- Playing announces **"Playing {station}"**; the **Now playing** line and status
  bar update from "Radio: stopped" to the station; the button and the Playback
  menu item both flip to **Stop**. Stopping says **"Radio stopped"** and the
  button returns to **Play**. With nothing selected it says **"No station
  selected. Add favorites from Browse Stations."** — never silence.
- Tray transport (RADIO-35) and the status-bar **Now playing** cell (RADIO-34)
  drive the same play/stop.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-11 — Volume up, down, and Mute (`radio.volume_up` / `radio.volume_down` / `radio.mute_toggle`)

*What & why.* Adjust Quill Radio's own volume — separate from your system volume
and your screen reader — and mute without losing the station. Volume is
remembered across restarts.

**Before you start**
- A station playing (RADIO-10).

**Do this**
1. Press **Ctrl+Up** a few times, then **Ctrl+Down** — from anywhere in the
   window except inside a text field. Or Tab to the **Volume, percent** slider and
   arrow it.
2. Press **Ctrl+M** (**Playback menu ▸ Mute/Unmute**) to mute, then again to
   unmute.
3. Stop, close Quill Radio, relaunch, and play again — confirm the volume is the
   level you left it.

**You should see and hear**
- Volume keys announce **"Radio volume {N}"**; the slider stays in step (arrowing
  it speaks the native percentage, no double-speak). Mute says **"Radio muted"**
  and unmute **"Radio unmuted"**. After a restart the **volume is remembered** at
  the same level (per-station memory may also apply).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-12 — Volume Boost (`radio.volume_boost`, Ctrl+Shift+B)

*What & why.* Push a quiet stream up to 50% past 100 for stations that are just
too soft — without changing the normal 0–100 scale.

**Before you start**
- A station playing on the **mpv** engine (Preferences ▸ Playback engine). On the
  classic engine this announces where to switch — that is **N/A**, not a fail.

**Do this**
1. Press **Ctrl+Shift+B**, or **Playback menu ▸ Volume Boost** (a checkable item).
2. Toggle it off again.

**You should see and hear**
- On the mpv engine: **"Volume Boost on: up to 50 percent louder."** and **"Volume
  Boost off."**; the menu check reflects the state. On the classic engine it says
  **"Volume Boost on. It takes effect on the mpv playback engine — check
  Preferences ▸ Playback engine."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-13 — Live DVR: Rewind, Forward, Back to Live (`radio.rewind` / `radio.forward` / `radio.jump_to_live`)

*What & why.* Pause and step back/forward within a live stream's buffer, then jump
back to the live edge — so you never miss a word. Needs the **mpv** engine.

**Before you start**
- A station playing on the **mpv** engine (else the commands announce where to
  switch — **N/A**, not a fail).

**Do this**
1. Press **Ctrl+Shift+Left** (**Playback menu ▸ Rewind 30 Seconds**).
2. Press **Ctrl+Shift+Right** (**Forward 30 Seconds**).
3. Press **Ctrl+Shift+L** (**Back to Live**).

**You should see and hear**
- Rewind says **"Rewound 30 seconds."** plus how far behind live (e.g. **"30
  seconds behind live."** / **"1 minute behind live."**). Forward says **"Forward
  30 seconds."** + position. Back to Live says **"Back to live."** With nothing
  playing, **"Nothing is playing."**; on the classic engine, **"Rewinding live
  radio needs the mpv playback engine — check Preferences ▸ Playback engine."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-14 — What's Playing: speak, review, copy, announce (`radio.whats_playing`, `radio.whats_playing_details`, `radio.copy_whats_playing`, `radio.toggle_title_announcements`)

*What & why.* Hear the current track on demand, open a reviewable/copyable window,
copy the text, and turn automatic track-title announcements on or off.

**Before you start**
- A station playing that carries track metadata (many music streams do).

**Do this**
1. Press **Ctrl+T** (**Playback menu ▸ What's Playing?**). This opens the
   reviewable **Now Playing** window.
2. In that window, arrow through the read-only text; press **Copy**; close with
   **Close** / **Escape**.
3. Back in the main window, toggle **Playback menu ▸ Announce Track Titles**.

**You should see and hear**
- Ctrl+T speaks/opens the current title (formatted per your What's Playing
  template, default `{title} by {artist}`), or fetches it if not yet known. The
  Now Playing window is a read-only text area named **"Now playing"** with a
  **Copy** button and a character count; **Copy** says **"Copied."** The Announce
  Track Titles toggle says **"Track titles will be announced as they change."** /
  **"Track title announcements turned off."** (Copy What's Playing, if bound,
  copies the same text silently to the clipboard.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-15 — Play Last Station (`radio.play_last`, Ctrl+L)

*What & why.* Instantly resume whatever was on last — radio as an appliance.

**Before you start**
- You have played at least one station this session or a previous one.

**Do this**
1. Stop playback. Press **Ctrl+L**, or **Station menu ▸ Play Last Station**.

**You should see and hear**
- The last station starts and it says **"Playing {station}"**. With an empty
  history it says **"Nothing in the radio history yet. Play a station first."**
  (The **Recently Played** submenu under Station lists recent stations and
  refreshes each time the menu opens.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-16 — Sound Enhancements (`radio.sound_enhancements`, Playback ▸ Sound Enhancements…)

*What & why.* A three-band EQ, "even out volume", channel mode, night mode, and
broadcast polish (OptiLab) — applied live to what's playing, per-station or as
the shared default. Needs **FFmpeg**.

**Before you start**
- A station playing. FFmpeg available (else the dialog says it needs FFmpeg).

**Do this**
1. **Playback menu ▸ Sound Enhancements…**.
2. Choose a **Quick preset** (Flat / Bass Boost / Voice Clarity / Podcast), or Tab
   through **Bass / Mid / Treble** sliders and arrow them; try **Even Out Volume**,
   **Channel mode**, **Night mode**, and the **OptiLab** box.
3. Press **OK** (or **Cancel** to revert). If a per-station override exists, try
   **Reset to Default**.

**You should see and hear**
- Each slider is named with its band and dB range; picking a preset says e.g.
  **"Voice Clarity: Bass +0, Mid +3, Treble +4."** Changes preview live as you
  move controls; **Cancel** reverts them. When editing a favorite's own override,
  **Reset to Default** says **"Sound Enhancements for {station}: back to the
  shared default."** Without FFmpeg the intro tells you to install it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-17 — Output Device (Playback ▸ Output Device…, Ctrl+Shift+D)

*What & why.* Send just the radio to a chosen sound card while your screen reader
and Quill Radio's own sounds stay on the system default. Needs **mpv**.

**Before you start**
- A station playing on the **mpv** engine (else a message points you to switch).
  More than one audio output helps you hear the difference.

**Do this**
1. Press **Ctrl+Shift+D**, or **Playback menu ▸ Output Device…**.
2. In **Output Device**, arrow the list and pick a device; confirm.

**You should see and hear**
- A single-choice dialog titled **"Output Device"** asking **"Send Quill Radio's
  audio to which device?"** On confirm it says **"Output device: {label}."** and
  the playing station moves to that device immediately; picking the same one says
  **"Output device unchanged: {label}."** On the classic engine a message
  explains device choice needs libmpv and where to switch.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-18 — Sleep Timer and Wake-Up Timer (`radio.wake_timer`, Playback ▸ Sleep Timer… / Wake-Up Timer…)

*What & why.* Fade the radio off after a set time (sleep), or have it turn itself
on at a set time to a chosen station (wake) — an alarm clock that plays radio.

**Before you start**
- At least one favorite (for the wake station). For the wake timer to actually
  fire, Quill Radio (or QUILL) must be running, the tray counts.

**Do this**
1. **Playback menu ▸ Wake-Up Timer…**.
2. Check **Wake up with the radio**; pick a **Station**; type a **Time** like
   `07:00` or `7:30 AM`; optionally **Every day**; press **OK**.
3. Separately open **Playback menu ▸ Sleep Timer…** and set a short duration to
   confirm it exists and is keyboard-operable.

**You should see and hear**
- Wake-Up Timer shows a current-setting summary, a **Wake up with the radio**
  checkbox, a **Station** choice, a **Time** field, and an **Every day** checkbox.
  A bad time says **'That time was not understood; try "07:00" or "7:30 AM".'**;
  no station says **"Pick a station first (add favorites from Browse Stations)."**
  On save it speaks the timer summary, or **"Wake-up timer turned off."** The
  Sleep Timer dialog is likewise labelled and keyboard-complete; the status bar's
  **Sleep timer** cell shows the countdown.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-19 — Record Now / Stop Recording (`radio.record_toggle`, Ctrl+Shift+Grave then 6)

*What & why.* Capture the station you're listening to, right now, to a file — and
stop it with the same command. **Needs FFmpeg** (else **Blocked**).

**Before you start**
- A station playing. FFmpeg available (else a message points to Help ▸ Get
  FFmpeg… — mark **Blocked**). A destination folder set (see RADIO-22).

**Do this**
1. Press the **Record** button, or **Record menu (Alt, R) ▸ Record Now / Stop
   Recording**, or the chord **Ctrl+Shift+Grave** then **6**.
2. Let it run a few seconds. Press it again to stop.

**You should see and hear**
- Starting says **"Recording started: {station}."** with an earcon; the **Record**
  button flips to **Stop Recording**; the status bar's Recording cell reads
  Recording. Stopping says **"Stopping recording…"** With nothing playing it says
  **"Nothing is playing to record. Start a station first."** Without FFmpeg it
  shows the **Get FFmpeg…** pointer instead of failing silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-20 — Record Station (`radio.record_station`, Record ▸ Record Station…)

*What & why.* Record station B in the background while you listen to A (or to
nothing), for a set number of minutes.

**Before you start**
- At least one favorite. FFmpeg available (else **Blocked**).

**Do this**
1. **Record menu ▸ Record Station…**.
2. Choose a **Station** from the list; set the **Duration (minutes)** with the
   spinner; press **Start Recording**.

**You should see and hear**
- A dialog explaining the recording runs on its own; a **Station** choice (your
  favorites, plus "{name} (now playing)" if applicable) and a **Duration** spinner
  (1–1440). With no station chosen: **"Pick a station first (add favorites from
  Browse Stations)."** On start it says **"Recording started: {station}, for N
  minutes."** and the recording runs in the background while playback is
  unaffected.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-21 — Schedule Recording (`radio.schedule_recording`, Record ▸ Schedule Recording…)

*What & why.* Set a recording to fire at a future time — once, daily, or weekly —
even while Quill Radio sits in the tray.

**Before you start**
- FFmpeg available. A favorite to record, or a station name + stream URL.

**Do this**
1. **Record menu ▸ Schedule Recording…**.
2. Fill the add form: pick a **Favorite station** (fills name + URL) or type
   **Station name** and **Stream URL**; choose **Repeats** (Once/Daily/Weekly),
   the **Day** (weekly) or **Date** (once, `YYYY-MM-DD`), a **Time** (`7:30 PM`
   or `19:30`), a **Time zone**, and **Duration** hours/minutes.
3. Press **Add Schedule**. Then select the new entry in the **Scheduled
   recordings** list and try **Edit**, **Duplicate**, **Disable/Enable**,
   **Remove**.

**You should see and hear**
- Every field is labelled and keyboard-complete. Adding says **"Scheduled
  recording added for {name}"**; editing **"Saved changes to {name}"**; removing
  **"Removed scheduled recording"**; disable/enable **"{name} disabled/enabled"**.
  Validation is spoken: a missing name/URL, a zero-length duration ("Set a
  recording length of at least one minute."), a bad time or date, or a past time
  ("Choose a date and time in the future.").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-22 — Recording Settings (`radio.recording_settings`, Record ▸ Recording Settings…)

*What & why.* Choose the recording format, quality, destination and temp folders,
filename pattern, length cap, concurrency, reconnect behavior, and whether Sound
Enhancements are baked into recordings.

**Before you start**
- Quill Radio open. A folder you can write to for recordings.

**Do this**
1. **Record menu ▸ Recording Settings…**.
2. Tab through: **Format**, **Quality (bitrate)**, **Destination folder** (+
   **Browse…**), **Temporary folder** (+ **Browse…**), **Filename pattern**,
   **Maximum recording length**, **Maximum simultaneous recordings**, the **If the
   connection drops** reconnect group, and **Apply Sound Enhancements to
   recordings**.
3. Set a destination folder; press **OK**.

**You should see and hear**
- Every control is labelled and reachable; the **Browse…** buttons open native
  folder pickers. The Quality control hides for lossless/raw formats. On **OK**
  it says **"Recording settings saved"** (Cancel/Escape discards). The filename
  pattern accepts `{station}`, `{date}`, `{time}`.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-23 — Recordings library (`radio.recordings`, Record ▸ Recordings…)

*What & why.* One place for every recording — made, in progress, and scheduled —
where you can play, stop, reveal, and delete them.

**Before you start**
- At least one finished recording (do RADIO-19). Optionally one in progress.

**Do this**
1. **Record menu ▸ Recordings…**.
2. Arrow the **Recordings** list (Name/Status/Size/When). Press **Enter** or
   **Play** on a finished one; **Stop Recording** on an in-progress one; **Open in
   Folder**; then **Remove…** and confirm.
3. Close with **Escape** (recordings continue).

**You should see and hear**
- The list is announced; the Status column reads **Recording / Recorded /
  Scheduled / Completed**; the status line summarizes counts and the folder. Play
  says **"Playing recording {name}"** (button flips to Stop); an in-progress row
  says **"Still recording; stop it first to play it."**; Open in Folder says
  **"Showing {name} in the file manager"**; Remove confirms ("Remove Recording"),
  then says **"Removed recording {name}"**. The list live-refreshes.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-24 — Stop All Recordings (`radio.stop_all_recordings`, Record ▸ Stop All Recordings)

*What & why.* End every running recording at once.

**Before you start**
- Two or more recordings running (start one with RADIO-19, another with
  RADIO-20). FFmpeg available.

**Do this**
1. **Record menu ▸ Stop All Recordings** (also on the Recordings dialog when ≥2
   run).

**You should see and hear**
- It says **"Stopping all N recordings…"** (singular "recording" for one), and
  the recordings then appear as **Recorded** in the library. With nothing
  recording it says **"Nothing is recording right now."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-25 — A scheduled recording fires while the app is in the tray

*What & why.* The whole point of scheduling is that it works unattended — even
with the window hidden in the system tray.

**Before you start**
- FFmpeg available. From RADIO-21, add a schedule set for **two or three minutes
  from now**, Once.

**Do this**
1. Send Quill Radio to the tray (**Ctrl+W**, or Station ▸ Send to Tray).
2. Wait past the scheduled time without touching the app.
3. Bring the window back (tray hotkey **Ctrl+Alt+Shift+R**, or double-click the
   tray icon) and open **Record ▸ Recordings…**.

**You should see and hear**
- The recording starts at its time while the app is in the tray (you may hear an
  earcon / spoken cue), and afterward it appears in the Recordings library as a
  finished **Recorded** file of about the scheduled length.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-26 — Resume interrupted recordings after a crash

*What & why.* If Quill Radio is killed mid-recording, the next launch should
offer to resume the interrupted capture rather than losing it silently.

**Before you start**
- FFmpeg available. Start a recording (RADIO-19), then **force-kill** Quill Radio
  (Task Manager ▸ End task) while it records. Optionally have two running for the
  batch case.

**Do this**
1. Relaunch Quill Radio.
2. Read the resume prompt that appears; choose **Resume** (or **Resume All**), or
   **Skip** / **Skip All**. Try the **Don't ask me again** checkbox once to see it.

**You should see and hear**
- For one interrupted recording, a **Resume Recording** dialog: "A recording of
  {station} was in progress… Resume it for the remaining N minute(s)?" with
  **Resume** / **Skip** and **Don't ask me again**. For several, a **Resume
  Recordings** dialog listing them in a review area with **Resume All** / **Skip
  All**. Resume continues the capture for its remaining time; the result lands in
  the Recordings library.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-27 — Add and remove favorites from the main page

*What & why.* Favoriting is a one-key toggle for whatever is playing, and the
favorites tree on the main page is where you live.

**Before you start**
- A station playing that is not yet a favorite (from Browse/Search).

**Do this**
1. Press the **Add to Favorites** button (it toggles to **Remove from
   Favorites**). Confirm the station appears in the tree.
2. In the tree, select the station and press **Enter** to play it; press
   **Delete** to remove it and confirm the prompt; press **F2** to rename.

**You should see and hear**
- Add says **"Added {station} to favorites"** (with an earcon); the tree updates;
  the button becomes **Remove from Favorites** and says **"Removed {station} from
  favorites"** when pressed again. In the tree, **Enter** plays ("Playing
  {station}"), **Delete** asks **"Remove {name} from your favorites?"** then
  **"Removed {name} from favorites"**, and **F2** renames via a "Rename Station"
  prompt ("Station renamed to {name}").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-28 — Reorder favorites, and confirm order survives a restart

*What & why.* You should be able to hand-arrange favorites and have that order
kept — reordering announces where the station landed, and it must persist.

**Before you start**
- At least three favorites in one folder (or at the top level).

**Do this**
1. In the tree, select a station and press **Alt+Shift+Down** to move it down,
   then **Alt+Shift+Up** to move it back. (Or use **Mark for Move** from the
   context menu: Shift+F10 ▸ Mark for Move, select a destination, then Move
   Marked Above/Below.)
2. Close Quill Radio and relaunch. Check the order is exactly as you left it.

**You should see and hear**
- Each move announces where it landed, e.g. **"Moved down, now below {station}"**;
  an edge move says **"Already at the edge of its folder."** If you were in an
  A–Z/Z–A sort, the first reorder says **"Switched to manual order."** and reveals
  (never destroys) your stored order. **After a restart the manual order is
  preserved.**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-29 — Manage Favorites (`radio.manage_favorites`, Station ▸ Manage Favorites…)

*What & why.* The full favorites workbench: search, play, remove, reorder, and
organize into nested folders in one dialog.

**Before you start**
- Several favorites saved, ideally in a couple of folders.

**Do this**
1. **Station menu ▸ Manage Favorites…**.
2. Type in **Search favorites** to filter; arrow the **Favorites and folders**
   tree; press **Play**; use **Move Up / Move Down / Move to Folder…**; try
   **Mark for Move** then **Move Above / Move Below**; **New Folder…**,
   **Rename…**, **Delete Folder…**, **Remove All…**.
3. Close with **Escape**.

**You should see and hear**
- A **Search favorites** box (filters names/countries/tags/folders), the tree
  ("Enter plays, Delete removes, Shift+F10 opens all actions"), a status line, and
  the two rows of buttons above. Play says "Playing {label}"; moves announce the
  landing ("Moved down, now below {neighbor}"); Mark says "Marked {label}. Select
  a destination…"; Remove All warns it keeps folders and saves a backup. Close
  says **"Exited Manage Favorites"** and keeps playback running.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-30 — Favorites folders: create, rename, move, delete, sort

*What & why.* Folders keep a big favorites list navigable. This walks the folder
prompts from the main-page context menu.

**Before you start**
- A few favorites at the top level.

**Do this**
1. In the tree, press **Ctrl+Shift+E** (or Shift+F10 ▸ New Folder…) — choose a
   location, then type a name like `News/Local`.
2. Select a station, Shift+F10 ▸ **Move to Folder…**, and file it into the folder.
3. On a folder, Shift+F10 ▸ **Rename Folder…** (F2), **Sort This Folder…**, and
   **Delete Folder…**.
4. Use **View menu ▸ Sort Favorites** (Ascending / Descending / Unsorted) and
   **Expand All / Collapse All Folders**.

**You should see and hear**
- New Folder says **"Created folder {path}. File stations into it with Move to
  Folder."** (or "A folder named {path} already exists."). Move to Folder says
  **"Filed {station} under {folder}."** Rename says **"Folder renamed to {name};
  N station(s) came along."** Sort This Folder is a choice (Follow the default /
  A→Z / Z→A / Unsorted) announced when set. Delete Folder reassures your stations
  are safe, then **"Folder {path} deleted; N station(s) moved to the top level."**
  View ▸ Sort Favorites announces the new order; Expand/Collapse say so.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-31 — Back Up and Restore stations & settings (`.qrbackup` round-trip)

*What & why.* Move Quill Radio to a new PC, or recover after a reinstall, by
backing up your stations, folders, and settings (and optionally recordings) to a
single `.qrbackup` file — and restoring it faithfully.

**Before you start**
- Some favorites, folders, and settings worth saving. A folder to write to.

**Do this**
1. **Station menu ▸ Back Up Stations and Settings…**. If you have recordings,
   answer whether to include them; then save the `.qrbackup` file.
2. Change something (remove a favorite, rename a folder).
3. **Station menu ▸ Restore from Backup…**; pick the `.qrbackup`; confirm the
   replace warning. Verify your favorites/folders are back exactly.

**You should see and hear**
- Backup: an include-recordings Yes/No/Cancel prompt (if any exist), a save dialog
  defaulting to `quill-radio-backup-{date}.qrbackup`, then **"Backing up Quill
  Radio."** → **"Backup saved to {name}."** (or a spoken failure). Restore: an
  open dialog, a confirm ("Restore N settings file(s)… This replaces your current
  stations and settings.") then **"Restoring Quill Radio…"** → **"Restored N
  settings file(s)…. Your stations are back."** The round-trip reproduces your
  favorites, folders, and settings.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-32 — Resume Last Station and Start with Windows (autostart)

*What & why.* An appliance turns on ready to go: optionally start with Windows and
resume the last station at launch.

**Before you start**
- Windows (autostart is Windows-only). A station you have played.

**Do this**
1. Toggle **Station menu ▸ Resume Last Station on Launch** on.
2. Toggle **Station menu ▸ Start Quill Radio with Windows** on. (Optionally sign
   out/in or reboot to confirm it launches — otherwise verify the menu check and
   the announcement.)
3. Close and relaunch Quill Radio; confirm the last station resumes.

**You should see and hear**
- Resume toggle says **"Quill Radio will pick up where you left off at launch."**
  / **"Resume on launch turned off."** Autostart toggle reflects what actually
  took: **"Quill Radio will start with Windows."** / **"…will not start with
  Windows."** (a locked-down registry may refuse — it reports the real state). On
  relaunch with Resume on, the last station is already playing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-33 — Missed-recording report on launch

*What & why.* If a scheduled recording's time passed while Quill Radio was closed,
the next launch should tell you it was missed — not swallow it silently.

**Before you start**
- FFmpeg available. From RADIO-21, add a **Once** schedule for a time **a couple
  of minutes from now**, then **close Quill Radio** and wait past that time.

**Do this**
1. Relaunch Quill Radio and listen during the first few seconds.

**You should see and hear**
- Shortly after the window comes up, a spoken one-line summary of the scheduled
  recording(s) missed while the app was closed. (An occurrence whose window is
  still open at launch is started late instead of reported missed.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-34 — The status-bar mini-player

*What & why.* The bottom status bar is a compact, arrow-navigable mini-player:
what's on, volume, recording, sleep timer, favorites count, and the time — each
cell does something on Enter.

**Before you start**
- A station playing. **View menu ▸ Show Status Bar** on.

**Do this**
1. Press **F6** to move focus into the **Status bar**.
2. **Left/Right Arrow** across the cells (Home/End jump to the ends); listen to
   each. Press **Enter** on a cell.
3. Try **Shift+F10** on the **Now playing** or **Volume** cell for its context
   menu. Press **Escape** to return to the favorites list.

**You should see and hear**
- Six cells, each announced as **"{name}, {value}"**: **Now playing** (station or
  "Stopped"; Enter opens full Now Playing details; menu has Play/Pause, Mute,
  Record), **Volume** ("{pct}%" / "Muted" / "{pct}% (boosted)"; Enter mutes; menu
  has Volume Up/Down, Mute, Volume Boost), **Recording** ("Idle" / "Recording" /
  "N recording"; Enter toggles record), **Sleep timer** ("Off" / "N min left";
  Enter opens the sleep dialog), **Favorites** ("N stations"; Enter jumps to the
  list), **Time** (clock; Enter speaks the full date/time). Escape says
  **"Returned to favorite stations."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-35 — Send to Tray, show/hide, tray hotkey and media keys (`view.toggle_window_to_tray`)

*What & why.* Quill Radio keeps playing from the system tray, and you can
show/hide it and drive transport by global hotkey and media keys without the
window in front.

**Before you start**
- A station playing.

**Do this**
1. Press **Ctrl+W** (**Station menu ▸ Send to Tray**) — the window hides, playback
   continues.
2. Press the **tray hotkey Ctrl+Alt+Shift+R** to bring it back; press it again to
   hide. (This is `view.toggle_window_to_tray`, also in Help ▸ Global Hotkeys….)
3. With the window hidden or focused, press your keyboard's **Play/Pause** and
   **Stop** media keys.
4. Right-click the tray icon and use its **Play / Pause** and **Stop** items.

**You should see and hear**
- Send to Tray says **"Quill Radio is still running in the system tray."** and
  playback keeps going. The tray hotkey shows/hides the window (a second launch of
  Quill Radio also just brings the running one forward — single instance). Media
  keys and the tray menu's Play/Pause and Stop drive the same transport and are
  spoken.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-36 — Close confirmation: Exit, Minimize to Tray, or Cancel

*What & why.* Closing while a station plays (or a recording runs) must not silently
kill it — you get a spoken choice you can cancel. Alt+F4 must never be a dead key.

**Before you start**
- A station playing (and optionally a recording running). Preferences ▸ "When
  closing the window" set to **Ask every time**.

**Do this**
1. Press the titlebar **Close (X)**, or **Station menu ▸ Exit**.
2. Read the dialog; press **Cancel** first (stay open). Repeat and choose
   **Minimize to Tray**, then repeat and choose **Exit**. Try the **Don't ask me
   again** checkbox once.

**You should see and hear**
- A dialog titled **"Closing Quill Radio"** asking to exit or minimize; when a
  recording is active it prepends **"Recording is in progress — exiting now stops
  it."** Buttons: **Minimize to Tray** (default), **Exit**, **Cancel**; **Don't
  ask me again** remembers the choice in Preferences. **Cancel/Escape** keeps the
  window. **Exit** quits for real (not minimize). Alt+F4 either closes or, if the
  Alt+F4-to-tray preference is on, tucks to the tray still playing — never nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-37 — Preferences (Station ▸ Preferences…, Ctrl+,)

*What & why.* One dialog for how Quill Radio behaves: resume, updates, engine,
output device, close action, What's Playing wording, logging, and more.

**Before you start**
- Quill Radio open.

**Do this**
1. Press **Ctrl+,**, or **Station menu ▸ Preferences…**.
2. **Tab** through the checkboxes (Resume on Launch, Check for updates, Announce
   dialog transitions, Recover failed streams, Alt+F4 to tray, Verbose logging,
   Keep computer awake), the choices (When closing the window, Playback engine,
   Radio output device, Favorites sort order), the text fields (What's Playing
   announcement, Log folder), and the **Reset All Stations' Sound Enhancements…**
   action.
3. Change one setting; press **OK** (or Cancel/Escape to discard).

**You should see and hear**
- Every control is labelled with a spoken help description; the Playback engine
  choice lists **Automatic / Windows Media (classic) / mpv**. On **OK** it says
  **"Preferences saved"** and changes apply immediately (a playing station
  reconnects through a newly chosen engine/device). Escape discards.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-38 — View menu: Text Size, Show Status Bar, Show Station Details, Customize Features

*What & why.* Low-vision legibility and layout choices, plus the ability to turn
whole feature areas (Recording, Weather) on or off.

**Before you start**
- Quill Radio open.

**Do this**
1. **View menu ▸ Text Size** ▸ **Large** (then back to **Normal**).
2. Toggle **View ▸ Show Status Bar** off and on; toggle **Show Station Details**.
3. **View ▸ Customize Features…**: turn **Recording** or **Weather** off, save,
   and note it takes effect next launch.

**You should see and hear**
- Text Size says **"Text size: Large"** and the window fonts grow immediately;
  Normal restores them. Show Status Bar says **"Status bar shown/hidden."** and the
  bar appears/disappears live. Show Station Details announces its new state.
  Customize Features saves with **"Feature settings saved. Menu changes take
  effect the next time you open Quill Radio."** — and on the next launch the
  turned-off menu (e.g. Record) is absent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-39 — Weather menu and the QuillVille switcher

*What & why.* Quill Radio embeds a Weather menu (handing full weather off to the
Quill Weather app) and a QuillVille switcher to reach sibling apps. This scenario
proves both are present and reachable; the weather features themselves are tested
in **`app-weather.md`**.

**Before you start**
- Quill Radio open with the **Weather** area enabled (default). Quill Weather
  installed for the launch cross-check.

**Do this**
1. Open the **Weather** menu (Alt, then arrow to Weather). Confirm it lists **Open
   the Quill Weather App**, **Weather Now… (Ctrl+Shift+W)**, **Quick Weather
   (Ctrl+Shift+Q)**, **Active Alerts…**, **Add Location…**, **Settings…**, **Test
   Alert…**, and (if enabled) NOAA Weather Radio items.
2. Open the **QuillVille** menu and read the app list.

**You should see and hear**
- The **Weather** menu is present and every item announced; **Open the Quill
  Weather App** launches Quill Weather side by side (see `app-weather.md` for the
  weather features). The **QuillVille** switcher lists the sibling apps **excluding
  Quill Radio itself** — for a public build that means only QUILL and Quill
  Weather (the gated apps must not appear; cross-check `gated-absence.md`).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-40 — Playback survives a dropped connection (auto-reconnect)

*What & why.* Internet streams hiccup; Quill Radio should recover rather than go
silent, optionally scanning the station's own website for a working stream.

**Before you start**
- A station playing. Preferences ▸ "Recover failed streams from the station's
  website" on (default). A way to briefly interrupt the network (e.g. toggle
  Wi-Fi off a few seconds, then on).

**Do this**
1. With a station playing, drop the network briefly, then restore it.
2. Listen without touching the app.

**You should see and hear**
- Playback recovers on its own when the network returns (it may reconnect or, if
  the stream is dead, find a replacement from the station's website), rather than
  failing silently. Any recovery is spoken. (Recording reconnect is governed by
  the Recording Settings "If the connection drops" group in RADIO-22.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## RADIO-41 — Spotify entries are absent (`spotify.connect` / `spotify.browse`) [GATED future.spotify]

*What & why.* Spotify integration is gated off for the public 1.0 release; it must
**not** appear in a public build.

**Before you start**
- A public Quill Radio build (feature flag `future.spotify` off).

**Do this**
1. Open the **Help** menu and read every item.
2. Open the **Command Palette** (Help ▸ Command Palette…) and type **`spotify`**.

**You should see and hear**
- There is **no** "Connect to Spotify…" or "Browse Spotify…" item in the Help menu,
  and the palette finds no Spotify commands. If you are on a dev/admin build with
  the flag on, they may appear — then mark this **N/A**, do not fail it. Confirm
  absence in `gated-absence.md`.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 41
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
