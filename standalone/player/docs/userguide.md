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
> chapter summary/recap**, and **voice commands** — both hands-free (offline Whisper or
> Nemotron) and say-or-type. Still to come: an **always-on hotword** and **BARD sources**
> (pending the NLS contract). Where a feature is still future, this guide says so.

---

## 1. Getting started

### Install and launch

- **From source (developers):** from the repository root,
  `pip install -e ".[ui]"`, then run `python -m quill.apps.player` (or, inside the
  standalone folder, `python -m quill_media_player`).
- **Installed build:** open **Quill Media Player** from the Start Menu, or choose
  it from any QuillVille app's **QuillVille** menu (it offers to download and
  install it the first time if it isn't present).
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

1. **Menu bar** — File, Playback, Audio, Navigation, Library, View, Magical,
   Tools, Settings, Help. (In today's build the standalone app ships File,
   Navigation, QuillVille, and Help; the rest arrive with their features.)
2. **Now Playing** — a review-only line with the title, and (as they arrive)
   author/narrator, source, and format. Arrow through it to read it.
3. **Playback controls** — Play/Pause, Stop, Previous/Next chapter, Rewind,
   Forward, "Where am I?", the position slider, and the volume slider.
4. **Content area** — the Chapters, Bookmarks, Library, Queue, and Audio pages
   (Bookmarks is available today; the others arrive with their features).
5. **Status bar** — live state you can review field by field (Section 11).

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
  launches this same app and shares your library, bookmarks, and positions.
- **BARD** — arriving once the NLS BARD contract lands.

When you open a book you've heard before, it **resumes exactly where you left
off** — you don't have to find your place again.

---

## 4. Playback and the keyboard

Core transport needs no chord. Every key here is **remappable** in the Keyboard
Shortcuts editor.

| Key | Action | Key | Action |
| --- | --- | --- | --- |
| Space | Play / Pause | Stop button | Stop |
| Left / Right | Skip back / forward | `[` / `]` | Previous / Next chapter |
| Up / Down | Volume up / down | M | Mute / Unmute |
| B | Add bookmark | Ctrl+B | Add bookmark (menu) |
| Ctrl+G | Go to Position (H:M:S) | W | Where am I? |
| Ctrl+O | Open file | Ctrl+W | Minimize to tray |

**Where am I?** speaks the title, current chapter, how far in you are, and how
much remains — a single key whenever you want your bearings.

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

Playback speed, when enabled, ranges from 0.5× to 4.0× and preserves pitch so
voices don't turn squeaky.

---

## 5. Chapters

Chapters come from M4B chapter atoms, MP3 chapter tags, Podcasting 2.0 lists, and
**DAISY** navigation. They appear as a **tree**, so a multi-level table of contents
(common in DAISY) keeps its hierarchy — parts with their chapters nested beneath —
while a flat book shows a single level.

- Move by chapter with **`[`** and **`]`**; entering a new chapter is announced
  ("Chapter 12: The Return").
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
- **Edit a bookmark's note** — select it and choose **Edit Bookmark Note…**.
- **Jump to a bookmark** — open the **Bookmarks** list, arrow to one, press
  **Enter**.
- **Remove** — select it and choose Remove Bookmark.
- **Send a bookmark into your document** — **Ctrl+Shift+C** copies a paste-ready line
  (`[1:23:45] your note — Title`) to the clipboard; paste it into your QUILL document
  or a Sticky Note. (A direct insert into a running QUILL is a future refinement.)
- **Export bookmarks** — **File > Bookmarks & Sync > Export Bookmarks…** writes the
  book's bookmarks to a Markdown file.
- **Sync across devices** — **Export / Import Sync Bundle** moves your bookmarks between
  machines as a portable file (merged on import, never overwriting). Automatic
  server-side sync (QuilleSync) is a future item.

Bookmarks are saved per book and survive between sessions.

---

## 8. Sound, speed, and the equalizer

- **Volume** — Up/Down, and **M** to mute (unmuting restores your level). Volume
  is remembered per book.
- **Speed** — slower/faster in fine steps, remembered per book, pitch-preserving.
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

- **Verbosity** — choose Minimal, Normal, or Verbose. Minimal keeps the essentials
  and stays quiet about routine ticks; Verbose narrates more.
- **Earcons** — short non-speech cues for play/pause, bookmark, chapter, and end;
  each can be toggled independently of speech, and you can pick an earcon
  personality (Classic, Warm, Minimal).
- **Braille** — a dedicated status line renders Now Playing, chapter, and position
  on your refreshable display.
- **Self-voicing** (optional) speaks the player's announcements even when no screen
  reader is running.

---

## 11. The status bar

The status bar mirrors QUILL's own multi-field status bar, so it reviews the same
way you already know. Its fields: **State**, **Position**, **Chapter**, **Speed**,
**Sleep**, **Source & format**, and **Backend**.

