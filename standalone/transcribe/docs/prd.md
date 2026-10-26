# QUILL Transcribe -- Product Requirements

Version 1.0.0. Status: implemented; releases 1 November 2026 (first public
release). In `RELEASED_APPS` from 2026-10-16, so every public QuillVille menu,
tray menu and companion-install offer lists it, and Quill Cast's and Quill
Radio's Edit > Dictate Here shows in public builds. Its own QuillVille menu is
five rows (QUILL, Quill Radio, Quill Weather, Quill Converter, Quill Inkwell on
Ctrl+Alt+Shift+F7 to F11); it is last in `QUILLVILLE_APP_ORDER`, so no other
app's row changes key. A release blocker remains: the screen-reader pass in
Outlook, Word, Notepad and the browsers (`docs/qa/screen-reader-checks-2026-10.md`).

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
4. **Internet models.** At 1.0.0, only OpenAI, which already had QUILL's key
   storage, consent and network review. It is listed only when a key is saved
   and asks before anything is sent. Since 2026-10-16 (dictation design record
   section 23, D-31 to D-37), Dictation Settings' **Speech Providers...** adds
   twelve speech companies with the person's own account (Azure, Google,
   Amazon, Deepgram, AssemblyAI, Speechmatics, ElevenLabs, Gladia, Rev.ai,
   Groq, Mistral, IBM Watson), each with its own consent question, keys in
   Windows Credential Manager, and none recommended. Choose Model (Ctrl+M) does
   not list them yet; Dictation Settings does. Local models stay the default.
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
11. **Never lose what was said** (after 1.0.0, D-5). Words held while paused,
   and a phrase whose typing stopped part-way, are kept on disk, sealed with
   Windows DPAPI, until they are typed or discarded; Recent Phrases lists them
   after this run's phrases, with Discard. A finished recording's transcript
   can be typed into a field (Review Transcript's Type into a Field). The text
   history is opt-in (Keep a dictation history: off, 1, 7 or 30 days), text
   only, clearable, and deleted when turned off.
12. **Snippet blanks by voice** (after 1.0.0, D-8). "QUILL insert snippet"
   asks for each blank and choice, then types the filled snippet as one
   phrase. "read that" reads the whole of the last insertion (D-18).

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
13. **Correcting in other programs** (after 1.0.0, 2026-10-16, D-10). The
   correcting commands work on the words this session typed, and only those,
   as backspace-and-retype; the other program is never read. Each is refused
   with one sentence when the focus moved, when Windows saw a key or the mouse
   after dictation's own typing (when, never which key), or, for the commands
   that retype, in Word and Outlook until the insertion harness shows they are
   safe. "Correct that" with a one-answer engine asks the other built-in engine
   for a second opinion (D-19), in memory only.
14. **Correcting yourself, styles and polish** (after 1.0.0, 2026-10-16).
   The editors' settings and code (dictation design record section 28):
   **Fix it when I correct myself** (off) fixes "Thursday, no, Friday" before
   anything is typed; **Dictation style** offers Polished only when the review
   could reach an AI; **Allow polishing my dictation with AI when I ask** (off)
   makes "QUILL polish that" backspace the last phrase into Review Dictation and
   send one fixed request there, after the review's consent, never by itself.
   Learning a correction asks by voice ("QUILL yes"), never in a window, because
   a window would take the focus from the field; it follows "correct that" and
   "choose", which work here on the session's own words since decision 13.

15. **Learning and profiles** (after 1.0.0, 2026-10-16, D-25 and D-23).
   Practice Dictation is the one window of QUILL Transcribe's own that
   dictation writes into: its field is an editor-style target written with one
   undo step a phrase, never keystrokes, and only after the same refusals as
   any start. Its recognition test scores with the benchmark's own word-error
   count. Five lessons use the family's Tutorials window. Seven named profiles
   (Standard, Email, Document, Markdown, Chat, Coding, Verbatim) overlay the
   dictation settings; switching is manual only (menu, tray, More Dictation
   Settings, or by voice), and Lock Profile stops voice switching. In another
   program, a formatting profile types nothing for a heading and says why,
   because the other program's formatting cannot be applied by keystrokes
   QUILL Transcribe can trust.

13. **One settings store, and Dictate Here** (after 1.0.0, 2026-10-16).
   "Share dictation settings with every QuillVille program" (dict.md D-13) replaces the
   one-way hand-off as the way settings move: `family_dictation.json` in
   `%LOCALAPPDATA%\QuillVille\Dictation`, written when Dictation Settings is
   saved anywhere and read here on the 800 ms clock, behind one check box that
   is on for a new install and off for one whose settings were changed. Keys,
   the tray, the working tick, strict mode, the read-back and every consent stay
   local. The word list moved to the same folder, copied with the old file kept.
   Quill Cast's and Quill Radio's Edit > Dictate Here (D-16) send a `start`
   request, or launch QUILL Transcribe with `--tray --dictate-here`. Dictation
   design record, section 30.
16. **Model advice from real speech** (after 1.0.0, 2026-10-22, D-22 and
   B-1). Met. The recommendation, tiers, speed factors and memory peaks come
   from the real-speech machine run recorded in
   `docs/qa/dictation-real-speech-benchmark-2026-10-22.md` (dictation design
   record, section 36), shared with QUILL and QUILL Lite through one engine
   and catalogue. English is ranked by the LibriVox held-out audiobooks:
   Parakeet Unified 3.2 percent of words wrong at 0.21 per thread, so it is
   recommended on 8 GB with four cores; Parakeet TDT v3 (3.8, 0.11) on 8 GB
   with two cores. Spanish is ranked by the mean of FLEURS Spanish and the
   Spanish audiobooks, only from models measured in Spanish: Parakeet TDT v3
   (4.4 and 7.3) on 8 GB, against the built-in Whisper's 30.5 and 27.0, which
   stays the pick on 4 GB with Moonshine for English. The memory cap is
   600 MB under 7 GB and 1.6 GB under 15 GB (it was 1 GB), and never more
   than is free less 500 MB. Tiers: Parakeet TDT v3, Parakeet Unified and
   Whisper base.en Lightweight; Nemotron Balanced. The advice's note says the
   figures come from real recordings on one computer.
17. **Removed models** (after 1.0.0, 2026-10-22, dictation design record
   section 37, which replaces section 32.6's deprecate-for-one-release
   policy). Met. Distil-Whisper small.en, Whisper small.en, Distil-Whisper
   medium.en, Whisper medium.en and Distil-Whisper large-v3 were each beaten
   by Parakeet Unified on the held-out audiobooks (5.9, 4.3, 6.3, 3.6 and 4.5
   percent against 3.2), faster on one thread and in no more memory, and are
   removed from the shared catalogue in the same release
   (`quill/core/windows_dictation/removed_models.py`). Whisper base.en and
   every multilingual Whisper size stay. A saved choice of one becomes
   Parakeet Unified when that is already downloaded, otherwise the built-in
   model (`engines.coerce_engine`); nothing is downloaded. The change is
   recorded in the family's shared dictation folder and said once, the next
   time dictation starts in any QuillVille program. Downloaded files are not
   deleted: the folders (`whisper-small.en-int8`,
   `whisper-distil-small.en-int8`, `whisper-medium.en-int8`,
   `whisper-distil-medium.en-int8`, `whisper-distil-large-v3-int8`) stay under
   `%LOCALAPPDATA%\QuillVille\Dictation\models` (portable:
   `data\dictation\models`) until the person deletes them.
18. **Moonshine base and long phrases** (after 1.0.0, 2026-10-22, PR #1683).
   Met. It returned nothing for any phrase over about 8.5 seconds; long
   phrases are now heard in pieces of 8 seconds or less, cut at the quietest
   moment, and joined. Measured after the fix: 5.9 percent on the held-out
   audiobooks.
19. **Help > What's New** (build 3, 2026-10-25). Met. The Help menu has
   **What's New** on Ctrl+Shift+F1, the key every standalone QuillVille app
   gives it: QUILL Transcribe's changelog (`docs/CHANGELOG`) opened as HTML in
   the browser through the family's shared `quill/ui/whats_new.py`. A build
   with no changelog says so rather than doing nothing.

Still to check by hand: speed, memory, screen-reader lag and battery on a real
4 GB Windows 10 computer with NVDA or JAWS running (B-8), and Whisper medium
and large-v3-turbo, which were too slow to re-run and keep their earlier
figures.

## Waiting for a later version

- Keeping audio for replay, which stays a separate opt-in that text history
  never implies.
- A profile chosen automatically by the program in front (needs the privacy
  review in the spec, section 7.6), and a word list per profile (D-21).
- A multi-page setup with Back on each step.
- Inkwell and the editors using QUILL Transcribe as a service rather than
  through the owner and microphone locks; Inkwell's own Dictate Anywhere pausing when the
  focus moves, as QUILL Transcribe's does.
- A published list of tested programs with results in it. The list, the test
  that fills it and the screen reader checks exist since 2026-10-15 (the user
  guide's "Programs it has been tested with"); every row is still untested.
