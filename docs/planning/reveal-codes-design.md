# Reveal Codes — Design Note

Status: Draft for future consideration (not scheduled)
Author: design exploration, 2026-06-29
Scope: A WordPerfect-style **Reveal Codes** experience for QUILL — a second,
synchronized view that makes the document's *hidden* formatting codes and
invisible characters explicit, navigable, and (later) editable, while the main
editor stays clean text. Screen-reader-first, braille-aware, keyboard-driven.

Related:
- `docs/planning/rich-text-formatting-hidden-codes-design.md` — the hidden-codes
  formatting model this feature visualizes (the codes Reveal Codes reveals).
- Shipped building blocks: **Describe Formatting at Cursor**
  (`quill/ui/main_frame_format_codes.py`), **Describe Character at Cursor**
  (`quill/core/char_describe.py`), the markup↔visible **offset map**
  (`quill/ui/rich_text_surface.py`), and the spoken vocabulary
  (`quill/core/format_speech.py`).
- Heritage research: WordPerfect / WordPerfect Editor "Reveal Codes" (`ed30.md`).

## 1. Vision and heritage

WordPerfect's **Reveal Codes** (Alt-F3) split the screen: clean text on top, the
same text below with every formatting and structural code shown inline as a
bracketed token — `[Bold On]`, `[Tab]`, `[HRt]`, `[Font:Courier]`. The two cursors
moved together: put the cursor on a word above and the matching code lit up below;
move through the codes below and the text cursor tracked. You could **delete a code
to remove its effect** ("cursor on `[Bold On]`, press Delete, text unbolds"). The
WordPerfect *Editor* variant (`ed30.md` §"Reveal Codes") showed the raw hex/ASCII
of every byte in a synced lower window. People *loved* this: it removed all mystery
about why text looked the way it did, and it gave total, surgical control.

QUILL is the perfect home to bring this forward, and to do it better than the
original. QUILL already keeps the **codes hidden** by design (the editing buffer is
clean text; formatting rides along as invisible codes materialized only at export —
see the hidden-codes design note). Reveal Codes is the natural companion: a way to
*see and hear* exactly what is in the document, on demand, without ever cluttering
the editor. And because QUILL is screen-reader-first, we can do something WordPerfect
never could — make every code a **spoken, brailled, individually-navigable object**,
not just a visual glyph. This is "Reveal Codes" reimagined for people who read with
their ears and fingers.

The guiding feeling: **nothing about your document is hidden from you.** Press one
key, and the whole invisible scaffold — every bold span, font change, tab, hard
return, non-breaking space, page break — becomes a place you can move through,
inspect, and (later) repair. The editor stays clean; the truth is one keystroke away.

## 2. What QUILL already has to build on

Reveal Codes is an assembly of pieces QUILL already owns, not a rewrite:

1. **A hidden-codes formatting model.** The rich-text model
   (`quill/io/rtf_model.py`: `InlineSpan` / `RichParagraph` / `RichDocument`) and
   the Pandoc-span markup (`[text]{font-family="Arial" font-size="14"}`, `::: {align}`)
   already represent every code Reveal Codes must show.
2. **A markup↔visible offset map.** `quill/ui/rich_text_surface.py`
   (`analyze_markdown`, `format_at_markdown_offset`, `build_render_plan`) already
   maps a visible caret offset to the markup/formatting in effect there. The whole
   "two cursors that track each other" mechanism is exactly this map, used in both
   directions.
3. **A spoken formatting vocabulary.** `quill/core/format_speech.py`
   (`describe_inline_format`, `describe_format_transition`) already turns formatting
   into phrases like "Arial, 14 point, centered, bold." Reveal Codes reuses it for
   token labels.
4. **An invisible-character vocabulary.** `quill/core/char_describe.py`
   (`describe_character`, shipped with "Describe Character at Cursor") already names
   tabs, no-break/zero-width spaces, smart quotes, line endings, and their code
   points. These are the *structural* codes (`[Tab]`, `[HRt]`, `[NBSP]`).
5. **On-demand interrogation precedent.** "Describe Formatting at Cursor" and
   "Describe Character at Cursor" already answer "what is here?" for a single point.
   Reveal Codes generalizes point interrogation into a continuous, navigable map.

So Reveal Codes is mostly **a new view over existing data**, plus a synchronization
controller and a thin code-stream model that unifies the formatting and character
vocabularies into one ordered token list.

