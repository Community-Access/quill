# Quill Radio 1.0

Welcome to Quill Radio, the internet radio from QUILL in a window of its own.
It opens on your favorites, plays with one key, and tells you what it is doing
as it goes.

Quill Radio has its own menu bar, tray icon and app icon, and it goes further
than the radio inside QUILL ever did. The two share the same radio and the
same saved favorites and settings, so anything new arrives in both at once.

These notes cover 1.0 and the updates up to 1.1.0, newest first. The more
reliable recordings that were once promised here came in Quill Radio 2.0,
which has its own notes.

## The updates after 1.0

### What's new in 1.1.0

#### Nearly every station now plays

Quill Radio 1.1.0 comes with a second, newer player that many media players
use. Quill Radio uses it for you, so there is nothing to set up. With it,
Quill Radio plays nearly every kind of station you will meet, including the
Ogg, Opus and streaming formats that Windows Media cannot play. Many
community, independent and international stations that used to be "found it,
but it will not play" now just play.

The older Windows Media player is still there. In Preferences (Ctrl+comma),
set Playback engine to "Windows Media (classic)" and Quill Radio plays exactly
as it did before. If either player cannot open a station, Quill Radio quietly
tries the other one before telling you about a problem.

#### Pause live radio, and rewind it

Quill Radio now keeps the last part of a live station, about 45 minutes for
most. Pause for the doorbell and carry on where you left off. Missed a
sentence? **Rewind 30 Seconds** (Ctrl+Shift+Left). Catch up with **Forward 30
Seconds** (Ctrl+Shift+Right), or go straight to **Back to Live**
(Ctrl+Shift+L). Every move tells you how far behind live you are.

#### Better sound

- **A second sound card for the radio.** Preferences has **Radio output
  device**. Send the radio to a USB headset and keep your screen reader on the
  main speakers. If you unplug the headset, your choice is remembered, and if
  the device cannot be used, the radio plays through the default one and tells
  you.
- **Volume Boost** (Ctrl+Shift+B) makes a quiet station up to 50 percent
  louder than full volume.
- **Combine channels into mono**, in Sound Enhancements, helps if you hear
  with one ear or use one earbud, so a voice on the other side is never lost.
- **Night mode** lifts the quiet parts so you can listen late without reaching
  for the volume. There are two new presets, **Small Speakers** and **Late
  Night**.
- With the new player, every change in Sound Enhancements takes effect
  straight away, mid-song.

#### Hearing what is playing

- **What's Playing** (Ctrl+T) has an answer on far more stations.
- **It says it the way you would.** Some stations send a jumble of codes
  instead of a title. Now Quill Radio finds the title and artist in it and
  says "Now playing: YOUR SONG by Elton John." In Preferences, **What's Playing
  announcement** lets you choose the wording, for example the artist first.
  Leave it blank for the usual wording.
- **"Buffering..." instead of silence.** When the internet hiccups, Quill
  Radio tells you what is happening while it waits.

#### Finding stations that would not play

- **Stations that used to fail now fix themselves.** It started with Magic
  104.1 in Oklahoma City: listed in the directory, but nothing played, because
  the real stream was hidden behind a player on the station's website. Now,
  when a station will not play, Quill Radio looks for the real stream itself,
  including on the station's own website if you leave that on in Preferences.
  If it finds one, it plays it and remembers it. If it finds several, it sends
  you to Find Streams to choose.
- **Find Streams reaches stations behind a Play button.** Thousands of
  stations put their "Listen Live" on a player whose stream is not written on
  the page. Find Streams now recognises that player and finds the real stream,
  offering both versions when a station has two. It never hands you a wrong
  one.
- **The whole dial, not just the first 50.** Browse Stations shows up to 200
  results at once, most listened first, and **More Stations** loads the next
  page with your cursor on the first new one.

#### Smaller things

- **Alt+F4 can tuck the radio away.** A new Preferences checkbox, **Alt+F4
  minimizes to the system tray**, keeps the music playing in the tray. It is
  off at first.
- **Record the station exactly as sent.** Recording Settings has a new format,
  **Raw stream**, which saves exactly what the station sent with nothing
  changed. It is the best starting point if you edit your own recordings.
  This came straight from a listener's request.
- **Volume keys work in Browse Stations**, from anywhere in the window, and say
  the new level.

### What's new in 1.0.2

- **Volume keys work** in the Favorites list, where you land when the app
  opens.
