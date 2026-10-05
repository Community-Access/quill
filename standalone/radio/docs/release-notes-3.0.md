# Quill Radio 3.0

Version 3.0.4, released 2026-09-28.

Welcome to Quill Radio 3.0. This is the release where the radio helps you
find something to listen to from the moment you open it, and then helps you
keep it, record it and come back to it.

These notes cover 3.0 and the four small updates that followed it, newest
first. If you are new to 3.0, you may like to skip ahead to "What 3.0
brought", which describes the whole release. The 3.2 release has its own
notes, which **Help > Release Notes** (Shift+F1) opens.

## The updates after 3.0

### What's new in 3.0.4

#### If it cannot start, it tells you

A listener wrote that her portable copy did not open. No window, no message,
nothing in the tray. Quill Radio had no way to tell her what went wrong.

Now, if Quill Radio cannot start, you get one plain message box that every
screen reader reads. It says "Quill Radio did not start", gives the reason in
words, names the file that holds the details, and gives you the support
address to send it to. It is specific where it can be:

- If a needed file is missing, it tells you the two things to check.
- If a file is damaged, or is the wrong kind for your computer, it says so.
- If Windows says "access denied", it suggests checking your antivirus and the
  folder's permissions.

It also catches the most common mistake with a portable copy: starting Quill
Radio while you are still inside the zip file. Instead of a confusing message,
it tells you the zip was never unpacked and walks you through Extract All.

Nothing changes when Quill Radio starts normally. The user guide's chapter
When you need a hand starts with "If Quill Radio does not start".

#### Up is louder on the volume slider

A listener wrote: "your volume is backwards, when you turn it up it's down
arrow." They were right. Now Up and Page Up make it louder, and Down and Page
Down make it quieter, on the Volume slider in every window. That matches
Ctrl+Up, Ctrl+Down and the Windows volume mixer. Every other slider follows
the same rule, so in Sound Enhancements, Up gives you more bass, mid or treble.

#### Save your podcast list for another app

OPML is the file every podcast app uses to share a list of shows. Quill Radio
could bring one in, but could not save one. Now **Export Podcasts to OPML**
sits next to Import, on the menu of the Subscriptions folder and of the
Podcasts branch (press Shift+F10 on either), and in the Command Palette. It
saves every show you follow, folders included, and tells you how many it
saved. QUILL Cast writes exactly the same file, so the two apps always agree.

### What's new in 3.0.3

3.0.3 answered five things listeners told us about in the first days of 3.0,
and added Westwood One's live sports channels.

#### Favorites that started slowly start quickly again

When a station moved its stream to a new address, Quill Radio found the new
address every time but never remembered it, so every play meant the same long
wait. Now it remembers the new address the first time, and the favorite starts
straight away after that. You do not need to do anything.

#### Help opens its documents again

In 3.0.0 to 3.0.2, **Help > User Guide** (Ctrl+F1), **Release Notes**
(Shift+F1) and **Product Requirements** (Alt+Shift+F1) did nothing. Now they
open again, in your web browser.

#### The Stop button is back

The main window has a **Stop** button again (Alt+T), first in the row before
Mute and Volume. It stops whatever is playing, just like **Ctrl+Period** and
**Station > Stop**. Stopping is the one thing everybody needs to find at once,
without knowing a key.

#### Keys that are easier to press

Every command can now be reached without holding several keys down at once.
That matters on a braille notetaker such as the BrailleNote Evolve, and for
anyone who finds a four-key combination hard. Thank you to BITS for raising
it.

- **The QuillVille menu has letters.** Press Alt+Q, then one letter, to open
  another app: Q for QUILL, W for Quill Weather, V for Quill Converter.
- **You choose the keys that open other QuillVille apps.** Find them in
  **Help > Keyboard Shortcuts** (Ctrl+Alt+K) by searching for "QuillVille".
- **More menu items have a letter.** The Sort Favorites and Main Window Shows
  choices, and Play Favorite Station, now do. The Station menu has more items
  than the alphabet has letters, so Preferences (Ctrl+comma), Exit (Ctrl+Q)
  and the two Spotify items have only their keys.
- The user guide has a new section, **Keyboard access without chords**, with
  every way in: menu letters, changing keys, the Command Palette and Sticky
  Keys.

#### Westwood One Sports

**Browse Stations** (Ctrl+B) has a new branch, **Westwood One Sports**, with
the network's ten live event channels. During a big event, such as college
basketball, the NFL or the Masters, Westwood One streams several games at
once, one on each channel. Each one is a row you can play, favorite, record or
schedule. The schedule at westwoodonesports.com says which game is on which
channel. Between events, a channel may be silent. Westwood One's other shows
reach you through local stations under **Networks**.

#### Updates install now, or when you close

When an update has downloaded, you now have two choices:

- **Install and restart now** (Enter). Quill Radio closes, updates and opens
  again.
- **Install when I close** (Alt+C). Keep listening, and the update is
  installed the next time you close Quill Radio.

