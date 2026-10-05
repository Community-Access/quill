# Quill Converter User Guide: Converting Audio and Video on Your Own Computer

Version 1.0.0 -- September 28, 2026

## Introduction

Quill Converter changes audio and video files from one format into another, on
your own computer, without uploading anything to a website. Sound to sound,
video to sound, and video to video. It can clean up the sound on the way
through, let you hear the result before you commit, join a pile of files into
one audiobook, and split a chaptered book back into its chapters.

It is a small window with a queue, a few choices and a Convert button. Focus
lands on the queue the moment it opens, every control has a name, most have an
access key, and everything runs from the keyboard. It was built for screen
readers from the first line: every action says what it did, and the status bar
always carries the same words.

### What you will be able to do

By the end of this guide you will be able to:

- turn a recording into the format your player, phone or editor wants;
- pull the sound out of a video, or make a video smaller;
- clean up speech, even out loudness, and hear the result before you convert;
- keep, write, find and edit chapters, so a long recording stays easy to move
  around in;
- join a folder of files into one audiobook, or split a book into its chapters;
- download the sound of a video, a playlist or a channel from a link.

### How this guide is laid out

Each chapter starts with what it covers and ends with a short summary of what
you learned and where to go next. You do not have to read them in order.

1. **Getting started** -- installing, your first conversion, and the main
   window.
2. **Formats** -- what Quill Converter reads and writes, video included.
3. **Making it sound right** -- presets, effects, and hearing a preview.
4. **Chapters** -- keeping them, writing your own, the Chapter Workbench, and
   joining and splitting.
5. **Working with the queue** -- adding, ordering, tags, the report, and
   Advanced Options.
6. **Converting from a link** -- one video, a playlist, or a channel.
7. **Out of the way, and easy to find** -- the tray, a key to show and hide
   Quill Converter, and finding any command by name.
8. **When you need a hand** -- F1, troubleshooting, updates and support.

The keyboard reference at the end lists every key in one place.

### Reading this guide with a screen reader

Every chapter is a level 2 heading and every topic inside it is a level 3
heading, so your screen reader's heading keys move through the guide a topic at
a time. Keys are written the way you press them, such as Ctrl+Enter. A menu
path such as **File > Add Files...** means open the File menu and choose Add
Files. Help > User Guide (Ctrl+F1) opens this guide from inside the app.

## Chapter 1: Getting started

This chapter gets Quill Converter onto your computer and walks you through one
conversion from start to finish. Then it tours the main window, so you know
where everything is.

### Installing

There are two downloads. Choose one.

- **Quill-Converter-Setup-Shared-1.0.0.exe** -- the installer, recommended for
  most people. It installs the shared QuillVille runtime if this computer does
  not have it yet (the same runtime QUILL and Quill Radio use), then the app,
  with a Start Menu entry and an uninstaller.
- **Quill-Converter-Portable-1.0.0.zip** -- the portable copy. Unpack it
  anywhere, including a USB stick or a folder with spaces in its name, and run
  `QuillConverter.exe`. It keeps its settings in its own `data` folder next to
  the app and writes nothing to the computer it runs on.

