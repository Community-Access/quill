# Quill Radio 3.0 Release Notes

Version 3.0.3, released 2026-09-28.

## What's new in 3.0.3

3.0.3 answers five things listeners told us about in the first days of 3.0,
and adds Westwood One's live sports channels.

### Favorites that start slowly start quickly again

A favorite whose saved address has stopped working used to take a long time to
start, then say it was trying the station's current address, and play. Quill
Radio was finding the right address every time -- and then failing to save it,
so the next time, and every time after, it waited out the dead address and
repaired it again. For a favorite added from StreamTheWorld, a station's
website or by hand, the repair never stuck.

Now it does. The first time a favorite needs repairing, the current address is
saved into it, and from then on it starts straight away. Nothing to do: it
happens the next time you play it.

### Help opens its documents again

**Help > User Guide** (Ctrl+F1), **Release Notes** (Shift+F1) and **Product
Requirements** (Alt+Shift+F1) did nothing in 3.0.0 to 3.0.2, in both the
installed and the portable copy. They were looking beside the shared engine for
documents that are installed beside Quill Radio. They open again in 3.0.3, in
your web browser.

### The Stop button is back

The main window has a **Stop** button again (Alt+T), first in the row, before
Mute and Volume. It stops whatever is playing -- the same as **Ctrl+Period** and
**Station > Stop**. Stopping is the one thing everybody needs at once without
knowing a key.

### Keys that are easier to press

Every command in Quill Radio can now be reached without holding several keys
down at once -- which matters on a braille notetaker such as the BrailleNote
Evolve, and for anybody for whom a four-key chord is hard. Thank you to BITS for
raising it.

- **The QuillVille menu has access letters.** Alt+Q, then one letter, opens an
  app: Q for QUILL, W for Quill Weather, V for Quill Converter. Two single keys,
  nothing held down.
- **The QuillVille "Open" commands can be rebound.** They used to be fixed to
  Ctrl+Alt+Shift+F7 and upward. Now each is a command in **Help > Keyboard
  Shortcuts** (Ctrl+Alt+K) -- search for "QuillVille" -- and you can give it any
  key you like; the menu shows your key from then on.
- **Every enabled menu item has an access letter as well as a key**, which a
  test checks on every build. Preferences, Exit, the Sort Favorites and Main
  Window Shows choices, the Spotify items and Play Favorite Station had none.
- A new user guide section, **Keyboard access without chords**, gathers every
  way in: menu letters, rebinding, the Command Palette, and Sticky Keys.

### Westwood One Sports: every game channel, in Browse

**Browse Stations** (Ctrl+B) has a new branch, **Westwood One Sports**, with the
network's own ten live event channels. During a big event -- the NCAA basketball
tournaments, the NFL, the Masters -- Westwood One streams several games at once,
one per channel, and now every one of them is a row you can play, favorite,
record or schedule. The schedule at westwoodonesports.com says which game is on
which channel; between events a channel may be silent.

These ten are every stream Westwood One publishes. Its syndicated shows reach
listeners through local stations, which **Networks** already finds.

### Updates install themselves, now or when you close

When an update has downloaded, the **Update downloaded** window now offers:

- **Install and restart now** (Enter) -- Quill Radio closes, updates and opens
  again.
- **Install when I close** (Alt+C) -- new. Keep listening; the update is
  installed the next time you close Quill Radio, and the next time you open
  it, it is the new version.

**A portable copy now updates itself.** In 3.0.0 to 3.0.2 it could not: it said
it could not install the update automatically and left the zip in
`data\updates`. Now the new files replace the old ones in the copy's own folder,
and the `data` folder -- your favorites, settings, history and recordings -- is
never touched.

**If you have a portable 3.0.0, 3.0.1 or 3.0.2**, update it once by hand, because
those versions cannot run the new updater: close Quill Radio, unzip
`Quill-Radio-Portable-3.0.3.zip`, and copy everything inside its `QuillRadio`
folder over your copy's folder, replacing files when asked. Your `data` folder
is not in the zip, so it is left exactly as it is. From 3.0.3 on, updates
install themselves.

**Coming from a 2.x portable copy?** Its updater is 2.x's own, and it can leave a
window reading "find" on screen while it waits. Close that window, unzip the
3.0.3 zip into a new folder, and start it: it offers to bring your 2.x
favorites in on its first launch. Or copy the old copy's `data` folder into the
new one before you first open it.

## What's new in 3.0.2

3.0.2 fixes one thing a listener met on the first day of 3.0.1: pressing a
Quill Radio pinned to the taskbar opened a message instead of the radio.

### A pinned Quill Radio starts Quill Radio

When you pin a running app to the taskbar, Windows pins the program it can see.
For Quill Radio that is the shared QuillVille engine every app in the family
runs on, and Windows pinned it with nothing to say which app to open. Pressed,
the pin said "QuillVilleRuntime.exe is the shared engine the QuillVille apps
run on; it is not an app of its own."

Now the engine starts the app. If Quill Radio is the only QuillVille app on the
computer, it opens, as the pin always should have. If several are installed, a
short list, Open a QuillVille app, asks which one: arrow to it and press Enter,
or press Escape to open nothing.

### New pins are made right

Quill Radio now tells Windows which app it is, and its Start Menu and desktop
shortcuts carry the same identity. Pinning the running window pins the Quill
Radio shortcut itself, which starts the app the proper way.

A pin made before 3.0.2 still works, through the fix above. To have it join
the running window on the taskbar again, right-click it, choose Unpin from
taskbar, then pin Quill Radio again from the Start Menu or its running window.

## What's new in 3.0.1

Quill Radio 3.0.1 replaced 3.0.0, which was withdrawn the day after it
shipped; everything 3.0 brought is here, and so is
the thing 3.0.0 could not always manage: opening. 3.0.1 starts every way you
can start it, arrives with its full playback engine every time, and carries
every tool it uses inside the download. It is a small release with one
promise: press the key, and the radio is there.

### If you have 3.0.0

Install 3.0.3 over it. Your favorites, settings, history, recordings, schedule
and keys all stay. If your 3.0.0 opens, Help > Check for Updates...
(Ctrl+Alt+U) offers the matching download. For a portable copy, unpack the
3.0.3 zip and copy the `data` folder from beside your old `QuillRadio.exe` into
the new folder before you first open it.

There is nothing else to do. Anything 3.0.0 set up wrongly on your computer is
put right for you, as the rest of this section explains.

### It opens, every time

