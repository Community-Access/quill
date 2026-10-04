# Tutorial 4: From document to published audiobook, with voices, Read Aloud and the Audio Studio

**Goal:** hear your document in the voice you want. Then use the Audio Studio
to turn a folder of documents into an audiobook with chapters, or join a
folder of recordings into one book, fix its chapters by ear, and publish it.
Last, make a DAISY book for accessible book players.

You can do all of this from the keyboard, QUILL tells you what is happening at
each step, and nothing changes until you have checked it.

## 1. Pick a voice

**Tools > Speech > Speech and Dictation...** opens the speech settings. You
can choose from old and new voices:

- **SAPI 5**: the Windows voices you already have. Nothing to download.
- **eSpeak NG** and **DECtalk**: the classic voices, which you can download
  when you want them (yes, Perfect Paul is there).
- **Kokoro**: natural-sounding voices that run on your own computer (about a
  114 MB download, once; no account needed). The QUILL Cast podcast is
  narrated by two of these.
- **ElevenLabs** (optional): a paid online voice, if you have an account.
  QUILL asks you before it sends anything.
- **Read in Browser** (experimental, Settings > Experimental): reads your
  document in a web page using your browser's voices, including Edge's online
  natural voices. QUILL tells you when a voice works online, because then your
  text is sent to the company that makes the voice.

Every download shows its progress and is checked to make sure it arrived
safely.

## 2. Read aloud

Select text (or just place the caret) and use **Tools > Reading & Dictation >
Read Aloud**. Press a key to stop. Try the same paragraph with two or three
voices and keep the one you like best.

To fine-tune how a passage is read, the **SSML Builder** lets you add
emphasis, pauses and changes in pitch and speed using ordinary controls,
without typing any tags. It works with SAPI 5 and eSpeak NG.

To make a quick audio file, open the palette and choose `Generate Speech
Audio`. It turns the current document into audio in the background. WAV always
works; with the **ffmpeg** helper installed (Help > Download Optional
Components), you also get **MP3, M4A, M4B, OGG, Opus, FLAC**.

## 3. Open the Audio Studio and choose what to do

For anything bigger than one file, **Tools > Speech > Audio Studio...** is the
place to go (it is also in the command palette, and on `Ctrl+Shift+Grave, Y`).
The first page asks what you want to do:

- **Narrate documents**: QUILL reads your files aloud into audio.
- **Combine audio files**: you have already recorded, and QUILL builds the
  book.
- **Edit an existing audiobook**: open an MP3 or M4B that has chapters and
  change them.

The wizard remembers what you chose last time and starts there. Every page is
announced ("Step 2 of 7: What should I read?"), **Back** and **Next** move
between steps, and **Skip to summary** jumps to the end when a saved project
already fills in every page, so doing it again takes three keystrokes.

## 4. Narrate documents

Point **What should I read?** at a folder of documents (Word, Markdown, HTML,
text). You can choose which files to include and whether to look in
subfolders. **Count documents** tells you how many it found.

On **Who should read it?**:

- Pick the engine and voice, and use **Preview voice** to hear it first.
- **Round-robin voices** takes turns through a list of voices you choose:
  article 1 gets voice 1, article 2 gets voice 2, and so on.
- **Voice casting** goes further: add a rule like `*interview* =` your guest
  voice, or `#1 =` your narrator, and every matching chapter is read by that
  voice. First matching rule wins; everything else takes turns as above. This
  is handy for fiction with a lot of dialogue.

On the output step, two boxes are worth knowing about:

- **Audition** converts only the first document, so you can check the voice
  and pace in a few minutes before a long run.
- **Reuse unchanged audio from the last run** (on by default) saves you time.
  If you edit one chapter and run it again, only that chapter is read again;
  the rest say "Reused ... (unchanged since last run)". You can draft with a
  fast voice, then switch to your favourite voice for the final version and
  everything is rebuilt for you.

On the book page, type a half-remembered title and press **Look up book
details**. QUILL looks it up in Open Library and MusicBrainz (free, and QUILL
asks before it goes online the first time), fills in the author, genre and
year from the match you pick, and offers to download the cover as `cover.jpg`.
Tick the spoken credits if you want the book to introduce itself.

