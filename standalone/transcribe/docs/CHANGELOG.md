# QUILL Transcribe Changelog

All notable changes to QUILL Transcribe are recorded here, newest first. The
release notes (`release-notes-1.0.md`) tell the same story as a narrative; this
file is the itemized list.

## Unreleased

Version 1.0.0 (build 2), released on 1 November 2026: the first public
release. Everything in this section ships in it, on top of the first test
build listed under 1.0.0 below. The changes are grouped by area; each says
where in the user guide to read more.

### Release and the QuillVille family

- **Released on 1 November 2026.** From then QUILL Transcribe is part of every
  public QuillVille build: it is on the QuillVille menu of QUILL, Quill Radio,
  Quill Weather, Quill Converter and Quill Inkwell (Alt+Q, then T; Alt+U, then
  T in Quill Converter), on the tray menus of Quill Radio, Quill Weather and
  Quill Inkwell, and offered for download from them when it is not installed.
  Nothing is downloaded until you say yes. QUILL Transcribe's own QuillVille
  menu opens QUILL, Quill Radio, Quill Weather, Quill Converter and Quill
  Inkwell on Ctrl+Alt+Shift+F7 to F11. User guide: "The other QuillVille
  apps".
- **Dictate Here from Quill Cast and Quill Radio.** Their **Edit > Dictate
  Here** (Ctrl+F11) asks QUILL Transcribe to dictate into the box you are in,
  starting it in the tray if it is not running, and shows in every copy. For
  example, in Quill Radio press Ctrl+F to open Search Stations, then Ctrl+F11,
  and say the station's name. Ctrl+F11 there starts dictation but does not
  stop it; your own start and stop key does. User guide: "Dictate Here from
  Quill Cast and Quill Radio".
- **One microphone across the family.** QUILL, QUILL Lite, QUILL Transcribe and
  Quill Inkwell share one microphone lock, held only while one of them is
  dictating, QUILL's Locked Dictation (Ctrl+F9) included. Your start and stop
  key while an editor dictates names it and the key that stops it: "QUILL Lite
  is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try again."
  Ctrl+F11 in an editor while QUILL Transcribe listens opens no second
  microphone and names your key: "QUILL Transcribe is listening. Press
  Alt+Shift+Backslash to stop it, then try again." Waiting in the tray holds
  nothing, so the editors dictate as usual. User guide: "One microphone: QUILL,
  QUILL Lite and QUILL Transcribe".
- **QUILL Lite's window is refused like QUILL's.** QUILL Transcribe does not
  type into QUILL Lite; it says "This is a QUILL window: press Ctrl+F11 to
  dictate here."

### Starting, stopping and where it types

- **The start and stop key is Alt+Shift+Backslash from the start.** Change it,
  or empty it so the tray menu starts dictation instead, with **File > Start
  and Stop Key...** (Ctrl+Alt+Shift+D; Alt+F, then K). Every key box has
  **Record Key**: press the combination you want and it is written out for
  you; typing the key still works. When Windows says your key is taken, QUILL
  Transcribe now sends you to the File menu, where the row is, rather than the
  Dictation menu. User guide: "Keys".
- **Three more keys you can choose**, each empty until you choose it in the
  File menu: the **Dictation Status Key** (Ctrl+Alt+Shift+A), the **Resume
  Key** (Ctrl+Alt+Shift+U) and the **Discard Held Words Key**
  (Ctrl+Alt+Shift+Y), so you can ask, resume or discard from the program you
  are working in.
- **Hold the key to talk.** With **Hold the dictation key to talk** checked in
  More Dictation Settings (Alt+H, off until you turn it on), hold your start
  and stop key while you speak; letting go stops dictation and keeps your last
  phrase. What you say while the key is down is typed when you let go, so
  nothing reaches the other program while Alt or Ctrl is held. A quick press
  still turns dictation on and off. It is the same setting as QUILL's and
  QUILL Lite's. User guide: "Holding the key to talk".