A portable copy now updates itself too. Your favorites, settings, history and
recordings, all kept in the copy's data folder, are never touched.

**If you have a portable 3.0.0, 3.0.1 or 3.0.2,** please update by hand this
one time:

1. Close Quill Radio.
2. Unzip the newest portable zip.
3. Copy everything inside its QuillRadio folder over your copy's folder, and
   say yes when asked to replace files.

Your data folder is not in the zip, so it stays exactly as it is.

**Coming from a 2.x portable copy?** The old updater can leave a window saying
"find" on the screen. Close it. Unzip the new copy into a new folder and start
it. The first time it opens, it offers to bring in your 2.x favorites.

### What's new in 3.0.2

#### A pinned Quill Radio opens Quill Radio

If you pinned Quill Radio to the taskbar while it was running, pressing the
pin showed a message about the shared QuillVille engine instead of opening the
radio. Now the pin opens your app. If you have several QuillVille apps, a
short list called **Open a QuillVille app** asks which one. Arrow to it and
press Enter, or press Escape to open nothing.

New pins are made right from the start. If you would like an old pin to group
with the running window again, unpin it and pin Quill Radio again from the
Start Menu.

### What's new in 3.0.1

Quill Radio 3.0.1 replaced 3.0.0, which was withdrawn the day after it came
out because it could not always open. 3.0.1 starts every way you might start
it, always comes with its full player, and carries everything it needs inside
the download. Press the key, and the radio is there.

#### If you have 3.0.0

Install the newest version over it. Your favorites, settings, history,
recordings, schedule and keys all stay. If your 3.0.0 opens, **Help > Check
for Updates** (Ctrl+Alt+U) offers you the right download. For a portable copy,
unpack the new zip, then copy the data folder from your old copy into the new
one before you open it for the first time. Anything 3.0.0 set up wrongly on
your computer is put right for you.

#### It opens, every time

On some new installs, 3.0.0 showed a box titled "Unhandled exception in
script" instead of the radio. That is fixed. If you open the shared QuillVille
engine by mistake, it now tells you to start Quill Radio from its own Start
Menu shortcut instead. And if something goes badly wrong while Quill Radio
starts, the details are saved in a report you can send to support.

#### Start with Windows, and recordings that wake the computer

In 3.0.0, **Start with Windows** did not open the radio when you signed in,
and **waking the computer for a recording** woke it to silence. Both work now.
Quill Radio also quietly repairs either one each time it opens, if you had
turned it on. It never adds anything you did not ask for, never changes the
computer from a portable copy, and does nothing in Safe Mode.

#### The full player, however you open it

Quill Radio's full player is what lets you rewind live radio, boost the
volume and choose a sound card. In 3.0.0, opening the app from a taskbar pin
or an old desktop icon could leave you with only the simpler Windows Media
player. Now the full player and recording are there however you open it. If
the installer finds an old desktop icon, it replaces it with one that works.
Opening other apps from the QuillVille menu works properly for the same
reason.

#### Everything in the box

Nothing downloads the first time you use a feature. Both downloads include
everything Quill Radio uses for playing, recording, converting, YouTube and
Exact OptiLab processing. YouTube formats that used to be missing or slow now
play, and the work that makes that possible happens on your own computer.
Whichever QuillVille app you installed first, you get all of it.

#### Repair, only for emergencies

Because everything now comes inside the app, the Help items that used to say
"Get" now say what they are for:

- **Help > Repair FFmpeg** (Ctrl+Alt+F)
- **Help > Repair mpv Playback Engine** (Ctrl+Alt+M)
- **Station > Repair YouTube Support** (Ctrl+Alt+Y)

In Audio Health, the buttons are **Repair FFmpeg** (Alt+R) and **Repair mpv**
(Alt+M).

Repair YouTube Support is for the day YouTube changes faster than Quill Radio
can release an update. It fetches the newest YouTube helper, checks that it is
genuine, and tells you which version it installed. If you already have the
newest, it says so as good news. It always asks before it goes online, and it
is off in Safe Mode. A portable copy never downloads anything; if part of it
is missing, it tells you how to put it right.

#### Tab moves on from your favorites

In the main window, Tab used to stay stuck on the favorites list. Now Tab goes
on to Mute, then Volume, then the now-playing line, and back round to your
favorites. Shift+Tab goes the other way.

#### An installer a screen reader can read

The installer's **Create a desktop icon** and **Launch Quill Radio** choices
are now ordinary checkboxes. In 3.0.0, screen readers said "not checked"
whether they were or not. Now you hear the truth, and Space changes them.

#### If something still is not right

**Help > Get Help from Support** (Ctrl+Alt+F2) writes to a person at
Community Access, with your app's version filled in. You can also write to
support@community-access.org from any email account.

## What 3.0 brought

Quill Radio is an internet radio player for Windows, made for people who use
a screen reader. It plays live stations, podcasts, audiobooks, YouTube and
television, and it records. Nothing needs an account, and nothing you listen
to leaves your computer. It is made by Community Access.

