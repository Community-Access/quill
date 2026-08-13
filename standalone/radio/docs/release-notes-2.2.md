# Quill Radio 2.2 -- Release Notes

Quill Radio 2.2.0 is the release where the app grows up around you. Windows stop
wandering off. Your stations learn to look after themselves -- backed up, kept in
the order you left them, recoverable when a finger slips. Two whole new kinds of
station arrive. And the app finally remembers things it used to forget: your
volume, and every song a station has played.

Everything here lives in the shared `quill` package, so QUILL gains it too.
Quill Radio and QUILL share one codebase and one data store, and nothing is
vendored into the Quill Radio wrapper.

## The headline: the QuillVille Runtime, and downloads that finally travel light

This is the big change in how Quill Radio is delivered. Quill Radio, QUILL, Quill
Weather, and QUILL Audio Studio now share **one** Python engine -- the
**QuillVille Runtime** -- installed just once per user and reused by every app in
the family. Install any one of them, and every app you add afterward starts
instantly, because the engine it needs is already there. No second copy, no
second long download. The runtime is reference-counted, so it is removed only
when the last app that relies on it is uninstalled; uninstalling Quill Radio
while Quill Weather is still around leaves the shared engine in place for
Weather.

That shared engine unlocks two brand-new, much smaller ways to get Quill Radio,
alongside the two full downloads you already knew:

- **Companion edition (new)** -- `Quill-Radio-Companion-<version>.zip`, about
  **3 MB**. Just the app and its docs, running on the shared runtime. The first
  time you launch it, if the runtime is not already installed, Quill Radio offers
  to download and install it once (about 230 MB) with a fully accessible progress
  bar. After that first time, this app and every other QuillVille app start
  instantly. Three megabytes instead of three hundred.
- **Thin installer (new)** -- the small "Lite" setup. It installs the app and
  downloads the shared runtime only if it is not already present. If you already
  run another QuillVille app, there is nothing large to fetch.
- **Full portable zip** -- `Quill-Radio-Portable-<version>.zip`, about **200 MB**.
  Still the one for a USB stick: fully self-contained, runs with no installation
  and no internet, carrying its own genuine, unmodified copy of Python plus the
  bundled ffmpeg and mpv engines.
- **Full installer** -- `Quill-Radio-Setup-Shared-<version>.exe`. The recommended
  path for most people: it installs the shared runtime (unless another QuillVille
  app already put it there) plus the app.

**Accessible progress, every time.** Whenever the runtime is downloaded -- by an
installer or by the Companion edition's own first launch -- Quill Radio shows a
progress bar that works with NVDA, JAWS, and Narrator, announcing progress as a
percentage the whole way.

**Friendlier to antivirus.** Quill Radio's launcher is now a genuine, tiny native
program, and the Python it runs is the official, unmodified build. Earlier
versions used a renamed and modified copy of Python's own `pythonw.exe` as the
launcher -- a pattern some antivirus tools flagged as a false positive. That
pattern is completely gone, so the app is far less likely to be mistaken for
something it is not. (Releases are still not code-signed, so SmartScreen may
caution on first run; choose More info, then Run anyway. Signing is planned.)

The full picture, edition by edition, is in the **Installing** chapter of the
Quill Radio User Guide.

## Two new kinds of station: YouTube and Live365

### YouTube plays and records like any other station

Paste a YouTube link into **Add Custom Station** -- an ordinary video link, a
`youtu.be` short link, or a channel's live page -- and it becomes a station: it
plays through the same player, sits in Favorites, records with Record Now, and
can be captured by a scheduled recording. Quill Radio saves the *page* address,
never a stream address, and re-finds the audio each time you play or record, so
a recording you schedule today still works next week. Off in Safe Mode. A
private, removed, region-blocked, or not-yet-live video says so in plain words.

### It works out of the box

The `yt-dlp` helper that finds the audio behind a link is built into Quill
Radio, so your first YouTube link simply plays -- no download, no consent
prompt, nothing to agree to before you have heard anything. It costs about 3 MB
in the installer, which is a better trade than a dialog standing between you and
the thing you asked for. The helper is bundled only in the apps that can
actually use it -- Quill Radio, Audio Studio, and Audio Converter -- so Weather,
Cast, Social, Beacon, and Inkwell do not carry it.

### Update YouTube Support, for when YouTube changes

**Station > Update YouTube Support...** fetches a newer `yt-dlp` than the one
your copy of Quill Radio was built with. YouTube changes how it serves audio
every so often, and when it does the helper needs updating -- so this exists to
keep you from waiting for the next Quill Radio release to get YouTube working
again. An update installed this way takes precedence over the built-in copy from
then on. It tells you which version you ended up with, asks before it reaches the
network, and is off in Safe Mode. You should not need it otherwise.

### A YouTube station knows what it is playing

Finding the audio behind a link takes one request, and that request answers with
far more than an audio address. Quill Radio keeps all of it: the video's
**length**, its **uploader**, its **description**, the **chapters the uploader
published**, and whether a **caption track** exists. None of it costs an extra
moment or an extra connection -- it rides the request the app was making anyway.

A live broadcast reports no length at all, which is the honest answer -- it has
no timeline to sit on.

### A finished video has a timeline, so you can move around it

This is the part a live broadcast can never offer, and it is where a YouTube
station stops being "radio that happens to come from YouTube" and starts being a
player. Everything below is on the **Playback** menu and works on any finished
video:

