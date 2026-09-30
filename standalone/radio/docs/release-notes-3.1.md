# Quill Radio 3.1 Release Notes

Version 3.1.0, released 2026-09-29.

Quill Radio 3.1 is the release where the radio can answer you. **Ask QUILL
Radio** holds a conversation about what is playing, on the ChatGPT plan you
already pay for; the radio watches your podcasts and tells you what arrived;
it keeps a list of everything it has told you; and you can leave a note to
yourself on any station. Twelve fixes came with them. Everything below is
written for a listener who uses a screen reader; every step names its key.

The 3.0 line -- the launch and its four follow-up releases, 3.0.1 to 3.0.4 --
has its own document, `release-notes-3.0.md`, and the changelog lists every
change by version.

## What's new in 3.1.0

Four new things, and twelve fixes. Quill Radio can now answer questions about what is playing on the ChatGPT plan you already pay for, watch your subscribed podcasts for you, keep a list of what it has told you, and hold a note you write to yourself about any station or podcast.

### Ask QUILL Radio: a conversation that knows what is playing

Every radio listener has asked the air a question. Who is this? What was that
song? Where is this station, and who runs it? What did the presenter just say
the book was called? From 3.1.0 Quill Radio can answer, and it answers about
*what you are hearing*, because the station and the title the stream is
announcing go with every question you ask.

**Community > Ask QUILL Radio...** (**Ctrl+Shift+8**) opens a conversation
window of its own -- on the Window menu, one Ctrl+Tab away, with the transport
keys still live, so the player is never further away than usual. Type in **Your
message** and press Enter; the reply is read aloud as it arrives and added to
the conversation above, where you can read it again word by word. Or press
**Ask About What's Playing** and type nothing at all: it asks about the song and
the station for you, and each press asks the next question. It is a
conversation, so "and where can I hear more of them?" follows on from the
answer before.

**It runs on your own ChatGPT plan.** There is no key to paste, no bill per
question, and nothing goes through QUILL's servers. **Community > Use My
ChatGPT Subscription...** (**Alt+F5**), then **Continue with ChatGPT**: your
browser opens on OpenAI's own sign-in page, you allow "QUILL Radio" to use
your plan, and you come back signed in. The model is your plan's own list, read
from your account, with the first chosen for you. **Allow web search** is off
until you check it; on, the assistant may look up a schedule, a news story a
presenter mentioned, or a new release, and tell you what it found.

**It works from text, not from sound.** Ask QUILL Radio never listens to the
stream, records anything or transcribes speech. What it knows is what the app
already knows in words: the station's name, and the title the stream announces
in its metadata when it announces one. If a station sends no titles, the
assistant knows the station and not the song, and says so. A question about
what a presenter just said is answered from what the model knows about the
programme, not from hearing it.

**Turning web search on** takes four keystrokes: press **Alt+F5** (Community >
Use My ChatGPT Subscription; sign in first if you have not), press **Alt+W** or
Tab to **Allow web search**, press **Space**, and hear "Web search is allowed."
It is saved at once. Space on the same checkbox turns it off again. With it on,
"what time is the news on this station" or "what did the presenter mean by the
story about the bridge" can be looked up rather than guessed.

What you ask counts toward your plan's usage, which OpenAI enforces; when a
limit is reached the window says so in words, and **Open ChatGPT Usage** shows
when it resets. Only a refresh token is kept, in Windows' credential store,
under Quill Radio's own name -- your password is never seen. **Sign Out** (two
presses) asks OpenAI to revoke it and forgets it here; **Forget on This
Computer** forgets it here only; neither button exists until you are signed
in. Quill Radio, QUILL Lite and QUILL each sign in as themselves, and appear as
themselves under Apps in ChatGPT's settings, so signing one out leaves the
others as they were. Ask QUILL Radio is off in Safe Mode.

Some of what people will ask it, with a station on:

