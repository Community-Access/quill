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
>
> **Reviewed 2026-09-28 for the Quill Radio 3.0.3 release.** The current
> release ships two downloads -- the installer
> (`Quill-Radio-Setup-Shared-3.0.3.exe`) and the portable ZIP
> (`Quill-Radio-Portable-3.0.3.zip`), both on the
> [Quill Radio 3.0.3 release page](https://github.com/Community-Access/quill/releases/tag/quill-radio-v3.0.3).
> Where this page and the app disagree, the app and its own User Guide
> (`standalone/radio/docs/userguide.md`, Help > User Guide, Ctrl+F1) are right.
> In particular, the main window no longer has Play/Pause, Stop, Record or
> Browse Stations buttons (each kept its menu item and key), and live radio can
> be rewound but not paused.

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
- The **search** row above searches every station source at once — type a station name, optionally narrow it, and press **Search**. **Country** is a dropdown (with an **Any country** default) and **Tag/genre** is an editable combo box, both filled once per session from [RadioBrowser](https://api.radio-browser.info)'s own most-popular lists so you don't have to guess the exact spelling; Tag stays editable for a rare custom tag, and picking a country or tag runs the search right away. One search fans out to RadioBrowser, **iHeart**, **TuneIn**, and SomaFM together and blends the matches into **one merged, de-duplicated list** (the same stream on two directories, or the same station name and country twice, collapses to a single row; the most likely answer sorts to the top). Each source is failure-tolerant — one directory being down never blanks the list — and all of them are off in Safe Mode. **You do not have to type a station the way its directory spells it:** the query is taken apart into brand, frequency, callsign and place, and each directory is asked for several spellings of it — so `14.90 AM` finds 1490, `1009` finds 100.9, a trailing `FM` no longer loses the station, and naming the state finds one the name alone cannot reach (Radio Browser knows Sunny 105.7 only as “WCSN 105.7 FM Orange Beach”, but `105.7` inside Alabama has exactly one answer). The merged list is then ranked against what you actually typed, since each directory only ranked its own rows against the query it was sent.
- Arrow through the results list and a read-only **Station details** pane reports everything QUILL knows about the selected station: country, language, tags, codec and bitrate, community vote count, homepage, and the stream URL itself. Each row also shows a **Source** column (RadioBrowser, iHeart, TuneIn, SomaFM, ACB Media, or Website), and a **Source** dropdown above the list filters it to just one source without re-searching.
- **Type or paste a website address** into *any* search box and QUILL scans that page for streams and lists what it finds, badged **Website** — the "Find Streams from a Website" capability, wherever you happen to be typing. That means the Browse Stations search row, the browse tree's **Find** box (whatever folder you are standing in), and **Search All Sources...**; the dedicated **Find Streams from a Website...** button stays as a shortcut. A bare `oj991.com` is understood — no `https://` needed — and a query that is *not* an address searches the directories exactly as before.

  This is how you reach a station no directory carries, which is more of them than people expect: OJ 99.1 (WWOJ, Avon Park FL) is in neither TuneIn nor RadioBrowser, so no spelling of its name could ever find it, while its own home page gives up the stream on the first try. Before this, typing that address into Search All Sources handed it to sixteen directories as a station *name*, RadioBrowser matched the token "com", and the answer was 33 rows of `Cruisin92.com` and `STAR1079.com` with the station nowhere in it; typing it into the tree's Find box returned nothing at all, because a web address is never a row label. The recogniser that tells an address from a name lives in `quill/core/radio/page_url.py` precisely so that every surface can reach it.
- **Refresh Directory** re-fetches iHeart's station directory on demand — useful if its catalog has grown since you opened the dialog. RadioBrowser and TuneIn are always live, so only iHeart is cached per session.
- **Play** starts the selected station. **Add to Favorites** (relabels to **Remove from Favorites** once it's saved) keeps it in your Favorites category for next time.

Closing the Browse Stations dialog does not stop playback — the station keeps playing in the background exactly like it would if you'd left the dialog open.

### Adding your own stations

Not every station is in RadioBrowser's directory. Two more buttons in the Browse Stations dialog cover that:

- **Add Custom Station...** takes a name and any http or https stream URL directly, plus an optional homepage and tags. A **Test** button plays the link right there so you can confirm it works before pressing **Save**. **Live365 links are recognized and fixed for you.** A Live365 station page (`live365.com/station/...`) or web-player link (`player.live365.com/a25891`) is a web page, not a stream, so pasting one used to save a station that could never play. Paste any Live365 link — or just its bare station id, like `a25891` — and QUILL rewrites it to that station's real stream address and tells you it did ("Recognized a Live365 link — using its stream URL"). It is a straight text rewrite: no network lookup, nothing sent anywhere, and non-Live365 URLs are left exactly as you typed them.
- **YouTube stations.** Paste a YouTube link — an ordinary video link, a `youtu.be` short link, or a channel's live page such as `youtube.com/@handle/live` — and Quill Radio treats it as a station: it plays in the same player, saves to Favorites, records with **Record Now**, and can be captured by a **scheduled recording**. The link is saved as its page address, not as a stream address, because YouTube's stream addresses expire after a few hours; QUILL finds the audio again each time the station plays or records. That lookup uses **yt-dlp**, a free component QUILL installs on demand (about 3 MB) the first time you add a YouTube station, after showing you a one-time notice — including the reminder to record only what you have the right to record. You are asked when you *add* the station rather than when it plays, so a scheduled recording that fires while you are away is never the first time QUILL reaches YouTube. YouTube stations are unavailable in Safe Mode. Finding the stream takes a moment, so you hear "Connecting" first; if the video is private, removed, blocked in your country, or not live yet, QUILL says so plainly.
- **Find Streams from a Website...** takes a website address you type, fetches that one page, and lists every stream-shaped link it finds on it (an audio tag, a `.pls`/`.m3u` playlist link, a URL that looks like a Shoutcast or Icecast mount point), each with a plain-language reason. Select a candidate, **Test** to preview it, then **Use This Link...** to carry the guessed name and URL straight into Add Custom Station. This fetches and reads one page you explicitly typed — it does not open an interactive browser inside QUILL. If you paste (or the page links to) an **iHeart or TuneIn station page**, Find Streams now follows that player page and pulls out the real underlying stream, instead of handing back the unplayable directory page URL. **SecureNet's player** (`securenetsystems.net/v5/...`), used by a large number of American broadcasters, is handled too — and it failed for the opposite reason from the others. That page *does* write its stream address out in plain text; the address just looks unremarkable — `https://ice66.securenetsystems.net/ROM`, with no `.mp3` on the end and no `/stream` in the path — so the scan used to file it with the page's ordinary links and discard it, returning junk or nothing at all. QUILL now recognizes the player itself and lists the real stream first, whether you point it at the player page or at a station's own site with the player embedded. A related trap is closed with it: those player pages are served from hosts named like `streamdb9web.securenetsystems.net`, and the `/stream` inside that *hostname* used to satisfy the generic "looks like a stream" heuristic, so the scan offered the player **page** as a playable candidate — a page answers HTML, which is exactly what an endless "Connecting." is. A player page is now identified as a page (by host, so new player paths need no maintenance, and never catching the `ice<N>` mount hosts that do play), followed one level to the real audio, and never offered as something to play; the same applies to iHeart and TuneIn landing pages. A station saved from such a page also repairs itself on the first failed play.

#### Checked before it is listed

Find Streams from a Website now opens every link it finds and listens to the first moment of it before it shows you the list. Ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift) made this possible.

- **What "checked" means.** QUILL reads the link's reply and only its first 4 KB, never the whole stream, and recognises MP3, AAC, Ogg (Opus, Vorbis or FLAC), FLAC and WAV. A link that keeps sending audio with no set length is a **live stream**. Audio with a set length is a file, such as a podcast episode, and is marked **Audio file, not a live stream**. A playlist (`.m3u`, `.pls`, `.xspf`, `.asx`) is checked through its first entry. An HLS stream counts as live only when it is a live playlist rather than a recording, and an encrypted one is left out because no Quill player can open it.
- **How the list reads.** Live streams come first. Each row starts with what it is, so it is the first thing you hear on the row: for example "Live: WXYZ FM, MP3, 128 kbps", using the name the stream sends or, if it sends none, the station's name from the directory or server that listed it, or else the server's web address. Next come the links that could not be checked, each with its name and why: "Not checked: Capital UK, there were too many links to check them all", "Not checked: live on stream.example.org, the server refused to let QUILL check (403)". They stay in the list because a busy server is not a broken one; Test them yourself. Audio files come last. The Link and Found by columns follow.
- **What is left out.** A link that answers with a web page, or that the server says is gone, is not audio, so it is not listed. The status line says how many were left out. If every link was left out, that is what you hear.
- **What you hear.** One sentence when the scan finishes, such as "Found 3 live streams and 2 links not checked." When it was the scan's own limit that left links unchecked, the sentence says so: "Found 12 live streams and 36 links not checked, because one scan checks at most 48 links." One scan checks at most 16 links, or 48 when a server lists its streams. Any links beyond that, and any still waiting when the 20 seconds are up, stay in the list as Not checked, and the row says which. Nothing is said for each row, and the list does not change after it appears. Checking takes a few seconds, at most 20, so if nothing has happened after 8 seconds QUILL says once "Still scanning the page and checking its links." Press Scan again during a scan to hear that sentence again; it does not start a second scan.
- **Sites without HTTPS.** QUILL always tries the secure address first. If the site refuses it, does not answer, or its secure connection fails, QUILL reads the plain `http://` page instead, as many small community stations only have that. Only the page's public text is read, and certificates are still checked in full wherever HTTPS is used. When a stream is offered both ways, the `https://` copy is kept.
- **More places a stream is found.** Player settings written into the page (`data-stream`, `data-audio-src` and similar, even with several addresses in one), player configuration such as `streamUrl:` or `hls_url:` with no file extension, addresses printed as plain text, the page's `<base href>`, a Radio.co embedded player, up to three of the site's own player scripts, pop-up players opened with `window.open`, and an Icecast server's status page, which lists every mount by name.
- The same check is used when stream recovery looks for a station's new address on its website, and when you paste a station's web page into Add Custom Station, so a link heard playing is preferred over one that only looks right.
- **Only the public internet.** Find Streams, the check, stream recovery and Add Custom Station's look behind a web page never read an address on this computer or your own network, such as your router, a NAS or a printer, even when a page or a directory entry names one. Such a link is left out of the list rather than offered for Test, and every redirect is checked the same way. If you type one, you hear: "That address is on this computer or your own network, which Find Streams does not scan. To list a server on your network, add it under My Servers in Browse Stations." A page whose links are all on your own network says so, rather than that they were not audio, and the status line counts such links apart from the ones that were not audio. Add Custom Station still saves a stream on your own network exactly as you type it, and anything you choose to play still plays. A proxy set in Windows is still used. An idea from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift).

#### Streaming servers, Global Player and directories

More ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift), written in QUILL's own code.

- **A whole server at once.** Type the address of an Icecast or SHOUTcast server, such as `http://radio.example.org:8000/`, or scan a station site that links to the server's status page, and Find Streams lists every stream the server carries, by the name the server gives it. Icecast is asked through its status list, or its status page when the list is turned off; SHOUTcast through its statistics, so a server carrying several stations shows them all. Streams that are off air, video, and the server's own admin pages are left out. Each stream is still checked before it is listed.
- **How many are listening.** When the server says, the row ends with the count, for example "Live: WABC Community Radio, MP3, 128 kbps, 12 listeners". The name, format and bitrate still come first, and nothing extra is said.
- **Global's stations.** A Global Player page, such as `https://www.globalplayer.com/live/capital/uk/`, or a station site that links to one, gives the stream Global lets everyone play. Streams Global keeps for signed-in or paying listeners are never listed. Global's own list of every station, `https://media-ssl.musicradio.com/`, works too.
- **IPRD is asked about the site.** If IPRD's station list is already on your computer, because you opened or searched IPRD before, the stations IPRD lists for that website are added and checked too. A scan never downloads the IPRD list itself.
- **Locus Sonus Soundmap (Open Microphones).** Browse Stations has a new branch of open microphones streaming live sound from places around the world: a hydrophone in an Amsterdam canal, a farm in New York state. Each is named with its place and plays, records and saves like any station. The list is the soundmap's own list of microphones on air now, so it changes through the day. When none are on air, the branch says so and Refresh looks again. Find Streams from a Website lists them too when you give it the soundmap page, https://locusonus.org/soundmap/.

#### Working with the list

More ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift), written in QUILL's own code. A server listing can give 30 to 100 rows, so the list can be sorted, filtered, searched and acted on several rows at a time. The list changes only when you ask, and you stay on the same stream when it is still shown.

