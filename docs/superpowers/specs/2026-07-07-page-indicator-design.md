# Page indicator for every document — design

Closes GitHub issue #872.

## Problem

QUILL already has a mature, exact page-tracking system — but only for
BRF/braille documents (`main_frame_braille.py` / `main_frame_braille_phase2.py`,
detection in `brf_page_detection.py`). For every other format (`.txt`, `.md`,
`.docx`, PDF-imported text), there is only a form-feed-based "Go To Page"
(`navigation.py:page_starts` / `page_start_for_number`) that does nothing
useful in practice, because nothing in QUILL's import pipeline ever inserts a
literal `\f` character. There is no page count, no page indicator, and no
page-based navigation for the documents most people actually write in.

A beta tester asked directly: "Are we going to be able to see proper page
numbers with QUILL?" Direction from Jeff: add a page item to the status bar
**by default**, even for plain text files — not gated behind Braille mode —
and make sure it ships for Beta 2 rather than waiting for a later release.

## Non-goals

- Not a print/layout engine. QUILL will never compute the *actual* page
  count Word or a printer would produce for arbitrary text/Markdown/DOCX —
  that requires a full page-layout engine (fonts, margins, paper size) this
  project does not have and is not building.
- Not touching the existing BRF/braille page system at all. Braille
  documents keep their own richer "braille" status cell and command set;
  this feature's status cell is suppressed whenever that one is active, so
  the two never compete for the same space.
- Not adding page-based navigation for EPUB. EPUB already has its own
  chapter/heading navigator; page numbers are not a meaningful concept for
  reflowable EPUB content and are out of scope here.
- Not building a `Document.page_count` field or any new persisted page
  metadata. Both tracks below are computed on demand from the document's
  text (real pages from `\f` markers already in the text; estimates from a
  live word count), the same way `document_progress` and other status cells
  already work.

## Design

### One status cell, two tracks

A single new status bar item, `"page"`, is added to `STATUS_BAR_ITEMS`
(`quill/core/settings_normalizers.py`) and, unlike most items there, is
**not** added to `_default_status_bar_hidden()` — it is visible out of the
box for every document, per the explicit ask. It is suppressed whenever the
existing `"braille"` cell is active (BRF documents), via the same
feature-style filtering `_statusbar_items()` already does in
`main_frame_statusbar.py`.

The cell's text is computed by a new `_statusbar_page_text()` method in
`main_frame_statusbar.py`, mirroring the existing `_statusbar_braille_text()`
pattern (a resolver cached on the frame, keyed by `(id(document), len(text))`,
rebuilt when the text length changes):

- **Exact track:** if `navigation.page_starts(text)` finds more than one
  page boundary (i.e. the document contains at least one `\f`), the cell
  reads **"Page 3 of 12"** — no qualifier, because it's a real count.
- **Estimated track:** otherwise, the cell reads **"Page ~3 of ~12
  (estimated)"** — the tilde and the word "estimated" are both always
  present together; this is deliberate and non-negotiable UI copy, so nobody
  mistakes an estimate for a fact. The accessible name/tooltip additionally
  spells out: *"Estimated from word count only (~{N} words per page) — does
  not reflect fonts, margins, or actual print/export pagination."*

Detection between the two tracks is nothing more than "does this document's
text contain a `\f`" — no per-format special-casing is needed once the
import side (below) is in place.

### Track A — the estimate (`quill/core/navigation.py`)

Two new pure functions:

```python
def estimate_page_count(text: str, words_per_page: int) -> int: ...
def estimate_page_for_position(text: str, position: int, words_per_page: int) -> int: ...
```

Word count reuses the same splitting logic `core/metrics.py` already uses
for the existing word-count status cell, so the estimate's "words" always
matches what the user already sees elsewhere. Both functions clamp to at
least 1 page for any non-empty document.

