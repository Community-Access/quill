# Quill Radio 2.0

Welcome to Quill Radio 2.0. This release is about recordings you can trust:
if you schedule shows, leave long recordings running while you are away, or
have ever come back to find a recording cut short or missing, it is for you.

It also gives you more to find, because iHeart and TuneIn now join the search.
And Quill Radio is the same radio as the one in QUILL, so everything here
reaches QUILL too.

These notes cover 2.0 and the updates up to 2.1.2, newest first. Everything
after that, including all of Quill Radio 3.0, has its own notes, which **Help
> Release Notes** (Shift+F1) opens.

## The updates after 2.0

### What's new in 2.1.2

A quick update for three things you told us about, two of them from 2.1.1
itself. Thank you for the fast, clear reports.

- **One-click updating works again.** On 2.1.1, **Install and restart** could
  stop with a "decompression bomb" message and send you off to update by hand.
  A safety check meant for documents was turning away the real update, which
  is much bigger. Now it lets a full update through, and your favorites,
  recordings and settings are kept.
- **Favorites keep the order you gave them.** Some of you updated and found a
  hand-sorted list suddenly in A to Z order. Now an older favorites list keeps
  its own order. If an earlier update already rearranged yours, choose
  **Unsorted** in Preferences and your order comes right back.
- **Dictation in the Speech Hub no longer closes the app** on an older copy.

### What's new in 2.1.1

2.1.1 is about weather radio done properly, and about a kind of station that
matters to this community and has never been easy to find: the radio reading
service.

#### NOAA Weather Radio, from a real directory

The **Weather / NOAA** branch in Browse Stations now lists the actual NOAA
Weather Radio transmitters. Open it and you get the states. Open a state and
you get its transmitters, each named with its call sign, frequency and town,
such as "KHB36 162.550 MHz Manassas". Press Enter to play the best internet
stream for it. You can favorite, record and schedule them like any station.

- **Search speaks weather radio.** Type the 6-digit county code your weather
  alert radio uses, a call sign, or a county and state such as "Fairfax, VA",
  and you get the exact transmitters.
- **Your local transmitter, in one step.** At the time, **Weather > Listen to
  your Local NOAA Weather Radio** used the weather location you had saved and
  just played it.
- **It works offline.** A complete list of 1,035 transmitters, covering every
  state and territory, comes inside the app. **Update NOAA Weather Radio
  Directory** fetches the newest list whenever you ask.

#### Radio Reading Services

For decades, radio reading services have had volunteers read newspapers,
magazines and grocery ads aloud for people who are blind or print-disabled.
Finding their internet streams has always been word of mouth. A new **Radio
Reading Services** branch in Browse Stations gathers them: WRBH Reading Radio
in New Orleans, Sun Sounds of Arizona, CRIS Radio, the KPBS and WKAR reading
services, ACB Media 1 to 5, the NFB Radio Network, Voice Corps and more.

Twenty services come with the app, so the branch is never empty, even
offline. They show up in Search by name, tag or state, and **Station > Update
Radio Reading Services** refreshes the list when you ask. Play them, favorite
them, and record your evening paper.

Both lists stay offline in Safe Mode.

#### Two more from your feedback

- **iHeart is something you can browse.** Browse Stations has an **iHeart**
  branch that opens into genres, and each genre into A to Z. You can go to
  Country, then the letter K, then play, without typing a thing.
- **Choosing SomaFM as the source no longer hides SomaFM stations.** "Groove
  Salad" now shows up whichever matching source you choose.

### What's new in 2.1.0

#### Weather, in words

2.1.0 added a **Weather** menu with free official weather in plain, spoken
text, with no account. (In 3.0, weather moved to its own app, Quill Weather.)
You searched for a place by ZIP code, city, county or address, picked the
right one from a list, and opened **Weather Now**. It read:

- any active watches, warnings and advisories first, with the full official
  instructions;
- a full paragraph of current conditions, from temperature and wind to the UV
  index and air quality;
- the National Weather Service forecast, period by period;
- an outlook of up to 16 days.

Every value was written out for listening, such as "the wind is blowing from
the west-northwest at 5 miles per hour" rather than "WNW 5 mph". You could
turn each detail on or off, and keep several places with **Add Location** and
**Remove Location**. **Quick Weather** spoke a one-line summary, and **Active
Alerts** went straight to the alerts. It was always an extra tool, never a replacement for a weather radio,
emergency alerts on your phone, or local emergency instructions.

