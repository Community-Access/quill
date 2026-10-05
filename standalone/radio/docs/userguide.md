# Quill Radio User Guide

Version 3.2.0, released 2026-10-03.

## Welcome

Welcome, and thank you for giving Quill Radio a try.

Quill Radio is internet radio for people who listen with a screen reader. I use
one every day, and I wanted a radio that simply worked with it. So the window
is small, and when it opens your cursor is already in your list of favorite
stations. Arrow to a station, press Enter, and it plays. Every menu item tells
you its key, everything you do is answered out loud, and a tray icon keeps the
music going while you get on with something else.

If you have JAWS, NVDA or Narrator and you enjoy radio, podcasts or audiobooks,
Quill Radio is for you. There is no account to make, nothing to pay and nothing
to sign up for.

### What you will be able to do

By the end of this guide you will be able to find a station from anywhere in
the world, keep the ones you love, and start any of them with one key. You will
be able to pause, rewind live radio, record a show tonight or every Tuesday,
and set the radio to wake you up or send you to sleep. You will know where
podcasts, audiobooks, YouTube and television fit in, and how to make the keys
and settings your own. And when something puzzles you, you will know where to
find help.

None of that needs to happen today. Chapter 2 gets you listening in about half
an hour. Everything after it is there for when you are curious.

### How this guide is laid out

The chapters follow the order you are likely to want things.

1. **Chapter 1: Installing Quill Radio.** Which download to choose, and how to
   install it or run it from a folder or USB stick.
2. **Chapter 2: Your first half hour.** A hand-held first session. You play a
   station, keep it, record something and learn the seven keys that do most
   of the work.
3. **Chapter 3: Finding your way around.** The main window, the status bar, Go
   To, the other windows, every menu, the tray, and closing.
4. **Chapter 4: Playing and moving around.** The keys that work in every
   window, the Player, pausing, rewinding, speed, chapters and bookmarks.
5. **Chapter 5: What's playing, and how it sounds.** Song titles, song history,
   volume, sound cards, sound enhancements, video and captions, and the sleep
   and wake-up timers.
6. **Chapter 6: Finding something to listen to.** Browse Stations, searching,
   your own servers, the catalog on your computer, and adding stations nobody
   lists.
7. **Chapter 7: Keeping your favorites.** Folders, order, the Favorites
   Manager, backups, and taking it all to another computer.
8. **Chapter 8: Recording.** Recording now, recording later, several at once,
   and what happens when the internet hiccups.
9. **Chapter 9: Podcasts, books, video and more.** Podcasts, downloads,
   television, weather radio and Spotify.
10. **Chapter 10: Local Media, your own music and audiobooks.** Playlists of
    the music, audiobooks and video on your computer: building them, putting
    them in order, and playing them from any window.
11. **Chapter 11: YouTube.** Searching YouTube, playing and recording it,
    channels, playlists, comments, being told about new videos, and your own
    YouTube sign-in.
12. **Chapter 12: The ACB Media schedule and reminders.** What is on, what is
    coming up, and being told about it.
13. **Chapter 13: The Community menu.** Ask QUILL Radio, your ChatGPT plan,
    ACB Media podcasts, Community Picks, and suggesting a station.
14. **Chapter 14: Making Quill Radio yours.** Preferences, keys, the Command
    Palette, quiet hours and more.
15. **Chapter 15: Safety nets.** Undo, why something is dimmed, Recent
    Problems, Activity, and what Quill Radio connects to.
16. **Chapter 16: When you need a hand.** Tutorials, F1 help, updates, Audio
    Health, support, and answers to common problems.

After the chapters comes the **Keyboard reference**: every key worth knowing,
in small tables grouped by task.

### Reading this guide with a screen reader

The guide is built from headings, so you can move through it quickly. Each
chapter is a level 2 heading, each section inside a chapter is a level 3
heading, and the smaller parts of a section are level 4. In JAWS or NVDA,
press 2 to jump from chapter to chapter and 3 to move between sections. Shift
with the number goes back. To see every heading at once, press Insert+F6 in
JAWS or Insert+F7 in NVDA and choose headings.

Now and then a short note from QUILLBee, QUILLVille's guide, is set apart as a
quote: a faster key, or something worth knowing before it catches you out. The
notes are block quotes, so in a web browser Q moves to the next one in JAWS and
NVDA, and Shift+Q goes back. The guide reads perfectly well if you skip them.

A few ways of writing things that you will meet everywhere:

- Keys are written the way Quill Radio shows them in its menus. Ctrl+Shift+F
  means hold Ctrl and Shift together and press F.
- A menu path such as **Station > Preferences...** means open the Station
  menu, then choose Preferences.
- "Press Alt+S, then choose X" means open the Station menu, arrow to X, and
  press Enter.
- "Choose a button" means Tab to it and press Space, or press its Alt letter
  if it has one. Enter presses the main button of a window.
- The keys in this guide are the ones Quill Radio comes with. If you change a
  key, the menus and the tutorials show your key. This guide cannot know it.

Most sections walk you through things in numbered steps, and each step says
what to press and what you should hear. Keep Quill Radio open beside the guide
and try each step as you read. Alt+Tab moves you between the two.

### Learning by doing: the tutorials

Quill Radio comes with 41 short guided lessons. Open them with **Help >
Tutorials...** (Ctrl+Alt+F1). A lesson can do a step for you, notice when you
have done it yourself, and always shows the keys you actually have. Wherever a
chapter covers something a lesson walks through, this guide names the lesson,
so you can practise straight away. Chapter 16 tells you how they work.

And whenever you wonder what something is for, press **F1**. Every window
answers with what the window is for and what the control you are on does.

### Where to go from here

You now know how this guide is laid out and how to move around it. If Quill
Radio is not on your computer yet, carry on with Chapter 1, Installing Quill
Radio. If it is already installed, jump to Chapter 2, Your first half hour,
and we will play your first station together.

## Chapter 1: Installing Quill Radio

This chapter gets Quill Radio onto your computer. It takes a few minutes, and
for most people the answer is simply "use the installer".

### The two downloads

Quill Radio 3.2.0 comes in two downloads. In each file name, `<version>` is the
release number, such as 3.2.0. Both are on the QUILL Releases page on GitHub,
under the tag `quill-radio-v3.2.0`.

1. **The installer**, `Quill-Radio-Setup-Shared-<version>.exe`. This is the
   right choice for most people. It puts Quill Radio in your Start menu and
   gives it an uninstaller. It also installs the QuillVille Runtime, the
   engine the family of Quill apps share, if your computer does not have it
   yet. Your favorites, history and settings are kept in the shared Quill data
   folder in your Windows profile, so QUILL and QUILL Cast can see them too.
2. **The portable copy**, `Quill-Radio-Portable-<version>.zip`. Everything it
   needs is inside the zip: its own genuine, unchanged Python, ffmpeg for
   recording and mpv for playback. Unpack it anywhere, a USB stick included,
   and nothing downloads when it runs. Choose this when you want the whole
   radio to travel with you, or when you are not allowed to install software.

### Installing with the installer, step by step

1. Download `Quill-Radio-Setup-Shared-3.2.0.exe` and open it from your
   Downloads folder.
2. If Windows SmartScreen shows a warning, see "If your antivirus or
   SmartScreen speaks up" below.
3. Setup may ask whether to install for you only or for everyone who uses the
   computer. Choose **Install for me only**. That needs no administrator
   rights. Installing for everyone asks Windows for permission.
4. The setup wizard opens. Press Enter on each page to accept the usual
   choices. The full installation includes this guide and the release notes.
   Then choose **Install**.
5. If the QuillVille Runtime is not on this computer yet, the installer copies
   it first. NVDA, JAWS and Narrator read the progress bar as a percentage.
6. On the last page, the **Launch Quill Radio** checkbox starts unchecked.
   Press **Space** to check it, then choose **Finish**.
7. Quill Radio opens with your cursor in the Favorite stations list. The very
   first time, a short welcome comes first. Chapter 2 walks you through it.

Next time, open Quill Radio from the Start menu: press the Windows key, type
`Quill Radio`, and press Enter.

### Using the portable copy, step by step

1. Download `Quill-Radio-Portable-3.2.0.zip`.
2. In File Explorer, select the zip, press the Applications key, and choose
   **Extract All...**. Choose a folder, for example on a USB stick, and choose
   **Extract**.
3. Open the folder you extracted, then the `QuillRadio` folder inside it.
4. Select `QuillRadio.exe` and press Enter. Quill Radio opens with your cursor
   in the Favorite stations list.
5. If it does not open, give it a moment. Since 3.0.4, a message tells you
   what went wrong and what to do. See "If Quill Radio does not start" in
   Chapter 16.

One thing catches people out. If you press Enter on `QuillRadio.exe` while you
are still inside the zip, Windows runs that one file on its own. Quill Radio
notices, tells you, and asks you to extract the whole zip first.

#### What a portable copy keeps to itself

A portable copy writes nothing to the computer it runs on. That is true from
the very first launch, and there is nothing to switch on.

- Your settings, favorites, history, logs and caches live in the `data` folder
  beside `QuillRadio.exe`.
- Recordings go to a `Recordings` folder, and downloads to a `Downloads`
  folder, both inside the portable folder, instead of your Music and Downloads
  folders.
- **Start Quill Radio with Windows** is not available. If you choose it, Quill
  Radio explains that a portable copy does not add itself to this computer's
  startup.
- **Wake the computer for a scheduled recording** is dimmed in Preferences,
  with the reason. Keeping the computer awake before a recording still works.
- To turn a portable copy into an ordinary one that uses this computer's
  profile, delete its `data` folder. Your Recordings and Downloads folders sit
  beside `data`, so they are kept.

### Bringing your favorites from Quill Radio 2.x

Quill Radio 2.x kept your favorites in this computer's profile, even when it
ran from the portable zip. A 3.0 or later portable copy keeps its own, so the
first time it starts, it looks for your old ones.

1. Unzip `Quill-Radio-Portable-3.2.0.zip` and start `QuillRadio.exe`, as
   above.
2. If an earlier Quill Radio on this computer has favorites, and this copy has
   none yet, a question opens titled "Favorites from an earlier Quill Radio".
   It tells you how many favorite stations it found.
3. Press **Enter** (Yes) to copy them into this portable copy, together with
   your settings, recording schedule and reminders. Quill Radio then opens
   with your favorites in the list.
4. Or choose **No** to start with an empty list.

Good to know:

- Your earlier copy is only read, never changed, and nothing is written to the
  computer.
- You are asked once. Your answer is remembered either way.
- The installed copy needs none of this. It reads the same profile 2.x did, so
  your favorites are simply there.

### If you had the Lite installer or the Companion zip

Test versions of 3.0 also offered a small "Lite" installer and a Companion zip.
Both are retired, and nothing is lost.

- If you used the Lite installer, run `Quill-Radio-Setup-Shared-3.2.0.exe`. It
  upgrades you in place and keeps your data.
- If you used the Companion zip, run the installer, or unpack the portable zip
  instead. Check for Updates on a Companion copy offers you the installer.

### The QuillVille Runtime

Quill Radio belongs to a small family of apps: QUILL, Quill Radio, Quill
Weather and QUILL Audio Studio. Underneath, they all run on the same Python
engine. The installer puts that engine on your computer once, as a shared
piece called the **QuillVille Runtime**, and every family app uses it. So once
you have one app, the next one you add installs quickly, because the engine is
already there.

You never need to look after it. Windows keeps count of how many family apps
use it, and removes it only when you uninstall the last one. Uninstall Quill
Radio while Quill Weather is still installed, and the runtime stays for
Weather.

The portable copy does not use the shared runtime. It carries its own.

### If your antivirus or SmartScreen speaks up

Quill Radio starts from a small program of its own, and the Python it runs is
the official, unchanged one. Older versions started from a renamed copy of
Python, and some antivirus programs mistook that for something harmful. That
is gone.

Release versions are signed, so Windows can check who made the installer, the
uninstaller and the app. Even so, while a new release is still new, Windows
SmartScreen may show a caution. To carry on:

1. In the SmartScreen window, choose **More info**.
2. Check that the publisher is shown, then choose **Run anyway**.

### What you learned, and where to go next

You chose between the installer and the portable copy, installed Quill Radio,
and know where it keeps your things. If you came from Quill Radio 2.x, your
favorites came with you. Now the fun part: go on to Chapter 2, Your first half
hour, and play your first station. The tutorial **Play your first station**,
in the Your first hour track, covers the same ground with a voice beside you.

## Chapter 2: Your first half hour

This chapter assumes nothing. I will stay with you the whole way, and every
step says what to press and what you should hear. Work straight down it and
you will finish with a station playing, a favorite saved, a recording made,
and the keys that matter under your fingers.

Two things to hold on to as you go. **Escape** always steps you back out of
wherever you are. And nothing below can lose anything you have not
deliberately saved, so explore freely.

If something does not happen the way this chapter says, please tell us. **Help
> Get Help from Support...** (Ctrl+Alt+F2) fills most of the message in for you.

The tutorials in the **Your first hour** track cover this chapter too: **Play
your first station**, **Keep a station, and find it tomorrow**, **The player
follows you**, **Do anything by name** and **Getting unstuck**.

### The first time you open it

The very first time you open Quill Radio, it greets you with three short
screens: "Welcome to Quill Radio", "Find something to listen to" and "Keep the
ones you like". Each one names the real key for what it describes, and if you
have already changed a key, it tells you yours.

If you already have favorites, for example after an upgrade, a restored backup
or an imported list, the welcome is skipped.

Here is how to walk through it:

1. Open Quill Radio. The welcome opens with your cursor in its text. You should
   hear "Welcome to Quill Radio. Screen 1 of 3."
2. Read the text with the arrow keys, at your own pace.
3. Press **Alt+N** for **Next**. The next screen opens and your cursor goes
   back into its text. On the last screen the same button reads **Finish**,
   and its key is **Alt+F**.
4. Press **Alt+B** for **Back** to go back a screen.
5. On screens 2 and 3, press **Alt+S** for **Browse Stations Now...** if you
   want to leave the welcome and go straight to Browse Stations, the list of
   everything there is to listen to.
6. Press **Escape**, or **Alt+K** for **Skip**, to leave at any time. Skipping
   counts as finished, so the welcome will not come back.

#### Tips now and then

The welcome has one checkbox, **Show me a tip now and then** (Alt+T). Leave it
checked. The first time you reach a place where one fact would help, Quill
Radio says a single sentence about it, for example: "Live radio can be
rewound. Rewind goes back 30 seconds at a time, up to the buffer's length, and
Back to Live catches up again." Each tip is said once, ever. Tips never take
your keyboard away. If you would rather not hear them, uncheck the box.

### Every time after that

Open Quill Radio from the Start menu, or run `QuillRadio.exe` in the portable
folder. The window opens with your cursor in the **Favorite stations** list.

- **No favorites yet?** Press **Ctrl+B** to open Browse Stations. It is a tree
  of everything: popular stations, NOAA Weather Radio, radio reading services,
  whole directories, podcasts and more. Open **ACB Media** for the whole ACB
  stream directory, ready to play with no setup. Or press **Ctrl+F** for Search
  Stations, to search by name, genre, country or language.
- **Have some favorites?** Arrow to a station and press **Enter**. That really
  is all there is to it.
- **Want the radio to start the moment you open the app?** Press
  **Ctrl+Alt+L** once. That turns on **Station > Resume Last Station on
  Launch**, and from then on Quill Radio starts your last station when it
  opens.

Everything Quill Radio says goes through your screen reader, whether that is
JAWS, NVDA or Narrator, and it never moves your cursor to do it.

#### Braille displays

What Quill Radio says also goes to your braille display, if you have one
connected. Nothing is shortened, so a long song title is all there for you to
pan through. The same message twice in a couple of seconds does not flash the
display twice. When several messages arrive at once, you see the first
straight away and then the newest. Errors always show at once. If the display
is unplugged, you still hear everything. Quill Radio has no braille setting of
its own, because it simply follows your screen reader.

### Task 1: play your first station (about two minutes)

1. Open Quill Radio from the Start menu, or run `QuillRadio.exe` from the
   portable folder.
2. Wait for the window. You should hear "Favorite stations, tree", or your
   screen reader's words for an empty tree. Your cursor is already in the
   favorites list. On a new installation the list is empty, and that is fine.
3. Press **Ctrl+B**. Browse Stations opens. Your screen reader reads the
   window's title, and your cursor is in the tree on its first row, **Search
   All Sources...**.
4. Press **Down Arrow** a few times. Each press reads a source: Favorites,
   Popular Stations, Trending Now, Recently Added or Changed, By Country, By
   Language, By Genre, By Quality, Weather / NOAA, ACB Media, and so on.
   Nothing has come from the internet yet. These are just the headings.
5. Stop on **Popular Stations** and press **Right Arrow** to open it. The first
   time, Quill Radio fetches the list, so give it a moment. You should hear
   "Loading Popular Stations", then how many stations arrived.
6. Press **Down Arrow** to move onto a station, then press **Enter**.
7. You should hear "Playing" and the station's name over a short connecting
   sound, and then the station itself. Well done. That is the whole idea of
   Quill Radio: arrow to something, press Enter.
8. Press **Ctrl+Down** twice. Each press tells you the new level, for example
   "Volume 70 percent." The volume moves in steps of ten, in every window.
9. Press **Enter** again on the same station. It stops, and you hear "Radio
   stopped." Press **Enter** once more and it plays again.

If it does not work:

- **You hear an error instead of the station.** Some directory addresses no
  longer work. Arrow to another station and press Enter. Quill Radio has
  already tried to repair the address for you. See "When a station will not
  play" in Chapter 6.
- **You hear nothing, but Quill Radio says it is playing.** Press **Ctrl+M** in
  case the radio is muted, then press **Ctrl+Up** a few times. Check the
  Windows volume as well.
- **The branch says "Could not be reached".** Either your internet or that
  directory is down. Try **By Country** instead. It answers from the catalog
  on your own computer, even with no internet.

Leave the station playing for the next task.

### Task 2: keep it (about one minute)

1. Press **Escape** to close Browse Stations. Your cursor goes back to the
   favorites list in the main window, and the station keeps playing.
2. Press **Ctrl+Shift+F**. This is **Station > Add Playing Station to
   Favorites**. It saves whatever is playing, from wherever you are. You
   should hear that the station was added to your favorites.
3. Press **Down Arrow** in the favorites list. There it is.
4. Press **Enter** on it, and it plays. From now on, that is your way to this
   station: open Quill Radio, press Enter.

That is the heart of Quill Radio. Everything after this is a bonus.

### Task 3: work the player from anywhere (about three minutes)

The keys that control what is playing work in every Quill Radio window, not
just the main one.

1. With something playing, press **Ctrl+B** to open Browse Stations again.
2. Press **Ctrl+Up**. The volume goes up and you hear the new level, even
   though you are in the browse window. The same goes for **Ctrl+P** (play or
   pause), **Ctrl+Shift+O** (mute and unmute) and the other keys listed in
   "The player follows you" in Chapter 4.
3. Press **Ctrl+Shift+G**. This is **Go to Player**. The Player window opens.
   Your screen reader reads its title, then the Now playing box. If the
   Player is already open somewhere behind you, the same key brings it to the
   front instead of opening a second one.
4. Press **Tab** to look around it. First comes a **Now playing** box you can
   read but not change. It tells you what is on, where you are in it, how fast
   it is playing and how loud. Then come the buttons: Play (or Stop), Pause
   (or Resume), Skip Back, Skip Forward, Where Am I?, Previous Chapter, Next
   Chapter, Chapters..., Slower, Faster, Normal Speed, Skip Silence, Volume
   Down, Volume Up, Mute/Unmute, and last, Add to Favorites.
5. Press **Escape**. The Player closes and you are back where you started.

### Task 4: do anything by name (about one minute)

If you cannot remember a key, you never need to.

1. Press **Ctrl+Shift+P**. The **Command Palette** opens, from any Quill Radio
   window, with your cursor in its search box.
2. Type a few letters of what you want, such as `vol`, `record` or `chapter`.
   The list gets shorter as you type.
3. Press **Down Arrow** to the command you want and press **Enter**. It does
   exactly what its key or menu item would do. Each entry also tells you its
   key, so the palette quietly teaches you shortcuts as you go.

### Task 5: record something (about three minutes)

1. With a station playing, press **Ctrl+R**.
2. You should hear "Recording started" and the station's name. Down in the
   status bar, the Record cell now reads **Stop Recording**, with the time so
   far.
3. Wait ten or twenty seconds.
4. Press **Ctrl+R** again to stop. You should hear "Stopping recording", then
   that the recording was saved, with the file's name.
5. Press **Ctrl+Shift+R**. The **Radio Recordings** window opens with your
   cursor in the list. Your recording is at the top, because the newest comes
   first.
6. Press **Enter** on it. You should hear "Playing recording" and its name,
   and then your recording.
7. Press **Delete** to remove it. A question opens: "Delete the recording
   ...?" **No** is already chosen, so pressing Enter keeps your recording. To
   delete it, press **Y**, or Tab to **Yes** and press Enter. Your cursor moves
   to the recording that took its place in the list.
8. Press **Escape** to close Radio Recordings.

Good to know: recordings are saved in your Music folder, in a folder called
`Quill Radio Recordings`. A portable copy saves them in its own `Recordings`
folder. **Open in Folder** in Radio Recordings shows you the file in File
Explorer.

### Task 6: the seven keys worth learning

Everything else is in the menus and the Command Palette. These seven carry the
day:

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

It happens to everybody. Any of these will get you back on your feet:

- **Escape** closes the window you are in and takes you back to the one you
  came from.
- **F6** moves into the status bar along the bottom of the main window. Press
  F6 again, or Escape, to come back. Tab never goes there. See "The status
  bar" in Chapter 3.
- **Ctrl+Shift+G** brings the Player to you, wherever you are.
- **Ctrl+G** opens Go To, a numbered list of places.
- **F1** tells you where you are: what the window is for, then what the
  control you are on does, in a box you can arrow through.
- **Ctrl+F1** opens this guide.

### What you learned, and where to go next

In half an hour you played a station, saved it as a favorite, used the player
from another window, ran a command by name, and made and deleted a recording.
That is genuinely most of what Quill Radio is for. When you are ready, Chapter
3, Finding your way around, shows you the rest of the main window and its
menus. If you would like to practise first, the tutorial **Getting unstuck**
is a gentle next step.

## Chapter 3: Finding your way around

Now that you have heard a station, let us take a slow walk around. This
chapter shows you the main window, the status bar along its bottom, Go To, the
other windows Quill Radio opens, every menu, the tray icon and how to close the
app. You do not need to learn it all at once. Read it once, and come back when
you wonder where something lives.

### The main window

The main window is a list you play from, not a busy control panel. Tab moves
through six stops, in this order.

1. **Now playing**, a box you can read but not change. It tells you the
   station and what the player is doing, the song when there is one, and
   anything else worth knowing, such as a recording running. Arrow through it,
   or copy it with Ctrl+C. It never changes under you while you are reading:
   any update waits until you leave the box. It does not show how long you
   have been listening. Press **Ctrl+Shift+W** for that.
2. **Favorite stations**, the tree of your stations. It shows the same folders
   you make in the Favorites Manager. **Alt+F** jumps here from anywhere in the
   window.
3. **The play button**, which tells you what it will do and to what. While
   nothing is playing it reads **Play** and the selected favorite's name
   (Alt+L). While something plays it reads **Stop** and that station's name
   (Alt+T). While a podcast, recording or file on your computer is paused it
   reads **Resume** and its name (Alt+U). If you gave the station your own
   name in Favorites, that is the name you hear. With a folder or nothing
   selected it reads **Play -- nothing selected**, and pressing it tells you
   what would work. Stop does the same as **Ctrl+Period** and **Station >
   Stop**, and **Ctrl+P** presses this button from anywhere.
4. **Website** (Alt+B), which opens the station's own website in your
   browser. If something is playing, you get that station's site; if not, you
   get the site of the favorite you are on. It is the quickest way to a
   station's schedule, such as Double Tap Live's, and Quill Radio tells you
   which site it opened. If the station never gave a website, it says so and
   opens nothing.
5. **Mute**, a button that stays pressed while the radio is muted. It always
   shows the real state, even if you muted from somewhere else.
6. **Volume** (Alt+O), a slider. Up and Right make it louder, Down and Left
   make it quieter, and Page Up and Page Down move in bigger steps. The
   slider, Ctrl+Up and Ctrl+Down, and the Volume cell in the status bar always
   agree, including with each station's remembered volume.

Along the bottom is the **status bar**. Tab never reaches it, so press **F6**.
See "The status bar" below.

If you used an older version, the other buttons that used to be here have
moved, not gone. Play is **Enter** on a station, or **Ctrl+P**. Record is
**Ctrl+R**. Browse Stations is **Ctrl+B**. Chapters are in the Player
(**Ctrl+Shift+G**). Adding the playing station to your favorites is
**Ctrl+Shift+F**.

#### The favorites tree, step by step

1. Press **Alt+F** to put your cursor in the tree.
2. Arrow **Up** and **Down** to move. **Right Arrow** opens a folder and **Left
   Arrow** closes it.
3. Press **Enter** on a station to play it. Press **Enter** on the station that
   is playing to stop it.
4. Press **Space** on the playing station to pause or resume it, when it is
   something that can be paused. Live radio cannot be paused.
5. Press **F2** to rename a station or folder. Leave a station's name blank to
   go back to the directory's own name.
6. Press **Delete** to remove a station. Quill Radio asks first.
7. Press **Ctrl+Up** or **Ctrl+Down** to change the volume without leaving the
   tree.
8. Press **Shift+F10**, or the Applications key, for everything you can do.

#### The menu on a station or a folder

On a **station**, the menu offers **Play** (or **Stop**), **Station
Details...**, **Rename...** (F2), **Move Up** (Alt+Shift+Up), **Move Down**
(Alt+Shift+Down), **Move to Folder...**, **Remove...** (Delete), **New
Folder...** (Ctrl+Shift+E), **Mark for Move**, and **Manage Favorites...**.
Once you have marked a station, **Move Marked Above** and **Move Marked Below**
join the list.

**Station Details...** opens a box you can read and copy, with the station's
source, stream, format and country.

On a **folder**, the menu offers **Rename Folder...** (F2), **Sort This
Folder...**, **Delete Folder...**, **New Folder...** (Ctrl+Shift+E), and
**Manage Favorites...**.

Putting your favorites in your own order, and playing them without the list,
are in Chapter 7, Keeping your favorites.

### The status bar

The status bar runs along the bottom of the main window. It is a row of cells,
and each one is something you can press:

1. **Play**, which reads **Stop** while something plays.
2. **Mute**, which reads **Unmute** while muted.
3. **Volume**, with the level, and "boosted" when Volume Boost is on.
4. **Record Now**, which reads **Stop Recording**, with the time, while a
   recording runs.
5. **Sleep timer**, with the time left, or "Off".
6. **Time**, the time of day.

To use it:

1. Press **F6**. Your cursor moves into the bar. You should hear "Status bar"
   and the cell's name, such as "Play (Ctrl+P)".
2. Press **Right Arrow** or **Left Arrow** to move from cell to cell. **Home**
   and **End** jump to the first and last cells.
3. Press **Enter** or **Space** to press the cell you are on. On **Volume**,
   Enter mutes or unmutes. On **Sleep timer**, Enter opens the Sleep Timer. On
   **Time**, Enter tells you the full date and time.
4. Press the **Applications key** or **Shift+F10** for the cell's own menu.
   Every cell's menu starts with **Activate** and ends with **Hide Status
   Bar**. In between:
   - **Play**: Play or Stop, Pause or Resume, Mute/Unmute, Play Favorite
     Station..., Recently Played, Record Now, Schedule Recording..., Recording
     Settings..., Stop All Recordings (when two or more are running), and
     Browse Stations....
   - **Mute** and **Volume**: Volume Up, Volume Down, Mute/Unmute, Volume
     Boost, Output Device..., and Sound Enhancements....
   - **Record**: Record Now or Stop Recording, Stop All Recordings (when two
     or more are running), Schedule Recording..., Recordings..., and Recording
     Settings....
   - **Sleep timer**: Sleep Timer... and Wake-Up Timer....
5. Press **F6** again, or **Escape**, to go back to the favorites tree. You
   should hear "Returned to favorite stations."

To hide or show the whole bar, press **Ctrl+Shift+Alt+B** (**View > Show
Status Bar**).

#### What the status line is telling you

The Now playing box, the tray icon's tooltip and the first line of the
Playback menu all use the same words for what a stream is doing. Some of these
are things you did, and some are just the internet being the internet, so the
words are chosen to tell them apart:

| What it says | What is happening |
|---|---|
| `Radio: stopped` | Nothing is playing. |
| `Radio: connecting to WQXR...` | A station you just chose is being opened. |
| `Radio: buffering WQXR...` | It was playing and ran short of audio. It is filling up again, and usually comes back within a few seconds. |
| `Radio: playing WQXR` | Playing. "(muted)" is added when muted. |
| `Radio: paused - WQXR` | You paused a recording, podcast, file or video. |
| `Radio: Reconnecting to WQXR. Attempt 2 of 3.` | The stream dropped and Quill Radio is getting it back. Each try is spoken as well as shown, so a long wait never sounds like the app has frozen. It tries three times, after two, five and fifteen seconds. |
| `Radio: could not play WQXR - ...` | It failed, and the reason follows. |

So **buffering** means the stream is still there and the sound ran out for a
moment, and **reconnecting** means the connection was lost and is being
rebuilt.

### Go To: one key for every place

Press **Ctrl+G** in the main window (**View > Go To...**) and a short numbered
list of places opens. Press a number and you are there.

1. Press **Ctrl+G**. The Go To list opens with your cursor in it.
2. Press a number key, **1** to **9**, or **0** for the tenth place. That place
   opens straight away.
3. Or arrow to a row and press **Enter**.
4. Press **Escape** to close the list. Your cursor goes back exactly where it
   was.

The list starts out like this:

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

**The numbers never change on their own.** Recordings is 4 today and it will
be 4 next year, whether or not it is open. Ctrl+1 to Ctrl+9 work differently:
they reach the windows you have open, in the order you opened them.

Each row also tells you that place's own shortcut. Use Go To for a month and
you may find you no longer need it.

#### Go To Settings, step by step

Go To Settings lets you choose which places are on the list, and in what
order.

1. Press **Ctrl+G** to open Go To.
2. Press **Tab** to the **Settings...** button and press **Space**. Go To
   Settings opens.
3. The first list, **In the menu** (Alt+I), holds the places on the list,
   numbered. Arrow to one.
4. Press **Tab** to **Move Up** or **Move Down** and press **Space** to move
   it. Quill Radio tells you its new number.
5. To take a place off, select it and choose **Remove** (Alt+R). It moves to
   the second list.
6. The second list, **Not in the menu** (Alt+N), holds places you can add:
   Scheduled Recordings, Station Catalog Status, Audio Health, Keyboard
   Shortcuts, and What's Playing. Select one and choose **Add** (Alt+A).
7. Choose **OK** to save. You should hear "Go To menu saved."

The list holds ten places, because the number row has ten keys. If you try to
add an eleventh, Quill Radio says so and suggests removing one first.

**An update never renumbers your list.** A place added in a later version waits
in "Not in the menu" until you choose to add it.

Inside Go To, use **Space**, not Enter, on the **Settings...** and **Close**
buttons. Enter always goes to the highlighted place.

### Windows, and moving between them

Quill Radio's bigger places open as windows of their own:

- Browse Stations
- Local Media
- Search Stations (its title is "Internet Radio")
- Manage Favorite Stations
- Schedule Recording
- Radio Recordings
- Song History
- Now Playing
- The Player
- Tutorials

What that means for you:

- **Each one is a real window.** It has its own place on the taskbar and in
  Alt+Tab, rather than sitting on top of the main window.
- **Each one has a menu bar**, so Alt reaches menus in all of them.
- **The main window stays within reach.** You can keep several windows open
  and move between them as you like.
- **They close the way windows close:** Escape, Ctrl+W, Ctrl+F4, Alt+F4, or the
  title bar. There is no Close button.
- **Asking for a window that is already open brings it to the front**, rather
  than opening a second copy. If you had minimized it, it comes back too.

Smaller windows, such as Downloads, Go To, Preferences and Sound Enhancements,
are ordinary dialogs. They have no menu bar, and Escape closes them.

#### Move between windows, step by step

1. Press **Ctrl+Tab** to go to the next open window, or **Ctrl+Shift+Tab** to
   go back to the previous one. It wraps around.
2. Press **Ctrl+1** through **Ctrl+9** to jump straight to the first through
   ninth open window.
3. Or press **Alt+W** to open the **Window** menu. It lists every open window,
   numbered in the order you opened them. Arrow to one and press Enter.

When you arrive in a window, your cursor is on the control you last used
there, or on the window's main control the first time. When you close a
window, you go back to the one you came from.

If you would like to hear when windows open and close, turn on **Announce
dialog transitions (more spoken detail)** in Preferences. Quill Radio then says
"Entered ..." and "Exited ...". It starts off.

### What the main window shows

The middle of the main window can show one of five views. Everything around
it stays the same in every view: the menu bar, the Now playing box, Mute and
Volume, and the status bar.

1. Press **Ctrl+Shift+2** (**View > Main Window Shows > Browse Stations**). You
   should hear "Main window now shows Browse Stations", and a sentence about
   it. Your cursor is in the tree.
2. Use it just as you would the Browse Stations window.
3. Press **Ctrl+Shift+1** to go back to your favorites.

The five views:

- **Favorite stations** (Ctrl+Shift+1): your own stations and folders. This is
  where you start.
- **Browse Stations** (Ctrl+Shift+2): the tree of every source.
- **Search Stations** (Ctrl+Shift+3): the search with separate fields.
- **Radio Recordings** (Ctrl+Shift+4): everything you have recorded.
- **Player** (Ctrl+Shift+5): what is on, where you are in it, and the play
  buttons.

Your choice works at once and is remembered. **Main window shows** in
Preferences is the same setting. Each view remembers how you left it, so
Browse is still opened up where you were when you come back. Pressing the key
for the view you are already in puts your cursor back in it.

Everything is still its own window when you want it. **Ctrl+B** still opens
Browse and **Ctrl+F** still opens Search. If that place is already your main
view, the key takes you there rather than opening a second copy.

To leave a view, choose another one with Ctrl+Shift+1 to Ctrl+Shift+5. A view
is not a window, so Escape in the Player view does not close Quill Radio.

If you used "Open Browse Stations at startup" in an older version, your main
window now shows Browse instead, and nothing else opens by itself.

### The menus

The main window's menu bar, from left to right, is **Station** (Alt+S),
**Edit** (Alt+E), **View** (Alt+V), **Playback** (Alt+P), **Audio** (Alt+A),
**Video** (Alt+D), **Record** (Alt+R), **Community** (Alt+C), **QuillVille**
(Alt+Q), **Help** (Alt+H) and **Window** (Alt+W).

Every menu item shows its own key, and if you change a key, the menu shows
yours. This section lists every item in menu order with the key it comes with.
Most of them have a walkthrough in their own chapter, so treat this as a map
rather than something to learn.

#### Station menu (Alt+S)

- **Browse Stations...** (Ctrl+B): the tree of every source. See "Browse
  Stations" in Chapter 6.
- **Local Media...** (Ctrl+O): your own music, audiobooks and video, in
  playlists. See Chapter 10, Local Media, your own music and audiobooks.
- **Update Radio Reading Services...** (Ctrl+Alt+F10): fetches the latest list
  of radio reading services from the RadioBrowser directory and tells you how
  many it found. The list that comes with Quill Radio stays as a backup. Off in
  Safe Mode.
- **Search Stations...** (Ctrl+F): the search window titled "Internet Radio".
  See "Search Stations" in Chapter 6.
- **Add Custom Station...** (Ctrl+N): save any stream address under your own
  name. See "Adding your own stations" in Chapter 6.
- **Add YouTube Link...** (Ctrl+Alt+N): keep any YouTube link under Browse
  Stations, YouTube.
- **Search YouTube...** (Ctrl+Shift+6): find videos, playlists and channels on
  YouTube, answered in Browse Stations.
- **Add from YouTube Playlist...** (Ctrl+Shift+Y): turn videos from a playlist
  into favorites.
- **Import YouTube Subscriptions...** (Ctrl+Alt+Shift+Y): follow every channel
  in a file you download from Google.
- **Repair YouTube Support...** (Ctrl+Alt+Y): for emergencies, fetches the
  newest YouTube helper.
- **Find Streams from a Website...** (Ctrl+Alt+S): look through a station's web
  page for its stream.
- **Search Sources...** (Ctrl+Alt+Shift+U): choose which directories Search
  Stations asks.
- **Choose Browse Sources...** (Ctrl+Shift+Alt+O): choose which sources Browse
  Stations shows.
