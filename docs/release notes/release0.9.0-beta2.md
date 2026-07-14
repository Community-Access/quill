# QUILL 0.9.0 Beta 2

## Polished by the people who use it.

*From Community Access. Free. Optional by design. Private by default. Yours to make quiet.*

Every single line below started life as a message from a beta tester — a crash
report, a "this felt weird," a voice that wouldn't speak, a language that wasn't
there. You wrote in; we listened; this is the result. Keeping the promise made at
Beta 1, this is overwhelmingly your reports, turned into fixes and polish,
especially around getting the optional pieces you want — with **one exception**:
a page indicator, because enough of you asked for it that it couldn't wait.

This is the friendly companion to the **"0.9.0 Beta 2"** section of `CHANGELOG.md`.
The same words appear in-app under **Help > What's New** and on **Check for Updates**.

Grazie, thank you, and keep the reports coming. 💙

---

## Getting the extras you want, reimagined

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

## A page number, honestly presented

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

## A simpler installer, and a lighter one

- **No more component checkboxes.** Beta 1's installer asked you to pick optional
  parts — several of which did nothing, because they're fetched on demand anyway.
  The installer now just installs QUILL; everything optional arrives when you first
  reach for it.
- **A smaller download.** Kokoro's neural-voice engine is now fetched on demand
  with everything it needs, trimming the installer noticeably — you download
  Kokoro only if and when you want those voices.

## Speech that just works

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
- **macOS: Pandoc from the pandoc.org installer is found.** A QUILL window opened
  from Finder doesn't inherit a Terminal's folders, so a real Pandoc install could
  look missing. QUILL now checks the usual locations directly.

## Kinder to screen readers

- **Dialogs open on the first real control**, not the OK/Cancel button or a tab
  strip. The Speech Hub, Manage Speech Models, Manage Voices, the AI Hub, About,
  and Quillin preferences all land you where you can start working — and because
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
- **macOS: the QUILL key answers to a real Ctrl+Shift+` press.** macOS reports the
  Cmd key, not the physical Control key, through the check QUILL was using — so a
  literal Ctrl+Shift+` press went unrecognized. It's recognized now. (Cmd+Shift+`
  is macOS's own "cycle windows" shortcut and will keep going to the OS first;
  reassign it in System Settings > Keyboard Shortcuts if you'd rather use Cmd.)

## Language, stability, and support

- **Italian is here to switch to.** Elena Brescacin's beautiful, complete Italian
  translation shipped in Beta 1 — but a build step meant it never actually appeared
  under Change Display Language. It does now, all 1,100-plus phrases of it. Grazie
  mille, Elena. (Tools > Writing and Language > Change Display Language.)
- **Danish joins the Braille Translation menu.** The grade 1 and grade 2 tables
  shipped with the engine all along; Danish just never made it onto QUILL's list.
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

## Three fixes that unblock real work

- **PDF and document import works out of the box again.** A tester on a clean
  install hit "can't extract text from PDFs — no extraction engine available."
  The free local converter and PDF text extractors were described in-app as
  built-in, but weren't actually installed by the shipping build. They now ship
  with QUILL on every install, so File → Import just works — and if a PDF has no
  selectable text, QUILL now tells you it looks like a scanned document and points
  you to OCR, instead of a confusing "no engine" message.
- **Report a Bug works even if you never signed in.** After upgrading, some of you
  found the bug reporter saying "no token." The Windows build wasn't including the
  built-in reporting token, so it shipped empty. It's fixed at the source (and the
  release now refuses to build without it, so this can't happen again), and if the
  token is ever missing, QUILL now opens the online bug form for you — reading the
  instructions aloud — instead of leaving you stuck.
- **"Casual Writer" finally just lets you write.** The profile was quietly leaving
  AI, GLOW review, remote files, analysis, watch folders, notebooks, and developer
  tools switched on. Choose Casual Writer now and those step out of the way, for a
  clean "write, format, print, send" workspace — while read aloud, voice commands,
  dictation, and braille stay right where they are, because a simpler profile
  should never be a less accessible one. Want any of it back? Preferences >
  Profiles and Features, one toggle each.

---

## With gratitude

Beta 2 is a community release in the truest sense. **Elena Brescacin**
([elettrona](https://github.com/elettrona)) gave QUILL its first non-English voice.
**Richard Wells** chased down the Kokoro and Piper voice issues with patient,
detailed reports and diagnostics. And every tester who hit an odd crash, a stuck
focus, a missing language, or a confusing download and took the time to tell us —
this release is yours. Please keep it coming.
