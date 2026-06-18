# QUILL Braille Mode Plan

## Working Title

QUILL Braille Mode

## Product Vision

QUILL Braille Mode will provide a lightweight, screen-reader-first
environment for opening, editing, validating, navigating, translating,
and tracking progress in BRF files, with a focus on English UEB
workflows.

This feature should not attempt to replace Duxbury, BrailleBlaster, or
full production transcription systems in its first release. Instead,
QUILL should become a fast, dependable, accessible tool for blind users
who need to work directly with BRF files, understand where they are,
track transcription or proofreading progress, and optionally perform
English UEB translation without bloating the editor.

## Primary Audience

The primary audience is screen reader users, especially:

- Blind transcriptionists
- Blind proofreaders
- Blind braille readers working with BRF files
- Blind developers or educators reviewing braille output
- Users who need to inspect or lightly edit BRF without launching a full
  transcription suite

Visual preview features should be minimal, optional, and never required
for the workflow.

## Core Philosophy

QUILL should not visually imitate braille as its main purpose.

QUILL should make BRF files understandable, navigable, inspectable, and
manageable through speech, keyboard commands, status information, and
structured navigation.

The experience should answer these questions instantly:

- What braille page am I on?
- What print page am I on, if known?
- What line and cell am I on?
- Am I on a continuation page?
- Is this page too long?
- Is this line too long?
- Where did I leave off?
- Which pages have I proofed?
- Which pages still need review?
- Is the file likely valid BRF?
- Can I translate or back-translate this section without installing a
  huge package?

## Scope Summary

### Included in QUILL Core

QUILL core should include:

- Open and save `.brf` and `.brl`
- Preserve all spaces, line breaks, and form feeds
- Detect BRF page breaks
- Calculate braille page, line, and cell position
- Status bar support
- Screen-reader announcement commands
- Go to braille page
- Go to print page when detectable
- Insert page break
- Validate BRF layout
- Detect page numbering conventions
- Track reading/proofing progress
- Save progress in a sidecar file
- Provide keyboard-first warnings and navigation

### Optional Add-On

A separate optional Braille Pack should include:

- Liblouis runtime
- English UEB Grade 1 table
- English UEB Grade 2 table
- Required table dependencies only
- Translation worker process
- Plain text to UEB BRF
- BRF to draft print text
- Translate selection
- Back-translate current page
- Back-translate selection

This keeps the base editor lightweight.

## Deployment and Packaging the Braille Pack (liblouis)

liblouis is a C library with optional Python bindings and a `lou_translate`
command-line tool. QUILL never imports liblouis in-process (see the out-of-process
worker, BR-021); the pack only has to put a liblouis runtime plus the UEB tables
somewhere the worker subprocess can find them. The remaining question — answered
here so it is no longer a gap — is how that runtime reaches a user's machine.

### What the pack contains

- The liblouis runtime for the platform: `liblouis.dll` (Windows) or the shared
  library, **or** the self-contained `lou_translate(.exe)` CLI. QUILL prefers the
  CLI because it removes all ctypes/binding packaging: the worker simply shells to
  `lou_translate` with a table name and the text on stdin.
- The English UEB tables (`en-ueb-g1.ctb`, `en-ueb-g2.ctb`) and **only** their
  required dependency tables.
- A small `manifest.json` (pack version, table list, SHA-256 of each file) so
  `braille_pack_version()` can report a version and the installer can verify
  integrity.
- The third-party `LICENSE` files (see Licensing below).

The pack installs into `<install-dir>/braille-pack/` (Windows) or the platform
data dir. `is_braille_pack_installed()` (BR-020) checks, in order: `lou_translate`
on `PATH`, the bundled `braille-pack/` location, then an importable `louis`
module — so any of the three delivery paths below is detected the same way.

### Delivery options

1. **Optional Inno Setup component (recommended default).** Ship the pack as a
   selectable component in the Windows installer. This is offline, deterministic,
   needs no hosting, and "just works" for users who opt in at install time.