- **Update Station Catalog** (Ctrl+Alt+Shift+G): bring the station catalog on
  your computer up to date now.
- **Connect to Spotify...** (Ctrl+Alt+P) and **Browse Spotify...**
  (Ctrl+Alt+O): only there when the experimental Spotify feature is on. See
  "Spotify (experimental)" in Chapter 9.
- **Manage Favorites...** (Ctrl+Shift+M): the Manage Favorite Stations window.
- **Add Playing Station to Favorites** (Ctrl+Shift+F): saves what is playing.
  If it is already a favorite, the same item removes it, and its name says so.
- **Quick Actions...** (Ctrl+Alt+Q): the order of the actions on the Browse
  Stations menu.
- **New Folder...** (Ctrl+Shift+E): a new favorites folder, wherever you like.
- **Import Stations from Playlist...** (Ctrl+I): read stations from an M3U,
  M3U8, PLS, XSPF or ASX file.
- **Export Favorites to Playlist...** (Ctrl+Shift+X): write your favorites to
  an M3U file.
- **Back Up Stations and Settings...** (Ctrl+Shift+U) and **Restore from
  Backup...** (Ctrl+Alt+Shift+W): see "Backing up and restoring" in Chapter 7.
- **Play Last Station** (Ctrl+L): whatever you had on last.
- **Recently Played**: a submenu of your last nine stations, newest first.
  Inside it, **Alt+Shift+1** plays the newest. It reads "(none yet)" when it is
  empty.
- **Play Favorite Station...** (Alt+Shift+F): a numbered list of every
  favorite. It is there once you have favorites.
- **Resume Last Station on Launch** (Ctrl+Alt+L): a checkable item. When
  checked, opening Quill Radio plays your last station. It starts off.
- **Start Quill Radio with Windows** (Ctrl+Alt+W): a checkable item. Quill
  Radio opens by itself when you sign in to Windows. It only affects your own
  account and needs no administrator rights. A portable copy does not offer
  it. If signing in ever opens the wrong thing, turn it off and on again, and
  Quill Radio writes the startup entry fresh.
- **Download Preferences...** (Ctrl+Alt+Shift+D): where downloads are saved and
  how they are filed.
- **Preferences...** (Ctrl+,): see "Preferences" in Chapter 14.
- **Send to Tray** (Ctrl+W): hides every Quill Radio window. Playing and
  recording carry on, and the tray icon stays. You should hear "Quill Radio is
  still running in the system tray."
- **Exit** (Ctrl+Q): closes Quill Radio straight away, even during a
  recording. See "Closing Quill Radio" later in this chapter.

#### Edit menu (Alt+E)

- **Undo Last Action** (Ctrl+Z): brings back the last thing you removed or
  cleared. See "Taking back the last thing you did" in Chapter 15.
- **Undo History...** (Ctrl+Alt+Shift+A): the last ten things you can take
  back, each with its own Undo.

#### View menu (Alt+V)

- **Listening Statistics...** (Ctrl+Shift+Q): how long you listened, and to
  what.
- **Show Station Details** (Ctrl+D): a checkable item, on to begin with. Shows
  or hides the details box in Browse Stations and Search Stations.
- **Show Status Bar** (Ctrl+Shift+Alt+B): a checkable item, on to begin with.
- **Sort Favorites**: a submenu with **Ascending (A to Z)**
  (Ctrl+Alt+Shift+F4), **Descending (Z to A)** (Ctrl+Alt+Shift+F5) and
  **Unsorted (manual order)** (Ctrl+Alt+Shift+F6). The order you are using
  reads as checked. It is the same setting as the one in Preferences.
- **Expand All Folders** (Ctrl+Alt+E) and **Collapse All Folders**
  (Ctrl+Alt+Shift+E): open or close every folder in the favorites tree at
  once.
- **Downloads...** (Ctrl+Shift+J): the list of downloads.
- **Go To...** (Ctrl+G): the numbered list of places.
- **Station Catalog Status...** (Ctrl+Alt+Shift+S): what is stored on your
  computer.
- **Audio Health...** (Ctrl+Alt+Shift+M): can this copy play and record?
- **Choose Columns...** (Ctrl+Alt+Shift+C): what each row says in Find
  Stations and Recordings.
- **Customize Features...** (Ctrl+Alt+C): turn the Record menu off if you never
  record.
- **Main Window Shows**: a submenu of the five views, **Favorite stations**
  (Ctrl+Shift+1), **Browse Stations** (Ctrl+Shift+2), **Search Stations**
  (Ctrl+Shift+3), **Radio Recordings** (Ctrl+Shift+4) and **Player**
  (Ctrl+Shift+5).
- **Text Size**: a submenu with **Normal** (Ctrl+Alt+1), **Large**
  (Ctrl+Alt+2) and **Larger** (Ctrl+Alt+3). Makes the main window's text
  bigger, and is remembered.

#### Playback menu (Alt+P)

- A dimmed first line tells you what is playing, such as "Radio: stopped".
- **Play** (Ctrl+P): reads **Stop** while something plays and **Resume** while
  something is paused, the same three words as the main window's play button,
  which it presses. When nothing is playing, it plays the favorite selected in
  the tree.
- **Pause** (Ctrl+Space): reads **Resume** while paused. It holds a podcast, a
  recording, a downloaded or local file, or a finished video, and picks it up
  where you left off. On a live station it is dimmed and tells you why: live
  radio is going out now, so there is nothing to hold.
- **Rewind 30 Seconds** (Ctrl+Shift+Left), **Forward 30 Seconds**
  (Ctrl+Shift+Right) and **Back to Live** (Ctrl+Shift+L).
- **Continue Listening...** (Ctrl+Alt+Shift+L): everything you started and did
  not finish.
- **Chapters...** (Ctrl+Shift+C), **Next Chapter** (Ctrl+Shift+.) and
  **Previous Chapter** (Ctrl+Shift+,).
- **Transcript...** (Ctrl+Shift+T): read what a video says.
- **Play Faster** (Ctrl+Shift+Up), **Play Slower** (Ctrl+Shift+Down) and
  **Normal Speed** (Ctrl+Shift+0).
- **Where Am I?** (Ctrl+Shift+W): where you are, how long it is, and which
  chapter.
- **Go to Position...** (Ctrl+Alt+J): jump to an exact time.
- **Skip Silence** (Ctrl+Shift+9): shorten long pauses in anything that is not
  live.
- **Go to Player** (Ctrl+Shift+G): open the Player, or bring it to the front.
- **What's Playing?** (Ctrl+T): the Now Playing window.
- **Song History...** (Ctrl+Shift+H): what each station played earlier.
- **Sleep Timer...** (Ctrl+Shift+Z) and **Wake-Up Timer...** (Ctrl+Alt+Z).
- **Bookmark This Moment** (Ctrl+Alt+A).

The walkthroughs are in Chapter 4, Playing and moving around, and Chapter 5,
What's playing, and how it sounds.

#### Audio menu (Alt+A)

- **Mute/Unmute** (Ctrl+M).
- **Volume Up** (Ctrl+Up) and **Volume Down** (Ctrl+Down).
- **Volume Boost** (Ctrl+Shift+B): a checkable item. Lets the volume go up to
  50 percent past full.
- **Output Device...** (Ctrl+Shift+D): which sound card or headset the radio
  plays through.
- **Audio and Described Audio...** (Ctrl+Shift+A) and **Play Described Audio**
  (Ctrl+Alt+D).
- **Use One Volume for All Stations** (Ctrl+Alt+V): a checkable item, off to
  begin with.
- **Forget Every Station's Own Volume...** (Ctrl+Alt+Shift+V).
- **Announce Track Titles** (Ctrl+Alt+T): a checkable item, off to begin with.
- **Sound Enhancements...** (Ctrl+E): tone controls, evening out the volume,
  which ear the sound goes to, night mode and broadcast polish.

The walkthroughs are in Chapter 5, What's playing, and how it sounds.

#### Video menu (Alt+D)

The Video menu is always there. When there is no picture to act on, its items
tell you so.

- **Show Video** (Ctrl+Shift+V).
- **Captions** (Ctrl+Shift+K) and **Caption Settings...** (Ctrl+Shift+Alt+T).
- **Video Information** (Ctrl+Shift+I).
- **Take a Snapshot** (Ctrl+Shift+Alt+H).
- **Full Screen** (F11).
- **Read Comments...** (Ctrl+Shift+7): the comments on the YouTube video that
  is playing. See "Read a video's comments" in Chapter 11.
- **Video Size**: a submenu with **Fit** (Ctrl+Alt+4), **50%** (Ctrl+Alt+5),
  **100%** (Ctrl+Alt+6) and **200%** (Ctrl+Alt+7). In this release, Fit gives
  the same size as 100%.

See "Video, captions and described audio" in Chapter 5.

#### Record menu (Alt+R)

- **Record Now / Stop Recording** (Ctrl+R).
- **Record Station...** (Ctrl+Alt+R).
- **Stop All Recordings** (Ctrl+Alt+X).
- **Schedule Recording...** (Ctrl+Shift+S).
- **Recordings...** (Ctrl+Shift+R).
- **Recording Settings...** (Ctrl+Alt+Shift+I).

If you turn Recording off in Customize Features, the Record menu goes away.
See Chapter 8, Recording.

#### Community menu (Alt+C)

- **Ask QUILL Radio...** (Ctrl+Shift+8) and **Use My ChatGPT Subscription...**
  (Alt+F5): a conversation that already knows what is playing, on the ChatGPT
  plan you pay for.
- **ACB Media Schedule...** (Ctrl+Shift+N), **What Is On Now** (Ctrl+Alt+H),
  **Upcoming...** (Ctrl+Alt+Shift+F) and **Refresh the Schedule** (F5).
- **ACB Media Podcasts...** (Ctrl+Alt+I).
- **Community Picks...** (Ctrl+Alt+0) and **Suggest a Station or Podcast...**
  (Ctrl+Alt+9).

See Chapter 12, The ACB Media schedule and reminders, and Chapter 13, The
Community menu.

#### QuillVille menu (Alt+Q)

This menu opens the other apps in the family. Every row has its own letter, so
**Alt+Q and then one letter** opens an app. That is two single key presses,
with nothing held down:

- **Open QUILL**: Alt+Q, then Q (or Ctrl+Alt+Shift+F7)
- **Open Quill Weather**: Alt+Q, then W (or Ctrl+Alt+Shift+F8)
- **Open Quill Converter**: Alt+Q, then V (or Ctrl+Alt+Shift+F9)

Each app will keep its letter as more of the family arrives: C for Quill Cast,
A for Audio Studio, I for Quill Inkwell.

The long keys are only where things start. Each row is a command called
**QuillVille: Open** and the app's name, and you can give it any key you like
in **Help > Keyboard Shortcuts...** (Ctrl+Alt+K). See "Keyboard access without
chords" in Chapter 14.

#### Help menu (Alt+H)

- **Command Palette...** (Ctrl+Shift+P).
- **Keyboard Shortcuts...** (Ctrl+Alt+K): the Keyboard Manager.
- **Global Hotkeys...** (Ctrl+Alt+G).
- **Recent Problems...** (Ctrl+Alt+Shift+P).
- **Activity...** (Shift+F9) and **Repeat Last Result** (F9). See "Activity and
  Repeat Last Result" in Chapter 15.
- **Notifications...** (Ctrl+Alt+Shift+F3): everything you have been told
  about. See "Notifications" in Chapter 12.
- **Quiet Hours...** (Ctrl+Alt+Shift+Z).
- **Bookmarks...** (Ctrl+Alt+Shift+J).
- **Export My Setup...** (Ctrl+Alt+Shift+X) and **Import My Setup...**
  (Ctrl+Alt+Shift+N).
- **Keyboard Shortcuts Sheet...** (Ctrl+Alt+Shift+K).
- **Get Help from Support...** (Ctrl+Alt+F2).
- **Repair FFmpeg...** (Ctrl+Alt+F) and **Repair mpv Playback Engine...**
  (Ctrl+Alt+M): emergency repairs, for when a tool that comes with Quill Radio
  has gone missing. You should never need them.
- **What Is This?** (F1): help for the window you are in and the control you
  are on.
- **Tutorials...** (Ctrl+Alt+F1).
- **User Guide** (Ctrl+F1), **Release Notes** (Shift+F1) and **Product
  Requirements...** (Alt+Shift+F1). Each opens in your web browser.
- **Check for Updates...** (Ctrl+Alt+U).
- **Release Channel...**: Stable, Beta or Dev. See "Release channels" in
  Chapter 16.
- **About Quill Radio** (Alt+F1): the version, and where the project lives.

Three commands are only in the Command Palette: **Redeem Unlock Code...**,
**Repeat Last Announcement** and **Announcement Self-Test...**. See "Other
help" in Chapter 16.

#### Window menu (Alt+W)

This lists every open Quill Radio window, numbered in the order you opened
them, each with its key: Ctrl+1 for the first, and so on. See "Windows, and
moving between them" earlier in this chapter.

#### The menus in other windows

Every other big window has a small menu bar of its own: one menu belonging to
that window, with **Close** (Ctrl+W), then a **Station** menu and a **Window**
menu. The Station menu has **Browse Stations...** (Ctrl+B), **Search
Stations...** (Ctrl+F), **Manage Favorites...** (Ctrl+Shift+M),
**Recordings...** (Ctrl+Shift+R) and **Preferences...** (Ctrl+,). A window
never lists itself.

**Alt+S is the Station menu in every window**, and **Alt+W** is always the
Window menu. Each window's own menu has its own key:

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

If an Alt key lands on a control instead of a menu, press **Alt** on its own,
then **Right Arrow** or **Left Arrow** to move along the menu bar.

### The system tray

While Quill Radio runs, it keeps an icon in the notification area, the row of
small icons beside the clock. From there you can control the radio without
opening its window at all.

#### Use the tray, step by step

1. Press **Windows+B** to move to the notification area.
2. Arrow to the **Quill Radio** icon. If it is not there, press Enter on the
   "Show hidden icons" button first and look again.
3. Press the **Applications** key, or **Shift+F10**, to open its menu.
4. The menu offers, in this order: **Show Quill Radio**, a dimmed line saying
   what is playing, **Play** (or **Stop**), **Pause** (or **Resume**, dimmed on
   live radio), **Mute/Unmute**, **Play Favorite Station...**, **Recently
   Played**, **Record Now** (or **Stop Recording**), **Schedule Recording...**,
   **Recording Settings...**, **Stop All Recordings** (when two or more are
   running), **Browse Stations...**, **Open QUILL**, **Open Quill Weather**,
   and **Exit Quill Radio**.
5. Arrow to one and press **Enter**.

To bring the window back, choose **Show Quill Radio** on this menu, or
double-click the icon.

#### Show and hide from anywhere

**Ctrl+Alt+Shift+R** shows or hides Quill Radio from any program. Press it
while the window is showing, and Quill Radio tucks itself into the tray and
says "Quill Radio hidden to the tray". Press it again, and the window comes
back with your cursor in it, and you hear "Quill Radio shown." Playing and
recording carry on either way. This key hides only the main window. **Send to
Tray** (Ctrl+W) hides every Quill Radio window.

If another program already uses Ctrl+Alt+Shift+R, Quill Radio leaves it alone
and says nothing, so use the tray icon instead. Each family app has its own
key: QUILL is Ctrl+Alt+Shift+Q and Quill Weather is Ctrl+Alt+Shift+W.

If you open Quill Radio again while it is already running, even hidden in the
tray, the copy that is running comes forward. You never end up with two.

### Closing Quill Radio

There are a few ways to close Quill Radio, and they behave a little
differently:

- **Station > Exit** (Ctrl+Q), and **Exit Quill Radio** on the tray menu,
  close it at once. They never ask, even during a recording, and the
  recording stops.
- **The close button on the title bar, and Alt+F4**, follow the **When closing
  the window** setting in Preferences:
  - **Ask every time**, the starting choice, only asks while a recording is
    running. Otherwise the window closes and Quill Radio exits.
  - **Exit** always exits.
  - **Minimize to Tray** always hides to the tray, still playing.
- **Alt+F4 minimizes to the system tray**, also in Preferences, makes Alt+F4
  hide to the tray, still playing, whatever the setting above says.

When Quill Radio does ask, a window titled "Closing Quill Radio" tells you a
recording is running and that exiting will stop it:

1. Choose **Exit** (Enter) to close, **Minimize to Tray** (Alt+M) to keep it
   running, or **Cancel** (Escape).
2. If you want your choice remembered, check **Don't ask me again** (Alt+D)
   first.

Closing any window other than the main one never stops what is playing.

### What you learned, and where to go next

You now know the six stops in the main window, how to reach the status bar
with F6, how Go To takes you anywhere with one number, and how to move between
windows. You have a map of every menu, and you know how to use the tray and
close the app the way you prefer. Next, Chapter 4, Playing and moving around,
shows you the keys that control what is playing from any window. The tutorial
**The player follows you** is a good companion to it.

## Chapter 4: Playing and moving around

This chapter is about whatever is playing right now: starting and stopping
it, pausing, going back a little, speeding up, jumping between chapters,
marking a moment to come back to, and picking up where you left off. Most of
it works from any Quill Radio window, so you rarely have to go looking for the
player.

### The player follows you

The keys that control playing work in every Quill Radio window, not only the
main one. That includes:

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
- **Ctrl+.** stops.
- **Ctrl+Up** and **Ctrl+Down** turn the volume up and down.
- **Ctrl+Shift+O** mutes and unmutes.
- **Ctrl+Shift+Left** and **Ctrl+Shift+Right** skip back and forward.
- **Ctrl+Shift+Up**, **Ctrl+Shift+Down** and **Ctrl+Shift+0** change the speed.
- **Ctrl+Shift+,** and **Ctrl+Shift+.** move by chapter, and **Ctrl+Shift+C**
  opens the list of chapters. In a Local Media playlist they move to the
  previous and next item.
- **Ctrl+Shift+9** turns Skip Silence on or off.
- **Ctrl+Shift+W** tells you where you are.
- **Ctrl+Shift+G** brings up the Player.
- **Ctrl+Shift+P** opens the Command Palette.

The main window works a little differently, because its menus have the same
commands:

- **Enter** on a favorite, or **Ctrl+P**, plays or stops.
- **Ctrl+Space** pauses and resumes.
- **Ctrl+.** stops.
- **Ctrl+M** mutes, and so does **Ctrl+Shift+O**.
- **Ctrl+Shift+Left** and **Ctrl+Shift+Right** go back and forward 30 seconds,
  and **Ctrl+Shift+L** goes back to live.

You can count on three things:

- **A key means the same thing everywhere.** Volume moves by the same amount
  and is spoken in the same words in every window.
- **A key that cannot do anything tells you why.** Ask for a speed change or a
  chapter while a live station plays, and you hear "This is live radio, which
  plays at broadcast speed and has no chapters or position to move through."
- **A key that does something tells you so.** Play, Stop and Mute all speak.
  Mute especially, because without a word, muting sounds exactly like the
  station dropping out.

### The Player window

The Player (Ctrl+Shift+G) is a small window with every playing control as a
button, and a box telling you what is playing, where you are in it, the speed
and the volume. It is on the Window menu and in the Ctrl+Tab order like any
other window.

1. Press **Ctrl+Shift+G** from any window. The Player opens, or comes to the
   front if it is already open. Your cursor is in the **Now playing** box.
2. Arrow through the Now playing box to read it. It keeps up with anything you
   change elsewhere while it is open.
3. Press **Tab** to move through the buttons, in this order: **Play** (reads
   **Stop** while playing), **Pause** (reads **Resume** while paused, and is
   dimmed on live radio with the reason), **Skip Back**, **Skip Forward**,
   **Where Am I?**, **Previous Chapter**, **Next Chapter**, **Chapters...**,
   **Slower**, **Faster**, **Normal Speed**, **Skip Silence**, **Volume
   Down**, **Volume Up**, **Mute/Unmute**, then **Add to Favorites** (reads
   **Remove from Favorites** when the playing station is already a favorite).
4. Press **Space** on a button to use it. Each button does the same as its
   key, and the box updates.
5. The keys work inside the Player too, and each one updates the box.
6. To close the Player, press **Escape**, **Ctrl+W**, **Ctrl+F4** or
   **Alt+F4**. You go back to the window you came from.

The Player's menu bar has three menus: **Player** (Alt+P), with **Close**
(Ctrl+W); **Station** (Alt+S); and **Window** (Alt+W).

You can also make the Player the main window's view. See "What the main window
shows" in Chapter 3.

### Pausing and resuming

**Pause** (Ctrl+Space) holds a podcast episode, a recording, a downloaded or
local file, or a finished video. **Resume** picks it up where you left off.

1. With something playing that is not live, press **Ctrl+Space**. You should
   hear "Paused."
2. Press **Ctrl+Space** again. You should hear "Resumed."

**Live radio cannot be paused.** It is going out now, so there is nothing to
hold. On a live station, Pause is dimmed and tells you that. Stop ends it. To
catch something you just missed, rewind instead, as the next section shows.

In windows other than the main one, **Ctrl+P** also pauses and resumes
anything that is not live.

### Rewinding live radio, and going back to live

Missed what the newsreader just said? With the standard mpv playback engine,
Quill Radio keeps the last stretch of a live station, roughly 45 minutes at
typical quality, so you can go back and hear it.

1. While a live station plays, press **Ctrl+Shift+Left** (**Playback > Rewind
   30 Seconds**). You should hear "Rewound 30 seconds", and how far behind
   live you are.
2. Press it again to go back further, as far as Quill Radio has kept since you
   started listening.
3. Press **Ctrl+Shift+Right** (**Forward 30 Seconds**) to move forward again.
4. Press **Ctrl+Shift+L** (**Back to Live**) to jump straight back to what is
   on now. You should hear "Back to live."

The Windows Media engine keeps nothing to go back to, so on that engine these
keys tell you that rewinding live radio needs the mpv playback engine. To get
it back, set **Playback engine** to Automatic in Preferences.

### Speed, position and chapters

These work on anything that is not live: a finished YouTube video, a podcast
episode, a recording or a downloaded file.

- **Play Faster** (Ctrl+Shift+Up), **Play Slower** (Ctrl+Shift+Down) and
  **Normal Speed** (Ctrl+Shift+0) step through round speeds from a quarter of
  normal up to four times. Quill Radio remembers the speed for that kind of
  thing: a speed you choose for a recording applies to every recording, and
  one you choose on a YouTube row applies to YouTube rows. While a **podcast
  episode** plays, the speed is remembered for that show, and you hear
  "Remembered for this show". Normal Speed forgets it and tells you so.
- **Rewind 30 Seconds** and **Forward 30 Seconds** move you along and say where
  you landed, such as "3 minutes 10 seconds of 18 minutes 40 seconds".
- **Where Am I?** (Ctrl+Shift+W) tells you your position, the length and the
  chapter you are in.
- **Next Chapter** (Ctrl+Shift+.) and **Previous Chapter** (Ctrl+Shift+,) move
  by chapter. Like a CD player, Previous Chapter first goes back to the start
  of the chapter you are in.
- **Skip Silence** (Ctrl+Shift+9) shortens long pauses. It works straight away,
  with no break in the sound.

On a live station, each of these tells you why it cannot help: "This is live
radio, which plays at broadcast speed and has no chapters or position to move
through."

#### Go to Position, step by step

1. With something playing that is not live, press **Ctrl+Alt+J** (**Playback >
   Go to Position...**). The Go to Position window opens.
2. Type the time in **Hours** (Alt+H), **Minutes** (Alt+M) and **Seconds**
   (Alt+S). Or Tab to **Or type a timecode** and type it all at once, such as
   `1:23:45`.
3. Choose **OK**. Playing jumps there and tells you where you are now.

#### Chapters, step by step

The chapter list works for a video's published chapters, the chapter marks
inside a recording or a downloaded episode, and episodes that QUILL Cast has
already worked through.

1. While something with chapters plays, press **Ctrl+Shift+C** (**Playback >
   Chapters...**). The Chapters window opens.
2. Its first line tells you how many chapters there are and where they came
   from. Your cursor is in the **Chapters** list (Alt+C), and the chapter
   playing now is marked.
3. Arrow to a chapter. Each one reads as a sentence, such as "3. Introducing
   layers, starts at 5 minutes 31 seconds".
4. To jump there, Tab to **Go To** and press **Space**. The list stays open,
   so you can keep exploring.
5. When what is playing is a file on your computer, **Preview This Mark** plays
   ten seconds either side of where the chapter starts, without moving your
   place. **Stop Preview** stops it.
6. Press **Escape** to close the list.

If there are no chapters, Quill Radio tells you. It does not make chapters up
for itself, because that needs a large speech engine, and QUILL Cast already
does it.

### Skip Silence, and a speed that sticks

**Skip Silence** (Ctrl+Shift+9, on the **Playback** menu) shortens the long
pauses in a recording, a YouTube row or a podcast episode as it plays. It is
lovely for a slow talk or a recording with lots of dead air, because it gets
you through faster without making anyone sound rushed. It works straight
away. It does nothing on live radio, and tells you so if you turn it on while
a station plays.

1. Play a recording, a podcast episode or a YouTube row.
2. Press **Ctrl+Shift+9**. You hear that Skip Silence is on.
3. Press **Ctrl+Shift+9** again to turn it off.

To change the speed as well:

1. Press **Ctrl+Shift+Up** to play faster, or **Ctrl+Shift+Down** to play
   slower. Each press tells you the new speed.
2. Press **Ctrl+Shift+0** to go back to normal speed.

**Your speed is remembered by kind.** A speed you choose while a recording
plays applies to every recording. One you choose on a YouTube row applies to
YouTube rows. Podcast episodes keep their own speed for each show.

### Continue Listening, step by step

Continue Listening lists everything you started and did not finish:
recordings, podcast episodes, audiobook chapters and anything else that is not
live.

1. Press **Ctrl+Alt+Shift+L** (**Playback > Continue Listening...**). The window
   opens, and a heading tells you how many things are unfinished.
2. Arrow through the **Unfinished** list (Alt+U). Each row says what it is and
   where you stopped.
3. Press **Enter**, or choose **Resume**, to carry on from where you stopped.
4. Choose **Forget This One** (Alt+F) to take a row off the list.
5. Press **Escape** to close.

Quill Radio and QUILL Cast keep your place in an episode you follow in the
same spot on your computer, so either app knows how far you got. An episode
that either app has finished stays finished.

### Bookmarks

**Bookmark This Moment** (Ctrl+Alt+A, on the **Playback** menu) marks where
you are in whatever is playing, with one key press: a station, a recording, a
saved YouTube row, or an episode of a podcast you follow. You do not need to
write a note.

#### Use bookmarks, step by step

1. While something plays, press **Ctrl+Alt+A**. You hear that the moment was
   bookmarked.
2. Later, press **Ctrl+Alt+Shift+J** (**Help > Bookmarks...**). The Bookmarks
   window opens with your cursor in **Everywhere you marked** (Alt+E).
3. Arrow to a bookmark and press **Enter**, or choose **Go There** (Alt+G), to
   go back to it.
4. The other buttons:
   - **Share** (Alt+S) copies the place, the note and what it is in.
   - **Edit Note...** (Alt+N) adds or changes a note.
   - **Delete** (Alt+D) removes everything selected. Hold Shift with the arrow
     keys to select several. It tells you how many it removed.
   - **Export...** (Alt+X) writes them all to a Markdown file, grouped by what
     each one is in.
5. Press **Escape** to close.

**A live station's bookmark is honest about what it can do.** Live radio has
no shared timeline, so a station bookmark keeps the station and how far into
your listening you were. Go There tunes you in to what is on now. A recording,
a video or a podcast episode does take you to the exact spot.

**Your bookmarks are shared with QUILL Cast.** A bookmark you make here is in
Cast's Bookmarks window, and the other way round. If Quill Radio cannot open
one, it is still listed, with Go There dimmed and the reason.

### Hardware media keys

Many keyboards and headsets have media keys: Play/Pause, Stop, Next and
Previous. Quill Radio listens for two of them all the time it is running, even
when another program has focus and even when Quill Radio is hidden in the
tray. So you can start and stop the radio without finding its window at all.

- The **Play/Pause** key starts or stops the radio. On live radio it does not
  pause, because live radio cannot be paused. It works like Play and Stop in
  the main window: when nothing is playing, it plays your selected favorite.
- The **Stop** key stops whatever is playing.

To try it:

1. Start Quill Radio, then switch to another program, such as your email.
2. Press the **Play/Pause** media key. The radio starts, and you hear what is
   playing.
3. Press it again, or press **Stop**, to stop the radio.

Good to know: the Next and Previous keys are not used. On Windows, media keys
go to whichever program asks first. If another program, such as a music
player, already has a key when Quill Radio starts, that key stays with the
other program, and Quill Radio says nothing. Close the other program and
restart Quill Radio to take it back. You can also give any playing command a
key that works everywhere, in **Help > Global Hotkeys...** (Ctrl+Alt+G).

Windows also knows what you are listening to. When you press a volume key,
Windows shows a small "now playing" panel, and the lock screen shows the same
thing. Quill Radio fills it in with the station and, when the station sends
one, the song. Your screen reader reads that panel when it appears. Quill
Radio does not announce it out loud each time the song changes; it is there
for when you want it.

### What you learned, and where to go next

You can now control what is playing from any window, open the Player, pause
anything that is not live, rewind live radio and catch up again, change the
speed, move by chapter, and bookmark a moment to come back to. Your keyboard's
media keys work too. Next, Chapter 5, What's playing, and how it sounds, helps
you find out what that song was and get the sound just right. The tutorials
**Keep a moment, and move around inside one** and **Pick up where you left
off** practise what this chapter covered.

## Chapter 5: What's playing, and how it sounds

This chapter answers two everyday questions: "what was that song?" and "can I
make it sound better?" It also covers the picture and captions for video, and
the timers that send you to sleep or wake you up.

### What's Playing, step by step

1. Press **Ctrl+T** (**Playback > What's Playing?**). The Now Playing window
   opens, titled "Now Playing:" and the station's name. If you press it again
   while the window is open, the window is refreshed and brought forward, and
   you hear the title and artist.
2. Your cursor is in a box with the title and artist. Arrow through it, a
   letter at a time if you want the exact spelling.
3. Tab to **Copy** and press **Space** to copy it. You should hear "Copied."
4. Press **Escape** to close.

If nothing is playing, you hear "Nothing is playing." and no window opens. If
no title has arrived yet, you hear "Checking what's playing..." while Quill
Radio finds out. A station that never sends titles opens the window with its
name and "This stream doesn't share track titles."

Quill Radio looks for the title in three places: first in what comes with the
sound itself, then in what the player can read from the stream, and last on
the station server's own public status page. It only ever asks the server you
are already listening to, and not in Safe Mode. When a station sends messy
text, such as catalog codes, Quill Radio picks out the title and artist for
you.

To change the words What's Playing uses, edit **What's Playing announcement**
in Preferences.

**Copy What's Playing**, in the Command Palette, copies the title and artist
straight to the clipboard with no window, and tells you what it copied.

**Announce Track Titles** (Ctrl+Alt+T, on the **Audio** menu) says each new
title as the song changes. It starts off. In the Command Palette it reads
"(currently On)" or "(currently Off)".

### Song History, step by step

Song History keeps what each station played while you listened: up to 200
songs for each station, kept only on your computer.

1. Press **Ctrl+Shift+H** (**Playback > Song History...**). If no songs have
   been noted yet, you hear that, and no window opens.
2. The Song History window opens with your cursor in the **Songs** list
   (Alt+O), newest first. Each row reads like "Your Song by Elton John, heard
   10:04, played twice".
3. To look at another station's list, press **Alt+A** for **Station** and
   choose it.
4. With a song selected, Tab to a button and press **Space**:
   - **Copy** puts the song on the clipboard.
   - **Send to Clip Library** keeps it with your other saved snippets.
   - **Background** asks your AI provider, if you have set one up, for a short
     note about the song and the artist. The answer always says it was written
     by an AI model. It appears in the **Background** box (Alt+K), and your
     cursor moves there. Not available in Safe Mode.
   - **Song Details** looks the song up on MusicBrainz: which release, what
     year, how long. If nothing more is known, it says so.
   - **Clear...** asks whether to clear **This station** or **All stations**.
     **Cancel** is already chosen, so Enter on its own clears nothing.
5. Press **Escape**, **Ctrl+W** or **Ctrl+F4** to close. Song History is a
   window of its own, with the menus **Songs** (Alt+G), **Station** (Alt+S) and
   **Window** (Alt+W).

Good to know: Song History only fills up while a station sends song titles.
Stations that send none, such as many talk stations and reading services,
leave nothing to note.

If a song is still playing when Quill Radio checks again, its play count goes
up rather than it being listed twice. Station names, "Live" and advert markers
are left out.

### Listening statistics

**View > Listening Statistics...** (Ctrl+Shift+Q) answers how much you
listened, as well as to what.

1. Press **Ctrl+Shift+Q**. The Listening Statistics window opens.
2. **Period** (Alt+P) chooses This week, This month, This year or All time. It
   starts on All time. When you change it, you hear the new total.
3. Tab to the report and arrow through it: the total time, how many sessions,
   then a breakdown **by station** and **by network**. Times are read as
   words, such as "3 hours, 47 minutes".
4. **Copy** (Alt+C) copies the whole report. You should hear "Copied."
5. **Save as CSV...** (Alt+S) writes every session to a spreadsheet file. The
   suggested name is `quill-radio-listening.csv`.
6. **Delete My History...** (Alt+D) removes every session. It asks first, and
   **No** is already chosen.
7. Press **Escape** to close.

What counts as listening:

- Only time when sound is actually coming out. Connecting, buffering, paused
  or stopped time does not count.
- Anything under ten seconds is not counted. Skipping past stations is not
  listening.

Your history stays on your computer.

### Volume

- **Ctrl+Up** and **Ctrl+Down** change the volume in steps of ten, from any
  window. In the main window they work everywhere except in a text box, where
  Ctrl with an arrow still moves through the text.
- **Ctrl+M** mutes and unmutes in the main window. **Ctrl+Shift+O** works in
  every window, including the main one.
- **Each favorite remembers its own volume.** Set it while the station plays,
  and it comes back at that level next time.
- **The last level you set is remembered** for everything else, from one day to
  the next.

#### One volume for every station

1. Press **Ctrl+Alt+V** (**Audio > Use One Volume for All Stations**). You
   should hear that one volume for all stations is on, and the level.
2. Now Ctrl+Up and Ctrl+Down turn everything up or down together. Turning it
   on keeps the level you are hearing, so nothing suddenly jumps.
3. Press **Ctrl+Alt+V** again to go back. Every station returns to its own
   remembered level.

#### Forgetting every station's own volume

1. Press **Ctrl+Alt+Shift+V** (**Audio > Forget Every Station's Own
   Volume...**).
2. A question tells you how many stations have their own level. **No** is
   already chosen. Press **Y** to forget them.
3. You should hear "Forgot the volume for" and how many. Your stations,
   folders and other settings are left exactly as they were.

### Volume Boost

Some stations broadcast much more quietly than others, so even full volume is
too soft. Volume Boost lets the radio go up to 50 percent past full volume.

1. While a quiet station plays, press **Ctrl+Shift+B** (**Audio > Volume
   Boost**). You should hear "Volume Boost on: up to 50 percent louder."
2. Press **Ctrl+Up** to turn it up. The Volume cell in the status bar adds
   "boosted".
3. Press **Ctrl+Shift+B** again to turn it off.

Your volume steps, each station's own level and mute all work as before.
Boost can make a station that is already loud sound distorted, so turn it off
when you move on.

If it does not work: Volume Boost needs the mpv playback engine. If Quill
Radio says so, set **Playback engine** to Automatic in Preferences.

### Output Device, step by step

You can send the radio to a different sound card or headset from your screen
reader. Many people like to hear the radio in headphones while speech stays
on the speakers, or the other way round.

1. Press **Ctrl+Shift+D** (**Audio > Output Device...**). A list opens: "Send
   Quill Radio's audio to which device?"
2. The first row is **System default**. Arrow to a sound card or headset. A
   device you chose before that is not plugged in reads "(not currently
   available)".
3. Press **Enter**. The station moves to that device straight away, without a
   break in the sound. You should hear "Output device" and its name.

Your screen reader and Quill Radio's own sounds stay on the system default.
This is the same setting as **Radio output device** in Preferences, and it
works on either playback engine, mpv or Windows Media.

Windows often calls both sound cards on a laptop "Speakers": "Speakers
(Realtek High Definition Audio)" for the built-in ones, and "Speakers (Logi
USB Headset)" for a headset. Listen past the first word for the make in
brackets.

#### If the device cannot be opened

