# RTF & Rich Formatting — Plan of Record

> **Status:** Direction decided 2026-06-27 — *hidden-codes first*. **P1–P4 landed
> on `feature/0.8.0-beta2`** on 2026-06-27 by cherry-picking the complete
> hidden-codes implementation from `2.0-dev` (commit `be02966`, re-applied as
> `3d16560`). What remains open: **P5** (out-of-band overlay / clean-on-disk
> end-state) and the **editable WYSIWYG pane** (deferred to 2.0). The design
> rationale lives in
> [`rich-text-formatting-hidden-codes-design.md`](rich-text-formatting-hidden-codes-design.md);
> this file is the plan that turns it into shippable phases and records the
> decisions. Code references "rtf.md Part One" (e.g.
> `quill/ui/rich_text_surface.py`); this restores that anchor.
>
> **What landed (verified green on beta2):** the shared model carries
> font-family/size/color/highlight/underline/strikethrough/super-subscript run
> attributes and per-paragraph align/line-spacing/indent/named-style + page
> breaks (`quill/io/rtf_model.py`); Pandoc attribute-span `[text]{...}` and fenced
> `::: {align}` parsing with offset integrity; builders in `quill/core/tagging.py`;
> the RTF reader/writer round-trips the full vocabulary (`quill/io/rtf.py`, incl.
> `\colortbl`); a native `python-docx` writer with a Pandoc fallback
> (`quill/io/docx_writer.py`); HTML via `quill/core/browser_preview.py`; the
> **Format** menu + accessible **Font** dialog + **Describe Formatting** command
> + announce-on-move setting (`quill/ui/main_frame_format_codes.py`,
> `quill/ui/font_format_dialog.py`); spoken vocabulary in
> `quill/core/format_speech.py`. The `core.format` feature is live (not gated);
> the read-only rich lens (`core.rich_text_lens`) stays gated pending the #526 SR
> pass. Tests: 171 RTF/format unit tests, plus io+core suites (4165) green;
> GATE-11, public-surface, dialog-inventory, menu-lint all pass.

## 1. Intent — meet you where you are, regardless of surface

A QUILL user receives a `.docx` from a colleague, a `.rtf` from an old archive,
an `.html` snippet, or a plain `.md`. The promise is the same in every case:

- **Open it and read it cleanly.** The editing buffer is always clean text. No
  visible markup, no WYSIWYG word-processor to fight with a screen reader.
- **Keep what the document means.** Bold, italic, headings, lists, links, and
  (as we build out) underline, font, size, alignment, color survive the trip in
  and back out — they are not silently flattened.
- **Hear the formatting on demand.** "What is the formatting here?" is a quiet,
  explicit, spoken answer, never chatter.
- **Hand it back in any surface.** Export to Word, RTF, HTML, or plain text and
  the formatting materializes faithfully into that format's own conventions —
  or, when a target genuinely cannot carry something, QUILL says so honestly
  before the user commits.

The phrase that governs this work: **rich support across surfaces, plain
experience at the center.** The plain-text editor is the one place the writer
lives; formats are doors in and out of it.

## 2. Ground truth (what the code is today)

Verified by reading the tree, 2026-06-27:

- **Canonical text is a plain string.** `Document.text: str`
  (`quill/core/document.py`). The editor is a plain `wx.TextCtrl`
  (`quill/ui/main_frame.py`, `TE_MULTILINE | TE_RICH2 | TE_NOHIDESEL`). Search,
  metrics, outline, autosave, AI, verbosity, compare, and **undo** all run on
  that string. *This does not change.*
- **RTF already round-trips as a format.** `quill/io/rtf.py` (EDS-21) reads RTF
  into QUILL's Markdown-style canonical markup and writes that markup back to
  valid RTF. Bold, italic, headings, bullets, and links survive.
  `quill/io/rtf_safety.py` sanitizes embedded objects, binary payloads, and
  remote references before any conversion.
- **A wx-free rich model and an offset map already exist.**
  `quill/io/rtf_model.py` defines `InlineSpan` / `RichParagraph` /
  `RichDocument`, the `markdown_to_rich` / `rich_to_markdown` round-trip, the
  caret offset mapping (`analyze_markdown`, `markdown_offset_to_plain_offset`,
  `plain_offset_to_markdown_offset`), `format_at_markdown_offset` for spoken
  caret cues, and `scan_rtf_features` for honest-fidelity warnings (the
  `_UNSUPPORTED_FEATURES` table: tables, images, footnotes, highlight,
  strikethrough, underline, color, sub/superscript).
- **A spoken-formatting vocabulary exists.** `quill/core/format_speech.py`
  (`describe_inline_format`) turns formatting flags into phrases.