- **The wake phrase.** With **Listen for the wake phrase while dictation is
  off** checked in Dictation Settings (off until you turn it on), say "Quill
  dictate" in the field you want and dictation starts there. While it waits,
  the State field and the tray say Listening for your wake phrase, and nothing
  it hears is written, kept or sent until it hears the phrase. It does not
  listen while QUILL Transcribe, QUILL or QUILL Lite, or a program on your
  never-type list, is in front. User guide: "Starting with your voice: the
  wake phrase".
- **Programs dictation never types into.** A list you keep, in More Dictation
  Settings (Alt+N), that starts with the common password managers and the
  Windows sign-in prompts. Dictation and Insert Again refuse a listed program
  by name and type nothing; held words stay held. User guide: "Where it will
  not type".
- **Resume in This Field**, from the window or the tray: choosing it again
  cancels the wait, and says your words are still held.
- **Programs it has been tested with.** A new section of the user guide lists
  Notepad, WordPad, Word, Outlook, Edge, Chrome, Firefox and Visual Studio
  Code, each marked supported, best effort, unsupported or untested, with the
  version and the day it was checked. So far every row says untested: a
  program that was not tried is never listed as unsupported.

### What you hear, and what is typed

- **Quiet with your screen reader.** Words are typed as the keys of your
  keyboard layout, so a screen reader no longer says "c" before or after each
  phrase. With phrase feedback set to a tone or to nothing, QUILL Transcribe
  presses Ctrl straight after the words, which every screen reader takes as
  "stop talking", so you no longer hear "period" after every phrase. With the
  read-back on, you still hear everything. User guide: "What you hear".
- **Saying the same phrase twice writes it twice.** It was taken for the
  screen reader's echo and dropped.
- **A tick while a phrase is worked on.** With a large model there can be
  seconds between your pause and the text. When a phrase takes more than a
  second, a soft tick plays once a second until it arrives; the first time in
  a session that one takes four seconds, you hear "Still working on that
  phrase." On by default here; turn it off in More Dictation Settings, **Tick
  while a phrase is being worked on**. With **What you hear after each phrase**
  set to words only there is no tick, only the sentence; set to nothing, there
  is neither.
- **A calmer spoken preview.** With **Show it, and say new words quietly**
  chosen for the words heard so far, each word is said once, when the model
  has settled on it.
- **Dictation on your braille display.** While you work in the other program,
  the words heard so far ("Hearing: ...") and the changes that are shown but
  not said (Command mode, Waiting for a command, Listening for your wake
  phrase) appear on a braille display, without being spoken.