Sometimes Windows will not let Quill Radio use a device just then: a Bluetooth
or USB headset that has gone to sleep, a device another program is holding,
or one whose Windows name has changed. Quill Radio tells you, names the
device, and puts the setting back to what it was, for example: "Speakers (Logi
USB Headset) could not be opened, so the output device is back to System
default." The sound stays on the device it was using before, and Preferences
shows the same. Wake the device or plug it in, then choose it again. If a
device you saved cannot be opened when Quill Radio starts, it is handed back
the same way, so you are never stuck with a setting that does nothing.

#### On an older copy of Windows

A few older copies of Windows do not have the modern media player that Quill
Radio's Windows Media engine uses, so Quill Radio falls back to an older,
classic one. That classic player always plays on whatever device Windows gives
it, and cannot be told otherwise. Quill Radio does not quietly change your
engine to get round this. Instead, choosing a device tells you so in one
sentence and opens Windows' Sound settings for you. Under **Volume mixer**,
every app has its own output device there. Find Quill Radio in that list and
choose the device, and Windows remembers it from then on. A copy without the
mpv engine opens that same page as soon as you press Ctrl+Shift+D. And if a
device is saved in your settings while the classic player is in use, Quill
Radio hands the setting back and tells you the same thing.

### Sound Enhancements, step by step

Sound Enhancements lets you shape the sound: more bass, clearer voices, an
even volume, or the sound in one ear only.

1. Press **Ctrl+E** (**Audio > Sound Enhancements...**). The Sound Enhancements
   window opens on **Quick preset**.
2. **Quick preset** (Alt+Q) sets the three tone sliders to a good starting
   point: Flat, Bass Boost, Voice Clarity, Podcast, Small Speakers or Late
   Night. If you then move a slider, the preset becomes Custom.
3. **Bass** (Alt+B), **Mid** (Alt+M) and **Treble** (Alt+T) are sliders from
   -12 to +12 dB. Use the arrow keys.
4. **Even Out Volume** (Alt+E) lifts quiet passages and calms loud ones.
5. **Channel mode** (Alt+H) is **Stereo**, **Mono**, **Left only** or **Right
   only**. Mono blends both sides together, so a voice on one side never
   disappears if you use one earbud. Left only or Right only sends everything
   to one ear, leaving the other free for your screen reader.
6. **Night mode (even loudness)** (Alt+N) keeps the loudness even as you
   listen, for quiet late-night listening.
7. **Apply broadcast polish (OptiLab)** (Alt+A) turns on a broadcast-style
   sound. **Polish mode** (Alt+P) is Off, Podcast Leveler (speech), Stream
   Polish (music) or Smooth Limiter (mastering). **Input (dB)** (Alt+I) turns
   the level going in up or down. **Auto-Adapt** (Alt+U) is a slider from 0 to
   100 percent.
8. **Exact OptiLab processing** (Alt+X) is **Off** (where it starts), **When
   saving** (the full OptiLab sound for recordings and converted files, and the
   one we recommend), or **When saving and while listening** (the station
   takes longer to start, and each change needs a short reconnect). If your
   copy does not include the OptiLab part, this choice is dimmed and says so.
9. You hear every change on what is playing straight away.
10. Choose **OK** to keep your settings, or **Cancel** (Escape) to put
    everything back as it was.

Broadcast polish is adapted, with thanks, from **OptiLab Core by Lanes Audio /
dgl1984** (https://github.com/dgl1984/optilab, Apache-2.0 with the Commons
Clause). While you listen, Quill Radio always uses its own built-in version,
so you hear each change at once.

Recordings are kept exactly as the station sent them unless you turn on
**Apply Sound Enhancements to recordings** in Recording Settings.

#### For one station, or for every station

Open Sound Enhancements while a favorite plays, and your settings are saved
for that station only. Open it with nothing playing, or while a station that
is not a favorite plays, and you set the shared settings that every other
station follows. When a favorite's own settings are open, **Reset to Default**
(Alt+R) puts that station back on the shared settings. **Reset All Stations'
Sound Enhancements...** in Preferences does that for every station at once.

### Video, captions and described audio

Quill Radio plays YouTube links and television as sound only, to begin with.
You can also show the picture, read the captions, and choose a described
audio track.

#### Show the video, step by step

1. While a video or TV channel plays, press **Ctrl+Shift+V** (**Video > Show
   Video**). The "Quill Radio Video" window opens. You should hear "Video
   shown" and its size.
2. The picture has a name and description for your screen reader. Tab takes
   you to a line telling you the title, position, chapter and audio track.
3. Press **F11** for full screen. You should hear "Full screen. Press F11 or
   Escape to leave."
4. Press **Escape** to leave full screen. Press **Escape** again, or
   **Ctrl+Shift+V**, **Ctrl+W** or **Ctrl+F4**, to close the window. You should
   hear "Video hidden. Audio is still playing."

Showing and hiding the picture never restarts what is playing or loses your
place. The window has no buttons: every command is on the Video menu, in the
Command Palette, and on a key. The playing keys work inside it too.

The rest of the Video menu:

- **Video Information** (Ctrl+Shift+I) tells you the size, the frame rate, and
  whether captions and described audio are available.
- **Take a Snapshot** (Ctrl+Shift+Alt+H) saves the current picture into your
  recordings folder, for example so you can read a slide with OCR. You should
  hear "Snapshot saved as" and its name.
- **Video Size** (Ctrl+Alt+4 to Ctrl+Alt+7) sets the window to Fit, 50%, 100%
  or 200%.

Nothing can tell before a video plays whether it contains flashing, so Quill
Radio makes getting away from the picture immediate: Ctrl+Shift+V hides it
from any window.

#### Captions, step by step

1. While a video plays, press **Ctrl+Shift+K** (**Video > Captions**). You
   should hear "Getting captions...", then "Captions on, in the Captions
   window."
2. The "Quill Radio Captions" window opens without taking your cursor. Switch
   to it with **Ctrl+Tab** or Alt+Tab.
3. The captions are text you can arrow through. Each new line is added after
   the ones already spoken, so the newest is last. The line being spoken now
   is marked with a greater-than sign.
4. To read back without the text moving, turn off **Follow playback** (Alt+F).
5. Press **Escape** to close the window. Closing it turns captions off. You
   should hear "Captions off."

If the captions were made by a computer, the window tells you. A video with no
captions says "This video has no captions published."

#### Caption Settings, step by step

1. Press **Ctrl+Shift+Alt+T** (**Video > Caption Settings...**).
2. Set **Caption size** (100 to 300 percent), **Text colour** (Alt+T),
   **Background colour** (Alt+B), **Background opacity** (Alt+O, a slider)
   and **Position** (Alt+P, bottom or top).
3. Choose **Save**. Quill Radio reads the new style back to you.

Captions start as solid white on solid black. That looks heavier than most
players on purpose, because captions sit over whatever the picture shows, and
no colour is readable against everything.

#### Audio and Described Audio, step by step

A described audio track is a second narration that tells you what a sighted
viewer can see. Quill Radio names it and puts it first.

1. While a video plays, press **Ctrl+Shift+A** (**Audio > Audio and Described
   Audio...**). The window opens. Its heading says "Described audio is
   available for this video." or "No described audio was published for this
   video."
2. Your cursor is in the **Audio tracks** list, on the described track when
   there is one. Tracks in the language you use Quill Radio in come first,
   then the video's original track, then the rest in alphabetical order.
3. Press **Enter**, or choose **Play This Track**, to switch. Your place is
   kept.
4. You should hear "Playing the described audio track." or the track's name.

**Play Described Audio** (Ctrl+Alt+D) switches straight to the described
track, with no list. If there is none, it tells you what the video does have.

When you play a video that has a described track, Quill Radio tells you once,
and tells you the key.

A YouTube video's transcript, which you can read, search and play from, is in
Chapter 11, YouTube, under "Transcript, step by step".

### Timers

#### Sleep Timer, step by step

Like to fall asleep to the radio? The sleep timer fades it out for you.

1. Press **Ctrl+Shift+Z** (**Playback > Sleep Timer...**). The Sleep Timer
   window opens.
2. Choose how long in **Stop Radio and Podcasts playback after**: 15, 30, 45,
   60 or 90 minutes, or **Custom...**. With Custom, Tab to the minutes box and
   type a number from 1 to 600.
3. Choose **Start** (Enter). You should hear "Sleep timer set for" and the
   minutes.
4. When the time is up, the sound fades out and stops, and your volume is put
   back where it was. You should hear "Sleep timer: playback stopped, volume
   restored."

While a timer is running, the same window shows the time left and offers
**Extend 5 Minutes** and **Cancel Sleep Timer**. The Sleep timer cell in the
status bar shows the minutes left; press Enter on it to open the window. The
Command Palette also has **Extend Sleep Timer 5 Minutes** and **Cancel Sleep
Timer**.

#### Wake-Up Timer, step by step

The Wake-Up Timer starts a favorite at a time you choose, once or every day.

1. Press **Ctrl+Alt+Z** (**Playback > Wake-Up Timer...**). The window tells you
   the current setting.
2. Check **Wake up with the radio** (Alt+W) with Space.
3. Choose a **Station** (Alt+S) from your favorites.
4. Type a **Time** (Alt+T), such as `07:00` or `7:30 AM`.
5. Check **Every day (not just once)** (Alt+D) if you want it every day.
6. Choose **OK**. You should hear your setting read back.
7. At that time you hear "Good morning." and the station's name, and it
   starts playing.

Quill Radio must be running at that time. Running in the tray counts; a
closed app does not. The Wake-Up Timer does not wake a sleeping computer. To
turn it off, open it and uncheck **Wake up with the radio**.

### What you learned, and where to go next

You can now find out what is playing and look back at what played, see how
much you have listened, set the volume your way, boost a quiet station, send
the radio to another sound card, and shape the sound. You know how to show a
video, read its captions and choose described audio, and how to use the sleep
and wake-up timers. Next, Chapter 6, Finding something to listen to, opens up
the whole world of stations. The tutorials **What was that song?**, **Shape
the sound**, **How much did I actually listen?**, **Sleeping, waking, and
being left alone** and **The picture, captions and described audio** go with
this chapter.

## Chapter 6: Finding something to listen to

There are tens of thousands of stations out there, and this chapter shows you
how to find the ones you will love. You will wander through Browse Stations,
search every directory at once, find a station from its web address, and add
stations that no directory lists. None of it needs an account or a sign-in.

The **Finding something to listen to** track of the tutorials walks through
all of this: **Wander the browse tree**, **Search every directory at once**,
**Find a station by its web address**, **Find stations by name, tag and
country**, **Add a station nobody lists**, **The catalog on your own disk**
and **When a station will not play**.

### Browse Stations

Browse Stations (Ctrl+B) is one window with one big tree. Its first row is
**Search All Sources...**. Below that, each top-level branch is a source of
things to hear. Open a branch and its contents load there and then. **Enter**
plays the row you are on.

#### Open it and look around, step by step

1. Press **Ctrl+B** from any window. Browse Stations opens, or comes to the
   front if it is already open. Your screen reader reads the title, and your
   cursor is in the tree.
2. Browse Stations remembers the branch you were in last time. The very first
   time, you are on **Search All Sources...**.
3. Press **Down Arrow** to move from branch to branch. Nothing is fetched until
   you open one.
4. Press **Right Arrow** to open a branch. You should hear "Loading" and the
   branch's name. If it takes more than three seconds, Quill Radio tells you
   it is still working.
5. Press **Down Arrow** to move through what loaded. A folder tells you how
   many rows it holds, for example "France, 812 stations".
6. Press **Enter** on a station, episode or chapter to play it. Press **Enter**
   on the row that is playing to stop it.
7. Press **Shift+F10**, or the Applications key, for everything a row offers.
   See "What a row offers" below.
8. Press **Tab** to move past the tree. You come to a **details box** about the
   row you are on, then **Radio volume**, **Mute**, **Go to Player**, **Add to
   Favorites** (it reads **Remove from Favorites** on a row you have saved),
   and **Refresh**, which fetches the highlighted source again from the
   internet.
9. Press **Alt+T** to jump back to the tree from anywhere in the window.
10. Press **Escape**, **Ctrl+W** or **Ctrl+F4** to close Browse Stations. What
    you are listening to keeps playing.

The details box follows the row you are on. For a station it gives the
source, stream, format and country, and any note to yourself you have written
about it. For a branch it says whether it answers from the catalog on your
computer or asks the internet each time. If you would rather not Tab past it,
turn it off with **View > Show Station Details** (Ctrl+D).

The window's menu bar has **Browse** (Alt+B) with **Close** (Ctrl+W),
**Station** (Alt+S) and **Window** (Alt+W).

#### The branches, in order

After **Search All Sources...**, the branches are:

1. **Favorites**: your own stations and folders.
2. **Local Media**: your own music, audiobooks and video, in playlists
   you make. See Chapter 10, Local Media, your own music and audiobooks.
3. **Popular Stations**: ranked by votes over the years.
4. **Trending Now**: ranked by what people are listening to today.
5. **Recently Added or Changed**: new stations, and ones whose address was
   just repaired.
6. **By Country**: then by state or region, then stations. A country with no
   regions takes you straight to its stations.
7. **By Language**.
8. **By Genre**.
9. **By Quality**: by sound format.
10. **Weather / NOAA**: the NOAA Weather Radio directory, state by state.
11. **ACB Media**: ACB Media 1 to 10.
12. **Double Tap Live**: the blind tech show's own 24-hour channel, with talk,
    tech, music and the best of the Double Tap podcast, on air around the
    clock.
13. **NFB Radio**: the NFB Radio Network.
14. **Radio Reading Services**: services that read print aloud for blind and
    print-disabled listeners.
15. **Westwood One Sports**: Westwood One's ten live event channels. During
    the NCAA tournaments, the NFL and other big events, each one carries a
    different game.
16. **SomaFM**.
17. **TuneIn**: TuneIn's own folders, from continent down to city.
18. **iHeart**: **By City** first, then genres.
19. **Networks**: well-known broadcasters, grouped by type.
20. **Community M3U (Music Genres)**.
21. **Xiph / Icecast Directory**: switched off to begin with.
22. **SHOUTcast Directory**: the live Top 500, then 313 genres.
23. **Live365**: about 5,500 independent stations, A to Z.
24. **Quillin Sources**: only when an installed Quillin adds a source.
25. **Radio Paradise**: including lossless FLAC.
26. **Podcasts (Apple)**: your Subscriptions, then 16 national storefronts.
27. **Podcast Index**.
28. **Internet Archive**.
29. **LibriVox Audiobooks**.
30. **Project Gutenberg Audiobooks**.
31. **AudioPub (Community Audio)**.
32. **Audius (Independent Music)**.
33. **Mixcloud (Shows & DJ Sets)**.
34. **ccMixter (Creative Commons)**.
35. **My Servers**: Icecast or SHOUTcast servers you add yourself.
36. **Television (iptv.org)**.
37. **YouTube**: channels, playlists and videos you save.
38. **Explore (Wikidata)**: switched off to begin with.

That is 36 sources. A new installation shows 34 of them, because Xiph and
Wikidata start switched off. Quillin Sources only appears when something adds
to it. You can switch branches on and off with **Choose Browse Sources**,
described later in this chapter.

#### More about some of the branches

- **Weather / NOAA** lists the states, each with how many transmitters it has.
  Open a state for its transmitters, named with call sign, frequency and
  place, such as "KHB36 162.550 MHz Manassas". Enter plays the best internet
  stream of it available. The whole directory of 1,035 transmitters comes
  with Quill Radio, so this branch works with no internet.
- **Radio Reading Services** comes with twenty trusted services, including
  WRBH 88.3 Reading Radio, Sun Sounds of Arizona, CRIS Radio, the KPBS and
  WKAR reading services, ACB Media 1 to 5 and the NFB Radio Network. Play,
  favorite, record and schedule them like any other station.
- **iHeart** opens into **By City** (317 markets) and then genres. Each genre
  opens into A to Z letter folders of stations.
- **By Country, By Language, Trending Now** and **Recently Added or Changed**
  are different views of the same community directory. Trending and Popular
  often disagree, and that is fine: one is about today, the other about years.
- **Double Tap Live** is the round-the-clock channel of Double Tap, the daily
  show where blind people talk tech, from Steven Scott and Shaun Preece at
  Accessible Media Inc. It has been on air since 30 September 2026, with talk,
  tech, music and the best of the podcast. It sits right under ACB Media,
  because it is made for exactly the people who use this radio. What's
  Playing reads the segment or song the stream announces, and you can
  favorite, record and schedule it like any station.
- **Westwood One Sports** lists the network's ten live event channels,
  Westwood One Sports channel 1 to channel 10. That is every stream Westwood
  One publishes. During a big event such as the NCAA basketball tournament,
  each channel carries a different game at the same time, and the schedule at
  westwoodonesports.com tells you which game is on which channel. Between
  events a channel may be silent. You can favorite, record and schedule them
  like any station, and a recording scheduled on channel 3 records whatever
  game channel 3 carries at that time. Sometimes the rights to a game keep it
  off the internet, and the channel then says so.
- **Networks** groups well-known broadcasters: public broadcasters such as the
  BBC, NPR, CBC, ABC Australia, Radio France and Deutschlandfunk, plus US news
  and talk, sports, music, and syndicators. A syndicator such as Westwood One
  has no single stream, so it opens a search across the stations that carry
  it, and its name tells you so.
- **SHOUTcast Directory** starts with **Top 500 (most listeners right now)**,
  then 313 genres. Each genre is sorted by how many people are listening, most
  first. SHOUTcast gives at most 500 stations per genre. A SHOUTcast station
  takes a moment to start, because its address is looked up when you press
  Enter. If it cannot be found, Quill Radio tells you.
- **Live365** is arranged A to Z. Names that start with a number or symbol are
  under **#**. The whole list is fetched once a day, so opening a letter
  needs no wait.
- **Radio Paradise** lists each channel once for each quality: 320k AAC first
  (where Enter lands), then 192k MP3, 128k AAC, 64k and 32k AAC+, and FLAC
  last, because it is lossless and the heaviest.
- **Podcasts (Apple)** starts with **Subscriptions**, then storefronts such as
  United States, United Kingdom, Ireland, Japan and Brazil. A storefront holds
  Top Podcasts, Top Episodes and Apple's genres. Each genre, and each
  subgenre under it, lists Apple's own top shows for it, up to 200. Opening a
  show reads the publisher's own feed. See "Podcasts in Browse Stations" in
  Chapter 9.
- **Podcast Index** offers **Trending Now**, **By Category** (112 categories)
  and **Search the Podcast Index...**. You can open any show without
  following it. If a folder cannot load, Quill Radio tells you why. If your
  copy has no Podcast Index key, the branch shows one row, **Add a Podcast
  Index Key...**, instead. See "Apple's categories and the Podcast Index" in
  Chapter 9.
- **Internet Archive** offers Old Time Radio, Audiobooks & Poetry, the Live
  Music Archive, Radio Programs, News & Public Affairs and more. A folder with
  more than one page ends with **More...**. An item that publishes no rights
  information tells you so.
- **LibriVox Audiobooks** offers **Recently Added**, **By Genre** (43 genres)
  and **By Author**, A to Z. A book with chapters is a folder of chapters.
- **Project Gutenberg Audiobooks** offers All Audiobooks, twelve topics and
  eight languages, with a "More audiobooks" row to see the next page.
- **AudioPub (Community Audio)** has one shelf, **Discover**: a random fifty,
  different every time. Nothing from AudioPub is stored on your computer.
- **Audius** offers Trending Now and 27 genres, and leaves out tracks you have
  to pay for. **Mixcloud** lists DJ sets and radio shows. A Mixcloud row opens
  on the Mixcloud website in your browser, and the row tells you so before you
  press Enter. **ccMixter** is Creative Commons music by tag, with each
  track's licence on its row.
- **Explore (Wikidata)**, when you switch it on, offers **By City**, **By
  Format** and **On the Dial** by FM band. Its rows say "from Wikidata". The
  streams themselves still come from Radio Browser.

#### How the tree behaves

- **Numbers in names sort like numbers.** You get "ACB Media 1, 2, 3 ... 10",
  not "1, 10, 2".
- **Some branches remember where you stopped.** A LibriVox chapter, an Old
  Time Radio episode or a podcast episode keeps your place as you listen. A
  few seconds in is not worth keeping, and finishing something clears its
  place.
- **A slow branch tells you it is slow, and a broken one tells you it is
  broken.** An empty branch tells the two kinds of empty apart. "Nothing in
  here" is a real answer. "Could not be reached. Open it again to try." means
  try again later. If it fails twice or more in a row, it adds a count, such as
  "It has failed 3 times in a row -- the directory itself may be down. You
  can hide it in Browse Sources." Quill Radio never switches a source off for
  you.
- **The tree reads ahead.** When you land on a closed folder, Quill Radio
  quietly starts fetching what is inside, so it opens at once when you press
  Right Arrow. Safe Mode fetches nothing.

### What a row offers

Press **Shift+F10**, or the Applications key, on any row.

#### On a station, episode, chapter or video

In this order:

- **Play**, or **Stop** if it is playing. A downloaded file offers **Play** or
  **Pause**, then **Stop**.
- **Add to Favorites** or **Remove from Favorites**.
- **Station Details...**, which reads you the details.
- **Copy Stream Link** (or **Copy Link** for a recording).
- **Rename Favorite...**, only on a row you have saved. Leave the name blank
  to go back to the directory's own name.
- **Open Website**, when the station has a home page.
- **Download...** or **Remove Download**, where the source allows saving.
- **Record This Station...** and **Schedule Recording...**, on a live station.
  Both come filled in with this station.
- On an episode of a show you follow: **Mark Episode as Played** (or **as
  Unplayed**), **Play Next in QUILL Cast**, **Add to QUILL Cast Queue** and
  **Send to the QUILL Cast Inbox**.
- **Report Bad Station...**, on a live station.
- On the row that is playing, when it is not live: **Previous Chapter**,
  **Next Chapter**, **Chapter List...**, **Captions On or Off**, **Where Am
  I?**, **Speed Up**, **Slower** and **Back to Normal Speed**, each with its
  key.
- **View Transcript...**, on podcast episodes and YouTube rows.
- **Read Comments...**, on a YouTube video.
- **Remove from YouTube** and the three **Add a ...** items, on a saved
  YouTube video.
- **Set a Reminder...**, or **Remove Reminder** once it has one.
- **Note to Self...**, always last.

#### On a folder

- **Open** or **Close**, and **Refresh**.
- On a podcast show: **Subscribe to This Podcast** or **Unsubscribe from This
  Podcast**, and **Copy Feed Address**. A show you follow also has **Move to
  Folder...**, **Mark All as Played...**, **Download All Episodes...** and
  **Remove All Downloads...**.
- **Add All ... to Favorites**, once its rows have loaded.
- **Add This Place to Favorites** (or **This Show**), on a folder below the top
  level.
- **Download All ... Files...**, on a book or collection you are allowed to
  save.
- **Close Search Results**, on a Search Results branch.
- On a YouTube channel: **Follow This Channel in Quill Radio**, or **Stop
  Following This Channel** and **Notify Me About New Videos** (or **Stop
  Notifying About New Videos**) once you follow it, and **Subscribe on
  YouTube...**.
- On a top-level source: **Search This Source...** (where the source can be
  searched), **Source Options...** (where it has options), **Hide This
  Source** and **Reset Sources to Default**.

A dimmed item tells you why it is dimmed. See "Why a menu item is dimmed" in
Chapter 15.

#### The Delete key

**Delete** removes the row you are on, when it is yours to remove: a saved
YouTube video, playlist or channel, a server you added, or a favorite. It asks
first and names the row, and **No** is already chosen. The question has a
**Don't ask me again** box. On a top-level source such as Podcasts, Delete
hides the source, just like **Hide This Source** on the menu, and **Reset
Sources to Default** brings it back. On a folder inside one of Quill Radio's
own sources, Delete explains that there is nothing to delete.

#### A note to yourself about any station

**Note to Self...** sits at the end of every row's menu. Use it to write
yourself a reminder about a station or a show, such as "the morning show is
the good one", "only worth it on Sundays", or "the 6am repeat is the one with
the interview".

1. Arrow to the row, press **Shift+F10**, and choose **Note to Self...**.
2. A box opens with any note you already wrote. Type whatever you like.
3. Choose **OK**.

The next time you arrow onto that row, your note is read in the details box,
so you never need to open anything to find it. To remove a note, empty the box
and choose OK. The note stays with the station's address rather than its name,
so renaming it, sorting your favorites or refreshing the catalog never loses
it or moves it to another row. In the Favorites Manager, a station's menu has
**Note to Self...** too.

#### Your own tags on a station

A note is for reading. A tag is for finding. If you know something about a
station that its name does not say, such as the team it carries or the show
you love on it, give it a tag, and every search will find the station by that
word.

1. Arrow to the station, press **Shift+F10**, and choose **Edit Station
   Tags...**. It is on the station rows here, in Search Stations, on your
   favorites in the main window and in the Favorites Manager.
2. Type your tags in **Your tags**, with a comma between each one. For
   example: `Detroit Tigers, MLB, baseball`.
3. Below that, **Directory tags** shows the tags the station directory already
   gave it. You cannot change those, but they are searched too.
4. Choose **OK**. Escape closes the box and changes nothing.

Your tags are read in the details box and in **Station Details**, just after
the directory's tags. To remove them, empty the box and choose OK. A favorite
keeps its tags with it, so they come along in a backup and in Export My Setup.
A station that is not a favorite keeps its tags too, and they move with it if
you add it to your favorites later.

To tag the station you are listening to, open the **Command Palette** from the
Help menu and choose **Edit Tags for the Playing Station**.

### Find in this folder, step by step

Above the tree is a search box. It searches from the folder you are on,
downward.

1. In the tree, highlight the folder you want to search, such as one iHeart
   genre, one state or a podcast show.
2. Press **Ctrl+F**. Your cursor moves to the **Find in this folder** box
   (Alt+I), and you should hear "Find in this folder."
3. Type what you want and press **Enter**.
4. The matches take the place of the folder's contents, and your cursor moves
   to the first one. You should hear how many matched.
5. Press **Escape** in the box, or clear the text, to go back to the folder
   you searched from.

Find picks the quickest way to search where you are standing, and tells you
which it used:

- On **Podcasts**, it asks a real podcast search engine. Shows come back as
  folders that open straight into episodes.
- On **By Country, By Language, By Genre** and **By Quality**, it answers at
  once from the catalog on your computer, limited to where you are. Find
  "jazz" while you are on France and you get France's jazz stations, with or
  without the internet.
- On **LibriVox**, the **Internet Archive**, **TuneIn**, **iHeart**, **NOAA**
  (by call sign, SAME code, or "County, ST"), **Project Gutenberg**,
  **SomaFM**, **Audius**, **Mixcloud** and **ccMixter**, it uses that source's
  own search.
- On a **podcast show**, it searches the episodes, show notes included.
- Anywhere else it looks through the folder itself, within limits, and tells
  you if it only showed the first results.

If you type a **web address** instead of a name, Find looks on that website
for its stream, wherever you are standing. See "Find a station by its web
address" below.

### Search All Sources, step by step

**Search All Sources...** at the top of the tree asks every directory at once.

1. Press **Ctrl+B**, then **Home** to go to **Search All Sources...**.
2. Press **Enter**. A box opens: "What are you looking for? Every source is
   searched at once."
3. Type a name, a call sign or a genre and press **Enter**.
4. You should hear that it is searching. After about four seconds you hear
   "Still searching", and you keep hearing it until the answer arrives.
5. The answer appears as a **Search Results** branch under Search All Sources,
   with your cursor on it. Open it and arrow through the results.
6. To close the results, press **Delete** on the Search Results branch, or
   choose **Close Search Results** from its menu. Nothing is lost.

Worth knowing:

- **The whole search takes at most eight seconds.** Any source that did not
  answer in time is named in the results, such as "Internet Archive did not
  answer within 8 seconds". Search again and it is usually there.
- **Searching for the same thing twice is instant.** Answers are kept for ten
  minutes, while a fresh search runs quietly and replaces them.
- **You can start one from the Find box.** On Search All Sources, or inside its
  results, press Ctrl+F, type and press Enter. That searches every source.
- **Search All Sources asks every directory**, even branches you have hidden
  from the tree.
