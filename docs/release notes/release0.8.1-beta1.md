# QUILL 0.8.1 Beta 1 — Meet You Where You Are

### The screen-reader-first writing studio, built by the people who depend on it.

*From Community Access. Free. Optional by design. Private by default. Yours to make quiet.*

This is the narrative companion to the **"0.8.1 Beta 1"** section of `CHANGELOG.md`
(the canonical, append-as-you-go log). It tells the story of what changes in
0.8.1 Beta 1 on top of the 0.8.0 line — what each feature is, and, just as
important, **why it matters** for the way you actually work.

---

## The story of this release

0.8.0 made QUILL a serious writing and document studio. **0.8.1 makes it yours.**

Three threads run through this beta. First, a complete, **optional** AI suite that
stays silent until you invite it in. Second, a wave of **power-user editing tools**
in the tradition of the editors people still miss — Reveal Codes, classic-editor
commands, and bookmarks that finally remember where you were. Third, a quieter,
**lighter, more honest install**: a smaller download, on-demand components you can
fetch from one place, and clearer, calmer announcements.

Everything new is off, optional, or additive. Nothing here changes how your fingers
already work — it just gives them more to reach for when you want it.

---

## The AI suite — powerful, and entirely up to you

### It is off until you turn it on

The headline addition is a complete, screen-reader-first AI suite under one new
top-level **AI** menu. It works with the provider *you* choose — a private
**on-device** model (Ollama) or an account with **OpenAI, Anthropic (Claude),
Google Gemini, or OpenRouter** — and nothing leaves your machine without your
consent.
**Why it matters:** AI in QUILL is a tool you pick up, not a thing that happens to
you. Set it up once and every feature shares that one connection; never set it up
and QUILL is exactly the editor it always was.

### Set up in seconds — the AI Setup Wizard

A short wizard ("Set Up AI… — start here") offers one choice — on-device, an
account, or not now — with a one-step connect and a Test Connection check. Click any
AI action before setup and QUILL offers the wizard right there instead of failing. A
**Basic** mode keeps the menu small for newcomers.
**Why it matters:** no dead ends, no jargon wall. You are never punished for trying a
button before you have configured anything.

### Ask Quill — one conversation that knows your document

A single, context-aware chat replaces the old scattered AI dialogs. Ask about your
text, have it draft or rewrite, and apply suggestions through a **reviewable change
preview** applied as one undo step.
**Why it matters:** nothing is ever silently rewritten. You see the change, you
accept or reject it, and one Undo puts everything back.

### The Listening Companion — recordings become finished documents

Transcribe an audio or video file (optionally translating to English or identifying
speakers), then turn the transcript into **Meeting Minutes, Action Items, an
Executive Summary, Interview or Study Notes, Q&A, a Follow-Up Email, Key Quotes, a
Decisions Log, or a clean draft** — from one context-aware list. Build your own with
the no-syntax **Action Builder**, or let a watch-folder do it automatically.
**Why it matters:** the gap between "I recorded it" and "I have the document" closes
to a couple of keystrokes.

### The AI Library — Prompts, Skills, and Agents in one place

A tabbed manager with a real promotion path: a **Prompt** graduates into a multi-step
**Skill**, and a Skill into a first-class **Agent** — all reviewable, all running
through the connection you set up once.
**Why it matters:** your reusable know-how grows with you instead of scattering
across dialogs.

### Everyday writing help, always reviewable

Rewrite, summarise, expand, continue, fix grammar, or generate a table of contents;
AI spell check and grammar-and-style check; translate a selection or document; the
AI Thesaurus; and Document Q&A. Read the selection or document aloud, or export it as
audio in a natural cloud voice, alongside QUILL's on-device speech.
**Why it matters:** every proposed change is an accessible accept/reject preview and
a single undo step — help you can trust, not magic you have to babysit.

---

## Rich formatting that stays out of your way

### Hidden codes, spoken on demand

