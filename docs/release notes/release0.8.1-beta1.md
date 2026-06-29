# QUILL — Meet You Where You Are

### The screen-reader-first writing studio, built by the people who depend on it. This is the public beta, build 0.8.1 Beta 1.

*From Community Access. Free. Optional by design. Private by default. Yours to make quiet.*

This release document is the narrative companion to the **"0.8.1 Beta 1"**
section of `CHANGELOG.md` (the canonical, append-as-you-go log). It tracks what
changes in 0.8.1 Beta 1 on top of the 0.8.0 line.

---

## What 0.8.1 Beta 1 adds over 0.8.0

This release carries forward everything through 0.8.0 — private on-device speech,
document-to-audiobook production, braille proofreading, talking-book export,
guided proofing, multilingual narration, Mastodon posting, and the upgrade
hardening that makes betas safe to update. Its headline is a complete,
screen-reader-first **AI suite** — optional, private by default, and built around
the provider you choose.

This page is organised by theme, with a heading for every change so you can jump
between them with your screen reader's heading navigation. The big themes are:

- **The AI suite** — a context-aware assistant, transcription that becomes
  finished documents, and reviewable writing help.
- **Rich formatting and faithful documents** — real formatting that stays out of
  your way, and a way to keep it beside a plain-text file.
- **Editing and accessibility** — the Spoken Echo, a far better Keyboard Manager,
  three classic-editor power tools, and quieter, calmer announcements.
- **Braille** — new layout-repair tools for files that will not emboss.
- **Fixes and smaller enhancements** — the rest of what changed.

---

## The AI suite

### Optional, and private by default

This release's headline addition is a complete, screen-reader-first AI suite under
one new top-level **AI** menu. It is **off until you turn it on**, it works with
the provider *you* choose — a private **on-device** model (Ollama) or an account
with **OpenAI, Anthropic (Claude), Google Gemini, or OpenRouter** — and nothing
leaves your machine without your consent. Set it up once and every AI feature
below shares that one connection.

### Set up AI in seconds, the gentle way