| Key | What it does |
| --- | --- |
| Ctrl+Shift+C | **Chapters...** -- the uploader's own chapter list; Enter jumps to one |
| Ctrl+Alt+Right | Next chapter |
| Ctrl+Alt+Left | Previous chapter, or back to the start of this one |
| Ctrl+Shift+Right | Forward 30 seconds |
| Ctrl+Shift+Left | Back 30 seconds |
| Ctrl+Alt+Up | Play faster |
| Ctrl+Alt+Down | Play slower |
| Ctrl+Alt+0 | Normal speed |
| Ctrl+Shift+P | **Where am I?** -- position, length, and the chapter you are in |

The chapter list reads each entry as a whole sentence -- "3. Introducing layers,
starts at 5 minutes 31 seconds" -- and marks the one playing now. Speed steps
through round, speakable values (0.25x to 4x) rather than drifting by a
multiplier, and the speed you choose is remembered for the next video.

**Every one of these says why when it declines.** Point any of them at a live
stream and you hear "This is a live stream, so there is no timeline to move
along", not silence. A slider that cannot move and a "next chapter" that quietly
does nothing are worse than not offering them at all, because you cannot tell a
broken control from a stream that has no timeline. Ask for chapters on a video
whose uploader published none and it says that too.

**Go to Position... (Ctrl+Shift+J)** is the other half of having a timeline.
Skipping thirty seconds at a time gets you near; this gets you exactly where you
meant. It opens the same accessible dialog the Quill Media Player uses -- three
labelled Hours / Minutes / Seconds spin controls as the primary input, plus a
timecode field if you would rather type `1:23:45` -- rather than growing a
second, lesser prompt of its own. Ask for a point past the end and it says so
and takes you to the end instead of failing.

**And a fix that belongs here.** Rewind / Forward 30 Seconds always ran the
*live-stream* seek, which moves inside mpv's rolling buffer and reports how far
behind the live edge you now are. On a finished video there is no live edge, so
that number was invented -- exactly the kind of confident wrong measurement this
app refuses to make anywhere else. The keys now pick the operation the source
actually deserves: a video moves along its own timeline and says "3 minutes 10
seconds of 18 minutes 40 seconds"; a live stream behaves precisely as before.

### Add from YouTube Playlist

On the Station menu. Paste a `playlist?list=...` link -- already filled in for
you if it is on your clipboard -- and Quill Radio lists the videos in the
uploader's own running order, never re-sorted, because a series is meant to be
worked through in order.

Each row reads as a whole sentence: "3. Introducing layers, 5 minutes 31
seconds, 3Blue1Brown". Everything about a video is in the line your screen
reader speaks, so there are no columns to arrow across. Times are spelled out in
words on purpose -- "5:31" read aloud is ambiguous unless you already know it is
a time.

Arrow the list, select what you want with Shift or Ctrl, and choose **Add
Selected** -- or take the lot with **Add All**. Each becomes an ordinary station
you can play, favorite, and record. Quill Radio says how many it added and how
many were already in your favorites, so adding fifty videos never leaves you
wondering whether the button worked.

The listing itself is deliberately shallow: one request for the whole playlist
rather than one per video, and no video's audio is fetched until you play it.

The window is headed with the playlist's own name, read from the same request
that fetched the list, so you always know which playlist you are looking at.

A *watch* link that happens to carry a `list=` in it is still just that one
video. You asked for the video; quietly turning it into fifty stations would be
a nasty surprise.

**What this is, and what it is not.** Adding a playlist is an **import**, not a
subscription and not a play queue. The videos you pick become ordinary favorites
-- each plays, records, and schedules exactly like a station -- and they sit in
your favorites list alongside everything else rather than in a folder of their
own. Nothing plays through them in order: playing one video plays that video, and
Quill Radio does not move on when it ends. Nothing re-checks the playlist later,
so videos added upstream after your import are not picked up -- run the command
again on the same link to collect them, and anything already in your favorites is
skipped rather than duplicated. Playing a playlist as a queue, and keeping one in
step with its source, are separate pieces of work; saying so is better than
letting "playlist support" imply either.

#### Search YouTube from Find Stations

Type a search and YouTube videos appear alongside the radio directories, each
one an ordinary station you can play, favorite and record. No key, no account,
no setup -- it uses the same yt-dlp that already plays your YouTube links, so
there is nothing to configure.

Rows read "title, uploader", and the search is deliberately shallow: one
request for the whole result set, and no video's audio is fetched until you
actually play it.

A note on how this works, because it matters for what to expect. Quill Radio
does not use YouTube's official Data API, which would require every listener to
create a Google Cloud project and paste an API key in before searching. It uses
yt-dlp's keyless extraction -- the same approach FreeTube, NewPipe and
Invidious all take. The trade-off is that YouTube occasionally changes how its
site works and extraction breaks until upstream fixes it. That is exactly what
**Station > Update YouTube Support...** is for: it fetches a newer yt-dlp
without waiting for the next Quill Radio release.

### Choose what Find Stations searches

Quill Radio now searches eight places, which is wonderful when you are hunting
for something and noise when you already know what you want. **Station > Search
Sources...** lets you switch any of them off:

| Source | What it is |
| --- | --- |
| Radio Browser | The community directory behind most results |
| TuneIn | TuneIn's station directory |
| iHeart | iHeartRadio's stations |
| SomaFM | SomaFM's listener-supported channels |
| NOAA Weather Radio | US weather radio by SAME code, callsign, county or state |
| Radio Reading Service | Services broadcasting newspapers and magazines aloud |
| Spotify | Songs, shows and episodes; needs a connected account |
| YouTube | Videos, added as stations |

**A source that is off is never contacted.** This is not a filter applied to
results that were fetched anyway -- turning off iHeart means those network
requests do not happen. So switching sources off makes searching genuinely
faster and quieter, not just tidier.