Quill Radio runs on the shared QuillVille Runtime, the one engine every app in
the family uses. On some fresh installs 3.0.0 never got past that engine:
Windows showed a box titled "Unhandled exception in script" where the app
should have been. The cause was small and unkind. A windowed program has no
console, and the runtime tried to write to one anyway. 3.0.1 gives those
writes somewhere harmless to go before anything else happens.

Two more things change so that a problem at start is never a mystery again:

- If you open `QuillVilleRuntime.exe` by itself, it now tells you, in a plain
  message box, that it is the engine the apps run on rather than an app, and
  to start Quill Radio from its own Start Menu shortcut.
- If the runtime ever meets an error it cannot handle while starting an app,
  it writes the details to a text file in
  `%LOCALAPPDATA%\QuillVille\Runtime\crash-reports`. Send that file to
  support@community-access.org and a person can see exactly what happened.

### Start with Windows, and recordings that wake the computer

Two features start Quill Radio when you are not there to press anything, and
in 3.0.0 both started the wrong thing.

- **Start with Windows** told Windows to run the shared runtime, with nothing
  to say which app it should be. So each time you signed in, the radio did not
  appear. It now starts Quill Radio through its own `QuillRadio.exe`, which
  keeps working even when a future runtime update moves the runtime to a new
  folder.
- **Waking the computer for a recording** registers a Windows task that starts
  Quill Radio at the right moment. 3.0.0 wrote that task so that it named a
  file that did not exist, and the computer woke to silence. Now the wake
  starts Quill Radio in time, and the recording you scheduled is made.

Fixing the command was not enough on its own, because 3.0.0's entries are
already on people's computers. So every time Quill Radio opens, it quietly
checks its own entries in the background, without slowing the launch:

- A Start with Windows entry that is there and out of date is rewritten.
- A recording wake that is turned on, still ahead of you and out of date is
  registered again for the same moment.

It only ever repairs what you turned on. It never creates an entry, never
touches the computer from a portable copy, does nothing in Safe Mode, and if
Windows refuses the change, the app opens anyway.

### The full player, however you open it

Quill Radio plays through the bundled mpv engine, which is what lets you
rewind live radio, boost the volume and choose an output device. In 3.0.0 two
ordinary ways of opening the app could lose it:

- **A taskbar pin.** Pin Quill Radio while it is running and Windows may pin
  the runtime underneath it rather than the app.
- **A desktop icon from an earlier installer**, which pointed straight at the
  runtime.

Started either way, 3.0.0 could not find its own folder, reported "mpv engine
not available", and fell back to the classic Windows Media player. 3.0.1 looks
for mpv and ffmpeg beside the runtime as well, so the full engine, and
recording, are there from every starting point.

The installer also mends the icon itself. If it finds a Quill Radio desktop
icon, it checks Create a desktop icon for you, removes the old icon and writes
a new one that starts Quill Radio properly. Uncheck the box if you would rather
have no desktop icon at all.

Opening another app from the Apps menu is fixed for the same reason: every
QuillVille app is the same runtime started with a different app, and 3.0.1
starts it that way.

### Everything in the box

Nothing downloads the first time you use a feature. Both downloads carry every
tool Quill Radio uses:

- **ffmpeg**, for recording and converting.
- **mpv**, the playback engine.
- **yt-dlp**, which plays YouTube.
- **Deno 2.9.7 and yt-dlp-ejs 0.8.0**, new in 3.0.1. YouTube guards its audio
  with small puzzles written in JavaScript; without an engine to solve them,
  some formats went missing or played slowly. Deno solves them on your own
  computer. Its checksum is pinned when Quill Radio is built, the puzzle
  scripts come only from inside the app, and yt-dlp never fetches code from
  the internet. A Deno you happen to have installed elsewhere is never used,
  only the one Quill Radio shipped.
- **The OptiLab Core adapter**, for Exact OptiLab processing.

The installer adds Deno and OptiLab even when another QuillVille app put the
shared runtime on your computer first, so what you can do never depends on
which app you installed first.

### Repair, only for emergencies

Because everything ships inside the app, the Help menu items that used to say
Get now say what they are for:

- **Help > Repair FFmpeg...** (Ctrl+Alt+F)
- **Help > Repair mpv Playback Engine...** (Ctrl+Alt+M)
- **Station > Repair YouTube Support...** (Ctrl+Alt+Y)

In Audio Health (Ctrl+Alt+Shift+M), the buttons are **Repair FFmpeg...**
(Alt+R) and **Repair mpv...** (Alt+M). The keys have not changed, and every
message that used to point at a Get item now names the Repair item.

Repair YouTube Support is for the day YouTube changes faster than Quill Radio
releases, and in 3.0.0 it failed on exactly the copies that needed it: it used
a Python installer tool that neither the installed nor the portable app
carries. In 3.0.1 it fetches the newest yt-dlp from the Python Package Index
directly, checks it against the published SHA-256 checksum before using it,
and tells you the version it installed. If the built-in helper is already the
newest, it says so, as good news rather than an error. And a repaired helper
is used only while it is newer than the built-in one, so a later Quill Radio
update never leaves you on an older copy. It still asks before it goes online
and stays off in Safe Mode.

A portable copy never offers to download anything. If part of one is missing,
it now says the copy is incomplete and suggests unpacking the whole zip again,
or checking whether antivirus quarantined part of it.

### Tab moves on from your favorites

In the main window, Tab on the favorite stations list stayed on the list;
only Shift+Tab could leave it. Now Tab goes on to Mute, then Volume, then the
now-playing line and back to your favorites, and Shift+Tab walks the same
circle the other way. It works the same whichever view the main window is
showing -- Favorites, Browse, Search, Recordings or the Player.

### An installer a screen reader can read

The installer's two choices, **Create a desktop icon** and **Launch Quill
Radio**, are now real Windows checkboxes. 3.0.0 drew them as a custom list
that screen readers announced as "not checked" whatever their state; now you
hear the truth, and Space changes it. Both still start unchecked (unless the
installer is replacing an old desktop icon, as above), and a silent install
launches nothing.

### If something still is not right

Help > Get Help from Support... (Ctrl+Alt+F2) writes to a person at Community
Access, with the app's version already filled in. You can also write to
support@community-access.org from any email account, and attach a crash file
from `%LOCALAPPDATA%\QuillVille\Runtime\crash-reports` if there is one.

## What Quill Radio is

Quill Radio is an internet radio player for Windows, built for people who use a
screen reader. It plays live stations, podcasts, audiobooks, YouTube and
television, and it records. Nothing needs an account, and nothing you listen to
leaves your computer. It is made by Community Access.

These notes cover everything new since 2.1.2. Version 2.2.0 was built but never
published, so its changes are included here too.

## Downloads