New setting `page_estimate_words_per_page: int = 300`, clamped to
`[150, 600]`, following the exact pattern of `braille_lines_per_page`
(`settings.py`, `settings_specs.py`) — declared, parsed in `from_dict`,
clamped, and wired into the constructor. Exposed in Preferences under the
same group as the other status-bar settings, with help text making the
estimate's approximate nature explicit at the settings level too, not just
in the status bar.

### Track B — real pages (`quill/io/pdf.py`, DOCX import)

This reuses machinery that already exists rather than building new exact-page
tracking:

- **PDF:** `_extract_with_pdfplumber` / `_extract_with_pypdf`
  (`quill/io/pdf.py`) already extract real per-page text and a real
  `page_count`, then discard both by joining every page with `"\n\n"`. Change
  the join to `"\f"` between pages (keeping paragraph breaks within a page
  as they are today) so the real boundaries survive into the `Document`'s
  text. No new field is needed — `page_starts()` on the resulting text *is*
  the page count and boundary list.
- **DOCX:** the reader gains detection of explicit hard page breaks
  (`<w:br w:type="page"/>`) and inserts a `\f` at each one. Documents with no
  explicit break (the common case) produce no `\f` and fall straight through
  to the estimate — this is expected and correct; DOCX has no *computed*
  page count without a layout engine, only author-inserted breaks are ever
  "real." `quill/io/docx_writer.py` already turns `\f` back into a real page
  break on export, so this round-trips symmetrically.

**Scope note (added during implementation planning):** DOCX import goes
through Pandoc or MarkItDown conversion to Markdown text
(`quill/io/structured.py:_read_docx`), neither of which preserves explicit
page-break positions in the converted text. Detecting hard page breaks
would require a separate python-docx scan with no reliable way to map
those positions into the converted text. Track B therefore ships for
**PDF only** in the first implementation; DOCX stays on the Track A
estimate. Real DOCX pagination is left as a follow-up, matching this
issue's own original recommendation to treat exact-format pagination as
separable, incremental work.

### Go to Page command

The existing (currently dead) `navigation.page_start_for_number` powers an
exact "Go to Page" for any document whose text contains `\f` — this is the
same command surface the issue's linked plan expected, just newly reachable
because real documents now carry page markers. For estimate-track documents,
a parallel "Go to Page (estimated)" command computes a target character
offset from the word-count heuristic. Its confirmation/prompt text repeats
the same "this is an estimate" framing as the status cell — the disclaimer
travels with the feature everywhere it surfaces, not just once.

### Testing

- `quill/core/navigation.py`: pure unit tests for `estimate_page_count` /
  `estimate_page_for_position` across empty, single-word, and multi-page
  texts, and for the interaction between `\f`-bearing and `\f`-free text.
- `quill/io/pdf.py`: extraction test asserting `\f` appears between pages
  and `page_starts()` on the result matches the source `page_count`.
- DOCX import: a fixture `.docx` with one explicit page break, asserting the
  imported text contains exactly one `\f` at the right offset.
- `main_frame_statusbar.py`: light-stub tests for `_statusbar_page_text()`
  covering both tracks, the BRF-suppression rule, and the resolver cache
  invalidating correctly when the document's text length changes.
- Settings: round-trip test for `page_estimate_words_per_page` (default,
  clamp bounds, persistence).

## Documentation

- **PRD:** new subsection under the status bar / navigation area, describing
  both tracks and the exactness contract (cell wording rules above).
- **User guide:** new subsection under Status Bar explaining the Page cell
  in plain language, including a short, explicit "this is an estimate, not a
  printed page count" paragraph, and documenting the two Go to Page commands
  and the `page_estimate_words_per_page` setting.
- **CHANGELOG / Beta 2 release notes:** new entry under "0.9.0 Beta 2." Per
  Jeff's direction, this ships in Beta 2 despite being a feature rather than
  a fix; the release notes' "no new headline features here" sentence is
  softened to carve out this one exception rather than removed outright.
- Issue #872 is closed once all of the above lands and tests pass.