Each row says its own state and what the source is: "On. YouTube. Videos, added
as stations you can play and record." There are no checkboxes, because checkbox
state inside a list is announced inconsistently across NVDA, JAWS and Narrator
-- and on/off is the one thing this dialog exists to tell you. **Turn On or
Off** flips the row you are on and says what happened.

**Your choices are remembered** -- both which sources are on and the Source
filter in the results list. A preference you have to set again on every search
is not really a preference. **Reset to Default** turns everything back on.

### Paste a Live365 link and it just plays

The Live365 link you actually have is almost never the stream -- it is the
station page or the web player, and both of those are web pages, which no player
can play. Add Custom Station recognizes any Live365 station page, player link, or
bare station id and rewrites it to that station's real stream address, telling
you it did. It is a pure text rewrite: no network
lookup, nothing sent anywhere, and a link that is not Live365 is passed through
exactly as you typed it.

## Browse by network: the BBC, NPR, and broadcasters worldwide

Browse Stations gains a **Networks** branch that gathers well-known broadcasters
into one-click lists, grouped by type: public broadcasters (BBC, CBC, ABC
Australia, RTE, RNZ, NHK, Deutsche Welle, Deutschlandfunk, Radio France, and
more), US news and talk (NPR, Fox News Radio, CNN, Bloomberg), US public radio,
sports, and music. Each list is drawn live from the Radio Browser directory, so
there is nothing new to keep up to date and no new place your searches go.
Syndication services that have no single stream of their own -- Westwood One, NBC
News Radio, ABC News Radio -- open a search across their local affiliate stations
instead, and the label says so.

**Browse Stations also remembers where you were.** Play a station and reopen the
browse tree, and it lands on the source you were last in -- Networks, TuneIn,
iHeart, wherever -- instead of collapsed at the top with everything closed.

## Song History: what that station played earlier

**What's Playing** tells you the song on right now, and then it is gone. **Song
History** (Playback menu, **Ctrl+Shift+H**) is the memory behind it: a
per-station list of every track change Quill Radio noticed, newest first, with
the time you heard it. Pick a station at the top, arrow the list, and each entry
reads as a whole sentence -- "Your Song by Elton John, heard 10:04, played
twice".

From any song you can **Copy** it, **Send to Clip Library** to keep it with your
other saved snippets, or ask for **Background**: a short, friendly note about the
song and artist from whichever AI provider you have set up. That answer is always
introduced as written by an AI model rather than by the station, because it sits
inches from the station's own information and the two must never be confused. It
needs no setup beyond the AI you may already have configured, it is never
available in Safe Mode, and if you have no provider set up the window simply says
so.

The log is yours and stays on your machine. It keeps up to 200 songs per station,
one station's listening never pushes out another's, and **Clear...** empties one
station or all of them. If you would rather Quill Radio not keep the list at all,
turn off **Keep a song history for each station** in Preferences; existing
entries stay until you clear them.

Quiet touches that make the list worth reading: a song still playing when the
poll comes round again folds into the entry already there (with a play count)
rather than filling the list with the same title six times, and stations that
broadcast their own name, "Live", or an advert marker instead of a track are left
out.

## One volume for every station

Quill Radio remembers a volume for each favorite. That is lovely when stations
are mastered at wildly different levels, and maddening when you simply want
everything quieter -- because the per-station level won outright, twenty
favorites meant twenty places to turn the volume down.

**Playback > Use One Volume for All Stations** fixes that. Tick it and a single
level answers for every station, so **Ctrl+Up** and **Ctrl+Down** turn
*everything* up or down instead of only the station you happen to be on. Ticking
it adopts whatever you are hearing at that moment, so nothing lurches.

Your per-station levels are not thrown away. Untick it and every station goes
straight back to its own remembered volume, exactly as it was -- so trying this
out costs you nothing. If you would rather be rid of them properly, **Forget
Every Station's Own Volume...** does that deliberately: it tells you how many
stations have one, asks first, and leaves your stations, folders, and every other
setting untouched.

It is off unless you turn it on, and the menu's checkmark follows the setting
however you change it -- from the menu, the Command Palette, or a shortcut you
rebound yourself.

## Quick-play your favorites

Ten commands -- *Play Favorite 1* through *Play Favorite 10* -- play the first
ten stations in your favorites list directly, without opening anything. They
default to **Ctrl+Alt+Shift+1** through **Ctrl+Alt+Shift+0** (the plain number
keys are already used by window switching, headings, and the copy tray), and like
every command they are rebindable in **Keyboard Shortcuts** -- set them to Alt+1
through Alt+0 if you prefer -- and appear on the Command Palette.

## The windows finally stay where you put them

For a while, opening Browse Stations, Search Stations, Manage Favorites, Schedule
Recording, or the Weather Center could make the menu bar seem to vanish into thin
air -- because those screens were dialogs, and a dialog cannot carry a menu bar --
and the modal ones locked you out of the main window entirely. They are proper
**windows** now. Each one carries the full menu bar, so the menus are always a
single **Alt** away no matter where you are, and none of them holds the main
window hostage; you can keep several open at once. A new **Window** menu lists
everything you have open, numbered in the order you opened it, and you move
between them the way you already do everywhere else: **Ctrl+Tab** for the next,
**Ctrl+Shift+Tab** for the previous, **Ctrl+1** through **Ctrl+9** to leap
straight to one. Each window opens only when you ask, and closing it sets you
gently back where you came from, announced as you land. The menus are there from
the very first keystroke, too: pressing **Alt** right after launch used to summon
the window's own Minimize/Maximize menu, because focus had not settled inside yet
-- focus lands in the window immediately now, so Alt opens Radio's own menu bar
the instant the app appears.

## Your stations, yours to keep