- **Sort and Filter** (Alt+O) opens a menu: Scan order, Name A to Z, Bitrate highest first, and Listeners most first when the page gave listener counts; Live streams only; and All formats or one format the list holds (MP3, AAC, Ogg, HLS, Opus). Live streams stay first whatever the order. One sentence says what changed, such as "Sorted by bitrate, highest first." or "Showing 4 of 31 links: MP3 only." A filter that would leave nothing is refused ("No links are live AAC streams, so the list is unchanged."). A new scan clears the filter, so nothing hides its results, and keeps the order; its sentence says both.
- **Test** and **Use This Link...** act on the focused row. **Add to Favorites** and **Save as Playlist...** act on the selected rows, or on the focused row when none is selected, and their names say how many: "Add 3 to Favorites". One stream goes straight into Favorites; two or more ask for a folder, named after the page to start with. A playlist can be M3U, PLS, XSPF or ASX. Each result says the count: "Added 3 streams to Favorites, in the folder WXYZ; 1 was already there." "Saved 3 streams to WXYZ.m3u."
- **Stream details**, the field after the list, shows the focused stream one fact per line: Name, Status, Format, Listeners, Link, Server, Found by. It is read only, and nothing is said as it changes.
- **Scan This Stream's Server**, in the list's menu, puts the stream's own server address in the Website address field, where you hear it, and scans it, so one stream can show everything the server carries. It is offered only when it could list something new: not for the page's own site, your own network, or the big streaming networks.
- To pick rows that are not next to each other, filter first and then press Ctrl+A. Ctrl+Up and Ctrl+Down stay the volume keys.
- **The last ten sites that worked.** The Website address field remembers the last ten addresses that found at least one live stream, newest first: press Alt+Down to choose one, then Enter or Scan. The list is empty until a scan finds a live stream. Arrowing through the closed field only changes its text and never starts a scan, and nothing is said when the list changes. An address with a query (`?`), a fragment (`#`) or a user name is never remembered, because it may carry a sign-in token, and neither is one on your own network. The list is kept with your recent searches in `radio_history.json`.
- **Mirrors count once.** When a station serves one live stream from numbered hosts such as `ice1`, `ice2` and `ice3`, and each copy sent the same name and format, you get one row, the https copy first. A link that could not be checked is never merged, since nothing shows it is the same stream. The status line says so, for example "Showed 3 numbered copies of the same stream as one."; nothing extra is spoken.
- **Play Random Station and Play Random Favorite** (Station menu in Quill Radio, Ctrl+Shift+O and Ctrl+Alt+Shift+Q; Internet Radio menu in QUILL) play something without choosing. Random Station picks from the Find Stations or Find Streams list you last filled, or from your favorites when none is open; Random Favorite always uses favorites. The same station is never played twice in a row when there is a choice, and one sentence says what was picked and from how many.
- **Reopen Last Results.** Find Streams keeps the streams from your last scan, with the sort order, the filter and the row you were on. When it opens and results are waiting it says so; **Reopen Last Results** (Alt+P) shows them again without scanning or playing anything, and says how long ago they were found. A new scan replaces them, a scan that finds nothing clears them, and Clear Recent Searches... forgets them. Ctrl+Shift+O in the list plays a random stream from the rows shown.
- **Sounds and names while it works.** A long scan makes a soft sound every two seconds. A search that finds nothing plays its own sound, and one that could not finish plays another. While links are checked, each stream that reports a name shows it as "Checking KEXP." in the status line, and the name is spoken at most once every two seconds. **Play sounds while Find Streams searches** in Preferences turns the three sounds off; the sentences are still said.
- **Typing a name, and other ways to find it.** The Find Streams address box also takes a station name: `kexp`, `bbcradio4` with no spaces, or `kexp.mp3` with an ending is looked up in Radio Browser, IPRD and Radio Garden, ignoring spaces and punctuation, and each stream is checked as usual. A name that matches a recent website first asks whether to check that site again. **Try other ways when a website has no stream** in Preferences (off by default) makes a website with no stream fall back to the directories, by the name in its address. The result says which way found it. There is no browser-assisted step in Quill Radio.
- **Radio Garden.** Paste a Radio Garden station page, such as `https://radio.garden/listen/kexp/Zk1UxX-Y`, into the Find Streams address box and press Scan: the station's own stream is found through Radio Garden's page address, checked as live audio and listed, with "Found by Radio Garden." A station name typed in the box is searched there too (at most five stations looked up). Radio Garden has no official public interface, so only the three addresses its own page uses are read, only for what you type or paste, and a refusal is one plain sentence. Safe Mode contacts nothing.
- **Clear Recent Searches...** (Station menu in Quill Radio, Ctrl+Alt+Shift+Backspace; Internet Radio menu in QUILL) forgets both the station searches Find Stations remembers and these recent websites. It asks first, naming only what is there, for example "Clear 15 recent station searches and 10 recent websites? No station or favorite is removed.", with No as the default, then says once "Cleared 15 recent searches and 10 recent websites." With nothing to clear it says "There are no recent searches or websites to clear." If Find Stations is open, its search box's list empties too and keeps what you typed.
- **More sites are read.** Find Streams follows "Listen Live" links written in French, Spanish, Portuguese, German, the Nordic languages, Italian and Dutch, such as "Écouter en direct", "Ouvir ao vivo" or a `/direkt/` page, and a player on the site's own `listen.`, `play.`, `player.`, `radio.`, `stream.` or `streams.` address. A different site's address is never followed.