- **Opening Browse Stations gets the first search ready.** It quietly fetches
  the three directories whose whole list is kept on your computer (Live365,
  Radio Paradise and SHOUTcast's genre list), once each time you run Quill
  Radio. Safe Mode skips this.

### Find a station by its web address

No directory has every station. OJ 99.1 (WWOJ, Avon Park, Florida) is in
neither TuneIn nor RadioBrowser, so no spelling of its name will find it. But
its website has the stream on it, and that is enough.

1. Press **Ctrl+B**, then **Ctrl+F** to reach the Find box. Search All Sources
   and the Search Stations window work too.
2. Type the station's web address as you would in a browser, such as
   `oj991.com`. You do not need `https://`.
3. Press **Enter**. Quill Radio fetches that one page and finds the stream its
   player uses.
4. You should hear that one stream was found. A **Website** row appears, named
   for the station. Play it, favorite it or open its menu like any other row.

This looks at one page; it is not a web search. If you type something that is
not an address, such as "jazz", the directories are searched as usual. An
address with no stream on it gets "Nothing found on that website."

### Search Stations

**Station > Search Stations...** (Ctrl+F) opens a search with separate fields
for name, genre and country. The window's title is **Internet Radio**, and Go
To calls it Find Stations.

#### Search by name, tag and country, step by step

1. Press **Ctrl+F**. You should hear "Internet Radio", then the **Station
   name** field (Alt+M), where your cursor is.
2. Type a name, a frequency or a call sign, such as `WQXR` or `105.7`.
3. Press **Enter**. You should hear how many results came back, and your cursor
   moves to the first one.
4. Arrow through the results. Each row names the station and the directory it
   came from, such as "via iHeart".
5. Press **Enter** on a result to play it. Press **Enter** again to stop it.
6. To keep it, Tab to **Add to Favorites** and press **Space**.
7. Press **Escape** to close the window. The station keeps playing.

To narrow things down:

- **Tag/genre** (Alt+T) and **Country** (Alt+O) are drop-down lists filled from
  the directory. Choosing one searches straight away.
- **Source** (Alt+U) shows results from just one directory: All sources, Radio
  Browser, iHeart, TuneIn, Podcasts, SomaFM, ACB Media, Community M3U, Xiph,
  Spotify, YouTube or Website. It filters what you have without searching
  again.
- **Category** (Alt+Y) switches the window to a list instead of a search:
  Favorites, Popular Stations, ACB Media, SomaFM, TuneIn, Music Genres, Xiph
  Directory or Search Results. The window opens on Favorites.
- In the **Station name** field, press **Down Arrow** for searches you ran
  before, newest first. Choosing one brings back the name, tag and country
  together. It remembers fifteen.
- When Radio Browser has more than 200 results, the **More Stations** button
  loads the next lot and puts your cursor on the first new station.

After the results, Tab reaches a **Station details** box, the status line,
**Radio volume**, **Mute**, **Play** (reads **Stop** while the selected station
plays), **Add to Favorites**, **More Stations**, **Add Custom Station...**,
**Find Streams from a Website...** and **Refresh**. In the Music Genres
category, Refresh reads the genre list again. Shift+F10 on a result offers
Play or Stop, Add to or Remove from Favorites, Open Website and Report Bad
Station....

The window's menus are **Go** (Alt+G, with **Close**, Ctrl+W), **Station**
(Alt+S) and **Window** (Alt+W). The Genre box also uses the letter G, so if
Alt+G lands on the Genre box, press **Alt** on its own and arrow to the Go
menu.

#### What a search does for you

- **It starts on your own computer.** Matches from the station catalog appear
  the moment you press Enter, and the live directories add theirs after. So a
  search still answers when the internet does not.
- **You do not have to spell it the directory's way.** `14.90 AM` finds 1490,
  `1009` finds 100.9, and `105-9` finds 105.9. A "play" or "listen to" at the
  start is ignored, and FM or AM at the end does not throw it off. Naming the
  state helps: `Sunny 105.7 Gulf Shores Alabama` finds the station Radio
  Browser only knows as "WCSN 105.7 FM Orange Beach".
- **The likeliest answer comes first.** A station that matches both name and
  frequency comes above one that matches only the frequency. Between two
  equally good matches, the one known to play comes first.
- **Weather radio places work.** A six-digit SAME code, a call sign such as
  `KHB36`, "County, ST" or a state name also finds NOAA Weather Radio
  transmitters. Reading services match by name, tag or state.
- **The libraries are searched too.** LibriVox, the Internet Archive, Project
  Gutenberg, Apple Podcasts, Audius, Mixcloud and ccMixter answer a moment
  after the stations. Quill Radio tells you once when they have all answered,
  and keeps your place if you are already arrowing. Enter on a podcast show
  plays its latest episode. A LibriVox book plays its first section. An
  Internet Archive collection tells you it opens on its own website.
- **A web address looks on that website** for its stream. See "Find a station
  by its web address" above.
- **It knows which station carries your team.** Type a team, such as `Tigers`
  or `Detroit baseball`, or a league, such as `MLB`, and the team's flagship
  radio station comes up near the top, with the reason in the row: "carries
  the Detroit Tigers". Quill Radio comes with a checked list of flagship
  stations for MLB, NFL, NBA, WNBA, NHL and MLS teams. A team that only
  streams its games, or whose station could not be confirmed, is not on it.
- **Your own tags count.** A station you tagged comes up for any of your tags,
  and the row says which one, such as "has your tag Red Wings". See "Your own
  tags on a station" above.
- Search is off in Safe Mode.

#### Search Sources, step by step

Search Sources decides which directories Search Stations asks. There are
twelve, all on to begin with: Radio Browser, TuneIn, iHeart, SomaFM,
SHOUTcast, Live365, TV, Radio Paradise, NOAA Weather Radio, Radio Reading
Service, Spotify and YouTube. "YouTube in Search Stations" in Chapter 11 says
what the YouTube one finds.

1. Press **Ctrl+Alt+Shift+U** (**Station > Search Sources...**). The Search
   Sources window opens with your cursor in the **Sources** list.
2. Arrow through the list. Each row says whether it is on first, such as "On.
   TuneIn."
3. To change one, Tab to **Turn On or Off** and press **Space**. You should
   hear the source's name and "on" or "off".
4. **Turn On All** turns every source on. **Reset to Default** puts things back
   as they started.
5. Press **Escape** or choose **Close**. Quill Radio tells you which sources it
   will search.

A source that is off is never asked by Search Stations, so searching is
quicker and quieter. The libraries are not on this list.

### Choosing your sources

#### Choose Browse Sources, step by step

If Browse Stations has branches you never use, you can tidy them away.

1. Press **Ctrl+Shift+Alt+O** (**Station > Choose Browse Sources...**). The
   Browse Sources window opens with your cursor in the **Branches** list.
2. Arrow through the list. Each row says whether it is on first, such as "On.
   LibriVox Audiobooks. Public-domain audiobooks, by chapter." The rows are in
   groups: Yours, Stations, Accessibility, Spoken word, Music, Explore.
3. Press **Enter** or **Space** on a row to turn it on or off. You should hear
   the source's name and "on" or "off". The **Turn On or Off** button does the
   same.
4. **Turn On All** turns every source on. **Reset to Default** goes back to
   what a new installation shows.
5. Press **Escape** or choose **Close**. Your choice is already saved. If
   Browse Stations is open, it rebuilds at once, and you hear "Browse Stations
   has been updated."

A branch that is off is not in the tree at all, and is never contacted while
you browse. A source added in a later version shows up unless you hide it.

You can also tidy up from the tree itself: press **Delete** on a top-level
branch, or press **Shift+F10** on it and choose **Hide This Source**. **Reset
Sources to Default** is on the same menu.

#### Source Options, step by step

Two sources have options of their own: Radio Paradise and the SHOUTcast
Directory.

1. In Browse Stations, arrow to the top-level **Radio Paradise** or
   **SHOUTcast Directory** row.
2. Press **Shift+F10** and choose **Source Options...**.
3. A list opens. For **Radio Paradise Quality**, choose which quality comes
   first for each channel (320 kbps to begin with). For **SHOUTcast Stations
   to Show**, choose everything the directory lists (the starting choice) or
   only stations someone is listening to right now.
4. Press **Enter**. Quill Radio reads your choice back and reloads the branch.

### My Servers, step by step

A church, school or community station that runs its own Icecast or SHOUTcast
server is often in no directory at all. You can add it yourself.

1. Press **Ctrl+B**, arrow to **My Servers** and press **Right Arrow**.
2. Arrow to **Add a Server...** and press **Enter**. A box opens. If an address
   is on your clipboard, it is already filled in.
3. Type or paste the server's address, including its port number, and press
   **Enter**.
4. Quill Radio checks it before saving. You should hear, for example, "Added
   http://stream.example.org:8000. It has 4 stations." An address that answers
   with nothing is not saved, because that nearly always means a wrong address
   or a missing port number.
5. Open the server's folder. Every stream is there, with what is playing on it
   right now.

### The Station Catalog

Quill Radio comes with a directory of working stations built in: more than
62,000 stations from 240 countries, plus SomaFM and the Project Gutenberg
audiobook shelf. It keeps them in a catalog on your own computer. That makes a
real difference:

- **Browsing answers at once, with or without the internet.** By Country, By
  Language, By Genre and By Quality answer from your own computer. Even the
  very first time you open Quill Radio with no internet at all, you have a
  complete radio.
- **Every folder tells you its size before you open it**, such as "France, 812
  stations".
- **Search starts on your computer.** Catalog matches appear the moment you
  search, and the live directories add theirs after.
- **A row that probably will not play tells you so.** Radio Browser checks
  every stream it lists, and rows it could not play are marked "may not be
  playable". Rows that have to be looked up before they start, such as TuneIn
  and YouTube, say "resolved when you play it". Other rows have no mark,
  because only Radio Browser publishes a check.
- **If you are offline, Quill Radio tells you once**, for example "You are
  offline. Browsing from your catalog, updated this morning.", and carries on
  working.

#### What is stored, and what is not

The catalog holds Radio Browser's stations and every way of browsing them,
SomaFM, and the Project Gutenberg audiobook shelf. Everything else stays live
and needs the internet, each for a reason: **Apple Podcasts** (Apple's terms
do not allow storing its charts), **TuneIn** (its folders may not be stored),
**iHeart** (its terms do not allow storing its listings), the **Internet
Archive** (far too large), **LibriVox** (live for now), and the **music
charts** (out of date the moment they are stored).

In Browse Stations, the details box tells you for each branch: "Answers from
your catalog, updated 2 hours ago" or "Asks the internet each time; nothing is
stored."

#### How it stays fresh

There are three ways, and you can switch each one off in Preferences:

- **Shortly after you open Quill Radio**, a quick check in the background,
  skipped when the catalog is already fresh.
- **On a schedule**, every 24 hours to begin with. You can choose anything from
  6 hours to 2 days, or Manually only. It updates one source at a time, never
  all at once.
- **Whenever you ask**, with **Station > Update Station Catalog**
  (Ctrl+Alt+Shift+G). It always tells you how it went, such as "Station
  catalog updated: 174 new stations, 431 updated."

If a directory is down, all you lose is a little freshness, never your
stations. If a source suddenly answers with nothing, Quill Radio treats it as
an outage, not as every station closing. A station that disappears is hidden
straight away, but only forgotten after two weeks. **Popular** and
**Trending** are always fetched live first. When the directory cannot answer,
the catalog's copy steps in, and every such row says how old it is, such as
"as of 2 hours ago".

#### Station Catalog Status, step by step

1. Press **Ctrl+Alt+Shift+S** (**View > Station Catalog Status...**). Your
   cursor is in the **Sources and what is stored** list (Alt+S).
2. Arrow through it. Each source tells you what is stored and how fresh it is,
   such as "Radio Browser: 62,375 stations, updated 2 hours ago", or why it is
   live only, such as "iHeart: live only; its terms do not allow storing its
   listings".
3. Choose **Update Now** (Alt+U) to bring it up to date now. The window closes
   and the update runs.
4. Or choose **Rebuild From Shipped Snapshot** (Alt+R) to put back the catalog
   that came with Quill Radio. **It does not ask first.** Your favorites and
   your own stations are never touched.
5. Press **Escape** to close.

Your favorites, your own stations, your servers and your YouTube channels are
kept in their own files, and nothing to do with the catalog ever reads or
changes them. If you turn the catalog off in Preferences, browsing goes back
to live only, with nothing stored and nothing fetched in the background. Safe
Mode never updates the catalog, though it may read it.

### Adding your own stations

Found a stream address on a station's website, or been sent one by a friend?
You can add any station yourself, even one no directory knows about.

#### Add Custom Station, step by step

1. Press **Ctrl+N** (**Station > Add Custom Station...**). Add Custom Station
   opens with your cursor in **Station name** (Alt+N).
2. Type the name you want to hear.
3. Tab to **Stream URL** (Alt+U) and paste the stream's address.
4. If you like, Tab to **Homepage** (Alt+H) and **Tags** (separated by commas).
5. Tab to **Test** and press **Space** to hear the stream before you save it.
6. Choose **OK** (Enter) to save. You should hear that the station was added.
   If you already have it, Quill Radio tells you.

If OK does nothing, something is missing or not quite right. The reason is in
the text just above the buttons. It is not spoken by itself, so use your
screen reader's command to read the whole window (Insert+B in NVDA and JAWS)
to hear it.

Three kinds of link get extra help:

- **A YouTube link becomes a station.** Chapter 11, YouTube, says how a
  YouTube link plays, records and is kept.
- **A Live365 link is fixed for you.** A Live365 station page, a player link
  such as `player.live365.com/a25891`, or just a station number is turned into
  the real stream address, and the window tells you so. Nothing is fetched to
  do this.
- **A SecureNet player link** (`securenetsystems.net/v5/...`) is saved as you
  typed it, because its stream has to be read from the page. Either use Find
  Streams from a Website with the link, or just save it and play it, and the
  repair described next finds the stream.

Any other address is saved exactly as you typed it.

#### When a station will not play

Some stations are listed with an address that no longer works, often because
the real stream is hidden behind a player on the station's own website.
Rather than just giving up, Quill Radio tries a few things in turn:

1. It looks the address up again, in case the player moved servers.
2. It fetches a fresh address from the directory.
3. If **Recover failed streams from the station's website** is on in
   Preferences (it starts on), it looks at the station's own website, follows
   a "Listen Live" link, and recognises Triton players there.

If it finds one clear stream, it plays it and remembers it for that favorite.
If it finds several, it tells you how many, and you can choose one in Find
Streams from a Website. It tries once per station each time you run Quill
Radio, and not in Safe Mode.

#### Find Streams from a Website, step by step

1. Press **Ctrl+Alt+S** (**Station > Find Streams from a Website...**). The
   window opens with your cursor in **Website address** (Alt+W).
2. Type or paste the address of the station's page and press **Enter**. The
   **Scan** button does the same.
3. When the scan finishes, the status line tells you how many streams it
   found. Press **Tab** to the **Candidates found** list. Each row gives the
   link and why it was picked out.
4. Arrow to one. Tab to **Test** and press **Space** to hear it. The button
   reads **Stop Test** while it plays.
5. When you find the right one, Tab to **Use This Link...** and press
   **Space**. Add Custom Station opens with the link filled in. Give it a name
   and choose OK.
6. Press **Escape** to close the window.

Enter on the list does nothing; use the buttons.

This works for many stations whose Listen Live button is a web player. For
Triton Digital and StreamTheWorld players, including the whole
`player.listenlive.co` network, Quill Radio reads the station's call letters
and looks up the real stream through the provider's own public service. When
a station has both an MP3 and an AAC stream, you are offered both. It also
recognises **iHeart** and **TuneIn** station pages and **SecureNet** players,
and offers their real stream first. A web page is never offered to you as
something to play.

#### Import Stations from Playlist, step by step

Import reads **M3U**, **M3U8**, **PLS**, **XSPF** and **ASX** playlists. The
"Listen Live" link a station gives you is often a PLS or XSPF file, and
several reading services publish ASX.

1. Press **Ctrl+I** (**Station > Import Stations from Playlist...**). A file
   window opens: "Choose a playlist to import".
2. Find the file and choose **Open**.
3. The Import Stations window tells you how many stations it found and asks
   which folder they go in. Your cursor is in the **Folder** box.
4. Choose a folder from the list, or type a new one such as `News/Local`, and
   it is made for you. "(Top level)" means no folder.
5. Choose **OK**.
6. If some of the stations are already in your favorites, Quill Radio tells
   you how many and asks whether to skip those or import everything.
7. You should hear how many stations were imported, and which folder they went
   into.

Station names come from the playlist itself. A bare address is named after the
website it comes from. An M3U8 file that is really a live stream, not a list
of stations, is recognised and politely refused. XSPF and ASX files are read
safely, and a file built to grow to an enormous size is refused out loud.

### What you learned, and where to go next

You can now wander Browse Stations, look up what a row offers, leave yourself
a note on any station, search one folder or every directory at once, and find
a station from nothing more than its web address. You know how to choose your
sources, add your own servers and stations, and what the catalog on your
computer does for you. Next, Chapter 7, Keeping your favorites, shows you how
to organise everything you have found. The tutorials in the **Finding
something to listen to** track are a friendly way to practise this chapter.

## Chapter 7: Keeping your favorites

Your favorites are the heart of Quill Radio: the short list of stations you
actually listen to. This chapter shows you how to put them in folders and in
your own order, play them without even opening the list, and keep them safe
with a backup or take them to another computer.

The tutorials **Folders, and an order of your own** and **Ten stations, no
list at all**, in the Making it yours track, practise this chapter.

### Putting your favorites in your own order

1. In the favorites tree, arrow to a station.
2. Press **Alt+Shift+Up** or **Alt+Shift+Down** to move it one place within its
   folder. Quill Radio tells you where it landed, naming the station it moved
   past.
3. If the list was sorted A to Z, the first move switches it to your own order
   and says "Switched to manual order". Your own order is never overwritten by
   a sorted view.

For a longer move:

1. Arrow to the station you want to move. Press **Shift+F10** and choose
   **Mark for Move**.
2. Arrow to the station it should sit beside, even in another folder.
3. Press **Shift+F10** and choose **Move Marked Above** or **Move Marked
   Below**. The station moves there and joins that folder.

**View > Sort Favorites** chooses the order for the whole list: **Ascending (A
to Z)** (Ctrl+Alt+Shift+F4, where it starts), **Descending (Z to A)**
(Ctrl+Alt+Shift+F5), or **Unsorted (manual order)** (Ctrl+Alt+Shift+F6). The
menu shows the one you are using as checked.

**View > Expand All Folders** (Ctrl+Alt+E) and **View > Collapse All
Folders** (Ctrl+Alt+Shift+E) open or close every folder at once.

### Playing a favorite without the list

Once you have a handful of favorites, you can start them without arrowing at
all.

- **Alt+1** through **Alt+0** play favorites 1 to 10, in the order the tree
  shows them. You should hear "Playing favorite 1" and the station's name. If
  there is no favorite in that place, you hear how many you have.
- **Alt+Shift+F** opens **Play Favorite Station**, a numbered list of every
  favorite:
  1. Press **Alt+Shift+F**. The list opens with the words "Choose a favorite
     station to play:".
  2. Arrow to a station, or type its number.
  3. Press **Enter** and it plays. Escape closes the list without playing
     anything.
- **Ctrl+L** is **Play Last Station**: whatever you had on last, with no
  looking.
- **Station > Recently Played** lists your last nine stations, newest first.
  Inside that menu, **Alt+Shift+1** plays the newest.

### The Favorites Manager

**Station > Manage Favorites...** (Ctrl+Shift+M) opens **Manage Favorite
Stations**, a full organizer. The main window's tree can do most of the same
things, so think of the Manager as the place for a big tidy-up.

#### Organize your favorites, step by step

1. Press **Ctrl+Shift+M**. Manage Favorite Stations opens with your cursor in
   **Search favorites** (Alt+K).
2. To find something, type part of a name, country, language, tag, one of
   your own tags, or a folder name. A team or league works too: `Tigers`
   finds the favorite that carries the Detroit Tigers. The list below shrinks
   as you type into one flat list. Each station tells you its folder, and why
   it matched when its name does not say. Clear the box to see everything
   again.
3. Press **Tab** to the **Favorites and folders** tree. Arrow to a station or
   folder.
4. Press **Enter** to play a station. Press **Enter** on the playing station to
   stop it.
5. With your cursor in the tree, press **F2** to rename, **Delete** to remove
   (it asks first), or **Ctrl+Shift+E** for a new folder. These three keys only
   work while you are in the tree.
6. Press **Tab** to reach the buttons, in this order: **Play** (reads **Stop**
   while that station plays), **Remove**, **Move Up**, **Move Down**, **Move to
   Folder...**, **Mark for Move**, **Move Above**, **Move Below**, **New
   Folder...**, **Rename...**, **Delete Folder...** and **Remove All...**.
   Press **Space** on one to use it.
7. Press **Escape**, **Ctrl+W** or **Ctrl+F4** to close the Manager.

Some buttons in this window share an Alt letter, so Tab to the buttons rather
than using Alt keys.

#### Folders

- **New Folder...** (Ctrl+Shift+E) asks where the folder goes, at the top level
  or inside another folder, and then its name. It exists straight away, even
  before you put a station in it.
- **Move to Folder...** files the selected station. Choose "(Top level -- no
  folder)", a folder you already have, or "(New folder...)". Type a path with
  a `/`, such as `News/Morning`, to put one folder inside another.
- **Rename** a folder (F2) and its folders inside come along too.
- **Delete Folder...** asks first, with No already chosen. Its stations move
  out to the top level. A station is never deleted along with a folder.

#### Reordering

- **Move Up** and **Move Down** move a station within its folder.
- For a long move, select the station, choose **Mark for Move**, select where
  it should go, then choose **Move Above** or **Move Below**. The station joins
  that folder.
- If the list is sorted A to Z or Z to A, the first move switches to your own
  order and says "Switched to manual order". Your own order is never
  overwritten.
- Quill Radio tells you where the station landed, naming its new neighbour.

#### Listening from a folder

Press **Shift+F10** on a folder for **Play All in Folder**, **Shuffle
Folder**, **Export This Folder...**, **Rename Folder...** and **Delete
Folder...**.

1. Choose **Play All in Folder**. The folder's first station plays, and Quill
   Radio remembers the rest.
2. To move to the next station in the folder, press **Ctrl+Shift+P**, type
   `next station`, and choose **Next Station in Folder**. **Previous Station in
   Folder** goes back. These two are only in the Command Palette.
3. At either end, Quill Radio tells you, rather than going round again.

Shuffle sets one order and sticks to it, so Previous takes you back through the
same stations. A folder always includes everything inside it: playing "News"
plays "News/Local" too, but never a separate folder called "Newsroom".
**Export This Folder...** writes just that folder to an M3U file.

On a station, the menu offers **Play**, **Rename Station...** (F2),
**Remove...** (Delete), **Move Up**, **Move Down**, **Mark for Move**, **Move to
Folder...** and **Note to Self...**, plus **Move Above** and **Move Below**
once a station is marked.

#### Other things to know

- **Rename** gives a station your own name everywhere. Leave it blank to go
  back to the directory's own name.
- **Remove All...** clears every favorite at once, and keeps your folders. It
  asks first, with **No** already chosen. Quill Radio also keeps a rolling
  backup of your favorites, so even that can be recovered.
- **Sort order** for the whole list is in Preferences and on **View > Sort
  Favorites**. Any one folder can have its own order: in the main window's
  tree, press **Shift+F10** on the folder and choose **Sort This Folder...**.
  Choose Ascending, Descending, Unsorted, or follow the order of the whole
  list.
- The Manager's menus are **Favorites** (with **Close**, Ctrl+W), **Station**
  and **Window**.

### Export Favorites to Playlist, step by step

Want your favorites in another media player, or to share them with a friend?

1. Press **Ctrl+Shift+X** (**Station > Export Favorites to Playlist...**). A
   file window opens: "Export favorites to a playlist". The suggested name is
   `quill-radio-favorites.m3u`.
2. Choose a folder and a name, then choose **Save**.
3. You should hear, for example, "Exported 42 stations to
   quill-radio-favorites.m3u."

Export writes an **M3U** file, which almost every media player can open. Each
station is written with the name you see and its stream address, so importing
the file brings the same stations back. M3U has no folders, so your folders
are not carried across. To export one folder, use **Export This Folder...** in
Manage Favorite Stations.

### Backing up and restoring

A backup is a single `.qrbackup` file. It is worth making one now and then,
and always before you reset or replace a computer.

#### What a backup holds

- Your favorite stations, with their folders and saved places.
- Your Quill Radio settings, and the stations you played recently.
- The podcasts you follow, and where you are in each episode.
- Your notes on stations and podcasts, your station tags and your bookmarks.
- Your Go To list, Quick Actions and row-action order.
- Scheduled recordings, the wake-up timer and reminders.
- Your recording settings, including which folder recordings go to.
- Saved YouTube rows, the YouTube channels you follow, your own streaming
  servers, your Local Media list, quiet hours and download choices.
- Your recordings, only if you answer **Yes** when it asks.

It does not hold passwords or sign-ins (private podcast feeds, server
passwords, your YouTube sign-in), downloaded podcast episodes, or the music and
audiobook files your Local Media list points to. You type the passwords again on
the new computer.

Your favorites, settings and podcasts are never quietly left out. If one of
them cannot be read, the backup is not saved, and Quill Radio tells you which
one and why.

#### Back up, step by step

1. Press **Ctrl+Shift+U** (**Station > Back Up Stations and Settings...**).
2. If you have recordings, Quill Radio asks whether to include them, and says
   how many there are, how much space they take and which folder they are in.
   If some are stored only in OneDrive, it says how many; Quill Radio asks
   Windows to download them as it backs up, so stay connected to the internet.
   Choose **Yes** or **No**.
3. A file window opens: "Save Quill Radio Backup". Choose a folder and a name,
   then **Save**.
4. The status bar counts through the recordings as they are copied. When it
   finishes you hear where the backup was saved and what it holds.
5. If anything was left out, a message says how many and asks **Show what was
   left out, and why?** Choose **Yes** for a list with one line per file and
   the reason: stored only in OneDrive and not downloaded, in use by another
   program, a folder path too long for Windows, or could not be read. What to
   do is under the list, and **Copy List** copies it. The same list goes into
   **Help > Recent Problems...** (Ctrl+Alt+Shift+P), so you can find it later.

Backup files are never copied into a backup as recordings, so it is fine to
keep your backups in the same folder as your recordings.

#### Restore, step by step

1. Press **Ctrl+Alt+Shift+W** (**Station > Restore from Backup...**).
2. A file window opens: "Restore Quill Radio Backup". Choose the `.qrbackup`
   file and choose **Open**.
3. A question tells you what the backup holds and when it was made, and warns
   you: "This replaces your current stations and settings." **No** is already
   chosen, so pressing Enter does nothing. To restore, press **Y**, or Tab to
   **Yes** and press Enter.
4. Quill Radio restores the files and reloads, so you have them straight away.
   Recordings go into the folder named in **Record > Recording Settings...**
   (Ctrl+Alt+Shift+I). A recording that is already there is left alone, so
   restoring onto a computer that still has your OneDrive folder does not copy
   everything twice.

### Moving to a new or reset computer

Your favorites, settings and podcasts live on this computer, in your Windows
user folder, not in OneDrive. A reset removes them. Your recordings live
wherever **Record > Recording Settings...** (Ctrl+Alt+Shift+I) says under
**Destination folder**; if that is a OneDrive folder, OneDrive keeps them.

Before the reset:

1. Make a backup: **Station > Back Up Stations and Settings...**
   (Ctrl+Shift+U). Save it into your OneDrive folder.
2. If your recordings are already in OneDrive, you can answer **No** to
   including them; they are safe there. If they are on this computer only,
   answer **Yes**, or copy the recordings folder to OneDrive or a USB drive
   yourself.
3. Check the backup is fully uploaded: in File Explorer, the backup file's
   **Status** column should say it is available or synced, not that it is
   still uploading. Opening onedrive.com in a browser and finding the file
   there is the surest check.
4. If you were told anything was left out, read the list and do what it
   says before you reset.

After the reset:

1. Install Quill Radio and sign in to OneDrive. Wait for your OneDrive folder
   to appear.
2. If your recordings are in OneDrive, right-click that folder in File
   Explorer and choose **Always keep on this device**, so they are on the
   computer and not only in the cloud.
3. In Quill Radio, press **Ctrl+Alt+Shift+W** (**Station > Restore from
   Backup...**), choose your backup file and answer **Yes**.
4. Press **Ctrl+Alt+Shift+I** (**Record > Recording Settings...**) and check
   **Destination folder** (Alt+D) is your OneDrive recordings folder. The
   backup brings this setting back, but the path can change if your Windows
   user name changed; use **Browse...** to choose the folder again if needed.
5. Retype any podcast or server passwords.

### Moving your setup to another machine

Getting a new computer? You can take everything you have built with you in
one file.

**Help > Export My Setup...** (Ctrl+Alt+Shift+X) writes one `.quillsetup`
file with your podcast subscriptions, folders and playlists, favorite stations
and saved places, settings, your Go To order, your Quick Actions order,
scheduled recordings, bookmarks and any keys you changed. **Help > Import My
Setup...** (Ctrl+Alt+Shift+N) puts them on the new computer.

1. On the old computer, press **Ctrl+Alt+Shift+X**. A question tells you what
   will be saved and that passwords are not included. Choose to carry on.
2. Choose a folder and a name, and save. Copy the file to the new computer.
3. On the new computer, press **Ctrl+Alt+Shift+N** and choose the file.
4. A question tells you what the file holds, and says plainly that importing
   **replaces** what is on this computer. Choose to carry on.
5. Close Quill Radio and open it again, so everything is read in fresh.

Both Export and Import count what they did. Export My Setup is shared with
QUILL Cast, so on a computer without Cast some items, such as Cast's podcast
settings, were never made and have nothing to carry; that is what "skipped"
means there, and nothing is lost. When anything is left out, a message offers
**Show what was left out, and why?**, which names every item and its reason.

The file is an ordinary ZIP with a list inside saying what it holds.
**Passwords are not in it.** Sign-ins for private podcast feeds, server
passwords and unlock codes stay on the old computer, and you type them again
on the new one.

### Sharing data with QUILL