Read the summary. If you like, choose **Save a job file** to keep all your
choices in a `.quilljob` file you can load next time (or edit in Notepad).
Then press **Start**. QUILL tells you how it is going, file by file. You can
cancel at any time, or tuck the progress into the status bar.

## 5. Combine a folder of recordings

Recorded a memoir chapter per session? Choose **Combine audio files** and
point it at the folder. Each file becomes a chapter named after the file, and
you always get to check the chapter list before they are joined. You can
rename, reorder or remove chapters, or bring in titles from a CSV file or
Audacity labels. You get an M4B or MP3 with chapters, and you can also trim
silence, add fades, change the speed, or match the ACX loudness rules.

Two extras for bigger jobs: **Library mode** builds every subfolder as its own
audiobook, named after its folder, without you having to watch; and the
**watch action** ("Build audiobook from the folder") rebuilds a watched
folder's master automatically whenever new recordings land.

## 6. The Chapter Workbench

Open any MP3 or M4B with chapters. A long recording with no chapters opens as
one big chapter, ready for you to split up.

It has a built-in player: Play and Pause, Previous and Next chapter, Rewind
and Forward, a position slider that reads out the time in plain words, a speed
control that does not change the pitch, and **Where am I?** to hear where you
are. The player remembers where you stopped in every book. (Want gapless audio
and exact seeking? Download the **mpv player engine** from **Help > Download
Optional Components** and QUILL uses it automatically. Without it, QUILL uses
its built-in player.)

To fix chapters by ear:

1. Play until you hear where a boundary belongs.
2. Choose **Split at playhead** to start a new chapter there.
3. **Set start to playhead** retimes an existing boundary; **Merge into
   previous** joins a chapter to the one before it, and **Restore original**
   undoes your changes.

Two helpers make suggestions, and you decide whether to keep them. **Propose
chapters from silences...** listens for pauses and suggests where chapters
could start. **Propose AI titles...** writes out the first minute of each
chapter *on your own computer*, sends only that text to the AI you have set
up, and suggests a short title for each chapter. You can keep, rename, or
choose **Restore original**. **Check against ACX** tells you in plain words
whether the loudness meets Audible's rules.

An MP3 is saved **in place**: only the chapter information changes, not the
sound. An M4B is saved as a new file, with no loss of quality.

The Workbench player also has a **Mute** button. The separate **Audio Studio**
app goes further: your media keys work, each book remembers its own volume,
there is a sleep timer, and the next book starts by itself when one finishes.
Your library there is a tree (Favorites, In Progress, Recently Played, Inbox,
plus your own folders), and it can pick up the last book where you left off.

## 7. Publish it

The Workbench's **Publish...** button gives you these choices, and nothing is
sent anywhere until you say so:

- **Podcast feed**: writes a podcast feed file (`.rss`) next to the book,
  without going online, with chapters that podcast apps can read.
- **Folder feed (all episodes)**: run a whole show from one folder. Each
  finished file becomes an episode with its own description, date, length and
  chapters. One button rebuilds the feed after each new episode; another
  writes an accessible `show-notes.html` page beside it.
- **SFTP upload**: sends the book and its files to your own web server,
  safely. Your password is kept in Windows Credential Manager. QUILL tells you
  the percent as it goes, and **Cancel** stops it.
- **Auphonic**: makes your audio sound professional, using your own Auphonic
  account. **Check account and load presets** tells you how many credits you
  have and lists your presets. Then QUILL uploads the book, waits, and saves
  the results next to it. Your Auphonic key is stored safely, and you can
  manage it in **AI > AI Hub > Services**.

Build the episode, update the feed, and upload both. You can run your whole
show from QUILL.

## 8. DAISY talking books

**File > Export > DAISY Talking Book** writes a DAISY 2.02 text-only talking
book, the format used by accessible book players and libraries. Your headings
become the way readers move around the book, so make sure your headings are in
good order first (GLOW can check them for you: [tutorial
6](06-make-it-accessible-with-glow.md)).

## 9. Round trip: audio in

It works the other way too. `Ctrl+F9` lets you dictate without going online,
and **transcription** turns a recording into a document on your own computer.
Give a transcript to the **Listening Companion** and it can write meeting
minutes, a to-do list or a summary for you to check. To hear more, QUILL Cast
episode 21 covers Read Aloud and voices, and episode 33 covers the Audio
Studio.

**Next:** [Start an Accessible Vault](05-start-a-vault.md).