2. **Download-on-demand from inside QUILL.** `install_braille_pack()` fetches a
   pinned, signed pack archive when the user explicitly chooses **Braille →
   Install Braille Pack…**. This keeps the base installer lean and lets a user who
   skipped the component add it later.
3. **System liblouis already on PATH.** Power users (and most Linux installs) can
   `apt install liblouis-bin` / `brew install liblouis`; detection finds it with
   no QUILL packaging at all.

**Recommendation: ship 1 and 2 together.** The optional component is the primary,
offline path; download-on-demand is the fallback for users who skipped it. Both
resolve to the same detection logic, so the Translation submenu appears whenever
*any* path succeeded and stays hidden otherwise (never shown disabled).

### Inno Setup specifics

- Add a `[Components]` entry, e.g. `Name: "braillepack"; Description: "Braille
  translation pack (liblouis + UEB tables)"; Types: full` — left **unchecked in
  the default/compact install** so the base installer stays small.
- Tag the pack files in `[Files]` with `Components: braillepack` so they are only
  laid down when the component is selected, into `{app}\braille-pack\`.
- The build pipeline vendors a **pinned** liblouis Windows build + tables into the
  packaging tree and verifies each file's SHA-256 against `manifest.json` before
  Inno Setup runs. No build ever pulls "latest".

### Download-on-demand constraints (security)

`install_braille_pack()` is currently a no-op stub by design. When the real
download lands it MUST:

- Be triggered only by the explicit **Install Braille Pack…** action — no
  auto-prompt, no auto-download, no silent network calls.
- Fetch a **pinned URL** (a specific QUILL release asset), verify the archive's
  SHA-256 against an embedded expected hash, and verify a release signature before
  unpacking.
- Be added to the network-egress audit (`_REVIEWED_EGRESS`) so the egress gate
  passes; until then, the stub keeps the gate green.
- Respect Safe Mode: like AI and the watch folder, the installer and the
  Translation submenu are hidden when `QUILL_SAFE_MODE=1`.

### Licensing

liblouis is LGPL-2.1-or-later and the UEB tables carry their own (mostly free)
licenses. Because QUILL invokes liblouis **out of process** (a separate
executable/process, never linked or imported into QUILL), the LGPL's dynamic
linking obligations are not triggered for QUILL itself. The pack must still ship
the upstream `LICENSE`/`COPYING` files and the build must record the exact
upstream version so corresponding source can be offered on request.

### Deployment script

`scripts/build_braille_pack.py` is the deterministic half of packaging. Given a
directory of already-vendored liblouis runtime files + tables, it:

1. computes a SHA-256 for every file and writes `manifest.json` (pack version,
   liblouis version, platform, per-file hash + size);
2. zips the tree into `quill-braille-pack-<version>-<platform>.zip`;
3. prints the archive's SHA-256 to pin in `quill.core.braille_pack`.

It never touches the network. A separate, audited **vendor step** populates its
input directory: download a *pinned* upstream liblouis build and the chosen
tables, verify their hashes, and drop them in `vendor/braille-pack/`. The release
CI job runs the vendor step then the build script, and uploads the archive as a
**QUILL GitHub release asset**. That asset — not an upstream URL — is what QUILL
downloads, which is the clean answer to "can QUILL pull these directly?": pulling
straight from liblouis upstream is fragile (no stable, hash-pinned Windows
binary asset) and a supply-chain risk, so QUILL only ever fetches packs we built,
hashed, and host ourselves.

### How QUILL obtains a pack (the magic behind the scenes)

`install_braille_pack()` (today a stub) will:

1. Resolve a **pinned URL + expected SHA-256** from a small table shipped in
   QUILL (keyed by QUILL version), so a build only ever fetches the pack it was
   tested against.
2. Download to a temp file through `quill/io/http_transport.py` (verified TLS,
   size cap, progress callback for the announcement).
3. Verify the archive SHA-256 against the embedded expected hash (and a release
   signature if present); refuse to install on mismatch.
4. Extract atomically into the per-user data dir `braille-pack/` (unzip to a temp
   dir, then `os.replace`), then re-run detection so the Translation submenu
   appears (on next menu build / restart).

This call site is registered in the network-egress audit, runs only on the
explicit **Install Braille Pack…** action, and is disabled in Safe Mode.

### Additional languages (on-demand language packs)

liblouis ships tables for ~all supported languages; the runtime is identical, so
"another language" is just another table file. Two strategies:

- **Bundle all tables (simplest).** The full liblouis table set is only a few MB,
  so the base pack can include every table. "Additional languages" then needs no
  download at all — only UI to choose the table. Recommended unless installer
  size is critical.
- **Per-language packs (lean base).** Ship the runtime + English UEB in the base
  pack and host each extra language as its own small archive. A hosted
  `language_index.json` (code, name, archive URL, SHA-256, bytes) drives an
  **Install Braille Language…** picker; selecting one downloads + verifies +
  extracts that language's tables into `braille-pack/tables/`, reusing the same
  pinned-URL + hash-verify flow above.

Either way the worker just receives a table name (e.g. `fr-bfu-comp6.utb`); no
QUILL code is language-specific.

### Implementation status

Phase 5 software is complete: pack detection (`braille_pack.py`), the
out-of-process worker + client (`braille_worker.py`, `braille_worker_client.py`),
the Translation submenu and commands, and `scripts/build_braille_pack.py`. The
remaining work is operational: vendor + host the first signed pack asset, pin its
URL/hash, and flip `install_braille_pack` from stub to the verified download
above (with its egress-audit entry).

## Supported Braille Variants for Initial Release

Initial support should be intentionally narrow:

- English only
- UEB Grade 1
- UEB Grade 2
- Braille ASCII BRF
- Optional Unicode braille conversion for internal processing or export

Do not include Nemeth, foreign-language tables, tactile graphics,
PDF-to-BRF, DOCX-to-BRF, or eBraille authoring in the first release.

## Important Page Concepts QUILL Should Understand

### 1. Physical BRF Page Break

A BRF page break is usually represented by a form feed character.

In QUILL, this should be treated as a structural page boundary.

User-facing command names:

- Next Braille Page
- Previous Braille Page
- Insert Braille Page Break
- Delete Braille Page Break
- Show Page Breaks as Text

Screen reader announcement:

“Page break. Beginning braille page 12.”

### 2. Calculated Braille Page

If a BRF file does not contain form feeds, QUILL should calculate
braille pages using the active profile.

Default profile:

- 40 cells per line
- 25 lines per page

Also provide presets:

- 40 by 25
- 39 by 25
- 32 by 25
- Custom cells and lines

Screen reader announcement:

“Calculated braille page 12. No form feed found.”

### 3. Print Page Number

A braille transcription can show the original print page number, usually
at the end of line 1.

QUILL should scan line 1 of each braille page for likely print page
numbers.

Examples QUILL should detect:

- `#a`
- `#ab`
- `,iv`
- `a#c`
- `b#c`
- `#ab-#ad`

