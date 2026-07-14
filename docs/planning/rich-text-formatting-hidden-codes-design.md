# Rich Text Formatting with Hidden Codes — Design and Implementation Note

Status: **Implemented** on the 2.0 branch (was: draft exploration, 2026-06-26).
Scope: font family, point size, color, highlight, underline, strikethrough,
super/subscript, paragraph alignment, line spacing, paragraph spacing, indent,
named paragraph styles, page breaks, and a "Clear formatting" command in the QUILL
editor — exported faithfully to Word (`.docx`), RTF, and HTML, while the editing
buffer stays free of visible markup.

## 1. Problem and intent

QUILL originally applied only bold, italic, and underline, writing inline markup
(`**...**`, `<u>...</u>`) into a plain `wx.TextCtrl`. There was no font, size,
color, alignment or layout, and Word export ran Markdown through Pandoc, whose
docx writer silently dropped inline CSS for font/size/alignment.

The product intent, stated by the user:

- Apply font, style, point size, alignment, and color — and the broader set of
  word-processor attributes (strikethrough, super/subscript, line spacing,
  paragraph spacing, indent, named styles, page breaks).
- **The formatting codes must be hidden from the user.** The document stays
  "simple, fast, and efficient." The user reads and edits clean text.
- The user can **interrogate** the document — ask "what is the formatting here?" —
  quickly, and (being a screen-reader user) *hear* the answer.
- The tags are **materialized only at export**.

This reframes the feature away from a WYSIWYG/visible-markup editor toward a clean
buffer with a formatting layer that is queried on demand and serialized at export
time.

## 2. Why this fits QUILL's existing architecture

Four existing pieces made the hidden-codes model practical rather than a rewrite:

1. **A rich intermediate model** — `quill/io/rtf_model.py`
   (`InlineSpan` / `RichParagraph` / `RichDocument`, `markdown_to_rich` /
   `rich_to_markdown`) is the shared model for every writer.
2. **An offset map between markup and visible text** — `analyze_markdown` /
   `format_at_markdown_offset` map visible caret offsets to markup offsets, which
   is exactly "hide the codes but keep the caret honest."
3. **A spoken-formatting vocabulary** — `quill/core/format_speech.py`
   (`describe_inline_format`) turns formatting flags into phrases.
4. **Font/size/alignment precedent** — `quill/core/heading_styles.py` validates
   alignment against `{left, right, center, justify}` and emits CSS; the same
   logic generalizes from headings to arbitrary runs and paragraphs.

## 3. The materialized tag vocabulary

Tags are produced at export and (under storage Option A) on save. They use
Pandoc's generic attribute-span / fenced-div syntax with explicit values. Because
Word is written by our own python-docx code, **we own attribute interpretation**.

```
Inline run:   [Hello world]{font-family="Arial" font-size="14" color="#C00000"}
Inline flags: [note]{underline strike superscript}
Paragraph:    ::: {align="center" line-spacing="1.5" pstyle="quote"}
              Centered, 1.5-spaced quote.
              :::
Page break:   ::: pagebreak
```

The implemented vocabulary:

- **Inline (run-level):** `font-family`, `font-size` (points), `color`,
  `highlight`, plus the boolean flags `underline`, `strike`, `superscript`,
  `subscript`, and the existing `bold` / `italic` (carried as `**`/`*` inside the
  span label).
- **Block (paragraph-level), via fenced div:** `align`
  (`left`/`right`/`center`/`justify`), `pstyle` (a named Word style:
  `quote`/`title`/`subtitle`/`caption`), `line-spacing` (`1`/`1.5`/`2`),
  `space-before` / `space-after` (points), `indent` (left indent, points),
  `first-line-indent` (points).
- **Page break:** the standalone marker line `::: pagebreak`.

