# Quill Radio User Guide

Version 2.2.0

Quill Radio is internet radio the way a screen reader user would design it: a small window whose favorites tree has focus the instant it opens, menus that say everything they do, spoken feedback for every action, and a tray icon so the music keeps playing while you work. It runs the exact same radio code as QUILL itself and shares its data, so nothing you set up here is ever stranded.

## Installing

Quill Radio comes in four downloads. Two of them are brand new in this release and much smaller than before, because Quill Radio can now share one Python engine -- the QuillVille Runtime -- with every other QuillVille app. The section just below explains the runtime; the one after it lays out the four downloads so you can pick the one that suits you.

If you are not sure which to choose: the **full installer** is the easy, recommended path for most people, and the **full portable zip** is the one to put on a USB stick.

### The QuillVille Runtime: install the engine once, and every app starts instantly

Quill Radio is part of a small family of apps -- QUILL itself, Quill Radio, Quill Weather, and QUILL Audio Studio. They are separate apps, but underneath they all run on the same Python engine.

Starting with this release, that engine is installed just once per user, as a shared component called the **QuillVille Runtime**, and every QuillVille app reuses it. Install any one app that carries the runtime, and every app you add afterward starts instantly, because the engine it needs is already on your PC. There is no second copy, no second long download.

The runtime looks after itself. It is reference-counted: Windows keeps track of how many QuillVille apps rely on it, and it is only removed when you uninstall the very last app that needs it. Uninstalling Quill Radio while, say, Quill Weather is still installed leaves the shared runtime in place for Weather; uninstalling the last one cleans it up for you.

### The four downloads

You can install Quill Radio in whichever of these ways fits you best. In each filename, `<version>` is the release you are downloading, such as 2.2.0.

1. **Full portable zip** -- the file named `Quill-Radio-Portable-<version>.zip` (about 311 MB). Fully self-contained: extract it anywhere -- a folder, an external drive, a USB stick -- and run `QuillRadio\QuillRadio.exe`. There is no installation and nothing ever downloads at runtime. It carries its own genuine, unmodified copy of Python, plus the bundled ffmpeg (for recording) and mpv (for playback) engines. Its `data` folder keeps your favorites, history, recordings, and settings inside the app folder, so the whole radio travels with you. This is the one to reach for when you want a self-contained radio with no installer and no internet.

2. **Companion edition (new)** -- the file named `Quill-Radio-Companion-<version>.zip` (about 3 MB). Feather-light: it contains only the app itself and its documentation, and it runs on the shared QuillVille Runtime. The first time you launch it, if the runtime is not already installed, Quill Radio offers to download and install it for you -- about 230 MB, once -- with a fully accessible progress bar (see "Accessible progress every time" below). After that, this app and every other QuillVille app start instantly. Choose the Companion edition when you would rather download three megabytes than three hundred, and you are happy for the shared engine to be fetched once on first launch.

3. **Full installer** -- the file named `Quill-Radio-Setup-Shared-<version>.exe`. A standard Windows installer that gives Quill Radio its own Start Menu entry and an uninstaller. It installs the shared QuillVille Runtime (unless it is already present from another QuillVille app) and then the app. Your favorites, history, and settings live in the shared Quill store in your Windows profile. This is the recommended path for most people.

4. **Thin installer (new)** -- the "Lite" installer, a very small setup program that installs the app and downloads the shared QuillVille Runtime only if it is not already present. If you already run another QuillVille app, there is nothing large to fetch and the install finishes quickly. Choose it when you want a proper installed app but the smallest possible download.

### Accessible progress every time

Whenever the QuillVille Runtime is being downloaded -- whether an installer is fetching it or the Companion edition is fetching it on its own first launch -- Quill Radio shows a fully accessible progress bar. It works with NVDA, JAWS, and Narrator, and progress is announced as a percentage as it climbs. You always know how far along the download is, and when it is finished.

### About security software and antivirus

This release changes how Quill Radio starts, specifically to be friendlier to antivirus software.

Quill Radio's launcher is now a genuine, tiny native program, and the Python it runs is the official, unmodified build. Earlier versions used a renamed and modified copy of Python's own `pythonw.exe` as the launcher. That pattern is a common one for antivirus tools to flag, and some of them did -- as a false positive, but an understandable one. That pattern is now completely gone. The result is an app that is far less likely to be mistaken for something it is not.

Windows SmartScreen may still show a caution on first run because this release is not yet code-signed; choose "More info" then "Run anyway". The build is exactly what this repository's source produces.

## Getting started

