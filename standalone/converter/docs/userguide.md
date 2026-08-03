# Quill Converter User Guide

Version 1.0

Quill Converter is one job done properly: changing audio from one format into
another, on your own machine, without uploading anything to a website. It is a
small window with a queue, a couple of choice controls, and a Convert button.
Focus lands on the queue the instant it opens, every control has a name and an
access key, and the whole thing runs from the keyboard.

## Getting started

Launch Quill Converter from the Start Menu, or `run-quill-converter.bat` from a
source checkout, or `python -m quill.apps.converter` if you have the `quill`
package installed.

The window opens with keyboard focus on the **Files to convert** list. From
there:

1. Press Alt+A (**Add Files...**) and pick one or more files, or Alt+O
   (**Add Folder...**) and pick a whole folder.
2. Choose an output format in **Convert to** (Alt+V).
3. Choose a **Preset** (Alt+P), or leave it on "Just convert (no processing)".
4. Optionally set an **Output folder**. Leave it blank and Quill Converter
   creates a `Converted` folder beside your source.
5. Press Alt+C (**Convert**).

Progress is spoken and written to the status bar as it goes, and the run ends
with a summary that says how many files converted and names any that failed.

Only one copy of Quill Converter runs at a time. Launching it again while it is
already running does not open a second window.

## What it converts

**Input.** Audio files: MP3, WAV, FLAC, OGG, OGA, Opus, M4A, M4B, AAC, WMA,
AIFF, AIF, ALAC, APE, WV, MKA, AMR, 3GP, and CAF. Video files, from which the
audio track is pulled out: MP4, M4V, MKV, MOV, WebM, AVI, FLV, and WMV.

**Output.** MP3, M4A, M4B, Opus, OGG, FLAC, WAV, AAC, AIFF, ALAC, WMA, and CAF.

The **Convert to** list is not a fixed menu: at startup Quill Converter asks the
bundled FFmpeg which encoders it actually has and lists only the formats it can
really produce. That is deliberate -- a batch should never die half way through
because an encoder was missing. WAV, AIFF, and CAF are always available. If
FFmpeg cannot be found at all, WAV is the only format offered, and starting a
conversion tells you that FFmpeg is needed and points you at QUILL's
**Help > Download Optional Components**.

## The five ways files get in

There is no drag and drop, by design -- everything below is reachable from the
keyboard.

1. **Add Files...** (Alt+A, or File > Add Files..., Ctrl+O). A standard
   multi-select file picker filtered to audio and video files, with an "All
   files" option if you need it.
2. **Add Folder...** (Alt+O, or File > Add Folder...). Queues the whole folder.
   From the main window a folder is always scanned right through its
   sub-folders, and the output mirrors the source folder structure.