## 3. The experience

### 3.1 Turning it on (View menu) and reaching it (F6 region cycle)

- **View → Reveal Codes** is a checkable menu item that *shows or hides* the Reveal
  Codes pane. The choice persists (`settings.reveal_codes_visible`). Hidden is the
  default and costs nothing (the code stream is not built while hidden).
- **F6 cycles between the regions; Reveal Codes is one of them when shown.** QUILL
  already has an F6 / Shift+F6 region rotation (`navigate.next_region` /
  `navigate.previous_region`, implemented by `_current_focus_region_labels()` /
  `_focus_region()`), today: **Editor → (Document Tabs) → (Preview) → Status Bar →**
  wrap. Reveal Codes joins that rotation **whenever the pane is showing**, right
  after the Editor, so F6 moves **Editor → Reveal Codes → Status Bar** (and through
  Document Tabs / Preview when those are present), and **Shift+F6 cycles backwards**.
  No new keybinding and no surprise — Reveal Codes is just another first-class
  region, the modern form of WordPerfect's "switch windows." Entering it lands on the
  code or text segment at your current editing position; leaving it (F6 onward, or
  Escape back to the editor) returns you exactly where you were inspecting.

### 3.2 The synchronized cursors (the heart of it)

The two views share one logical position, expressed in two coordinate spaces:

- **Move in the pane → the editor follows.** Arrow to a code/segment in the pane and
  QUILL sets the editor's caret (and a light selection over the affected range) to
  the matching visible-text offset. If the editor is on screen, the highlight tracks
  with you; if you then press F6/Escape, you land exactly there.
- **Move in the editor → the pane follows.** As the editor caret moves, the pane
  highlights the token at that offset (throttled, off the hot path). When you enter
  the pane, you are already on the right token.

The mapping is the existing visible↔markup offset map; the controller just keeps the
two carets in agreement, marshaling cross-view updates through `wx.CallAfter`.

### 3.3 What you hear and feel

This is where QUILL surpasses the original. Each token is a first-class, labeled
object:

- **Spoken:** arrowing onto a token announces it as a unit — "Bold on", "Tab",
  "Hard return", "Font Arial", "Center on", "Non-breaking space", "Page break" —
  never spelled out character by character. Text segments read as their words.
- **Paired codes are related aloud:** landing on `[Bold On]` can announce its reach
  — "Bold on, 12 characters" or "Bold on, to 'world'" — and a command jumps to the
  matching `[Bold Off]`.
- **Braille:** the pane renders the codes **literally and inline** —
  `⠦Bold on⠴ Hello ⠦Bold off⠴⠦Tab⠴` — so a braille reader feels the scaffolding the
  way a WordPerfect user once saw it. This is the truest revival of the original for
  braille users.
- **Verbosity is yours.** `settings.reveal_codes_verbosity` (quiet / balanced /
  detailed) controls how much each move announces — from just the code name to the
  full attribute set and pairing distance.

### 3.4 Two presentations of the same stream

A single setting (`settings.reveal_codes_view`) chooses how the stream is shown; both
are driven by the identical token model:

- **Structured (default, most accessible):** one navigable item per token in a
  read-only list — `[Bold On]`, `Hello world`, `[Bold Off]`, `[Tab]`,
  `[Hard Return]`. Up/Down moves token-to-token; each move is a clean, discrete
  screen-reader event and syncs the editor. No character-hunting, no ambiguity.
- **Flowed (WordPerfect parity):** the running text with bracketed code tokens
  inline, in a read-only multiline control. The caret moves by character/word but
  treats a code token as one atomic unit (you cannot land "inside" `[Bold On]`); the
  screen reader announces the token when the caret crosses it. This is the closest
  visual/braille match to classic Reveal Codes and the best fit for low-vision and
  braille users.

### 3.5 Editing from Reveal Codes (later phase)

True to WordPerfect, the pane eventually becomes a place to *act*, not just look:

- **Delete a code to remove its effect.** Put the cursor on `[Bold On]` (or `[Center
  On]`, `[Font:Arial]`) and press Delete — the span/attribute is stripped from the
  document, the editor updates, and the change is one undo step. Deleting a paired
  "on" code removes its partner too.
- **Later: insert/replace codes** from the pane (e.g. drop a `[Page Break]` at a
  point, change a `[Size:12]` to `[Size:14]`) via the same builders the Format menu
  uses. Text editing itself stays in the editor; the pane edits *codes*.