Nothing downloads the first time you use a feature. Both downloads already
contain everything the app needs: FFmpeg and ffprobe (which do the converting
and reading), libmpv (the mpv playback engine, the Chapter Workbench's player),
yt-dlp (for Convert from URL), mutagen (for carrying cover art and chapters
across) and, in builds that include it, the OptiLab Core broadcast-polish
adapter.

#### The File Explorer right-click menu

The installer offers three choices, each a real Windows checkbox that a screen
reader announces as checked or not checked: **Create a desktop icon** (off by
default), **Add "Convert with Quill Converter" to the File Explorer
right-click menu** (on by default), and, on the last page, **Launch Quill
Converter** (off by default). With the File Explorer entry on, right-click
any audio or video file Quill Converter reads and choose
**Convert with Quill Converter**. The file opens in Quill Converter, already
queued.

- Select many files first and choose it once: they all land in the same window,
  in one queue. Quill Converter only ever runs one copy of itself, so a second
  launch hands its files to the window that is already open.
- The entry is added for your Windows account only, and the uninstaller removes
  it.
- `.ts` files are left off this menu, because on many computers `.ts` is a
  TypeScript source file rather than video. Add Files and Add Folder still take
  them.

QUILL has its own, separate setting for a **Convert with Quill** entry; it also
opens Quill Converter. You do not need both.

### Your first conversion

1. Start Quill Converter from the Start Menu. Focus is on the **Files to
   convert** list.
2. Press Alt+A (**Add Files...**) and choose one or more files. Or press Alt+O
   (**Add Folder...**) to add a whole folder, sub-folders included. You can
   also paste files you copied in File Explorer with Ctrl+V, or drop them on
   the list.
3. Press Alt+T to reach **Convert to** and choose a format with the arrow keys.
   Each format is spoken with what it is for, for example "MP3 audio -- plays
   everywhere".
4. Press Alt+P for **Preset** and choose how the result is made, or leave it on
   "Just convert (no processing)".
5. If you want the sound improved, press Alt+E for **Effects** and choose a
   recipe named for the problem it solves, such as "Clean up speech".
6. If the files have chapters, or you want some, press Alt+K for **Chapter marks**.
   The default, "Keep each file's own chapters", carries them across as they
   are. See [Where chapters come from](#where-chapters-come-from).
7. Press Alt+Y (**Play Preview**) to hear fifteen seconds exactly as the converted
   file will sound. Press it again to stop.
8. Press the **Convert** button, or Ctrl+Enter from anywhere in the window.

Progress is announced at 25, 50 and 75 percent, counted inside each file as well
as across the queue, so one long audiobook is not silence until it ends. The status
bar says how far it has got and, once it can tell, about how long is left, and the
**Progress** bar under the buttons fills as it goes. The run ends
by saying how many files converted and naming any that did not. If anything
failed, Ctrl+R opens the Conversion Report with the reason for each one.

Converted files go to the **Output folder**. Leave it empty and Quill Converter
makes a folder named `Converted` beside the first file in the queue. Your
originals are never changed, and an existing file is not overwritten: a
converted file whose name is taken is numbered instead, unless you choose
otherwise in [Advanced Options](#advanced-options).

Quill Converter remembers your format, presets, effects, custom effects, the
keep-from and keep-until times, the Chapter marks choice, the Advanced Options, and
the output folder between runs, so the next job starts where the last one
ended.

### The main window

Tab order, top to bottom, with each control's access key:

- **Files to convert** -- the queue (focus starts here). A folder reads as "name (folder)".
- **Add Files...** (Alt+A), **Add Folder...** (Alt+O), **Remove** (Alt+R).
- **Convert to** (Alt+T) -- the output format. Sound formats come first, then
  video.
- **Preset** (Alt+P) -- quality settings chosen for a purpose. The list changes
  with the format: sound presets for a sound format, video presets for a video
  format.
- **Effects** (Alt+E) and **Custom Effects...** (Alt+S).
- **Chapter marks** (Alt+K) -- where the converted files' chapters come from -- and
  **Chapter Workbench...**.
- **Output folder** (Alt+D) and **Browse...** (Alt+B).
- The **Advanced** section, when View > Advanced Options (Ctrl+Alt+V) is
  checked. See [Advanced Options](#advanced-options).
- **Convert** (Ctrl+Enter), **Play Preview** (Alt+Y), **Hear Original** (Alt+G),
  **From URL...** (Alt+L).
- **Progress** -- a progress bar, named "Conversion progress", under the
  buttons. It shows how far a conversion has got, counting inside each file as
  well as across the queue, and is empty when nothing is converting. It is not
  in the Tab order, because a progress bar never takes focus; review the window
  to find it, or simply listen to the status bar, which says the same in words
  with about how long is left.

The menu bar is File, Queue, View, Convert, QuillVille, Help and Window, and no
control on the window uses a menu's letter, so Alt+F always opens the File menu.

While a conversion runs, the Convert button becomes **Stop Converting**, and
Ctrl+Enter stops as well.

Press F1 on any control to hear what it does, after a sentence about what the
window is for.

### What you learned, and where to go next

You can install Quill Converter, add files, choose a format, and press
Ctrl+Enter. You know that your originals are never changed, and that the
converted copies go to the output folder. Next, Chapter 2 explains the formats,
so you can choose one by what it is for.

## Chapter 2: Formats

Quill Converter reads 82 kinds of file and writes 34. This chapter lists them,
explains what the fussier formats decide for you, and covers video.

### What it reads

Quill Converter reads 82 file types. Sound files:

- **Everyday:** MP3, WAV, FLAC, OGG, OGA, Opus, M4A, M4B, AAC, WMA, AIFF, AIF,
  AIFC, ALAC, CAF, MKA, WEBA, M4R.
- **Lossless and archival:** APE (Monkey's Audio), WV (WavPack), TTA, TAK, SHN
  (Shorten), W64, RF64, BWF, DSF, DFF.
- **Film and broadcast:** AC3, EAC3, EC3, DTS, THD, MLP, MP2, MP1, MPA.
- **Phones, voice and telephony:** AMR, AWB, SPX (Speex), GSM, AU, SND, VOC.
- **Older and specialist:** MPC (Musepack), RA (RealAudio), OMA, AA3.
- **Tracker music:** MOD, XM, IT, S3M.

Video files:

- MP4, M4V, MKV, MOV, QT, WebM, AVI, DIVX, FLV, F4V, WMV, ASF, MPG, MPEG, MPE,
  VOB, TS, MTS, M2TS, M2T, 3GP, 3G2, OGV, RM, RMVB, MXF, DV, WTV, DVR-MS, NUT.

A file with a name ending in one of these that turns out to be damaged, or not
really that kind of file, fails on its own; the rest of the batch carries on.

### What it writes

34 formats: 25 sound and 9 video. The **Convert to** list only shows the ones
the bundled FFmpeg can actually write, so a batch never stops half way because
an encoder was missing.

Sound formats, in the order the list offers them:

- MP3 audio -- plays everywhere
- M4A audio (AAC) -- Apple devices and phones
- M4B audiobook -- remembers your place in book players
- Opus audio -- smallest files for speech
- Ogg Vorbis audio -- open format
- FLAC -- lossless, smaller than WAV
- WAV -- uncompressed, for editing
- AAC audio stream (.aac)
- AIFF -- uncompressed, Apple
- Apple Lossless (ALAC, .m4a)
- WMA -- Windows Media Audio
- CAF -- Core Audio Format
- AC-3 (Dolby Digital) -- DVD and home theater
- E-AC-3 (Dolby Digital Plus)
- MP2 -- broadcast and DVD audio
- WavPack -- lossless
- TTA (True Audio) -- lossless
- MKA -- Matroska audio, lossless FLAC inside
- WebM audio (Opus) -- for web pages
- M4R -- iPhone ringtone
- Speex -- low bit rate speech
- AMR narrowband -- phone voice memos
- AMR wideband -- clearer phone voice
- AU -- Sun and Java audio
- Wave64 -- WAV for files over 4 GB

Video formats:

- MP4 video (H.264) -- plays everywhere
- MP4 video (H.265, HEVC) -- half the size, newer devices
- MKV video (H.264) -- keeps every audio and subtitle track
- WebM video (VP9) -- for the web
- MOV video (H.264) -- QuickTime and Apple editing
- AVI video (Xvid) -- older players and TVs
- WMV video -- Windows Media
- MPEG-2 video -- DVD players
- Ogg video (Theora) -- open format

#### What the formats decide for you

Some formats only accept certain settings. Quill Converter makes the file right
rather than letting it fail:

- **Sample rates.** AC-3, E-AC-3, MP2, Opus, WebM audio, Speex and AMR only
  accept certain sample rates. If a preset or Advanced Options asks for one
  they do not accept, the file gets the nearest rate the format does accept.
  AMR narrowband is always 8 kHz and AMR wideband 16 kHz.
- **Channels.** AMR is always mono, so a stereo file is mixed down.
- **Bit rates.** Lossless and uncompressed formats (WAV, FLAC, AIFF, ALAC, CAF,
  WavPack, TTA, MKA, AU, Wave64) ignore a bit rate, because it means nothing to
  them.
- **Byte order.** AIFF and AU are written the way those formats require, so an
  AIFF made by Quill Converter opens everywhere.
- **32-bit.** Choosing 32-bit in Advanced Options for WAV, Wave64 or CAF
  gives real 32-bit floating point.

### Converting video

- **Video to a sound format** keeps its sound. This is how you get the audio
  out of a recorded lecture, a film or a music video.
- **Video to a video format** keeps it a video, with the picture re-encoded in
  the new format.
- **A sound file queued for a video format** is skipped, because a video needs
  a picture. The end-of-run summary says how many were skipped and why.
- **Every audio track is kept** in MP4, MKV, MOV and WebM -- a described-audio
  track or a second language comes through. The other video formats keep the
  first audio track.
- **Subtitles** are kept in MKV.
- **Effects apply to the sound** of a video conversion too, so "Louder dialogue
  for films and TV" on a film gives you a new film with clearer speech.
- **Video files are converted one at a time**, because a video encoder already
  uses every core of the computer. Several at once would only make each slower.
- **The graphics card does the heavy lifting when it can.** MP4, MKV and MOV
  video (H.264) and MP4 H.265 are encoded on the computer's graphics chip when it
  has a video encoder -- NVIDIA, Intel or AMD, which most Windows computers
  have -- typically several times faster than on the processor. Quill
  Converter tries it once per session with a fraction of a second of test
  picture and uses it only if it works; if a real conversion on it ever fails,
  that file is converted again on the processor, and the processor is used for
  the rest of the session. There is nothing to set. WebM (VP9), AVI, WMV,
  MPEG-2 and Ogg Theora always use the processor.

#### Video presets

When the format is a video format, the Preset list offers:

- **Same quality (recommended)** -- looks the same as the original, at the
  original size.
- **Phones and the web, up to 1080p** -- good quality in a noticeably smaller
  file.
- **Smaller file, up to 720p** -- for sharing and messaging; about a quarter of
  the size.
- **Smallest file, up to 480p** -- for slow connections and small screens.
- **Change the container only (fastest, no quality loss)** -- copies the
  picture and sound untouched into the new format. It takes seconds rather than
  minutes, but effects cannot apply (you are told they were skipped), and some
  combinations of picture and sound do not fit every container. When that
  happens the file fails with a reason that says so; choose one of the other
  presets instead.

A size limit never makes a picture bigger: a 480p video on "up to 1080p" stays
480p.

### What you learned, and where to go next

You know what goes in and what comes out, and that a video can become sound or
stay a video. When a format is fussy, Quill Converter makes the file right
rather than letting it fail. Chapter 3 is about how the result sounds.

## Chapter 3: Making it sound right

A preset decides the quality of the result. An effect fixes something in the
sound on the way through. A preview lets you hear both before you spend time
converting a whole batch.

### Sound presets

When the format is a sound format, the Preset list offers:

- **Just convert (no processing)** -- a pure format change. The default.
- **MP3 320 kbps (maximum quality)**, **MP3 192 kbps**, **MP3 128 kbps
  (small)**.
- **Podcast (MP3, spoken word)** -- mono MP3 for talk, with a rumble filter.
- **Audiobook (M4B)** -- mono M4B at a compact bit rate.
- **Voice memo (small MP3)** -- mono, 22 kHz, tiny files for spoken notes.
- **Web voice (Opus)** -- mono Opus at a low bit rate, the smallest for the
  web.
- **Archival (FLAC, lossless)** -- keeps the original rate and channels.
- **Hearing-aid mono** -- everything mixed down to one channel.

Each preset is spoken with a sentence about what it is for. The **Convert to**
choice always wins over a preset's own format, so you can take the Podcast
preset and still ask for Opus. Quill Converter remembers your last sound preset
and your last video preset separately.

### Effects

The **Effects** choice (Alt+E) is what to do to the sound on the way through.
Each recipe is named for the problem it solves, so you do not need to know what
a de-esser is to use one.

- **No effects** -- the sound is converted exactly as it is.
- **Clean up speech** -- removes rumble, hum and steady background hiss, softens
  harsh s sounds, and sets a comfortable listening level.
- **Podcast ready** -- cleans the voice, evens out loud and quiet speakers, and
  meets the podcast loudness standard of -16 LUFS.
- **Audiobook, ACX ready** -- rumble filter, gentle noise reduction and the ACX
  loudness window of -20 LUFS with peaks held under -3 dB, as Audible requires.
- **Clearer voice for listening** -- lifts the frequencies that carry
  consonants, trims muddiness, and evens out the level; easier on the ears and
  on hearing aids.
- **Louder dialogue for films and TV** -- brings speech forward over music and
  effects, then evens out the loudness so explosions and whispers sit closer
  together.
- **Night listening** -- quiet parts come up and loud parts come down, so you
  can listen at low volume without reaching for the control.
- **Music, streaming loudness** -- normalizes to -14 LUFS, the level Spotify,
  YouTube and Apple Music play at, with a safety limiter.
- **Broadcast standard, EBU R128** -- normalizes to -23 LUFS, the loudness
  standard for television and radio.
- **Remove electrical hum** -- notches out 50 and 60 Hz mains hum and its first
  harmonic, and the rumble below it.
- **Reduce background noise** -- takes down steady hiss, fan and
  air-conditioner noise.
- **Remove long silences** -- cuts every pause longer than half a second;
  lectures and voice memos get shorter without losing a word.
- **Bass boost** -- adds warmth and weight to thin-sounding music or small
  speakers.
- **Custom** -- the effects you chose in the Custom Effects dialog.

#### Custom Effects

**Custom Effects...** (Alt+S on the main window, or Ctrl+E from anywhere) puts
every effect on one page. It opens showing exactly what the current Effects
choice does, so you can pick "Podcast ready", open Custom Effects, and change
one thing. Pressing OK makes the result your **Custom** recipe and selects it.

Check boxes, in the order they are applied:

- **Remove low rumble** -- cuts the rumble below 30 Hz: traffic, handling noise,
  air conditioning.
- **Remove electrical hum** -- the 50 and 60 Hz mains hum a ground loop or a
  cheap cable adds.
- **Reduce background noise** -- steady hiss and fan noise, gently.
- **Remove long silences** -- every pause longer than half a second.
- **De-ess (soften harsh s sounds)**.
- **Voice clarity** -- lifts consonants and trims muddiness.
- **Bass boost** -- six decibels of warmth below 100 Hz.
- **Treble boost** -- brightness above 4 kHz.
- **Dialogue boost (films and TV)** -- speech forward over music and effects.
  The result is stereo.
- **Compress dynamics** -- evens out loud and quiet passages.
- **Speech leveling** -- brings each phrase to a similar level, quickly; good
  for a speaker who drifts away from the microphone.
- **Night mode leveler** -- slowly rides the volume for listening quietly.
- **Peak limiter** -- stops any peak going above -1 dB, so a loudness boost can
  never clip. Recommended whenever loudness or gain is on.

Then:

- **Loudness target** -- no normalization, Audiobook / ACX (-20 LUFS), Podcast /
  streaming (-16 LUFS), Music streaming (-14 LUFS), or Broadcast TV and radio,
  EBU R128 (-23 LUFS).
- **Gain in decibels** -- a flat volume change from -30 to +30. 0 changes
  nothing.
- **Playback speed** -- from 0.5 to 2.0, without changing pitch. 1.0 is
  unchanged.
- **Fade in** and **Fade out**, in seconds, up to 30.
- **Keep from, seconds into each file** -- start every converted file this far
  in. Handy for trimming an intro, or making a ringtone.
- **Keep until, seconds** -- stop every converted file here. 0 keeps everything
  to the end.

Keep from and Keep until apply to every file in the run, whichever effect
recipe is chosen, and they are remembered until you change them. When they are
set, Quill Converter says so as part of what Convert will do. Chapters follow
the cut: a chapter partly inside the kept part is trimmed to it, one wholly
outside is dropped, and the rest are shifted so the first starts at zero.

### Preview: hear it before you convert

- **Play Preview** (Alt+Y, or Ctrl+P) plays fifteen seconds of the highlighted file,
  or of the first file in the queue, exactly as it will sound after conversion.
  The clip is really encoded through the chosen format and effects and then
  played back, so a low bit rate sounds like a low bit rate.
- **Hear Original** (Alt+G, or Ctrl+Shift+P) plays the same fifteen seconds
  untouched, so you can compare the two back to back.
- Press either one again to stop.

The fifteen seconds start a quarter of the way into the file, and never more
than 30 seconds in, because the first seconds of most recordings are silence, a
jingle or somebody asking whether the microphone is on. For a video format you
hear the sound the new video will have.

### What you learned, and where to go next

Choose a preset for the quality, an effect for the problem, and press Ctrl+P to
hear fifteen seconds before you commit. Custom Effects (Ctrl+E) lets you take a
recipe and change one thing. Chapter 4 is about chapters.

## Chapter 4: Chapters

Chapter marks are how you find your way around a long recording without seeing
a waveform, so Quill Converter treats them as part of the content. This chapter
covers where they come from, writing your own, where they end up, editing them
in the Chapter Workbench, and joining and splitting files by chapter.

### Where chapters come from

Chapter marks are how you find your way around a long recording without seeing
a waveform, so Quill Converter treats them as part of the content. The
**Chapter marks** choice (Alt+K) says where the converted files' chapters come from:

- **Keep each file's own chapters** -- the default. Chapters already in the
  file are carried across as they are.
- **Use the chapter list beside each file (.cue, .chapters.txt, Audacity
  labels, .chapters.json)** -- chapters you wrote yourself. See below.
- **Find chapters at the pauses** -- a chapter starts at every pause of two
  seconds or more, and no chapter is shorter than 20 seconds.
- **A chapter every 5 minutes**, and every **10**, **15**, **30** or **60
  minutes** -- evenly spaced chapters titled Part 1, Part 2 and so on, for a
  lecture or a ten-hour recording. A last piece under a minute joins the one
  before it.
- **Remove all chapters** -- the converted files have none.

To see whether a file already has chapters, highlight it and press Alt+Enter
(File Properties).

#### Writing your own chapters

You can define chapters for any file, in any format, with a text file. Put it
beside the source with the same name and `.chapters.txt` on the end: for
`Lecture 3.mp3`, that is `Lecture 3.chapters.txt`. One chapter per line, the
time first:

```
0:00 Welcome
1:30 Questions
1:02:05 Summary
```

Times are minutes and seconds, or hours, minutes and seconds (h:mm:ss). Then
choose **Use the chapter list beside each file** and convert.

Quill Converter also accepts, beside the file and with the same name:

- `name.cue` -- a CUE sheet.
- `name.chapters.json` -- Podcasting 2.0 chapters.
- `name.labels.txt` -- labels exported from Audacity.
- `name.txt` -- if it reads as a chapter list. A transcript or other text is
  ignored.

A file with no chapter list beside it keeps its own chapters.

#### Where chapters land

- **Inside the file**, written by FFmpeg: MP3 (ID3 CHAP and CTOC frames), M4B,
  M4A, Apple Lossless, M4R, MP4, MOV, MKV, MKA, WebM, WebM audio, Opus, and
  WMA and WMV.
- **As chapter comments** (CHAPTER001, CHAPTER001NAME and so on, the
  convention their players read): Ogg Vorbis, FLAC, Speex and Ogg video.
- **In a .cue sheet beside the file**: every other format -- WAV, AIFF,
  WavPack, AC-3, the AAC stream, MP2 and the rest -- has no place for chapters
  inside the file, so a `.cue` sheet with the same name is written next to the
  converted file.

Nothing is silently lost: where a format cannot hold chapters inside the file,
look beside the converted file for its `.cue` sheet.

#### Chapter Workbench

**Queue > Chapter Workbench...** (Ctrl+H, or the **Chapter Workbench...**
button) opens the highlighted MP3, M4B or M4A in the Chapter Workbench,
the same one QUILL's Audio Studio uses. It has a player, so you can hear the
book and work at the playhead:

- rename a chapter, split one at the playhead, set a chapter's start to the
  playhead, and merge chapters;
- find chapters at silences;
- import and export chapter lists: Audacity labels, CUE, timestamps,
  Podcasting 2.0 JSON and CSV;
- edit the book's details -- book title, author, narrator, genre and year --
  and, with **All tags...**, every other tag and the cover art in the Tag
  Editor (see [Editing tags](#editing-tags));
- save: an MP3 is saved in place, with only its tags rewritten; an M4B or M4A
  whose tags alone changed is also saved in place, while changed chapters in
  one are saved as a new file (Save As), losslessly;
- split the book into one file per chapter.

The player is libmpv, bundled with both downloads, so it seeks exactly in every
format.

For any other format, the Workbench explains the other routes: write a chapter
list beside the file and choose it in Chapter marks, or convert the file to M4B or
MP3 first and open that.

Preview and Hear Original ignore chapters; they play fifteen seconds of sound.

### Join into One File

**Convert > Join into One File...** (Ctrl+J) joins every file in the queue, in
queue order, into one sound file. A folder in the queue contributes its files in
name order.

1. Put the files in order. Alt+Up and Alt+Down move the highlighted file.
2. Choose a sound format, preset and effects as usual.
3. Press Ctrl+J and choose where to save the joined file.

The joined file gets one chapter per source. Each chapter is named from the
source's title tag, or from a tidied file name when it has none: "01 - Intro"
becomes "Intro". The chapters go wherever the format keeps them (see [Where
chapters land](#where-chapters-land)): inside the file for MP3, M4B, M4A, Apple
Lossless, MKA, M4R, Opus and the other formats that hold chapters; as chapter
comments for Ogg Vorbis, FLAC and Speex; and in a `.cue` sheet beside the file
for the rest. Files with different sample rates or channel counts join cleanly.

Join needs at least two files and a sound format; a video format is refused with
a reason.

### Split by Chapters

**Convert > Split by Chapters** (Ctrl+Shift+S) makes one file per chapter from
every queued file that has chapters: an audiobook, a podcast episode, a film.

Split uses the same **Chapter marks** choice as Convert, so it can cut where the
file has no chapters of its own:

- **Keep each file's own chapters** and Split cuts at the chapters already in
  the file.
- **A chapter every 30 minutes** and Split cuts a ten-hour recording into
  30-minute files.
- **Find chapters at the pauses** and Split cuts at the pauses.
- **Use the chapter list beside each file** and Split cuts exactly where your
  list says.
- **Remove all chapters** is about what a converted copy keeps, so Split uses
  each file's own chapters instead, and the summary says so.

The pieces go into a folder named after the source, inside the output folder.
Each file is named with its number and chapter title, for example "01 - Chapter
title", and tagged with that title and its track number. The chosen format,
preset and effects apply to every piece. Files without chapters are named in
the summary and left alone.

### What you learned, and where to go next

You can keep a file's chapters, write your own in a plain text file, find them
at the pauses, or have one every few minutes. You know where they land in each
format, and that nothing is silently lost. Join (Ctrl+J) makes many files one
book, and Split (Ctrl+Shift+S) makes one book many files. Chapter 5 is about
the queue.

## Chapter 5: Working with the queue

The queue is the list of files waiting to be converted. This chapter covers
filling it and ordering it, editing tags, what happens during and after a
conversion, and the Advanced Options for when a preset is not quite right.

### Managing the queue

- **Add files:** Alt+A, or File > Add Files... (Ctrl+O).
- **Add a folder:** Alt+O, or File > Add Folder... (Ctrl+Shift+O). A folder is
  scanned right through its sub-folders, and the output reproduces its folder
  layout. To take only the top level, clear **Look in subfolders too** in
  Advanced Options.
- **Paste files** copied in File Explorer: Ctrl+V. In a text box, such as the
  Output folder, Ctrl+V pastes text as usual.
- **Drag and drop** files or folders onto the list.
- **Reorder:** Alt+Up and Alt+Down move the highlighted row.
- **Remove:** Delete in the list, the Remove button (Alt+R), or Queue > Remove
  from Queue (Ctrl+Delete). Nothing is deleted from disk.
- **Clear the queue:** Queue > Clear Queue (Ctrl+Shift+Delete).
- **File Properties:** Alt+Enter describes the highlighted file: its length,
  size, container, overall bit rate, tags, each video, audio and subtitle track,
  whether it has cover art, and its chapters.

Adding the same file twice queues it once. A file that is not a media file is
left out, and the announcement says how many were.

### Editing tags

**Queue > Edit Tags...** (Ctrl+T) opens the Tag Editor on the highlighted file:
the same editor Audio Studio uses, built into Quill Converter so nothing else
needs installing. Its 26 fields and the cover art are spread over five pages:

- **Main** -- title, subtitle, artist, album, album artist, track and disc
  (each a number of a total), genre and year.
- **Details** -- original release date, comment, lyrics or transcript,
  grouping, language, beats per minute, and a Part of a compilation check box.
- **Publishing** -- composer, conductor, publisher, copyright, encoded by and
  ISRC.
- **Sort order** -- sort title, sort artist, sort album and sort album artist.
- **Cover art** -- what the current cover is, with **Load image...** (a JPEG
  or PNG, up to 8 MB), **Save image as...** and **Remove image**.

Control+Tab moves to the next page and Control+Shift+Tab to the previous one;
Tab moves between the fields.

Press OK and the tags are written into the file; the sound itself is not
touched, and chapter marks are kept. Cancel changes nothing.

The Tag Editor works on MP3, M4A, M4B and MP4 files. For another format, such
as FLAC or WAV, Quill Converter says so rather than risk damaging it: convert it
to one of those four first -- its tags come along -- and edit the converted copy.
Tags also travel through every conversion by themselves, and the Chapter
Workbench has the five fields an audiobook needs in its Book details, with an
**All tags...** button that opens this same editor.

### During and after a conversion

- **Stop:** Ctrl+Enter or the Stop Converting button. Stop is immediate: the file
  being converted stops too, and its unfinished output is removed, so nothing
  half-written is left in the output folder. Files already finished are kept,
  and the Conversion Report lists the stopped ones as skipped. A Join stops
  the same way, part way through a file, and saves nothing.
- **Progress** is counted inside each file, not only by files finished: a single
  two-hour audiobook moves from 0 to 100 like a queue of fifty songs does. It is
  announced at 25, 50 and 75 percent, and the status bar and the tray icon's
  tooltip update about once a second -- "Converting Book.m4b: 42 percent, about 3
  minutes left", or "Converted 3 of 10, 47 percent overall" for a queue -- so a
  conversion running in the tray is still something you can check on. The time
  left appears once there is enough to estimate from. The **Progress** bar under
  the buttons moves with it.
- **Conversion Report** (Ctrl+R) lists every file: converted (with its new
  name, and a note when there is one -- where its chapters went, or that
  subtitles a container cannot hold were left out), skipped, or failed with the
  reason. It also says what settings were
  used, where the files went and how long it took. **Copy All** puts the whole
  report on the clipboard, ready to paste into an email.
- **Open Output Folder** (Ctrl+Shift+F) opens the folder in File Explorer.
- **Open Output Folder When Done** (Ctrl+Shift+W) is a check item on the Convert
  menu: when checked, the output folder opens by itself when a conversion
  finishes.
- **Cover art** is carried into the converted copy where FFmpeg would drop it:
  MP3, M4A, M4B, M4R, FLAC, Ogg, Opus and Speex. Text tags such as title,
  artist and album are normally kept as well.

#### Why a file failed

A failure is explained in plain words first, then FFmpeg's own last line, which
support may ask for. The explanations are:

- The file has no track of the kind this format needs -- for example, a sound
  file cannot become a video.
- The file could not be found; it may have been moved, renamed or deleted.
- The file is damaged, or is not really the kind of file its name says.
- Windows refused access to the file or the output folder.
- The output drive is full.
- That combination of tracks cannot be copied into this container; choose a
  preset that converts rather than copies.
- The chosen format could not accept this file's sound or picture settings.
- The file is copy-protected and cannot be converted.
- This file uses a codec the bundled FFmpeg cannot read.
- The file has no sound track to convert -- for example, a video with no audio.

### Advanced Options

**View > Advanced Options** (Ctrl+Alt+V) is a check item that shows or hides an
**Advanced** section in the main window, just above the Convert button. Showing
it moves focus to its first control, and Quill Converter remembers whether it
is shown. Its settings shape the same Convert as everything else on the page.

Every setting starts on its neutral choice -- use the preset, or keep the
file's own -- so showing the section to look around changes nothing.

- **Bit rate (size and quality)** (Alt+Z) -- 96 to 320 kbps for compressed formats.
  Lossless formats ignore it.
- **Sample rate** (Alt+M) -- resample every file to this rate. A format that
  cannot take it gets the nearest rate it can.
- **Channels** (Alt+N) -- mono or stereo. Mono halves the size of speech.
- **Bit depth** -- 16, 24 or 32-bit float for WAV, AIFF, FLAC and the
  other lossless formats. Compressed formats ignore it.
- **If a file already exists** (Alt+X) -- number the new one (the default,
  which never destroys anything), skip it, or replace it.
- **Broadcast polish** (Alt+I) -- runs each converted file through the OptiLab
  Core engine: Podcast Leveler for speech, Stream Polish for music, Smooth
  Limiter for peaks. Off by default, and unavailable when the build does not
  include it.
- **Look in subfolders too** -- a check box, on by default. When a
  folder is in the queue, its subfolders are converted too, and the same folder
  layout is rebuilt in the output folder.

### What you learned, and where to go next

You can add, reorder and remove files, see what is inside one with
Alt+Enter, and edit its tags with Ctrl+T. Ctrl+Enter stops a conversion as
well as starting it, and the Conversion Report (Ctrl+R) says what happened to
every file and why. Chapter 6 is about converting from a link.

## Chapter 6: Converting from a link

Quill Converter can download the sound of a video from YouTube and many other
sites, and of a whole playlist or channel, and put it straight into the queue.

### Convert from URL

**From URL...** (Alt+L, or File > Convert from URL..., Ctrl+U) takes a web
address -- YouTube and many other sites -- and downloads its audio. Quill
Converter first reads the link, without downloading anything, to find out what
it is:

- **One video.** Its audio downloads, with progress in the status bar, and
  joins the queue.
- **A playlist.** The **Download a Playlist or Channel** window says how many
  videos it has and asks **How many**: all of it, or the first 10, 25 or 100.
  A link to one video inside a playlist (a YouTube address with both `v=` and
  `list=`) also asks **What to download**: only that video, or the whole
  playlist.
- **A YouTube channel.** The same window asks which **Section** -- Videos,
  Shorts or Live streams; only the ones the channel has are listed -- **How
  many** of the newest (10, 25, 100, or all of it, which can be thousands),
  and **Published**: any date, or only the past week, month or year.

Either way, **Skip videos already downloaded from here** is checked: Quill
Converter remembers what it has fetched from each playlist and channel, so
pasting the same link next week downloads only what is new. Clear it to fetch
everything again.

A playlist or channel downloads as one job, exactly like a conversion: the
progress bar, the status bar ("Downloading 7 of 42: the video's title") and
25, 50 and 75 percent spoken; Ctrl+Enter or Stop Converting stops it at once;
and every video that downloaded joins the queue, in order. A playlist's files
are numbered in playlist order ("001 - ..."), a channel's are named by date,
and all of them are tagged with the playlist or channel as the **album** and a
**track number**, so they play in order in any player -- and **Join into One
File** (Ctrl+J) turns a lecture series into one audiobook with a chapter per
video. A video that cannot be downloaded (private, removed, or blocked where
you are) does not stop the rest; the summary counts them and **Conversion
Report** (Ctrl+R) lists each with the site's reason. Long runs pause a few
seconds between videos, so the site does not block your computer.

The downloads are kept in a temporary folder, so when the Output folder is
empty the converted copies go to `Converted` inside your Downloads folder -- a
playlist or channel into its own folder there, named after it.

The downloader, yt-dlp, and the JavaScript runtime it needs for YouTube, deno,
are both included, so nothing is installed. Only download content you have the
right to use; no account or password of yours is sent to the site. Anything
that is not a full `http://` or `https://` address is refused with a plain
explanation. Convert from URL is unavailable in Safe Mode.

### What you learned, and where to go next

Paste a link into Convert from URL (Ctrl+U). One video downloads at once; a
playlist or channel asks how much you want first, and pasting the same link
later fetches only what is new. Chapter 7 is about keeping Quill Converter out
of the way while it works.

## Chapter 7: Out of the way, and easy to find

A long conversion can run in the notification area while you do something else.
This chapter covers the tray, choosing a key to show and hide Quill Converter
from anywhere, and finding any command when you cannot remember which menu it
is in.

### The tray

- **Minimize to Tray** (File > Minimize to Tray, Ctrl+W) hides the window to the
  notification area; the same command brings it back. A conversion keeps
  running.
- **File > Show and Hide Key...** (Ctrl+Alt+Shift+H) lets you choose one key
  that shows or hides Quill Converter from anywhere in Windows. There is no key
  until you choose one. Type the key you want, or leave the box empty for none.
  If another QuillVille app already uses it, Quill Converter tells you whose it
  is and lets you try another. If you tried a test copy before 1.0.0,
  Ctrl+Alt+Shift+C did this; other QuillVille apps use that key for menu
  commands, so it is off now, and Quill Converter tells you so once.
- The tray icon's menu has Show and Exit.
- **Exit** (File > Exit, Ctrl+Q) really exits. Alt+F4 closes the window.

### Finding a setting or a command

Quill Converter keeps its options in its menus, so there is no settings window to search.
Instead, **Help > Find a Setting or Command** (**Ctrl+Alt+Shift+S**) searches
every menu at once.

1. Press **Ctrl+Alt+Shift+S**.
2. Type part of what you are looking for, such as "tags". The list
   below narrows as you type, and each row says which menu the command is in.
   An option also says whether it is on or off.
3. Press **Down** to move into the list, and **Enter** on the one you want.

Enter does exactly what choosing that row from its menu would do. For an
option, it switches it and tells you whether it is now on or off. Escape
closes the window without doing anything.

### What you learned, and where to go next

Ctrl+W tucks Quill Converter into the tray and brings it back. If you want one
key that works from any program, choose it in File > Show and Hide Key...
(Ctrl+Alt+Shift+H). Ctrl+Alt+Shift+S finds any command by name. Chapter 8 is
for when something goes wrong.

## Chapter 8: When you need a hand

Everybody gets stuck sometimes. This chapter covers the help that is always one
key away, what to do when something does not work, where your settings live,
updates, and how to reach a person.

### Help where you are

Press **F1** on any control to hear what the window is for and what that
control does. Help > User Guide (Ctrl+F1) opens this guide, and Help >
Keyboard Shortcuts... (Ctrl+Alt+K) lists every key in a window you can arrow
through.

### Troubleshooting

- **Quill Converter does not open.** It never fails silently: if the app's
  engine cannot start, a plain message opens that your screen reader reads on
  its own. It says "Quill Converter did not start", gives the reason in words,
  names the launch log that holds the details, and gives the support address.
  If it says the zip was opened from inside, extract the whole zip first
  (Applications key on the zip, then **Extract All...**) and open
  `QuillConverter.exe` from the extracted folder. If it names a missing file
  or DLL, extract the zip again into an empty folder and check your antivirus
  quarantine. If it says "Python reported", send the launch log to support:
  `data\logs\launch.log` beside a portable copy, or
  `%APPDATA%\Quill\logs\QuillConverter-launch.log` for an installed one. If
  nothing at all happens and there is no message, a Quill Converter is
  probably already running; check the notification area and Task Manager.
- **"Quill Converter cannot find FFmpeg."** FFmpeg is installed with the app,
  so this means it was removed or damaged. Help > Get FFmpeg... (Ctrl+Alt+F)
  puts it back.
- **Only a few formats are listed.** The list shows what the FFmpeg in use can
  write. The same fix applies: Get FFmpeg.
- **Sound files were skipped.** The format is a video format, and a sound file
  has no picture. Choose a sound format for them.
- **"Change the container only" failed.** That picture and sound cannot be
  copied into that container as they are. Choose Same quality instead, which
  converts rather than copies.
- **A video is taking a long time.** On a computer whose graphics chip has no
  video encoder, H.264 runs at about the speed of playback and H.265 slower;
  WebM (VP9) is slow everywhere. MP4 H.264 is the fastest choice. The status
  bar and tray tooltip say how far the file has got and about how long is
  left.
- **A file failed as copy-protected.** Files with DRM, such as purchased
  Audible books or protected iTunes purchases, cannot be converted.
- **Preview is silent.** Preview plays through the Windows default sound device.
  Check that it is the one you are listening on.

### Settings and Safe Mode

Your choices are kept in `converter.json` in the app's data folder: the shared
QuillVille data folder for the installed app, or the `data` folder beside the
program for the portable copy. Uninstalling never deletes the shared data
folder; another app in the family may still be using it.

Starting with the environment variable `QUILL_SAFE_MODE=1` runs Quill Converter
in Safe Mode. Everything local still works; Convert from URL is refused.

### Your version and updates

**Help > About Quill Converter** (Alt+F1) shows your version with a build
number, such as 1.0.0 (build 1). The build number tells you which build of a
version you have: when a fix comes out without a new version number, it is a
newer build.

**Help > Check for Updates...** (Ctrl+Alt+U) asks whether a newer Quill
Converter is out. If one is, it shows you what changed and offers to download
it, with progress spoken as it goes. It only checks when you ask, and it offers
the same kind of download you have: the installer if you installed, or the
portable zip if you unpacked one.

### Getting help

Support is run by **Community Access**, and the address is
**support@community-access.org**. A person reads it, and replies come back by
email.

The quickest way there is **Help > Get Help from Support...** (Ctrl+Alt+F2).
It asks what kind of message this is, a subject, what happened, and -- if you
want an answer somewhere other than the address you send from -- an email
address. What you expected and how to reproduce it are optional, and worth more
than anything else when you can give them.

Press Send and your **own mail program opens with the whole message already
written**, addressed to support, with Quill Converter's name and version and
your Windows version filled in at the bottom. Nothing is sent until you send it
there, so you can read it over, add anything, or change your mind.

If this computer has no mail program set up -- webmail only, say -- the app puts
the whole message on your clipboard and tells you the address, so nothing you
typed is lost. Writing to **support@community-access.org** yourself always
works just as well. Say which app you were using and what happened. If a
conversion failed, open the Conversion Report (Ctrl+R), press Copy All, and
paste it into your message.

### What you learned, and where to go next

F1 explains wherever you are, Troubleshooting covers the common problems, and
Help > Get Help from Support... (Ctrl+Alt+F2) writes to a person. The keyboard
reference below lists every key, so it is a good page to come back to.

## Keyboard reference

The same list is in the app: Help > Keyboard Shortcuts... (Ctrl+Alt+K) shows
every key in a read-only window you can arrow through.

### File menu

| Command | Key |
| --- | --- |
| Add Files... | Ctrl+O |
| Add Folder... | Ctrl+Shift+O |
| Paste Files | Ctrl+V |
| Convert from URL... | Ctrl+U |
| Open Output Folder | Ctrl+Shift+F |
| Minimize to Tray | Ctrl+W |
| Show and Hide Key... | Ctrl+Alt+Shift+H |
| Exit | Ctrl+Q |

### Queue menu

| Command | Key |
| --- | --- |
| File Properties... | Alt+Enter |
| Chapter Workbench... | Ctrl+H |
| Edit Tags... | Ctrl+T |
| Remove from Queue | Ctrl+Delete |
| Clear Queue | Ctrl+Shift+Delete |
| Move Up | Alt+Up |
| Move Down | Alt+Down |

### View menu

| Command | Key |
| --- | --- |
| Advanced Options (show or hide) | Ctrl+Alt+V |

### Convert menu

| Command | Key |
| --- | --- |
| Convert Now (Stop while running) | Ctrl+Enter |
| Preview with Your Settings | Ctrl+P |
| Preview Original | Ctrl+Shift+P |
| Custom Effects... | Ctrl+E |
| Join into One File... | Ctrl+J |
| Split by Chapters | Ctrl+Shift+S |
| Conversion Report... | Ctrl+R |
| Open Output Folder When Done | Ctrl+Shift+W |

### Help menu

| Command | Key |
| --- | --- |
| Help for This Window | F1 |
| Find a Setting or Command... | Ctrl+Alt+Shift+S |
| User Guide | Ctrl+F1 |
| Release Notes | Shift+F1 |
| Changelog | Ctrl+Shift+F1 |
| Product Requirements | Alt+Shift+F1 |
| Keyboard Shortcuts... | Ctrl+Alt+K |
| Get Help from Support... | Ctrl+Alt+F2 |
| Get FFmpeg... | Ctrl+Alt+F |
| Check for Updates... | Ctrl+Alt+U |
| About Quill Converter | Alt+F1 |

### Anywhere

| Action | Key |
| --- | --- |
| Show or hide Quill Converter | The key you chose (none at first) |
| Remove the highlighted queue row | Delete |
| Next window, previous window | Ctrl+Tab, Ctrl+Shift+Tab |
| Go to window 1 to 9 | Ctrl+1 to Ctrl+9 |

The **QuillVille** menu (Alt+U) opens the other released apps in the family --
QUILL, Quill Radio, Quill Weather and Quill Inkwell. Each item has an access
letter, so Alt+U and then Q, R, W or I opens that app with nothing held down,
and each shows its key, which you can see in Keyboard Shortcuts.
The **Window** menu lists the open windows.