This part describes everything new since 2.1.2. Version 2.2.0 was never
published, so its changes are here too. Here is the short version:

- More than thirty branches to browse, and over 62,000 stations kept on your
  own computer, so browsing works with no internet at all.
- One search, Ctrl+F, finds stations, podcasts, audiobooks, archive
  recordings, music and YouTube videos.
- Described audio on videos is named and one key away: Ctrl+Alt+D.
- Podcasts, audiobooks, the Internet Archive, free music, YouTube and about
  9,300 television channels, all with no account and no key.
- Download what you are allowed to keep, and pick up where you left off.
- More than forty guided tutorials that notice when you do each step:
  Ctrl+Alt+F1.
- F1 in any window explains that window and the control you are on.
- Every menu item shows its key, and Ctrl+Alt+Shift+K lists every key in one
  place.
- Undo (Ctrl+Z), a Recent Problems list, and Quiet Hours.
- Everything the app says also reaches a braille display.

### Getting it

There are two downloads, and both are signed so Windows can check them.

- **The installer**, Quill-Radio-Setup-Shared, is the right choice for most
  people. It sets up the shared QuillVille Runtime if you do not already have
  it, then Quill Radio, with a Start Menu entry and an uninstaller.
- **The portable copy**, Quill-Radio-Portable, is a zip. Unpack it anywhere,
  even a USB stick, and run QuillRadio.exe. It needs no installing and no
  internet.

A portable copy writes nothing to the computer it runs on. Everything you set
up stays in the data folder beside it. Two things that change the computer
itself are not available in a portable copy: Start with Windows, and waking
the computer for a recording.

If you tried a "Lite" installer or a Companion zip from a 3.0 preview, both
are retired. The installer upgrades them in place.

### Your first few minutes

The first time you open Quill Radio, a short welcome of three screens explains
what the app is, how to find something to listen to, and how favorites work.

- Skip is a real button, and skipping counts as done.
- It never appears if you already have favorites, for example after an
  upgrade.
- The keys it names are your keys, even if you changed them.
- The text is in a box you can arrow through and copy.
- **Browse Stations Now** takes you straight to the station tree.

A checkbox, **Show me a tip now and then**, turns on six one-time tips. Each
appears once, the first time it would help, and never takes focus.

### Finding something to listen to

#### Browse Stations

Press **Ctrl+B**. The tree has more than thirty branches, including:

- **By Country**, **By Language**, **Trending Now** and **Recently Added or
  Changed**. Countries open into states or regions, then stations, most
  listened first.
- **Internet Archive**: Old Time Radio, audiobooks and poetry, the Live Music
  Archive, radio programs, and news.
- **LibriVox**: free audiobooks by genre, by author and recently added.
- **Project Gutenberg**: audiobooks read by people, by topic and by language.
- **Audius**, **Mixcloud** and **ccMixter**: independent music, DJ sets, and
  Creative Commons music with its licence in the row. Mixcloud shows open in
  your web browser, and the row says so first.
- **AudioPub**: audio people made and shared.
- **Explore**: stations by city, by format, and On the Dial.
- **My Servers**: your own Icecast or SHOUTcast server.
- **Networks**: the BBC, NPR, CBC, ABC Australia, RTE, RNZ, NHK, Deutsche
  Welle, Radio France and more.
- **SHOUTcast**: the Top 500 by live listeners, then 313 genres.
- **Live365**: about 5,500 independent stations, A to Z.
- **Radio Paradise**: each channel at every quality, up to lossless.
- **Podcasts (Apple)**, **Podcast Index**, **YouTube** and **Television**,
  described further on.

Moving around the tree is easier too:

- Numbers in names sort as numbers, so ACB Media 2 comes before ACB Media 10.
- Opening a folder keeps you on it and says how many it holds. You step in
  when you are ready.
- Browse Stations reopens where you left it.
- Folders usually open at once, because Quill Radio starts loading one as soon
  as you land on it.
- A slow branch says what it is loading. An empty one tells you whether it is
  really empty or the directory could not be reached.
- Where a directory counts its audience, the details show "Live listeners".
- The tree's label is now Alt+T, so Alt+S always opens the Station menu.
- Shift+F10 or the Applications key on any row shows everything you can do
  with it.

**Station > Choose Browse Sources** (Ctrl+Alt+Shift+O) turns branches on or
off. Each row says its state, such as "On. YouTube.", and Turn On or Off flips
it. Or press Shift+F10 on a branch and choose **Hide This Source**. **Source
Options** on a source's menu chooses, for example, Radio Paradise's quality.

#### Stations kept on your computer

More than 62,000 stations from 240 countries come inside the app, so those
branches answer at once and work offline. A few, such as Apple Podcasts,
TuneIn, iHeart and the Internet Archive, always need the internet.

- **View > Station Catalog Status** (Ctrl+Alt+Shift+S) shows what is kept on
  this computer and how fresh it is.
- **Station > Update Station Catalog** (Ctrl+Alt+Shift+G) refreshes it when
  you ask, and says what changed. It also refreshes by itself once a day, and
  you can turn that off.