- **Volume stays where you put it.** A favorite always comes back at the volume
  you left it.
- **A real three-band equalizer.** Sound Enhancements has Bass, Mid and Treble
  sliders, each with a proper name your screen reader says. The old presets,
  Flat, Bass Boost, Voice Clarity and Podcast, set all three at once.
- **Sound Enhancements remembered for each station**, so a jazz station and a
  talk station can sound different. **Reset to Default** puts one station back,
  and Preferences can reset them all.
- **Exit or Minimize to Tray, your choice.** Closing while something plays asks
  what you want, with a "Don't ask me again" box. Preferences has a matching
  **When closing the window** setting.
- **Check for Updates shows a real window** when you are up to date, and Quill
  Radio checks once a day when it starts, silently unless there is something
  new.
- **Quieter by default.** Windows no longer say "Entered" and "Exited" unless
  you turn on **Announce dialog transitions** in Preferences.
- **The documents are on the Help menu.** User Guide, Release Notes and
  Product Requirements open in your browser.
- **Sound Enhancements** arrived, with an equalizer and **Even Out Volume**,
  which lifts quiet parts and tames loud ones. Recording Settings can apply
  them to recordings too.
- **SomaFM joins the search**, in the same results.
- **Preferences** (Ctrl+comma) is new, starting with Resume Last Station on
  Launch and the daily update check.
- **OK means OK.** Recording Settings, the Wake-Up Timer and Add Station say OK
  instead of Save, like other Windows windows.

## What 1.0 brought

- **Your folders, on the front page.** The main window is your favorites, in
  the folders you make, with everything you can do one Shift+F10 away. **New
  Folder** (Ctrl+Shift+E) makes a folder right where you are.
- **Favorites first.** The app opens on your favorites, and Enter plays.
  **Play Last Station** (Ctrl+L) brings back what you had on, and **Resume Last
  Station on Launch** means opening the app is all you ever do. **Recently
  Played** keeps your last fifteen stations close.
- **A real Favorites Manager.** Folders inside folders, search across names,
  countries and tags, Move Up and Move Down, and Mark and Move for long hops.
  Rename a station to what you call it, and rename folders with F2. Deleting a
  folder keeps its stations.
- **What's Playing.** Ctrl+T says the song or show, and you can have new titles
  read as they change.
- **Recording, grown up.** Record what you are hearing, record a different
  station while you listen to something else, or schedule shows once, daily or
  weekly, picking from your favorites. The **Recordings** list shows what is
  recording now, what is recorded and what is scheduled. Recordings ride out
  short drops in the connection.
- **Wake up with the radio.** The sleep timer has a twin: choose a favorite and
  a time, once or every day. Quill Radio needs to be running, and the tray
  counts.
- **Never two things at once.** Starting anything stops whatever else was
  playing, in every app in the family.
- **Each favorite remembers its own volume.**
- **Your keyboard's media keys** control the radio from anywhere, even from
  the tray.
- **The Command Palette** (Ctrl+Shift+P) finds any command by name.
- **One set of favorites and settings**, shared with QUILL and QUILL Cast. Set
  it up once and have it everywhere.
- **An installer and a portable copy.** The portable copy keeps your whole
  radio on a USB stick. Everything it needs is included, and Check for Updates
  offers the right download for your copy.
- **Reporting a problem from the Help menu**, with no account needed.
- **Spoken feedback everywhere**, through JAWS, NVDA or Narrator, without
  taking your focus.

### What Quill Radio is not

It is not QUILL with some menus taken away. It is just the radio. QUILL's
editor, AI, transcription, braille and speech tools are not installed at all.

### Good to know

- Quill Radio runs on Windows 10 or 11, on ordinary 64-bit computers and on
  ARM computers through Windows' own emulation. You do not need to install
  anything else.
- At the time, releases were not yet signed, so Windows SmartScreen could warn
  you the first time. Choosing More info, then Run anyway, started it.

## Where to learn more

The user guide, **Help > User Guide** (Ctrl+F1), covers today's Quill Radio,
starting with Chapter 2, Your first half hour.

**Help > Tutorials** (Ctrl+Alt+F1) starts with the lessons in Your first hour,
beginning with Play your first station and Keep a station, and find it
tomorrow.

If you get stuck, choose **Help > Get Help from Support** (Ctrl+Alt+F2), or
write to support@community-access.org. A person at Community Access reads
every message.