Screen reader announcement:

“Print page 12.”

or:

“Print page 12, continuation b.”

### 4. Page Change Indicator

When a new print page begins in the middle of a braille page, a page
change indicator may appear. This is commonly a line of unspaced dots
3-6 ending with the new print page number.

In Braille ASCII this often looks like a row of hyphens ending with a
number, such as:

`-------------------------------------#ab`

QUILL should detect this as a print page boundary.

Screen reader announcement:

“Print page change indicator. New print page 12.”

Commands:

- Next Print Page Change
- Previous Print Page Change
- List Print Page Changes
- Mark Current Line as Print Page Change
- Remove Print Page Change Mark

### 5. Lettered Continuation Print Pages

A single print page often occupies multiple braille pages. Continuation
pages may be marked by an unspaced letter before the print page number.

Examples:

- `#a` means print page 1
- `a#a` means first continuation of print page 1
- `b#a` means second continuation of print page 1

QUILL should detect continuation letters and expose them clearly.

Status example:

“Braille page 3 of 87. Print page 1, continuation b. Line 14, cell 31.”

### 6. Braille Page Number

The braille page number is usually placed at the right margin on the
last line of the braille page.

QUILL should detect it separately from the print page number.

Example status:

“Print page 12. Braille page 34.”

This matters because the user may care about either one depending on the
task.