- **F6** moves across the fields; each is announced with its label ("Chapter: 12 of
  14, The Return").
- **Shift+F6** (Read Status Bar) speaks all fields at once.

---

## 12. System tray and media keys

On Windows, the player lives in the **notification-area tray**:

- Its tooltip shows what's playing.
- Double-click, or the **Restore Player** hotkey, brings the window back.
- Right-click for a menu of the essentials (Play/Pause, skip, chapter, bookmark,
  sleep, Show Player, Exit).
- **Closing to the tray** is a choice — *ask*, *minimize to tray*, or *exit* —
  and a deliberate **Exit** always quits, never bounces back.

Because the tray icon and its menu are historically hard for screen readers, the
tray is a convenience, never the only way: **global media keys** (Play/Pause,
skip, chapter) work even while minimized, and state changes are spoken. On macOS
there is no notification-area tray (the app uses the Dock and the system Now
Playing controls instead).

---

## 13. Mini-player, Magical Mode, and voice control

- **Mini-player** — **View > Mini Player** opens a compact, always-on-top window
  (Play/Pause, Previous/Next chapter) so playback stays reachable while you work
  elsewhere. **View > Compact Mode** shrinks the main window to just the transport.
  *(Available now.)*
- **Summarize This Chapter (AI)** — **Playback > Summarize This Chapter (AI)** asks
  your configured AI for a one- or two-sentence summary and speaks it (also shown in a
  dialog you can read).
- **AI Recap of Where I Am** — **Playback > AI Recap of Where I Am** recaps the passage
  up to your current point ("here's what's been happening"), so you can pick a book back
  up after a break.
  Both use the AI: for a book with a text layer (DAISY/EPUB) they summarize the text
  directly; for pure audio they transcribe the passage first, so that needs the offline
  speech engine installed. Both require an AI provider set up in QUILL's AI Hub, are off
  in Safe Mode, and never run on protected BARD content. *(Available now.)*
- **Magical Mode** — **View > Magical Mode** turns on opt-in flourishes. Today it
  gives a warm spoken **welcome-back recap** when you reopen a book ("Welcome back.
  The Return, resuming at 6 hours 42 minutes"). Richer touches — spoken chapter intros
  with chimes, an ambient soundscape, listening streaks — are future items, and
  everything turns off in Safe Mode. *(Welcome-back is built; the rest arrive.)*
- **Voice control** — two ways to command the player by voice, both built:
  - **Hands-free: Listen for a Command (Ctrl+Shift+L).** Press once and the player starts
    listening (you'll hear a "Listening" cue and the book quietens); say your command; press
    Ctrl+Shift+L again to stop. The player transcribes what you said **on your own computer**
    (offline, using a small Whisper speech model) and carries it out — announcing the result.
    The book is *ducked, never paused*, so you don't lose your place, and it restores the
    moment the command finishes. If nothing is recognized the player tells you what it heard so
    you can try again. A safety timer closes the microphone automatically if you forget to stop.
    (Needs a microphone and a speech model installed in QUILL — open QUILL ▸ download a small
    Whisper model once.)
  - **Type it: Type a Voice Command (Ctrl+Shift+V).** Opens a box; type the command — or speak
    it in with your operating system's dictation — for when you'd rather not talk aloud.
  - Either way the commands are the same: *"next chapter"*, *"skip back thirty"*,
    *"go to 1:20:00"*, *"bookmark this"*, *"how much is left"*, *"sleep in twenty"*,
    *"summarize"*, *"recap"*. Unrecognized input is announced, never guessed, and every voice
    command also has its own key, so voice is purely additive. *(An always-on hotword — no key
    press to start listening — is a future addition.)*

---

## 14. Settings

Today you control the player from its menus: the **Audio** page for the equalizer,
boost, normalize, and skip-silence; **Playback > Sleep Timer**; and the **View** menu
for Mini Player, Compact Mode, Magical Mode, and Always on Top. Your listening
position, per-book volume, and bookmarks are remembered automatically.

A single **searchable, categorized Preferences dialog** — with per-book overrides and
import/export — is on the roadmap; its full catalogue of options is specified in the
PRD (Section 10). Until it lands, the menu controls above cover the day-to-day
settings.

---

## 15. Privacy and safety

- The player makes **no network calls** except to the sources you choose; there is
  no telemetry.
- **Safe Mode** disables all network sources — local playback still works.
- Protected BARD content is handled only through the sanctioned mechanism; a
  decrypted copy is never written to disk.
- Your BARD sign-in and any keys live only in your operating system's secure vault,
  never in a settings file or the app itself.

---

## 16. Accessibility notes

- Every control is keyboard-operable and screen-reader- and braille-announced.
- Sliders are arrow-adjustable and speak their values; lists read a full sentence
  per row and support first-letter search; reordering never needs a drag.
- The player honors your system High Contrast, dark mode, reduced-motion, and text
  scaling.
- Nothing important is conveyed by color alone.

---

## 17. Troubleshooting

- **"Could not open …"** — the file may be a format the current engine can't play;
  try another file, or ensure the bundled engines are present next to the app.
- **EQ / boost / skip-silence are greyed out** — libmpv isn't loaded on this
  system; core playback still works.
- **No tray icon** — you're on macOS (which has no notification-area tray) or the
  tray is disabled in settings; use the Dock or the window itself.
- **It didn't resume where I expected** — resume is saved per file; a renamed or
  moved file is treated as new.

---

## 18. Feature availability at a glance

| Available now | Still to come |
| --- | --- |
| Open file / folder / DAISY, resume | Always-on hotword (say a wake word to start) |
| **Hands-free voice (offline Whisper/Nemotron)** | Spoken chapter intros / soundscape |
| Chapter **tree** (multi-level, DAISY) | Spoken chapter intros / soundscape |
| **Summarize Chapter + AI Recap (AI)** | Automatic (server) cross-device sync |
| **Copy/Export bookmarks + Sync bundle** | Embedded in-QUILL window; zero-gap gapless |
| Book Library (LibriVox) + multi-track | BARD sources (NLS contract) |
| 10-band EQ, boost, normalize, skip-silence | Embedded in-QUILL player window |
| Go to Position (H:M:S), bookmarks | Full DAISY 3 read-along |
| Sleep timer, mini-player, status bar (F6) | |
| Magical welcome-back, compact / on-top | |
| System tray, in-QUILL launch, updates | |

For the complete design and the phased build plan, see the PRD next to this guide
(`prd.md`).