- **Dictation Status** (Alt+F9 in the Dictation menu, as in QUILL and QUILL
  Lite): one sentence with what dictation is doing, the program it is writing
  into, the model, and how many phrases are held. "Speech goes to OpenAI." (or
  the speech provider's name) ends the state line while an online engine has
  your speech.
- **Emoji arrive whole.** An emoji, or any character beyond the first 65,536
  in Unicode such as a rarer Chinese character, is typed as one character. A
  plain edit box such as the Run box (Windows+R) used to receive half of it
  and show a box or nothing. For example, if a word in My Words is replaced
  with a thumbs-up emoji, saying that word in the Run box now types the
  thumbs-up. Limit: a program whose font has no picture for an emoji still
  shows a box, though your screen reader reads it by name.

### Commands, spelling and correcting

- **The command word: "QUILL scratch that".** A command starts with QUILL, and
  whatever follows QUILL is never typed into the other program. Said on its
  own, "scratch that" is typed as words (strict mode, on in QUILL Transcribe;
  "stop dictation" always works). If what follows QUILL is not a command you
  hear "Not a command", and "QUILL type that" types it. "QUILL command mode"
  takes commands without the word until "dictation mode" or eight seconds with
  none. Choices in More Dictation Settings: the command word (Alt+C), strict
  mode (Alt+E) and the seconds (Alt+D). User guide: "The command word".
- **Command Key and Speak a Command.** An optional system-wide key, empty until
  you choose it in setup or in **File > Command Key...** (Ctrl+Alt+Shift+K):
  press it in the field and the next thing you say is a command; twice,
  command mode. **Dictation > Speak a Command** (F11, as in QUILL and QUILL
  Lite) does the same from the window. Two new sounds play when QUILL hears the
  command word and when command mode ends.
- **Spell an address with pauses.** While spelling, each phrase joins the
  letters you spelled just before it, with no space: "QUILL start spelling",
  "juliet oscar", "at sign echo x-ray", "dot charlie oscar", "stop spelling"
  types *jo@ex.co*. Say "space" for a space. Limit: a whole word such as
  "smith" is not a letter and is left out; spell it.
- **A Markdown link by voice.** "open bracket the guide close bracket open
  paren page close paren" types `[the guide](page)`, with no space between the
  bracket and the parenthesis.
- **Snippets, abbreviations and clips by voice, in any program.** "insert
  snippet" and its name, "insert abbreviation" and its name, and "paste clip"
  and a number are typed as one phrase, and "QUILL scratch that" takes all of
  it back. A snippet with blanks asks for each blank by name and each choice by
  its options, then types the whole snippet once; say skip, scratch that to go
  back, or cancel. "QUILL read that" reads back all of what dictation typed.
- **What can I say** is a spoken answer while dictating, so dictation is not
  paused, and the Dictation Commands window lists only what works in other
  programs, with your own words and phrases.
- **Correcting in another program.** "Correct that" and "choose one" to
  "choose three", "capitalize that", "all caps that", "no caps that", "replace
  Tuesday with Wednesday", "change that to" and new words, "delete last
  sentence" and "delete previous paragraph" work on the words QUILL Transcribe
  typed there itself: it takes them back with Backspace and types the
  corrected words. It never reads the other program. A correction is refused,
  with one sentence and nothing sent, if the focus has moved, if you have
  typed, clicked or moved the mouse since, or, for the commands that retype
  words, in Word and Outlook, which change words as they are typed. User
  guide: "Correcting in another program".
- **A second opinion for "correct that".** With Moonshine, Whisper or a
  downloaded model, the other built-in engine listens to your last phrase
  again, and you can choose its answer. The sound stays in memory only.
- **Dictation profiles**: Standard, Email, Document, Markdown, Chat, Coding and
  Verbatim, each changing the pause, filler words, punctuation and how
  headings, bold and italic are written. Choose one in **Dictation > Dictation
  Profile** (Ctrl+Shift+F), the tray menu, More Dictation Settings, or by voice
  ("QUILL email mode"). **Lock Profile** (Ctrl+Shift+L) stops voice switching.
  Standard, the default, changes nothing. User guide: "Profiles: the kind of
  writing you are doing".
- **Bold and italic by voice**: "QUILL bold that" and "QUILL italic that". In
  the Markdown and Coding profiles they retype the phrase you just dictated
  with asterisks round it; in other profiles they say why they cannot format
  another program.
- **Fix it when I correct myself** (Alt+X in Dictation Settings, off until you
  turn it on): "meet on Thursday, no, Friday" types "meet on Friday". It
  happens before anything is typed, on this computer, with no AI.
- **Dictation style** (Alt+Y in Dictation Settings): Verbatim, Clean or, when
  AI is set up in QUILL, Polished. One choice that sets filler removal, fixing
  your corrections and, for Polished, review first and polishing.

### Review and polish

- **Review before it is typed.** Say "QUILL review that" and the last phrase is
  backspaced away and held in the **Review Dictation** window (Shift+F4 in the
  Dictation menu, as in QUILL and QUILL Lite). Read it, change it, keep talking
  into it, and with AI set up in QUILL, ask the AI to change it ("QUILL make it
  shorter"). "QUILL insert it" or Ctrl+Enter goes back to the field you were in
  and types it there once. You are asked before anything is sent to an AI.
  **Send dictation to review first** (Alt+V in More Dictation Settings) sends
  everything you say there. User guide: "Review before it is typed".
- **Polish what you said, when you ask.** Check **Allow polishing my dictation
  with AI when I ask** (Alt+G in More Dictation Settings, off by default).
  Then "QUILL polish that" opens the last phrase in Review Dictation and asks
  the AI once to fix punctuation, capitals and small slips, keeping your words;
  **Polish** (Ctrl+P) in the window does the same. It never runs by itself.

### Your words, settings and history

- **Your dictation settings, shared with the family.** More Dictation Settings
  has **Share dictation settings with every QuillVille program** (Alt+Q).
  When it is checked, what you save here is used by QUILL, QUILL Lite and Quill
  Inkwell, and what you save in them is used here within a second. Keys, the
  tray, the working tick, strict mode, what you hear after each phrase and
  every permission to send your speech stay QUILL Transcribe's own. Checked for
  a new install; unchecked if you had already changed your settings. User
  guide: "Sharing dictation settings with the family".
- **The word list's new home.** My Words and Phrases lives in
  `%LOCALAPPDATA%\QuillVille\Dictation`, copied there from QUILL's data folder
  the first time it is needed. The old file is left as a backup.
- **Import and Export in My Words and Phrases** (Alt+Shift+F10). Export saves
  your list to a Markdown file or a CSV file with say, write and kind columns.
  Import adds what is new from either, after showing how many it will add;
  nothing you have is replaced, and your list as it was is kept as
  dictation-before-import.md.
- **A backslash in your own phrases is kept.** A phrase that writes a folder,
  such as "my folder" writing `C:\new\temp`, used to read back as `C:`, a new
  line and `ew`, then a tab. It is now saved with each backslash doubled and
  reads back exactly as you typed it. To fix a phrase that already broke, open
  My Words and Phrases, choose it, Edit, and type the folder again. Limit: when
  you edit `dictation.md` by hand, write `\\` for a backslash before `n` or
  `t`.
- **The editors' dictation keys work here.** In the QUILL Transcribe window,
  Ctrl+F11 starts and stops, Alt+Shift+F6 opens Dictation Settings and Shift+F5
  transcribes a recording; Ctrl+D, Ctrl+, and Ctrl+O still work. New here on
  the editors' keys: **My Words and Phrases** (Alt+Shift+F10) and **Switch
  Dictation Language** (Ctrl+Shift+F11), both in the Dictation menu. User
  guide: "The same keys as QUILL and QUILL Lite".
- **Recent Phrases** (Shift+F11): the last 20 phrases of this run, newest
  first, with what a correction replaced marked "(before correction)". Insert
  Again types one into the program you go back to, with the same checks as
  dictation; Copy puts it on the clipboard.
- **Nothing you said is lost.** Words held while dictation is paused, and a
  phrase Windows stopped typing part-way, are kept on this computer, sealed for
  your Windows account, until you type or discard them, so a crash, a sleep or
  exiting loses nothing. Recent Phrases lists them after this run's phrases,
  with a review you did not finish, and has **Discard** (Alt+D).
- **Dictation history, off unless you want it.** **Keep a dictation history**
  (Alt+Y in More Dictation Settings) keeps the text of what you dictate for
  one, seven or thirty days, never the sound. **Clear History** (Alt+H) in
  Recent Phrases deletes it after asking; turning it off deletes it too.

### Models and speech providers

- **Which model suits this computer, and why.** Choose Model (Ctrl+M) and Set
  Up show a read-only **Recommended for this computer** box: the model that
  suits your computer and dictation language, whether it keeps up, about how
  soon your words appear after you pause, and the download size. The Model
  Library (Ctrl+L) adds **What matters most** and **Show Recommended Model**.
  It is only advice; your model never changes by itself. Every model is
  labelled **Lightweight**, **Balanced** or **High accuracy**.
- **Speech providers, your own account.** Dictation Settings has **Speech
  Providers...** (Alt+V): twelve speech companies, from Azure and Google to
  Deepgram and Groq, each with only the fields it needs, a Test Connection that
  sends no speech, and keys in Windows Credential Manager. Choose one in the
  Speech engine list there (Choose Model does not list the providers yet); you
  are told what is sent and No is the default. If it cannot be reached, your
  model stays your choice. User guide: "Speech providers: your own account".
- **A proper guide to choosing a model.** The user guide's "Models" chapter
  explains every choice: the built-in Moonshine (the default, nothing to
  download) and Whisper, Windows speech recognition, the ten downloadable
  models with their sizes, languages, tiers and memory, the recommendation,
  OpenAI and the speech providers, with a worked example, "Dictating in
  Spanish" (commands stay in English) and "Limits".
- **Advice from real speech.** The recommendation, the tiers and the figures
  now come from tests with recordings of real people (22 October 2026), not a
  synthetic voice, and the advice says so. For English on a computer with
  8 GB and four cores it names NVIDIA Parakeet Unified 0.6B: 3.2 percent of
  words wrong on audiobooks no model was trained on, against 6.5 for the
  built-in Moonshine. With 8 GB and two cores it names Parakeet TDT 0.6B v3.
  In Spanish on 8 GB it names Parakeet TDT v3: 4.4 percent wrong, against
  30.5 for the built-in Whisper. On 4 GB, or with little memory free, it
  stays with the built-in Moonshine (English) and Whisper (Spanish). Shared
  with QUILL and QUILL Lite. User guide: "How we chose: tested on real
  speech".
- **More memory on an 8 GB computer, and free memory counts.** A computer
  with 8 GB may now give dictation 1.6 GB beside the screen reader (it was
  1 GB), and never more than is free when you ask, less half a gigabyte. User
  guide: "The recommendation".
- **Tiers follow real speed.** Parakeet TDT v3, Parakeet Unified and Whisper
  base.en are now **Lightweight**; Nemotron is **Balanced**. User guide: "What
  the tiers mean".
- **Removed: five English-only models.** Distil-Whisper small.en, Whisper
  small.en, Distil-Whisper medium.en, Whisper medium.en and Distil-Whisper
  large-v3. On real recordings Parakeet Unified got 3.2 percent of words wrong
  on the held-out audiobooks, against 3.6 to 6.3 for these, and ran faster,
  in the same or a smaller memory tier. Whisper base.en and the multilingual Whisper
  models stay. If one was your model, it becomes Parakeet Unified if that is
  downloaded, otherwise the built-in model; nothing is downloaded, and you
  are told once, the next time dictation starts. Their files are not deleted:
  they stay in `%LOCALAPPDATA%\QuillVille\Dictation\models` until you delete
  the folder. To use Parakeet Unified, download it from the Model Library
  (Ctrl+L). User guide: "Models removed in October 2026".
- **Moonshine base hears long phrases.** It wrote nothing for any phrase
  longer than about eight and a half seconds; it now hears them in pieces and
  joins them. The pieces overlap by half a second (23 October 2026), so a
  word that falls where two pieces meet is no longer lost. User guide: "The
  models you can download".
- **A better Spanish model, said once** (23 October 2026). The first time you
  dictate in Spanish on a computer that can run Parakeet TDT v3 (in practice
  8 GB of memory and four cores), while your Spanish would go to the built-in
  Whisper, you hear one sentence: "For Spanish, NVIDIA Parakeet TDT 0.6B v3
  gets about 6 percent of words wrong, against 29 for the built-in model. It
  is a 670 MB download in the model list." (or "It is already downloaded;
  choose it in the model list."). Nothing is downloaded or switched, a 4 GB
  computer hears nothing, and it is said once across every QuillVille
  program. At most one such sentence is said at each start: a downloaded
  model that gave way to the built-in one, then a removed model, then this.
  Shared with QUILL and QUILL Lite. User guide: "Dictating in Spanish".

### Practice and lessons

- **Practice Dictation** (Ctrl+Shift+P in the Dictation menu): a window with a
  field of QUILL Transcribe's own that dictation types into straight away, so
  you can learn and test without writing into another program. **Start
  Dictation Here** (Alt+H, or Ctrl+F11 in the window) starts and stops it.
  User guide: "Practice Dictation".
- **The recognition test.** In Practice Dictation, **Read This Sentence**
  (Alt+T) clears the field and scores the first thing you say against the
  sentence shown: "All 9 words right", or how many percent were right and which
  words were heard differently, with three suggestions below 80 percent.
  **Score the Field** (Alt+S) scores everything in the field.
- **Tutorials** (Ctrl+Alt+F1 in the Help menu): five short lessons (a first
  dictation, pausing and resuming, commands with the command word, snippets by
  voice, and review), in the same Tutorials window as QUILL, with a tutorial
  book beside the user guide.

### Recordings

- **Transcribe a Recording translates into English.** For a recording in
  Spanish, check **Translate into English** (Alt+E) and the transcript comes
  out in English, with the built-in Whisper or a multilingual Whisper you
  downloaded; with any other model the box is unavailable. The same in QUILL
  and QUILL Lite. User guide: "Transcribing a recording".
- **Type a transcript into a field.** **Review Transcript** has **Type into a
  Field** (Alt+F): the transcript, or the part you selected, is typed into the
  program you go back to, with the same checks as dictation.

### Sounds and the window

- **Where QUILL Transcribe's own sounds play, and Alt+Shift+M to turn them
  off.** **Options > App Sounds Play On...** (Ctrl+Shift+S) offers System
  default, None (no sounds), or any sound card or headset by name. After a
  change one sound plays on the new card. If that card is unplugged the sounds
  play on the system default until it is back, and QUILL Transcribe says so
  once. **Alt+Shift+M** turns the sounds off and back on, and **Options > App
  Sounds** shows a check mark while they are on. Your screen reader is never
  moved. Asked for on QUILLVille by Rick Lewis. User guide: "Where QUILL
  Transcribe's own sounds play".
- **Alt+W opens the Window menu again.** The **Discard Held Words** button also
  claimed Alt+W, so Alt+W threw away held words instead of opening the Window
  menu. The button's letter is now C (Alt+C). **Dictation > Discard Held
  Words** (Ctrl+Shift+D) is unchanged.

### Installing

- **Runs on Python 3.14, and older runtimes are cleaned up.** The shared
  QuillVille runtime this build installs is Python 3.14. The installer then
  removes older runtimes (Python 3.13) that no installed QuillVille app uses
  any more; one that an app or a shortcut still points to is left alone.
  Portable copies carry their own Python and change nothing outside their
  folder.

## 1.0.0 - 2026-11-01

The first release.

### Dictating into other programs

- Start and stop dictation with a key you choose, from the tray menu, or from
  the window. No key is registered until you choose one.
- Words are typed into the field that had the focus when dictation started,
  and only that field.
- When the focus moves, dictation pauses and holds what you say. Resume writes
  the held words back where you started; Resume in This Field moves dictation to
  the field you are in, after the same checks as a new start; Discard Held
  Words throws them away.
- Starting from the tray or the window waits until you are back in another
  program, and gives up after 20 seconds.
- Password fields, programs running as administrator, and QUILL's own windows
  are refused with a sentence that says why.
- A phrase Windows did not fully take is reported as possibly incomplete, never
  as written.
- The same commands, punctuation, spelling, capitals and spacing modes and
  word list as dictation in QUILL. Commands that need to read the other
  program's text are refused politely.

### Models and microphone

- Choose Model lists every model, marked as on this computer or over the
  internet, with its languages, size, source, licence and whether it is
  downloaded.
- The chosen model is the one that runs. A missing model, or one that will not
  load, stops the start and says so; Use the Built-in Model This Time uses
  Moonshine for one session, on purpose.
- OpenAI appears only with a saved OpenAI key, and asks before any speech is
  sent.
- The Model Library and Dictation Settings are the same windows QUILL uses.
- Choose Microphone, and a four-second microphone test in setup that stays on
  this computer.

### The app

- Set Up QUILL Transcribe: microphone, model, key, and starting with Windows,
  all on one page; Skip changes nothing.
- A tray menu that says what dictation is doing and which model it uses, and
  does everything the window does.
- A calm window: state, model and microphone, what happens next.
- Transcribe a Recording, with a read-only Review Transcript window to copy,
  save or open the result in QUILL.
- While QUILL Transcribe runs, Quill Inkwell's Dictate Anywhere key is passed
  to it, so only one program dictates at a time. The first run brings over
  Inkwell's Dictate Anywhere settings and key, without changing Inkwell.
- QUILL and QUILL Lite's Dictate in Other Programs hands your editor's
  dictation settings to QUILL Transcribe while it runs.
- F1 help on every window and control.
- Safe Mode listens to nothing, registers no keys and downloads nothing.