Launch Quill Radio from the Start Menu (or the portable folder's `QuillRadio.exe`). The window opens with keyboard focus on your **Favorite stations** tree.

- No favorites yet? Press Alt+S for the Station menu, then **Browse Stations...** to wander a tree of every source -- popular stations, NOAA Weather Radio, radio reading services, whole directories -- or **Search Stations...** to search thousands of stations by name, genre, country, or language. Either way, listen before you commit, and add the keepers to your favorites. The **ACB Media** submenu is also right there -- the whole ACB stream directory, playable without any setup.
- With favorites: arrow to a station and press **Enter**. That is the whole loop.
- Want the radio on the moment the app opens? Check **Station > Resume Last Station on Launch** once, and Quill Radio becomes an appliance: launch it, and your station is already playing.

Everything Quill Radio announces goes through the same announcement engine QUILL uses, so it speaks through your screen reader (JAWS, NVDA, Narrator) without stealing focus.

Those announcements also go to a connected **braille display**, not just to speech -- what's playing, a finished directory refresh, a recording starting. Nothing is shortened, so a long track title is there in full for you to pan through, and the same message repeated within a couple of seconds does not flash the display twice (a flash message replaces whatever is under your fingers, so repeats are worse than useless). If a burst of different messages arrives at once, the first is written immediately and the rest settle to the newest, rather than each shoving the last aside faster than cell one can be read; errors always write through straight away. Braille never costs you speech: an unplugged display, or a screen reader that will not take the message, simply means it was spoken and not brailled -- never silence. Turn it off with **Show announcements in braille** in Preferences, under Accessibility.

## The main window

Tab order: the now-playing line, the favorites tree, then four buttons.

- **Now playing** (read-only text): what is on right now; also mirrored in the status bar and the Playback menu.
- **Favorite stations** (tree): the same nested folder structure you build in the Favorites Manager, right on the main page. Enter plays a station, Delete removes it (with confirmation), F2 renames a station or folder, and Shift+F10 opens the full context menu -- Play/Stop, **Station Details...** (a reviewable, copyable readout of the station's source, stream, format, and country -- the same view the search results give), Rename, Move to Folder, Remove, New Folder, Mark for Move, and Manage Favorites. Your custom names are used everywhere.
- Buttons: **Play** (it becomes **Stop** while connecting or playing -- one transport control, never a dead button; its reliable keyboard shortcut is **Ctrl+P**, which works from anywhere in the window), **Add to Favorites** (it becomes **Remove from Favorites** when the playing station is already saved -- perfect for keeping something you found in ACB Media or Recently Played), **Record**, and **Browse Stations...**
- **Volume** (slider): right in the Tab order after the buttons, so you can tab to it while a station is playing and use the **arrow keys** (or Page Up/Page Down) to turn the volume up or down. It is one of three ways to set the volume -- the others are **Ctrl+Up/Ctrl+Down** from anywhere in the window, and the status bar's Volume cell -- and all three stay in agreement, including with each station's remembered volume.
- **Status bar** (along the bottom): a row of cells that always show what is going on -- Now playing, Volume (with a note when Volume Boost is on), Recording, Sleep timer, Favorites count, and the time. Press **F6** to move focus into it; a second F6, or Escape, hands focus back to the favorites tree. Arrow **Left** and **Right** to move across the cells (**Home** and **End** jump to the first and last), press **Enter** or **Space** to act on the cell you are on (Now playing opens the What's Playing window, Volume mutes or unmutes, Recording starts or stops recording, Sleep timer opens the timer dialog, Favorites jumps back to the list, Time speaks the full date and time), and press the **Applications key** or right-click for a context menu with more actions (play/pause, mute, volume up and down, Volume Boost, stop all recordings, and Hide Status Bar). Turn the whole bar off from **View > Show Status Bar** if you would rather not have it.

## Windows, and moving between them

Quill Radio's bigger surfaces -- **Browse Stations**, **Search Stations**, **Manage Favorites**, **Schedule Recording**, and the **Weather Center** -- open as their own **windows**, not dialogs. Two things follow from that, both on purpose:

- **The menu bar is always there.** Every window carries the full menu bar, so Alt reaches your menus no matter which window you are in. (Older versions used dialogs, which cannot carry a menu bar, so opening one made the menus seem to disappear.)
- **The main window stays reachable.** Opening one of these windows no longer locks you out of the favorites list; you can keep several windows open at once and work across them.

A **Window** menu on every window lists what is open, numbered in the order you opened them. To move between windows:

- **Ctrl+Tab** goes to the next window, **Ctrl+Shift+Tab** to the previous one (it wraps around).
- **Ctrl+1** through **Ctrl+9** jump straight to the first through ninth open window.
- Or open the **Window** menu and pick one by name and number.

Each window opens only when you ask for it, and closing a window puts focus back on the window you came from. Quill Radio announces "Entered ..." as a window opens and "Exited ..." as it closes, and drops your focus on the window's main control so you can start straight away. (Inside QUILL itself these same surfaces open as ordinary dialogs; the multi-window model is the standalone Quill Radio experience.)

## Menus

### Station (Alt+S)

- **Browse Stations...** -- a search-free window for wandering: one tree whose top-level branches are the sources. **Favorites** sits first (your own folders and streams), then **Popular Stations**, **Radio Browser (by Genre)** (walk the Radio Browser directory by genre, not only search it), **Weather / NOAA**, **ACB Media**, **NFB Radio**, **Radio Reading Services**, **SomaFM**, **TuneIn** (its real folder tree, which drills from continent down to city), **Networks** (well-known broadcasters -- the BBC, NPR, CBC, ABC Australia, Radio France, Deutschlandfunk, public radio worldwide, plus national news and sports -- grouped by type, each a one-click list drawn from the Radio Browser directory; a few, like Westwood One, are syndication services with no single stream, so those open a search across their local affiliate stations, and the label says so), **Community M3U (Music Genres)**, and the **Xiph / Icecast Directory**. Expand a branch and its stations load on the spot; **Enter** plays the highlighted station, and **Shift+F10** (or right-click) opens Play/Stop, Add/Remove Favorite, Copy stream link, Open website, **Report Bad Station...**, and Refresh. (TuneIn stations work out their stream only when played, so **Add to Favorites** on a TuneIn station resolves it on demand before saving -- it works there now just like every other source.) Browse Stations also **remembers the source you were last in**, so playing a station and reopening the tree puts you back on that branch instead of collapsed at the top with everything closed. Two branches deserve their own words:
  - **Weather / NOAA** is the real NOAA Weather Radio directory, state by state. Open the branch and you get the states (each with its transmitter count); open a state and you get its actual transmitters, named with call sign, frequency, and place -- "KHB36 162.550 MHz Manassas" -- and Enter plays the best available internet re-stream. The complete directory (1,035 transmitters) is bundled inside the app, so this branch works even offline. See "Your local NOAA Weather Radio" in the Weather chapter for the one-keypress local version.
  - **Radio Reading Services** lists the audio information services that read newspapers, magazines, and local print aloud for people who are blind or print-disabled -- WRBH 88.3 Reading Radio, Sun Sounds of Arizona, CRIS Radio, the Connecticut Radio Information System, the KPBS and WKAR reading services, ACB Media 1-5, the NFB Radio Network, Voice Corps, and more. Twenty vetted services are bundled, so the branch is never empty; play, favorite, record, and schedule them like any other station.
  - **iHeart** opens into **genres** (Country, Pop, News/Talk, Sports, and the rest), and each genre into an **A-Z** sub-directory of its stations -- so you expand a genre, expand a letter, and press Enter to play. Each level loads only when you open it. (Browsing uses iHeart's own genre directory; a station's stream is ready to play with no extra step.)
- **Find in this folder** -- below the tree is a search box that searches **only from the folder you are highlighted on, downward** -- one iHeart genre, one state, one source -- so you get a short, relevant list instead of searching every directory at once. Highlight the folder you want to search within, type part of a station name, and press **Enter** (or the **Find** button); matching stations appear as a flat list under that folder. Press **Clear** to drop the results and put the cursor back on the folder you searched from. To search a folder, Quill Radio loads that folder's stations first, so a search from a very large branch is kept bounded (it tells you if it showed only the first results -- search a smaller folder to see the rest). For a search across *every* directory at once, use **Search Stations...** instead.
- **Search Stations...** -- the full station search: search across four directories at once -- **RadioBrowser**, **SomaFM**, **iHeart**, and **TuneIn** -- blended into one results list, test-play, favorite. A search that looks like weather-radio geography -- a 6-digit **SAME code**, a **call sign** like `KHB36`, or a **"County, ST"** or state name -- also brings back exact NOAA Weather Radio transmitters from the authoritative directory, and reading services match by name, tag, or state right alongside. Every result is labeled with the directory it came from ("via iHeart", "via TuneIn"). RadioBrowser shows up to 200 stations at once, most-listened first; when there are still more, a **More Stations** button loads the next page and puts your cursor on the first newly added station. iHeart and TuneIn add a small set of their most relevant, immediately-playable matches to each search (each iHeart/TuneIn result's real stream is looked up on demand, so they are capped per search to keep one search from becoming dozens of network requests).
  - **Source** -- a dropdown to narrow the search to one directory (All sources, RadioBrowser, iHeart, TuneIn, SomaFM, ACB Media, or Website) when you already know where a station lives. When the same station is carried by more than one directory (a SomaFM channel RadioBrowser also lists, say), it appears under each of those directories' filters, not just the one whose copy you happened to play.
  - **Tag/genre** and **Country** -- these are now proper dropdown lists, filled in from the directory itself, so you pick "jazz" or "United Kingdom" from a list instead of typing the exact spelling; choosing one runs the search right away.
  - **Refresh** -- re-fetches the iHeart station directory. iHeart's directory index is cached once per Browse Stations session (TuneIn and RadioBrowser are always live), so use Refresh if you want the very latest iHeart listing.
  - The status line tells you when more can be loaded and suggests adding a tag or country to narrow a very broad search. Search is disabled in Safe Mode.
- **Update Radio Reading Services...** -- refresh the Radio Reading Services list on demand from the community RadioBrowser directory, off the UI thread, announcing how many services it found. The bundled list stays as the fallback, and the command is off in Safe Mode.
- **Add Custom Station...** -- paste any stream URL and name it yourself. Three kinds of link get extra help here:
  - **A YouTube link becomes a station.** Paste an ordinary video link, a `youtu.be` short link, or a channel's live page (`youtube.com/@handle/live`) and Quill Radio treats it exactly like a radio station: it plays through the same player, sits in your favorites, records with **Record Now**, and can be captured by a **scheduled recording**. What gets saved is the *page* address, never a stream address -- YouTube's stream addresses expire after a few hours, so Quill Radio looks the audio up fresh every time the station plays or records. That is what lets a recording you schedule today still work next week. The small helper that does the looking-up, `yt-dlp`, is **built into the app**, so your first YouTube link simply plays -- there is no download to approve and nothing to set up. If YouTube changes how it serves audio (which happens from time to time) and links stop resolving, **Station > Update YouTube Support...** downloads the current version of that helper and uses it in place of the built-in copy from then on, so you do not have to wait for the next release of Quill Radio. It tells you which version you ended up with, is off in Safe Mode, and asks before it reaches the network. You should not need it otherwise. Because looking the audio up takes a moment, it happens in the background: you hear "Connecting" straight away and the window never freezes. A video that is private, removed, blocked in your region, or not live yet says so in plain words. YouTube stations are unavailable in Safe Mode.
  - **A YouTube playlist becomes a list you can browse.** Choose **Station > Add from YouTube Playlist...** and paste a playlist link (`youtube.com/playlist?list=...`). If the link is already on your clipboard, the box is filled in for you. Quill Radio lists the videos in it -- in the order the uploader put them, never re-sorted, because a series is meant to be worked through in order -- and each row reads as a whole sentence: its position, its title, how long it runs, and who published it, for example "3. Introducing layers, 5 minutes 31 seconds, 3Blue1Brown". Arrow the list and select what you want (hold Shift or Ctrl to pick several), then choose **Add Selected**, or take the lot with **Add All**. Each one becomes an ordinary station you can play, favorite, and record. Quill Radio tells you how many it added and how many were already in your favorites, so "Add All" on a fifty-video playlist never leaves you guessing whether anything happened. The listing itself is deliberately shallow: Quill Radio asks once for the whole playlist rather than once per video, and does not fetch any video's audio until you actually play it. One thing worth knowing: a *watch* link that happens to carry a `list=` in it -- which is what you get when you copy a link while a playlist is open -- is still treated as that single video. You asked for the video, and turning it into fifty stations without being asked would be a surprise, so only a genuine playlist address expands. The window is headed with the playlist's own name -- Quill Radio reads it from the same single request that fetched the list -- so you always know which playlist you are looking at. Playlists use the same built-in `yt-dlp` helper as any other YouTube link, and are unavailable in Safe Mode.

    **What adding a playlist does and does not do.** It is an *import*, not a subscription and not a play queue. The videos you choose become ordinary favorites -- each one plays, records, and can be scheduled exactly like a station -- and they land in your favorites list alongside everything else, not in a folder of their own. Nothing plays through the list in order: playing one video plays that video, and Quill Radio does not move on to the next when it ends. Nothing re-checks the playlist later either, so videos the uploader adds after you import are not picked up; run **Add from YouTube Playlist...** on the same link again to collect them (anything already in your favorites is skipped rather than duplicated). Group the imported videos yourself with **New Folder** (Ctrl+Shift+E) and the Favorites Manager if you want them kept together.
  - **What Quill Radio knows about a YouTube video.** Looking up a video's audio is one request, and that request answers with more than an audio address, so Quill Radio keeps all of it: how long the video is, who published it, its description, any chapters the uploader marked, and whether captions exist. None of it costs an extra moment or an extra connection. That is what makes the chapter, seeking, and speed controls on the Playback menu possible. A live broadcast reports no length, which is the honest answer for something with no ending yet.
  - **A Live365 link is fixed for you.** The Live365 link most people have is the station page (`live365.com/station/...`) or the web player (`player.live365.com/a25891`) -- both are web pages, and pasting one used to save a station that could never play, with nothing to explain why. Quill Radio now recognizes a Live365 station page, player link, or even a bare station id and rewrites it to that station's real stream address, telling you in the dialog that it did. Nothing is fetched or sent anywhere -- it is purely a matter of rewriting the text -- and a link that is not Live365 is used exactly as you typed it.
  - **Any other stream URL** is saved as you typed it, as always. A SecureNet player link (`securenetsystems.net/v5/...`) is saved as typed too, because unlike the two above its real stream address cannot be worked out from the link alone -- it has to be read from the page. Two things get you there: use **Find Streams from a Website...** below with the player link, or just save it and press Play, and the self-healing repair will find the stream for you on the first attempt.
- **When a station won't play, Quill Radio tries to fix it for you.** Some stations are listed in the directory but their stream address is dead -- often because the real stream is behind a player on the station's website. Instead of just failing, Quill Radio works down a short ladder: it re-resolves the address (for StreamTheWorld-style players that moved servers), refreshes the address from the directory, and -- if the setting is on -- scans the station's own website, following a "Listen Live"/"Play"/"Tune In" link into the player and recognizing Triton players there. If it finds one clear stream it plays it and remembers it for that favorite; if it finds several it tells you the count and you can open Find Streams to choose. The website step is the "Recover failed streams from the station's website" checkbox in Station > Preferences (Ctrl+,), on by default and off in Safe Mode. It only tries once per station per session.
- **Find Streams from a Website...** -- give it a website address; it scans that one page for stream links, with a Test button that toggles to Stop Test while a candidate plays. This now also works for many stations whose "Listen Live" button is a modern JavaScript player (Triton Digital / StreamTheWorld, including the whole `player.listenlive.co` network -- for example `player.listenlive.co/34461`). Those players build their stream address in code, so it is not written anywhere in the page for a scanner to read; Quill Radio recognizes the player, reads the station's call letters from the page, and looks the real stream up through the station provider's own public address service -- no browser, no guessing. Both the MP3 and the AAC stream are offered when a station publishes both. It also recognizes an **iHeart** or **TuneIn** station page pasted directly and resolves its real playable stream through that directory, instead of handing back a page address that will not play. It also handles **SecureNet's player** (`securenetsystems.net/v5/...`), used by a large number of American broadcasters, which failed for the opposite reason: that page *does* write its stream address out in plain text, but the address looks like nothing special -- `https://ice66.securenetsystems.net/ROM`, with no `.mp3` on the end and no `/stream` in the path -- so the scan used to file it with the page's ordinary links and throw it away, returning junk or nothing at all. Quill Radio now recognizes the player itself and offers the real stream first, whether you point it at the player page or at a station's own site with the player embedded. If a page is not one of these players or directories, or does not name its station, the scan simply behaves as before.
- **Manage Favorites...** -- the favorites, made organizable. See "The Favorites Manager" below.
- **New Folder...** (Ctrl+Shift+E) -- create a folder right where you want it: pick the location (top level or inside any existing folder), then name it. The folder exists immediately, ready for Move to Folder.
- **Import Stations from Playlist...** -- import an M3U or M3U8 playlist. Choose the file, then pick where the stations go: an existing folder, or type a brand-new folder path at any depth (like `News/Local`, created for you). If any of the playlist's stations are already in your favorites, Quill Radio tells you how many and asks whether to skip those duplicates or import everything. Station names come from the playlist's own `#EXTINF` lines; a bare URL is named after its host.
- **Export Favorites to Playlist...** -- the other direction: write your stations out to an M3U playlist file. Use it to hand your stations to any other media player, share your list with someone, or keep a plain-text copy you can read outside Quill Radio. Each station is written with the name you see (your custom name if you gave it one) and its stream address, so importing the file back brings the same stations in. M3U is a flat format with no notion of folders, so folder structure is not carried across -- exactly as importing one discards it.
- **Back Up Stations and Settings...** and **Restore from Backup...** -- save your favorites, settings, wake timer, and recording schedule (and, if you choose, your recorded audio) into one portable `.qrbackup` file, then bring it all back on a new device or after a reinstall. Back Up asks whether to include recordings (they can be large); Restore previews the backup and confirms before it replaces your current stations, and reloads the app so it takes effect right away.
- **Play Last Station** (Ctrl+L) -- resume whatever you last had on, one keystroke, no navigation.
- **Recently Played** (submenu) -- your last fifteen stations, newest first, playable inline.
- **Favorite Stations** (submenu) -- every favorite, nested by your folders, playable inline.
- **ACB Media** (submenu) -- ACB's whole stream directory, playable inline.
- **Resume Last Station on Launch** (check item) -- the appliance switch.
- **Start Quill Radio with Windows** (check item) -- have Quill Radio open by itself when you sign in. It adds (or removes) an entry just for your own account, so it needs no administrator rights and touches nothing for anyone else who uses the computer. Pair it with **Resume Last Station on Launch** and the radio is simply on when you sit down. (Windows only.)
- **Preferences...** (Ctrl+,) -- Resume Last Station on Launch, automatic Check for Updates, Announce dialog transitions (off by default -- turn on for more spoken detail around every dialog), When closing the window (Ask every time / Exit / Minimize to Tray -- governs the titlebar X, Station > Exit, and by default Alt+F4 too), **Alt+F4 minimizes to the system tray** (off by default: turn it on and Alt+F4 alone tucks the radio into the tray, still playing, while X and Exit keep the setting above -- the reflexive close stops meaning quit), **Playback engine** (Automatic -- recommended -- uses the bundled mpv engine, which powers the output device choice, pausing and rewinding live radio, Volume Boost, and stations in more formats; "Windows Media (classic)" is exactly the pre-1.1 behavior if you ever want it back), and **Radio output device** (route just the radio to a second sound card or USB headset -- your screen reader and Quill Radio's own sounds stay on the system default device; an unplugged device is remembered, not reset, and if it can't be used the radio plays through the default and says so). Every setting takes effect the moment you save -- switching engine or device mid-song reconnects the station right where it matters: on the new engine or device. Preferences also carries **Favorites sort order** (Ascending A to Z, Descending Z to A, or Unsorted -- how your folders and stations are ordered in the list; Ascending/Descending re-sort when you add a station, while Unsorted keeps your hand-arranged Move Up/Down order, which is never lost) and two troubleshooting settings: **Verbose logging** (a debug-mode checkbox that turns on detailed logging live, no restart, for when you need to diagnose something or attach detail to a bug report) and **Log folder** (choose where the log is written so it's easy to find; a failed recording captures the recorder's own error output into it as well). Finally, **Keep the computer awake while playing or recording** (on by default) stops Windows from going to sleep while a station is playing or a recording is running, so the audio never cuts off mid-listen; your screen can still turn off, and the moment nothing is playing or recording the setting lets the computer sleep normally again. Turn it off if you would rather Quill Radio never touch your power settings. (Windows only.) And **Winamp-style playback keys in the Recordings player** (on by default) governs the classic-skin letter keys -- X play, C pause, V stop, B next, Z previous, arrows to seek, T for elapsed or remaining, J to jump -- in the Recordings window; turn it off to type letters there for list typeahead instead. Ctrl+Up and Ctrl+Down still change the volume either way.
- **Send to Tray** (Ctrl+W) -- hide the window; playback continues from the notification area.
- **Exit** -- quit Quill Radio. Closing the window this way, from the titlebar X, or with Alt+F4 all ask first (unless you've told it not to, or set a fixed answer in Preferences): Exit, Minimize to Tray, or Cancel, with a "Don't ask me again" checkbox. Recording in progress is called out in the message, since exiting stops it. And if "Alt+F4 minimizes to the system tray" is on in Preferences, Alt+F4 skips all of this and simply tucks the radio into the tray, still playing.

### Playback (Alt+P)

- A live (disabled) now-playing line at the top, so the menu itself tells you what is on.
- **Play / Stop** (Ctrl+P) -- one transport item that reads Play when idle and Stop while connecting or playing, exactly like the panel button.
- **Mute/Unmute** (Ctrl+M), **Volume Up** (Ctrl+Up), **Volume Down** (Ctrl+Down). Ctrl+Up and Ctrl+Down work from **anywhere in the window** -- the favorites tree, a button, the status bar -- with one sensible exception: inside a text box, Ctrl+arrow still moves and edits text, as it should. Two things are remembered. Each **favorite** remembers the volume you set while it plays and gets it back the next time it starts, because stations are mastered wildly differently and you should only have to fix that once per station. And the **last level you set** is remembered across sessions for everything else, so a station that is not a favorite comes back where you left it rather than at full volume the next time you launch. (A favorite's own remembered level always wins over the general one.)
- **Output Device...** (Ctrl+Shift+D) -- pick which sound card or headset the radio plays through, in one keystroke, without opening Preferences. Choose a device and the station moves to it immediately; the choice is remembered, and it is the same setting as **Radio output device** in Preferences, so the two always agree. Your screen reader and Quill Radio's own announcements stay on the system default device. Needs the mpv playback engine (the default).
- **Volume Boost** (Ctrl+Shift+B, check item) -- amplifies up to 50% past full volume for stations that just broadcast quiet. Your 0-100 volume scale, per-station volume memories, and mute all behave exactly as before; the boost is applied on top. Needs the mpv playback engine (the default -- see Preferences below).
- **Rewind 30 Seconds** (Ctrl+Shift+Left), **Forward 30 Seconds** (Ctrl+Shift+Right), **Back to Live** (Ctrl+Shift+L) -- live radio you can move around in. On the mpv playback engine (the default), Quill Radio keeps a rolling buffer of the stream (roughly 45 minutes at typical bitrates): jump back to catch a missed sentence, work your way forward, then leap straight back to live. Every move announces how far behind live you are. Needs the mpv playback engine.
  - **A note on pausing.** Whether Play/Stop *holds your place* or *rejoins live* depends on the engine. On the **mpv** engine, pausing keeps your position in the rolling buffer, so Play resumes exactly where you stopped. On the **Windows Media (classic)** engine there is no buffer, so pausing a live stream and pressing Play again reconnects at the current live moment -- it looks like the stream simply refreshed. If you press Play/Stop expecting to resume where you left off and instead hear live audio, open **Station > Preferences (Ctrl+,)** and set **Playback engine** to **Automatic** (which uses mpv); the buffer, Rewind/Forward, and Back to Live all require that engine. (A live stream also only rewinds as far back as the buffer has actually filled since you started listening.)
- **Chapters...** (Ctrl+Shift+C), **Next Chapter** (Ctrl+Alt+Right), **Previous Chapter** (Ctrl+Alt+Left) -- a finished YouTube video has a timeline, so you can move around it the way a live broadcast never lets you. Chapters opens the uploader's own chapter list, each entry read as a whole sentence ("3. Introducing layers, starts at 5 minutes 31 seconds") with the one playing now marked; Enter jumps to it. Previous Chapter restarts the current chapter first, then steps back, the way a CD player does. **Rewind / Forward 30 Seconds** (Ctrl+Shift+Left / Ctrl+Shift+Right) move along the video's own timeline -- the same keys move within live radio's rolling buffer when a live stream is playing, and Quill Radio picks the right one for what you are listening to. On a video they say where you landed ("3 minutes 10 seconds of 18 minutes 40 seconds"); on a live stream they say how far behind live you are. **Go to Position...** (Ctrl+Shift+J) jumps straight to an exact time, using the same accessible Hours / Minutes / Seconds dialog the Quill Media Player uses -- three labelled spin controls, plus a timecode field if you would rather type `1:23:45`. **Where Am I?** (Ctrl+Shift+P) speaks your position, the length, and the chapter you are in.
- **Play Faster** (Ctrl+Alt+Up), **Play Slower** (Ctrl+Alt+Down), **Normal Speed** (Ctrl+Alt+0) -- speed for a finished video, stepping through round, speakable values from 0.25x to 4x rather than drifting by a multiplier. The speed you choose is remembered for the next video. Live radio plays at normal speed; setting a speed while a station is on says so, and remembers it for when a video plays.
  - **All of these say why when they decline.** Ask for chapters, seeking, or speed while a live stream is playing and you hear "This is a live stream, so there is no timeline to move along"; ask for chapters on a video whose uploader published none and it says that instead. A control that quietly does nothing is worse than one that is not offered, because you cannot tell it apart from a broken app.
- **What's Playing?** (Ctrl+T) -- opens a reviewable Now Playing window: the current title and artist in a read-only, selectable field you can arrow through **character by character** to catch an exact spelling, with a **Copy** button. It reads the title straight from the stream's own metadata (and if no title has arrived yet, Ctrl+T speaks and fetches it, as before). When a station sends messy broadcast metadata (a string of catalog codes rather than a clean "Artist - Title"), Quill Radio finds the title and artist in it and reads just those. And when a station answers with nothing at all -- no metadata, and the playback engine's own title channel is empty too (common on HLS) -- Quill Radio takes one more step: it reads the current title from the stream server's own public "now playing" status page (the Icecast or SHOUTcast status endpoint). It only ever asks the same server you are already listening to, and it is off in Safe Mode -- so a batch of stations that used to answer with silence now report a real title. You control the wording in Station > Preferences (Ctrl+,) with a small template: `{title}` and `{artist}` tokens, `[square brackets]` around optional wording that disappears when a field is empty (the default `{title}[ by {artist}]` drops the " by" when there's no artist), and `{raw}` for the stream's exact original text. Leave it blank to restore the default.
- **Copy What's Playing** (Command Palette) -- copies the current title and artist straight to the clipboard without opening the Now Playing window (which Ctrl+T opens, above). You no longer have to press What's Playing first: if a station is on and no title has arrived yet, Quill Radio says "Checking what's playing...", fetches it, and then copies it. Both this and the Ctrl+T window always tell you *something* -- a stream that sends no titles at all says so and still opens a window naming the station, and a lookup that fails is reported rather than passing in silence. The confirmation names what it copied, so you know it worked without pasting to check.
- **Use One Volume for All Stations** (check item) -- Quill Radio normally remembers a volume for each favorite, which is lovely when stations are mastered at wildly different levels and maddening when you simply want everything quieter: with twenty favorites, there were twenty places to turn the volume down. Tick this and a single level answers for every station, so Ctrl+Up and Ctrl+Down turn *everything* up or down. Ticking it adopts whatever you are hearing at that moment, so nothing jumps. Your per-station levels are not thrown away -- untick it and every station goes straight back to its own remembered volume. Off unless you turn it on.
- **Forget Every Station's Own Volume...** -- the deliberate way to be rid of those per-station levels rather than merely bypassing them: it tells you how many stations have one, asks first, and leaves your stations, folders, and every other setting untouched.
- **Song History...** (Ctrl+Shift+H) -- what each station played earlier. What's Playing tells you the song on right now and then forgets it; this is the memory behind it. Choose a station at the top, then arrow the list: each entry reads as a whole sentence, such as "Your Song by Elton John, heard 10:04, played twice", newest first. From a selected song, **Copy** puts it on the clipboard, **Send to Clip Library** keeps it with your other saved snippets, and **Background** asks whichever AI provider you have set up for a short note about the song and artist. That answer always begins by saying it was written by an AI model rather than by the station -- it sits inches from the station's own information, and the two must never be confused -- and it is never available in Safe Mode; with no provider set up, the window simply says so. **Clear...** empties one station's list or every station's. The log keeps up to 200 songs per station, one station's listening never pushes out another's, and it never leaves your machine. A song still playing when Quill Radio checks again folds into the entry already there with a play count, rather than filling the list with the same title six times, and stations that broadcast their own name, "Live", or an advert marker instead of a track are left out. To stop keeping the list at all, turn off **Keep a song history for each station** in Preferences; entries already saved stay until you clear them.
- **Announce Track Titles** (check item) -- when on, title changes are announced as they happen. Off by default. On the Command Palette this entry names its own state, so it reads **Announce Track Titles (currently On)** or **(currently Off)** -- the palette has no checkmark, and you should not have to throw a switch to find out which way it is set.
- **Sleep Timer...** -- fade out and stop after a set time, restoring your volume.
- **Wake-Up Timer...** -- the sleep timer's twin: pick a favorite, a time, once or every day, and the station starts playing by itself. Quill Radio must be running (the tray counts).
- **Sound Enhancements...** -- a three-band equalizer (Bass, Mid, Treble sliders, -12 to +12 dB each, freely adjustable), a compressor ("Even Out Volume", boosts quiet passages and tames loud ones), a **Channel mode** choice (Stereo, Mono, Left only, Right only) and **Night mode**. Channel mode routes the audio for accessibility: **Mono** blends both stereo channels into one, so a station that hard-pans a voice to one side never disappears with single-sided hearing or a single earbud; **Left only** or **Right only** sends the whole stereo mix (nothing is lost) to just that one ear and silences the other, so you can listen to the radio in one ear while your screen reader (or anything else) uses the other. **Night mode** evens loudness in real time by lifting quiet passages -- the complement to Even Out Volume taming loud ones; ideal for low-volume late-night listening. A "Quick preset" combo box (Flat, Bass Boost, Voice Clarity, Podcast, Small Speakers, Late Night) sets all three sliders at once as a starting point -- move any slider afterward and it becomes Custom. Off by default. The dialog also has a **Broadcast polish (OptiLab)** section: an **Apply broadcast polish** checkbox (a bypass that keeps your chosen mode while turned off), a **Polish mode** choice -- **Podcast Leveler** for speech, **Stream Polish** for music, or **Smooth Limiter** for clean peak control -- an **Input** trim in decibels (0, no change, by default), and an **Auto-Adapt** slider (0-100%). Broadcast polish levels quiet and loud passages, adds density, and limits peaks, so a run of stations at very different loudness sits at a steadier, fuller level -- especially handy for talk streams and unattended recordings. In **Stream Polish**, Auto-Adapt is staged rather than a single "more of everything" control (following OptiLab Core 1.4.0): each part of the chain fades in over its own portion of the slider, the leveler eases off as you raise it while a slow loudness lift takes over, that lift ignores silence and low-level noise so it cannot build gain on nothing, and high frequencies come under firmer control toward the top instead of being boosted. The practical effect is that high settings sound louder and steadier rather than more processed, with no point where something audibly switches on. **Podcast Leveler** and **Smooth Limiter** respond to Auto-Adapt more simply, leaning their leveling and density more assertive as you raise it. It is adapted, with thanks and credit, from OptiLab Core by dgl1984 (https://github.com/dgl1984/optilab, Apache-2.0); it is a faithful adaptation of that plugin's three modes rather than the plugin itself.

**Every control previews live.** As you move a slider or change any setting -- EQ, compressor, channel mode, night mode, or broadcast polish -- you hear it on what's playing right away, without pressing OK (on the default mpv engine it applies with no interruption; on the Windows Media engine it reconnects once the change settles). **OK** keeps and saves the settings; **Cancel** (or Escape) puts everything back the way it was when you opened the dialog.

**Every setting is remembered per station as well as shared.** The whole dialog -- EQ, compressor, channel mode, night mode, and broadcast polish -- is saved per station when you open it while a favorite is playing (so one station can be routed to one ear, or given its own broadcast polish, and remembered); with nothing playing, or a non-favorite on, you are setting the shared default every other station follows. The per-station Reset to Default button and Preferences' Reset All Stations' Sound Enhancements both drop a station back to that shared default.

### Record (Alt+R)

- **Record Now / Stop Recording** -- capture the station you are listening to. When a capture begins, Quill Radio announces "Recording started" with the station name, so it is always clear the command took effect. This command follows what you are listening to: if the station on now is the one recording, it stops that recording; otherwise it starts a new one. A recording of a *different* station running in the background is never stopped by Record Now -- stop those from the Recordings window.
- **Record Station...** -- record a *different* station for a set number of minutes while you listen to something else (or to nothing). The recorder is its own process; it never needed the player. You can start as many of these as you like -- they all record at once (see "Recording several stations at once" below).
- **Stop All Recordings** -- stop every recording in progress at once. (It is also in the tray/status menu, and appears as a button in the Recordings window when two or more recordings are running.)
- **Schedule Recording...** -- record a show later, once, daily, or weekly, even from the tray. Pick a favorite from the list and its name and stream fill in for you (both stay editable for one-off streams). Enter the time however you think of it -- "7:30 PM" or "19:30", both are understood -- and pin each entry to its own **time zone** (defaulting to your local time), so a show quoted in another zone records at the right moment and the list shows each entry's time with its zone. Set how long to record with the **Hours** (0-24) and **Minutes** (0-59) fields -- a three-hour show is simply "3" and "0", no arithmetic. The schedule is something you manage, not just add to:
  - **Edit** -- change a selected entry's station, time, duration, or repeat *in place*, without deleting and re-adding it. The Add button relabels to **Save Changes** while you edit, and the status line names the entry you are editing so it is always clear you are changing that one, not adding a new one. Choose **New** to abandon the edit and start a fresh entry instead.
  - **Duplicate** -- start a **new, independent** entry pre-filled from the selected one (its name gets " (copy)"), as a quick starting point for another day or a second time slot. It keeps the original's stream URL until you change it, so pick a different favorite or edit the URL if you meant a different station; the two are separate schedules from the moment you choose **Add Schedule**.
  - **Enable / disable** -- turn an entry off without losing it; a disabled entry reads "(disabled)" in the list and does not fire, and you can turn it back on any time.
  - **Remove** names the schedule it will delete and dims when none is selected; the Delete key and a context menu work on the list too.
  The list is ordered by **when each recording next occurs** (the soonest first), not the order you entered them, and each row shows the stream's host in brackets so two similar entries -- or a duplicate that still points at the original station -- are easy to tell apart. After you choose **Add Schedule** (or **Save Changes**), focus moves to your entry in the list, and the form clears for the next one, so you are never left on the Add button wondering whether it worked.

  A schedule is due from its start time through the end of its duration, so if Quill Radio reaches a few seconds late it still starts with the remaining minutes, and on launch it catches up anything whose window is still open. (Quill Radio has to be running for a scheduled recording to fire -- the tray icon counts -- so a show whose whole window passed while Quill Radio was closed is simply missed, and the next launch tells you, naming up to three and collapsing the rest to a count.)

#### Scheduling a recording, step by step

The one thing to remember: you **fill in the details first, then choose Add Schedule last** -- Add is the button that commits the entry you have just described, not a "start a new form" button.

1. Open **Record > Schedule Recording...** (Alt+R, then Schedule Recording).
2. In the **Station** list, pick a favorite -- its name and stream URL fill in for you. (You can only choose from your favorites here; add the station to Favorites first if it is not listed. For a one-off stream, type the name and paste the URL by hand instead.)
3. Set the **time** ("7:30 PM" or "19:30", whichever you think in) and choose a **time zone** if the show is quoted in one other than your own (otherwise leave it at "(local time)").
4. Choose how often: **Once** (also pick a date), **Daily**, or **Weekly** (also pick the weekday).
5. Set the length with **Hours** (0-24) and **Minutes** (0-59) -- a three-hour show is just "3" and "0".
6. Choose **Add Schedule**. Your entry appears in the list (ordered by when it will next record), focus lands on it, and the form clears so you can add another the same way.

To change one later, select it and choose **Edit** (the button becomes **Save Changes**); to make a similar one, select it and choose **Duplicate**, adjust the fields, and choose **Add Schedule** again.
- **Recordings...** -- everything you have recorded, live. See "The Recordings list" below.
- **Recording Settings...** -- format (MP3, OGG, FLAC, WAV, or **Raw stream** -- see below), bitrate, **destination folder** (recordings land in **Music\Quill Radio Recordings** under your user folder unless you point them somewhere else -- somewhere you can actually find them, not a buried application folder), an optional **Temporary folder (while recording)** (set one and a recording is written there and moved to your destination the moment it finishes, so a half-written file never appears among your finished recordings and a fast scratch disk can absorb the writing; leave it blank to record straight to the destination, and if the move ever fails the finished file is left safely in the temporary folder rather than lost), filename pattern, a maximum-length safety cap, **Maximum simultaneous recordings** (0 = unlimited, the default -- see "Recording several stations at once" below), the **If the connection drops** section (reconnect on/off, how many attempts, and how many seconds between them), and **Apply Sound Enhancements to recordings** -- off by default, so recordings stay an unfiltered archival copy even with Sound Enhancements on for live listening; turn it on to record the filtered (EQ/compressor) audio instead, for every recording method (Record Now, Record Station, and scheduled recordings alike).

### Recording several stations at once

Quill Radio records as many stations at the same time as you want. Start a Record Station capture, then another, then another -- each records independently while you go on listening to whatever you like. Overlapping **scheduled** recordings all fire too: two shows booked for the same hour both record, where before only one would and the rest were dropped.

Each recording is fully self-contained -- its own connection, its own reconnect-on-a-hiccup handling (below), its own crash-resume -- so one recording dropping, finishing, or being stopped never affects the others. This now covers a stream that *stalls* -- a connection that goes quiet without cleanly disconnecting (a pulled Ethernet cable, a dropped Wi-Fi adaptor) -- which used to leave a recording wedged: still shown as "recording" but no longer growing. Quill Radio detects the stall within about half a minute and either reconnects and continues into a "(part 2)" file or, if reconnection is off or the show's window has ended, stops and saves what it captured.

There is now a second check behind that one, and it does not depend on the connection reporting anything at all: Quill Radio simply watches whether the recording **file is still growing**. A recording that is capturing audio always grows. If the file has not gained a single byte across four checks in a row -- about a minute -- the stream is not recording, whatever it claims, and Quill Radio treats it exactly like a dropped connection: it reconnects and continues, or stops and saves what it has. It is deliberately patient, so a slow network or a station's own momentary rebuffering is never mistaken for a dead one, and it is never applied to a recording you have just asked to stop (that one is *meant* to stop growing).

Recording filenames use your computer's **current** time zone. If you change the computer's time zone (or it shifts for daylight saving) while Quill Radio is running, new recordings are named with the new local time straight away -- no restart needed.

If you would rather cap it (a slower machine, a metered connection), set **Maximum simultaneous recordings** in Recording Settings to a number; **0** means unlimited, which is the default. When the cap is reached, a scheduled recording that would exceed it is held pending and retried while its window is still open, rather than being lost.

To stop recordings: **Record Now** stops the recording of the station you are listening to; the Recordings window's **Stop Recording** button stops the one you have selected there; and **Stop All Recordings** (Record menu, tray/status menu, or the button that appears in the Recordings window when two or more are running) stops every one at once.

### Raw stream recording (lossless capture)

The **Raw stream -- exactly as sent, no re-encoding (lossless)** format in Recording Settings saves a recording that is bit-for-bit identical to what the station broadcasts. The MP3/OGG/FLAC/WAV formats decode the incoming audio and re-encode it to your chosen format; the raw option skips all of that and copies the station's own audio packets straight to disk, untouched. Choose it when you want the cleanest possible source to edit or convert yourself, with no quality lost to a second encoding.

Quill Radio picks the file type for you from the stream's own format: an MP3 stream is saved as a `.mp3` file, AAC as `.aac`, Ogg Vorbis as `.ogg`, Opus as `.opus`, FLAC as `.flac`. Anything unusual is saved into a Matroska `.mka` file, a container that holds any kind of audio losslessly and opens in players like VLC. Because nothing is being re-encoded, the Bitrate setting and Apply Sound Enhancements have no effect on a raw recording and are simply ignored. If a recording is interrupted and continues into a "(part 2)" file, that part keeps the same file type as the recording it continues.

### View (Alt+V)

- **Show Station Details** -- shows or hides the read-only details box (source, stream, format, country) in Browse Stations and Search Stations. On by default; turn it off if you would rather not tab past it. Every station surface honors the choice, and it is remembered between sessions.
- **Show Status Bar** -- shows or hides the status strip along the bottom of the main window (Now playing, Volume, Recording, Sleep timer, Favorites count, and the time). On by default. Reach the bar with **F6** and arrow across it; see "The main window" above for the full navigation.
- **Sort Favorites** -- Ascending (A to Z), Descending (Z to A), or Unsorted (your manual order). This is the same setting as the one in Preferences, put here so it is quick to reach; the current order is shown with a bullet. Choosing Unsorted reveals the hand-arranged order you built with Move Up/Down.
- **Expand All Folders** / **Collapse All Folders** -- open or close every folder in the favorites tree at once.
- **Customize Features...** -- turn whole areas of Quill Radio off if you never use them. The list shows each switchable area with a short description of what it covers -- the **Recording** menu (recording, scheduling, and the recordings list) and the **Weather** menu -- and unchecking one leaves out that whole menu, and every command under it, the next time you open the app. Nothing is deleted and nothing is lost; tick it again and it comes back. Everything is switched on to begin with, and a feature added in a future version arrives switched on too, so you only ever have to turn *off* what you do not want. Handy if you want a plain radio and nothing else to arrow past.
- **Text Size** -- Normal, Large, or Larger. Scales the text on the main window (the favorites list, the buttons, the now-playing line, and the status bar) up for easier reading. Remembered between sessions.

### Help (Alt+H)

- **Command Palette...** (Ctrl+Shift+P) -- every Quill Radio command in one searchable list.
- **Keyboard Shortcuts...** -- open the Keyboard Manager to view, search, and change Quill Radio's keyboard shortcuts (see "Global hotkeys and keyboard shortcuts" below).
- **Global Hotkeys...** -- assign a system-wide key to Quill Radio's playback controls so they work while another program has focus (see below).
- **Redeem Unlock Code...** -- enter a signed code for a pre-release capability. Verified entirely on your machine; nothing is transmitted; one code counts for QUILL, Quill Radio, and QUILL Cast together.
- **Check for Updates...** -- compares your version with the newest release, downloads the right artifact for your flavor directly (the installer for an installed copy, the portable zip for a portable one) with spoken progress, then offers Install now or Open folder. Already up to date shows a dialog too, not just a spoken announcement. Quill Radio also runs this check quietly once a day when it launches -- silent unless it actually finds something, and Station > Preferences (Ctrl+,) turns it off if you'd rather check manually only.
- **Get FFmpeg...** -- a safety net: FFmpeg ships inside Quill Radio, but if it ever goes missing this downloads the official build so recording works again.
- **User Guide** / **Release Notes** / **Product Requirements...** -- this guide, the version history, and the product requirements document, each opened right in your browser.
- **Report a Bug...** -- files an issue directly from the app (no GitHub account needed), stamped "Quill Radio" with this app's own version so we know exactly what you were running; falls back to the online support form if anything goes wrong.
- **Repeat Last Announcement** and **Announcement Self-Test...** (Command Palette) -- speech disappears the moment it finishes, so Repeat Last Announcement says the last thing Quill Radio told you all over again. The Self-Test announces a test phrase and then reports which channels actually delivered it -- speech, braille, sound -- and which screen-reader connection served each. It is the quickest way to tell "braille is not working" apart from "no braille display is connected", which otherwise look identical.
- **About Quill Radio** -- version, sync statement, project address.

## The Favorites Manager

Station > Manage Favorites... is a full organizer, keyboard-first:

- **Search favorites** filters live across names (including your custom names), countries, languages, tags, and folder names; results flatten into one arrow-key list with each station's folder spoken in its label.
- **Folders of any depth.** Create one with **New Folder...** (Ctrl+Shift+E) -- pick its location, name it, and it exists immediately, even before a station lives in it. Or just file a station under "News/Morning" and the path springs into being. Rename a folder (F2) and its subfolders come along; delete one and its stations simply step out to the top level -- nothing is ever deleted with a folder.
- **Reordering.** Move Up / Move Down within a folder; for long hops, **Mark for Move**, select the destination, then **Move Above** or **Move Below** -- the moved station joins the destination's folder. Reordering is your hand-arranged "Unsorted" order, and the Move buttons work from any view: if the list is currently sorted Ascending or Descending, the first move switches to manual order (revealing your saved order, announced "Switched to manual order") and moves the station within it -- exactly like Alt+Shift+Up/Down on the main page. Your stored order is preserved, never overwritten by the alphabetical view, so a hand-arranged list can't be lost.
- **Remove All...** clears every favorite at once (your folders stay) after a confirmation that defaults to No. Because favorites keep a rolling backup, an accidental Remove All can still be recovered.
- **Sort order.** Preferences (Ctrl+,) sets the default order for every folder -- Ascending (A to Z), Descending (Z to A), or Unsorted. Any single folder can override that from its context menu (**Sort This Folder...** on the main-page tree): choose Ascending, Descending, Unsorted, or "follow the default" just for that folder's stations. Ascending/Descending re-sort automatically as you add stations.
- **Rename** (F2 on a station) gives it your own display name everywhere; blank restores the directory's name.
- Enter plays (the Play button reads Stop while that station is on), Delete removes (with confirmation), Shift+F10 opens every action on the selected item. The main-page tree offers the same actions, so the Manager is for the heavy lifting, not a required stop.

## The Recordings list

Record > Recordings... shows the whole recording life cycle in one place. The list updates rows in place keyed by file path, so it is a no-op when nothing has changed; when something has, your selection, focus, and scroll position are preserved instead of the list rebuilding under you mid-read:

- Every recording being written right now -- each its own **Recording** row, its size growing as you watch, with its own live elapsed time. They are counted from the recorder itself, so a recording still being written to the temp folder is always visible here, never invisible until it lands. When several are running, each is its own row.
- Every finished file, newest first -- status **Recorded**, with size and date.
- Upcoming scheduled recordings -- status **Scheduled**, with their zone-labeled times.

The recording and scheduled counts are accurate: a schedule that is currently firing is not double-counted, and a completed one-time schedule drops out of the scheduled count rather than lingering.

Actions: **Play** (through the app's own player; it reads **Stop** while that recording is playing), **Stop Recording** (stops the recording selected in the list), **Stop All Recordings** (appears when two or more are running -- stops every one), **Open in Folder**, **Remove** (Delete key, with confirmation), **Refresh**. While a recording plays back, **Ctrl+Up** and **Ctrl+Down** change its volume right here, the same as they do for live radio. The tray tooltip carries "(recording)" -- or "(2 recording)" while a recording is active.

### Winamp keys in the Recordings list

If you came to Windows audio through Winamp, its classic-skin keys are almost certainly still in your fingers. They work here, on the letter keys you already know -- no modifier, no menu:

| Key | What it does |
| --- | --- |
| X | Play the selected recording (or resume a paused one) |
| C | Pause / unpause |
| V | Stop |
| Shift+V | Stop (Winamp's fade-out; this player has no fade, so it stops cleanly) |
| B | Next recording -- moves down the list and plays it |
| Z | Previous recording |
| Left / Right | Back / forward 5 seconds |
| Shift+Left / Shift+Right | Back / forward 30 seconds |
| R | Shuffle on / off |
| S | Repeat: off, then all recordings, then this recording |
| Ctrl+V | Stop after the current recording (a one-shot) |
| T | Read out elapsed time, or time remaining -- press again to swap |
| J | Jump to a recording: type any part of its name |
| Ctrl+J | Jump to a time: type `90`, `1:30`, or `1:02:03` |
| L | Open (plays the selected recording -- the same as Play) |
| Ctrl+Up / Ctrl+Down | Volume up / down |

Every one of them says what it did, so you never have to guess whether the key landed.

Two deliberate differences from Winamp:

- **Ctrl+T stays What's Playing**, which is the more useful thing to have on that key in a radio app. Winamp's elapsed/remaining toggle is on plain **T** here instead.
- **Up and Down arrow move through the list**, not the volume. That is what Winamp itself does in its Playlist Editor, and this list is a playlist editor by any other name. Volume is on Ctrl+Up and Ctrl+Down, where it has always been.

Seeking needs a recording with a timeline, which means the mpv playback engine; on a live stream or with the classic Windows Media engine the seek keys say why they cannot move rather than doing nothing.

Turn the letter keys off with **Winamp-style playback keys in the Recordings player** in Preferences (Ctrl+,) -- worth doing if you would rather type a letter to jump through the list. Ctrl+Up and Ctrl+Down are unaffected either way.

**Shuffle, repeat, and stop-after-current now work**, because the Recordings list has a play queue. They were deliberately unbound before: all three describe a queue that did not exist, and a key that only looks like it worked is worse than a key that is not offered.

- **R** turns shuffle on and off. Shuffle here is a **fixed order**, not a fresh roll each time you press Next -- so every recording plays once before any of them repeats, and **Z** reliably takes you back to the one you just heard. "Pick at random each time" can do neither.
- **S** cycles repeat: off, then all recordings, then this recording. Repeat-one applies when a recording *finishes on its own*; pressing **B** still moves on, because a Next that refused to move would look broken.
- **Ctrl+V** stops after the current recording. It is a one-shot: it clears itself the moment it fires, and it outranks repeat, because it is the thing you asked for just now rather than a standing preference. It is deliberately not remembered between sessions -- a stop that survived a restart would halt playback for a reason nobody could remember asking for.

A recording that reaches its end on its own is now followed by whatever the queue says is next. Shuffle and repeat are remembered between sessions.

### If the internet hiccups during a recording

ffmpeg first rides out short gaps itself (the reconnect settings in Recording Settings). If the connection truly dies, Quill Radio waits and resumes into a numbered **part file**, announcing each attempt. Then, when the recording finally finishes, **Quill Radio stitches the pieces back into one file** -- so a show that dropped twice leaves you with one recording under the name you expected, not three files to find and play in order. You are told which happened: "Joined 3 parts into one recording", or, if they could not be joined, "Kept 3 separate parts" and the reason. Three things keep that tidy:

- The parts are stitched back together when the recording ends. The join is a straight copy -- nothing is re-encoded, so no quality is lost and even a three-hour capture takes seconds -- and it is done carefully: the joined recording is written, checked, and only then put in place, and the part files are removed only once that has verifiably worked. If anything at all goes wrong, every part is left exactly where it is and Quill Radio says so. A failed join never costs you the recording.
- A continuation records only the *remaining* time to the original scheduled end, not a fresh full duration -- a 60-minute show that drops at minute 50 records a ~10 minute continuation, not another 60.
- A drop is classified before any reconnect attempt is spent, and only a genuinely-terminal failure gives up: your disk is full, or the server returned an HTTP 404, 410, or 451 that means the stream is truly gone. Everything else -- a network hiccup, a 5xx, or a momentary 403 Forbidden from an expiring or rotating stream token -- is transient and reconnects. (A transient error ffmpeg has already recovered from can no longer be mistaken for a fatal one when the stream later drops for an unrelated reason, so a recording is far less likely to stop short.)

Reconnect handling is per recording, so when several are recording at once each rides out its own hiccups without touching the others. And crash-resume covers all of them: if Quill Radio closes unexpectedly while several recordings were running, the next launch offers to resume every interrupted one -- a single prompt for one recording, or one batched "Resume all?" prompt when there were several.

Output filenames are never silently overwritten: a pattern that produces the same name twice gets `" (2)"`, `" (3)"` appended instead of clobbering the earlier file, and part files keep the original start timestamp in their name so they group together. And on Windows, the FFmpeg child is tied to Quill Radio's lifetime through a job object, so a crashed or killed Quill Radio takes it down rather than stranding a bare recording writing to your temp folder.

### If a recording was in progress when Quill Radio quit or crashed

A recording used to be lost the moment Quill Radio quit or crashed. It now remembers an in-progress recording and offers to pick it back up. On the next launch it first tidies the temp folder (any finished orphan file is moved to your recordings folder; a file still being written is left untouched), then, if a recording was in progress and is still within a 10-minute grace window, asks once in an accessible dialog:

> A recording of WQXR was in progress until 9:00 AM. Resume it for the remaining 12 minute(s)?

**Resume** (Enter) restarts the recording for the remaining minutes only. **Skip** (Escape) leaves it as it is. A **Don't ask me again** checkbox remembers your choice -- always resume, or never ask -- changeable later in Preferences. Nothing happens when nothing was in progress, and a corrupt marker is discarded rather than driving a bogus resume.

## Spotify (experimental)

Quill Radio can search Spotify, browse your library and playlists, and play through Spotify's own playback engine. This is an **experimental** capability: it ships in the app, but it needs setting up first. Nothing reaches Spotify until you deliberately connect an account.

### Does a free Spotify account work?

**Yes for finding things; no for playing them inside Quill Radio.** That distinction matters, because it is easy to hear "Premium required" and assume a free account is useless here. It is not.

**On a free account you can:**

- Search Spotify from inside Quill Radio.
- Browse your saved shows, episodes, tracks, and playlists.

**On a free account you cannot:**

- Have audio start *inside Quill Radio*. A track chosen here will not sound.

**Why, and what this is not.** This is not "free accounts cannot play Spotify music" -- of course they can, and millions of people do every day, in Spotify's own app, where the advertising that funds the free tier lives. The restriction is about **where** the audio plays, not whether you may listen. Spotify does not license other applications to stream free-tier audio, and says so in its own developer documentation. There are exactly two ways another app could play a Spotify track, and both are closed to free accounts:

- The **Web Playback SDK**, which "requires a Spotify Premium subscription (mobile only types of premium subscriptions are excluded)".
- The **Start/Resume Playback** endpoint, of which Spotify says: "This API only works for users who have Spotify Premium."

So with a free account, the sensible way to use this is to let Quill Radio do the *finding* -- which is the part that is genuinely awkward with a screen reader -- and play what you find in the Spotify app.

Quill Radio tells you which kind of account you signed in with straight away, so you are never left wondering why a track will not start.

For the same reason, a Spotify selection can never be recorded or downloaded on any account, unlike every other station in the app: the audio is copy-protected.

### What you need

| Requirement | Why it is needed |
| --- | --- |
| A Spotify account | Free or Premium. Free searches and browses; only Premium plays (see above). |
| Your own Spotify Client ID | Quill Radio does not ship a Spotify app identity; you supply your own, so nothing of yours passes through anyone else's. The steps are below. There is no client secret to copy -- Quill Radio signs in with the modern Authorization Code with PKCE flow, which needs only the Client ID. |
| Windows with the Edge WebView2 runtime | Spotify audio is copy-protected and can only be played by Spotify's own Web Playback engine, which runs inside a hidden Microsoft Edge WebView2 component. The WebView2 runtime is part of current Windows (it ships with Microsoft Edge), so it is normally already present. |

### Getting your Client ID, step by step

1. Go to the **Spotify Developer Dashboard** at `https://developer.spotify.com/dashboard` and sign in with your ordinary Spotify account. There is no charge, and this works with a free account.
2. Choose **Create app**.
3. Give it any **App name** and **App description** you like -- they are only for you. "Quill Radio" is fine.
4. In **Redirect URI**, enter exactly `http://127.0.0.1:43217/callback` and press **Add**. It must match character for character, including the port number. That address is how Spotify hands the finished sign-in back to your own computer; nothing leaves your machine through it.
5. Under **Which API/SDKs are you planning to use?**, tick **Web API** and **Web Playback SDK**.
6. Accept the terms and choose **Save**.
7. Open your new app's **Settings**. Your **Client ID** is shown there -- copy it. You will also see a **Client secret**: **you do not need it**, and you should not paste it anywhere.

### Where to put it in Quill Radio

Unless you are in Safe Mode, two items sit in the **Help** menu: **Connect to Spotify...** and **Browse Spotify...** If you would rather not see them at all, turn **Spotify** off in **Manage Individual Features** and they disappear.

Choose **Station > Connect to Spotify...**, paste your Client ID into the **Client ID** field, and choose **Connect**. You do this once.

### Connecting to Spotify

Choose **Station > Connect to Spotify...** to open an accessible sign-in dialog. Enter your Client ID and start the sign-in: your web browser opens to Spotify's own approval page, you approve access, and Spotify sends you back to a tiny local address on your own machine (`127.0.0.1`) that Quill Radio is listening on for exactly that one moment. Quill Radio captures the result and stores your sign-in tokens in the **Windows credential vault** -- never in a plain file, never in `podcasts.json` or a log. Your Client ID is stored alongside them so the whole connection lives in one place and clears together.

### Browsing and playing

Choose **Station > Browse Spotify...** to open an accessible search box with a results list. Type what you are looking for, arrow to a result, and press **Enter** to play it. A Spotify item plays through the hidden Web Playback engine, which coexists with Quill Radio's normal mpv and Windows Media engines -- a Spotify selection is routed to it automatically, and everything you already know keeps working: the one transport control (Play/Stop), volume, the status-bar mini-player, the tray, and any system-wide Global Hotkeys you have assigned all drive Spotify playback exactly as they drive a normal station.

### What Spotify playback cannot do

- **No downloading or recording.** Spotify audio is copy-protected (DRM), and the Web Playback engine is the only sanctioned way to play it, so a Spotify station cannot be recorded or saved the way an ordinary stream can.
- **Premium only.** Without Spotify Premium, playback will not start even after you sign in.
- **Off in Safe Mode.** Like every network feature, Spotify is disabled when Quill Radio runs in Safe Mode.
- **First-time network notice.** Because connecting reaches Spotify's servers, the first sign-in asks for a one-time network-access confirmation, the same as QUILL's other online features.

## Hardware media keys

If your keyboard has media keys, Play/Pause and Stop control Quill Radio system-wide while it runs -- even from the tray. Keys another app already owns are left alone.

## Global hotkeys and keyboard shortcuts

Quill Radio's shortcuts are now yours to change, and its playback controls can reach across your whole desktop.

**Keyboard Shortcuts (Help > Keyboard Shortcuts...)** opens the Keyboard Manager: a searchable, conflict-aware list of every Quill Radio command and the key assigned to it. Find a command, assign a new key (it warns you if the key is already in use, or is a risky one such as a plain letter or an arrow key), clear it, or restore the defaults. The keymap is **shared with QUILL and QUILL Cast** -- the same `%APPDATA%\Quill` data store described below -- so a shortcut you change here changes it in the editor too, and vice versa. One note: a few commands whose default is a two-key chord (the media transport keys) or uses a comma (Preferences on Ctrl+,) keep their built-in shortcut until you next launch Quill Radio; a plain single-key command such as the Command Palette takes effect immediately.

**Quick-play your favorites.** Ten commands -- Play Favorite 1 through Play Favorite 10 -- play the first ten stations in your favorites list directly, without opening a menu or arrowing the list. They default to **Ctrl+Alt+Shift+1** through **Ctrl+Alt+Shift+0** (the plain number keys are already taken by window switching, headings, and the copy tray, so these use a free combination), and they appear on the Command Palette. Rebind them here to **Alt+1** through **Alt+0** if you would rather have the shorter keys.

**Global Hotkeys (Help > Global Hotkeys...)** lets you give a **system-wide** key to Quill Radio's transport actions -- Play/Pause, Stop, Mute, Volume Up, Volume Down, and Show/Hide to the tray -- so you can, for example, pause the radio without leaving the program you are working in. Only these safe playback and window commands can be assigned a global key; a global hotkey can never trigger anything that changes a document or a file. None are set by default. The first time you assign one, Quill Radio reminds you that a system-wide key may override the same key in another program; as with the media keys and the Ctrl+Alt+Shift+R show/hide chord, a key another app already owns is left alone. (Windows only.)

## Quillins in Quill Radio

Quill Radio can now run **Quillins** -- QUILL's small, sandboxed, permission-gated add-ons -- from its own **Quillins** menu, not just inside the editor. A Quillin says in its manifest which apps it is for (its `targets`), so only add-ons written for Quill Radio appear here. The bundled `radio-community-directory` sample shows the idea: it contributes an extra station directory that appears alongside RadioBrowser and the others when you Find Stations. Quillins are off in Safe Mode. (Third-party Quillins remain disabled in this release; the bundled ones are the foundation.)

## The system tray

Closing the window keeps Quill Radio available in the notification area with its own icon, announced by name. Right-click (or keyboard-invoke) the tray icon for: Show, the live now-playing line, a single **Play/Stop** item whose label is always current, Mute/Unmute, your **Favorite Stations** (nested by folder) and **Recently Played** submenus, Record Now/Stop Recording, Schedule Recording, Recording Settings, Browse Stations, and Exit. Double-click brings the window back.

**Show or hide Quill Radio from any program** with **Ctrl+Alt+Shift+R**. This is a system-wide hotkey -- like the hardware media keys above, it works even when another app has focus, so you never have to hunt for Quill Radio's window first. Press it while the window is showing and Quill Radio tucks itself into the tray (it says "hidden to the tray"); press it again and the window returns and takes focus (it says "shown"). Playback and any recording keep running the whole time. If another app has already claimed Ctrl+Alt+Shift+R, Quill Radio simply does not take it -- there is no error, and you still show and hide the window with the tray icon and the "Alt+F4 minimizes to the system tray" preference. Each app in the family uses its own chord so they never clash: QUILL is Ctrl+Alt+Shift+Q and Quill Weather is Ctrl+Alt+Shift+W. (Windows only.)

## Sharing data with QUILL

Quill Radio reads and writes the same data store as QUILL and QUILL Cast (`%APPDATA%\Quill`): favorites (folders, custom names, and per-station volumes included), history, recordings, schedules, timers, and settings. A station you favorite here is a favorite in QUILL's radio; the wake-up timer you set in QUILL fires here. Uninstalling Quill Radio never deletes that shared data.

## Dependencies, honestly stated

- **Playback** uses the bundled **mpv** engine (`tools\mpv` inside the install folder -- license texts and source note ship right next to it) with the Windows Media Player engine built into Windows as automatic fallback and as the "classic" choice in Preferences. Nothing to install, nothing downloads at runtime. Between the two engines, effectively every stream format in real-world use plays: **MP3, AAC and HE-AAC (AAC+), Ogg Vorbis, Opus, FLAC streams, and HLS (m3u8)** -- and a station one engine can't open is quietly retried on the other before you ever hear an error.
- **Recording**, **Sound Enhancements** on the classic engine, and (when "Apply Sound Enhancements to recordings" is on) recording's own filtering all use **ffmpeg**, which the installer bundles at `tools\ffmpeg` inside the install folder. Nothing downloads at runtime. On the classic engine, Sound Enhancements plays through a small local relay (ffmpeg filters the stream, a loopback-only web server on your own machine hands the filtered audio to the player) -- nothing about it is reachable off your computer; on the mpv engine the same filters run inside the player itself, no relay at all.
- **Station search** talks to four keyless, account-free directories, blended into one results list: the community **RadioBrowser** directory, the free **SomaFM** directory, **iHeart** (search reads its public station sitemap, `www.iheart.com`, with each chosen station's real stream resolved on demand from its own page; browsing iHeart by genre reads its free, keyless content directory, `us.api.iheart.com`, which already includes the stream), and **TuneIn** (through RadioTime's open OPML directory, `opml.radiotime.com` -- the same service TuneIn's own web player uses). **Find Streams** fetches only the one page you type (following its "Listen Live" link one level and, if it's a Triton/StreamTheWorld player or an iHeart/TuneIn page, one lookup to that provider's own public address service); **stream recovery** does the same lookups against a failing station's own website only when a stream won't play (and only if you leave the setting on); **What's Playing** reads metadata from the stream you are already playing, and as a last resort reads the current title from that same stream server's own public status page (its Icecast or SHOUTcast now-playing endpoint -- the same host, never a third party). All network features are off in Safe Mode. No other network calls exist, and every one of them is inventoried in QUILL's network-egress audit.
- **NOAA Weather Radio** browsing, search, and the local-transmitter lookup use the keyless **WeatherIndex** directory (api.wxindex.org) when online, with the complete directory also bundled inside the app as a permanent offline fallback; **Radio Reading Services** refreshes from the community **RadioBrowser** directory the station search already uses, with its own bundled list as the fallback. The **Weather** menu's text weather talks to the **National Weather Service** (api.weather.gov), **Open-Meteo** (extended outlook, air quality), and **OpenStreetMap** (location search) -- all free, keyless, and account-free; see the Weather chapter.
- The **ACB Media** directory is bundled -- no network needed to browse it, and the bundled **Radio Reading Services** and **NOAA Weather Radio** directories browse offline the same way.

## Weather

Weather is now its own app -- **Quill Weather** -- and this Weather section has moved into the Quill Weather User Guide (`../../weather/docs/userguide.md`), its own home.

Weather is still built into Quill Radio: the **Weather** menu appears whenever the **Weather** feature is enabled (**View > Customize Features...**), and it leads with **Open the Quill Weather App** to hand off to the standalone watcher. Turn Weather off in Customize Features and the menu disappears -- ideal if you only want the radio. Quill Weather and Quill Radio are separate apps that run side by side, each reachable from the other's File/Weather menu and tray.

## Keyboard reference

| Action | Key |
| --- | --- |
| Play / Stop | Ctrl+P |
| Play Last Station | Ctrl+L |
| Mute / Unmute | Ctrl+M |
| Volume up / down | Ctrl+Up / Ctrl+Down |
| Volume Boost | Ctrl+Shift+B |
| Output Device | Ctrl+Shift+D |
| Rewind / Forward 30 seconds | Ctrl+Shift+Left / Ctrl+Shift+Right |
| Back to Live | Ctrl+Shift+L |
| Chapters (finished video) | Ctrl+Shift+C |
| Go to Position (finished video) | Ctrl+Shift+J |
| Next / previous chapter | Ctrl+Alt+Right / Ctrl+Alt+Left |
| Play faster / slower / normal speed | Ctrl+Alt+Up / Ctrl+Alt+Down / Ctrl+Alt+0 |
| Where am I? (position, length, chapter) | Ctrl+Shift+P |
| What's Playing? | Ctrl+T |
| Sound Enhancements (EQ, compressor, channel mode) | Ctrl+E |
| Song History | Ctrl+Shift+H |
| Play favorites 1-10 directly | Ctrl+Alt+Shift+1 ... Ctrl+Alt+Shift+0 |
| Send to tray | Ctrl+W |
| Show / hide from any app (system-wide) | Ctrl+Alt+Shift+R |
| Next / previous window | Ctrl+Tab / Ctrl+Shift+Tab |
| Jump to window 1-9 | Ctrl+1 ... Ctrl+9 |
| Preferences | Ctrl+, |
| New Folder | Ctrl+Shift+E |
| Command Palette | Ctrl+Shift+P |
| Play selected favorite | Enter (in the list) |
| Focus the status bar (a second press returns) | F6 |
| Rename (manager) | F2 |
| Remove (manager / recordings) | Delete |
| Reorder selected favorite | Alt+Shift+Up / Alt+Shift+Down |
| Station menu | Alt+S |
| Playback menu | Alt+P |
| Record menu | Alt+R |
| View menu | Alt+V |
| Help menu | Alt+H |

These keys belong to Quill Radio's own menus and are kept separate from QUILL's keymap, so nothing here collides with editor shortcuts.

## Troubleshooting

- **A station will not play.** Streams move. If the station came from the directory, Quill Radio automatically fetches its current address and retries once; if it still fails, search for it again in Browse Stations, or re-add it as a custom station. If a station is simply dead, tell us: **Report Bad Station...** on that station's context menu in Browse Stations or Search Stations opens a bug report already filled in with the station's name, stream, source, and country, so you do not have to write any of it out. It carries the station's details only -- never your name, email, or any file paths. (Directories hide stations their own checker believes are dead, so a station that plays for the directory but not for you is one only you can flag.) (Format problems are largely history as of 1.1.0: the two engines together play MP3, AAC/HE-AAC, Ogg Vorbis, Opus, FLAC, and HLS, and a stream one engine can't open is retried on the other automatically.)
- **No sound but the app says playing.** Check Mute (Ctrl+M), the per-station volume (Ctrl+Up), and the Windows volume mixer entry for Quill Radio.
- **A recording stopped early.** Check Record > Recordings... -- a dropped connection continues into "(part 2)" files when reconnect is on, and those parts are joined back into one recording when it finishes. The maximum-length cap in Recording Settings also ends recordings deliberately.
- **I still have "(part 2)" files.** That means the join was refused or failed, and Quill Radio will have said why when the recording ended -- most often because a part is missing, or the parts are not all the same format. Your audio is safe: every part is exactly as it was recorded, and they play in numbered order.
- **The wake-up timer did not fire.** Quill Radio (or QUILL) must be running at the set time -- the tray counts, a closed app does not. It also never retro-fires: opening the app hours after the set time stays silent until the next occurrence.
- **The tray icon is gone.** Check the taskbar overflow area, or set Quill Radio to "always show" in Windows taskbar settings.
- **Rewind, Volume Boost, or the output device "needs the mpv playback engine."** Preferences (Ctrl+,) > Playback engine is set to Windows Media (classic), or the bundled engine is missing. Set it back to Automatic; these features live in the mpv engine.
- **Playback sounds different since 1.1.0.** It shouldn't -- but if anything about the new engine bothers you, Preferences (Ctrl+,) > Playback engine > "Windows Media (classic)" is exactly the old behavior. Please report what you heard either way (Help > Report a Bug...).
