# QUILL 0.9.0 - The Last Feature Beta: Everything We Promised, By Ear

### The screen-reader-first writing studio, built by the people who depend on it.

*From Community Access. Free. Optional by design. Private by default. Yours to make quiet.*

This is the narrative companion to the **"0.9.0 Beta 1"** section of `CHANGELOG.md`
(the canonical, append-as-you-go log). And it is a milestone: **0.9.0 is the final
feature release before QUILL 1.0.** Every feature this project set out to build is
now in the product. From this beta to 1.0, not one new feature will be added - only
bug fixes, polish, and the steady work of making what exists unbreakable. If
something is rough, tell us and we will fix it. If something is missing, it is
missing on purpose, and 1.0 will ship without it so that what *is* here is
trustworthy.

---

## The story so far - how a text editor became a studio

Every version of QUILL has been an answer to the same question, asked by the people
who use it: *what would a writing tool be like if the screen reader came first, not
last?*

The early betas answered it small and stubborn: a clean editor that spoke plainly,
saved atomically, and never surprised your hands. **0.5** gave the community its
power tools - the Developer Console, GitHub integration, keyboard packs you could
share, sound packs that made the editor musical, and an updater that verified what
it fetched. **0.6** turned QUILL into a platform: the Quillin extension system,
Insert Automation, Braille Mode's first phase, and the first AI writing toolkit -
every piece optional, every piece spoken. **0.7** was named *Meet You Where You
Are* because that was its whole idea: braille translation and embossing matured,
DAISY talking books shipped, and the format list grew until the answer to "can
QUILL open it?" became, usually, yes. **0.8** made it a serious document studio -
rich formatting as invisible codes you could reveal like the WordPerfect of
memory, Illuminations that let plain text keep its formatting, faithful Word and
RTF round trips.

**0.9.0 finishes the promise.** A complete optional AI suite that is silent until
invited. The Accessible Vault - linked notes, backlinks, and search you traverse
by ear, no graph picture required. Story Studio, a binder for a whole book. GLOW,
guided accessibility review and repair, so the person most affected by an
inaccessible document is the one best equipped to fix it. Hey QUILL, hands-free
voice that can never do harm. Document rescue with free on-device OCR. Table
Studio. The Quillin Hub. A 36-episode audio course narrated by QUILL's own
voices. Restore points that remember every save. And a save pipeline that tells
the truth, every time, in words.

None of it was built in a vacuum. It was built out of your bug reports, your
mailing-list threads, your "this almost works" messages, and your patience with
betas. Eight lines from one tester rewrote how saving works. This release is the
community's release, and the rest of these notes tell its story feature by
feature - what each thing is and, just as important, **why it matters** for the
way you actually work.

One law holds throughout: everything new is off, optional, or additive. Nothing
here changes how your fingers already work - it just gives them more to reach for
when you want it.

---

## The AI suite - powerful, and entirely up to you

### It is off until you turn it on

The headline addition is a complete, screen-reader-first AI suite under one new
top-level **AI** menu. It works with the provider *you* choose - a private
**on-device** model (Ollama) or an account with **OpenAI, Anthropic (Claude),
Google Gemini, or OpenRouter** - and nothing leaves your machine without your
consent.
**Why it matters:** AI in QUILL is a tool you pick up, not a thing that happens to
you. Set it up once and every feature shares that one connection; never set it up
and QUILL is exactly the editor it always was.

### Set up in seconds - the AI Setup Wizard

A short wizard ("Set Up AI... - start here") offers one choice - on-device, an
account, or not now - with a one-step connect and a Test Connection check. Click any
AI action before setup and QUILL offers the wizard right there instead of failing. A
**Basic** mode keeps the menu small for newcomers.
**Why it matters:** no dead ends, no jargon wall. You are never punished for trying a
button before you have configured anything.

### Free AI for everyone - a path that meets you where you are

You never have to pay to use QUILL's AI. The wizard now leads with the best **free**
options and picks good defaults for you. **Most private:** run a model on your own
computer with Ollama - no account, works offline, and nothing you write ever leaves
your machine. **Best quality:** connect **OpenRouter** with your own free key and
QUILL preselects a strong free writing model for you. Every provider that needs a key
has a **Get API key** button that opens the right signup page in your browser, so
there is no hunting for where to sign up, and model choices say **Free** out loud
when they cost nothing. Both the wizard and the **AI Hub** now offer a real model
**dropdown** - pick a recommended model or list everything your account or device
offers, instead of typing an id from memory. Everyday writing help and the one-shot
agents (Rewrite, Summarize, Expand, Table of Contents) work well on free models, and
Ask Quill quietly simplifies its steps on a small model so it answers instead of
stalling.
**Why it matters:** flagship models are wonderful, but they should be an *option*,
not a toll gate. If you cannot afford one, QUILL still gives you real, useful AI -
and it is honest about the trade-offs: free cloud models can be slower and are
rate-limited to *your own* quota, so keep anything confidential on the private
on-device option.

### Ask Quill - one conversation that knows your document

A single, context-aware chat replaces the old scattered AI dialogs. Ask about your
text, have it draft or rewrite, and apply suggestions through a **reviewable change
preview** applied as one undo step.
**Why it matters:** nothing is ever silently rewritten. You see the change, you
accept or reject it, and one Undo puts everything back.

### The Listening Companion - recordings become finished documents

Transcribe an audio or video file (optionally translating to English or identifying
speakers), then turn the transcript into **Meeting Minutes, Action Items, an
Executive Summary, Interview or Study Notes, Q&A, a Follow-Up Email, Key Quotes, a
Decisions Log, or a clean draft** - from one context-aware list. Build your own with
the no-syntax **Action Builder**, or let a watch-folder do it automatically.
**Why it matters:** the gap between "I recorded it" and "I have the document" closes
to a couple of keystrokes.

### The AI Library - Prompts, Skills, and Agents in one place

A tabbed manager with a real promotion path: a **Prompt** graduates into a multi-step
**Skill**, and a Skill into a first-class **Agent** - all reviewable, all running
through the connection you set up once.
**Why it matters:** your reusable know-how grows with you instead of scattering
across dialogs.

### Everyday writing help, always reviewable

Rewrite, summarise, expand, continue, fix grammar, or generate a table of contents;
AI spell check and grammar-and-style check; translate a selection or document; the
AI Thesaurus; and Document Q&A. Read the selection or document aloud, or export it as
audio in a natural cloud voice, alongside QUILL's on-device speech - and new this
beta, **ElevenLabs** joins the Read Aloud voice list: bring your own key, pick an
ElevenLabs voice like any other, and QUILL synthesizes sentence by sentence with
smart caching so repeated text is never re-billed. Consent is per session, and like
every cloud voice it is optional beside the always-free on-device engines.
**Why it matters:** every proposed change is an accessible accept/reject preview and
a single undo step - help you can trust, not magic you have to babysit.

### Bring the AI agent you already use

