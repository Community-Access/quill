# PDF text reliability: choosing each page's reading

Date: 2026-10-16. Jeff's todo, P2 item 28, "Text-extraction reliability,
shared by both editors and Import / Convert". This is text-reading work: which
words come out of a PDF, in what order, with what page boundaries. It is not
PDF document-structure work, and nothing here makes headings, tables or any
other structure.

## Short version

The PDF reader used to keep the first non-empty answer from pdfplumber or
pypdf, scored by how much text there was. A page of replacement characters
scored 100, a clean title page scored 25, and a bad first answer hid a good
second one. Now each page is read by pdfplumber first; a clean reading is kept
at once (the fast path), and a doubtful one is read two or three more ways and
the most *readable* reading wins. Readability is a bounded 0-100 score built
from the kinds of damage a listener trips over. The same reader serves File >
Open in QUILL and QUILL Lite, Import / Convert's text-layer tier and Document
Q&A. Clean documents cost the same as before (38.3 against 37.6 ms a page);
doubtful pages cost about 40 percent more; peak memory fell from 429 MB to
6.5 MB on 200 pages.

## What was wrong (measured before any change)

The fixture corpus (`tests/corpus/pdf/`, built by `build_pdf_corpus.py`) was
read with the old reader first. What it found:

| File | Old result |
|---|---|
| `clean_prose.pdf` | Scores 32 and 18 per page, 50 for the document: clean text called mediocre, because it is short. |
| `letter_spaced.pdf` | pdfplumber read a widely spaced paragraph one letter at a time; repair closed the letters up into "Widelettersarehardtoread". pypdf had it right and was never asked. |
| `two_columns.pdf` | The two columns run together row by row ("through the night Repairs to the bridge"). pypdf, which follows the drawing order, had them in order. |
| `nested_outline.pdf` | "Chapter 2" under a long body line was swallowed into that paragraph. |
| `damaged_encoding.pdf` | A page of U+FFFD scored 17, the same as clean pages; a font that stored its "x" as a private-use glyph read "The net bo holds", because unmapped private-use characters were deleted. |
| `blank_edges.pdf` | A blank first page vanished: the leading form feed was stripped, so page 2's text became page 1 and every offset shifted. |
| 200 clean pages | 6.9-7.5 s, peak traced memory **429 MB**: pages were never released. |

Also: `quill.io.structured._format_pdf` ran MarkItDown on any document below
50, replaced *all* of the text with its answer (losing the page breaks), and
recorded an automatic 85; `format_pdf_document` kept whichever answer was
*longer*. The shipped runtime cannot import MarkItDown at all (magika needs
onnxruntime, which the runtime excludes), so the behaviour differed between a
development install and a shipped build. PRD 5.5 described a per-page
selection with `pypdfium2` and `pdfminer.six` as extractors that the reader
never had.

## The engine roster

Per page, in tie-break order (`quill/io/pdf_select.py::ROSTER`):

1. `pdfplumber` -- pdfminer.six underneath. The first reading of every page.
2. `pdfplumber-dedupe` -- the same page with overprinted duplicate characters
   removed; tried only when the first reading shows fake-bold doubling
   ("HHeelllloo").
3. `pypdf` -- plain mode, which follows the order the page was drawn in.
4. `pypdf-layout` -- layout mode, which keeps horizontal gaps as spaces;
   tidied (indentation dropped, wide gaps reduced to three spaces, blank runs
   collapsed) without changing a word.
5. `pypdf-columns` -- the layout reading split at a detected column gutter and
   read down each column in turn; only when the layout reading shows two
   columns.
6. `markitdown` -- only for a document that still scores below 50, page by
   page (below).

`pypdfium2` stays what it always was: the rasteriser for OCR. OCR is never run
by the reader.

## The fast path

pdfplumber reads the page. If that reading scores at least
**`FAST_PATH_SCORE = 90`** and the page's characters show no column gutter, it
is repaired (unless repair would lower its score) and kept; nothing else reads
the page.

The threshold was measured on the corpus: every clean page's first reading
scored 100, and every damaged one scored 78 or less (the private-use page, with
2 unreadable characters in 38) or 0. 90 sits in that gap, and lets a page with
up to about 2.5 percent unreadable characters through on the fast path, where
the other extractors would have read the same glyphs the same way.