- "What is this song, and who made it?"
- "Tell me about this station: who runs it, where, and what it plays."
- "This is in Spanish. What are they talking about?"
- "Explain the rules of the sport they are commentating on."
- "Is there a podcast like this one?"
- "What time is the news on this station?" (with web search allowed)

**Quick questions, and the three that know you.** A **Quick questions** list
sits above the message box with nine prepared questions. Six ask about what is
playing and send nothing more. Three ask about you, and this is where the radio
becomes yours: **Recommend stations like my favorites** sends the names of your
favorites and asks for five you do not have; **What have I been hearing on this
station lately?** sends the songs Quill Radio has logged there and asks what
they add up to; **Suggest something new from everything I have played** sends
the stations you have played recently, with a few songs from each, and asks for
three that would be new to you. Each one says, before you send, exactly what it
attaches and how many -- "This question also sends the names of your 32
favorite stations" -- and puts the question in the box for you to press Enter
on, or change, or not. Arrow the list as much as you like; only Enter, or Use
This Question, chooses. Nothing about you leaves the computer unless you choose
one of those three, and nothing at all goes on a timer: every question is one
request on your plan, made when you ask.

### Quill Radio watches your podcasts for you

Quill Radio has always refreshed a podcast when you opened it. Now it can check
them on its own and tell you what arrived.

**How often** is in Preferences, under *Check subscribed podcast feeds*, from
*Manually only* through *Once a day*. Quill Radio and QUILL Cast read the same
setting now, so turning it on in either turns it on -- they used to keep
separate ones, which meant choosing a cadence in one app did nothing in the
other. If you had already chosen one in Quill Radio, it is carried over.

**Per podcast** too. Each podcast's own settings can say *Manually only* while
the rest keep the shared cadence, so a finished show or one that publishes twice
a year stops costing you a request every hour. Refresh on a row always asks,
whatever the setting says -- a switch that could strand a podcast would be a
trap rather than a preference.

If you are subscribed to nothing, or everything is set to never, no check
happens at all. Nothing wakes up to do nothing.

### And tells you in the way you asked

*When new episodes arrive* -- globally, or on one podcast:

- **Notify me** -- a desktop notification and a short sound.
- **Quietly** -- it goes in the Notifications list and nothing is said. This is
  what makes a daily show bearable: nine new episodes is something you want to
  be able to find, not something you want announced nine times.
- **Not at all** -- nothing is recorded.

**Quietly is the default.** An app that starts putting notifications over what
you are reading, because you subscribed to something, has made a decision that
was yours to make.

Quiet hours hold back the notification and the sound. They deliberately do not
hold back the list entry: being quiet about something is not the same as never
having been told.

### Notifications: what you have been told

**Ctrl+Alt+Shift+F3**, or Help > Notifications.

A desktop notification is a good way to be told something and a poor way to
remember it. It appears over whatever you were reading, it leaves on its own
schedule, and if your screen reader was in the middle of a sentence when it
arrived you may never have heard it at all.

So the notification is not the record -- this list is. One line for each thing,
newest first, and anything you have not read yet begins with the word "New".
Press Enter on a row to open what it was about. **Mark All as Read** clears the
markers without removing anything; **Clear List** empties it, and removes only
the record of being told.

It is one list shared with QUILL Cast, so whichever app is open can show you
what the other found.

### A note to yourself about any station

**Note to Self...** on any row, next to Set a Reminder.

Write whatever you like -- "the morning show is the good one", "only worth it on
Sundays", "the 6am repeat is the one with the interview" -- and it is read back
in the details pane the next time you arrow onto that row. That is the whole
point: a note you have to open a window to find is a note you have to remember
you wrote.

Emptying the box removes it. It is kept against the station's address rather
than its name, so renaming it, re-sorting your favorites or refreshing the
catalogue does not lose it or move it onto somebody else's row.

### Choosing a sound card switches to it, or says why it cannot

