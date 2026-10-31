# Changelog

All notable changes to Quill Media Player are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Quill Media Player runs the same player code as QUILL from the shared `quill` package, so a fix lands in both at once; `standalone/player` carries only the wrapper, launcher and docs.

## 1.0.0

Testing build: **1.0.0 (build 2)**. Quill Media Player has not been published yet: the other QuillVille apps do not list it in their QuillVille menus, and QUILL's **Tools > Media > Media Player** row appears once it is released. Everything below is in the build.

### Since build 2 (2026-10-30 and 2026-10-31)

- **Host-runtime licensing.** Media Player has no separate installer. When its
  host uses the QuillVille Runtime, that runtime currently carries PyMuPDF
  1.28.2 under AGPL-3.0 through the shared GLOW dependency; the player does not
  itself expose GLOW. Release-specific source and legal review remain open.
- **Controls that had no label now have a spoken name** (2026-10-30).
  JAWS, NVDA and Narrator used to announce them as a bare role, such as
  "edit" or "list". Now playing, the Chapters tree and the Bookmarks list now say what they are.
- **Sharp text at any display scaling** (2026-10-31). QUILL Media Player now handles
  each monitor's scaling itself instead of letting Windows stretch it, so
  text stays sharp at 125, 150 and 200 percent and on monitors with
  different scaling, and windows and list columns keep their proportions.
  Setting the environment variable `QUILL_DPI_UNAWARE` to `1` turns this off,
  for diagnosing a display problem (#1702). User guide: "Text looks blurry, or a window is the wrong size".

### Opening and listening to books

- **Open what you have.** **Open File** (Ctrl+O) plays an audio file or audiobook (MP3, M4B, M4A, AAC, OGG/Opus, FLAC, WAV and more); **Open Folder as Book** plays a folder of audio as one book; **File > Open DAISY Book...** reads a DAISY book's heading structure from its `.ncx`, single-file and multi-file alike.
- **The Book Library.** **File > Book Library...** (Ctrl+L) searches the free LibriVox catalog; pick a book and press Play, and its sections appear in the Chapters tree.
- **Chapters as a tree.** A multi-level table of contents keeps its parts with their chapters nested beneath; a flat book shows one level. Z and B (or the Previous chapter and Next chapter buttons) move by chapter and announce it, Enter in the tree jumps, and a book split across several files loads the right file. When one track finishes, the player rolls into the next.
- **Go to Position** (Ctrl+G): Hours, Minutes and Seconds fields, or a timecode typed as `1:23:45`, `83:45`, `5025` or `1h23m45s`. A time past the end says so and moves you to the end.
- **Picking up where you left off.** A book you have heard before resumes where you stopped, announced as a welcome back. Your place is saved every fifteen seconds and again when you close the player, and it is tied to the audio itself, so a moved or renamed copy of the same recording resumes while a different recording of the same title keeps its own place. A position in the first few seconds is not kept.
- **Sleep timer.** **Playback > Sleep Timer** stops after 15, 30 or 60 minutes, or at the end of the chapter, then pauses, saves your place and says goodnight.
- **Lyrics** (2026-10-15). **Playback > Lyrics...** (Ctrl+Alt+L) shows the words of the playing song from LRCLIB, found from the file's tags or an "Artist - Title" file name. With timed words, **Current line** shows the line being sung and **Follow playback** keeps the cursor on it; nothing is read out as lines change, and **Say Current Line** speaks the line once. Lyrics are looked up only when you ask, never in Safe Mode, and kept in memory only.

### Bookmarks and notes

- **Bookmarks** with Ctrl+B, or with a note on Ctrl+Shift+B; **Navigation > Edit Bookmark Note...** (Ctrl+Alt+N); **Navigation > Go to Bookmarks List** (Ctrl+Alt+M) and back to the player controls with Ctrl+Alt+P. Ctrl+Shift+C copies a paste-ready `[1:23:45] note — Title` line for a QUILL document.
- **Export and sync.** **File > Bookmarks & Sync** exports a book's bookmarks to Markdown (Ctrl+Alt+E) and exports (Ctrl+Alt+S) or imports (Ctrl+Alt+I) a sync bundle that moves bookmarks between machines, merged on import and never overwriting.
- **Hearing your notes as you reach them.** A bookmark with a note is read aloud when playback reaches it, on by default under **Playback > Read My Notes Aloud as I Reach Them**. Only bookmarks with a note speak, a label is read first (or "Note:" without one), and seeking, skipping back or pausing never triggers or repeats one.

### Sound, volume and the sliders

- **Volume, speed and the Audio page.** Ctrl+Up and Ctrl+Down change the volume from anywhere in the window, the Mute button mutes and unmuting restores your level, and volume is remembered per book. Speed runs from 0.5x to 3x, pitch preserved. The Audio page has volume boost and loudness normalization, a 10-band equalizer whose bands speak their gain in decibels (presets Flat, Voice, Bass, Treble, Night and Podcast), and skip silence. These run on the bundled libmpv engine; where it cannot load they are disabled and the player says why.
- **Up is more on every slider, and Slider Keys to choose** (2026-09-28, 2026-10-26). Up and Page Up raise the position and volume sliders and Down and Page Down lower them, and Home and End go with them: Home is full volume, 100 percent, and End is 0. **File > Preferences...** (Ctrl+,) has a **Slider Keys...** button that chooses between **Up is more** (the default) and **As Windows sliders** (Down, Page Down and End raise a slider; Up, Page Up and Home lower it). It is one choice for every Quill app at once. Right is always more and Left less, each key press tells the screen reader the new value, and Ctrl+Up and Ctrl+Down are not changed.
- **Where the player's own sounds play.** **App Sounds Play On...** in Preferences sends the earcons to the book's own device (the default), the system default, any sound card or headset by name, or nowhere. **Alt+Shift+M** (**Playback > App Sounds**) turns them off and back on. If the chosen device is unplugged the sounds play on the system default and the player says so once. **Playback > Audio Output Device...** (Ctrl+Shift+K) chooses where the book plays.

### The window and the keyboard

- **Winamp's classic keys.** X plays, C pauses, V stops (Shift+V too), B and Z step track or chapter, Left and Right seek five seconds (thirty with Shift) and T says the time elapsed or remaining, on the same letters as Quill Radio's Recordings player and QUILL Cast.
- **Alt letters that do not fight the menus** (2026-10-17). Alt+P pressed Play instead of opening the Playback menu, and Alt+V, Alt+W, Alt+F and Alt+N did the same to View, Window, File and Navigation. The menus keep their letters and the buttons moved: Play or Pause is Alt+A, Stop Alt+T, Previous chapter Alt+C, Next chapter Alt+X, Rewind Alt+R, Forward Alt+O, Where am I? Alt+I, Mute Alt+U, Speed Alt+D, Add Bookmark Alt+M, Remove Bookmark Alt+K, Equalizer preset Alt+E, Volume boost Alt+B, Normalize loudness Alt+L and Skip silence Alt+S.
- **Arrows that belong to the focused control** (2026-10-17). In the Chapters tree Left closes a part and Right opens it, the sliders keep their arrows (so Left on the volume slider is quieter rather than a seek), and Left and Right change page on the Chapters, Bookmarks and Audio tabs.
- **The status bar.** State, Position, Chapter, Sleep and Backend fields: F6 (**Navigation > Review Status Field**) moves across them and Shift+F6 (**Navigation > Read Status Bar**) speaks them all.
- **Tray and show-and-hide key.** The player lives in the notification area; **File > Minimize to Tray** (Ctrl+W) keeps it playing and Exit (Ctrl+Q) quits. **File > Show and Hide Key...** (Ctrl+Alt+Shift+H) chooses a key that shows and hides the player from any program; there is none until you choose one. Ctrl+Alt+Shift+P, which earlier builds used, belongs to other QuillVille apps and is off, and the player says so once after the update.
- **Mini Player and views.** **View > Mini Player** (Ctrl+Shift+M), **Compact Mode** (Ctrl+Alt+K), **Magical Mode** (Ctrl+Shift+G, a spoken welcome-back recap) and **Always on Top** (Ctrl+Shift+T).
- **Preferences** (Ctrl+,) gathers the Audio Output Device..., App Sounds Play On... and Slider Keys... buttons, a "This session only" box, and a **Find a setting** box that also reaches the Audio page.

### AI and voice

- **Summarize This Chapter (AI)** and **AI Recap of Where I Am** in the Playback menu, using the AI set up in QUILL's AI Hub; for pure audio they transcribe the passage first. Off in Safe Mode, and never run on protected BARD content.
- **Voice commands.** **Listen for a Command** (Ctrl+Shift+L) transcribes a spoken command offline with a small speech model while the book is ducked, never paused; **Type a Voice Command** (Ctrl+Shift+V) takes it typed. Commands such as "next chapter", "go to 1:20:00", "bookmark this" or "sleep in twenty" all also have a key or menu row.

### Help

- **Help > What's New** (Ctrl+Shift+F1) opens this changelog in your browser, on the same key as every other Quill app. Until this file was written, the player had no changelog and the command said it was not found in the build.
- **Help > Find a Setting or Command** (Ctrl+Alt+Shift+S) searches every menu; **Help > Get Help from Support...** (Ctrl+Alt+F2) writes a message to Community Access in your own mail program; **Help > Check for Updates...** (Ctrl+Alt+U) and **About** (Ctrl+Alt+A).

### Privacy and safety

- No network calls except to the sources you choose, and no telemetry. Safe Mode turns off every network source; local playback still works. BARD sign-ins and keys live only in the operating system's secure vault.
