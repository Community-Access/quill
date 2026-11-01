# QUILL Media Player — User Guide

The QUILL Media Player is an accessible audiobook and media player built for
people who read with a screen reader and a braille display. Everything works from
the keyboard, everything important is spoken, and nothing hides behind a
mouse-only control. This guide explains every feature and every shortcut, names
every safeguard, and states honestly what is available today versus rolling out.

You can use the player two ways — both run the same code and share the same
library, bookmarks, resume positions, and settings:

- **Inside QUILL** — from the Tools menu / command palette.
- **As its own app** — **Quill Media Player**, a tray-resident window you can open
  on its own (Start Menu, or the QuillVille launcher).

A book you start in one continues in the other, at the same place.

> **What's available now.** Nearly everything in this guide is built: playback and
> **chapter navigation as a tree**, resume, bookmarks, **Go to Position (H:M:S)**, the
> **10-band equalizer and DSP**, **DAISY navigation** (single- and multi-file), the
> **Book Library** (LibriVox), the **sleep timer**, the **mini-player**, the
> **multi-field status bar** (F6 review), the Magical **welcome-back** recap, the **AI
> chapter summary/recap**, and **voice commands** — both hands-free (offline, with QUILL's speech
> engines) and say-or-type. Still to come: an **always-on hotword** and **BARD sources**
> (pending the NLS contract). Where a feature is still future, this guide says so.

---

## 1. Getting started

### Install and launch

- **From source (developers):** from the repository root,
  `pip install -e ".[ui]"`, then run `python -m quill.apps.player` (or, inside the
  standalone folder, `python -m quill_media_player`).
- **Installed build:** open **Quill Media Player** from the Start Menu, or choose
  it from any QuillVille app's **QuillVille** menu (it offers to download and
  install it the first time if it isn't present). Until Quill Media Player is
  released, the QuillVille menus of the other apps do not list it yet; open it
  from the Start Menu or from source instead.
- If you type `! python -m quill.apps.player` in QUILL's prompt, it launches in
  this session so its output lands right here.

### First run

When the player opens, focus lands on the **playback controls**. Until you open a
book, the Now Playing area reads "Open a file or a folder to begin." Press
**Ctrl+O** to choose a file.

---

## 2. The window, by ear

