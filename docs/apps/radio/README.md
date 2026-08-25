# Quill Radio material relocated from QUILL's documentation

> Quill Radio is a standalone application with its own complete documentation
> set (`standalone/radio/docs/` — User Guide, PRD, release notes), opened from
> the app's own Help menu. During the 2026-08-17 documentation scoping, QUILL's
> user guide stopped documenting the standalone apps' features: QUILL's guide
> now carries only the QuillVille pointer that launches them. The chapters
> removed from `docs/user guide/userguide.md` are preserved here so nothing is
> lost, following the pattern of `docs/apps/player/README.md`.
>
> **This material is historical.** It described Internet Radio as it ran in and
> around QUILL 1.0.0; Quill Radio 3.0's own User Guide is the current and far
> more complete reference (the tree browser replaced the dialog described
> below, and Sound Enhancements, scheduled recording, custom stations and
> backups are all documented there in their current form).

| Relocated from | Section |
|---|---|
| `docs/user guide/userguide.md` | "Internet Radio" (the in-editor chapter) |
| `docs/user guide/userguide.md` | "Quill Radio: the standalone app" |

---

## Internet Radio

Internet radio plays live streams in the background — the station browser, favorites, recording, scheduling, and everything else described in this chapter. In QUILL 1.0.0 it runs as the standalone **Quill Radio** app rather than inside the editor; see *Quill Radio: the standalone app* (below) for how to launch it. It is disabled entirely in Safe Mode, since it is a network feature.

> **The browsing described in this chapter is the older, in-editor dialog.** Quill Radio 3.0 replaced it with a tree of thirty branches you can wander without searching for anything: the station directory by country, by language, by what is trending today; podcasts by country and genre with no account anywhere; and whole libraries — the Internet Archive, LibriVox, Project Gutenberg, Audius, Mixcloud, ccMixter — plus browse axes drawn from Wikidata (by city, by format, or where a station sits on the dial). None of it needs a key or a sign-in. It is all documented in the **Quill Radio User Guide**, which the standalone app opens from its own Help menu.

### Finding and playing a station

**Browse Stations...** opens a search-and-browse dialog:

- A **Category** list on the left offers two instantly available options that need no network call to show: **Favorites** (stations you've saved) and **ACB Media** (the American Council of the Blind's ten Live365 stations, bundled directly into QUILL). Choosing either fills the results list immediately.
- The **search** row above searches every station source at once — type a station name, optionally narrow it, and press **Search**. **Country** is a dropdown (with an **Any country** default) and **Tag/genre** is an editable combo box, both filled once per session from [RadioBrowser](https://api.radio-browser.info)'s own most-popular lists so you don't have to guess the exact spelling; Tag stays editable for a rare custom tag, and picking a country or tag runs the search right away. One search fans out to RadioBrowser, **iHeart**, **TuneIn**, and SomaFM together and blends the matches into **one merged, de-duplicated list** (the same stream on two directories, or the same station name and country twice, collapses to a single row; exact name matches sort to the top). Each source is failure-tolerant — one directory being down never blanks the list — and all of them are off in Safe Mode.
- Arrow through the results list and a read-only **Station details** pane reports everything QUILL knows about the selected station: country, language, tags, codec and bitrate, community vote count, homepage, and the stream URL itself. Each row also shows a **Source** column (RadioBrowser, iHeart, TuneIn, SomaFM, ACB Media, or Website), and a **Source** dropdown above the list filters it to just one source without re-searching.
- **Type or paste a website address** into the search box and Browse Stations scans that page for streams and lists what it finds, badged **Website** — the "Find Streams from a Website" capability, right in the same search box (the dedicated **Find Streams from a Website...** button below stays as a shortcut).
- **Refresh Directory** re-fetches iHeart's station directory on demand — useful if its catalog has grown since you opened the dialog. RadioBrowser and TuneIn are always live, so only iHeart is cached per session.
- **Play** starts the selected station. **Add to Favorites** (relabels to **Remove from Favorites** once it's saved) keeps it in your Favorites category for next time.

Closing the Browse Stations dialog does not stop playback — the station keeps playing in the background exactly like it would if you'd left the dialog open.

### Adding your own stations

Not every station is in RadioBrowser's directory. Two more buttons in the Browse Stations dialog cover that:

- **Add Custom Station...** takes a name and any http or https stream URL directly, plus an optional homepage and tags. A **Test** button plays the link right there so you can confirm it works before pressing **Save**. **Live365 links are recognized and fixed for you.** A Live365 station page (`live365.com/station/...`) or web-player link (`player.live365.com/a25891`) is a web page, not a stream, so pasting one used to save a station that could never play. Paste any Live365 link — or just its bare station id, like `a25891` — and QUILL rewrites it to that station's real stream address and tells you it did ("Recognized a Live365 link — using its stream URL"). It is a straight text rewrite: no network lookup, nothing sent anywhere, and non-Live365 URLs are left exactly as you typed them.
- **YouTube stations.** Paste a YouTube link — an ordinary video link, a `youtu.be` short link, or a channel's live page such as `youtube.com/@handle/live` — and Quill Radio treats it as a station: it plays in the same player, saves to Favorites, records with **Record Now**, and can be captured by a **scheduled recording**. The link is saved as its page address, not as a stream address, because YouTube's stream addresses expire after a few hours; QUILL finds the audio again each time the station plays or records. That lookup uses **yt-dlp**, a free component QUILL installs on demand (about 3 MB) the first time you add a YouTube station, after showing you a one-time notice — including the reminder to record only what you have the right to record. You are asked when you *add* the station rather than when it plays, so a scheduled recording that fires while you are away is never the first time QUILL reaches YouTube. YouTube stations are unavailable in Safe Mode. Finding the stream takes a moment, so you hear "Connecting" first; if the video is private, removed, blocked in your country, or not live yet, QUILL says so plainly.
- **Find Streams from a Website...** takes a website address you type, fetches that one page, and lists every stream-shaped link it finds on it (an audio tag, a `.pls`/`.m3u` playlist link, a URL that looks like a Shoutcast or Icecast mount point), each with a plain-language reason. Select a candidate, **Test** to preview it, then **Use This Link...** to carry the guessed name and URL straight into Add Custom Station. This fetches and reads one page you explicitly typed — it does not open an interactive browser inside QUILL. If you paste (or the page links to) an **iHeart or TuneIn station page**, Find Streams now follows that player page and pulls out the real underlying stream, instead of handing back the unplayable directory page URL. **SecureNet's player** (`securenetsystems.net/v5/...`), used by a large number of American broadcasters, is handled too — and it failed for the opposite reason from the others. That page *does* write its stream address out in plain text; the address just looks unremarkable — `https://ice66.securenetsystems.net/ROM`, with no `.mp3` on the end and no `/stream` in the path — so the scan used to file it with the page's ordinary links and discard it, returning junk or nothing at all. QUILL now recognizes the player itself and lists the real stream first, whether you point it at the player page or at a station's own site with the player embedded. A station saved from such a page also repairs itself on the first failed play.

### What's playing

QUILL reports the current track — artist and title — from the stream's own broadcast metadata, and can announce it automatically each time the song changes. When a stream sends no title of its own and the player has none to offer, QUILL now falls back to the station server's own now-playing information (its Icecast or Shoutcast status page, on the same host you're already streaming), so more stations tell you what's on.

**Copying and reviewing what's playing.** Two commands go beyond the spoken announcement: **Copy What's Playing** puts the track on the clipboard, and **What's Playing - Review and Copy...** opens a small read-only window you can arrow through character by character (handy for the exact spelling of a song or artist) with a Copy button. Both work the moment a station is on: if the track title has not been read from the stream yet, QUILL says "Checking what's playing...", fetches it, and then finishes the job. If the stream carries no titles at all, it says so plainly, and the review window still opens showing the station name — so these commands always answer you.

### Volume

The Browse Stations dialog has its own **Radio volume** slider and a **Mute** button. This volume is entirely separate from your Windows system volume and from your screen reader's own speech volume — turning radio down (or muting it) never touches either of those.

**Ctrl+Up** and **Ctrl+Down** change the volume from anywhere in the Quill Radio window — you no longer have to be on the favorites tree first (inside a text field they still move the cursor, as you would expect). The level you set is **remembered between sessions**, so a station does not come back at full volume the next time you launch. A favorite with its own remembered level still wins for that station.

### Recording a station

Recording needs the **FFmpeg** optional component — the same one QUILL's audiobook and batch-speech tools use for compressed audio exports. If it isn't installed yet, the recording commands are simply not there; install it from **Help > Download Optional Components** (the "Audio: export, playback & chapters" entry) and they appear.

- **Record Now** (the Quill Radio **Record** menu or the app's tray icon) starts recording whatever station is currently playing. Choosing it again, or **Stop Recording**, ends the recording.
- **Schedule Recording...** queues a recording for later without you needing QUILL open right at that moment to press Record — just QUILL running somewhere. Choose **Once** (a specific date and time), **Daily**, or **Weekly** (a chosen day of the week), a station name and stream URL, and how many minutes to record. The time field accepts a friendly **12-hour** time like `7:30 PM` as well as 24-hour `19:30`, and each schedule can carry its own **time zone** — so you can record an Eastern show at its Eastern time even from the Pacific coast, and daylight saving is handled for you. Existing schedules can be **Edited** in place, **Duplicated** as the starting point for a variation (handy for the same show on several days), or **Enabled/Disabled** without deleting them, from buttons or the list's context menu. A schedule is due from its start time through the end of its duration, so a late arrival (QUILL reaching 8:01 for an 8:00 schedule) still starts with the remaining minutes, and on launch QUILL catches up anything whose window is still open. If QUILL was closed for the whole window, that occurrence is simply missed — and on the next launch QUILL tells you, naming up to three missed recordings and collapsing the rest to a count.
- **Recording Settings...** sets the format (MP3, OGG, FLAC, or WAV), bitrate, destination folder, a filename pattern using `{station}`, `{date}`, and `{time}` placeholders, and a maximum recording length that acts as a safety cap even if you forget a recording is running. New recordings go to a visible **Music\Quill Radio Recordings** folder by default (falling back to your home folder) rather than a buried application-data path, so a finished recording is easy to find. An optional **Temporary folder (while recording)** writes the file there and moves it to your destination the moment it finishes, so a half-written file never appears in your recordings folder.
- **Recordings...** opens a single list of your whole recording life cycle — the file being written right now (its size growing on a live refresh), every finished recording (newest first), and any upcoming scheduled recordings — where you can play, reveal in the file manager, stop the active recording, or remove a finished one, all from the keyboard. The list updates rows in place keyed by file path: it is a no-op when nothing has changed, and when something has your selection, focus, and scroll position are preserved instead of the list rebuilding under you. The active row shows a live elapsed time, scheduled entries show their zone-labeled times, and the **Refresh** button updates on demand.

### Winamp keys in the Recordings list

If your listening habits were formed on Winamp, its classic-skin main-window keys work in the **Recordings...** window on the letter keys you already know — no modifier, no menu:

| Key | What it does |
| --- | --- |
| X | Play the selected recording, or resume a paused one |
| C | Pause / unpause |
| V | Stop |
| Shift+V | Stop (Winamp's fade-out; this player has no fade, so it stops cleanly) |
| B | Next recording — moves down the list and plays it |
| Z | Previous recording |
| Left / Right | Back / forward 5 seconds |
| Shift+Left / Shift+Right | Back / forward 30 seconds |
| T | Elapsed time, or time remaining — press again to swap |
| J | Jump to a recording: type any part of its name |
| Ctrl+J | Jump to a time: type `90`, `1:30`, or `1:02:03` |
| L | Open (the same as Play) |
| Ctrl+Up / Ctrl+Down | Volume up / down |

Every one of them announces what it did, so a key that did not land is never mistaken for one that did.

Two deliberate differences from Winamp, both worth knowing: **Ctrl+T stays What's Playing**, which is the more useful thing to have on that key in a radio app, so Winamp's elapsed/remaining toggle sits on plain **T**; and **Up and Down arrow keep moving through the list** rather than changing the volume — which is exactly what Winamp itself does in its Playlist Editor, and this list is a playlist editor by any other name.

Seeking needs a recording with a timeline, which means the mpv playback engine; on a live stream, or with the classic Windows Media engine, the seek keys say why they cannot move instead of doing nothing. Letters typed into a text field are never swallowed. Turn the letter keys off with **Winamp-style playback keys in the Recordings player** in Preferences if you would rather use them to type through the list; Ctrl+Up and Ctrl+Down are unaffected either way.

Shuffle, repeat, and stop-after-current are deliberately absent: all three describe a play queue this list does not have yet, and a key that only looks like it worked is worse than no key at all.

### If a recording was in progress when QUILL quit or crashed

A recording used to be lost the moment QUILL (or the standalone Quill Radio) quit or crashed — the FFmpeg process it had spawned kept writing to a temp file nobody would ever find. QUILL now remembers an in-progress recording and offers to pick it back up.

On the next launch, QUILL first tidies the temp folder: any finished orphan file is moved to your recordings folder, while a file still being written is left untouched. If a recording was in progress and is still within a 10-minute grace window, QUILL asks once, in an accessible dialog:

> A recording of WQXR was in progress until 9:00 AM. Resume it for the remaining 12 minute(s)?

**Resume** (Enter) restarts the recording for the remaining minutes only. **Skip** (Escape) leaves it as it is. A **Don't ask me again** checkbox remembers your choice — always resume, or never ask — and you can change it later in Preferences. Nothing happens when nothing was in progress, and a corrupt marker file is discarded rather than driving a bogus resume.

### How recordings survive a dropped connection

A live stream can drop mid-recording. QUILL rides out short gaps itself (FFmpeg's own reconnect handling), and if the process still dies it waits and starts a **continuation file**, up to the number of attempts in Recording Settings. Two things keep that tidy:

- A continuation records only the **remaining** time to the original scheduled end, not a fresh full duration — a 60-minute show that drops at minute 50 records a ~10 minute continuation, not another 60.
- A drop is classified before any reconnect attempt is spent. A **fatal** failure (your disk is full, or the server took the stream down with an HTTP 4xx such as 404 or 410) stops trying — the stream is gone, and reconnecting would only spam continuation files. A **transient** drop (a network hiccup or a 5xx) is retried.

Output filenames are also never silently overwritten: a pattern that produces the same name twice gets `" (2)"`, `" (3)"` appended instead of `-y` clobbering the earlier file, and continuation parts keep the original start timestamp in their name so they group together. And on Windows, the FFmpeg child is tied to QUILL's lifetime through a job object, so a crashed or killed QUILL takes it down rather than stranding a bare recording writing to your temp folder.

### Sound Enhancements

**Playback > Sound Enhancements...** applies a three-band equalizer (Bass, Mid, Treble sliders, -12 to +12 dB each, freely adjustable) and a compressor ("Even Out Volume") to whatever station is playing, filtered live through FFmpeg — needs the same FFmpeg component recording does. A "Quick preset" combo box (Flat, Bass Boost, Voice Clarity, Podcast) sets all three sliders at once as a starting point; move any slider afterward and it becomes Custom. Off by default; turning anything on reconnects the stream instantly (live radio has no position to lose).

Sound Enhancements is remembered **per favorite station**: open it while a favorite is playing to give that station its own EQ and compressor, separate from the shared default — a jazz station and a talk station no longer have to sound the same. Open it with nothing playing (or a non-favorite station on) to change the shared default every other station follows. **Recording Settings...** has a matching **Apply Sound Enhancements to recordings** checkbox (off by default) if you'd rather your recordings capture the filtered audio too.

### What's not in Internet Radio

TuneIn and iHeartRadio **are** now supported as station sources (they appear blended into your search results, above) — through open, no-key, no-account backends that resolve only the stations you actually search for, never a bulk scrape. YouTube audio is still not supported.

---

## Quill Radio: the standalone app

You don't have to open the full QUILL editor to listen. **Quill Radio** runs
Internet Radio as a small standalone app — its own window, its own menu bar, its
own system tray icon.

It is the same feature, not a copy: the app runs the exact same code QUILL itself
uses, and reads the same settings and favorites from the same place on disk. A
station you favorite in Quill Radio is a favorite in QUILL. Everything described
in the Internet Radio chapter above — the station browser, the link finder,
recording and scheduled recording — works identically here.

**Starting the app.** On an installed QUILL, Quill Radio is in the Start Menu,
right next to QUILL itself. The installer also offers an optional desktop icon
for it (a checkbox during setup; unchecked by default so your desktop stays
yours). From a source checkout or the portable build, use `run-quill-radio.bat`,
or `python -m quill.apps.radio`.

**Everything is keyboard-first.** The app opens on a real main panel, not an
empty window: focus lands on the app's most important list the moment it opens.

- **Quill Radio** — focus starts in your **Favorite stations** list: arrow to a station and press **Enter** to play it. Tab reaches Play/Pause, Stop, Record, and Browse Stations buttons, with a live now-playing line above. Menus: **Station** (Browse Stations, Add Custom Station, Find Streams from a Website, and your Favorite Stations listed inline so switching is one keystroke), **Playback** (a live now-playing line, Play/Pause with Ctrl+P, Stop, Mute, volume), **Record** (Record Now / Stop, Schedule Recording, Recording Settings), and **Help**.

Quill Radio puts an icon in the system tray with the same radio controls QUILL's
own tray icon offers, plus **Show** (double-click also works) and **Exit**. And
when you decide you want the full editor after all, **Help > Open in Quill**
launches it.

The app respects Safe Mode (`QUILL_SAFE_MODE=1`) and skips the tray icon on
macOS, where the system has no equivalent notification-area icon (the same rule
QUILL itself follows).
