# QUILL Transcribe Changelog

All notable changes to QUILL Transcribe are recorded here, newest first. The
release notes (`release-notes-1.0.md`) tell the same story as a narrative; this
file is the itemized list.

## Unreleased

- **Nothing you said is lost** (2026-10-16). Words held while dictation is paused, and a phrase Windows stopped typing part-way, are now kept on this computer, sealed for your Windows account, until you type or discard them, so a crash, a sleep or exiting loses nothing. **Recent Phrases** (Shift+F11) lists them after this run's phrases, with a review you did not finish, and has **Discard** (Alt+D). Stopping says they are kept; the next start says how many are waiting, and exiting no longer asks about words that are kept.
- **Type a transcript into a field** (2026-10-16). **Review Transcript** has **Type into a Field** (Alt+F): the transcript, or the part you selected, is typed into the program you go back to, with the same checks as dictation.
- **Dictation history, off unless you want it** (2026-10-16). **Keep a dictation history** (Alt+Y in More Dictation Settings) keeps the text of what you dictate for one, seven or thirty days, never the sound. **Clear History** (Alt+H) in Recent Phrases deletes it after asking; turning it off deletes it too.
- **Snippet blanks by voice** (2026-10-16). "QUILL insert snippet bug report" asks for each blank by name and each choice by its options, then types the whole snippet once; say skip, scratch that to go back, or cancel. "QUILL scratch that" takes all of it back.
- **"QUILL read that" reads all of it** (2026-10-16): a whole snippet or clip, not just its name.

- **Review before it is typed** (2026-10-15). Say "QUILL review that" and the
  last phrase is backspaced away and held in the **Review Dictation** window
  (Shift+F4 in the Dictation menu, as in QUILL and QUILL Lite). Read it, change
  it, keep talking into it, and with your ChatGPT subscription or your own key
  set up in QUILL, ask the AI to change it ("QUILL make it shorter") and hear
  what changed. "QUILL insert it" or Ctrl+Enter goes back to the field you were
  in and types it there once, with the same checks as every phrase. Nothing is
  typed into the other program while you review, and you are asked before
  anything is sent to an AI. **Send dictation to review first** (Alt+V in More
  Dictation Settings) sends everything you say there.

- **Programs it has been tested with** (2026-10-15). A new section of the user
  guide lists Notepad, WordPad, Word, Outlook, Edge, Chrome, Firefox and Visual
  Studio Code, each marked supported, best effort, unsupported or untested,
  with the version, the day it was checked and the day it is due to be checked
  again. The table comes from a test that types the same phrases into each
  program and reads them back. So far every row says untested: the first run
  was stopped because the test computer was in use, and a program that was
  not tried is never listed as unsupported.

- **The command word: "QUILL scratch that"** (2026-10-15). A command now
  starts with QUILL, and whatever follows QUILL is never typed into the other
  program. Said on its own, "scratch that" is typed as words (strict mode, on
  in QUILL Transcribe; "stop dictation" always works). If what follows QUILL
  is not a command you hear "Not a command", and "QUILL type that" types it.
  "QUILL command mode" takes commands without the word until "dictation mode"
  or eight seconds with none, ending with a falling tone; the State field and
  the tray say Command mode. Choices in More Dictation Settings: the command
  word (Alt+C), strict mode (Alt+E) and the seconds (Alt+D).
- **Command Key** (2026-10-15). An optional system-wide key, empty until you
  choose it in setup or in **File > Command Key...** (Ctrl+Alt+Shift+K): press
  it in the field and the next thing you say is a command; twice, command
  mode. **Dictation > Speak a Command** (F11, as in QUILL and QUILL Lite) does
  the same from the window. Two new sounds play when QUILL hears the command
  word and when command mode ends.

- **Import and Export in My Words and Phrases** (2026-10-15). Export saves
  your list to a Markdown file or a CSV file with say, write and kind columns.
  Import adds what is new from either, after showing how many it will add;
  nothing you have is replaced, and your list as it was is kept as
  dictation-before-import.md. You hear the counts, such as "Imported 12 words,
  3 already there." QUILL Lite can now use this same list too (Use the shared
  word list, in its own My Words and Phrases).

- **Which model suits this computer, and why** (2026-10-15). Choose Model
  (Ctrl+M) and Set Up show a read-only **Recommended for this computer** box:
  the model that suits your computer and dictation language, whether it keeps
  up, about how soon your words appear after you pause, and the download size.
  The Model Library adds **What matters most** and **Show Recommended Model**.
  It is only advice, labelled an estimate; your model never changes by itself.
  Every model is now labelled **Lightweight**, **Balanced** or **High
  accuracy**.