#### One tree for browsing every source

You asked to pick a source like SomaFM and just see its stations, without
typing a search. So **Browse Stations** became its own window: one tree whose
branches are the sources. Open a branch and its stations appear. Press
**Enter** to play, and **Shift+F10** for everything else: Play or Stop, add or
remove a favorite, copy the stream link, open the station's website, and
Refresh. **Search Stations** stays a separate window with your cursor already
in the search box.

The branches were:

- **Favorites**, at the top, with your own folders and stations.
- **Popular Stations**, the most listened stations right now.
- **Weather / NOAA**, NOAA Weather Radio streams.
- **ACB Media** and **NFB Radio**, the accessibility community's own streams.
- **SomaFM**, its whole line-up at once.
- **TuneIn**, as real folders: Music, Talk, Sports, Local Radio, By Location,
  By Language and more.
- **Community M3U (Music Genres)**, a big community catalog by genre, from the
  m3u-radio-music-playlists collection by junguler, with our thanks.
- **Xiph / Icecast Directory**, the long-running free directory, by genre.

#### Smaller things you will notice

- **Move a favorite from the keyboard.** In your own (Unsorted) order, press
  **Alt+Shift+Up** or **Alt+Shift+Down** to move a station within its folder.
  Quill Radio tells you where it landed, such as "Moved down, now above WABC."
- **Update in one click.** Choose Download, then **Install and restart now**.
  Quill Radio installs the update and opens again, with every favorite,
  recording and setting kept.
- **Only one copy at a time.** Starting Quill Radio while it is already
  running, even in the tray, now brings the running copy forward.
- **The Record button tells you when you are recording.** It changes to **Stop
  Recording** while a recording runs, and back to **Record** after.
- **Volume changes are quiet again.** Holding Ctrl+Up on a saved station used
  to repeat the station's name at every step. Now you just hear "Radio volume
  60", "Radio volume 70".
- **The Country list stays put while you arrow through it.** A search now only
  runs when you ask for one.
- **No bitrate for a raw recording.** Recording Settings shows Quality only
  for the MP3 and OGG formats, where it does something.
- **Search finds stations by branding and call sign.** "103.1 Austin", "1031
  Austin" and the station's number all find the same station.
- **Exiting after a recording works.** Quill Radio no longer stops answering
  when you close it after recording.
- **SomaFM search ignores spacing and punctuation**, so "GrooveSalad" finds
  "Groove Salad".

### What's new in 2.0.2

#### Hear Sound Enhancements as you change them

Move any control in **Playback > Sound Enhancements** and you hear the change
on what is playing straight away. **OK** keeps it. **Cancel** or **Escape**
puts everything back. Every setting can now belong to one station: open the
window while a favorite plays to give that station its own sound, or with
nothing playing to set the default for every other station.

#### Broadcast polish

Sound Enhancements has a new broadcast polish section, adapted with thanks
from OptiLab Core by Lanes Audio (dgl1984). Choose **Podcast Leveler** for
speech, **Stream Polish** for music, or **Smooth Limiter** for gentle peak
control. It evens out stations that are much louder or quieter than each
other, which is lovely for talk and for recordings you leave running.

#### Record as many stations at once as you like

Before, Quill Radio could only record one thing at a time, so overlapping
scheduled shows lost out. Now every recording runs on its own. Overlapping
shows all record, and you can record one station while you listen to another.

- **Maximum simultaneous recordings**, in Recording Settings, can set a limit
  for a slower computer. Zero, the default, means no limit.
- **Record Now** records the station you are on, and pressing it again stops
  that recording only.
- **Stop Recording** in the Recordings window stops the one you chose. **Stop
  All Recordings** stops them all.
- The Recordings window shows each recording with its own time.
- After an unexpected close, Quill Radio offers to carry on with all of them
  in one question.

#### More

- **Left only and Right only now play in one ear.** In 2.0.1 they played in
  both. Now you can keep the radio in one ear and your screen reader in the
  other.
- **Sort your favorites** A to Z, Z to A, or keep your own order, in
  Preferences (Ctrl+comma). A folder can have its own sort.
- **Import Stations from Playlist** reads an M3U playlist into the folder you
  choose, and asks what to do about stations you already have.

### What's new in 2.0.1

- **A recording no longer stops after a minute on a small hiccup.** A brief
  problem at the station now reconnects as it should.
- **You know when recording has begun.** You hear "Recording started" and the
  station's name.