3. **The command line.** Pass file or folder paths when you launch the app and
   each one that exists is queued immediately:
   `python -m quill.apps.converter song.wav album\`
4. **The Windows Explorer right-click menu.** Turn on the "Offer Convert with
   QUILL" setting in QUILL, and audio and video files gain a **Convert with
   Quill** entry that opens Quill Converter with your selection already queued.
   The verb is **off by default** -- nothing is added to your context menu until
   you ask for it.
5. **Convert from URL...** (Alt+U, or File > Convert from URL...). Described in
   its own section below; the downloaded audio arrives in the converter ready to
   go.

Duplicate paths are ignored, so adding the same file twice queues it once.

To take something out of the queue, select the row and press **Delete**, or use
the **Remove** button (Alt+R).

## The main window, control by control

Tab order, top to bottom:

- **Files to convert** (Alt+F, a list box). One row per queued item; a folder
  reads as "name (folder)". Delete removes the selected row.
- **Add Files...** (Alt+A), **Add Folder...** (Alt+O), **Remove** (Alt+R).
- **Convert to** (Alt+V, a combo box). The output format, in capitals.
- **Preset** (Alt+P, a combo box). Each entry is spoken as its name plus a
  plain-language description of what it is good for, so you can choose by
  hearing rather than by guessing.
- **Output folder** (a text field) and **Browse...** (Alt+B). Leave it blank to
  get a `Converted` folder beside the first thing in your queue.
- **Convert** (Alt+C), **Convert from URL...** (Alt+U), **Advanced...**.

Two access keys are shared on this window: Alt+O reaches both **Add Folder...**
and the **Output folder** field, and Alt+V reaches both **Convert to** and
**Advanced...**. Pressing the key repeatedly cycles between them, and Tab
reaches everything in order, so nothing is unreachable -- but Tab is the
reliable route to Advanced.

The status bar reports how many items are queued, then per-file progress during
a run, then the summary.

From the main window, conversions never overwrite an existing file: if the
output name is already taken, the new file is auto-numbered instead. If you want
Skip or Overwrite instead, use **Advanced...** (below), which exposes the
conflict policy.

## Presets

- **Just convert (no processing)** -- a pure format change. The default.
- **MP3 320 kbps (maximum quality)**, **MP3 192 kbps**, **MP3 128 kbps
  (small)**.
- **Podcast (MP3, spoken word)** -- mono MP3 with a rumble-removing high-pass.
- **Audiobook (M4B)** -- mono M4B at a compact bitrate.
- **Voice memo (small MP3)** -- mono, 22 kHz, tiny files for spoken notes.
- **Web voice (Opus)** -- mono Opus at a low bitrate, the smallest for the web.
- **Archival (FLAC, lossless)** -- keeps the original rate and channels.
- **Hearing-aid mono** -- downmix to a single channel.

A preset sets the starting recipe; the **Convert to** choice always wins over
the preset's own format, so you can take the Podcast preset and still ask for
Opus.

## Advanced

**Advanced...** (also File > Advanced Options...) hands your current queue to
the full **Convert Audio** dialog. It is the same dialog QUILL's Audio Studio
opens, so there is only one converter to learn.

The dialog repeats the queue and the format/preset/output controls, and adds:

- **Include sub-folders** (Alt+I, a check box, on by default) -- whether a
  queued folder is scanned right through or only at its top level. Each folder
  row in the queue says which it will be.
- **On conflict** (Alt+C, a combo box): "Rename (auto-number) -- never
  overwrites" (the default), "Skip files that already exist", or "Overwrite
  existing files".
- **Advanced options** (Alt+P, a check box). Ticking it reveals the panel below
  and moves focus to its first control, so the reveal is announced rather than
  being a silent resize. Unticking it puts focus back on the check box.

The revealed panel, in order:

- **Bit rate** (Alt+R): Auto (use preset), 96, 128, 192, 256, or 320 kbps.
- **Sample rate** (Alt+M): Keep source rate, 48 kHz, 44.1 kHz, 22.05 kHz,
  16 kHz.
- **Channels** (Alt+H): Keep source channels, Mono, Stereo.
- **Bit depth** (Alt+D): Keep source depth, 16-bit, 24-bit, 32-bit float.
- **Loudness** (Alt+L): No loudness normalization, Audiobook / ACX (-20 LUFS),
  or Podcast / streaming (-16 LUFS).
- **Gain (dB)** (Alt+G): -30 to +30 in half-decibel steps. 0 means no change.
- **Speed (tempo)** (Alt+S): 0.5x to 2.0x, no pitch shift. 1.0 is unchanged.
- **Fade in (seconds)** (Alt+I) and **Fade out (seconds)** (Alt+O): 0 to 10.
- **Remove low-frequency rumble (high-pass)** (Alt+U).
- **Trim leading and trailing silence** (Alt+T).
- **Compress dynamics (even out loud/quiet)** (Alt+C).
- **Level volume across the file** (Alt+V).

Every one of these starts on a neutral "leave the preset alone" value, so an
Advanced panel you opened but did not touch changes nothing.

The dialog's affirmative button is labelled **Convert**; **Cancel** and Escape
both back out without converting, and cancelling is announced.

## Convert from URL

**Convert from URL...** (Alt+U, or File > Convert from URL...) takes a web
address, downloads the audio from it, and opens the Convert Audio dialog with
that file already in the queue.

What happens, in order:

1. A text box asks you to paste a link. Anything that is not a full `http://`
   or `https://` address is rejected with a plain explanation.
2. The first time only, a consent dialog explains that this feature uses
   **yt-dlp** to download audio from a web address, that Quill Converter will
   download and install that component on demand (about 3 MB, from PyPI), that
   you should only download content you have the right to use, and that no
   account or credential of yours is sent to the site. Answer **Yes** to
   continue or **No** to stop; answering No is announced and nothing is
   installed.