- **The rich lens exists but is read-only and gated off.**
  `quill/ui/rich_text_surface.py` is a dual-pane surface (a `wx.RichTextCtrl`
  rendering + the canonical Markdown editor) with a pure, tested render plan
  (`build_render_plan`). The feature flag `core.rich_text_lens` is `locked_off`
  in `quill/core/feature_catalog.py` — "pending fuller screen-reader testing;
  RTF files continue to open as plain text in the meantime."
- **Structured reads exist, editing does not.** `quill/io/structured.py` reads
  `.docx` / `.xlsx` / `.csv` / `.sqlite` into a Document (read-only extract,
  spreadsheet reads capped at 50 rows × 20 cols as a memory bound). Editable
  Word/CSV views are a separate workstream (#514, partly blocked on Table
  Studio) and are out of scope here.

**Conclusion:** roughly 80% of rich formatting is already built as a wx-free,
testable layer. The remaining work is the formatting *commands*, the *writers*,
the *interrogation*, and one deferred-risk item (an editable WYSIWYG pane).

## 3. Decisions

1. **Hidden-codes first.** Formatting is invisible codes over a clean buffer,
   applied via Format-menu commands, interrogated and spoken on demand,
   materialized only at export. This is the screen-reader-first, lowest-risk
   path and reuses the existing `RichDocument` model. (Design note §4, Option A
   then Option B.)
2. **The plain editor stays the one editing surface.** Undo, offset commands,
   search, AI, and verbosity continue to act on the canonical markup. Every
   formatting edit funnels through the existing plain-lens undo stack, so undo
   is correct for free.