**The gutter check** (`quill/io/pdf.py::_suspect_columns`) uses pdfplumber's own
character boxes, which it already computed: on a page with at least 150
characters and six lines, it looks in the middle 40 percent of the text width
for a vertical band at least 12 points wide that at most a tenth of the lines
cross, with at least three lines on each side of it. One column of prose
crosses the middle on nearly every line, so it never matches. A table can match;
that only costs the page a comparison, never changes how it is read.

## The readability score

`quill/io/pdf_score.py`, `SCORE_VERSION = 1`. The score is 100 multiplied by
six factors, each between 0 and 1, rounded and clamped to 0-100:

```
score = round(100 x suspicious x fragmented x one_word_lines x joins x coverage x column_order)

suspicious     = max(0, 1 - 4 x share of visible characters that are U+FFFD,
                     private use, stray controls, or (cid:N) placeholders)
fragmented     = max(0, 1 - 1.5 x share of words inside runs of 3+ single Latin letters)
one_word_lines = 1 - min(0.6, max(0, share_of_one_word_lines - 0.5) x 1.2)
                 (only with 6 or more non-blank lines; so never below 0.4)
joins          = max(0.2, 1 - 4 x max(0, share_of_implausible_words - 0.03))
                 implausible: Latin words of 20+ letters, "wordWord" or "word.Word"
                 seams, doubled letters; 3 percent allowance for real long words
coverage       = min(1, content_chars / fullest reading's content_chars / 0.95)
column_order   = 1 - 0.5 x share of two-column rows run together side by side
                 (only when the page shows two columns)
```

Empty text scores 0. What it deliberately does not penalise: length (a
one-line title scores 100), digits and punctuation (a row of figures scores
100), and other scripts (Greek, Cyrillic and Japanese prose score 100; word
length is judged only for Latin, Greek, Cyrillic and Armenian words).

**Before and after repair.** Every reading is scored as extracted and again
after `repair_extracted_text`; the higher score wins for that reading, and if
the repaired text scored lower, the unrepaired text is kept. So a repair
heuristic that misfires on an unusual page cannot silently win, and the score
of a page is never inflated by a repair that deleted something (no repair
deletes characters any more; see below).

**Coverage** is measured against the fullest reading of the same page (letters
and digits, placeholders and junk excluded), so a reading that is clean because
it lost half the page does not beat one that kept it.

**Regression pins** (`tests/unit/io/test_pdf_score.py`): repeated replacement
characters score 0, never 100; letters one at a time score below 40; the score
is always within 0-100 over random input; a poor first reading loses to a
cleaner one (`test_pdf.py`, and on a real file in `test_pdf_corpus.py`).

## Doubtful pages and the document score

A page is **doubtful** (`quill/io/pdf.py::doubtful_pages`) when it has text
scoring below **`DOUBTFUL_PAGE_SCORE = 40`**, holds any unreadable character,
is image-only (pdfplumber found a picture and no text), or failed to read. A
blank page is never doubtful. Both editors say which, in one shared sentence
(`quill/core/pdf_open.py::doubtful_pages_sentence`): "Page 3 may read poorly.",
"Pages 2, 5 and 9 may read poorly.", or, past six, "11 pages may read poorly,
starting with page 1." QUILL says it in the open status (`intake.py`), QUILL
Lite in its open announcement; the Document Intake Report and Review
Extraction Quality list each page with its reason.

The **document score** is the mean of the pages with text, multiplied by
`1 - 0.5 x image_only / (text_pages + image_only)`. Blank pages do not count,
so a report with a blank cover still scores 100.

## MarkItDown, scored by the same rules

Only when the document still scores below 50, no password was used, and the
document is within the page cap. MarkItDown's answer is split at its form
feeds; it is used only if its pages line up with the reader's (a missing
trailing blank page is tolerated). Then each page is contested with the same
`choose_page` and replaced only when MarkItDown's reading wins by at least 10
points (or the reader had nothing). There is no automatic score. If MarkItDown
cannot import -- always, in the shipped runtime -- nothing changes.
`quill.io.structured._format_pdf` no longer calls it at all; it reads through
`read_pdf_for_open` like QUILL Lite.

## Repairs before reflow

