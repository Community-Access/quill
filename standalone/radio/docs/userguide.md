# Quill Radio User Guide

Version 3.1.1, released 2026-09-30.

## Upcoming Preferences Search

Preferences gains **Find a setting** in the next maintenance update. Type a
term from a setting's label or help, press Down for matching settings, then Enter
to focus one. Control+F returns to search; Escape clears a search before closing.
Search navigates only: OK still saves, Cancel still cancels, and values are not
indexed. Disabled settings stay disabled.

Quill Radio is internet radio built for screen reader users. It is a small window. The favorites tree has focus the moment it opens. The menus say everything they do, every action speaks, and a tray icon keeps the music playing while you work. It runs the same radio code as QUILL itself and, when installed, shares its data, so nothing you set up here is stranded.

## Contents

The chapters, in order, grouped by what you want to do. Each one is a level 2 heading, so press your screen reader's 2 key to move from chapter to chapter.

- Start here: How to use this guide; Installing; Getting started; Your first half hour, step by step.
- Everyday listening: The player follows you; The main window; Go To; Windows, and moving between them; Menus.
- Finding things to hear: Browse Stations; Search Stations; Adding your own stations.
- Keeping what you like: The Favorites Manager; Backing up and restoring; Preferences.
- Controlling what plays: Pausing, rewinding and moving around; What's playing, and what played; Volume and sound; Video, captions and described audio; Timers.
- Recording: Recording, including scheduled recordings and the Recordings list.
- How the lists work: The Station Catalog; Quick Actions; What each row says; Listening statistics.
- Podcasts, bookmarks and the community: Handing an episode to QUILL Cast; Bookmarks; Skip Silence; The ACB Media schedule; Reminders and Upcoming; The Community menu.
- Safety nets: Taking back the last thing you did; Why a menu item is dimmed; Recent Problems; Quiet hours; Moving your setup to another machine; Checking your subscribed podcasts.
- Making it yours: What the main window shows; Keyboard Shortcuts, the Sheet, and Global Hotkeys; The Command Palette; Tutorials.
- Help and the rest: Help, updates and documents; Spotify (experimental); Hardware media keys; The system tray; Closing Quill Radio; Quillins; Sharing data with QUILL; Weather; Television; Dependencies, honestly stated.
- Reference: Keyboard reference; Getting help; Troubleshooting.

## How to use this guide

- Every chapter is a heading, so your screen reader's heading keys move between them.
- Most features have numbered steps. Each step says which key to press and what you should hear, or where focus lands.
- Keys are the ones Quill Radio ships with. If you rebind a key in the Keyboard Manager, the menus show your key, and so do the tutorials inside the app. This guide cannot know it.
- "Press Alt+S, then choose X" means: open the Station menu, arrow to X, and press Enter. Every menu item also shows its own shortcut.
- A path such as **Station > Preferences...** means the Station menu, then the Preferences item.
- "Choose a button" means Tab to it and press Space, or press its Alt letter where it has one. Enter presses the default button of a dialog.
- "Good to know" and "If it does not work" notes follow the steps where they help. The last chapter, Troubleshooting, collects the common problems in one place.
- For guided lessons that can run a step for you, open **Help > Tutorials...** (Ctrl+Alt+F1).
- For help on the exact control you are on, press **F1** in the app.

## Installing

### The two downloads

Quill Radio 3.1.1 comes in two downloads. In each file name, `<version>` is the release, such as 3.1.1.

1. **The installer**, `Quill-Radio-Setup-Shared-<version>.exe`. This is the right choice for most people. It gives Quill Radio a Start Menu entry and an uninstaller. It installs the shared QuillVille Runtime if it is not already on the computer, then the app. Your favorites, history and settings live in the shared Quill data folder in your Windows profile, so QUILL and QUILL Cast see them too.
2. **The portable copy**, `Quill-Radio-Portable-<version>.zip`. It is fully self-contained. It carries its own genuine, unmodified Python and the bundled ffmpeg (for recording) and mpv (for playback). Unpack it anywhere, a USB stick included. Nothing downloads when it runs. Use it when you want the whole radio to travel with you, or when you cannot install software.

Both downloads are on the QUILL Releases page on GitHub, under the tag `quill-radio-v3.1.1`.

### Install with the installer, step by step

1. Download `Quill-Radio-Setup-Shared-3.1.1.exe` and open it from your Downloads folder.
2. If Windows SmartScreen shows a warning, see "About security software" below.
3. Setup may first ask whether to install for you only or for all users. Choose **Install for me only**. That needs no administrator rights. Installing for all users asks Windows for permission.
4. The setup wizard opens. Press Enter on each page to accept the defaults. The full installation includes this guide and the release notes. Then choose **Install**.
5. If the QuillVille Runtime is not already on this computer, the installer copies it first. The progress bar is read as a percentage by NVDA, JAWS and Narrator.
6. On the last page, press **Space** on the **Launch Quill Radio** checkbox to check it (it starts unchecked), then choose **Finish**.
7. Quill Radio opens. Focus lands in the Favorite stations tree. On a first launch, the welcome screens come up first (see "The first time you open it").

Next time, open Quill Radio from the Start Menu: press the Windows key, type `Quill Radio`, and press Enter.

### Use the portable copy, step by step

1. Download `Quill-Radio-Portable-3.1.1.zip`.
2. In File Explorer, select the zip, press the Applications key, and choose **Extract All...**. Choose a folder, for example on a USB stick, and choose **Extract**.
3. Open the extracted folder, then the `QuillRadio` folder inside it.
4. Select `QuillRadio.exe` and press Enter. Quill Radio opens with focus in the Favorite stations tree.
5. If it does not open, wait a moment: from 3.0.4 a message says what happened and what to do. See "If Quill Radio does not start" under Troubleshooting.

Pressing Enter on `QuillRadio.exe` while you are still inside the zip, before extracting it, runs that one file alone; Quill Radio says so and asks you to extract the whole zip first.

**A portable copy writes nothing to the computer it runs on.** This is true from the very first launch, and there is no setting to find first.

- Settings, favorites, history, logs and caches live in the `data` folder beside `QuillRadio.exe`.
- Recordings go to a `Recordings` folder inside the portable folder, and downloads to a `Downloads` folder, instead of your Music and Downloads folders.
- **Start Quill Radio with Windows** is not available. Choosing it says that a portable copy does not add itself to this computer's startup.
- **Wake the computer for a scheduled recording** is greyed out in Preferences, with the reason. Keeping the computer awake before a recording still works.
- To turn a portable copy into an ordinary copy that uses this computer's profile, delete its `data` folder. Your Recordings and Downloads folders sit beside `data`, so deleting `data` keeps them.

### Bring your favorites from Quill Radio 2.x

Quill Radio 2.x kept its favorites in this computer's profile, even when it ran from the portable zip. A 3.0 portable copy keeps its own, so the first time it starts, it looks for them.

1. Unzip `Quill-Radio-Portable-3.1.1.zip` and start `QuillRadio.exe`, as above.
2. If an earlier Quill Radio on this computer has favorites, and this copy has none yet, a question opens: "Favorites from an earlier Quill Radio". It says how many favorite stations it found.
3. Press **Enter** (Yes) to copy them, with your settings, recording schedule and reminders, into this portable copy. Quill Radio then opens with your favorites in the tree.
4. Or choose **No** to start empty.

Good to know:

- The earlier copy is only read, never changed. Nothing is written to the computer.
- You are asked once. Either answer is remembered in the portable copy.
- The installed copy needs none of this: it reads the same profile 2.x did, so your favorites are simply there.

### If you had the Lite installer or the Companion zip

Test builds of 3.0 also offered a thin "Lite" installer and a small Companion zip. Both are retired. Nothing is lost:

- If you used the Lite installer, run `Quill-Radio-Setup-Shared-3.1.1.exe`. It upgrades your installation in place and keeps your data.
- If you used the Companion zip, run the installer, or unpack the portable zip instead. Check for Updates on a Companion copy offers the installer.

### The QuillVille Runtime

Quill Radio belongs to a small family of apps: QUILL, Quill Radio, Quill Weather and QUILL Audio Studio. Underneath, they run on the same Python engine. The installer puts that engine on your computer once per user, as a shared component called the **QuillVille Runtime**, and every family app reuses it. Install one app, and the next one you add starts instantly, because the engine is already there.

The runtime looks after itself. Windows keeps count of how many family apps rely on it. It is removed only when you uninstall the last app that needs it. Uninstalling Quill Radio while Quill Weather is still installed leaves the runtime in place for Weather.

The portable copy does not use the shared runtime. It carries its own.

### About security software and antivirus

Quill Radio's launcher is a small native program, and the Python it runs is the official, unmodified build. Earlier versions used a renamed copy of Python's own `pythonw.exe` as the launcher. Some antivirus tools flagged that pattern as a false positive. That pattern is gone.

Release builds are code-signed. The installer, the uninstaller and the app carry an Authenticode signature, so Windows can verify who built them. While a new release builds reputation, SmartScreen may still show a caution. To go ahead:

1. In the SmartScreen window, choose **More info**.
2. Check that the publisher is shown, then choose **Run anyway**.

## Getting started

### The first time you open it

The very first launch shows a short welcome of three screens: "Welcome to Quill Radio", "Find something to listen to" and "Keep the ones you like". Each screen names the real key for what it describes. If you have already rebound a key, it tells you your key.

The welcome never appears if you already have favorites, for example after an upgrade, a restored backup or an imported station list.

Walk through it like this:

1. Launch Quill Radio. The welcome opens with focus in the text. You should hear "Welcome to Quill Radio. Screen 1 of 3."
2. Read the text with the arrow keys.
3. Press **Alt+N** for **Next**. The next screen opens and focus returns to its text. On the last screen, the same button reads **Finish**, and its key is **Alt+F**.
4. Press **Alt+B** for **Back** to go back a screen.
5. On screens 2 and 3, press **Alt+S** for **Browse Stations Now...** to leave the welcome and open Browse Stations, the tree of everything there is to listen to.
6. Press **Escape**, or **Alt+K** for **Skip**, to leave at any time. Skipping counts as done. The welcome will not come back.

The welcome has one checkbox, **Show me a tip now and then** (Alt+T), which is on. Tips are one sentence each. Each is shown once ever, the first time you reach a place where one fact helps. For example: "Live radio can be rewound. Rewind goes back 30 seconds at a time, up to the buffer's length, and Back to Live catches up again." Tips never take the keyboard and never repeat. Uncheck the box to turn them all off.

### Every launch after that

Launch Quill Radio from the Start Menu, or run `QuillRadio.exe` in the portable folder. The window opens with keyboard focus on the **Favorite stations** tree.

- **No favorites yet?** Press **Ctrl+B** to open Browse Stations. It is a tree of every source: popular stations, NOAA Weather Radio, radio reading services, whole directories, podcasts and more. Expand **ACB Media** for the whole ACB stream directory, playable with no setup. Or press **Ctrl+F** for Search Stations, to search by name, genre, country or language.
- **With favorites:** arrow to a station and press **Enter**. That is the whole loop.
- **Want the radio on the moment the app opens?** Press **Ctrl+Alt+L** once to turn on **Station > Resume Last Station on Launch**. From then on, launching Quill Radio starts your last station.

Everything Quill Radio announces goes through your screen reader (JAWS, NVDA or Narrator) without stealing focus.

Announcements also go to a connected **braille display**. Nothing is shortened, so a long track title is there in full to pan through. The same message repeated within a couple of seconds does not flash the display twice. If a burst of messages arrives at once, the first is shown at once and the rest settle to the newest. Errors always show straight away. An unplugged display never costs you speech: the message is still spoken. Quill Radio has no braille setting of its own.

## Your first half hour, step by step

This chapter assumes nothing. Every step says which key to press and what you should hear. Work straight down it and you will finish with a station playing, a favorite saved, a recording made, and the keys that matter in your fingers.

If something does not happen as described, please report it. **Help > Get Help from Support...** (Ctrl+Alt+F2) fills most of the report in for you.

Throughout: **Escape** steps back out of wherever you are, and no step below can lose anything you have not deliberately saved.

### Task 1: play your first station (about two minutes)

1. Launch Quill Radio from the Start Menu, or run `QuillRadio.exe` from the portable folder.
2. Wait for the window. You should hear "Favorite stations, tree", or your screen reader's words for an empty tree. Focus is already in the favorites list. On a new installation the list is empty, and that is expected.
3. Press **Ctrl+B**. Browse Stations opens. Your screen reader reads the window title, and focus is in the tree on its first row, **Search All Sources...**.
4. Press **Down arrow** a few times. Each press reads a source: Favorites, Popular Stations, Trending Now, Recently Added or Changed, By Country, By Language, By Genre, By Quality, Weather / NOAA, ACB Media, and so on. Nothing has loaded from the internet yet. These are only the branches.
5. Stop on **Popular Stations** and press **Right arrow** to open it. The first time, it fetches the list, so give it a moment. You should hear "Loading Popular Stations", then how many stations arrived.
6. Press **Down arrow** to move onto a station, then press **Enter**.
7. You should hear "Playing" and the station's name over a short connecting sound, then the station itself. That is the whole loop: arrow to a thing, press Enter.
8. Press **Ctrl+Down** twice. Each press says the new level, for example "Volume 70 percent." Volume moves in steps of ten, in every window.
9. Press **Enter** again on the same station. It stops, and you hear "Radio stopped." Press **Enter** once more and it plays again.

If it does not work:

- **You hear an error instead of the station.** Some directory addresses are dead. Arrow to another station and press Enter. Quill Radio has already tried to repair the address for you (see "When a station will not play").
- **You hear nothing at all, but the app says playing.** Press **Ctrl+M** in case the radio is muted, then **Ctrl+Up** a few times. Also check the Windows volume.
- **The branch says "Could not be reached".** The internet or that directory is down. Try **By Country** instead: it answers from the catalog on your own computer, even offline.

Leave the station playing for the next task.

### Task 2: keep it (about one minute)

1. Press **Escape** to close Browse Stations. Focus returns to the favorites tree in the main window, and the station keeps playing.
2. Press **Ctrl+Shift+F**. This is **Station > Add Playing Station to Favorites**. It saves whatever is playing, wherever you are. You should hear that the station was added to your favorites.
3. Press **Down arrow** in the favorites tree. Your station is there.
4. Press **Enter** on it. It plays. From now on this is your route to that station: launch, then Enter.

That is the core of Quill Radio. Everything below is optional.

### Task 3: work the player from anywhere (about three minutes)

The player is one object, and every window can reach it.

1. With something playing, press **Ctrl+B** to open Browse Stations again.
2. Press **Ctrl+Up**. The volume goes up and says the new level, from the browse window. The same is true of **Ctrl+P** (play or pause), **Ctrl+Shift+O** (mute and unmute) and every other transport key in "The player follows you".
3. Press **Ctrl+Shift+G**. This is **Go to Player**. The Player window opens and your screen reader reads its title, then the Now playing box. If the Player is already open behind you, the same key brings it to the front instead of opening a second copy.
4. Press **Tab** through it. First is a read-only **Now playing** box: what is on, where you are in it, how fast it is playing and how loud. Then come the buttons: Play (or Stop), Pause (or Resume), Skip Back, Skip Forward, Where Am I?, Previous Chapter, Next Chapter, Chapters..., Slower, Faster, Normal Speed, Skip Silence, Volume Down, Volume Up, Mute/Unmute, and last Add to Favorites.
5. Press **Escape**. The Player closes and focus goes back to the window you came from.

### Task 4: do anything by name (about one minute)

If you cannot remember a key, you never need to.

1. Press **Ctrl+Shift+P**. The **Command Palette** opens, from any Quill Radio window. Focus is in its search box.
2. Type a few letters of what you want, such as `vol`, `record` or `chapter`. The list narrows as you type.
3. Press **Down arrow** to the command you want and press **Enter**. It runs exactly as its key or menu item would. Each entry shows its own keystroke, so the palette teaches you the shortcut as you use it.

### Task 5: record something (about three minutes)

1. With a station playing, press **Ctrl+R**.
2. You should hear "Recording started" and the station's name. The status bar's Record cell now reads **Stop Recording**, with the time so far.
3. Wait ten or twenty seconds.
4. Press **Ctrl+R** again to stop. You should hear "Stopping recording", then that the recording was saved, with the file's name.
5. Press **Ctrl+Shift+R**. The **Radio Recordings** window opens with focus in the list. Your recording is at the top, because the newest is first.
6. Press **Enter** on it. You should hear "Playing recording" and its name, then the recording.
7. Press **Delete** to remove it. A question opens: "Delete the recording ...?" **No is the default**, so Enter alone keeps the recording. To delete it, press **Y**, or Tab to **Yes** and press Enter. Focus lands on the recording that took its place in the list.
8. Press **Escape** to close Radio Recordings.

Good to know: recordings are saved in your Music folder, under `Quill Radio Recordings`, or in the `Recordings` folder of a portable copy. **Open in Folder** in Radio Recordings shows the file in File Explorer.

### Task 6: the seven keys worth memorising

Everything else is in the menus and the palette. These seven carry the day:

| What you want | Key |
| --- | --- |
| Play or stop, in the main window | Enter on a favorite, or Ctrl+P |
| Pause or resume a recording, podcast or file | Ctrl+Space |
| Volume up or down | Ctrl+Up / Ctrl+Down |
| Go to the Player, from anywhere | Ctrl+Shift+G |
| Do something by name | Ctrl+Shift+P |
| Browse for stations | Ctrl+B |
| What is playing right now? | Ctrl+T |

### If you get lost

- **Escape** closes the window you are in and returns you to the one you came from.
- **F6** moves into the status bar along the bottom of the main window. A second F6, or Escape, brings you back. Tab never lands there. See "The status bar".
- **Ctrl+Shift+G** brings the Player to you, wherever you are.
- **Ctrl+G** opens Go To, a numbered list of places.
- **F1** explains where you are: the window's purpose, then the control that has focus, in a text box you can arrow through.
- **Ctrl+F1** opens this guide.

## The player follows you

Every Quill Radio window answers to the whole transport, not only the main window. That includes:

- Browse Stations
- Search Stations (the Internet Radio window)
- Manage Favorite Stations
- Radio Recordings
- Song History
- The Chapters list
- Now Playing
- Downloads
- Find Streams from a Website
- The Tutorials window
- The Video window
- The Player itself

In all of them:

- **Ctrl+P** plays, or pauses and resumes.
- **Ctrl+.** stops outright.
- **Ctrl+Up** and **Ctrl+Down** move the volume.
- **Ctrl+Shift+O** mutes and unmutes.
- **Ctrl+Shift+Left** and **Ctrl+Shift+Right** skip back and forward.
- **Ctrl+Shift+Up**, **Ctrl+Shift+Down** and **Ctrl+Shift+0** change the speed.
- **Ctrl+Shift+,** and **Ctrl+Shift+.** move by chapter, and **Ctrl+Shift+C** opens the chapter list.
- **Ctrl+Shift+9** turns Skip Silence on or off.
- **Ctrl+Shift+W** says where you are.
- **Ctrl+Shift+G** brings up the Player.
- **Ctrl+Shift+P** opens the Command Palette.

The main window works a little differently, because its menus carry the same verbs:

- **Enter** on a favorite, or **Ctrl+P**, plays or stops.
- **Ctrl+Space** pauses and resumes.
- **Ctrl+.** stops outright.
- **Ctrl+M** mutes, and **Ctrl+Shift+O** does too.
- **Ctrl+Shift+Left** and **Ctrl+Shift+Right** rewind and go forward 30 seconds, and **Ctrl+Shift+L** goes back to live.

Three things follow from having one table of keys:

- **A key means one thing everywhere.** Volume moves the same distance and says it in the same words in every window.
- **A key that cannot act says why.** Ask for speed or chapters while a live stream plays and you hear "This is live radio, which plays at broadcast speed and has no chapters or position to move through."
- **A key that does act says so.** Play, Stop and Mute all speak. Mute especially: without a word, muting sounds exactly like the stream dropping.

### The Player window (Ctrl+Shift+G)

The Player is a small window of its own. It holds the whole transport as buttons, plus a readout of what is playing, where you are in it, the speed and the volume. It stands in the Window menu and the Ctrl+Tab rotation like any other window.

1. Press **Ctrl+Shift+G** from any window. The Player opens, or comes to the front if it is already open. Focus is in the **Now playing** box.
2. Arrow through the Now playing box to read it. It follows changes made anywhere else while it is open.
3. Press **Tab** to move through the buttons, in this order: **Play** (reads **Stop** while playing), **Pause** (reads **Resume** while paused; dimmed on live radio, with the reason), **Skip Back**, **Skip Forward**, **Where Am I?**, **Previous Chapter**, **Next Chapter**, **Chapters...**, **Slower**, **Faster**, **Normal Speed**, **Skip Silence**, **Volume Down**, **Volume Up**, **Mute/Unmute**, then **Add to Favorites** (reads **Remove from Favorites** when the playing station is already a favorite).
4. Press **Space** on a button to use it. Each button runs the same command as its key, then the readout updates.
5. The keys work inside the Player too, and each one updates the readout.
6. To close the Player, press **Escape**, **Ctrl+W**, **Ctrl+F4** or **Alt+F4**. Focus returns to the window you came from.

The Player's own menu bar has three menus: **Player** (Alt+P), with **Close** (Ctrl+W); **Station** (Alt+S); and **Window** (Alt+W).

You can also make the Player the main window's view. See "What the main window shows".

## The main window

### What is in it

Tab moves through five stops, in this order. It is a list you play from, not a player.

1. **Now playing**, a read-only box. It says the station and what the player is doing, the track when there is one, and anything else true, such as a recording running. You can arrow through it and copy it with Ctrl+C. It is never rewritten while you are reading it: an update that arrives while it has focus waits until you leave. It does not show elapsed time. Press **Ctrl+Shift+W** for that.
2. **Favorite stations**, the tree. It shows the same folders you build in the Favorites Manager. **Alt+F** jumps to it from anywhere in the window.
3. **The transport button**, which says what it will do and to what: **Play** and the selected favorite's name (Alt+L) while nothing is playing, **Stop** and the playing station's name (Alt+T) while something is, and **Resume** and its name (Alt+U) while a podcast, recording or local file is paused. The name is the one you gave the station in Favorites, if you gave it one. With a folder or nothing selected it reads **Play -- nothing selected**, and pressing it says what would work. Stop is the same as **Ctrl+Period** and **Station > Stop**; **Ctrl+P** presses this button from anywhere. (Until 2026-10-01 this was a Stop button that stayed Stop while nothing played; a listener asked whether it should become Play, and it should.)
4. **Mute**, a toggle button. It shows the true state, even when you muted from somewhere else.
5. **Volume** (Alt+O), a slider. Up and Right make it louder, Down and Left quieter, and Page Up and Page Down move it in bigger steps. (Until 3.0.4 Up was quieter, because that is what a Windows slider does on its own; a listener reported it as backwards, and it was.) The slider, Ctrl+Up and Ctrl+Down, and the status bar's Volume cell always agree, including with each station's remembered volume.

Along the bottom is the **status bar**. Tab never reaches it. Press **F6**. See "The status bar".

The other buttons older versions had here have moved, not gone. Play is **Enter** on a station or **Ctrl+P**. Record is **Ctrl+R**. Browse Stations is **Ctrl+B**. Chapters are in the Player (**Ctrl+Shift+G**). Adding the playing station to favorites is **Ctrl+Shift+F**.

### The favorites tree, step by step

1. Press **Alt+F** to put focus in the tree.
2. Arrow **Up** and **Down** to move. **Right arrow** opens a folder and **Left arrow** closes it.
3. Press **Enter** on a station to play it. Press **Enter** on the playing station to stop it.
4. Press **Space** on the station that is playing to pause or resume it, when what is playing can be paused. Live radio cannot be paused.
5. Press **F2** to rename a station or folder. A blank station name restores the directory's own name.
6. Press **Delete** to remove a station. A confirmation asks first.
7. Press **Ctrl+Up** or **Ctrl+Down** to change the volume without leaving the tree.
8. Press **Shift+F10** or the Applications key for the full menu of actions.

On a **station**, the menu offers: **Play** (or **Stop**), **Station Details...**, **Rename...** (F2), **Move Up** (Alt+Shift+Up), **Move Down** (Alt+Shift+Down), **Move to Folder...**, **Remove...** (Delete), **New Folder...** (Ctrl+Shift+E), **Mark for Move**, and **Manage Favorites...**. Once a station is marked, **Move Marked Above** and **Move Marked Below** appear too.

**Station Details...** opens a readout you can review and copy: the station's source, stream, format and country.

On a **folder**, the menu offers: **Rename Folder...** (F2), **Sort This Folder...**, **Delete Folder...**, **New Folder...** (Ctrl+Shift+E), and **Manage Favorites...**.

### Put your favorites in your own order

1. Arrow to a station.
2. Press **Alt+Shift+Up** or **Alt+Shift+Down** to move it one place within its folder. Quill Radio says where it landed, naming the station it passed.
3. If the list was sorted A to Z, the first move switches to your own manual order and says "Switched to manual order". Your stored order is never overwritten by a sorted view.

For a long move:

1. Arrow to the station you want to move. Press **Shift+F10** and choose **Mark for Move**.
2. Arrow to the station it should sit beside, even in another folder.
3. Press **Shift+F10** and choose **Move Marked Above** or **Move Marked Below**. The station moves there and joins that folder.

**View > Sort Favorites** chooses the order for the whole list: **Ascending (A to Z)** (Ctrl+Alt+Shift+F4, the default), **Descending (Z to A)** (Ctrl+Alt+Shift+F5), or **Unsorted (manual order)** (Ctrl+Alt+Shift+F6). The menu marks the current one as checked.

**View > Expand All Folders** (Ctrl+Alt+E) and **View > Collapse All Folders** (Ctrl+Alt+Shift+E) open or close every folder at once.

### Play a favorite without the list

- **Alt+1** through **Alt+0** play favorites 1 to 10, in the order the tree shows them. You should hear "Playing favorite 1" and the station's name. If there is no favorite in that slot, you hear how many you have.
- **Alt+Shift+F** opens **Play Favorite Station**, a numbered list of every favorite:
  1. Press **Alt+Shift+F**. The list opens with the prompt "Choose a favorite station to play:".
  2. Arrow to a station, or type its number.
  3. Press **Enter**. It plays. Escape closes the list without playing anything.
