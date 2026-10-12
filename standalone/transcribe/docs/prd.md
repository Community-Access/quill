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

## Waiting for a later version

- Typing a reviewed transcript into another program's field.
- Optional transcript history.
- Named dictation profiles for email, notes and forms.
- A multi-page setup with Back on each step.
- Inkwell and the editors using QUILL Transcribe as a service rather than
  through the owner lock; Inkwell's own Dictate Anywhere pausing when the
  focus moves, as QUILL Transcribe's does.
- A published list of tested programs.