- If you are offline, the app says so once and carries on.
- Your favorites, own stations and servers are kept separately and never
  touched.

#### Search

Press **Ctrl+F** for Search Stations. Results include radio stations, books,
archive recordings, podcasts, music and YouTube, and each row says where it
came from.

- Results appear as each library answers, without moving your place.
- Pressing Play on a podcast plays its latest episode, and on a book it plays
  the first section.
- Press **Down** in the station name box to reuse an earlier search.
- A row that may not play says so. Quill Radio never guesses.
- **Station > Search Sources** (Ctrl+Alt+Shift+U) chooses which sources are
  searched.

Search understands what people actually type. "Sunny 105.7 Gulf Shores
Alabama" finds the station even though a directory lists it as WCSN.
Frequencies are repaired, so "14.90 AM" finds 1490 and "1009" finds 100.9.
Every source is asked at the same time, so search is much faster. If one is
slow, you hear which, and repeating a search within ten minutes shows the
earlier answer at once.

#### Search inside Browse Stations

In Browse Stations, the Find box (Ctrl+F) searches the branch you are in, in
the best way that branch allows. It also matches descriptions, so you can
search a podcast's episodes by subject. Standing on **Search All Sources**,
typing and pressing Enter searches everything.

#### Adding your own stations

- **Station > Add Custom Station** (Ctrl+N) takes a stream address, a YouTube
  link or a Live365 link.
- **Station > Find Streams from a Website** (Ctrl+Alt+S) finds the stream on a
  station's web page.
- **Station > Import Stations from Playlist** (Ctrl+I) reads all the common
  playlist files, such as M3U and PLS.
- **Station > Export Favorites to Playlist** (Ctrl+Shift+X) writes an M3U
  playlist.
- A playlist file made to cause trouble is refused, and you are told why.

### Listening

#### Keys that work in every window

- Play: **Ctrl+P**.
- Stop: **Ctrl+Period**.
- Pause and Resume: **Ctrl+Space**, for podcasts, recordings, files and
  finished videos. Live radio cannot be paused.
- Rewind live radio: **Ctrl+Shift+Left** goes back 30 seconds, and **Back to
  Live** (Ctrl+Shift+L) returns to the broadcast.
- Volume: **Ctrl+Up** and **Ctrl+Down**, except inside a text box. It moves
  in steps of 10, says "Volume 60 percent", lifts mute, and is remembered.
- Mute: **Ctrl+Shift+O** in every window, and **Ctrl+M** in the main window.
- Play Last Station: **Ctrl+L**.
- Your first ten favorites: **Alt+1** through **Alt+0**.

Every key says what it did. A key that cannot act says why, for example "This
is a live stream, so there is no timeline to move along".

#### Moving through anything that has an end

On a finished video, recording, podcast episode or file:

- **Ctrl+Shift+Left** and **Ctrl+Shift+Right**: back or forward 30 seconds.
- **Ctrl+Shift+C**: the list of chapters. Enter jumps to one.
- **Ctrl+Shift+Comma** and **Ctrl+Shift+Period**: previous and next chapter.
- **Ctrl+Shift+Up** and **Ctrl+Shift+Down**: faster or slower, from a quarter
  speed to four times. **Ctrl+Shift+0** is normal speed again.
- **Ctrl+Alt+J**: go to a time, such as 1:23:45.
- **Ctrl+Shift+W**: where am I, with position, length and chapter.
- **Ctrl+Shift+9**: Skip Silence, which shortens long pauses.

Your speed is remembered for each kind of thing, so a speed chosen for one
recording applies to all recordings.

#### Windows you can move between

Browse Stations, Search Stations, Manage Favorites, Schedule Recording,
Recordings, Downloads, Song History, Now Playing, the Player and Tutorials are
now windows of their own, each in the taskbar and in Alt+Tab.

- Ctrl+Tab and Ctrl+Shift+Tab move between them, and you land on the control
  you last used there.
- Asking for a window that is open brings it to the front.
- Escape, Ctrl+W, Ctrl+F4 or Alt+F4 closes them.
- **Playback > Go to Player** (Ctrl+Shift+G) opens the Player window, with
  what is playing, the position, speed and volume.
- **View > Main Window Shows** chooses what fills the main window: Favorites
  (Ctrl+Shift+1), Browse Stations (Ctrl+Shift+2), Search Stations
  (Ctrl+Shift+3), Radio Recordings (Ctrl+Shift+4) or the Player
  (Ctrl+Shift+5).
- **View > Go To** (Ctrl+G) opens a numbered list of every place in the app,
  and the numbers never change.

#### The main window and the status bar

The main window is now the now-playing line, your favorites, Mute and Volume.
At the time, Alt+M was Mute and Alt+U the volume slider. The now-playing line
is a box you can arrow through and copy.