### 7. Transcriber-Generated Pages

Some braille page numbers may be prefixed with `t`.

Example:

`t1`

QUILL should detect these as transcriber-generated pages.

Status example:

“Transcriber-generated braille page t3.”

### 8. Front Matter Braille Pages

Some front matter braille page numbers may be prefixed with `p`.

Example:

`p1`

QUILL should detect these as preliminary/front-matter pages.

Status example:

“Front matter braille page p4.”

### 9. Running Head

A running head may appear on the first line of many braille pages.

QUILL should not confuse a running head with body text or a page number.

Status example:

“Running head detected: Exploring Psychology.”

Commands:

- Announce Running Head
- Ignore Running Head for Status
- Use Running Head in Status
- Detect Running Head Pattern

### 10. Combined Print Page Numbers

A braille page may represent combined or omitted print pages.

Examples:

- `#be-#bi`
- `#dd-#de`
- `,iv-,v`

QUILL should detect these as ranges.

Status example:

“Print pages 25 through 29.”

### 11. Implied or Missing Print Page Numbers

Sometimes print page numbers are implied or absent in the original
print.

QUILL should not pretend these are certain unless they are present or
user-confirmed.

Status example:

“Print page unknown. Braille page 14.”

or:

“Possible implied print page 8.”

## Status Bar Design

The visual status bar should remain short:

BRF Pg 12/87 \| Ln 14/25 \| Cell 31/40 \| Print 7 \| 14%

But the screen reader announcement should be richer.

Normal spoken status:

“Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7.
Fourteen percent through file.”

Detailed spoken status:

“Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7,
continuation a. Running head: Chapter 2. Last proofed page: 9. Three
pages marked needs review.”

Brief spoken status:

“Page 12. Line 14. Cell 31.”

## Status Verbosity Settings

Add a setting:

Braille status verbosity:

- Brief
- Normal
- Detailed

Also add settings for:

- Announce page changes automatically
- Announce print page changes automatically
- Announce line overflow while typing
- Announce cell position on demand only
- Include proofing status in announcement
- Include running head in announcement
- Include continuation page information

Default should be conservative to avoid screen reader spam.

## Required Keyboard Commands

### Status Commands

- Read Braille Status
- Read Detailed Braille Status
- Read Current Line and Cell
- Read Current Braille Page
- Read Current Print Page
- Read Current Running Head
- Read Progress Summary

### Navigation Commands

- Go to Braille Page
- Go to Print Page
- Next Braille Page
- Previous Braille Page
- Next Print Page
- Previous Print Page
- Next Page Change Indicator
- Previous Page Change Indicator
- Next Layout Warning
- Previous Layout Warning
- Go to Last Reading Position
- Go to Last Proofed Page

### Editing Commands

- Insert Braille Page Break
- Remove Braille Page Break
- Insert Print Page Change Indicator
- Mark Current Line as Print Page Change
- Insert Braille Page Number
- Insert Running Head
- Normalize Line Endings
- Recalculate Page Map

### Proofing Commands

- Mark Current Braille Page as Proofed
- Mark Current Braille Page as Needs Review
- Clear Proofing Mark
- Add Proofing Note
- List Pages Needing Review
- List Proofed Pages
- Export Proofing Report

### Translation Commands

These commands are available only when the optional Braille Pack is
installed:

- Translate Plain Text to UEB Grade 1 BRF
- Translate Plain Text to UEB Grade 2 BRF
- Translate Selection to UEB
- Back-Translate BRF to Draft Text
- Back-Translate Current Page
- Back-Translate Selection
- Compare Back-Translation with Source

Back-translation must always be described as draft output.

## Menus

Add a Braille menu.

Suggested structure:

Braille Status Read Braille Status Read Detailed Braille Status Read
Progress Summary

Navigation Go to Braille Page Go to Print Page Next Braille Page
Previous Braille Page Next Print Page Change Previous Print Page Change

