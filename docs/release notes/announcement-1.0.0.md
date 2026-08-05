# QUILL 1.0.0 is here

## A writing suite built by and for the people who work by ear and by touch.

*From Community Access. Free. Optional by design. Private by default. Built with you.*

Most software is built to be looked at, and then made reachable afterward. A label gets
added, a focus order gets repaired, a warning that flashed red is finally given a word. If
you write, read, proofread, or transcribe braille without looking at the screen, you know
how that story ends: the feature technically works, and using it is exhausting.

QUILL starts at the other end. Every feature began with the question of what you will
*hear* and what your fingers will *read*, and the visible interface is what fell out of
that answer. When a feature could not be made to work well by ear, it was redesigned until
it could, or it was not shipped. That is what 1.0.0 is: a complete writing and document
environment for blind and print-disabled readers, writers, students, proofreaders, and
braille transcribers, and for anyone who navigates by keyboard rather than mouse.

---

## It talks to you properly

Everything QUILL says goes through one shared service that speaks on four channels at
once: speech, braille, sound, and the status line. Speech reaches your screen reader
through a dedicated bridge for each one, so announcements arrive in your own voice at
your own rate instead of through a second, competing synthesizer. JAWS, NVDA, and
Narrator on Windows; VoiceOver on macOS. When any screen reader is running, QUILL's own
built-in voice stays silent so it can never talk over you. Sound carries its own share of
the load, because a sound never talks over a screen reader: starting a selection opens
with a rising two-note gate and completing it plays the mirror image, and the top and the
end of a document answer with a ceiling tick and a floor thud.

QUILL also says as much or as little as you want: four verbosity profiles, plus Quiet Mode
and Meeting Mode for when you need it to stop talking right now. **Spoken Echo** replays
the last twenty announcements as an arrowable list, and an **Announcement Self-Test**
reports which channels actually reached you.

## The keyboard is the interface

More than seven hundred named commands, every one reachable three ways: from the menu bar,
from the Command Palette, and from a shortcut you assign. Nothing hides in a toolbar with
no menu equivalent. The palette matches multi-word queries in any order, finds a command by
its shortcut, and speaks each result's shortcut alongside its name, so it quietly teaches
you the faster route while it runs the command for you. The status bar is a control panel
too, not a decoration: arrow to any cell and press Enter to act on it.

## Braille is a format, not a rendering of print

QUILL opens and saves `.brf`, `.brl`, `.pef`, and `.ueb` files while preserving the bytes.
Form feeds, line endings, and layout come back out exactly as they went in, and a round
trip produces an identical file. For a transcriber, that is the whole ballgame.

Text in QUILL begins in **braille cell 1**, not cell 2, eliminating the long-standing
offset that RichEdit controls share with Microsoft Word. Selected text shows dots 7-8,
restoring the tactile selection feedback braille readers expect. Both corrections are on by
default, because braille readers tested them and reported back.

Back-translating a braille file elsewhere requires that you already know which code it
uses, and picking wrong produces garbage with no explanation. **Back-Translate to Text
(Auto-Detect Code)** removes that burden: QUILL scores the file against every English
braille code it knows and announces the winner, "Detected UEB Grade 2 (contracted)." You
learn what your file is instead of being quizzed about it. Around it sit print-page
navigation, page-by-page proofing status, layout validation, and an exportable report.

## Every format, and it speaks the language of each one

Plain text, Markdown, HTML, Word, RTF, OpenDocument, EPUB, PowerPoint, spreadsheets, PDF,
LaTeX, CSV, JSON, XML, braille formats, and images through OCR. PDF and spreadsheet readers
ship with every install, so a brand-new copy opens a PDF or an `.xlsx` with nothing to
fetch first.

**Ctrl+B** wraps a Markdown selection in asterisks, writes `<strong>` in HTML, and applies
real bold in Word or RTF. One command, one intention, the correct result for the document
you are actually in. Formatting lives beside your text as hidden codes, which is why
search, spell check, read aloud, bookmarks, and braille all behave identically no matter
how formatted a document is, and **Reveal Codes** makes every code visible and speakable
on demand: the WordPerfect feature many people still miss, rebuilt screen-reader-first.