Apply real document formatting — **bold, italic, underline, strikethrough,
super/subscript, font family and point size, colour and highlight**, plus paragraph
**alignment, line spacing, indent, and named styles** — without ever seeing markup
clutter. The buffer stays clean, fast, plain text; the formatting rides along as
invisible codes. Ask **"Describe formatting at cursor"** to *hear* exactly what is in
effect ("Arial, 14 point, centred, bold").
**Why it matters:** you get real formatting and a clean editing experience — you no
longer have to choose between the two.

### Keep your formatting in a plain-text file — Illuminations

A plain `.txt` cannot hold fonts or colours, so saving formatted text as plain text
used to lose them. Now QUILL can write an **Illumination**: a small companion file
(`yourfile.txt.illumination`) that stores the formatting beside the clean text. The
`.txt` stays genuinely plain everywhere else; reopening it *in QUILL* restores every
font, colour, and alignment exactly.
**Why it matters:** your text stays portable and plain, and your formatting still
survives — no lock-in, no surprise loss.

### Faithful round-trips

RTF and Word documents round-trip through the clean buffer and materialise back to
real formatting on export. **Word (.docx)**, **RTF**, and **HTML** carry font, size,
colour, highlight, and alignment; when a format genuinely cannot hold something,
QUILL tells you *before* you commit.
**Why it matters:** you hand documents back looking the way they came in, and you are
never silently stripped of work.

---

## Editing and accessibility — the power tools people missed

### Reveal Codes — see and hear every hidden code (Alt+F3)

The beloved WordPerfect feature, reimagined screen-reader-first. Press **Alt+F3** (or
**View → Reveal Codes**) to open a pane showing your document as a stream of bracketed
codes and text — `[Bold On]`, `[Font: Arial]`, `[Center]`, `[Tab]`, `[¶ Hard Return]`,
`[No-Break Space]`. **F6** moves between the editor, the Reveal Codes pane, and the
status bar (**Shift+F6** back), and the two carets stay in sync. Every code is an
individually-announced, navigable item; jump from a `[Bold On]` to its matching
`[Bold Off]` and hear its reach. Choose a **Structured** list or a **Flowed** view,
with quiet / balanced / detailed verbosity.
**Why it matters:** nothing about your document is hidden from you. The clean editor
stays clean; the truth is one keystroke away.

### Bookmarks that remember — per document, across sessions

Named bookmarks now belong to the **specific file** you set them in and **persist
between sessions**, so reopening a document brings its jump points back. QUILL also
remembers your **last cursor position** in each saved document and returns you there
when you reopen it.
**Why it matters:** close a long document on Friday, reopen it Monday, and you are
right where you left off — with every named landmark intact. (Set Bookmark, Go To
Bookmark, List Bookmarks; List Bookmarks is on Alt+Shift+B.)

### Inline notes — sticky comments that stay with your content

Jot a private note about the current line or selection with **Alt+Shift+I**. The
note is **anchored to the text**, so it follows that content as you edit and comes
back when you reopen the document (per document, like bookmarks). **Alt+Shift+J** /
**Alt+Shift+G** move to the next / previous note (the cursor jumps to the noted text
and QUILL reads the note); **Alt+Shift+H** speaks the note at the cursor, and pressing
it again quickly opens it to view, edit, or delete.
**Why it matters:** the running commentary, queries, and reminders you keep while
drafting finally live *with the words they are about* — surviving edits and reloads —
instead of in a separate file you have to keep in sync. If the noted text is deleted,
the note is kept rather than silently lost.

### Three classic-editor power tools

In the WordPerfect Editor tradition, all unbound by default (assign keys in the
Keymap Editor):
- **Repeat Next Command** — set a count, and the next command runs that many times
  (down twenty lines, delete ten words, insert forty dashes) in one gesture.
- **Restore Deleted Text** — QUILL keeps the last three blocks removed by its
  structured delete commands; re-insert any of them at the cursor (distinct from Undo,
  which only reverts in place).
- **Describe Character at Cursor** — names the exact character under the caret (Unicode
  name, code point, category, and notes for invisibles), the screen-reader descendant
  of "Reveal Codes".
**Why it matters:** the precise, repeatable, eyes-free moves that long-time editor
users have been asking QUILL to bring forward.

### Re-read anything QUILL just said — the Spoken Echo