Page Tools Insert Braille Page Break Insert Print Page Change Indicator
Rebuild Page Map Detect Print Page Numbers Detect Braille Page Numbers

Proofing Mark Page as Proofed Mark Page as Needs Review Add Proofing
Note List Pages Needing Review Export Proofing Report

Validation Validate BRF Layout Next Warning Previous Warning Warnings
Summary

Translation Translate to UEB Grade 1 Translate to UEB Grade 2
Back-Translate to Draft Text Install Braille Pack

Settings Braille Document Settings Braille Status Settings Translation
Settings

## Braille Document Settings Dialog

This should be a simple, accessible dialog.

Fields:

- Braille code
- Grade
- Cells per line
- Lines per page
- Use form feeds as page breaks
- Calculate pages if form feeds are missing
- Detect print page numbers
- Detect braille page numbers
- Detect page change indicators
- Track reading position
- Track proofing status
- Save sidecar progress file
- Status verbosity
- Automatic announcements

No complex visual preview is required.

## Sidecar Progress File

QUILL should not modify the BRF just to store workflow information.

Use a sidecar file:

`filename.brf.quill.json`

Example:

{ “documentType”: “brf”, “profile”: { “brailleCode”: “UEB”, “grade”:
“2”, “cellsPerLine”: 40, “linesPerPage”: 25, “pageBreakMode”: “formFeed”
}, “position”: { “lastOffset”: 48291, “lastBraillePage”: 42, “lastLine”:
14, “lastCell”: 31, “lastPrintPage”: “18” }, “proofing”: {
“lastProofedBraillePage”: 39, “pagesNeedingReview”: \[12, 27, 31\],
“proofedPages”: \[1, 2, 3, 4, 5, 6, 7, 8, 9\] }, “anchors”: \[ { “type”:
“printPage”, “printPage”: “1”, “braillePage”: 1, “offset”: 0,
“confidence”: “detected” }, { “type”: “printPage”, “printPage”: “7”,
“braillePage”: 12, “offset”: 13210, “confidence”: “userConfirmed” }\],
“notes”: \[ { “braillePage”: 12, “line”: 22, “cell”: 1, “note”: “Check
page change indicator.” }\] }

## Validation Engine

QUILL should include a BRF validator that is navigable by keyboard and
useful through speech.

Warnings should include:

- Line exceeds selected cell width
- Page exceeds selected line count
- Page has too few lines, possible missing content
- No form feeds found
- Mixed line endings
- Unexpected non-Braille-ASCII character
- Possible print text in BRF
- Page change indicator found on invalid line
- Page change indicator missing page number
- Braille page number missing
- Braille page number repeated
- Braille page number appears out of sequence
- Print page number appears out of sequence
- Continuation page letter appears out of sequence
- Running head inconsistent
- Trailing spaces warning, optional only
- File uses unusual page size
- File appears to be Unicode braille rather than Braille ASCII

Warnings should be presented like this:

“Warning 3 of 12. Braille page 14, line 26. Page has 26 lines; expected
25. Press Enter to move to issue.”

## Page Map Engine

The page map is the heart of the feature.

For each page, store:

- Start offset
- End offset
- Physical page number
- Calculated page number
- Detected braille page number
- Detected print page number
- Continuation letter, if any
- Running head, if any
- Line count
- Maximum line length
- Whether form feed ended the page
- Warnings
- Proofing status

This gives QUILL instant navigation and status.

## Print Page Detection Strategy

QUILL should use confidence levels.

### High Confidence

- Page change indicator line ending with a valid page number
- Line 1 right-margin page number matching expected pattern
- Repeated print page number with continuation letters
- User-confirmed print page anchor

### Medium Confidence

- Right-aligned number on line 1
- Consistent sequence across several pages
- Combined page number pattern

### Low Confidence

- Number appears near right margin but pattern is ambiguous
- No running head detected
- Short page with multiple possible page number candidates

QUILL should expose confidence in detailed status only.

Example:

“Print page 7, detected with high confidence.”