There are two downloads. Both are code-signed.

- **Quill-Radio-Setup-Shared-3.0.3.exe** is the installer, and the right choice
  for most people. It installs the shared QuillVille Runtime if it is not
  already on the computer, then Quill Radio, with a Start Menu entry and an
  uninstaller.
- **Quill-Radio-Portable-3.0.3.zip** is the portable copy. Unpack it anywhere,
  including a USB stick, and run `QuillRadio.exe`. It needs no installation and
  no internet.

A portable copy writes nothing to the computer it runs on. Settings, favorites,
history, recordings and downloads all stay in the `data` folder beside
`QuillRadio.exe`, from the first launch. Delete that folder and the copy
becomes an ordinary one that uses this computer's profile. Two features that
change the computer itself are unavailable in a portable copy: Start with
Windows, and waking the computer for a recording.

If you used a thin "Lite" installer or a Companion zip from a 3.0 preview: both
are retired. The installer upgrades a thin install in place, and Check for
Updates on a Companion copy offers you the installer.

## Highlights

- Browse Stations has more than thirty branches, and the whole station
  directory, over 62,000 stations, ships inside the app. Browsing works with no
  internet at all.
- One search, Ctrl+F, finds stations, podcasts, audiobooks, archive recordings,
  music and YouTube videos.
- Described audio on videos is named and one key away: Ctrl+Alt+D.
- Podcasts, audiobooks, the Internet Archive, free music, YouTube and about
  9,300 television channels, all with no account and no key.
- Download what you are allowed to keep, and pick up where you left off.
- More than forty guided tutorials that watch you do each step: Ctrl+Alt+F1.
- F1 in any window explains that window and the control you are on.
- Every menu item shows its shortcut, and the Keyboard Shortcuts Sheet
  (Ctrl+Alt+Shift+K) lists every key in one place.
- Undo for destructive actions (Ctrl+Z), a Recent Problems list, and Quiet
  Hours.
- Every message the app speaks also reaches a braille display.

## First run

The first time you open Quill Radio, a short welcome of three screens explains
what the app is, how to find something to listen to, and how favorites work.

- Skip is a real button, and skipping counts as done.
- It never appears if you already have favorites, for example after an upgrade
  or a restored backup.
- The keys it names are your keys, so a rebound key shows as rebound.
- The text is in a box you can arrow through and copy from.
- Browse Stations Now takes you straight to the station tree.

A checkbox, Show me a tip now and then, turns on six one-time tips. Each
appears once, the first time it would help, and never takes focus.

## Finding stations

### Browse Stations

Press **Ctrl+B**. The tree now has more than thirty branches. New ones include:

- **By Country**, **By Language**, **Trending Now** and **Recently Added or
  Changed**. Countries open into states or regions, then stations, most
  listened first.
- **Internet Archive**: Old Time Radio, audiobooks and poetry, the Live Music
  Archive, radio programs, and news. Large folders say how much they hold and
  offer a More row.
- **LibriVox**: public-domain audiobooks by genre, by author and recently
  added. There is no By Title branch, because LibriVox offers no such list.
- **Project Gutenberg**: human-read audiobooks by topic and by language.
- **Audius**, **Mixcloud** and **ccMixter**: independent music, DJ sets, and
  Creative Commons music with its licence shown in the row. Mixcloud shows open
  in your web browser, and the row says so before you press Enter.
- **AudioPub**: audio people made and shared, on a Discover shelf.
- **Explore**: stations known to Wikidata, by city, by format, and On the Dial.
- **My Servers**: your own Icecast or SHOUTcast server address. An address that
  returns nothing is not saved, because it is usually a missing port number.
- **Networks**: the BBC, NPR, CBC, ABC Australia, RTE, RNZ, NHK, Deutsche Welle,
  Radio France and more.
- **SHOUTcast**: the Top 500 by live listeners, then 313 genres. Each genre
  lists at most 500 stations, sorted by live listeners.
- **Live365**: about 5,500 independent stations, A to Z.
- **Radio Paradise**: each channel at every quality it offers, up to lossless
  FLAC.
- **Podcasts (Apple)**, **Podcast Index**, **YouTube** and **Television**, all
  described under Podcasts, YouTube, TV and video.

Other changes to the tree:

- Numbers in names sort as numbers, so ACB Media 2 comes before ACB Media 10.
- Expanding a folder keeps you on it and says its count. You step in when you
  are ready.
- Browse Stations reopens where you left it.
- Landing on a folder starts loading it in the background, so opening it is
  usually instant.
- A slow branch says what it is loading, and says so again after three
  seconds.
- An empty branch tells you whether it is really empty or the directory could
  not be reached. After two failures in a row it suggests the directory may be
  down.
- Where a directory measures its audience, the details panel shows "Live
  listeners", kept separate from community votes.
- The tree's label is now Alt+T, so Alt+S opens the Station menu.
- Shift+F10 or the Applications key on any row shows every action for it.

**Station > Choose Browse Sources (Ctrl+Alt+Shift+O)** turns branches on or
off. Right-click a branch and choose Hide This Source to hide it on the spot.
Each row says its state, for example "On. YouTube.", and Turn On or Off flips
it. There are no checkboxes, because screen readers announce them
inconsistently in lists. A source added in a later version appears for you
even if you have changed this list before.

Some sources have options. **Source Options...** on a source's context menu
chooses Radio Paradise's default quality, and whether SHOUTcast lists every
station or only those with listeners.

### The station catalog on your computer

The station directory ships inside the app: more than 62,000 stations across
240 countries, plus SomaFM and the Project Gutenberg audio shelf. It adds about
7.5 MB. Those branches answer instantly and work offline, and every folder says
its size before you open it.

Some branches stay live, because their terms or their size rule out storing
them: Apple Podcasts, TuneIn, iHeart, the Internet Archive, LibriVox and the
music charts.

- **View > Station Catalog Status (Ctrl+Alt+Shift+S)** lists what is stored on
  this computer, how fresh it is, and what is not stored and why.
- The details panel says where a branch's answers come from.
- If you are offline, the app says so once and carries on from the catalog.
- **Station > Update Station Catalog (Ctrl+Alt+Shift+G)** refreshes it on
  demand and says what changed. It also refreshes shortly after launch and
  once a day, and both can be turned off.
- A directory that is down costs you freshness, never stations. A station that
  vanishes is only forgotten after two weeks.
- Your favorites, custom stations and servers are stored separately and are
  never touched by the catalog.

### Search