**View > Show Status Bar** (Ctrl+Alt+Shift+B), then **F6**, takes you into
the status bar. Left and Right move between parts. Enter acts on one: Play or
Stop, Mute, Volume, Record, Sleep timer and the clock. A recording counts down
to its end, or counts up if it has no length.

#### What's playing, and Song History

- **What's Playing** (Ctrl+T) opens a window you can review and copy, and says
  where the title came from.
- **Song History** (Ctrl+Shift+H) keeps up to 200 songs per station, newest
  first, as sentences such as "Your Song by Elton John, heard 10:04, played
  twice". Song Details looks up the release and year, only when you ask.
  Background asks AI for a note, always labelled as written by AI.

#### Shaping the sound

- **Audio > Sound Enhancements** (Ctrl+E): equalizer, compressor, channel
  mode, night mode and broadcast polish, which you hear as you change them.
- **Exact OptiLab processing** can use the real OptiLab Core by Lanes Audio.
  It is off at first. "When saving" is the one to choose: it processes a
  recording once it finishes and never risks the original.
- Stream Polish Auto-Adapt is smoother, and silence or hiss no longer raise
  the level.
- **Audio > Use One Volume for All Stations** (Ctrl+Alt+V) and **Forget Every
  Station's Own Volume** (Ctrl+Alt+Shift+V).
- **Audio > Output Device** (Ctrl+Shift+D) picks the sound card.
- **Audio > Volume Boost** (Ctrl+Shift+B).

OptiLab Core is by Lanes Audio (dgl1984), used with thanks.

#### Continue Listening

**Playback > Continue Listening** (Ctrl+Alt+Shift+L) lists everything you
began and did not finish, newest first, with how far in you are. Files on your
computer keep their place even if you move or rename them. Quill Radio and
QUILL Cast share one place per podcast episode.

#### Staying connected

- A station that drops briefly reconnects on its own, quietly.
- If the connection is really lost, Quill Radio tries three times and tells
  you each time, for example "Reconnecting to KFI AM 640. Attempt 1 of 3."
- iHeart stations such as KFI no longer stop after about 20 seconds.
- While a station is buffering or reconnecting, the status says so.

### Podcasts, YouTube, TV and video

#### Podcasts

- **Podcasts (Apple)** in Browse Stations: choose a country for its top shows
  and the whole genre tree. No key, no account.
- **Podcast Index**: open a show and play its episodes without subscribing.
  It has Trending Now, 112 categories and its own search. A search sends only
  the words you typed.
- Searching for a podcast asks Apple and the Podcast Index together.
- **Subscribe to This Podcast** adds a show to the library you share with
  QUILL Cast, and each show says how many episodes are unheard.
- Each show lists its 25 newest episodes. For an inbox, a play queue,
  automatic downloads and private feeds, use QUILL Cast, which shares the same
  library.

#### YouTube

- Paste a YouTube link into **Add Custom Station** (Ctrl+N) and it becomes a
  station you can play, keep, record or schedule.
- **Station > Add YouTube Link** (Ctrl+Alt+N) files a channel, playlist or
  video.
- **Add from YouTube Playlist** (Ctrl+Shift+Y) adds a playlist's videos to
  your favorites. Run it again later to collect new ones.
- **Import YouTube Subscriptions** (Ctrl+Alt+Shift+Y) reads the subscriptions
  file from your own Google export. No sign-in, and nothing sent to Google.
- Your first link just plays. **Station > Repair YouTube Support**
  (Ctrl+Alt+Y) is there for the day YouTube changes.
- Quill Radio does not download YouTube videos, and cannot use YouTube Premium
  or watch history, because YouTube's terms do not allow it.

#### Described audio and other audio tracks

- **Audio > Audio and Described Audio** (Ctrl+Shift+A) lists every audio
  track a video has, by name, with any described track first.
- **Audio > Play Described Audio** (Ctrl+Alt+D) switches straight to it.
- When a video has a described track, Quill Radio says so once. Switching
  keeps your place. If there is none, it tells you what tracks there are.
- Dubbed tracks are listed by language. One video offers twenty-four.

#### Transcripts

**Playback > Transcript** (Ctrl+Shift+T) opens a finished video's captions or
a podcast's transcript in a box you can read.

- Playing never moves your cursor. Enter on a line plays from that moment.
- Ctrl+F finds text and says the time, such as "Found at 12 minutes 8 seconds.
  Enter plays from here."
- **Links** lists every web address in it. **Save As** keeps a copy as plain
  text or as a subtitle file, and **Open in QUILL** sends it to QUILL.
- Automatic captions say so in their heading.
- Rows with a transcript say "transcript available".

#### Video

**Video > Show Video** (Ctrl+Shift+V) shows the picture of what is already
playing, without restarting it.

- The picture has a real name, never takes focus by itself, and Tab always
  leaves it. Every command is on the Video menu.
- **Captions** (Ctrl+Shift+K) start as white on black and can be made up to
  three times bigger in **Caption Settings** (Ctrl+Alt+Shift+T).