Attribute order is fixed (keyed pairs then boolean flags for runs; a fixed key
order for divs) so apply-then-reparse and `markdown -> rich -> markdown` are
stable identities. `quill/io/rtf_model.parse_span_attributes` parses the
space-separated `key="value"` grammar (and bare flags); `quill/core/tagging.py`
owns the matching builders (`render_span_attributes`, `render_block_attributes`).

## 4. Hidden-codes storage

The editor never shows tags. **Option A (markup canonical, hidden in the view)**
is implemented: `Document.text` holds the Pandoc-span/fenced-div markup; the
existing markup-to-visible offset map keeps the caret honest; saving `.md` writes
the markup (invisible in QUILL). **Option B (out-of-band overlay + sidecar)**
remains the documented future end-state; because both options converge on the same
`RichDocument` before any writer runs, the writers, menus, speech and tests carry
over unchanged.

## 5. Shared model and parsing — `quill/io/rtf_model.py`

- `InlineSpan` gained `underline`, `strike`, `superscript`, `subscript`,
  `font_family`, `font_size_pt`, `color`, `highlight`.
- `RichParagraph` gained `align`, `named_style`, `line_spacing`, `space_before`,
  `space_after`, `indent`, `first_line_indent`, and a `"pagebreak"` style.
- `InlineFormat` / `MarkdownSegment` mirror the new fields so caret context reports
  them.
- The inline walker recognizes `[...]{...}` spans; `_classify_lines` recognizes
  `::: {...}` fenced divs and the `::: pagebreak` marker. Span/div/marker markup is
  consumed without contributing visible characters, so offset tracking stays
  correct (the whole `:::` line is structure — no visible text and no visible
  newline).

## 6. Materialization helpers and editor commands

`quill/core/tagging.py`:

- `build_span_insertion(selected_text, attrs)` — run span, with merge-into-existing
  so applying font then size yields one span, not nested spans.
- `build_block_attributes(selected_text, attrs)` / `build_block_alignment(...)` —
  paragraph fenced div, also merge-aware.
- `build_clear_formatting` / `strip_run_formatting` — Clear Formatting (unwraps
  spans and emphasis, preserves links).
- `build_page_break` — the `::: pagebreak` marker.

`quill/ui/main_frame_format_codes.py` (`FormatCodesMixin`, extracted to keep
`main_frame.py` within the GATE-11 budget) holds every command and the menu
construction/binding: `format_set_font/size/color/highlight`,
`format_strikethrough/superscript/subscript`, `format_clear_formatting`,
`open_font_dialog`, `format_align`, `format_set_line_spacing`,
`format_set_space_before/after`, `format_set_indent/first_line_indent`,
`format_set_named_style`, `insert_page_break`, and the interrogation commands. The
Format menu gains Font / Size / Align / Color / Highlight / Line Spacing /
Paragraph Spacing / Paragraph Indent / Paragraph Style submenus plus
strikethrough/superscript/subscript/clear/page-break/Font-dialog items.

## 7. Interrogation and screen-reader communication

- `describe_inline_format` speaks the full set, e.g.
  `"quote style, Arial, 14 point, bold strikethrough, centered, double spaced,
  indented, red"`. Order is paragraph-style → typeface → size → weight/decoration
  → layout → color.
- **"Describe Formatting at Cursor"** reads `format_at_markdown_offset` at the caret
  and announces it. Default hotkey: **Ctrl+Shift+D**
  (`format.describe_formatting`, remappable).
- An optional **on-caret-move** announcement of formatting *transitions* (only the
  delta, via `describe_format_transition`) is available behind the
  `announce_formatting_on_move` setting (Format menu check item; off by default so
  navigation stays quiet).
- Every apply action announces its result.

## 8. Export pipeline (identical for A and B)

All writers consume the extended `RichDocument` (or the canonical markup):

- **Word (`.docx`)** — `quill/io/docx_writer.py` (python-docx). Per paragraph:
  alignment, line spacing, space before/after, left/first-line indent, and named
  styles (Quote/Title/Subtitle/Caption) plus heading/bullet styles; page breaks via
  `add_page_break`. Per run: bold/italic/underline/strike/super/subscript,
  `font.name`, `font.size`, `font.color.rgb`, highlight. `write_docx_document`
  prefers this writer and **falls back to the Pandoc path** when python-docx is
  absent, so docx export never hard-fails. (Optional dependency: `quill[docx]`.)