Here is the piece many of you asked for: a real backup you can carry to a new
machine. **Station > Back Up Stations and Settings...** gathers your favorites,
settings, wake timer, and recording schedule -- and, if you want them, your
recorded shows -- into a single `.qrbackup` file, and **Restore from Backup...**
brings it all home on a new PC, a new BrailleNote, or a fresh Windows. Made for
exactly the day you switch devices.

Underneath that, your favorites now protect themselves. Every change quietly
snapshots the previous version aside -- the **last 20 are kept** -- so a bad edit
or an accidental delete is never final; you can step back. That safety net is what
makes the Favorites Manager's **Remove All...** button safe to offer: clear every
station at once (your folders stay) behind a plain confirmation, and if you change
your mind, your list is still there to bring back. This is the "delete all my
favorites so I can import a fresh list in a different order" request, answered.

**Export Favorites to Playlist** (Station menu) saves your stations to an M3U
playlist you can hand to any media player, share, or keep as a plain-text backup
outside Quill Radio. It is the twin of Import Stations from Playlist, and the two
round-trip -- so exporting, re-ordering the file elsewhere, clearing your list,
and importing it back is now a complete, supported journey.

## Favorites, exactly the way you arranged them

If you have ever hand-sorted thirty stations into the order that makes sense to
*you*, this part is a love letter. Moving a favorite up or down from a sorted
A-to-Z view no longer quietly overwrites that hand-built order first: Quill Radio
switches to manual order (and says so -- "Switched to manual order"), then moves
the station, leaving your saved arrangement intact. When a long haul of arrow
presses feels absurd, **Mark and Move** does it in one gesture -- right-click (or
the Applications key) a station, choose **Mark for Move**, travel to the
destination, and pick **Move Marked Above** or **Move Marked Below**, and it jumps
straight there, adopting that spot's folder, on the main list and in the Manager
alike. The Manager's own **Move Up / Down / Above / Below** buttons work from the
alphabetical view now, too (they used to sit dead unless you were already in
manual order). **Ctrl+Shift+E** makes a **New Folder** from anywhere, including
with your cursor in the favorites tree. Adding a **custom station** shows it in
your list right away instead of looking as though nothing happened. And **TuneIn**
stations -- which only work out their stream when you play them -- can finally be
added to Favorites straight from Browse, stream and all.

## Know what is playing, and hold onto it

**Ctrl+T** does more than speak now. "What's Playing?" opens a small window with
the current title and artist in a field you can arrow through character by
character and copy -- to catch a spelling, or paste a song into a search -- and it
still speaks the title, still falls back to speaking when a stream has not sent
its track yet. Any favorite gives you the same reviewable readout through
**Station Details...** on its context menu: source, stream, format, country. More
stations actually have a title to show, as well: a batch of streams -- some HLS,
and a handful others could read but Quill Radio could not -- tuck the current song
into the player's metadata rather than the main title field, and Quill Radio now
reads that too, so names and artists appear where they used to be blank. And there
is a new way to reach the volume: a **Volume** slider right in the Tab order, so
you can tab to it mid-song and arrow it up or down -- however you change the
volume, the slider, the status bar, and Ctrl+Up/Down all stay in perfect
agreement.

**Report Bad Station.** A station that plays for the directory but not for you is
something only you can flag. **Report Bad Station...** on any station's context
menu (in Browse Stations and Search Stations) opens the normal Report a Bug flow
pre-filled with that station's details -- name, stream, source, country -- so the
report is complete on the first try. It carries station information only; never
your name, email, or file paths.

## Finding your next favorite

Browsing got kinder. Expanding a country or a genre in Browse Stations no longer
flings your cursor down into the station list; it stays on the folder you opened
-- you still hear its count -- so you step into the stations when *you* decide to.
The search source picker now reads **Radio Browser** as two clear words (run
together, a screen reader could make the option sound as though it had gone
missing), and there is a **Radio Browser (by Genre)** branch so you can wander
that enormous directory by genre instead of only searching it. And after you
update in place, new categories -- iHeart, Radio Reading Services -- show up right
away: Browse used to keep serving the previous version's cached directory until it
expired, and it now recognizes when the app itself ships a newer one, while still
respecting a directory you refreshed by hand.

## The View menu: a dashboard you can read

A new **View** menu gathers several comforts in one place. **Show Station
Details** turns the read-only details box in Browse and Search on or off, and
every station screen honors your choice. **Show Status Bar** lays a strip along
the bottom of the main window that always tells you what is going on -- what is
playing, the volume (and whether Volume Boost is on), whether a recording is
running, the sleep timer, how many favorites you have, and the time. Press **F6**
to land in it, arrow left and right across the cells (**Home** and **End** jump to
the ends), and press **Enter** on a cell to *act*: Enter on Now Playing opens the
What's Playing window, on Volume mutes, on Recording starts or stops a capture, on
the Sleep timer opens it. Right-click any cell for more -- play and pause, mute,
volume up and down, Volume Boost, stop all recordings -- and **Escape** (or a
second F6) hands focus straight back to your favorites. The menu also lifts **Sort
Favorites** (Ascending, Descending, Unsorted) up out of Preferences, adds **Expand
All** and **Collapse All Folders** to open or shut your whole tree at once, and
offers **Text Size** (Normal, Large, Larger) to enlarge everything on the main
window together. Every choice here is remembered between sessions.

**Customize Features** (View menu) turns whole areas of Quill Radio on or off --
the **Recording** and **Weather** menus, each with a description. Uncheck one and
its whole menu (and every command under it) is left out the next time the app
opens, so you can trim Quill Radio to just what you use. Everything is on until
you turn it off.

## Everything Quill Radio says now reaches braille