- **Ctrl+L** is **Play Last Station**: whatever you last had on, with no navigation.
- **Station > Recently Played** lists your last nine stations, newest first. **Alt+Shift+1** plays the newest, from inside that menu.

### The status bar

The status bar runs along the bottom of the main window. It is a row of cells that lead with actions:

1. **Play**, which reads **Stop** while something plays.
2. **Mute**, which reads **Unmute** while muted.
3. **Volume**, with the level, and "boosted" when Volume Boost is on.
4. **Record Now**, which reads **Stop Recording** with the time while a recording runs.
5. **Sleep timer**, with the time left, or "Off".
6. **Time**, the current time.

To use it:

1. Press **F6**. Focus moves into the bar. You should hear "Status bar" and the cell's name, such as "Play (Ctrl+P)".
2. Press **Right arrow** or **Left arrow** to move from cell to cell. **Home** and **End** jump to the first and last cells.
3. Press **Enter** or **Space** to press the cell you are on. On **Volume**, Enter mutes or unmutes. On **Sleep timer**, Enter opens the Sleep Timer. On **Time**, Enter speaks the full date and time.
4. Press the **Applications key** or **Shift+F10** for the cell's menu. Every cell's menu starts with **Activate** and ends with **Hide Status Bar**. In between:
   - **Play**: Play or Stop, Pause or Resume, Mute/Unmute, Play Favorite Station..., Recently Played, Record Now, Schedule Recording..., Recording Settings..., Stop All Recordings (when two or more are running), and Browse Stations....
   - **Mute** and **Volume**: Volume Up, Volume Down, Mute/Unmute, Volume Boost, Output Device..., and Sound Enhancements....
   - **Record**: Record Now or Stop Recording, Stop All Recordings (when two or more are running), Schedule Recording..., Recordings..., and Recording Settings....
   - **Sleep timer**: Sleep Timer... and Wake-Up Timer....
5. Press **F6** again, or **Escape**, to return to the favorites tree. You should hear "Returned to favorite stations."

To hide or show the whole bar, press **Ctrl+Shift+Alt+B** (**View > Show Status Bar**).

### What the status line is telling you

The Now playing line, the tray tooltip and the Playback menu's first row say one thing for each state a stream can be in. The words differ on purpose, because only some of these states are your doing:

| What it says | What is happening |
|---|---|
| `Radio: stopped` | Nothing is playing. |
| `Radio: connecting to WQXR...` | A station you just chose is being opened. |
| `Radio: buffering WQXR...` | It was playing and ran out of audio. The stream is refilling, and usually comes back within a few seconds. |
| `Radio: playing WQXR` | Playing. "(muted)" is added when muted. |
| `Radio: paused - WQXR` | You paused a recording, podcast, file or video. |
| `Radio: Reconnecting to WQXR. Attempt 2 of 3.` | The stream dropped and Quill Radio is getting it back. Each attempt is spoken as well as shown, so a long wait never sounds like a hang. There are three attempts, after two, five and fifteen seconds. |
| `Radio: could not play WQXR - ...` | It failed, with the reason. |

**Buffering** means the stream is still there and the audio ran out for a moment. **Reconnecting** means the connection went away and is being rebuilt.

## Go To: one key for every place

Press **Ctrl+G** in the main window (**View > Go To...**) and a short numbered list of places opens. Press the number and you are there.

1. Press **Ctrl+G**. The Go To list opens with focus in the list.
2. Press a number key, **1** to **9**, or **0** for the tenth place. That place opens at once.
3. Or arrow to a row and press **Enter**.
4. Press **Escape** to close the list. Focus returns exactly where it was.

The default list:

| Key | Place | Its own shortcut |
| --- | --- | --- |
| 1 | Favorites (the main window) | none |
| 2 | Browse Stations | Ctrl+B |
| 3 | The Player | Ctrl+Shift+G |
| 4 | Recordings | Ctrl+Shift+R |
| 5 | Downloads | Ctrl+Shift+J |
| 6 | Manage Favorites | Ctrl+Shift+M |
| 7 | Song History | Ctrl+Shift+H |
| 8 | Listening Statistics | Ctrl+Shift+Q |
| 9 | Find Stations | Ctrl+F |
| 0 | Preferences | Ctrl+, |

**The numbers never change on their own.** Recordings is 4 today and 4 next year, whether or not it is open. That is what Ctrl+1 to Ctrl+9 cannot do: those reach the windows you have open, in the order you opened them.

Each row also shows that place's own shortcut, where the list has one. Use Go To for a month and you may find you no longer need it.

### Go To Settings, step by step

Go To Settings chooses which places are in the list and in what order.

1. Press **Ctrl+G** to open Go To.
2. Press **Tab** to the **Settings...** button and press **Space**. Go To Settings opens.
3. The first list, **In the menu** (Alt+I), holds the places in the list, numbered. Arrow to one.
4. Press **Tab** to **Move Up** or **Move Down** and press **Space** to move it. Quill Radio says its new number.
5. To take a place out, select it and choose **Remove** (Alt+R). It moves to the second list.
6. The second list, **Not in the menu** (Alt+N), holds places you can add: Scheduled Recordings, Station Catalog Status, Audio Health, Keyboard Shortcuts, and What's Playing. Select one and choose **Add** (Alt+A).
7. Choose **OK** to save. You should hear "Go To menu saved."

The list holds ten places, because the number row has ten keys. Asking for an eleventh says so and suggests removing one first.

**An update never renumbers your list.** A place added in a later version waits in "Not in the menu" until you add it.

Inside Go To, use **Space**, not Enter, on the **Settings...** and **Close** buttons. Enter always goes to the highlighted place.

## Windows, and moving between them

Quill Radio's bigger surfaces open as their own windows, not dialogs:

- Browse Stations
- Search Stations (its title is "Internet Radio")
- Manage Favorite Stations
- Schedule Recording
- Radio Recordings
- Song History
- Now Playing
- The Player
- Tutorials

Several things follow:

- **Each one is a real window.** It stands on its own in the taskbar and the Alt+Tab order, not glued on top of the main window.
- **Each one carries a menu bar**, so Alt reaches menus in every one of these windows.
- **The main window stays reachable.** You can keep several windows open and work across them.
- **They close the way windows close:** Escape, Ctrl+W, Ctrl+F4, Alt+F4, or the title bar. There is no Close button on them.
- **Asking for a window that is already open brings it to the front** instead of opening a second copy.

Smaller dialogs, such as Downloads, Go To, Preferences and Sound Enhancements, are ordinary dialogs. They have no menu bar and close with Escape.

### Move between windows, step by step

1. Press **Ctrl+Tab** to go to the next open window, or **Ctrl+Shift+Tab** to go to the previous one. It wraps around.
2. Press **Ctrl+1** through **Ctrl+9** to jump straight to the first through ninth open window.
3. Or press **Alt+W** to open the **Window** menu. It lists every open window, numbered in the order you opened them. Arrow to one and press Enter.

Moving to a window puts focus on the control you last used there, or on the window's main control the first time. Closing a window puts focus back in the window you came from.

If you want spoken cues as windows open and close, turn on **Announce dialog transitions (more spoken detail)** in Preferences. Quill Radio then says "Entered ..." and "Exited ...". It is off by default.

## Menus

The main window's menu bar, from left to right: **Station** (Alt+S), **Edit** (Alt+E), **View** (Alt+V), **Playback** (Alt+P), **Audio** (Alt+A), **Video** (Alt+D), **Record** (Alt+R), **Community** (Alt+C), **QuillVille** (Alt+Q), **Help** (Alt+H) and **Window** (Alt+W).

Every menu item shows its own shortcut. If you rebind a key, the menu shows your key. This chapter lists every item, in menu order, with its default key. Most items have a walkthrough in their own chapter.

### Station menu (Alt+S)

- **Browse Stations...** (Ctrl+B) -- the tree of every source. See "Browse Stations".
- **Update Radio Reading Services...** (Ctrl+Alt+F10) -- refreshes the Radio Reading Services list from the RadioBrowser directory and says how many services it found. The bundled list stays as the fallback. Off in Safe Mode.
- **Search Stations...** (Ctrl+F) -- the field-based search window, titled "Internet Radio". See "Search Stations".
- **Add Custom Station...** (Ctrl+N) -- save any stream address under your own name. See "Adding your own stations".
- **Add YouTube Link...** (Ctrl+Alt+N) -- file any YouTube link under Browse Stations, YouTube.
- **Add from YouTube Playlist...** (Ctrl+Shift+Y) -- turn videos from a playlist into favorites.
- **Import YouTube Subscriptions...** (Ctrl+Alt+Shift+Y) -- follow every channel in a Google Takeout file.
- **Repair YouTube Support...** (Ctrl+Alt+Y) -- emergency repair: fetch the newest YouTube helper.
- **Find Streams from a Website...** (Ctrl+Alt+S) -- scan a station's web page for its stream.
- **Search Sources...** (Ctrl+Alt+Shift+U) -- choose which directories Search Stations asks.
- **Choose Browse Sources...** (Ctrl+Shift+Alt+O) -- choose which branches Browse Stations shows.
- **Update Station Catalog** (Ctrl+Alt+Shift+G) -- refresh the station catalog on this computer now.
- **Connect to Spotify...** (Ctrl+Alt+P) and **Browse Spotify...** (Ctrl+Alt+O) -- only when the experimental Spotify feature is on. See "Spotify (experimental)".
- **Manage Favorites...** (Ctrl+Shift+M) -- the Manage Favorite Stations window.
- **Add Playing Station to Favorites** (Ctrl+Shift+F) -- saves what is playing. When the playing station is already a favorite, the same item removes it, and its label says so.
- **Quick Actions...** (Ctrl+Alt+Q) -- the order of actions on the Browse Stations right-click menu.
- **New Folder...** (Ctrl+Shift+E) -- a new favorites folder, wherever you choose.
- **Import Stations from Playlist...** (Ctrl+I) -- read stations from an M3U, M3U8, PLS, XSPF or ASX file.
- **Export Favorites to Playlist...** (Ctrl+Shift+X) -- write your favorites to an M3U file.
- **Back Up Stations and Settings...** (Ctrl+Shift+U) and **Restore from Backup...** (Ctrl+Alt+Shift+W) -- see "Backing up and restoring".
- **Play Last Station** (Ctrl+L) -- whatever you last had on.
- **Recently Played** -- a submenu of your last nine stations, newest first. Inside it, **Alt+Shift+1** plays the newest. It reads "(none yet)" when empty.
- **Play Favorite Station...** (Alt+Shift+F) -- a numbered list of every favorite. Present when you have favorites.
- **Resume Last Station on Launch** (Ctrl+Alt+L) -- a check item. When checked, launching Quill Radio plays your last station. Off by default.
- **Start Quill Radio with Windows** (Ctrl+Alt+W) -- a check item. Quill Radio opens by itself when you sign in to Windows. It adds an entry for your own account only and needs no administrator rights. Not available in a portable copy.
- **Download Preferences...** (Ctrl+Alt+Shift+D) -- where downloads are saved and how they are filed.
- **Preferences...** (Ctrl+,) -- see "Preferences".
- **Send to Tray** (Ctrl+W) -- hides every Quill Radio window. Playback and recordings continue, and the tray icon stays. You should hear "Quill Radio is still running in the system tray."
- **Exit** (Ctrl+Q) -- quits Quill Radio at once, even during a recording. See "Closing Quill Radio".

### Edit menu (Alt+E)

- **Undo Last Action** (Ctrl+Z) -- brings back the last destructive thing you did. See "Taking back the last thing you did".

### View menu (Alt+V)

- **Listening Statistics...** (Ctrl+Shift+Q) -- how long you listened, and to what.
- **Show Station Details** (Ctrl+D) -- a check item, on by default. Shows or hides the read-only details box in Browse Stations and Search Stations.
- **Show Status Bar** (Ctrl+Shift+Alt+B) -- a check item, on by default.
- **Sort Favorites** -- a submenu: **Ascending (A to Z)** (Ctrl+Alt+Shift+F4), **Descending (Z to A)** (Ctrl+Alt+Shift+F5), **Unsorted (manual order)** (Ctrl+Alt+Shift+F6). The current order reads as checked. It is the same setting as in Preferences.
- **Expand All Folders** (Ctrl+Alt+E) and **Collapse All Folders** (Ctrl+Alt+Shift+E) -- every folder in the favorites tree at once.
- **Downloads...** (Ctrl+Shift+J) -- the download queue.
- **Go To...** (Ctrl+G) -- the numbered list of places.
- **Station Catalog Status...** (Ctrl+Alt+Shift+S) -- what is stored on this computer.
- **Audio Health...** (Ctrl+Alt+Shift+M) -- can this installation play and record?
- **Choose Columns...** (Ctrl+Alt+Shift+C) -- what each row says in Find Stations and Recordings.
- **Customize Features...** (Ctrl+Alt+C) -- turn the Record menu off if you never record.
- **Main Window Shows** -- a submenu of five views: **Favorite stations** (Ctrl+Shift+1), **Browse Stations** (Ctrl+Shift+2), **Search Stations** (Ctrl+Shift+3), **Radio Recordings** (Ctrl+Shift+4) and **Player** (Ctrl+Shift+5).
- **Text Size** -- a submenu: **Normal** (Ctrl+Alt+1), **Large** (Ctrl+Alt+2), **Larger** (Ctrl+Alt+3). Scales the main window's text. Remembered.

### Playback menu (Alt+P)

- A dimmed first row shows what is playing, such as "Radio: stopped".
- **Play** (Ctrl+P) -- reads **Stop** while something plays and **Resume** while something is paused, the same three words as the main window's transport button, which it presses. From idle, it plays the favorite selected in the tree.
- **Pause** (Ctrl+Space) -- reads **Resume** while paused. It holds a podcast, a recording, a downloaded or local file, or a finished video, and picks it up where it was. On a live station it is dimmed and says why: live radio is going out now, so there is nothing to hold.
- **Rewind 30 Seconds** (Ctrl+Shift+Left), **Forward 30 Seconds** (Ctrl+Shift+Right) and **Back to Live** (Ctrl+Shift+L).
- **Continue Listening...** (Ctrl+Alt+Shift+L) -- everything you started and did not finish.
- **Chapters...** (Ctrl+Shift+C), **Next Chapter** (Ctrl+Shift+.) and **Previous Chapter** (Ctrl+Shift+,).
- **Transcript...** (Ctrl+Shift+T) -- read what a video says.
- **Play Faster** (Ctrl+Shift+Up), **Play Slower** (Ctrl+Shift+Down) and **Normal Speed** (Ctrl+Shift+0).
- **Where Am I?** (Ctrl+Shift+W) -- position, length and chapter.
- **Go to Position...** (Ctrl+Alt+J) -- jump to an exact time.
- **Skip Silence** (Ctrl+Shift+9) -- shorten long pauses in something with a timeline.
- **Go to Player** (Ctrl+Shift+G) -- open the Player, or bring it to the front.
- **What's Playing?** (Ctrl+T) -- the Now Playing window.
- **Song History...** (Ctrl+Shift+H) -- what each station played earlier.
- **Sleep Timer...** (Ctrl+Shift+Z) and **Wake-Up Timer...** (Ctrl+Alt+Z).
- **Bookmark This Moment** (Ctrl+Alt+A).

The walkthroughs are in "Pausing, rewinding and moving around", "What's playing, and what played", "Timers" and "Bookmarks".

### Audio menu (Alt+A)

- **Mute/Unmute** (Ctrl+M).
- **Volume Up** (Ctrl+Up) and **Volume Down** (Ctrl+Down).
- **Volume Boost** (Ctrl+Shift+B) -- a check item. Up to 50 percent louder than full volume.
- **Output Device...** (Ctrl+Shift+D) -- which sound card or headset the radio uses.
- **Audio and Described Audio...** (Ctrl+Shift+A) and **Play Described Audio** (Ctrl+Alt+D).
- **Use One Volume for All Stations** (Ctrl+Alt+V) -- a check item, off by default.
- **Forget Every Station's Own Volume...** (Ctrl+Alt+Shift+V).
- **Announce Track Titles** (Ctrl+Alt+T) -- a check item, off by default.
- **Sound Enhancements...** (Ctrl+E) -- equalizer, compressor, channel mode, night mode and broadcast polish.

The walkthroughs are in "Volume and sound" and "Video, captions and described audio".

### Video menu (Alt+D)

The Video menu is always there. Its items say so when there is no picture to act on.

- **Show Video** (Ctrl+Shift+V).
- **Captions** (Ctrl+Shift+K) and **Caption Settings...** (Ctrl+Shift+Alt+T).
- **Video Information** (Ctrl+Shift+I).
- **Take a Snapshot** (Ctrl+Shift+Alt+H).
- **Full Screen** (F11).
- **Video Size** -- a submenu: **Fit** (Ctrl+Alt+4), **50%** (Ctrl+Alt+5), **100%** (Ctrl+Alt+6), **200%** (Ctrl+Alt+7). In this release, Fit gives the same size as 100%.

See "Video, captions and described audio".

### Record menu (Alt+R)

- **Record Now / Stop Recording** (Ctrl+R).
- **Record Station...** (Ctrl+Alt+R).
- **Stop All Recordings** (Ctrl+Alt+X).
- **Schedule Recording...** (Ctrl+Shift+S).
- **Recordings...** (Ctrl+Shift+R).
- **Recording Settings...** (Ctrl+Alt+Shift+I).

The Record menu disappears if you turn Recording off in Customize Features. See "Recording".

### Community menu (Alt+C)

- **Ask QUILL Radio...** (Ctrl+Shift+8) and **Use My ChatGPT Subscription...** (Alt+F5) -- a conversation that already knows what is playing, on the ChatGPT plan you pay for.
- **ACB Media Schedule...** (Ctrl+Shift+N), **What Is On Now** (Ctrl+Alt+H), **Upcoming...** (Ctrl+Alt+Shift+F) and **Refresh the Schedule** (F5).
- **ACB Media Podcasts...** (Ctrl+Alt+I).
- **Community Picks...** (Ctrl+Alt+0) and **Suggest a Station or Podcast...** (Ctrl+Alt+9).

See "The ACB Media schedule", "Reminders and Upcoming" and "The Community menu".

### QuillVille menu (Alt+Q)

Opens the other apps in the family. Every row has an access letter, so **Alt+Q and then one letter** opens an app -- two single keys, nothing held down:

- **Open QUILL** -- Alt+Q, Q (or Ctrl+Alt+Shift+F7)
- **Open Quill Weather** -- Alt+Q, W (or Ctrl+Alt+Shift+F8)
- **Open Quill Converter** -- Alt+Q, V (or Ctrl+Alt+Shift+F9)

Each app keeps its letter as more of the family is released: C for Quill Cast, A for Audio Studio, I for Quill Inkwell.

The long chords are only defaults. Each row is a command named **QuillVille: Open** and the app, and you can give it any key you like in **Help > Keyboard Shortcuts...** (Ctrl+Alt+K). See "Keyboard access without chords".

### Help menu (Alt+H)

- **Command Palette...** (Ctrl+Shift+P).
- **Keyboard Shortcuts...** (Ctrl+Alt+K) -- the Keyboard Manager.
- **Global Hotkeys...** (Ctrl+Alt+G).
- **Recent Problems...** (Ctrl+Alt+Shift+P).
- **Quiet Hours...** (Ctrl+Alt+Shift+Z).
- **Bookmarks...** (Ctrl+Alt+Shift+J).
- **Export My Setup...** (Ctrl+Alt+Shift+X) and **Import My Setup...** (Ctrl+Alt+Shift+N).
- **Keyboard Shortcuts Sheet...** (Ctrl+Alt+Shift+K).
- **Get Help from Support...** (Ctrl+Alt+F2).
- **Repair FFmpeg...** (Ctrl+Alt+F) and **Repair mpv Playback Engine...** (Ctrl+Alt+M) -- emergency repair tools, for when a bundled tool has gone missing. Everything ships inside Quill Radio, so you should never need them.
- **What Is This?** (F1) -- help for the window you are in and the control that has focus.
- **Tutorials...** (Ctrl+Alt+F1).
- **User Guide** (Ctrl+F1), **Release Notes** (Shift+F1) and **Product Requirements...** (Alt+Shift+F1). Each opens in your web browser.
- **Check for Updates...** (Ctrl+Alt+U).
- **About Quill Radio** (Alt+F1) -- version and project address.

Three commands live only in the Command Palette: **Redeem Unlock Code...**, **Repeat Last Announcement** and **Announcement Self-Test...**. See "Help, updates and documents".

### Window menu (Alt+W)

Lists every open Quill Radio window, numbered in the order you opened them, each with its key: Ctrl+1 for the first, and so on. See "Windows, and moving between them".

### The menus in other windows

Every peer window has its own small menu bar: one menu of its own with **Close** (Ctrl+W), a **Station** menu, and a **Window** menu. The Station menu has **Browse Stations...** (Ctrl+B), **Search Stations...** (Ctrl+F), **Manage Favorites...** (Ctrl+Shift+M), **Recordings...** (Ctrl+Shift+R) and **Preferences...** (Ctrl+,). A window never lists itself.

**Alt+S is the Station menu in every window**, and **Alt+W** is always the Window menu. Each window's own menu has its own key:

| Window | Its own menu |
| --- | --- |
| Browse Stations | Browse (Alt+B) |
| Search Stations ("Internet Radio") | Go (Alt+G) |
| Player | Player (Alt+P) |
| Manage Favorite Stations | Favorites (Alt+F) |
| Radio Recordings | Recordings (Alt+R) |
| Schedule Recording | Schedule (Alt+D) |
| Song History | Songs (Alt+G) |
| Now Playing | View (Alt+V) |
| Tutorials | View (Alt+V) |

If an Alt key lands on a control instead of a menu, press **Alt** alone, then **Right arrow** or **Left arrow** to move across the menu bar.

## Browse Stations

Browse Stations (Ctrl+B) is one window with one large tree. Its first row is **Search All Sources...**. Below it, each top-level branch is a source. Expand a branch and its contents load on the spot. **Enter** plays the highlighted row. Nothing needs a key, an account or a sign-in.

### Open it and move around, step by step

1. Press **Ctrl+B** from any window. Browse Stations opens, or comes to the front if it is already open. Your screen reader reads the title, and focus is in the tree.
2. Browse Stations remembers the branch you were last in. The first time, focus is on **Search All Sources...**.
3. Press **Down arrow** to move from branch to branch. Nothing is fetched until you open one.
4. Press **Right arrow** to open a branch. You should hear "Loading" and the branch name. If it takes more than three seconds, it tells you it is still working.
5. Press **Down arrow** to move through what loaded. A folder says how many rows it holds, for example "France, 812 stations".
6. Press **Enter** on a station, episode or chapter to play it. Press **Enter** on the row that is playing to stop it.
7. Press **Shift+F10** or the Applications key for everything a row offers. See "What a row offers".
8. Press **Tab** to move past the tree: a read-only **details box** about the highlighted row, **Radio volume**, **Mute**, **Go to Player**, **Add to Favorites** (it reads **Remove from Favorites** on a row you have saved), and **Refresh**, which reloads the highlighted source from the internet.
9. Press **Alt+T** to jump back to the tree from anywhere in the window.
10. Press **Escape**, **Ctrl+W** or **Ctrl+F4** to close Browse Stations. The station keeps playing.

The details box follows the highlighted row. For a station it gives the source, stream, format and country. For a branch it says whether it answers from your catalog or asks the internet each time. Turn it off with **View > Show Station Details** (Ctrl+D) if you would rather not Tab past it.

The window's menu bar has **Browse** (Alt+B) with **Close** (Ctrl+W), **Station** (Alt+S) and **Window** (Alt+W).

### The branches, in order

After **Search All Sources...**, the branches are:

1. **Favorites** -- your own stations and folders.
2. **Popular Stations** -- ranked by votes over years.
3. **Trending Now** -- ranked by what is being listened to today.
4. **Recently Added or Changed** -- new stations, and ones whose address was just repaired.
5. **By Country** -- then by state or region, then stations. A country with no regions gives you its stations directly.
6. **By Language**.
7. **By Genre**.
8. **By Quality** -- by audio format.
9. **Weather / NOAA** -- the NOAA Weather Radio directory, state by state.
10. **ACB Media** -- ACB Media 1 to 10.
11. **Double Tap Live** -- the blind tech show's own 24-hour channel: talk, tech, music and the best of the Double Tap podcast, on air around the clock.
12. **NFB Radio** -- the NFB Radio Network.
13. **Radio Reading Services** -- services that read print aloud for blind and print-disabled listeners.
14. **Westwood One Sports** -- Westwood One's ten live event channels: during the NCAA tournaments, the NFL and other big events, each carries a different game.
15. **SomaFM**.
16. **TuneIn** -- TuneIn's own folder tree, from continent down to city.
17. **iHeart** -- **By City** first, then genres.
18. **Networks** -- well-known broadcasters, grouped by type.
19. **Community M3U (Music Genres)**.
20. **Xiph / Icecast Directory** -- off by default.
21. **SHOUTcast Directory** -- the live Top 500, then 313 genres.
22. **Live365** -- about 5,500 independent stations, A to Z.
23. **Quillin Sources** -- only when an installed Quillin contributes a source.
24. **Radio Paradise** -- including lossless FLAC.
25. **Podcasts (Apple)** -- your Subscriptions, then 16 national storefronts.
26. **Podcast Index**.
27. **Internet Archive**.
28. **LibriVox Audiobooks**.
29. **Project Gutenberg Audiobooks**.
30. **AudioPub (Community Audio)**.
31. **Audius (Independent Music)**.
32. **Mixcloud (Shows & DJ Sets)**.
33. **ccMixter (Creative Commons)**.
34. **My Servers** -- Icecast or SHOUTcast servers you add yourself.
35. **Television (iptv.org)**.
36. **YouTube** -- channels, playlists and videos you save.
37. **Explore (Wikidata)** -- off by default.