- Also on the Video menu: Video Information (Ctrl+Shift+I), Take a Snapshot
  (Ctrl+Alt+Shift+H), Full Screen (F11), and Video Size (Ctrl+Alt+4 to
  Ctrl+Alt+7).

#### Television

**Television** in Browse Stations has about 9,300 free channels by country
and category. In the United States they are also grouped by state and city,
and a five-digit ZIP code finds that state's channels. Adult channels are left
out. "Which channels can my antenna receive?" opens antennaweb.org. If you
have a TV guide file, the user guide explains how to make channels say what is
on now and next.

#### Spotify (experimental)

Spotify is experimental and off at first. A free account can search and
browse. Playing inside Quill Radio needs Spotify Premium; on a free account,
**Open in Spotify** plays it in Spotify's own app. You need to set up your own
Spotify connection first, and the user guide's Spotify section walks you
through it. Then choose **Station > Connect to Spotify** (Ctrl+Alt+P) and
**Browse Spotify** (Ctrl+Alt+O). Spotify can never be recorded or downloaded.

### Saving and recording

#### Saving files to keep

- **Download** on a row's menu saves it. **Download All Files** on a book saves
  every chapter in order, while you listen to something else.
- One bad chapter costs one chapter, not the book. Progress is counted as "12
  of 40".
- Download is only offered where saving is allowed. Where it is missing,
  asking for it says why.
- Download All tells you how many started, and how many were skipped because
  you already have them.
- **View > Downloads** (Ctrl+Shift+J) is the list of downloads. Open
  Containing Folder finds a file, and a part-finished file picks up where it
  stopped. You choose whether downloads carry on when the window closes.
- **Station > Download Preferences** (Ctrl+Alt+Shift+D) sets where things go.
  A sentence at the bottom says what will happen to the next download.
- A downloaded book plays in chapter order and says each chapter, such as "4 of
  40, The Dead Hand".
- A Creative Commons licence is saved in a text file beside the audio.

#### Recording

- **Record > Record Now / Stop Recording** (Ctrl+R), **Record Station**
  (Ctrl+Alt+R), **Stop All Recordings** (Ctrl+Alt+X), **Schedule Recording**
  (Ctrl+Shift+S), **Recordings** (Ctrl+Shift+R) and **Recording Settings**
  (Ctrl+Alt+Shift+I).
- Schedule Recording takes hours and minutes in separate boxes, and a late
  start still ends on time.
- The Recordings window opens with a summary, such as "Recording, 42 min left.
  Next: KFI at 11:00 tomorrow. 14 recorded."
- When a station drops, recording carries on and the pieces are joined into
  one recording afterwards. If joining fails, every piece is kept and you are
  told why.
- A recording that saved nothing says so, with the reason.
- Recording file names follow your computer's current time zone.
- In Preferences, **Interrupted recordings at launch** chooses Ask each time,
  Always resume them, or Never resume them.

#### Recording while the computer sleeps

A sleeping computer cannot start a recording. Now Schedule Recording tells you
so, Quill Radio holds off sleep as a recording comes near, and it can wake the
computer shortly before one. Both are checkboxes, on at first. Waking the
computer is not available in a portable copy.

#### Winamp keys in the Recordings window

The Recordings window answers to Winamp's classic keys, with nothing held
down: X play, C pause, V stop, Shift+V stop with fade, B next, Z previous.
Left and Right move 5 seconds, Shift+Left and Shift+Right 30. R shuffles, S
repeats, Ctrl+V stops after the current one, T says elapsed or remaining time,
J jumps to a recording by name and Ctrl+J to a time. A preference turns the
letters off if you would rather type to find a recording.

### Favorites and your setup

#### Favorites

- **Mark for Move**, then **Move Marked Above** or **Move Marked Below**,
  moves a station in one step. Moving one in a sorted list switches to your own
  order first, so nothing is lost.
- **Station > New Folder** (Ctrl+Shift+E) works from anywhere.
- **Station > Add Playing Station to Favorites** (Ctrl+Shift+F). Adding one
  you already have says so and takes you to it.
- **View > Sort Favorites**, **Expand All Folders** (Ctrl+Alt+E) and
  **Collapse All Folders** (Ctrl+Alt+Shift+E).
- The last 20 versions of your favorites are kept as backups, and the
  Favorites Manager has **Remove All**.

#### Backing up and moving to a new computer

- **Station > Back Up Stations and Settings** (Ctrl+Shift+U) saves your
  favorites, settings, schedule and, if you like, recordings into one file.
  **Restore from Backup** (Ctrl+Alt+Shift+W) brings it back.
- **Help > Export My Setup** (Ctrl+Alt+Shift+X) and **Import My Setup**
  (Ctrl+Alt+Shift+N) move your favorites, settings, keys and more to another
  computer. Passwords are never included.
- In Preferences, **Data Folder** can point Quill Radio at a folder Dropbox,
  OneDrive, Google Drive or iCloud already keeps in step. If two computers use
  it at once, Quill Radio tells you the next time it starts.

#### Making it yours