Everything Quill Radio speaks -- What's Playing, a finished refresh, a recording
starting -- is now also written to a connected braille display, not only spoken.
Nothing is truncated, an identical message inside two seconds does not steal the
display twice, and braille never costs speech: an unplugged display or a reader
that refuses the call degrades to "spoke but did not braille", never to silence.
Turn it off with **Show announcements in braille** in Preferences >
Accessibility. A *burst* of different messages no longer flickers across the
display either -- the first message of a quiet period writes instantly and
anything landing within the next 150 ms settles to the newest, with errors always
writing through at once.

Speech is gone the moment it finishes, so **Repeat Last Announcement** (Command
Palette) brings the last thing Quill Radio said back. **Announcement
Self-Test...** announces a phrase and then tells you which channels actually
delivered it and through which backend, so "braille is broken" and "no display is
connected" stop looking the same. Quill Radio also gains its own sound cues, all
of which can be turned off or replaced from a sound pack.

## Recording, sturdier in three ways

**An interrupted recording ends up as one file.** When a stream drops
mid-recording, Quill Radio reconnects and continues into a "(part 2)" file -- and
now, when the recording finishes, it stitches the pieces back into a single
recording under the name you expected. A show that dropped twice no longer leaves
you three files to find and play in order. The join is a straight copy, so nothing
is re-encoded and even a long capture takes seconds, and it is done in an order
that cannot lose your audio: the joined file is written, verified, and only then
put in place, and the parts are removed only once that has demonstrably worked.
Anything that goes wrong -- a missing part, parts in different formats, an FFmpeg
error -- leaves every part exactly where it is. You are told either way: "Joined 3
parts into one recording", or "Kept 3 separate parts" and the reason.

**A recording that stops recording is now noticed**, even when nothing reports a
problem. A stalled stream can leave FFmpeg alive and apparently healthy while the
file stops growing, so the recording looked fine and captured nothing. Quill Radio
now watches the recording file's size as a second, independent check: if it has
not gained a byte across four checks in a row -- about a minute -- the recording is
treated exactly like a dropped connection, so it reconnects and continues or stops
and saves what it captured. It is patient enough that a slow network or a
station's own rebuffering is never mistaken for a dead one, and it is never
applied to a recording you have just asked to stop.

**The scheduled-recordings list is ordered by when each recording next occurs**,
soonest first, rather than the order you entered them, and each row shows the
stream's host in brackets so two similar entries -- or a duplicate still pointing
at the original station -- are easy to tell apart.

## Winamp's keys, in the Recordings player

If you came to Windows audio through Winamp, its classic-skin keys never really
left your fingers. Until now the Recordings window answered to exactly two of
them -- Ctrl+Up and Ctrl+Down for volume -- and nothing else. There was no play,
no pause, no stop, no seek, nothing to move between recordings. The whole
transport set is now there, on the letter keys you already know, with no
modifier to reach for:

| Key | What it does |
| --- | --- |
| X | Play the selected recording, or resume a paused one |
| C | Pause / unpause |
| V | Stop |
| Shift+V | Stop (Winamp's fade-out; this player has no fade, so it stops cleanly) |
| B | Next recording -- moves down the list and plays it |
| Z | Previous recording |
| Left / Right | Back / forward 5 seconds |
| Shift+Left / Shift+Right | Back / forward 30 seconds |
| R | Shuffle on / off |
| S | Repeat: off, then all recordings, then this recording |
| Ctrl+V | Stop after the current recording |
| T | Elapsed time, or time remaining -- press again to swap |
| J | Jump to a recording: type any part of its name |
| Ctrl+J | Jump to a time: type `90`, `1:30`, or `1:02:03` |
| L | Open (the same as Play) |
| Ctrl+Up / Ctrl+Down | Volume up / down |

Every one of them says what it did. A transport key whose result you cannot hear
is not a working transport key, so "Playing", "Paused", "Back 5 seconds" and the
rest are spoken -- and, since 2.2, brailled as well.

There are two places this deliberately parts company with Winamp, and both are
the better answer here rather than an oversight:

- **Ctrl+T stays What's Playing.** Winamp puts the elapsed/remaining toggle
  there; in a radio app, knowing what is on the air is worth more. The time
  toggle is on plain **T**, which nothing else was using.
- **Up and Down still move through the list.** In Winamp those are volume in the
  main window but list navigation in the Playlist Editor -- and the recordings
  list *is* a playlist editor by any other name. Volume stays on Ctrl+Up and
  Ctrl+Down, exactly where it already was.

### And the last three keys, which needed a queue first

**R**, **S** and **Ctrl+V** were held back on purpose. All three -- shuffle,
repeat, stop-after-current -- describe a play queue, and the recordings list did
not have one. Binding them to something that only looked like it worked would
have been worse than leaving them unbound, because you cannot tell a key that
does nothing from an app that is broken.

The list has a queue now, so they are bound.

**Shuffle (R) is a fixed order, not a fresh roll each time.** That distinction
is the whole feature. "Pick one at random on every Next" eventually plays the
same recording twice before it plays some others at all -- and, far worse here,
**Z** cannot take you back to what you just heard, because nothing recorded
where you had been. Shuffle instead reorders the whole list once: every
recording plays exactly once before any repeats, and previous is the exact
inverse of next.

**Repeat (S)** cycles off, then all recordings, then this recording, saying
which each time. Repeat-one applies when a recording *finishes on its own* --
pressing **B** still moves you on, because a Next that refused to move would
look broken rather than deliberate.

**Stop after current (Ctrl+V)** is a one-shot. It outranks repeat, because it is
the thing you asked for a moment ago rather than a standing preference; it
clears itself the instant it fires; and it is deliberately *not* remembered
between sessions. A stop that survived a restart would halt playback for a
reason nobody could remember asking for.

A recording that reaches its end is now followed by whatever the queue says is
next, rather than simply stopping. Shuffle and repeat are remembered; the
one-shot is not.

Seeking needs something with a timeline, which means a finished recording on the
mpv engine; on a live stream, or with the classic Windows Media engine, the seek
keys say why they cannot move rather than silently doing nothing. A letter typed
into a text field is never swallowed. And if you would rather have the letters
for list typeahead, **Winamp-style playback keys in the Recordings player** in
Preferences turns them off -- volume is unaffected either way.

Not included, deliberately: shuffle, repeat, and stop-after-current. All three
describe a play queue, and the recordings list does not have one yet. A key that
only looks like it worked is worse than a key that is not there, so they wait for
the release that gives the list a queue to shuffle.

The map itself lives in one small shared module with no wx in it, so the
standalone Media Player and QUILL Cast can adopt exactly these keys instead of
growing a second, subtly different set.

## It looks after itself now

A cluster of quiet reliability wins. Quill Radio **keeps your computer awake**
while a station plays or a recording runs, so Windows dozing off can no longer cut
a long listen -- or a scheduled capture -- short. (Your screen may still sleep to
save power; only the machine's sleep is held, and only while something is actually
going, and a Preferences checkbox turns it off if you would rather Quill Radio
never touch your power settings.) The **Stop button answers Alt+S** again: it used
to advertise Alt+S and Alt+P, which are really the Station and Playback menu keys,
so pressing them opened a menu instead of stopping the radio -- it no longer claims
those, and **Ctrl+P** stops or plays from anywhere, welcome when a loud station is
drowning out your screen reader. **Exit means exit**: if you close to the tray,
choosing Exit -- even from the tray menu -- genuinely quits now instead of ducking
back into hiding. On the pausing-and-rewinding engine, audio **stops firmly on
exit** rather than lingering for a beat (closing to the tray with Ctrl+W or the X
still keeps playing on purpose -- that is what the tray is for). **Install and
restart** no longer hangs behind a stray, focus-stealing terminal window; it runs
fully hidden and finishes. And you can **schedule a recording in hours and
minutes** now -- separate Hours and Minutes boxes, so three hours is simply "3" and
"0", no arithmetic (your existing schedules are unchanged).

**Output Device on the Playback menu (Ctrl+Shift+D).** Switch the radio to another
sound card or USB headset in one keystroke instead of opening Preferences. It
changes the device immediately and remembers the choice, exactly like the
Preferences setting it shortcuts.

**Broadcast polish follows OptiLab Core 1.4.0.** If you use **Stream Polish**
for music, its Auto-Adapt slider behaves better now, particularly at the top.

Previously, raising Auto-Adapt pushed every stage harder at once -- the leveler,
the compressor and the limiter all leaned in together -- and that is what
produced the occasional volume lurch when the material changed. Following
upstream, each stage now fades in over its own part of the slider using
OptiLab's own smoothing curve, so there is no point where something switches on.
The leveler actually *eases off* as you raise Auto-Adapt, and a separate slow
loudness lift takes over instead.

That lift only responds to real program material: silence, low-level hiss and
rumble no longer cause it to build gain, which is the other half of what made
the old behaviour unpredictable. Bright, high-frequency moments get firmer
control as the slider rises rather than the flat presence boost the chain used
to apply at every setting, the limiter looks further ahead toward the top of the
range, and the whole chain now delivers to OptiLab's -0.1 dBFS target -- so high
settings give you more sustained loudness rather than more processing.

**Podcast Leveler** and **Smooth Limiter** are untouched: this release's
Auto-Adapt work is specific to Stream Polish.

With thanks to **dgl1984 / Lanes Audio**, whose OptiLab Core this is adapted
from -- <https://github.com/dgl1984/optilab>, licensed Apache-2.0 with the
Commons Clause. Quill Radio reproduces the shape of its modes as audio filters
rather than embedding the plugin, so broadcast polish works on any machine and
previews live as you move a control.

### And now the real thing, for recordings you keep

Reproducing the shape of those modes has one honest limit, and it is worth
stating plainly. OptiLab eases its lift and pulls back bass assistance *while*
its final limiter is working hard. The filter chain Quill Radio uses for live
listening cannot do that: nothing in it can see how hard a later stage is
working, so there is no way to react to it. Faking the effect would have meant
guessing, and a guess dressed as a feature is worse than an absence.

So for **saved recordings**, Quill Radio can now run the *actual* OptiLab
engine. Lanes Audio's processing code is included in the build and does the work
itself, rather than being imitated -- which means the feedback loop above simply
happens, and what you keep is what OptiLab would have produced.

**Live listening is unchanged, and deliberately so.** It keeps the built-in
chain, because that is what lets every adjustment be audible the instant you
make it, with no reconnect and no gap. A recording has no such constraint: it is
processed once, afterwards, where taking a moment longer costs nothing.

The distinction is worth holding onto, because it is the whole design:

| | Built-in chain | Exact OptiLab |
| --- | --- | --- |
| Where it runs | Everywhere -- live, relayed, recorded | Saved files only |
| Hear changes as you make them | Yes | No; it is not on the live path |
| Limiter feedback loop | Absent -- the chain cannot react to its own limiter | Present |

It is entirely optional. If your build does not include the OptiLab component
the option says so, and everything else works exactly as before.

**Sound Enhancements answers Ctrl+E.** The three-band equalizer -- Bass, Mid and
Treble, each freely adjustable from -12 to +12 dB, with Flat, Bass Boost, Voice
Clarity, Podcast, Small Speakers and Late Night as starting points -- along with
the compressor, channel mode, night mode and broadcast polish, has been in Quill
Radio since 1.0.2. What it never had was a key of its own; you went through the
Playback menu every time. **Ctrl+E** now opens it. Everything inside still
previews live as you move a slider, and is still remembered per station as well
as shared.

## Reach Quill Radio from anywhere -- one global hotkey

A new system-wide hotkey shows or hides Quill Radio without your having to find
its window first. Press **Ctrl+Alt+Shift+R** from inside any program -- your
browser, your editor, wherever you happen to be working -- and Quill Radio tucks
itself into the system tray, saying "hidden to the tray"; the music (or a
recording in progress) never stops, and the tray icon keeps it a keystroke away.
Press the same keys again and the window comes right back and takes focus,
announced with "shown". It is the fastest way to glance at what is playing, or to
step away and back, without leaving what you are doing. Windows only, and
courteous about it: if another app has already claimed Ctrl+Alt+Shift+R, Quill
Radio leaves that chord alone and never grabs it -- no error, nothing broken, and
the tray icon and the Alt+F4-to-tray preference still show and hide the window
exactly as before. Every app in the family gets its own chord so they never
collide: QUILL is Ctrl+Alt+Shift+Q, and Quill Weather is Ctrl+Alt+Shift+W.

## The QuillVille menu, and Weather as its own app

Quill Radio, QUILL, and Quill Weather each carry the same top-level **QuillVille**
menu (**Alt+Q**) listing every family member, so you can jump to any of them from
the same place everywhere. Opening an app that is already running just brings it
forward.

The weather work that grew up in this release has moved into a home of its own:
**Quill Weather**, a small, standalone, tray-resident app that watches your
location for official alerts, speaks each new warning the moment it is issued, can
start with Windows, and will even keep watch with no window open at all. Its full
story -- background alert monitoring, the customizable alert sounder, Test Alert,
the hour-by-hour forecast, the moon almanac, worldwide forecasts, and the rest --
now lives in the **Quill Weather release notes and user guide**, not here.

It is still right where you expect it inside Quill Radio, too. The **Weather** menu
is present whenever the **Weather** feature is enabled (**View > Customize
Features...**), and it now leads with an **Open the Quill Weather App** item so you
can hand the watch off to the standalone app in one step. Turn Weather off in
Customize Features and the menu disappears entirely -- perfect if you only want the
radio.

And on the radio side, **Station > Start Quill Radio with Windows** launches Quill
Radio automatically when you sign in.

## Quillins in Quill Radio

Quill Radio can run Quillins -- QUILL's small, sandboxed, permission-gated add-ons
-- from its own Quillins menu. A Quillin declares which apps it is for, so only
add-ons written for the radio appear. One thing a radio Quillin can do is
contribute an extra station directory, which then shows up alongside RadioBrowser
and the others when you search. Off in Safe Mode; third-party Quillins stay
disabled in this release.

## Spotify (experimental)

Quill Radio can search Spotify, browse your library and playlists, and play
through Spotify's own playback engine. It is **experimental**, and it needs
setting up -- so here is the whole thing, plainly.

### Does a free Spotify account work?

**Yes for finding things, no for playing them inside Quill Radio.** The
distinction is worth being precise about, because it is easy to hear "Premium
required" and conclude a free account is useless here. It is not.

**What works on a free account:**

- Searching Spotify from inside Quill Radio.
- Browsing your saved shows, episodes, tracks, and playlists.
- Everything else in Quill Radio, which is untouched by any of this.

**What does not:**

- Audio starting *inside Quill Radio*. A track you choose here will not sound.

**Why -- and what this is not.** This is **not** "free accounts cannot play
Spotify music". Of course they can, and millions of people do every day, in
Spotify's own app, where the advertising that funds the free tier lives. The
restriction is about **where** the audio plays, not whether you are allowed to
listen. Spotify does not license other people's apps to stream free-tier audio,
and it says so plainly in its own developer documentation. There are exactly two
ways another app could play a Spotify track, and both are closed to free
accounts:

- The Web Playback SDK, which "requires a Spotify Premium subscription (mobile
  only types of premium subscriptions are excluded)".
