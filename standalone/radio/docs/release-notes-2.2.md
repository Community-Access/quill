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

**YouTube plays and records like any other station.** Paste a YouTube link into
**Add Custom Station** -- an ordinary video link, a `youtu.be` short link, or a
channel's live page -- and it becomes a station: it plays through the same
player, sits in Favorites, records with Record Now, and can be captured by a
scheduled recording. Quill Radio saves the *page* address, never a stream
address, and re-finds the audio each time you play or record, so a recording you
schedule today still works next week. It needs the small `yt-dlp` helper, which
is never bundled: it installs on demand (about 3 MB) after a one-time consent and
rights notice shown when you add your first YouTube station -- asked then, not
while a recording is firing at 3am. Off in Safe Mode. A private, removed,
region-blocked, or not-yet-live video says so in plain words.

**Paste a Live365 link and it just plays.** The Live365 link you actually have is
almost never the stream -- it is the station page or the web player, both of them
web pages that used to save as a station that could never play. Add Custom
Station now recognizes any Live365 station page, player link, or bare station id
and rewrites it to that station's real stream address, telling you it did. It is
a pure text rewrite: no network lookup, nothing sent anywhere, and a link that is
not Live365 is passed through exactly as you typed it.

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

Quill Radio can play music straight from Spotify, through Spotify's own playback
engine. It is **experimental**, and it asks a lot of you before it will do
anything: a paid Spotify **Premium** account (Spotify only lets an app stream its
audio for Premium subscribers), your own Spotify Client ID, and the Edge WebView2
runtime. Spotify audio is copy-protected, so a Spotify selection can never be
recorded or downloaded -- unlike every other station in the app.

Nothing reaches Spotify until you connect an account: sign-in is a one-time
network-access consent away, and the whole feature is refused in Safe Mode. If you
would rather not see it at all, turn **Spotify** off in Manage Individual
Features and its menu items disappear. The full story -- what you need, how to
connect, and how to browse and play -- is in the **"Spotify (experimental)"**
section of the Quill Radio User Guide.

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
- **The Command Palette now says whether Announce Track Titles is on or off.**
  The palette has no checkmark, so the entry read "Announce Track Titles On/Off"
  whichever way the switch was actually set -- you had to throw it to find out. It
  now reads **"Announce Track Titles (currently On)"** or **"(currently Off)"**,
  and updates the moment you toggle it.
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