3. The download runs in the background with spoken progress, then the Convert
   Audio dialog opens on the downloaded file.

yt-dlp is never bundled with Quill Converter. It is installed only if you say
yes, and the whole feature is **unavailable in Safe Mode** -- asking for it
there says so and stops.

## The tray, and staying out of the way

Quill Converter lives in the notification area while it works.

- **Minimize to Tray** (Ctrl+W, or File > Minimize to Tray) hides the window;
  the same command brings it back. Hiding and showing are both announced.
- **Ctrl+Alt+Shift+C** does the same thing from anywhere in Windows, even when
  another program has focus. If another program already owns that chord, Quill
  Converter quietly leaves it alone rather than fighting for it.
- Right-click the tray icon (or double-click it to just restore the window) for
  **Show Quill Converter**, **Open Quill Converter**, and **Exit Quill
  Converter**.
- While a batch runs, the tray tooltip carries the same progress text as the
  status bar, so a minimized conversion is still reviewable.
- Starting the app with `--tray` opens it straight into the tray with no window.

**Exit** (File > Exit, or the tray menu) really exits. Alt+F4 closes the window.

## The other menus

**QuillVille** lists the sibling apps that have shipped a public release --
Open QUILL, Open Quill Radio, Open Quill Weather -- so the family is always one
keystroke apart. Choosing one that is not installed offers to get it rather than
failing silently.

**Window** carries the standard window switcher: Ctrl+Tab for the next window,
Ctrl+Shift+Tab for the previous, and Ctrl+1 through Ctrl+9 to jump to one
directly.

**Help** has **Check for Updates...** and **About Quill Converter**. Check for
Updates looks at Quill Converter's own releases, downloads the right one for how
you installed (installer or portable), speaks progress milestones, and then
offers to install it. Each app in the family updates independently.

## Using it with a screen reader

- **Focus at launch** lands on the Files to convert list, never on a bare frame.
- **Everything is announced.** Queue counts, progress, the end-of-run summary,
  "nothing to convert", hiding and showing to the tray -- all of it goes through
  the shared announcement engine, which speaks through your screen reader (JAWS,
  NVDA, Narrator) without stealing focus, and writes to your **braille display**
  as well as speaking.
- **The status bar is the visual floor**, so nothing is spoken-only and nothing
  is colour-only.
- **Every control has an accessible name**, including the ones whose visible
  label sits beside them.
- **Access keys** are on every button and field (listed above). Menus are
  Alt+F for File, Alt+Q for QuillVille, Alt+W for Window, Alt+H for Help. On
  the File menu: Alt+A Add Files, Alt+O Add Folder, Alt+U Convert from URL,
  Alt+V Advanced Options, Alt+T Minimize to Tray, Alt+X Exit.
- **Delete** removes the selected queue row; you never need a mouse to manage
  the queue.
- **No dialog traps.** The Convert Audio dialog has a real Cancel that Escape
  reaches, and its Advanced reveal moves focus so you hear the change.

## Where your settings live

Quill Converter shares one settings store with QUILL and the rest of the family,
so a preference set in one app is honoured in the others.

- **Installed:** `%APPDATA%\Quill`.
- **Portable:** if you run the portable build, the folder beside the program
  contains a `data` folder, and once you choose portable storage everything --
  settings, logs, keymap -- lives there and travels with the stick instead of
  touching the machine you plug it into.

Uninstalling Quill Converter never deletes that shared folder; QUILL or another
family app may still be using it.

## Safe Mode

Setting `QUILL_SAFE_MODE=1` before launching starts Quill Converter in Safe
Mode: the default keymap is used instead of your saved one, unlocks are not
persisted, and **Convert from URL** is refused outright. Ordinary conversion
still works completely -- it is all local.

## For scripts: `quill convert`

Everything above is also available without a window, over the same engine:

```
python -m quill convert INPUT... --to FORMAT [options]
```

Inputs can be files, folders, or glob patterns; folders mirror their tree.
`--preset` picks a starting recipe (`--list-presets` prints them), `--out` sets
the destination, `--recurse` descends into sub-folders, and `--dry-run` plans
the batch and prints what it would do without converting anything.