Press **Ctrl+F** for Search Stations. Results now include radio stations,
LibriVox books, Internet Archive recordings, Project Gutenberg audiobooks,
podcasts, Audius, Mixcloud, ccMixter, SHOUTcast, Live365 and YouTube. Each row
says where it came from.

- Libraries answer separately and appear as they arrive, without moving your
  place in the list.
- Pressing Play on a podcast plays its latest episode. On a LibriVox book it
  plays the first section.
- Press **Down** in the station-name box to reuse an earlier search. Name, tag
  and country come back together.
- Clearing the name and tag boxes clears the results and says so.
- A row the directory's own checker could not play says "may not be playable".
  TuneIn and YouTube rows say they need a lookup first. Nothing is guessed.
- **Station > Search Sources (Ctrl+Alt+Shift+U)** chooses which sources are
  searched. A source that is off is not asked.

Search understands what people actually type. A query is split into brand,
frequency, call sign and place, and each directory is asked more precise
questions. So "Sunny 105.7 Gulf Shores Alabama" finds the station even though
the directory lists it as WCSN. Frequencies are repaired: "14.90 AM" becomes
1490, and "1009" becomes 100.9. What you typed is always searched first, and
results are ranked against your whole query.

Search is also much faster. Every source is asked at once, and TuneIn and
iHeart look up their results in parallel. A search that takes longer than eight
seconds names the source that did not answer, and a long search says it is
still working. Repeating a search within ten minutes shows the earlier answer
at once while a fresh one runs.

### Search inside Browse Stations

In Browse Stations, the Find box (Ctrl+F from anywhere in the window) searches
the branch you are in, using the fastest honest route:

- On the Podcasts branch, the real podcast search.
- On a catalog branch, your own catalog.
- Elsewhere, the library's own search engine, where it has one.

Each answer says where it came from. Find also matches descriptions, so you can
search a podcast's episodes by subject.

Standing on **Search All Sources...**, typing in the Find box and pressing
Enter searches everything. Delete on the Search Results branch closes it.

### Adding your own stations

- **Station > Add Custom Station (Ctrl+N)** takes a stream address, a YouTube
  link or a Live365 link. A Live365 page link is rewritten to its stream, with
  nothing sent anywhere.
- **Station > Find Streams from a Website (Ctrl+Alt+S)** finds the stream on a
  station's web page, including stations that use SecureNet's player.
- **Station > Import Stations from Playlist (Ctrl+I)** reads M3U, M3U8, PLS,
  XSPF and ASX files.
- **Station > Export Favorites to Playlist (Ctrl+Shift+X)** writes an M3U
  playlist.
- A stream address that points at a PLS, XSPF, ASX, ASF redirector, B4S, WPL or
  Windows or Linux Internet shortcut is understood. An HLS stream is no longer
  mistaken for a playlist.
- Playlist files from strangers are read safely. A file built to exhaust memory
  is refused out loud.

## Listening and the player

### The transport keys

Transport keys work in every Quill Radio window, not only the main one.

- Play: **Ctrl+P**.
- Stop: **Ctrl+.** (Ctrl and period).
- Pause and Resume: **Ctrl+Space**. This works for podcasts, recordings,
  downloads, files and finished videos. Live radio cannot be paused.
- Live radio can be rewound: **Ctrl+Shift+Left** goes back 30 seconds, and
  **Back to Live (Ctrl+Shift+L)** returns to the broadcast.
- Volume: **Ctrl+Up** and **Ctrl+Down**, from anywhere except inside a text
  field.
- Mute: **Ctrl+Shift+O** in every window. The main window also answers
  **Ctrl+M**.
- Play Last Station: **Ctrl+L**.
- The first ten favorites play with **Alt+1** through **Alt+0**.

Volume now behaves the same everywhere. It moves in steps of 10, it says
"Volume 60 percent.", and changing it lifts mute. The last level you set is
remembered between sessions.

Every transport key says what it did, including Play, Stop and Mute. A key that
cannot act says why. For example, chapter keys on a live stream say "This is a
live stream, so there is no timeline to move along".

### Anything with an end has a timeline

On a finished video, recording, podcast episode or file:

- **Ctrl+Shift+Left** and **Ctrl+Shift+Right**: back or forward 30 seconds.
- **Ctrl+Shift+C**: Chapters, a list of the uploader's chapters. Enter jumps to
  one.
- **Ctrl+Shift+Comma** and **Ctrl+Shift+Period**: previous and next chapter.
- **Ctrl+Shift+Up** and **Ctrl+Shift+Down**: play faster or slower, from 0.25
  to 4 times. **Ctrl+Shift+0** returns to normal speed.
- **Ctrl+Alt+J**: Go to Position. Type hours, minutes and seconds, or a time
  such as 1:23:45.
- **Ctrl+Shift+W**: Where Am I. Position, length and current chapter.
- **Ctrl+Shift+9**: Skip Silence. It shortens long pauses without losing your
  place. On live radio it says it has no effect.

Your speed is remembered per kind of thing, so a speed chosen for a recording
applies to all recordings.

### The Player window

**Playback > Go to Player (Ctrl+Shift+G)** opens the Player window, or brings
it to the front if it is already open. It shows what is playing, the position,
the speed and the volume, and it carries the whole transport. Escape closes it
and returns you to where you were.

### Windows you can move between

Browse Stations, Search Stations, Manage Favorites, Schedule Recording,
Recordings, Downloads, Song History, Now Playing, the Player and Tutorials are
now real windows. Each has its own place in the taskbar and in Alt+Tab.

- Every window has a **Station** menu (Alt+S) and its own menu. See Where each
  window's menu is, below.
- Ctrl+Tab and Ctrl+Shift+Tab move between Quill Radio's windows, and focus
  lands on the control you last used there.
- Asking for a window that is open brings it to the front.
- These windows close with Escape, Ctrl+W, Ctrl+F4, Alt+F4 or the title bar.

**View > Main Window Shows** chooses what fills the main window: Favorites
(Ctrl+Shift+1), Browse Stations (Ctrl+Shift+2), Search Stations
(Ctrl+Shift+3), Radio Recordings (Ctrl+Shift+4) or the Player (Ctrl+Shift+5).
The menu bar, the now-playing line, Mute and Volume stay in place around it.

**View > Go To (Ctrl+G)** opens a numbered list of every place in the app. The
numbers never change.

### The main window

The main window is now the now-playing line, your favorites, Mute and Volume.
The now-playing line is a read-only box you can arrow through and copy. Alt+M
is Mute and Alt+U is the volume slider. The transport buttons have moved to
their keys, the menus and the Player window.

