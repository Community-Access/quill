# Tutorial 4: From document to published audiobook — voices, Read Aloud, and the Audio Studio

**Goal:** hear your document in the voice you want, then walk the Audio
Studio's three journeys: narrate a folder of documents into a chaptered
audiobook, combine a folder of recordings into one book, fix its chapters
by ear, and publish the result — plus DAISY for accessible book players.

Everything here is keyboard-first and announced; a screen reader narrates
every step, and nothing is applied without your review.

## 1. Pick a voice

**Tools > Speech > Speech and Dictation...** opens the speech hub. QUILL's
voice lineup spans eras:

- **SAPI 5** — the Windows voices you already have; zero downloads.
- **eSpeak NG** and **DECtalk** — the classics, downloadable on demand
  (yes, Perfect Paul).
- **Kokoro** — modern neural voices that run entirely on your machine
  (about a 114 MB one-time download; no cloud, no account). The QUILL Cast
  podcast is narrated by two of these.
- **ElevenLabs** (optional) — a premium cloud voice if you have an account;
  every use is per-session consented.
- **Read in Browser** (experimental, Settings > Experimental) — an
  accessible reader page using your browser's voice catalog, including
  Edge's online natural voices. QUILL states plainly that online browser
  voices synthesize in the vendor's cloud.

Every download is checksum-verified with visible progress.

## 2. Read aloud

Select text (or just place the caret) and use **Tools > Reading & Dictation >
Read Aloud**. Stop on a key. Try the same paragraph in two or three engines —
voices are a taste, and QUILL does not judge.

For fine control of a passage, the **SSML Builder** composes emphasis,
pauses, and prosody from accessible controls — no hand-written tags — and
plays natively on SAPI 5 and eSpeak NG.

For a quick one-shot file, Palette > `Generate Speech Audio` renders the
current document to audio in the background. WAV always works; with the
**ffmpeg** helper installed (Help > Download Optional Components), you also
get **MP3, M4A, M4B, OGG, Opus, FLAC**.

## 3. Open the Audio Studio and pick a journey

For anything bigger than one file, **Tools > Speech > Audio Studio...** is
the workshop (also in the command palette, default binding
`Ctrl+Shift+Grave, Y`). The first page asks the only question that matters:

- **Narrate documents** — QUILL reads your files aloud into audio.
- **Combine audio files** — you already recorded; QUILL builds the book.
- **Edit an existing audiobook** — open any chaptered MP3/M4B and reshape it.

The wizard remembers your last journey and pre-selects it. Every page is
announced ("Step 2 of 7: What should I read?"), **Back** and **Next** move
between steps, and **Skip to summary** fast-forwards when a saved project
profile already fills every page — a repeat run is three keystrokes.

## 4. Journey one: narrate documents

Point **What should I read?** at a folder of documents (Word, Markdown,
HTML, text). Filters, subfolders, and a size cap keep discovery honest;
**Count documents** speaks the settled number.

On **Who should read it?**:

- Pick the engine and voice, and **Preview voice** before committing.
- **Round-robin voices** cycles a list you build — article 1 gets voice 1,
  article 2 voice 2, wrapping around.
- **Voice casting** goes further: add a rule like `*interview* =` your
  guest voice, or `#1 =` your narrator, and every matching chapter is read
  by that voice. First matching rule wins; everything else follows the
  rotation. This is how dialogue-heavy fiction gets cast deliberately.

On the output step, two boxes deserve attention:

- **Audition** converts only the first document — judge the voice and pace
  in minutes before an overnight run.
- **Reuse unchanged audio from the last run** (on by default) is the
  authoring loop: QUILL fingerprints each document's text plus every
  audio-shaping setting. Re-run after editing one chapter and the rest
  announce "Reused ... (unchanged since last run)". Only what changed is
  re-synthesized — draft with a fast local voice, then swap in your best
  voice for the money pass and everything rebuilds automatically.

On the book page, type a half-remembered title and press **Look up book
details** — Open Library and MusicBrainz (free, keyless; QUILL asks before
the first contact) fill the author, genre, and year from the match you
pick, and offer to download the jacket as `cover.jpg`. Tick the spoken
credits if you want the book to introduce itself.

