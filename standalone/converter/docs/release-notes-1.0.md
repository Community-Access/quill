# Quill Converter 1.0.0 Release Notes

Released September 28, 2026.

Somewhere between "I recorded this in the wrong format" and "my player will not
open this," almost everybody hits the wall of media conversion. The usual answer
is a website that wants you to upload your file, sit through an advertisement,
and trust a stranger with your recording -- or a program whose every button is
unlabeled to a screen reader.

Quill Converter is the other answer. It runs entirely on your own computer, it
was built for screen readers from the first line, and with 1.0.0 it converts
video as well as sound.

This is Quill Converter's first public release. The app was first built in July
2026 as an audio converter; it did not ship then, and the months since went
into making it the converter we wanted to hand people: video, effects you can
hear before you commit, chapters that survive every conversion, joining and
splitting, an Explorer right-click, and reasons instead of error codes when
something fails.

## Downloads

Two downloads. Choose one.

- **Quill-Converter-Setup-Shared-1.0.0.exe** -- the installer, recommended. It
  installs the shared QuillVille runtime if the computer does not already have
  it, then the app, with a Start Menu entry and an uninstaller.
- **Quill-Converter-Portable-1.0.0.zip** -- unpack anywhere, a USB stick
  included. It keeps its settings in its own `data` folder next to the app and
  writes nothing to the computer it runs on.

## Everything is included

Nothing downloads the first time you use a feature. Both downloads carry:

- **FFmpeg and ffprobe**, which do the converting and read what is inside a
  file.
- **libmpv**, the mpv playback engine, as the Chapter Workbench's player.
- **yt-dlp**, for Convert from URL, and **deno**, the JavaScript runtime it
  needs for YouTube.
- **mutagen**, for carrying cover art and chapters into the converted copy.
- **The OptiLab Core adapter**, for broadcast polish in Advanced Options, in
  builds that include it.

Conversion never touches the network. The only things that do are Check for
Updates and Convert from URL, and both only when you ask.

## What is new, and why

### A video, a whole playlist, or a channel

Paste a link into **Convert from URL** (Ctrl+U). One video downloads its
audio. A playlist asks whether you want all of it or the first few; a YouTube
channel asks which section (videos, Shorts, live streams), how many of the
newest, and from how recently. Every video's audio joins the queue in order,
numbered and tagged as one album with track numbers, ready for Ctrl+Enter --
or for Join into One File, which makes a lecture series one audiobook with a
chapter per video. Paste the same link next week and only the new videos
download. A private or removed video is listed in the report rather than
stopping the rest, and Stop works mid-download like everywhere else.

### Right-click to convert

The installer adds **Convert with Quill Converter** to the File Explorer
right-click menu for every audio and video type the app reads. It is checked by
default, applies to your Windows account only, and the uninstaller removes it.
Select fifty files, choose it once, and all fifty arrive in one window, in one
queue -- not fifty windows, and not one file and forty-nine lost. The fastest
way to convert a file is from where you already are.

### 34 formats out, 82 in

Quill Converter writes 25 sound formats and 9 video formats, and reads 82 file
types: everyday audio, lossless and archival formats such as WavPack, APE and
DSD, film sound such as AC-3 and DTS, phone formats such as AMR, older formats
such as RealAudio and Musepack, tracker music, and 30 kinds of video file.

Each format is spoken with what it is for -- "M4B audiobook -- remembers your
place in book players" -- so you choose by purpose, not by acronym. And the list
only offers what the bundled FFmpeg can really write, so a hundred-file batch
never dies half way because an encoder was missing.

Some formats are fussy, and that is now the converter's problem instead of
yours. A format that only accepts certain sample rates (AC-3, E-AC-3, MP2, Opus,
WebM audio, Speex, AMR) gets the nearest rate it accepts; AMR is made mono;
lossless formats ignore a bit rate that means nothing to them.

### Video

Converting a video to a sound format keeps its sound. Converting it to a video
format keeps it a video: MP4 (H.264 or H.265), MKV, WebM, MOV, AVI, WMV, MPEG-2
or Ogg Theora. The video presets are named for the result, not the codec
setting: **Same quality**, **Phones and the web, up to 1080p**, **Smaller file,
up to 720p**, **Smallest file, up to 480p**, and **Change the container only**,
which copies the picture and sound untouched in seconds.