- **Review and copy What's Playing.** **What's Playing - Review and Copy**
  shows the title and artist in a box you can arrow through letter by letter,
  with a Copy button. **Copy What's Playing** copies it straight away.
- **Channel mode**: Stereo, Mono, Left only or Right only, for all stations or
  one.
- **Turn a recording down while it plays.** Ctrl+Up and Ctrl+Down work in the
  Recordings window too.

## What 2.0 brought

### Recordings you can trust

#### A recording carries on after a restart

This was the worst one. You started a recording, Quill Radio or Windows
closed unexpectedly, and the recording was simply gone.

Now Quill Radio remembers a recording in progress. The next time it opens, it
moves any finished piece into your recordings folder where you will find it.
Then, if the show has not ended, it asks you once:

> A recording of WQXR was in progress until 9:00 AM. Resume it for the
> remaining 12 minutes?

**Resume** (Enter) records the minutes that are left. **Skip** (Escape) leaves
it. **Don't ask me again** remembers your answer, and you can change it later
in Preferences.

#### Scheduled recordings start even when Quill Radio is late

A recording set for 8:00 used to be missed if Quill Radio only got there at
8:01. Now a scheduled recording starts any time during the show and records
the rest of it. If it fails to start, it tries again while the show is still
on. When two shows are due at once, you are told, and neither is quietly
lost.

#### The Recordings list keeps your place

The Recordings list used to jump back to the top every time it refreshed. Now
it keeps your place and your selection. Its counts are right, the recording in
progress shows a running time, and the tray says "(recording)" while one runs.

#### Recordings survive dropped connections

- If the station drops at minute 50 of an hour, Quill Radio records the last
  10 minutes, not another hour.
- A recording never overwrites an earlier one. A second file with the same
  name gets "(2)", "(3)" and so on.
- If the station has really gone, or your disk is full, Quill Radio stops
  trying rather than filling your folder with empty pieces.
- If Quill Radio closes unexpectedly, the recording stops with it, and closing
  the window never hangs while a recording finishes.

### More stations: iHeart and TuneIn

Search now includes **iHeart** and **TuneIn**, two of the biggest station
directories, in the same list as before. Each result says where it came from,
and you play it the same way. Neither needs an account.

To steer a search, a **Source** list narrows it to one directory, and the
**Tag/genre** and **Country** boxes are now lists you choose from, so you never
have to guess a spelling. **Find Streams from a Website** also understands a
TuneIn or iHeart page. Both are off in Safe Mode, and QUILL and QUILL Cast can
find these stations too.

### Scheduling recordings, with real editing

The schedule used to let you add an entry or delete it, and nothing else. Now
you can:

- **Edit** an entry: its station, time or length.
- **Duplicate** an entry, to set up the same show on another day.
- **Turn an entry off and on** without losing it. An entry that is off says
  "(disabled)".
- **Type the time your way**, "7:30 PM" or "19:30".
- **Give an entry its own time zone**, so a show quoted in Eastern time records
  at the right moment wherever you are.

### What's Playing reaches more stations

When a station will not say what is playing the usual way, Quill Radio now
asks the station's own server for the title. So many stations that used to
answer with silence now tell you the song. It only ever asks the server you
are already listening to, and it is off in Safe Mode.

### When something needs looking into

Preferences (Ctrl+comma) has **Verbose logging**, which records more detail,
and **Log folder**, so you can keep the log somewhere easy to find and send to
support. Recording problems are now written to the log as well.

### Built on 1.1

Everything 1.1 brought is still here: the newer player and the classic
Windows Media one, nearly every kind of station stream, a second sound card for
the radio, pausing and rewinding live radio, Volume Boost, Sound Enhancements,
Alt+F4 to the tray, and automatic update checks. The Quill Radio 1.0 notes tell
that story.

### Good to know

At the time, releases were not yet signed, so Windows SmartScreen could warn
you the first time. Choosing More info, then Run anyway, started it.

## Where to learn more

The user guide, **Help > User Guide** (Ctrl+F1), covers today's Quill Radio.
For recording, read Chapter 8, Recording. For finding stations, read Chapter 6,
Finding something to listen to.

**Help > Tutorials** (Ctrl+Alt+F1) has a Recording group of lessons, starting
with Record what is on now and Book a show that has not started yet.

If you get stuck, choose **Help > Get Help from Support** (Ctrl+Alt+F2), or
write to support@community-access.org. A person at Community Access reads
every message.