That is 35 sources. A new installation shows 33 of them, because Xiph and Wikidata start switched off. Quillin Sources appears only when something contributes to it. Turn branches on and off with **Choose Browse Sources** (see below).

More about some of them:

- **Weather / NOAA** lists the states, each with its transmitter count. Open a state for its transmitters, named with call sign, frequency and place, such as "KHB36 162.550 MHz Manassas". Enter plays the best available internet re-stream. The whole directory of 1,035 transmitters is bundled, so this branch works offline.
- **Radio Reading Services** has twenty vetted services bundled, including WRBH 88.3 Reading Radio, Sun Sounds of Arizona, CRIS Radio, the KPBS and WKAR reading services, ACB Media 1 to 5 and the NFB Radio Network. Play, favorite, record and schedule them like any other station.
- **iHeart** opens into **By City** (317 markets) and then genres. Each genre opens into A to Z letter folders of stations.
- **By Country, By Language, Trending Now** and **Recently Added or Changed** are views of the same community directory. Trending and Popular often disagree, on purpose.
- **Double Tap Live** is Double Tap's own round-the-clock channel -- the daily show where blind people talk tech, from Steven Scott and Shaun Preece at Accessible Media Inc., with talk, tech, music and the best of the podcast on air around the clock since 30 September 2026. One station, directly under ACB Media because it is made for exactly the listeners this radio is. What's Playing reads the segment or song the stream announces; favorite, record and schedule it like any station.
- **Westwood One Sports** lists the network's own ten live event channels, Westwood One Sports channel 1 to channel 10 -- every stream Westwood One publishes. During a big event such as the NCAA basketball tournament, each channel carries a different game at the same time; the schedule at westwoodonesports.com says which game is on which channel. Between events a channel may be silent. Favorite, record and schedule them like any station: a recording scheduled on channel 3 records whatever game channel 3 carries at that time. Rights can keep a game off the internet, and the channel then says so.
- **Networks** groups well-known broadcasters: public broadcasters such as the BBC, NPR, CBC, ABC Australia, Radio France and Deutschlandfunk, plus US news and talk, sports, music, and syndicators. A syndicator such as Westwood One has no single stream, so it opens a search across its affiliate stations, and the label says so.
- **SHOUTcast Directory** starts with **Top 500 (most listeners right now)**, then 313 genres. Each genre is sorted by live listeners, most first. SHOUTcast returns at most 500 stations per genre. A SHOUTcast station takes a moment to start, because its address is looked up when you press Enter. If it cannot be resolved, it says so.
- **Live365** is arranged A to Z. Names that start with a number or symbol are under **#**. The whole list is fetched once a day, so opening a letter costs no wait.
- **Radio Paradise** lists each channel once per quality: 320k AAC first (what Enter lands on), then 192k MP3, 128k AAC, 64k and 32k AAC+, and FLAC last because it is lossless and the heaviest.
- **Podcasts (Apple)** starts with **Subscriptions**, then storefronts such as United States, United Kingdom, Ireland, Japan and Brazil. A storefront holds Top Podcasts, Top Episodes and Apple's genre tree. Opening a show reads the publisher's own feed. See "Podcasts in Browse Stations".
- **Podcast Index** offers **Trending Now**, **By Category** (112 categories) and **Search the Podcast Index...**. You can open any show without subscribing.
- **Internet Archive** offers Old Time Radio, Audiobooks & Poetry, the Live Music Archive, Radio Programs, News & Public Affairs and more. A folder with more than one page ends with **More...**. An item that publishes no rights information says so.
- **LibriVox Audiobooks** offers **Recently Added**, **By Genre** (43 genres) and **By Author**, A to Z. A book with chapters is a folder of chapters.
- **Project Gutenberg Audiobooks** offers All Audiobooks, twelve topics and eight languages, with a "More audiobooks" row to page on.
- **AudioPub (Community Audio)** has one shelf, **Discover**: a random fifty, different every time. Nothing from AudioPub is stored on this computer.
- **Audius** offers Trending Now and 27 genres, and leaves out pay-gated tracks. **Mixcloud** lists DJ sets and radio shows; a Mixcloud row opens on Mixcloud in your browser, and the row says so before you press Enter. **ccMixter** is Creative Commons music by tag, with each track's licence on its row.
- **Explore (Wikidata)**, when you turn it on, offers **By City**, **By Format** and **On the Dial** by FM band. Rows say "from Wikidata". The streams still come from Radio Browser.

**Numbers in names sort like numbers.** "ACB Media 1, 2, 3 ... 10", not "1, 10, 2".

**Some branches remember where you stopped.** A LibriVox chapter, an Old Time Radio episode or a podcast episode keeps your place as you listen. A few seconds in is not kept, and finishing something clears its place.

**A branch that is slow says so, and a branch that is broken says that.** An empty branch tells the two kinds of empty apart: "Nothing in here" is an answer, while "Could not be reached. Open it again to try." means try later. From the second failure in a row it adds a count, such as "It has failed 3 times in a row -- the directory itself may be down. You can hide it in Browse Sources." Quill Radio never switches a source off for you.

**The tree reads ahead.** Land on a closed folder and Quill Radio quietly starts fetching what is inside, so the expand you were about to make opens at once. Safe Mode fetches nothing.

### What a row offers

Press **Shift+F10** or the Applications key on any row.

On a **station, episode, chapter or video**, in this order:

- **Play**, or **Stop** if it is playing. A downloaded file offers **Play** or **Pause**, then **Stop**.
- **Add to Favorites** or **Remove from Favorites**.
- **Station Details...** -- speaks the details.
- **Copy Stream Link** (or **Copy Link** for a recording).
- **Rename Favorite...** -- only on a saved row. A blank name restores the directory's own.
- **Open Website** -- when the station has a home page.
- **Download...** or **Remove Download** -- where the source allows saving.
- **Record This Station...** and **Schedule Recording...** -- on a live station. Both are filled in with this row's station.
- On an episode of a show you follow: **Mark Episode as Played** (or **as Unplayed**), **Play Next in QUILL Cast**, **Add to QUILL Cast Queue** and **Send to the QUILL Cast Inbox**.
- **Report Bad Station...** -- on a live station.
- On the row that is playing, when it has a timeline: **Previous Chapter**, **Next Chapter**, **Chapter List...**, **Captions On or Off**, **Where Am I?**, **Speed Up**, **Slower** and **Back to Normal Speed**, each with its key.
- **View Transcript...** -- on podcast episodes and YouTube rows.
- **Remove from YouTube** and the three **Add a ...** items -- on a saved YouTube video.
- **Set a Reminder...**, or **Remove Reminder** once it has one. Always last.

On a **folder**:

- **Open** or **Close**, and **Refresh**.
- On a podcast show: **Subscribe to This Podcast** or **Unsubscribe from This Podcast**, and **Copy Feed Address**. A show you follow adds **Move to Folder...**, **Mark All as Played...**, **Download All Episodes...** and **Remove All Downloads...**.
- **Add All ... to Favorites**, once its rows have loaded.
- **Add This Place to Favorites** (or **This Show**), on a folder below the top level.
- **Download All ... Files...**, on a book or collection you may save.
- **Close Search Results**, on a Search Results branch.
- On a top-level source: **Search This Source...** (where the source can be searched), **Source Options...** (where it has options), **Hide This Source** and **Reset Sources to Default**.

A dimmed item says why it is dimmed. See "Why a menu item is dimmed".

**Delete** removes the row you are on, when it is yours to remove: a saved YouTube video, playlist or channel, a server you added, or a favorite. It asks first, names the row, and **No** is the default. The question has a **Don't ask me again** box. On a top-level source such as Podcasts, Delete hides the source, the same as **Hide This Source** on the context menu; **Reset Sources to Default** brings it back. On a folder inside one of Quill Radio's own sources, Delete explains that there is nothing to delete.

### Find in this folder, step by step

Above the tree is a search box that searches from the folder you are on, downward.

1. In the tree, highlight the folder you want to search, such as one iHeart genre, one state, or a podcast show.
2. Press **Ctrl+F**. Focus moves to the **Find in this folder** box (Alt+I) and you should hear "Find in this folder."
3. Type what you want and press **Enter**.
4. The matches replace the folder's contents, and focus moves to the first match. You should hear how many matched.
5. Press **Escape** in the box, or erase the text, to go back to the folder you searched from.

Find takes the fastest route for where you are standing, and says which it took:

- On **Podcasts**, it asks the real podcast search engine. Shows come back as folders you open straight into episodes.
- On **By Country, By Language, By Genre** and **By Quality**, it answers at once from the catalog on this computer, scoped to where you are. Find "jazz" while on France and you get France's jazz stations, online or off.
- On **LibriVox**, the **Internet Archive**, **TuneIn**, **iHeart**, **NOAA** (by call sign, SAME code, or "County, ST"), **Project Gutenberg**, **SomaFM**, **Audius**, **Mixcloud** and **ccMixter**, it uses that source's own search.
- On a **podcast show**, it searches the episodes, including their show notes.
- Elsewhere it walks the folder, within limits, and says if it showed only the first results.

If you type a **web address** instead of a name, Find scans that website for its stream, wherever you are standing. See "Find a station by its web address".

### Search All Sources, step by step

**Search All Sources...** at the top of the tree asks every directory at once.

1. Press **Ctrl+B**, then **Home** to go to **Search All Sources...**.
2. Press **Enter**. A box opens: "What are you looking for? Every source is searched at once."
3. Type a name, a call sign or a genre and press **Enter**.
4. You should hear that it is searching. After about four seconds it says "Still searching" and keeps saying so until the answer arrives.
5. The answer appears as a **Search Results** branch under Search All Sources, with focus on it. Open it and arrow through the results.
6. To close the results, press **Delete** on the Search Results branch, or choose **Close Search Results** from its menu. Nothing is lost.

Worth knowing:

- **The whole search is capped at eight seconds.** Any source that did not answer in time is named in the results, such as "Internet Archive did not answer within 8 seconds". Search again and it is usually there.
- **Searching the same thing twice is instant.** Answers are remembered for ten minutes, while a fresh search runs behind and replaces them.
- **You can start one from the Find box.** On Search All Sources, or inside its results, press Ctrl+F, type and press Enter. That runs the search across all sources.
- **Search All Sources asks every directory**, including branches you have hidden from the tree.
- **Opening Browse Stations warms up the first search.** It quietly fetches the three directories that keep their whole list in a local cache (Live365, Radio Paradise and SHOUTcast's genre list), once per run. Safe Mode skips this.

### Find a station by its web address

No directory carries every station. OJ 99.1 (WWOJ, Avon Park, Florida) is in neither TuneIn nor RadioBrowser, so no spelling of its name finds it. Its website has the stream on it.

1. Press **Ctrl+B**, then **Ctrl+F** to reach the Find box. (Search All Sources and the Search Stations window work too.)
2. Type the station's web address as you would in a browser, such as `oj991.com`. You do not need `https://`.
3. Press **Enter**. Quill Radio fetches that one page and finds the stream its player uses.
4. You should hear that one stream was found. A **Website** row appears, named for the station. Play it, favorite it or right-click it like any other row.

This is a scan of one page, not a web search. Type something that is not an address, such as "jazz", and it searches the directories as usual. An address that has no stream gets "Nothing found on that website."

### Podcasts in Browse Stations

1. Press **Ctrl+B**, arrow to **Podcasts (Apple)** and press **Right arrow**. The first folder is **Subscriptions**, then the storefronts.
2. Open a storefront, then **Top Podcasts**, or a genre.
3. Arrow to a show and press **Right arrow** to open it. Its episodes load from the publisher's own feed.
4. Press **Enter** on an episode to play it.
5. To follow the show, go back to the show's row, press **Shift+F10** and choose **Subscribe to This Podcast**. It is filed in the podcast library shared with Quill Cast, so it is there the next time Cast opens.
6. Your shows appear under **Subscriptions**, one folder each, with the newest episodes. The Subscriptions folder shows your count, such as "Subscriptions (3)", and each show shows its unheard count, such as "(2 unheard)".

Worth knowing:

- An episode whose feed publishes a transcript says "transcript available". **View Transcript...** on its menu opens it without playing anything.
- How many episodes each show lists is set in Preferences: **Episodes listed per subscribed podcast**, 25 newest by default.
- A show you follow has housekeeping on its menu: **Move to Folder...**, **Mark All as Played...** (with a "Don't ask me again" box shared with Quill Cast), **Download All Episodes...** and **Remove All Downloads...** (files go; the subscription stays).
- Finish an episode here and the show's unheard count drops at once.
- When Subscriptions is empty it offers **Add a Podcast by URL...**, **Import Podcasts from OPML...** and **Search for a Podcast...**.
- **Export Podcasts to OPML...** (from 3.0.4) is on the menu of the **Subscriptions** folder and of the **Podcasts (Apple)** branch, beside Import. It writes every show you follow, folders included, to an OPML file, the format every podcast app reads, and says how many it wrote, for example "Exported 12 podcasts to quill-radio-podcasts.opml." It is the same file Quill Cast's Subscriptions > Export OPML writes, so nothing is lost between the two.
- The rich side of podcasting, such as automatic downloads, retention and the play queue, is Quill Cast's job.

To check your shows for new episodes, see "Checking your subscribed podcasts".

### Saving episodes, books and tracks

Where a source's terms allow it, you can keep a copy.

1. In Browse Stations, highlight a book chapter, an archive recording, a Creative Commons track or a podcast episode.
2. Press **Shift+F10** and choose **Download...**. It joins the download queue, and you can keep listening.
3. On a book's folder, choose **Download All Files...** to save every chapter into one folder, in order.
4. Press **Ctrl+Shift+J** to open **Downloads** and follow progress.

Where saving is not offered, asking says why, and the reasons differ. A **live station** has no file to save (use Record Station instead). **Spotify** is copy-protected. **YouTube** is excluded on purpose. For **Audius**, the choice belongs to the artist. A Creative Commons track is saved with its licence in a small text file beside it.

A downloaded book plays like a book. Chapters play in order (chapter 2 before chapter 10), each starts on its own, and Quill Radio says where you are, such as "4 of 40". At the end of the last chapter it says so.

### The Downloads window, step by step

1. Press **Ctrl+Shift+J** (**View > Downloads...**). Downloads opens with focus in the list. A heading above it sums up the queue.
2. Arrow through the list. Each row says what it is and where it has got to: waiting, downloading, saved or failed.
3. Press **Enter** on a saved row to open its folder in File Explorer. The button **Open Containing Folder** does the same.
4. Tab to the buttons: **Cancel This One**, **Remove From List**, **Clear Finished**, **Clear All**, and **Preferences...** (which opens Download Preferences). None of them deletes a file already on your disk.
5. Press **Escape** to close Downloads. Downloads keep going.

If you send Quill Radio to the tray with downloads still going, it either finishes them in the background or stops them, as Download Preferences says, and tells you which.

Downloads are filed tidily. A podcast goes in a folder named for its show. A book gets its own folder. Once you have more than one book by the same author, that author gets a folder too. You can change all of this in Download Preferences.

### Download Preferences, step by step

1. Press **Ctrl+Alt+Shift+D** (**Station > Download Preferences...**). Focus is in **Downloads folder (blank uses the default)**.
2. Leave it blank for the default, or type a folder, or Tab to **Browse...** to choose one. The default is a Quill Radio folder inside your Downloads folder. In a portable copy it is the `Downloads` folder inside the portable folder.
3. Tab through the checkboxes and press **Space** to change any:
   - **A folder per podcast show** -- on.
   - **A folder per book** -- on.
   - **Group books by author once an author has more than one** -- on.
   - **Keep downloads going when the window closes to the tray** -- on.
   - **Ask where to save each download instead of filing it automatically** -- off. When on, a book asks once, not once per chapter.
4. A sentence below the checkboxes always says what will happen to the next thing you save.
5. Choose **OK** to save. Quill Radio reads back the new rules.

### YouTube in Browse Stations

YouTube needs no Google account and no sign-in.

1. Press **Ctrl+Alt+N** (**Station > Add YouTube Link...**). A box opens. If a YouTube link is on your clipboard, it is already filled in.
2. Paste a link and press **Enter**. It is filed by what it is: `@name` follows the channel, `@name/live` saves the live broadcast, a playlist link becomes a folder, and a video link becomes a row.
3. You should hear, for example, "Following that channel. Find it under Browse Stations, YouTube." A moment later it names what you added.
4. Press **Ctrl+B**, arrow to **YouTube** and open it. A channel opens into **Uploads** and the channel's playlists. A long channel pages with **More...**.
5. Press **Enter** on a video to play it. Videos play, record and can be favorited like a station.

Worth knowing:

- While the YouTube branch is empty it shows **Add a Channel...**, **Add a Playlist...** and **Add a Video...**. After that, those three live on the branch's menu (Shift+F10) and every row inside it.
- The first time you add or play anything from YouTube, Quill Radio asks once whether it may contact YouTube, and remembers the answer.
- A row takes the video's own name, with the channel and length spoken after it. The row is saved first, so a video whose details will not load is still saved and still plays.
- **View Transcript...** on any YouTube row fetches the captions and opens the transcript reader without playing anything.
- If a video will not play, Quill Radio offers to fetch the current YouTube helper. Say yes and it installs it, says the version, and plays the video. See "Repair YouTube Support".
- YouTube is unavailable in Safe Mode.

### My Servers, step by step

A church, school or community station running its own Icecast or SHOUTcast server is often in no directory at all.

1. Press **Ctrl+B**, arrow to **My Servers** and press **Right arrow**.
2. Arrow to **Add a Server...** and press **Enter**. A box opens. If an address is on your clipboard, it is filled in.
3. Type or paste the server's address, including its port number, and press **Enter**.
4. Quill Radio checks it before saving. You should hear, for example, "Added http://stream.example.org:8000. It has 4 stations." An address that answers with nothing is not saved, because that is nearly always a wrong address or a missing port.
5. Open the server's folder. Every stream appears with what is playing on it right now.

### Source Options, step by step

Two sources have options: Radio Paradise and the SHOUTcast Directory.

1. In Browse Stations, arrow to the top-level **Radio Paradise** or **SHOUTcast Directory** row.
2. Press **Shift+F10** and choose **Source Options...**.
3. A list opens. For **Radio Paradise Quality**, choose which quality comes first for each channel (320 kbps by default). For **SHOUTcast Stations to Show**, choose everything the directory lists (the default) or only stations someone is listening to now.
4. Press **Enter**. Quill Radio reads back your choice and reloads the branch.

### Choose Browse Sources, step by step

1. Press **Ctrl+Shift+Alt+O** (**Station > Choose Browse Sources...**). The Browse Sources window opens with focus in the **Branches** list.
2. Arrow through the list. Each row says its state first, such as "On. LibriVox Audiobooks. Public-domain audiobooks, by chapter." Rows are grouped: Yours, Stations, Accessibility, Spoken word, Music, Explore.
3. Press **Enter** or **Space** on a row to turn it on or off. You should hear the source's name and "on" or "off". The **Turn On or Off** button does the same.
4. **Turn On All** turns every source on. **Reset to Default** goes back to what a new installation shows.
5. Press **Escape** or choose **Close**. Your choice is already saved. If Browse Stations is open, it rebuilds at once and you hear "Browse Stations has been updated."

A branch that is off is not in the tree at all and is never contacted while you browse. A source added in a later version appears unless you hide it.

You can also prune from the tree itself: press **Delete** on a top-level branch, or press **Shift+F10** on it and choose **Hide This Source**. **Reset Sources to Default** is on the same menu.

## Search Stations

**Station > Search Stations...** (Ctrl+F) opens the field-based search. The window's title is **Internet Radio**. Go To calls it Find Stations.

### Search by name, tag and country, step by step

1. Press **Ctrl+F**. You should hear "Internet Radio", then the **Station name** field (Alt+M), where focus is.
2. Type a name, a frequency or a call sign, such as `WQXR` or `105.7`.
3. Press **Enter**. You should hear how many results arrived. Focus moves to the first result.
4. Arrow through the results. Each row names the station and the directory it came from, such as "via iHeart".
5. Press **Enter** on a result to play it. Press **Enter** again to stop it.
6. To keep it, Tab to **Add to Favorites** and press **Space**.
7. Press **Escape** to close the window. The station keeps playing.

To narrow the search:

- **Tag/genre** (Alt+T) and **Country** (Alt+O) are drop-down lists filled from the directory. Choosing one runs the search straight away.
- **Source** (Alt+U) narrows the results to one directory: All sources, Radio Browser, iHeart, TuneIn, Podcasts, SomaFM, ACB Media, Community M3U, Xiph, Spotify, YouTube or Website. It filters without searching again.
- **Category** (Alt+Y) switches the window to a list instead of a search: Favorites, Popular Stations, ACB Media, SomaFM, TuneIn, Music Genres, Xiph Directory or Search Results. The window opens on Favorites.
- In the **Station name** field, press **Down arrow** for the searches you ran before, newest first. Picking one restores the name, tag and country together. The list holds fifteen.
- When Radio Browser has more than 200 results, the **More Stations** button loads the next page and puts your cursor on the first new station.

Other controls, in Tab order after the results: a read-only **Station details** box, the status line, **Radio volume**, **Mute**, **Play** (reads **Stop** while the selected station plays), **Add to Favorites**, **More Stations**, **Add Custom Station...**, **Find Streams from a Website...** and **Refresh**. In the Music Genres category, Refresh re-reads the genre list. Shift+F10 on a result offers Play or Stop, Add to or Remove from Favorites, Open Website and Report Bad Station....

The window's menus are **Go** (Alt+G, with **Close**, Ctrl+W), **Station** (Alt+S) and **Window** (Alt+W). The Genre box's label also uses the letter G, so if Alt+G lands on the Genre box, press **Alt** alone and arrow to the Go menu.

### What a search does

- **It starts at home.** Matches from the station catalog on your own computer appear the moment you press Enter. The live directories add theirs behind them. A search still answers when the internet does not.
- **You do not have to spell it the directory's way.** `14.90 AM` finds 1490, `1009` finds 100.9, and `105-9` finds 105.9. A leading "play" or "listen to" is ignored. A trailing FM or AM does not throw it off. Naming the state helps: `Sunny 105.7 Gulf Shores Alabama` finds the station Radio Browser knows only as "WCSN 105.7 FM Orange Beach".
- **The list is ordered by what you most likely want.** A station matching name and frequency comes above one matching only the frequency. Between two equal matches, the one known to play comes first.
- **Weather radio geography works.** A six-digit SAME code, a call sign such as `KHB36`, "County, ST" or a state name also brings back NOAA Weather Radio transmitters. Reading services match by name, tag or state.
- **The libraries are searched too.** LibriVox, the Internet Archive, Project Gutenberg, Apple Podcasts, Audius, Mixcloud and ccMixter answer a moment after the stations. Quill Radio tells you once when they have all answered, and your place is kept if you are already arrowing. Enter on a podcast show plays its latest episode. A LibriVox book plays its first section. An Internet Archive collection says it opens on its own site.
- **A web address scans that site** for its stream. See "Find a station by its web address".
- Search is off in Safe Mode.

### Search Sources, step by step

Search Sources decides which directories Search Stations asks. There are twelve, all on by default: Radio Browser, TuneIn, iHeart, SomaFM, SHOUTcast, Live365, TV, Radio Paradise, NOAA Weather Radio, Radio Reading Service, Spotify and YouTube.

1. Press **Ctrl+Alt+Shift+U** (**Station > Search Sources...**). The Search Sources window opens with focus in the **Sources** list.
2. Arrow through the list. Each row says its state first, such as "On. TuneIn."
3. To change one, Tab to **Turn On or Off** and press **Space**. You should hear the source's name and "on" or "off".
4. **Turn On All** turns every source on. **Reset to Default** restores the defaults.
5. Press **Escape** or choose **Close**. Quill Radio says which sources it will search.

A source that is off is never contacted by Search Stations, so searching is faster and quieter. The libraries are not in this list.

## Adding your own stations

### Add Custom Station, step by step

1. Press **Ctrl+N** (**Station > Add Custom Station...**). Add Custom Station opens with focus in **Station name** (Alt+N).
2. Type the name you want to hear.
3. Tab to **Stream URL** (Alt+U) and paste the stream's address.
4. Optionally, Tab to **Homepage** (Alt+H) and **Tags** (comma-separated).
5. Tab to **Test** and press **Space** to play the stream before saving.
6. Choose **OK** (Enter) to save. You should hear that the station was added. If you already have it, you are told so.

If OK does nothing, a field is missing or wrong. The reason is in the status text above the buttons. It is not spoken on its own, so use your screen reader's command to read the whole window (Insert+B in NVDA and JAWS) to hear it.

Three kinds of link get extra help:

- **A YouTube link becomes a station.** A video link, a `youtu.be` short link or a channel's live page plays like a radio station. It sits in your favorites, records with Record Now, and can be scheduled. Quill Radio saves the page address and looks up the audio fresh every time, so a recording you schedule today still works next week. The YouTube helper, and the JavaScript engine YouTube needs, are built into the app; nothing downloads on first use. A private, removed, region-blocked or not-yet-live video says so in plain words.
- **A Live365 link is fixed for you.** A Live365 station page, a player link such as `player.live365.com/a25891`, or a bare station id is rewritten to the real stream address, and the dialog says so. Nothing is fetched to do this.
- **A SecureNet player link** (`securenetsystems.net/v5/...`) is saved as typed, because its stream must be read from the page. Use Find Streams from a Website with the link, or just save it and play it: the repair described below finds the stream.

Any other address is saved exactly as you typed it.

### When a station will not play

Some stations are listed with a dead address, often because the real stream sits behind a player on the station's own site. Instead of just failing, Quill Radio works down a short ladder:

1. It looks the address up again, for players that moved servers.
2. It refreshes the address from the directory.
3. If **Recover failed streams from the station's website** is on in Preferences (it is on by default), it scans the station's own website, follows a "Listen Live" link, and recognises Triton players there.

If it finds one clear stream, it plays it and remembers it for that favorite. If it finds several, it tells you the count, and you can choose one in Find Streams from a Website. It tries once per station per session, and not in Safe Mode.

### Find Streams from a Website, step by step

1. Press **Ctrl+Alt+S** (**Station > Find Streams from a Website...**). The window opens with focus in **Website address** (Alt+W).
2. Type or paste the station's page address and press **Enter**. The **Scan** button does the same.
3. When the scan finishes, the status line says how many streams it found. Press **Tab** to the **Candidates found** list. Each row gives the link and why it was flagged.
4. Arrow to a candidate. Tab to **Test** and press **Space** to hear it. The button reads **Stop Test** while it plays.
5. When you find the right one, Tab to **Use This Link...** and press **Space**. Add Custom Station opens with the link filled in. Name it and choose OK.
6. Press **Escape** to close the window.

Enter on the list does nothing; use the buttons.

It works for many stations whose Listen Live button is a JavaScript player. For Triton Digital and StreamTheWorld players, including the whole `player.listenlive.co` network, Quill Radio reads the station's call letters and looks up the real stream through the provider's own public service. Both the MP3 and AAC streams are offered when a station publishes both. It also recognises **iHeart** and **TuneIn** station pages, and **SecureNet** players, and offers their real stream first. A player page is never offered as something to play.

### Add from a YouTube playlist, step by step

1. Press **Ctrl+Shift+Y** (**Station > Add from YouTube Playlist...**). A box opens. A playlist link on your clipboard is already filled in.
2. Paste a playlist link (`youtube.com/playlist?list=...`) and press **Enter**. You should hear "Listing that playlist...", then how many videos it has.
3. A window titled "Add from YouTube Playlist" opens, headed with the playlist's own name. Focus is in the **Videos** list, in the uploader's order. Each row reads like "3. Introducing layers, 5 minutes 31 seconds, 3Blue1Brown".
4. Select what you want. Hold **Shift** or **Ctrl** with the arrow keys to select several.
5. Choose **Add Selected** (Alt+S), or **Add All** (Alt+A) for the lot.
6. You should hear how many were added, and how many were already in your favorites.
7. Press **Escape** to close the window.

Each video becomes an ordinary favorite you can play, record and schedule. This is an import, not a subscription: videos added to the playlist later are not picked up, and playing one video does not move on to the next. Run it again on the same link to collect new videos; ones you already have are skipped. A watch link that happens to carry `list=` is treated as that single video.

### Import YouTube Subscriptions, step by step

This follows every channel you subscribe to, from a file you export from Google. No account, sign-in or password is involved, and nothing is sent anywhere.

1. In a web browser, go to `takeout.google.com`. Choose **YouTube and YouTube Music**, narrow it to **subscriptions**, and download the archive.
2. Unzip it. The file you need is `YouTube and YouTube Music\subscriptions\subscriptions.csv`.
3. In Quill Radio, press **Ctrl+Alt+Shift+Y** (**Station > Import YouTube Subscriptions...**). An explanation opens. Choose **OK**.
4. A file window opens: "Choose your subscriptions.csv". Find the file and choose **Open**.
5. You should hear what happened, such as "Imported 24 channels; 3 you already followed". The channels appear under YouTube in Browse Stations.

It is a one-time import. Channels you subscribe to later appear when you export and import again. Channels you already follow are skipped. Rows that are not channels are skipped rather than failing the import.

Quill Radio cannot sign you in to YouTube Premium, and Premium's benefits do not carry over: YouTube's terms forbid a third-party app from background play or offline storage. Watch history cannot be brought across by any third-party app.

### Repair YouTube Support

This is an emergency repair. YouTube support is built in, but YouTube changes how it serves audio more often than Quill Radio ships releases.

1. Press **Ctrl+Alt+Y** (**Station > Repair YouTube Support...**).
2. You should hear "Updating YouTube support...".
3. A message says the new version, such as "YouTube support is now version ...", that the built-in version is already the newest, or that it could not be updated. Press Enter to close it.

It asks before it reaches the network and is off in Safe Mode. A repaired helper is used only while it is newer than the built-in one, so a later Quill Radio update never runs an older copy. You should not need it unless YouTube links stop playing.

### Import Stations from Playlist, step by step

Import reads **M3U**, **M3U8**, **PLS**, **XSPF** and **ASX** playlists. The "Listen Live" link a station gives you is often a PLS or XSPF file, and several reading services publish ASX.

1. Press **Ctrl+I** (**Station > Import Stations from Playlist...**). A file window opens: "Choose a playlist to import".
2. Find the file and choose **Open**.
3. The Import Stations window says how many stations it found and asks which folder they go into. Focus is in the **Folder** box.
4. Choose an existing folder from the list, or type a new path such as `News/Local`. It is created for you. "(Top level)" means no folder.
5. Choose **OK**.
6. If some stations are already in your favorites, Quill Radio says how many and asks whether to skip those or import everything.
7. You should hear how many stations were imported, and the folder they went into.

Station names come from the playlist itself. A bare address is named after its host. An M3U8 file that is really a live stream, not a list of stations, is recognised and refused. XSPF and ASX files are read safely: a file built to expand to gigabytes is refused out loud.

### Export Favorites to Playlist, step by step

1. Press **Ctrl+Shift+X** (**Station > Export Favorites to Playlist...**). A file window opens: "Export favorites to a playlist". The suggested name is `quill-radio-favorites.m3u`.
2. Choose a folder and a name, then choose **Save**.
3. You should hear, for example, "Exported 42 stations to quill-radio-favorites.m3u."

Export writes an **M3U** file, which almost every media player can open. Each station is written with the name you see and its stream address, so importing the file brings the same stations back. M3U has no folders, so the folder structure is not carried across. To export one folder, use **Export This Folder...** in Manage Favorite Stations.

## The Favorites Manager

**Station > Manage Favorites...** (Ctrl+Shift+M) opens **Manage Favorite Stations**, a full organizer. The main window's tree offers most of the same actions, so the Manager is for the heavy lifting.

### Organize your favorites, step by step

1. Press **Ctrl+Shift+M**. Manage Favorite Stations opens with focus in **Search favorites** (Alt+K).
2. To filter, type part of a name, country, language, tag or folder name. The list below narrows as you type into one flat list, and each station says its folder. Clear the box to see everything again.
3. Press **Tab** to the **Favorites and folders** tree. Arrow to a station or folder.
4. Press **Enter** to play a station. Press **Enter** on the playing station to stop it.
5. With focus in the tree, press **F2** to rename, **Delete** to remove (it asks first), or **Ctrl+Shift+E** for a new folder. These three keys work only while the tree has focus.
6. Press **Tab** to reach the buttons, in this order: **Play** (reads **Stop** while that station plays), **Remove**, **Move Up**, **Move Down**, **Move to Folder...**, **Mark for Move**, **Move Above**, **Move Below**, **New Folder...**, **Rename...**, **Delete Folder...** and **Remove All...**. Press **Space** on one to use it.
7. Press **Escape**, **Ctrl+W** or **Ctrl+F4** to close the Manager.

Some buttons share an Alt letter in this window, so use Tab to reach buttons rather than Alt keys.

### Folders

- **New Folder...** (Ctrl+Shift+E) asks where the folder lives, top level or inside another folder, then its name. It exists at once, even before a station is in it.
- **Move to Folder...** files the selected station. Choose "(Top level -- no folder)", an existing folder, or "(New folder...)". Type a path with `/`, such as `News/Morning`, to nest folders.
- **Rename** a folder (F2) and its subfolders come along.
- **Delete Folder...** asks first, with No as the default. Its stations step out to the top level. Nothing is ever deleted with a folder.

### Reordering

- **Move Up** and **Move Down** move a station within its folder.
- For a long move: select the station, choose **Mark for Move**, select the destination, then choose **Move Above** or **Move Below**. The station joins the destination's folder.
- If the list is sorted A to Z or Z to A, the first move switches to manual order and says "Switched to manual order". Your stored order is never overwritten.
- Quill Radio says where the station landed, naming its neighbour.

### Listening from a folder

Press **Shift+F10** on a folder for **Play All in Folder**, **Shuffle Folder**, **Export This Folder...**, **Rename Folder...** and **Delete Folder...**.

1. Choose **Play All in Folder**. The folder's first station plays, and Quill Radio remembers the rest.
2. To move to the next station in the folder, press **Ctrl+Shift+P**, type `next station`, and choose **Next Station in Folder**. **Previous Station in Folder** goes back. These two are in the Command Palette only.
3. At either end it says so rather than wrapping round.

Shuffle is one fixed order, so Previous walks back through the same sequence. A folder always includes everything beneath it: playing "News" plays "News/Local" too, but never a separate folder called "Newsroom". **Export This Folder...** writes just that folder to an M3U file.

On a station, the menu offers **Play**, **Rename Station...** (F2), **Remove...** (Delete), **Move Up**, **Move Down**, **Mark for Move**, **Move to Folder...**, and **Move Above** and **Move Below** once a station is marked.

### Other things to know

- **Rename** gives a station your own name everywhere. A blank name restores the directory's own.
- **Remove All...** clears every favorite at once. Your folders stay. It asks first, and **No** is the default. Favorites keep a rolling backup, so even that can be recovered.
- **Sort order** for the whole list is in Preferences and on **View > Sort Favorites**. Any one folder can have its own order: in the main window's tree, press **Shift+F10** on the folder and choose **Sort This Folder...**. Choose Ascending, Descending, Unsorted, or follow the default.
- The Manager's menus are **Favorites** (with **Close**, Ctrl+W), **Station** and **Window**.

## Backing up and restoring

A backup is one `.qrbackup` file holding your favorites, settings, wake-up timer and recording schedule, and your recordings if you choose.

### Back up, step by step

1. Press **Ctrl+Shift+U** (**Station > Back Up Stations and Settings...**).
2. If you have recordings, Quill Radio asks whether to include them, because they can be large. Choose **Yes** or **No**.
3. A file window opens: "Save Quill Radio Backup". Choose a folder and a name, then **Save**.
4. You should hear that the backup was saved.

### Restore, step by step

1. Press **Ctrl+Alt+Shift+W** (**Station > Restore from Backup...**).
2. A file window opens: "Restore Quill Radio Backup". Choose the `.qrbackup` file and choose **Open**.
3. A question says what the backup holds and when it was made, and warns: "This replaces your current stations and settings." **No is the default**, so Enter alone does nothing. To restore, press **Y**, or Tab to **Yes** and press Enter.
4. Quill Radio restores the files and reloads, so the change takes effect at once.

To move everything, including bookmarks and keys, to another computer, see also "Moving your setup to another machine".

## Preferences

**Station > Preferences...** (Ctrl+,) opens **Quill Radio Preferences**, one page of settings. Every setting takes effect the moment you choose OK. Switching the playback engine or the output device while something plays reconnects straight away.

### Change a setting, step by step

1. Press **Ctrl+,**. Quill Radio Preferences opens with focus on its first control.
2. Press **Tab** to move through the controls. Each one's name is also its help. Press **F1** on any control for more.
3. For a drop-down list, press **Alt+Down arrow** to open it, or arrow through the choices where you are.
4. For a checkbox, press **Space**.
5. Choose **OK** (Enter) to save. You should hear "Preferences saved." Escape cancels.

### What is in Preferences

The drop-down lists come first:

- **Main window shows** -- Favorite stations (the default), Browse Stations, Search Stations, Radio Recordings or Player. See "What the main window shows".
- **When closing the window** -- Ask every time (the default), Exit, or Minimize to Tray. This governs the title bar's close button and Alt+F4. See "Closing Quill Radio".
- **Playback engine** -- the rows are what this copy has. With the mpv engine present: Automatic (recommended, uses mpv), Windows Media, or mpv. Without it, there is no mpv row and Automatic reads "Automatic (uses Windows Media; mpv is not installed)", so what you hear is what you get. Automatic with mpv adds rewinding live radio, Volume Boost and more stream formats. The output device works on either engine. The row reads "Windows Media (classic)" only on a machine without Windows' modern media player, and that one is the pre-1.1 behaviour.
- **Radio output device** -- System default, or a sound card or headset. Only the radio moves. Your screen reader and Quill Radio's own sounds stay on the system default. A device that cannot be opened is given back: the setting returns to what it was and Quill Radio says so. The same setting as **Audio > Output Device...**. It applies to the mpv engine and to Windows Media, which is Windows' modern media player and takes a device too; only on a machine falling back to the classic control is the device the one Windows gives Quill Radio in Sound settings (see Output Device, step by step).
- **Favorites sort order** -- Ascending (A to Z, the default), Descending (Z to A), or Unsorted (manual order).
- **Station catalog update frequency** -- Every 6 hours, Every 12 hours, Every 24 hours (the default), Every 2 days, or Manually only.
- **Episodes listed per subscribed podcast** -- 10, 25 (the default), 50, 100 newest, or All episodes.
- **Interrupted recordings at launch** -- Ask each time (the default), Always resume them, or Never resume them. See "If a recording was in progress when Quill Radio quit".

Then the checkboxes:

- **Resume Last Station on Launch** -- off.
- **Check for updates automatically on launch** -- on. A quiet check once a day, silent unless it finds something.
- **Announce dialog transitions (more spoken detail)** -- off. When on, Quill Radio says "Entered ..." and "Exited ..." as windows open and close.
- **Recover failed streams from the station's website** -- on.
- **Share play counts with the RadioBrowser directory** -- on. See "Dependencies, honestly stated".
- **Alt+F4 minimizes to the system tray** -- off. When on, Alt+F4 tucks the radio into the tray, still playing.
- **Verbose logging (debug mode)** -- off. Detailed logging for tracking down a problem. It applies at once, with no restart.
- **Keep the computer awake while playing or recording** -- on. Windows does not go to sleep while a station plays or a recording runs. The screen can still turn off.
- **Keep the computer awake before a scheduled recording** -- on. Stops Windows sleeping in the few minutes before a recording is due.
- **Wake the computer for a scheduled recording** -- on. If the computer is asleep when a recording is due, Windows wakes it a couple of minutes early. This adds a task to Windows Task Scheduler. In a portable copy it is greyed out, with the reason.
- **Keep a local station catalog on this computer** -- on. Off restores live-only browsing, with nothing stored.
- **Check for station catalog updates when Quill Radio starts** -- on.
- **Winamp-style playback keys in the Recordings player** -- on. See "Winamp keys in Radio Recordings".

Then two text boxes:

- **What's Playing announcement** -- a template for what What's Playing says. `{title}` and `{artist}` are the song and artist. Wording inside `[square brackets]` disappears when a field is empty. `{raw}` is the stream's exact original text. The default is `{title}[ by {artist}]`. Leave it blank to restore the default.
- **Log folder** -- where the log is written. Leave it blank for the default. Changing it moves the log at once.

Then two buttons:

- **Reset All Stations' Sound Enhancements...** -- drops every station's own Sound Enhancements back to the shared default.
- **Data Folder...** -- where every Quill app keeps its settings, favorites, subscriptions and playback positions. Point it at a folder that Dropbox, OneDrive, Google Drive or iCloud keeps in sync, and your setup travels between computers. The change applies the next time an app starts; a restart is offered, and your data is moved for you. Caches such as the station catalog stay on each computer. Do not run Quill apps on two computers against the same folder at the same time. If you do, the next launch says so.

Then two groups:

- **Podcasts**: **Check subscribed podcast feeds** (Manually only, the default, through every 15 minutes to once a day), and **Check subscribed podcast feeds at launch** (off). See "Checking your subscribed podcasts".
- **Reminders**: **New reminders start at** (15 minutes before, by default), and **Play a sound when a reminder comes due** (on).

### Customize Features, step by step

Customize Features turns the Record menu off if you never record.

1. Press **Ctrl+Alt+C** (**View > Customize Features...**). The window "Customize Quill Radio Features" opens.
2. **Search features** filters the list. There is one area: **Enable Recording**, which covers the Record menu.
3. Press **Space** to uncheck it, then choose **Save**.
4. You should hear "Feature settings saved. Menu changes take effect the next time you open Quill Radio."

Nothing is deleted, and turning it back on restores the menu. The tray and status bar menus keep offering Record Now, Schedule Recording and Recording Settings either way.

## Pausing, rewinding and moving around

### Pause and resume

**Pause** (Ctrl+Space) holds a podcast episode, a recording, a downloaded or local file, or a finished video, and **Resume** picks it up where it was.

1. With something that has a timeline playing, press **Ctrl+Space**. You should hear "Paused."
2. Press **Ctrl+Space** again. You should hear "Resumed."

**Live radio cannot be paused.** On a live station, Pause is dimmed and says why: live radio is going out now, so there is nothing to hold. Stop ends it. To catch something you missed, rewind instead.

In windows other than the main one, **Ctrl+P** also pauses and resumes anything with a timeline.

### Rewind live radio, and go back to live

With the default mpv playback engine, Quill Radio keeps a rolling buffer of a live stream, roughly 45 minutes at typical bitrates.

1. While a live station plays, press **Ctrl+Shift+Left** (**Playback > Rewind 30 Seconds**). You should hear "Rewound 30 seconds", and how far behind live you are.
2. Press it again to go back further, as far as the buffer has filled since you started listening.
3. Press **Ctrl+Shift+Right** (**Forward 30 Seconds**) to move forward again.
4. Press **Ctrl+Shift+L** (**Back to Live**) to jump straight back to the live moment. You should hear "Back to live."

On the Windows Media engine there is no buffer -- neither the modern player nor the classic control keeps one -- and these keys say that rewinding live radio needs the mpv playback engine. Set **Playback engine** to Automatic in Preferences to get it back.

### Speed, position and chapters

These work on anything with a timeline: a finished YouTube video, a podcast episode, a recording, a downloaded file.

- **Play Faster** (Ctrl+Shift+Up), **Play Slower** (Ctrl+Shift+Down) and **Normal Speed** (Ctrl+Shift+0) step through round values from 0.25 times to 4 times. The speed is remembered by kind: a speed you choose for a recording applies to every recording, and one for a YouTube row applies to YouTube rows. While a **podcast episode** plays, the speed is remembered for that show: you hear "Remembered for this show", and Normal Speed forgets it out loud.
- **Rewind 30 Seconds** and **Forward 30 Seconds** move along the timeline and say where you landed, such as "3 minutes 10 seconds of 18 minutes 40 seconds".
- **Where Am I?** (Ctrl+Shift+W) says your position, the length and the chapter you are in.
- **Next Chapter** (Ctrl+Shift+.) and **Previous Chapter** (Ctrl+Shift+,) move by chapter. Previous Chapter first restarts the current chapter, the way a CD player does.
- **Skip Silence** (Ctrl+Shift+9) shortens long pauses. It takes effect at once, with no interruption.

On a live stream, each of these says why it cannot act: "This is live radio, which plays at broadcast speed and has no chapters or position to move through."

### Go to Position, step by step

1. With something with a timeline playing, press **Ctrl+Alt+J** (**Playback > Go to Position...**). The Go to Position window opens.
2. Type the time in **Hours** (Alt+H), **Minutes** (Alt+M) and **Seconds** (Alt+S). Or Tab to **Or type a timecode** and type it in one go, such as `1:23:45`.
3. Choose **OK**. Playback jumps there and says the new position.

### Chapters, step by step

The chapter list works for a video's published chapters, a recording's or downloaded episode's own chapter marks, and episodes Quill Cast has already analysed.

1. While something with chapters plays, press **Ctrl+Shift+C** (**Playback > Chapters...**). The Chapters window opens.
2. Its first line says how many chapters there are and where they came from. Focus is in the **Chapters** list (Alt+C). The chapter playing now is marked.
3. Arrow to a chapter. Each reads as a sentence, such as "3. Introducing layers, starts at 5 minutes 31 seconds".
4. To jump there, Tab to **Go To** and press **Space**. The list stays open so you can keep exploring.
5. When the thing playing is a file on this computer, **Preview This Mark** plays ten seconds either side of the chapter boundary through its own player. Your place does not move. **Stop Preview** stops it.
6. Press **Escape** to close the list.

Where there are no chapters, it says so. Quill Radio does not work chapters out for itself: that takes a 91 MB speech engine, and Quill Cast already does it.

### Continue Listening, step by step

Continue Listening lists everything you started and did not finish: recordings, podcast episodes, audiobook chapters and other rows with a timeline.

1. Press **Ctrl+Alt+Shift+L** (**Playback > Continue Listening...**). The window opens. A heading says how many are unfinished.
2. Arrow through the **Unfinished** list (Alt+U). Each row says what it is and where you stopped.
3. Press **Enter**, or choose **Resume**, to play it from where you stopped.
4. Choose **Forget This One** (Alt+F) to take a row off the list.
5. Press **Escape** to close.

Both Quill Radio and Quill Cast keep your place in a subscribed episode in the same place on this computer, so either app knows how far you got. An episode either app has finished stays finished.

## What's playing, and what played

### What's Playing, step by step

1. Press **Ctrl+T** (**Playback > What's Playing?**). The Now Playing window opens, titled "Now Playing:" and the station's name. Press it again while the window is open and the window is refreshed, brought forward, and the title and artist are spoken.
2. Focus is in a read-only box with the title and artist. Arrow through it, a character at a time if you want the exact spelling.
3. Tab to **Copy** and press **Space** to copy it. You should hear "Copied."
4. Press **Escape** to close.

If nothing is playing, you hear "Nothing is playing." and no window opens. If no title has arrived yet, you hear "Checking what's playing..." while Quill Radio fetches it. A station that sends no titles at all opens the window with its name and "This stream doesn't share track titles."

Where the title comes from: first the information carried with the audio, then the playback engine's own reading of the stream, and last the stream server's own public status page. It only ever asks the server you are already listening to, and not in Safe Mode. When a station sends messy text, such as catalog codes, Quill Radio picks out the title and artist.

To change what What's Playing says, edit **What's Playing announcement** in Preferences.

**Copy What's Playing** in the Command Palette copies the title and artist straight to the clipboard, without the window. It names what it copied.

**Announce Track Titles** (Ctrl+Alt+T, **Audio** menu) speaks each new title as it changes. It is off by default. In the Command Palette it reads "(currently On)" or "(currently Off)".

### Song History, step by step

Song History keeps what each station played while you listened: up to 200 songs per station, on this computer only.

1. Press **Ctrl+Shift+H** (**Playback > Song History...**). If no songs have been logged yet, you hear so and no window opens.
2. The Song History window opens with focus in the **Songs** list (Alt+O), newest first. Each row reads like "Your Song by Elton John, heard 10:04, played twice".
3. To see another station's list, press **Alt+A** for **Station** and choose it.
4. With a song selected, Tab to a button and press **Space**:
   - **Copy** -- puts the song on the clipboard.
   - **Send to Clip Library** -- keeps it with your other saved snippets.
   - **Background** -- asks your AI provider, if you have set one up, for a short note about the song and artist. The answer always says it was written by an AI model. It appears in the **Background** box (Alt+K), and focus moves there. Not available in Safe Mode.
   - **Song Details** -- looks the song up on MusicBrainz: which release, what year, how long. If nothing more is known, it says so.
   - **Clear...** -- asks whether to clear **This station** or **All stations**. **Cancel is the default**, so Enter alone clears nothing.
5. Press **Escape**, **Ctrl+W** or **Ctrl+F4** to close. Song History is a window of its own, with the menus **Songs** (Alt+G), **Station** (Alt+S) and **Window** (Alt+W).

Good to know: Song History only fills while a station sends track titles. A station that sends none, such as many talk and reading services, leaves nothing to log.

A song still playing when Quill Radio checks again adds to its play count instead of repeating. Station names, "Live" and advert markers are left out.

## Volume and sound

### Volume

- **Ctrl+Up** and **Ctrl+Down** change the volume in steps of ten, from any window. In the main window they work from any control except a text box, where Ctrl+arrow still edits text.
- **Ctrl+M** mutes and unmutes in the main window. **Ctrl+Shift+O** works in every window, including the main one.
- **Each favorite remembers its own volume.** Set it while the station plays, and it comes back next time.
- **The last level you set is remembered** for everything else, across sessions.

To use one level for every station:

1. Press **Ctrl+Alt+V** (**Audio > Use One Volume for All Stations**). You should hear that one volume for all stations is on, and the level.
2. Now Ctrl+Up and Ctrl+Down turn everything up or down. Ticking it adopts the level you are hearing, so nothing jumps.
3. Press **Ctrl+Alt+V** again to go back. Every station returns to its own remembered level.

To throw the per-station levels away for good:

1. Press **Ctrl+Alt+Shift+V** (**Audio > Forget Every Station's Own Volume...**).
2. A question says how many stations have their own level. **No is the default.** Press **Y** to forget them.
3. You should hear "Forgot the volume for" and the count. Your stations, folders and other settings are untouched.

### Volume Boost

Some stations broadcast much more quietly than others, so full volume is still too soft. Volume Boost lets the radio go up to 50 percent past full volume.

1. While a quiet station plays, press **Ctrl+Shift+B** (**Audio > Volume Boost**). You should hear "Volume Boost on: up to 50 percent louder."
2. Press **Ctrl+Up** to raise the volume. The status bar's Volume cell adds "boosted".
3. Press **Ctrl+Shift+B** again to turn it off.

Your volume scale, per-station levels and mute work as before. Boost can distort a station that is already loud, so turn it off when you move on.

If it does not work: Volume Boost needs the mpv playback engine. If it says so, set **Playback engine** to Automatic in Preferences.

### Output Device, step by step

1. Press **Ctrl+Shift+D** (**Audio > Output Device...**). A list opens: "Send Quill Radio's audio to which device?"
2. The first row is **System default**. Arrow to a sound card or headset. A saved device that is unplugged reads "(not currently available)".
3. Press **Enter**. The station moves to that device at once, without a break in the sound. You should hear "Output device" and its name.

Your screen reader and Quill Radio's own sounds stay on the system default. The choice is the same setting as **Radio output device** in Preferences, and it works on either engine: Windows Media is Windows' modern media player now, and it takes a device just as mpv does.

**On an older copy of Windows** that does not offer the modern media player, Quill Radio falls back to the classic control, and there the list cannot move the sound: that control plays on the device Windows gives Quill Radio, and nothing in it takes a device name. Quill Radio does not change your engine choice to get around this. Instead, choosing a device says so in one sentence and opens Windows' Sound settings at once, where under **Volume mixer** every app has its own output device. Find Quill Radio in that list and pick the device. Windows remembers it across restarts. A copy without the mpv engine opens the same page as soon as you press Ctrl+Shift+D. If a device is in the setting while the engine is Windows Media, Quill Radio gives it back and says the same thing.

**If the device cannot be opened** -- a Bluetooth or USB headset that has gone to sleep, a device another program is holding, one whose Windows id changed -- Quill Radio says so, names it, and puts the setting back to what it was: "Speakers (Logi USB Headset) could not be opened, so the output device is back to System default." The sound stays on the mpv engine, on the device that was in use before, and Preferences shows the same. Wake the device or plug it in, then choose it again. A saved device that cannot be opened when Quill Radio starts is given back the same way, so a copy is never stuck with a setting it cannot honour. Until 3.1.1 this case was silent: the station quietly moved to Windows Media, which can only use the system default, the setting kept naming a device that was not in use, and the sound card seemed not to switch at all.

Both sound cards on a laptop are often called "Speakers" by Windows -- "Speakers (Realtek High Definition Audio)" for the built-in ones, "Speakers (Logi USB Headset)" for a headset -- so listen past the first word for the make.

### Sound Enhancements, step by step

1. Press **Ctrl+E** (**Audio > Sound Enhancements...**). The Sound Enhancements window opens with focus on **Quick preset**.
2. **Quick preset** (Alt+Q) sets the three sliders as a starting point: Flat, Bass Boost, Voice Clarity, Podcast, Small Speakers or Late Night. Move a slider afterwards and it becomes Custom.
3. **Bass** (Alt+B), **Mid** (Alt+M) and **Treble** (Alt+T) are sliders from -12 to +12 dB. Use the arrow keys.
4. **Even Out Volume** (Alt+E) is a compressor: it lifts quiet passages and tames loud ones.
5. **Channel mode** (Alt+H): **Stereo**, **Mono**, **Left only** or **Right only**. Mono blends both channels, so a voice panned to one side never disappears with one earbud. Left only or Right only sends the whole mix to one ear, so your screen reader can use the other.
6. **Night mode (even loudness)** (Alt+N) evens loudness in real time, for quiet late-night listening.
7. **Apply broadcast polish (OptiLab)** (Alt+A) turns on a broadcast-style chain. **Polish mode** (Alt+P): Off, Podcast Leveler (speech), Stream Polish (music) or Smooth Limiter (mastering). **Input (dB)** (Alt+I) trims the level going in. **Auto-Adapt** (Alt+U) is a slider from 0 to 100 percent.
8. **Exact OptiLab processing** (Alt+X): **Off** (the default), **When saving** (the real engine for recordings and converted files, recommended), or **When saving and while listening** (the station starts slower, and each change needs a brief reconnect). If your copy does not include the OptiLab component, this choice is disabled and says so.
9. You hear every change on what is playing right away.
10. Choose **OK** to keep the settings, or **Cancel** (Escape) to put everything back as it was.

**Per station or for everyone.** Open Sound Enhancements while a favorite plays, and the settings are saved for that station. With nothing playing, or a non-favorite on, you set the shared default every other station follows. When a favorite's own settings are open, **Reset to Default** (Alt+R) drops that station back to the shared default. **Reset All Stations' Sound Enhancements...** in Preferences does it for every station.

Broadcast polish is adapted, with thanks, from **OptiLab Core by Lanes Audio / dgl1984** (https://github.com/dgl1984/optilab, Apache-2.0 with the Commons Clause). Live listening always uses the built-in chain, so you hear each change at once.

Recordings stay unfiltered unless you turn on **Apply Sound Enhancements to recordings** in Recording Settings.

## Video, captions and described audio

Quill Radio plays YouTube links and television as audio by default. You can also show the picture, read captions, and choose a described audio track.

### Show the video, step by step

1. While a video or TV channel plays, press **Ctrl+Shift+V** (**Video > Show Video**). The "Quill Radio Video" window opens. You should hear "Video shown" and its size.
2. The picture has a name and description for your screen reader. Tab moves to a read-only status line with the title, position, chapter and audio track.
3. Press **F11** for full screen. You should hear "Full screen. Press F11 or Escape to leave."
4. Press **Escape** to leave full screen. Press **Escape** again, or **Ctrl+Shift+V**, **Ctrl+W** or **Ctrl+F4**, to close the window. You should hear "Video hidden. Audio is still playing."

Showing and hiding the picture never restarts the stream or loses your place. The window has no buttons: every command is on the Video menu, in the Command Palette, and on a key. The transport keys work inside it.

Other Video menu items:

- **Video Information** (Ctrl+Shift+I) says the size, the frame rate, and whether captions and described audio exist.
- **Take a Snapshot** (Ctrl+Shift+Alt+H) saves the current frame as a picture in your recordings folder, for example to read a slide with OCR. You should hear "Snapshot saved as" and its name.
- **Video Size** (Ctrl+Alt+4 to Ctrl+Alt+7) sets the window to Fit, 50%, 100% or 200%.

Nothing can tell whether a video contains flashing before it plays, so Quill Radio makes getting away immediate: Ctrl+Shift+V hides the picture from any window.

### Captions, step by step

1. While a video plays, press **Ctrl+Shift+K** (**Video > Captions**). You should hear "Getting captions...", then "Captions on, in the Captions window."
2. The "Quill Radio Captions" window opens without taking focus. Switch to it with **Ctrl+Tab** or Alt+Tab.
3. The captions are text you can arrow through. Each line joins the ones already spoken, newest last. The line being spoken is marked with a greater-than sign.
4. To read back without the text moving, turn off **Follow playback** (Alt+F).
5. Press **Escape** to close the window. Closing it turns captions off. You should hear "Captions off."

If the captions were made by machine, the window says so. A video with no captions says "This video has no captions published."

### Caption Settings, step by step

1. Press **Ctrl+Shift+Alt+T** (**Video > Caption Settings...**).
2. Set **Caption size** (100 to 300 percent), **Text colour** (Alt+T), **Background colour** (Alt+B), **Background opacity** (Alt+O, a slider) and **Position** (Alt+P, bottom or top).
3. Choose **Save**. Quill Radio reads back the new style.

The default is solid white on solid black. It looks heavier than most players, on purpose: captions sit over whatever the picture shows, and no colour is readable against everything.

### Audio and Described Audio, step by step

A described audio track is a second narration that says what a sighted viewer can see. Quill Radio names it and puts it first.

1. While a video plays, press **Ctrl+Shift+A** (**Audio > Audio and Described Audio...**). The window opens. Its heading says "Described audio is available for this video." or "No described audio was published for this video."
2. Focus is in the **Audio tracks** list, on the described track when there is one. Tracks in the language you read the app in come first, then the video's original track, then the rest alphabetically.
3. Press **Enter**, or choose **Play This Track**, to switch. Your place is kept.
4. You should hear "Playing the described audio track." or the track's name.

**Play Described Audio** (Ctrl+Alt+D) switches straight to the described track, with no list. If there is none, it says what the video does have.

When you play a video that has a described track, Quill Radio says so once, and tells you the key.

### Transcript, step by step

1. While a YouTube video plays, press **Ctrl+Shift+T** (**Playback > Transcript...**). You should hear "Fetching transcript...", then the window "Transcript:" and the title opens.
2. Focus is in the transcript, an ordinary read-only text box. Arrow through it, select, or use your screen reader's review cursor.
3. Press **Enter** on any line to play from the moment that line was spoken. The **Play from Here** button does the same.
4. Press **Ctrl+F** (or **Find...**) to search. Each hit says where it is, such as "Found at 12 minutes 8 seconds".
5. Other buttons: **Copy**, **Links...** (Ctrl+Shift+L, every web address in the transcript), **Save As...** (plain text, WebVTT or SubRip), and **Open in QUILL**.
6. Press **Escape** to close.

If the captions are automatic, the heading says so. A live stream has no transcript and says so, and so does a video with no captions. For a podcast episode whose feed publishes a transcript, use **View Transcript...** on the episode's menu in Browse Stations.

## Timers

### Sleep Timer, step by step

1. Press **Ctrl+Shift+Z** (**Playback > Sleep Timer...**). The Sleep Timer window opens.
2. Choose how long in **Stop Radio and Podcasts playback after**: 15, 30, 45, 60 or 90 minutes, or **Custom...**. With Custom, Tab to the minutes box and type a number from 1 to 600.
3. Choose **Start** (Enter). You should hear "Sleep timer set for" and the minutes.
4. When time is up, the sound fades out and stops, and your volume is restored. You should hear "Sleep timer: playback stopped, volume restored."

While a timer runs, the same window shows the time left and offers **Extend 5 Minutes** and **Cancel Sleep Timer**. The status bar's Sleep timer cell shows the minutes left; press Enter on it to open the window. The Command Palette also has **Extend Sleep Timer 5 Minutes** and **Cancel Sleep Timer**.

### Wake-Up Timer, step by step

The Wake-Up Timer starts a favorite at a time you choose, once or every day.

1. Press **Ctrl+Alt+Z** (**Playback > Wake-Up Timer...**). The window says the current setting.
2. Check **Wake up with the radio** (Alt+W) with Space.
3. Choose a **Station** (Alt+S) from your favorites.
4. Type a **Time** (Alt+T), such as `07:00` or `7:30 AM`.
5. Check **Every day (not just once)** (Alt+D) if you want it daily.
6. Choose **OK**. You should hear the setting read back.
7. At that time you hear "Good morning." and the station's name, and it starts playing.

Quill Radio must be running at that time. The tray counts; a closed app does not. The Wake-Up Timer does not wake a sleeping computer. To turn it off, open it and uncheck **Wake up with the radio**.

## Recording

Recording needs ffmpeg, which is bundled with Quill Radio.

### Record what is on now

1. While a station plays, press **Ctrl+R** (**Record > Record Now / Stop Recording**).
2. You should hear "Recording started" and the station's name, over the start-recording sound.
3. The status bar's Record cell reads **Stop Recording** with the time so far.
4. Press **Ctrl+R** again to stop. You should hear "Stopping recording", then that it was saved, with the file's name.

Ctrl+R follows what you are listening to. If the station you are hearing is recording, it stops that recording. Otherwise it starts a new one. A recording of a different station, running in the background, is never stopped by Ctrl+R.

### Record a different station, step by step

Record Station records any favorite for a set time, while you listen to something else or to nothing.

1. Press **Ctrl+Alt+R** (**Record > Record Station...**). The Record Station window opens.
2. Choose the station in **Station** (Alt+T). Your favorites are listed, and so is the station playing now if it is not a favorite.
3. Set **Duration (minutes)** (Alt+D), from 1 to 1,440. It starts at 60.
4. Choose **Start Recording** (Enter). You should hear "Recording started:", the station and the minutes.

You can start as many as you like. They all record at once.

### Recording several stations at once

You can record two shows that overlap, or record one station while you listen to another. Each recording is independent: its own connection, its own reconnect handling, its own crash recovery. Overlapping scheduled recordings all fire.

To record two stations at once:

1. Play the first station and press **Ctrl+R**. You should hear "Recording started" and its name.
2. Press **Ctrl+Alt+R** for Record Station. Choose the second station, set the minutes, and choose **Start Recording**.
3. Press **Ctrl+Shift+R** to open Radio Recordings. Both rows read **Recording**, and the line under the list says how many are running.
4. To stop one, select its row, Tab to **Stop Recording** and press Space. To stop them all, press **Ctrl+Alt+X**.

Good to know:

- A stream that stalls without disconnecting is noticed within about half a minute. Quill Radio reconnects and continues, or stops and saves what it has.
- As a second check, a recording whose file has not grown for about a minute is treated as dropped.
- To cap how many run at once, set **Maximum simultaneous recordings** in Recording Settings. 0 means no limit, the default. A scheduled recording over the cap waits and retries while its time window is still open.
- To stop them: **Ctrl+R** stops the one for the station you are hearing. **Stop Recording** in Radio Recordings stops the one selected there. **Stop All Recordings** (Ctrl+Alt+X) stops every one. You should hear "Stopping all" and the count.

Recording file names use your computer's current time zone, even if it changes while Quill Radio runs.

### Schedule a recording, step by step

The one thing to remember: **fill in the details first, then choose Add Schedule last.**

1. Press **Ctrl+Shift+S** (**Record > Schedule Recording...**). The Schedule Recording window opens. The station playing now, if any, is already filled in.
2. If you have favorites, the **Favorite station** list (Alt+F) is there. Its first row is "(type the details below)". Choose a favorite and its name and stream fill in for you.
3. Or type them yourself in **Station name** (Alt+M) and **Stream URL** (Alt+U).
4. Tab to **Repeats** and choose **Once**, **Daily** or **Weekly**.
5. For Weekly, Tab to **On day (weekly only)** and choose the day. For Once, type the date in **Date (once only)** (Alt+C), as `YYYY-MM-DD`.
6. Type the start in **Time (7:30 PM or 19:30)** (Alt+T).
7. If the show's time is given in another time zone, choose it in **Time zone** (Alt+Z). Otherwise leave "(local time)".
8. Set the length in **Duration -- hours** (Alt+H, 0 to 24) and **and minutes** (Alt+I, 0 to 59). A three-hour show is 3 and 0.
9. Choose **Add Schedule** (Alt+A). You should hear "Scheduled recording added for" and the station. Focus moves to your entry in the list, and the form clears for the next one.

If something is missing, the status line says what, and nothing is added.

The list at the top, **Scheduled recordings** (Alt+G), is ordered by when each will next record. Each row shows the station's server in brackets, so two similar entries are easy to tell apart. With an entry selected:

- **Edit** loads it into the form. The Add button becomes **Save Changes**. Choose **New** (Alt+N) to stop editing and start a fresh entry.
- **Duplicate** starts a new entry filled in from this one, named with " (copy)". It keeps the original's stream until you change it.
- **Disable** turns an entry off without losing it. It reads "(disabled)" and does not fire. **Enable** turns it back on.
- **Remove**, or the **Delete** key, deletes the entry **at once, with no question**.
- **Shift+F10** on the list offers Edit, Duplicate, Enable or Disable, and Delete.

Close the window with **Escape** or **Ctrl+W**. Its menus are **Schedule** (Alt+D), **Station** (Alt+S) and **Window** (Alt+W).

Quill Radio must be running for a scheduled recording to start. The tray counts. A recording is due from its start time to the end of its length, so if Quill Radio starts a few minutes late, it records the rest. A show whose whole time passed while Quill Radio was closed is missed, and the next launch tells you, naming up to three.

To make sure the computer is awake, see **Keep the computer awake before a scheduled recording** and **Wake the computer for a scheduled recording** in Preferences.

You can also schedule from Browse Stations: **Schedule Recording...** on a live station's menu opens this window with that station filled in. The ACB Media schedule can schedule a programme for you.

### Recording Settings, step by step

1. Press **Ctrl+Alt+Shift+I** (**Record > Recording Settings...**).
2. Set the controls you want:
   - **Format** (Alt+F): MP3 (the default), OGG Vorbis, FLAC, WAV, or **Raw stream -- exactly as sent, no re-encoding (lossless)**.
   - **Quality (bitrate)** (Alt+Q): 96 to 320 kbps. The default is 192. Hidden for the lossless formats.
   - **Destination folder** (Alt+D): where recordings go. Blank means `Music\Quill Radio Recordings` in your user folder, or the `Recordings` folder of a portable copy. **Browse...** chooses one.
   - **Temporary folder (while recording)** (Alt+T): optional. A recording is written there and moved to the destination when it finishes, so a half-written file never appears among your recordings. Blank records straight to the destination.
   - **Filename pattern** (Alt+P): the default is `{station} - {date} {time}`.
   - **Maximum recording length (minutes)** (Alt+M): a safety cap, 180 by default.
   - **Maximum simultaneous recordings** (Alt+S): 0, meaning no limit, by default.
   - Under **If the connection drops**: **Reconnect and keep recording automatically** (Alt+K, on), **Reconnect attempts** (Alt+A, 5) and **Seconds between attempts** (Alt+C, 10).
   - **Apply Sound Enhancements to recordings** (Alt+E): off, so recordings stay an unfiltered copy. Turn it on to record the filtered sound, for every kind of recording.
3. Choose **OK**. You should hear "Recording settings saved".

**Raw stream** saves exactly what the station sends, with no re-encoding, so nothing is lost. The file type follows the stream: `.mp3`, `.aac`, `.ogg`, `.opus` or `.flac`, and anything unusual goes in a Matroska `.mka` file. Bitrate and Sound Enhancements do not apply to a raw recording.

### Radio Recordings, step by step

Radio Recordings shows every recording in one list: ones being written now, finished ones, and scheduled ones.

1. Press **Ctrl+Shift+R** (**Record > Recordings...**). Radio Recordings opens with focus in the list, newest first.
2. Arrow through the list. Each row gives the name and a status: **Recording**, **Recorded** or **Scheduled**, then size and date. A recording being written grows as you watch.
3. Press **Enter** on a finished recording to play it. Press **Enter** again to stop. While it plays, Ctrl+Up and Ctrl+Down change its volume.
4. Tab to the buttons: **Play** (reads **Stop** while the selected recording plays), **Stop Recording** (on a row being recorded), **Stop All Recordings** (when two or more are running), **Open in Folder** (shows the file in File Explorer), **Remove...** and **Refresh**.
5. Press **Delete** to remove a finished recording. **No is the default**; press **Y** to delete. Focus lands on the neighbouring recording. Ctrl+Z in the main window brings it back.
6. Press **Escape** to close. Recordings keep going.

The line under the list leads with what is happening, such as "Recording, 42 min left. Next: KFI at 11:00 tomorrow. 14 recorded. In D:\Music\Quill Radio Recordings." If you have schedules but none can fire, it says "3 scheduled, none coming up".

The list updates in place every couple of seconds, keeping your selection and position. It has no right-click menu. Its menus are **Recordings** (Alt+R, with **Close**, Ctrl+W), **Station** and **Window**. To choose which columns each row reads, see "What each row says".

### Winamp keys in Radio Recordings

If Winamp's classic keys are in your fingers, they work in the Radio Recordings list, with no modifier:

| Key | What it does |
| --- | --- |
| X | Play the selected recording, or resume a paused one |
| C | Pause or unpause |
| V, or Shift+V | Stop |
| B | Next recording: moves down the list and plays it |
| Z | Previous recording |
| Left / Right | Back or forward 5 seconds |
| Shift+Left / Shift+Right | Back or forward 30 seconds |
| R | Shuffle on or off |
| S | Repeat: off, then all recordings, then this recording |
| Ctrl+V | Stop after the current recording, once |
| T | Say the elapsed time, or the time remaining; press again to swap |
| J | Jump to a recording: type part of its name |
| Ctrl+J | Jump to a time: type `90`, `1:30` or `1:02:03` |
| L | Play the selected recording |
| Ctrl+Up / Ctrl+Down | Volume up or down |

Every key says what it did. Two differences from Winamp: **Ctrl+T** stays What's Playing, so elapsed or remaining is plain **T**; and **Up** and **Down** move through the list, not the volume.

- Shuffle is a fixed order, so every recording plays once before any repeats, and Z takes you back to the one you just heard.
- Repeat-one applies when a recording finishes on its own. B still moves on.
- Ctrl+V clears itself once it fires, and is not remembered between sessions. Shuffle and repeat are remembered.
- A recording that ends on its own is followed by the next one in the queue.
- Seeking needs the mpv engine.

Turn the letter keys off with **Winamp-style playback keys in the Recordings player** in Preferences, if you would rather type letters to jump through the list. Ctrl+Up and Ctrl+Down work either way.

### If the internet hiccups during a recording

ffmpeg first rides out short gaps itself, using the reconnect settings in Recording Settings. If the connection really dies, Quill Radio waits and continues into a numbered part file, announcing each attempt. When the recording finishes, **it joins the parts back into one file**, and says so: "Joined 3 parts into one recording", or "Kept 3 separate parts" and the reason.

- The join is a straight copy with no re-encoding, so nothing is lost and it takes seconds. The joined file is checked before the parts are removed. If anything goes wrong, every part is left as it was.
- A continuation records only the time left to the original end. A 60-minute show that drops at minute 50 records about 10 more minutes.
- Only a truly final failure gives up: a full disk, or a server answer meaning the stream is gone. Other errors reconnect.
- File names are never overwritten. A repeated name gets " (2)", " (3)" and so on.
- If Quill Radio is closed or crashes, its ffmpeg recorder is closed with it.

### If a recording was in progress when Quill Radio quit

A crash, a power cut or a forced restart can end Quill Radio in the middle of a recording. The part already recorded is kept, and Quill Radio offers to record the rest.

On the next launch, Quill Radio tidies its temporary folder, moving any finished file to your recordings folder. Then, if a recording was in progress and its scheduled end has not passed by more than ten minutes, a window titled **Resume Recording** asks, for example:

> A recording of WQXR was in progress until 2026-09-26 09:00:00. Resume it for the remaining 12 minute(s)?

1. Read the question with your screen reader's read-window command if it was not read in full.
2. If you want Quill Radio to remember your answer from now on, press **Alt+D** to check **Don't ask me again** first.
3. Choose **Resume** (Enter) to record the remaining minutes, or **Skip** (Escape) to leave it. Resume records from the same station, for the minutes that are left.

If several recordings were interrupted, one question covers them all. It lists them, asks "Resume all of them for their remaining time?", and offers **Resume All** and **Skip All**.

To change your mind later:

1. Press **Ctrl+,** to open Preferences.
2. Tab to **Interrupted recordings at launch**.
3. Choose **Ask each time** (the default), **Always resume them** or **Never resume them**.
4. Choose **OK**.

## The Station Catalog

Quill Radio 3.0 ships the working-station directory inside the app: more than 62,000 stations across 240 countries, plus SomaFM and the Project Gutenberg audio shelf. It keeps them in a catalog on your own computer. That is why browsing feels different in 3.0:

- **Browse answers at once, online or off.** By Country, By Language, By Genre and By Quality answer from your disk. A first launch with no internet at all is still a complete radio.
- **Every folder says its size before you open it**, such as "France, 812 stations".
- **Search starts locally.** Catalog matches appear the moment you search, and the live directories add theirs behind them.
- **A row that probably will not play says so.** Radio Browser checks every stream it lists. Rows it could not play are marked "may not be playable". Rows that must be looked up before they start, such as TuneIn and YouTube, say "resolved when you play it". Other rows are unmarked, because only Radio Browser publishes a check.
- **If you are offline, Quill Radio says so once**, such as "You are offline. Browsing from your catalog, updated this morning.", and keeps working.

### What is stored, and what is not

The catalog covers Radio Browser's stations and every way through them, SomaFM, and the Project Gutenberg audiobook shelf. The rest stays live and needs the internet, each for a reason: **Apple Podcasts** (Apple's terms bar storing its charts), **TuneIn** (a remote tree that may not be stored), **iHeart** (its terms do not allow storing its listings), the **Internet Archive** (too large), **LibriVox** (live for now), and the **music charts** (stale the moment they are stored).

In Browse Stations, the details box says it per branch: "Answers from your catalog, updated 2 hours ago" or "Asks the internet each time; nothing is stored."

### How it stays fresh

Three ways, each yours to switch off in Preferences:

- **Shortly after launch**, a quick background check, skipped when the catalog is already fresh.
- **On a schedule**, every 24 hours by default. You can choose 6 hours to 2 days, or Manually only. One source at a time, never a burst.
- **On demand**, with **Station > Update Station Catalog** (Ctrl+Alt+Shift+G). It always answers out loud, such as "Station catalog updated: 174 new stations, 431 updated."

A directory that is down costs you its freshness, never your stations. A source that suddenly answers with nothing is treated as an outage. A station that disappears is hidden at once but forgotten only after two weeks. **Popular** and **Trending** stay live first. When the directory cannot answer, the catalog's copy steps in, and every such row says "as of 2 hours ago".

### Station Catalog Status, step by step

1. Press **Ctrl+Alt+Shift+S** (**View > Station Catalog Status...**). Focus is in the **Sources and what is stored** list (Alt+S).
2. Arrow through it. Each source says what is stored and how fresh it is, such as "Radio Browser: 62,375 stations, updated 2 hours ago", or why it is live only, such as "iHeart: live only; its terms do not allow storing its listings".
3. Choose **Update Now** (Alt+U) to refresh now. The window closes and the update runs.
4. Or choose **Rebuild From Shipped Snapshot** (Alt+R) to put back the catalog that came with the app. **It does not ask first.** Your favorites and custom stations are never touched.
5. Press **Escape** to close.

Your favorites, custom stations, servers and YouTube channels live in their own files, and no catalog operation reads or writes them. Turning the catalog off in Preferences restores live-only browsing, with nothing stored and no background requests. Safe Mode never refreshes the catalog, but it may read it.

## Quick Actions

**Station > Quick Actions...** (Ctrl+Alt+Q) decides the order of the actions on the Browse Stations right-click menu, so the ones you use most come first. Enter on a row still does what it always has.

1. Press **Ctrl+Alt+Q**. The Quick Actions window opens.
2. **Actions for** (Alt+F) chooses the list: **Station actions** (rows you play) or **Browse folder actions** (folders).
3. Tab to **Order (first is at the top of the menu)** (Alt+O). Arrow to an action. The line below says what it does and its position.
4. Press **Alt+Up** or **Alt+Down** to move it, or Tab to **Move Up** (Alt+U), **Move Down** (Alt+D) or **Move to Top** (Alt+T). Quill Radio says its new number.
5. **Reset This List** (Alt+R) puts the chosen list back as it shipped. The other list is left alone.
6. Choose **OK** (Enter). You should hear "Quick Actions saved." Escape cancels.

It orders only what a row already offers, and never adds anything. A station already in your favorites still offers Remove, not Add, and a live stream still offers no Download.

## What each row says

A list is read one column at a time, so the columns are the sentence you hear on every row. **View > Choose Columns...** (Ctrl+Alt+Shift+C) decides it for the Find Stations results and the Radio Recordings list.

1. Press **Ctrl+Alt+Shift+C**. The Choose Columns window opens.
2. **Columns for** (Alt+F) chooses the list: Find Stations or Recordings.
3. Tab to **Shown, in the order they are read** (Alt+S). Arrow to a column.
4. Press **Alt+Up** or **Alt+Down** to move it, or use **Move Up** (Alt+U) and **Move Down** (Alt+D).
5. **Hide** (Alt+I) takes a column out of the row altogether. It moves to **Hidden (not read out at all)** (Alt+H). Select one there and choose **Show** (Alt+W) to put it back in its proper place.
6. **A row will read** (Alt+A) spells out the sentence one row will say with your settings, so you can hear the effect before you save.
7. **Reset This List** (Alt+R) puts the chosen list back as it shipped.
8. Choose **OK**. You should hear "Columns saved."

One column in each list is pinned, the station's name or the recording's name, because a row with nothing to identify it cannot be acted on. Asking to hide it says why not.

Some columns are offered but start switched off. Find Stations can also show **Language**, **Genres**, **Popularity** and **Bitrate**. Recordings can also show **Length**, which is blank where the only number is a safety cap.

If the Find Stations window is already open, close and reopen it to see new columns.

## Listening statistics

**View > Listening Statistics...** (Ctrl+Shift+Q) answers how much you listened, not just what.

1. Press **Ctrl+Shift+Q**. The Listening Statistics window opens.
2. **Period** (Alt+P) chooses This week, This month, This year or All time. It starts on All time. Changing it speaks the new total.
3. Tab to the report and arrow through it: the total time, how many sessions, then a breakdown **by station** and **by network**. Durations are read as words, such as "3 hours, 47 minutes".
4. **Copy** (Alt+C) copies the whole report. You should hear "Copied."
5. **Save as CSV...** (Alt+S) writes every session to a spreadsheet file. The suggested name is `quill-radio-listening.csv`.
6. **Delete My History...** (Alt+D) removes every session. It asks first, and **No is the default**.
7. Press **Escape** to close.

What counts:

- Only time when audio is actually coming out. Connecting, buffering, paused or stopped time does not count.
- Anything under ten seconds is not a session. Skipping past stations is not listening.

Your history stays on this computer.

## Handing an episode to QUILL Cast

Quill Radio finds and plays podcast episodes. Quill Cast, its sister app, is the full podcast player, with a play queue and an inbox. When you find an episode in Quill Radio that you want to hear later in Cast, hand it over in one step.

On an episode of a show you follow, in Browse Stations, the menu offers three handoffs:

- **Play Next in QUILL Cast** puts it at the top of Cast's queue. You hear "It will be next in the QUILL Cast queue."
- **Add to QUILL Cast Queue** puts it at the end. You hear "Added to the end of the QUILL Cast queue."
- **Send to the QUILL Cast Inbox** files it for you to decide about later. You hear "Sent to the QUILL Cast Inbox."

The same menu also has **Mark Episode as Played** or **as Unplayed**. Cast picks that up too.

1. Press **Ctrl+B** for Browse Stations. Open **Podcasts (Apple)**, then **Subscriptions**, then a show.
2. Arrow to an episode and press **Shift+F10**.
3. Arrow to one of the three handoffs and press **Enter**. You hear what will happen.
4. The next time you open Quill Cast, the episode is where you asked.

Good to know: these are handed over, not done at once. Quill Cast carries them out the next time it opens, which is why the confirmation says "will be". Asking twice for the same episode counts once. An instruction Cast has not picked up within a month is dropped. The handoffs appear only on episodes of shows you subscribe to, because Cast has to know the show.

## Bookmarks

**Bookmark This Moment** (Ctrl+Alt+A, **Playback** menu) marks where you are on whatever is playing, in one keystroke: a station, a recording, a saved YouTube row, or an episode from your subscriptions. No note is needed.

### Use bookmarks, step by step

1. While something plays, press **Ctrl+Alt+A**. You should hear that the moment was bookmarked.
2. Later, press **Ctrl+Alt+Shift+J** (**Help > Bookmarks...**). The Bookmarks window opens with focus in **Everywhere you marked** (Alt+E).
3. Arrow to a bookmark and press **Enter**, or choose **Go There** (Alt+G), to go back to it.
4. Other buttons:
   - **Share** (Alt+S) copies the place, the note and what it is in.
   - **Edit Note...** (Alt+N) adds or changes a note.
   - **Delete** (Alt+D) removes everything selected. Shift with the arrows selects several. It says how many it removed.
   - **Export...** (Alt+X) writes them all to a Markdown file, grouped by what each is in.
5. Press **Escape** to close.

**A live station's bookmark is honest.** Live radio has no shared timeline, so a station bookmark records the station and the time into your listening. Go There tunes in now. A recording, a video and a podcast episode do seek to the spot.

**The list is shared with QUILL Cast.** A bookmark you make here is in Cast's Bookmarks window, and the other way round. A bookmark Quill Radio cannot open still appears, with Go There dimmed and a reason.

## Skip Silence, and a speed that sticks

**Skip Silence** (Ctrl+Shift+9, **Playback** menu) shortens the long pauses in a recording, a YouTube row or a podcast episode as it plays. Use it to get through a slow-spoken talk or a recording with dead air, without making the voices faster. It takes effect at once. It has no effect on live radio, and says so if you turn it on while a station plays.

1. Play a recording, a podcast episode or a YouTube row.
2. Press **Ctrl+Shift+9**. You hear that Skip Silence is on.
3. Press **Ctrl+Shift+9** again to turn it off.

To change the speed as well:

1. Press **Ctrl+Shift+Up** to play faster, or **Ctrl+Shift+Down** to play slower. Each press says the new speed.
2. Press **Ctrl+Shift+0** to go back to normal speed.

**Play Faster is remembered by kind.** A speed you choose while a recording plays applies to every recording. One chosen on a YouTube row applies to YouTube rows. Podcast episodes keep their own speed per show.

## The ACB Media schedule

**Community > ACB Media Schedule...** (Ctrl+Shift+N) lists everything ACB has published for its ten channels, in one list, oldest first. Each row gives its date, start and end times, programme and channel, such as "Tuesday 4 August, 8:00 AM to 9:30 AM, Herbie's Community Cooking Corner, ACB Media 5". It opens on the next programme still to come. The programme on air now ends with "on now".

### Browse the schedule, step by step

1. Press **Ctrl+Shift+N**. The ACB Media Schedule window opens. It reads the schedule from ACB every time it opens.
2. The first control is a read-only summary. It says how many programmes are published, how far the schedule runs, when this copy was pulled from ACB (such as "Pulled from ACB just now, at 9:47 AM"), and whose clock the times are on. Arrow through it.
3. Tab to the filters:
   - **Search** -- every word must appear somewhere, so "blues tuesday" finds the Tuesday blues show.
   - **Date** (Alt+D) -- one date. Only dates with programmes are offered, each with a count.
   - **Channel** (Alt+H) -- one of the ten channels.
   Clearing a filter brings the whole schedule back.
4. Tab to the list of programmes. Arrow through it.
5. Press **Enter** to tune in to the programme's channel. The button says what it will do: **Play Now**, **Play This Channel Now**, or **Stop** when that channel is already playing.
6. Press **Shift+F10** for everything else a programme offers. The list's menu also has **Refresh the Schedule**, even when nothing is selected.
7. Press **Escape** to close.

The buttons below the list, in order: **Play**, **Record...**, **Remind Me...** (reads **Remove Reminder** when one is set), **Add to Queue**, **Copy Details**, **Show Notes...**, **Next Programme**, **Refresh** and **Export...**. The Search box and the Show Notes button share a letter, so use Tab to reach them.

What each does:

- **Play** tunes in to the channel. Live radio has one thing on at a time, so Quill Radio tells you whether the programme is on now or when it starts.
- **Record...** asks you to confirm the channel, date, time and length, then schedules it. **Yes is the default** here. It appears in Recordings and Upcoming like any other scheduled recording.
- **Remind Me...** asks how much warning you want. See "Reminders and Upcoming".
- **Add to Queue** puts the channel in the play queue. A queued live channel plays whatever is on when the queue reaches it.
- **Copy Details** copies what, when, which channel and the description.
- **Show Notes...** reads the programme's description.
- **Next Programme** moves to the next thing that has not finished.
- **Refresh** reads the schedule from ACB again.
- **Export...** writes what you are looking at, filters included, to a Markdown file.

A verb that cannot run is dimmed and says why. A programme that finished this morning cannot be recorded.

**Why the list can look short.** ACB publishes a fortnight of listings at a time and then stops. For part of any month, nothing is posted for today. The summary line says so plainly, such as "Nothing is published for today or later -- ACB last posted a schedule through 15 August." Nothing is broken. Press **Refresh** once ACB posts more.

**Times are shown on your clock.** ACB publishes in US Central time, and Quill Radio converts every programme to your own. When the two differ, the summary says so, such as "Times are shown in US Mountain Standard Time. ACB publishes in US Central time."

ACB sometimes lists the same programme twice under two ids. Quill Radio shows it once.

### What Is On Now, and Refresh the Schedule

These two answer without opening a window.

**What Is On Now** tells you, in one sentence, what is on across all ten ACB Media channels.

1. In the main window, press **Ctrl+Alt+H** (**Community > What Is On Now**).
2. You hear the programmes on air now, channel by channel. Nothing opens and focus does not move.
3. To tune in to one, press **Ctrl+Shift+N** for the schedule, where the programme on now ends with "on now", and press **Enter** on it.

It answers from the stored schedule, so it is instant, and it works offline.

**Refresh the Schedule** fetches the newest listings from ACB.

1. In the main window, press **F5** (**Community > Refresh the Schedule**). In the schedule window itself, use its **Refresh** button.
2. With the schedule window open, it reloads the list in place. With it closed, it fetches quietly and speaks the result.

Good to know: these keys belong to the main window's Community menu. In another Quill Radio window, press **Ctrl+Tab** until you are back in the main window first. In Browse Stations, the **Refresh** button reloads a source, not the schedule.

### Working offline

The schedule is kept on this computer. With no connection, the window opens from what it has and says how old it is. If the schedule cannot be read at all, you get an empty list and a sentence saying so, and the reason goes into Recent Problems. On the first of a month ACB has not posted yet, the window shows the previous month's listings, and the summary says how far they run.

## Reminders and Upcoming

### Set a reminder, step by step

Any programme in the ACB Media schedule, and any station, recording or saved row in Browse Stations, can carry a reminder.

1. Highlight the row and press **Shift+F10**. Choose **Set a Reminder...** (in the schedule, **Remind Me...**). The Set a Reminder window opens: "Remind me about" and the title.
2. **When** (Alt+W): for a programme, how much warning you want, from "When it starts" to "1 day before". For a station or recording, when to remind you, counted from now: In 15 minutes, In 30 minutes, In an hour, In 3 hours, or Tomorrow, at this time.
3. **Note (optional)** (Alt+N): anything you want said with the reminder. It never leaves this computer.
4. **Priority** (Alt+P): Normal or High. High is the only reminder that comes through quiet hours on its own. It is not louder, sooner or repeated.
5. Choose **OK**. You should hear "Reminder set for", the title and when.

Once a row has a reminder, the same menu slot reads **Remove Reminder**.

**When a reminder comes due**, Quill Radio plays the reminder sound (three rising bell tones), says what it is and when it starts, and shows a desktop notice with a **Go There** button. A reminder that came due while the app was closed is still said when you next open it, if that is within a couple of hours. Quiet hours can hold a reminder back; it is said when the quiet window ends.

In Preferences, **New reminders start at** sets the usual warning, and **Play a sound when a reminder comes due** turns the sound off. The reminder is still spoken either way.

### Upcoming, step by step

**Community > Upcoming...** (Ctrl+Alt+Shift+F) lists everything Quill Radio has planned: your reminders and your scheduled recordings, together, soonest first. Each row starts with its kind: "Reminder:" or "Recording:".

1. Press **Ctrl+Alt+Shift+F**. Upcoming opens. A summary is at the top, and focus is in **What is coming up** (Alt+W).
2. Arrow through the list.
3. Press **Enter**, or choose **Go There** (Alt+G), to open what the row is about. A recording opens **Schedule Recording**. A schedule programme opens the **ACB Media Schedule**. A station reminder tunes in. Upcoming then closes.
4. On a reminder, **Snooze...** (Alt+S) pushes it out by 5, 10 or 30 minutes from now. **Dismiss** (Alt+D) forgets it.
5. Press **Escape** to close.

Snooze and Dismiss work on reminders only. A scheduled recording is changed or cancelled in Schedule Recording, where Delete removes it at once.

## The Community menu

### Ask QUILL Radio: a conversation that knows what is playing

Ask QUILL Radio is the radio's own assistant. It runs on the ChatGPT plan you
already pay for -- there is no key to paste and no bill per question -- and it
knows one thing ChatGPT on the web does not: **what you are listening to**. The
station and the title the stream is announcing go with every message, so the
questions that matter on a radio need no names typed:

- "What is this song, and who made it?"
- "Tell me more about the artist playing now."
- "Tell me about this station: who runs it, where, and what it plays."
- "What kind of programmes does this station broadcast, and when?"
- "Is there a podcast like this one?"
- "This presenter mentioned a book. What was it?"
- "What was the news story they just referred to?" (with web search allowed)
- "Explain the rules of the sport they are commentating on."
- "This is in Spanish. What are they talking about?"

It is a conversation, so "and where can I hear more of them?" follows on from
the answer before. Nothing you ask changes what is playing.

**It works from text, not from sound.** Ask QUILL Radio never listens to the
stream, records anything or transcribes speech. What it knows is what the app
already knows in words: the station's name, and the title the stream announces
in its metadata when it announces one. If a station sends no titles, the
assistant knows the station and not the song, and says so. A question about
what a presenter just said is answered from what the model knows about the
programme, not from hearing it.

**Before the first question: sign in.** Ask QUILL Radio works one way, on your
ChatGPT subscription -- Plus, Pro, Team or Enterprise. See "Use My ChatGPT
Subscription, step by step" below. With no sign-in, Ctrl+Shift+8 says so and
opens that window instead.

### Ask QUILL Radio, step by step

1. Play something, or don't -- it answers either way, it simply knows more
   with a station on.
2. Press **Ctrl+Shift+8** (**Community > Ask QUILL Radio...**). The Ask QUILL
   Radio window opens with focus in **Your message**. It is a window of its
   own, on the Window menu and one Ctrl+Tab away, and the transport keys still
   work in it, so the player is never further away than usual.
3. **What it knows**, one Shift+Tab back, says what is on right now, which
   model answers, and whether web search is allowed. Arrow through it once.
4. Type a question and press **Enter**. You hear "Working.", then the reply is
   read aloud as it arrives, and it is added to **Conversation**, the read-only
   box above, where you can read it again word by word.
5. Or press **Ask About What's Playing** (Alt+P) and type nothing: it asks
   about the song and the station for you, and each press asks the next
   suggested question.
6. **New Conversation** (Alt+N) starts again. **Copy Last Reply** (Alt+L) puts
   the most recent answer on the clipboard. **ChatGPT Account** (Alt+G) opens
   the sign-in window. **Escape**, **Ctrl+W** or **Close** closes the window.

**Quick questions: the ones worth one keystroke.** Above Your message is a
**Quick questions** list (Alt+Q). Arrow through it freely; nothing happens
until you press **Enter** on the one you want, or **Use This Question**
(Alt+T). Then the question is put in the message box for you to send as it is
or change, focus moves there, and the Status line says what else, if anything,
will go with it. Six of them ask about what is playing and send nothing more:

- What is this song?
- Tell me about the artist playing now
- Tell me about this station
- What does this station broadcast, and when?
- Is there a podcast like this station?
- What is the title now playing about? (it translates a title in another language)

Three of them ask about *you*, and each says, before you send, exactly what it
attaches -- and how many:

- **Recommend stations like my favorites** sends the names of your favorite
  stations and their folders, up to sixty, and asks for five you do not have.
- **What have I been hearing on this station lately?** sends the songs Quill
  Radio has logged on the station playing, up to twenty-five, and asks what
  they add up to.
- **Suggest something new from everything I have played** sends the names of
  the stations you have played recently with a few songs from each, and asks
  for three stations or podcasts that would be new to you.

Nothing about you is sent unless you choose one of those three, and nothing is
sent at all until you press Enter. Every question is one request on your plan,
made when you ask and never on a timer.

Good to know: Ask QUILL Radio needs the internet, and it is off in Safe Mode.
What you ask counts toward your ChatGPT plan's own usage, which OpenAI enforces;
when a limit is reached, the window says so in words and **Open ChatGPT Usage**
in the account window shows when it resets.

### Use My ChatGPT Subscription, step by step

1. Press **Alt+F5** (**Community > Use My ChatGPT Subscription...**). The
   window opens on **About this**, which says where your questions go and what
   it costs. Arrow through it once.
2. Tab to **Continue with ChatGPT** and press it. Your browser opens on
   OpenAI's own sign-in page.
3. Sign in to ChatGPT there. On the page that asks whether **QUILL Radio** may
   use your plan, allow it. That is the name you will see under Apps in
   ChatGPT's settings from now on.
4. Come back to Quill Radio. The window says "Signed in with ChatGPT as" your
   email address, and focus lands on **Model**, a list of every model your plan
   offers, read from your account. The first is chosen for you; arrow to
   another and it is saved as you land on it. **Refresh Models** reads the
   list again.
5. **Allow web search** (Alt+W) is off until you check it. Press **Alt+W**
   then **Space**, and hear "Web search is allowed." On, the assistant may look
   things up on the web through OpenAI -- a station's schedule, a news story a
   presenter mentioned, a new release -- and tell you what it found. Saved as
   soon as you change it; Space again turns it off.
6. **Open ChatGPT Usage** (Alt+U) opens the plan's own usage page in your
   browser. **Sign Out** (Alt+O, press twice) asks OpenAI to revoke Quill
   Radio's sign-in and forgets it here. **Forget on This Computer** (Alt+F)
   forgets it here only, for a machine that is offline or a sign-in you already
   removed in ChatGPT's settings. Both appear only while you are signed in.
7. Press **Escape** to close.

If the browser did not open, the window says so and offers **Copy the Sign-In
Address**; paste it into any browser on this computer and finish there. **Stop
Waiting** gives up without changing anything.

Good to know: only a refresh token is kept, in Windows' credential store, under
Quill Radio's own name; your ChatGPT password is never seen by Quill Radio.
Each QUILL app signs in as itself -- Quill Radio, QUILL Lite and QUILL each
appear under Apps in ChatGPT's settings -- so signing one out leaves the others
as they were. There is no free QUILL AI service behind Ask QUILL Radio and no
API key to paste: it is your plan, or nothing, and the window says so.

### ACB Media Podcasts, step by step

1. Press **Ctrl+Alt+I** (**Community > ACB Media Podcasts...**). Quill Radio fetches ACB's podcast directory, then the window opens.
2. Focus is in the **Available** list. Arrow through it. The **Description** box below says what the highlighted show is about.
3. Press **Enter** or **Space** to add the highlighted show to **What you are adding**. **Add All** adds every one.
4. In What you are adding, **Move Up**, **Move Down**, **Remove** and **Sort A to Z** arrange your picks. Enter or Space on a pick removes it.
5. Choose **Add These** (Alt+T). The shows are subscribed or added to your favorites, and Quill Radio says what it did.
6. Press **Escape** to close without adding anything.

### Community Picks, step by step

**Community > Community Picks...** (Ctrl+Alt+0) is a curated list of stations and podcasts that listeners have suggested and Community Access has checked. Use it when you want a few good places to start, chosen by people rather than by a directory's ranking.

1. Press **Ctrl+Alt+0**. You hear "Reading the Community Picks list...", then the Community Picks window opens.
2. Focus is in the **Available** list. Arrow through it. The **Description** box, the next Tab stop, says what the highlighted pick is.
3. Press **Enter** or **Space** to put the highlighted pick in **What you are adding**, or Tab to the **Add** button. You hear "Added" and the name. **Add All** adds every one.
4. In What you are adding, use **Move Up**, **Move Down**, **Remove** and **Sort A to Z** to arrange your picks.
5. Press **Alt+T** for **Add These**, or Tab to it and press **Space**. Stations go into your favorites and podcasts are subscribed. Quill Radio says what it did.
6. Press **Escape**, or choose **Close**, to leave without adding anything.

Good to know: the list is fetched fresh each time and checked against Community Access's signature. If it cannot be fetched, or the signature does not match, Quill Radio uses the copy that came with the app instead, and notes why in Recent Problems. Something already in your library says so instead of being added twice.

### Suggest a Station or Podcast, step by step

Know a station or podcast other listeners should hear? Suggest it for the Community Picks list. Your suggestion goes by email to **support@community-access.org**, where a person at Community Access reads it. You do not need an account of any kind, and nothing is posted on a website. (Changed 2026-09-26: suggestions used to become public GitHub issues. They now go to support like every other message from Quill Radio.)

**What the window asks**

1. Press **Ctrl+Alt+9** (**Community > Suggest a Station or Podcast...**). The Suggest a Station or Podcast window opens. At the top it says where the suggestion goes and that nothing is sent until you press Send in your mail program.
2. **What is it** (Alt+W) is a list with two choices: **A radio station** or **A podcast**. Use the Up and Down arrows. It starts on A radio station.
3. **Name** (Alt+N): what it should be called in the list, such as "Radio Nowhere". This one is required, and it can be up to 120 characters.
4. **Address** (Alt+A): the stream address for a station, or the feed address for a podcast. It is required and must start with `https://` or `http://`. The easiest way to get it: press **Shift+F10** on the station in Quill Radio and choose **Copy Stream Link**, or on a podcast show choose **Copy Feed Address**, then paste it here with **Ctrl+V**.
5. **Description** (Alt+D): one or two sentences saying what it is, for somebody who has never heard it. Optional, up to 600 characters. Press **Tab** to leave this box; Enter starts a new line.
6. **Language** (Alt+L): such as `en` or `en-US`. Optional.
7. **Why it belongs** (Alt+H): anything that would help Community Access decide. Optional. Only the people who read the suggestion see it.

**Sending it**

1. Press **Alt+S** for **Send Suggestion**, or Tab to it and press **Space**.
2. Quill Radio checks what you typed first. If something needs fixing, it speaks the first problem and shows the whole list in a message. Press **Enter** to close the message, fix the field, and press **Alt+S** again. It catches a missing name or address, an address that does not start with `https://` or `http://`, an address with a space in it (usually a copy that did not paste whole), and a station or podcast that is **already in the Community Picks list**.
3. When everything is in order, your own mail program opens with a new email already written, and you hear "Your mail program has opened with your suggestion written. Press Send there." The Suggest window closes.
4. In your mail program, the email is addressed to support@community-access.org, with a subject such as "[Quill Radio 3.0.3] Suggestion: Radio Nowhere". Read it over if you like, add anything you want to say, and **press Send there**. Nothing leaves your computer until you do.

**If you have no mail program**

Some computers have no mail program set up, only webmail such as Gmail or Outlook.com in a browser. Then nothing can open, and Quill Radio says so: "No mail program answered. Write to support@community-access.org." The whole suggestion, with the address and the subject at the top, is put on your clipboard. Open your webmail, start a new email to **support@community-access.org**, and paste it into the message with **Ctrl+V**. The Suggest window stays open, so what you typed is still there.

A suggestion too long for a mail program to accept (usually a very long "Why it belongs") is shortened in the email, with a line saying so, and the complete text is put on your clipboard. Quill Radio tells you when this happens; select the email's text and paste the full version over it with **Ctrl+V**.

**What is included, and what is not**

- Included: exactly what you typed, whether it is a station or a podcast, and the app's name and version ("Quill Radio 3.0.3").
- Not included: your name, your Windows version, your screen reader, your favorites or listening history, or any file on your computer.
- Because the email goes from your own mail account, Community Access sees the address you send from, as with any email you write. It is not published anywhere.
- Nothing goes to GitHub or any other public site, and Quill Radio itself makes no connection to send it: your mail program does the sending.

**What happens next**

A person at Community Access reads every suggestion. If it fits the list, they add it, and it appears in **Community Picks** for everybody the next time the list is fetched, with no update needed. They may write back to ask a question or to tell you it was added.

**Closing without sending**

Press **Escape**, or choose **Close** (Alt+O). Nothing is written or sent.

Suggest a Station or Podcast is off in Safe Mode: it says "Safe Mode is on, so nothing is sent anywhere."

## Taking back the last thing you did

Press **Ctrl+Z** in the main window (**Edit > Undo Last Action**) and the last destructive thing you did comes back: an unsubscribe, a Remove All Downloads, a Mark All as Played, or a deleted recording. It says what it brought back, such as "Undid Unsubscribe. Brought back The Daily, with 412 episodes and 3 downloaded files."

1. Do something you regret, such as deleting a recording in Radio Recordings. Its announcement ends with "Ctrl+Z undoes this".
2. Press **Escape** or **Ctrl+Tab** until you are back in the main window.
3. Press **Ctrl+Z**. You hear what came back.
4. If there is nothing to take back, you hear "Nothing to undo".

Good to know:

- **It is one step, not a stack.** Undoing twice does nothing the second time, and says "Nothing to undo".
- **Deleted files come back.** A file Quill Radio deletes for you is moved aside first, so undo restores it. Once you do the next destructive thing, the one before is gone for good.
- **Anything it cannot bring back, it says so.** For example, a private feed's saved password is deleted when you unsubscribe; undo brings the subscription back and says the password must be entered again.

An action that can be undone ends its announcement with "Ctrl+Z undoes this". Ctrl+Z works in the main window. If you are in Browse Stations, press **Escape** or **Ctrl+Tab** to get to the main window first.

## Why a menu item is dimmed

Every dimmed item carries its reason. Screen readers that read menu help speak it, and the status bar shows it. For example:

- "Download All Episodes: nothing to download, all 40 are already here."
- "Mark All as Played: nothing to mark, all 63 episodes are already played."
- "Pause: this is live radio, which is going out now."

To hear the reason for a dimmed item:

1. Arrow to the dimmed item in the menu.
2. If your screen reader speaks menu help, the reason follows the item's name.
3. If it does not, press **Escape** to close the menu, then press **Ctrl+Shift+P**, type the command's name, and arrow to it. The Command Palette reads the reason in the list.

The Command Palette does the same: an unavailable command reads its reason instead of a bare "(unavailable)". Items dim rather than disappear, so you can always hear that a verb exists.

## Recent Problems

**Help > Recent Problems...** (Ctrl+Alt+Shift+P) lists what has failed recently, such as feeds that could not be read, downloads that died and streams that dropped, each with its reason and time. It exists because a spoken failure you missed would otherwise be gone.

1. Press **Ctrl+Alt+Shift+P**. Focus is in **What has failed recently** (Alt+W), newest first. With nothing in it, you hear "No recent problems".
2. Arrow through the list.
3. **Retry** (Alt+R) tries the highlighted problem again, such as playing a station or queueing a download again.
4. **Copy All** (Alt+C) copies the list as text, for a support message. It holds addresses and error messages, never passwords.
5. **Clear List** (Alt+L) empties it. It does not fix anything.
6. Press **Escape** to close.

Nothing in the list leaves this computer.

## Quiet hours

**Help > Quiet Hours...** (Ctrl+Alt+Shift+Z) sets a time window, 22:00 to 07:00 by default, in which Quill Radio stops speaking on its own.

1. Press **Ctrl+Alt+Shift+Z**. The Quiet Hours window opens.
2. Check **Quiet hours on** (Alt+Q) with Space.
3. Choose **From** (Alt+F) and **To** (Alt+T), in half hours. The window may cross midnight.
4. Check **Let reminders through anyway** (Alt+R) if you want every reminder to speak during quiet hours.
5. A line below says what the setting will do. Choose **OK**.

What it means exactly:

- Feeds are still checked, downloads still run and recordings still record. Only the announcements about them wait.
- **Anything you press a key for still answers.** Press Play at three in the morning and you hear what is playing.
- Failures always speak.
- A High priority reminder comes through on its own.

The window is shared with the other Quill listening apps, so you set it once. **Quiet Hours On/Off** in the Command Palette switches it quickly.

## Moving your setup to another machine

**Help > Export My Setup...** (Ctrl+Alt+Shift+X) writes one `.quillsetup` file carrying what you have built: subscriptions, folders and playlists, favorite stations and saved places, settings, your Go To order, your Quick Actions order, scheduled recordings, bookmarks and any keys you rebound. **Help > Import My Setup...** (Ctrl+Alt+Shift+N) puts them on the other machine.

1. On the old computer, press **Ctrl+Alt+Shift+X**. A confirmation says what will be written and that passwords are not included. Choose to continue.
2. Choose a folder and a name, and save. Copy the file to the new computer.
3. On the new computer, press **Ctrl+Alt+Shift+N** and choose the file.
4. A confirmation names what the file holds and says plainly that importing **replaces** what is on this computer. Choose to continue.
5. Close and reopen Quill Radio, so everything is read back in.

The file is an ordinary ZIP with a readable manifest. **Passwords are not in it**: private-feed sign-ins, server credentials and unlock codes stay on the old machine and must be entered again.

## Checking your subscribed podcasts

Quill Radio can ask every show you follow for new episodes.

**Ask once, for everything:**

1. In Browse Stations, open **Podcasts (Apple)** and highlight **Subscriptions**, or any folder in it.
2. Press **Shift+F10** and choose **Check All Feeds Now**. You should hear "Checking subscribed feeds...", then one summary at the end.

It checks paused shows too. **Refresh** on a single show asks just that one.

**Or have Quill Radio ask on its own.** In Preferences, under **Podcasts**:

1. Press **Ctrl+,** and Tab to **Check subscribed podcast feeds**.
2. Choose how often: Manually only (the default), or every 15 minutes up to once a day.
3. Optionally, check **Check subscribed podcast feeds at launch**.
4. Choose **OK**. Quill Radio says what it will now do.

Both are off to begin with, so the app never uses your data allowance on a schedule you did not choose. What an automatic check does:

- It reads episode lists only. Nothing is downloaded or queued, and nothing you are playing changes.
- A show you have paused is skipped.
- It speaks once at the end, counted and named. When it finds nothing, it says nothing.
- During quiet hours it still checks, and holds the summary.
- A check that fails goes into Recent Problems.

If you also run Quill Cast, the two apps share the record of when a check happened, so they do not ask the same publisher twice.

## What the main window shows

The middle of the main window can show one of five views. The menu bar, the Now playing line, Mute and Volume, and the status bar stay the same in every one.

1. Press **Ctrl+Shift+2** (**View > Main Window Shows > Browse Stations**). You should hear "Main window now shows Browse Stations", and a sentence about it. Focus is in the tree.
2. Use it as you would the Browse Stations window.
3. Press **Ctrl+Shift+1** to go back to your favorites.

The five views:

- **Favorite stations** (Ctrl+Shift+1) -- your own stations and folders. The default.
- **Browse Stations** (Ctrl+Shift+2) -- the tree of every source.
- **Search Stations** (Ctrl+Shift+3) -- the field-based search.
- **Radio Recordings** (Ctrl+Shift+4) -- everything you have recorded.
- **Player** (Ctrl+Shift+5) -- what is on, where you are in it, and the transport buttons.

The choice takes effect at once and is remembered. **Main window shows** in Preferences is the same setting. A view you have visited keeps its state, so Browse is still expanded when you come back. Pressing the key for the view you are already in puts focus back in it.

Everything is still its own window on demand. **Ctrl+B** still opens Browse and **Ctrl+F** still opens Search. When that surface is already your main view, the key takes you there instead of opening a second copy.

To leave a view, choose another one with Ctrl+Shift+1 to Ctrl+Shift+5. A view has no window of its own to close, so Escape in the Player view does not close Quill Radio.

If you used "Open Browse Stations at startup" in an older version, your main window now shows Browse, and nothing else opens by itself.

## Keyboard Shortcuts, the Sheet, and Global Hotkeys

### Keyboard access without chords

Every command in Quill Radio can be reached without holding several keys down at once, which matters on a braille notetaker such as the BrailleNote Evolve and for anyone for whom a three- or four-key chord is hard.

- **Every menu is one Alt+letter away, and every item in it has an access letter.** Press Alt and the menu's letter, then the item's letter: **Alt+Q, then W** opens Quill Weather; **Alt+S, then B** opens Browse Stations. Two keys, one after the other. A few items share a letter: pressing it again moves to the next item with it, and Enter chooses. The Station menu has more items than the alphabet has letters, so four of its items have a key but no letter: **Preferences** (Ctrl+comma), **Exit** (Ctrl+Q), **Connect to Spotify** (Ctrl+Alt+P) and **Browse Spotify** (Ctrl+Alt+O). A test checks on every build that no other enabled item is left without a letter.
- **Any key can be changed.** **Help > Keyboard Shortcuts...** (Ctrl+Alt+K) lists every command -- the QuillVille "Open" commands included since 3.0.3 -- and you can give any of them a shorter key, or one your notetaker can type. The menus show your key from then on.
- **The Command Palette** (Ctrl+Shift+P) finds any command by typing part of its name and pressing Enter.
- **The menus themselves always work**: Alt, then the arrow keys and Enter, one key at a time.
- **Windows' Sticky Keys** lets a chord be typed one key at a time: press Shift five times to turn it on.

### Change a key, step by step

**Help > Keyboard Shortcuts...** (Ctrl+Alt+K) opens the Keymap Editor, a searchable list of every command and its key.

1. Press **Ctrl+Alt+K**. The Keymap Editor opens with focus in **Search** (Alt+S).
2. Type part of a command's name, such as `record`. Or type a key, such as `Ctrl+B`, to see what it does. **Record Keys...** (Alt+R) lets you press the key instead of typing it.
3. Tab to the **Keyboard shortcuts** list and arrow to the command.
4. Choose **Edit Keybinding...** (Alt+E). A box opens with the current key.
5. Type the new key, such as `Ctrl+Shift+K`, and choose **OK**.
6. If the key is already in use, or is a risky one such as a plain letter, Quill Radio warns you and names the command that owns it.
7. Choose **OK** to close the editor. Menus show your new key at once.

The keymap is shared with QUILL and Quill Cast, so a key you change here changes there too. A few keys, such as Preferences on Ctrl+, and the transport keys, keep their old key until you next launch Quill Radio. Radio's own defaults sit on top of the shared keymap, so they never collide with QUILL's editor keys.

### The Keyboard Shortcuts Sheet, step by step

**Help > Keyboard Shortcuts Sheet...** (Ctrl+Alt+Shift+K) lists every key Quill Radio answers to, filterable.

1. Press **Ctrl+Alt+Shift+K**. Focus is in **Filter (a key, or what you want to do)** (Alt+F). You should hear how many shortcuts are listed.
2. Type what you want to do, such as `record`, or a key you cannot place, such as `Ctrl+B`. The list narrows as you type.
3. Press **Enter** to move into the list. Arrow through it. Each row says the key, what it does and where it works.
4. **Copy All** (Alt+C) copies the list as filtered. **Change Shortcuts...** (Alt+S) closes the sheet and opens the Keymap Editor.
5. Press **Escape** to close.

The sheet is built from the menus in front of you, so it shows the keys you actually have. Keys with no menu item, such as F6 into the status bar, the Winamp letters in Radio Recordings and Shift+F10 on a row, are listed too.

### Global Hotkeys, step by step

A global hotkey works while another program has focus.

1. Press **Ctrl+Alt+G** (**Help > Global Hotkeys...**). A list of commands opens, each with its global key or none.
2. Arrow to a command, such as **Radio: Play/Pause**, **Radio: Stop**, **Radio: Mute/Unmute**, **Radio: Volume Up** or **Radio: Volume Down**.
3. Choose **Assign...** (Alt+A) and give it a key. The first time, Quill Radio reminds you that a system-wide key may override the same key in another program.
4. **Clear** (Alt+L) removes a global key.
5. Choose **Save** to keep your changes, or **Cancel**.

None are assigned by default. The list is shared with QUILL, so it also shows rows such as New Sticky Note and Podcasts: Play/Pause, which do nothing in Quill Radio. Its first row, "Show/Hide QUILL to the tray", shows or hides Quill Radio when you assign it here. Only safe playback and window commands can have a global key. A key another program already owns is left alone.

Quill Radio's own show-and-hide key, **Ctrl+Alt+Shift+R**, is always on and is not in this list. See "The system tray".

## The Command Palette

**Ctrl+Shift+P** opens the Command Palette from any Quill Radio window. It lists every command by name.

1. Press **Ctrl+Shift+P**. Focus is in the search box, and you hear how many commands are available.
2. Type a few letters of what you want.
3. Arrow to a command. Each shows its own key.
4. Press **Enter** to run it. Escape closes the palette.

A command that cannot run now reads its reason. A check item names its state, such as "Announce Track Titles (currently On)". Some commands live only here: Copy What's Playing, Next Station in Folder, Previous Station in Folder, Extend Sleep Timer 5 Minutes, Cancel Sleep Timer, Quiet Hours On/Off, Repeat Last Announcement, Announcement Self-Test... and Redeem Unlock Code....

## Tutorials

**Help > Tutorials...** (Ctrl+Alt+F1) opens 41 guided tutorials, 281 steps in all, in six tracks: Your first hour, Finding something to listen to, Making it yours, Recording, More than radio, and Living with it. They are not a copy of this guide:

- **They show the keys you have.** Rebind a key and the tutorial says your key.
- **Try it runs the step for you.**
- **Follow me notices when you have done a step**, says what it saw, and reads the next one. It watches what changed in the app, never which key you pressed. It never takes the keyboard, and nothing is graded.

### Take a tutorial, step by step

1. Press **Ctrl+Alt+F1**. The Quill Radio Tutorials window opens with focus in **Find a tutorial (or type 'here' for this window)** (Alt+F).
2. Type words to narrow the list. Every word must appear somewhere in a tutorial, so "record tuesday" finds the scheduling lesson. Type **here** to list tutorials about the window you came from. Press **Enter** to move into the list.
3. The tree lists tutorials by track. Each row says how many steps, roughly how long, and whether you finished it. Arrow to one.
4. Press **Enter**, or choose **Start** (Alt+A). The lesson page opens with the first step in a read-only box.
5. Read the step. Choose **Try it** (Alt+T) to have the app do it, or do it yourself.
6. Check **Follow me** (Alt+M) to have the lesson notice when you have done each step.
7. Choose **Next** (Alt+N) to move on, **Back** (Alt+B) to go back, or **Say it again** (Alt+G) to hear the step again.
8. Choose **Contents** (Alt+C) to go back to the list.
9. Press **Escape** to close the window. Your place is kept.

The Tutorials window is a peer window. Leave it open, press **Ctrl+Tab** to the app, do the step there, and hear the lesson move on behind you. The transport keys work inside it.

On the contents page, **Read it all** (Alt+R) shows a whole tutorial as one page of text. **The whole book as a document** (Alt+D) opens every tutorial as one document. **Forget my progress** (Alt+P) clears which tutorials you finished and where you were, after asking.

The same lessons are in `tutorials.md` beside this guide, with the shipped keys.

## Help, updates and documents

### Context help (F1), step by step

1. On any control, in any window, press **F1**.
2. A help window opens. It says what the window you are in is for, then what the control under focus does and how to use it.
3. Arrow through the text. You can copy it.
4. Press **Escape**. Focus returns exactly where you were.

### Check for Updates, step by step

1. Press **Ctrl+Alt+U** (**Help > Check for Updates...**). You should hear "Checking for updates".
2. If there is nothing new, a message says "You are up to date" and your version. Press Enter to close it.
3. If there is an update, the Update Available window opens. Focus is in **What's new** (Alt+N), a read-only box with the release notes. Arrow through them.
4. Choose **Update** (Enter) to download it, with spoken progress. Or choose **Close** (Escape) to leave it for now.
5. When the download finishes, the **Update downloaded** window offers three choices:
   - **Install and restart now** (Enter): Quill Radio closes, the update is installed, and Quill Radio opens again, updated.
   - **Install when I close** (Alt+C): keep listening. The update is installed the next time you close Quill Radio, and the next time you open it, it is the new version. It does not reopen by itself.
   - **Open folder**, to find the downloaded file yourself, or **Close** (Escape) to leave it.

Quill Radio offers the download that matches your copy: the portable zip to a portable copy, and the installer otherwise. **A portable copy updates itself in place**: the new files replace the old ones in its folder, and the `data` folder -- your favorites, settings, history and recordings -- is never touched.

**Updating a portable copy from 3.0.0, 3.0.1 or 3.0.2.** Those three could not install their own portable update: they said "Could not install the update automatically" and left the zip in `data\updates`. Update them once by hand: close Quill Radio, unzip `Quill-Radio-Portable-3.1.1.zip`, and copy everything in its `QuillRadio` folder over your copy's folder, replacing files when asked. Your `data` folder is not in the zip, so it is left alone.

**Updating to 3.1.1 from 3.0.4 or earlier: once, by hand.** Up to 3.0.4 the small
helper program that installs an update was being shut down by Windows before it
could run, so **Install and restart now** closed Quill Radio and nothing else
happened. That helper is part of what 3.1.1 replaces, which means 3.0.4 cannot
install 3.1.1 for you. Do this one update yourself: download
`Quill-Radio-Setup-Shared-3.1.1.exe` from the releases page and run it, or, for a
portable copy, unpack `Quill-Radio-Portable-3.1.1.zip` over your folder as above.
Your favorites, settings, recordings and history are untouched. Every update
after this one installs itself.

**If Check for Updates keeps offering an update you have already installed.**
Up to 3.0.4 Quill Radio read its version number from the shared QuillVille
Runtime rather than from its own installer, and the runtime carries a copy of
every QuillVille app's version -- so on a computer with several of these apps the
number could be wrong, and Check for Updates then compared the wrong number.
From 3.1.1 the number comes from the installer that put Quill Radio there.
Install 3.1.1 by hand as above and the answer is right from then on.

Quill Radio also checks quietly once a day at launch. It speaks only when it finds something. Turn it off with **Check for updates automatically on launch** in Preferences.

### Audio Health, step by step

Audio Health answers "is this going to work?" in one list. It tests nothing: no sound is played, no device opened, no file written. It is safe to open during a recording.

1. Press **Ctrl+Alt+Shift+M** (**View > Audio Health...**). A headline sums up, and focus is in **What the radio is using right now** (Alt+W).
2. Arrow through the list. It covers: which playback engine is really in use (and whether Automatic has fallen back to Windows Media because mpv is missing), whether mpv and ffmpeg are present and what their absence costs, where the audio is going, what Sound Enhancements are doing, whether exact OptiLab is included, and whether a recording could be written to your recordings folder now.
3. **Check Again** (Alt+C) re-reads everything, for example after plugging in a headset. It speaks the headline.
4. **Repair FFmpeg...** (Alt+R) and **Repair mpv...** (Alt+M) are enabled only when that tool is missing.
5. Press **Escape** to close.

### Repair a missing tool

Both mpv and ffmpeg ship inside every copy of Quill Radio. If one goes missing, antivirus quarantine or an unfinished update is the usual cause. Quill Radio says so once at launch: which tool is gone, what it costs, and what to do.

- **Without mpv**, stations still play through Windows Media, but rewinding live radio, choosing the output device, Volume Boost, track titles from the stream and stall detection stop working, and Ogg Vorbis, Opus and HLS stations do not play at all.
- **Without ffmpeg**, recording and downloading stop working.

To repair:

1. Press **Ctrl+Alt+F** (**Help > Repair FFmpeg...**) or **Ctrl+Alt+M** (**Help > Repair mpv Playback Engine...**).
2. Confirm the download. Quill Radio fetches the official build and says when it is ready.

Reinstalling Quill Radio also restores both. A healthy installation says nothing about any of this.

### Other help

- **User Guide** (Ctrl+F1) opens this guide in your web browser. Use your browser's heading navigation to move between chapters, and Ctrl+F to find a word.
- **Release Notes** (Shift+F1) opens what is new in this version: what changed, what was fixed, and what to know when you upgrade.
- **Product Requirements...** (Alt+Shift+F1) opens the design record: what Quill Radio promises and why. You do not need it to use the app.
- **Get Help from Support...** (Ctrl+Alt+F2) -- see "Getting help".
- **About Quill Radio** (Alt+F1) -- the version, and where the project lives.
- **Repeat Last Announcement** (Command Palette) says the last thing Quill Radio told you, again.
- **Announcement Self-Test...** (Command Palette) announces a test phrase and reports which channels delivered it: speech, braille and sound. It tells "braille is not working" apart from "no braille display is connected".
- **Redeem Unlock Code...** (Command Palette) takes a signed code for a pre-release feature. It is checked entirely on your computer; nothing is sent. One code counts for QUILL, Quill Radio and Quill Cast together.

## Spotify (experimental)

Quill Radio can search Spotify, browse your library and playlists, and play through Spotify's own playback engine. This is **experimental and off by default**. When the Spotify feature is on, **Connect to Spotify...** (Ctrl+Alt+P) and **Browse Spotify...** (Ctrl+Alt+O) appear on the **Station** menu. Quill Radio has no switch of its own for it; it follows the Spotify feature in the feature settings it shares with QUILL. Nothing reaches Spotify until you connect an account. It is off in Safe Mode.

### Does a free Spotify account work?

**Yes for finding things; no for playing them inside Quill Radio.**

- On a free account you can search Spotify and browse your saved shows, episodes, tracks and playlists.
- You cannot have audio start inside Quill Radio. Spotify does not license other apps to stream free-tier audio: its Web Playback SDK and its Start/Resume Playback service both require Spotify Premium.

With a free account, let Quill Radio do the finding and play what you find in the Spotify app. Quill Radio tells you which kind of account you signed in with straight away.

A Spotify selection can never be recorded or downloaded, on any account: the audio is copy-protected.

### What you need

- A Spotify account. Free searches and browses; only Premium plays.
- Your own Spotify **Client ID**. Quill Radio ships no Spotify app identity, so nothing of yours passes through anyone else's. There is no client secret to copy.
- Windows with the Microsoft Edge WebView2 runtime, which current Windows already has.

### Get your Client ID, step by step

1. Go to the Spotify Developer Dashboard at `https://developer.spotify.com/dashboard` and sign in with your ordinary Spotify account. It is free.
2. Choose **Create app**.
3. Give it any **App name** and **App description**, such as "Quill Radio".
4. In **Redirect URI**, enter exactly `http://127.0.0.1:43217/callback` and choose **Add**. It must match character for character.
5. Under **Which API/SDKs are you planning to use?**, check **Web API** and **Web Playback SDK**.
6. Accept the terms and choose **Save**.
7. Open your app's **Settings** and copy the **Client ID**. You do not need the Client secret; do not paste it anywhere.

### Connect, step by step

1. Press **Ctrl+Alt+P** (**Station > Connect to Spotify...**). An accessible sign-in window opens.
2. Paste your Client ID into **Client ID** and choose **Connect**.
3. The first time, Quill Radio asks once for permission to use the network.
4. Your web browser opens Spotify's own approval page. Approve access.
5. Spotify sends you back to a local address on your own computer (`127.0.0.1`) that Quill Radio listens on for that one moment. Quill Radio says you are connected, and which kind of account it is.

Your sign-in is stored in the Windows credential vault, never in a plain file or a log.

### Browse and play, step by step

1. Press **Ctrl+Alt+O** (**Station > Browse Spotify...**). A search box opens with a results list.
2. Type what you are looking for and press Enter.
3. Arrow to a result and press **Enter** to play it.

A Spotify item plays through a hidden Spotify player, alongside Quill Radio's normal engines. Play and Stop, volume, the status bar, the tray and any global hotkeys all work on it.

## Hardware media keys

Many keyboards and headsets have media keys: Play/Pause, Stop, Next and Previous. Quill Radio listens for two of them system-wide while it runs, even when another program has focus and even when Quill Radio is hidden in the tray. That makes it an appliance: you can start and stop the radio without finding its window.

- The **Play/Pause** key starts or stops the radio. On live radio it does not pause, because live radio cannot be paused. It works like Play and Stop in the main window: from idle it plays your selected favorite.
- The **Stop** key stops whatever is playing.

To try it:

1. Start Quill Radio, then switch to another program, such as your email.
2. Press the **Play/Pause** media key. The radio starts, and you hear what is playing.
3. Press it again, or press **Stop**, to stop the radio.

Good to know: the Next and Previous keys are not used. Media keys are first come, first served on Windows. If another program, such as a music player, already owns a key when Quill Radio starts, that key stays with the other program and Quill Radio says nothing. Close the other program and restart Quill Radio to take the key. You can also give any playback command a system-wide key of your own in **Help > Global Hotkeys...** (Ctrl+Alt+G).

## The system tray

Quill Radio keeps an icon in the notification area while it runs.

### Use the tray, step by step

1. Press **Windows+B** to move to the notification area.
2. Arrow to the **Quill Radio** icon. If you do not find it, press Enter on the "Show hidden icons" button first.
3. Press the **Applications** key, or **Shift+F10**, to open its menu.
4. The menu offers, in order: **Show Quill Radio**, a dimmed line saying what is playing, **Play** (or **Stop**), **Pause** (or **Resume**, dimmed on live radio), **Mute/Unmute**, **Play Favorite Station...**, **Recently Played**, **Record Now** (or **Stop Recording**), **Schedule Recording...**, **Recording Settings...**, **Stop All Recordings** (when two or more are running), **Browse Stations...**, **Open QUILL**, **Open Quill Weather**, and **Exit Quill Radio**.
5. Arrow to one and press **Enter**.

To bring the window back, choose **Show Quill Radio** on this menu, or double-click the icon.

### Show and hide from anywhere

**Ctrl+Alt+Shift+R** shows or hides Quill Radio from any program. Press it while the window is showing, and Quill Radio hides to the tray and says "Quill Radio hidden to the tray". Press it again, and the window returns with focus and says "Quill Radio shown." Playback and recordings keep running. This key hides the main window only. **Send to Tray** (Ctrl+W) hides every Quill Radio window.

If another program already owns Ctrl+Alt+Shift+R, Quill Radio does not take it, and says nothing. Use the tray icon instead. Each family app uses its own key: QUILL is Ctrl+Alt+Shift+Q and Quill Weather is Ctrl+Alt+Shift+W.

Launching Quill Radio again while it is running, even hidden in the tray, brings the running copy forward instead of starting a second one.

## Closing Quill Radio

- **Station > Exit** (Ctrl+Q), and **Exit Quill Radio** on the tray menu, quit at once. They never ask, even during a recording, and the recording stops.
- **The title bar's close button and Alt+F4** follow **When closing the window** in Preferences:
  - **Ask every time** (the default) asks only while a recording is running. Otherwise the window just closes and Quill Radio exits.
  - **Exit** always exits.
  - **Minimize to Tray** always hides to the tray, still playing.
- **Alt+F4 minimizes to the system tray**, in Preferences, makes Alt+F4 alone hide to the tray, still playing, whatever the setting above says.

When Quill Radio asks, the window "Closing Quill Radio" says a recording is in progress and that exiting stops it:

1. Choose **Exit** (Enter) to quit, **Minimize to Tray** (Alt+M) to keep it running, or **Cancel** (Escape).
2. Check **Don't ask me again** (Alt+D) first to make your choice the setting.

Closing any window other than the main one never stops playback.

## Quillins in Quill Radio

Quillins are QUILL's small, sandboxed add-ons. A Quillin says which apps it is for, so only ones written for Quill Radio load here. They still load and contribute in this release, for example the bundled Radio Community Directory, which adds a directory to Find Stations and a branch to Browse Stations.

The Quillins menu itself is held back from this release, so there is nothing to install or configure from Quill Radio. What a bundled Quillin adds simply appears where it belongs. Quillins are off in Safe Mode, which is one way to tell whether a problem comes from one.

### Quillin station sources

A Quillin can contribute a whole station source. When one is installed and enabled, a **Quillin Sources** branch appears in Browse Stations, with one folder per contributed source. Its stations play, favorite and search like anything else. The branch is absent otherwise.

## Sharing data with QUILL

An installed Quill Radio reads and writes the same data store as QUILL and Quill Cast (`%APPDATA%\Quill`): favorites (with folders, custom names and per-station volumes), history, recordings, schedules, timers and settings. A station you favorite here is a favorite in QUILL's radio. Uninstalling Quill Radio never deletes that shared data.

What that means in practice:

- **Set up once.** Favorites you built in QUILL's radio are already in Quill Radio the first time it opens, and the welcome screens are skipped.
- **Podcasts are shared with Quill Cast.** A show you subscribe to in Browse Stations is in Cast's library, and your place in an episode is known to both apps.
- **Bookmarks and quiet hours are shared.** Set them in either app.
- **Keys are shared.** A key you rebind in the Keymap Editor changes in QUILL and Quill Cast too, where they have the same command.

A portable copy keeps its own data in its `data` folder and shares nothing with the computer it runs on.

To keep your data somewhere else, such as a folder that OneDrive or Dropbox keeps in sync, use **Data Folder...** in Preferences. See "Preferences".

## Weather

Weather is its own app, **Quill Weather**, and has its own guide. Open it from the **QuillVille** menu (Ctrl+Alt+Shift+F8). Quill Radio has no Weather menu.

What stays in Quill Radio is the radio part of weather: the **Weather / NOAA** branch of Browse Stations, with every NOAA Weather Radio transmitter that has an internet feed.

### Find your local NOAA Weather Radio, step by step

1. Press **Ctrl+B** and arrow to **Weather / NOAA**. Press **Right arrow**.
2. Arrow to your state and press **Right arrow**. Each transmitter reads with its call sign, frequency and place.
3. Press **Enter** on one to play it.
4. Or press **Ctrl+F** and type a call sign, a SAME code, or "County, ST", such as `Fairfax, VA`, and press Enter.

## Television

Quill Radio plays television the way it plays everything else. Pick a channel, press Enter, and it plays with the same captions, audio-track choice and transport keys as any stream.

**Television (iptv.org)** is built on the iptv.org community catalog of publicly available TV streams: roughly 9,300 playable channels. Channels flagged adult, channels that have closed, channels with no stream, and streams that would fail are left out.

### Watch a channel, step by step

1. Press **Ctrl+B**, arrow to **Television (iptv.org)** and press **Right arrow**.
2. Choose **By Country** or **By Category** and press **Right arrow**.
3. In By Country, a country with local coverage, such as the United States, opens into **Nationwide** and its states. A state lists its own channels and its cities' channels, each with its city.
4. Arrow to a channel and press **Enter**. It plays as audio.
5. Press **Ctrl+Shift+V** to show the picture. See "Show the video".

Worth knowing:

- **Search understands places.** Anywhere you can search, TV answers by channel name, network, country, city, state or five-digit ZIP code. Typing 66044 answers with Kansas television.
- **"Which channels can my antenna receive? (antennaweb.org)"** opens antennaweb.org in your browser.
- **The channel list updates itself weekly.** **"Update the channel list now"**, at the top of the branch, fetches today's copy.

### Your own TV guide

Put an XMLTV programme guide named `tv_guide.xml` in your Quill Radio data folder, and every channel the guide covers gains a line in its details: "Now: ... Next: ...". The file is read locally and never fetched from anywhere. Replace it and it is read again. Delete it and the lines disappear.

1. Get an XMLTV file for your area from a guide service you trust. Quill Radio does not supply one.
2. Rename it `tv_guide.xml`.
3. Copy it into your Quill Radio data folder. For an installed copy that is `%APPDATA%\Quill`; type that into File Explorer's address bar to go there. For a portable copy it is the `data` folder beside `QuillRadio.exe`.
4. In Browse Stations, arrow to a channel the guide covers. The details box, after the tree, now has a "Now: ... Next: ..." line.

## Dependencies, honestly stated

- **Playback** uses the bundled **mpv** engine, with the Windows Media Player engine built into Windows as a fallback and as the "classic" choice. Nothing downloads at runtime. Together they play MP3, AAC and HE-AAC, Ogg Vorbis, Opus, FLAC and HLS. A station one engine cannot open is tried on the other before you hear an error.
- **Recording**, and Sound Enhancements on the classic engine, use the bundled **ffmpeg**. On the classic engine, Sound Enhancements plays through a small relay on your own computer that nothing outside can reach. On the mpv engine the filters run inside the player.
- **Station search and browsing** talk to public directories, all keyless and account-free: RadioBrowser, SomaFM, iHeart, TuneIn, SHOUTcast, Live365, Radio Paradise, a community M3U catalog on GitHub, iptv.org, the Internet Archive, LibriVox, Project Gutenberg, AudioPub, Audius, Mixcloud, ccMixter, Apple's podcast storefront and Podcast Index. Xiph and Wikidata ship switched off. **Choose Browse Sources** lists every one, each saying whether it is on. A branch that is off is never contacted while you browse, and not for its catalog refresh either. **Search All Sources** asks every directory.
- **Podcast Index** is on by default. It is the one directory here that needs a key, and Quill Radio ships its own. The key identifies the app, not you.
- **Things that happen without you pressing anything:** a quiet check for updates once a day at launch (one request to GitHub, with no version or machine details sent); the station catalog refresh; and, while a station plays, re-reading the track title from the stream you are already listening to. Each has a switch in Preferences.
- **Playing a RadioBrowser station tells RadioBrowser.** That is its community play count, which ranks its stations. It sends the station's id and nothing about you, only for RadioBrowser's own stations. Turn it off with **Share play counts with the RadioBrowser directory** in Preferences.
- **Find Streams** fetches only the one page you give it, following its Listen Live link one level, plus one lookup to a player's own address service when needed. **Stream recovery** does the same automatically for a failing station, when its setting is on. **What's Playing** reads the stream you are playing, and as a last resort that same server's status page.
- **What Quill Radio has none of:** no account, no sign-in, no advertising, no tracking, no analytics, no usage reporting, and no unique identifier for your copy or computer. Nothing you type, write or record is sent anywhere. Every network call the app can make is listed in QUILL's network audit, which the build checks. All network features are off in Safe Mode.
- **NOAA Weather Radio** uses the keyless WeatherIndex directory (api.wxindex.org) when online, with the whole directory bundled as an offline fallback. **Radio Reading Services** refreshes from RadioBrowser, with its own bundled list as the fallback. The **ACB Media** directory is bundled.

## Keyboard reference

Every menu item shows its own key, and shows the key you actually have if you rebound it. For every key at once, press **Ctrl+Alt+Shift+K** for the Keyboard Shortcuts Sheet. The lists below are the ones worth knowing, by task.

### Menus in the main window

- Station menu: Alt+S
- Edit menu: Alt+E
- View menu: Alt+V
- Playback menu: Alt+P
- Audio menu: Alt+A
- Video menu: Alt+D
- Record menu: Alt+R
- Community menu: Alt+C
- QuillVille menu: Alt+Q
- Help menu: Alt+H
- Window menu: Alt+W

In every other window, Alt+S is the Station menu and Alt+W the Window menu. See "The menus in other windows".

### Playing

| Action | Key |
| --- | --- |
| Play the selected favorite, or stop | Enter (in the list), or Ctrl+P |
| Pause or resume something with a timeline | Ctrl+Space |
| Stop outright | Ctrl+. |
| Play favorites 1 to 10 | Alt+1 to Alt+0 |
| Play Favorite Station (a list of all of them) | Alt+Shift+F |
| Play Last Station | Ctrl+L |
| Recently Played, newest (inside the menu) | Alt+Shift+1 |
| Add or remove the playing station as a favorite | Ctrl+Shift+F |
| Rewind or forward 30 seconds | Ctrl+Shift+Left / Ctrl+Shift+Right |
| Back to Live | Ctrl+Shift+L |
| Continue Listening | Ctrl+Alt+Shift+L |
| Chapters | Ctrl+Shift+C |
| Next or previous chapter | Ctrl+Shift+. / Ctrl+Shift+, |
| Play faster, slower, normal speed | Ctrl+Shift+Up / Ctrl+Shift+Down / Ctrl+Shift+0 |
| Skip Silence | Ctrl+Shift+9 |
| Where Am I? | Ctrl+Shift+W |
| Go to Position | Ctrl+Alt+J |
| Go to Player | Ctrl+Shift+G |
| What's Playing? | Ctrl+T |
| Song History | Ctrl+Shift+H |
| Bookmark This Moment | Ctrl+Alt+A |
| Sleep Timer | Ctrl+Shift+Z |
| Wake-Up Timer | Ctrl+Alt+Z |

### Volume and sound

| Action | Key |
| --- | --- |
| Volume up or down, in steps of 10 | Ctrl+Up / Ctrl+Down |
| Mute or unmute | Ctrl+M in the main window; Ctrl+Shift+O in every window |
| Volume Boost | Ctrl+Shift+B |
| Output Device | Ctrl+Shift+D |
| Use One Volume for All Stations | Ctrl+Alt+V |
| Forget Every Station's Own Volume | Ctrl+Alt+Shift+V |
| Announce Track Titles | Ctrl+Alt+T |
| Sound Enhancements | Ctrl+E |

### Video

| Action | Key |
| --- | --- |
| Show or hide the video | Ctrl+Shift+V |
| Captions on or off | Ctrl+Shift+K |
| Caption Settings | Ctrl+Shift+Alt+T |
| Video Information | Ctrl+Shift+I |
| Take a Snapshot | Ctrl+Shift+Alt+H |
| Full screen | F11 |
| Video Size: Fit, 50%, 100%, 200% | Ctrl+Alt+4 / 5 / 6 / 7 |
| Audio and Described Audio | Ctrl+Shift+A |
| Play Described Audio | Ctrl+Alt+D |
| Transcript | Ctrl+Shift+T |

### Finding stations

| Action | Key |
| --- | --- |
| Browse Stations | Ctrl+B |
| Search Stations | Ctrl+F |
| Find in this folder (inside Browse Stations) | Ctrl+F |
| Add Custom Station | Ctrl+N |
| Add YouTube Link | Ctrl+Alt+N |
| Add from YouTube Playlist | Ctrl+Shift+Y |
| Import YouTube Subscriptions | Ctrl+Alt+Shift+Y |
| Repair YouTube Support | Ctrl+Alt+Y |
| Find Streams from a Website | Ctrl+Alt+S |
| Search Sources | Ctrl+Alt+Shift+U |
| Choose Browse Sources | Ctrl+Shift+Alt+O |
| Update Station Catalog | Ctrl+Alt+Shift+G |
| Update Radio Reading Services | Ctrl+Alt+F10 |
| Station Catalog Status | Ctrl+Alt+Shift+S |

### Favorites

| Action | Key |
| --- | --- |
| Manage Favorites | Ctrl+Shift+M |
| New Folder | Ctrl+Shift+E |
| Rename (in a tree) | F2 |
| Remove (in a tree or list) | Delete |
| Move the selected favorite up or down | Alt+Shift+Up / Alt+Shift+Down |
| Sort: A to Z, Z to A, manual | Ctrl+Alt+Shift+F4 / F5 / F6 |
| Expand or collapse all folders | Ctrl+Alt+E / Ctrl+Alt+Shift+E |
| Quick Actions | Ctrl+Alt+Q |
| Import Stations from Playlist | Ctrl+I |
| Export Favorites to Playlist | Ctrl+Shift+X |
| Back Up Stations and Settings | Ctrl+Shift+U |
| Restore from Backup | Ctrl+Alt+Shift+W |

### Recording

| Action | Key |
| --- | --- |
| Record Now or Stop Recording | Ctrl+R |
| Record Station | Ctrl+Alt+R |
| Stop All Recordings | Ctrl+Alt+X |
| Schedule Recording | Ctrl+Shift+S |
| Recordings | Ctrl+Shift+R |
| Recording Settings | Ctrl+Alt+Shift+I |
| Downloads | Ctrl+Shift+J |

### Community

| Action | Key |
| --- | --- |
| Ask QUILL Radio | Ctrl+Shift+8 |
| Use My ChatGPT Subscription | Alt+F5 |
| ACB Media Schedule | Ctrl+Shift+N |
| What Is On Now | Ctrl+Alt+H |
| Upcoming | Ctrl+Alt+Shift+F |
| Refresh the Schedule | F5 |
| ACB Media Podcasts | Ctrl+Alt+I |
| Community Picks | Ctrl+Alt+0 |
| Suggest a Station or Podcast | Ctrl+Alt+9 |

### Windows and views

| Action | Key |
| --- | --- |
| Go To (a numbered list of places) | Ctrl+G |
| Next or previous window | Ctrl+Tab / Ctrl+Shift+Tab |
| Jump to open window 1 to 9 | Ctrl+1 to Ctrl+9 |
| Close the window you are in | Escape, Ctrl+W, or Ctrl+F4 |
| Main window shows: favorites, Browse, Search, Recordings, Player | Ctrl+Shift+1 to Ctrl+Shift+5 |
| Into or out of the status bar | F6 |
| Show or hide the status bar | Ctrl+Shift+Alt+B |
| Show Station Details | Ctrl+D |
| Text Size: Normal, Large, Larger | Ctrl+Alt+1 / 2 / 3 |
| Listening Statistics | Ctrl+Shift+Q |
| Choose Columns | Ctrl+Alt+Shift+C |
| Audio Health | Ctrl+Alt+Shift+M |
| Customize Features | Ctrl+Alt+C |
| Send to Tray | Ctrl+W |
| Show or hide from any program | Ctrl+Alt+Shift+R |
| Preferences | Ctrl+, |
| Download Preferences | Ctrl+Alt+Shift+D |
| Resume Last Station on Launch | Ctrl+Alt+L |
| Start Quill Radio with Windows | Ctrl+Alt+W |
| Exit | Ctrl+Q |

### Help and tools

| Action | Key |
| --- | --- |
| What Is This? (context help) | F1 |
| User Guide | Ctrl+F1 |
| Release Notes | Shift+F1 |
| Product Requirements | Alt+Shift+F1 |
| About Quill Radio | Alt+F1 |
| Tutorials | Ctrl+Alt+F1 |
| Command Palette | Ctrl+Shift+P |
| Keyboard Shortcuts (Keymap Editor) | Ctrl+Alt+K |
| Keyboard Shortcuts Sheet | Ctrl+Alt+Shift+K |
| Global Hotkeys | Ctrl+Alt+G |
| Undo Last Action | Ctrl+Z |
| Recent Problems | Ctrl+Alt+Shift+P |
| Quiet Hours | Ctrl+Alt+Shift+Z |
| Bookmarks | Ctrl+Alt+Shift+J |
| Export My Setup / Import My Setup | Ctrl+Alt+Shift+X / Ctrl+Alt+Shift+N |
| Get Help from Support | Ctrl+Alt+F2 |
| Repair FFmpeg | Ctrl+Alt+F |
| Repair mpv Playback Engine | Ctrl+Alt+M |
| Check for Updates | Ctrl+Alt+U |

**Nothing here sits on Ctrl+Alt+arrow.** That block belongs to JAWS's and NVDA's table navigation. Speed and chapters moved off it in 3.0, to Ctrl+Shift+Up and Down and Ctrl+Shift+comma and period. If you have notes from an earlier version, those are the keys that changed.

## Getting help

Support is run by **Community Access**. Write to **support@community-access.org** with questions, problems, ideas or suggestions. A person reads every message, and replies come by email.

Every kind of feedback from Quill Radio goes to that one address: **Get Help from Support**, **Report Bad Station** and **Suggest a Station or Podcast**. None of them is posted on GitHub or any other public site. (Changed 2026-09-26. Earlier versions filed some reports as public GitHub issues.)

### Get Help from Support, step by step

**What the window asks**

1. Press **Ctrl+Alt+F2** (**Help > Get Help from Support...**). The Get Help from Support window opens. At the top it says the message goes to support@community-access.org and that nothing is sent until you send it from your mail program.
2. **What kind of message** (Alt+W) is a list: Something is broken, A question, An accessibility problem, or An idea or request. Use the Up and Down arrows. It only helps route your message; say anything you like below.
3. **Subject** (Alt+U): a short line saying what this is about, the way an email subject does, such as "Recording stops after an hour". Required.
4. **What happened** (Alt+H): describe it in as much or as little detail as you like. This is the part a person reads first. Required. Enter starts a new line; press **Tab** to move on.
5. **What you expected** (Alt+X): what you thought would happen instead. Optional.
6. **Steps to reproduce** (Alt+R): how somebody else could make it happen, such as "Play BBC Radio 4, press Ctrl+R, wait an hour". Optional, and worth more than anything else when you can give it.
7. **Your email address** (Alt+E): where support should reply. Optional. The message goes from your own mail account, so support can answer that address anyway; fill this in only if you want the answer somewhere else.
8. **Screen reader** (Alt+A): which one you use, if any. It is filled in from the screen reader that is running, so usually you can leave it.
9. Below the fields, a line says what else is included, such as "Also included: Quill Radio 3.0.3, and your Windows version."

**Sending it**

1. Press **Enter**, or Tab to **Send** and press **Space**.
2. If the subject or What happened is empty, or the email address does not look right, the first problem is spoken and the whole list is shown. Press **Enter** to close it, fix the field, and send again.
3. Otherwise your own mail program opens with the whole message written, addressed to support@community-access.org, with a subject such as "[Quill Radio 3.0.3] Recording stops after an hour". You hear "Your mail program is opening with the message ready. Nothing is sent until you send it there." The Get Help window closes.
4. **Press Send in your mail program.** Nothing leaves your computer until you do.

**If you have no mail program**

On a computer with only webmail, nothing can open, and Quill Radio says "No mail program answered. Write to support@community-access.org." The whole message, with the address and subject at the top, is on your clipboard. Start a new email to **support@community-access.org** in your webmail and paste it with **Ctrl+V**. The Get Help window stays open with what you typed.

A very long message is shortened in the email, with a line saying so, and the complete text goes on your clipboard. Quill Radio says when this happens; paste the full text over the shortened one with **Ctrl+V**.

**What is included, and what is not**

- Included: what you typed, the kind of message, Quill Radio's name and version, your Windows version, and the screen reader you chose.
- Not included: your favorites, recordings, listening history, passwords, or any file. If support needs more, they will ask, and **Copy All** in **Recent Problems** (Ctrl+Alt+Shift+P) gives them the details without any passwords.
- It is an ordinary email from your own account to Community Access. Nothing is posted publicly, and Quill Radio itself makes no connection to send it.

**What happens next**

A person at Community Access reads it and replies by email, usually to the address you sent from. Press **Escape**, or choose **Cancel**, to close the window without writing anything.

**Report Bad Station** (Shift+F10 on a station in Browse Stations or Search Stations) opens this same window with the station's name, stream, source and country already filled in. It never includes your name, email or file paths.

Writing to support@community-access.org yourself, from any email account, works just as well.

## Troubleshooting

### The sound card does not switch

Choose the device in **Audio > Output Device...** (Ctrl+Shift+D) and listen for the announcement. "Output device" and its name means the station moved. "... could not be opened, so the output device is back to ..." means Windows would not open that device for Quill Radio just now: wake the headset, close whatever else is using the card, or plug it back in, then choose it again. "The playback engine is the classic Windows Media control" means this machine has no modern media player, so the list cannot move the sound on that engine; Windows' Sound settings open in the same breath, so give Quill Radio its device there under Volume mixer, or set **Playback engine** to Automatic in Preferences to choose it here. "Windows Media is playing this station, and it cannot use the chosen output device" means the station itself would not play on the mpv engine, so it is on Windows Media for now; try the station again, or another stream of it. Before 3.1.1 none of this was said, which is why a card that would not open looked like a switch that did nothing. Check the row you chose, too: Windows calls both a laptop's built-in card and a USB headset "Speakers", and only the make in brackets tells them apart.

### If Quill Radio does not start

From 3.0.4, `QuillRadio.exe` never fails silently. If the app's engine cannot start, or stops with an error, a plain message opens that your screen reader reads on its own. It says "Quill Radio did not start" (or "stopped unexpectedly", if it had been running a while), gives the reason in words, names the file where the details are, and gives the support address.

- **The message says the zip was opened from inside.** You pressed Enter on `QuillRadio.exe` while still inside the zip, so only that one file was copied out. Select the zip in File Explorer, press the Applications key, choose **Extract All...**, and open `QuillRadio.exe` from the extracted folder.
- **The message says a file is missing, or a DLL could not be found.** Extract the whole zip again into an empty folder, and check your antivirus program's quarantine for anything it took from the Quill Radio folder.
- **The message says Windows refused to run its files, or access was denied.** Move the folder somewhere you own, such as Documents, or a USB stick, and check antivirus and any application-control setting.
- **The message says a file is damaged, or the wrong kind for this computer.** Quill Radio needs 64-bit Windows 10 or 11. Download the zip again.
- **The message says "Python reported", followed by an error.** Send the launch log to support; the next paragraph says where it is.
- **Nothing at all happens, and no message.** A Quill Radio is probably already running, in the tray, and the new launch handed over to it. Check the notification area and Task Manager. If a copy is running but not responding, end it there and start again.

The launch log holds what the engine reported the last time it was started. A portable copy keeps it at `data\logs\launch.log` beside `QuillRadio.exe`; an installed copy at `%APPDATA%\Quill\logs\QuillRadio-launch.log`, next to `quill.log`. Each start replaces it, so send it before you try again. It contains file paths from your computer and nothing else personal.

### Everything else

- **A favorite takes a long time to start, then says it is trying the station's current address.** Its saved address has stopped working, and Quill Radio found the current one. From 3.0.3 the current address is saved into the favorite, so this happens once, not every time you play it. If a station still starts slowly every time, find it again in Browse Stations (Ctrl+B) or search (Ctrl+F), play it, and press Ctrl+Shift+F to save it fresh.
- **Help > User Guide, Release Notes or Product Requirements does nothing.** That was a fault in 3.0.0 to 3.0.2: they looked for the documents beside the shared engine instead of beside `QuillRadio.exe`. Fixed in 3.0.3. The same documents are always on quillforall.org.
- **A pinned Quill Radio says "QuillVilleRuntime.exe is the shared engine ... it is not an app of its own".** That pin was made from the running window before 3.0.2, so Windows pinned the shared engine rather than Quill Radio. From 3.0.2 the pin starts Quill Radio anyway (or, with several QuillVille apps installed, asks which to open). To make the pin a proper one, right-click it, choose Unpin from taskbar, and pin Quill Radio again from the Start Menu or its running window.
- **A station will not play.** Streams move. For a directory station, Quill Radio fetches its current address and retries, and can scan the station's own site (see "When a station will not play"). If it still fails, search for it again, or re-add it as a custom station. If a station is simply dead, press **Shift+F10** on it in Browse Stations or Search Stations and choose **Report Bad Station...**. The report is filled in with the station's name, stream, source and country, and never your name, email or file paths.
- **A station plays for twenty or thirty seconds, then stops.** This was a real fault, fixed in 3.0. Some stations, iHeart's in particular, arrive in short chunks, and one failed top-up used to drain the buffer and go silent. Quill Radio now reconnects instead: you hear "Reconnecting to" the station, "Attempt 1 of 3", up to three times. If a station still stops dead with no reconnect attempt, please report it with **Report Bad Station...**.
- **A recording, book chapter or downloaded show is not reconnected at its end.** That is deliberate. It has genuinely ended.
- **No sound, but the app says playing.** Check Mute (Ctrl+M), the station's own volume (Ctrl+Up), Volume Boost, the output device (Ctrl+Shift+D), and the Windows volume mixer entry for Quill Radio. **View > Audio Health** (Ctrl+Alt+Shift+M) shows the whole chain.
- **A station's own web address will not play.** Quill Radio needs the audio feed, not the website. Type the web address into any search box and Quill Radio finds the feed for you. If a home page finds nothing, try its "Listen Live" page, or search the station by name.
- **The directories do not have my station.** Type its web address into any search box, such as `oj991.com`. If the station has a working player on its site, that is usually all it takes.
- **A recording saved nothing.** Quill Radio says so, names the station, and gives the reason, such as "the connection failed" or "the disk is full". No empty file is kept. You hear the error sound, not the saved sound.
- **A recording stopped early.** Check Radio Recordings. A dropped connection continues into "(part 2)" files, which are joined when the recording ends. The maximum length in Recording Settings also ends recordings on purpose.
- **I still have "(part 2)" files.** The join was refused or failed, and Quill Radio said why when the recording ended. Every part is safe, exactly as recorded, and plays in order.
- **A scheduled recording did not start.** Quill Radio must be running, in the tray at least. Check that the entry is not "(disabled)" in Schedule Recording, and that **Wake the computer for a scheduled recording** is on in Preferences if the computer sleeps.
- **The wake-up timer did not fire.** Quill Radio must be running at the set time. The tray counts; a closed app does not. It never fires late: opening the app hours after the set time stays silent until the next occurrence.
- **The tray icon is gone.** Check the "Show hidden icons" area, or set Quill Radio to always show in the Windows taskbar settings.
- **Rewind or Volume Boost "needs the mpv playback engine".** In Preferences, **Playback engine** is set to Windows Media, or the bundled engine is missing. (The output device no longer needs mpv: Windows Media takes a device too.) Set it to Automatic, or use **Help > Repair mpv Playback Engine...**. For the output device alone, Windows' Sound settings can give Quill Radio a device under Volume mixer on any engine; Ctrl+Shift+D opens that page.
- **Playback sounds different since 1.1.0.** In Preferences, **Playback engine** set to Windows Media is the non-mpv path. Please tell us what you heard (Ctrl+Alt+F2).
- **Quill Radio is too chatty, or too quiet.** Quiet Hours (Ctrl+Alt+Shift+Z) holds back speech nobody asked for. Recent Problems (Ctrl+Alt+Shift+P) keeps any failure you missed.
- **A feature says it is "off in Safe Mode".** Safe Mode is a troubleshooting start that turns off network features, the station catalog refresh, YouTube, Spotify and Quillins, so a problem can be narrowed down. Quill Radio starts in Safe Mode only when it is asked to. If support asks you to use it, they will tell you how, and an ordinary launch afterwards brings everything back.
- **Something else.** Press **Ctrl+Alt+Shift+P** for Recent Problems and **Ctrl+Alt+Shift+M** for Audio Health, then write to support with **Ctrl+Alt+F2**. Copy All in Recent Problems gives support the details without any passwords.