- The Start/Resume Playback web endpoint, of which Spotify says: "This API only
  works for users who have Spotify Premium."

So with a free account, use Quill Radio to *find* things -- which is the part
that is genuinely hard with a screen reader -- and play them in the Spotify app.
Quill Radio now tells you which kind of account you signed in with, immediately,
rather than letting you discover it when a track silently refuses to start.

### Spotify in Find Stations

Because searching Spotify works on **every** account tier, Spotify results now
appear in **Find Stations** alongside the radio directories, once you have
connected your account. Search once and you see stations, shows, and tracks
together, instead of remembering which of two search boxes holds which kind of
thing.

- Songs read as "title, artist", so a list of results is still usable when
  several share a name.
- Shows read as "show, publisher".
- Every Spotify row is labelled **Spotify** in the Source column, and there is a
  **Spotify** entry in the Source filter if you want only those -- or want them
  out of the way.

On a Spotify row, Shift+F10 offers **Open in Spotify**, which opens it in the
Spotify app. That is deliberately not called "Open Website": on a free account
it is not a footnote about a station's home page, it is *how you play the thing*.
Premium subscribers can simply press Enter and hear it here.

If you have never connected Spotify, nothing changes -- no Spotify rows appear,
and Find Stations behaves exactly as before. Off in Safe Mode. If Spotify is
slow or unreachable, the rest of your results still arrive.

For the same reason, a Spotify selection can never be **recorded** or
**downloaded** on any account, unlike every other station in the app: the audio
is copy-protected.

### What you need

1. **A Spotify account** -- free or Premium, per above.
2. **Your own Spotify Client ID.** Quill Radio ships no shared identity, so
   nothing of yours passes through anyone else's account.