Phase 1 is read-only navigation + interrogation; code-deletion and insertion follow
(see §11).

## 4. The code-stream model — `quill/core/reveal_codes.py` (new, wx-free)

A pure, testable core module that turns the document into an ordered stream of
tokens. This is the single source of truth both presentations render and the sync
controller indexes.

```python
class TokenKind(enum.Enum):
    TEXT = "text"            # visible characters
    FORMAT_ON = "format_on"  # [Bold On], [Font:Arial], [Center On], [Style:Heading 2]
    FORMAT_OFF = "format_off" # [Bold Off], ...
    STRUCTURE = "structure"  # [Tab], [Hard Return], [Page Break], [Link: ...]
    INVISIBLE = "invisible"  # [No-Break Space], [Zero-Width Space], [Smart Quote]

@dataclass(frozen=True, slots=True)
class CodeToken:
    kind: TokenKind
    label: str           # display/braille: "Bold On", "Tab", "Font: Arial"
    spoken: str          # screen-reader phrase: "bold on", "tab", "font Arial"
    visible_start: int   # offset into the CLEAN visible text this token sits at
    visible_end: int     # == visible_start for zero-width codes; span for TEXT
    markup_start: int    # offset into the underlying markup (for edit/delete)
    markup_end: int
    pair_index: int | None = None  # index of the matching ON/OFF partner
    attrs: dict[str, str] | None = None  # font-family, font-size, color, align, ...

def build_code_stream(markup: str) -> list[CodeToken]:
    """Linearize markup into text + code tokens, in document order.

    Built on analyze_markdown()/RichDocument for formatting spans + paragraph
    attributes, and char_describe.describe_character() for structural/invisible
    characters. Every token records both its visible-text offset range (for caret
    sync) and its markup offset range (for delete/insert). ON/OFF pairs are linked.
    """
```

Design points:
- **Two offset spaces per token.** `visible_*` drives caret sync with the editor;
  `markup_*` drives code deletion/editing. Both come from the existing offset map,
  so they stay consistent with the editor's own mapping.
- **Pairing.** Run-level formatting emits an ON token at the span start and an OFF
  token at the span end, linked by `pair_index`, so the pane can show
  `[Bold On]…[Bold Off]` and jump between them. Paragraph attributes (`align`,
  `style`) emit a single block marker at the paragraph head.
- **Reuse, don't reinvent.** `label`/`spoken` for formatting come from
  `format_speech.describe_inline_format`; for invisibles from
  `char_describe.describe_character`. New vocabulary is only the bracketing.
- **Pure and incremental-friendly.** No `wx`. Accepts a markup string (or a range)
  so the pane can rebuild only the changed/visible region after edits (§10).

## 5. The code vocabulary

| Document feature | Pane label | Spoken (balanced) | Source |
|---|---|---|---|
| Bold span | `[Bold On]` / `[Bold Off]` | "bold on" / "bold off" | format_speech |
| Italic / Underline | `[Italic On]` … | "italic on" … | format_speech |
| Strike/super/subscript | `[Strikethrough On]` … | "strikethrough on" … | format_speech |
| Font family | `[Font: Arial]` | "font Arial" | rtf_model attrs |
| Point size | `[Size: 14]` | "14 point" | rtf_model attrs |
| Color / highlight | `[Color: red]` / `[Highlight: yellow]` | "red text" / "yellow highlight" | rtf_model attrs |
| Paragraph align | `[Center]` / `[Right]` / `[Justify]` | "centered" … | RichParagraph.align |
| Named style | `[Style: Heading 2]` | "heading 2" | heading_styles |
| Link | `[Link: example.com]` | "link to example dot com" | rtf_model |
| List item | `[• List]` | "bullet" | rtf_model |
| Tab | `[Tab]` | "tab" | char_describe |
| Hard return / paragraph | `[¶ Hard Return]` | "hard return" | char_describe |
| Page break | `[Page Break]` | "page break" | format codes |
| No-break / zero-width space | `[No-Break Space]` / `[Zero-Width Space]` | "non-breaking space" … | char_describe |
| Smart quote / em dash | `[Smart Quote ”]` / `[Em Dash]` | "right smart quote" … | char_describe |
| Line-ending type | `[CRLF]` / `[LF]` (detailed verbosity) | "Windows line ending" … | char_describe |