- **Programs dictation never types into** (2026-10-15). A list you keep, in
  More Dictation Settings (Alt+N), that starts with the common password
  managers and the Windows sign-in prompts. Dictation and Insert Again refuse a
  listed program by name and type nothing; held words stay held.
- **"Speech goes to OpenAI."** ends the state line while the OpenAI engine has
  your speech.
- **Resume in This Field** from the window or tray: choosing it again now
  cancels the wait, and says your words are still held.

- **Where QUILL Transcribe's own sounds play, and Alt+Shift+M to turn them off.** **Options > App Sounds Play On...** (Ctrl+Shift+S) offers System default, None (no sounds), or any sound card or headset by name. After a change one sound plays on the new card, so you hear where it went. If that card is unplugged the sounds play on the system default until it is back, and QUILL Transcribe says so once. **Alt+Shift+M** turns QUILL Transcribe's sounds off and back on where they were, and **Options > App Sounds** shows a check mark while they are on. Each QUILL app keeps its own choice; "Share these choices with my other Quill apps" keeps them in step. Your screen reader is never moved. Asked for on QUILLVille by Rick Lewis.

### Dictating into other programs

- The start and stop key is **Alt+Shift+Backslash** from the start. Change it
  or empty it in Dictation > Start and Stop Key.
- Record Key, beside every key box: press the combination you want and it is
  written out for you. Typing the key still works.
- No more "c" before or after each phrase with JAWS: words are typed as the
  keys of your keyboard layout rather than as Unicode keystrokes.
- With phrase feedback set to a tone or to nothing, the screen reader no longer
  says "period" (or the last character) after every phrase: QUILL Transcribe
  presses Ctrl, which every screen reader takes as "stop talking", straight
  after the words. With the read-back on, you still hear everything.
- Saying the same phrase twice writes it twice. It was taken for the screen
  reader's echo and dropped.
- **One microphone across the family.** QUILL, QUILL Lite, QUILL Transcribe and
  Quill Inkwell share one microphone lock, held only while one of them is
  dictating, QUILL's Locked Dictation (Ctrl+F9) included. Your start and stop
  key while an editor dictates names it and the key that stops it: "QUILL Lite
  is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try again."
  Ctrl+F11 in an editor while QUILL Transcribe listens opens no second
  microphone and names your key: "QUILL Transcribe is listening. Press
  Alt+Shift+Backslash to stop it, then try again." Waiting in the tray holds
  nothing, so the editors dictate as usual.
- **QUILL Lite's window is refused like QUILL's.** QUILL Transcribe no longer
  types into QUILL Lite; it says "This is a QUILL window: press Ctrl+F11 to
  dictate here."
- **The editors' dictation keys.** In the QUILL Transcribe window, Ctrl+F11
  starts and stops, Alt+Shift+F6 opens Dictation Settings and Shift+F5
  transcribes a recording, as in QUILL and QUILL Lite. Ctrl+D, Ctrl+, and
  Ctrl+O still work. Two commands are new here, on the editors' keys: **My
  Words and Phrases** (Alt+Shift+F10) and **Switch Dictation Language**
  (Ctrl+Shift+F11), both in the Dictation menu.
- **Recent Phrases** (Shift+F11, as in the editors): the last 20 phrases of this
  run, newest first. Insert Again types one into the program you go back to,
  with the same checks as dictation; Copy puts it on the clipboard. Memory
  only: nothing is saved to disk yet.
- **Snippets, abbreviations and clips by voice, in any program.** "insert
  snippet" and its name, "insert abbreviation" and its name, and "paste clip"
  and a number are typed as one phrase, and "scratch that" takes all of it
  back. A snippet's blanks are typed as [name], with no questions, and the
  cursor stays at the end.
- **What can I say lists what works here.** Said while dictating, it answers
  in a sentence instead of opening a window, so dictation is not paused. The
  Dictation Commands window lists only what works in other programs, and your
  own words and phrases.
- **A tick while a phrase is worked on.** With a large model there can be
  seconds between your pause and the text. When a phrase takes more than a
  second, a soft tick plays once a second until it arrives; the first time in a
  session that one takes four seconds, you hear "Still working on that phrase."
  On by default in QUILL Transcribe; turn it off in More Dictation Settings,
  **Tick while a phrase is being worked on**. With **What you hear after each
  phrase** set to words only there is no tick, only the sentence; set to
  nothing, there is neither.
- **Runs on Python 3.14, and older runtimes are cleaned up.** The shared QuillVille
  runtime this build installs is Python 3.14. The installer then removes older
  runtimes (Python 3.13) that no installed QuillVille app uses any more; one that
  an app or a shortcut still points to is left alone. Portable copies carry their
  own Python and change nothing outside their folder.

## 1.0.0 - 2026-10-11

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
