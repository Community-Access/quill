# Quill Converter 1.0 -- Release Notes

Somewhere between "I recorded this in the wrong format" and "this download is an
M4A and my player wants MP3," almost everybody hits the wall of audio
conversion. The usual answer is a sketchy website that wants you to upload your
file, sit through an advertisement, and trust a stranger with your recording.

Quill Converter is a real one, and it runs entirely on your own machine.

## What it is

A small window with one job. A list of the files you want changed, a box for
what you want them changed into, a preset if you want the decisions made for
you, and a Convert button. That is the whole app.

Open it and your cursor is already in the file list -- not floating in an empty
window, not somewhere you have to go hunting for. Add a file, pick a format,
press Convert. Every step is spoken, and the run ends by telling you what
happened, including the name of anything that did not work. No conversion ever
finishes by quietly claiming success.

## Nothing leaves your computer

There is no upload. There is no account. There is no "processing on our
servers." Your audio is converted by the FFmpeg that ships inside the app, on
your own disk, and it works with the network unplugged.

The one feature that does reach the internet -- **Convert from URL**, which
pulls the audio out of a web link -- is honest about it. The component that does
the downloading is not bundled. The first time you use it, the app asks you
once, in plain language: here is what this does, here is what it will install,
about how big it is, where it comes from, and please only download things you
have the right to use. Say no and nothing is installed. It stays off entirely in
Safe Mode.

## What it converts

Almost anything you are likely to have. MP3, WAV, FLAC, OGG, Opus, M4A, M4B,
AAC, WMA, AIFF, ALAC, and more -- and it will happily pull the audio track out
of a video file (MP4, MKV, MOV, WebM, AVI, and the rest) on the way past.

Coming out, you can have MP3, M4A, M4B, Opus, OGG, FLAC, WAV, AAC, AIFF, ALAC,
WMA, or CAF. The list is not decoration: when the app starts, it asks FFmpeg
what it can genuinely encode and only offers those. That is a deliberate
kindness. Nothing is worse than starting a hundred-file batch and finding out
half way through that the encoder was never there.

## Presets, for when you would rather not think about bitrates

Pick one and go:

- **Just convert** -- change the format, change nothing else. This is the
  default, and it is the right answer surprisingly often.
- **Podcast** -- mono MP3 for talk, with the low rumble taken out.
- **Audiobook** -- a compact mono M4B.
- **Voice memo** -- tiny files for spoken notes.
- **Web voice** -- the smallest thing that still sounds like a person.
- **Archival** -- lossless FLAC, keeping your original rate and channels.
- **Hearing-aid mono** -- everything downmixed to one channel.
- Plus straightforward MP3 at 320, 192, and 128 kbps.

Each one reads out with a sentence explaining what it is for, so you can choose
by listening rather than by decoding jargon.

## And Advanced, for when you would

Press **Advanced** and the full studio opens: exact bit rate, sample rate,
channels and bit depth; loudness normalization to an audiobook or a podcast
target; gain; a rumble-removing high-pass; silence trimming; a speed change that
does not make anyone sound like a chipmunk; a compressor; a volume leveler; and
fades in and out.

Everything in there starts on "leave the preset alone," so opening the panel to
look around cannot accidentally change your output. And when you tick the box to
reveal it, your focus moves into the panel -- so you hear that it opened instead
of wondering whether anything happened.

## Whole folders, safely

Point it at a folder and it works right through it, sub-folders and all, and
rebuilds the same folder structure on the way out. It converts several files at
once so a big batch is not an afternoon, and the window stays responsive
throughout.

It will not overwrite your originals. If a file of that name already exists, the
new one is numbered instead. If you actually want Skip or Overwrite, they are
there in Advanced -- but you have to ask.

## It gets out of the way

Press Ctrl+W and it tucks into the notification area and keeps working. Press
Ctrl+Alt+Shift+C from anywhere in Windows and it comes back. While a batch runs,
the tray tooltip carries the same progress the status bar does, so a minimized
conversion is still something you can check on.

And it is one keystroke from the rest of the family: the QuillVille menu opens
QUILL, Quill Radio, or Quill Weather without hunting through the Start Menu.

## Five doors, one converter

You will meet the same converter wherever you happen to be:

- **Quill Converter**, this app.
- **Audio Studio > Voices > Convert Audio...**, inside QUILL.
- **Right-click a file in Windows Explorer** and choose **Convert with Quill**.
  This one is off until you turn it on, so nothing appears in your context menu
  uninvited.
- **Convert from URL**, for a link.
- **`quill convert`** on the command line, with a dry-run planner, for scripts
  and for people who like it that way.

They are not five copies. They are five doors onto one engine, so a thing fixed
in one place is fixed in all of them.

## Built for a screen reader from the first line

Not retrofitted. Focus starts where you need it. Every control has a name your
screen reader can read. Every action says what it did -- through speech and
through your braille display -- and writes the same words to the status bar, so
nothing is spoken-only and nothing is colour-only. Every dialog has a real
Cancel that Escape reaches. There is no drag and drop to be locked out of,
because there is nothing that only a mouse can do.

## Your settings, where you want them

Quill Converter shares one settings store with QUILL and the rest of the family,
so what you set once holds everywhere. Running the portable build from a stick?
Everything lives in the `data` folder beside the program and travels with you,
leaving the machine you plugged into exactly as you found it. And uninstalling
Quill Converter never touches that shared folder -- another app in the family
may still be living there.
