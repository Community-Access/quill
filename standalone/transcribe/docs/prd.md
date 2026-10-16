# QUILL Transcribe -- Product Requirements

Version 1.0.0. Status: implemented.

The full product requirements are in the repository at
`docs/Product Requirement Documents and Specifications/quilltranscribe.md`.
This page records what version 1.0 does with the decisions that document left
open, and what waits for a later version.

## Decisions taken for 1.0

1. **Name.** QUILL Transcribe; product identifier `QuillTranscribe`; app key
   `transcribe`. Its icon is a text caret with words arriving at it.
2. **One owner.** Version 1.0 does not have a full service that QUILL, QUILL Lite
   and Inkwell talk to. It has one owner at a time instead: QUILL Transcribe
   holds an operating-system lock in the family data folder while it runs, and
   Quill Inkwell's Dictate Anywhere key is passed to it. Inkwell takes the same
   lock only for the length of its own session, so the two never listen at
   once. Requests between them carry one word (toggle, start, stop or show) and
   never any words that were spoken.
3. **Recordings.** Transcribe a Recording is included. It is QUILL's own
   command and pipeline, unchanged; QUILL Transcribe adds only a window to
   review the result and copy it, save it, or open it in QUILL.
4. **Internet models.** Only OpenAI, which already had QUILL's key storage,
   consent and network review. It is listed only when a key is saved and asks
   before anything is sent.
5. **Where it works.** No list of supported programs is claimed yet. The list
   comes from testing with NVDA, JAWS and Narrator in Outlook, Word, Notepad and
   the three browsers.
6. **One microphone** (after 1.0.0, 2026-10-13). A second operating-system lock,
   separate from the owner lock, is held by whichever of QUILL, QUILL Lite, QUILL
   Transcribe and Inkwell has the microphone open, and only for as long as it is
   open. A second start is refused with the name of the program listening. It is
   separate because QUILL Transcribe holds the owner lock for as long as it runs,
   and the editors must still dictate while it waits in the tray. QUILL Lite's
   window is claimed as QUILL's is, so QUILL Transcribe does not type into it.
   QUILL's Locked Dictation (Ctrl+F9) takes the same lock while it records.
7. **The editors' keys** (after 1.0.0). A dictation command QUILL Transcribe
   shares with the editors answers the editors' chord (family rule 2), and the
   1.0 key stays as a second key (rule 5). The editors' dictation commands it
   does not have are listed, each with its reason, in
   `quill/core/transcribe/parity.py` (rule 11).
8. **The working tick** (after 1.0.0). A soft tick once a second while a heard
   phrase takes more than a second to recognise, and one sentence after four
   seconds, once a session. On by default here, off in the editors. *What you
   hear after each phrase* caps it: words only gives the sentence and no tick,
   nothing gives neither.
9. **Recent Phrases** (after 1.0.0). The editors' window and code, on
   Shift+F11. Insert Again types into the program you go back to, through the
   same keystroke path and checks as dictation. Memory only for now.
10. **In other programs** (after 1.0.0). "insert snippet", "insert
   abbreviation" and "paste clip" work, because they only insert. "What can I
   say" is a spoken sentence while dictating, and Dictation Commands lists
   exactly what works in other programs, with the person's own phrases.
11. **The wake phrase and holding the key** (after 1.0.0, 2026-10-15). Both are
   the editors' settings, off by default. The wake phrase listens only while
   another program is in front, and never while QUILL Transcribe, QUILL, QUILL
   Lite or a program on the never-type list is; nothing heard is kept until the
   phrase is heard, and the state line and tray say "Listening for your wake
   phrase". Holding follows the start and stop key itself, by asking Windows
   whether that one key is still down while a press is followed, with no
   keyboard hook. Because a system-wide key needs Ctrl or Alt, what is said
   while it is held is typed when it comes up.
12. **Feedback where you work** (after 1.0.0, 2026-10-15). The words heard so far
   and the unspoken state changes go to a braille display only. Dictation
   Status is the editors' Alt+F9. Dictation Status, Resume and Discard Held
   Words each have an optional system-wide key, empty until chosen, picked and
   checked like the others.

## Waiting for a later version

- Typing a reviewed transcript into another program's field.
- Recent Phrases kept on disk between runs (the rest of D-5).
- Snippet blanks filled in by voice, with spoken prompts (the rest of D-8).
- Optional transcript history.
- Named dictation profiles for email, notes and forms.
- A multi-page setup with Back on each step.
- Inkwell and the editors using QUILL Transcribe as a service rather than
  through the owner and microphone locks; Inkwell's own Dictate Anywhere pausing when the
  focus moves, as QUILL Transcribe's does.
- A published list of tested programs with results in it. The list, the test
  that fills it and the screen reader checks exist since 2026-10-15 (the user
  guide's "Programs it has been tested with"); every row is still untested.