Moving through the window with Tab (or your screen reader's controls), you meet
these regions in order:

1. **Menu bar** - File, Navigation, Playback, View, AI, QuillVille, Help and
   Window. Press Alt (or F10) to reach it, Left and Right to move between the
   menus, and Down to open one. For example, to set the sleep timer, press
   Alt, Right twice to Playback, Down, then T for Sleep Timer.
2. **Now Playing** — a review-only line with the title, and (as they arrive)
   author/narrator, source, and format. Arrow through it to read it.
3. **Playback controls** — Play/Pause, Stop, Previous/Next chapter, Rewind,
   Forward, "Where am I?", the position slider, and the volume slider.
4. **Content area** - three pages: Chapters, Bookmarks and Audio. Press
   Ctrl+Tab to move between them. The Book Library is a window of its own
   (File > Book Library..., Ctrl+L); a play queue is not built yet.
5. **AI** - a read-only line saying which AI the player uses, if any. Press
   Enter on it to open Choose Your AI (Section 13b).
6. **Status bar** — live state you can review field by field (Section 11).

---

## 3. Opening books

- **Open File** — **Ctrl+O**. Choose an audio file or audiobook (MP3, M4B, M4A,
  AAC, OGG/Opus, FLAC, WAV, and more).
- **Open Folder as Book** — File menu. Point it at a folder of audio and it plays
  them as one book.
- **Open DAISY Book** — **File > Open DAISY Book…**. Choose the book's `.ncx`; the
  player reads its heading structure into the Chapters tree (single- and multi-file
  DAISY audio books).
- **Book Library** — **File > Book Library…**. Search the free **LibriVox** catalog,
  pick a book, and press **Play**; its sections appear in the Chapters tree.
- **From inside QUILL** — open the player from **Tools > Media > Media Player**; it
  launches this same app and shares your library, bookmarks, and positions. That
  row appears in QUILL once Quill Media Player is released.
- **BARD** — arriving once the NLS BARD contract lands.

When you open a book you've heard before, it **resumes exactly where you left
off** — you don't have to find your place again. Your place is saved every
fifteen seconds while you listen and again the moment you close the Player, so
closing never loses the last few seconds.

---

## 4. Playback and the keyboard

Core transport needs no chord: the single letters in the next section (X, C,
V, B, Z, T and the arrows) play, pause, stop, step and seek from anywhere in
the window except a text field. The player controls are also buttons you can
Tab to and press with Space: Play/Pause, Stop, Previous chapter, Next chapter,
Rewind, Forward, Where am I?, Mute, and the Speed, Position and Volume
controls. These keys are fixed; the standalone player has no Keyboard
Shortcuts editor yet.

### Alt letters in the window

Every button and labelled control in the window has its own Alt letter, and
none of them is a letter the menu bar uses. That matters because Windows sends
Alt plus a letter to a button before a menu when both claim it: until
2026-10-17, Alt+P pressed Play instead of opening the Playback menu, and Alt+V,
Alt+W, Alt+F and Alt+N did the same to View, Window, File and Navigation. Now
the menus keep their letters and the buttons moved:

| Alt+ | Opens or presses | Alt+ | Opens or presses |
| --- | --- | --- | --- |
| F | File menu | A | Play or Pause button |
| N | Navigation menu | T | Stop |
| P | Playback menu | C | Previous chapter |
| V | View menu | X | Next chapter |
| Q | QuillVille menu | R | Rewind |
| H | Help menu | O | Forward |
| W | Window menu | I | AI menu |
| D | Speed | U | Mute or Unmute |
| M | Add Bookmark (Bookmarks page) | K | Remove Bookmark (Bookmarks page) |
| E | Equalizer preset (Audio page) | B | Volume boost (Audio page) |
| L | Normalize loudness (Audio page) | S | Skip silence (Audio page) |

The Play button says Play or Pause depending on what is happening, and the
Mute button says Mute or Unmute, but each keeps one letter, so Alt+A and Alt+U
always work. Where am I? has no Alt letter any more: it used to have I,
which the AI menu took on 2026-11-01, and every other letter in its name was
already in use. Tab to it, or press Shift+F6 to hear the status bar. For
example: press Alt+P and the Playback menu opens; press Escape,
then Alt+A, and the book plays or pauses. The Bookmarks and Audio letters work
while that page is the one showing (Ctrl+Tab moves between pages).

### Arrows in the Chapters tree, sliders and page tabs

Left and Right seek five seconds back and forward (Shift with them, thirty
seconds) from anywhere in the window except where the focused control needs
them itself. In the **Chapters** tree, Left closes a part and Right opens it,
as in any tree, so a DAISY book's parts and chapters can be opened and closed
from the keyboard. On the **position** and **volume** sliders the arrows move
the slider, so Left on the volume slider makes it quieter rather than going
back in the book. On the page tabs (Chapters, Bookmarks, Audio) Left and Right
change the page. Text fields keep every key, as before. For example: Tab to the
Chapters tree, press Right on "Part One" to open it, Down to a chapter and
Enter to play it; then Tab to a button and Right goes forward five seconds.
The limit: letter keys such as X, C and B are still the player's in the tree,
so typing a chapter's first letter does not jump to it there.

| Key | Action | Key | Action |
| --- | --- | --- | --- |
| C | Play / Pause | V | Stop |
| Left / Right | Back / forward 5 seconds | Z / B | Previous / Next track or chapter |
| Ctrl+Up / Ctrl+Down | Volume up / down | T | Time elapsed or remaining |
| Ctrl+B | Add bookmark | Ctrl+Shift+B | Add bookmark with a note |
| Ctrl+G | Go to Position (H:M:S) | Ctrl+O | Open file |
| F6 | Review the status bar | Ctrl+W | Minimize to tray |

**Slider Keys: which way the arrows move a slider.** On the position and
volume sliders Right is always more and Left less. Up and Down, Page Up and
Page Down, and Home and End follow one choice made for every Quill app at
once: open **File > Preferences...** (**Ctrl+,**) and choose the
**Slider Keys...** button.

- **Up is more**, the default: Up, Page Up and Home raise a slider, Home being
  the top (100 percent on a volume), and Down, Page Down and End lower it, End
  being 0.
- **As Windows sliders**: the keys a standard Windows slider uses. Down, Page
  Down and End raise it (End is 100 percent), and Up, Page Up and Home lower it
  (Home is 0).

Change it in any Quill app and every other app follows at your next key press.
Each key press tells your screen reader the new value, so it is never read from
before the key. Ctrl+Up and Ctrl+Down, the volume keys that work from anywhere
in the window, are not changed.

**Where am I?** is a button in the player controls: it speaks the title,
current chapter, how far in you are, and how much remains. It has no key of
its own; for a quick reading without leaving where you are, press **T**, which
says the time elapsed or, pressed again, the time remaining. For example,
while a book plays, press T and you hear something like "1 minute 40 seconds
of 58 minutes".

### Winamp's classic keys

If you came to Windows audio through Winamp, its main-window letter keys are
almost certainly still in your fingers. They work here, unchanged, on the same
letters Quill Radio's Recordings player and QUILL Cast already answer to — one
shared map, so nothing has to be relearned per app.

| Key | Action |
| --- | --- |
| X | Play, or resume what is paused |
| C | Pause / unpause |
| V | Stop |
| Shift+V | Stop (Winamp's fade-out; this engine has no fade, so it stops cleanly) |
| B | Next track |
| Z | Previous track |
| Left / Right | Back / forward 5 seconds |
| Shift+Left / Shift+Right | Back / forward 30 seconds |
| T | Elapsed time, or time remaining — press again to swap |
| J | Jump to a track: type any part of its title |
| Ctrl+J | Go to Position |
| L | Open File... |
| Ctrl+Up / Ctrl+Down | Volume up / down |

Two things worth knowing:

- **B and Z step through the book's tracks** when the book is one file per
  chapter. A book that is a *single* file with chapter marks has no track list,
  so they step by chapter instead — the same intent against the other shape.
- **Ctrl+J opens the Go to Position dialog** you already have on Ctrl+G, rather
  than a second, lesser prompt. It is the accessible one: labelled Hours,
  Minutes and Seconds spin controls, plus a timecode field for `1:23:45`.

Every key says what it did, and positions are spoken as words ("1 minute 40
seconds of 58 minutes"), never as a clock face — read aloud, `1:40` is a time of
day, not a duration. Letters are never swallowed while a text field has focus.

The **position slider** speaks human time as you move it ("2 hours 14 minutes of
11 hours"), not a meaningless tick number.

Playback speed, the **Speed** choice in the player controls, ranges
from 0.5× to 3× and preserves pitch so voices don't turn squeaky.

---

## 5. Chapters

Chapters come from M4B chapter atoms, MP3 chapter tags, Podcasting 2.0 lists, and
**DAISY** navigation. They appear as a **tree**, so a multi-level table of contents
(common in DAISY) keeps its hierarchy — parts with their chapters nested beneath —
while a flat book shows a single level.

- Move by chapter with **Z** and **B** (previous and next), or the Previous
  chapter and Next chapter buttons; entering a new chapter is announced
  ("Chapter 12: The Return"). In a book of one file per chapter, Z and B step
  by file, which is the same thing.
- Open the **Chapters** tree, arrow through it (in and out of levels), and press
  **Enter** to jump. Each row reads as a full sentence with its title and time.
- For a book split across several files (LibriVox sections, multi-file DAISY),
  activating a node loads that file and moves you there.
- **Continuous play** — when one track (a LibriVox section, or a file of a
  multi-file book) finishes, the player automatically rolls into the next.

**DAISY talking books** add navigation by heading — open one via **File > Open DAISY
Book…** (single- and multi-file books). Full DAISY 3 read-along (text + audio sync)
is a future item.

---

## 6. Go to Position (H:M:S)

Press **Ctrl+G** to jump to an exact time.

- Enter **Hours**, **Minutes**, and **Seconds** in three labeled fields — each is
  a spin control you can adjust with the arrow keys, and each announces its value.
- Or type a **timecode** into the single field: `1:23:45`, `83:45` (minutes and
  seconds), `5025` (whole seconds), or `1h23m45s` all work.
- Press **Enter** to jump. The player announces where you landed
  ("Jumped to 1 hour 23 minutes 45 seconds").
- If you ask for a time past the end, it says so and moves you to the end instead
  ("Beyond the end — moved to 11:14:00").

---

## 6a. Picking up where you left off

Open a book you have listened to before and Quill Media Player takes you back
to where you stopped, announcing it as a "welcome back" rather than silently
jumping. Your position is saved every fifteen seconds while you listen, and
again when you close the player, so an unexpected shutdown costs you seconds
rather than the session.

Your place is tied to the **audio itself**, not to where the file happens to
sit. Move the book to another drive, rename it, or reorganise your whole
library, and your position follows it. That also means the same recording on
two different computers is recognised as the same book — the groundwork for
carrying your place between machines. Two *different* recordings of the same
title stay separate, which is what you want: your place in one narrator's
reading says nothing about another's.

A position right at the start is not remembered. "Three seconds in" is the
beginning, and being asked whether to resume there is a question with no useful
answer.

## 7. Bookmarks

Bookmarks mark a moment you want to return to, with an optional label and note.

- **Add a bookmark** at the current spot — **Ctrl+B** (or the Add Bookmark
  button). The player confirms the time it saved.
- **Add a bookmark with a note** — **Ctrl+Shift+B**. Type a note; it shows in the
  Bookmarks list next to the time.
- **Edit a bookmark's note** — select it and choose **Navigation > Edit Bookmark
  Note...** (Ctrl+Alt+N).
- **Jump to a bookmark** — press **Ctrl+Alt+M** (**Navigation > Go to Bookmarks
  List**) to land in the Bookmarks list, arrow to one, press **Enter**.
  **Ctrl+Alt+P** (**Navigation > Go to Player Controls**) takes you back.
- **Remove** — select it and press the **Remove Bookmark** button below the list.
- **Send a bookmark into your document** — **Ctrl+Shift+C** copies a paste-ready line
  (`[1:23:45] your note — Title`) to the clipboard; paste it into your QUILL document
  or a Sticky Note. (A direct insert into a running QUILL is a future refinement.)
- **Export bookmarks** — **File > Bookmarks & Sync > Export Bookmarks…** writes the
  book's bookmarks to a Markdown file.
- **Sync across devices** — **Export / Import Sync Bundle** moves your bookmarks between
  machines as a portable file (merged on import, never overwriting). Automatic
  server-side sync (QuilleSync) is a future item.

Bookmarks are saved per book and survive between sessions.

### Hearing your notes as you reach them

A note you left at 14:32 is read to you when playback gets there, so a note is
something you can make *while listening* and be reminded of while listening --
rather than something you have to stop and open a list to find.

- It is **on by default**, under **Playback > Read My Notes Aloud as I Reach
  Them**. Writing the note is the opt-in: if you took the trouble to leave one,
  you meant to hear it.
- Only bookmarks that **have a note** speak. A plain bookmark is a place to jump
  to, so announcing it with nothing to say would be noise.
- A bookmark with a label speaks the label first -- "Chapter 4: the argument
  starts here" -- and one without says "Note:" so a sentence spoken over an
  audiobook is never mistaken for part of the book.
- **Seeking never triggers it.** Dragging the scrubber across an hour does not
  read out every note it passed, skipping back does not repeat one you just
  heard, and pausing does not announce the same note over and over. You only
  hear a note when you genuinely listen through it.
- Switching it back on part-way through a book does not replay the notes you
  passed while it was off.

No timestamp is spoken with the note: you are at that moment already, and a
spoken "14:32" is ambiguous in a way the written form is not.

---

## 8. Sound, speed, and the equalizer

- **Volume** — **Ctrl+Up** and **Ctrl+Down** from anywhere in the window, or Up
  and Down on the Volume slider (Home is full volume and End silence, unless
  you chose the Windows slider keys under **Slider Keys...**); the **Mute** button mutes, and unmuting
  restores your level. Volume is remembered per book.
- **Speed** — the Speed choice in the player controls, from 0.5× to 3×,
  pitch-preserving.
- **Volume boost / normalization** lifts quiet recordings (Audio page).
- **Equalizer** — a 10-band graphic EQ with presets (Flat, Voice, Bass, Treble,
  Night, Podcast); each band is a labeled slider whose value **is** the gain in
  decibels, so your screen reader speaks a real number.
- **Skip silence** shortens long gaps.

Find these on the **Audio** page of the notebook.

The rich audio effects (EQ, boost, skip-silence, gapless) run on the bundled
**libmpv** engine. On the rare system where libmpv can't load, those controls are
disabled and the player tells you why — core playback still works.

---

## 9. Sleep timer

**Playback > Sleep Timer** stops the player after 15, 30, or 60 minutes, or at the
**End of Chapter**. When it fires it pauses, saves your place, and says "goodnight,"
so you never lose your spot overnight. (A gentle fade-out is a future refinement.)

---

## 10. Announcements, earcons, and braille

- **Earcons** — short non-speech cues for what the player does. Turn them all
  off and on with **Alt+Shift+M** (**Playback > App Sounds**), and choose where
  they play in Preferences (see the next section).
- **Braille** — everything the player announces also goes to your braille
  display, through your screen reader.

Not built yet in the standalone player, though the PRD plans them: a
verbosity choice (Minimal, Normal, Verbose), separate switches and a choice
of personality for each earcon, a dedicated braille status line, and
self-voicing without a screen reader. Nothing in its menus or Preferences
sets these today.

---

## 10a. Where the player's own sounds play

Quill Media Player makes short sounds of its own, the earcons described above. You choose where they play, and you can turn them off.

- **Alt+Shift+M** turns Quill Media Player's sounds off. Press it again and they come back, on the same sound card as before. You hear a short sound as they go off, and another where they now play when they come back on, and both are spoken too. **Playback > App Sounds** has a check mark that shows whether they are on.
- **App Sounds Play On...**, a button in the Preferences window, lets you pick where they play. Open **File > Preferences...** (Ctrl+,) and Tab to the button, or type "sounds" in its Find a setting box. The choices are:
  - **Same as its audio**. This is where it starts. The sounds go wherever the book plays, and follow it when you move it to another sound card. The choice names the device it means right now.
  - **System default**. The sounds go where Windows sends sound.
  - **None (no sounds)**. Quill Media Player makes no sounds at all. Everything it tells you is still spoken.
  - **Any sound card or headset in the list.** The sounds get a device of their own.

After you choose, one sound plays on the new device, so you know straight away where it went.

If the device you chose is unplugged or asleep, you still hear every sound, on the system default, and Quill Media Player tells you once. When the device comes back, the sounds go back to it by themselves.

This changes Quill Media Player only. Your other QUILL apps keep their own choice, unless you have checked "Share these choices with my other Quill apps", which copies a change here to the others that share. Your screen reader is never moved.

## 11. The status bar

The status bar mirrors QUILL's own multi-field status bar, so it reviews the same
way you already know. Its fields: **State**, **Position**, **Chapter**,
**Sleep**, and **Backend**.

- **F6** (**Navigation > Review Status Field**) moves across the fields; each is
  announced with its label ("Chapter: 12 of 14, The Return").
- **Shift+F6** (**Navigation > Read Status Bar**) speaks all fields at once.

---

## 12. System tray and media keys

On Windows, the player lives in the **notification-area tray**:

- Its tooltip shows what's playing.
- Double-click the tray icon to bring the window back. You can also choose a
  key that shows and hides the player from any program: **File > Show and Hide
  Key...** (Ctrl+Alt+Shift+H). There is no key until you choose one. Type the
  key you want, or leave the box empty for none. If another QuillVille app
  already uses it, the player tells you whose it is and lets you try another.
  If you used an earlier version, Ctrl+Alt+Shift+P did this; other QuillVille
  apps use that key, so it is off now, and the player tells you once after you
  update.
- Right-click it, or press the Applications key on it, for its menu: **Show
  Quill Media Player** and **Exit Quill Media Player**. Playback commands are
  not on the tray menu yet; use the window.
- **File > Minimize to Tray** (Ctrl+W) tucks the window into the tray and
  playback carries on. Closing the window saves your place; there is no
  setting yet to choose between asking, going to the tray and exiting when you
  close it, so use Minimize to Tray when you want to keep listening. A
  deliberate **Exit** (Ctrl+Q) always quits.

Because the tray icon and its menu are historically hard for screen readers, the
tray is a convenience, never the only way: everything is in the window and its
menus. The standalone player does not yet take the keyboard's media keys
(Play/Pause, Next, Previous) when another program is in front. On macOS there
is no notification-area tray (the app uses the Dock instead).

---

## 13. Mini-player, Magical Mode, and voice control

- **Mini-player** — **View > Mini Player** opens a compact, always-on-top window
  (Play/Pause, Previous/Next chapter) so playback stays reachable while you work
  elsewhere. **View > Compact Mode** shrinks the main window to just the transport.
  *(Available now.)*
- **Summarize This Chapter (AI)** and **AI Recap of Where I Am** are in the
  Playback menu. They use whichever AI you chose; see Section 13b.
- **Magical Mode** — **View > Magical Mode** turns on opt-in flourishes. Today it
  gives a warm spoken **welcome-back recap** when you reopen a book ("Welcome back.
  The Return, resuming at 6 hours 42 minutes"). Richer touches — spoken chapter intros
  with chimes, an ambient soundscape, listening streaks — are future items, and
  everything turns off in Safe Mode. *(Welcome-back is built; the rest arrive.)*
- **Voice control** — two ways to command the player by voice, both built:
  - **Hands-free: Listen for a Command (Ctrl+Shift+L).** Press once and the player starts
    listening (you'll hear a "Listening" cue and the book quietens); say your command; press
    Ctrl+Shift+L again to stop. The player transcribes what you said **on your own computer**
    (offline, with a small, fast speech model) and carries it out — announcing the result.
    The book is *ducked, never paused*, so you don't lose your place, and it restores the
    moment the command finishes. If nothing is recognized the player tells you what it heard so
    you can try again. A safety timer closes the microphone automatically if you forget to stop.
    It uses the speech engine you chose in QUILL (Tools ▸ Speech ▸ Speech and Dictation...) and
    that engine's smallest fast model, because a command is only a few words. If that engine has no
    model, it tries Whisper.cpp, then the QUILL speech models (where it prefers the built-in
    Moonshine tiny), then Faster Whisper. If none has a model, you hear "Voice listening needs a
    microphone and an installed speech model. Open QUILL and download a small Whisper model
    first." Open QUILL, press Alt+T, H, S, and download Whisper.cpp's Tiny or Base model once.
    Vosk is not used for voice commands.
  - **Type it: Type a Voice Command (Ctrl+Shift+V).** Opens a box; type the command — or speak
    it in with your operating system's dictation — for when you'd rather not talk aloud.
  - Either way the commands are the same: *"next chapter"*, *"skip back thirty"*,
    *"go to 1:20:00"*, *"bookmark this"*, *"how much is left"*, *"sleep in twenty"*,
    *"summarize"*, *"recap"*. Unrecognized input is announced, never guessed, and every voice
    command also has a key or a menu row (the sleep timer, for one, is **Playback > Sleep
    Timer**), so voice is purely additive. *(An always-on hotword — no key
    press to start listening — is a future addition.)*

---

## 13a. Lyrics

**Playback > Lyrics...** (Ctrl+Alt+L) shows the words of the song you are
playing, from LRCLIB (lrclib.net), a free community catalogue of song
lyrics. The song is found from the file's own tags (artist, title, album
and length), or from a file name shaped like "Artist - Title".

1. While a song is open, press **Ctrl+Alt+L**. You hear "Looking up lyrics
   for" and the song.
2. The Lyrics window opens, titled "Lyrics:" and the song, with your
   cursor in the words (**Lyrics**, Alt+L). Arrow through them; **Ctrl+C**
   copies what you select.
3. When the words are timed, **Current line** (Alt+U) shows the line being
   sung now, and **Follow playback** (Alt+F, on to start with) keeps the
   cursor in the words on that line. Turn Follow playback off to read back
   without being moved; turn it on again and it catches up.
4. Nothing is read out as the lines change. **Say Current Line** (Alt+S)
   speaks the line being sung, once, when you want to hear it.
5. Press **Escape**, **Ctrl+W** or **Ctrl+F4** to close.

When a song has words but no timings, the words still appear, Follow
playback is unavailable, and Current line says so. When there are no
words you hear why instead of a window: no lyrics found, the song is an
instrumental, or the file does not say its artist and title.

Lyrics are looked up only when you ask, never in the background and never
in Safe Mode, and they are kept in memory only: nothing is written to your
computer.

---

## 13b. AI: summaries, recaps and Ask

The player can use an AI to tell you about the book you're listening to. It
uses the AI you pick for it, and nothing is sent until you ask. The audio
itself never leaves your computer.

### Picking an AI

Open **AI > Choose Your AI...** (**Ctrl+Shift+F8**). You can use QUILL's free
AI, your ChatGPT plan, GitHub Copilot, Codex, or your own key. The player signs
in on its own, as QUILL Media Player, so signing in here doesn't sign in any
other QuillVille app. To hear which one is in use, press **Ctrl+F8**
(**AI > Which AI Am I Using**). The AI line in the main window says the same
thing; press Enter on it to open Choose Your AI.

The rest of the AI menu: **Use My ChatGPT Subscription...** (**Alt+F5**),
**Use My Own AI Key...** (**Alt+F2**), **AI Usage...** (**Ctrl+Alt+Shift+F2**)
and **Privacy Agreement...** (**Ctrl+Alt+Shift+K**).

### Summarize This Chapter and AI Recap of Where I Am

- **Summarize This Chapter (AI)** (**Ctrl+Alt+C**) gives you the chapter
  you're in, in a sentence or two.
- **AI Recap of Where I Am** (**Ctrl+Alt+R**) reminds you what was going on up
  to your place in the book, without giving away anything further on. It's
  handy after a few days away from a book.

Both are in the Playback menu, where they've always been. The answer is read
aloud and also shown in a window you can read again and copy. Ask for the same
chapter again and you get the same answer straight away, without sending
anything.

The AI can only read text, so the player finds some first. For pure audio it
makes a short transcript of the passage, at most five minutes, right here on
your computer; that needs QUILL's offline speech engine installed. Only that
text goes to the AI. You can also say "summarize" or "recap" to the voice
command bar.

Neither one works in Safe Mode, and neither ever runs on protected BARD
content.

### Ask

**AI > Ask...** (**Ctrl+Shift+8**) opens a conversation about the book. Each
message takes along the book's title, the chapter you're in, your place in it
and the list of chapters, so you can ask things like "how many chapters are
left?" or pick **Remind me who this character is** from Quick questions. No
file names or folders go with it, and no audio.

---

## 14. Settings

**File > Preferences...** (Ctrl+,) gathers the player's settings in one window:
**Audio Output Device...**, **App Sounds Play On...** and **Slider Keys...**
(buttons that open their own windows; Slider Keys is described under "Arrows in
the Chapters tree, sliders and page tabs"), and, in a box labelled **This session only**, Compact mode, Magical
mode, Always on top and the Sleep timer, which reset when the player closes. Each
does exactly what its menu row does. Its **Find a setting** box searches these and
the settings that stay in the main window: type "skip silence", press Down to
the match and press Enter, and Preferences closes, the Audio page comes forward and the focus lands on Skip
silence.

The same settings are also in the menus: the **Audio** page for the equalizer,
boost, normalize, and skip-silence; **Playback > Sleep Timer**; **Playback > Audio
Output Device...** (Ctrl+Shift+K); and the **View** menu for Mini Player (Ctrl+Shift+M),
Compact Mode (Ctrl+Alt+K), Magical Mode (Ctrl+Shift+G), and Always on Top
(Ctrl+Shift+T). Your listening position, per-book volume, and bookmarks are
remembered automatically.

Per-book overrides and importing or exporting settings, specified in the PRD
(Section 10), are not built yet.

---

## 15. Privacy and safety

- The player makes **no network calls** except to the sources you choose; there is
  no telemetry.
- **Lyrics** are fetched from LRCLIB only when you open the Lyrics window,
  sending the song's artist, title, album and length, and are kept in memory
  only.
- **AI** is used only when you ask, through the AI you chose (Section 13b).
  What goes is text: the book's title, chapter names and your place, and for a
  summary or recap a short transcript made on your computer. Audio never goes.
- **Safe Mode** disables all network sources and every AI command — local
  playback still works.
- Protected BARD content is handled only through the sanctioned mechanism; a
  decrypted copy is never written to disk.
- Your BARD sign-in and any keys live only in your operating system's secure vault,
  never in a settings file or the app itself.

---

## 16. Accessibility notes

- Every control is keyboard-operable and screen-reader- and braille-announced.
- Sliders are arrow-adjustable and speak their values: Up and Right mean more
  (louder, further on), Down and Left less, Page Up and Page Down in bigger steps,
  and Home and End go to the top and the bottom. **Slider Keys...** in
  Preferences turns Up, Down, Page Up, Page Down, Home and End round to match
  a standard Windows slider instead, in every Quill app at once.
  Lists read a full sentence per row and support first-letter search; reordering
  never needs a drag.
- The player honors your system High Contrast, dark mode, reduced-motion, and text
  scaling.
- Nothing important is conveyed by color alone.

---

## 17. Troubleshooting

- **"Could not open …"** — the file may be a format the current engine can't play;
  try another file, or ensure the bundled engines are present next to the app.
- **EQ / boost / skip-silence are greyed out** — libmpv isn't loaded on this
  system; core playback still works.
- **No tray icon** — you're on macOS (which has no notification-area tray), or
  Windows has hidden it in the overflow area (press Windows+B, then the arrow
  keys); otherwise use the window itself.
- **It didn't resume where I expected** — your place is tied to the audio itself,
  so a moved or renamed copy of the same recording resumes; a *different*
  recording of the same title (another narrator, another edition) is a separate
  book with its own place, and a position in the first few seconds is not kept
  (see "Picking up where you left off").

---
- **Text looks blurry, or a window is the wrong size.** QUILL Media Player scales itself for each monitor. Text stays sharp at 125, 150 or 200
  percent, and when you move a window to a monitor with different scaling;
  windows and list columns keep their proportions. If a window looks wrong at
  your scaling, you can turn this off to see whether it is the cause. Search
  Windows for "Edit environment variables for your account", add a variable
  named `QUILL_DPI_UNAWARE` with the value `1`, and start QUILL Media Player again.
  Windows then stretches it the old way, so text is blurrier. Delete the
  variable to put scaling back, and tell support what you saw.

## 18. Feature availability at a glance

| Available now | Still to come |
| --- | --- |
| Open file / folder / DAISY, resume | Always-on hotword (say a wake word to start) |
| **Hands-free voice (offline, QUILL's speech engines)** | Spoken chapter intros / soundscape |
| Chapter **tree** (multi-level, DAISY) | Spoken chapter intros / soundscape |
| **Summarize Chapter + AI Recap, Ask (AI)** | Automatic (server) cross-device sync |
| **Copy/Export bookmarks + Sync bundle** | Embedded in-QUILL window; zero-gap gapless |
| Book Library (LibriVox) + multi-track | BARD sources (NLS contract) |
| 10-band EQ, boost, normalize, skip-silence | Embedded in-QUILL player window |
| Go to Position (H:M:S), bookmarks | Full DAISY 3 read-along |
| Sleep timer, mini-player, status bar (F6) | |
| Magical welcome-back, compact / on-top | |
| System tray, in-QUILL launch, updates | |

For the complete design and the phased build plan, see the PRD next to this guide
(`prd.md`).

## Finding a setting or a command

Quill Media Player keeps most of its options in its menus, and
**Help > Find a Setting or Command** (**Ctrl+Alt+Shift+S**) searches every menu at
once. (Preferences has its own **Find a setting** box for what is in that window;
see Settings.)

1. Press **Ctrl+Alt+Shift+S**.
2. Type part of what you are looking for, such as "bookmarks". The list
   below narrows as you type, and each row says which menu the command is in.
   An option also says whether it is on or off.
3. Press **Down** to move into the list, and **Enter** on the one you want.

Enter does exactly what choosing that row from its menu would do. For an
option, it switches it and tells you whether it is now on or off. Escape
closes the window without doing anything.

## What's New

**Help > What's New** (**Ctrl+Shift+F1**) opens the player's changelog in your
browser: what changed in the version you have, grouped by subject. Every Quill
app has the same door on the same key.

## Licences and notices

Quill Media Player is free and released under the MIT License. It also includes software,
data and sounds from other projects, each under its own licence.

To read them, open the Help menu, choose About Quill Media Player, and then choose the
Licences and Notices button. The list opens as a plain text file, with one
heading for each component: what it is, its licence, who holds the copyright
and what the licence asks of us. The full licence texts are at the end.

The same file, THIRD-PARTY-NOTICES.txt, and Quill Media Player's own licence, LICENSE.txt,
are also in the folder where Quill Media Player is installed or unpacked, so you can open
them without starting the app.

## Getting help

Support is run by **Community Access**, and the address is
**support@community-access.org**. A person reads it, and replies come back by
email.

The quickest way there is **Help > Get Help from Support...** (Ctrl+Alt+F2),
which every app in the family answers with the same form: what kind of message
this is, a subject, what happened, and -- if you want an answer -- an email
address to reply to. What you expected and how to reproduce it are optional,
and worth more than anything else when you can give them.

Press Send and your **own mail program opens with the whole message already
written**, addressed to support, with Quill Media Player's name and version and your Windows
version filled in at the bottom. Nothing is sent until you send it there, so you
can read it over, add anything, or change your mind.

If this machine has no mail program set up -- webmail only, say -- the app puts
the whole message on your clipboard and tells you the address, so nothing you
typed is lost. And writing to **support@community-access.org** yourself always
works just as well: there is no form you have to use. Say which app you were
using and what happened.