- **View > Customize Features** (Ctrl+Alt+C) turns whole areas on or off.
- **View > Text Size**: Normal (Ctrl+Alt+1), Large (Ctrl+Alt+2) and Larger
  (Ctrl+Alt+3).
- **View > Choose Columns** (Ctrl+Alt+Shift+C) chooses what Search Stations
  and Recordings read on each row, and in what order. A line underneath reads
  a sample row as you change it.
- **Station > Quick Actions** (Ctrl+Alt+Q) chooses the order of a row's menu.
- **Help > Keyboard Shortcuts** (Ctrl+Alt+K) changes keys, and **Global
  Hotkeys** (Ctrl+Alt+G) sets keys that work from any program.
- **Ctrl+Alt+Shift+R** shows or hides Quill Radio from any program without
  stopping what is playing.
- **Station > Start Quill Radio with Windows** (Ctrl+Alt+W) and **Resume Last
  Station on Launch** (Ctrl+Alt+L).
- The **QuillVille** menu (Alt+Q) opens other apps in the family.
- **Quillins** (Alt+N) are small add-ons, and one can add its own station
  source.
- Every app in the family has its own icon, told apart by shape and lightness
  as well as colour.

### Community and ACB Media

- **Community > ACB Media Schedule** (Ctrl+Shift+N) lists every published
  programme, with **What Is On Now** (Ctrl+Alt+H), **Upcoming**
  (Ctrl+Alt+Shift+F), which includes your scheduled recordings, and **Refresh
  the Schedule** (F5). Times are now right for every time zone.
- **ACB Media Podcasts** (Ctrl+Alt+I).
- **Community Picks** (Ctrl+Alt+0) and **Suggest a Station or Podcast**
  (Ctrl+Alt+9). A suggestion opens your own email program with the message
  written, addressed to support@community-access.org. A person at Community
  Access reads it. Nothing is posted anywhere public.
- **Station > Update Radio Reading Services** (Ctrl+Alt+F10) refreshes the
  reading services list.
- The **Weather / NOAA** branch lists every NOAA Weather Radio transmitter you
  can hear online.

### Help when you need it

#### Help that answers

- **F1** in any window says what the window is for, then what the control you
  are on does.
- **Help > Tutorials** (Ctrl+Alt+F1) opens 41 guided lessons in six groups.
  Each step says what to do and what you should hear. Try it does the step for
  you, and Follow me notices when you have done it, however you did it.
  Nothing is graded. Type "here" in the filter for lessons about the window
  you came from.
- **Help > Keyboard Shortcuts Sheet** (Ctrl+Alt+Shift+K) lists every key, and
  you can type to filter it. It always shows your own keys.
- **Help > Command Palette** (Ctrl+Shift+P) finds any command by name, in every
  window. On and off commands say their state.
- A dimmed menu item says why it is dimmed.
- **Help > Get Help from Support** (Ctrl+Alt+F2) opens your own email program
  with a message to support@community-access.org already written, including
  your app version, Windows version and screen reader. Nothing is sent until
  you press Send. With no email program, the message goes on your clipboard.

#### Knowing what went wrong

- **View > Audio Health** (Ctrl+Alt+Shift+M) answers "is this going to work?":
  which player is in use, where the sound is going, and whether a recording
  could be saved. It is safe to open during a recording.
- If part of the player or recorder goes missing, Quill Radio says so once,
  with what it costs you and how to fix it.
- **Help > Recent Problems** (Ctrl+Alt+Shift+P) lists recent failures with the
  reason and time. Retry tries again. Nothing leaves your computer.

#### Undo and Quiet Hours

- **Edit > Undo Last Action** (Ctrl+Z) brings back the last Unsubscribe,
  Remove All Downloads, Delete Recording or Mark All as Played, and says what
  came back. Deleted files really return.
- **Help > Quiet Hours** (Ctrl+Alt+Shift+Z), 22:00 to 07:00 at first, stops
  announcements nobody asked for. A key you press still answers, and failures
  always speak. QUILL Cast shares the setting.

#### Bookmarks, timers and statistics

- **Playback > Bookmark This Moment** (Ctrl+Alt+A) and **Help > Bookmarks**
  (Ctrl+Alt+Shift+J).
- **Sleep Timer** (Ctrl+Shift+Z) and **Wake-Up Timer** (Ctrl+Alt+Z).
- **View > Listening Statistics** (Ctrl+Shift+Q).

#### Updates

**Help > Check for Updates** (Ctrl+Alt+U) offers the right download for your
copy, and shows what is new before you update. If there is nothing new, it
says "You are up to date". The daily check when Quill Radio starts only
speaks when there is an update, and you can turn it off in Preferences
(Ctrl+comma).

### Keyboard and screen reader

- Every menu item shows its key, and no two share one. If you changed a key,
  the menu shows yours.
- Speed and chapter keys no longer use Ctrl+Alt+arrows, which screen readers
  use for tables.
- Every message ends as a full sentence, so messages do not run together.
- Everything spoken also goes to a braille display, and an unplugged display
  never stops speech.