| Key, in the list | What it does |
|---|---|
| Shift+Up, Shift+Down | Select several rows |
| Ctrl+A | Select every row shown |
| Ctrl+C | Copy the stream links of the selected rows |
| Ctrl+F | Find a stream by name, link, format, bitrate, listeners or how it was found |
| F3, Shift+F3 | Find the next or previous match, wrapping |
| Ctrl+S | Save the selected rows as a playlist |
| Enter | Test the focused stream; on another row while one plays, test that one instead; on the same row, stop |
| Applications key, Shift+F10 | The list's menu |

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

**Resume** (Enter) restarts the recording for the remaining minutes only. **Skip** (Escape) leaves it as it is. A **Don't ask me again** checkbox remembers your choice — always resume, or always skip. Change it later in Preferences, under **Interrupted recordings at launch**. Nothing happens when nothing was in progress, and a corrupt marker file is discarded rather than driving a bogus resume.

### How recordings survive a dropped connection

A live stream can drop mid-recording. When it does, QUILL waits and starts a **continuation file**, up to the number of attempts in Recording Settings. FFmpeg is deliberately not allowed to reconnect a live stream inside one file, because every new connection can begin with the station's pre-roll advert, and that would splice an advert into the middle of the recording with nothing to show where. Three things keep that tidy:

- **Station adverts are cut.** Many stations play an advert or a welcome message to every new connection. When a recording starts, QUILL listens to the station once more about 20 seconds later (decoded in memory, never saved), and when the recording ends it compares how each part begins with that and with the other parts. Audio that opens two separate connections cannot be the live programme, so it is cut from the start of every part before they are joined, and you hear how much was removed. A station whose advert differs every time, or that plays none, is left exactly as recorded. YouTube broadcasts and HLS streams are not checked.

- A continuation records only the **remaining** time to the original scheduled end, not a fresh full duration — a 60-minute show that drops at minute 50 records a ~10 minute continuation, not another 60.
- **You always hear how it ended.** When a recording is over -- not between reconnects -- QUILL says the station, when it started, how long it is and its folder. If the station went away for good before the end, you hear the error sound, how much was kept ("Saved 44 of 190 minutes") and why. Each message is kept in Activity (Shift+F9) with the file name and Open Folder; an early end is listed as partial. If a reconnect connects but records nothing, the parts you already have are kept.
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