The vocabulary is intentionally small and fixed, mirroring the hidden-codes design's
"fixed, small vocabulary" principle. New code kinds are added only when the
formatting model gains them.

## 6. UI architecture

### 6.1 Layout

A horizontal splitter inside the document view: **editor on top, Reveal Codes pane
on the bottom** (the WordPerfect arrangement). The sash is keyboard-resizable and the
split ratio persists. Hiding the pane (View toggle) collapses the splitter so the
editor reclaims the full area and no stream is built. Orientation (bottom vs. side)
is an open question (§13) but bottom is the heritage default.

### 6.2 New UI module — `quill/ui/reveal_codes_pane.py`

- The pane widget (a read-only `wx.ListBox`/owner-drawn list for Structured mode, a
  read-only `wx.TextCtrl` for Flowed mode), with an accessible name and per-item
  accessible labels.
- A **sync controller** that owns the bidirectional caret tracking: editor→pane
  (throttled, on `EVT_TEXT`/idle and caret-move) and pane→editor (on selection
  change in the pane, via `wx.CallAfter`).
- Rebuild policy: rebuild the stream on document load/replace and, after edits, on a
  short idle debounce; only the visible window for large documents (§10).

Keep all logic that can be wx-free in `core/reveal_codes.py`; the pane is a thin
view + sync shell, so `main_frame.py` gains only a small delegate (GATE-11).

### 6.3 Commands

- `view.reveal_codes_toggle` — show/hide the pane (View menu, checkable). Persists.
  *Reaching* the pane is handled by the existing F6 region cycle (§6.5), not a
  separate focus command — so there is no F6 rebinding to do.
- `reveal.next_code` / `reveal.previous_code` — jump code-to-code (skip text), for
  fast scanning **within** the pane.
- `reveal.go_to_pair` — jump between an ON code and its OFF partner.
- `reveal.delete_code` — (later) strip the code under the cursor.

The `toggle` gets a keymap entry; the in-pane commands default to sensible local
keys. Everything is reassignable in the Keymap Editor.

### 6.4 Settings

- `reveal_codes_visible: bool = False` — pane shown (persisted View toggle state).
- `reveal_codes_view: str = "structured"` — `"structured"` | `"flowed"`.
- `reveal_codes_verbosity: str = "balanced"` — `"quiet"` | `"balanced"` | `"detailed"`.
- `reveal_codes_split_ratio: float` — remembered sash position.

### 6.5 F6 region cycle (decided)

Reveal Codes is a **first-class focus region**, reached through QUILL's existing
F6 / Shift+F6 rotation — no new keybinding, no conflict. Concretely:

- **`_current_focus_region_labels()`** (`quill/ui/main_frame.py`) appends
  `"Reveal Codes"` to its ordered list **when the pane is showing**, positioned right
  after `"Editor"`, so the cycle is **Editor → Reveal Codes → Status Bar** (with
  Document Tabs / Preview included when they too are present). It is omitted when the
  pane is hidden, so F6 never lands on an unreachable region — exactly the pattern
  already used for Preview (only when split) and Document Tabs (only when shown).
- **`_detect_active_region()`** recognizes focus inside the pane and reports
  `"Reveal Codes"`; **`_focus_region("Reveal Codes")`** moves focus into the pane and
  places its caret on the token matching the editor's current offset.
- **F6** (`navigate.next_region`) steps forward through the cycle; **Shift+F6**
  (`navigate.previous_region`) steps backward. Both already exist and are unchanged.

So "F6 should move between editor, Reveal Codes (if showing), and the status bar,
Shift+F6 backwards" is satisfied by adding one region to the existing rotation — the
cleanest possible integration.

## 7. Synchronization design

- **Single offset authority.** Both directions use the visible↔markup offset map
  (`rich_text_surface`). The editor caret is a visible offset; each token carries its
  visible range; mapping is O(log n) against the token list (binary search on
  `visible_start`).
- **Editor → pane** runs on caret-move/idle, throttled (coalesce rapid moves; update
  at most ~10×/sec), never on the typing hot path.
- **Pane → editor** fires on the pane's selection-change, marshaled with
  `wx.CallAfter`, setting the editor caret + a light range highlight.
- **Edits invalidate, idle rebuilds.** A document edit marks the stream stale; a
  short debounce rebuilds it (incrementally where possible) so the pane never blocks
  typing. Until rebuilt, the pane shows the last good stream with a subtle "updating"
  state.