Review the plain-sentence summary, optionally **Save a job file** (a
portable `.quilljob` that pins the entire run — load it on the first page
next time, or edit it in Notepad), and press **Start**. Progress is
announced, per-file, cancelable, and minimizable to the status bar.

## 5. Journey two: combine a folder of recordings

Recorded a memoir chapter per session? Point the combine journey at the
folder: each file becomes a chapter titled from its name, and you always
review the chapter list before the merge — rename, reorder, remove,
import titles from a CSV or Audacity labels. Output is a real M4B (native
chapters) or MP3 (chapter markers), with optional silence trimming,
fades, tempo, and ACX loudness.

Two scale-ups when you need them: **Library mode** builds every subfolder
as its own audiobook, unattended, each titled after its folder; and the
**watch action** ("Build audiobook from the folder") rebuilds a watched
folder's master automatically whenever new recordings land.

## 6. Journey three: the Chapter Workbench

Open any chaptered MP3 or M4B — or a chapterless three-hour recording,
which opens as one big chapter, ready to carve.

The built-in player anchors everything: Play/Pause, Previous/Next chapter,
Rewind/Forward, a position slider that speaks human time, a pitch-preserved
speed control, and **Where am I?** for the full audible glance. The player
remembers where you stopped in every book. (Want gapless audio and exact
seeking? Download the **mpv player engine** from **Help > Download Optional
Components** and playback upgrades to libmpv automatically; QUILL falls
back to the built-in engine whenever mpv is absent.)

The surgery, all by ear:

1. Play until you hear where a boundary belongs.
2. **Split at playhead** — the fix-a-bad-chapter move.
3. **Set start to playhead** retimes an existing boundary; **Merge into
   previous** and **Restore original** round it out.

Two analysis helpers propose, never impose: **Propose chapters from
silences...** scans the recording and lands a proposal in the list for
review; **Propose AI titles...** slices each chapter's opening minute,
transcribes it *on your machine* with the local speech model, sends only
that text to your configured AI, and proposes a short title per chapter —
review, rename, or **Restore original**. **Check against ACX** speaks a
plain-words loudness verdict before you submit anywhere.

Saving is honest about physics: an MP3 saves **in place** (tags only, audio
untouched); an M4B saves as a new file via a lossless re-mux.

## 7. Publish it

The Workbench's **Publish...** button offers explicit, consent-first paths:

- **Podcast feed** — a complete `.rss` written next to the book, entirely
  offline, chapters linked for Podcasting 2.0 apps.
- **Folder feed (all episodes)** — run a whole show from one folder: every
  master becomes an episode with its own description (edited in an
  accessible list), true publication date, duration, and chapter link. One
  button regenerates the complete feed after every build; another writes an
  accessible `show-notes.html` beside it.
- **SFTP upload** — the book and its companions go to your server through
  QUILL's own SSH machinery (strict host keys, password in the Windows
  Credential Manager), with spoken percent progress and a real **Cancel**.
- **Auphonic** — professional mastering in your own account: **Check
  account and load presets** speaks your credit balance and fills the
  preset picker, then QUILL uploads, waits, and downloads the results next
  to the book. The token lives in the credential vault, manageable
  centrally in **AI > AI Hub > Services**.

Build the episode, regenerate the feed, upload both — the entire show runs
from QUILL.

## 8. DAISY talking books

**File > Export > DAISY Talking Book** writes a DAISY 2.02 text-only talking
book — the standard for accessible book players and library services. Your
headings become the DAISY navigation structure, so build a clean heading
outline first (GLOW will happily check it: [tutorial 6](06-make-it-accessible-with-glow.md)).

## 9. Round trip: audio in

The same suite works in reverse — `Ctrl+F9` dictates offline via Whisper,
and **transcription** turns a recording into a document privately. Feed a
transcript to the **Listening Companion** and get meeting minutes, action
items, or a summary, reviewably. QUILL Cast episode 24 walks this whole
tutorial by ear.

**Next:** [Start an Accessible Vault](05-start-a-vault.md).