**View > Show Status Bar (Ctrl+Alt+Shift+B)**, then **F6**, moves into the
status bar. Left and Right move between cells. Enter acts on a cell: Play or
Stop, Mute, Volume, Record, Sleep timer, and the clock. Escape returns to your
favorites. A recording counts down to the end you chose. A recording with no
length counts up instead, such as "18 min so far".

### What's playing

- **What's Playing? (Ctrl+T)** opens a window you can review and copy.
- It says where the title came from: the stream itself, the player, or the
  station's status page. If the station's raw text differs from what is shown,
  you see both.
- Copy What's Playing always responds.
- **Song History (Ctrl+Shift+H)** keeps up to 200 songs per station, newest
  first, as sentences such as "Your Song by Elton John, heard 10:04, played
  twice". Song Details looks up the release and year on MusicBrainz, only when
  you ask. Background asks your AI provider for a note, always labelled as
  written by AI, and is off in Safe Mode. Clear empties one station or all.

### Sound

- **Audio > Sound Enhancements (Ctrl+E)**: equalizer, compressor, channel mode,
  night mode and broadcast polish, previewed live.
- **Exact OptiLab processing** can run the real OptiLab Core engine by Lanes
  Audio. It is off by default. "When saving" is recommended: it processes a
  recording once, after it finishes, and never risks the original. "While
  listening" works too, but each settings change needs a short reconnect.
- The built-in Stream Polish Auto-Adapt slider is smoother, and silence or hiss
  no longer raise the level.
- **Audio > Use One Volume for All Stations (Ctrl+Alt+V)** replaces
  per-station volumes with one level. Turning it off restores each station's
  own level. **Forget Every Station's Own Volume (Ctrl+Alt+Shift+V)** clears
  them.
- **Audio > Output Device (Ctrl+Shift+D)** picks the sound card.
- **Audio > Volume Boost (Ctrl+Shift+B)**.

OptiLab Core is by Lanes Audio (dgl1984), used with thanks under its Apache-2.0
with Commons Clause licence.

### Continue Listening

**Playback > Continue Listening (Ctrl+Alt+Shift+L)** lists everything you began
and did not finish, newest first, with how far in you are. Files on your
computer are recognised by content, so moving or renaming them keeps your
place. A few seconds in does not count, finishing clears the entry, and live
stations never appear.

Quill Radio and QUILL Cast share one place per podcast episode, saved when you
pause as well as when you stop. The most recent decision wins, not the furthest
point.

### Staying connected

- A station that drops briefly now reconnects on its own, silently.
- If the connection is really lost, Quill Radio retries three times and
  announces each attempt, for example "Reconnecting to KFI AM 640. Attempt 1 of
  3."
- iHeart stations use their steadier stream where one exists. This fixes
  stations like KFI stopping after about 20 seconds.
- While a stream is buffering or reconnecting, the status says so instead of
  "playing".
- TuneIn now prefers an encrypted stream address when one is offered.

## Podcasts, YouTube, TV and video

### Podcasts

- **Podcasts (Apple)** in Browse Stations: choose a country for its top shows
  and Apple's whole genre tree. No key and no account. Choosing a genre now
  includes the genres under it.
- **Podcast Index** lets you open a show and play its episodes without
  subscribing. It has Trending Now, 112 categories, and Search the Podcast
  Index. Rows say when a feed can no longer be read. It needs no key: Quill
  Radio identifies itself, and a search sends only the words you typed. You
  can use your own key instead.
- Searching for a podcast asks Apple and the Podcast Index together. If one
  does not answer, you still get the other's results.
- **Subscribe to This Podcast** adds the show to the library shared with QUILL
  Cast. Subscriptions shows a count, and each show says how many episodes are
  unheard.
- Each show lists its 25 newest episodes. That count is Quill Radio's only
  podcast setting. For an inbox, a play queue, automatic downloads and private
  feeds, use QUILL Cast, which shares the same library.

### YouTube

- Paste a YouTube link into **Add Custom Station (Ctrl+N)** and it becomes a
  station. It plays, sits in Favorites, and can be recorded or scheduled.
- **Station > Add YouTube Link (Ctrl+Alt+N)** files a channel, playlist or
  video by what the link is.
- **Add from YouTube Playlist (Ctrl+Shift+Y)** lists a playlist in its own
  order. Adding videos is a one-time import into favorites: run it again later
  to collect new videos. Existing favorites are skipped.
- **Import YouTube Subscriptions (Ctrl+Alt+Shift+Y)** reads the
  subscriptions.csv file from your own Google export. No sign-in, nothing
  stored, nothing sent to Google.
- The yt-dlp helper is built in, so your first link just plays.
  **Station > Repair YouTube Support (Ctrl+Alt+Y)** is the emergency repair: it
  fetches a newer helper when YouTube changes. It asks first and is off in
  Safe Mode.
- Quill Radio does not download YouTube videos, and YouTube Premium and watch
  history cannot be used, because YouTube's terms do not allow it.

### Described audio and other audio tracks

- **Audio > Audio and Described Audio (Ctrl+Shift+A)** lists every audio track
  a video has, by name, with any described track first and already selected.
- **Audio > Play Described Audio (Ctrl+Alt+D)** switches straight to it.
- When a video has a described track, Quill Radio says so once.
- Switching tracks keeps your place.
- If there is no described track, it says what tracks there are instead.
- Dubbed tracks are listed by language name. One video offers twenty-four.

### Transcripts

**Playback > Transcript (Ctrl+Shift+T)** opens a finished video's captions or a
podcast's published transcript in a read-only text box.

- Playback never moves your cursor.
- Enter on a line jumps playback to that moment.
- Ctrl+F finds text and says the time, such as "Found at 12 minutes 8 seconds.
  Enter plays from here."
- The Links button lists every web address in the transcript.
- Save As offers plain text, WebVTT or SubRip. Open in QUILL sends it to QUILL.
- An automatic caption track says so in its heading.
- Rows with a transcript say "transcript available" and offer View Transcript
  without playing.

Live streams have no transcript.

### Video

**Video > Show Video (Ctrl+Shift+V)** shows the picture of what is already
playing. Opening or closing it never restarts playback or loses your place.

- The picture has a real name, such as "Video: The Adventures of Sherlock
  Holmes, part 4". It never takes focus by itself, and Tab always leaves it.
- There are no on-screen buttons. Every command is on the Video menu.
- **Captions (Ctrl+Shift+K)** default to white on solid black, and scale to
  300 percent. **Caption Settings (Ctrl+Alt+Shift+T)** changes them.
- Also on the Video menu: Video Information (Ctrl+Shift+I), Take a Snapshot
  (Ctrl+Alt+Shift+H), Full Screen (F11), and Video Size (Ctrl+Alt+4 to
  Ctrl+Alt+7).