An installed Quill Radio keeps its things in the same place as QUILL and QUILL
Cast (`%APPDATA%\Quill`): your favorites (with their folders, your names for
them and each station's volume), history, recordings, schedules, timers and
settings. A station you favorite here is a favorite in QUILL's radio too.
Uninstalling Quill Radio never deletes any of it.

What that means for you:

- **You set things up once.** Favorites you made in QUILL's radio are already
  in Quill Radio the first time it opens, and the welcome is skipped.
- **Podcasts are shared with QUILL Cast.** A show you follow in Browse Stations
  is in Cast's library, and both apps know how far you got in an episode.
- **Bookmarks and quiet hours are shared.** Set them in either app.
- **Keys are shared.** A key you change in the Keyboard Manager changes in
  QUILL and QUILL Cast too, where they have the same command.

A portable copy keeps its own things in its `data` folder and shares nothing
with the computer it runs on.

If you would like your data kept somewhere else, such as a folder that
OneDrive or Dropbox keeps in step across your computers, use **Data Folder...**
in Preferences. See "Preferences" in Chapter 14.

### What you learned, and where to go next

Your favorites are now just the way you like them: in folders, in your own
order, and a single key away with Alt+1 to Alt+0. You can export them, back
them up, restore them, and take your whole setup to another computer. Next,
Chapter 8, Recording, shows you how to keep a copy of a show, now or later.
The tutorial **Back it up, move it, and keep it working**, in the Living with
it track, goes with the second half of this chapter.

## Chapter 8: Recording

Recording means you never have to miss a show. You can record what is on now,
record a different station while you listen to something else, book a
recording for tonight or every week, and record several stations at once.
Everything you need for recording comes with Quill Radio.

The **Recording** track of the tutorials covers this chapter: **Record what is
on now**, **Book a show that has not started yet**, **Record several stations
at once**, **Live in the Recordings list** and **When a recording breaks**.

### Record what is on now

1. While a station plays, press **Ctrl+R** (**Record > Record Now / Stop
   Recording**).
2. You should hear "Recording started" and the station's name, over the
   start-recording sound.
3. The Record cell in the status bar now reads **Stop Recording**, with the
   time so far.
4. Press **Ctrl+R** again to stop. You should hear "Stopping recording", then
   that it was saved, with the file's name.

Ctrl+R follows what you are listening to. If the station you are hearing is
being recorded, Ctrl+R stops that recording. If not, it starts one. A
recording of a different station, running in the background, is never stopped
by Ctrl+R.

### Record a different station, step by step

Record Station records any favorite for as long as you choose, while you
listen to something else, or to nothing at all.

1. Press **Ctrl+Alt+R** (**Record > Record Station...**). The Record Station
   window opens.
2. Choose the station in **Station** (Alt+T). Your favorites are listed, and so
   is the station playing now if it is not a favorite.
3. Set **Duration (minutes)** (Alt+D), from 1 to 1,440. It starts at 60.
4. Choose **Start Recording** (Enter). You should hear "Recording started:",
   the station and the minutes.

You can start as many as you like, and they all record at once.

### Recording several stations at once

You can record two shows that overlap, or record one station while you listen
to another. Each recording looks after itself, with its own connection, and
recovers on its own if something goes wrong. Scheduled recordings that overlap
all start as planned.

To record two stations at once:

1. Play the first station and press **Ctrl+R**. You should hear "Recording
   started" and its name.
2. Press **Ctrl+Alt+R** for Record Station. Choose the second station, set the
   minutes, and choose **Start Recording**.
3. Press **Ctrl+Shift+R** to open Radio Recordings. Both rows read
   **Recording**, and the line under the list tells you how many are running.
4. To stop one, select its row, Tab to **Stop Recording** and press Space. To
   stop them all, press **Ctrl+Alt+X**.

Good to know:

- If a stream goes quiet without actually disconnecting, Quill Radio notices
  within about half a minute. It reconnects and carries on, or stops and saves
  what it has.
- As a second check, a recording whose file has not grown for about a minute
  is treated as dropped.
- To limit how many record at once, set **Maximum simultaneous recordings** in
  Recording Settings. 0 means no limit, which is where it starts. A scheduled
  recording over the limit waits and tries again while its time is still
  open.
- Ways to stop: **Ctrl+R** stops the one for the station you are hearing.
  **Stop Recording** in Radio Recordings stops the one selected there. **Stop
  All Recordings** (Ctrl+Alt+X) stops every one, and you hear "Stopping all"
  and how many.

Recording file names use your computer's time zone, even if it changes while
Quill Radio is running.

### Schedule a recording, step by step

The one thing to remember: **fill in the details first, then choose Add
Schedule last.**

1. Press **Ctrl+Shift+S** (**Record > Schedule Recording...**). The Schedule
   Recording window opens. If something is playing, that station is already
   filled in.
2. If you have favorites, the **Favorite station** list (Alt+F) is there. Its
   first row is "(type the details below)". Choose a favorite, and its name and
   stream are filled in for you.
3. Or type them yourself in **Station name** (Alt+M) and **Stream URL**
   (Alt+U).
4. Tab to **Repeats** and choose **Once**, **Daily** or **Weekly**.
5. For Weekly, Tab to **On day (weekly only)** and choose the day. For Once,
   type the date in **Date (once only)** (Alt+C), written as `YYYY-MM-DD`.
6. Type the start time in **Time (7:30 PM or 19:30)** (Alt+T).
7. If the show's time is given in another time zone, choose that zone in
   **Time zone** (Alt+Z). Otherwise leave it on "(local time)".
8. Set the length in **Duration -- hours** (Alt+H, 0 to 24) and **and
   minutes** (Alt+I, 0 to 59). A three-hour show is 3 and 0.
9. Choose **Add Schedule** (Alt+A). You should hear "Scheduled recording added
   for" and the station. Your cursor moves to your new entry in the list, and
   the form clears, ready for the next one.

If something is missing, the status line tells you what, and nothing is added.

#### Your scheduled recordings

The list at the top, **Scheduled recordings** (Alt+G), is in the order they
will next record. Each row shows the station's server in brackets, so two
similar entries are easy to tell apart. With an entry selected:

- **Edit** puts it back in the form. The Add button becomes **Save Changes**.
  Choose **New** (Alt+N) to stop editing and start a fresh entry.
- **Duplicate** starts a new entry copied from this one, with " (copy)" added
  to its name. It keeps the original's stream until you change it.
- **Disable** switches an entry off without losing it. It reads "(disabled)"
  and does not record. **Enable** switches it back on.
- **Remove**, or the **Delete** key, deletes the entry **straight away, without
  asking**.
- **Shift+F10** on the list offers Edit, Duplicate, Enable or Disable, and
  Delete.

Close the window with **Escape** or **Ctrl+W**. Its menus are **Schedule**
(Alt+D), **Station** (Alt+S) and **Window** (Alt+W).

#### Making sure it happens

Quill Radio must be running for a scheduled recording to start. Running in the
tray counts. A recording is due from its start time until the end of its
length, so if Quill Radio starts a few minutes late, it records the rest. A
show whose whole time passed while Quill Radio was closed is missed, and the
next time you open it, Quill Radio tells you, naming up to three.

To make sure the computer is awake, look at **Keep the computer awake before a
scheduled recording** and **Wake the computer for a scheduled recording** in
Preferences.

You can also schedule from Browse Stations: **Schedule Recording...** on a live
station's menu opens this window with that station filled in. The ACB Media
schedule can book a programme for you too. See Chapter 12.

### Recording Settings, step by step

1. Press **Ctrl+Alt+Shift+I** (**Record > Recording Settings...**).
2. Change whichever of these you want:
   - **Format** (Alt+F): MP3 (where it starts), OGG Vorbis, FLAC, WAV, or **Raw
     stream -- exactly as sent, no re-encoding (lossless)**.
   - **Quality (bitrate)** (Alt+Q): 96 to 320 kbps, starting at 192. It is
     hidden for the lossless formats.
   - **Destination folder** (Alt+D): where recordings go. Blank means
     `Music\Quill Radio Recordings` in your user folder, or the `Recordings`
     folder of a portable copy. **Browse...** lets you choose.
   - **Temporary folder (while recording)** (Alt+T): optional. A recording is
     written here and moved to the destination when it finishes, so a
     half-finished file never appears among your recordings. Blank records
     straight into the destination.
   - **Filename pattern** (Alt+P): it starts as `{station} - {date} {time}`.
   - **Maximum recording length (minutes)** (Alt+M): a safety limit, 180 to
     begin with.
   - **Maximum simultaneous recordings** (Alt+S): 0, meaning no limit, to begin
     with.
   - Under **If the connection drops**: **Reconnect and keep recording
     automatically** (Alt+K, on), **Reconnect attempts** (Alt+A, 5) and
     **Seconds between attempts** (Alt+C, 10).
   - **Apply Sound Enhancements to recordings** (Alt+E): off, so recordings
     are kept exactly as the station sent them. Turn it on to record the sound
     with your enhancements, for every kind of recording.
3. Choose **OK**. You should hear "Recording settings saved".

**Raw stream** saves exactly what the station sends, without changing it, so
nothing at all is lost. The file type matches the stream: `.mp3`, `.aac`,
`.ogg`, `.opus` or `.flac`, and anything unusual goes in a Matroska `.mka`
file. Bitrate and Sound Enhancements do not apply to a raw recording.

### Radio Recordings, step by step

Radio Recordings shows every recording in one list: the ones being recorded
now, the finished ones, and the scheduled ones.

1. Press **Ctrl+Shift+R** (**Record > Recordings...**). Radio Recordings opens
   with your cursor in the list, newest first.
2. Arrow through the list. Each row gives the name and a status,
   **Recording**, **Recorded** or **Scheduled**, then the size and date. A
   recording being made grows as you watch.
3. Press **Enter** on a finished recording to play it. Press **Enter** again to
   stop. While it plays, Ctrl+Up and Ctrl+Down change its volume.
4. Tab to the buttons: **Play** (reads **Stop** while the selected recording
   plays), **Stop Recording** (on a row being recorded), **Stop All
   Recordings** (when two or more are running), **Open in Folder** (shows the
   file in File Explorer), **Remove...** and **Refresh**.
5. Press **Delete** to remove a finished recording. **No** is already chosen;
   press **Y** to delete. Your cursor lands on the next recording. If you
   change your mind, Ctrl+Z in the main window brings it back.
6. Press **Escape** to close. Recordings keep going.

The line under the list starts with what is happening, such as "Recording, 42
min left. Next: KFI at 11:00 tomorrow. 14 recorded. In D:\Music\Quill Radio
Recordings." If you have schedules but none of them will happen, it says "3
scheduled, none coming up".

The list keeps itself up to date every couple of seconds, without losing your
place. It has no Shift+F10 menu. Its menus are **Recordings** (Alt+R, with
**Close**, Ctrl+W), **Station** and **Window**. To choose what each row says,
see "What each row says" in Chapter 14.

#### Winamp keys in Radio Recordings

If Winamp's classic keys are second nature to you, they work in the Radio
Recordings list, with no Ctrl or Alt needed:

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
| T | Say the time so far, or the time left; press again to swap |
| J | Jump to a recording: type part of its name |
| Ctrl+J | Jump to a time: type `90`, `1:30` or `1:02:03` |
| L | Play the selected recording |
| Ctrl+Up / Ctrl+Down | Volume up or down |

Every key tells you what it did. Two things differ from Winamp: **Ctrl+T** is
still What's Playing, so the time is plain **T**; and **Up** and **Down** move
through the list rather than changing the volume.

- Shuffle sets one order, so every recording plays once before any repeats,
  and Z takes you back to the one you just heard.
- Repeat-one applies when a recording finishes on its own. B still moves on.
- Ctrl+V switches itself off once it has done its job, and is not remembered
  next time. Shuffle and repeat are remembered.
- When a recording ends on its own, the next one in the queue plays.
- Jumping around inside a recording needs the mpv engine.

If you would rather type letters to jump through the list, turn the letter
keys off with **Winamp-style playback keys in the Recordings player** in
Preferences. Ctrl+Up and Ctrl+Down work either way.

### If the internet hiccups during a recording

Short gaps are smoothed over by themselves, using the reconnect settings in
Recording Settings. If the connection really does drop, Quill Radio waits and
carries on in a numbered part file, telling you about each try. When the
recording finishes, **it joins the parts back into one file**, and tells you:
"Joined 3 parts into one recording", or "Kept 3 separate parts" and the reason.

- Joining is a straight copy, so nothing is lost and it takes seconds. The
  joined file is checked before the parts are removed. If anything goes wrong,
  every part is left just as it was.
- A continued recording only records the time left until the original end. A
  60-minute show that drops at minute 50 records about 10 more minutes.
- It only gives up for good on something that cannot be fixed by trying
  again: a full disk, or the station's server saying the stream is gone. Any
  other problem means it reconnects.
- File names are never overwritten. A name used twice gets " (2)", " (3)" and
  so on.
- If Quill Radio is closed or crashes, the recording stops with it.

### If a recording was in progress when Quill Radio quit

A crash, a power cut or a forced restart can stop Quill Radio in the middle of
a recording. The part already recorded is kept, and Quill Radio offers to
record the rest.

The next time it starts, Quill Radio tidies its temporary folder, moving any
finished file to your recordings folder. Then, if a recording was in progress
and its planned end was no more than ten minutes ago, a window titled
**Resume Recording** asks, for example:

> A recording of WQXR was in progress until 2026-09-26 09:00:00. Resume it for the remaining 12 minute(s)?

1. If the whole question was not read, use your screen reader's command to
   read the window.
2. If you want Quill Radio to remember your answer from now on, press **Alt+D**
   to check **Don't ask me again** first.
3. Choose **Resume** (Enter) to record the minutes that are left, or **Skip**
   (Escape) to leave it. Resume records from the same station.

If several recordings were interrupted, one window, **Resume Recordings**,
covers them all. It lists them, asks "Resume all of them for their remaining time?", and offers **Resume
All** and **Skip All**.

To change your mind later:

1. Press **Ctrl+,** to open Preferences.
2. Tab to **Interrupted recordings at launch**.
3. Choose **Ask each time** (where it starts), **Always resume them** or
   **Never resume them**.
4. Choose **OK**.

### What you learned, and where to go next

You can now record what is on, record another station in the background,
record several at once, and book a show for later, once, daily or weekly. You
know where your recordings live, how to play them with ordinary or Winamp
keys, and what Quill Radio does when the internet or the computer lets you
down. Next, Chapter 9, Podcasts, books, video and more, goes beyond radio. If
you would like a hand booking your first show, the tutorial **Book a show that
has not started yet** walks you through it.

## Chapter 9: Podcasts, books, video and more

Quill Radio is not only radio. This chapter shows you how to follow podcasts,
hand an episode over to QUILL Cast, save audiobooks and episodes to keep,
watch television, find your local weather radio, and try Spotify. Your own
music and audiobooks have a chapter of their own, Chapter 10.

Most of the **More than radio** track of the tutorials belongs to this
chapter: **Follow a podcast**, **Audiobooks, archives and free music**,
**Watch television**, **NOAA Weather
Radio**, **Save a copy, and find it on disk** and **Spotify, honestly**.

### Podcasts in Browse Stations

1. Press **Ctrl+B**, arrow to **Podcasts (Apple)** and press **Right Arrow**.
   The first folder is **Subscriptions**, then the storefronts.
2. Open a storefront, then **Top Podcasts**, or a genre.
3. Arrow to a show and press **Right Arrow** to open it. Its episodes load from
   the publisher's own feed.
4. Press **Enter** on an episode to play it.
5. To follow the show, go back to the show's row, press **Shift+F10** and
   choose **Subscribe to This Podcast**. It goes into the podcast library you
   share with QUILL Cast, so it is there the next time you open Cast.
6. The shows you follow appear under **Subscriptions**, one folder each, with
   their newest episodes. The Subscriptions folder shows how many you follow,
   such as "Subscriptions (3)", and each show tells you how many episodes you
   have not heard, such as "(2 unheard)".

Worth knowing:

- An episode whose feed publishes a transcript says "transcript available".
  **View Transcript...** on its menu opens it without playing anything.
- How many episodes each show lists is set in Preferences, under **Episodes
  listed per subscribed podcast**. It starts at the 25 newest.
- A show you follow has some tidying-up on its menu: **Move to Folder...**,
  **Mark All as Played...** (with a "Don't ask me again" box shared with QUILL
  Cast), **Download All Episodes...** and **Remove All Downloads...** (the
  files go, but you still follow the show).
- **Folders of shows** work here too, the same folders QUILL Cast uses. On a
  folder under Subscriptions, **Shift+F10** offers **New Folder Inside...**,
  **Rename Folder...**, **Delete Folder...** and **Check All Feeds Now**.
  Deleting a folder asks first, and its shows and folders move up a level:
  nothing is unsubscribed. **Check All Feeds Now** looks for new episodes in
  every show you follow, straight away, even ones you have paused.
- When you finish an episode here, the show's unheard count goes down at once.
- While Subscriptions is empty, it offers **Add a Podcast by URL...**,
  **Import Podcasts from OPML...** and **Search for a Podcast...**.
- **Export Podcasts to OPML...** (since 3.0.4) is on the menu of the
  **Subscriptions** folder and of the **Podcasts (Apple)** branch, next to
  Import. It writes every show you follow, folders included, to an OPML file,
  the kind of file every podcast app can read, and tells you how many it
  wrote, for example "Exported 12 podcasts to quill-radio-podcasts.opml." It is
  the same file QUILL Cast's Subscriptions > Export OPML writes, so nothing is
  lost between the two.
- The fuller side of podcasts, such as automatic downloads, how long to keep
  episodes and the play queue, is QUILL Cast's job.

### Apple's categories and the Podcast Index

Each storefront under **Podcasts (Apple)** has Apple's categories, such as
History, Comedy or News, and most have subcategories, such as Comedy Fiction.
Open one and you get Apple's own top shows for that category, up to 200. Since
3.2.0 these are full lists. Before, a category only held the few shows that
made the storefront's overall chart, and some held none at all.

You do not have to wait while you look around. When you arrow through a long
list, such as Top Podcasts, Quill Radio does not load every show you pass. It
waits until you stop on one, so the list stays quick with your screen reader,
and a big folder fills in all at once.

The **Podcast Index** branch is another way to find shows, with **Trending
Now**, **By Category** and **Search the Podcast Index...**. It needs a free
key. Quill Radio usually comes with one. If your copy has none, the branch
shows a single row:

1. Press **Ctrl+B**, arrow to **Podcast Index** and press **Right Arrow**.
2. Arrow to **Add a Podcast Index Key...** and press **Enter**. The **Podcast
   Index Credentials** window opens.
3. If you do not have a key yet, get one free at api.podcastindex.org/signup.
4. Type or paste the key into **Key** and the secret into **Secret**, then
   press **Save**.

A key you enter in Quill Radio works in QUILL Cast too, and the other way
round.

If a Podcast Index folder cannot load, Quill Radio tells you why, instead of
saying "Nothing in here". If the Podcast Index turns your key down, you hear
that the key was not accepted, so you know to check it rather than your
internet connection.

### Checking your subscribed podcasts

Quill Radio can ask every show you follow whether it has new episodes.

**To check everything now:**

1. In Browse Stations, open **Podcasts (Apple)** and highlight
   **Subscriptions**, or any folder in it.
2. Press **Shift+F10** and choose **Check All Feeds Now**. You should hear
   "Checking subscribed feeds...", then one summary at the end.

This checks paused shows too. **Refresh** on a single show checks just that
one, whatever your settings say.

**Or let Quill Radio check by itself.** In Preferences, under **Podcasts**:

1. Press **Ctrl+,** and Tab to **Check subscribed podcast feeds**.
2. Choose how often: Manually only (where it starts), or anything from every
   15 minutes to once a day.
3. If you like, check **Check subscribed podcast feeds at launch** too.
4. Choose **OK**. Quill Radio tells you what it will now do.

Both start off, so Quill Radio never uses your internet allowance on a
schedule you did not choose. Quill Radio and QUILL Cast share the how-often
setting, so choosing it in one sets it in both. When Quill Radio checks by
itself:

- It only reads the lists of episodes. Nothing is downloaded or queued, and
  nothing you are playing changes.
- A show you have paused is skipped.
- It speaks once at the end, with how many it found and their names. If it
  finds nothing, it says nothing.
- During quiet hours it still checks, and saves the summary for later.
- A check that fails goes into Recent Problems.
- New episodes it finds can also be noted in the Notifications list, so you
  can look them up later. See "Notifications" in Chapter 12.

If you also use QUILL Cast, the two apps share a note of when each show was
last checked, so they do not both ask the same podcast.

### Handing an episode to QUILL Cast

Quill Radio finds and plays podcast episodes. QUILL Cast, its sister app, is a
full podcast player, with a play queue and an inbox. When you find an episode
in Quill Radio that you want to hear later in Cast, you can hand it over in
one step.

On an episode of a show you follow, in Browse Stations, the menu offers three
ways to hand it over:

- **Play Next in QUILL Cast** puts it at the top of Cast's queue. You hear "It
  will be next in the QUILL Cast queue."
- **Add to QUILL Cast Queue** puts it at the end. You hear "Added to the end of
  the QUILL Cast queue."
- **Send to the QUILL Cast Inbox** keeps it for you to decide about later. You
  hear "Sent to the QUILL Cast Inbox."

The same menu also has **Mark Episode as Played** or **as Unplayed**, and Cast
picks that up too.

1. Press **Ctrl+B** for Browse Stations. Open **Podcasts (Apple)**, then
   **Subscriptions**, then a show.
2. Arrow to an episode and press **Shift+F10**.
3. Arrow to one of the three and press **Enter**. You hear what will happen.
4. The next time you open QUILL Cast, the episode is where you asked.

Good to know: these are messages to Cast, not things done there and then.
Cast carries them out the next time it opens, which is why you hear "will
be". Asking twice for the same episode counts once. A message Cast has not
picked up within a month is dropped. These three only appear on episodes of
shows you follow, because Cast needs to know the show.

### Saving episodes, books and tracks

Where a source allows it, you can keep your own copy.

1. In Browse Stations, highlight a book chapter, an archive recording, a
   Creative Commons track or a podcast episode.
2. Press **Shift+F10** and choose **Download...**. It joins the list of
   downloads, and you can carry on listening.
3. On a book's folder, choose **Download All Files...** to save every chapter
   into one folder, in order.
4. Press **Ctrl+Shift+J** to open **Downloads** and see how it is going.

Where saving is not offered, asking tells you why, and the reasons differ. A
**live station** has no file to save, so use Record Station instead.
**Spotify** is copy-protected. **YouTube** is left out on purpose. For
**Audius**, it is up to the artist. A Creative Commons track is saved with its
licence in a small text file beside it.

A downloaded book plays like a book. Chapters play in order (chapter 2 before
chapter 10), each one starts on its own, and Quill Radio tells you where you
are, such as "4 of 40". At the end of the last chapter, it tells you so.

#### The Downloads window, step by step

1. Press **Ctrl+Shift+J** (**View > Downloads...**). Downloads opens with your
   cursor in the list. A heading above it sums up what is happening.
2. Arrow through the list. Each row says what it is and how far it has got:
   waiting, downloading, saved or failed.
3. Press **Enter** on a saved row to open its folder in File Explorer. The
   **Open Containing Folder** button does the same.
4. Tab to the buttons: **Cancel This One**, **Remove From List**, **Clear
   Finished**, **Clear All**, and **Preferences...** (which opens Download
   Preferences). None of them deletes a file already saved on your computer.
5. Press **Escape** to close Downloads. Your downloads keep going.

If you send Quill Radio to the tray with downloads still going, it either
finishes them in the background or stops them, as Download Preferences says,
and tells you which.

Downloads are filed neatly. A podcast goes in a folder named after its show. A
book gets its own folder. Once you have more than one book by the same author,
that author gets a folder too. You can change all of this in Download
Preferences.

#### Download Preferences, step by step

1. Press **Ctrl+Alt+Shift+D** (**Station > Download Preferences...**). Your
   cursor is in **Downloads folder (blank uses the default)**.
2. Leave it blank for the usual place, type a folder, or Tab to **Browse...**
   to choose one. The usual place is a Quill Radio folder inside your Downloads
   folder. In a portable copy, it is the `Downloads` folder inside the portable
   folder.
3. Tab through the checkboxes and press **Space** to change any of them:
   - **A folder per podcast show**: on.
   - **A folder per book**: on.
   - **Group books by author once an author has more than one**: on.
   - **Keep downloads going when the window closes to the tray**: on.
   - **Ask where to save each download instead of filing it automatically**:
     off. When it is on, a book asks once, not once for every chapter.
4. A sentence under the checkboxes always tells you what will happen to the
   next thing you save.
5. Choose **OK** to save. Quill Radio reads your new choices back to you.

### Your own music and audiobooks: Local Media

Local Media has a chapter of its own now: Chapter 10, Local Media, your own
music and audiobooks.

### YouTube

YouTube has a chapter of its own now: Chapter 11, YouTube.

### Television

Quill Radio plays television the same way it plays everything else. Pick a
channel, press Enter, and it plays, with the same captions, choice of audio
track and playing keys as any stream.

**Television (iptv.org)** uses the iptv.org community list of TV streams that
are freely available: roughly 9,300 channels that play. Channels marked as
adult, channels that have closed, channels with no stream, and streams that
would not work are left out.

#### Watch a channel, step by step

1. Press **Ctrl+B**, arrow to **Television (iptv.org)** and press **Right
   Arrow**.
2. Choose **By Country** or **By Category** and press **Right Arrow**.
3. In By Country, a country with local channels, such as the United States,
   opens into **Nationwide** and its states. A state lists its own channels and
   its cities' channels, each with its city.
4. Arrow to a channel and press **Enter**. It plays as sound.
5. Press **Ctrl+Shift+V** to show the picture. See "Show the video, step by
   step" in Chapter 5.

Worth knowing:

- **Search understands places.** Anywhere you can search, TV answers by
  channel name, network, country, city, state or five-digit ZIP code. Type
  66044 and you get Kansas television.
- **"Which channels can my antenna receive? (antennaweb.org)"** opens
  antennaweb.org in your browser.
- **The channel list updates itself every week.** **"Update the channel list
  now"**, at the top of the branch, fetches today's copy.

#### Your own TV guide

If you put a TV guide file in the XMLTV format, named `tv_guide.xml`, into your
Quill Radio data folder, every channel the guide covers gets an extra line in
its details: "Now: ... Next: ...". The file is only read from your computer,
never fetched from anywhere. Replace it and it is read again. Delete it and
the lines go away.

1. Get an XMLTV file for your area from a guide service you trust. Quill Radio
   does not supply one.
2. Rename it `tv_guide.xml`.
3. Copy it into your Quill Radio data folder. For an installed copy, that is
   `%APPDATA%\Quill`; type that into File Explorer's address bar to go there.
   For a portable copy, it is the `data` folder beside `QuillRadio.exe`.
4. In Browse Stations, arrow to a channel the guide covers. The details box,
   after the tree, now has a "Now: ... Next: ..." line.

### Weather radio

Weather has an app of its own, **Quill Weather**, with its own guide. Open it
from the **QuillVille** menu (Ctrl+Alt+Shift+F8). Quill Radio has no Weather
menu.

What stays in Quill Radio is the radio side of weather: the **Weather / NOAA**
branch of Browse Stations, with every NOAA Weather Radio transmitter that can
be heard on the internet.

#### Find your local NOAA Weather Radio, step by step

1. Press **Ctrl+B** and arrow to **Weather / NOAA**. Press **Right Arrow**.
2. Arrow to your state and press **Right Arrow**. Each transmitter reads with
   its call sign, frequency and place.
3. Press **Enter** on one to play it.
4. Or press **Ctrl+F** and type a call sign, a SAME code, or "County, ST", such
   as `Fairfax, VA`, and press Enter.

### Spotify (experimental)

Quill Radio can search Spotify, browse your library and playlists, and play
through Spotify's own player. This is **experimental, and off to begin with**.
When the Spotify feature is on, **Connect to Spotify...** (Ctrl+Alt+P) and
**Browse Spotify...** (Ctrl+Alt+O) appear on the **Station** menu. Quill Radio
has no switch of its own for it: it follows the Spotify feature in the feature
settings it shares with QUILL. Nothing reaches Spotify until you connect an
account, and it is off in Safe Mode.

#### Does a free Spotify account work?

**Yes for finding things, no for playing them inside Quill Radio.**

- With a free account you can search Spotify and browse your saved shows,
  episodes, tracks and playlists.
- You cannot start the sound inside Quill Radio. Spotify does not allow other
  apps to play free-account audio; playing through another app needs Spotify
  Premium.

With a free account, let Quill Radio do the finding, and play what you find
in the Spotify app. Quill Radio tells you which kind of account you signed in
with straight away.

Nothing from Spotify can ever be recorded or downloaded, on any account,
because the sound is copy-protected.

#### What you need

- A Spotify account. Free can search and browse; only Premium plays.
- Your own Spotify **Client ID**. Quill Radio does not come with one of its
  own, so nothing of yours passes through anyone else's. There is no client
  secret to copy.
- Windows with the Microsoft Edge WebView2 runtime, which up-to-date Windows
  already has.

#### Get your Client ID, step by step

1. Go to the Spotify Developer Dashboard at
   `https://developer.spotify.com/dashboard` and sign in with your ordinary
   Spotify account. It is free.
2. Choose **Create app**.
3. Give it any **App name** and **App description**, such as "Quill Radio".
4. In **Redirect URI**, type exactly `http://127.0.0.1:43217/callback` and
   choose **Add**. It must match exactly, letter for letter.
5. Under **Which API/SDKs are you planning to use?**, check **Web API** and
   **Web Playback SDK**.
6. Accept the terms and choose **Save**.
7. Open your app's **Settings** and copy the **Client ID**. You do not need the
   Client secret, so do not paste it anywhere.

#### Connect, step by step

1. Press **Ctrl+Alt+P** (**Station > Connect to Spotify...**). A sign-in window
   opens.
2. Paste your Client ID into **Client ID** and choose **Connect**.
3. The first time, Quill Radio asks once whether it may go online.
4. Your web browser opens Spotify's own page asking you to approve. Approve
   it.
5. Spotify sends you back to an address on your own computer (`127.0.0.1`)
   that Quill Radio listens on for just that moment. Quill Radio tells you that
   you are connected, and which kind of account it is.

Your sign-in is kept in the Windows credential store, never in an ordinary
file or a log.

#### Browse and play, step by step

1. Press **Ctrl+Alt+O** (**Station > Browse Spotify...**). A search box opens
   with a list of results.
2. Type what you are looking for and press Enter.
3. Arrow to a result and press **Enter** to play it.

Spotify plays through a hidden Spotify player alongside Quill Radio's own.
Play and Stop, volume, the status bar, the tray and any global hotkeys all
work with it.

### What you learned, and where to go next

You can now follow podcasts and check them for new episodes, hand episodes to
QUILL Cast, save books and episodes to keep, watch television, find your local weather radio, and know just what
Spotify can and cannot do here. Next,
Chapter 10, Local Media, brings in the music and audiobooks on your own
computer. The tutorial
**Follow a podcast** is a good place to practise.

## Chapter 10: Local Media, your own music and audiobooks

Quill Radio plays more than the internet. Local Media is where your own files
live: the music on your computer, the audiobooks you bought, a folder of old
radio shows, even videos. You put them in playlists, in whatever order you
like, and Quill Radio plays them one after another, with the same keys you
already use for the radio.

This chapter starts with an empty window and ends with playlists you have
built, arranged and left playing while you get on with something else.

The tutorial **Play your own files in playlists**, in the **More than radio**
track, walks you through the same ground in about eight minutes.

### What Local Media is, and why you would use it

A playlist in Local Media is simply a list of files in an order you chose.
Nothing is ever copied or moved. A playlist only remembers where each file is
and what its tags say, such as the title, artist, album and length. Taking
something out of a playlist never deletes it from your computer.

You might use it to:

- Play an album, or a whole music folder, in the right order.
- Listen to an audiobook you bought, chapter by chapter, and pick up where you
  stopped.
- Build a playlist for a long drive or a quiet evening, in your own order.
- Play a playlist you made years ago in Winamp, foobar2000 or VLC.

Nothing in Local Media touches the internet, so it works just the same in Safe
Mode and when you are offline.

### Getting started

#### Open Local Media, step by step

1. Press **Ctrl+O** (**Station > Local Media...**). The Local Media window
   opens. It is a window of its own, like Radio Recordings, so it is on the
   Window menu and in the Ctrl+Tab order. It is also on the Go To list and in
   the Command Palette.
2. The first time, there is nothing in it yet. Quill Radio says so: "Nothing
   in Local Media yet." Your cursor is already on the **Add Media Files...**
   button, with **Add a Folder...** and **New Playlist...** beside it.
3. Press **Ctrl+O** again, or **Space** on the button. A file window opens.
   So from anywhere in Quill Radio, Ctrl+O twice takes you straight to picking
   files.
4. Pick one file, or hold **Ctrl** and pick several, and press **Enter**.
5. You should hear "Made a playlist called", the name of the folder the files
   came from, and how many items it has. A playlist of tracks from your Abbey
   Road folder is called Abbey Road, which is what you would have typed
   anyway.

If Local Media is already open, Ctrl+O from the main window brings it to the
front rather than opening a second copy.

#### Bring in a whole folder, step by step

1. In the empty window, press **Ctrl+Alt+O** (**Local Media > Add a
   Folder...**), or choose the **Add a Folder...** button.
2. Choose the folder and press **Enter**. You hear "Looking for media in", and
   the folder's name.
3. Every file in it comes in, and the files in the folders inside it too, in
   the order you would read the names: track 2 comes before track 10, and disc
   one comes before disc two.
4. You hear "Made a playlist called", the folder's name, and how many items it
   has.

Once you have playlists, **Add a Folder...** in the window adds the folder's
files to the end of the playlist you are on. To make a brand new playlist from
a folder, use **Add a Folder...** on the Local Media branch of Browse Stations,
or **Local Media: Add a Folder...** in the Command Palette.

#### Follow the Folder

A playlist made from a folder keeps an eye on it. Copy new music into the
folder later, and it joins the end of the playlist the next time you open Local
Media or choose that playlist. You hear how many new files were added.

- **Follow the Folder** (**Local Media > Follow the Folder**, Ctrl+Alt+F)
  turns this on and off. It has a check mark when it is on. Turned off, the
  playlist stays exactly as it is.
- **Check the Folder Now** (F5) looks straight away. If there is nothing new,
  you hear "Nothing new in the folder for", and the playlist's name.

Both only work on a playlist that was made from a folder. On any other
playlist, Quill Radio tells you so.

#### What Quill Radio can play

Quill Radio plays MP3, M4A and M4B audiobooks, AAC, Ogg, Opus, FLAC, WAV, WMA,
AIFF and more, and video files such as MP4, MKV, MOV and WebM. A video plays
its sound, and **Ctrl+Shift+V** shows the picture. When you add a folder,
anything that is not music or video, such as cover pictures and text files, is
left out.

### Finding your way around the window

#### The two lists

The window has two lists side by side, and Tab moves between them.

- **Playlists** (Alt+Y) on the left. Each one says how many items it has and
  how long it plays, such as "Road Trip, 12 items, 47 minutes".
- **Items** (Alt+I) on the right: what is in the playlist you are on, in the
  order it plays. Each row reads the title, the artist, the album, the length
  and the file name. **Choose Columns...** (Ctrl+Alt+Shift+C) chooses what
  each row says.

Under the lists are the **Add Media Files...**, **Add a Folder...** and **New
Playlist...** buttons, and a line that sums up the playlist you are on.

The row that is playing says **playing** after its title, or **paused**. A file
that is not where it used to be, because a drive is unplugged or a folder was
renamed, says **missing**. It keeps its place in the list until you decide
what to do with it.

Type the first letters of a title to jump to it. To select several items,
hold **Shift** and arrow, or press **Ctrl+A** (**Edit > Select All**) for every
item in the playlist.

#### The menus in the window

The window has its own menu bar, and every item on it shows its key:

- **Local Media** (Alt+L): New Playlist, Add Media Files, Add a Folder, Insert
  Files Here and Insert Files After, Import a Playlist, Export as M3U, Rename
  Playlist, Duplicate Playlist, Delete Playlist, Follow the Folder, Check the
  Folder Now, Choose Columns and Close.
- **Edit** (Alt+E): Undo, Cut, Copy, Paste Before, Paste After, Remove from
  Playlist, Remove Missing Items, Select All, Properties, Show in File Explorer
  and Locate Missing File.
- **Arrange** (Alt+A): Move Up, Move Down, Move to Top, Move to Bottom, Move to
  Position and Sort Playlist.
- **Play** (Alt+P): Play, Pause or Resume, Next Item, Previous Item, Play This
  Playlist, Continue Where I Left Off, Play Next, Add to Up Next, Shuffle,
  Shuffle Again, Repeat, Stop After This Item and Playlist Summary.

The Station and Window menus are there too, the same as in every Quill Radio
window. You seldom need the menus, though: press **Shift+F10**, or the
Applications key, on an item or a playlist, and everything you can do with it
is right there.

Close the window with **Escape** or **Ctrl+W** (**Local Media > Close**)
whenever you like. Whatever is playing carries on.

### Building playlists

#### Make a new playlist, step by step

1. Press **Ctrl+N** (**Local Media > New Playlist...**).
2. Type a name, such as Sunday Morning, and press **Enter**.
3. You hear "Made Sunday Morning. It is empty". Your cursor is on **Add Media
   Files...**, ready to fill it.
4. Press **Space** and pick your files. They are added to the end of the new
   playlist.

If you leave the name empty, the playlist is called My Playlist. Two playlists
never share a name: Quill Radio adds a number to the second one.

#### Add, insert and remove

- **Add Media Files...** (Ctrl+O) adds files at the end of the playlist you
  are on. You hear "Added", how many, and "to the end of", and the playlist's
  name.
- **Insert Files Here...** (Insert) adds files just before the item you are
  on, and **Insert Files After...** (Shift+Insert) adds them just after it.
  This is how you slip a song in between two others. You hear where they went,
  such as "Inserted 2 items at 5 of 14."
- **Remove from Playlist** (Delete) takes the selected items out of the
  playlist. You should hear "Removed", then "The file is still on your
  computer. Ctrl+Z undoes this."

> **QUILLBee's tip:** Delete in Local Media never deletes a file. It only
> takes the item out of the list, which is why it does not stop to ask. If
> you change your mind, Ctrl+Z puts it back in the very same place.

#### Playlists from other programs

**Import a Playlist...** (Ctrl+I) reads an M3U, M3U8 or PLS playlist that
Winamp, foobar2000, VLC or another player made, and turns it into a new
playlist named after the file.

1. Press **Ctrl+I** (**Local Media > Import a Playlist...**).
2. Choose the playlist file and press **Enter**.
3. You hear "Imported", how many items, and the new playlist's name.

A few things to know:

- If some of the files are not on this computer, they come in anyway and are
  marked missing, and Quill Radio tells you how many.
- Web addresses in the playlist are left out, and Quill Radio tells you how
  many. Internet stations belong in your favorites: **Import Stations from
  Playlist**, in Chapter 6, is the place for those.
- On the Local Media branch of Browse Stations, the menu on the branch offers
  **Import a Playlist...** too.

#### Rename, duplicate and delete a playlist

These work on the playlist you are on, from the **Local Media** menu or from
the menu on the playlist itself (Shift+F10 in the Playlists list).

- **Rename Playlist...** (F2) gives it a new name. Ctrl+Z gives back the old
  one.
- **Duplicate Playlist** (Ctrl+D) makes a copy, called the same name with
  "copy" after it, placed just below the original. It keeps the same items,
  shuffle, repeat and folder. It is a handy way to try out a new order without
  losing the old one.
- **Delete Playlist...** (Shift+Delete, or Delete in the Playlists list) asks
  first, with **No** already chosen. Only the list goes: your files stay where
  they are. You hear "Deleted the playlist", and its name, and **Ctrl+Z**
  brings it back, items and all, in the same place.

### Arranging a playlist

A playlist is an order you chose, and Local Media gives you every way to
change it from the keyboard. After each move, Quill Radio tells you where the
items landed, such as "Moved to 3 of 12", and the moved items stay selected so
you can move them again.

#### Move items, step by step

1. Arrow to an item. To move several at once, hold **Shift** and arrow to
   select them.
2. Press **Alt+Shift+Up** (**Arrange > Move Up**) or **Alt+Shift+Down**
   (**Arrange > Move Down**) to move them one place.
3. Press **Alt+Shift+Home** (**Move to Top**) to send them to the start, or
   **Alt+Shift+End** (**Move to Bottom**) to send them to the end.
4. At the top or the bottom, you hear "Already at the top" or "Already at the
   bottom", so you know you have gone as far as you can.

#### Move to Position, step by step

When you know exactly where something belongs, type its new place:

1. Select the item, or items.
2. Press **Ctrl+J** (**Arrange > Move to Position...**).
3. Type the number of the place it should go, from 1 to the number of items,
   and press **Enter**. You hear where it landed.

#### Cut and paste to move a long way

For a longer move, cut and paste is quickest.

1. Select what you want to move and press **Ctrl+X** (**Edit > Cut**). Nothing
   disappears yet. You hear "Cut", and what you cut.
2. Arrow to where it belongs.
3. Press **Ctrl+V** (**Edit > Paste Before**) to put it before that item, or
   **Ctrl+Alt+V** (**Edit > Paste After**) to put it after it.

> **QUILLBee wants you to know:** Cutting in Local Media only marks the items.
> They stay in the list, playing and all, until you paste. If you never
> paste, nothing has changed.

#### Copy into another playlist

**Ctrl+C** (**Edit > Copy**) holds copies of the selected items. Arrow to
another playlist, or another place in the same one, and paste with **Ctrl+V**
or **Ctrl+Alt+V**. The originals stay where they were. Ctrl+C also puts the
files' paths on the clipboard as text, so you can paste them into an email or
a document.

#### Sort Playlist, step by step

1. Press **Ctrl+Shift+S** (**Arrange > Sort Playlist...**).
2. Choose how to sort: **Title**, **Artist, then album**, **Album, then track
   order**, **File name**, **Folder, then file name**, **Length, shortest
   first**, **Date added, oldest first** or **Random order**.
3. Press **Enter**. The playlist is sorted once, and your cursor is on the
   first item.

A sort happens once. After that, the order is yours to change again, and
**Ctrl+Z** puts back the order you had before.

#### Moving whole playlists

In the **Playlists** list, **Alt+Shift+Up** and **Alt+Shift+Down** move the
playlist you are on up and down, and **Alt+Shift+Home** and **Alt+Shift+End**
move it to the top or the bottom. Your playlists stay in that order here and in
Browse Stations.

#### Undo and Undo History

Changed your mind? **Ctrl+Z** (**Edit > Undo**) takes back the last change:
a move, a sort, a paste, a removal, a rename, or a deleted playlist. Press it
again to go back one more step.

In the main window, **Edit > Undo History** (Ctrl+Alt+Shift+A) lists the last
ten things you can take back, Local Media changes among them, and lets you
take back just one. "Taking back the last thing you did", in Chapter 15, says
more.

### Playing

#### Play a playlist, step by step

1. Arrow to an item and press **Enter**. Quill Radio plays it, then carries on
   down the playlist by itself. You should hear the title and where it is,
   such as "Playing Here Comes the Sun, 7 of 17."
2. Press **Space** on the item that is playing to pause it. Press **Space**
   again to carry on. On any other item, Space selects it, as it does in any
   list.
3. Press **Enter** on the item that is playing to stop it.
4. Press **Ctrl+Right** (**Play > Next Item**) for the next item and
   **Ctrl+Left** (**Play > Previous Item**) for the one before.
5. When the last item ends, you hear "That was the end of", and the
   playlist's name.

The **Play** menu has the same verbs with keys that work from anywhere in the
window: **Play** (Ctrl+Enter) and **Pause or Resume** (Ctrl+Space).

In the **Playlists** list, **Enter** plays the whole playlist you are on from
the start.

#### Play This Playlist, and Continue Where I Left Off

- **Play This Playlist** (Ctrl+Alt+P) plays the playlist from the start, or
  from the start of its shuffled order when shuffle is on.
- **Shuffle and Play**, on the menu on a playlist, turns shuffle on and starts
  playing in one go.
- **Continue Where I Left Off** (Ctrl+Alt+C) goes back to the item you were
  last listening to in that playlist, at the place you stopped. This is the
  one to use for an audiobook. If there is nothing to go back to, it plays the
  playlist from the start.

#### Play Next and Add to Up Next

Sometimes you want to hear a particular song soon, without changing your
playlist.

- **Play Next** (Ctrl+Shift+Enter) plays the selected items straight after the
  one that is playing. You hear "Will play next."
- **Add to Up Next** (Ctrl+Alt+Enter) puts them after anything already
  waiting. You hear how many are waiting.

Either way, once they have played, the playlist carries on where it left off.

#### Shuffle and Shuffle Again

- **Shuffle** (Ctrl+H) turns shuffle on and off, and has a check mark on the
  Play menu when it is on. Shuffle picks one order and keeps it, so every item
  plays once before any plays again, and the previous key always takes you back
  to what you just heard.
- **Shuffle Again** (Ctrl+Shift+H) deals a fresh order. The new order starts
  after the item that is playing.

#### Repeat

**Repeat** (Ctrl+R) goes round three choices, and Quill Radio says the one you
land on:

- **Repeat off**: the playlist plays once and stops.
- **Repeat the whole playlist**: after the last item, it starts again at the
  top.
- **Repeat this item**: the item that is playing plays again when it ends.
  Pressing Next still moves on.

Each playlist remembers its own shuffle and repeat.

#### Stop After This Item

**Stop After This Item** (Ctrl+Alt+S) stops when the item that is playing
ends. You hear "Will stop after this item", and later "Stopped after that
item, as you asked." It switches itself off once it has done its job, so the
next time you play, the playlist carries on as normal. It is perfect for
falling asleep to one more chapter.

#### Next and previous from any window

You do not need the Local Media window open to move through a playlist. From
any Quill Radio window, the chapter keys move through the playlist that is
playing: **Ctrl+Shift+.** for the next item and **Ctrl+Shift+,** for the one
before.

When a file has chapters of its own, like an audiobook, the chapter keys move
by chapter first. At the last chapter, they move on to the next item.

The Command Palette has **Local Media: Next Item** and **Local Media: Previous
Item** too, if you would rather move by name.

#### Where Am I, and Playlist Summary

- **Where Am I** (Ctrl+Shift+W), from any window, tells you where you are in
  the item and in the playlist, such as "2 minutes 10 seconds of 3 minutes 5
  seconds, 7 of 17 in Abbey Road."
- **Playlist Summary** (Ctrl+T, in the Local Media window) sums up the
  playlist you are on in one breath: how many items and how long, what is
  playing and where, how many are waiting up next, and whether shuffle and
  repeat are on.

### Local Media in Browse Stations

Local Media is also the second branch of Browse Stations, right under
Favorites. It is handy when you are already browsing and want your own music
without opening another window.

#### Play from the tree, step by step

1. Press **Ctrl+B** to open Browse Stations, arrow to **Local Media** and press
   **Right Arrow**.
2. Your playlists are listed, each with how many items it has and how long it
   plays. Under them are **Add Media Files...**, **Add a Folder...**, **New
   Playlist...** and **Open the Local Media Window**. While you have no
   playlists yet, **Import a Playlist...** is there too.
3. Arrow to a playlist and press **Right Arrow** to open it. Each item says
   its artist and length, "video" for a video, and "missing" for a file that is
   not there.
4. Press **Enter** on an item. It plays, and the rest of the playlist follows
   it.

In the tree, **Add Media Files...** and **Add a Folder...** always make a new
playlist, named after the folder, and one made from a folder follows it.

#### The menu on a row

Press **Shift+F10**, or the Applications key, on any Local Media row.

- **On the Local Media branch:** Open or Close, Open in Local Media Window,
  Add Media Files, Add a Folder, New Playlist, Import a Playlist, Hide This
  Source and Reset Sources to Default.
- **On a playlist:** Open or Close, Play This Playlist, Shuffle and Play,
  Continue Where I Left Off (when there is somewhere to continue from), Open in
  Local Media Window, Add Media Files, Add a Folder, Check the Folder for New
  Files (for a playlist made from a folder), Rename, Duplicate, Export as M3U
  and Delete Playlist.
- **On an item:** Play (or Stop, on the one playing), Play Next, Add to Up
  Next, Remove from Playlist, Locate (for a missing file) or Show in File
  Explorer, Copy Path, Properties, Open in Local Media Window, and Where Am I?
  on the item that is playing.

**Open in Local Media Window** opens the window on that very playlist and
item, so you can carry on arranging there.

The **Delete** key works here too. On an item, it asks "Remove", the title,
"from", the playlist, and "The file stays", the same way Delete always asks in
Browse Stations. On a playlist, it asks whether to delete the playlist.

### When a file goes missing

If you move a folder, rename it, or unplug the drive a file was on, the item
says **missing**. It keeps its place in the playlist, and when Quill Radio comes
to it while playing, it skips to the next one that is there. Plug the drive
back in and the item simply plays again.

#### Locate a missing file, step by step

1. Arrow to the missing item.
2. Press **Ctrl+Shift+L** (**Edit > Locate Missing File...**), or choose
   **Locate File...** on its menu.
3. A file window opens, already looking for the file by name. Find it where it
   is now and press **Enter**.
4. You hear "Found", and its title. If the whole folder moved, the other
   missing files from that folder are found too, and Quill Radio tells you how
   many.

Pressing Ctrl+Shift+L on an item that is not missing takes you to the first
one that is. If nothing in the playlist is missing, Quill Radio tells you so.

#### Remove Missing Items

If the files are gone for good, **Remove Missing Items** (Ctrl+Shift+Delete,
on the **Edit** menu) takes every missing item out of the playlist at once.
**Ctrl+Z** brings them back if you were too quick.

### Properties and File Explorer

- **Properties...** (Alt+Enter) opens **Local Media Item Properties**, a box
  you can arrow through and copy from. It shows the title, artist, album, length, whether it is audio or
  video, its place in the playlist, the file name, the folder, whether it is on
  this computer, and how big it is. Press **Escape** to go back to the list.
- **Show in File Explorer** (Ctrl+Shift+E) opens the item's folder in File
  Explorer with the file already selected.
- **Copy Path**, on an item's menu in Browse Stations, puts the file's full
  path on the clipboard.

### Exporting a playlist, step by step

**Export as M3U...** goes the other way from Import, so another player can
open your playlist.

1. Arrow to the playlist and press **Ctrl+Shift+X** (**Local Media > Export as
   M3U...**).
2. A save window opens with the playlist's name already filled in. Choose
   where to save it and press **Enter**.
3. You hear "Exported", how many items, and the file's name.

Save it in your music folder and it keeps working when you copy the whole
folder to another computer, because the files inside that folder are written
relative to it. An empty playlist has nothing to export, and Quill Radio says
so.

### Playing files from File Explorer

You do not have to open Local Media first. If you are looking at the music on
your computer or an external drive in File Explorer, you can play a song from
right there, the same way you might choose VLC or Windows Media Player.

#### Play a song with Open with, step by step

1. In File Explorer, move to the song you want to hear.
2. Press **Shift+F10**, or the Applications key, to open its menu.
3. Choose **Open with**. On Windows 11, if you do not see Quill Radio straight
   away, choose **Choose another app**.
4. Choose **Quill Radio** and press **Enter**. You hear "Playing", and the
   song's name.

Quill Radio is in the Open with list for music, audiobooks, video, and M3U
and PLS playlists as soon as it is installed. Nothing else changes: whatever
opened your music before still opens it when you press Enter.

#### Make Quill Radio your media player, step by step

If you would like your music to open in Quill Radio every time you press Enter
on it, you can choose that in Windows. Windows keeps this choice for you alone,
and no app is allowed to make it for you, so Quill Radio takes you to the right
page and you choose there.

1. In Quill Radio, press **Ctrl+,** to open **Preferences**.
2. Press **Tab** until you reach the **Windows and your files** group, and the
   **Make Quill Radio My Media Player...** button. Its access key is **Alt+Q**.
   Press **Space**.
3. Quill Radio explains what happens next. Press **Enter** for OK.
4. Windows opens **Settings**, on the **Default apps** page for Quill Radio. It
   is a list of file types, each with the app that opens it now.
5. Press **Tab** until you reach the list, then arrow to **.mp3** and press
   **Enter**. Windows asks which app should open .mp3 files.
6. Arrow to **Quill Radio**, then press **Tab** to the **Set default** button
   and press **Enter**.
7. Do the same for any other type you want Quill Radio to open, such as .m4a,
   .m4b for audiobooks, or .flac. Anything you leave alone stays with the app
   that opens it now.
8. Press **Alt+F4** to close Settings.

On Windows 10 the page is the general Default apps page. Choose **Choose
default apps by file type**, find .mp3, and choose Quill Radio there.

You can also do it from File Explorer: on a song, choose **Open with**, then
**Choose another app**, pick **Quill Radio**, and choose **Always**.

To change your mind, go back to the same Settings page and choose another app.
If you use the portable copy of Quill Radio, press the button again after you
move its folder, so Windows knows where it went.

#### Several files at once

Select several songs in File Explorer and press **Enter**. Hold **Shift** and
arrow down to select a run of songs, or hold **Ctrl**, arrow to each song you
want, and press **Space** to add it. They become one list in Local Media called
**Opened files**, and the first one starts playing. **Ctrl+Shift+.** and
**Ctrl+Shift+,** move to the next and previous song, just as in any playlist.

Opening a folder plays everything in it, in the same order **Add a Folder**
uses. Opening an M3U or PLS playlist adds it to Local Media as a playlist of
its own and plays it; open the same playlist again and it plays the copy you
already have.

The Opened files list is a scratch list. The next time you open files from File
Explorer, it is replaced with the new ones. To keep it, choose **Save as
Playlist...** on it, in the Local Media window (**Ctrl+S**) or on its menu in
Browse Stations, and give it a name. Then it is a playlist like any other, and
the next files you open start a new Opened files list.

#### When Quill Radio is already open

If Quill Radio is already running, even tucked away in the system tray, the
file goes to the copy that is open, and it starts playing. Quill Radio does not
jump in front of File Explorer, so you can carry on choosing songs. You hear
what is playing once, even when you opened several files.

If a file cannot be played, you hear one sentence saying so, such as "Quill
Radio could not find song.mp3." when a drive has been unplugged, or "Quill
Radio cannot play notes.docx." for something that is not music or video.

#### The right-click menu

Every song also has two items of its own on its right-click menu:

- **Play with Quill Radio** plays it, just like Open with.
- **Add to Quill Radio Playlist** adds it to the end of the Opened files list
  without stopping what is playing. If nothing is playing, it starts.

On Windows 11, press **Shift+F10** to reach them. The shorter menu that the
Applications key opens keeps them under **Show more options**.

### Keys in the Local Media window

| Key | What it does |
| --- | --- |
| Enter | Play the item, or stop the one playing; on a playlist, play it |
| Space | Pause or resume the item playing |
| Ctrl+Enter, Ctrl+Space | Play, Pause or Resume, from anywhere in the window |
| Ctrl+Right, Ctrl+Left | Next item, previous item |
| Ctrl+Alt+P | Play This Playlist |
| Ctrl+Alt+C | Continue Where I Left Off |
| Ctrl+Shift+Enter, Ctrl+Alt+Enter | Play Next, Add to Up Next |
| Ctrl+H, Ctrl+Shift+H | Shuffle on or off, Shuffle Again |
| Ctrl+R | Repeat: off, the whole playlist, this item |
| Ctrl+Alt+S | Stop After This Item |
| Ctrl+T | Playlist Summary |
| Ctrl+N | New Playlist |
| Ctrl+O | Add Media Files |
| Ctrl+Alt+O | Add a Folder |
| Insert, Shift+Insert | Insert files before or after the item |
| Ctrl+I, Ctrl+Shift+X | Import a Playlist, Export as M3U |
| F2 | Rename Playlist |
| Ctrl+S | Save as Playlist, to keep the Opened files list |
| Ctrl+D | Duplicate Playlist |
| Shift+Delete | Delete Playlist (asks first) |
| Ctrl+Alt+F, F5 | Follow the Folder, Check the Folder Now |
| Delete | Remove from the playlist (the file stays) |
| Ctrl+Shift+Delete | Remove Missing Items |
| Ctrl+Shift+L | Locate Missing File |
| Alt+Shift+Up, Alt+Shift+Down | Move up or down one place |
| Alt+Shift+Home, Alt+Shift+End | Move to the top or the bottom |
| Ctrl+J | Move to Position |
| Ctrl+Shift+S | Sort Playlist |
| Ctrl+X, Ctrl+C | Cut, Copy |
| Ctrl+V, Ctrl+Alt+V | Paste Before, Paste After |
| Ctrl+A | Select All |
| Ctrl+Z | Undo |
| Alt+Enter | Properties |
| Ctrl+Shift+E | Show in File Explorer |
| Ctrl+Alt+Shift+C | Choose Columns |
| Escape, Ctrl+W | Close the window; playing carries on |

From any Quill Radio window: **Ctrl+O** opens Local Media, **Ctrl+Shift+.**
and **Ctrl+Shift+,** move to the next and previous item, and **Ctrl+Shift+W**
says where you are.

### What you learned, and where to go next

You can now bring your own music, audiobooks and videos into Quill Radio, from
single files, whole folders or other players' playlists. You can build
playlists, slip songs in between others, put everything in exactly the order
you want, and take back any change you regret. You can play, shuffle and
repeat, line up what plays next, stop after one more item, pick up where you
left off, and move through a playlist from any window. When a file goes
missing, you know how to find it again. And you can play a song straight from
File Explorer, or make Quill Radio the app your music opens in.

The tutorial **Play your own files in playlists**, in the **More than radio**
track, walks through it all with you. Next, Chapter 11, YouTube, brings in
everything YouTube can do here.

## Chapter 11: YouTube

YouTube is full of things worth listening to: lectures and talks, travel
shows, radio programmes that only publish there, live broadcasts, and a great
deal of music. Quill Radio brings it in as if it were radio. You can search it,
play it, record it, follow channels, read along with captions, read what
people said in the comments, and be told when a channel puts up something new.
None of it needs a Google account. If you would like your own Home page and
subscriptions too, you can turn on your YouTube sign-in.

The tutorial **YouTube, with no account anywhere**, in the **More than radio**
track, walks you through the first steps.

### Playing a YouTube link

A video link, a `youtu.be` short link or a channel's live page plays just like
a radio station. You can add one with **Add YouTube Link...** (below) or with
**Add Custom Station...** (Ctrl+N). It sits in your favorites, records with
Record Now, and can be scheduled. Quill Radio saves the page's address and
finds the sound fresh every time, so a recording you schedule today still
works next week. Everything YouTube needs is built into Quill Radio, so
nothing downloads the first time. A private, removed, blocked or not-yet-live
video tells you so in plain words.

#### Adding YouTube to Browse Stations, step by step

1. Press **Ctrl+Alt+N** (**Station > Add YouTube Link...**). A box opens. If a
   YouTube link is on your clipboard, it is already filled in.
2. Paste a link and press **Enter**. Quill Radio files it by what it is: an
   `@name` link follows the channel, `@name/live` keeps the live broadcast, a
   playlist link becomes a folder, and a video link becomes a row.
3. You should hear, for example, "Following that channel. Find it under Browse
   Stations, YouTube." A moment later it names what you added.
4. Press **Ctrl+B**, arrow to **YouTube** and open it. A channel opens into
   **Uploads**, **Live** and the channel's playlists. A long channel has **More...** at
   the end to see the next page.
5. Press **Enter** on a video to play it. Videos play, record and can be made
   favorites, just like a station.

Worth knowing:

- **Search YouTube...** is always the first row under YouTube, and **My
  YouTube** comes next when your sign-in is on.
- While the YouTube branch is empty, it shows **Add a Channel...**, **Add a
  Playlist...** and **Add a Video...**. After that, those three are on the
  branch's menu (Shift+F10) and on every row inside it, where the last one is
  called **Add a Video URL...**.
- The first time you add or play anything from YouTube, Quill Radio asks once
  whether it may contact YouTube, and remembers your answer.
- A row uses the video's own name, with the channel and length read after it.
  The row is saved first, so a video whose details will not load is still
  saved and still plays.
- **View Transcript...** on any YouTube row fetches the captions and opens the
  transcript without playing anything.
- If a video will not play, Quill Radio offers to fetch the newest YouTube
  helper. Say yes, and it installs it, tells you the version, and plays the
  video. See "Repair YouTube Support" below.
- YouTube is not available in Safe Mode.

### Finding things on YouTube

#### Search YouTube, step by step

Search YouTube finds videos, playlists and channels, and puts them in one list
with each row telling you which it is.

1. Press **Ctrl+Shift+6** (**Station > Search YouTube...**). Browse Stations
   opens, and a box asks what you would like to find. If Browse Stations is
   already open, you can also press **Enter** on **Search YouTube...**, the
   first row under **YouTube**.
2. Type what you are looking for, such as `Bristol walking tour`, and press
   **Enter**. You should hear "Searching YouTube for Bristol walking tour...".
3. When the answer arrives, you hear how many were found, once, such as "38
   found for Bristol walking tour: 20 videos, 10 playlists, 8 channels." Your
   cursor is on the first result, in a **Search Results** branch at the top of
   the tree.
4. Arrow through the rows. Each one says what it is first:
   - "Bristol walking tour (video, 12 minutes, Rick Steves)"
   - "Europe Through the Back Door (playlist, Rick Steves)"
   - "Rick Steves' Europe (channel, 1.2 million subscribers)"
5. Press **Enter** on a video to play it. Press **Enter** (or **Right
   Arrow**) on a playlist to open its videos, or on a channel to open it.
6. When you are done, press **Escape** in the Find box, or choose **Close
   Search Results** from the branch's menu, to tidy the results away.

Worth knowing:

- Videos come first, then playlists, then channels. Up to 20 videos and 10 of
  each of the others come back from one search. If what you want is not
  there, search for something more exact.
- A playlist row says how many videos it has only when YouTube tells Quill
  Radio. Often it does not, so open the playlist to find out.
- Every result is an ordinary row, so Shift+F10 offers the same things it
  would anywhere else in Browse Stations: Add to Favorites, Copy Link, View
  Transcript, Read Comments and so on.
- **Search Stations** (Ctrl+F) still finds YouTube videos alongside radio
  stations, as before. Search YouTube is the one to use when you want
  channels and playlists too.

#### YouTube in Search Stations

**Search Stations** (Ctrl+F) asks YouTube too, and the videos it finds sit in
the same list as the radio stations. To see only those, choose **YouTube** in
**Source** (Alt+U). To stop Search Stations asking YouTube at all, turn it off
in **Station > Search Sources...** (Ctrl+Alt+Shift+U). Search Stations finds
videos only; Search YouTube, above, finds playlists and channels as well.

#### Search with filters, or search YouTube Music

YouTube's own Filters menu is here too. Use it when a plain search gives you
too much: only this week's uploads, only long videos, only what is live right
now, or the most-watched first.

1. Press **Ctrl+Alt+Shift+0** (**Video > YouTube > Search YouTube with
   Filters...**). A window opens with the cursor in **Search for**.
2. Type what you are looking for.
3. Tab through the choices and set the ones you want. Each starts at "no
   filter", so you only change what matters to you:
   - **Source** (Alt+O): **YouTube**, or **YouTube Music songs** to find songs
     rather than music videos. The filters below do not apply to YouTube
     Music.
   - **Type** (Alt+T): **Videos**, **Live now**, **Playlists** or **Channels**.
   - **Uploaded** (Alt+U): any time, the last hour, today, this week, this
     month or this year.
   - **Length** (Alt+L): under 4 minutes, 4 to 20 minutes, or over 20 minutes.
   - **Sort by** (Alt+R): relevance, upload date, view count or rating.
4. Press **Enter**. Browse Stations opens, and you hear something like
   "Searching YouTube for walking tours, videos, this week...".
5. The answers arrive in **Search Results**, just like Search YouTube's. Every
   row plays on Enter and has its usual menu.

### Channels

#### Open a channel, step by step

1. Arrow to a channel row (from a search, from **My YouTube**, or one you
   follow) and press **Right Arrow**.
2. It opens into **Uploads**, then **Live**, then **Shorts**, then the
   channel's playlists.
3. Open **Uploads** for the newest videos first. A long channel has
   **More...** at the end for the next page.
4. Open **Live** for anything the channel is broadcasting right now, which
   comes first, followed by its past broadcasts. If the channel has never
   broadcast live, Live is simply empty.
5. Open **Shorts** for the channel's short videos. They play like any other
   video.

To read what a channel says about itself, press **Shift+F10** on its row and
choose **About This Channel...** (T). A small window shows its name, how many
subscribers it has and its own description. Read it with the arrow keys, and
press **Escape** to close it.

#### Follow a channel, or subscribe on YouTube

There are two ways to keep a channel, and you can use either or both.

**Follow This Channel in Quill Radio** keeps the channel under Browse
Stations, YouTube, on this computer. No account is needed.

1. Arrow to a channel row and press **Shift+F10** (or the Applications key).
2. Choose **Follow This Channel in Quill Radio** (F).
3. You should hear "Following Rick Steves' Europe in Quill Radio." The channel
   now has its own row under **YouTube**.

To stop, press **Shift+F10** on the channel and choose **Stop Following This
Channel** (P).

**Subscribe on YouTube...** subscribes your YouTube account, the same as the
Subscribe button on YouTube's own website.

1. Press **Shift+F10** on a channel and choose **Subscribe on YouTube...**
   (Y).
2. You hear "Opening Rick Steves' Europe on YouTube in your browser. YouTube
   will ask you to confirm the subscription there." Your web browser opens on
   YouTube's own page for that channel.
3. Confirm the subscription in your browser, where you are signed in to
   YouTube.

Quill Radio never subscribes for you; YouTube always asks you to
confirm. YouTube's own notification bell for the channel is
on that same page in your browser. If you use your YouTube sign-in in Quill Radio (see below), the new
subscription shows up in **My YouTube > Subscriptions**.

#### Get told about new videos, step by step

Quill Radio can tell you when a channel you follow puts up a new video. This
is Quill Radio's own bell, separate from YouTube's.

1. In Browse Stations, open **YouTube** and arrow to a channel you follow.
2. Press **Shift+F10** and choose **Notify Me About New Videos** (N).
3. You should hear that new videos will notify you.

From then on, whenever Quill Radio checks your podcasts for new episodes, it
also looks at that channel's newest few videos. Each new one goes into **Help >
Notifications** as "New on Rick Steves' Europe: Bristol walking tour", with a
desktop notice and a sound, the same as a new podcast episode. Press **Enter**
on it in Notifications to play the video.

Worth knowing:

- It is off for every channel until you turn it on.
- The first look only notes what is already there, so you are not told about
  old videos as if they were new.
- It follows the same schedule as your podcasts, set by **Check subscribed
  podcast feeds** in Preferences. If that is set to Manually only, channels
  are not checked on their own either.
- Quiet hours hold back the desktop notice and the sound, but the entry in
  Notifications is always kept.
- To stop, choose **Stop Notifying About New Videos** from the same menu.
  Stopping following a channel turns its bell off too.

### Playlists and your subscriptions

#### Add from a YouTube playlist, step by step

1. Press **Ctrl+Shift+Y** (**Station > Add from YouTube Playlist...**). A box
   opens. A playlist link on your clipboard is already filled in.
2. Paste a playlist link (`youtube.com/playlist?list=...`) and press **Enter**.
   You should hear "Listing that playlist...", then how many videos it has.
3. A window titled "Add from YouTube Playlist" opens, with the playlist's own
   name at the top. Your cursor is in the **Videos** list, in the order the
   uploader chose. Each row reads like "3. Introducing layers, 5 minutes 31
   seconds, 3Blue1Brown".
4. Select what you want. Hold **Shift** or **Ctrl** with the arrow keys to
   select several.
5. Choose **Add Selected** (Alt+S), or **Add All** (Alt+A) for the lot.
6. You should hear how many were added, and how many were already in your
   favorites.
7. Press **Escape** to close the window.

Each video becomes an ordinary favorite you can play, record and schedule.
This brings the videos in once; it does not follow the playlist. Videos added
to the playlist later are not picked up, and when one video ends, the next
does not start. To collect new videos, run it again on the same link, and the
ones you already have are skipped. A watch link that happens to have `list=`
in it is treated as just that one video.

#### Import YouTube Subscriptions, step by step

This follows every channel you subscribe to on YouTube, using a file you
download from Google. No account, sign-in or password is involved, and nothing
is sent anywhere.

1. In a web browser, go to `takeout.google.com`. Choose **YouTube and YouTube
   Music**, narrow it down to **subscriptions**, and download the file.
2. Unzip it. The file you need is `YouTube and YouTube
   Music\subscriptions\subscriptions.csv`.
3. In Quill Radio, press **Ctrl+Alt+Shift+Y** (**Station > Import YouTube
   Subscriptions...**). An explanation opens. Choose **OK**.
4. A file window opens: "Choose your subscriptions.csv". Find the file and
   choose **Open**.
5. You should hear how it went, such as "Imported 24 channels; 3 you already
   followed". The channels appear under YouTube in Browse Stations.

This brings your channels in once. Channels you subscribe to later appear when
you download and import the file again. Channels you already follow are
skipped, and any row that is not a channel is skipped too, rather than
spoiling the import.

Even with your YouTube sign-in turned on, YouTube Premium's extras do not
carry over: YouTube's terms do not allow another app to play in the background
or keep copies for offline listening. No app other than YouTube's own can
bring your watch history across.

### Watching and reading along

#### Moving around a finished video

A finished YouTube video works like a recording: it has a beginning and an
end. So everything in "Speed, position and chapters" in Chapter 4 works on it.
Play Faster (Ctrl+Shift+Up), Play Slower (Ctrl+Shift+Down) and Normal Speed
(Ctrl+Shift+0) change the speed, and the speed you choose on a YouTube video is
kept for YouTube videos. Rewind and Forward 30 Seconds (Ctrl+Shift+Left and
Right) move you along, **Where Am I?** (Ctrl+Shift+W) tells you how far in you
are, and **Go to Position...** (Ctrl+Alt+J) jumps to a time you type. When the
video's maker published chapters, **Chapters...** (Ctrl+Shift+C), **Next
Chapter** (Ctrl+Shift+.) and **Previous Chapter** (Ctrl+Shift+,) step through
them. Quill Radio remembers where you stopped, so a long video carries on from
there next time. A live broadcast has none of this, and each of these keys
tells you so.

#### Captions, the picture and described audio

YouTube plays as sound only to begin with. **Captions** (Ctrl+Shift+K) opens
the captions in a window you can read with your screen reader or braille
display, **Show Video** (Ctrl+Shift+V) shows the picture, and **Audio and
Described Audio...** (Ctrl+Shift+A) lists the video's sound tracks, including
a described one when the video has it. "Video, captions and described audio"
in Chapter 5 walks through each one.

#### Transcript, step by step

1. While a YouTube video plays, press **Ctrl+Shift+T** (**Playback >
   Transcript...**). You should hear "Fetching transcript...", then a window
   titled "Transcript:" and the video's title opens.
2. Your cursor is in the transcript, an ordinary box you can read but not
   change. Arrow through it, select text, or use your screen reader's review
   cursor.
3. Press **Enter** on any line to play from the moment that line was spoken.
   The **Play from Here** button does the same.
4. Press **Ctrl+F** (or **Find...**) to search. Each match tells you where it
   is, such as "Found at 12 minutes 8 seconds".
5. The other buttons are **Copy**, **Links...** (Ctrl+Shift+L, every web
   address in the transcript), **Save As...** (plain text, WebVTT or SubRip),
   and **Open in QUILL**.
6. Press **Escape** to close.

If the captions were made automatically, the heading says so. A live stream
has no transcript and tells you so, and so does a video with no captions. For
a podcast episode whose feed publishes a transcript, use **View
Transcript...** on the episode's menu in Browse Stations.

#### Read a video's comments, step by step

1. Do one of these:
   - While a YouTube video is playing, press **Ctrl+Shift+7** (**Video >
     Read Comments...**).
   - In Browse Stations, arrow to a YouTube video, press **Shift+F10** and
     choose **Read Comments...** (O).
2. A window titled "YouTube Comments" opens. You hear "Fetching comments...",
   then how many arrived, such as "100 comments."
3. Press **Tab** to reach the **Comments** list, and arrow through it. Each
   row reads like "Alice: The bridge at sunset is the best bit. ... (1,203
   likes, 2 years ago)". A reply comes right after the comment it answers and
   reads like "Ben, reply to Alice: Agreed!". Emoji are read as their names,
   such as "(face with tears of joy)", and a web address as "link to
   example.com". Loading more comments adds rows at the end and never moves
   you.