`quill/io/pdf_repair.py` keeps its four repairs and its rule ("a missed repair
is an annoyance, a wrong one changes the document"), with these changes:

- **Private-use glyphs are kept.** A ligature slot (U+F000-U+F007,
  U+E000-U+E007) is expanded only where it touches a letter; anything else is
  left as it is and counted as unreadable, so the page is reported. No
  font-specific mapping is guessed.
- **Letter-spaced lines with no word gaps** are not closed up when the result
  would be a mixed-case run longer than 12 letters (a spaced sentence, not a
  heading). Capitals and short words still close up.
- **Dehyphenation** keeps identifier hyphens (a word with a digit, or in
  capitals: `ISBN-`, `A4-`) and joins always-hyphenated prefixes (`self`,
  `well`, `ex`, `all`, `half`, `non`, `cross`) keeping the hyphen.
- **Reflow never joins** a line below a long one when the lower line is
  heading-like (capitals; `Chapter 2`, `Part IV`, `2.1 Methods`; or up to eight
  capitalised words with no closing punctuation), an address line (a house
  number, or a ZIP or postcode at the end), a row with a three-space column gap,
  or a second row of figures under a line ending in a figure; and lettered and
  roman list markers (`a)`, `(b)`, `iv.`) start list items.

All of it is idempotent (`test_the_new_protections_are_idempotent`) and leaves
numbers and identifiers untouched (`test_numbers_and_identifiers_survive_every_repair`).

## Outline bookmarks

`quill/io/pdf_outline.py` reads the outline as `(title, page, level)`. The
stored shape is unchanged -- `source_metadata["pdf_outline"]` is still
`(title, page)` pairs, so older builds and saved sessions read it -- with
`pdf_outline_levels` beside it only when the outline nests.
`quill/core/pdf_open.py::_resolved` finds each title at the start of a line on
its destination page (whitespace and case forgiven; a title shorter than two
characters is not trusted) and falls back to the page start. Two entries with
the same title on one page take successive matches; the bookmark names stay
distinct ("Summary", "Summary (2)"). Go To's Outline kind says a nested entry's
level ("Summary, level 3, page 15"). The level never becomes a heading. QUILL's
first-open import still does nothing when the document already has bookmarks,
so user bookmarks and existing stores are untouched.

## Bounds kept

Passwords (one read, never stored, never in metadata), page order, a form feed
between pages with blank pages kept as empty sections, the 200-page cap, the
four failure outcomes (no reader installed, encrypted, damaged, no text
layer -- an image-only document now keeps its page count so the OCR offer can
say it), no network, OCR opt-in, the original PDF never written
(`test_reading_never_changes_the_pdf`). Each pdfplumber page is closed after it
is read, which is where the memory went.

## Measured budget

Measured side by side (`old` is the reader at the branch point, `new` is this
change), on the development machine with other agents running, MarkItDown
disabled on both sides, median of two or three runs. Peak is
`tracemalloc`'s traced peak for one full read.

| Case | Old | New | Ratio | Peak old | Peak new |
|---|---|---|---|---|---|
| Corpus, 10 files, 20 pages | 108 ms (5.4 ms/page) | 158 ms (7.9 ms/page) | 1.46 | 3.4 MB | 1.1 MB |
| 200 clean pages | 7,528 ms (37.6 ms/page) | 7,653 ms (38.3 ms/page) | 1.02 | 428.7 MB | 6.5 MB |
| 50 questionable pages | 2,093 ms (41.9 ms/page) | 2,921 ms (58.4 ms/page) | 1.40 | 108.2 MB | 5.0 MB |

The corpus is small and mostly questionable on purpose, and its per-file cost
is dominated by opening both readers, so its ratio overstates the everyday
cost. On clean pages the reader costs what it did. A questionable page pays for
two or three readings.

**The gate** (`tests/unit/io/test_pdf_corpus.py`, marked `perf`): 60 clean
pages must all take the fast path, under 250 ms a page and 48 MB peak; 20
questionable pages must all be won by the better reading, under 400 ms a page.
The ceilings are several times the measurement, as GATE-PERF's are, because a
loaded CI box is slower and a gate that fails on a bad afternoon gets deleted;
what they catch is a change of kind, such as every page paying for every
extractor, or pages no longer being released.

## Not done here

- Columns are ordered only when the gap is clear in pypdf's layout reading;
  three columns, or columns around pictures, can still mix.
- No heading levels, table cells, header associations, or anything derived
  from fonts or layout: the separate PDF structure plan (headings from font
  size, tables from ruled lines) is untouched.
- Tagged-PDF structure is not read.