A short **AI Setup Wizard** (the first item in the AI menu, "Set Up AI… — start
here") walks you through a single choice — on-device, an AI account, or not now —
with a one-step connect and a Test Connection check. Click any AI action before
you have set things up and QUILL offers the wizard right there instead of failing.
Newcomers can stay in a simpler **Basic** mode with a smaller AI menu; "Show
advanced AI features" reveals the full set whenever you want it.

### Ask Quill — one conversation that knows your document

A single, context-aware chat (**Ask Quill**) replaces the old scattered AI
dialogs. Ask about your text, have it draft or rewrite, and apply suggestions
through a reviewable change preview. **Ask Quill by Voice** adds spoken questions
and spoken answers with transport controls for a hands-light, eyes-free
conversation, and falls back to text and screen-reader announcements when voice is
unavailable.

### The Listening Companion — turn recordings into finished documents

Transcribe an audio or video file (optionally **translating it to English** or
**identifying the speakers**), then let QUILL turn the transcript into something
useful: **Meeting Minutes, Action Items, an Executive Summary, Interview Notes,
Study Notes, Q&A, a Follow-Up Email, Key Quotes, a Decisions Log, or a clean
draft** — picked from one context-aware list. You can run those same **Transcript
Actions** on any open document, build your own with a no-syntax **Action Builder**
(a name, plain-language instructions, and an optional reference document), and even
have a watch-folder transcribe new recordings and produce the document
automatically.

### The AI Library — Prompts, Skills, and Agents in one place

Your reusable AI know-how lives in a single tabbed manager. Save a **Prompt**,
promote it into a multi-step **Skill**, and promote that into a first-class
**Agent** — a real continuum, all reviewable and editable, all running through the
connection you set up once.

### Everyday writing help, always reviewable

Rewrite, summarise, expand, continue, fix grammar, or generate a table of contents
from **Transform Selection**; proofread with **AI spell check** and a
**grammar-and-style check**; **translate** a selection or the whole document; find
richer synonyms with the **AI Thesaurus**; and put questions to your document with
**Document Q&A**. Every change QUILL proposes is shown as an accessible
accept/reject preview and applied as a single, one-step **undo** — nothing is ever
silently rewritten.

### Read aloud and export audio in natural AI voices

Read the selection or the whole document aloud, stop on a key, or **export the
document as an audio file** in your chosen cloud voice — alongside the on-device
speech QUILL already shipped.

### In your control, by design

AI is optional and off by default, provider-neutral, and consent-gated: QUILL
shows you what would be sent before it sends it, keeps a reviewable record of AI
changes you can undo, and never widens its own permissions. Organisations can
restrict which providers are allowed.

---

## Rich formatting and faithful documents

### Hidden codes, spoken on demand

This release lets you apply real document formatting — **bold, italic, underline,
strikethrough, superscript/subscript, font family and point size, text colour and
highlight**, plus paragraph **alignment, line spacing, indent, and named styles**
— without ever seeing markup clutter in your editor. The buffer stays clean, fast,
plain text; the formatting rides along as invisible codes. Apply it from the new
**Format** menu (Font / Size / Align / Colour / Highlight) or the accessible
**Font...** dialog, and ask **"Describe formatting at cursor"** to *hear* exactly
what is in effect ("Arial, 14 point, centred, bold"). An optional setting announces
formatting changes as you move the caret. The plain-text editor, undo, search, and
AI all keep working on the same clean text — nothing about your normal editing
changes.

RTF and Word documents round-trip through this clean buffer and materialise back to
real formatting on export: **Word (.docx)** carries font, size, colour, highlight,
and alignment via a native writer (graceful Pandoc fallback if the optional
`python-docx` extra is absent), and **RTF** and **HTML** export carry the same.
When a target format genuinely cannot hold something, QUILL tells you before you
commit rather than dropping it silently.

### Keep your formatting in a plain-text file — Illuminations

A plain `.txt` has nowhere to store fonts, colours, or alignment, so saving
formatted text as plain text normally loses them. This release introduces the
**Illumination** — named for the decorative layer a scribe paints over a
manuscript: the clean text is the manuscript, and a small companion file,
`yourfile.txt.illumination`, holds the formatting beside it. The `.txt` stays
genuinely plain everywhere else, and reopening it *in QUILL* restores every font,
colour, and alignment exactly. A new **Settings → Editing → Saving formatted text
as plain text** option lets you choose to be asked each time, to always write an
Illumination, or to save plain and drop the formatting. If the `.txt` is edited
elsewhere, QUILL notices the mismatch and opens it plain rather than mis-applying
old formatting; for one self-contained file that keeps everything, save as
Markdown, Word, or RTF.

---

## Editing and accessibility

### Re-read anything QUILL just said — the Spoken Echo

Speech is fleeting: an indent depth, a formatting description, a save result, a "no
matches" — once spoken, it is gone. The **Spoken Echo** captures the last twenty
things QUILL announced and shows them, newest first, in a read-only dialog you can
arrow through, re-read, and copy. Open it any time with **Alt+Shift+E** (Help →
Show Spoken Echo), and it works after *every* announcement, including ones produced
by ordinary editing keys like Tab. For the screen-reader gesture you already know,
**double-pressing** an informational command — Describe Formatting, Document
Summary, Context Help, or Announce Contrast — pops the Echo open instead of
re-speaking; the dedicated key remains the universal path. Toggle the double-press
behaviour with **Settings → Accessibility → Double-press to show the Spoken Echo**.

### A Keyboard Manager that meets you halfway

Customising shortcuts no longer means remembering exact syntax or whether a key is
free. The **Keymap Editor** (Preferences → Keyboard) now searches two ways from a
single box: type part of a command's name to filter, or type a *shortcut* —
`ctrl+alt+m`, `Control + Shift + K`, or a QUILL chord like `quill, s` — and it
tells you precisely which command owns that key, or that it is unassigned and
available. Spelling is forgiving: `control`, `ctrl`, or `ctl`, modifiers in any
order, any case, with macOS `Cmd` kept distinct from `Ctrl`. Don't want to type it?
Choose **Record Keys** and press the combination. Assigning a key that is already
taken names the command that holds it — by its friendly title — and offers to move
the key there for you, rather than silently refusing. And **Run Diagnostics**
audits your whole keymap for duplicate shortcuts, bindings to commands that no
longer exist, unreadable bindings, and keys that are assigned but cannot actually
fire, with a one-click **Heal** that clears the bad entries and re-applies your
shortcuts so menus and keys line up again.

### Three classic-editor power tools for keyboard-first writers

In the tradition of the venerable WordPerfect Editor, three additions with no prior
equivalent in QUILL. All three ship unbound, so assign keys in the Keymap Editor.

- **Repeat Next Command** (Edit menu). Set a count, then the next command runs that
  many times — down twenty lines, delete ten words, insert forty dashes, even
  replay a macro N times — in a single gesture. The count applies once and then
  clears.
- **Restore Deleted Text** (Edit menu). QUILL keeps the last three blocks removed by
  its structured delete commands (delete to line start or end, to document start or
  end, or delete paragraph). Pick one from an accessible list and it is re-inserted
  at the cursor. Unlike Undo — which reverts the last edit in place — Restore Deleted
  Text can drop recovered text anywhere.
- **Describe Character at Cursor** (Tools → Advanced). The screen-reader descendant
  of "Reveal Codes": an accessible dialog, in the same read-only style as F1 help,
  that names the exact character under the caret — its Unicode name, code point
  (hexadecimal and decimal), category, and plain-language notes for the invisibles
  that bite writers (a no-break space, a zero-width space, a smart quote, a tab, a
  line ending).

### Hear how deep your indentation is

Tab / Shift+Tab can now speak the new indentation depth — "4 spaces", "8 spaces",
"1 tab" — instead of "Indented lines", honouring your tabs-vs-spaces and
indent-width settings. Toggle with **Announce indentation depth on Tab** (Settings
→ Accessibility).

### Calmer, quieter announcements

- **Quieter dialogs, your choice.** A new **Announce entering and leaving dialogs**
  setting (Settings → Accessibility) turns off the spoken "Entered / Exited *name*
  dialog" cues for people whose screen reader already announces dialogs.
- **Quieter Read Aloud for screen-reader users.** While Read Aloud played, QUILL
  selected each sentence to follow along — which made your screen reader announce
  the selection over QUILL's chosen voice. This follow-along is now **off by
  default**, so the cursor stays put and only the Read Aloud voice is heard. Turn it
  back on with **Move cursor to follow Read Aloud** (Settings → Read Aloud).

### Jump straight to an open document

With several documents open, press **Alt+1** through **Alt+9** (and **Alt+0** for
the tenth) to go directly to that document by its position, instead of cycling with
Ctrl+Tab. If nothing is open at that position, QUILL tells you and stays put. The
Window menu also lists your open documents with these shortcuts shown beside them,
and the keys are remappable in the Keymap Editor.

---

## Braille

### Repair tools for files that will not emboss

A new **Braille → Repair** submenu brings NLS-style proofreading to QUILL's braille
mode, for the two classic problems: *page width exceeded* (a line over the cell
limit, almost always trailing spaces) and *page depth exceeded* (a page over the
line limit).

- **Read Layout Metrics** speaks the diagnostic numbers in one pass: the cursor's
  cell and current line length, the longest line in the file against your
  cells-per-line limit (with a "page width exceeded" warning), the current and total
  braille pages, and the longest page against your lines-per-page limit (with a
  "page depth exceeded" warning).
- **Go to Longest Line** and **Go to Longest Page** jump the cursor straight to the
  worst offender so you can fix it by hand — for a too-deep page, usually by
  inserting a page break where one is missing.
- **Remove Trailing Spaces on This Line** and **Remove Trailing Spaces in Whole
  File** clear the trailing spaces that cause most page-width problems, preserving
  every line ending and form feed.

The cell and line limits come from your existing **Cells per line** and **Lines per
page** settings (Preferences → Braille), so the diagnostics match the page geometry
you are transcribing for.

---

## Fixes

- **The portable build launches again, and opens documents.** Double-clicking
  `quill.exe` in the portable bundle now starts QUILL (the bundle-root launcher was
  orphaned from its runtime), and setting QUILL as the default app for Word (or
  other) documents now opens the file when you press Enter on it in your file
  manager — previously nothing happened.
- **The AI Hub opens instead of crashing.** Activating the AI Hub on the 0.7.0 line
  failed with a "lazy string" / lazy-loading error; it now opens to the
  provider/authorisation screen. (Community-Access/support #51, #53)
- **Far less double-spoken chatter.** "No misspellings found" was one of many actions
  QUILL spoke twice — once from the status bar (which already speaks) and again from
  a separate announcement. Across updates, GitHub, SSH, dictation, the copy tray, and
  profile switches, these now speak exactly once. (#728)
- **Report a Bug is keyboard-navigable again, and submitting no longer seems to lose
  your text** — you can Tab through the form, and QUILL reliably confirms the report
  was copied to your clipboard on submit for NVDA users. (#729)
- **No alarming "text-to-speech failed" when your screen reader is running.** QUILL's
  own SAPI voice is only a fallback for people with no screen reader; if it failed to
  start, QUILL spoke a scary "TTS engine failed" message (with a wrong "press F8"
  instruction) even though the screen reader was handling speech. That case is now
  logged quietly and not spoken — QUILL only speaks up when you genuinely have no
  other voice, pointing you to the real **Tools → Retry TTS Engine**. The SAPI voice
  also initialises correctly under a read-only install now (its helper cache moved to
  a writable per-user folder), so self-voicing works for those who rely on it.
  Relatedly, the screen-reader detection no longer flashes a brief console window
  that a braille display could announce.
- **A control-type choice for braille displays that start each line in cell two.** On
  a rich-text editor control, some braille displays show every line's first character
  in cell two — the same quirk long-time Word users will recognise. **Preferences →
  Accessibility → Editor control type (braille)** can switch the editor to **Plain
  edit, like Notepad** — a simple control that the rich control was only ever needed
  in place of for *read-only* views (#616), so an editable plain control still reads
  correctly. RichEdit 2.0 is offered as a middle option. The control-type change
  applies to documents opened after it (restart to apply everywhere).
- **Downloading Kokoro voices now shows its progress instead of dropping you back at
  the document.** Starting the Kokoro voice-pack download from Manage Voices appeared
  to do nothing: focus snapped back to the editor and the progress window was never
  announced, because it opened while the Manage Voices dialog was still closing. The
  download now opens after that dialog is fully gone, so the progress window presents
  and your screen reader announces it. Once the Kokoro models are present, the
  redundant 114 MB download button is hidden rather than offered again.

---

## Smaller enhancements

- **Portable installs update to the portable build, not the installer.** Check for
  Updates now recognises when you are running the portable bundle and offers the
  portable **.zip** for that release instead of pushing the Windows installer at you.
  The download lands in your updates folder with an **Open folder** button so you can
  swap it into place; installed copies keep getting the installer exactly as before.

---

## For testers

- Upgrade path: install over Beta 1 and confirm your settings, keymap, and
  documents carry forward (see `docs/release/upgrade-path-regression-0.8.0.md`).
- Fresh install: see `docs/release/fresh-install-regression-0.8.0.md`.
- Acceptance: `docs/release/user-acceptance-test-plan-0.8.0.md`.

## Release mechanics (do not announce yet)

Per the active release hold, the repo stays on Beta 1 labels and the update feed
stays where it is. No version bump, tag, push, or feed change until explicitly
approved. See `RELEASE.md` for the tag-time checklist.
