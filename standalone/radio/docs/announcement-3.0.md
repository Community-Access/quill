# Quill Radio 3.0

**A radio that answers the questions people actually arrive with.**

Version 3.0.2, released 2026-09-28.

Community Access has released **Quill Radio 3.0** for Windows. It
is free, it is part of the QuillVille family, and it is built for people who
listen to their computer rather than look at it.

Quill Radio plays internet radio, podcasts, audiobooks and archive recordings,
records what is on, and schedules what is coming. Everything it does, it does
from the keyboard, and it says what it did.

---

## What 3.0 is about

Version 2.1 opened on an empty favorites tree. That is an accurate picture of
having no favorites, and an answer to none of the questions anybody actually
opens a radio app with. Almost everything in 3.0 follows from taking those
questions seriously.

### You are somewhere, from the first second

The first run is three short screens, not seven, and every one of them names
the real key for what it describes. From the second screen, one button takes
you straight into Browse Stations. The main window shows whichever surface you choose --
favorites, the browse tree, search, recordings or the player -- rather than
opening a second window on top of the one you were in.

### More than thirty branches you can wander without searching for anything

The station directory by country, by language, by what is trending today.
Podcasts by country and genre, with no account anywhere. Whole libraries --
the Internet Archive, LibriVox, Project Gutenberg, Audius, Mixcloud, ccMixter.
NOAA Weather Radio by state, county or SAME code. Radio reading services.
Television from the iptv.org catalogue. None of it needs a key or a sign-in.

### It works before the internet does

A catalogue of stations lives on your own computer, so a search answers the
instant you press Enter -- and still answers when the connection does not. The
live directories layer in behind the local answers rather than holding them up.

### Search now finds the station you meant

This is the newest thing in 3.0, and it came from three listeners who could not
find five stations between them. A query is not a string: "Sunny 105.7 Gulf
Shores Alabama" is a brand, a frequency, a city and a state, and the
directories index two of those.

So the query is taken apart and each directory is asked several narrower
questions instead of one wide one. `14.90 AM` finds 1490 and `1009` finds
100.9. A trailing `FM` no longer loses the station. And naming the state does
real work: Radio Browser knows Sunny 105.7 only as "WCSN 105.7 FM Orange
Beach", so no spelling of "Sunny" could reach it -- but `105.7` inside Alabama
has exactly one answer, and now it arrives first, misspelled city and all.

The merged results are then ordered by which one you most likely wanted: name
*and* frequency above frequency alone, the station in the place you named above
one that merely shares a word, and -- between two equally good matches -- the
one whose stream is known to play, then the one more people listen to.

Typing a station's **web address** works too, in every search box. A site is
scanned for its stream, which is how you reach the stations no directory
carries at all -- and there are more of those than people expect.

### Recording that behaves like a recorder

Record what is playing, or schedule it, and record several stations at once. A
scheduled recording can wake the computer for itself rather than silently
missing the show. A dropped connection reconnects and the parts are joined back
into one file; a recording cut off by a crash is offered for resuming at the
next launch. The Recordings player answers Winamp's keys.

### Live radio you can rewind

Missed what the announcer just said? **Ctrl+Shift+Left** goes back 30 seconds
into a rolling buffer of the live stream, and **Ctrl+Shift+L** catches up
again. Podcasts, recordings and files pause and resume with **Ctrl+Space**.

### Every window can reach the player

The player, browse, search, recordings, favorites and scheduling are **windows**
-- peers, not overlays -- with one menu bar each, one now-playing line, and a
status bar whose cells are actions rather than decoration.

### The app teaches itself

**Help > Tutorials...** (Ctrl+Alt+F1) opens 41 guided tutorials, 281 steps
in all, in six tracks. A lesson runs one step at a time, tells you what you should *hear*
when it worked, and can run the step for you. Tick **Follow me** and it watches
the app and moves on when you have done the thing. The keys a tutorial shows
are read from your own keymap, so they cannot go stale -- and if you rebind a
command, every lesson that mentions it says your key from then on.

### F1 answers, everywhere

Every window states its purpose and then describes the control you are standing
on. Every menu item shows its keyboard route, and no two items in a menu bar
claim the same key -- a rule now enforced by an automated gate rather than by
anybody remembering.

---

## Accessibility is the design, not a feature of it

Quill Radio is built by and for screen-reader users. Some of what that means in
practice:

- **It says what the screen reader will not.** Window titles, control names and
  focus moves are the reader's job; a background result, a state change on a
  control you are not standing on, and the outcome of an action are the app's.
  Saying both is how an app becomes something people turn the speech off for.
- **Sizes are measured in characters, not pixels**, so a readout grows with the
  system font instead of shrinking against it.
- **Nothing is discovered by looking.** Every list says how many rows it has,
  every long operation says it is running, and a source having a bad day says
  so rather than posing as "no matches".

---

## Availability

Quill Radio 3.0 is a free download for Windows 10 and 11, released on
2026-09-27 as version 3.0.1, which replaced the withdrawn 3.0.0; the current
version is 3.0.2, released 2026-09-28. Both
downloads are on the QUILL Releases page on GitHub
(github.com/Community-Access/quill), under the tag `quill-radio-v3.0.2`:

- **`Quill-Radio-Setup-Shared-3.0.2.exe`**, the installer, is the one most
  people want. It sets up the shared QuillVille Runtime if it is not already
  there, then the app, with a Start Menu entry and an uninstaller.
- **`Quill-Radio-Portable-3.0.2.zip`**, the portable copy, unpacks anywhere, a
  USB stick included, and writes nothing to the computer it runs on. Settings,
  favorites and history live in a `data` folder beside the app, from the very
  first launch.

Both are code-signed. **Help > Check for Updates** (Ctrl+Alt+U) offers
whichever of the two you are running, with the release's What's New notes to
read first.

Quill Radio shares its engine with **QUILL**, the full accessible word
processor, and sits beside **Quill Cast** (podcasts), **Quill Weather**,
**Audio Studio**, **Quill Media Player**, **Quill Inkwell**, **Quill
Converter**, **Quill Beacon** and **QUILL Lite** -- one family, one set of
keys, one way of speaking.

Upgrading from 2.x keeps your favorites, your settings and your keymap.

---

## About Community Access

Community Access builds software for blind and low-vision users
that does not ask them to work around it. Everything in the QuillVille family
is free, keyboard-first, and designed with a screen reader running.

Support: support@community-access.org, or **Help > Get Help from Support...**
(Ctrl+Alt+F2) inside the app. A person reads every message.

The user guide (Ctrl+F1 in the app) walks through every feature step by step.
