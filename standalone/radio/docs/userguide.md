# Quill Radio User Guide

Version 3.0.0

Quill Radio is internet radio the way a screen reader user would design it: a small window whose favorites tree has focus the instant it opens, menus that say everything they do, spoken feedback for every action, and a tray icon so the music keeps playing while you work. It runs the exact same radio code as QUILL itself and shares its data, so nothing you set up here is ever stranded.

## Installing

Quill Radio comes in four downloads. Two of them are brand new in this release and much smaller than before, because Quill Radio can now share one Python engine -- the QuillVille Runtime -- with every other QuillVille app. The section just below explains the runtime; the one after it lays out the four downloads so you can pick the one that suits you.

If you are not sure which to choose: the **full installer** is the easy, recommended path for most people, and the **full portable zip** is the one to put on a USB stick.

### The QuillVille Runtime: install the engine once, and every app starts instantly

Quill Radio is part of a small family of apps -- QUILL itself, Quill Radio, Quill Weather, and QUILL Audio Studio. They are separate apps, but underneath they all run on the same Python engine.

Starting with this release, that engine is installed just once per user, as a shared component called the **QuillVille Runtime**, and every QuillVille app reuses it. Install any one app that carries the runtime, and every app you add afterward starts instantly, because the engine it needs is already on your PC. There is no second copy, no second long download.

The runtime looks after itself. It is reference-counted: Windows keeps track of how many QuillVille apps rely on it, and it is only removed when you uninstall the very last app that needs it. Uninstalling Quill Radio while, say, Quill Weather is still installed leaves the shared runtime in place for Weather; uninstalling the last one cleans it up for you.

### The four downloads

You can install Quill Radio in whichever of these ways fits you best. In each filename, `<version>` is the release you are downloading, such as 3.0.0.

1. **Full portable zip** -- the file named `Quill-Radio-Portable-<version>.zip` (about 311 MB). Fully self-contained: extract it anywhere -- a folder, an external drive, a USB stick -- and run `QuillRadio\QuillRadio.exe`. There is no installation and nothing ever downloads at runtime. It carries its own genuine, unmodified copy of Python, plus the bundled ffmpeg (for recording) and mpv (for playback) engines. Its `data` folder keeps your favorites, history, recordings, and settings inside the app folder, so the whole radio travels with you. This is the one to reach for when you want a self-contained radio with no installer and no internet.

2. **Companion edition (new)** -- the file named `Quill-Radio-Companion-<version>.zip` (about 3 MB). Feather-light: it contains only the app itself and its documentation, and it runs on the shared QuillVille Runtime. The first time you launch it, if the runtime is not already installed, Quill Radio offers to download and install it for you -- about 230 MB, once -- with a fully accessible progress bar (see "Accessible progress every time" below). After that, this app and every other QuillVille app start instantly. Choose the Companion edition when you would rather download three megabytes than three hundred, and you are happy for the shared engine to be fetched once on first launch.

3. **Full installer** -- the file named `Quill-Radio-Setup-Shared-<version>.exe`. A standard Windows installer that gives Quill Radio its own Start Menu entry and an uninstaller. It installs the shared QuillVille Runtime (unless it is already present from another QuillVille app) and then the app. Your favorites, history, and settings live in the shared Quill store in your Windows profile. This is the recommended path for most people.

4. **Thin installer (new)** -- the "Lite" installer, a very small setup program that installs the app and downloads the shared QuillVille Runtime only if it is not already present. If you already run another QuillVille app, there is nothing large to fetch and the install finishes quickly. Choose it when you want a proper installed app but the smallest possible download.

### Accessible progress every time

Whenever the QuillVille Runtime is being downloaded -- whether an installer is fetching it or the Companion edition is fetching it on its own first launch -- Quill Radio shows a fully accessible progress bar. It works with NVDA, JAWS, and Narrator, and progress is announced as a percentage as it climbs. You always know how far along the download is, and when it is finished.

### About security software and antivirus

This release changes how Quill Radio starts, specifically to be friendlier to antivirus software.

Quill Radio's launcher is now a genuine, tiny native program, and the Python it runs is the official, unmodified build. Earlier versions used a renamed and modified copy of Python's own `pythonw.exe` as the launcher. That pattern is a common one for antivirus tools to flag, and some of them did -- as a false positive, but an understandable one. That pattern is now completely gone. The result is an app that is far less likely to be mistaken for something it is not.

Releases are code-signed as of 3.0: the installers, the uninstallers, and the app itself carry a genuine Authenticode signature, so Windows can verify who built what you are running. If SmartScreen still shows a caution while a newly published release builds reputation, the signature is there to check -- and the build is exactly what this repository's source produces.

## Getting started

### The first time you open it

The very first launch shows a short welcome: three screens -- what Quill Radio
is, the three ways to find something to listen to, and how favorites work. Each
one names the actual key for the thing it describes, so if you have already
rebound something in the Keyboard Manager it tells you *your* key, not the
default.

Two things to know about it:

- **Skip leaves in one keystroke**, and skipping counts as done. It will not
  come back and ask again.
- **It never appears if you already have favorites** -- an imported station
  list, a restored backup, or an upgrade from an older Quill Radio. It is for
  somebody starting from nothing, and nobody else.

On the second and third screens there is a **Browse Stations Now...** button, so
you can leave the welcome and go straight to finding a station.

There is also a checkbox, **Show me a tip now and then**. Tips are one sentence
each, shown once ever, the first time you reach somewhere that a single
non-obvious fact would help -- that live radio can be paused and rewound, that
Quill Radio remembers a volume for each station separately, that a recording can
be scheduled for a programme that has not started yet and will wake the computer
to catch it. They never take the keyboard and they never repeat. Unchecking the
box switches all of them off permanently.

### Every launch after that