4. Press **Tab** to reach **Full text** and read the selected comment whole,
   with the arrow keys.
5. To look for something, press **Alt+M** for **Search comments** and type. The
   list narrows as you type, and when you pause you hear how many match, such
   as "12 of 100 comments match." Clear the box to see them all again.
6. To change the order, press **Alt+B** for **Sort by** and choose **Newest
   first** or **Top comments**. Quill Radio asks YouTube again.
7. Press **Alt+L** for **Load More** to fetch the next hundred, up to a
   thousand. The comments you already have stay where they are.
8. Press **Alt+P** for **Copy Comment** to put the selected comment, with who
   wrote it, on the clipboard.
9. Press **Escape** to close the window. You are back where you were.

If the comments cannot be fetched, you hear why in one sentence, such as
"Comments are turned off for that video.", and it is listed in **Recent
Problems** (Ctrl+Alt+Shift+P).

#### The YouTube Video window, step by step

This window gathers everything about one video apart from playing it: what the
uploader wrote, the moments they listed, and, for a premiere or a scheduled
stream, how long until it starts.

1. Do one of these:
   - While a YouTube video is playing, press **Ctrl+Alt+Shift+8** (**Video >
     YouTube > YouTube Video...**).
   - In Browse Stations, arrow to a YouTube video, press **Shift+F10** and
     choose **YouTube Video...** (Y).
2. A window titled "YouTube Video" opens. When the details arrive you hear
   what the video is right now, such as "Live now.", "A video, 42 minutes
   long." or "Starts in 2 hours 5 minutes.", and how many moments its
   description lists.
3. Press **Alt+D** for the **Description** and read it with the arrow keys.
4. Press **Alt+M** for **Moments in the description**. These are the lines of
   the description that give a time, like a running order or a track list.
   Each reads like "The interview, 12:40". If this video is the one playing,
   press **Enter** on a moment to jump straight there.
5. For a premiere or a stream that has not started yet, **Remind Me When It
   Goes Live...** (Alt+G) sets one of Quill Radio's own reminders, so you are
   told when to come back.
6. **Save Audio...** (Alt+S) adds the video's sound to your downloads, the same
   as **Download...** on its row. **Live Chat...** (Alt+H) opens its chat.
7. Press **Escape** to close the window.

For the words the video speaks, use **Transcript** (Ctrl+Shift+T), described
above. It already lets you search, jump to a line and save the whole
transcript to a file.

#### Skip sponsor segments, step by step

Many videos stop for a sponsor's message, a plug for merchandise or a reminder
to like and subscribe. SponsorBlock is a list, kept by volunteers, of where
those parts are. Quill Radio can jump over them for you. It is off until you
turn it on.

1. Press **Ctrl+Alt+Shift+9** (**Video > YouTube > Skip Sponsor
   Segments...**).
2. Read the short explanation at the top. To look a video up, Quill Radio
   sends SponsorBlock only the first four characters of a scrambled form of
   the video's id. It never sends the video's address or anything about you,
   so SponsorBlock cannot tell what you are watching.
3. Check **Skip marked segments in YouTube videos** (Alt+S).
4. Tick the kinds you want skipped. Sponsor reads, self-promotion and
   reminders to like or subscribe are ticked to start with. You can add
   intros, end credits, previews, talking in music videos and off-topic
   tangents.
5. Choose **OK**. You hear, for example, "Skipping 3 kinds of segment in
   YouTube videos."

From then on, when a video reaches a marked part, Quill Radio jumps to the end
of it and says so once, such as "Skipped a sponsor segment." If you go back
into that part on purpose, it lets you listen. Many videos have nothing
marked, and then nothing happens. Live streams are never skipped.

### Live chat

A live stream's chat is where people talk while it is on. Quill Radio shows it
as a plain list you can read at your own pace, and it never pulls you away from
what you are reading. A finished stream's chat replay works too, where YouTube
kept one.

#### Open a live chat, step by step

1. Do one of these:
   - While a YouTube live stream is playing, press **Ctrl+Alt+Shift+7**
     (**Video > YouTube > Live Chat...**).
   - In Browse Stations, arrow to a YouTube video, press **Shift+F10** and
     choose **Live Chat...** (H).
2. A window titled "YouTube Live Chat" opens and connects. Messages start to
   arrive at the bottom of the **Messages** list (Alt+G).
3. Arrow through the list. Each row reads who wrote it, then what they said,
   then anything special about it, such as "Sam: great show, moderator" or
   "Ann: thank you!, paid $5.00". A paid message, a member, a moderator and the
   channel's owner are all named.
4. Press **Alt+X** for **Full text** to read the selected message whole, with
   when it was sent. Web addresses are written out in full here.
5. To see only some messages, press **Alt+I** for **Filter messages** and type
   words. New messages that match keep arriving.
6. Press **Alt+Y** for **Copy Message** to copy the selected message with its
   author.
7. Press **Escape** to close the window. The chat stops, and you are back
   where you were.

For a finished stream's replay, if that same video is playing, the messages
appear as playback reaches the moment each was written, so the chat keeps in
step with what you hear.

If the chat cannot be read, you hear why once, such as "Chat is turned off for
this video." or "This video has no chat replay.", and it is listed in **Recent
Problems** (Ctrl+Alt+Shift+P). If the connection drops, Quill Radio quietly
tries again a few times before telling you.

#### Using Live Chat with a screen reader

The window is built so a busy chat never fights your screen reader:

- **New messages never move you.** They are added at the bottom without
  changing which message is selected, without moving focus and without making
  the list read itself again. You can read message 12 while 200 more arrive.
- **Following is your choice.** If you want the newest message read as it
  arrives, check **Follow new messages** (Alt+F). Then, while you are on the
  last row of the list, the selection steps down onto each new message.
  Anywhere else in the list, nothing moves. It is off to start with.
- **Pause holds everything still.** Press **Space** on the list, or check
  **Pause** (Alt+U). New messages are counted instead of added. When you
  resume, they arrive together and you hear how many came in, such as "14 new
  messages while paused."
- **Speaking new messages is off to start with.** Choose it in **Speak new
  messages** (Alt+P): every message; only paid messages, moderators and the
  owner; or only messages that mention a word you type in **Word to listen
  for** (Alt+W), such as your name. Quill Radio speaks at most once every few
  seconds, and a burst becomes one short sentence, such as "12 new messages."
  A paid message, and any message with your word in it, is still read in its
  own words. Quiet Hours silence it. **Ctrl+S** turns speaking on and off
  without leaving the list.
- **Emoji are read as words.** A smiley reads as ":grinning_face:", a row of
  the same emoji as ":face_with_tears_of_joy: x3", and a channel's own emotes
  by their names.
- **Links say they are links.** A web address in a row reads as "link
  example.com/page".

Keys in the Live Chat window:

| Action | Key |
| --- | --- |
| First or newest message in the list | Home / End |
| Previous or next message from the same person | Ctrl+Up / Ctrl+Down |
| Jump to the newest message | Ctrl+J |
| Read the newest message without moving | Ctrl+L |
| When the selected message was sent | Ctrl+T |
| Pause or resume the list | Space (on the list) |
| Speak new messages on or off | Ctrl+S |
| Move between the list, Full text and the filter | F6 / Shift+F6 |
| Close | Escape, Ctrl+W or Ctrl+F4 |

### Your own YouTube

#### Use your YouTube sign-in (My YouTube)

Everything above works without signing in to anything. If you also want your
own YouTube, such as your Home page, your subscriptions, Watch Later, Liked
videos and your playlists, Quill Radio can borrow the sign-in your web browser
already has. It is off until you turn it on.

When this is on, Quill Radio reads your browser's YouTube sign-in each time it
asks YouTube for something. It never copies, saves or logs your sign-in: it
only remembers which browser (or which cookies.txt file) to read, and YouTube
sees the same account it sees when you use that browser. Anyone who can use
your Windows account can already do this, so it opens nothing new. Turn it off
any time and Quill Radio goes back to asking YouTube as a guest.

1. Make sure you are signed in to YouTube in your web browser.
2. In Quill Radio, press **Ctrl+,** to open Preferences, and Tab to the
   **YouTube** group.
3. Check **Use my YouTube sign-in from my web browser** (Alt+N).
4. In **Read the YouTube sign-in from** (Alt+H), choose your browser:
   Microsoft Edge, Google Chrome, Mozilla Firefox, Brave, Opera or Vivaldi.
   Firefox is the most dependable choice; see the next section.
5. Choose **OK**. You should hear that My YouTube is under Browse Stations,
   YouTube.
6. Press **Ctrl+B**, open **YouTube**, and open **My YouTube**. It has:
   - **Home**: what YouTube recommends for you.
   - **Subscriptions**: **New from Your Subscriptions** (the newest videos
     from every channel you subscribe to) and **Your Channels** (the channels
     themselves).
   - **Watch Later**.
   - **Liked Videos**.
   Videos that are for members only, or that YouTube keeps for grown-ups, play
   too when your account is allowed to see them.
   - **Your Playlists**.
   - **History**: what you watched, newest first.

Every video plays on Enter, and every channel and playlist opens, just like the
rest of Browse Stations. The channels under **Your Channels** offer **Follow
This Channel in Quill Radio** too.

To use a cookies.txt file instead of a browser, export one with a browser
extension. Then, in Preferences, choose **Choose a cookies.txt File...**
(Alt+X) and pick the file, set **Read the YouTube sign-in from** to **A
cookies.txt file I choose**, and choose OK. Quill Radio reads the file each
time and never changes it.

To turn it off, uncheck **Use my YouTube sign-in from my web browser** and
choose OK. My YouTube disappears from the tree.

#### When the YouTube sign-in does not work

If something under My YouTube will not open, Quill Radio tells you why in one
sentence. The usual reasons:

- "...keeps it locked while it is open." Edge, Chrome, Brave, Opera and
  Vivaldi lock their sign-in while they are running. Close the browser
  completely and try again.
- "...protects its sign-in so that only ... itself can read it." Newer
  versions of Chrome and Edge do not let other programs read their sign-in at
  all. Choose **Mozilla Firefox** in Preferences, or use a cookies.txt file.
- "...could not find ...'s sign-in on this computer." That browser is not
  installed, or you have not signed in to YouTube in it.
- "The cookies.txt file chosen in Preferences is not there any more." Choose
  the file again, or choose a browser.
- "YouTube wants you signed in for this." Turn on the sign-in in Preferences,
  and check that you are signed in to YouTube in that browser.

### Repair YouTube Support

This is for emergencies. YouTube support is built in, but YouTube changes how
it sends its sound more often than Quill Radio has new releases.

1. Press **Ctrl+Alt+Y** (**Station > Repair YouTube Support...**).
2. You should hear "Updating YouTube support...".
3. A message tells you the new version, such as "YouTube support is now
   version ...", or that the built-in version is already the newest, or that
   it could not be updated. Press Enter to close it.

It asks before it goes online, and it is off in Safe Mode. A repaired helper is
only used while it is newer than the one built in, so a later Quill Radio
update never ends up using an older copy. You should not need this unless
YouTube links stop playing.

### What you learned, and where to go next

You can now play and keep YouTube links, search YouTube for videos, playlists
and channels, open a channel's uploads and live broadcasts, follow channels
here or subscribe on YouTube, be told about new videos, bring in playlists and
your subscriptions, move around a video, read along with its captions and
transcript, read its comments, follow a live chat, skip sponsor segments,
search with YouTube's own filters or YouTube Music, and, if you like, use your
own YouTube sign-in.
Next, Chapter 12, The ACB Media schedule and reminders, helps you catch the
programmes you care about.

## Chapter 12: The ACB Media schedule and reminders

ACB Media runs ten channels made with blind listeners in mind. This chapter
shows you how to see what is on and what is coming up, tune in, record a
programme, and have Quill Radio remind you before it starts. It finishes with
Upcoming, which brings all your plans together, and Notifications, which
remembers everything you have been told.

The tutorial **The ACB Media schedule**, in the More than radio track, walks
through it with you.

### The ACB Media schedule

**Community > ACB Media Schedule...** (Ctrl+Shift+N) lists everything ACB has
published for its ten channels, in one list, earliest first. Each row gives
the date, the start and end times, the programme and the channel, such as
"Tuesday 4 August, 8:00 AM to 9:30 AM, Herbie's Community Cooking Corner, ACB
Media 5". It opens on the next programme still to come, and the programme on
air now ends with "on now".

#### Browse the schedule, step by step

1. Press **Ctrl+Shift+N**. The ACB Media Schedule window opens. It reads the
   schedule from ACB every time it opens.
2. The first thing in the window is a summary you can read. It tells you how
   many programmes are listed, how far ahead the schedule goes, when this copy
   came from ACB (such as "Pulled from ACB just now, at 9:47 AM"), and whose
   clock the times are on. Arrow through it.
3. Tab to the filters:
   - **Search**: every word must appear somewhere, so "blues tuesday" finds the
     Tuesday blues show.
   - **Date** (Alt+D): one date. Only dates with programmes are offered, each
     with how many.
   - **Channel** (Alt+H): one of the ten channels.
   Clearing a filter brings the whole schedule back.
4. Tab to the list of programmes and arrow through it.
5. Press **Enter** to tune in to the programme's channel. The button tells you
   what it will do: **Play Now**, **Play This Channel Now**, or **Stop** when
   that channel is already playing.
6. Press **Shift+F10** for everything else you can do with a programme. The
   list's menu also has **Refresh the Schedule**, even when nothing is
   selected.
7. Press **Escape** to close.

#### What the buttons do

The buttons below the list, in order, are **Play**, **Record...**, **Remind
Me...** (reads **Remove Reminder** once one is set), **Add to Queue**, **Copy
Details**, **Show Notes...**, **Next Programme**, **Refresh** and
**Export...**. The Search box and the Show Notes button share a letter, so Tab
to reach them.

- **Play** tunes in to the channel. Live radio only has one thing on at a time,
  so Quill Radio tells you whether the programme is on now or when it starts.
- **Record...** asks you to check the channel, date, time and length, then
  books the recording. **Yes** is already chosen here. It appears in
  Recordings and Upcoming like any other scheduled recording.
- **Remind Me...** asks how much warning you want. See "Reminders" below.
- **Add to Queue** puts the channel in the play queue. When the queue reaches
  it, you hear whatever is on at that moment.
- **Copy Details** copies what, when, which channel and the description.
- **Show Notes...** reads you the programme's description.
- **Next Programme** moves to the next thing that has not finished.
- **Refresh** reads the schedule from ACB again.
- **Export...** writes what you are looking at, with your filters, to a
  Markdown file.

Anything that cannot be done is dimmed and tells you why. For example, a
programme that finished this morning cannot be recorded.

**Why the list can look short.** ACB publishes two weeks of listings at a time
and then stops. So for part of every month, nothing is listed for today. The
summary tells you plainly, such as "Nothing is published for today or later --
ACB last posted a schedule through 15 August." Nothing is broken. Press
**Refresh** once ACB posts more.

**Times are shown on your own clock.** ACB publishes in US Central time, and
Quill Radio changes every programme to your time. When the two differ, the
summary tells you, such as "Times are shown in US Mountain Standard Time. ACB
publishes in US Central time."

ACB sometimes lists the same programme twice. Quill Radio shows it once.

#### What Is On Now, and Refresh the Schedule

These two answer without opening a window.

**What Is On Now** tells you, in one sentence, what is on across all ten ACB
Media channels.

1. In the main window, press **Ctrl+Alt+H** (**Community > What Is On Now**).
2. You hear what is on now, channel by channel. Nothing opens and your cursor
   does not move.
3. To tune in to one, press **Ctrl+Shift+N** for the schedule, where the
   programme on now ends with "on now", and press **Enter** on it.