The last twenty announcements are kept and shown newest-first in a read-only dialog
you can arrow through, re-read, and copy (**Alt+Shift+E**). Double-pressing an
informational command opens the Echo instead of re-speaking.
**Why it matters:** speech disappears the instant it is spoken; now you can get it
back.

### A far richer Keyboard Manager

The Keymap Editor searches two ways from one box — type part of a command name to
filter, or type a shortcut to reverse-look-up exactly which command owns it. **Record
Keys** lets you press a combination instead of typing it; assigning a taken key names
the command that holds it and offers to reassign; **Run Diagnostics** audits the whole
keymap and heals duplicate, orphaned, or inert bindings.
**Why it matters:** customising shortcuts no longer means remembering exact syntax or
guessing whether a key is free.

### Quieter, calmer, and quicker to move

- **Hear how deep your indentation is** — Tab / Shift+Tab can speak "4 spaces",
  "1 tab", instead of just "Indented lines".
- **Quieter dialogs, your choice** — turn off the spoken "Entered / Exited *name*
  dialog" cues if your screen reader already announces them.
- **Jump straight to an open document** — **Alt+1**…**Alt+9** (and **Alt+0** for the
  tenth) go directly to that document instead of cycling.
- **Quieter Read Aloud** — the follow-along selection is now off by default, so only
  the Read Aloud voice is heard, not "…selected" over it.
**Why it matters:** less chatter, fewer keystrokes, more signal.

---

## Story Studio — organize a whole book

### The binder: your project, one keystroke away

**Tools → Story Studio...** opens a keyboard-navigable **binder** for a project
folder. Your **Manuscript** appears with its parts, chapters, and scenes taken
straight from the Markdown headings you already write, alongside groups for
**Characters, Places, Plot threads, Research, and Brainstorm**. Arrow through the
tree; press Enter on any item to open that file — a chapter opens at its heading,
an element opens its notes.
**Why it matters:** a novel is more than one long file. Story Studio gives a
blind writer the same "see the whole book at a glance" a sighted writer gets from
a corkboard — as a tree a screen reader reads naturally, with no visual board.

### Character sheets and plot threads — a form, not a syntax

Select an element and choose **Edit details...** to fill in a small, accessible
form: a character's **Role, Goal, Motivation, and Arc**; a plot thread's
**Status**; **tags**. Your answers are saved as tidy front matter at the top of
the element's file, so editing the form and editing the file are the same bytes.
Blank fields are dropped, and anything already in the file that Story Studio does
not recognise is kept untouched.
**Why it matters:** structure without a database and without learning any markup
— and your notes stay in plain, portable text you own.

### Compile the manuscript, then export it your way

Press **Compile manuscript...** and Story Studio stitches every manuscript file
together, in order, into a new document. From there the ordinary **File →
Export** takes over — Markdown, HTML, Word, DAISY, and more — because the compiled
manuscript is just a document like any other.
**Why it matters:** the gap between "chapters in a folder" and "one finished file
to send" closes to a single keystroke, and you export it with tools you know.

### Nothing is locked in

A Story project is an ordinary **folder of plain-text files** plus one small
companion file that remembers the order and the element groupings. Delete the
companion and you still have every word. Story Studio is entirely optional and
additive: if you never open it, nothing about your editing changes.
**Why it matters:** your book is yours, in files any program can read, forever.

---

## Braille — proofreading for pages that must emboss

A new **Braille → Repair** submenu brings NLS-style proofreading: **Read Layout
Metrics** (longest line and page against your cells-per-line / lines-per-page limits,
with width and depth warnings), **Go to Longest Line / Longest Page**, and **Remove
Trailing Spaces** (this line or the whole file), all honouring your existing braille
page settings. A new **Editor control type (braille)** choice lets braille displays
that show the first character of each line in cell two switch to a plain edit control.
**Why it matters:** the difference between "it looks fine on screen" and "it actually
embosses cleanly", found and fixed before you send it.

---

## A smaller, friendlier install

### Download only what you need

The base installer is smaller because the heavy, optional pieces now download on
demand — checksum-verified, with a cancelable progress bar, disabled in Safe Mode:
- The **offline speech engine** (whisper.cpp), **Kokoro** neural voices, and the
  classic **eSpeak NG** and **DECtalk** voices.