### Television

**Television (iptv.org)** in Browse Stations has about 9,300 channels by
country and category. In the United States, channels are also grouped by state
and city. Search understands television, and a five-digit ZIP code finds that
state's channels.

- Adult channels are left out.
- "Which channels can my antenna receive?" opens antennaweb.org in your
  browser.
- For a TV guide, put an XMLTV file named `tv_guide.xml` in your data folder.
  Covered channels then say what is on now and next. It is read locally and
  never fetched.
- The channel list refreshes weekly, and the branch has an update-now action.

### Spotify (experimental)

Spotify is experimental and off by default.

- A free account can search and browse. Playback inside Quill Radio needs
  Spotify Premium, because Spotify only allows other apps to play for Premium
  accounts. On a free account, **Open in Spotify** on a row's context menu
  plays it in Spotify's own app.
- You need your own Spotify Client ID. Create an app on the Spotify Developer
  Dashboard, set the redirect URI to exactly `http://127.0.0.1:43217/callback`,
  and tick Web API and Web Playback SDK. You do not need the client secret.
- Then choose **Station > Connect to Spotify (Ctrl+Alt+P)**, paste the Client
  ID, and approve in your browser. **Browse Spotify (Ctrl+Alt+O)** then
  searches.
- Your sign-in is kept in Windows Credential Manager. Spotify audio can never
  be recorded or downloaded. Spotify is off in Safe Mode.

## Saving and recording

### Saving files to keep

- **Download** on a row's context menu saves it. **Download All Files** on a
  book saves every chapter, in order, while you listen to something else.
- One bad chapter costs one chapter, not the book. Progress is counted as "12
  of 40".
- Download All says how many started and how many were skipped because you
  already have them.
- Only sources that allow saving are offered. Where Download is missing, asking
  for it says why: a live station has no file (use Record Station), Spotify is
  copy-protected, Quill Radio does not download from YouTube, and Audius leaves
  the choice to each artist.
- **View > Downloads (Ctrl+Shift+J)** is the queue. Finished rows stay until
  you clear them. Open Containing Folder finds a file. Stopping takes effect
  mid-chapter, and a part-finished file resumes. You choose whether downloads
  continue when the window closes.
- **Station > Download Preferences (Ctrl+Alt+Shift+D)** sets where things go.
  Podcasts go under their show, books get their own folder, and an author gets
  a folder once you have two of their books. A sentence at the bottom says what
  will happen to the next download. "Ask me where" asks once per book.
- A downloaded book plays in chapter order and announces each chapter, such as
  "4 of 40, The Dead Hand".
- A Creative Commons licence is saved in a text file beside the audio.

### Recording

- **Record > Record Now / Stop Recording (Ctrl+R)**, **Record Station
  (Ctrl+Alt+R)**, **Stop All Recordings (Ctrl+Alt+X)**, **Schedule Recording
  (Ctrl+Shift+S)**, **Recordings (Ctrl+Shift+R)** and **Recording Settings
  (Ctrl+Alt+Shift+I)**.
- Schedule Recording takes hours and minutes in separate boxes.
- A late start still ends on time.
- The scheduled list is sorted by the next occurrence, and each row shows the
  stream's host.
- The Recordings window opens with a summary, such as "Recording, 42 min left.
  Next: KFI at 11:00 tomorrow. 14 recorded."
- When a stream drops, recording continues into a part file, and the parts are
  joined into one recording afterwards. If joining fails, every part is kept,
  and you are told why.
- A recording whose file stops growing for about a minute is treated as a
  dropped connection.
- A recording that saved nothing says so, with the reason, and the empty file
  is removed.
- Recording file names follow the computer's current time zone.
- **Preferences > Interrupted recordings at launch** chooses Ask each time,
  Always resume them, or Never resume them. This undoes "Don't ask me again".

### Recording while the computer sleeps

A sleeping computer cannot start a scheduled recording. Now:

- Schedule Recording says so before you set anything.
- Quill Radio holds off sleep as a recording approaches.
- It can wake the computer shortly before a recording, using a Windows
  scheduled task.

Both are separate checkboxes, on by default. Waking the computer is not
available in a portable copy.

### Winamp keys in the Recordings window

The Recordings window answers to Winamp's classic keys, with no modifier:

- X play, C pause, V stop, Shift+V stop with fade, B next, Z previous.
- Left and Right move 5 seconds. Shift+Left and Shift+Right move 30 seconds.
- R shuffle. Shuffle is a fixed order, so every recording plays once and Z
  always goes back.
- S repeat: off, all, or this recording.
- Ctrl+V stop after the current recording. It is not remembered between
  sessions.
- T elapsed or remaining time. J jump to a recording by name. Ctrl+J jump to a
  time.
- Up and Down still move through the list, and Ctrl+Up and Ctrl+Down change
  the volume.

A preference turns the letters off if you prefer typing to find a recording.
Seeking needs the mpv engine and a finished recording.

## Favorites and your setup

### Favorites

- Moving a favorite from a sorted view switches to manual order first, so your
  own order is kept.
- **Mark for Move**, then **Move Marked Above** or **Move Marked Below**, moves
  a station in one step.
- **Station > New Folder (Ctrl+Shift+E)** works from anywhere.
- **Station > Add Playing Station to Favorites (Ctrl+Shift+F)**. Adding one you
  already have says so and moves you to it.
- **View > Sort Favorites**, **Expand All Folders (Ctrl+Alt+E)** and **Collapse
  All Folders (Ctrl+Alt+Shift+E)**.
- The last 20 versions of your favorites are kept as backups. The Favorites
  Manager has **Remove All**.
- Deleting a row leaves you on the row that took its place.

### Backup and moving to another computer

- **Station > Back Up Stations and Settings (Ctrl+Shift+U)** saves favorites,
  settings, the wake timer, the recording schedule and, if you choose,
  recordings into one .qrbackup file. **Restore from Backup
  (Ctrl+Alt+Shift+W)** brings it back.
- **Help > Export My Setup (Ctrl+Alt+Shift+X)** and **Import My Setup
  (Ctrl+Alt+Shift+N)** move favorites, folders, settings, the Go To list, your
  servers, scheduled recordings, YouTube channels, bookmarks and rebound keys.
  The file is an ordinary ZIP. Passwords are never included. Importing
  replaces what is there, and says so first.
- **Preferences > Data Folder** can point Quill's data folder at a folder
  Dropbox, OneDrive, Google Drive or iCloud already syncs. The move happens at
  the next launch. If two computers use the folder at once, the next launch
  tells you.