- **RTF** (`quill/io/rtf.py`) — emits `\ul`, `\strike`, `\super`/`\sub`, a font
  table (`\fN`/`\fsN`), a color table (`\cfN`/`\highlightN`), alignment
  (`\qc/\qr/\qj`), line spacing (`\slN\slmult1`), spacing (`\sb`/`\sa`), indent
  (`\li`/`\fi`), and page breaks (`\page`). The RTF **reader** was upgraded to
  recover underline, strikethrough, super/subscript, color and highlight (parsing
  `\colortbl`), so opening an RTF/Word file round-trips losslessly. Consequently
  those items were dropped from `_UNSUPPORTED_FEATURES` (only tables, images and
  footnotes remain reported as flattened).
- **HTML** (`markdown_to_html` → `quill/core/browser_preview.py`) — renders run
  spans to `<span style>` (font/size/color/background/`text-decoration`/
  `vertical-align`) and divs to `<div style>` (`text-align`, `line-height`,
  margins, `text-indent`, named-style CSS); page breaks to
  `page-break-after: always`. This also enriches the live preview.
- **Plain text** (`markdown_to_plain_text`) — strips span wrappers, fenced-div
  markers and page-break lines, keeping the visible words.

## 9. Dependencies and gates

- **`python-docx`** is declared as the optional `quill[docx]` extra; the native
  writer activates when it is installed, Pandoc otherwise.
- mypy stays scoped to `core` / `io`; all new/changed modules type-check.
- Menus only (no new modal except the optional Font dialog, which routes through
  `_show_modal_dialog` + `apply_modal_ids`); `menu_lint` and GATE-11 pass.
- No new network egress.

## 10. Phasing — delivered

1. Inline run formatting (font/size/color/highlight/underline) — **done.**
2. Paragraph alignment — **done.**
3. python-docx Word writer + optional dependency — **done.**
4. Color / highlight across model, builders, writers, speech — **done.**
5. Strikethrough, super/subscript, Clear Formatting — **done.**
6. Line spacing, paragraph spacing, indent, named styles, page break — **done.**
7. Accessible "Font…" dialog, Describe-Formatting hotkey, on-caret-move toggle,
   lossless RTF read-back — **done.**
8. Out-of-band overlay + sidecar persistence (storage Option B) — **future**, as
   the clean-document end-state; reuses everything above.

## 11. Verification

- Unit: `tests/unit/io/test_rtf_model.py` (span/div/page-break round-trip, offset
  stability, interrogation), `tests/unit/core/test_format_speech.py` (phrases),
  `tests/unit/core/test_tagging.py` (builders/merge/clear/page-break),
  `tests/unit/io/test_rtf.py` (writer control words + lossless read-back),
  `tests/unit/io/test_export.py` (HTML spans/divs/page-break, plain-text strip),
  `tests/unit/io/test_docx_writer.py` (opens the produced `.docx` and asserts
  run/paragraph attributes; skipped when python-docx is absent).
- Round-trip: `markdown -> rich -> markdown` is identity for every attribute.
- Lint/types: `ruff check .`, `mypy quill\core quill\io`, `menu_lint`, GATE-11.

## 12. Open questions for the future (Option B)

- Sidecar format and naming for Option B persistence, and behavior when a `.txt` is
  opened in another editor (overlay dropped vs. warned).
- Font/size pickers: the menu presets + "More Font Options…" dialog exist; a visual
  color picker could be added later (the current color field accepts a name or
  `#RRGGBB`, which is the most screen-reader-friendly form).
- Note: color *names* normalize to `#RRGGBB` when round-tripped through RTF (the RTF
  color table is numeric); this is expected and lossless in meaning.
