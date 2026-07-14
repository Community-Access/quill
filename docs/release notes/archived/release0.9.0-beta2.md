# QUILL 0.9.0 Beta 2

## Built with you. Polished for all of us.

*From Community Access. Free. Optional by design. Private by default. Yours to make quiet — and yours to help shape.*

This release is what happens when a community does more than test software: it **builds it together**. Every crash report, every “this felt strange,” every missing label, every voice that would not speak, every shortcut that collided, and every idea that made QUILL more useful has helped move the project forward.

Beta 2 is not software created somewhere else and handed to the people who use it. It is the result of people speaking up, developers listening closely, testers trying again, and the whole community making QUILL better **by and for each and every one of us**.

The promise from Beta 1 continues here: this release is overwhelmingly your reports turned into fixes, clarity, polish, confidence, and new possibility. A few features we had been eager to ship joined the celebration too — including the long-requested page indicator, because when enough of you ask for something that matters, it deserves to move.

This is the friendly, long-form companion to the **“0.9.0 Beta 2”** section of `CHANGELOG.md`. The shorter text shown under **Help > What’s New** and **Check for Updates** comes from that changelog; this document tells the fuller story of what changed, why it matters, and where your feedback can guide the next step.

**Grazie. Thank you. Keep testing, keep imagining, and keep the reports coming. This release belongs to you.**

### The Beta 2 celebration, at a glance

- A new experimental **QuillRichEdit** surface invites real-world braille testing and begins a lightweight rich-text future.
- A top-to-bottom **macOS completion pass** makes QUILL dramatically more native, useful, secure, and testable on the Mac.
- A fully self-contained **Offline Edition** brings every optional component along for air-gapped and locked-down environments.
- New page awareness, **Print Studio**, headers and footers, image alt-text enforcement, Work Personas, Clip Library, AutoOutline, email flows, and more make everyday work feel richer and more intentional.
- Speech, dictation, audio export, AI setup, Ollama support, optional-component management, GitHub browsing, privacy, diagnostics, stability, and platform integration all received meaningful community-driven improvements.

---

## Help us finish the next chapter

Some of the most important work in this release can only be proven on the hardware and platforms you use every day. These are not ceremonial requests. Your results decide what becomes the dependable default next.

### Braille display owners: please put QuillRichEdit to the test

We've been chasing two long-standing braille reports, and this release ships
the first real lever for both. They are:

- **The "cell-two" offset** — some displays start the first character of every
  line in cell 2 instead of cell 1 (a long-standing word-processor-control
  quirk, not specific to QUILL).
- **Missing selection dots** — some displays do not show dots 7-8 under
  selected text when the caret is in QUILL's default editor.

The lever is a new experimental editor surface called **QuillRichEdit** — the
*same* native Rich Edit control QUILL already uses as its default editor,
wrapped so QUILL can reach underneath it. It adds a switch that asks that same
control to behave more like a plain text-edit control for braille purposes,
while keeping everything that makes it read correctly to JAWS and NVDA. **We
do not yet know if this fixes the offset or the missing dots on real hardware
— that is genuinely what we need you to find out.**

**How to try it, step by step:**

1. Open **Preferences > Experimental**.
2. Tick **Enable experimental features** (the master switch).
3. Tick **Enable experimental editor surfaces**.
4. Set **Editor surface** to **QuillRichEdit**.
5. Tick **QuillRichEdit: emulate a system edit control (braille test)**.
6. **Apply Settings, then restart QUILL** — all three of these settings take
   effect on the next launch, not immediately.
7. With your braille display attached, open or type into a document and check:
   does text now start in cell 1, or still cell 2? Does selecting text now show
   dots 7-8 underneath it? Does JAWS or NVDA still read the editor's content
   correctly?

If you can, please test under **both NVDA and JAWS** — braille rendering can
differ between screen readers, so a result under one does not guarantee the
same under the other. Tell us what you see, for each screen reader you tried,
along with your braille display model, through **Help > Report a Bug**, either
way: helped, no difference, or worse. This is still an open question, and
real-hardware reports are the only way to answer it. **To go back**, untick the
two experimental-editor checkboxes (or set **Editor surface** back to its
default) and restart QUILL.

This same surface also carries QUILL's first native RTF load/save and in-place
bold/italic/underline/font/alignment formatting, as a first step toward a
lighter-weight rich-text document mode — but the braille question above is the
reason it needs your feedback most.

### Mac users: three quick checks that can close the loop

If you use QUILL on macOS, three things would help us enormously. Each is
fixed in code in this release but needs a Mac to confirm, so please try the
fix and leave a short comment — *helped*, *no difference*, or *worse* — so we
can close it out or reopen it.