QUILL is also honest about what it cannot do. A Word file containing features QUILL cannot
carry names them specifically and asks how you want to proceed, and the first rich save over
a flagged original makes a timestamped backup beside it. QUILL never silently rewrites a
complex file and asks you to trust that everything survived.

## Reading, speaking, and dictating

Read Aloud speaks the document, a section, or a selection, stripping Markdown punctuation
so you hear words rather than a recital of hash marks. Voices include Windows SAPI 5,
DECtalk, eSpeak-NG, the local neural engines Piper and Kokoro, the macOS system voice, and
optional bring-your-own-key cloud voices. Audiobook and Batch Speech exports a whole folder
to chaptered audio with real MP3 chapter markers and ACX loudness normalization.

Dictation runs **on your own machine**, on whisper.cpp, Faster Whisper, Vosk, or NVIDIA's
Nemotron, with a model manager that checks your actual RAM and GPU before recommending
one. A safety net
saves your audio before transcription runs, so a session is never lost to a failed
transcription.

## AI, entirely on your terms

QUILL's AI is optional, opt-in, and silent until invited. If you never set it up, no menu
nags you. If you do, there is a genuinely free path and the wizard shows it rather than
hiding it behind the paid options: run Ollama locally and everything happens on your own
machine at no cost, or pick OpenRouter, where the wizard preselects a free model and labels
every free model as "Free." QUILL bundles no keys and takes no cut.

The discipline underneath every AI feature is that **the AI proposes, you dispose.** Every
suggested edit stops at a review dialog built to be judged by ear: changes announced as what
they are, and the sentence before and after each change available so you can judge a
one-word edit with the context a sighted reviewer gets from a highlight. Nothing touches
your document until you agree, and then it lands as a single undo step. QUILL never quietly
changes what is answering you, and never switches between cloud and on-device.

## Trust is the product

A writing tool that loses work, or that silently does something other than what it said, is
worse than no writing tool at all, and that is doubly true when you cannot glance at the
screen to catch it. Autosave snapshots your documents continuously, formatting included;
saves are atomic; undo survives a session. And if your screen reader stops mid-session,
QUILL snapshots every open document immediately, then says what happened using whatever can
still talk.

QUILL is a local program: it opens your files from your disk and writes them back to your
disk, and nothing about your documents is uploaded as a matter of course. Every feature that
reaches the internet is optional, asks before its first use, and is disabled in **Safe
Mode**, a known-good state with extensions, AI, and network features all switched off.

## Start where you want to start

The first launch asks one question: what kind of writing do you do? Your answer picks a
feature profile, from Just a Text Editor through Writer, Braille Professional, and
AI-Powered Author to Full QUILL, with a plain-English preview of what each one turns on
before you commit. No profile is a trap: switch at any time, toggle any single feature,
and ask **Help > Why Don't I See a Feature?** when something you read about here is not on
your menus. Install it with the Windows installer, unpack the portable ZIP onto a USB
stick, or take the Offline Edition, which carries every optional component inside it for
an air-gapped machine. macOS builds are notarized and Developer-ID signed.

## Built with you

QUILL is free, and it is built by and with the community that uses it. The ranked spelling
workflow came from a longtime Kurzweil 1000 user's side-by-side comparison. The braille
cell-alignment correction became the default because braille readers tested it and reported
back. The Offline Edition became genuinely offline because someone checked the promise
instead of assuming the label was enough.

If something surprises you, beautifully or badly, tell us. **Help > Report a Bug** is the
direct line, and a report that says "this works perfectly" is worth as much as one that
says it does not. The complete QUILL 1.0.0 release notes describe the editor feature by
feature, and also cover the companion apps that ship alongside it.

**QUILL 1.0.0. One editor. Every format. Built with you.**