H.264 and H.265 run on the computer's graphics chip when it has a video
encoder -- NVIDIA, Intel or AMD, which most Windows computers have -- typically
several times faster than the processor alone: on our test laptop a 1080p film
to H.265 went from half the speed of playback to five times it, with a file
the same size. It is tried once with a moment of test picture and used only if
it works, and any file it fails on is converted again on the processor.
Nothing to set.

A film's described-audio track and its second language come through in MP4,
MKV, MOV and WebM, and MKV keeps the subtitles. We would rather a converter
never quietly drop the one track a blind viewer needed.

### Effects named for the problem they solve

A new **Effects** choice on the main window offers twelve recipes named for
what is wrong: Clean up speech, Podcast ready, Audiobook ACX ready, Clearer voice
for listening, Louder dialogue for films and TV, Night listening, music and
broadcast loudness, hum, noise, long silences, and bass. You should not have to
know what a de-esser is to fix sibilance.

**Custom Effects** (Ctrl+E) puts every switch on one page, starting from the
recipe you chose, so you can take "Podcast ready" and change one thing. It also
has loudness targets, gain, speed, fades, and "keep from" and "keep until" for
trimming an intro or making a ringtone. Effects apply to the sound of video
conversions too.

### Hear it before you convert

**Preview** (Ctrl+P) plays fifteen seconds exactly as the result will sound: the
clip is really encoded in the chosen format with the chosen effects, then played
back. **Hear Original** (Ctrl+Shift+P) plays the same fifteen seconds untouched.
Compare them, change something, compare again -- before you spend an hour
converting a whole audiobook.

### Chapters, through every conversion

Chapter marks are how somebody who cannot glance at a waveform finds their way
around a long recording, so Quill Converter treats them as content, not as
metadata that may or may not survive. A new **Chapter marks** choice on the
main window (Alt+K) says where they come from:

- **Keep each file's own chapters** -- the default.
- **Use the chapter list beside each file** -- chapters you wrote yourself.
- **Find chapters at the pauses** -- a pause of two seconds or more, and no
  chapter shorter than 20 seconds.
- **A chapter every 5, 10, 15, 30 or 60 minutes** -- Part 1, Part 2 and so on.
- **Remove all chapters.**

You can define chapters for any format with a plain text file. Beside
`Lecture 3.mp3`, save `Lecture 3.chapters.txt` with lines such as
`0:00 Welcome`, `1:30 Questions` and `1:02:05 Summary`, and choose "Use the
chapter list beside each file". A `.cue` sheet, Podcasting 2.0 `.chapters.json`,
Audacity labels (`.labels.txt`) or a plain `.txt` that reads as a chapter list
work too. A file with no list keeps its own chapters.

Chapters land wherever the format can hold them. FFmpeg writes them inside MP3
(ID3 CHAP and CTOC), M4B, M4A, Apple Lossless, M4R, MP4, MOV, MKV, MKA, WebM,
Opus and WMA. Ogg Vorbis, FLAC, Speex and Ogg video get the CHAPTER001 comments
their players read. Every other format -- WAV, AIFF, WavPack, AC-3 and the rest
-- has no place for chapters, so a `.cue` sheet is written beside the converted
file. Nothing is silently lost. Keep from and Keep until trim the chapters to the part you keep.

The **Chapter Workbench** (Queue > Chapter Workbench..., Ctrl+H) opens the
highlighted MP3, M4B or M4A in the Audio Studio's Chapter Workbench, with a
player: rename, split at the playhead, set a start to the playhead, merge, find
chapters at silences, import and export chapter lists (Audacity labels, CUE,
timestamps, Podcasting 2.0 JSON, CSV), edit the book's details or, with All
tags..., every tag in the Tag Editor, save, and split into files. The player is libmpv, now bundled in both downloads, so it seeks
exactly.

### Join and split

**Join into One File** (Ctrl+J) puts the whole queue, in order, into one sound
file with one chapter per source, named from its title or a tidied file name --
inside the file for every format that holds chapters, MP3 included, and as
comments or a `.cue` sheet for the rest. A folder of MP3 chapters becomes one
audiobook your book player can navigate.