Launch Quill Radio from the Start Menu (or the portable folder's `QuillRadio.exe`). The window opens with keyboard focus on your **Favorite stations** tree.

- No favorites yet? Press Alt+S for the Station menu, then **Browse Stations...** to wander a tree of every source -- popular stations, NOAA Weather Radio, radio reading services, whole directories -- or **Search Stations...** to search thousands of stations by name, genre, country, or language. Either way, listen before you commit, and add the keepers to your favorites. The **ACB Media** submenu is also right there -- the whole ACB stream directory, playable without any setup.
- With favorites: arrow to a station and press **Enter**. That is the whole loop.
- Want the radio on the moment the app opens? Check **Station > Resume Last Station on Launch** once, and Quill Radio becomes an appliance: launch it, and your station is already playing.

Everything Quill Radio announces goes through the same announcement engine QUILL uses, so it speaks through your screen reader (JAWS, NVDA, Narrator) without stealing focus.

Those announcements also go to a connected **braille display**, not just to speech -- what's playing, a finished directory refresh, a recording starting. Nothing is shortened, so a long track title is there in full for you to pan through, and the same message repeated within a couple of seconds does not flash the display twice (a flash message replaces whatever is under your fingers, so repeats are worse than useless). If a burst of different messages arrives at once, the first is written immediately and the rest settle to the newest, rather than each shoving the last aside faster than cell one can be read; errors always write through straight away. Braille never costs you speech: an unplugged display, or a screen reader that will not take the message, simply means it was spoken and not brailled -- never silence. Turn it off with **Show announcements in braille** in Preferences, under Accessibility.

## Your first half hour, step by step

This chapter assumes nothing. Every step says which key to press and what you
should hear. If you have never used Quill Radio before, work straight down it
and you will finish with a station playing, a favorite saved, a recording made,
and the six keys that matter in your fingers.

If something does not happen as described, that is worth reporting rather than
working around -- **Alt+H**, then **R** for **Report a Bug...**, fills most of
the report in for you.

Throughout: **Escape** always steps back out of wherever you are, and no step
below can lose anything you have not deliberately saved.

### Task 1: play your first station (about two minutes)

1. Launch Quill Radio from the Start Menu, or run `QuillRadio.exe` from the
   portable folder.
2. Wait for the window. You should hear **"Favorite stations, tree"** or your
   screen reader's equivalent -- focus lands in the favorites list on its own,
   and there is nothing to Tab to first. If the list is empty, that is expected
   on a fresh install.
3. Press **Ctrl+B**. This is **Browse Stations**, and it opens a window with one
   big tree in it. You should hear **"Entered Browse Stations"** and land in the
   tree.
4. Press **Down arrow** a few times. Each press reads a source: Favorites,
   Popular Stations, Radio Browser by Genre, Weather / NOAA, ACB Media, and so
   on. Nothing has loaded from the internet yet -- these are just the branches.
5. Stop on **Popular Stations** and press **Right arrow** to open it. The first
   time, this fetches the list, so give it a moment; Quill Radio announces when
   the stations arrive.
6. Press **Down arrow** to move onto a station, then press **Enter**.
7. You should hear **"Playing"** and then the station. That is the whole loop:
   arrow to a thing, press Enter.
8. Press **Ctrl+Down** twice. Each press says the new level -- **"Volume 80
   percent."**, then **"Volume 70 percent."** Volume moves in steps of ten, and
   it says the number every time, in every window.
9. Press **Ctrl+P** to stop, and **Ctrl+P** again to start. It says **"Stopped."**
   and **"Playing."** so you never have to guess which way the toggle went.

Leave the station playing for the next task.

### Task 2: keep it (about one minute)

1. Press **Escape** to close Browse Stations. You should hear **"Exited Browse
   Stations"**, and focus returns to the main window's favorites list.
2. Press **Alt+F**. That is the **Add to Favorites** button, reachable without
   Tabbing to it. You should hear **"Added *station* to Favorites."**
3. Press **Down arrow** in the favorites list. Your station is there.
4. Press **Enter** on it. It plays. From now on this is your two-keystroke
   route to that station: launch, Enter.

That is the core of Quill Radio. Everything below is optional.

### Task 3: work the player from anywhere (about three minutes)

The player is one object, and every window can reach it. This is the part that
makes Quill Radio different from a player with a window you have to go back to.

1. With something playing, press **Ctrl+B** to open Browse Stations again.
2. Press **Ctrl+Up**. The volume goes up and says so -- **from the browse
   window**, without going back to the main one. The same is true of
   **Ctrl+P** (play/stop), **Ctrl+Shift+O** (mute and unmute), and every other
   transport key in the reference at the end of this guide.
3. Press **Ctrl+Shift+G**. This is **Go to Player**, and it opens the
   **Player window**. You should hear **"Entered Player"**. If the player is
   already open somewhere behind you, the same key **brings it to the front**
   instead of opening a second copy -- one key, one player, always.
4. Press **Tab** through it. The first thing is a read-only **Now playing**
   box saying what is on, where you are in it, how fast it is playing and how
   loud. After that come the buttons, in the order people reach for them:
   Play/Pause, Stop, Skip Back, Skip Forward, Where Am I, chapters, speed,
   volume, mute.
5. Press **Escape**. The player closes and focus goes back to the window you
   came from.

The player is a real window: it stands in the Window menu and the Ctrl+Tab
rotation like Browse Stations does, so you can keep it open beside whatever
you are doing and flick over to it whenever you want.

### Task 4: do anything by name (about one minute)

If you cannot remember a key, you never need to.

1. Press **Ctrl+Shift+P**. This is the **Command Palette**, and it opens from
   **every** window -- the main one, Browse Stations, the Favorites Manager,
   the Recordings list.
2. Type a few letters of what you want -- `vol`, or `record`, or `chapter`.
   The list narrows as you type.
3. **Down arrow** to the command you want and press **Enter**. It runs, exactly
   as the key or the menu item would, and each entry shows its own keystroke so
   the palette teaches you the shortcut while you use it.

The whole player is in there, so the palette can pause what is playing, not
just change a setting.

### Task 5: record something (about three minutes)

1. With a station playing, press **Ctrl+R**.
2. You should hear that recording has started. The status bar's Record cell
   now reads **Stop Recording** with the time, and the now-playing line notes
   the recording, so more than one place agrees it is happening.
3. Wait ten or twenty seconds.
4. Press **Ctrl+R** again to stop. Quill Radio names the file it saved.
5. Press **Ctrl+Shift+R** to open the **Recordings** list. Your recording is at
   the top -- newest first. (**Ctrl+G** now opens **Go To**, the list of places;
   Recordings is in it, so Ctrl+G then its number works too.)
6. Press **Enter** on it to play it back.
7. Press **Delete** to remove it. A confirmation appears; press **Enter** or
   **Y** for Yes. Focus lands on the recording that took its place in the list,
   not at the top and not nowhere.
8. Press **Escape** to leave the Recordings list.

### Task 6: the six keys worth memorising

Everything else is in the menus and the palette. These six carry the day:

| What you want | Key |
| --- | --- |
| Play or stop | Ctrl+P |
| Volume up or down | Ctrl+Up / Ctrl+Down |
| Go to the player, from anywhere | Ctrl+Shift+G |
| Do something by name | Ctrl+Shift+P |
| Browse for stations | Ctrl+B |
| What is playing right now? | Ctrl+T |

### If you get lost

- **Escape** closes the window you are in and says which one you left.
- **F6** moves into the status bar along the bottom -- the transport buttons
  (Play/Stop, Mute), the volume, recording, the sleep timer, and the time. A
  second **F6** or **Escape** brings you back. (Tab never lands there; F6 is
  the door.)
- **Ctrl+Shift+G** brings the player to you, wherever you are.
- **F1** explains where you are: the window's purpose, then the control under
  focus -- in a text field you can arrow through. **Ctrl+F1** opens this guide.
- **Alt+H** then **U** opens this guide.

## The player follows you

Older versions of Quill Radio had one player and more than one place that knew
how to talk to it -- and only the main window had keys. Standing in Browse
Stations you could hear a podcast and not change its speed, because speed lived
on the main window's menu bar and a menu accelerator only fires for the window
that owns the menu bar. Half the player did not exist in the window you were
standing in.

That is over. Every window Quill Radio opens answers to the whole transport:

- Browse Stations
- Find Stations
- Manage Favorites
- The Recordings list
- Song History
- The Chapter list
- Now Playing
- The download queue
- Find Streams from a Website
- The player panel itself

In all of them, **Ctrl+P** plays or stops, **Ctrl+.** stops outright,
**Ctrl+Up** and **Ctrl+Down** move the volume, **Ctrl+Shift+O** mutes and
unmutes, **Ctrl+Shift+Left** and **Ctrl+Shift+Right** skip, **Ctrl+Shift+Up**
and **Ctrl+Shift+Down** change speed, **Ctrl+Shift+,** and **Ctrl+Shift+.**
move by chapter, **Ctrl+Shift+C** opens the chapter list, **Ctrl+Shift+W** says
where you are, and **Ctrl+Shift+G** summons the player panel.

Three things follow from having one table of keys rather than several:

- **A key means one thing everywhere.** Volume moves the same distance and
  reports it in the same words in every window, because there is one
  implementation and one sentence behind all of them.
- **A key that cannot act says why.** Ask for speed or chapters while a live
  stream is playing and you hear *"This is live radio, which plays at broadcast
  speed and has no chapters or position to move through."* A key that quietly
  does nothing is indistinguishable from a key that is not bound at all, which
  is how people conclude an app is broken.
- **A key that does act says so too.** Play, Stop and Mute all speak. Mute
  especially: silence is what muting is *for*, so without a word there is no
  way to tell muting apart from the stream dropping.

### Go to Player (Ctrl+Shift+G)

The Player is a small window of its own. It holds the whole transport as
buttons, plus a readout of what is playing, where you are in it, the speed and
the volume, and it stands in the Window menu and the Ctrl+Tab rotation like
any other window.

- **Ctrl+Shift+G opens it -- and if it is already open, brings it to the
  front.** One key always reaches the player; it never stacks a second copy.
- Every button runs the same thing the keys and the menus run, so the player
  can never drift from them, and a verb the thing playing cannot do refuses
  out loud here exactly as it does everywhere else.
- The keys work **inside** the player too, and every one of them re-reads the
  readout, so a key and a button leave the player saying the same thing. The
  readout also follows changes made anywhere else while the window sits open.
- **Escape** (or Ctrl+W, or Ctrl+F4, or Alt+F4) closes it and puts focus back
  in the window you came from.

## The main window

Tab order: the now-playing line, the favorites tree, then Mute and Volume.
Four stops, deliberately -- this is a list you play from, not a player.

- **Now playing** (a read-only box you can tab into): what is on right now -- the station and what the player is doing, the track when there is one, and a line for anything else true, such as a recording running. It is a real control rather than a label, so you can **arrow through it**, review it a word at a time, and **copy it** with Ctrl+C when you want to know what that track was. It is never rewritten while you are reading it: an update that arrives while it has focus waits until you leave, rather than moving the text out from under you. Elapsed position is not in it on purpose -- it changes every second -- so press **Ctrl+Shift+W** when you want to know where you are.
- **Favorite stations** (tree): the same nested folder structure you build in the Favorites Manager, right on the main page. Enter plays a station, Delete removes it (with confirmation), F2 renames a station or folder, and Shift+F10 opens the full context menu -- Play/Stop, **Station Details...** (a reviewable, copyable readout of the station's source, stream, format, and country -- the same view the search results give), Rename, Move to Folder, Remove, New Folder, Mark for Move, and Manage Favorites. Your custom names are used everywhere.
- **Mute** (toggle button): new on the main window, and exactly the control the Browse window has always had -- same label, same **Ctrl+M**. It follows whatever the rest of the app does rather than only sending, so it never shows the opposite of the truth.
- **The buttons that used to be here are not gone, only moved.** Play/Stop is **Enter** on a station, or **Ctrl+P** from anywhere. Record is **Ctrl+R**. Browse Stations is **Ctrl+B**. Chapters live in the player (**Ctrl+Shift+G**). Adding the playing station to favorites is **Ctrl+Shift+F**, on the Station menu and in the player. The main window stopped being a second copy of the player, which is what it had quietly become.
- **Volume** (slider): last in the Tab order, so you can tab to it while a station is playing and use the **arrow keys** (or Page Up/Page Down) to turn the volume up or down. It is one of three ways to set the volume -- the others are **Ctrl+Up/Ctrl+Down** from anywhere in the window, and the status bar's Volume cell -- and all three stay in agreement, including with each station's remembered volume.
- **Status bar** (along the bottom): a row of buttons that lead with **actions** -- **Play** (reading **Stop** while something plays), **Mute** (reading **Unmute** while muted), **Volume** (the level, with a note when Volume Boost is on), **Record Now** (reading **Stop Recording** with the time left or elapsed while a capture runs), **Sleep timer**, and the **time**. Press **F6** to move focus into it -- and only F6: Tab around the main window never detours through the bar. Inside, arrow **Left** and **Right** to move across the cells (**Home** and **End** jump to the ends), **Enter** or **Space** presses the one you are on, and a second F6 or Escape hands focus back to the favorites tree. Each cell's **Applications key** / right-click menu is where the depth is: the Play cell offers **your favorites and recent stations, recording, and Browse Stations**; Mute and Volume offer **Volume Up/Down, Volume Boost, the Output Device, and Sound Enhancements**; Record offers **Schedule Recording, the Recordings window, and Recording Settings**; Sleep timer offers the **Wake-Up Timer** too. Turn the whole bar off from **View > Show Status Bar** if you would rather not have it.

### What the status line is telling you

The main window's Now playing line (and the tray tooltip, which says the same
thing) has one line for each thing a stream can be doing. They are
deliberately different words, because they are different situations and only
some of them are your doing:

| What it says | What is happening |
|---|---|
| `Radio: stopped` | Nothing is playing. |
| `Radio: connecting to WQXR...` | A station you just chose is being opened. |
| `Radio: buffering WQXR...` | It was playing and ran out of audio. The stream is refilling; you did not do anything, and it usually comes back on its own within a few seconds. |
| `Radio: playing WQXR` | Playing. `(muted)` is added when the sound is muted. |
| `Radio: paused - WQXR` | You paused it. On a live station this is a real pause, and you can rewind into what you missed. |
| `Radio: Reconnecting to WQXR. Attempt 2 of 3.` | The stream dropped and Quill Radio is getting it back. Each attempt is spoken as well as shown, so a long wait never sounds like the app has hung. Three attempts, at two, five and fifteen seconds; after that it stops and says so. |
| `Radio: could not play WQXR - ...` | It failed, with the reason. |

Buffering and reconnecting are worth telling apart. **Buffering** means the
stream is still there and the audio ran out for a moment. **Reconnecting** means
the connection went away and is being rebuilt. Both used to read as either
"playing" or "connecting", which was the app saying something it did not know.

## Go To: one key for every place

Press **Ctrl+G** anywhere in Quill Radio and a short numbered list opens. Press
the number, and you are there. Escape closes it and puts you back exactly where
you were, on the same control.

The default list:

| Key | Place |
| --- | --- |
| 1 | Favorites (the main window) |
| 2 | Browse Stations |
| 3 | The Player |
| 4 | Recordings |
| 5 | Downloads |
| 6 | Manage Favorites |
| 7 | Song History |
| 8 | Listening Statistics |
| 9 | Find Stations |
| 0 | Preferences |

Ten places, numbered 1 to 9 and then 0 -- the number row, in the order your hand
meets it.

**The number never changes on its own.** Recordings is 4 today and 4 next year,
whether or not it is open. That is the whole point of the list, and it is what
Ctrl+1 to Ctrl+9 cannot do: those reach the windows you have *open*, in the
order you opened them, so the numbering shifts under you all day.

Each row also shows that place's own direct shortcut, where it has one. That is
deliberate: use Ctrl+G 2 for a month, read "Browse Stations, Ctrl+B" every time,
and one day you will find you no longer need the list.

### Making it yours

**Go To Settings** -- the Settings button in the list, or **View > Go To** --
chooses which places are in the menu and in what order. It is the same window
as Choose Columns: two lists, one of what is in the menu and one of what is not,
with **Move Up** and **Move Down**. Put what you use most at 1.

Places you can add: Scheduled Recordings, Station Catalog Status, Audio Health,
Keyboard Shortcuts, and What's Playing.

The menu holds ten because the number row does. Asking for an eleventh says so
and suggests removing one first, rather than refusing silently.

**An update will never renumber your list.** A place added in a later version
waits in the "not in the menu" list until you put it somewhere, so whatever you
have learned stays true.

## Windows, and moving between them

Quill Radio's bigger surfaces -- **Browse Stations**, **Search Stations**, **Manage Favorites**, **Schedule Recording**, **Recordings**, **Downloads**, **Song History**, the **Now Playing / Station Details** viewer, and **the Player** -- open as their own **windows**, not dialogs. Several things follow from that, all on purpose:

- **Each one is a real, independent window.** It stands on its own -- in the taskbar and the Alt+Tab order too -- rather than floating glued on top of the main window. Browse is beside the favorites list, not over it.
- **The menu bar is always there.** Every window carries a menu bar, so Alt reaches menus no matter which window you are in. (Older versions used dialogs, which cannot carry a menu bar, so opening one made the menus seem to disappear.)
- **The main window stays reachable.** Opening one of these windows never locks you out of the favorites list; you can keep several windows open at once and work across them.
- **They close the way windows close.** **Escape**, **Ctrl+W**, **Ctrl+F4**, **Alt+F4**, or the titlebar -- take your pick. There is no Close button on them any more: a button labelled Close on a status-bearing window kept reading as an action that did something more, and a window already has its ways out.
- **Asking for a window that is already open brings it to the front** rather than opening a second copy.

A **Window** menu on every window lists what is open, numbered in the order you opened them. To move between windows:

- **Ctrl+Tab** goes to the next window, **Ctrl+Shift+Tab** to the previous one (it wraps around).
- **Ctrl+1** through **Ctrl+9** jump straight to the first through ninth open window.
- Or open the **Window** menu and pick one by name and number.

Each window opens only when you ask for it, and closing a window puts focus back in the window you came from. Moving to a window with Ctrl+Tab or the Window menu drops your focus **on the control you last used there** -- the same row of the same list -- or on the window's main control the first time. Quill Radio announces "Entered ..." as a window opens and "Exited ..." as it closes. (Inside QUILL itself these same surfaces open as ordinary dialogs; the multi-window model is the standalone Quill Radio experience.)

## Menus

### Station (Alt+S)

- **Browse Stations...** -- a search-free window for wandering: one tree whose top-level branches are the sources. **Favorites** sits first (your own folders and streams), then **Popular Stations**, **Radio Browser (by Genre)** (walk the Radio Browser directory by genre, not only search it), **Weather / NOAA**, **ACB Media**, **NFB Radio**, **Radio Reading Services**, **SomaFM**, **TuneIn** (its real folder tree, which drills from continent down to city), **Networks** (well-known broadcasters -- the BBC, NPR, CBC, ABC Australia, Radio France, Deutschlandfunk, public radio worldwide, plus national news and sports -- grouped by type, each a one-click list drawn from the Radio Browser directory; a few, like Westwood One, are syndication services with no single stream, so those open a search across their local affiliate stations, and the label says so), **Community M3U (Music Genres)**, and the **Xiph / Icecast Directory**. Version 3.0 added nine more: four new axes over the station directory Quill Radio was already downloading -- **By Country** (then by state or region), **By Language**, **Trending Now**, and **Recently Added or Changed** -- and five whole libraries: **Podcasts (Apple)**, **Internet Archive**, **LibriVox Audiobooks**, **Project Gutenberg Audiobooks**, and free music from **Audius**, **Mixcloud** and **ccMixter**. None of them needs a key, an account, or a registration of any kind. Expand a branch and its stations load on the spot; **Enter** plays the highlighted station, and **Shift+F10** (or right-click) opens Play/Stop, Add/Remove Favorite, Copy stream link, Open website, **Report Bad Station...**, and Refresh. (TuneIn stations work out their stream only when played, so **Add to Favorites** on a TuneIn station resolves it on demand before saving -- it works there now just like every other source.) Browse Stations also **remembers the source you were last in**, so playing a station and reopening the tree puts you back on that branch instead of collapsed at the top with everything closed. Two branches deserve their own words:
  - **Weather / NOAA** is the real NOAA Weather Radio directory, state by state. Open the branch and you get the states (each with its transmitter count); open a state and you get its actual transmitters, named with call sign, frequency, and place -- "KHB36 162.550 MHz Manassas" -- and Enter plays the best available internet re-stream. The complete directory (1,035 transmitters) is bundled inside the app, so this branch works even offline. See "Your local NOAA Weather Radio" in the Weather chapter for the one-keypress local version.
  - **Radio Reading Services** lists the audio information services that read newspapers, magazines, and local print aloud for people who are blind or print-disabled -- WRBH 88.3 Reading Radio, Sun Sounds of Arizona, CRIS Radio, the Connecticut Radio Information System, the KPBS and WKAR reading services, ACB Media 1-5, the NFB Radio Network, Voice Corps, and more. Twenty vetted services are bundled, so the branch is never empty; play, favorite, record, and schedule them like any other station.
  - **iHeart** opens into **genres** (Country, Pop, News/Talk, Sports, and the rest), and each genre into an **A-Z** sub-directory of its stations -- so you expand a genre, expand a letter, and press Enter to play. Each level loads only when you open it. (Browsing uses iHeart's own genre directory; a station's stream is ready to play with no extra step.)
  - **By Country, By Language, Trending Now, Recently Added or Changed** are four views of the same community directory the tree has always used. Open **By Country**, pick a country, and you get its states or regions; open one and you get its stations, most-listened first. A country with no regional breakdown gives you its stations directly rather than making you open an empty folder to find that out. **By Language** is the same data on the axis that is hardest to find elsewhere -- the radio you want is not always in the language of the country you are sitting in. **Trending Now** is not the same as **Popular Stations**: popular ranks by votes cast over years, trending ranks by what is being listened to today, and the two lists disagree more than you would expect. **Recently Added or Changed** is new stations and ones whose address was just repaired.
  - **AudioPub (Community Audio)** -- audio that people made and shared publicly on audiopub.site. Its **Discover** shelf is a random fifty, different every single time, each row named with its creator and play count, each playable with a full timeline; a "More to discover" row keeps going. Nothing from AudioPub is stored on this computer -- the uploaders keep the rights to their audio, and Station Catalog Status says so. Discover is deliberately the only shelf for now: newest, popular, search and live broadcasts wait on AudioPub's developer blessing a public interface for them.
  - **Podcasts (Apple)** -- choose a country and you get that storefront's top shows plus Apple's whole podcast genre tree, with subgenres beneath each genre. Open a show for its episodes; **Enter** on an episode plays it. There is no key, no account and no sign-in at any step, and the top podcasts in Ireland, Japan or Brazil are one folder away. Apple is only how the show is *found*: opening a show resolves it to the publisher's own RSS feed, and the episode list, the audio and the transcripts all come from there. Quill Radio does not use Podcast Index, deliberately -- Apple answers the same questions with nothing to register for.

    **Subscribing, and finding what you subscribed to.** **Shift+F10** on a show offers **Subscribe to This Podcast**, which files it in the shared podcast library -- the same library Quill Cast reads, so the show is simply *there* the next time Cast opens. And it is findable right here too: the Podcasts branch leads with a **Subscriptions** folder, one folder per show you follow, each expanding to its newest episodes. On a show you already follow, the same menu slot reads **Unsubscribe from This Podcast** instead. The Subscriptions folder wears your follow count as its badge -- "Subscriptions (3)" -- and each show beneath it wears "(2 unheard)", the same count Quill Cast shows, so what is waiting is visible from either app. An episode whose feed publishes a transcript says "transcript available" on its row, and **View Transcript...** on its context menu opens it in the transcript reader without playing anything. How many episodes each show lists is a preference (**Ctrl+,** > "Episodes listed per subscribed podcast", 25 newest by default) -- deliberately Quill Radio's one podcast setting. Playback, downloads and per-episode actions work exactly as anywhere else in the tree; the rich side of podcasting -- automatic downloads, retention, the play queue, the full archive -- is **Quill Cast**'s job, and that is where a serious podcast habit belongs.

    **The show's own menu does the housekeeping.** A subscribed show's context menu carries **Move to Folder...** (Enter in the picker confirms; the tree reloads and the cursor lands on the show in its new home), **Mark All as Played...** (dimmed when nothing is unheard; its confirmation has a "Don't ask me again" checkbox shared with Quill Cast, and the badges clear on screen the moment it speaks), **Download All N Episodes...** (counted from the shared library, so it works without expanding the show), and **Remove All Downloads...** (files gone, subscription and played state untouched; dimmed when nothing is downloaded). Episode rows of a subscribed show add **Mark Episode as Played** / **as Unplayed**, one direction at a time. And the badges believe your ears: finish an episode here and the show's unheard count drops immediately, without waiting for Quill Cast's next launch.
  - **Internet Archive** -- Old Time Radio, Audiobooks & Poetry, the Live Music Archive, Radio Programs, News & Public Affairs and more. Open a collection for its series, a series for its episodes, an episode for its files. The depth is the Archive's own; Old Time Radio alone holds 8,710 recordings across 114 series. A folder holding more than one page ends with **More...**, which says how much it is still hiding, and an item that publishes no rights information says exactly that rather than letting you assume it is free to reuse.
  - **LibriVox Audiobooks** -- **Recently Added**, **By Genre** (43 genres), and **By Author**, grouped A to Z across some seven thousand of them. A book with chapters is a folder of chapters; a book that is one single reading is simply playable. There is deliberately no **By Title**: LibriVox's catalogue supports author, genre and date filters and no title filter in any form, and a branch that quietly finds nothing is worse than one that is not offered.
  - **Project Gutenberg Audiobooks** -- the 1,124 Gutenberg records that carry human-read audio, by topic and by language, each shelf paging through completely via a "More audiobooks" row. It complements LibriVox rather than duplicating it. With the station catalog on, All Audiobooks answers from your own disk, instantly.
  - **Saving what you are allowed to save.** Right-click (or Shift+F10) a book chapter, an archive recording, a Creative Commons track or a podcast episode and choose **Download...** to keep it. On a book's folder, **Download All Files...** saves every chapter into one folder, in order, while you carry on listening -- it resumes a part-finished file rather than starting again, one bad chapter costs only that chapter, and stopping keeps everything already saved. Quill Radio only offers this where the source's terms clearly allow it; where it does not, asking anyway tells you why, and the four reasons are genuinely different. A **live station** has no file to save at all (that is what Record Station is for), **Spotify** is copy-protected, **YouTube** is a deliberate exclusion, and for **Audius** the choice belongs to the artist and is not stated in the listing. A Creative Commons track is saved with its licence in a small text file beside it.
  - **The download queue.** Everything you save goes through one queue, one at a time, in the order you asked -- so you can queue several books and carry on listening. **View > Downloads...** (Ctrl+Shift+J) shows what is waiting, what is downloading, what was saved and what failed. **Open Containing Folder** takes you to a finished file; you can cancel one, remove a row, clear the finished ones or clear the lot, and any of those keeps whatever is already on your disk. If you close the window with downloads still going, Quill Radio either finishes them in the background or stops them -- whichever you chose in **Station > Download Preferences** -- and tells you which it did. That same Preferences window is a button away inside the queue, because that is where the question tends to occur to you.
  - **Where downloads are filed.** A podcast goes in a folder named for its show; a book gets a folder of its own; and once you have more than one book by the same author, that author gets a folder too. You can switch any of that off, choose your own folder, or ask to be prompted every time.
  - **A downloaded book plays like a book.** Its chapters are in proper order (chapter 2 before chapter 10), and when one finishes the next starts on its own, announcing where you are -- "4 of 40". When the last chapter ends, Quill Radio says so rather than simply going quiet.
  - **Audius**, **Mixcloud** and **ccMixter** -- independent and Creative Commons music. Audius gives you trending overall and within 27 genres, and drops pay-gated tracks rather than listing them and refusing when you press Enter. Mixcloud gives you 28 music and 10 talk categories of DJ sets and radio shows, and is **metadata only**: Quill Radio never extracts a Mixcloud stream, so activating a show opens it on Mixcloud in your own browser -- and the row says so *before* you press Enter. ccMixter is Creative Commons music by tag, with each track's licence shown on its own row.
  - **Explore (Wikidata)** -- browse axes no station directory publishes: **By City**, **By Format**, and **On the Dial** by FM frequency band. Wikidata supplies the organisation behind a station and Radio Browser still supplies every stream, so nothing here changes how a station plays, records or is favorited; the rows are labelled "from Wikidata" because the match between the two is made by Quill Radio, not published by either. Opening a place (or a format) asks Radio Browser for it directly, so you get the stations that can actually play rather than only the ones Wikidata happened to list. There was a **By Owner** axis and it has been removed: the station directory does not record who owns a station, so an owner folder had to be assembled call sign by call sign, and roughly three of them in four opened to nothing or to a fraction of the company named. Every axis still here is one the directory can answer for itself.
  - **Some branches remember where you stopped.** A live station has no position worth keeping -- you tune in and you are where everyone else is. A recording does: a LibriVox chapter, an Old Time Radio episode, a podcast episode. Quill Radio saves your place in those as you listen and offers it back the next time you play them. A few seconds in is not a position and is not offered, and finishing something clears its place so replaying starts at the beginning rather than the closing credits.
  - **My Servers** -- the branch no directory can give you. A community station, a church, a school, a reading service running its own Icecast or SHOUTcast box was never indexed anywhere, and almost all of them publish a complete list of what they are serving right now. Open **My Servers**, choose **Add a Server...**, and paste the address (if it is already on your clipboard it is filled in for you). Quill Radio checks it before saving it and tells you what it found -- "Added http://stream.example.org:8000. It has 4 stations." An address that answers with nothing is **not** saved, because a branch that is empty the day you add it is nearly always a wrong address, usually a missing port number. Every mount then appears with what is playing on it right now, so you can hear what is on before you tune in.
  - **Captions and video keys work from every window** -- Browse Stations, Search, Manage Favorites, Recordings, Song History, the Downloads window and the Video Window itself, not only the main one. **Ctrl+Shift+V** shows or hides the picture (and closes the Video Window from inside it; Escape, Ctrl+W and Ctrl+F4 close it too), **Ctrl+Shift+K** turns captions on, **Ctrl+Shift+T** opens the transcript, **Ctrl+Shift+A** lists the audio and described-audio tracks, **Ctrl+Shift+I** describes the video.
  - **Captions open in their own window**, as text you can arrow through: each line joins the ones already spoken, the line being spoken now is marked with a greater-than sign, and **Follow Playback** (a checkbox) can be turned off so the window holds still while you read back. It never announces itself -- read it whenever you like. It works on either playback engine and with no picture showing, and it is drawn at the size you chose in Caption Settings, up to 300%. Escape closes it, and closing it turns captions off.
  - **The audio-track list leads with the language you read the app in**, then the video's own original track, then the rest alphabetically -- a video with twenty-four dubs is a list you can now find your way down.
  - **Podcast Index** -- the open podcast directory, and the one branch where you can **look at a show without subscribing to it**. Open any show and its episodes are there: play one, add it to Favorites, download it, or read its transcript, exactly as anywhere else in the tree. Three ways in: **Trending Now**, **By Category** (the index's own 112 categories), and **Search the Podcast Index...**, which answers inside the tree. Each show row says who makes it, how many episodes it has and what it is about before you open it -- and says so plainly when the index can no longer read the feed. **Subscribe** on a show row files it in the shared library with QUILL Cast, artwork and all. Nothing needs setting up: Quill Radio carries its own credential for the index. Switch the branch off in Choose Browse Sources and podcasts work exactly as before.
  - **YouTube** -- channels, playlists and single videos, with no Google account and no sign-in anywhere. **Add a Channel...** takes a channel address (`https://www.youtube.com/@name`); Quill Radio reads it once to check it can before saving. Each channel opens into **Uploads** plus any playlists the channel publishes, and a channel with thousands of videos pages with **More...** rather than trying to be one enormous level. **Add a Playlist...** and **Add a Video...** sit beside it: a saved playlist opens as a folder of its videos, a saved video is a playable row, and either offers **Remove from YouTube** on the same menu that plays it. Videos play, record and can be favorited exactly like a station -- and any YouTube row offers **View Transcript...**, which fetches the video's captions and opens the transcript reader without playing anything (an automatic track says so in the heading). The quickest way in is **Station > Add YouTube Link... (Ctrl+Alt+N)**: paste anything YouTube and it is filed by what the link is -- `@name` follows the channel, `@name/live` saves the broadcast, a playlist link becomes a folder, a video link a row. The three **Add a ...** rows appear while the YouTube branch is empty and step aside once it has something in it; from then on they live on the **context menu** (right-click, or Shift+F10) of the branch and of every row inside it. Whichever way you add something, the tree refreshes and the cursor lands on the new row.

    Whichever way you add it, Quill Radio asks YouTube what the link *is* and the row takes the video's own name: "Do schools kill creativity?", with the channel and the length spoken after it, and the video's description in the details panel. The lookup happens in the background and cannot cost you the link -- the row is saved first, so a video whose details will not read is still saved, still plays, and simply keeps its address. A row saved by an older version names itself the first time you play it.

    **Delete** removes the row you are on -- a saved video or playlist, a followed channel, a server you added, a favorite -- after asking a question that names it. The question has a **Don't ask me again** box (unticked, and No is the default button), and the branch reloads so the row is really gone. Delete on one of Quill Radio's own branches explains that there is nothing there to delete and points you at Hide This Source; that explanation has a **Don't show this again** box too.

    The first time anything YouTube is added or played, Quill Radio asks once whether it may contact YouTube at all, and remembers the answer. If a video refuses to play, Quill Radio offers to fetch the current YouTube helper for you -- say yes and it installs it, tells you the version, and plays the video you were trying to play. **Station > Update YouTube Support...** does the same thing at any time: YouTube changes how it serves audio far more often than Quill Radio ships releases, and that item fetches the current helper.
- **Find in this folder** -- above the tree (one Shift+Tab away from the stations) is a search box that searches **from the folder you are highlighted on, downward** -- one iHeart genre, one state, one source -- so you get a short, relevant list instead of searching every directory at once. Highlight the folder, type, press **Enter** (or the **Find** button); matches appear under that folder, and **Clear** puts you back where you searched from. **Ctrl+F** jumps to the box from anywhere in the window. Find takes the fastest route for where you are standing, and says which it took: on the **Podcasts** branch it asks the real podcast search engine, and shows come back as folders you expand straight into episodes -- type "double tap", press Enter, expand, play. On a catalog-served branch (**By Country**, **By Language**, **By Genre**, **By Quality**) it answers instantly from the catalog on this computer, scoped to where you are -- Find "jazz" while on France and you get France's jazz stations, online or off, announced as "From your catalog." On **LibriVox** it searches the whole book catalog (books arrive as folders of chapters); the **Internet Archive** answers with items you can drill into; **TuneIn** with stations already resolved; **iHeart** from its full station index; **NOAA** by call sign, SAME code, or "County, ST"; **Project Gutenberg**, **SomaFM**, **Audius**, **Mixcloud** and **ccMixter** through their own catalogs. Only a branch with no search engine of its own walks the subtree, bounded, and tells you if it showed only the first results -- and a directory that cannot be reached says so instead of posing as "no matches." For a search across *every* directory at once, use **Search Stations...** instead.
- **A branch that is slow says so, and a branch that is broken says *that*.** Opening a source names what it is loading ("Loading Old Time Radio..."), and if it takes more than three seconds it tells you it is still working -- silence and a hang feel identical otherwise. And an empty branch distinguishes the two kinds of empty: "there are no stations in this genre" is an answer, while "that directory could not be reached" means try again later. If a directory is having a bad day (it happens -- LibriVox and the Internet Archive both were on 16 August), Quill Radio says so plainly rather than quietly showing you nothing.
- **The tree reads ahead.** Land on a closed folder and Quill Radio quietly starts fetching what is inside it; open a folder and the first few folders inside it fetch behind you. The expand you were about to make opens instantly. This follows your cursor only -- a source you hid in Choose Browse Sources is still never contacted, and Safe Mode still fetches nothing.
- **Search All Sources...** -- the first row of the tree, always. Press Enter on it and the full Search Stations window opens with focus in the search box: one query, every provider's own search engine, results interleaved and labelled. It is the same window as **Station > Search Stations...**; this row is simply the door from inside the tree. And each searchable top-level source -- Podcasts (Apple), iHeart, TuneIn, YouTube and the rest -- offers **Search This Source...** on its context menu, which opens that same window with the Source filter already narrowed to it: standing on podcasts searches podcasts. A source with no search engine of its own (Weather / NOAA, NFB Radio) honestly offers nothing.
- **Every live station row can be captured from where you found it.** A station's context menu offers **Record This Station...** and **Schedule Recording...**, pre-filled with that row's station rather than whatever is playing -- the same two commands the Record menu carries. A row you have favorited also offers **Rename Favorite...** in place (blank restores the directory's own name).
- **Search Stations...** -- the full station search: search across four directories at once -- **RadioBrowser**, **SomaFM**, **iHeart**, and **TuneIn** -- blended into one results list, test-play, favorite. A search that looks like weather-radio geography -- a 6-digit **SAME code**, a **call sign** like `KHB36`, or a **"County, ST"** or state name -- also brings back exact NOAA Weather Radio transmitters from the authoritative directory, and reading services match by name, tag, or state right alongside. Every result is labeled with the directory it came from ("via iHeart", "via TuneIn"). RadioBrowser shows up to 200 stations at once, most-listened first; when there are still more, a **More Stations** button loads the next page and puts your cursor on the first newly added station. iHeart and TuneIn add a small set of their most relevant, immediately-playable matches to each search (each iHeart/TuneIn result's real stream is looked up on demand, so they are capped per search to keep one search from becoming dozens of network requests). And since 3.0 the search starts at home: matches from the **station catalog on your own computer** appear the instant you press Enter -- ordinary rows, labeled with the directory they came from -- with the live directories layering in behind them, so a search answers immediately, and still answers when the internet does not. Library results play too: press Enter on a podcast show and Quill Radio fetches its feed and plays the **latest episode**; a LibriVox book plays its **first section**; each is announced by name, and an Internet Archive collection says plainly that it opens on its own site.
  - **The libraries are searched too.** Beside the radio directories, a search also asks **LibriVox**, the **Internet Archive**, **Project Gutenberg** and **Apple Podcasts**, so a book or a recording turns up when you type its title rather than only when you go looking for it in Browse Stations. Those rows are labelled with where they came from, exactly like the station rows, and the **Source** dropdown below narrows to one of them. They arrive a moment after the stations, because each library is asked separately so a slow one cannot hold up the rest, and Quill Radio tells you once when they have all answered. If you are already arrowing the results when one arrives, your place is kept.

    The **music libraries answer too** -- **Audius**, **Mixcloud** and **ccMixter** -- so a track or a DJ set turns up by name and not only by wandering into the right shelf. They keep the same manners they have in Browse Stations: an Audius track and a ccMixter upload play here (a ccMixter row shows its Creative Commons licence), while a Mixcloud row is the show's page and opens in your browser, which the row tells you before you press Enter. If a library ever genuinely cannot be searched, Quill Radio names it rather than leaving you to wonder why nothing came back from it.
  - **Source** -- a dropdown to narrow the search to one directory (All sources, Radio Browser, iHeart, TuneIn, Podcasts, SomaFM, ACB Media, Community M3U, Xiph, Spotify, YouTube, or Website) when you already know where a station lives. **Podcasts** gathers every podcast result whichever exact directory stamped it, and it is the filter **Search This Source...** on the Podcasts branch opens on. When the same station is carried by more than one directory (a SomaFM channel RadioBrowser also lists, say), it appears under each of those directories' filters, not just the one whose copy you happened to play.
  - **Tag/genre** and **Country** -- these are now proper dropdown lists, filled in from the directory itself, so you pick "jazz" or "United Kingdom" from a list instead of typing the exact spelling; choosing one runs the search right away.
  - **Refresh** -- re-fetches the iHeart station directory. iHeart's directory index is cached once per Browse Stations session (TuneIn and RadioBrowser are always live), so use Refresh if you want the very latest iHeart listing.
  - The status line tells you when more can be loaded and suggests adding a tag or country to narrow a very broad search. Search is disabled in Safe Mode.
- **Update Radio Reading Services...** -- refresh the Radio Reading Services list on demand from the community RadioBrowser directory, off the UI thread, announcing how many services it found. The bundled list stays as the fallback, and the command is off in Safe Mode.
- **Add Custom Station...** -- paste any stream URL and name it yourself. Three kinds of link get extra help here:
  - **A YouTube link becomes a station.** Paste an ordinary video link, a `youtu.be` short link, or a channel's live page (`youtube.com/@handle/live`) and Quill Radio treats it exactly like a radio station: it plays through the same player, sits in your favorites, records with **Record Now**, and can be captured by a **scheduled recording**. What gets saved is the *page* address, never a stream address -- YouTube's stream addresses expire after a few hours, so Quill Radio looks the audio up fresh every time the station plays or records. That is what lets a recording you schedule today still work next week. The small helper that does the looking-up, `yt-dlp`, is **built into the app**, so your first YouTube link simply plays -- there is no download to approve and nothing to set up. If YouTube changes how it serves audio (which happens from time to time) and links stop resolving, **Station > Update YouTube Support...** downloads the current version of that helper and uses it in place of the built-in copy from then on, so you do not have to wait for the next release of Quill Radio. It tells you which version you ended up with, is off in Safe Mode, and asks before it reaches the network. You should not need it otherwise. Because looking the audio up takes a moment, it happens in the background: you hear "Connecting" straight away and the window never freezes. A video that is private, removed, blocked in your region, or not live yet says so in plain words. YouTube stations are unavailable in Safe Mode.
  - **A YouTube playlist becomes a list you can browse.** Choose **Station > Add from YouTube Playlist...** and paste a playlist link (`youtube.com/playlist?list=...`). If the link is already on your clipboard, the box is filled in for you. Quill Radio lists the videos in it -- in the order the uploader put them, never re-sorted, because a series is meant to be worked through in order -- and each row reads as a whole sentence: its position, its title, how long it runs, and who published it, for example "3. Introducing layers, 5 minutes 31 seconds, 3Blue1Brown". Arrow the list and select what you want (hold Shift or Ctrl to pick several), then choose **Add Selected**, or take the lot with **Add All**. Each one becomes an ordinary station you can play, favorite, and record. Quill Radio tells you how many it added and how many were already in your favorites, so "Add All" on a fifty-video playlist never leaves you guessing whether anything happened. The listing itself is deliberately shallow: Quill Radio asks once for the whole playlist rather than once per video, and does not fetch any video's audio until you actually play it. One thing worth knowing: a *watch* link that happens to carry a `list=` in it -- which is what you get when you copy a link while a playlist is open -- is still treated as that single video. You asked for the video, and turning it into fifty stations without being asked would be a surprise, so only a genuine playlist address expands. The window is headed with the playlist's own name -- Quill Radio reads it from the same single request that fetched the list -- so you always know which playlist you are looking at. Playlists use the same built-in `yt-dlp` helper as any other YouTube link, and are unavailable in Safe Mode.

  - **One command for any YouTube link.** **Station > Add YouTube Link...** (**Ctrl+Alt+N**) takes whatever you pasted and files it under Browse Stations > YouTube by what the link is: a video becomes a playable row, a playlist a folder of its videos, a channel page a followed channel. `@name` follows the channel; `@name/live` saves the broadcast. If the link on your clipboard is a YouTube one, the box starts filled in.
  - **Import the channels you already follow -- with no account, no sign-in, and nothing sent anywhere.** **Station > Import YouTube Subscriptions...** (**Ctrl+Alt+Shift+Y**) reads the subscriptions file you export from Google and adds every channel in it to **YouTube Channels**, so following forty channels costs one file instead of forty pasted addresses. To get the file: go to `takeout.google.com`, choose **YouTube and YouTube Music**, narrow it to **subscriptions**, and download the archive; inside it the file is `YouTube and YouTube Music\subscriptions\subscriptions.csv`. Quill Radio then tells you what happened -- "Imported 24 channels; 3 you already followed" -- and the channels appear under YouTube Channels in Browse Stations, exactly as if you had added them by hand.

    **Why it is a file and not a "Sign in with Google" button.** Signing in would mean attaching your real Google account to an app that also extracts audio from YouTube pages, which is not something YouTube endorses -- so the account, not just the feature, would be the thing at risk. It would also make you create your own Google Cloud project first, which is seven steps of developer console before you hear a single channel. Reading a file you exported yourself has none of that: nothing authenticates, no password or token is stored, no request is made to Google at all, and it works offline and in Safe Mode. It is your data, exported by Google's own tool, handed to a program you chose.

    **What it does and does not do.** It is a one-time import: nothing keeps syncing afterwards and nothing runs in the background, so channels you subscribe to later on YouTube will not appear until you export again and re-import (channels already followed are skipped rather than duplicated). It imports *channels*, not history -- see below. Rows that are not channels, and any single row Google's export mangles, are skipped rather than failing the whole import.

    **On YouTube Premium and watch history, plainly.** Quill Radio cannot sign you in to YouTube Premium, and Premium's benefits do not carry into it: ad-free playback, background play and offline downloads belong to YouTube's own apps, and YouTube's developer terms specifically forbid a third-party app from separating audio from video, playing in a background player, or storing content for offline use. There is no Premium exception to ask for. Watch history cannot be synchronised either -- not by Quill Radio and not by any third-party app: YouTube removed watch history and Watch Later from outside reach years ago, and its own documentation answers such a request with "Watch history data cannot be retrieved through the API". Your subscriptions are the part that *can* be brought across, which is what this command does.

    **What adding a playlist does and does not do.** It is an *import*, not a subscription and not a play queue. The videos you choose become ordinary favorites -- each one plays, records, and can be scheduled exactly like a station -- and they land in your favorites list alongside everything else, not in a folder of their own. Nothing plays through the list in order: playing one video plays that video, and Quill Radio does not move on to the next when it ends. Nothing re-checks the playlist later either, so videos the uploader adds after you import are not picked up; run **Add from YouTube Playlist...** on the same link again to collect them (anything already in your favorites is skipped rather than duplicated). Group the imported videos yourself with **New Folder** (Ctrl+Shift+E) and the Favorites Manager if you want them kept together.
  - **What Quill Radio knows about a YouTube video.** Looking up a video's audio is one request, and that request answers with more than an audio address, so Quill Radio keeps all of it: how long the video is, who published it, its description, any chapters the uploader marked, and whether captions exist. None of it costs an extra moment or an extra connection. That is what makes the chapter, seeking, and speed controls on the Playback menu possible. A live broadcast reports no length, which is the honest answer for something with no ending yet.
  - **A Live365 link is fixed for you.** The Live365 link most people have is the station page (`live365.com/station/...`) or the web player (`player.live365.com/a25891`) -- both are web pages, and pasting one used to save a station that could never play, with nothing to explain why. Quill Radio now recognizes a Live365 station page, player link, or even a bare station id and rewrites it to that station's real stream address, telling you in the dialog that it did. Nothing is fetched or sent anywhere -- it is purely a matter of rewriting the text -- and a link that is not Live365 is used exactly as you typed it.
  - **Any other stream URL** is saved as you typed it, as always. A SecureNet player link (`securenetsystems.net/v5/...`) is saved as typed too, because unlike the two above its real stream address cannot be worked out from the link alone -- it has to be read from the page. Two things get you there: use **Find Streams from a Website...** below with the player link, or just save it and press Play, and the self-healing repair will find the stream for you on the first attempt.
- **When a station won't play, Quill Radio tries to fix it for you.** Some stations are listed in the directory but their stream address is dead -- often because the real stream is behind a player on the station's website. Instead of just failing, Quill Radio works down a short ladder: it re-resolves the address (for StreamTheWorld-style players that moved servers), refreshes the address from the directory, and -- if the setting is on -- scans the station's own website, following a "Listen Live"/"Play"/"Tune In" link into the player and recognizing Triton players there. If it finds one clear stream it plays it and remembers it for that favorite; if it finds several it tells you the count and you can open Find Streams to choose. The website step is the "Recover failed streams from the station's website" checkbox in Station > Preferences (Ctrl+,), on by default and off in Safe Mode. It only tries once per station per session.
- **Find Streams from a Website...** -- give it a website address; it scans that one page for stream links, with a Test button that toggles to Stop Test while a candidate plays. This now also works for many stations whose "Listen Live" button is a modern JavaScript player (Triton Digital / StreamTheWorld, including the whole `player.listenlive.co` network -- for example `player.listenlive.co/34461`). Those players build their stream address in code, so it is not written anywhere in the page for a scanner to read; Quill Radio recognizes the player, reads the station's call letters from the page, and looks the real stream up through the station provider's own public address service -- no browser, no guessing. Both the MP3 and the AAC stream are offered when a station publishes both. It also recognizes an **iHeart** or **TuneIn** station page pasted directly and resolves its real playable stream through that directory, instead of handing back a page address that will not play. It also handles **SecureNet's player** (`securenetsystems.net/v5/...`), used by a large number of American broadcasters, which failed for the opposite reason: that page *does* write its stream address out in plain text, but the address looks like nothing special -- `https://ice66.securenetsystems.net/ROM`, with no `.mp3` on the end and no `/stream` in the path -- so the scan used to file it with the page's ordinary links and throw it away, returning junk or nothing at all. Quill Radio now recognizes the player itself and offers the real stream first, whether you point it at the player page or at a station's own site with the player embedded. If a page is not one of these players or directories, or does not name its station, the scan simply behaves as before.
- **Manage Favorites...** -- the favorites, made organizable. See "The Favorites Manager" below.
- **New Folder...** (Ctrl+Shift+E) -- create a folder right where you want it: pick the location (top level or inside any existing folder), then name it. The folder exists immediately, ready for Move to Folder.
- **Import Stations from Playlist...** -- import an **M3U**, **M3U8**, **PLS**, **XSPF** or **ASX** playlist. The "Listen Live" link you actually have is at least as likely to be a `.pls` (the standard SHOUTcast and Icecast listen link) or an `.xspf` (what the Xiph directory itself serves) as an M3U, and several radio reading services still publish `.asx`. ASX in the wild is frequently not valid XML at all, so it is read twice -- once properly, and once forgivingly when the file will not parse. An `.m3u8` that turns out to be a *live stream's* manifest rather than a list of stations is recognised as one and refused, instead of importing a live stream as a list of two-second "stations"; what is inside the file decides, not what the file is called. XSPF and ASX are XML from strangers, so they are read with entity expansion switched off -- a small crafted file designed to expand to gigabytes is refused out loud rather than opened. Choose the file, then pick where the stations go: an existing folder, or type a brand-new folder path at any depth (like `News/Local`, created for you). If any of the playlist's stations are already in your favorites, Quill Radio tells you how many and asks whether to skip those duplicates or import everything. Station names come from the playlist's own `#EXTINF` lines; a bare URL is named after its host.
- **Export Favorites to Playlist...** -- the other direction: write your stations out to a playlist file in **M3U**, **PLS**, **XSPF** or **ASX**, whichever the player you are handing it to prefers. Each format reads back into Quill Radio, so exporting, re-ordering elsewhere and importing again is a complete round trip -- a station name containing an ampersand survives it, which is not true of most playlist writers. Use it to hand your stations to any other media player, share your list with someone, or keep a plain-text copy you can read outside Quill Radio. Each station is written with the name you see (your custom name if you gave it one) and its stream address, so importing the file back brings the same stations in. M3U is a flat format with no notion of folders, so folder structure is not carried across -- exactly as importing one discards it.
- **Back Up Stations and Settings...** and **Restore from Backup...** -- save your favorites, settings, wake timer, and recording schedule (and, if you choose, your recorded audio) into one portable `.qrbackup` file, then bring it all back on a new device or after a reinstall. Back Up asks whether to include recordings (they can be large); Restore previews the backup and confirms before it replaces your current stations, and reloads the app so it takes effect right away.
- **Play Last Station** (Ctrl+L) -- resume whatever you last had on, one keystroke, no navigation.
- **Recently Played** (submenu) -- your last fifteen stations, newest first, playable inline.
- **Favorite Stations** (submenu) -- every favorite, nested by your folders, playable inline.
- **ACB Media** (submenu) -- ACB's whole stream directory, playable inline.
- **Resume Last Station on Launch** (check item) -- the appliance switch.
- **Start Quill Radio with Windows** (check item) -- have Quill Radio open by itself when you sign in. It adds (or removes) an entry just for your own account, so it needs no administrator rights and touches nothing for anyone else who uses the computer. Pair it with **Resume Last Station on Launch** and the radio is simply on when you sit down. (Windows only.)
- **Choose Browse Sources...** -- decide which branches Browse Stations shows. Twenty-eight sources is a good problem and still a problem: if you only ever open your local stations and ACB Media, every branch you never use is distance to arrow past. Each row in this window says its own state out loud -- "On. LibriVox Audiobooks. Public-domain audiobooks, by chapter." -- and one button turns the focused branch on or off, with Turn On All and Reset to Default beside it. The same rule as Search Sources applies: **a branch that is off is not in the tree at all, and is never contacted**, so this is a speed and privacy control as much as a tidiness one. Your choice is remembered, and a source added in a future version appears automatically unless you have hidden it. You can also prune without opening this window at all: right-click any top-level branch in Browse Stations and choose **Hide This Source** -- the same setting, applied in place -- with **Reset Sources to Default** on the same menu, so the way back is never a dialog away.
- **Update Station Catalog** -- Quill Radio keeps a copy of the station directories on this computer, so browsing answers instantly and works offline. It updates itself quietly (shortly after launch, and on a schedule you set in Preferences -- every 24 hours unless you change it), and this command updates it right now, then tells you exactly what happened: "Station catalog updated: 174 new stations, 431 updated." A directory that cannot be reached costs you its freshness, never your stations.
- **Download Preferences...** -- the standing rules for everything you save: which folder downloads go to (blank uses a Quill Radio folder inside your own Downloads), whether each podcast show and each book gets a folder of its own, whether books group under their author once an author has more than one, whether closing the window to the tray keeps the queue going, and whether Quill Radio should ask where to put each download instead of filing it automatically (asked once per book -- never once per chapter). A live sentence at the bottom of the window always answers "what will happen to the next thing I save?", and the same window is one button away inside View > Downloads.
- **Preferences...** (Ctrl+,) -- Resume Last Station on Launch, automatic Check for Updates, Announce dialog transitions (off by default -- turn on for more spoken detail around every dialog), When closing the window (Ask every time / Exit / Minimize to Tray -- governs the titlebar X, Station > Exit, and by default Alt+F4 too), **Alt+F4 minimizes to the system tray** (off by default: turn it on and Alt+F4 alone tucks the radio into the tray, still playing, while X and Exit keep the setting above -- the reflexive close stops meaning quit), **Playback engine** (Automatic -- recommended -- uses the bundled mpv engine, which powers the output device choice, pausing and rewinding live radio, Volume Boost, and stations in more formats; "Windows Media (classic)" is exactly the pre-1.1 behavior if you ever want it back), and **Radio output device** (route just the radio to a second sound card or USB headset -- your screen reader and Quill Radio's own sounds stay on the system default device; an unplugged device is remembered, not reset, and if it can't be used the radio plays through the default and says so). Every setting takes effect the moment you save -- switching engine or device mid-song reconnects the station right where it matters: on the new engine or device. Preferences also carries **Favorites sort order** (Ascending A to Z, Descending Z to A, or Unsorted -- how your folders and stations are ordered in the list; Ascending/Descending re-sort when you add a station, while Unsorted keeps your hand-arranged Move Up/Down order, which is never lost) and two troubleshooting settings: **Verbose logging** (a debug-mode checkbox that turns on detailed logging live, no restart, for when you need to diagnose something or attach detail to a bug report) and **Log folder** (choose where the log is written so it's easy to find; a failed recording captures the recorder's own error output into it as well). Finally, **Keep the computer awake while playing or recording** (on by default) stops Windows from going to sleep while a station is playing or a recording is running, so the audio never cuts off mid-listen; your screen can still turn off, and the moment nothing is playing or recording the setting lets the computer sleep normally again. Turn it off if you would rather Quill Radio never touch your power settings. (Windows only.) The three **Station catalog** settings live here too: keep the local catalog at all (off restores live-only browsing with nothing stored), check for catalog updates at launch, and the update frequency -- every 24 hours unless you choose 6 hours to 2 days, or Manually only. And **Winamp-style playback keys in the Recordings player** (on by default) governs the classic-skin letter keys -- X play, C pause, V stop, B next, Z previous, arrows to seek, T for elapsed or remaining, J to jump -- in the Recordings window; turn it off to type letters there for list typeahead instead. Ctrl+Up and Ctrl+Down still change the volume either way. **Episodes listed per subscribed podcast** (25 newest by default) governs how many episodes each show under Podcasts > Subscriptions lists -- deliberately Quill Radio's one podcast setting, with the full archive living in Quill Cast. And the **Data Folder...** button opens the family-wide data location: where every Quill app stores its settings, favorites, subscriptions, and playback positions. Point it at a folder that Dropbox, OneDrive, Google Drive, or iCloud already keeps in sync and your whole Quill setup travels between computers -- no account, no sign-in; the sync client does the moving. The change applies the next time an app starts (a restart is offered), your existing data is moved for you, and the machine-heavy caches (like the Station Catalog) deliberately stay on each computer rather than churning through the sync service. One rule to respect: do not run Quill apps on two computers against the same folder at the same time -- if you do, the next launch says so ("this data folder was in use on LAPTOP-X...") rather than letting two machines silently fight over one profile.
- **Send to Tray** (Ctrl+W) -- hide the window; playback continues from the notification area.
- **Exit** -- quit Quill Radio. Closing the window -- titlebar X, Alt+F4, or this item -- simply exits, even while a station is playing: a live stream is not work you can lose, so it never stands between you and the door. The only thing that asks first is a **recording in progress** (Exit, Minimize to Tray, or Cancel, with a "Don't ask me again" checkbox), because exiting stops the capture. A fixed answer set in Preferences ("When closing the window") is honored instead of asking. And if "Alt+F4 minimizes to the system tray" is on in Preferences, Alt+F4 tucks the radio into the tray, still playing.

### Playback (Alt+P)

- A live (disabled) now-playing line at the top, so the menu itself tells you what is on.
- **Play / Stop** (Ctrl+P) -- one transport item that reads Play when idle and Stop while connecting or playing, exactly like the panel button.
- **Mute/Unmute** (Ctrl+M), **Volume Up** (Ctrl+Up), **Volume Down** (Ctrl+Down). Ctrl+Up and Ctrl+Down work from **anywhere in the window** -- the favorites tree, a button, the status bar -- with one sensible exception: inside a text box, Ctrl+arrow still moves and edits text, as it should. Two things are remembered. Each **favorite** remembers the volume you set while it plays and gets it back the next time it starts, because stations are mastered wildly differently and you should only have to fix that once per station. And the **last level you set** is remembered across sessions for everything else, so a station that is not a favorite comes back where you left it rather than at full volume the next time you launch. (A favorite's own remembered level always wins over the general one.)
- **Output Device...** (Ctrl+Shift+D) -- pick which sound card or headset the radio plays through, in one keystroke, without opening Preferences. Choose a device and the station moves to it immediately; the choice is remembered, and it is the same setting as **Radio output device** in Preferences, so the two always agree. Your screen reader and Quill Radio's own announcements stay on the system default device. Needs the mpv playback engine (the default).
- **Volume Boost** (Ctrl+Shift+B, check item) -- amplifies up to 50% past full volume for stations that just broadcast quiet. Your 0-100 volume scale, per-station volume memories, and mute all behave exactly as before; the boost is applied on top. Needs the mpv playback engine (the default -- see Preferences below).
- **Rewind 30 Seconds** (Ctrl+Shift+Left), **Forward 30 Seconds** (Ctrl+Shift+Right), **Back to Live** (Ctrl+Shift+L) -- live radio you can move around in. On the mpv playback engine (the default), Quill Radio keeps a rolling buffer of the stream (roughly 45 minutes at typical bitrates): jump back to catch a missed sentence, work your way forward, then leap straight back to live. Every move announces how far behind live you are. Needs the mpv playback engine.
  - **A note on pausing.** Whether Play/Stop *holds your place* or *rejoins live* depends on the engine. On the **mpv** engine, pausing keeps your position in the rolling buffer, so Play resumes exactly where you stopped. On the **Windows Media (classic)** engine there is no buffer, so pausing a live stream and pressing Play again reconnects at the current live moment -- it looks like the stream simply refreshed. If you press Play/Stop expecting to resume where you left off and instead hear live audio, open **Station > Preferences (Ctrl+,)** and set **Playback engine** to **Automatic** (which uses mpv); the buffer, Rewind/Forward, and Back to Live all require that engine. (A live stream also only rewinds as far back as the buffer has actually filled since you started listening.)
- **Chapters...** (Ctrl+Shift+C), **Next Chapter** (Ctrl+Shift+.), **Previous Chapter** (Ctrl+Shift+,) -- a finished YouTube video has a timeline, so you can move around it the way a live broadcast never lets you. Chapters opens the uploader's own chapter list, each entry read as a whole sentence ("3. Introducing layers, starts at 5 minutes 31 seconds") with the one playing now marked; Enter jumps to it. Previous Chapter restarts the current chapter first, then steps back, the way a CD player does. **Rewind / Forward 30 Seconds** (Ctrl+Shift+Left / Ctrl+Shift+Right) move along the video's own timeline -- the same keys move within live radio's rolling buffer when a live stream is playing, and Quill Radio picks the right one for what you are listening to. On a video they say where you landed ("3 minutes 10 seconds of 18 minutes 40 seconds"); on a live stream they say how far behind live you are. **Go to Position...** (Ctrl+Alt+J) jumps straight to an exact time, using the same accessible Hours / Minutes / Seconds dialog the Quill Media Player uses -- three labelled spin controls, plus a timecode field if you would rather type `1:23:45`. **Where Am I?** (Ctrl+Shift+W) speaks your position, the length, and the chapter you are in.
- **Play Faster** (Ctrl+Shift+Up), **Play Slower** (Ctrl+Shift+Down), **Normal Speed** (Ctrl+Shift+0) -- speed for a finished video, stepping through round, speakable values from 0.25x to 4x rather than drifting by a multiplier. The speed you choose is remembered for the next video. Live radio plays at normal speed; setting a speed while a station is on says so, and remembers it for when a video plays. And while a **podcast episode** plays, the speed you choose is remembered **for that show**: the announcement adds *"Remembered for this show,"* the show's episodes start at your speed from then on (outranking any speed set in Quill Cast, without changing it there), and Normal Speed forgets the memory out loud. A remembered speed applies automatically to downloaded episodes always, and to streamed ones when the mpv engine is playing; on the Windows Media Player fallback it stays saved rather than risking a stuttering stream -- Play Faster is still one keypress away.
  - **All of these say why when they decline.** Ask for chapters, seeking, or speed while a live stream is playing and you hear "This is a live stream, so there is no timeline to move along"; ask for chapters on a video whose uploader published none and it says that instead. A control that quietly does nothing is worse than one that is not offered, because you cannot tell it apart from a broken app.
- **What's Playing?** (Ctrl+T) -- opens a reviewable Now Playing window: the current title and artist in a read-only, selectable field you can arrow through **character by character** to catch an exact spelling, with a **Copy** button. It reads the title straight from the stream's own metadata (and if no title has arrived yet, Ctrl+T speaks and fetches it, as before). When a station sends messy broadcast metadata (a string of catalog codes rather than a clean "Artist - Title"), Quill Radio finds the title and artist in it and reads just those. And when a station answers with nothing at all -- no metadata, and the playback engine's own title channel is empty too (common on HLS) -- Quill Radio takes one more step: it reads the current title from the stream server's own public "now playing" status page (the Icecast or SHOUTcast status endpoint). It only ever asks the same server you are already listening to, and it is off in Safe Mode -- so a batch of stations that used to answer with silence now report a real title. You control the wording in Station > Preferences (Ctrl+,) with a small template: `{title}` and `{artist}` tokens, `[square brackets]` around optional wording that disappears when a field is empty (the default `{title}[ by {artist}]` drops the " by" when there's no artist), and `{raw}` for the stream's exact original text. Leave it blank to restore the default.
- **Where the track information came from.** Quill Radio looks for a title in three places -- the metadata carried along with the audio, the playback engine's own reading of the stream, and the station's status page -- and the full details window (Enter on the status bar's Now playing cell) now names which one answered. They are not the same kind of fact: a status page is a snapshot the station publishes for its own listing, and it can be a song behind what you are hearing. Where the title you are shown was *read out of* something messier -- advert markers, catalog codes, the station's own call sign -- the window shows what the station actually sent alongside it, and says plainly that the tidy version is a reading of it. That reading is usually right and is not always right, so you can see both.
- **Copy What's Playing** (Command Palette) -- copies the current title and artist straight to the clipboard without opening the Now Playing window (which Ctrl+T opens, above). You no longer have to press What's Playing first: if a station is on and no title has arrived yet, Quill Radio says "Checking what's playing...", fetches it, and then copies it. Both this and the Ctrl+T window always tell you *something* -- a stream that sends no titles at all says so and still opens a window naming the station, and a lookup that fails is reported rather than passing in silence. The confirmation names what it copied, so you know it worked without pasting to check.
- **Use One Volume for All Stations** (check item) -- Quill Radio normally remembers a volume for each favorite, which is lovely when stations are mastered at wildly different levels and maddening when you simply want everything quieter: with twenty favorites, there were twenty places to turn the volume down. Tick this and a single level answers for every station, so Ctrl+Up and Ctrl+Down turn *everything* up or down. Ticking it adopts whatever you are hearing at that moment, so nothing jumps. Your per-station levels are not thrown away -- untick it and every station goes straight back to its own remembered volume. Off unless you turn it on.
- **Forget Every Station's Own Volume...** -- the deliberate way to be rid of those per-station levels rather than merely bypassing them: it tells you how many stations have one, asks first, and leaves your stations, folders, and every other setting untouched.
- **Song History...** (Ctrl+Shift+H) -- what each station played earlier. What's Playing tells you the song on right now and then forgets it; this is the memory behind it. Choose a station at the top, then arrow the list: each entry reads as a whole sentence, such as "Your Song by Elton John, heard 10:04, played twice", newest first. From a selected song, **Copy** puts it on the clipboard, **Send to Clip Library** keeps it with your other saved snippets, **Song Details** tells you more than the station did -- which release the song came from, what year it is, and how long it runs, from MusicBrainz; it is a button rather than something that happens automatically, because looking up every song you ever heard would use your connection for something you never asked for, and if nothing more is known it says so plainly. And **Background** asks whichever AI provider you have set up for a short note about the song and artist. That answer always begins by saying it was written by an AI model rather than by the station -- it sits inches from the station's own information, and the two must never be confused -- and it is never available in Safe Mode; with no provider set up, the window simply says so. **Clear...** empties one station's list or every station's. The log keeps up to 200 songs per station, one station's listening never pushes out another's, and it never leaves your machine. A song still playing when Quill Radio checks again folds into the entry already there with a play count, rather than filling the list with the same title six times, and stations that broadcast their own name, "Live", or an advert marker instead of a track are left out. To stop keeping the list at all, turn off **Keep a song history for each station** in Preferences; entries already saved stay until you clear them.
- **Announce Track Titles** (check item) -- when on, title changes are announced as they happen. Off by default. On the Command Palette this entry names its own state, so it reads **Announce Track Titles (currently On)** or **(currently Off)** -- the palette has no checkmark, and you should not have to throw a switch to find out which way it is set.
- **Sleep Timer...** -- fade out and stop after a set time, restoring your volume.
- **Wake-Up Timer...** -- the sleep timer's twin: pick a favorite, a time, once or every day, and the station starts playing by itself. Quill Radio must be running (the tray counts).
- **Sound Enhancements...** -- a three-band equalizer (Bass, Mid, Treble sliders, -12 to +12 dB each, freely adjustable), a compressor ("Even Out Volume", boosts quiet passages and tames loud ones), a **Channel mode** choice (Stereo, Mono, Left only, Right only) and **Night mode**. Channel mode routes the audio for accessibility: **Mono** blends both stereo channels into one, so a station that hard-pans a voice to one side never disappears with single-sided hearing or a single earbud; **Left only** or **Right only** sends the whole stereo mix (nothing is lost) to just that one ear and silences the other, so you can listen to the radio in one ear while your screen reader (or anything else) uses the other. **Night mode** evens loudness in real time by lifting quiet passages -- the complement to Even Out Volume taming loud ones; ideal for low-volume late-night listening. A "Quick preset" combo box (Flat, Bass Boost, Voice Clarity, Podcast, Small Speakers, Late Night) sets all three sliders at once as a starting point -- move any slider afterward and it becomes Custom. Off by default. The dialog also has a **Broadcast polish (OptiLab)** section: an **Apply broadcast polish** checkbox (a bypass that keeps your chosen mode while turned off), a **Polish mode** choice -- **Podcast Leveler** for speech, **Stream Polish** for music, or **Smooth Limiter** for clean peak control -- an **Input** trim in decibels (0, no change, by default), and an **Auto-Adapt** slider (0-100%). Broadcast polish levels quiet and loud passages, adds density, and limits peaks, so a run of stations at very different loudness sits at a steadier, fuller level -- especially handy for talk streams and unattended recordings. In **Stream Polish**, Auto-Adapt is staged rather than a single "more of everything" control (following OptiLab Core 1.4.0): each part of the chain fades in over its own portion of the slider, the leveler eases off as you raise it while a slow loudness lift takes over, that lift ignores silence and low-level noise so it cannot build gain on nothing, and high frequencies come under firmer control toward the top instead of being boosted. The practical effect is that high settings sound louder and steadier rather than more processed, with no point where something audibly switches on. **Podcast Leveler** and **Smooth Limiter** respond to Auto-Adapt more simply, leaning their leveling and density more assertive as you raise it. It is adapted, with thanks and credit, from **OptiLab Core by Lanes Audio / dgl1984** (https://github.com/dgl1984/optilab, Apache-2.0 with the Commons Clause) -- a faithful adaptation of that plugin's three modes as ffmpeg filter chains, rather than the plugin itself. **Exact OptiLab processing** (a choice in the same section) runs the real engine instead. **Off** is the default and keeps the built-in version everywhere. **When saving** uses the real engine for recordings and converted files, which is the recommended setting: a saved file is processed once, after it finishes, so it costs you nothing while you listen, and the original is only replaced once a good processed copy exists. **When saving and while listening** uses it for the stream you are hearing too -- and that one has a real cost, because the engine is a separate program the audio has to travel through: the station takes a moment longer to start, and every change you make in this dialog needs a brief reconnect before you hear it, instead of applying instantly. The equalizer, Even Out Volume, channel mode and night mode all keep working the same way whichever you choose; only the broadcast polish changes hands. If your copy of Quill Radio does not include the OptiLab component, the choice is disabled and says so.

  **Exact processing for recordings.** The adaptation has one honest limit: OptiLab eases its lift and pulls back bass help *while* the final limiter is working hard, and the filter chain Quill Radio uses for live listening cannot do that -- no stage in it can see how hard a later stage is working. So for **saved recordings** Quill Radio can run the real OptiLab engine instead, when the optional OptiLab component is included in your build. Live listening always uses the built-in chain: that is what lets you hear every adjustment the moment you make it, with no reconnect. If the component is absent the option says so and nothing else changes.

**Every control previews live.** As you move a slider or change any setting -- EQ, compressor, channel mode, night mode, or broadcast polish -- you hear it on what's playing right away, without pressing OK (on the default mpv engine it applies with no interruption; on the Windows Media engine it reconnects once the change settles). **OK** keeps and saves the settings; **Cancel** (or Escape) puts everything back the way it was when you opened the dialog.

**Every setting is remembered per station as well as shared.** The whole dialog -- EQ, compressor, channel mode, night mode, and broadcast polish -- is saved per station when you open it while a favorite is playing (so one station can be routed to one ear, or given its own broadcast polish, and remembered); with nothing playing, or a non-favorite on, you are setting the shared default every other station follows. The per-station Reset to Default button and Preferences' Reset All Stations' Sound Enhancements both drop a station back to that shared default.

- **Show Video** (Ctrl+Shift+V) -- see the picture. Quill Radio has always played YouTube links as audio; this shows them as well, in a window of their own. The important part is what it does *not* do: the picture attaches to the stream that is already playing, so showing it never restarts anything and never loses your place, and hiding it again does not interrupt the sound for an instant. If you never press it, nothing about the app changes.
  The window has the picture and a status line, and no buttons at all -- every command is on this menu, in the Command Palette, and on a key you can change, because a strip of unlabelled picture buttons is exactly what makes other players unusable. The picture itself has a proper name and description for your screen reader, so landing on it tells you which video you are on and where the controls are, and Tab always takes you back out of it.
  **F11** is full screen, and it tells you both ways out. **Video Size** gives you Fit, 50%, 100% and 200% from the keyboard. **Take a Snapshot** saves the current frame as a picture file -- useful for a slide you want to read with OCR or send to somebody. **Video Information** (Ctrl+Shift+I) tells you the size, the frame rate, and whether captions and described audio exist.
  If a video is unpleasant to look at, the picture can be dimmed, and Ctrl+Shift+V removes it from wherever you are in the app. Nothing can tell whether a video contains flashing before it plays, so Quill Radio does not pretend to -- it just makes getting away from it immediate.
- **Captions** (Ctrl+Shift+K) and **Caption Settings...** -- turn captions on and off, and set how they look: size up to 300%, text and background colour, how solid the background is, and whether they sit at the top or the bottom. The default is solid white on solid black, which looks heavier than most players and is deliberate: caption text sits over whatever the video happens to be showing, and no colour can be guaranteed to be readable against that. If a video's captions were generated by machine rather than written by a person, Quill Radio says so when you turn them on.
- **Audio and Described Audio...** (Ctrl+Shift+A) -- **the one worth knowing about.** A *described* audio track is a second narration mixed into a programme that says what a sighted viewer can see: who came into the room, what the caption on screen says, where the scene moved. Broadcasters have published them for years, and almost no desktop player lets you find one -- the better ones offer "Track 1, Track 2, Track 3" and leave you to play each and listen. Quill Radio names them. This window lists every audio track the video publishes, with the described one **first**, your cursor already on it, and a line above the list saying *"Described audio is available for this video."* Press Enter or **Play This Track** to switch. Your place is kept when you do, so turning description on an hour into something does not send you back to the beginning. If a video has no described track the window still opens and tells you what it does have -- "This video has one audio track, English. No described audio was published." -- because a greyed-out command would leave you guessing whether the video or the app was at fault.
  **You do not have to remember it is there.** When you play a video that has a described track, Quill Radio says so once, and tells you the key: "Described audio is available for this video. Press Ctrl+Alt+D..." Once per video, and never again for that one.
- **Play Described Audio** (Ctrl+Alt+D) -- the same thing without the list. One keystroke straight to the described track, for when you always want it. If there is none, it says so and names what the video does have.
- **Transcript...** (Ctrl+Shift+T) -- read what a video says. Every YouTube link Quill Radio plays already downloads the video's caption track, and until now it was thrown away. This opens it in a proper reader: an ordinary read-only text box, so arrow keys, selection and your screen reader's review cursor work exactly as they do anywhere else. **Follow the audio** moves the cursor to the line being spoken -- it is off until you turn it on, because while you are reading, playback must not move your cursor out from under you. **Enter on any line** plays from the moment that line was spoken. **Ctrl+F** finds, and says *where* each hit is ("Found at 12 minutes 8 seconds"), which is the thing a transcript in a text file can never tell you. You can also **Copy**, **Save As** plain text or WebVTT or SubRip (the timed forms, so another player can follow along), and **Open in QUILL** as a document. If the captions are automatic rather than written by a person, the window says so in its heading -- machine transcripts are useful and they are not accurate. A live stream has no transcript and says so; so does a video whose uploader published no captions.

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
- **Show Status Bar** -- shows or hides the status strip along the bottom of the main window (Now playing, Volume, Recording, Sleep timer, Favorites count, and the time). The Recording cell shows time as well as state, and which kind depends on how the capture was started: ask for an hour and it counts **down** to the end you chose ("42 min left"); press Record Now, where you asked for no length at all, and it counts **up** ("18 min so far"). The only number the app has in that second case is a safety cap that stops a forgotten recording filling your disk, and counting down to that would be telling you about a plan you never made. On by default. Reach the bar with **F6** and arrow across it; see "The main window" above for the full navigation.
- **Sort Favorites** -- Ascending (A to Z), Descending (Z to A), or Unsorted (your manual order). This is the same setting as the one in Preferences, put here so it is quick to reach; the current order is shown with a bullet. Choosing Unsorted reveals the hand-arranged order you built with Move Up/Down.
- **Expand All Folders** / **Collapse All Folders** -- open or close every folder in the favorites tree at once.
- **Station Catalog Status...** -- the complete answer to "what is stored on this computer, and what is not." Every source in one list: the stored ones with their station counts and freshness ("Radio Browser: 62,375 stations, updated 2 hours ago"), and the live-only ones with the honest reason ("iHeart: live only; its terms do not allow storing its listings"). Update Now runs a refresh; Rebuild From Shipped Snapshot restores the catalog that came with the app -- and neither touches your favorites, custom stations, or servers, which live in their own files and are never part of any catalog operation.
- **Audio Health...** (Ctrl+Alt+Shift+M) -- the answer to "is this going to work?", in one list. Which playback engine is actually in use (and, when the setting is "automatic", whether it has quietly fallen back to Windows Media because mpv is missing -- the setting still reads *automatic*, which is true and tells you nothing); whether mpv and FFmpeg are present and what their absence costs you; where the audio is going, and whether the system is still offering the output device you chose; what Sound Enhancements are doing and whether they apply to this station or all of them; whether the exact-OptiLab component shipped in this build; and whether a recording started right now could actually be written to your recordings folder. **Check Again** re-reads everything, after plugging a headset back in or reinstalling a tool. It tests nothing -- no sound is played, no device opened, no file written -- so it is safe to open in the middle of a recording, which is exactly when you are most likely to want it.
- **Downloads...** (Ctrl+Shift+J) -- the download queue: what is waiting, downloading, saved and failed, with Open Containing Folder, per-row cancel and remove, Clear Finished, Clear All, and a Preferences button. Described in full under "The download queue" above.
- **Customize Features...** -- turn whole areas of Quill Radio off if you never use them. The list shows each switchable area with a short description of what it covers -- the **Recording** menu (recording, scheduling, and the recordings list) and the **Weather** menu -- and unchecking one leaves out that whole menu, and every command under it, the next time you open the app. Nothing is deleted and nothing is lost; tick it again and it comes back. Everything is switched on to begin with, and a feature added in a future version arrives switched on too, so you only ever have to turn *off* what you do not want. Handy if you want a plain radio and nothing else to arrow past.
- **Text Size** -- Normal, Large, or Larger. Scales the text on the main window (the favorites list, the buttons, the now-playing line, and the status bar) up for easier reading. Remembered between sessions.

### Help (Alt+H)

- **What Is This?** (F1) -- context help for wherever you are standing. Press F1 on any control, in any window, and a help window opens with two parts read as one pass: **what the window you are in is for**, then **what the control under focus does and how to drive it**. The text sits in a read-only, multi-line field you can arrow through and copy; Escape returns you exactly where you were. Every window and every control answers -- a build check refuses a new surface or control that ships without its help.
- **Command Palette...** (Ctrl+Shift+P) -- every Quill Radio command in one searchable list.
- **Keyboard Shortcuts...** -- open the Keyboard Manager to view, search, and change Quill Radio's keyboard shortcuts (see "Global hotkeys and keyboard shortcuts" below).
- **Keyboard Shortcuts Sheet...** (Ctrl+Alt+Shift+K) -- every key Quill Radio answers to, in one filterable list. Type what you want to do ("record") or a key you found and cannot place ("Ctrl+B"), and the list narrows to it. The sheet is built by reading the menu bar in front of you, so it shows **the keys you actually have**: rebind something in the Keyboard Manager and the sheet says your key, not the default. Keys that have no menu item -- F6 into the status bar, the Winamp letters in the Recordings list, Shift+F10 for a row's actions -- are listed too, each with the window it works in. **Copy All** copies the list as filtered; **Change Shortcuts...** hands you to the editor.
- **Global Hotkeys...** -- assign a system-wide key to Quill Radio's playback controls so they work while another program has focus (see below).
- **Redeem Unlock Code...** -- enter a signed code for a pre-release capability. Verified entirely on your machine; nothing is transmitted; one code counts for QUILL, Quill Radio, and QUILL Cast together.
- **Check for Updates...** (Ctrl+Alt+U) -- compares your version with the newest release, downloads **the edition you are actually running** with spoken progress, then offers Install now or Open folder. A release publishes four downloads -- the full installer, the thin "Lite" installer, the portable zip, and the Companion zip -- and each installer records which one it laid down, so an update gives you the same kind back. (Before 3.0 the choice was made by file extension, and the "are you portable?" test looked for an uninstaller beside the running program -- which, on the shared runtime, lives in your AppData folder where no uninstaller sits. Nearly every installed listener was therefore offered the portable zip. If that happened to you, this is the fix; you do not need to reinstall by hand, though installing once over the top records your edition so future updates are exact.) Already up to date shows a dialog too, not just a spoken announcement. Quill Radio also runs this check quietly once a day when it launches -- silent unless it actually finds something, and Station > Preferences (Ctrl+,) turns it off if you'd rather check manually only.
- **Get FFmpeg...** -- a safety net: FFmpeg ships inside Quill Radio, but if it ever goes missing this downloads the official build so recording works again.
- **User Guide** (Ctrl+F1) / **Release Notes** (Shift+F1) / **Product Requirements...** (Ctrl+Alt+F1) -- this guide, the version history, and the product requirements document, each opened right in your browser. (F1 itself is context help now, matching QUILL's editor: F1 answers for the control you are on, Ctrl+F1 opens the guide.)
- **Report a Bug...** -- files an issue directly from the app (no GitHub account needed), stamped "Quill Radio" with this app's own version so we know exactly what you were running; falls back to the online support form if anything goes wrong.
- **Repeat Last Announcement** and **Announcement Self-Test...** (Command Palette) -- speech disappears the moment it finishes, so Repeat Last Announcement says the last thing Quill Radio told you all over again. The Self-Test announces a test phrase and then reports which channels actually delivered it -- speech, braille, sound -- and which screen-reader connection served each. It is the quickest way to tell "braille is not working" apart from "no braille display is connected", which otherwise look identical.
- **About Quill Radio** -- version, sync statement, project address.

## The Station Catalog

Quill Radio 3.0 ships the whole working-station directory *inside the app* --
more than 62,000 stations across 240 countries, plus SomaFM and the Project
Gutenberg audio shelf, about seven and a half megabytes in the download --
and keeps it in a catalog on your own computer. That one change is why
browsing feels different in 3.0:

- **Browse answers instantly, online or off.** By Country, By Language, By
  Genre and By Quality answer from your disk in under a millisecond. First
  launch on a machine with no internet at all is a complete radio.
- **Every folder announces its size before you open it** -- "France, 812
  stations" -- something the live directory could never afford, because
  counting used to cost a network round trip and now costs nothing.
- **Find Stations starts locally.** Matches from the catalog appear the
  moment you search; the live directories layer in behind them.
- **The searches you have already run are one Down arrow away.** Press
  **Down** in the station-name box for the searches you ran before, newest
  first. Picking one restores all three fields together -- name, tag and
  country -- because they work as a set: *jazz in France* and *jazz in
  Brazil* are different searches, and a list that kept only "jazz" would
  give you back the wrong one. Running the same search again moves it to the
  top rather than adding a second copy, and an empty search is never kept.
  The list holds fifteen and lives in the same file as your recently played
  stations, so clearing that clears this too.
- **A row that probably will not play says so.** Radio Browser checks every
  stream it lists and publishes the result; rows it could not play are
  marked **"may not be playable"**, and rows that have to be looked up
  before they can start -- TuneIn, YouTube -- say **"resolved when you play
  it"** instead, so a pause before the audio begins is explained rather than
  worrying. Every other row stays unmarked: only Radio Browser publishes a
  check, so marking the rest "unknown" would put a word on nearly every row
  to tell you nothing. Select any row and the details box says more,
  including the good news and the "nobody has checked this" case.
- **If you are offline, the app says so exactly once** -- "You are offline.
  Browsing from your catalog, updated this morning." -- and then keeps
  working.

### What is stored, and what is not

The catalog covers the station directory itself: Radio Browser's stations
and every axis through them, SomaFM, and the Project Gutenberg audiobook
shelf. The rest stays live and needs the internet, each for a stated reason:
**Apple Podcasts (iTunes)** (charts are rankings, and Apple's terms bar
storing them), **TuneIn** (a remote tree that may not be stored), **iHeart**
(its terms do not allow storing its listings), the **Internet Archive**
(collections of half a million items), **LibriVox** (live for now -- its
chapter listing alone is bigger than the rest of the catalog combined), and
the **music charts** (stale the moment they are stored). **View > Station
Catalog Status...** lays all of this out in plain sentences, source by
source, with each one's count and freshness. And the browse window tells you
per branch: highlight one and the details panel says either "Answers from
your catalog, updated 2 hours ago" or "Asks the internet each time; nothing
is stored."

### How it stays fresh

Three ways, each yours to switch off in Preferences:

- **Shortly after launch**, a quick background check, skipped when the
  catalog is already fresh.
- **On a schedule** -- every 24 hours by default; choose 6 hours to 2 days,
  or "Manually only". One source at a time, a trickle rather than a burst.
- **On demand** -- **Station > Update Station Catalog**, which always answers
  out loud: "Station catalog updated: 174 new stations, 431 updated."

A directory that is down costs you its freshness, never your stations: a
source that suddenly answers with nothing is treated as an outage, not the
truth, and a station that disappears is hidden at once but only forgotten
after two weeks. **Popular** and **Trending** stay live-first; when the
directory cannot answer, the catalog's snapshot steps in, and every one of
those rows says "as of 2 hours ago" so you always know what you are hearing.

### Your stations are never part of it

The catalog is a copy of public directories. Your favorites, custom
stations, servers, and YouTube channels live in their own files, and no
catalog operation reads or writes them. Rebuild the catalog from the shipped
snapshot (a button in Station Catalog Status) and your stations are
byte-for-byte untouched. Turning the catalog off entirely (Preferences)
restores live-only browsing: nothing stored, no background requests of any
kind. Safe Mode never refreshes the catalog, though reading it is allowed --
it is local data, exactly like your favorites.

## The Favorites Manager

Station > Manage Favorites... is a full organizer, keyboard-first:

- **Search favorites** filters live across names (including your custom names), countries, languages, tags, and folder names; results flatten into one arrow-key list with each station's folder spoken in its label.
- **Folders of any depth.** Create one with **New Folder...** (Ctrl+Shift+E) -- pick its location, name it, and it exists immediately, even before a station lives in it. Or just file a station under "News/Morning" and the path springs into being. Rename a folder (F2) and its subfolders come along; delete one and its stations simply step out to the top level -- nothing is ever deleted with a folder.
- **Reordering.** Move Up / Move Down within a folder; for long hops, **Mark for Move**, select the destination, then **Move Above** or **Move Below** -- the moved station joins the destination's folder. Reordering is your hand-arranged "Unsorted" order, and the Move buttons work from any view: if the list is currently sorted Ascending or Descending, the first move switches to manual order (revealing your saved order, announced "Switched to manual order") and moves the station within it -- exactly like Alt+Shift+Up/Down on the main page. Your stored order is preserved, never overwritten by the alphabetical view, so a hand-arranged list can't be lost.
- **A folder is somewhere you listen from.** A folder's own menu (Shift+F10 on it) offers **Play All in Folder**, **Shuffle Folder** and **Export This Folder...**. Playing a folder starts its first station and remembers the rest, so **Next Station in Folder** and **Previous Station in Folder** -- both in the Command Palette -- walk them. A live station never ends, so there is nothing for a playlist to advance *on*; what "play the News folder" actually means is one keystroke to the next station in the set you chose. Shuffle is one fixed order, so Previous walks back through the same sequence rather than re-rolling. Reaching either end says so rather than wrapping round, because silently looping is how you hear the same station twice and cannot work out why. A folder always means everything beneath it -- playing "News" plays "News/Local" too -- and "News" never swallows a separate folder called "Newsroom".
- **Remove All...** clears every favorite at once (your folders stay) after a confirmation that defaults to No. Because favorites keep a rolling backup, an accidental Remove All can still be recovered.
- **Open this window at startup.** Preferences (Ctrl+,) chooses the one window
  Quill Radio opens for you at launch: None, Browse Stations, Search Stations,
  Manage Favorites, Radio Recordings, or Player. It opens over the main window,
  never instead of it, and **everything else stays closed**. None is the
  default. (This replaces the old "Open Browse Stations at startup" checkbox; if
  you had it ticked, you still get Browse.)
- **Sort order.** Preferences (Ctrl+,) sets the default order for every folder -- Ascending (A to Z), Descending (Z to A), or Unsorted. Any single folder can override that from its context menu (**Sort This Folder...** on the main-page tree): choose Ascending, Descending, Unsorted, or "follow the default" just for that folder's stations. Ascending/Descending re-sort automatically as you add stations.
- **Rename** (F2 on a station) gives it your own display name everywhere; blank restores the directory's name.
- Enter plays (the Play button reads Stop while that station is on), Delete removes (with confirmation), Shift+F10 opens every action on the selected item. The main-page tree offers the same actions, so the Manager is for the heavy lifting, not a required stop.

## Chapters, and checking a mark without losing your place

**Ctrl+Shift+C** opens the chapter list. It is no longer only for a video's
published chapters:

- For a **recording or a downloaded episode**, Quill Radio reads the file's own
  chapter frames.
- For an episode **QUILL Cast has already analysed**, it reads the result Cast
  left in the shared cache -- so chapters you worked out in Cast this morning
  are there in Radio this evening, without doing it twice.
- Where there is nothing, it says so. Radio works chapters out for itself, and
  is not going to: it is the lite app, and 91 MB of speech engine to answer a
  question its sibling has already answered is not a trade worth making.

The list says which of those it is using, in its own first line.

Where the thing playing is a **file on this computer**, the list also offers
**Preview This Mark**: ten seconds *either side* of the boundary, played through
its own player. Your place does not move, so checking six marks costs nothing.
Both sides, because the question a chapter mark raises is *does the programme
turn here* -- playing forward from the mark answers a different question, which
is what the section is about.

## Quick Actions

**Station > Quick Actions...** (Ctrl+Alt+Q) decides what each kind of row
offers, and in what order.

There are three lists, chosen from the combo box at the top: **Station
actions**, **Recording actions**, and **Browse folder actions**. In each, the
**first action is what Enter does**, the first nine also answer to **Ctrl+1**
through **Ctrl+9**, and the whole list is the order of the right-click menu.
Move Up, Move Down and **Make Default** rearrange; **Reset This List** puts a
list back to how it shipped.

QUILL Cast has had exactly this since 1.1.0, with the same keys and the same
nine, so whichever of the two you learn it in, you have learned it in both.

One thing it deliberately cannot do: it orders what a row *already* offers, and
never adds anything. A station already in your favorites still offers Remove and
not Add; a live stream still offers no Download. Putting Download at the top of
your list does not make a live stream downloadable -- it means Download is first
on the rows that have it.

## What each row says

A list is read out one column at a time, so the columns *are* the sentence you
hear on every row. **View > Choose Columns...** (Ctrl+Alt+Shift+C) is where you
decide it -- for Find Stations results, and for the Recordings list.

The window holds two lists: **Shown, in the order they are read** and
**Hidden**. Move Up and Move Down (or Alt+Up and Alt+Down) rearrange the shown
ones. **Hide** takes a column out of the row altogether -- not to the end of it,
out of it, because a column that is still there is still spoken. **Show** puts
one back where its place in the order says it belongs, so hiding something for a
week and showing it again does not send it to the end.

Underneath the lists, **A row will read:** spells out the sentence one row will
say with the settings exactly as they stand. You can hear the effect of a change
before pressing OK, which is the whole point: this is a speech setting wearing a
column setting's clothes.

**One column in each list is pinned** -- the station's name, the recording's
name -- because a row with nothing to identify it is a row you cannot act on.
Asking to hide it says so and why, rather than quietly doing nothing.

**Some columns are offered but start switched off**, because a list that says
everything says nothing. Find Stations can also show **Language**, **Genres**,
**Popularity** and **Bitrate** on its own. Recordings can also show **Length**,
which is blank wherever the number Quill Radio holds is a disk-safety cap rather
than a length you chose -- announcing a cap as a plan would be telling you
something you never said.

**Reset This List** puts one list back the way it shipped. Your choice is saved
per list and kept between sessions.

## Listening statistics

**Playback > Listening Statistics...** (Ctrl+Shift+Q) answers the question the
recently-played list never could: not *what did I have on*, but *how much*.

Choose a period -- this week, this month, this year, or all time -- and the
window reports how long you listened in total, how many listening sessions that
was, then a breakdown **by station** and **by network**. Durations are read as
language ("3 hours, 47 minutes"), never as a clock face, because a screen reader
reads `3:47:00` as a time of day.

**Copy** takes the whole report. **Save as CSV...** writes every session out for
a spreadsheet. **Delete My History...** removes the lot, and asks first with No
as the default, because there is no other copy of it anywhere.

What counts, and what does not:

- Time counts **only while audio is actually coming out**. Connecting does not
  count. Buffering through dead air does not count. Paused does not count. The
  app sitting stopped overnight does not count.
- Anything under ten seconds is not a session. Skipping past a station in a list
  is not listening, and a log full of three-second samples would make every
  per-station total meaningless.
- There is no "time saved by playing faster" and no "silence trimmed", because
  neither means anything for a live broadcast. They are left out rather than
  reported as zero.

Your history is kept on this computer and goes nowhere.

## Handing an episode to QUILL Cast

On a subscribed show's episode in the browse tree, alongside Play and Mark
Episode as Played:

- **Play Next in QUILL Cast**
- **Add to QUILL Cast Queue**
- **Send to the QUILL Cast Inbox**

These are a **handoff**, not an instant change. Quill Radio notes what you asked
for, and QUILL Cast carries it out the next time it opens -- which is why the
confirmation says so ("It will be next in the QUILL Cast queue") rather than
implying it has already happened. Both apps load and save the shared library
whole, so a write from here while Cast was open would overwrite whatever Cast
had done since it opened.

## The Recordings list

Record > Recordings... shows the whole recording life cycle in one place. The list updates rows in place keyed by file path, so it is a no-op when nothing has changed; when something has, your selection, focus, and scroll position are preserved instead of the list rebuilding under you mid-read.

The line under the list leads with what is happening rather than with counts: *"Recording, 42 min left. Next: KFI at 11:00 tomorrow. 14 recorded. In D:\Music\Quill Radio Recordings."* A recording due within the hour is given in minutes ("KFI in 12 minutes"), one further out by weekday, and a date past a week. If you have scheduled recordings but none of them can fire -- every one disabled, or a one-off that already ran -- it says "3 scheduled, none coming up" rather than a count that reads as cover.

The list itself holds:

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
- **NOAA Weather Radio** browsing, search, and the local-transmitter lookup use the keyless **WeatherIndex** directory (api.wxindex.org) when online, with the complete directory also bundled inside the app as a permanent offline fallback; **Radio Reading Services** refreshes from the community **RadioBrowser** directory the station search already uses, with its own bundled list as the fallback. (Text weather -- forecasts, alerts, air quality -- lives in the **Quill Weather** app now, along with its network calls; see the Weather chapter.)
- The **ACB Media** directory is bundled -- no network needed to browse it, and the bundled **Radio Reading Services** and **NOAA Weather Radio** directories browse offline the same way.

**If one of those bundled tools goes missing.** Both mpv and ffmpeg ship inside
every Quill Radio installer, so a missing one means a damaged installation
rather than something you never bought -- antivirus quarantine and a
half-finished update are the two usual causes. Quill Radio now says so, once, at
launch: one sentence naming which tool is gone, what it costs you, and what to
do. It does not repeat on every launch, but it will say it again if a *second*
tool goes missing later.

- **Without mpv**, stations still play through Windows Media, but live pause and
  rewind, choosing the output device, Volume Boost, Sound Enhancements without a
  relay, track titles from the stream, and knowing when a stream has stalled all
  stop working -- and Ogg Vorbis, Opus and HLS stations will not play at all. A
  station in one of those formats now says exactly that, rather than the generic
  "that stream could not be opened".
- **Without ffmpeg**, recording (now or scheduled) and downloading episodes and
  videos stop working. Everything else is normal. **Help > Get FFmpeg...**
  downloads the official build on its own.
- **Either way, reinstalling Quill Radio restores it.**

A healthy installation says nothing at all about any of this, which is the
point.

## Weather

Weather is its own app -- **Quill Weather** -- and this Weather section lives in the Quill Weather User Guide (`../../weather/docs/userguide.md`), its own home.

Quill Radio no longer has a Weather menu at all: forecasts, alerts, and background alert monitoring belong to Quill Weather, which you can open from the **QuillVille** menu. What stays in Quill Radio is the radio part of weather -- the **Weather / NOAA** branch of Browse Stations, with every NOAA Weather Radio transmitter that has an internet feed, still searchable by call sign, SAME code, or "County, ST".

## Keyboard reference

**Every menu item shows its own shortcut.** You never have to walk a menu to
find out whether there is a faster way in -- if there is a key, the item says
so, right there in the menu. And where an item has a shortcut you can change,
the menu shows *the key you actually have bound*: rebind it in **Help >
Keyboard Shortcuts...** and the menu updates to match. The table below is the
short list of the ones worth memorising; the menus carry the rest.

For the whole list at once, without opening six menus: **Help > Keyboard
Shortcuts Sheet... (Ctrl+Alt+Shift+K)**. It is built from the menu bar in front
of you, so it always shows the keys *you* have -- including anything you
rebound, which is more than this table can promise.

| Action | Key |
| --- | --- |
| Browse Stations | Ctrl+B |
| What Is This? (context help for the focused control) | F1 |
| User Guide | Ctrl+F1 |
| Keyboard Shortcuts Sheet (every key, filterable) | Ctrl+Alt+Shift+K |
| Audio Health (can this installation play and record?) | Ctrl+Alt+Shift+M |
| Find Stations | Ctrl+F |
| Manage Favorites | Ctrl+Shift+M |
| Recordings | Ctrl+Shift+R |
| Go To (a numbered list of places) | Ctrl+G |
| Record Now / Stop Recording | Ctrl+R |
| Schedule Recording | Ctrl+Shift+S |
| Play / Stop | Ctrl+P |
| Stop outright, whatever is happening | Ctrl+. or Ctrl+Alt+P |
| Play Last Station | Ctrl+L |
| Mute / Unmute | Ctrl+M (main window) or Ctrl+Shift+O (anywhere) |
| Volume up / down (steps of 10) | Ctrl+Up / Ctrl+Down |
| Go to Player (opens the player window, or brings it to the front) | Ctrl+Shift+G |
| Volume Boost | Ctrl+Shift+B |
| Output Device | Ctrl+Shift+D |
| Rewind / Forward 30 seconds | Ctrl+Shift+Left / Ctrl+Shift+Right |
| Back to Live | Ctrl+Shift+L |
| Chapters (finished video) | Ctrl+Shift+C |
| Go to Position (finished video) | Ctrl+Alt+J |
| Next / previous chapter | Ctrl+Shift+. / Ctrl+Shift+, |
| Play faster / slower / normal speed | Ctrl+Shift+Up / Ctrl+Shift+Down / Ctrl+Shift+0 |
| Where am I? (position, length, chapter) | Ctrl+Shift+W |
| Show or hide the video | Ctrl+Shift+V |
| Captions on or off | Ctrl+Shift+K |
| Video information | Ctrl+Shift+I |
| Full screen | F11 |
| Audio and Described Audio | Ctrl+Shift+A |
| Play Described Audio | Ctrl+Alt+D |
| Transcript (read what a video says) | Ctrl+Shift+T |
| What's Playing? | Ctrl+T |
| Sound Enhancements (EQ, compressor, channel mode) | Ctrl+E |
| Song History | Ctrl+Shift+H |
| Play favorites 1-10 directly | Ctrl+Alt+Shift+1 ... Ctrl+Alt+Shift+0 |
| Send to tray | Ctrl+W |
| Show / hide from any app (system-wide) | Ctrl+Alt+Shift+R |
| Next / previous window | Ctrl+Tab / Ctrl+Shift+Tab |
| Jump to window 1-9 | Ctrl+1 ... Ctrl+9 |
| Close the window you are in (Browse, Player, the managers) | Escape, Ctrl+W, or Ctrl+F4 |
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

**The transport keys work in every window**, not only the main one -- Browse
Stations, Find Stations, Manage Favorites, the Recordings list, Song History,
the chapter list, Now Playing, the download queue and the player panel all
answer to Play/Stop, volume, mute, skip, speed, chapters, Where Am I, Go to
Player and the Command Palette. They come from one shared table, so a key means
the same thing and moves the same distance wherever you press it.

**Nothing here sits on Ctrl+Alt+arrow.** That block belongs to JAWS's and
NVDA's table navigation, and a transport key there works everywhere except
while somebody is reading a table. Speed and chapters used to be on it; in 3.0
they moved to Ctrl+Shift+Up/Down and Ctrl+Shift+comma/period, and a build check
now fails if anything lands back on that block. If you have notes from an
earlier version, those four keys are the ones that changed.

These keys belong to Quill Radio's own menus and are kept separate from QUILL's keymap, so nothing here collides with editor shortcuts.

## Troubleshooting

- **A station will not play.** Streams move. If the station came from the directory, Quill Radio automatically fetches its current address and retries once; if it still fails, search for it again in Browse Stations, or re-add it as a custom station. If a station is simply dead, tell us: **Report Bad Station...** on that station's context menu in Browse Stations or Search Stations opens a bug report already filled in with the station's name, stream, source, and country, so you do not have to write any of it out. It carries the station's details only -- never your name, email, or any file paths. (Directories hide stations their own checker believes are dead, so a station that plays for the directory but not for you is one only you can flag.) (Format problems are largely history as of 1.1.0: the two engines together play MP3, AAC/HE-AAC, Ogg Vorbis, Opus, FLAC, and HLS, and a stream one engine can't open is retried on the other automatically.)
- **A station plays for twenty or thirty seconds and then stops.** This was a real fault, fixed in 3.0. Some stations -- iHeart's in particular -- are delivered in short chunks that have to be topped up every few seconds, and one failed top-up used to drain what was already buffered and then go silent, which lands about twenty to thirty seconds later. Quill Radio now reconnects instead of stopping: you hear "Reconnecting to *station*. Attempt 1 of 3", then either "Reconnected to *station*" or, after three tries, a plain statement that it could not be reconnected and may be off the air. If you are on 3.0 and still hear a station stop dead with no reconnection attempt at all, that is worth reporting -- use **Report Bad Station...** on the station, which fills the report in for you.
- **A recording is not reconnected the same way.** That is deliberate. A recording -- a LibriVox chapter, an Archive episode, a downloaded show -- reaching its end has genuinely ended, and "reconnecting" would simply play it again.
- **No sound but the app says playing.** Check Mute (Ctrl+M), the per-station volume (Ctrl+Up), and the Windows volume mixer entry for Quill Radio.
- **A station's own web address will not play.** Quill Radio needs the *audio feed*, not the station's website. Many stations build their player in JavaScript, so the feed is nowhere in the page for anything to find -- **Find Streams from a Website...** reads pages, and it deliberately never runs JavaScript. If a station's home page finds nothing, look for a "Listen Live" link, or paste the station's name into **Search Stations...** instead: the directories usually already have the feed.
- **A recording saved nothing.** Quill Radio says so, names the station, and gives the reason -- "the connection failed", "the station refused the connection", "that stream address is no longer there", "the disk is full". No file is kept, because an empty one is only something to find later and wonder about. This uses the error sound rather than the saved sound, so it never sounds like a successful recording. If the station is one that also drops out while playing, the two are the same underlying problem: the connection is not staying up long enough.
- **A recording stopped early.** Check Record > Recordings... -- a dropped connection continues into "(part 2)" files when reconnect is on, and those parts are joined back into one recording when it finishes. The maximum-length cap in Recording Settings also ends recordings deliberately.
- **I still have "(part 2)" files.** That means the join was refused or failed, and Quill Radio will have said why when the recording ended -- most often because a part is missing, or the parts are not all the same format. Your audio is safe: every part is exactly as it was recorded, and they play in numbered order.
- **The wake-up timer did not fire.** Quill Radio (or QUILL) must be running at the set time -- the tray counts, a closed app does not. It also never retro-fires: opening the app hours after the set time stays silent until the next occurrence.
- **The tray icon is gone.** Check the taskbar overflow area, or set Quill Radio to "always show" in Windows taskbar settings.
- **Rewind, Volume Boost, or the output device "needs the mpv playback engine."** Preferences (Ctrl+,) > Playback engine is set to Windows Media (classic), or the bundled engine is missing. Set it back to Automatic; these features live in the mpv engine.
- **Playback sounds different since 1.1.0.** It shouldn't -- but if anything about the new engine bothers you, Preferences (Ctrl+,) > Playback engine > "Windows Media (classic)" is exactly the old behavior. Please report what you heard either way (Help > Report a Bug...).