It answers from the schedule already on your computer, so it is instant and
works without the internet.

**Refresh the Schedule** fetches the newest listings from ACB.

1. In the main window, press **F5** (**Community > Refresh the Schedule**). In
   the schedule window itself, use its **Refresh** button.
2. If the schedule window is open, the list reloads where it is. If it is
   closed, the schedule is fetched quietly and you hear the result.

Good to know: these keys belong to the main window's Community menu. In
another Quill Radio window, press **Ctrl+Tab** until you are back in the main
window first. In Browse Stations, the **Refresh** button reloads a source, not
the schedule.

#### Working offline

The schedule is kept on your computer. With no internet, the window opens with
what it has and tells you how old it is. If the schedule cannot be read at
all, you get an empty list and a sentence saying so, and the reason goes into
Recent Problems. On the first of a month, before ACB has posted the new one,
the window shows the previous month's listings, and the summary tells you how
far they go.

### Reminders

Any programme in the ACB Media schedule, and any station, recording or saved
row in Browse Stations, can have a reminder.

#### Set a reminder, step by step

1. Highlight the row and press **Shift+F10**. Choose **Set a Reminder...** (in
   the schedule, it is **Remind Me...**). The Set a Reminder window opens:
   "Remind me about" and the title.
2. **When** (Alt+W): for a programme, how much warning you want, from "When it
   starts" to "1 day before". For a station or recording, when to remind you,
   counting from now: In 15 minutes, In 30 minutes, In an hour, In 3 hours, or
   Tomorrow, at this time.
3. **Note (optional)** (Alt+N): anything you want said with the reminder. It
   never leaves your computer.
4. **Priority** (Alt+P): Normal or High. A High reminder is the only kind that
   comes through quiet hours on its own. It is not louder, sooner or repeated.
5. Choose **OK**. You should hear "Reminder set for", the title and when.

Once a row has a reminder, the same place on its menu reads **Remove
Reminder**.

**When a reminder comes due**, Quill Radio plays the reminder sound (three
rising bell tones), tells you what it is and when it starts, and shows a
notification with a **Go There** button. If a reminder came due while Quill
Radio was closed, you still hear it when you next open it, as long as that is
within a couple of hours. Quiet hours can hold a reminder back; you hear it
when the quiet time ends.

In Preferences, **New reminders start at** sets how much warning you usually
want, and **Play a sound when a reminder comes due** turns the sound off. You
still hear the reminder spoken either way.

### Upcoming, step by step

**Community > Upcoming...** (Ctrl+Alt+Shift+F) lists everything Quill Radio
has planned: your reminders and your scheduled recordings, together, soonest
first. Each row starts with what kind it is, "Reminder:" or "Recording:".

1. Press **Ctrl+Alt+Shift+F**. Upcoming opens. A summary is at the top, and
   your cursor is in **What is coming up** (Alt+W).
2. Arrow through the list.
3. Press **Enter**, or choose **Go There** (Alt+G), to open what the row is
   about. A recording opens **Schedule Recording**. A programme opens the
   **ACB Media Schedule**. A station reminder tunes in. Then Upcoming closes.
4. On a reminder, **Snooze...** (Alt+S) puts it off by 5, 10 or 30 minutes from
   now. **Dismiss** (Alt+D) forgets it.
5. Press **Escape** to close.

Snooze and Dismiss only work on reminders. To change or cancel a scheduled
recording, use Schedule Recording, where Delete removes it straight away.

### Notifications

A notification pops up, says its piece and goes away, and if your screen
reader was in the middle of a sentence, you might never have heard it. So
Quill Radio keeps a list of everything it has told you this way, such as new
podcast episodes and reminders, and you can read it whenever you like.

1. Press **Ctrl+Alt+Shift+F3** (**Help > Notifications...**). The
   Notifications window opens with your cursor in the list, newest first.
2. Arrow through it. Each row is one line: the word "New" if you have not read
   it yet, which app said it, what it said, and how long ago.
3. Press **Enter**, or choose **Open**, to go to what the notification was
   about, such as the podcast it names or the station a reminder was set on.
   If there is nothing to open, Quill Radio tells you.
4. **Mark All as Read** takes the word "New" off every row. Nothing is
   removed.
5. **Clear List** empties the list. It only removes the record of being told,
   never the episodes or stations themselves.
6. Press **Escape** to close.

QUILL Cast shares the same list, so whichever app you have open can show you
what the other one found.

### What you learned, and where to go next

You can now browse the ACB Media schedule, tune in, record a programme with a
couple of key presses, and set reminders so you never miss the ones you love.
Upcoming shows you everything you have planned, and Notifications keeps
everything you have been told. Next, Chapter 13, The Community menu, has the
rest of what is on that menu, including Ask QUILL Radio. The tutorial
**Sleeping, waking, and being left alone** touches on reminders and quiet
hours too.

## Chapter 13: The Community menu

The Community menu (Alt+C) is where Quill Radio connects you with other
listeners and with a helpful assistant. This chapter covers Ask QUILL Radio,
signing in with your ChatGPT plan, ACB Media's podcasts, Community Picks, and
how to suggest a station or podcast for everyone to enjoy. The ACB Media
schedule, which is on this menu too, has Chapter 12 to itself.

The tutorial **Community Picks, and suggesting one**, in the More than radio
track, goes with this chapter.

### Ask QUILL Radio: a conversation that knows what is playing

Ask QUILL Radio is the radio's own assistant. It runs on the ChatGPT plan you
already pay for, so there is no key to paste and no charge per question. And
it knows one thing ChatGPT on the web does not: **what you are listening to**.
The station and the title the stream is announcing go with every message, so
you can ask about them without typing any names:

- "What is this song, and who made it?"
- "Tell me more about the artist playing now."
- "Tell me about this station: who runs it, where, and what it plays."
- "What kind of programmes does this station broadcast, and when?"
- "Is there a podcast like this one?"
- "This presenter mentioned a book. What was it?"
- "What was the news story they just referred to?" (with web search allowed)
- "Explain the rules of the sport they are commentating on."
- "This is in Spanish. What are they talking about?"

It is a conversation, so you can follow up with "and where can I hear more of
them?" and it knows what you mean. Nothing you ask changes what is playing.

**It works from words, not from sound.** Ask QUILL Radio never listens to the
stream, records anything or turns speech into text. It only knows what Quill
Radio already knows in words: the station's name, and the title the stream
sends, when it sends one. If a station sends no titles, the assistant knows the
station but not the song, and tells you so. If you ask about something a
presenter just said, the answer comes from what the assistant knows about the
programme, not from hearing it.

**Before your first question, sign in.** Ask QUILL Radio only works with your
own ChatGPT plan: Plus, Pro, Team or Enterprise. See "Use My ChatGPT
Subscription, step by step" below. If you have not signed in, Ctrl+Shift+8
tells you so and opens that window instead.

#### Ask QUILL Radio, step by step

1. Play something if you like. It answers either way; it just knows more with
   a station on.
2. Press **Ctrl+Shift+8** (**Community > Ask QUILL Radio...**). The Ask QUILL
   Radio window opens with your cursor in **Your message**. It is a window of
   its own, on the Window menu and one Ctrl+Tab away, and the playing keys
   still work in it.
3. **What it knows**, one Shift+Tab back, tells you what is on right now, which
   model will answer, and whether web search is allowed. It is worth reading
   once.
4. Type a question and press **Enter**. You hear "Working.", then the reply is
   read aloud as it arrives. It is also added to **Conversation**, the box
   above, where you can read it again word by word.
5. Or press **Ask About What's Playing** (Alt+P) without typing anything. It
   asks about the song and the station for you, and each press asks the next
   suggested question.
6. **New Conversation** (Alt+N) starts again. **Copy Last Reply** (Alt+L) puts
   the latest answer on the clipboard. **ChatGPT Account** (Alt+G) opens the
   sign-in window. **Escape**, **Ctrl+W** or **Close** closes the window.

#### Quick questions

Above Your message is a **Quick questions** list (Alt+Q). Arrow through it as
much as you like; nothing happens until you press **Enter** on the one you
want, or choose **Use This Question** (Alt+T). The question is then put in
the message box for you to send as it is or change, your cursor moves there,
and the Status line tells you what else, if anything, will go with it. Six of
them ask about what is playing and send nothing more:

- What is this song?
- Tell me about the artist playing now
- Tell me about this station
- What does this station broadcast, and when?
- Is there a podcast like this station?
- What is the title now playing about? (it translates a title in another
  language)

Three of them ask about *you*, and each one tells you, before you send it,
exactly what it will attach and how much:

- **Recommend stations like my favorites** sends the names of your favorite
  stations and their folders, up to sixty, and asks for five you do not have.
- **What have I been hearing on this station lately?** sends the songs Quill
  Radio has noted on the station playing, up to twenty-five, and asks what
  they add up to.
- **Suggest something new from everything I have played** sends the names of
  the stations you have played recently, with a few songs from each, and asks
  for three stations or podcasts that would be new to you.

Nothing about you is sent unless you choose one of those three, and nothing is
sent at all until you press Enter. Each question is one request on your plan,
made when you ask and never on a timer.

Good to know: Ask QUILL Radio needs the internet, and it is off in Safe Mode.
What you ask counts towards your ChatGPT plan's own limits, which OpenAI sets.
If you reach a limit, the window tells you in words, and **Open ChatGPT
Usage** in the account window shows when it resets.

### Use My ChatGPT Subscription, step by step

1. Press **Alt+F5** (**Community > Use My ChatGPT Subscription...**). The window
   opens on **About this**, which tells you where your questions go and what
   it costs. Read it once.
2. Tab to **Continue with ChatGPT** and press it. Your browser opens on
   OpenAI's own sign-in page.
3. Sign in to ChatGPT there. When the page asks whether **QUILL Radio** may use
   your plan, allow it. That is the name you will see under Apps in ChatGPT's
   settings from now on.
4. Come back to Quill Radio. The window says "Signed in with ChatGPT as" and
   your email address, and your cursor is on **Model**, a list of every model
   your plan offers, read from your account. The first one is chosen for you;
   arrow to another and it is saved as soon as you land on it. **Refresh
   Models** reads the list again.
5. **Allow web search** (Alt+W) starts off. Press **Alt+W**, then **Space**,
   and you hear "Web search is allowed." With it on, the assistant may look
   things up on the web through OpenAI, such as a station's schedule, a news
   story a presenter mentioned, or a new album, and tell you what it found. It
   is saved as soon as you change it, and Space again turns it off.
6. **Open ChatGPT Usage** (Alt+U) opens your plan's usage page in your
   browser. **Sign Out** (Alt+O, press it twice) asks OpenAI to cancel Quill
   Radio's sign-in and forgets it here. **Forget on This Computer** (Alt+F)
   only forgets it here, which is handy on a computer with no internet or for
   a sign-in you already removed in ChatGPT's settings. Both only appear while
   you are signed in.
7. Press **Escape** to close.

If the browser did not open, the window tells you and offers **Copy the
Sign-In Address**. Paste it into any browser on this computer and finish
there. **Stop Waiting** gives up without changing anything.

Good to know: Quill Radio never sees your ChatGPT password. It only keeps a
sign-in pass from OpenAI, in the Windows credential store, under Quill Radio's
own name. Each QUILL app signs in as itself, so Quill Radio, QUILL Lite and
QUILL each appear under Apps in ChatGPT's settings, and signing one out leaves
the others alone. There is no free QUILL AI service behind Ask QUILL Radio and
no key to paste: it is your plan or nothing, and the window tells you so.

### ACB Media Podcasts, step by step

1. Press **Ctrl+Alt+I** (**Community > ACB Media Podcasts...**). Quill Radio
   fetches ACB's list of podcasts, then the window opens.
2. Your cursor is in the **Available** list. Arrow through it. The
   **Description** box below tells you what the highlighted show is about.
3. Press **Enter** or **Space** to add the highlighted show to **What you are
   adding**. **Add All** adds every one.
4. In What you are adding, **Move Up**, **Move Down**, **Remove** and **Sort A
   to Z** arrange your choices. Enter or Space on one of your choices removes
   it.
5. Choose **Add These** (Alt+T). The shows are followed or added to your
   favorites, and Quill Radio tells you what it did.
6. Press **Escape** to close without adding anything.

### Community Picks, step by step

**Community > Community Picks...** (Ctrl+Alt+0) is a list of stations and
podcasts that listeners have suggested and Community Access has checked. Use
it when you would like a few good places to start, chosen by people rather
than by a directory's ranking.

1. Press **Ctrl+Alt+0**. You hear "Reading the Community Picks list...", then
   the Community Picks window opens.
2. Your cursor is in the **Available** list. Arrow through it. The
   **Description** box, the next Tab stop, tells you what the highlighted pick
   is.
3. Press **Enter** or **Space** to put the highlighted pick in **What you are
   adding**, or Tab to the **Add** button. You hear "Added" and the name. **Add
   All** adds every one.
4. In What you are adding, use **Move Up**, **Move Down**, **Remove** and
   **Sort A to Z** to arrange your choices.
5. Press **Alt+T** for **Add These**, or Tab to it and press **Space**.
   Stations go into your favorites and podcasts are followed. Quill Radio
   tells you what it did.
6. Press **Escape**, or choose **Close**, to leave without adding anything.

Good to know: the list is fetched fresh each time, and checked to make sure it
really came from Community Access. If it cannot be fetched, or the check
fails, Quill Radio uses the copy that came with it instead, and notes why in
Recent Problems. Anything already in your library tells you so, rather than
being added twice.

### Suggest a Station or Podcast, step by step

Know a station or podcast other listeners should hear? Suggest it for the
Community Picks list. Your suggestion goes by email to
**support@community-access.org**, where a person at Community Access reads it.
You do not need an account of any kind, and nothing is posted on a website.

#### What the window asks

1. Press **Ctrl+Alt+9** (**Community > Suggest a Station or Podcast...**). The
   Suggest a Station or Podcast window opens. At the top, it tells you where
   the suggestion goes, and that nothing is sent until you press Send in your
   email program.
2. **What is it** (Alt+W) is a list with two choices, **A radio station** or
   **A podcast**. Use the Up and Down Arrow keys. It starts on A radio station.
3. **Name** (Alt+N): what it should be called in the list, such as "Radio
   Nowhere". You must fill this in, and it can be up to 120 characters.
4. **Address** (Alt+A): the stream address for a station, or the feed address
   for a podcast. You must fill this in, and it must start with `https://` or
   `http://`. The easy way to get it: in Quill Radio, press **Shift+F10** on the
   station and choose **Copy Stream Link**, or on a podcast show choose **Copy
   Feed Address**, then paste it here with **Ctrl+V**.
5. **Description** (Alt+D): a sentence or two saying what it is, for someone
   who has never heard it. Optional, up to 600 characters. Press **Tab** to
   leave this box, because Enter starts a new line.
6. **Language** (Alt+L): such as `en` or `en-US`. Optional.
7. **Why it belongs** (Alt+H): anything that would help Community Access
   decide. Optional. Only the people who read your suggestion see it.

#### Sending it

1. Press **Alt+S** for **Send Suggestion**, or Tab to it and press **Space**.
2. Quill Radio checks what you typed first. If something needs fixing, it
   tells you the first problem and shows the whole list in a message. Press
   **Enter** to close the message, fix the field, and press **Alt+S** again. It
   catches a missing name or address, an address that does not start with
   `https://` or `http://`, an address with a space in it (usually something
   that did not paste in full), and a station or podcast that is **already in
   the Community Picks list**.
3. When everything is in order, your own email program opens with a new email
   already written, and you hear "Your mail program has opened with your
   suggestion written. Press Send there." The Suggest window closes.
4. In your email program, the email is addressed to
   support@community-access.org, with a subject such as "[Quill Radio 3.0.3]
   Suggestion: Radio Nowhere". Read it over if you like, add anything you want
   to say, and **press Send there**. Nothing leaves your computer until you do.

#### If you have no email program

Some computers have no email program set up, only webmail such as Gmail or
Outlook.com in a browser. Then nothing can open, and Quill Radio tells you:
"No mail program answered. Write to support@community-access.org." The whole
suggestion, with the address and the subject at the top, is put on your
clipboard. Open your webmail, start a new email to
**support@community-access.org**, and paste it in with **Ctrl+V**. The Suggest
window stays open, so what you typed is still there.

If a suggestion is too long for an email program to accept (usually a very
long "Why it belongs"), it is shortened in the email, with a line saying so,
and the full text is put on your clipboard. Quill Radio tells you when this
happens; select the email's text and paste the full version over it with
**Ctrl+V**.

#### What is included, and what is not

- Included: exactly what you typed, whether it is a station or a podcast, and
  the app's name and version ("Quill Radio 3.0.3").
- Not included: your name, your Windows version, your screen reader, your
  favorites or listening history, or any file from your computer.
- Because the email comes from your own email account, Community Access sees
  the address you send it from, as with any email you write. It is not
  published anywhere.
- Nothing goes to GitHub or any other public website, and Quill Radio itself
  does not send anything: your email program does the sending.

#### What happens next

A person at Community Access reads every suggestion. If it fits the list, they
add it, and it appears in **Community Picks** for everybody the next time the
list is fetched, with no update needed. They may write back to ask a question
or to let you know it was added.

#### Closing without sending

Press **Escape**, or choose **Close** (Alt+O). Nothing is written or sent.

Suggest a Station or Podcast is off in Safe Mode, and tells you "Safe Mode is
on, so nothing is sent anywhere."

### What you learned, and where to go next

You can now ask Quill Radio's assistant about whatever is playing, sign in with
your ChatGPT plan and choose a model, add ACB Media's podcasts, pick up
stations other listeners recommend, and suggest your own favorites for
everyone. Next, Chapter 14, Making Quill Radio yours, shows you how to change
settings and keys so the app fits you like a glove.

## Chapter 14: Making Quill Radio yours

Quill Radio works well straight away, but it is happiest when it fits the way
you listen. This chapter walks through Preferences, the one setting most
people never touch but might like to, the order of your menus and lists, your
keys, the Command Palette, quiet hours, and Quillins.

The tutorials in the **Making it yours** track go with this chapter, especially
**The settings actually worth changing**, **Make the keys yours**, **Decide
what a row says, and what its menu offers first** and **Quillins: extensions
in a radio**.

### Preferences

**Station > Preferences...** (Ctrl+,) opens **Quill Radio Preferences**, one
page of settings. Every setting takes effect the moment you choose OK. If you
change the playback engine or the output device while something is playing, it
reconnects straight away.

#### Change a setting, step by step

1. Press **Ctrl+,**. Quill Radio Preferences opens on its first setting.
2. Press **Tab** to move through the settings. Each one's name tells you what
   it does, and **F1** on any of them tells you more.
3. For a drop-down list, press **Alt+Down Arrow** to open it, or just arrow
   through the choices where you are.
4. For a checkbox, press **Space**.
5. Choose **OK** (Enter) to save. You should hear "Preferences saved." Escape
   cancels.

#### The drop-down lists

These come first:

- **Main window shows**: Favorite stations (where it starts), Browse
  Stations, Search Stations, Radio Recordings or Player. See "What the main
  window shows" in Chapter 3.
- **When closing the window**: Ask every time (where it starts), Exit, or
  Minimize to Tray. This decides what the title bar's close button and Alt+F4
  do. See "Closing Quill Radio" in Chapter 3.
- **Playback engine**: the list only shows the engines this copy actually
  has. With the mpv engine there, you can choose Automatic (recommended, which
  uses mpv), Windows Media, or mpv. Without it, there is no mpv choice, and
  Automatic reads "Automatic (uses Windows Media; mpv is not installed)", so
  what you see is what you get. Automatic with mpv gives you rewinding live
  radio, Volume Boost and more kinds of stream. Choosing an output device
  works on either engine. You only see "Windows Media (classic)" on a computer
  without Windows' modern media player, and that is the older player Quill
  Radio used before version 1.1.
- **Radio output device**: System default, or a sound card or headset. Only
  the radio moves; your screen reader and Quill Radio's own sounds stay on the
  system default. If a device cannot be opened, the setting goes back to what
  it was and Quill Radio tells you. This is the same setting as **Audio >
  Output Device...**. It works with the mpv engine and with Windows Media.
  Only on a computer that has fallen back to the classic player does the
  device come from Windows' Sound settings instead. See "Output Device, step
  by step" in Chapter 5.
- **Favorites sort order**: Ascending (A to Z, where it starts), Descending (Z
  to A), or Unsorted (manual order).
- **Station catalog update frequency**: Every 6 hours, Every 12 hours, Every 24
  hours (where it starts), Every 2 days, or Manually only.
- **Episodes listed per subscribed podcast**: 10, 25 (where it starts), 50,
  100 newest, or All episodes.
- **Interrupted recordings at launch**: Ask each time (where it starts),
  Always resume them, or Never resume them. See "If a recording was in
  progress when Quill Radio quit" in Chapter 8.

#### The checkboxes

Each one is listed with how it starts:

- **Resume Last Station on Launch**: off.
- **Check for updates automatically on launch**: on. A quiet check once a day,
  which says nothing unless it finds something.
- **Announce dialog transitions (more spoken detail)**: off. When it is on,
  Quill Radio says "Entered ..." and "Exited ..." as windows open and close.
- **Share these choices with my other Quill apps**: off. When it is on,
  Announce dialog transitions is kept the same in Quill Radio and every other
  Quill app that has this turned on too, such as QUILL Cast. Quill Radio tells
  you when it picks up a choice from another app. Nothing about your keys,
  your cursor or your screen reader is ever shared.
- **Recover failed streams from the station's website**: on.
- **Share play counts with the RadioBrowser directory**: on. See "What Quill
  Radio connects to" in Chapter 15.
- **Alt+F4 minimizes to the system tray**: off. When it is on, Alt+F4 tucks the
  radio into the tray, still playing.
- **Verbose logging (debug mode)**: off. Keeps a much more detailed log, to
  help track down a problem. It works at once, with no restart.
- **Keep the computer awake while playing or recording**: on. Windows does not
  go to sleep while a station plays or a recording runs. The screen can still
  turn off.
- **Keep the computer awake before a scheduled recording**: on. Stops Windows
  sleeping in the few minutes before a recording is due.
- **Wake the computer for a scheduled recording**: on. If the computer is
  asleep when a recording is due, Windows wakes it a couple of minutes early.
  This adds a task to Windows Task Scheduler. In a portable copy it is dimmed,
  with the reason.
- **Keep a local station catalog on this computer**: on. Turning it off goes
  back to live browsing only, with nothing stored.
- **Check for station catalog updates when Quill Radio starts**: on.
- **Winamp-style playback keys in the Recordings player**: on. See "Winamp keys
  in Radio Recordings" in Chapter 8.

#### Text boxes, buttons and groups

Two text boxes:

- **What's Playing announcement**: the pattern for what What's Playing says.
  `{title}` and `{artist}` are the song and the artist. Words inside `[square
  brackets]` disappear when the part inside is empty. `{raw}` is exactly what
  the stream sent. It starts as `{title}[ by {artist}]`. Leave it blank to go
  back to that.
- **Log folder**: where the log is written. Leave it blank for the usual place.
  Changing it moves the log straight away.

Two buttons:

- **Reset All Stations' Sound Enhancements...** puts every station's own Sound
  Enhancements back on the shared settings.
- **Data Folder...** chooses where every Quill app keeps its settings,
  favorites, subscriptions and places in episodes. Point it at a folder that
  Dropbox, OneDrive, Google Drive or iCloud keeps in step, and your setup
  travels between your computers. The change takes effect the next time an app
  starts; Quill Radio offers to restart, and moves your things for you.
  Things that are easy to fetch again, such as the station catalog, stay on
  each computer. Do not use Quill apps on two computers with the same folder
  at the same time. If you do, the next launch tells you.

Three groups:

- **Podcasts**: **Check subscribed podcast feeds** (Manually only, where it
  starts, through every 15 minutes up to once a day), and **Check subscribed
  podcast feeds at launch** (off). See "Checking your subscribed podcasts" in
  Chapter 9.
- **Reminders**: **New reminders start at** (15 minutes before, to begin
  with), and **Play a sound when a reminder comes due** (on).
- **YouTube**: **Use my YouTube sign-in from my web browser** (off), **Read
  the YouTube sign-in from** (Mozilla Firefox, to begin with), and **Choose a
  cookies.txt File...**. See "Use your YouTube sign-in (My YouTube)" in
  Chapter 11, which also says plainly what turning it on means for your
  privacy.

#### Finding a setting by typing

Preferences has a **Find a setting** box, so you don't have to hunt for a
checkbox. Type a word from a setting's name or its help, press Down
Arrow to go through the matching settings, then Enter to go to one. Ctrl+F takes you back to the search, and
Escape clears the search before it closes the window. It only finds settings;
it does not change them. OK still saves, Cancel still cancels, and the values
you have chosen are not searched. Settings that are dimmed stay dimmed.

### Customize Features, step by step

If you never record, you can switch the Record menu off so there is less to
arrow past.

1. Press **Ctrl+Alt+C** (**View > Customize Features...**). The window
   "Customize Quill Radio Features" opens.
2. **Search features** filters the list. There is one area: **Enable
   Recording**, which covers the Record menu.
3. Press **Space** to uncheck it, then choose **Save**.
4. You should hear "Feature settings saved. Menu changes take effect the next
   time you open Quill Radio."

Nothing is deleted, and checking it again brings the menu back. The tray and
status bar menus still offer Record Now, Schedule Recording and Recording
Settings either way.

### Quick Actions

**Station > Quick Actions...** (Ctrl+Alt+Q) sets the order of the actions on
the Browse Stations Shift+F10 menu, so the ones you use most are at the top.
Enter on a row still does what it always did.

1. Press **Ctrl+Alt+Q**. The Quick Actions window opens.
2. **Actions for** (Alt+F) chooses which list: **Station actions** (rows you
   play) or **Browse folder actions** (folders).
3. Tab to **Order (first is at the top of the menu)** (Alt+O). Arrow to an
   action. The line below tells you what it does and where it is.
4. Press **Alt+Up** or **Alt+Down** to move it, or Tab to **Move Up** (Alt+U),
   **Move Down** (Alt+D) or **Move to Top** (Alt+T). Quill Radio tells you its
   new number.
5. **Reset This List** (Alt+R) puts the chosen list back the way it came. The
   other list is left alone.
6. Choose **OK** (Enter). You should hear "Quick Actions saved." Escape
   cancels.

It only changes the order of what a row already offers; it never adds
anything. A station already in your favorites still offers Remove, not Add,
and a live stream still offers no Download.

### What each row says

Your screen reader reads a list one column at a time, so the columns are the
sentence you hear on every row. **View > Choose Columns...** (Ctrl+Alt+Shift+C)
lets you decide that sentence for the Find Stations results and the Radio
Recordings list.

1. Press **Ctrl+Alt+Shift+C**. The Choose Columns window opens.
2. **Columns for** (Alt+F) chooses the list: Find Stations or Recordings.
3. Tab to **Shown, in the order they are read** (Alt+S). Arrow to a column.
4. Press **Alt+Up** or **Alt+Down** to move it, or use **Move Up** (Alt+U) and
   **Move Down** (Alt+D).
5. **Hide** (Alt+I) takes a column out of the row altogether. It moves to
   **Hidden (not read out at all)** (Alt+H). Select one there and choose
   **Show** (Alt+W) to put it back in its proper place.
6. **A row will read** (Alt+A) spells out the sentence one row will say with
   your choices, so you can hear the difference before you save.
7. **Reset This List** (Alt+R) puts the chosen list back the way it came.
8. Choose **OK**. You should hear "Columns saved."

One column in each list always stays, the station's name or the recording's
name, because a row with nothing to say what it is cannot be used. If you try
to hide it, Quill Radio tells you why not.

Some columns are there but start switched off. Find Stations can also show
**Language**, **Genres**, **Popularity** and **Bitrate**. Recordings can also
show **Length**, which is blank when the only number known is the safety
limit.

If the Find Stations window is already open, close it and open it again to
see your new columns.

### Your keys, your way

#### Keyboard access without chords

You can reach every command in Quill Radio without holding several keys down
at once. That matters on a braille notetaker such as the BrailleNote Evolve,
and for anyone who finds a three- or four-key combination hard.

- **Every menu is one Alt+letter away, and every item in it has a letter of
  its own.** Press Alt and the menu's letter, then the item's letter: **Alt+Q,
  then W** opens Quill Weather; **Alt+S, then B** opens Browse Stations. That
  is two keys, one after the other. A few items share a letter: press it again
  to move to the next item with that letter, and press Enter to choose it. The
  Station menu has more items than there are letters, so four of its items
  have a key but no letter: **Preferences** (Ctrl+comma), **Exit** (Ctrl+Q),
  **Connect to Spotify** (Ctrl+Alt+P) and **Browse Spotify** (Ctrl+Alt+O).
  Every other item has its letter.
- **You can change any key.** **Help > Keyboard Shortcuts...** (Ctrl+Alt+K)
  lists every command, including the QuillVille "Open" commands, and you can
  give any of them a shorter key, or one your notetaker can type. The menus
  show your key from then on.
- **The Command Palette** (Ctrl+Shift+P) finds any command when you type part
  of its name and press Enter.
- **The menus themselves always work**: Alt, then the arrow keys and Enter, one
  key at a time.
- **Windows' Sticky Keys** lets you type a key combination one key at a time.
  Press Shift five times to turn it on.

#### Change a key, step by step

**Help > Keyboard Shortcuts...** (Ctrl+Alt+K) opens the Keymap Editor, a list
of every command and its key that you can search.

1. Press **Ctrl+Alt+K**. The Keymap Editor opens with your cursor in
   **Search** (Alt+S).
2. Type part of a command's name, such as `record`. Or type a key, such as
   `Ctrl+B`, to see what it does. **Record Keys...** (Alt+R) lets you press the
   key instead of typing its name.
3. Tab to the **Keyboard shortcuts** list and arrow to the command.
4. Choose **Edit Keybinding...** (Alt+E). A box opens with the current key.
5. Type the new key, such as `Ctrl+Shift+K`, and choose **OK**.
6. If that key is already used, or is a risky one such as a plain letter,
   Quill Radio warns you and tells you which command has it.
7. Choose **OK** to close the editor. The menus show your new key straight
   away.

Your keys are shared with QUILL and QUILL Cast, so a key you change here
changes there too. A few keys, such as Preferences on Ctrl+, and the playing
keys, keep their old key until you next open Quill Radio. Quill Radio's own
keys are set up so they never clash with QUILL's editor keys.

#### The Keyboard Shortcuts Sheet, step by step

**Help > Keyboard Shortcuts Sheet...** (Ctrl+Alt+Shift+K) lists every key
Quill Radio answers to, and you can filter it.

1. Press **Ctrl+Alt+Shift+K**. Your cursor is in **Filter (a key, or what you
   want to do)** (Alt+F). You should hear how many shortcuts are listed.
2. Type what you want to do, such as `record`, or a key you cannot place, such
   as `Ctrl+B`. The list gets shorter as you type.
3. Press **Enter** to move into the list, and arrow through it. Each row tells
   you the key, what it does and where it works.
4. **Copy All** (Alt+C) copies the list as it is filtered. **Change
   Shortcuts...** (Alt+S) closes the sheet and opens the Keymap Editor.
5. Press **Escape** to close.

The sheet is made from the menus you actually have, so it shows your keys.
Keys that have no menu item, such as F6 into the status bar, the Winamp letters
in Radio Recordings and Shift+F10 on a row, are listed too.

#### Global Hotkeys, step by step

A global hotkey works even while another program has focus.

1. Press **Ctrl+Alt+G** (**Help > Global Hotkeys...**). A list of commands
   opens, each with its global key, or none.
2. Arrow to a command, such as **Radio: Play/Pause**, **Radio: Stop**, **Radio:
   Mute/Unmute**, **Radio: Volume Up** or **Radio: Volume Down**.
3. Choose **Assign...** (Alt+A) and give it a key. The first time, Quill Radio
   reminds you that a key that works everywhere may take over the same key in
   another program.
4. **Clear** (Alt+L) removes a global key.
5. Choose **Save** to keep your changes, or **Cancel**.

None are set up to begin with. The list is shared with QUILL, so it also shows
rows such as New Sticky Note and Podcasts: Play/Pause, which do nothing in
Quill Radio. Its first row, "Show/Hide QUILL to the tray", shows or hides
Quill Radio when you set it here. Only safe playing and window commands can
have a global key. A key another program already uses is left alone.

Quill Radio's own show-and-hide key, **Ctrl+Alt+Shift+R**, is always on and is
not in this list. See "The system tray" in Chapter 3.

### The Command Palette

**Ctrl+Shift+P** opens the Command Palette from any Quill Radio window. It
lists every command by name, so it is the answer whenever you cannot remember
a key or a menu.

1. Press **Ctrl+Shift+P**. Your cursor is in the search box, and you hear how
   many commands there are.
2. Type a few letters of what you want.
3. Arrow to a command. Each one tells you its key.
4. Press **Enter** to run it. Escape closes the palette.

A command that cannot run right now tells you why. A setting you can switch on
and off tells you how it is set, such as "Announce Track Titles (currently
On)". Some commands are only here: Copy What's Playing, Next Station in
Folder, Previous Station in Folder, Extend Sleep Timer 5 Minutes, Cancel Sleep
Timer, Quiet Hours On/Off, Repeat Last Announcement, Announcement
Self-Test... and Redeem Unlock Code....

### Quiet hours

**Help > Quiet Hours...** (Ctrl+Alt+Shift+Z) sets a stretch of time, 22:00 to
07:00 to begin with, when Quill Radio stops speaking up on its own. It is
perfect for a radio by the bed.

1. Press **Ctrl+Alt+Shift+Z**. The Quiet Hours window opens.
2. Check **Quiet hours on** (Alt+Q) with Space.
3. Choose **From** (Alt+F) and **To** (Alt+T), in half hours. The time can go
   past midnight.
4. Check **Let reminders through anyway** (Alt+R) if you want every reminder
   to speak during quiet hours.
5. A line below tells you what your setting will do. Choose **OK**.

What it means, exactly:

- Feeds are still checked, downloads still run and recordings still record.
  Only the announcements about them wait.
- **Anything you press a key for still answers.** Press Play at three in the
  morning and you hear what is playing.
- Failures always speak.
- A High priority reminder comes through on its own.

Quiet hours are shared with the other Quill listening apps, so you only set
them once. **Quiet Hours On/Off** in the Command Palette switches them
quickly.

### Quillins in Quill Radio

Quillins are small add-ons for QUILL that are kept safely apart from the rest
of the app. Each Quillin says which apps it is for, so only the ones made for
Quill Radio load here. They load and add things in this release, for example
the Radio Community Directory that comes with Quill Radio, which adds a
directory to Find Stations and a branch to Browse Stations.

The Quillins menu itself is not in this release, so there is nothing to
install or set up from Quill Radio. What a bundled Quillin adds simply appears
where it belongs. Quillins are off in Safe Mode, which is one way to tell
whether a problem comes from one.

#### Quillin station sources

A Quillin can add a whole source of stations. When one is installed and
switched on, a **Quillin Sources** branch appears in Browse Stations, with one
folder for each source. Its stations play, become favorites and can be
searched like any others. When there is none, the branch is not there.

### What you learned, and where to go next

You have been through every setting in Preferences, switched off what you do
not need, put the actions and columns you use most first, and learned how to
change any key, see them all on one sheet, and reach any command by name. You
also know how quiet hours give you peace when you want it. Next, Chapter 15,
Safety nets, shows you the ways Quill Radio catches you when something goes
wrong. The tutorial **Make the keys yours** is a friendly way to practise
changing a key.

## Chapter 15: Safety nets

Everybody presses the wrong thing sometimes, or misses something Quill Radio
said. This chapter shows you how to take back what you did, why an item is
dimmed, where to find a failure you missed, how to hear the last result again,
and exactly what Quill Radio connects to. Knowing these are here makes it much
easier to explore without worrying.

The tutorial **Getting unstuck**, in the Your first hour track, and **The help
that comes with it**, in the Living with it track, cover much of this chapter.

### Taking back the last thing you did

Removed something by mistake? Press **Ctrl+Z** in the main window (**Edit >
Undo Last Action**) and the last thing you removed or cleared comes back: a
podcast you stopped following, a Remove All Downloads, a Mark All as Played,
or a deleted recording. Quill Radio tells you what it brought back, such as
"Undid Unfollow. Brought back The Daily, with 412 episodes and 3 downloaded
files."

1. Do something you regret, such as deleting a recording in Radio Recordings.
   What Quill Radio says ends with "Ctrl+Z undoes this".
2. Press **Escape** or **Ctrl+Tab** until you are back in the main window.
3. Press **Ctrl+Z**. You hear what came back.
4. If there is nothing to take back, you hear "Nothing to undo".

Good to know:

- **Ctrl+Z goes back one step at a time, newest first.** Press it again and it
  takes back the one before, up to ten steps.
- **Undo History lets you pick one.** **Edit > Undo History** (Ctrl+Alt+Shift+A)
  lists the last ten things you can take back, each one telling you what
  undoing it would bring back. Choose one and press **Undo This One**: only
  that one comes back, and the others stay as they are.
- **Deleted files come back.** A file Quill Radio deletes for you is moved
  aside first, so undo can put it back. After ten newer steps, the oldest one
  is gone for good.
- **If it cannot bring something back, it tells you.** For example, a private
  podcast's saved password is deleted when you stop following it. Undo brings
  the podcast back and tells you the password must be typed again.

Anything you can take back ends what Quill Radio says with "Ctrl+Z undoes
this". Ctrl+Z works in the main window, so if you are in Browse Stations,
press **Escape** or **Ctrl+Tab** to get to the main window first.

### Why a menu item is dimmed

A dimmed menu item always carries its reason. Screen readers that read menu
help say it, and the status bar shows it. For example:

- "Download All Episodes: nothing to download, all 40 are already here."
- "Mark All as Played: nothing to mark, all 63 episodes are already played."
- "Pause: this is live radio, which is going out now."

To hear the reason for a dimmed item:

1. Arrow to the dimmed item in the menu.
2. If your screen reader reads menu help, you hear the reason after the item's
   name.
3. If it does not, press **Escape** to close the menu, then press
   **Ctrl+Shift+P**, type the command's name, and arrow to it. The Command
   Palette reads the reason in the list.

The Command Palette works the same way: a command that cannot run reads its
reason instead of a bare "(unavailable)". Items are dimmed rather than hidden,
so you can always hear that a command exists.

### Recent Problems

**Help > Recent Problems...** (Ctrl+Alt+Shift+P) lists what has gone wrong
lately, such as podcasts that could not be read, downloads that failed and
stations that dropped, each with the reason and the time. If you missed
something Quill Radio said about a failure, this is where it waits for you.

1. Press **Ctrl+Alt+Shift+P**. Your cursor is in **What has failed recently**
   (Alt+W), newest first. If there is nothing, you hear "No recent problems".
2. Arrow through the list.
3. **Retry** (Alt+R) tries the highlighted problem again, such as playing a
   station or downloading something again.
4. **Copy All** (Alt+C) copies the list as text, for a message to support. It
   includes addresses and error messages, never passwords.
5. **Clear List** (Alt+L) empties it. It does not fix anything.
6. Press **Escape** to close.

Nothing in the list leaves your computer.

#### When closing could not finish saving

When Quill Radio closes, it notes the time, which is how it later finds
recordings it missed while it was closed. It also clears its note that a
recording was running. If it cannot save either of these, it still closes, but
the next time it starts it tells you once, and a **Closing** row appears in
Recent Problems. **Retry** on that row saves both again now. While you are
recording, the recording note is left alone, because that note is how Quill
Radio tells a crash from a normal close.

### Activity and Repeat Last Result

**Help > Activity...** (Shift+F9) lists everything Quill Radio reported this
session, good news or bad, newest first, one sentence to a row: whether it
worked, what it was, and when. For example, a settings file that could not be
saved, a save that worked after an earlier failure, or something that finished
in the background after you closed the window that started it. Recent Problems
keeps failures from one day to the next; Activity keeps this session's results
together with what you can do about them.

1. Press **Shift+F9**. Your cursor is in **What happened** (Alt+W), newest
   first. If there is nothing yet, the summary says so.
2. Arrow through the list. **Details** (Alt+D) below has the full sentence,
   the reason, the time and what you can do.
3. **Retry** (Alt+R) does the selected thing again, the same way. For the
   settings file, that means trying the save again.
4. **Open Folder** (Alt+F) opens the folder in File Explorer with the file
   selected, so you can see for yourself if a disk is full or a folder is
   read-only.
5. **Copy Details** (Alt+C) copies the selected result as text, for a message
   to support. **Clear List** (Alt+L) empties the list for this session.
6. Press **Escape** to close.

Finished recordings are in the list too, as "Recording saved", with Open
Folder to find the file. So are exports: the calendar, a playlist, and your
listening statistics.

**Help > Repeat Last Result** (F9) says the newest result that mattered again.
That is the last thing Quill Radio itself told you, not the last thing your
screen reader read, and it also tells you what Activity offers for it.

Nothing in the list leaves your computer. These two keys do the same in QUILL,
QUILL Lite and QUILL Cast.

### What Quill Radio connects to

It is fair to want to know what an app does on the internet. Here it all is,
plainly.

- **Playing** uses the **mpv** player that comes with Quill Radio, with the
  Windows Media player built into Windows as a backup and as the "classic"
  choice. Nothing downloads while you use it. Between them they play MP3, AAC
  and HE-AAC, Ogg Vorbis, Opus, FLAC and HLS. If one cannot open a station,
  the other tries before you hear an error.
- **Recording**, and Sound Enhancements on the classic engine, use the
  **ffmpeg** that comes with Quill Radio. On the classic engine, Sound
  Enhancements plays through a small relay on your own computer that nothing
  outside can reach. On the mpv engine, the enhancements happen inside the
  player.
- **Searching and browsing for stations** talks to public directories, none of
  which need a key or an account: RadioBrowser, SomaFM, iHeart, TuneIn,
  SHOUTcast, Live365, Radio Paradise, a community M3U list on GitHub,
  iptv.org, the Internet Archive, LibriVox, Project Gutenberg, AudioPub,
  Audius, Mixcloud, ccMixter, Apple's podcast storefront and Podcast Index.
  Xiph and Wikidata start switched off. **Choose Browse Sources** lists every
  one, each saying whether it is on. A branch that is off is never contacted
  while you browse, and not to refresh the catalog either. **Search All
  Sources** asks every directory.
- **Podcast Index** is on to begin with. It is the one directory here that
  needs a key, and Quill Radio comes with its own. The key identifies the app,
  not you.
- **Things that happen without you pressing anything:** a quiet check for
  updates once a day when Quill Radio opens (one request to GitHub, with no
  version or computer details sent); refreshing the station catalog; and,
  while a station plays, reading the song title from the stream you are
  already listening to. Each one has a switch in Preferences.
- **Playing a RadioBrowser station tells RadioBrowser.** That is how its
  community counts plays and ranks its stations. It sends the station's
  number and nothing about you, and only for RadioBrowser's own stations. Turn
  it off with **Share play counts with the RadioBrowser directory** in
  Preferences.
- **Find Streams** only fetches the one page you give it, follows its Listen
  Live link one step, and, when needed, makes one lookup to the player
  company's own address service. **Stream recovery** does the same by itself
  for a failing station, when its setting is on. **What's Playing** reads the
  stream you are playing, and as a last resort that same server's status page.
- **YouTube** is reached through the yt-dlp helper that comes with Quill
  Radio, only after you agree the first time, and never in Safe Mode. Search
  YouTube, opening a channel or playlist, and Read Comments each ask YouTube
  once. Notify Me About New Videos looks at the newest few videos of the
  channels you turned it on for, when your podcasts are checked. Your YouTube
  sign-in is used only if you turn it on in Preferences, and Quill Radio never
  copies, saves or logs it.
- **What Quill Radio has none of:** no account of its own, no advertising, no
  tracking, no usage reports, and nothing that identifies your copy or your
  computer. Nothing you type, write or record is sent anywhere. Every way the
  app can reach the internet is written down and checked before each release.
  Everything that uses the internet is off in Safe Mode.
- **NOAA Weather Radio** uses the WeatherIndex directory (api.wxindex.org),
  which needs no key, when you are online, and the whole directory comes with
  Quill Radio for when you are not. **Radio Reading Services** is refreshed
  from RadioBrowser, with its own list as a backup. The **ACB Media** directory
  comes with Quill Radio.

### What you learned, and where to go next

You now know that Ctrl+Z and Undo History can take back what you removed, that
a dimmed item always tells you why, and that Recent Problems, Activity and F9
keep anything you might have missed. You also know exactly what Quill Radio
does on the internet, and what it never does. The last chapter, Chapter 16,
When you need a hand, shows you every way to get help.

## Chapter 16: When you need a hand

Help is never far away in Quill Radio. This chapter covers the guided
tutorials, F1 help on any control, keeping Quill Radio up to date, checking
that playing and recording will work, getting in touch with a real person,
and answers to the problems people run into most.

The tutorial **The help that comes with it**, in the Living with it track,
walks you through the help you have here.

### Tutorials

**Help > Tutorials...** (Ctrl+Alt+F1) opens 41 guided lessons, 281 steps in
all, in six tracks: Your first hour, Finding something to listen to, Making it
yours, Recording, More than radio, and Living with it. They are not a copy of
this guide:

- **They show the keys you actually have.** If you change a key, the lesson
  tells you your key.
- **Try it does a step for you**, so you can see what happens first.
- **Follow me notices when you have done a step yourself**, tells you what it
  saw, and reads the next one. It watches what changed in the app, never which
  key you pressed. It never takes over your keyboard, and nothing is marked or
  scored.

#### Take a tutorial, step by step

1. Press **Ctrl+Alt+F1**. The Quill Radio Tutorials window opens with your
   cursor in **Find a tutorial (or type 'here' for this window)** (Alt+F).
2. Type words to narrow the list. Every word must appear somewhere in a
   lesson, so "record tuesday" finds the lesson about booking a recording.
   Type **here** to list the lessons about the window you came from. Press
   **Enter** to move into the list.
3. The tree lists lessons by track. Each row tells you how many steps, roughly
   how long, and whether you have finished it. Arrow to one.
4. Press **Enter**, or choose **Start** (Alt+A). The lesson opens with the
   first step in a box you can read.
5. Read the step. Choose **Try it** (Alt+T) to have Quill Radio do it for you,
   or do it yourself.
6. Check **Follow me** (Alt+M) if you want the lesson to notice when you have
   done each step.
7. Choose **Next** (Alt+N) to move on, **Back** (Alt+B) to go back, or **Say it
   again** (Alt+G) to hear the step again.
8. Choose **Contents** (Alt+C) to go back to the list.
9. Press **Escape** to close the window. Your place is kept.

The Tutorials window is a window of its own. Leave it open, press **Ctrl+Tab**
to go to the part of the app the step is about, do the step there, and hear
the lesson move on behind you. The playing keys work inside it too.

On the contents page, **Read it all** (Alt+R) shows a whole lesson as one page
of text. **The whole book as a document** (Alt+D) opens every lesson as one
document. **Forget my progress** (Alt+P) clears which lessons you finished and
where you were, after asking you.

The same lessons are also in `tutorials.md` beside this guide, with the keys
Quill Radio comes with.

### Context help (F1), step by step

1. On any control, in any window, press **F1**.
2. A help window opens. It tells you what the window you are in is for, then
   what the control you are on does and how to use it.
3. Arrow through the text. You can copy it if you like.
4. Press **Escape**. You are back exactly where you were.

### Check for Updates, step by step

Help > About shows your version with a build number, such as 3.2.0 (build 2). The
build number tells you which build of a version you have: when a fix comes out
without a new version number, it is a newer build, and Check for Updates offers it.

1. Press **Ctrl+Alt+U** (**Help > Check for Updates...**). You should hear
   "Checking for updates".
2. If there is nothing new, a message says "You are up to date", with your
   version. Press Enter to close it.
3. If there is an update, the Update Available window opens. Your cursor is in
   **What's new** (Alt+N), a box with the release notes. Arrow through them.
4. Choose **Update** (Enter) to download it, and you hear how it is getting on.
   Or choose **Close** (Escape) to leave it for now.
5. When the download finishes, the **Update downloaded** window gives you three
   choices:
   - **Install and restart now** (Enter): Quill Radio closes, the update is
     installed, and Quill Radio opens again, up to date.
   - **Install when I close** (Alt+C): carry on listening. The update is
     installed the next time you close Quill Radio, and the time after that
     you open it, it is the new version. It does not reopen by itself.
   - **Open folder**, to find the downloaded file yourself, or **Close**
     (Escape) to leave it.

Quill Radio offers the download that matches your copy: the portable zip for a
portable copy, and the installer for everyone else. **A portable copy updates
itself where it is**: the new files replace the old ones in its folder, and
the `data` folder, with your favorites, settings, history and recordings, is
never touched.

Quill Radio also checks quietly once a day when it opens. It only speaks when
it finds something. Turn it off with **Check for updates automatically on
launch** in Preferences.

#### Updating from an older version by hand

A few older versions need a hand to update once. After that, every update
installs itself.

- **From 3.0.4 or earlier to 3.2.0.** Up to 3.0.4, the small program that
  installs an update did not get the chance to run, so **Install and restart
  now** closed Quill Radio and nothing else happened. That is fixed in 3.2.0,
  but the fix cannot reach you through the old version. So do this one update
  yourself: download `Quill-Radio-Setup-Shared-3.2.0.exe` from the releases
  page and run it, or for a portable copy, unpack
  `Quill-Radio-Portable-3.2.0.zip` over your folder as described next. Your
  favorites, settings, recordings and history are not touched.
- **A portable copy of 3.0.0, 3.0.1 or 3.0.2.** These three could not install
  their own portable update. They said "Could not install the update
  automatically" and left the zip in `data\updates`. Update them once by hand:
  close Quill Radio, unzip `Quill-Radio-Portable-3.2.0.zip`, and copy
  everything in its `QuillRadio` folder over your copy's folder, replacing
  files when asked. Your `data` folder is not in the zip, so it is left alone.
- **If Check for Updates keeps offering an update you already installed.** Up
  to 3.0.4, on a computer with several QuillVille apps, Quill Radio could read
  the wrong version number, and then compared the wrong number. From 3.2.0 it
  reads its own. Install 3.2.0 by hand as above, and the answer is right from
  then on.

### Release channels: Stable, Beta and Dev

Quill Radio comes in three flavours, and you choose which one your copy
follows. They are called release channels.

- **Stable** is the version we recommend. It has been checked with JAWS and
  NVDA, and it is what most people use. Every copy starts here.
- **Beta** gets new features a few weeks early. It is mostly finished, but some
  things may not work right yet.
- **Dev** is the work in progress, sometimes several builds a week. Things will
  break. Only choose it if a developer asked you to, or you enjoy testing.

1. Open the **Help** menu, then choose **Release Channel...** (press **Alt+H**,
   then **N**). You can also open it from Preferences, with the **Change
   Release Channel** button.
2. Arrow through Stable, Beta and Dev. The box below tells you what each one
   means and what choosing it would do. Nothing changes yet.
3. Press **Switch** to move, or **Close** (Escape) to leave things as they are.
4. For Beta or Dev, a short warning comes first: what could go wrong, how your
   favorites are protected, and how to come back. Read it, tick the **I
   understand** box, and choose **Move to Beta** (or **Move to Dev**). **Stay on
   Stable**, or Escape, changes nothing.

Beta and Dev versions aren't signed, so when you install one, Windows
SmartScreen may warn that it comes from an unknown publisher; that's expected,
and choosing **More info**, then **Run anyway**, installs it.

Before it moves, Quill Radio saves a copy of your favorites, history and
settings. If it cannot, it stays where it is and tells you why. Your
recordings are not copied, and updates do not change them. Then it checks for
updates on the new channel straight away and offers you the newest version
there, if there is one. Nothing is installed unless you say so.

**When QUILL Lite or QUILL Cast is installed too.** These apps run on one shared engine on
your computer. When an app moves to Beta or Dev, it gets its own copy of that
engine, so the apps you leave on Stable are never touched. You can still move
several at once: tick them under "Also move my other QuillVille apps on this
computer" and choose **Switch**.

**A note about disk space.** That second copy of the engine takes about 335 MB.
It goes away by itself when your last app comes back to Stable. A portable copy
carries its own engine, so it needs no extra space.

**Updates on Beta and Dev.** On Beta and Dev, Quill Radio downloads a new version
quietly when its daily check finds one, so it is ready when you are. It never
installs anything without asking: when the download is done, it says so and
shows you what's new, and you choose when to install. It waits instead of
downloading on a metered connection, during Quiet Hours, and while you are recording.
Update History tells you why it waited. On Stable nothing changes: Quill Radio tells
you about a new version and downloads it only when you ask.

**If an update doesn't start.** After an update, Quill Radio checks that the new
version really opens. If it doesn't open within two minutes, the update undoes
itself and puts back the version you had, and the next time Quill Radio starts it
tells you so. Nothing of yours is changed, and Update History has the details.
To make this possible, Quill Radio keeps a copy of the installer for the version you
have: on Beta and Dev for as long as you have that version, and on Stable for a
week or three starts after each update. That copy takes about 200 MB of disk
space, which Stable gives back once the week or the three starts are up. After
an update, the previous installer is kept until the new version has started
three times, or for a week, and then it is deleted.

**Coming back to Stable.** Open Release Channel again and choose **Stable**.

- If the version you have is already a Stable one, you are back straight away
  and nothing is installed.
- If you have a newer Beta or Dev version, Quill Radio checks whether Stable can
  read everything you have saved. If it can, choose **Go back to** (the Stable
  version) **now**. Quill Radio downloads Stable and offers to install it, and your
  favorites and settings come with you.
- If Stable can't read something yet, Quill Radio says so and gives you two safe
  choices. **Wait for Stable** keeps the version you have, stops test versions,
  and moves you to Stable by itself when Stable catches up. **Use the copy
  from** (the day you joined) puts back the copy of your favorites and settings saved
  when you joined, then installs Stable. Anything you added since then won't be
  in it, but a copy of how things are right now is saved first, so nothing is
  thrown away.
- If there is no saved copy, waiting is the only choice, and the window says
  so.

The **Update History** button in the same window shows what the updater has
done for Quill Radio. Switching sends nothing about you: the only thing Quill
Radio ever sends when it checks for updates is a request for the list of
versions.

### Audio Health, step by step

Audio Health answers "is this going to work?" in one list. It does not test
anything: no sound is played, no device opened, no file written. So it is safe
to open even during a recording.

1. Press **Ctrl+Alt+Shift+M** (**View > Audio Health...**). A headline sums it
   up, and your cursor is in **What the radio is using right now** (Alt+W).
2. Arrow through the list. It tells you which playback engine is really in
   use (and whether Automatic has fallen back to Windows Media because mpv is
   missing), whether mpv and ffmpeg are there and what you lose without them,
   where the sound is going, what Sound Enhancements are doing, whether the
   full OptiLab is included, and whether a recording could be saved to your
   recordings folder right now.
3. **Check Again** (Alt+C) looks at everything again, for example after you
   plug in a headset, and tells you the headline.
4. **Repair FFmpeg...** (Alt+R) and **Repair mpv...** (Alt+M) are only
   available when that tool is missing.
5. Press **Escape** to close.

### Repair a missing tool

Both mpv and ffmpeg come inside every copy of Quill Radio. If one goes
missing, the usual cause is an antivirus program taking it away, or an update
that did not finish. Quill Radio tells you once when it opens: which tool is
gone, what you lose, and what to do.

- **Without mpv**, stations still play through Windows Media, but rewinding
  live radio, choosing the output device, Volume Boost, song titles from the
  stream and noticing when a stream goes quiet stop working, and Ogg Vorbis,
  Opus and HLS stations do not play at all.
- **Without ffmpeg**, recording and downloading stop working.

To repair:

1. Press **Ctrl+Alt+F** (**Help > Repair FFmpeg...**) or **Ctrl+Alt+M** (**Help
   > Repair mpv Playback Engine...**).
2. Agree to the download. Quill Radio fetches the official version and tells
   you when it is ready.

Installing Quill Radio again also puts both back. If everything is fine,
Quill Radio says nothing about any of this.

### Other help

- **User Guide** (Ctrl+F1) opens this guide in your web browser. Use your
  browser's heading keys to move between chapters, and Ctrl+F to find a word.
- **Release Notes** (Shift+F1) opens what is new in this version: what
  changed, what was fixed, and what to know when you upgrade.
- **Product Requirements...** (Alt+Shift+F1) opens the design record: what
  Quill Radio promises, and why. You do not need it to use the app.
- **Get Help from Support...** (Ctrl+Alt+F2): see "Getting help from support"
  below.
- **About Quill Radio** (Alt+F1): the version, and where the project lives.
- **Repeat Last Announcement** (Command Palette) says the last thing Quill
  Radio told you, again.
- **Announcement Self-Test...** (Command Palette) says a test phrase and tells
  you which ways it reached you: speech, braille and sound. It can tell
  "braille is not working" apart from "no braille display is connected".
- **Redeem Unlock Code...** (Command Palette) takes a code for a feature that
  is not released yet. The code is checked entirely on your computer; nothing
  is sent. One code works for QUILL, Quill Radio and QUILL Cast together.

### Getting help from support

Support is run by **Community Access**. Write to
**support@community-access.org** with questions, problems, ideas or
suggestions. A person reads every message, and you get your reply by email.

Every kind of message from Quill Radio goes to that one address: **Get Help
from Support**, **Report Bad Station** and **Suggest a Station or Podcast**.
None of them is posted on GitHub or any other public website.

#### What the window asks

1. Press **Ctrl+Alt+F2** (**Help > Get Help from Support...**). The Get Help
   from Support window opens. At the top it tells you the message goes to
   support@community-access.org, and that nothing is sent until you send it
   from your email program.
2. **What kind of message** (Alt+W) is a list: Something is broken, A question,
   An accessibility problem, or An idea or request. Use the Up and Down Arrow
   keys. It only helps your message reach the right person; say anything you
   like below.
3. **Subject** (Alt+U): a short line saying what it is about, like an email
   subject, such as "Recording stops after an hour". You must fill this in.
4. **What happened** (Alt+H): tell us in as much or as little detail as you
   like. This is the part a person reads first. You must fill this in. Enter
   starts a new line, so press **Tab** to move on.
5. **What you expected** (Alt+X): what you thought would happen instead.
   Optional.
6. **Steps to reproduce** (Alt+R): how someone else could make it happen, such
   as "Play BBC Radio 4, press Ctrl+R, wait an hour". Optional, but worth more
   than anything else when you can give it.
7. **Your email address** (Alt+E): where support should reply. Optional. The
   message comes from your own email account, so support can reply to that
   anyway; only fill this in if you want the answer to go somewhere else.
8. **Screen reader** (Alt+A): which one you use, if any. It is filled in from
   the screen reader that is running, so you can usually leave it.
9. Under the fields, a line tells you what else is included, such as "Also
   included: Quill Radio 3.0.3, and your Windows version."

#### Sending it

1. Press **Enter**, or Tab to **Send** and press **Space**.
2. If the subject or What happened is empty, or the email address does not
   look right, you hear the first problem and see the whole list. Press
   **Enter** to close it, fix the field, and send again.
3. Otherwise your own email program opens with the whole message written,
   addressed to support@community-access.org, with a subject such as "[Quill
   Radio 3.0.3] Recording stops after an hour". You hear "Your mail program is
   opening with the message ready. Nothing is sent until you send it there."
   The Get Help window closes.
4. **Press Send in your email program.** Nothing leaves your computer until you
   do.

#### If you have no email program

On a computer with only webmail, nothing can open, and Quill Radio says "No
mail program answered. Write to support@community-access.org." The whole
message, with the address and subject at the top, is on your clipboard. Start
a new email to **support@community-access.org** in your webmail and paste it
in with **Ctrl+V**. The Get Help window stays open with what you typed.

A very long message is shortened in the email, with a line saying so, and the
full text goes on your clipboard. Quill Radio tells you when this happens;
paste the full text over the shortened one with **Ctrl+V**.

#### What is included, and what is not

- Included: what you typed, the kind of message, Quill Radio's name and
  version, your Windows version, and the screen reader you chose.
- Not included: your favorites, recordings, listening history, passwords, or
  any file. If support needs more, they will ask, and **Copy All** in **Recent
  Problems** (Ctrl+Alt+Shift+P) gives them the details without any passwords.
- It is an ordinary email from your own account to Community Access. Nothing is
  posted publicly, and Quill Radio itself does not send anything.

#### What happens next

A person at Community Access reads it and replies by email, usually to the
address you sent from. To close the window without writing anything, press
**Escape** or choose **Cancel**.

**Report Bad Station** (Shift+F10 on a station in Browse Stations or Search
Stations) opens this same window with the station's name, stream, source and
country already filled in. It never includes your name, email or file paths.

Writing to support@community-access.org yourself, from any email account,
works just as well.

### Troubleshooting

Here are the problems people run into most often, and what to do about each.

#### The sound card does not switch

Choose the device in **Audio > Output Device...** (Ctrl+Shift+D) and listen
to what Quill Radio says.

- "Output device" and its name means the station moved. All is well.
- "... could not be opened, so the output device is back to ..." means Windows
  would not let Quill Radio use that device just then. Wake the headset, close
  anything else using the sound card, or plug it back in, then choose it
  again.
- "The playback engine is the classic Windows Media control" means this
  computer has no modern media player, so the list cannot move the sound on
  that engine. Windows' Sound settings open at the same moment, so give Quill
  Radio its device there under Volume mixer, or set **Playback engine** to
  Automatic in Preferences to choose it here.
- "Windows Media is playing this station, and it cannot use the chosen output
  device" means the station itself would not play on the mpv engine, so it is
  on Windows Media for now. Try the station again, or another stream of it.

Check the row you chose, too. Windows calls both a laptop's built-in sound
card and a USB headset "Speakers", and only the make in brackets tells them
apart.

#### If Quill Radio does not start

Since 3.0.4, `QuillRadio.exe` always tells you when something goes wrong. If
the app cannot start, or stops with an error, a plain message opens that your
screen reader reads by itself. It says "Quill Radio did not start" (or
"stopped unexpectedly", if it had been running a while), gives the reason in
words, names the file with the details, and gives the support address.

- **The message says the zip was opened from inside.** You pressed Enter on
  `QuillRadio.exe` while still inside the zip, so only that one file was
  copied out. Select the zip in File Explorer, press the Applications key,
  choose **Extract All...**, and open `QuillRadio.exe` from the folder you
  extracted.
- **The message says a file is missing, or a DLL could not be found.** Extract
  the whole zip again into an empty folder, and check your antivirus
  program's quarantine for anything it took from the Quill Radio folder.
- **The message says Windows refused to run its files, or access was
  denied.** Move the folder somewhere that belongs to you, such as Documents
  or a USB stick, and check your antivirus and any settings that control
  which programs may run.
- **The message says a file is damaged, or the wrong kind for this
  computer.** Quill Radio needs 64-bit Windows 10 or 11. Download the zip
  again.
- **The message says "Python reported", followed by an error.** Send the
  launch log to support; the next paragraph tells you where it is.
- **Nothing at all happens, and there is no message.** Quill Radio is probably
  already running, in the tray, and your new launch simply handed over to it.
  Check the notification area and Task Manager. If a copy is running but not
  responding, end it there and start again.

The launch log holds what happened the last time Quill Radio started. A
portable copy keeps it at `data\logs\launch.log` beside `QuillRadio.exe`; an
installed copy keeps it at `%APPDATA%\Quill\logs\QuillRadio-launch.log`, next
to `quill.log`. Each start replaces it, so send it before you try again. It
contains file locations from your computer and nothing else personal.

#### Everything else

- **My YouTube will not open, or says your browser keeps its sign-in locked
  or protected.** Close the browser completely and try again, or choose
  Mozilla Firefox or a cookies.txt file in Preferences. "When the YouTube
  sign-in does not work" in Chapter 11 goes through each message.
- **Search YouTube or Read Comments says YouTube did not answer.** YouTube
  changes things from time to time. Try **Station > Repair YouTube
  Support...** (Ctrl+Alt+Y), then try again.
- **A favorite takes a long time to start, then says it is trying the
  station's current address.** Its saved address stopped working, and Quill
  Radio found the new one. Since 3.0.3 the new address is saved into the
  favorite, so this happens once, not every time. If a station is still slow
  to start every time, find it again in Browse Stations (Ctrl+B) or search
  (Ctrl+F), play it, and press Ctrl+Shift+F to save it fresh.
- **Help > User Guide, Release Notes or Product Requirements does nothing.**
  That happened in 3.0.0 to 3.0.2 and was fixed in 3.0.3. The same documents
  are always on quillforall.org.
- **A Quill Radio pinned to the taskbar says "QuillVilleRuntime.exe is the
  shared engine ... it is not an app of its own".** That pin was made from the
  running window before 3.0.2, so Windows pinned the shared engine rather
  than Quill Radio. Since 3.0.2 the pin starts Quill Radio anyway (or, with
  several QuillVille apps installed, asks which one to open). To make the pin
  a proper one, right-click it, choose Unpin from taskbar, and pin Quill Radio
  again from the Start menu or its running window.
- **A recordings window or other window does nothing when you ask for it.**
  If it was minimized, Quill Radio now brings it back. If it still does
  nothing, send the launch log described above to support.
- **A station will not play.** Streams move. For a directory station, Quill
  Radio fetches its current address and tries again, and can look on the
  station's own website (see "When a station will not play" in Chapter 6). If
  it still fails, search for it again, or add it again as your own station. If
  a station is simply dead, press **Shift+F10** on it in Browse Stations or
  Search Stations and choose **Report Bad Station...**. The report is filled
  in with the station's name, stream, source and country, and never your
  name, email or file paths.
- **A station plays for twenty or thirty seconds, then stops.** This was a
  real problem, fixed in 3.0. Some stations, iHeart's especially, arrive in
  short pieces, and one missed piece used to leave the radio silent. Now Quill
  Radio reconnects: you hear "Reconnecting to" the station, "Attempt 1 of 3",
  up to three times. If a station still stops dead without trying to
  reconnect, please tell us with **Report Bad Station...**.
- **A recording, book chapter or downloaded show is not reconnected at its
  end.** That is on purpose. It really has finished.
- **No sound, but Quill Radio says it is playing.** Check Mute (Ctrl+M), the
  station's own volume (Ctrl+Up), Volume Boost, the output device
  (Ctrl+Shift+D), and Quill Radio's entry in the Windows volume mixer. **View >
  Audio Health** (Ctrl+Alt+Shift+M) shows you the whole picture.
- **A station's own web address will not play.** Quill Radio needs the sound
  stream, not the website. Type the web address into any search box, and
  Quill Radio finds the stream for you. If a home page finds nothing, try its
  "Listen Live" page, or search for the station by name.
- **The directories do not have my station.** Type its web address into any
  search box, such as `oj991.com`. If the station has a working player on its
  website, that is usually all it takes.
- **A recording saved nothing.** Quill Radio tells you, names the station, and
  gives the reason, such as "the connection failed" or "the disk is full". No
  empty file is kept, and you hear the error sound, not the saved sound.
- **A recording stopped early.** Look in Radio Recordings. If the connection
  dropped, the recording carries on in "(part 2)" files, which are joined when
  the recording ends. The maximum length in Recording Settings also ends
  recordings on purpose.
- **I still have "(part 2)" files.** The parts could not be joined, and Quill
  Radio told you why when the recording ended. Every part is safe, exactly as
  recorded, and they play in order.
- **A scheduled recording did not start.** Quill Radio must be running, at
  least in the tray. Check that the entry is not "(disabled)" in Schedule
  Recording, and that **Wake the computer for a scheduled recording** is on in
  Preferences if your computer sleeps.
- **The wake-up timer did not go off.** Quill Radio must be running at the set
  time. Running in the tray counts; a closed app does not. It never goes off
  late: if you open Quill Radio hours after the set time, it stays quiet until
  the next time comes round.
- **The tray icon is gone.** Look in the "Show hidden icons" area, or set
  Quill Radio to always show in the Windows taskbar settings.
- **Rewind or Volume Boost says it "needs the mpv playback engine".** In
  Preferences, **Playback engine** is set to Windows Media, or the mpv engine
  is missing. (The output device no longer needs mpv, because Windows Media
  can use a device too.) Set it to Automatic, or use **Help > Repair mpv
  Playback Engine...**. For the output device alone, Windows' Sound settings
  can give Quill Radio a device under Volume mixer on any engine, and
  Ctrl+Shift+D opens that page.
- **Playing sounds different since 1.1.0.** In Preferences, **Playback engine**
  set to Windows Media is the way to play without mpv. Please tell us what you
  heard (Ctrl+Alt+F2).
- **Quill Radio talks too much, or too little.** Quiet Hours
  (Ctrl+Alt+Shift+Z) holds back speech nobody asked for. Recent Problems
  (Ctrl+Alt+Shift+P) keeps any failure you missed.
- **Something says it is "off in Safe Mode".** Safe Mode is a special way of
  starting, used when tracking down a problem. It switches off everything that
  uses the internet, refreshing the station catalog, YouTube, Spotify and
  Quillins, so a problem can be narrowed down. Quill Radio only starts in Safe
  Mode when it is asked to. If support asks you to use it, they will tell you
  how, and starting normally afterwards brings everything back.
- **Something else.** Press **Ctrl+Alt+Shift+P** for Recent Problems and
  **Ctrl+Alt+Shift+M** for Audio Health, then write to support with
  **Ctrl+Alt+F2**. Copy All in Recent Problems gives support the details
  without any passwords.

### What you learned, and where to go next

You know where to turn when you need help: the tutorials for learning by
doing, F1 for whatever you are on, Audio Health for the sound, and a real
person at support@community-access.org for anything else. You can keep Quill
Radio up to date and sort out the most common problems yourself. That is the
end of the chapters. The Keyboard reference below is worth keeping handy for
your first few weeks. Thank you for listening with Quill Radio. Enjoy it.

## Keyboard reference

Every menu item shows its own key, and if you changed a key, it shows yours.
To see every key at once, press **Ctrl+Alt+Shift+K** for the Keyboard
Shortcuts Sheet. The tables below are the keys most worth knowing, grouped by
what you want to do. Each table is short, so you can arrow through it a row at
a time.

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

In every other window, Alt+S is the Station menu and Alt+W is the Window menu. See "The menus in other windows" in Chapter 3.

### Playing

| Action | Key |
| --- | --- |
| Play the selected favorite, or stop | Enter (in the list), or Ctrl+P |
| Website | Alt+B (on the main window) |
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
| Find Streams from a Website | Ctrl+Alt+S |
| Search Sources | Ctrl+Alt+Shift+U |
| Choose Browse Sources | Ctrl+Shift+Alt+O |
| Update Station Catalog | Ctrl+Alt+Shift+G |
| Update Radio Reading Services | Ctrl+Alt+F10 |
| Station Catalog Status | Ctrl+Alt+Shift+S |

### YouTube

| Action | Key |
| --- | --- |
| Search YouTube | Ctrl+Shift+6 |
| Add YouTube Link | Ctrl+Alt+N |
| Add from YouTube Playlist | Ctrl+Shift+Y |
| Import YouTube Subscriptions | Ctrl+Alt+Shift+Y |
| Read Comments on the video that is playing | Ctrl+Shift+7 |
| Live Chat of the video that is playing | Ctrl+Alt+Shift+7 |
| YouTube Video window (description, moments, like, playlists) | Ctrl+Alt+Shift+8 |
| Skip Sponsor Segments | Ctrl+Alt+Shift+9 |
| Search YouTube with Filters (and YouTube Music) | Ctrl+Alt+Shift+0 |
| Transcript of the video that is playing | Ctrl+Shift+T |
| Repair YouTube Support | Ctrl+Alt+Y |
| A row's menu: Follow, Subscribe on YouTube, Notify Me, Read Comments, Live Chat, YouTube Video, About This Channel | Shift+F10 |

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
| Local Media (your own files, in playlists) | Ctrl+O |
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
| Undo History | Ctrl+Alt+Shift+A |
| Recent Problems | Ctrl+Alt+Shift+P |
| Notifications | Ctrl+Alt+Shift+F3 |
| Quiet Hours | Ctrl+Alt+Shift+Z |
| Bookmarks | Ctrl+Alt+Shift+J |
| Export My Setup / Import My Setup | Ctrl+Alt+Shift+X / Ctrl+Alt+Shift+N |
| Get Help from Support | Ctrl+Alt+F2 |
| Repair FFmpeg | Ctrl+Alt+F |
| Repair mpv Playback Engine | Ctrl+Alt+M |
| Check for Updates | Ctrl+Alt+U |

**Nothing here uses Ctrl+Alt with an arrow key.** JAWS and NVDA use those keys
to move around tables, so Quill Radio leaves them alone. In 3.0, speed moved to
Ctrl+Shift+Up and Ctrl+Shift+Down, and chapters to Ctrl+Shift+comma and
Ctrl+Shift+period. If you have notes from an earlier version, those are the
keys that changed.

### Where to go next

Keep this reference nearby for your first few weeks, and you will soon find
you only need it now and then. When you forget a key, the Command Palette
(Ctrl+Shift+P) and the Keyboard Shortcuts Sheet (Ctrl+Alt+Shift+K) will always
find it for you, and the tutorial **Make the keys yours** shows you how to
change any key you do not like.