3. **The visible rich pane stays an optional, read-only preview.** It is
   un-gated only after the JAWS / NVDA / Narrator pass (#526), because
   `wx.RichTextCtrl` screen-reader quality is the open risk the `locked_off`
   flag is waiting on. The dual-lens design guarantees the user is never trapped
   in the rich pane — the plain lens is always present and authoritative.
4. **The editable WYSIWYG pane (#516's literal acceptance: "RichTextSurface is
   editable; persistent undo across rich edits") is deferred to 2.0.** Hidden-
   codes commands deliver the same user value (apply + undo formatting) without
   the bidirectional rich-edit/caret/undo-coherence risk. #516 is rescoped to
   "rich formatting via hidden codes + read-only lens un-gate."
5. **Honest fidelity is mandatory.** Before any lossy conversion (open or save),
   `scan_rtf_features` / `scan_*` results are surfaced so the user knows exactly
   what a target format cannot carry.

## 4. The cross-surface fidelity matrix (the contract)

What each surface carries, today and at the end of this plan. "✓" = faithful,
"→md" = degrades to the visible-text / canonical-markup subset, "warn" = honest-
fidelity warning shown before the user commits.

| Feature | Canonical (md) | RTF | Word (.docx) | HTML | Plain .txt |
| --- | --- | --- | --- | --- | --- |
| Bold / italic | ✓ | ✓ | ✓ | ✓ | →md (warn) |
| Headings / bullets / links | ✓ | ✓ | ✓ | ✓ | →md (warn) |
| Underline | P1 | P1 | P1 | P1 | →md (warn) |
| Font family / size | P1 | P1 | P3 | P1 | →md (warn) |
| Paragraph alignment | P2 | P2 | P2/P3 | P2 | →md (warn) |
| Color / highlight | P4 | P4 | P4 | P4 | →md (warn) |
| Tables / images / footnotes | — | read: sanitized; warn | read: extract; warn | warn | warn |

P1–P4 are the phases in §6. "—" means out of scope for this plan (tables belong
to Table Studio, #514 / §1.9 of the roadmap). The read direction always *accepts*
more than QUILL can re-emit; `scan_rtf_features` reports the gap so a round trip
never loses something silently.

## 5. Architecture — one model, many doors

```
  .docx / .rtf / .html / .md / .txt   (readers, quill/io/*)
                  |
                  v
       RichDocument  (quill/io/rtf_model.py)   <-- the single shared model
            ^      |
   markdown_to_rich|  rich_to_markdown
            |      v
   Canonical markup string == Document.text   <-- what the plain editor edits,
            ^      |                               what undo/search/AI act on
  format    |      |  offset map (analyze_markdown)
  commands  |      v
       Plain wx.TextCtrl editor  +  optional read-only RichTextSurface preview
                  |
                  v
  writers (quill/io/*)  ->  .docx / .rtf / .html / .txt   (materialize tags)
```

Every reader converges on `RichDocument`; every writer consumes it. The editor
and undo never see anything but the canonical markup. The rich preview is a
projection of that markup, rebuilt on change — never a second source of truth.

## 6. Phasing

Aligned with the design note §10; each phase is independently shippable and
user-visible, and each lands its own changelog/user-guide/PRD updates (per the
incremental-docs rule). **P1–P4 below landed together on 2026-06-27** (see the
status block at the top); they are kept here for the record. **P5 is the only
open phase.**

- **P1 — Inline run formatting.** Add `underline`, `font_family`,
  `font_size_pt` to `InlineSpan` / `InlineFormat`; teach the inline walker to
  read/write Pandoc-style attribute spans (`[text]{font-family="Arial"
  font-size="14"}`) consumed as zero-width markup so the offset map stays exact.
  `tagging.py` builders; Format menu **Font** / **Size** / **Underline**;
  "Describe formatting at cursor" spoken command; HTML + RTF render. Storage
  Option A (markup canonical). Undo via the plain-lens stack.
- **P2 — Paragraph alignment.** `RichParagraph.align` validated against
  `{left, right, center, justify}`; fenced-div materialization (`::: {align=...}`);
  Align menu; interrogation; HTML + RTF render.
- **P3 — Faithful Word writer.** New `quill/io/docx_writer.py` using
  **python-docx** (new dependency — needs explicit approval), replacing the
  Pandoc docx branch; per-run bold/italic/underline/font/size, per-paragraph
  alignment and styles. Falls back to the existing Pandoc path if python-docx is
  absent, so docx export never hard-fails.
- **P4 — Color / highlight** across model, builders, all writers, and speech.
- **P5 — Clean-document end-state (Option B).** Out-of-band `FormatOverlay`
  (range annotations over truly-plain text) + an `EVT_TEXT` delta handler that
  shifts ranges on insert/delete + sidecar persistence, so even saved `.md` /
  `.txt` is literally clean text. Everything above (model, writers, menus,
  speech, tests) carries over unchanged because both options converge on the
  same `RichDocument`.
- **Read-only lens un-gate** (parallel, gated on #526): after the JAWS / NVDA /
  Narrator pass, flip `core.rich_text_lens` on so users can view formatting
  rendered and hear caret formatting. No editing risk.

**Deferred to 2.0:** the editable WYSIWYG pane with bidirectional rich-edit
undo (#516's original literal acceptance). Revisit only if hidden-codes proves
insufficient in practice.

## 7. Interrogation & speech

- Extend `describe_inline_format` with the new fields so it speaks e.g. "Arial,
  14 point, centered, bold."
- A **"Describe formatting at cursor"** command (hotkey) reads
  `format_at_markdown_offset` at the caret and announces it — the primary,
  explicit, quiet interrogation affordance.
- Optional on-caret-move announcement of formatting transitions behind a user
  toggle (`describe_format_transition`), for users who want continuous feedback.
- Every apply action announces its result ("Centered", "Arial 14 point
  applied").

## 8. Risks & gates

- **`wx.RichTextCtrl` SR quality** is the real risk and the reason for the gate.
  Mitigation: the rich pane stays read-only and optional; the plain lens is
  always authoritative; un-gate only after #526.
- **New dependency `python-docx`** (P3) needs explicit approval before adding to
  `pyproject.toml`.
- **Module-size budget (GATE-11).** Keep new logic in `tagging.py` /
  `rtf_model.py` / `docx_writer.py`; keep `main_frame.py` command wrappers thin.
- **mypy** stays scoped to `core` / `io`; all new/changed core+io modules must
  type-check.
- **No new network egress** is introduced by any phase.
- **Dialog gates** are not triggered by the menu-first cut; a later "Font..."
  dialog must route through `_show_modal_dialog`.

## 9. Verification

- Unit: extend `tests/unit/io/test_rtf_model.py` for span/div round-trip and
  offset stability under the new attributes; `tests/unit/core/` cases for
  `format_speech` phrasing and `tagging` builders; writer round-trip tests for
  RTF/HTML (and docx in P3).
- Fidelity: tests asserting `scan_rtf_features` / honest-fidelity warnings fire
  for each unsupported construct.
- Manual SR pass (part of #526) before un-gating the read-only lens.

## 10. Relationship to other workstreams

- **#514 structured Word view + CSV grid** and **Table Studio (§1.9)** own
  tables/grids; this plan deliberately does not. Read direction sanitizes and
  warns on tables/images rather than dropping them silently.
- **#517 Quillin Hub** is unrelated (web/ops).
- Roadmap §1.6 lists "native RTF editing (#516)"; this plan supersedes the bare
  line item with the decided, phased approach above.