## Transcriptionist Progress Workflow

### Opening a BRF

When opening a BRF, QUILL should announce:

“BRF file opened. 87 braille pages detected. Print page tracking
available. Last position: braille page 12, line 14, cell 31.”

If no sidecar exists:

“BRF file opened. 87 braille pages detected. No progress file found.”

### During Work

The user can press the status command at any time:

“Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7. Page
not proofed.”

### Marking Progress

Command:

Mark Current Braille Page as Proofed

Announcement:

“Braille page 12 marked proofed.”

Command:

Mark Current Braille Page as Needs Review

Announcement:

“Braille page 12 marked needs review.”

### Progress Summary

Command:

Read Progress Summary

Example:

“Progress summary. 87 braille pages. Current page 12. 9 pages proofed. 3
pages need review. Last proofed page 9. Current print page 7. Estimated
completion 10 percent.”

## Lightweight Translation Architecture

The base QUILL installer should not bundle the whole braille world.

Use a separate optional component:

QUILL Braille Pack

Contents:

- Liblouis runtime
- English UEB Grade 1 table
- English UEB Grade 2 table
- Required include files
- Small translation worker process
- Version manifest

The translation worker should run out-of-process so that translation
errors or crashes do not crash QUILL.

Possible worker calls:

- translate_text_to_ueb_grade_1
- translate_text_to_ueb_grade_2
- back_translate_brf_to_text
- back_translate_selection
- validate_liblouis_installation
- list_available_tables

## Translation Safety

Translation must be helpful but honest.

Use these labels:

- “Translate to UEB”
- “Back-Translate to Draft Text”
- “Preview Translation”
- “Replace Selection with Translation”
- “Send Translation to New Document”

Do not label back-translation as “convert to perfect print.”

Back-translation announcement:

“Draft back-translation complete. Review required.”

## Optional Source-to-BRF Workflow

Later, QUILL can support a transcription workspace without making it
visual-first.

Instead of a complex side-by-side visual UI, use linked documents and
commands.

Commands:

- Link Source Position to Current BRF Position
- Read Linked Source Position
- Go to Linked BRF Position
- Go to Linked Source Position
- Compare Back-Translation with Source
- List Unlinked Source Pages

Status example:

“Source page 7 is linked to braille page 12, line 1.”

## Minimal Visual Design

Because this is for screen reader users, visual design should stay
minimal.

Avoid:

- Visual braille preview as the primary experience
- Color-coded warnings
- Graphical page map as the main navigation method
- Drag-and-drop page tools
- Mouse-dependent controls
- Hover-only explanations
- Complex split panes

Acceptable minimal visual elements:

- Plain status bar text
- Plain dialogs
- Plain list of warnings
- Plain text progress report
- Optional hidden symbols for page breaks

Everything must be keyboard accessible and screen-reader meaningful.

## Accessibility Requirements

- All commands available from menus
- All commands assignable to keyboard shortcuts
- Focus remains in the editor after status commands
- Dialog fields have proper labels
- Warning lists are navigable with arrow keys
- Pressing Enter on a warning moves to the issue
- Escape closes dialogs without changing focus unexpectedly
- No screen reader spam while typing
- Automatic announcements are configurable
- Manual status command always available
- Status text should be copyable
- Progress report should open as plain text

## Implementation Phases

The phases below are written in *dependency order* (Phase 1 first, then
2, 3, 4, 5, 6). The **pragmatic shipping order** — when each phase
will actually land in the codebase and ship to users — is different
because Phase 5 (the optional UEB Translation Pack) is intentionally
opt-in and depends only on Phase 1.

### Pragmatic shipping order

`1 → 5 → 2 → 3 → 4 → 6`

* **Phase 1 (BRF Core)** — open/save, page map, status, navigation.
  Foundation for every later phase.
* **Phase 5 (UEB Translation Pack, opt-in)** — translation is the most
  independent phase. It needs Phase 1's open/save round-trip and
  `go_to_page` command, but it does not need print-page detection or
  validation. Ship it as soon as Phase 1 is stable so English UEB
  users get the feature without bundling every language and table.