- Every question that could lose something starts on No.
- No two controls in a window share an Alt letter.

#### Where each window's menu is

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

### If you are coming from 2.1.2

Your favorites, history, recordings and settings come with you. The installer
upgrades 2.1.2 in place, and a new portable copy offers to copy in a 2.x copy's
favorites the first time it opens.

#### Keys that changed

- **F1** is now help for the control you are on. The User Guide is
  **Ctrl+F1**, and Release Notes stay on **Shift+F1**.
- **Help > Tutorials** is **Ctrl+Alt+F1**, and Product Requirements moved to
  **Alt+Shift+F1**.
- **Ctrl+G** is now Go To, and **Recordings** is **Ctrl+Shift+R**.
- **Restore from Backup** is **Ctrl+Alt+Shift+W**.
- **Stop** is **Ctrl+Period**, and Ctrl+Alt+P is now Connect to Spotify.
- **Update Radio Reading Services** is **Ctrl+Alt+F10**.
- The **Quillins** menu is **Alt+N**, because Alt+Q is QuillVille.
- **Alt+F4** exits, even while a station plays.

#### What moved

- The **Weather** menu is gone. Weather is now in Quill Weather, a separate
  app. The Weather / NOAA branch stays in Browse Stations.
- The main window's play buttons moved to their keys, the Playback menu and
  the Player window.
- One Playback menu became three: **Playback**, **Audio** and **Video**.
- The **Edit** menu now comes after Station.
- Browse, Search, Manage Favorites and Schedule Recording are windows, so the
  menu bar never disappears.
- "Open this window at startup" became **View > Main Window Shows**.

### Things that work better now

- Stations such as KFI no longer stop after about 20 seconds or repeat their
  last few seconds.
- A reconnect no longer leaves you in silence with nothing said.
- A recording that captured nothing now tells you.
- Installing the family's apps in any order now gives you the full player.
- Check for Updates offers the right download.
- The Close button in Browse Stations, Search Stations, Manage Favorites and
  Schedule Recording works.
- The Command Palette key opens the Command Palette.
- Alt+S opens the Station menu in every window, and every menu can be reached
  by its letter.
- The ACB schedule is no longer five hours early.
- The Xiph genre list keeps its genres and its order, and shows the 120 most
  used.
- An outage at LibriVox or the Internet Archive is no longer shown as an empty
  folder.
- SHOUTcast stations play.
- Every way into Browse Stations opens Browse Stations, not Search.
- Upcoming lists your scheduled recordings.
- Escape in the Player no longer closes the whole app.
- Alt+1 to Alt+0, Stop and Mute work in the main window.
- The first-run tip no longer says live radio can be paused.
- Import reads every common playlist file, not only M3U.
- Keymap Diagnostics shows only Quill Radio's own keys.
- Volume is the same in every window, and Volume Up while muted is heard.
- A station that is not a favorite no longer starts at full volume.
- Deleting a recording or favorite keeps your place in the list.
- Add to Favorites no longer claims to add a station you already have.
- Exit from the tray menu really exits.
- A key pressed while Quill Radio starts no longer closes it.
- Sound stops when you exit.

### Good to know

- Live radio cannot be paused. Rewind it with Ctrl+Shift+Left and come back
  with Back to Live, Ctrl+Shift+L.
- Live streams have no transcript.
- Adding a YouTube playlist is a one-time import, not a subscription.
- Your place in each episode is kept per computer.
- Some branches, such as Apple Podcasts, TuneIn, iHeart and the Internet
  Archive, need the internet every time.
- SHOUTcast lists at most 500 stations per genre.
- Spotify playback needs Premium, and Spotify is experimental.
- AudioPub offers only its Discover shelf for now.
- Moving through a recording in the Recordings window needs the full player.

### What may come next

Nothing here has a date. Ideas we are working towards:

- Public radio receivers on the internet, tuned from the keyboard.
- A shared list where fire departments, emergency offices, universities and
  local governments can add their own audio feeds.
- A directory where reading services can add and correct their own listings.
- Looking up AllStarLink and EchoLink nodes.

## Where to learn more

The user guide, **Help > User Guide** (Ctrl+F1), has everything in these notes
in more detail. Its chapters are: Installing Quill Radio; Your first half hour;
Finding your way around; Playing and moving around; What's playing, and how it
sounds; Finding something to listen to; Keeping your favorites; Recording;
Podcasts, books, video and more; The ACB Media schedule and reminders; The
Community menu; Making Quill Radio yours; Safety nets; and When you need a
hand.

**Help > Tutorials** (Ctrl+Alt+F1) has lessons in six groups: Your first hour,
Finding something to listen to, Making it yours, Recording, More than radio,
and Living with it. Play your first station is a good first lesson.

The 2.0 and 2.1 releases have their own notes, Quill Radio 2.0, in the same
docs folder.

If you get stuck, choose **Help > Get Help from Support** (Ctrl+Alt+F2), or
write to support@community-access.org. A person at Community Access reads
every message.