A listener chose a different device in **Audio > Output Device...** and the
sound stayed where it was. The playback engine itself was not at fault: mpv
switches devices at runtime and on reload, and we watched it do so on a
machine with two sound cards. What went wrong is that when the engine could
not *open* the chosen device -- a Bluetooth headset asleep, a card another
program was holding, a device whose Windows id had changed -- the station
was quietly rescued on Windows Media, which plays on the device Windows gives
the app, and nobody was told.

From 3.1.0:

- A playing station switches device the moment you choose one, live, with no
  break in the sound.
- If the device cannot be opened, you hear which one, and the setting goes
  back to what it was: "Speakers (Logi USB Headset) could not be opened, so
  the output device is back to System default." The sound stays on the mpv
  engine, on the device that was in use before, and Preferences agrees. Wake
  or plug in the device and choose it again.
- A saved device that will not open when Quill Radio starts is given back the
  same way, so no copy is stuck with a setting it cannot honour.
- If a station will not play on the mpv engine at all and falls back to
  Windows Media, that is said too.
- Every one of these decisions is written to the log.

One more thing worth knowing: Windows calls both a laptop's built-in card and a
USB headset "Speakers", so the list reads "Speakers (Realtek High Definition
Audio)" and "Speakers (Logi USB Headset)". The make in brackets is the part
that tells them apart.

### Windows Media plays to the sound card you choose

Quill Radio's Windows Media engine is Windows' modern media player now, and it
can be pointed at a device. So **Audio > Output Device...** moves the sound
whichever engine you are on: choose a card and the station moves to it at once,
with no break and no reconnect.

If the device cannot be opened -- a headset asleep, a card another program is
holding -- you hear which one, and the setting goes back to what it was rather
than naming a device you cannot hear.

On an older copy of Windows that does not offer the modern player, Quill Radio
falls back to the classic control, which has no way to choose a device at all.
There, and only there, choosing a device says so in one sentence and opens the
route that does work: Windows' own Sound settings, where under **Volume mixer**
every app has its own output device and the choice sticks across restarts. No
question first.

### Preferences names the engines this copy has

The Playback engine rows are built from what is installed. With the mpv engine
present: Automatic (recommended, uses mpv), Windows Media, mpv. Without it,
there is no mpv row, and Automatic reads "Automatic (uses Windows Media; mpv is
not installed)". A row for an engine that is not there was a choice that did
nothing. The Windows Media row reads "Windows Media (classic)" only on a
machine without the modern player, so the name tells you which one you have.

### Ctrl+T says the title every time

What's Playing said station, title and artist the first time and only the
station after that, though Copy still copied all three. Each press was opening
a fresh window, and a screen reader reads a brand-new window once. A second
press now refreshes the window that is already open and speaks the text.

### Enter in Preferences presses OK

After changing a dropdown, Enter did nothing. It now presses OK from anywhere
in the dialog except a button or a multi-line box. This is shared with every
QuillVille app's Preferences.

### Delete on a source branch hides the source

On a top-level branch such as Podcasts, Delete now hides the source, as it did
in earlier versions and as Hide This Source on the context menu does. Reset
Sources to Default brings it back.

### A minimized window comes back when you ask for it

A listener wrote that the recordings list was out of reach: **Record >
Recordings...** and Ctrl+Shift+R did nothing, though the folder itself was
fine. Since 3.0 every big surface -- Recordings, Browse Stations, Search
Stations, Favorites, the player -- is a window of its own, and asking for one
that is already open brings it forward instead of opening a second copy. A
window that had been minimized, from the taskbar, Windows+M or Windows+D,
counted as already open and stayed minimized: showing it did nothing and
raising it did not restore it, so the command went silent.

From 3.1.0 the window is restored first, then brought forward with focus on
the control you left it on. If Recordings... still does nothing for you,
send `%APPDATA%\Quill\logs\QuillRadio-launch.log` (or `data\logs\launch.log`
beside a portable copy) to support: since 3.0.4 anything the app could not do
is written there.