## 8. Accessibility (the point of the whole thing)

- **Discrete, labeled objects.** Structured mode makes every code a list item with a
  real accessible name, so screen readers announce "Bold on" as one event — the
  single biggest win over a visual-only Reveal Codes.
- **Focus is honest.** Entering the pane announces "Reveal Codes"; returning
  announces "Editor"; the caret always lands on the token matching where you were.
- **Braille-literal.** Flowed mode renders codes inline so braille users feel the
  scaffolding; Structured mode gives one code per braille line for scanning.
- **No color-only meaning.** Codes are conveyed by bracketed text + label, never by
  color alone; any visual styling is additive.
- **Quiet by default.** Verbosity is user-controlled; navigation never chatters more
  than the user asked for. Respect `prefers-reduced-motion` for any highlight
  animation (use instant highlight).
- **Keyboard-complete.** Show/hide, focus, code-to-code, pair-jump, sash resize, and
  (later) delete are all keyboard-reachable and reassignable.

## 9. Reuse map (what we are NOT rebuilding)

| Need | Existing code |
|---|---|
| Formatting in effect at an offset | `rich_text_surface.format_at_markdown_offset` |
| Spoken formatting phrases | `format_speech.describe_inline_format` |
| Invisible-character names/code points | `char_describe.describe_character` |
| Markup ↔ visible offset map | `rich_text_surface.analyze_markdown` |
| Render planning over markup | `rich_text_surface.build_render_plan` |
| Code deletion = strip span/attr | the hidden-codes builders (`core/tagging.py`) |

## 10. Performance

- **Zero cost when hidden** — no stream built, no sync wired.
- **Lazy + incremental** — build only the visible window for large documents;
  rebuild only the changed region after edits, on an idle debounce.
- **Virtualized list** in Structured mode for very long documents.
- **Throttled sync** so caret tracking never touches the typing hot path.

## 11. Phasing

1. **Read-only Reveal Codes (Structured mode).** `core/reveal_codes.build_code_stream`,
   the pane, View toggle, F6 focus, bidirectional caret sync, formatting + invisible
   tokens, spoken labels and verbosity. Built on storage Option A (markup canonical).
2. **Flowed mode + braille-literal rendering**, code-to-code and pair-jump commands.
3. **Edit from the pane:** `reveal.delete_code` (strip a span/attribute as one undo
   step), then code insertion/replacement via the Format-menu builders.
4. **Converge with storage Option B** (the out-of-band overlay from the hidden-codes
   design): the stream is then built from the overlay instead of markup, unchanged
   above that boundary. Optional: macro/field codes if QUILL ever adds them.

## 12. Verification

- **Unit (`tests/unit/core/test_reveal_codes.py`):** `build_code_stream` over
  representative markup — correct token order, labels, ON/OFF pairing, and that
  `visible_*`/`markup_*` offsets round-trip against the offset map; invisibles
  (tab, NBSP, smart quote, hard return) produce the right tokens.
- **Sync:** moving a synthetic caret in either space lands on the expected token
  (pure-function tests on the index; a thin UI test for the controller).
- **Accessibility:** each pane item exposes an accessible name; entering/leaving
  announces; verbosity levels gate phrase length.
- **End-to-end:** `python -m quill`, type a formatted paragraph, F6 into Reveal
  Codes, arrow through `[Bold On] … [Bold Off] [Tab] [Hard Return]`, confirm the
  editor caret tracks and the announcements match; toggle the View item to hide/show.
- **Gates:** `ruff`, `mypy quill\core` (the new core module), dialog/menu lints if a
  dialog is added, GATE-11 (logic stays in `core/reveal_codes.py`).

## 13. Open questions / decisions for scheduling

- **Split orientation default:** bottom (WordPerfect heritage) vs. side, and whether
  to offer both.
- **Edit scope in the pane:** code-deletion only, or full code insert/replace, and
  how aggressively to allow text editing from the pane (WordPerfect allowed it).
- **Storage coupling:** ship Phase 1 against Option A markup now, or wait for the
  Option B overlay so the stream is built from the overlay from day one.
- **Flowed-mode atomicity:** confirm the "caret cannot land inside a code token"
  behavior is comfortable for braille review, or offer a mode where it can.
- **Persistence of pane state** per document vs. global (remember last view/verbosity).