**Split by Chapters** (Ctrl+Shift+S) goes the other way: one file per chapter,
numbered, titled and tagged, in a folder named after the book. It follows the
Chapter marks choice, so "A chapter every 30 minutes" cuts a ten-hour recording into
30-minute files, "Find chapters at the pauses" cuts at the pauses, and a
chapter list beside the file cuts exactly where you said.

### Advanced Options, in the main window

The exact encoder settings are on the main window, not in a second window.
**View > Advanced Options** (Ctrl+Alt+V) shows or hides an Advanced section and
moves focus into it: quality (bit rate), sample rate, channels, bit depth, what
to do if a file already exists (number it, skip it or replace it), Broadcast
polish where the build has the OptiLab Core engine, and "Look in subfolders
too". Each starts on its neutral choice, so showing them changes nothing until
you change one, and they shape the same Convert as everything else on the page.

### A queue you can work with

Paste files you copied in File Explorer (Ctrl+V), drop them on the list, reorder
with Alt+Up and Alt+Down, clear with Ctrl+Shift+Delete. **File Properties**
(Alt+Enter) tells you what is inside a file -- its length, tracks, languages,
cover art and chapters -- in plain words, before you convert it. **Edit Tags**
(Ctrl+T) opens Audio Studio's Tag Editor right inside Quill Converter: every
tag of an MP3, M4A, M4B or MP4 over five pages, and its cover art.

### Reasons, not error codes

When a file fails, the report says why in words you can act on -- "The file is
copy-protected and cannot be converted", "The output drive is full" -- followed
by FFmpeg's own line for support. The **Conversion Report** (Ctrl+R) lists every
file and has a Copy All button for an email.

Convert becomes Stop while it runs, and Stop is immediate: the file being
converted stops as well, its unfinished output is removed, and the report
lists it as skipped. Progress is counted inside each file from FFmpeg's own
progress output, so one long audiobook moves from 0 to 100 percent rather than
sitting silent until it ends. It is spoken at 25, 50 and 75 percent; the status
bar and tray tooltip update about once a second with the percentage and about
how long is left ("Converting Book.m4b: 42 percent, about 3 minutes left");
and a progress bar under the buttons fills as it goes. The bar stays out of
the Tab order, since the status bar already says the same in words. Cover art is carried into MP3, M4A, M4B, FLAC, Ogg
and Opus copies where FFmpeg would have dropped it. And your format, presets,
effects and output folder are remembered for next time.

### Help that matches the family

The Help menu now has the same doors as Quill Radio and QUILL Lite, on the same
keys: F1 for the window you are in, the User Guide, Release Notes, Changelog and
Product Requirements, a Keyboard Shortcuts list (Ctrl+Alt+K), Get Help from
Support (Ctrl+Alt+F2), Get FFmpeg for repair, and Check for Updates.

Support is by email, to a person: **support@community-access.org**. Get Help
from Support writes the message in your own mail program, with the app's version
filled in, and nothing goes until you send it.

### In the family

Quill Converter now appears on the QuillVille menu of the other apps, and QUILL's
own **Convert with Quill** Explorer entry, which opens Quill Converter, is
available in public builds.

## Fixes since the July build

- **AIFF output works.** AIFF and AU are written in the byte order those formats
  require; AIFF files from the July build failed.
- **32-bit WAV is real 32-bit float**, as the Bit depth setting says.
- **Several Explorer selections make one queue**, not a string of lost launches.
- **A format's constraints no longer fail a file** half way through a batch.

## Known limits

- **WebM (VP9) video is slow**, and so is H.265 on a computer whose graphics
  chip has no video encoder. MP4 H.264 is the fastest choice. Video files are
  converted one at a time.
- **Change the container only can fail** when a file's picture or sound does
  not fit the new container. The report says so in those words; choose Same
  quality instead.
- **Copy-protected (DRM) files cannot be converted**, such as protected Audible
  books or iTunes purchases. The report says so.
- **The Chapter Workbench saves MP3, M4B and M4A.** For other formats, write a
  chapter list beside the file and choose it in Chapter marks, or convert to M4B or
  MP3 first.
- **Preview ignores chapters**; it plays fifteen seconds of sound.

## Getting help

Write to **support@community-access.org**, or use Help > Get Help from
Support... (Ctrl+Alt+F2). Community Access reads every message.