* **Phase 2 (Page Intelligence)** — print/braille page numbers,
  continuation letters, running heads, detailed status mode. The
  proofing counters in Phase 3 and the warning rules in Phase 4 both
  read Phase 2's detection signals, so this lands before them.
* **Phase 3 (Proofing and Progress)** — sidecar, last position, mark
  proofed / needs review, progress summary. The sidecar schema lands
  *after* Phase 2 so it can include the print-page hint field from
  the start.
* **Phase 4 (Validation)** — BRF validation engine. Most warnings are
  about things Phase 2 already detected as suspicious, so the
  validator lands after the detectors exist.
* **Phase 6 (Source-to-BRF linking)** — depends on everything above.

What this avoids:

* **Do not do Phase 3 before Phase 2.** The progress summary voice
  prompt depends on print-page detection, and the sidecar schema
  would have to be re-migrated to add the print-page field.
* **Do not do Phase 4 before Phase 2.** Most warning rules are
  checks on Phase 2's detection output; building the validator
  first means either writing rules with no signal to trigger or
  duplicating detection work in the validator.
* **Phase 5 can safely land before Phases 2, 3, and 4** because
  translation is opt-in and out-of-process, but it must still wait
  for Phase 1's open/save and `go_to_page`.

### Phase 1: BRF Core

Deliver:

- Open/save `.brf` and `.brl`
- Preserve layout exactly
- Detect form feeds
- Calculate braille page, line, and cell
- Status bar support
- Read Braille Status command
- Go to Braille Page command
- Insert Page Break command
- Basic page profile settings

Success criteria:

- User can open a BRF and immediately know current braille page, line,
  and cell.
- User can navigate by braille page.
- File saves without damaging spacing, line endings, or form feeds.

### Phase 2: Page Intelligence

Deliver:

- Detect print page numbers
- Detect braille page numbers
- Detect page change indicators
- Detect continuation page letters
- Detect running heads
- Add detailed status mode
- Add Go to Print Page
- Add Next/Previous Print Page Change

Success criteria:

- QUILL can say “print page 7” when the BRF contains usable page
  indicators.
- QUILL distinguishes braille page from print page.
- QUILL explains when print page is unknown or guessed.

### Phase 3: Proofing and Progress

Deliver:

- Sidecar progress file
- Last position restore
- Mark page proofed
- Mark page needs review
- Add proofing notes
- Read Progress Summary
- Export Proofing Report

Success criteria:

- A transcriptionist can stop work and resume later.
- QUILL can report proofing progress by page.
- Workflow data does not modify the original BRF.

### Phase 4: Validation

Deliver:

- BRF validation engine
- Warnings list
- Next/Previous Warning
- Page length warnings
- Line length warnings
- Page numbering warnings
- Page change indicator warnings
- Running head consistency warnings

Success criteria:

- User can locate layout problems without scanning the whole file
  manually.
- Warnings are spoken clearly and can be jumped to directly.

### Phase 5: Optional UEB Translation Pack

Deliver:

- Detect installed Braille Pack
- Install or configure Braille Pack
- Translate plain text to UEB Grade 1
- Translate plain text to UEB Grade 2
- Back-translate BRF to draft text
- Translate selection
- Back-translate current page
- Send output to new document

Success criteria:

- Base QUILL remains lightweight.
- Translation is available only when requested.
- English UEB users get useful conversion without bundling every
  language and table.

### Phase 6: Advanced Transcription Workflow

Deliver:

- Source-to-BRF linking
- Source page anchors
- BRF page anchors
- Back-translation comparison
- Linked progress report
- Project mode for transcription jobs

Success criteria:

- A transcriptionist can track source print pages and braille pages
  together.
- QUILL can help answer, “Where am I in the original source?”

## Data Structures

### BRFPage

Fields:

- index
- startOffset
- endOffset
- lineStartOffsets
- lineCount
- maxCellCount
- hasFormFeed
- detectedBraillePageNumber
- detectedPrintPageNumber
- continuationLetter
- runningHead
- pageChangeIndicators
- warnings
- proofingStatus