3. **Windows with the Edge WebView2 runtime**, which current Windows already has
   -- it arrives with Microsoft Edge.

### Getting your Client ID, step by step

1. Go to the **Spotify Developer Dashboard** at
   `https://developer.spotify.com/dashboard` and sign in with your ordinary
   Spotify account. There is no charge, and this works with a free account.
2. Choose **Create app**.
3. Give it any **App name** and **App description** you like -- they are just for
   you. "Quill Radio" is fine.
4. In **Redirect URI**, enter exactly this, then press **Add**:

   `http://127.0.0.1:43217/callback`

   It must match character for character, including the port number. This is how
   Spotify hands the finished sign-in back to your own computer; it never leaves
   your machine.
5. Under **Which API/SDKs are you planning to use?**, tick **Web API** and
   **Web Playback SDK**.
6. Accept the terms and choose **Save**.
7. Open your new app's **Settings**. Your **Client ID** is shown there -- copy it.

   You will also see a **Client secret**. **You do not need it**, and you should
   not paste it anywhere. Quill Radio signs in with the modern PKCE flow, which
   is designed precisely for apps that cannot keep a secret.

### Where to put it in Quill Radio

1. **Station > Connect to Spotify...**
2. Paste your Client ID into the **Client ID** field.
3. Choose **Connect**. Your browser opens Spotify's own approval page: you are
   signing in to Spotify, and your password is never typed into this app.
4. Approve access. Spotify returns you to a small address on your own machine
   (`127.0.0.1`) that Quill Radio listens on for that one moment.
5. Your sign-in is stored in the **Windows Credential Manager** -- never in a
   plain file, never in a log -- alongside your Client ID, so the whole
   connection lives in one place and clears together.

You do this once. Afterwards, **Station > Browse Spotify...** opens a search box and
a results list you can arrow through and play with Enter.

Nothing reaches Spotify until you deliberately connect an account, and the whole
feature is refused in Safe Mode. If you would rather not see it at all, turn
**Spotify** off in Manage Individual Features and its menu items disappear.

## An icon of its own -- and one for every app in the family

Quill Radio's icon was never the problem. The problem was that it was also **Quill Inkwell's icon, Quill Weather's icon, and QUILL Audio Studio's icon** -- byte-identical copies of the same file, not similar drawings. On a desktop with more than one Quill app installed, four different products wore one face in the taskbar, in Alt+Tab, in the Start menu and in the notification area. Nobody chose that; each new app was built from the last one's template, and an icon is easy not to notice.

Every app in the family now has its own, and they are still recognisably a set: one rounded tile shape, one gold accent, one bold picture. What separates them is deliberate on two axes at once -- a distinct silhouette *and* a distinct colour that differs in lightness as well as hue, because a set separated only by hue is a set that some colour-blind users cannot tell apart, and colour is the first thing to go at small sizes.

Radio keeps the design it always had -- a source with waves leaving it, on a deep indigo tile -- redrawn for the size that actually matters. At 16 by 16 pixels, which is the notification area and the small icons in a file list, the old three thin arcs merged into a single smear. There are now two, thicker and further apart.

## Fixes

- **Quill Radio remembers your volume, and Ctrl+Up/Down works from anywhere.**
  The player started every session at 100% unless the station was a favorite with
  its own remembered level, so a non-favorite station came back at full blast on
  the next launch. The last level you set is now saved and restored (a favorite's
  own level still wins), and saving it no longer reloads the favorites list or
  re-announces the station. Separately, **Ctrl+Up** and **Ctrl+Down** only worked
  while the favorites tree had focus; they now work from any focus in the window
  -- except inside a text field, where Ctrl+arrow still edits text.
- **"Copy What's Playing" and "What's Playing - Review and Copy" always answer
  you.** With a station playing, both commands could come back having done nothing
  at all -- no window, no copy, no message -- while with nothing playing they spoke
  a sensible message, which made the bug look inverted. Now, if a station is on,
  both fetch the title first ("Checking what's playing..."), then copy it or open
  the review window; a stream that sends no titles says so and still opens a window
  naming the station; a failed lookup is reported instead of silently swallowed;
  and the copy confirmation names what it copied.
- **The Command Palette now says which way every toggle is currently set.**
  Two people asked for this about **Announce Track Titles**: the palette has no
  checkmark, so the entry read the same whichever way the switch actually was --
  you had to throw it to find out. It now reads **"Announce Track Titles
  (currently On)"** or **"(currently Off)"** and updates the moment you toggle
  it. That was never one entry's problem, though, so the fix was generalised:
  *every* on/off command in the palette now carries its own state, refreshed each
  time the palette opens.
- **Recording filenames follow the computer's current time zone.** Change the
  computer's time zone (or ride a daylight-saving shift) while Quill Radio is
  running and new recordings are named with the new local time straight away -- no
  restart. Filenames used to keep stamping the zone that was in force when the app
  launched.
- **Launching Quill Radio no longer crashes on a stray keystroke.** A key pressed
  at the wrong moment during launch could take the app down before its window
  appeared.
- **Every destructive question now defaults to No.** Remove Favorite, Delete
  Folder, Remove Recording, Remove All Favorites, and Reset Sound Enhancements all
  used to open with Yes as the default button, so pressing Enter reflexively
  destroyed the thing. Enter is now always the safe answer and you choose Yes
  deliberately. A build check keeps it that way.

## Where the older notes live

The 2.0 and 2.1 releases -- recordings you can trust, iHeart and TuneIn in the
search, weather radio and radio reading services -- have their own document,
`release-notes-2.0`, which ships in the `docs` folder beside this one.