### Make it yours

- **View > Customize Features (Ctrl+Alt+C)** turns whole areas on or off.
- **View > Text Size**: Normal (Ctrl+Alt+1), Large (Ctrl+Alt+2) and Larger
  (Ctrl+Alt+3).
- **View > Choose Columns (Ctrl+Alt+Shift+C)** chooses which columns Search
  Stations and Recordings show, and in what order. That is what your screen
  reader reads on every row. A line underneath reads a sample row as you
  change it. Search can add Language, Genres, Popularity and Bitrate;
  Recordings can add Length.
- **Station > Quick Actions (Ctrl+Alt+Q)** chooses the order of actions on a
  row's right-click menu.
- **Help > Keyboard Shortcuts (Ctrl+Alt+K)** rebinds keys, and **Global
  Hotkeys (Ctrl+Alt+G)** sets keys that work from any program.
- **Ctrl+Alt+Shift+R** shows or hides Quill Radio from any program, without
  stopping playback. If another program owns that key, Quill Radio leaves it
  alone.
- **Station > Start Quill Radio with Windows (Ctrl+Alt+W)** and **Resume Last
  Station on Launch (Ctrl+Alt+L)**.
- The **QuillVille** menu (Alt+Q) opens other apps in the family.
- **Quillins** (Alt+N) are small add-ons. A Quillin can add its own station
  source, which appears under Quillin Sources. Third-party Quillins stay off in
  this release.
- Every app in the family now has its own icon, told apart by shape and by
  lightness as well as colour.

## Community and ACB Media

- **Community > ACB Media Schedule (Ctrl+Shift+N)** is one list of every
  published programme. **What Is On Now (Ctrl+Alt+H)**, **Upcoming
  (Ctrl+Alt+Shift+F)**, which also lists your scheduled recordings, and
  **Refresh the Schedule (F5)**.
- Schedule times were five hours early for Central time listeners. They are
  now read in the time zone ACB publishes them in.
- A repeating programme that had vanished from the schedule now appears.
- **ACB Media Podcasts (Ctrl+Alt+I)**.
- **Community Picks (Ctrl+Alt+0)** and **Suggest a Station or Podcast
  (Ctrl+Alt+9)**. A suggestion is an email to
  support@community-access.org: fill in the form, press Send Suggestion,
  and your own mail program opens with it written. Press Send there. A
  person at Community Access reads it. You need no account, and nothing is
  posted on GitHub or any other public site.
- **Ask the Audio Description Project (Ctrl+Alt+8)** and its settings
  (Ctrl+Alt+Shift+A).
- **Station > Update Radio Reading Services (Ctrl+Alt+F10)** refreshes the
  reading-services list.
- The **Weather / NOAA** branch lists every NOAA Weather Radio transmitter with
  an internet feed.

## Getting help and staying informed

### Help that answers

- **F1** in any window says what the window is for, then what the focused
  control does.
- **Help > Tutorials (Ctrl+Alt+F1)** opens 41 guided tutorials in six tracks.
  Each step says what to do, the keys, and what you should hear. Try it runs
  the step for you. Follow me, on by default, notices when you have done a
  step, however you did it, and reads the next one. Nothing is graded. Type
  "here" in the filter to see lessons about the window you came from. Your
  place is kept. The whole set is also the `tutorials` document in the docs
  folder.
- **Help > Keyboard Shortcuts Sheet (Ctrl+Alt+Shift+K)** lists every key,
  including the menus themselves and keys that have no menu item. Type to
  filter by action or by key. It reads the menu bar in front of you, so it
  always shows your keys.
- **Help > Command Palette (Ctrl+Shift+P)** works in every window. On and off
  commands say their current state, such as "Announce Track Titles (currently
  On)". Repeat Last Announcement and Announcement Self-Test are in the
  palette.
- A dimmed menu item says why it is dimmed.
- **Help > Get Help from Support (Ctrl+Alt+F2)** writes to
  support@community-access.org. Your own mail program opens with the
  message written, including the app's version, your Windows version and
  your screen reader; nothing is sent until you press Send there. With no
  mail program, the message goes on your clipboard. **Report Bad Station**
  and **Suggest a Station or Podcast** go to the same address. Nothing from
  Quill Radio is filed on GitHub, and the app carries no GitHub token.

### Knowing what went wrong

- **View > Audio Health (Ctrl+Alt+Shift+M)** answers "is this going to work?":
  which engine is playing, whether mpv and FFmpeg are present, where audio is
  going, what Sound Enhancements are doing, and whether a recording could be
  saved. It tests nothing, so it is safe during a recording.
- If mpv or FFmpeg goes missing, Quill Radio says so once at launch, with what
  it costs and the fix. A station that needs mpv says which format and why.
- **Help > Repair mpv Playback Engine (Ctrl+Alt+M)** and **Repair FFmpeg
  (Ctrl+Alt+F)** fetch them in an emergency. Installing family apps in any order now installs
  both correctly, and reinstalling restores them.
- **Help > Recent Problems (Ctrl+Alt+Shift+P)** lists recent failures with the
  reason and time. Retry tries again, and Copy All copies the list without
  passwords. Nothing leaves your computer.

### Undo and Quiet Hours

- **Edit > Undo Last Action (Ctrl+Z)** undoes the last Unsubscribe, Remove All
  Downloads, Delete Recording or Mark All as Played, and says what came back.
  Deleted files really return. It is one step, not a history. Each action it
  covers ends with "Ctrl+Z undoes this".
- **Help > Quiet Hours (Ctrl+Alt+Shift+Z)**, 22:00 to 07:00 by default, stops
  announcements nobody asked for. Feeds, downloads and recordings carry on, a
  key you press still answers, and failures always speak. Reminders can be
  let through. The setting is shared with QUILL Cast.

### Bookmarks, timers and statistics

- **Playback > Bookmark This Moment (Ctrl+Alt+A)** and **Help > Bookmarks
  (Ctrl+Alt+Shift+J)**.
- **Sleep Timer (Ctrl+Shift+Z)** and **Wake-Up Timer (Ctrl+Alt+Z)**.
- **View > Listening Statistics (Ctrl+Shift+Q)**.

### Updates

**Help > Check for Updates (Ctrl+Alt+U)** offers the installer, or the
portable zip if you run a portable copy. The Update Available window shows
what is new in a read-only box. Update is the default button, and Escape
closes. A check that finds nothing says "You are up to date". The daily check
at launch speaks only when there is an update, and can be turned off in
Preferences (Ctrl+,). Install and restart no longer hangs.

## Keyboard and accessibility