### PageChangeIndicator

Fields:

- offset
- braillePage
- line
- detectedPrintPage
- confidence

### ProofingStatus

Values:

- none
- proofed
- needsReview
- skipped
- userNote

## File Handling Rules

- Never trim trailing spaces automatically.
- Never normalize line endings without permission.
- Never remove form feeds automatically.
- Never rewrite page numbers automatically without user action.
- Preserve original encoding when possible.
- Warn before saving if non-Braille-ASCII characters exist.
- Use a sidecar for QUILL metadata.
- Provide “Save As Clean BRF” as a deliberate command, not default
  behavior.

## Suggested Internal Modules

- `brf_document.py`
- `brf_page_map.py`
- `brf_ascii.py`
- `brf_page_detection.py`
- `brf_status.py`
- `brf_validator.py`
- `brf_progress.py`
- `brf_sidecar.py`
- `braille_commands.py`
- `braille_pack.py`
- `braille_worker_client.py`

## Suggested Testing

Unit tests:

- Form feed page detection
- Calculated page detection
- Line and cell calculation
- Print page number detection
- Braille page number detection
- Page change indicator detection
- Continuation page detection
- Running head detection
- Validation warnings
- Sidecar read/write
- Save without layout damage

Accessibility tests:

- Open BRF with screen reader running
- Read status command
- Navigate warnings list
- Go to page dialog
- Mark proofing status
- Restore last position
- Ensure focus returns to editor
- Ensure no unsolicited announcements while typing

Real-world test files:

- BRF with form feeds
- BRF without form feeds
- BRF with 39-cell lines
- BRF with 40-cell lines
- BRF with print page changes
- BRF with continuation pages
- BRF with front matter
- BRF with transcriber-generated pages
- BRF with no print page numbers
- BRF containing unexpected characters
- Unicode braille file mistakenly named `.brf`

## Definition of Done for Version 1

Version 1 is complete when a screen reader user can:

- Open a BRF
- Hear page, line, and cell status
- Navigate by braille page
- Insert a page break
- Know whether print page tracking is available
- Save without damaging the file
- Mark reading/proofing progress
- Resume from last position
- Run a validation check
- Jump directly to warnings

## Long-Term Magic

Future features could include:

- “Where am I?” global command that speaks document, braille page, print
  page, line, cell, running head, and proofing status
- Smart resume: “Continue where I left off”
- Proofing dashboard as plain text
- Automatic detection of page profile
- “Explain this BRF page” command
- Draft back-translation of current page
- Compare source paragraph with back-translated BRF
- Per-project transcription notes
- Export clean proofing report
- Optional eBraille awareness later, without forcing QUILL into full
  eBraille authoring

## Product Principle

The best version of this feature is not flashy.

The best version is the one where a blind transcriptionist presses one
command and immediately knows:

“I am on braille page 42, print page 18, continuation b, line 14, cell
31. This page is not yet proofed. There is one layout warning on this
page.”

That is the magic.

For the translation piece, I would use Liblouis only as an optional
pack. Its official docs describe Python bindings for forward translation
and back-translation, which fits QUILL’s wxPython stack nicely.
([Liblouis](https://liblouis.io/documentation/liblouis/Python-bindings.html?utm_source=chatgpt.com "7.30 Python bindings"))
Liblouis already has English UEB tables, including `en-ueb-g1.ctb` and
`en-ueb-g2.ctb`; the Grade 2 table is about 196 KB in the project
listing, so the real bloat risk is not the UEB table itself but bundling
every language, every math table, and every possible dependency.
([GitHub](https://github.com/liblouis/liblouis/blob/master/tables/en-ueb-g2.ctb?utm_source=chatgpt.com "liblouis/tables/en-ueb-g2.ctb at master"))

My strongest recommendation: build **BRF Core + Page Intelligence +
Progress Tracking** first. That gives blind transcriptionists immediate
value without adding a heavy translator. Then ship **UEB translation as
an optional Braille Pack**.