- **Spell-check dictionaries for other languages** — pick **Spanish** or **French**
  under **Tools → Spell Check Language** and QUILL fetches the dictionary the first
  time.
- And the audio-export helper, **FFmpeg**.

**One place to get them all: Help → Download Optional Components.** A single dialog
lists every optional download with **Installed** vs **Available to download** and its
size, so you never hunt through menus.
**Why it matters:** a faster first download and install, Windows' built-in voices
working immediately, and a clear, accessible touch point for everything else.
**Upgrading?** Any component a previous release bundled is kept and keeps working —
nothing to re-download.

### Export speech audio as MP3 and more

With FFmpeg present, Generate Speech Audio now saves as **MP3, M4A, M4B, OGG, Opus, or
FLAC** (WAV still works without it).

---

## A thank-you, and a place to experiment

### Golden Quills

**Help → About QUILL** has a new **Golden Quills** tab recognising the people who
support the project financially, in alphabetical order, with our heartfelt thanks. It
includes an optional **Donate** button.
**Why it matters:** QUILL is free and always will be — donating is completely optional
and never required. This is simply gratitude, made visible.

### Experimental settings (for testing)

A new **Settings → Experimental** tab lets you test how QUILL feels on different
editor surfaces — **RichEdit 3.0 / 2.0**, **Notepad** (a plain edit control),
**Rich text**, or a **native Win32 EDIT** spike. A read-only panel explains each
choice's user and technical impact as you select it, and the options stay ignored
until you tick **"I understand features may degrade based on the control selected."**
A **Hide editor border** toggle is here too. QUILL warns you to restart when you change
these.
**Why it matters:** a safe sandbox for power users and testers to help shape the
editor, with a clear gate so nothing changes by accident.

### Proofread before you publish

- **Proofread Mastodon posts before sending (per account)** — tick it and pressing
  Post opens the F7 Spelling Review on the post text first.
- **Spell check a document before saving** — opens F7 automatically on Save / Save As.

---

## Fixes worth calling out

- **Bookmarks now persist** per document and across sessions (see above), and QUILL
  restores your last cursor position — fixing the old behaviour where bookmarks were
  forgotten on close and shared across documents.
- **Opening Word and other documents with QUILL as the default app works** — pressing
  Enter on a file in your file manager now opens it instead of doing nothing.
- **Far less double-spoken chatter** — actions like "No misspellings found" were
  spoken twice; now exactly once (#728).
- **Report a Bug is keyboard-navigable again** and reliably confirms the report was
  copied (#729).
- **No alarming "text-to-speech failed"** when your screen reader is running; the
  SAPI fallback also initialises correctly under a read-only install (#749).
- **Offline dictation works out of the box** — the engine is fetched on first use
  instead of failing with "whisper binary not found" (#742).
- **Saving a model no longer freezes at 2% and crashes** — download progress is
  throttled so it cannot flood the UI (#748).
- **Spell check finds real misspellings again** — when Hunspell is present its verdict
  is authoritative, instead of a permissive word list waving typos through.
- **The portable build launches and opens documents**, and the **AI Hub opens**
  instead of erroring on a lazy-string.

---

## For testers

- Upgrade path: install over Beta 1 and confirm your settings, keymap, and
  documents carry forward (see `docs/release/upgrade-path-regression-0.8.0.md`).
- Fresh install: see `docs/release/fresh-install-regression-0.8.0.md`.
- Acceptance: `docs/release/user-acceptance-test-plan-0.8.0.md`.
- New this beta to exercise: **Alt+F3** Reveal Codes; **Set/Go To/List Bookmarks**
  then reopen the file; **Tools → Spell Check Language**; **Help → Download Optional
  Components**; **Settings → Experimental**; **Help → About → Golden Quills**.

## Release mechanics (do not announce yet)

Per the active release hold, the repo stays on Beta 1 labels and the update feed
stays where it is. No version bump, tag, push, or feed change until explicitly
approved. See `RELEASE.md` for the tag-time checklist.