### Starting with Windows works again, and the installer repairs it

A listener who had set Quill Radio to start with Windows was met at every login
by a box reading "Unhandled exception in script" and "Failed to execute script
'runtime_launcher'", instead of the radio.

Quill Radio runs on a shared engine that the apps in the family use together.
Builds from last summer up to 3.0.1 wrote the "start with Windows" entry as that
engine on its own, with nothing to say which app to open. Run that way the
engine tried to explain itself in writing -- and an app started at login has
nowhere to write to, so the attempt to explain was itself the error.

3.0.2 fixed both halves: the engine can always write, and started on its own it
opens the app you have installed. Quill Radio has also repaired the entry every
time it opened since. But that repair needed you to open Quill Radio, and the
broken entry is the one thing stopping it from opening -- and nothing told you
that opening the radio by hand would cure your login.

From 3.1.0 the installer repairs the entry while it installs, so the next login
is right whether or not you open the radio first. It writes this copy's own
`QuillRadio.exe`, so the entry keeps working through future engine updates. If
you never asked for Quill Radio to start with Windows, nothing is added; a
portable copy never touches the computer it visits; and if your workplace locks
the registry, the install still succeeds.

If a login still opens the wrong thing, turn the setting off and on again with
**Station > Start Quill Radio with Windows**, which rewrites the entry from
scratch.

### Windows knows what you are listening to

Press a volume key and Windows shows a small "now playing" panel; the same
information is on the lock screen. Every media app fills that in. Quill Radio's
was blank.

It now carries the station you are listening to, with the song underneath when
the stream sends one. Your screen reader reads that panel when it appears, so
you can ask the computer what is playing rather than having to come back to
Quill Radio to find out.

Two things it deliberately does not do. It does not take over your keyboard's
media keys -- Quill Radio already answers those itself, including from the tray
and when another window has focus, and that is unchanged. And it does not say
anything out loud: the panel is there to be read when you open it, not
announced at you every time a song changes.

Live stations also now ask Windows to keep them current rather than smooth:
being half a minute behind is worse than an occasional rebuffer on live radio,
and there is nothing to rewind to anyway.

### Preferences opens at once

Opening **Preferences** took two seconds or more, every time.

The output-device list behind that window asked Windows for every device on the
computer and then picked the sound cards out afterwards. On a developer's
machine that was 4,048 devices, and 2.4 seconds, to find 2. Quill Radio now asks
Windows for audio devices instead of for everything, which takes about 8
milliseconds, and it remembers the answer for a few seconds so opening
Preferences twice does not ask twice.

Two things came with it. The old query could also time out and hand back an
empty list, so the device list sometimes appeared with nothing in it -- that is
gone. And an empty answer is never remembered, so a bad moment cannot turn into
a stretch of "no devices".

### Running from a source checkout finds mpv

For anyone building Quill Radio from the source tree: the playback engine list
showed only Automatic and Windows Media, because the search for the mpv engine
looked at every place a *released* copy keeps it and never at the one a
checkout actually uses. It looks there too now. An installed or portable copy
is unchanged, and a released build still never reads a build folder.

### A portable copy's favorites import now imports

A portable copy that had been opened once had an empty favorites file, and
the "copy my favorites" question, answered Yes, copied nothing and was
remembered as done. An empty favorites file is now replaced; anything the
copy already has is still left alone.

## Where to learn more

- **Help > User Guide** (Ctrl+F1) has a step-by-step section for every window
  named here, including "Ask QUILL Radio, step by step" and "Use My ChatGPT
  Subscription, step by step" under The Community menu.
- **Help > Tutorials** (Ctrl+Alt+F1) walks you through the radio one lesson at
  a time.
- `release-notes-3.0.md` covers the 3.0 launch and 3.0.1 through 3.0.4.
- Questions and problems: **Help > Get Help from Support** (Ctrl+Alt+F2), or
  write to support@community-access.org. A person reads it.