QUILL's agent can run on more than one engine. Already pay for **GitHub
Copilot**? Use that subscription directly - a short spoken device code in your
browser signs you in, no API key at all, running on your plan's models. Prefer
the **Claude Agent** or **OpenAI Agents** engines? They plug in with the
Anthropic or OpenAI API key you already have - no separate QUILL charge, ever.
On the **AI Hub > Engines** tab (or by choosing *"Use an AI agent you already
pay for"* in the Setup Wizard), pick your engine; QUILL installs the small
connector on demand and walks you through the sign-in out loud. Prefer QUILL's
built-in agent? The **Native** engine is always there, on whatever provider you
connected.

**Why it matters:** the smartest agent you have access to is often the one you are
already paying for. And the safety never changes: whichever engine runs, QUILL owns
every edit - the agent proposes, you approve a preview, one keystroke undoes it, and
the vendor agents run text-only so they can think but never touch your document on
their own. Optional, off by default, off in Safe Mode.

---

## Rich formatting that stays out of your way

### Hidden codes, spoken on demand

Apply real document formatting - **bold, italic, underline, strikethrough,
super/subscript, font family and point size, colour and highlight**, plus paragraph
**alignment, line spacing, indent, and named styles** - without ever seeing markup
clutter. The buffer stays clean, fast, plain text; the formatting rides along as
invisible codes. Ask **"Describe formatting at cursor"** to *hear* exactly what is in
effect ("Arial, 14 point, centred, bold").
**Why it matters:** you get real formatting and a clean editing experience - you no
longer have to choose between the two.

### Keep your formatting in a plain-text file - Illuminations

A plain `.txt` cannot hold fonts or colours, so saving formatted text as plain text
used to lose them. Now QUILL can write an **Illumination**: a small companion file
(`yourfile.txt.illumination`) that stores the formatting beside the clean text. The
`.txt` stays genuinely plain everywhere else; reopening it *in QUILL* restores every
font, colour, and alignment exactly.
**Why it matters:** your text stays portable and plain, and your formatting still
survives - no lock-in, no surprise loss.

### Faithful round-trips

RTF and Word documents round-trip through the clean buffer and materialise back to
real formatting on export. **Word (.docx)**, **RTF**, and **HTML** carry font, size,
colour, highlight, and alignment; when a format genuinely cannot hold something,
QUILL tells you *before* you commit.
**Why it matters:** you hand documents back looking the way they came in, and you are
never silently stripped of work.

---

## Editing and accessibility - the power tools people missed

### Reveal Codes - see and hear every hidden code (Alt+F3)

The beloved WordPerfect feature, reimagined screen-reader-first. Press **Alt+F3** (or
**View > Reveal Codes**) to open a pane showing your document as a stream of bracketed
codes and text - `[Bold On]`, `[Font: Arial]`, `[Center]`, `[Tab]`, `[Hard Return]`,
`[No-Break Space]`. **F6** moves between the editor, the Reveal Codes pane, and the
status bar (**Shift+F6** back), and the two carets stay in sync. Every code is an
individually-announced, navigable item; jump from a `[Bold On]` to its matching
`[Bold Off]` and hear its reach. Choose a **Structured** list or a **Flowed** view,
with quiet / balanced / detailed verbosity.
**Why it matters:** nothing about your document is hidden from you. The clean editor
stays clean; the truth is one keystroke away.

### Bookmarks that remember - per document, across sessions

Named bookmarks now belong to the **specific file** you set them in and **persist
between sessions**, so reopening a document brings its jump points back. QUILL also
remembers your **last cursor position** in each saved document and returns you there
when you reopen it.
**Why it matters:** close a long document on Friday, reopen it Monday, and you are
right where you left off - with every named landmark intact. (Set Bookmark, Go To
Bookmark, List Bookmarks; List Bookmarks is on Alt+Shift+B.)

### Inline notes - sticky comments that stay with your content

Jot a private note about the current line or selection with **Alt+Shift+I**. The
note is **anchored to the text**, so it follows that content as you edit and comes
back when you reopen the document (per document, like bookmarks). **Alt+Shift+J** /
**Alt+Shift+G** move to the next / previous note (the cursor jumps to the noted text
and QUILL reads the note); **Alt+Shift+H** speaks the note at the cursor, and pressing
it again quickly opens it to view, edit, or delete.
**Why it matters:** the running commentary, queries, and reminders you keep while
drafting finally live *with the words they are about* - surviving edits and reloads -
instead of in a separate file you have to keep in sync. If the noted text is deleted,
the note is kept rather than silently lost.

### Three classic-editor power tools

In the WordPerfect Editor tradition, all unbound by default (assign keys in the
Keymap Editor):
- **Repeat Next Command** - set a count, and the next command runs that many times
  (down twenty lines, delete ten words, insert forty dashes) in one gesture.
- **Restore Deleted Text** - QUILL keeps the last three blocks removed by its
  structured delete commands; re-insert any of them at the cursor (distinct from Undo,
  which only reverts in place).
- **Describe Character at Cursor** - names the exact character under the caret (Unicode
  name, code point, category, and notes for invisibles), the screen-reader descendant
  of "Reveal Codes".
**Why it matters:** the precise, repeatable, eyes-free moves that long-time editor
users have been asking QUILL to bring forward.

### Re-read anything QUILL just said - the Spoken Echo

The last twenty announcements are kept and shown newest-first in a read-only dialog
you can arrow through, re-read, and copy (**Alt+Shift+E**). Double-pressing an
informational command opens the Echo instead of re-speaking.
**Why it matters:** speech disappears the instant it is spoken; now you can get it
back.

### A far richer Keyboard Manager

The Keymap Editor searches two ways from one box - type part of a command name to
filter, or type a shortcut to reverse-look-up exactly which command owns it. **Record
Keys** lets you press a combination instead of typing it; assigning a taken key names
the command that holds it and offers to reassign; **Run Diagnostics** audits the whole
keymap and heals duplicate, orphaned, or inert bindings.
**Why it matters:** customising shortcuts no longer means remembering exact syntax or
guessing whether a key is free.

### Quieter, calmer, and quicker to move

- **Hear how deep your indentation is** - Tab / Shift+Tab can speak "4 spaces",
  "1 tab", instead of just "Indented lines".
- **Quieter dialogs by default** - the spoken "Entered / Exited *name* dialog"
  cues are now **off by default**, because every supported screen reader already
  announces a dialog and reads its title on focus, so the extra cue was just
  noise. Want them back? **Preferences > Accessibility > Announce entering and
  leaving dialogs**. Existing users who never deliberately switched them on pick
  up the quieter default automatically on upgrade.
- **Jump straight to an open document** - **Alt+1**...**Alt+9** (and **Alt+0** for the
  tenth) go directly to that document instead of cycling.
- **Quieter Read Aloud** - the follow-along selection is now off by default, so only
  the Read Aloud voice is heard, not "...selected" over it.
**Why it matters:** less chatter, fewer keystrokes, more signal.

---

## Story Studio - organize a whole book

### The binder: your project, one keystroke away

**Tools > Story Studio...** opens a keyboard-navigable **binder** for a project
folder. Your **Manuscript** appears with its parts, chapters, and scenes taken
straight from the Markdown headings you already write, alongside groups for
**Characters, Places, Plot threads, Research, and Brainstorm**. Arrow through the
tree; press Enter on any item to open that file - a chapter opens at its heading,
an element opens its notes.
**Why it matters:** a novel is more than one long file. Story Studio gives a
blind writer the same "see the whole book at a glance" a sighted writer gets from
a corkboard - as a tree a screen reader reads naturally, with no visual board.

### Character sheets and plot threads - a form, not a syntax

Select an element and choose **Edit details...** to fill in a small, accessible
form: a character's **Role, Goal, Motivation, and Arc**; a plot thread's
**Status**; **tags**. Your answers are saved as tidy front matter at the top of
the element's file, so editing the form and editing the file are the same bytes.
Blank fields are dropped, and anything already in the file that Story Studio does
not recognise is kept untouched.
**Why it matters:** structure without a database and without learning any markup
 - and your notes stay in plain, portable text you own.

### Compile the manuscript, then export it your way

Press **Compile manuscript...** and Story Studio stitches every manuscript file
together, in order, into a new document. From there the ordinary **File >
Export** takes over - Markdown, HTML, Word, DAISY, and more - because the compiled
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

## Accessible Vault - linked notes, backlinks, and no picture required

### Type [[a link]], follow it by ear

Linked notes are simply a folder of plain-text notes that point at one another.
The usual way to see those connections is a visual graph of dots and lines: a
wall of pixels a screen reader cannot climb. QUILL keeps the linking and drops
the wall. **Tools > Vault > Open Vault...** points QUILL at a folder of notes; it
indexes them and announces "Vault *name*: 312 notes, 480 links." Type
`[[Note Title]]` anywhere, put your cursor on it, and **Follow Wikilink** opens
that note, at the exact heading or block if you linked one. Link to a note that
does not exist yet and QUILL offers to **create** it on the spot; link to a name
two notes share and QUILL **asks which**, never guesses.
**Why it matters:** note-to-note links, the connective tissue of a real knowledge
base, now work in QUILL, and they work the way a keyboard-and-speech user actually
moves.

### The graph, spoken: Backlinks

**Show Backlinks** answers "what links here?" as a list you can hear: "5 notes
link here," each entry read with the sentence its link sits in, Enter to open the
source right at that mention. That list *is* the graph view - and for a
screen-reader user it is far more useful than a picture ever was.
**Why it matters:** you traverse the web of your notes forwards (follow a link)
and backwards (open a backlink) entirely by keyboard and ear.

### Find any note, find any word

**Go to Note** is a jump box: start typing part of a title and the list narrows
as you go, QUILL speaking the count ("7 matches"); press Enter to open the closest
one. **Search Vault** goes wider - type a word or phrase and hear how many results
turned up, each read as its note, line number, and the sentence it appears in;
flip on **Regex** for patterns or **Whole word** to skip partial hits, and Enter
opens a result at its exact line.
**Why it matters:** in a folder of hundreds of notes, the thing you want is one
short phrase and one keypress away - no scrolling, no squinting.

### Tags that gather your notes

**Show Tags** is a spoken tag pane. Filter your `#tags` - each with a count of how
many notes wear it - open one, and hear the notes that carry it. Nested tags roll
up, so `#area` gathers everything under `#area/sub` too.
**Why it matters:** the same "show me everything about X" that sighted users get
from clicking a tag, delivered as a list you can hear and act on.

### Embeds: pull one note into another

Write `![[Other Note]]` (or `![[Note#Heading]]`, or `![[Note#^block]]`) and QUILL
can pull that content in. **Speak Embed at Cursor** reads what the embed points to
without touching your text; **Resolve Embed Inline** drops the real content in
place as a single change you can undo.
**Why it matters:** reuse a definition, a boilerplate, or a shared section across
notes - and hear exactly what it resolves to before you commit.

### Templates and a daily journal

**Insert Template** picks from a `Templates` folder in your vault, fills in
`{{date}}`, `{{time}}`, and `{{title}}`, asks you any `{{prompt:Question}}` it
finds - spoken, one at a time - and leaves your cursor exactly where you marked
`{{cursor}}`. **Open Today's Note** opens (or creates) today's dated note, and
**Previous / Next Daily Note** step through the days.
**Why it matters:** the friction of "start a new note the same way every time"
disappears, and a daily journal is one command away.

### Turn your vault into a website

**Export Vault as Website** writes a small, self-contained site: one accessible
page per note, your `[[links]]` turned into real links between the pages, your
`![[embeds]]` filled in, and an index page listing everything. It runs in the
background and tells you how many pages it wrote. If your vault folder is a Git
repository, **Sync Vault** commits, pulls, and pushes over your own remote - and
if the same note changed in two places, it lists the conflicts and stops rather
than overwriting a word.
**Why it matters:** your notes can leave the app as a shareable, navigable site,
and stay backed up and in sync across your machines - on infrastructure you own.

### Plain text, yours forever

A vault is an ordinary folder of Markdown files plus one small `.quill` cache you
can delete without losing a word. Links live as plain `[[text]]` in your files -
nothing hidden - so every note opens in any editor. It is entirely optional: never
open a vault and QUILL is the editor it always was.

---

## The Quillin Hub - share what you make

QUILL has always been extendable - Quillin extensions, sound packs, keyboard
packs, verbosity packs, AI skill packs, pronunciation dictionaries. This beta
gives all of it a home: **the Quillin Hub** (`hub.quillforall.org`), the
community store and submission service for every shareable QUILL artifact.

**Submitting is validated before it is public.** **Tools > Quillins > Submit to
Quillin Hub...** runs the full artifact validator locally and reads you the
verdict in an accessible dialog *before* anything goes near the network - pick a
Quillin's manifest and the whole folder is checked. Every published artifact is
**cryptographically signed**: the Hub fails closed on unsigned submissions, the
storefront shows a spoken "Signed by" badge on everything, and the in-app
submission dialog and Quillin Manager both tell you the signature state of what
you are submitting or have installed.

**Why it matters:** the people who customize QUILL best are the people who use
it. The Hub turns "I made this for myself" into "everyone can have this" - with
the same validation, the same signing, and the same spoken clarity whether the
author is the QUILL team or you.

---

## Learn QUILL by ear - The QUILL Cast and new tutorials

QUILL's documentation now teaches in three registers. The user guide remains
the full reference. A new **tutorials** collection (docs/tutorials) walks six
complete workflows hands-on - your first hour, keyboard mastery, rescuing a
scanned PDF, building an audiobook, starting a Vault, and shipping an
accessible document with GLOW. When the Audio Studio landed during the
beta, tutorial 4 was rebuilt around it - voices and Read Aloud, then all
three Studio journeys through to a published podcast feed - and QUILL Cast
**episode 24 was re-recorded as "The Audio Studio"** so the audio course
teaches the same workshop your menus have.

And then there is **The QUILL Cast**: a full **36-episode, two-host audio
course** - about two and a quarter hours across seven parts - that leads a
brand-new user from the installer all the way to every feature family in the
product. Part one covers first steps (install, files, the command palette,
what QUILL says); the everyday-editor part makes you fast; then documents
and formats, files and automation, the speech suite, AI, and finally the
organization, production, and trust features - the Vault, Story Studio,
GLOW, braille production, and extensions. Every episode builds on the one
before it and ends with five minutes of hands-on homework.

The hosts, Liam and Jessica, are QUILL's own on-device **Kokoro** neural
voices - the product literally narrates its own curriculum, produced with
the same speech engine you can install from the Voice Picker. Every episode
ships with a full accessible transcript on the website, and an RSS feed lets
you subscribe in any podcast app.

**Why it matters:** some people learn by reading, some by doing, some by
listening on a walk. Now all three of them get a first-class path into QUILL
- and the audio path is proof-by-existence of what the speech suite can do.

---

## Import / Convert Document - rescue for locked-away documents

Everyone with a screen reader knows the feeling: someone hands you a PDF and
it turns out to be a photograph of a page. Nothing to read, nothing to search,
nothing to fix. This beta ships QUILL's answer - a supported document-rescue
tool with one rule: **free first, local first, and nothing is ever uploaded.**

### How it works

**File > Import > Import / Convert Document (OCR)...** takes almost anything -
Word, PowerPoint, Excel, HTML, EPUB, PDFs, images - and routes it through free,
on-device services:

1. **The free local converter runs first.** Born-digital files and PDFs with a
   real text layer convert instantly into clean, editable text. No account, no
   key, no cost.
2. **Scanned documents are detected, not dumped.** When a PDF comes back nearly
   empty, QUILL says what it found - "it looks scanned or image-based" - and
   *asks* whether to run free on-device OCR. You choose; QUILL never opens a
   blank result silently and never runs OCR behind your back.
3. **On-device OCR rescues the scan.** The local Tesseract engine reads each
   page on your own computer (CPU-only, works offline), keeps page boundaries
   as searchable markers, announces progress page by page, and - honestly -
   tells you when recognition confidence is low so you know to review the
   result rather than trust it blindly.

### A one-time, verified download

The OCR engine is not bundled; it is a free ~48 MB download from
**Tools > Reading & Dictation > Install Local OCR Engine (Tesseract)...**.
QUILL fetches the official installer from its own pinned release, verifies it
byte-for-byte, and opens it for you to complete - never a silent install. If
Tesseract is already on your machine, QUILL just finds it.

### The cloud escalation - for the documents nothing local can rescue

Some documents defeat even good on-device OCR: dense tables, filled forms,
handwriting, brutal photocopies. For those, QUILL now supports an optional
**Datalab Chandra cloud OCR service** - and the way it is wired says
everything about the product's values. It is strictly **free-first**: the
cloud is offered only after on-device OCR comes back weak, never as the first
stop. It is **consent-gated on every single upload**: a dialog names the
service, reminds you to think about private, medical, legal, and financial
content, and notes that the provider deletes results from its servers about
an hour after processing. A filename that suggests sensitive content (tax,
medical, legal, and similar) earns an extra CAUTION line - judged from the
name alone; QUILL never peeks at content to decide. And it is
**bring-your-own-key**: your Datalab key lives in the Windows credential
vault, never in a settings file, and billing is between you and the provider.
There is deliberately no "don't ask again."

### The Services tab - service management for humans

**AI Hub > Services** (or **OCR Service Settings...** straight from the OCR
submenu) manages it all in plain language: a live status line, the enable
switch, your key, default mode and output, a **Test Connection** that checks
your key and endpoint while explicitly uploading no document, a **Copy
Service Summary** that produces a secret-free description for support
requests, and one-press links to the provider's website, key page, pricing,
privacy documentation, and supported file types - each announcing that it
opens in your browser.

### Review exactly what needs reviewing

**Review Last OCR Result...** turns proofreading OCR output from a chore into
a checklist: the most recent conversion's source, service, page count, and
confidence, followed by every low-confidence line as "Page N: [confidence]
text". Arrow through the flagged lines, search the converted document for the
page marker, fix, done. And **Delete OCR Temporary Files** clears any
crash leftovers, announcing exactly what was removed. The whole workflow now
lives in one place: **Tools > Reading & Dictation > OCR and Document
Conversion**.

### Plain-language services page

**OCR and Conversion Services...** describes every service the way a person
would: the free local converter, the free local OCR engine, and the optional
cloud escalation - what each does, what it is best at, whether it is local or
cloud, what it costs, and each one's current status.

**Why it matters:** the documents most likely to be inaccessible - scans,
photocopies, image PDFs - are exactly the ones other tools quietly give up on.
QUILL turns them into text you can read, search, and edit - on your machine by
default, in the cloud only when a hard document genuinely needs it and you
have said yes, out loud, that one time.

---

## Hey QUILL - talk to your editor, hands-free

This release brings **Hey QUILL**, a complete voice-interaction experience that
lets you drive QUILL by speaking - entirely on your own device, with nothing
uploaded. It grows with you across four levels, so you can use as much or as
little as you like, and one promise holds at every level: **a misheard phrase
can never do harm.** Voice can only run a curated, non-destructive allowlist of
commands - the same one the AI agent is held to - so closing without saving,
sending, publishing, and deleting are simply not in its vocabulary. Everything
is off by default, off in Safe Mode, and abortable with "cancel" or "never
mind".

**1. Speak a single command.** **Tools > Speech > Voice Command (Offline)** is
push-to-talk: run it, say one command - "save file", "word count", "next
heading", "read aloud" - and QUILL recognizes it on-device and acts.

**2. Hold a conversation.** **Voice Conversation Mode** keeps listening after
each command through a short follow-up window, so you can chain "next heading",
then "read aloud", then "word count" without re-arming. Because a hands-free
loop should never leave you guessing, every state has a warm, musical cue drawn
from a proven accessible design: a rising chime when it turns on, a soft
two-note when the mic opens, a gentle rise when your command is recognized
(with a brief beat to say "cancel"), a sparkle when the action finishes, a
quiet tick while QUILL works, and a calm fall if nothing matched. The nine cues
are real **Sound Events** you can retune or replace in any sound pack, and your
turn ends naturally **when you stop speaking** (QUILL listens to the
microphone's energy, and calibrates to your room so a noisy mic is not mistaken
for endless talking). You can give QUILL **your name** for warmer prompts
("Listening, Jeff."), optionally have prompts **spoken aloud** (kept silent
whenever a screen reader is running, so QUILL never talks over it), and tune the
pause, cancel, follow-up, and tick timings to your own rhythm.

**3. Just say "Hey QUILL".** **Listen for Hey QUILL** turns on
always-listening: QUILL listens continuously, on-device, for the wake phrase.
Say "Hey QUILL, save file" to run a command outright, or just "Hey QUILL" to
start one. A live microphone is never a surprise - the status bar shows it is
on, a gentle reminder plays now and then, and a new **Speak Voice Status**
command tells you exactly what voice is doing at any moment. Running the command
again (or saying "stop") ends it instantly, and it turns itself off when QUILL
closes unless you deliberately choose to keep it listening across restarts.

**4. Ask a question.** When what you say is a question rather than a command -
"ask what a heading is", or "how do I save my document" - QUILL hands it to Ask
Quill with the question pre-filled and ready. You press Enter to send, so a
person is always in the loop for anything that reaches the AI; voice never
contacts a network service on its own.

**Choose your engine.** Voice runs on an on-device speech engine, and you can
pick which under **Settings > Voice recognition engine**: **whisper.cpp** for
accuracy, or **Vosk** for a fast, light engine that is ideal for the
always-listening wake word - with automatic fallback to your main engine if the
chosen one has no model installed.

For the complete picture - every mode, the full list of spoken commands, the
audio cues, and the privacy rules - see the new **Voice Interaction** page in
the user guide.

## QUILL parla italiano - the first community translation

QUILL's whole interface now speaks **Italian**: menus, dialogs, and spoken
messages, contributed by **Elena Brescacin** (`elettrona`) - the project's
first shipped display language beyond English, arriving during the beta
window exactly the way we hoped the translation pipeline would work: a
community member, a `.po` file, and the CI quality gates. Elena covered
100% of the catalog as it stood; the Audio Studio's arrival then grew the
catalog, the refreshed template is already committed for her to continue,
and anything not yet translated simply falls back to English. Switch under **Tools > Writing and Language > Change
Display Language**; QUILL applies it to spoken messages immediately and to
every menu after a restart. Grazie mille, Elena. (Your language next? The
user guide's translation chapter has the whole recipe.)

## Read Aloud in your language - not just English

The voice lists are no longer English-only, and the change reaches every
engine at once:

- **Windows voices, unfiltered.** The Windows engine now shows **every voice
  installed on your PC, in any language**. Add Italian, Spanish, French,
  German - anything - in Windows Settings > Time & language > Speech, and it
  appears in QUILL immediately.
- **Kokoro speaks five more languages.** The offline neural engine gains
  **Spanish, French, Hindi, Italian, and Brazilian Portuguese** voices - and
  they live in the same voice pack you already downloaded, so there is nothing
  new to fetch.
- **Piper adds Italian.** The catalog gains **Paola** and **Riccardo** as
  one-click, checksum-verified downloads.
- **eSpeak NG** offers the same languages from its built-in data, fully
  offline, as it always could - now surfaced properly.

Read Aloud, audiobook export, and batch speech all honor the chosen voice's
language, end to end.

**Why it matters:** a screen-reader user's world is not monolingual, and
neither is their reading. Whether it is a note from a relative, coursework, or
a novel, QUILL now reads it in a voice that belongs to the language - on
device, for free.

## The Audio Studio - your books, by ear, start to finish

0.9.0 promised that the whole product family would come home to QUILL, and
this is the homecoming's final chapter: **ChapterForge**, the last of the
three sibling apps, now lives on inside QUILL as the **Audio Studio** -
rebuilt from the ground up, screen-reader-first. It arrives during the beta
window as the completion of that promise, and it turns the speech tools you
already had into a complete audiobook and podcast production line.

### One door, three journeys

**Tools > Speech > Audio Studio** replaces the old Batch Export to Speech
Audio dialog - a single screen with some forty controls - with a guided
wizard that asks one thing at a time and speaks every step ("Step 2 of 7:
What should I read?"). Nothing was lost in the move: every option from the
classic dialog survives, from the chapter transition sounder and its volume
to round-robin voices, translated editions, dry runs, and per-folder
remembered settings. Your keyboard binding still works, and a repeat run on
a remembered folder is three keystrokes with **Skip to summary**.

The first page asks what you want to make, and the wizard reshapes itself:

- **Narrate documents into an audiobook or speech audio.** Word, Markdown,
  HTML, or text files, read by any QUILL voice - offline or cloud - one
  chapter per document or heading, optionally assembled into a single
  chaptered book with tags and a cover.
- **Combine audio files into one chaptered audiobook.** A folder of
  recordings becomes one master - MP3 with ID3 chapters or a true M4B -
  one chapter per file, natural order, titles from the filenames, and you
  always review the chapter list before the merge.
- **Edit an existing audiobook.** A finished MP3 or M4B opens in the
  Chapter Workbench, described next. A file with no chapters at all opens
  as one chapter, ready to carve.

### The Chapter Workbench - fix a book by ear

The Workbench is the heart of the feature: a chapter list that reads each
row in full ("3. The Long Road - starts 1:02:03, runs 12:40"), a built-in
**chapter-aware player** (Play/Pause, previous/next chapter, rewind/forward,
a position slider that speaks minutes and seconds, playback speed from 0.75x
to 2x with pitch preserved), and the surgery that was never possible by ear
before:

- **Split at playhead.** Listen for where the chapter should begin, pause
  there, press the button. The boundary lands exactly under your ear.
- **Set start to playhead** retimes an existing boundary the same way;
  **Merge into previous**, **Rename**, and **Restore original** round out
  the set.
- **Where am I?** answers with the full audible glance: chapter number and
  name, time into the chapter and left in it, position and time remaining
  in the whole book.
- The player **remembers where you stopped** in every book and resumes
  there next time.
- Chapter lists **import and export** in five formats - Audacity labels,
  plain timestamps, CUE sheets, Podcasting 2.0 JSON, and CSV (any
  spreadsheet with a Title column can name your chapters).
- **Split into files** goes the other way: one audio file per chapter,
  named and numbered - instant podcast episodes.

Saving is honest about physics: an MP3 saves its edits **in place** (only
the tags are rewritten; the audio bytes are untouched) and an M4B saves as
a new file through a **lossless re-mux** - no re-encode, no quality loss.

### Builds you can trust

Before a long build, the Studio runs a **pre-flight check** - files whose
sample rate, channels, or format differ are named in the log, file by file -
and states the estimated duration and size. After the build it **re-reads
the finished book and verifies** what a player will actually see: the
completion message says "verified 24 chapters," not just "done." Every book
gets two companions written next to it: a plain-text **chapter report** and
a **Podcasting 2.0 chapters.json** sidecar. An **audition** option converts
just the first document so you can judge the voice, pace, and loudness in
minutes before an overnight run, and **spoken opening and closing credits**
("My Book. Written by Jane Doe. Narrated by Sam Reader.") can be synthesized
in the run's own voice as the first and last chapters.

### Publish what you made

The Workbench's **Publish** button offers three explicit, consent-first
paths. **Podcast feed:** a complete RSS 2.0 file with iTunes and Podcasting
2.0 tags, written next to the book, generated entirely offline. And beyond
the single book, **Folder feed (all episodes)** runs a whole show from one
folder: every master becomes an episode with its own title, description
(edited in an accessible episode list), true publication date, duration,
and chapter link; the show settings persist in the folder so one button
regenerates the complete feed after every build, and a companion
**show-notes.html** page - headings per episode, descriptions, chapter
lists - is written on demand, ready to upload beside the feed. **SFTP
upload:** saved destinations send the book and its companions through
QUILL's own SSH machinery - the strict host-key policy applies, and
passwords live in the Windows Credential Manager, never in a settings file.
**Auphonic:** send the book to your own Auphonic account for professional
post-production; QUILL uploads, waits, and downloads the results beside the
book, with your API token in the credential vault. Check the account first
and QUILL speaks your remaining credits and loads your saved presets into a
picker, so the confirmation names the exact preset and balance before a
byte moves; the token is also manageable centrally in **AI Hub > Services**. Every network path is
inventoried in the egress audit, QUILL asks before the first contact with
any service, and the whole dialog is absent in Safe Mode.

Both transfer paths are monitored, abortable operations: a progress dialog
speaks whole-percent steps as bytes actually move ("Uploading book.m4b:
42%"), mirrors them to the status bar, and carries a real **Cancel** button.
Cancelling an SFTP upload stops mid-file (files already completed stay on
the server, and QUILL says so); cancelling an Auphonic run before the
upload finishes means no production starts, while cancelling later leaves
the production running in your account and skips the download - each
outcome announced in those words.

### Small kindnesses that add up

- **Maximum-file-size filter.** A **Skip files larger than (MB)** spinner now lives on the *What should I read?* step of the wizard. Discovery honors the cap (a folder with one accidental 400 MB export no longer hijacks an overnight run), and the live document count on the same step reflects the cap as you change it — press **Count documents** to hear the settled count announced.
- **Polish controls run during the build.** The audio source page's **Trim silences from each recording** and the book page's **fade-in / fade-out / tempo** controls now actually run during the audiobook build. `core/speech/audiobook.build_audiobook` runs every chapter file through `audio_edit.prepare_chapter_files` (head/tail silence trim, fades, pitch-preserving tempo) before ffmpeg concatenates them into the master. Staged files live in the build's temp directory, your source audio is never overwritten, and a polish failure on one file keeps the build going with that file's previous form. Defaults (no trim, `0` ms fades, `1.0` tempo) keep existing builds byte-identical.
- **Silence auto-chapter and ACX check in the Workbench.** The Chapter Workbench grows two long-running analysis buttons. **Propose chapters from silences...** scans the recording with ffmpeg `silencedetect` (noise threshold and minimum silence length tunable) and proposes chapter boundaries at the silence midpoints; the proposal lands in the chapter list for review and is never applied blind, with **Restore original** to undo. **Check against ACX** runs a loudnorm measurement and shows a verdict dialog with integrated loudness, true peak, and noise floor, plus a speakable recommendation for each failing criterion. The verdict is announced when the measurement finishes, regardless of how the dialog is dismissed.
- **UIA regression coverage for the new dialogs.** The nightly `tests/uia` suite (CI-only, never on a developer's desktop) walks the Audio Studio wizard page by page, asserts each page's "Step N of M" announcement lands in the spoken trace, opens the Chapter Workbench on a seeded corpus chaptered MP3 from the edit journey, and drives the silence-proposal parameters dialog from the Workbench. Regressions in focus order, modal-id wiring, or screen-reader announcements are caught by the robot overnight instead of by a user's ears after release.
- **Audio Studio keymap and cross-link.** `Tools > Speech > Audio Studio` is in the command palette under its display name and ships with a default key binding (`Ctrl+Shift+Grave, Y`). The **Export to Translated Speech Audio** dialog grows an "Open in Audio Studio" button that closes the dialog and opens the wizard with the document pre-filled, so the one-shot translation flow advertises the richer chaptered path.
- **Recent folders, recent books, and a remembered journey.** The Audio Studio's source pages (documents and audio journeys) show a combo of the most-recently-used folders; the **edit** journey's file picker remembers the most recently opened audiobooks. The wizard's first page also remembers which journey you used last (documents / audio / edit) and pre-selects that radio, so "Skip to summary" stays a 3-keystroke promise across sessions.
- **Persisted book_credits and library_mode in the project profile.** The Phase 4-6 wizard flags are now part of `speech-project.json` (profile schema v2; v1 files load with both fields defaulting to `False`). A folder that always wants spoken credits and library-mode builds lands on those toggles on the second run without a single click.
- **Job files.** Save a `.quilljob` from the summary page and the entire
  run - folder, voices, chapters, mastering, book details - is pinned in a
  small, hand-editable file. Load it on the Studio's first page and
  everything comes back.
- **Look up book details.** Type a title, press one button, and Open
  Library and MusicBrainz - free, keyless public catalogs - fill in the
  author, genre, and year from the match you choose. Only the title and
  author you typed are ever sent. And when the match has a jacket image,
  QUILL offers to download it as `cover.jpg` next to your audio and use
  it for the book - the book page completes itself from a title you
  half-remember, cover included.
- **An optional mpv playback engine, one download away.** Fetch the **mpv
  player engine** from Help > Download Optional Components (about 44 MB,
  pinned and checksum-verified, with its licenses and a source offer inside
  the download) and the Studio's player switches to libmpv - gapless audio,
  exact seeking, instant chapter jumps on 8-hour books - falling back to
  the built-in Windows engine automatically whenever mpv is absent or
  unusable. Power users can also drop their own `libmpv-2.dll` into
  `engine-packs\mpv` or point `QUILL_LIBMPV` at one.
- **AI chapter titles.** The Workbench's **Propose AI titles** listens to
  the opening minute of each chapter - transcribed on your machine by the
  local speech model, with only the text going to your configured AI - and
  proposes a short title per chapter, in the list, for review. A folder of
  track files becomes a navigable book without typing thirteen titles.
- **Voice casting.** Casting rules on the voice page assign a voice to
  matching chapters - by title glob (`Chapter *`, `*interview*`) or number
  (`#1`) - with the first match winning and everything else falling through
  to the rotation. Multi-voice productions get deliberate casting instead
  of a blind rotation.
- **Incremental rebuilds.** The Studio fingerprints every document it
  narrates - the text plus every setting that shapes its audio - and on
  the next run reuses the audio of anything unchanged instead of
  re-synthesizing it. Editing one chapter of a forty-document book now
  costs minutes, not the overnight run; changing the voice or any audio
  setting rebuilds everything automatically. On by default, with a
  checkbox on the output step to force a full rebuild.
- **Library mode.** Point the combine-audio journey at a folder of book
  folders and every subfolder builds as its own audiobook, unattended,
  each titled after its folder.
- **A watch action.** "Build audiobook from the folder" keeps a drop
  folder alive: new recordings trigger a rebuild of that folder's master -
  a batch of files causes one rebuild, not many.

**Why it matters:** audiobook and podcast production has always assumed a
sighted engineer with a waveform on a screen. The Audio Studio assumes the
opposite - that the person at the keyboard works by ear - and gives them
the entire pipeline: narrate, bind, listen, fix the chapters where their
ear says so, verify honestly, and publish. This one, more than most, was
built to be judged by listening - so listen hard, and tell us what you hear.

## Math in QUILL - equations that render, sound out, and travel to Word

The bundled Math Equations Quillin has always let you type `\(E=mc^2\)` at
the caret; what happened to it after that was the gap. Nothing rendered it,
nothing spoke it structurally, and Word never saw a real equation. That gap
closes this beta.

### Type it, or just pick it

**Ctrl+Shift+E** (or **Insert > Insert Equation...**) still takes plain
keyboard math - `a^2 + b^2 = c^2`, `\frac{-b \pm \sqrt{b^2-4ac}}{2a}` - and
wraps it as inline (`\(...\)`) or display (`$$...$$`). New this release:
**Insert > Snippet Gallery...** now carries ten ready-made algebra and
geometry formulas (the quadratic formula, the Pythagorean theorem,
slope-intercept and point-slope forms, the slope/distance/midpoint
formulas, difference of squares, and a circle's area and circumference) -
pick one and it lands correctly typeset, nothing to type at all. And while
writing ordinary prose, a library of Math AutoCorrect-style shortcuts
seeded from the DAISY-published Word list - `\alpha `, `\sqrt `, `\ne `,
`\pi `, and dozens more - expands the moment you type the code and a space,
muscle-memory compatible with anyone coming from Word.

### See it, or step through it

**View > Browser Preview...** and HTML export now render every equation as
real typeset math - stacked fractions, drawn radicals, raised exponents -
instead of literal `$$...$$` text; no setting to find, because both
delimiters QUILL now uses are MathJax's own defaults. And for a formula
that is hard to hold in your head all at once, **Insert > Explore Equation
Structure...** (or **Ctrl+Shift+Grave, F**) steps through it piece by
piece - into a fraction's numerator and denominator, a power's base and
exponent, a root's radicand - one ordinary Windows list per level (arrow
keys, type-ahead, Enter/OK to choose; Escape ends the session outright at
any depth - **Back up one level** is the dedicated choice for retracing a
step instead).

**Read this part aloud**, the command that speaks just the piece you're
on, can now use real math speech instead of a template: install the free
**MathCAT math speech engine** (**Help > Download Optional Components...**,
about 3 MB, MIT-licensed, `daisy/MathCATForC`) and that command switches to
the same natural-language speech engine NVDA itself ships - a `ctypes`
binding to their prebuilt library, no Rust toolchain required to build it.
Skip the download and the command keeps working exactly as before, with a
simpler built-in reading; nothing regresses either way. Math braille
(Nemeth/UEB) isn't wired up yet - a follow-up once the speech side has been
validated by ear.

### A real equation in Word, not a picture

**File > Export > Word Document...** now writes a genuine Word equation
object for every `\(...\)` / `$$...$$` in your document - the same kind
Word's own equation editor produces, editable there and read as math by
JAWS, not a picture and not literal text. Reopen that file later and the
equation comes back exactly as plain, editable `\(...\)` / `$$...$$` text,
whichever docx reading engine you use. A new [tutorial](../tutorials/07-type-math-like-a-pro.md), *Write math without learning a new
language*, walks through all of it end to end, gallery first, for anyone
who has never typed math on a computer before.

## Table Studio - accessible tables, at last (experimental)

Tables have always been the hardest thing to edit by ear. This release adds
**Table Studio**, one experimental surface that makes them genuinely workable -
build a new table from scratch, or **open a CSV or TSV** straight into the same
grid. Either way your data lands in a real, keyboard-accessible grid where the
arrow keys move by cell and **Left/Right speak the column heading** as you cross
a row, so you always know exactly where you are. F2 edits a cell; Alt+arrows move
a whole row or column; Ctrl+Insert adds a row. When you are done, insert the
result into your document as a properly-headed Markdown or HTML table - or save
it back out as CSV, so a file you opened makes a full round trip. The grid
announces cells through Windows accessibility for NVDA and JAWS, with an optional
native provider for even richer cell events on builds that include it. Enable it
on the Experimental tab (Tools menu).

## The Experimental tab - consent in layers

Before the two big production features, meet the front door they share.
**Preferences > Experimental** has been rebuilt around a simple idea: nothing
experimental should ever be reachable by accident.

The first checkbox is now a true master switch, relabeled to say exactly what
it governs: **Enable experimental features** - all of them. While it is off,
every other control on the tab is disabled and drops out of the tab order
entirely, so to a screen reader user an untouched Experimental tab is one
checkbox and silence. Tick it, and the individual experiments unlock - each
with its own switch: **GLOW accessibility review and repair**, **WordPress
publishing connections** (the read-only inbound tools; the send half stays
locked no matter what), and **Read the document aloud in your browser**.

The editor-surface options go one layer deeper, behind a second
acknowledgement that carries its own warning in its own label: **Enable
experimental editor surfaces (features may degrade based on the control
selected)**. The editor surface is the control your document lives in, so the
surface choice, the border option, and the live surface explainer stay
disabled until you have said yes twice.

**Why it matters:** experiments are how QUILL grows, and the community should
get to try them early - but a screen reader user should never tab into a
switch that can change the editor underneath them without two deliberate
consents first. Opt-in, layer by layer, is the whole design.

---

## GLOW - guided accessibility review and repair

GLOW (Guided Layout and Output Workflow) is QUILL's accessibility review
system, and with this beta it graduates from hidden preview to a **shipping
experimental feature - one switch away**. Open **Preferences > Experimental**,
tick the master switch and GLOW's own checkbox, apply, and **Tools > GLOW**
appears immediately, no restart. (Until then, the GLOW commands stay
discoverable in the command palette and simply explain how to enable the
feature.) The idea is guided confidence, not a compliance dashboard: GLOW
reviews what is in front of you, explains each finding in plain language, and
offers only safe, deterministic fixes you can inspect before accepting.

### Audit what you can hear

**Tools > GLOW > Audit Current Document** reviews the whole file;
**Audit Selection / Paragraph** reviews just the block at your caret. Findings
open as a normal QUILL tab you can arrow through, search, or keep open beside
your document: heading levels that jump, links that just say "click here",
images without alt text, HTML missing its language, tables without header
cells, dense paragraphs that will be hard to listen to. Every finding names its
rule, its severity, and a plain-language suggestion.

### Fix without fear

**Fix Selection / Paragraph** cleans up the block in place and leaves the
result selected for review. **Fix Current Document** goes further: it opens the
repaired text as a *named preview tab* and immediately starts a compare session
against the original, so you accept the change knowing exactly what moved -
never a silent rewrite.

### Structured documents too

New alongside the opt-in, **GLOW Audit File...** and **GLOW Fix File...** take on
the files that are usually hardest to check by ear: Word, PowerPoint, Excel,
PDF, and EPUB. The shared GLOW engine parses the document in the background
(the editor never freezes), and the audit comes back as a scored, graded report
with every finding listed. Fixing a file always writes a repaired copy beside
the original - `report.docx` becomes `report-accessible.docx` - and QUILL
confirms the destination before anything runs. Your source file is never
touched.

### Private by default, updated only on request

The everyday GLOW workflow runs entirely on your machine. The engine's optional
networked helpers (AI alt-text, PII redaction, language processing) are off
until you explicitly turn them on, per action. **Help > Check for GLOW
Updates...** fetches a newer engine only when you ask - the manifest is signed,
every wheel is checksum-verified, and a failed install rolls back to the
bundled engine.

**Why it matters:** accessibility review has mostly been visual dashboards and
sighted checklists. GLOW puts a guided, spoken, keyboard-first repair loop
inside the editor you already use - so the person most affected by an
inaccessible document is also the person best equipped to fix it.

---

## Braille - proofreading for pages that must emboss

A new **Braille > Repair** submenu brings NLS-style proofreading: **Read Layout
Metrics** (longest line and page against your cells-per-line / lines-per-page limits,
with width and depth warnings), **Go to Longest Line / Longest Page**, and **Remove
Trailing Spaces** (this line or the whole file), all honouring your existing braille
page settings.

An honest status note on the long-standing **cell-two display offset** (some braille
displays showing the first character of each line in cell two): the **Editor control
type (braille)** choice we shipped **has not resolved it** - the issue persists, and
an outcome is still being considered. The control-type options remain available
under **Preferences > Accessibility** for troubleshooting and experimentation, and
we will keep reporting plainly on where this stands.
**Why it matters:** the difference between "it looks fine on screen" and "it actually
embosses cleanly", found and fixed before you send it - and when something is not
fixed yet, you hear that from us in exactly those words.

---

## A smaller, friendlier install

### Download only what you need

The base installer is smaller because the heavy, optional pieces now download on
demand - checksum-verified, with a cancelable progress bar, disabled in Safe Mode:
- **Pandoc** - the engine behind Word, ODT, EPUB, and RTF import/export was the
  single largest bundled component (~220 MB unpacked). The first time a
  conversion needs it, QUILL offers the official, pinned build right there
  (~45 MB) - roughly halving the installer on its own.
- The **braille translation pack** - the liblouis tables and BRF profiles behind
  the Translation submenu and embossing export (~68 MB unpacked; a ~9 MB
  download when you first reach for them). Reading with a braille display never
  needed them - that is your screen reader - and now the installer does not
  carry them either.
- The **offline speech engine** (whisper.cpp), **Kokoro** neural voices, and the
  classic **eSpeak NG** and **DECtalk** voices.
- The **Vosk** speech engine - a tiny, very-low-resource dictation and transcription
  engine for older or low-memory machines with no graphics card. Get it from **Tools >
  Speech > Download Vosk** or the Optional Components dialog below.
- **Spell-check dictionaries for other languages** - pick **Spanish** or **French**
  under **Tools > Spell Check Language** and QUILL fetches the dictionary the first
  time.
- And the audio-export helper, **FFmpeg**.

**Upgrading from a release that bundled Pandoc or the braille pack?** Your
existing copies are kept and keep working - nothing to re-download.

No speech engine is bundled in the installer any more - even the small default
downloads the first time you dictate - and some build-only data was dropped from the
runtime, so the base download is lighter than ever.

**One place to get them all: Help > Download Optional Components.** A single dialog
lists every optional download with **Installed** vs **Available to download** and its
size, so you never hunt through menus.
**Why it matters:** a faster first download and install, Windows' built-in voices
working immediately, and a clear, accessible touch point for everything else.
**Upgrading?** Any component a previous release bundled is kept and keeps working -
nothing to re-download.

### Runs light on modest, CPU-only machines

Two new settings under **Settings > Performance and Memory** let QUILL fit its full AI
and speech features onto machines with limited memory - never by turning anything off,
only by being careful with memory:
- **Unload idle models after** a few minutes frees an AI or speech model you have
  stopped using; the next time you need it, it simply reloads.
- **Low-resource mode** keeps only one model loaded at a time and prefers the smallest
  one that fits. On a machine with very little memory it turns on automatically and
  tells you once, out loud.

**Why it matters:** the whole feature set - dictation, read-aloud, and AI - stays usable
on an older, CPU-only laptop, because QUILL holds one model in memory at a time instead
of several. You trade a moment of reloading for a much smaller memory footprint.

### AI that fits your machine, and a way forward when you are offline

- When your computer can comfortably run a more accurate on-device model than the one
  you have chosen, the **AI model** dialog now says so - a one-step suggestion you can
  take or ignore. New installs still default to the smallest model that fits.
- If a cloud AI request cannot reach the internet and you have an on-device model
  installed, QUILL now tells you that you can switch to it and keep working offline. It
  never switches for you - your privacy choice stays yours.

### Export speech audio as MP3 and more

With FFmpeg present, Generate Speech Audio now saves as **MP3, M4A, M4B, OGG, Opus, or
FLAC** (WAV still works without it).

---

## A thank-you, and a place to experiment

### Golden Quills

**Help > About QUILL** has a new **Golden Quills** tab recognising the people who
support the project financially, in alphabetical order, with our heartfelt thanks. It
includes an optional **Donate** button.
**Why it matters:** QUILL is free and always will be - donating is completely optional
and never required. This is simply gratitude, made visible.

### Experimental settings (for testing)

A new **Settings > Experimental** tab lets you test how QUILL feels on different
editor surfaces - **RichEdit 3.0 / 2.0**, **Notepad** (a plain edit control),
**Rich text**, a **native Win32 EDIT** spike, and new this beta, the **Scintilla**
control (the engine behind Notepad++, and the only alternative surface with full
multi-level undo *and* redo - it exists to answer one open question: how JAWS,
NVDA, and braille displays behave on it, and your reports decide its future). A
read-only panel explains each choice's user and technical impact as you select
it, and the options stay ignored until you tick **"I understand features may
degrade based on the control selected."** A **Hide editor border** toggle is here
too. QUILL warns you to restart when you change these.
**Why it matters:** a safe sandbox for power users and testers to help shape the
editor, with a clear gate so nothing changes by accident.

### Read your document in the browser's best voices (experimental)

New in this beta, off by default: turn on **Read the document aloud in your
browser** under **Settings > Experimental** (it takes effect immediately - no
restart) and a **Read in Browser** command appears under **Tools > Reading &
Dictation > Read Aloud** and in the command palette. QUILL writes a
self-contained, accessible reader page - a labelled voice picker, Speed,
Play/Pause/Stop, a live status line, Escape to stop - and opens it in your
chosen browser, where the browser's full voice set is available, including
Edge's "Online (Natural)" voices that the built-in engines cannot reach. It
reads section by section so book-length documents stay reliable, **Pause**
keeps your place and tells you where you are ("Paused at section 12 of 300"),
and your voice and speed choices are remembered.
**Why it matters / privacy:** the best-sounding free voices live in real
browsers. QUILL itself makes no network call and no audio file is produced -
but the browser's "Online (Natural)" voices synthesize in the vendor's cloud,
so choosing one sends the text being read to that service; voices labelled
"on this device" stay fully local, and the setting text says all of this
plainly. The reader page is deleted when you close QUILL, so no plaintext
copy of your document lingers.

### Proofread before you publish

- **Proofread Mastodon posts before sending (per account)** - tick it and pressing
  Post opens the F7 Spelling Review on the post text first.
- **Spell check a document before saving** - opens F7 automatically on Save / Save As.

---

## Safety advisories - a promise with an off switch we hope never to use

QUILL 0.9.0 ships with a working, enabled **remote safety-advisory system** - and
because trust is the entire product, here is exactly what it is and is not.

If the community reports that a specific shipped feature is misbehaving badly -
corrupting something, misleading a screen reader, breaking under an OS update -
we can publish a **signed advisory** that temporarily disables *that one
feature* until a fix ships. The advisory rides the same signed update feed as
releases, is delivered by the startup update check (now on by default; the
check fetches QUILL's own feed and sends nothing about you or your documents),
and once received it is honored offline and across restarts, because a safety
lock you can only reach while online would be useless during an incident.

The guarantees, in plain words:

- **It only ever turns things off.** An advisory can make a feature
  unavailable; it can never enable, install, or run anything.
- **It speaks.** A locked feature dims in the menus and QUILL announces the
  advisory and its reason out loud - never a mystery, never a silent removal.
- **It is signed.** Advisories are verified against the same signing chain as
  updates; nobody can lock your features by spoofing a feed.
- **You keep the last word.** A local escape hatch
  (`QUILL_IGNORE_FEATURE_LOCKS=1`) disables all remote locks for that run, for
  administrators and for the day an advisory is ever wrong.
- **Policy:** we will use this only in response to real user feedback, when a
  fix cannot ship fast enough, and every advisory is lifted by the same signed
  feed the moment the repaired release is out.

**Why it matters:** feature freeze plus a fleet of beta users means problems
will be found by people mid-sentence in real documents. This is how we protect
you in the hours between "you told us" and "it is fixed" - loudly, reversibly,
and with your override in writing.

---

## Under the hood - quality, reliability, and honest engineering

The features above stand on a day of unglamorous work that deserves its own
telling, because this is the part most release notes hide.

### The GLOW engine can no longer silently vanish

The most interesting bug of the cycle: GLOW's shared engine could be
*installed and silently unavailable* at the same time. The engine's recent
architecture split moved its analysis backend into a new component, but the
version floor QUILL asked for was loose enough that an older, pre-split
install could satisfy it - and the engine would simply report "not
installed" with no error anywhere. QUILL now pins the exact backend floor it
needs, the vendored offline wheels install cleanly on a bare machine, and
the failure mode is extinct by construction. If you ever wondered why an
optional engine "didn't take" - this class of problem is what got fixed.

### Startup can no longer be taken down by a warm-up

QUILL's deferred startup runs each step - screen-reader detection, crash
recovery, watch folders - inside its own isolation so a failing step is
logged and skipped, never fatal. One recent addition (the browser-preview
warm-up scheduler) had slipped outside that pattern; a failure there could
have killed startup. It is now isolated like everything else, and the
regression test that guards the whole contract is green again.

### Responsiveness as a policy, not an accident

Everything heavy that shipped this cycle runs on the background task pool:
GLOW's structured-file audits, document conversion, page-by-page OCR (with
cancel checks between pages), and the verified engine download. The editor
never freezes for any of it - progress lands in the status bar, results
arrive as tabs, and your cursor stays exactly where you left it. On-device
OCR is CPU-only by design, and the speech and AI engines continue to load
on demand and unload when idle, so a modest laptop stays a first-class
citizen.

### Documentation as part of the product

Every feature that shipped this cycle shipped *documented, everywhere, at
once*: user-guide sections for GLOW and Import / Convert Document, glossary
entries, F1 help for every new command (the control reference now covers
469 topics, regenerated from the same source of truth as the app), product
requirements updated, the roadmap reconciled so it tracks only genuinely
open work, six new tutorials, and a 36-episode audio course. If you can
reach a feature, you can read about it - and now, hear about it.

### Every robot reviewer answered

Alongside human review, every pull request in this cycle was combed by
automated reviewers - GitHub Copilot and CodeQL - and this beta closes out
**all 94 findings** they raised across the 0.9.0 feature wave: every one
triaged, the real ones fixed (about sixty changes, from implicit string
concatenation that could silently mangle a spoken message, to a modal dialog
opened inside another dialog's teardown, to hardening in the native Table
Studio UIA provider), and the false positives answered on the record. The
Table Studio native provider also **builds cleanly again** (#823), so the
richer UIA cell events are back on the menu for builds that compile it.

### The little disciplines

The whole repository now passes its style gate completely clean; the module
size budgets, dialog inventory, network egress audit, persistence audit, and
UI-surface snapshots were all re-verified; and the full test suite - now over
7,000 tests - passes. None of this is visible in a menu. All of it is why the
menus keep working.

---

## Fixes worth calling out

- **Bookmarks now persist** per document and across sessions (see above), and QUILL
  restores your last cursor position - fixing the old behaviour where bookmarks were
  forgotten on close and shared across documents.
- **Opening Word and other documents with QUILL as the default app works** - pressing
  Enter on a file in your file manager now opens it instead of doing nothing.
- **Far less double-spoken chatter** - actions like "No misspellings found" were
  spoken twice; now exactly once (#728).
- **Report a Bug is keyboard-navigable again** and reliably confirms the report was
  copied (#729).
- **No alarming "text-to-speech failed"** when your screen reader is running; the
  SAPI fallback also initialises correctly under a read-only install (#749).
- **Offline dictation works out of the box** - the engine is fetched on first use
  instead of failing with "whisper binary not found" (#742).
- **Saving a model no longer freezes at 2% and crashes** - download progress is
  throttled so it cannot flood the UI (#748).
- **Spell check finds real misspellings again** - when Hunspell is present its verdict
  is authoritative, instead of a permissive word list waving typos through.
- **The portable build launches and opens documents**, and the **AI Hub opens**
  instead of erroring on a lazy-string.
- **Live preview no longer flickers or re-announces as you type** - the external
  browser preview refreshes only after you pause typing (debounced) and keeps
  your place on reload (returning to the section you are editing, or your previous
  scroll position), instead of reloading on every keystroke and jumping to the
  top. The in-app side preview (Ctrl+F6 to focus it) updates silently in place
  with no reload - the recommended live preview for screen-reader/braille users.
- **The crash-report dialog tells you what happened** - choosing Send, Copy, or
  Send without a sign-in used to complete silently, indistinguishable from doing
  nothing for a screen-reader user; QUILL now confirms out loud that the report
  was sent, copied to your clipboard (and what to do next), or that sending
  failed and it was copied instead.
- **Snappier, less alarming startup** - the one-time WebView2 warm-up runs after
  the editor is ready, not before it, so a slow first setup no longer looks like a
  freeze; short UI stalls now also capture a diagnostic stack snapshot, and
  startup task timings are always written to the logs so a slow launch can be
  reported with evidence.
- **Idle AI models are actually released now** - the background idle-unload sweep
  crashed on every tick, so idle models were never freed; it now runs correctly.
- **F1 help now covers every command** - all 319 commands that previously had no
  help topic now have a plain-language description and their shortcut, so pressing
  F1 on any menu item or command always says something useful.
- **Smart triggers and Quillin-contributed abbreviations now actually fire** -
  typing `=bug()`, `=todo(10)`, or `=rand(3,4)` alone on a line and pressing Enter
  now inserts the generated text, and contributed abbreviations like `qbug` expand
  as you type (with Abbreviation Expansion on). Both were declared and documented
  since 0.7.0 but never dispatched. Numeric arguments work, every insertion is
  announced and undoable, and the per-trigger toggles on the Quillin's preferences
  page are honoured.
- **Quiet failures now speak up** - List Studio settings export/import confirms
  success or explains the failure, the Pronunciation Dictionaries dialog warns
  when a dictionary could not be saved, and the Quillin wizard's Copy JSON only
  claims "copied" when the clipboard actually took the text.
- **The Python snippet sandbox is harder to escape** - snippets are now also
  statically blocked from dunder attribute access (the classic route from a
  harmless-looking expression to the OS), on top of the existing
  separate-process isolation, import allowlist, and time/memory caps; if the
  OS refuses a resource cap, QUILL logs it instead of staying silent.

### Community contributions - thank you, Kelly Ford

Two fixes in this beta come from community contributor **Kelly Ford**:

- **New document tabs open focused, not blank** - opening a document with **Open
  from URL**, **Import**, or **Open from Remote** could leave the new tab
  unfocused and visually blank until you tabbed away and back (the closing file
  dialog was restoring focus to the previous tab). The new tab now reliably takes
  focus, just like the normal Open flow (#805).
- **The Pandoc download shows a real, cancelable progress dialog** - the first
  time a conversion needs Pandoc, its on-demand download now uses the same
  accessible percentage dialog (with a Cancel button and announced progress) as
  the other on-demand downloads, instead of a status-bar line that was easy to
  miss (#807).

---

## Every save tells the truth: Caroline's eight lines

A beta tester named Caroline wrote eight lines, pressed Ctrl+S, chose Word
format, named the file, and pressed Enter. QUILL said it saved. Then three
things went quietly wrong. The title bar still read "Untitled [modified]".
Pressing Ctrl+S again brought back the Save dialog with an empty name box, as
if the first save had never happened. And when she opened the file in Word,
her eight lines had been fused into one long unbroken line.

Every one of those symptoms traced to a real defect, and pulling that thread
uncovered more. This beta fixes all of it and then finishes the thought:
saving and converting in QUILL is now honest end to end, and it explains
itself in language a screen reader user can act on.

### What was wrong, and what is true now

**The title bar and the vanishing filename were one bug.** Word (.docx) was
the only Save As format that wrote the file without recording that the
document now lived there. The document stayed "untitled and modified" in
QUILL's mind, so the title never updated and the next save started from
scratch. Fixed - and a regression test now pins the contract for every format:
after any successful save, the document knows its path and knows it is clean.

**The fused lines were a translation dialect problem.** On its way to Word,
your document passed through a Markdown dialect in which a single line break
is a "soft wrap" - a suggestion, not a fact. Eight lines in, one paragraph
out. QUILL's rule is now uniform everywhere: **one editor line is one
paragraph**, in the native Word writer, in the Pandoc fallback, and in every
File > Export format - Word, OpenDocument, HTML, RTF, EPUB, and PDF alike.
What you hear line by line is what the exported document is.

**Your originals can no longer be destroyed by a reflex.** This one no user
had reported yet, and it was the most serious find of the audit. When you open
a PDF, an EPUB, a PowerPoint, or a spreadsheet, QUILL shows you *extracted
text* - the binary original cannot take that text back. Yet Ctrl+S would write
the text over the original file, destroying it. Now QUILL refuses, explains
("this document was opened as extracted text; saving over the original would
destroy it"), and opens Save As so your edits land somewhere that can hold
them. The same guard stops the reverse mistake: typing `notes.pdf` in Save As
no longer produces a Markdown file wearing a `.pdf` name that Acrobat cannot
open - QUILL offers File > Export, which makes a real PDF, or asks you to pick
a format it can genuinely write.

**A converting save now says what it did.** Saving as Word, RTF, or HTML has
always meant: the file on disk is converted; your editor keeps QUILL's clean
text; every further save converts again. That model is sound - and it was
silent. Now QUILL announces it the moment it happens: *"Saved as report.docx,
Word format. You are still editing QUILL text; each save converts it to
Word."* No mystery, no wondering which format you are "really" in.

**Failure sounds like failure.** A save that dies on a full disk or a locked
file now produces a clear spoken error and leaves your document exactly as it
was - never a crash, never a success message over a file that was not written.

### Restore points: any earlier save, back in one dialog

While fixing how saving *talks*, this beta also changes what saving *keeps*.
Every save now records a quiet snapshot of your document, and **File >
Restore Previous Version** brings the history to you in plain language:
"Today at 4:12 PM - 2,341 words." Pick a version and either **Restore** it —
QUILL saves your current text as a restore point first, so even restoring is
reversible, and nothing touches the disk until you save — or **Open as Copy**
to put the old version in a new tab beside your current one.

The engineering is deliberately humble. Snapshots are content-based, so
saving unchanged text stores nothing. Keeping a snapshot can never be the
reason a save fails — if the disk is full, your save still completes. And the
history thins as it ages like a well-kept journal: everything from the last
week, then one version per day for a month, then one per week, with the
newest five never pruned and a per-document disk cap in Preferences.

Where this sits among QUILL's safety nets: undo covers the current session,
backups keep the copy from just before each save, and restore points are the
long memory — last Tuesday's draft, back in three keystrokes. It is also the
first shipped piece of the QUILL Sync plan: the same version store becomes
the sync engine's history layer when sync arrives in a future release.

### Small kindness, big difference: the filename suggestion

Save an untitled document and the name box now arrives pre-filled from your
document's first line - heading marks, quote markers, and bullets stripped,
Windows-forbidden characters removed, capped to a sane length. For a screen
reader user, an empty edit box is a dead end; a sensible proposal is a running
start. It is on by default, it only ever *suggests* (type anything over it),
and it never renames a document that already has a name. Turn it off with
"Suggest a filename from the first line" in Preferences if you prefer the
blank box.

### Choose your converter - and hear the trade-off before you commit

"Convert to Word" is not one operation. A structure-first engine and a
formatting-first engine both produce legitimate Word documents that differ in
what they keep. QUILL now lets you choose, and - this is the part we care
about - **describes the outcome of every choice in plain spoken language**
before you commit to it.

- **Word document reading engine** (Preferences > Editing): how a .docx
  becomes editable text on open. *Auto* (default) tries MarkItDown first.
  *MarkItDown* is fast and reliable - headings, lists, and tables come
  through; images, comments, and fonts do not. *Pandoc* keeps richer
  structure - footnotes and complex tables survive better - and if Pandoc is
  not installed the preference quietly degrades rather than failing your open.
- **Word document saving engine** (Preferences > Editing): how your text
  becomes a .docx on save. *Native* keeps QUILL's formatting codes - fonts,
  sizes, colors, highlights, alignment - and maps each editor line to one Word
  paragraph; it is the right choice for documents written in QUILL. *Pandoc*
  maps structure to Word styles - headings, lists, tables, links, footnotes -
  but drops the font, size, and color codes.
- **Convert File** gains a per-conversion engine choice (Auto / Pandoc /
  MarkItDown) with a description that updates as you arrow through it. Pick
  MarkItDown for a conversion it cannot honestly do and QUILL says so and
  offers Pandoc - it never silently substitutes an engine you did not choose.

The defaults are unchanged and right for almost everyone. The choices exist
for the days they are not.

**The receipts.** Every engine description is backed by a measured bake-off
(`docs/qa/converter-bakeoff.md`): seven fixture documents - nested lists, a
data table, real footnotes, links, right-to-left Arabic text, a hundred-section
document, and per-run formatting - through every candidate engine. MarkItDown
and Pandoc passed the full corpus. The raw python-docx extract loses tables,
footnotes, and link destinations, which is why it is only a last-resort
fallback. Two outside libraries were evaluated and settled for good: **pydocx**
is rejected permanently (it cannot even be imported on Python 3.10 or newer,
and its last release was 2016), and **mammoth**, though well maintained, is
not adopted because MarkItDown already covers its route at equal fidelity - with
a recorded decision tree for the day that changes.

The full conversion behavior - what every Save As choice does, which formats
are protected, the one-line-one-paragraph rule, and the engine trade-offs - is
documented in the user guide ("Saving in Different Formats" and "Choosing a
conversion engine") and specified in the PRD (section 5.3a.1.1a), enforced by
io-layer tests rather than UI convention. Caroline: thank you. Eight lines
went a very long way.

---

## The road to 1.0 - what happens now

**This is the feature freeze.** From this beta forward, nothing new goes in.
Every commit between here and QUILL 1.0 is a bug fix, a polish pass, a
performance win, or a documentation improvement. That is not the project
slowing down - it is the project keeping its second promise. The first promise
was "we will build it all." The second is "it will all *work*."

What that means in practice:

- **Your bug reports are the roadmap now.** Every issue filed against this
  beta is triaged for 1.0. The fastest way to shape the release is to use
  QUILL for real work and tell us where it creaks.
- **Rough edges get smoothed, not shipped.** If something in this beta is
  confusing, wordy, too quiet, too loud, or slow, that is exactly the feedback
  the polish phase exists for.
- **Safety advisories stand guard.** If something serious surfaces in the
  field, we can disable that one feature - loudly and reversibly - while the
  fix ships (see the safety advisories section above).
- **A robot tester now uses QUILL the way you do.** A new nightly UI-automation
  suite launches the real app, presses real keys, and checks what a screen
  reader would meet: named controls, honest titles, Escape that works, and the
  words QUILL actually speaks. It reports; it never gates or auto-fixes -
  people read the report and people decide.
- **1.0 will be boring, in the best way.** Same features as this beta.
  Fewer surprises. That is the whole plan.

## For testers

- Upgrade path: install over the previous beta and confirm your settings,
  keymap, and documents carry forward
  (see `docs/release/upgrade-path-regression-0.8.0.md`).
- Fresh install: see `docs/release/fresh-install-regression-0.8.0.md`.
- Acceptance: `docs/release/user-acceptance-test-plan-0.8.0.md`.
- New this beta to exercise: **Alt+F3** Reveal Codes; **Set/Go To/List
  Bookmarks** then reopen the file; **File > Restore Previous Version** after a
  few saves; a Save As to Word and the announcement that follows;
  **Tools > Vault** on a folder of notes; **Tools > Story Studio**;
  **Tools > Speech > Voice Command**; **Help > Download Optional Components**;
  **Settings > Experimental**; **Help > About > Golden Quills**.

---

## Thank you - this one belongs to the community

QUILL is built by a small team and a large family. This release exists because:

- **Testers wrote to us.** Caroline's eight lines rebuilt the save pipeline.
  Kelly Ford's two contributions fixed focus and made a download honest. Dozens
  more of you filed the issues, confirmed the fixes, and re-tested the builds -
  wave after wave, until the open-issue count hit zero more than once.
- **Supporters kept the lights on.** The Golden Quills - the people who chose
  to give, when giving was never required - are named with gratitude in
  **Help > About QUILL**. Every feature in this release is free for everyone,
  forever, in part because of them.
- **The wider community built the ground we stand on.** Screen reader makers
  and the blind writing community whose decades of hard-won conventions this
  product tries to honor on every keystroke; the open-source projects QUILL
  gratefully builds on; and everyone who told a friend "try this editor."

A writing tool for blind writers, built with blind writers, feature complete
and heading to 1.0. Install the beta. Write something real with it. Tell us
what creaks.

We will fix it. That is the whole job now.

*- The QUILL team at Community Access*