- **Diacriticals no longer stolen by shortcuts.** In a Polish or other
  diacritical layout, Option+Z / +Q / +M / +I now type their character instead
  of firing a QUILL command. Does typing those characters work for you now?
  Please comment on
  [support#67](https://github.com/Community-Access/support/issues/67).

- **Settings speech controls are labelled for VoiceOver.** The Rate, Volume,
  and Pitch number boxes now announce their label alongside their value. Does
  VoiceOver read them clearly? Please comment on
  [support#69](https://github.com/Community-Access/support/issues/69).

- **Are the new Mac shortcuts comfortable?** We moved three shortcuts that
  collided with macOS system ones (see "Three Mac keyboard collisions fixed"
  below for the details). These are our best guess from a Windows box — if any
  collides with something on your setup or just feels awkward, tell us and
  we'll pick a better chord together.

---

## Everyday writing now feels more alive

These are the changes you can feel immediately: clearer navigation, stronger document accessibility, smarter printing, less friction, and more ways to make QUILL fit the way you work.

### A page number — honestly presented

A tester asked directly: "Are we going to be able to see proper page
numbers with QUILL?" Now every document shows one, in the status bar,
on by default, right next to your line/column position.

- **PDFs get a real page count.** QUILL now preserves each PDF's actual
  page boundaries when you open it, so you see an exact "3 of 12" and
  `Ctrl+Shift+G` (Go To Page) jumps exactly.
- **Everything else gets an honest estimate.** Plain text, Markdown, and
  Word documents don't have a real "page" until you print or export --
  it depends on font, margins, and paper size, none of which QUILL
  tracks while you write. So for these, the same cell shows "~3 of ~12
  (estimated)" -- the tilde and the word "estimated" always travel
  together, on purpose, so you never mistake a guess for a fact. Tune
  the words-per-page assumption in Preferences > Navigation and QUILL Key
  if your pages run long or short.
- Braille documents are untouched -- they keep their own, richer page
  system.

### Alt text you cannot accidentally skip

GLOW already catches missing alt text after the fact — this adds the
proactive half. **Insert > Image...** is QUILL's first dedicated
image-insertion flow: it won't let you insert without either real alt text
or an explicit "this image is decorative" choice, so a document can no
longer quietly pick up an un-alt-texted image. And for any image already
in your document, however it got there, **Tools > Describe Image at
Cursor** tells you exactly what's there: "Image: sunset.png, alt text: a
sunset over the lake" — or just as clearly, "alt text MISSING" if nobody
ever wrote one.

### Print Studio: know before you print

**File > Print Studio...** tells you what you're about to print before you
print it — "3 pages, Letter, default margins" — read aloud or in braille,
the way a visual print preview would show a sighted user. Then choose
**all, odd, or even pages**, **reverse the order**, or **skip the first
page** if it's pre-printed letterhead, before it hands off to the same
Print dialog you already know. Printing itself also got more honest along
the way — it used to draw whatever fit on one page and quietly drop the
rest of a longer document; now it paginates properly.

### Headers and footers, built for real documents

**File > Header and Footer...** builds one from named presets — title on
the left with the page number on the right, filename and date, Roman
numerals for front matter — or your own mix of a handful of tokens
(title, filename, date, page number) placed left, center, or right. Want
a different header on page one? There's a checkbox for that. Numeric or
Roman page numbers, starting wherever you like. It's saved with the
document and shows up on every page you print, Print Studio or plain
Print alike.

### Five joyful upgrades for the work between the big moments

- **Look Up now includes Wikipedia.** A short encyclopedia summary, with a
  link to the source, appears alongside definitions and synonyms when you're
  online — same consent and offline fallback as always.

- **A bigger clip history, alongside Copy Tray.** Copy Tray's curated 12 slots
  aren't going anywhere — **Clip Library** (Edit menu) is a second, rolling
  history of everything you choose to keep, searchable, favoritable, and
  promotable into a specific Copy Tray slot when one earns a permanent home.
  Turn on automatic capture (off by default) and every copy inside QUILL is
  remembered with no extra step.

- **Send as Email, or just Copy as Email Body.** The File menu can now hand
  your selection (or the whole document) straight to your mail client, or
  copy it to the clipboard formatted for pasting into one — useful when a
  mail client balks at a long message built the first way.

- **AutoOutline numbers your headings for you.** Format > Update Outline
  Numbering — numeric or legal style, your choice in Preferences > Editing —
  writes the number straight into the heading text, so it reads aloud and
  survives copy/paste and export with nothing extra to configure.

- **Work Personas: one action into a whole context.** Tools > Work
  Personas... bundles a feature profile, a working folder, your favorite
  files, and a keymap profile under a name — "School," "Novel," a client's
  name. Apply it instantly, launch straight into it with `quill --persona
  NAME`, or generate a double-clickable shortcut so it's one click away
  without QUILL already open.

### Make the QUILL key truly yours

A new **Change QUILL Key...** button in the Keymap Editor (**Preferences >
Keyboard > Keymap Editor**) lets you reassign the QUILL-key prefix itself
— the key every `QUILL Key + ...` chord starts with. Pick a new one and
QUILL validates it, warns you about conflicts with other bindings (and
with OS-reserved chords), then rewrites your stored chords to follow the
new prefix, so `QUILL Key + S`, `QUILL Key + V`, and the rest all move
together instead of you rebinding them one at a time. And typing `quill`
in the Keymap Editor's search box now lists every QUILL-key-chord command
in one place, so you can see — and rebind — the whole chord set at once.
It works the same on Windows and macOS.

### “Casual Writer” finally gets out of your way

- **"Casual Writer" finally just lets you write.** The profile was quietly leaving
  AI, GLOW review, remote files, analysis, watch folders, notebooks, and developer
  tools switched on. Choose Casual Writer now and those step out of the way, for a
  clean "write, format, print, send" workspace — while read aloud, voice commands,
  dictation, and braille stay right where they are, because a simpler profile
  should never be a less accessible one. Want any of it back? Preferences >
  Profiles and Features, one toggle each.

### Focus, status, and labels that tell the truth

- **Dialogs open on the first real control**, not the OK/Cancel button or a tab
  strip. The Speech Hub, Manage Speech Models, Manage Voices, the AI Hub, About, About Whisperer, the Help status
  dialogs, and Quillin preferences all land you where you can start working — and because
  the fix lives in the shared dialog machinery, every tabbed dialog behaves.

- **The status bar stopped repeating itself.** Pressing F6 into the status bar and
  arrowing across it made your screen reader say "Status Bar" before every cell.
  Now you hear it once, on arrival; after that each cell just tells you what it is
  and what it says — for example, "Position, Ln 12, Col 7."

- **The status bar stopped repeating itself, take two.** The general Message cell
  could end up showing the exact same text as another cell right next to it — a
  tester noticed it happening with the Page cell. Message now goes quiet whenever
  another visible cell is already saying the same thing, instead of saying it twice.

- **No more doubled ampersands.** "Writing & Language," "Reading & Dictation," and
  friends sometimes read back as "Writing && Language." They spell out "and" now.

- **AI Hub: choosing a provider stays where you put it.** Arrowing through the
  Provider list without opening its dropdown could bounce focus over to the Model
  field the moment its suggestions refreshed. Focus now stays put.

- **Preferences now lands you on the right control when you switch tabs.** Ctrl+Tab, Ctrl+Shift+Tab, or clicking a different Preferences tab moved the visible page but left focus wherever it had been, so a screen reader sometimes announced only "Panel" instead of the new tab's first field. Switching tabs now always moves focus to that tab's first real control.

---

## Your language, your braille, your way of working

Accessibility grows when more people can arrive as themselves. Beta 2 expands QUILL’s language reach, restores features that translations exposed, and keeps braille and screen-reader use at the center rather than at the edge.

- **Italian is here to switch to.** Elena Brescacin's beautiful, complete Italian
  translation shipped in Beta 1 — but a build step meant it never actually appeared
  under Change Display Language. It does now, all 1,100-plus phrases of it. Grazie
  mille, Elena. (Tools > Writing and Language > Change Display Language.)

- **Italian no longer blurs two "vaults" into one.** The OS credential vault
  and QUILL's document vault had landed on the same Italian word; they're
  now distinct — credential store "archivio delle credenziali," document
  vault "raccolta" — with stale fuzzy markers cleared and "encoding"
  corrected to "codifica." (#913)

- **Danish joins the Braille Translation menu.** The grade 1 and grade 2 tables
  shipped with the engine all along; Danish just never made it onto QUILL's list.

---

## Optional power, without optional confusion

QUILL remains small on purpose. The larger pieces arrive only when you choose them — but choosing, installing, testing, removing, and returning to your work should feel welcoming, predictable, and complete.

### Getting the extras you want, completely reimagined

QUILL stays small by downloading the big optional pieces only when you ask. Beta
testers told us that experience was confusing — so **Help > Download Optional
Components** was rebuilt into one warm, guided place.

- **One hub for everything optional.** Every component in a single list, the ones
  most people reach for first (Pandoc, then the braille pack), each row saying in
  plain language what it does and how big it is. The window opens instantly now
  instead of pausing to check what you already have.

- **Prove it works before you rely on it.** Anything installed gets a **Test**
  button: a voice reads you a sample so you actually hear it, the offline speech
  engine listens to a spoken phrase and tells you what it heard, and tools report
  their version. There's a **Remove** button too, and a **Manage** button that
  jumps you straight to the right picker (Manage Speech Models or Manage Voices).

- **A guided, step-by-step setup for offline dictation.** Choosing offline
  dictation used to mean hunting through menus. Now the row is simply called
  **Dictation (offline speech)**, and it walks you through it one step at a time —
  a banner at the top always tells you which step you're on and the single next
  thing to do: **1.** pick and install your engine — **Whisper.cpp** (light and
  fast, works on any computer), **Faster Whisper** (most accurate), or **Vosk**
  (tiny, for old or low-memory machines); **2.** pick a model, with the best fit
  for your computer already selected so it's one click; **3.** press **Test
  dictation** to hear it prove itself, and it becomes your default. QUILL
  remembers the engine you chose, so you come back to where you left off instead
  of it resetting to the built-in engine. Vosk used to sit as its own separate row
  further down the list; it's simply a third choice here now, so there's exactly
  one place to set up offline dictation.

- **You always land back where you started — on the row you were just on.**
  Downloading something used to fling you off into the editor or another tab, or
  reset the list to the top. Now every download — voices, engines, Pandoc, the
  braille pack, audio extras, Node.js, MathCAT, spell-check dictionaries —
  finishes, returns you to the hub, and reselects exactly the row you were working
  with.

- **A gentler helping hand.** If you Test a piece before it's fully set up, QUILL
  walks you over to finish rather than treating a perfectly normal situation as an
  error — for offline speech specifically, that now means reopening the same
  guided engine-and-model picker above, not a bigger settings dialog. And if a
  download genuinely fails, it offers to send a report with the details.

- **Runs portable, stays portable.** Everything installs into your portable data
  folder when you run QUILL from a drive, so your whole setup travels with you.

- **Audio export, playback, and chapters live in one place.** FFmpeg (for
  exporting compressed audio like MP3 and M4B), the mpv playback engine, and MP3
  audiobook chapter markers are now a single **"Audio: export, playback &
  chapters"** row instead of three scattered entries — and each piece is still
  fetched only when you first use its feature, so nothing large downloads until
  it's actually needed. **Node.js** now sits at the very bottom of the list, as
  the least-used extra.

- **"Set as Default" is now a real, findable button.** Pick your favorite offline
  speech model, or your favorite Read Aloud voice, and tell QUILL to use it from
  now on — a button and a right-click option, right where you already are, instead
  of a side effect of closing a dialog a particular way.

- **Speech Settings now separates offline from online.** The Speech and Dictation
  tabs each split into **Offline** and **Online**, so your installed-once local
  engines and voices aren't mixed in with API-key cloud services in one long list.

### PDF and Office extraction is one clear download away

- **PDF and document import works out of the box again — and it's now a
  one-click download.** A tester on a clean install hit "can't extract text
  from PDFs — no extraction engine available." The free local converter and
  PDF text extractors were described in-app as built-in, but weren't actually
  installed by the shipping build. Rather than bundling them whether or not
  you ever open a PDF, **Help > Download Optional Components > "PDF and
  Office text extraction"** (about 30 MB) now fetches them the moment you
  need them, on any install — and if a PDF has no selectable text, QUILL
  still tells you it looks like a scanned document and points you to OCR,
  instead of a confusing "no engine" message.

---

## Speech that speaks, dictation that listens, and audio that respects your time

The speech stack received one of the deepest practical passes in Beta 2. Voices now prove they work, previews behave like previews, transcription is more dependable, and long-running audio work gives you control instead of holding QUILL hostage.

### Voices, Read Aloud, and offline transcription

- **Kokoro voices really speak now.** Richard reported that after downloading
  Kokoro, previewing a voice failed with a baffling "needs one more component"
  message. His diagnostics log pointed straight at the culprit: a small support
  library Kokoro quietly needs was being left out of the build. It's back — and
  when anything speech-related does go wrong, the real reason is now written to the
  diagnostics log (**Help > Save Diagnostics**) instead of vanishing behind a vague
  message. Thank you, Richard.

- **Piper voices preview cleanly.** Also from Richard: previewing a freshly
  downloaded Piper voice failed with an internal error. Fixed — preview and saving
  audio both work.

- **Testing a downloaded Piper voice no longer says the model file is missing.**
  A second, separate Piper bug: the voice-preview code was looking in the wrong
  place for the file it had just downloaded. Fixed.

- **Offline speech-model downloads no longer crash with a cryptic Python error.**
  Downloading a whisper.cpp or Faster Whisper model could fail partway through
  with `'NoneType' object has no attribute 'write'` — an internal progress-bar
  library trying to write status to a console QUILL doesn't have. Fixed.

- **The braille pack's Test button now actually reports the installed LibLouis
  version**, instead of always saying "unknown."

- **DECtalk speaks instead of opening a file.** Testing a DECtalk voice in the
  installed app used to pop open a program file rather than talk. It speaks as it
  should now.

- **Read Aloud stops reading the punctuation.** Headings, bold text, and links in
  a Markdown document were being read aloud as literal `#` and `*` symbols
  (especially garbled with Piper). They're turned into plain, speakable text first
  now — live and on export.

- **Whisper model downloads are sturdier**, going through the same well-tested
  library Faster Whisper already uses, so a hiccup on the model host's side gives
  you a clear message instead of a mystery failure.

- **Offline transcription no longer mistakes the `openai-whisper` CLI for
  whisper.cpp.** If you had the `openai-whisper` PyPI package installed,
  QUILL could grab its `whisper` command and run it with whisper.cpp flags,
  failing with a confusing error. It now requires the real whisper.cpp
  binary name (`whisper-cli`/`main`), so your genuine whisper.cpp install is
  used and the OpenAI CLI is left alone. (#931)

- **Voice preview feedback.** Previewing a voice no longer overlaps a previous
  preview's audio or announcement. Slow voice synthesis now plays a short cue and
  (by default) says "Generating preview, please wait," and the Preview/Test button
  turns into a Stop button while a preview is active.

### Audio Studio: progress, cancellation, safer closing, and cleaner output

- **Audio Studio's batch export finally has a working Cancel button.** There was no way to stop a run in progress short of killing QUILL — no Cancel button, and Escape just dinged. Both now work: whatever file is currently synthesizing finishes normally first (no half-written audio files), then the run stops before the next one starts.

- **Audio Studio's log file now shows the same chunk-by-chunk progress you see on screen**, not just which document is up next — useful for checking on (or diagnosing) a run without watching the screen.

- **Audio Studio: WAV exports get their own subfolder; MP3 still lands beside your document.** WAV output now goes into an **Audio Output** subfolder next to the document it came from, instead of landing right beside it the way MP3 does. Exporting recursively through nested folders gives each subfolder its own Audio Output folder rather than funneling everything into one shared top-level folder.

- **QUILL now warns before Alt+F4 (or the window's close button) silently abandons a running Audio Studio export.** Closing used to just exit immediately, mid-job, with no warning. QUILL now asks first — close and stop it now, or leave QUILL open to finish — and points at **File > Send to Tray** as a way to keep it running quietly in the background instead. Routine background activity (search/replace, dictation, downloads) is unaffected; the warning is reserved for real, hard-to-redo work.

---

## AI that is understandable, local-friendly, and actually configurable

AI setup should never imply that a local provider needs a cloud key, hide a working Ollama installation, or send you to a terminal for routine setup. Beta 2 turns those rough edges into a guided path that respects local, remote, and cloud choices.

### Ollama and the AI Setup Wizard

- **The AI Setup Wizard no longer treats a working local Ollama as "not there."** A never-configured install's saved settings default to "Ollama," which the wizard's "remember what you already set up" step mistook for proof you'd deliberately added it — so on a brand-new install, Ollama was silently marked already-added and dropped out of the Provider list, leaving only key-requiring cloud options to pick from. It now confirms a local Ollama server actually answers before treating it as configured.

- **The AI Setup Wizard's Connect step no longer lands you in the API key field, and Remove no longer looks clickable before you've selected anything.** Reaching "Connect your AI providers" (or removing a provider) could jump focus into an API key field when the next provider in line needed one — easy to mistake for "Ollama needs a key too." Focus now always starts on the Provider list. Remove selected also stays disabled until you've actually picked something in the Added list.

- **Ollama's server address is now a real, editable field.** The wizard always checked `localhost` only, even though pointing it at Ollama running on another computer on your network was meant to work. A new **Ollama server address** field (shown only when Ollama is selected) is now used everywhere the wizard talks to Ollama — verify, model listing, and Finish — so a remote or self-hosted Ollama is a genuine, working choice.

- **Pull an Ollama model right from the Setup Wizard — no terminal required.** Choosing your default model used to just tell you to run `ollama pull <model>` yourself in a terminal. The Model step now shows which recommended models are already installed and offers a **Pull model** button for the rest, with live download progress, selecting the model for you the moment it's ready.

- **The AI Hub's API key field now correctly greys out for local Ollama.** It stayed active for every provider regardless of whether a key was actually needed, which is why Ollama's key field looked required even though nothing ever enforced it.

### Agent SDKs, model discovery, and interrupted installs

- **The AI Setup Wizard no longer gets stuck** showing an engine like OpenAI as
  "active" with no way to configure it after an interrupted install. Set Up works
  again.

- **OpenAI Agents SDK and Claude Agent SDK now have a way to add an API key.**
  Previously, once installed, there was no in-app way to configure either —
  **Set Up** in the AI Hub's Engines tab now opens a small dialog to paste,
  save, or remove the key, applied right away with no restart needed.

- **The AI Hub now reads your Ollama models for real.** Each Ollama model
  shows its actual abilities (Vision, Tools) discovered via `/api/show`
  instead of a hardcoded list, and picking the Ollama provider auto-probes
  whether Ollama is running and how many models you have — so you know at a
  glance whether local AI is reachable.

---

## Explore GitHub without leaving your editor

QUILL could already open and save files from a GitHub repository. Now it can
also **show you what's going on in one** — the issues, pull requests, branches,
commits, tags, releases, and workflow runs — without leaving the editor or
firing up a browser. **File > Open from Remote > GitHub Items...** opens a
read-only viewer modeled on the open-source [GHManage](https://github.com/kellylford/GHManage)
viewer, built keyboard- and screen-reader-first.

Type `owner/repo` and load (if you're already editing a file you opened from
GitHub, the repository is filled in for you). Pick a view — the combined
Issues & PRs inbox, Branches, Commits, Tags, Releases, or Workflow Runs — and
the list shows one row per item while a details box below shows the full text.
In the Issues & PRs view you can also filter by issues/PRs/both, by open/closed/
all, and sort by number, title, last-updated, or comment count.

Two list modes matter for screen readers: **Quick** shows compact cells, and
**Full** spells each one as `field: value` (`number: 208, type: ISSUE, state:
OPEN`) so your reader announces a self-describing line per row instead of bare
values. Select an issue or PR and the comment thread loads beneath it; **Alt+N**
and **Alt+P** jump between comments, announcing "Comment N of M." **Enter**
opens a row in your browser — and on a branch row, it drills into that branch's
commits. **Ctrl+R** refreshes, **Ctrl+O** opens in the browser, **Ctrl+G**
jumps to an issue or PR by number, and **View More** loads the next page.

It's read-only for now — you can browse and open, but not close, reopen, or
comment from inside QUILL. The same gates apply as the other GitHub commands:
disabled in Safe Mode, first-run consent, and anonymous access for public
repositories (lower rate limit) or your stored token for private ones. (#924)

### Mastodon posts now respect language and instance limits

- **Posting to Mastodon: set a post's language, and the counter respects your instance's limit.** A post written in Italian can be filed under the Italian preset instead of your account default; and if your instance allows more (or fewer) than 500 characters, the live counter now knows — via a one-time lookup of the instance's own limit (#922), including non-Mastodon forks like GoToSocial and Pleroma that don't implement the v2 lookup QUILL tries first.

---

## macOS: a top-to-bottom platform transformation

QUILL's macOS support got a top-to-bottom review across several passes this
release. Everything Mac-specific lives here in one place. We develop on
Windows, so every Mac fix below was made without a Mac in front of us, and a
few genuinely need your eyes to close out. Items marked **(tester results
wanted)** are code-complete and unit-tested here but only show their real
effect on a Mac — please try the fix and tell us through **Help > Report a Bug**
(or the linked support issue) if a symptom persists, so we can close it out or
reopen it.

This work reaches far beyond a handful of compatibility patches. It makes QUILL more recognizably Mac-like in its menus, shortcuts, launching, voices, Keychain behavior, portable mode, Finder integration, security, theming, clipboard use, announcements, and build discipline.

### The complete macOS improvement pass

- **Built-in keymap profiles now stay platform-aware.** The shipped keymap
  profiles no longer override the platform-specific defaults for quit,
  back/forward location, and document switching, so macOS users get the correct
  Cmd-based shortcuts instead of Windows-only overrides.

- **AI, compare, and dark-mode shortcuts now fire as advertised.** The
  proofread, translate, compare-navigation, and dark-mode commands now honor
  the keybindings shown in the UI and the keymap editor instead of silently
  ignoring them.

- **Preferences now appears in the standard macOS app-menu location.** The
  Preferences command is wired to the stock macOS menu id, making it reachable
  in the Quill app menu alongside About and Quit.

- **macOS launch paths are now platform-safe.** Opening a file, revealing a
  folder, launching an installer, or previewing a voice sample no longer relies
  on Windows-only `os.startfile` behavior on macOS; those flows use the native
  macOS launch path instead.

- **macOS: Pandoc from the pandoc.org installer is found.** A QUILL window
  opened from Finder doesn't inherit a Terminal's folders, so a real Pandoc
  install could look missing. QUILL now checks the usual locations directly.

- **macOS: LibreOffice import works on a standard install.** The three
  LibreOffice call sites (XLS, legacy Office, and Apple Pages import) used a
  bare `soffice` command that is never on PATH on a Mac, so a genuine
  LibreOffice install looked missing. QUILL now resolves
  `/Applications/LibreOffice.app/Contents/MacOS/soffice` directly (with a
  Homebrew/installer hint when it's missing). (#41)

- **macOS: a Homebrew or nvm-installed Node is found from a Finder-launched app.**
  A QUILL window opened from Finder gets a minimal PATH and never sources your
  shell profile, so a real on-disk Node install was invisible to the
  external-engine allowlist. The lookup now checks `/usr/local/bin`,
  `/opt/homebrew/bin`, `/opt/local/bin`, and the highest version under
  `~/.nvm/versions/node`. (#48)

- **macOS: earcons are no longer silent.** The app had no audio backend at all
  on macOS, so sound notifications never played even with the bundled pack
  selected. Fixed.

- **macOS: opening a file from Finder, the Dock, or Terminal now actually opens
  it**, instead of landing you in a blank document. Also fixed: any keyboard
  shortcut using the Command key silently did nothing, and
  Ctrl+Tab/Ctrl+Shift+Tab for switching between open documents landed on a
  toolbar button instead of switching (macOS reserves that combination) —
  document switching on macOS is now Cmd+Shift+]/[.

- **macOS: the QUILL key answers to a real Ctrl+Shift+` press.** macOS reports
  the Cmd key, not the physical Control key, through the check QUILL was using
  — so a literal Ctrl+Shift+` press went unrecognized. It's recognized now.
  (Cmd+Shift+` is macOS's own "cycle windows" shortcut and will keep going to
  the OS first; reassign it in System Settings > Keyboard Shortcuts if you'd
  rather use Cmd.)

- **Windows-only UI strings no longer render verbatim on macOS (#37).** Strings
  that named a Windows-only mechanism now adapt to the platform: the credential
  vault is "macOS Keychain" instead of "Windows Credential Manager" in API-key,
  publish, and forget-key messages; the dictation status says "System dictation"
  instead of "Windows dictation"; the setup wizard says "In my user profile"
  instead of "In my Windows user profile"; and help text that examples a
  "Ctrl+Alt" chord says "Cmd+Alt" on macOS.

- **Read Aloud finally speaks on macOS.** Every WAV-based voice engine (Piper,
  Kokoro, ElevenLabs, SAPI5, DECtalk) was silent on macOS — the live playback path
  only knew about Windows' `winsound` and silently threw each synthesized clip
  away. It now plays through macOS's `afplay`.

- **The earcon volume slider now works on macOS.** `NSSound` had no volume
  control wired, so the slider was a silent no-op. It now sets the volume on
  each played sound.

- **Whisper recommends the right model for your Mac's actual RAM.** QUILL
  reported a flat 8 GB on every Mac, so a 32 GB machine was told to use the
  small model. It now reads real memory via `sysctl`.

- **Three Mac keyboard collisions fixed.** `Ctrl+H` (Replace) became `Cmd+H`
  (macOS Hide), `Ctrl+M` (pop mark) became `Cmd+M` (Minimize), and `Ctrl+Space`
  (select chunk) became `Cmd+Space` (Spotlight) — all dead by default on macOS.
  They now default to `Cmd+Alt+F`, `Cmd+Alt+M`, and `Cmd+Alt+Space`, and Find
  Next/Previous now use the macOS-standard `Cmd+G` / `Cmd+Shift+G` (so you don't
  have to hold Fn for F3). Provisional picks — tell us if a chord collides with
  something on your setup.

- **DECtalk and MathCAT are no longer offered as downloads on macOS** (their
  only backends are Windows `.dll`s that can never load on a Mac), and the
  Dictation description no longer promises SAPI 5 on macOS (it doesn't exist
  there — Whisper is the path).

- **The braille pack download is Windows-only on macOS, which now points you to
  Homebrew liblouis instead.** The bundled pack ships a Windows `lou_translate`
  binary that could never run on a Mac, so offering it there was misleading. On
  macOS, QUILL now detects a Homebrew liblouis install (`brew install liblouis`)
  automatically and uses it. (#47)

- **No more duplicate "About Quill," and no stray `Cmd+F4`.** macOS showed two
  About entries (the Application menu and Help); the Help copy is gone. The
  redundant `Cmd+F4` close shortcut was Windows-only and never idiomatic on Mac.

- **VoiceOver announcements are gentler and bounded.** A runaway status message
  is now capped so it can't become an unreadable wall of text, and routine
  status no longer interrupts what you're already hearing (only narration that
  has to interrupt does).

- **Your documents are safer on a crash.** Saving a document and writing an
  autosave recovery snapshot are now atomic (write to a temp file, fsync, then
  rename) — a crash mid-write can no longer corrupt your real file or leave a
  truncated snapshot as the thing you recover.

- **The macOS build doesn't drag Windows-only packaging tools onto other
  platforms**, the dictation "microphone unavailable" message no longer says
  "Windows microphone permissions" verbatim, and the macOS release build now
  actually runs the test suite in CI — so the macOS-only tests (Keychain,
  high-contrast, screen-reader detection) finally run somewhere.

- **Launch QUILL from source by double-clicking in Finder.** A new
  `run-from-source.command` wrapper runs in Terminal on double-click (a `.sh`
  would only open in a text editor), forwarding to `run-from-source.sh` — no
  terminal needed. The first-run Gatekeeper prompt and its right-click → Open
  workaround are documented in the file header. (#923)

- **Tray status messages say the right thing on macOS.** QUILL's six
  minimize-to-tray / restore messages ("Quill is running in the system tray",
  "Minimized to system tray", etc.) used Windows terminology verbatim, but on
  macOS the feature renders as a menu-bar status item. They now say "menu bar"
  on macOS (and keep saying "system tray" on Windows).

- **The Settings default-folder hint no longer shows a Windows path on macOS.**
  The blank-default hint used to read `e.g. C:\Users\YourName\Documents` even on
  a Mac, where that path doesn't exist. It now shows `e.g.
  /Users/YourName/Documents` on macOS.

- **A background engine install can no longer crash a closed AI Hub.** The
  install-complete callback in the AI Hub Engines tab already guarded the
  re-enable of its Set Up button against a destroyed panel (an earlier fix),
  but the three calls after it were unguarded — closing the Hub before an
  install finished could still raise. All four post-install calls are now
  guarded, so a late callback against an already-closed Hub is a clean no-op.

- **Bundled tool paths are found on macOS.** QUILL's bundled-tool lookup used
  Windows backslashes in the relative path (`pandoc\pandoc.exe`); on macOS a
  backslash is a literal filename character, so the bundled binary was never
  found even when it genuinely exists. The paths now use forward slashes, which
  compose correctly on both platforms.

- **Short keychain secrets no longer leak into logs.** The macOS `security`
  CLI takes a secret as `-w <secret>` in separate arguments, and a short or
  non-hex secret slipped past the redaction that guards the diagnostics log.
  The value that follows `-w` is now redacted explicitly before logging, so a
  key passed to Keychain can't appear in a submitted report. (#60/#73)

- **Work Persona launchers are real on macOS.** (tester results wanted)
  Generating a shortcut for a persona used to write a Windows `.bat` file on
  macOS — useless on a Mac. It now writes a Finder-launchable `.command` shell
  script (with the executable bit set), so double-clicking it in Finder opens
  QUILL straight into the persona. Please confirm a generated persona shortcut
  opens QUILL into the right persona when double-clicked in Finder. (#38)

- **"Toggle hidden files" is Cmd+Shift+. on macOS.** (tester results wanted) In
  the Simple File Open dialog, the hidden-files toggle was bound to Ctrl+H —
  which is macOS's system Hide-window shortcut, so it hid QUILL instead. It now
  uses the Finder convention Cmd+Shift+. on macOS (and stays Ctrl+H on Windows).
  Please confirm Cmd+Shift+. toggles hidden files in the simple open dialog.
  (#51)

- **Very long Read Aloud spans no longer risk command-line overflow.** (tester
  results wanted) eSpeak synthesis passed the whole utterance as a command-line
  argument, which can overflow the OS command-line length (Windows ~32,767
  chars) on a very long span and truncate or abort with no clear error. Long
  input (over 8,000 characters) is now piped to eSpeak via `--stdin` instead.
  Please confirm a very long Read Aloud span synthesizes fully without
  truncation. (#64/#77)

- **PDF import now tells you what actually went wrong.** A PDF that couldn't be
  read used to collapse every failure into one "this looks like a scanned PDF —
  use OCR" message, even when the real problem was a password, a corrupt file, or
  a missing extractor. It now distinguishes four cases — *encrypted* (supply or
  remove the password; suggests `qpdf --decrypt`), *damaged* (repair or re-export;
  suggests `qpdf --check`, and notes OCR won't help a corrupt file),
  *scanned/image-only* (genuinely points at OCR), and *no extractor installed*
  (points at Help > Download Optional Components) — each with its own remedy.
  (#58)

- **Keymap packs no longer silently steal macOS system shortcuts.** Applying a
  keymap pack (VS Code, Word, Notepad++...) on macOS used to apply its bindings
  verbatim, so a pack chord could quietly land on a macOS system shortcut (Cmd+H
  hides, Cmd+M minimizes, Cmd+Space is Spotlight, F9-F12 are Mission Control) or
  collide with another command — because wx maps Ctrl to Cmd at runtime, a stored
  "Ctrl+G" and a default "Cmd+G" are the *same* shortcut on a Mac even though they
  read as different strings. Pack overrides are now checked on macOS against the
  runtime chord (with Ctrl folded to Cmd for the comparison only), and any
  override that lands on a system-reserved chord or collides with an existing
  binding is quietly dropped instead of stealing it. (#4)

- **Screen capture's "not available" message now says why.** On macOS, the bare
  "only available on Windows" message now names the macOS Screen Recording
  permission you'd need to grant (System Settings > Privacy & Security > Screen
  Recording) and points at the built-in Cmd+Shift+3/4/5 shortcuts as the
  in-the-meantime path. (#5)

- **"Set as default editor" no longer looks successful when it did nothing.** On
  macOS, setting QUILL as the default editor runs through `duti`, a third-party
  Homebrew tool that isn't preinstalled — so the action was a complete no-op in the
  common case, with no signal. It now reports exactly what happened: success when
  `duti` set the associations, or a clear "duti isn't installed, install it with
  `brew install duti`" message (noting the app bundle's own Info.plist
  associations still apply) when it isn't. (#8)

- **Dark Mode and high-contrast detection use the right source.** (tester
  results wanted) QUILL reads Dark Mode through wx's system-appearance API
  (`SystemSettings.GetAppearance().IsDark()`), which modern wx reports
  correctly on macOS, and detects Increase Contrast through the OS default — so
  a theme can follow the system instead of being manual-only. The earlier
  custom `defaults read`-based Dark Mode and Reduce Motion helpers had no UI
  consumer (dead code) and were removed. Please confirm QUILL's theme follows
  Dark Mode when you toggle it in System Settings. (#6)

- **The speech self-test works on macOS.** (tester results wanted) Verifying a
  downloaded speech engine used to depend on Windows SAPI 5 to synthesize a test
  clip — so "Test" always failed on a Mac. It now synthesizes the test clip with
  the built-in `say` command on macOS (and SAPI 5 on Windows), so the
  speak-to-transcribe confidence loop can actually run. Please confirm Test
  reports OK for a Whisper or Vosk engine on your Mac. (#29)

- **Pausing Read Aloud mid-sentence no longer skips the sentence.** (tester
  results wanted) When you paused eSpeak (or a WAV-based engine) partway through
  a sentence, the cursor advanced as if the whole sentence had been spoken, so
  resume skipped it. The cursor now stays at the sentence start when you pause
  mid-sentence, so resume re-reads the partial sentence. (#65/#78)

- **Keychain secrets never reach the command line on macOS.** Storing a secret
  (an AI API key, an SSH passphrase) used to fall back to the `security` CLI,
  which takes the value as a command-line argument — visible to any process on
  the machine and to the diagnostics log. QUILL now talks to Keychain through
  the native Security framework (pyobjc) first, passing the secret only in the
  Keychain item's data field where it never becomes an argument. The leaky CLI
  fallback still exists for machines without pyobjc, but it now warns the first
  time it's used that the secret will touch the command line. The no-leak
  guarantee is pinned by cross-platform unit tests. (#1/#16/#43)

- **Portable mode no longer silently loses your credentials on macOS.** Off
  Windows there's no portable single-folder credential store, so a portable
  Mac build used to drop your keys with no signal. It now routes
  load/save/delete to the login Keychain (the best available store) and logs a
  warning that Keychain storage is system-level, not portable. (#35)

- **"Set as default editor" refreshes LaunchServices on macOS.** Registering
  QUILL as the default editor used to write the `duti` associations but leave
  macOS's LaunchServices database stale, so Finder still opened files in the old
  app until a reboot or a manual `lsregister`. The action now force-registers
  the app bundle with LaunchServices (`lsregister -f`) right after setting the
  associations, so the new default takes effect immediately. The app-bundle
  detection was also fixed: it walks up from the running executable to find the
  enclosing `.app` instead of only recognizing a bundle when launched from
  inside one. (#74)

- **macOS announcements now speak when VoiceOver is off.** Every status
  announcement ("Saved," "Ln 12, Col 7," the QUILL-key chord...) is posted to
  VoiceOver, which is a no-op unless VoiceOver is running — so a low-vision Mac
  user running without VoiceOver heard nothing. QUILL now detects whether
  VoiceOver is running and, when it isn't, speaks the announcement through the
  native macOS speech synthesizer (`NSSpeechSynthesizer`), mirroring the Windows
  SAPI self-voice fallback. The native voice catalog is also wired so the system
  voice list is available to the app. (#2)

- **The Window menu behaves like a real macOS Window menu.** (tester results
  wanted) QUILL's Window menu (Next/Previous/Close-Other/Send-to-Tray) is now
  registered with the system as the Window menu, so AppKit moves it to its
  conventional slot (just left of Help) and merges in the standard items a Mac
  user expects — Minimize (Cmd+M), Zoom, Bring All to Front, and the live
  window list — alongside QUILL's own entries. Please confirm the Window menu
  sits in the right place and shows the standard Mac items. (#76)

- **"macOS (system voice)" is now a first-class Read Aloud engine.** (tester
  results wanted) The native TTS backend that powers the self-voicing fallback
  (#2) is now wired as a selectable engine: it appears in the Speech Hub engine
  list and the settings engine-choices on macOS, the voice picker lists system
  voices, the Preview button speaks a sample, Read Aloud reads with
  pause/stop, and batch export produces audio — all through the built-in `say`
  command, so it works even on a Mac without pyobjc. Please confirm the voice
  picker lists your system voices, Preview speaks, Read Aloud reads with
  pause/stop, and export-to-file produces audio. (#21/#75)

- **Extend-selection follows native Mac semantics.** On macOS, Option now
  extends the selection by word and Cmd by line/document, matching what Mac
  users expect (it used to apply Windows-oriented modifiers).

- **More macOS polish from the completion pass.** Dialog OK/Cancel buttons
  use the native Mac order; paste-as-Markdown tries the macOS `public.html`
  clipboard flavor; the New Sticky Note hotkey speaks a clear status on macOS;
  the close handler no longer calls Hide+Veto with no tray icon present; and the
  diagnostics bundle now collects macOS `~/Library/Logs/DiagnosticReports`
  crash logs alongside the Windows ones.

---

## Install QUILL your way

Whether you want the smallest regular installer, a portable copy that carries its optional pieces with it, a command available from every terminal, or a machine that must never touch the internet, Beta 2 gives you a clearer path.

### Fully offline, when you need it

QUILL normally keeps its installer small by downloading the bigger optional
pieces — Pandoc, offline speech engines, neural voices, the braille pack, and
more — only when you first reach for them. That's the right default for most
people, but it assumes you have an internet connection at some point after
install. A new **Offline Edition** build removes that assumption entirely:
every optional component ships inside the installer and the portable bundle
up front, so QUILL is fully functional the moment it's installed, with no
internet connection ever needed — right for an air-gapped machine, a
locked-down work laptop, or anywhere your first login can't reach the
internet.

**Help > Download Optional Components** knows the difference: in the Offline
Edition, every bundled piece shows as **Bundled** instead of offering a
Download button, since there's nothing left to fetch. The regular, smaller
installer and portable download you already know are unchanged and remain
the default choice for everyone else.

### A simpler installer — and a lighter one

- **No more component checkboxes.** Beta 1's installer asked you to pick optional
  parts — several of which did nothing, because they're fetched on demand anyway.
  The installer now just installs QUILL; everything optional arrives when you first
  reach for it.

- **A smaller download.** Kokoro's neural-voice engine is now fetched on demand
  with everything it needs, trimming the installer noticeably — you download
  Kokoro only if and when you want those voices.

### Add QUILL to PATH when that fits your workflow

- **Quill can add itself to PATH, so `quill <file>` works from any Command Prompt or PowerShell window.** The installer now offers an opt-in **"Add Quill to PATH"** task (off by default, cleanly removed on uninstall), and the user guide's command-line examples now lead with `quill.exe` — the command every install and portable copy actually has — instead of `python -m quill`, which only works from a source checkout. (#941)

---

## Trust is a feature

A community-built editor must be dependable not only when everything works, but also when something fails. Beta 2 strengthens the path from error to report, protects more personal information, verifies extension signatures for real, and makes support details far more actionable.

### Bug reporting that actually reaches us

After upgrading, some of you found the bug reporter saying "no token." The
Windows build wasn't including the built-in reporting token, so it shipped empty.
It's fixed at the source, and now **every build refuses to ship without it —
release, beta, or a local test build, on Windows and macOS alike, with no
opt-out** — so a tokenless bug reporter can never reach anyone again. If the
token is ever missing at runtime, QUILL opens the online bug form for you —
reading the instructions aloud — instead of leaving you stuck. And if an
already-running build is found to be missing the token, **Check for Updates**
offers to reinstall the latest release even at the same version — with a dialog
that says it restores the bug-report token, so "update to the version you
already have" is not confusing. A silent background check only records a
notification (it never auto-reinstalls the running version); use **Skip this
version** to silence it, and it stops the moment the token is back.

This is the fix behind every "please try this and tell us" ask in these notes —
it's what makes Report a Bug dependable on every install, Mac included.

### Quillin signatures are now genuinely verified

- **The "Signature" line in the Quillins Manager now actually verifies.** It was always there — `verified`, `invalid`, or `unsigned` — but the cryptography library it needs (PyNaCl) was a developer-only dependency that no shipping build included, so on your install it always read "PyNaCl is not installed" and could never tell a publisher-signed Quillin from a tampered one. PyNaCl is now bundled with Quill, so the signature check is real on every install. The `.minisig` sidecars shipped with signed Quillins finally mean something at the detail view.

Together, these two changes cover both sides of trust: normal shipping builds now perform the real cryptographic check, while an unusual or incomplete environment fails gracefully instead of taking the manager down with it.

### The Quillins Manager stays open when you need it

- **The Quillins Manager no longer crashes on open.** A reporter hit this
  right away: just viewing a Quillin's details crashed with a
  `ModuleNotFoundError`. The signature-status check (is this Quillin
  publisher-signed?) depended on a library that's only ever installed for
  QUILL's own development and release process, never in the shipped app —
  it now reports "signature check unavailable" instead of taking the
  whole dialog down with it.

---

## Reliability work that protects real work

Many of the fixes below are quiet by design. They remove freezes, false crash recovery, stale focus, clipboard races, encoding failures, and diagnostics gaps — the kinds of problems that disappear when the software is doing its job well.

### Windows shutdown, shell integration, and clean exits

- **QUILL no longer thinks it crashed when Windows shuts down or logs off with it open.** The OS session-end event now records a clean exit, so your next launch doesn't offer crash recovery for a session that ended normally. (#920)

- **Windows shell-integration registration no longer crashes on the Python 3.13 runtime.** An empty binary registry value (the `OpenWithProgids` entry) that older Pythons silently accepted now gets the right type, so file associations register cleanly again. (#921)

### Clipboard and community-reported crashes

- **"Failed to get data from the clipboard" errors during cut/paste are fixed.**
  A screen reader or clipboard-history tool briefly holding the clipboard used to
  show this error immediately; QUILL now gives it a brief moment before giving up.

- **Fixed four crash reports sent in through user feedback:** the Spell Check
  Language chooser, word prediction after recovering from a crash, and the AI
  Hub's Engines tab closing mid-install.

### Files, encodings, conversions, startup, and support codes

- **Opening Profiles and Features no longer crashes** — a translated profile name
  wasn't being fully resolved before the list was built.

- **Non-UTF-8 text files open cleanly.** A `.txt` or `.md` saved in an older
  Windows encoding (a curly quote or en-dash, no UTF-8 marker) used to crash on
  open. QUILL now falls back gracefully and tells you in the status bar.

- **A stalled graphics-card check can't freeze the app.** The speech options'
  hardware probe ran with no timeout on the main thread every time you opened the
  dialog; it's timeout-guarded and runs once per session now.

- **Convert Non-ASCII to HTML Entities no longer freezes QUILL on a large file.**
  On a document over a megabyte, this could take the better part of a minute —
  and QUILL, along with your screen reader, went unresponsive for the whole
  time. It now runs in the background instead.

- **Converting a UTF-8 file's non-ASCII characters no longer leaves a pointless
  byte-order mark behind.** Once every non-ASCII character becomes an HTML
  entity, the file is pure ASCII — but it still saved with a three-byte UTF-8
  marker at the start. That marker is dropped when nothing in the file needs
  it anymore.

- **First-run "Personalise QUILL" now offers to restart** when your choice of
  where to store data needs one to take effect — the same prompt Preferences
  already gives, instead of the choice silently waiting for your next launch.

- **The Outline Navigator (Ctrl+Shift+O) opens again.** It — and the EPUB and Quick
  Nav surfaces that share the same dialog — could crash instead of opening, because
  of an invalid call on the tree control's hidden root. Fixed.

- **Crash reports no longer carry your Windows username.** If your portable copy
  lived inside your home folder, the local crash-report file path was included
  verbatim in a submitted report's metadata — the one place that path wasn't
  already being scrubbed. It's redacted the same way as everywhere else now.

- **Errors carry a short support code** (like `[QUILL-SPEECH-WHISPER-DL-404]`), and
  it rides along in crash reports automatically — so if you paste an error to us,
  we can pinpoint the exact cause. Every one of QUILL's internal error types now
  has one.

---

## With gratitude — and with momentum

Beta 2 is a community release in the truest sense. **Elena Brescacin**
([elettrona](https://github.com/elettrona)) gave QUILL its first non-English voice.
**Richard Wells** chased down the Kokoro and Piper voice issues with patient,
detailed reports and diagnostics. And every tester who hit an odd crash, a stuck
focus, a missing language, or a confusing download and took the time to tell us —
this release is yours. Please keep it coming.

Beta 2 proves something bigger than any single feature: when people are heard, when feedback is treated as design input, and when accessibility is understood as a shared responsibility, software can become more useful, more humane, and more joyful with every pass.

**This is how QUILL grows: openly, thoughtfully, stubbornly, and together. Built by the community. Built for the community. Built for every one of us.**