- Every menu item shows its shortcut, and no two items share one. Where you
  have rebound a key, the menu shows your key.
- Speed and chapter keys no longer use Ctrl+Alt+arrows, which screen readers
  use for table navigation.
- Every announcement ends as a full sentence, so messages do not run together.
- Everything spoken also goes to a connected braille display. Nothing is cut
  short, a repeat within two seconds is not sent twice, and an unplugged
  display never stops speech.
- Every destructive question defaults to No, including Restore from Backup and
  Clear Song History.
- No two controls in a window share an Alt key, and no control's Alt key hides
  a menu.

### Where each window's menu is

- **Every window**: Station menu, Alt+S.
- **Browse Stations**: Browse menu, Alt+B.
- **Search Stations**: Go menu, Alt+G.
- **Player**: Player menu, Alt+P.
- **Manage Favorites**: Favorites menu, Alt+F.
- **Recordings**: Recordings menu, Alt+R.
- **Downloads**: Downloads menu, Alt+D.
- **Schedule Recording**: Schedule menu, Alt+D.
- **Song History**: Songs menu, Alt+G.
- **Now Playing**: View menu, Alt+V.

The main window's menu bar starts Station, Edit, View.

## Changes for people upgrading from 2.1.2

Nothing needs migrating. Favorites, history, recordings and settings stay where
they were.

### Keys that changed

- **F1** is now help for the control you are on. The User Guide is
  **Ctrl+F1**. Release Notes stay on **Shift+F1**.
- **Help > Tutorials** is **Ctrl+Alt+F1**. Product Requirements moved to
  **Alt+Shift+F1**.
- **Ctrl+G** is now Go To. **Recordings** is **Ctrl+Shift+R**.
- **Restore from Backup** is **Ctrl+Alt+Shift+W**.
- **Stop** is **Ctrl+.** (Ctrl and period). Ctrl+Alt+P is now Connect to
  Spotify.
- **Update Radio Reading Services** is **Ctrl+Alt+F10**.
- **Ask the Audio Description Project** is **Ctrl+Alt+8**.
- The **Quillins** menu is **Alt+N**, because Alt+Q is QuillVille.
- The browse tree's label is **Alt+T**, so **Alt+S** always opens the Station
  menu.
- **Alt+F4** exits, even while a station plays.

### What moved

- The **Weather** menu is gone. Weather alerts and forecasts are now in Quill
  Weather, a separate app. The Weather / NOAA branch stays in Browse Stations.
- The main window's transport buttons are gone. Use the keys, the Playback
  menu or the Player window.
- One Playback menu became three: **Playback**, **Audio** and **Video**.
  Described audio, Output Device and Use One Volume are on Audio.
- The **Edit** menu is now after Station.
- Browse, Search, Manage Favorites and Schedule Recording are windows, not
  dialogs, so the menu bar never disappears.
- "Open this window at startup" became **View > Main Window Shows**.
- Only two downloads are published, the installer and the portable zip. The
  thin installer and Companion zip from 3.0 previews are retired; see
  Downloads.
- Your favorites come with you. The installer upgrades 2.1.2 in place. A new
  portable copy finds a 2.x copy's favorites on first launch and offers to
  copy them in (Enter for Yes); the earlier copy is only read.

## Fixed in this release

- Stations such as KFI that stopped after about 20 seconds, or repeated their
  last few seconds.
- A reconnect that announced nothing for up to 22 seconds.
- A recording that captured nothing and said nothing.
- Installing family apps in the wrong order left out the mpv playback engine.
- Check for Updates offered installed users the portable zip, and a fresh
  install could fail to find its runtime.
- The Close button in Browse Stations, Search Stations, Manage Favorites and
  Schedule Recording did nothing.
- The Command Palette key opened nothing.
- Alt+S opened the tree instead of the Station menu. Seventeen labels in seven
  windows were hiding their window's menu.
- Quillins and QuillVille both claimed Alt+Q.
- The ACB schedule was five hours early.
- The Xiph genre list lost 412 genres on each refresh and sorted Jazz three
  thousand rows down. It now keeps Xiph's own order and shows the 120 most used.
- An Apple genre could show an empty chart.
- An outage at LibriVox or the Internet Archive looked like an empty folder,
  and could stay that way after they recovered.
- SHOUTcast stations did not play at first.
- Every "Browse Stations" door, including the tray, status bar and first run,
  opened Search instead.
- Upcoming did not list scheduled recordings.
- Escape in the embedded Player closed the whole app.
- Alt+1 to Alt+0, Stop and Mute (Ctrl+Shift+O) did nothing on the main
  window.
- The first-run tip said live radio could be paused.
- Import read only M3U.
- Keymap Diagnostics listed QUILL's commands and could delete your QUILL key
  changes.
- Volume differed between windows, and Volume Up while muted stayed silent.
- A non-favorite station started at full volume on the next launch.
- Deleting a recording or favorite lost your place in the list.
- Add to Favorites said it added a station you already had.
- Exit from the tray menu hid the app instead of quitting.
- A keystroke during launch could crash the app.
- Audio could keep playing after exit.

## Known limitations

- Live radio cannot be paused. Rewind it with Ctrl+Shift+Left and return with
  Back to Live, Ctrl+Shift+L.
- Live streams have no transcript.
- Adding a YouTube playlist is a one-time import, not a subscription or a play
  queue.
- Quill Radio does not download YouTube videos, and cannot use YouTube Premium
  or watch history.
- Playback positions are kept per computer. The Data Folder carries settings
  and favorites, not positions.
- Some branches, such as Apple Podcasts, TuneIn, iHeart and the Internet
  Archive, need the internet every time.
- SHOUTcast lists at most 500 stations per genre.
- Spotify playback needs Premium, and Spotify is experimental.
- AudioPub offers only its Discover shelf for now.
- Seeking in the Recordings window needs the mpv engine.

## What comes next

Nothing here has a date. Planned work for Quill Radio:

- Public software-defined radio receivers, such as OpenWebRX, KiwiSDR and
  WebSDR, tuned from the keyboard.
- A community feeds manifest, so fire departments, emergency offices,
  universities and local governments can list their own audio feeds.
- A directory where reading services submit and correct their own listings.
- AllStarLink and EchoLink node lookup, handing off to the official client.

## Where to learn more

- **User Guide**: Help > User Guide, Ctrl+F1.
- **Tutorials**: Help > Tutorials, Ctrl+Alt+F1.
- **Get Help from Support**: Help > Get Help from Support, Ctrl+Alt+F2.
- Release notes for 2.0 and 2.1 are in `release-notes-2.0`, in the same docs
  folder.
