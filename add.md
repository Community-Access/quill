# The Research Shelf: one spine for Look Up, Keep, and Send

**A definitive integration plan for issues #897 (Wikipedia lookup), #895 (Clip Library), and #900 (Send / Copy as Email).**

---

## 1. The insight that ties all three together

Read individually, these three issues look unrelated:

- **#897** wants an encyclopedia (Wikipedia) entry added to the non-AI Look Up surface.
- **#895** wants a clipboard *history* that lives alongside the curated 12-slot Copy Tray.
- **#900** wants a "hand this document to my email client" convenience.

But look at what they actually *are*. Each one is a different verb applied to the **same noun** — a small, portable piece of content that a writer found, kept, or wants to hand off:

| Issue | The verb | The content |
|-------|----------|-------------|
| #897 | **Look up** | a Wikipedia summary, a definition, a synonym set |
| #895 | **Keep** | anything you copied — a paragraph, a quote, a looked-up fact |
| #900 | **Send** | the document, a selection, or a kept fragment |

The magic is to stop building three features and instead build **one spine** — a portable content object — and then let *Look Up*, *Keep*, and *Send* all operate on it. When you do that, the three issues collapse into a single, coherent user story:

> **You look something up. You keep it. You send it.** And at every step you choose whether it travels as **plain text, Markdown, or HTML** — one knob, honored identically everywhere.

That last sentence is the user's "either html, markdown or text… configurable and interchangeable" requirement — and the boldest part of this plan is that the *same* format knob that renders a Wikipedia summary also governs what lands in the Clip Library and what fills an email body. Format becomes a property of *content in motion*, not a per-feature afterthought.

---

## 2. The spine: `Fragment` + the tri-format renderer

### 2.1 What already exists (we are not inventing a renderer)

QUILL's editor already keeps its canonical text as **Markdown-style markup**, and `quill/io/export.py` already knows how to turn that markup into all three target shapes:

- `markdown_to_plain_text(markup, link_style)` → readable plain text
- `markdown_to_html(markup, title)` → standalone HTML
- verbatim → Markdown (it already *is* Markdown)

So the "interchangeable html / markdown / text" engine is **already written and unit-tested**. We do not build a formatter. We build a small object that carries canonical Markdown plus provenance, and defer to these existing functions to render it. This is the whole trick — the ambition is in the *wiring*, not in new format code.

### 2.2 The new core object

Create `quill/core/fragment.py` (pure, wx-free, strict-typed, in-scope for `mypy quill\core`):

```python
@dataclass(frozen=True, slots=True)
class Fragment:
    """A portable piece of content with one canonical form and known origin.

    The canonical form is QUILL Markdown-style markup — the same markup the
    editor and every io/export writer already speak — so a Fragment renders to
    text, Markdown, or HTML through the existing export functions, and can be
    inserted into the editor with no conversion at all.
    """
    markup: str                      # canonical QUILL Markdown markup
    title: str = ""                  # human/screen-reader label, e.g. "Wikipedia: Ada Lovelace"
    source: str = ""                 # provenance: "Wikipedia", "Look Up", "Clipboard", "Document"
    source_url: str = ""             # citation link when one exists (Wikipedia, dictionary)
    kind: str = "text"               # text | encyclopedia | definition | image | file
    created_at: str = ""             # ISO-8601, UTC

class FragmentFormat(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"

def render_fragment(frag: Fragment, fmt: FragmentFormat, *, link_style: str = "text_url") -> str:
    """Render a Fragment in the requested format (pure).

    TEXT -> markdown_to_plain_text; MARKDOWN -> markup verbatim (+ optional
    citation footer); HTML -> markdown_to_html. A source_url, when present, is
    appended as a citation appropriate to the format (a line, a `[title](url)`,
    or an <a>), so a kept or sent fact never loses where it came from.
    """
```

`render_fragment` is the *single* place the three-way format choice is honored. Every feature below calls it. Change how a format renders once, and Look Up, the Clip Library, and Email all change together. That is what "interchangeable" buys us.

Everything in `fragment.py` is a pure function of its inputs, so it is fully unit-testable in `tests/unit/core/` with no display — matching the pattern `lexical.py` already established (its `render_lookup`, `merge_terms`, and `normalize_*` functions are all pure and directly tested).

---

## 3. Issue #897 — Wikipedia lookup, as a Fragment source

This is the smallest and best-scoped of the three (the issue's own follow-up comment already lays out the shape), and it becomes the **proving ground** for the spine.

### 3.1 The provider (rides existing `lexical.py` infrastructure)

Add to `quill/core/lexical.py`, in the exact shape of `FreeDictionaryProvider` / `DatamuseProvider`:

```python
WIKIPEDIA_HOST = "https://{lang}.wikipedia.org"

@dataclass(frozen=True, slots=True)
class EncyclopediaEntry:
    title: str
    summary: str
    url: str

class WikipediaProvider(LexicalProvider):
    """Keyless encyclopedia summaries from the Wikipedia REST API."""
    name = "Wikipedia"
    online = True
    # GET /api/rest_v1/page/summary/{title} -> {title, extract, content_urls...}
```

- Extend `LexicalResult` with `encyclopedia: tuple[EncyclopediaEntry, ...] = ()` and include it in `is_empty` / `_union_results`.
- Register `WikipediaProvider()` in `default_service()` alongside the other two online providers.
- Same guarantees as its siblings: keyless, HTTPS through `verified_ssl_context()` (SEC-5), cached, error-tolerant (a Wikipedia failure degrades to the offline answer, never raises), and **only queried when `online=True`** — the existing per-feature consent gate already governs this.

### 3.2 Surfacing it in the existing Look Up dialog

`render_lookup()` (lexical.py:442) and `build_lookup_items()` (lexical.py:419) are pure and already drive the dialog. Extend both:

- `render_lookup` gains an **"Encyclopedia:"** section (title + summary + source line) — a few lines, same pattern as the Synonyms/Antonyms sections.
- `build_lookup_items` adds the encyclopedia entry as a **read-only context item** (like a definition — no `insert` action), *plus* two new actionable items that are the bridge to the other two issues:
  - **Keep** → push this entry into the Clip Library as a Fragment (§4)
  - **Send** → hand this entry to Email as a Fragment (§5)

### 3.3 The format knob lands here first

The encyclopedia entry is a `Fragment(kind="encyclopedia", source="Wikipedia", source_url=…)`. A new setting decides how it renders when *displayed, kept, or sent*:

Add to `quill/core/settings_specs.py`, mirroring the existing `plain_text_link_style` choice spec (settings_specs.py:582):

```python
SettingSpec(
    "lookup_output_format",
    "Look Up result format",
    "editing",
    "choice",
    "How a looked-up encyclopedia or dictionary result is formatted when you "
    "read it, keep it in the Clip Library, or send it — plain text, Markdown, "
    "or a rich HTML snippet. Interchangeable at any time.",
    choices=(("text", "Plain text"), ("markdown", "Markdown"), ("html", "HTML")),
    keywords=("wikipedia", "lookup", "encyclopedia", "format", "html", "markdown"),
),
```

"Interchangeable" is literal: the setting is read at render time, never baked into stored data. A fact kept as a Fragment stores only canonical Markdown; flipping the format setting later changes how it pastes and how it emails, retroactively.

### 3.4 Network egress + gates

- **`network_egress_audit.py`**: add the Wikipedia REST endpoint as a new audited call site (required for any new outbound call). It is consent-gated by the same `online=True` path the other lexical providers use.
- No new dependency (stdlib `urllib`, already used in `lexical.py`).

---

## 4. Issue #895 — the Clip Library, as a Fragment store

The issue is explicit: **do not touch Copy Tray.** The 12-slot curated model stays exactly as-is (`quill/core/copy_tray.py`). The Clip Library is a *second, complementary tier* — a rolling history of Fragments.

### 4.1 New core store `quill/core/clip_library.py`

Model it on `CopyTray` (same atomic-JSON persistence via `write_json_atomic`, same load-tolerance), but storing **Fragments, not bare strings**:

```python
class ClipLibrary:
    """Rolling history of Fragments — the automatic tier beneath Copy Tray."""
    _FILENAME = "clip_library.json"
    _CAP = 200                       # ring buffer; oldest non-favorite drops first

    def remember(self, frag: Fragment) -> None: ...   # de-dupes by markup+source
    def favorite(self, index: int) -> None: ...       # protects from ring eviction
    def search(self, query: str) -> list[tuple[int, Fragment]]: ...
    def promote_to_tray(self, index: int, slot: int) -> str: ...  # the bridge
```

Because a clip is a `Fragment`, it **pastes in any of the three formats** through `render_fragment` — the same knob as §3.3. A Wikipedia summary kept from the Look Up dialog pastes as HTML into an HTML-aware target or as clean text elsewhere, the user's choice, decided at paste time.

### 4.2 Auto-capture (off by default, privacy-flagged)

Per the issue: an optional "remember everything I copy" mode.

- Setting `clip_library_autocapture` (bool, default **False**). Enabling it shows an explicit one-time privacy consent — silently recording clipboard history has real privacy weight, and QUILL's convention is to flag anything with such implications.
- When on, the existing copy path also calls `clip_library.remember(Fragment(markup=copied_text, source="Clipboard", …))` via `wx.CallAfter` (UI thread owns clipboard access).
- Sensitive-content guard: skip capture when the editor's redaction/secret heuristics (`quill/stability/redaction.py`) flag the copied text — history should not quietly hoard passwords.

### 4.3 Non-text clips (accessible descriptions, not binary)

The issue asks for images/files as **named, described objects**, not raw binary. A `Fragment(kind="image", title="Screenshot 3:14pm", markup="![Screenshot 3:14pm](…)")` carries an accessible label and a Markdown image reference — never a binary blob in the accessibility bar. Files become `kind="file"` with a path and speakable name. This keeps the Clip Library inside Copy Tray's existing "text and simple named objects only" accessibility contract.

### 4.4 The bridge to Copy Tray

`promote_to_tray(index, slot)` renders the Fragment to plain text (Copy Tray is a text store) and calls `CopyTray.copy_to(slot, text)`. This is the natural two-tier flow the issue asks about: the Clip Library is the wide net; promoting into a curated Copy Tray slot is how a rolling clip graduates to a permanent, labeled one. Copy Tray's code and model are untouched.

### 4.5 UI

New `quill/ui/clip_library_dialog.py` modeled on `copy_tray_dialog.py`, opened from a new command in a `main_frame_clip_library.py` mixin (new command handlers belong in a mixin, not `main_frame.py`). Reuse Copy Tray's proven screen-reader patterns: a searchable, arrow-navigable list; peek-before-paste; spoken feedback; **no checkboxes** (per house rule — favorites toggle via a button, and the list reorders by recency). All modals route through `_show_modal_dialog` with `apply_modal_ids`.

---

## 5. Issue #900 — Send / Copy as Email, as a Fragment sink

Email is the **third verb** on the same noun. The `mailto:` mechanism already exists in the codebase — `main_frame_power_tools.py` opens `mailto:` links via `webbrowser.open` (power_tools.py:622-627). We generalize it from "open a link's address" to "compose a message from a Fragment."

### 5.1 `quill/core/email_handoff.py` (pure)

```python
def build_mailto(frag: Fragment, fmt: FragmentFormat, *, subject: str) -> str:
    """Build a mailto: URL whose body is the Fragment rendered in `fmt`.

    Body is render_fragment(frag, fmt); subject defaults to the document name
    or Fragment title. Pure and testable — no webbrowser, no wx.
    """
```

- **Send as Email** (from a document, selection, looked-up fact, or clip) → build the `mailto:` and hand off via `webbrowser.open`, exactly the existing power-tools call site, reused. Simplest, safest, no new credential surface — matching the issue's recommended `mailto:`-only starting scope.
- **Copy as Email Body** → render the Fragment in the chosen format and put it on the clipboard, for the common case where a mail client won't accept a long `mailto:` body. HTML format copies HTML-rich; text/Markdown copy plain.
- **Format**: reuse the same three-way choice. Add `email_body_format` *or* simply reuse `lookup_output_format` under a shared "content format" umbrella — see §6.1. HTML email bodies are the payoff: a looked-up Wikipedia summary emails as a formatted snippet with a live citation link, all from the one knob.

### 5.2 Consent, spell check, egress

- Pre-send spell-check prompt and explicit consent, matching QUILL's convention for anything leaving the machine (the issue calls this out; it mirrors the network-egress consent pattern).
- **`network_egress_audit.py`**: `mailto:` hand-off is a launch, not a direct socket, but add an audit entry documenting it as an outbound path for completeness and reviewability.
- Non-goal held firmly: **no SMTP, no account management, no Outlook COM.** This is a hand-off convenience, exactly as scoped.

---

## 6. The unified surface — where the magic is felt

### 6.1 One "content format" choice, three honorings

Rather than three separate format settings, expose **one** user-facing choice — *"How kept and sent content is formatted: Text / Markdown / HTML"* — read at render time by Look Up display, Clip Library paste, and Email body alike. (Implement as a single setting key consumed by all three; keep the per-feature spec name generic, e.g. `content_handoff_format`.) One knob. Interchangeable. Honored identically everywhere. That is the user's requirement met at the architecture level, not bolted on per feature.

### 6.2 Two universal verbs: **Keep it** and **Send it**

Because Look Up results, selections, clips, and the whole document are all `Fragment`s, we add two commands that work *everywhere*:

- **`fragment.keep`** — push the current context (looked-up entry, selection, or document) into the Clip Library.
- **`fragment.send`** — hand the current context to Email.

Registered once in the command registry, surfaced from the Look Up dialog, the Clip Library dialog, the editor context menu, and the document/File menus. A writer learns *one* pair of verbs and they compose across the entire research-to-share loop.

### 6.3 The end-to-end story (the "magical" flow)

1. Writer highlights *"Ada Lovelace,"* opens **Look Up** → the offline thesaurus, Free Dictionary, Datamuse, **and now a Wikipedia summary** appear in one accessible surface.
2. The summary is a `Fragment`. Writer presses **Keep it** → it lands in the **Clip Library** with its Wikipedia citation intact.
3. Later, writer opens the Clip Library, finds it by search, **pastes** it into the draft — as HTML, Markdown, or clean text per their one format setting.
4. Writer finishes the draft and presses **Send it** → the document (or just that clip) opens in their mail client, body formatted in the same chosen shape, citation link live.

Three issues. One noun, three verbs, one format knob. Look up → keep → send.

---

## 7. Build order (each step ships value alone)

| Phase | Deliverable | Depends on | Ships without the rest? |
|-------|-------------|-----------|-------------------------|
| **0** | `fragment.py` + `render_fragment` + tests | existing `io/export.py` | spine only, internal |
| **1** | Wikipedia provider + Look Up section (#897) | Phase 0 | **Yes** — #897 fully closed |
| **2** | Clip Library store + dialog + Copy Tray bridge (#895) | Phase 0 | **Yes** — #895 fully closed |
| **3** | Email hand-off (#900), reusing the mailto call site | Phase 0 | **Yes** — #900 fully closed |
| **4** | Unified `keep` / `send` verbs + single format setting | Phases 1–3 | the integration payoff |

Phase 0 is a few pure functions over code that already exists. Phases 1–3 each independently close their issue on the shared spine, so the plan degrades gracefully — even if only Phase 1 ships, #897 is done and the spine is proven. Phase 4 is where the three become one.

---

## 8. Invariant & gate checklist (QUILL house rules)

- **Layering**: `fragment.py`, `clip_library.py`, `email_handoff.py`, Wikipedia provider → all in `quill/core`, wx-free, strict-typed (`mypy quill\core`). Renderers reused from `quill/io/export.py` (also wx-free). UI lives in new mixins (`main_frame_clip_library.py`, extensions to power-tools/lookup), never bloating `main_frame.py`.
- **Threading**: all clipboard and mail-client access on the UI thread; background lookups on `QuillTaskManager`, results marshaled with `wx.CallAfter`.
- **Persistence**: Clip Library JSON via `write_json_atomic`; tolerant load like `CopyTray._load`.
- **Network egress (GATE)**: new audit entries for the Wikipedia endpoint and the `mailto:` hand-off; both consent-gated.
- **Dialogs**: every new dialog through `_show_modal_dialog` + `apply_modal_ids`; passes the dialog-inventory and button-contract gates.
- **Error codes (GATE-EC)**: any new exception (e.g. a Clip Library corruption error) inherits `CodedError` with a unique `QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>` code.
- **Safe Mode**: Wikipedia lookup respects the existing online-consent gate; no AI is involved in any of the three (the whole point of #897's non-AI framing is preserved).
- **Accessibility (QUILL is screen-reader-first)**: reuse Copy Tray's proven SR patterns — searchable arrow-navigable lists, peek-before-paste, spoken feedback, **no checkboxes in list controls** (combobox-add + reorderable list per house rule); non-text clips carry accessible names, never raw binary. Every new surface is keyboard-complete and announces on enter/exit.
- **Module size budget (GATE-11)**: new logic in new modules keeps `main_frame.py` off the ratchet.

---

## 9. Open decisions for your review

1. **One format setting or two?** §6.1 recommends a *single* `content_handoff_format` consumed by Look Up, Clip Library, and Email. Alternative: keep `lookup_output_format` and `email_body_format` separate for finer control. Recommendation: **one** — it is the cleaner expression of "interchangeable," and per-target overrides can come later if anyone asks.
2. **Clip Library capacity / eviction**: proposed 200-item ring with favorites protected. Adjustable.
3. **Wikipedia language**: default to the UI/document language, fall back to `en`. Confirm.
4. **Auto-capture default**: proposed **off**, behind a one-time privacy consent. Confirm you want it available at all (some deployments may prefer to omit clipboard-history capture entirely).

---
---

# Backlog review: remaining open issues

Proposals and priorities for the rest of the open backlog. Issues **#895, #897, #900** are covered in depth in the integration plan above. **Already shipped and documented in the CHANGELOG / release notes (removed from this future-facing list):** #909 (the free-first import pipeline is now a base dependency), #890 (Casual Writer tightened to a true "just write" profile), and the Report-a-Bug "No token" build regression. Closed items (#898 Second View, #901 tablet/low-vision, #905/#906/#907 Convert-Non-ASCII bugs) are excluded.

## Priority ladder (my recommendation)

| Rank | Issue | Title (short) | Impact | Confidence | Why here |
|------|-------|---------------|--------|-----------|----------|
| **P1** | #891 | Print Studio (preview, margins, odd/even/reverse) | High | Medium | "The biggest concrete gap" in the Jarte comparison; a blind user still prints for sighted colleagues. |
| **P1** | #899 | Mandatory alt text + inline object placeholders | High | Medium | The one genuine *accessibility* win here (not just parity). Now well-scoped — GLOW already does audit/repair; only insertion-time enforcement + inline announcement remain. |
| **P2** | #892 | Keyboard-first Header/Footer Builder | High | Medium | Named Jarte-Plus gap; self-contained, but real net-new metadata + export work. Natural sibling to #891. |
| **P2** | #894 | Accessible AutoOutline (heading auto-numbering) | Medium | Med-High | Rides existing `markdown_sections` parsing; useful for agendas/policies/board packets. |
| **P3** | #896 | Work Personas (launchable profiles) | Med-High | Medium | Strong story, but the most integration-heavy item (profiles + sessions + copy tray + folders at once). Do it after its pieces settle. |
| **P3** | #893 | "Rich Document" discoverability | Medium | High (feature exists) | Downgraded per the issue's own re-check: serves a *secondary* audience (low-vision / ex-Word), not QUILL's core keyboard-first user. Low cost, low urgency. |

Rationale for the shape: the two items that are genuinely *mission* work (printing you can't do today, accessibility you can't enforce today) lead, then a band of solid, well-scoped features, with the integration-heavy and secondary-audience items last.

---

## #891 — Print Studio: accessible preview, margins, odd/even/reverse — **P1**

**State:** Real wx print plumbing already exists — `_print_data` (`main_frame.py:~1143`), a Page Setup item (`~1637`) on `wx.PageSetupDialogData`, and `print_document()` (`~9908`) driving `wx.Printer`. Missing: any preview surface and any odd/even/reverse/first-page-different options.

**Proposal:** A **Print Studio** dialog that, before handing off to `wx.Printer`, gives an *accessible* (spoken/textual, not WYSIWYG) preview summary — "N pages, Letter, 1-inch margins" — the screen-reader equivalent of a visual preview. Add odd-only / even-only / reverse-order / different-first-page as options layered on the existing `wx.Printout.OnPrintPage` pagination once page ranges are computed. Verify the native `wx.PageSetupDialogData` margin dialog with an actual screen reader before deciding a custom margin control is warranted.

**Non-goals:** No WYSIWYG renderer. Header/footer *authoring* is #892.

**Priority:** P1 — most-flagged gap; medium confidence because it's real net-new UI + print-pipeline work. Pairs naturally with #892 as a "printing & page layout" epic.

---

## #899 — Mandatory alt text + accessible inline object placeholders — **P1**

**State (corrected per the issue's own re-check):** GLOW (`quill/core/glow.py`) already *audits* missing alt text, *auto-fixes* it, can *generate* it via opt-in cloud AI, and inventories every image's alt status (`link_inventory.py`, `ImageAltRecord`). So an accessible image object model already exists — as an after-the-fact audit pass.

**The two real gaps this issue should now own:**
1. **Insertion-time enforcement** — make alt text a *required field* in the Insert Image flow, so a document can't accrue un-alt-texted images in the first place (proactive, vs. GLOW's reactive repair).
2. **Inline reading experience** — what a screen reader announces as the caret passes an image *in the live document*: "Image: sunset.png, alt text: a sunset over the lake" vs. **"Image: sunset.png, alt text MISSING"** — making absent alt text impossible to *miss*, not just impossible to *see*.

Extend the same idea to non-image embeds as accessible placeholders ("Page break", "Equation", "Embedded object removed for safety"). Equations/OCR content likely reuse MathCAT + OCR infrastructure — investigate before designing. Export must map cleanly onto DOCX/HTML/EPUB alt conventions.

**Priority:** P1 — the strongest *accessibility* item on the list (not mere parity), and now well-scoped since GLOW carries the heavy lifting. Recommend a short spike on the inline-object model (the document is plain-text/Markdown; `![alt](path)` exists but there's no broader placeholder concept yet) before committing to a design.

---

## #892 — Keyboard-first Header/Footer Builder — **P2**

**State:** No header/footer authoring exists beyond `wx.PageSetupDialogData` margins (which has no header/footer concept at all).

**Proposal:** A keyboard-first builder driven by **named presets** (not a blank canvas): "Title left, page number right", "Filename and date", "Different first page", "Roman numerals for front matter", "Start numbering at page N". Each preset composed from a small fixed token set (title, filename, date, page number [Arabic/Roman], custom text) × position (left/center/right) + first-page-different toggle. Store as **document metadata** (part of the document's identity, survives save/reload), not a one-off print-time setting. Confirm round-trip through DOCX/RTF native header/footer XML before committing to the token model.

**Non-goals:** Not a general macro/field-code system — a curated token set beats an open-ended one for this audience.

**Priority:** P2 — high impact, self-contained, but real net-new UI + metadata + export work. Sequence it right after / alongside #891.

---

## #894 — Accessible AutoOutline (heading auto-numbering) — **P2**

**State:** Heading-parsing foundation already exists — `markdown_sections.parse_heading_blocks` / `current_section_at`, already used by the Section status cell and heading navigation. No auto-numbering today (confirmed genuine gap; the power-tools line-numbering feature is unrelated plain line numbers).

**Proposal:** A toggleable AutoOutline mode where heading level drives numbering style (1 / 1.1 / 1.1.1, or I/A/1 legal), renumbering on add/remove/reorder. Insert numbering as **literal text** (survives copy/paste and export, matches "what you see is in the file"), via a reserved prefix pattern the renumber pass can safely find-and-replace — nail this mechanic down before implementation. Verify clean DOCX export with no double-numbering (Word's auto-numbering vs. QUILL's literal text).

**Non-goals:** Not an outline/mind-map view — numbering on existing structure only.

**Priority:** P2 — useful for a common document class (agendas, policies, reports); medium-high confidence since it builds on working parsing infra. Literal numbered text is arguably *more* valuable for screen-reader users (unambiguous read aloud) than a rendering overlay would be.

---

## #896 — Work Personas: launchable profiles tied to sessions, favorites, folders — **P3**

**State:** All the raw material exists — feature profiles, sessions, autosave/recovery, notebooks, Story Studio, Copy Tray. Missing: a single launchable identity that *ties them together*.

**Proposal:** A **Work Persona** = a named bundle referencing a feature profile + default working folder + favorite/recent files + a Copy Tray slot set + (optional) keymap profile. Launching restores that persona's session via existing session/recovery machinery, scoped per-persona. Generate a per-persona launch shortcut (`.lnk` / command-line arg) so a persona is reachable without QUILL already running — the way Jarte's separate shortcuts worked.

**Non-goals:** Not multi-user/access-control — convenience bundles for one person's contexts (school/work/hobby). Not a Story Studio/Notebook replacement — personas *use* those.

**Priority:** P3 — meaningful, genuinely differentiated (QUILL's underlying pieces beat Jarte's), but the **most integration-heavy** item here (profiles + sessions + copy tray + folders simultaneously). Ranked below the self-contained wins precisely because the risk is in the integration. Note the natural dependency: it builds on the Copy Tray / Clip Library work (#895) and the now-tightened Casual Writer profile (#890, shipped) — so the Clip Library is the remaining prerequisite.

---

## #893 — "Rich Document" workflow discoverability — **P3**

**State:** The Rich Text lens already exists and works — `core.rich_text_lens` (`feature_catalog.py:~149`), wired to `view.switch_editing_lens`, locked_off under at least one profile (`settings.py:~595`). This is discoverability/framing, not a build.

**Proposal:** Surface "Rich Document" as a plain-language onboarding choice (first-run wizard and/or profile-adjacent setting) for users who want WordPad-like editing without learning Markdown — framed as an experience, not as "enable the Rich Text lens flag." Add an in-context "Switch to Rich Document view" affordance (menu + command palette) for users mid-session. Audit which profiles lock the lens off and confirm that's still right if it's being promoted.

**Non-goals:** Not changing the underlying Markdown-with-invisible-codes architecture; not making Rich Text the default for everyone.

**Priority:** P3 — **explicitly downgraded per the issue's own re-check.** QUILL's plain-text/Markdown default *is* the screen-reader-optimized design, not a way-station to a "real" rich mode. This mainly serves a secondary audience (low-vision, sighted co-authors, ex-Word/WordPad users). Real and worth doing — the feature already exists so the cost is low — but it's a "nice for a secondary audience," not a core-mission gap like #891 or #899.

---

## Suggested sequencing

1. **Printing epic: #891 then #892** — the single biggest comparison gap, done as one coherent "printing & page layout" push.
2. **#899** — spike the inline-object model, then insertion-time enforcement + inline announcement on top of GLOW.
3. **#894** — self-contained productivity win on existing parsing infra.
4. **#896** — last of the features; wants #895 settled first.
5. **#893** — low-urgency discoverability polish; fold into whatever onboarding-wizard work is already happening rather than scheduling standalone.

*(Accessibility note: #891, #892, #894, #899 all add user-facing surfaces to a screen-reader-first product. Each proposal above bakes in the non-visual equivalent — spoken print summaries, keyboard-first builders, literal in-file numbering, inline "alt text MISSING" announcements — rather than treating accessibility as a later review pass. When these move to implementation, route the new dialogs through `_show_modal_dialog` + `apply_modal_ids` and the existing dialog-inventory gate, same as every other QUILL surface.)*

---

# QuillRichEdit: a native Rich Edit wrapper as a controlled experimental surface

**A proposal to add a WordPad/HJPad-class RTF editing mode by *reaching through* the native Microsoft Rich Edit control QUILL already ships — and, in doing so, turning the two open braille bugs (#616 cell-2 offset, #813 dots 7-8 on selection) from black-box A/B guesswork into things we can directly measure and drive.**

---

## 1. The insight (the part that makes this magical)

QUILL's **default editor is already a native Microsoft Rich Edit control** — `RICHEDIT50W` from `msftedit.dll` — created as a `wx.TextCtrl` with `TE_RICH2 | TE_NOHIDESEL` (`main_frame.py:4322`). It is the same control class WordPad used (`CRichEditCtrl` → RichEdit), and it is the default *specifically for accessibility*: its `IAccessible` value is reported correctly to JAWS and NVDA (#616), which the failed Scintilla experiment proved is the hard part.

So we are not choosing *whether* to use Rich Edit. We already do. What we are missing is **access to it**. QUILL talks to that native control only through wx's high-level `TextCtrl` API, which is a black box over three things we now need:

1. **Real RTF load/save.** wx's `LoadFile`/`SaveFile` document that the `fileType` argument is *ignored* for `wx.TextCtrl` — there is no RTF round-trip through the high-level API. The native control does it through `EM_STREAMIN` / `EM_STREAMOUT` with an `EDITSTREAM` callback, which wx never surfaces.
2. **The Text Object Model (TOM).** The Rich Edit `ITextDocument` / `ITextSelection` interfaces — the layer that drives how selection and ranges are exposed to `IAccessible2` — are unreachable through wx. This is *exactly* the layer #813 (JAWS braille not showing dots 7-8 on selection) is suspected to live in (`docs/planning/editor-surface-experiments.md:72-78`).
3. **Low-level messages.** `EM_EXGETSEL`, `EM_SETEDITSTYLE`, `EM_GETEDITSTYLE`, margin/format messages — the levers to *investigate and mitigate* the cell-2 offset (#616) on a real Rich Edit HWND, instead of the generic-window bridge that already failed for Scintilla.

**The magic:** a thin `QuillRichEdit` wrapper over the *same* native control we already ship converts these from "wx behaviors we can only A/B against each other" into "a native control we can read from and write to directly." That single move unlocks a genuinely new capability (basic RTF editing) **and** gives us the instrument to finally resolve two braille bugs — without adopting `wx.RichTextCtrl`, without a custom rich-text engine, and without touching the plain-text/Markdown default.

> The product promise: *QUILL can open, read, edit, and save basic RTF documents using the native Windows Rich Edit control — accessible lightweight rich text, not full Word fidelity.*

---

## 2. What exists today (the surfaces and the contract we must honor)

This is the ground truth the wrapper has to live inside. QUILL's main frame talks to `self.editor` through a small duck-typed **`EditorSurface` protocol** (`quill/ui/editor_surface.py`), and every surface below satisfies it. New surfaces do **not** refactor anything; they implement the same shape and (optionally) advertise `surface_kind` / `bind_editor_events`.

### 2.1 Editor surfaces wired today

| Surface (`experimental_editor_surface`) | Win32 class / control | Accessibility posture | Notes |
|---|---|---|---|
| `default` | delegates to `editor_control_kind` | — | not a surface; resolves to one below |
| **`rich2` (shipping default)** | `RICHEDIT50W` (msftedit) via `wx.TextCtrl TE_RICH2` | Correct `IAccessible` value (#616); **JAWS cell-2 offset**; **#813 dots 7-8 suspected here** | the baseline every feature is calibrated against |
| `rich` | `RICHEDIT20W` (riched20) via `TE_RICH` | A/B comparison point for #813 | near-identical through wx |
| `plain` | classic Win32 `EDIT` via `TE_MULTILINE` | **Best for braille — cell 1, no offset**; no visual rich formatting | fixes cell-2 but loses rich display |
| `rtf` | **`wx.richtext.RichTextCtrl`** | Non-native; **cannot read/write RTF** (own XML); poor SR support | the control the research says to *avoid* — a dead end for this goal |
| `win32` | raw Win32 `EDIT` via pywin32 | partial; type-time features inert | spike (`win32_edit_surface.py`) |
| `stc` | Scintilla (`wx.stc`) | **NVDA-only; JAWS can't follow caret**; accessibility bridge **failed** (2026-07-03, twice) | `stc_edit_surface.py`; risk analysis in the experiments doc |

Plus three **non-experimental alternate surfaces** that already satisfy the protocol and must keep working untouched: `CsvGridSurface` (CSV grid), `WordDocumentSurface` (`word_view.py`, accessible Word view), and `RichTextSurface` (`rich_text_surface.py`).

Gating: every experimental surface is off unless **both** `experimental_acknowledged` *and* `experimental_editor_surfaces_enabled` are set (the master switch + the "features may degrade based on the control selected" acknowledgement). `QuillRichEdit` rides the exact same two gates.

### 2.2 The contract = the abilities every surface must honor

From `editor-surface-experiments.md` (the "contract QUILL assumes") — the wrapper must satisfy **all** of this or degrade it *visibly* (via capability reporting), never silently:

- **Value:** `GetValue` / `ChangeValue` / `SetValue` / `GetRange` / `IsEmpty` — LF-only text, offsets matching Python string indices into `GetValue()`.
- **Caret & selection:** `GetInsertionPoint` / `SetInsertionPoint`, `GetSelection` → `(start, end)` with `(caret, caret)` when empty, `SetSelection`, `GetStringSelection`, `ShowPosition`, `GetLastPosition`.
- **Editing:** `WriteText`, `AppendText`, `Replace`, `Remove`, `Clear`.
- **State:** `IsModified` / `SetModified` / `MarkDirty` / `DiscardEdits`, `SetEditable` / `IsEditable`, `Undo` / `Redo` / `CanUndo` / `CanRedo`.
- **Geometry:** `PositionToXY` / `XYToPosition` / `GetNumberOfLines`.
- **Events** (`_bind_editor_events`): `EVT_TEXT`, `EVT_CHAR_HOOK`, `EVT_KEY_DOWN`/`EVT_KEY_UP`, `EVT_LEFT_UP` + `EVT_SET_FOCUS`, `EVT_CONTEXT_MENU`.
- **Accessibility:** value, caret, and selection exposed through `IAccessible`/UIA so JAWS/NVDA read and track it and braille follows the caret.

### 2.3 The QUILL abilities that ride this contract (all must be honored)

Grouped by what breaks if the contract slips (from the doc):

- **Offset-anchored:** bookmarks & last-cursor memory, inline notes, **hidden formatting codes / Illuminations / Reveal Codes**, wikilink resolution (Vault), search & replace, spell/grammar fix-ups, **AI change previews** (one `Replace`, one undo step), read-aloud position tracking.
- **Type-time:** typography autoformat (smart quotes/dashes), Quillin smart triggers & abbreviations, describe-key, typing echo, QUILL key chords, dictation hotkeys.
- **Continuous:** status-bar cells (selection, stats), Reveal Codes idle sync, **braille status line**, caret-move formatting announcements.
- **Adjacent subsystems that read `GetValue()`/selection:** GLOW audit/repair, Copy Tray / Clip Library, export (`io/export.py`, `io/rtf.py`, Pandoc), page indicator (#872, form-feed page boundaries), translation/BRF.

The wrapper's job is to keep every one of these working on the RTF surface **or** report, per document, exactly what it can't (capability reporting), and fall back cleanly rather than half-work.

---

## 3. The wrapper: `QuillRichEdit`

A Windows-only adapter that hides the Win32 bits behind a clean, testable, **replaceable** Python API — small, native, and isolated so the backend can be swapped without touching the rest of QUILL.

```python
class QuillRichEdit:
    # --- the EditorSurface contract (delegates to the inner native control) ---
    def GetValue(self) -> str: ...
    def ChangeValue(self, value: str) -> None: ...
    def GetInsertionPoint(self) -> int: ...
    def SetInsertionPoint(self, pos: int) -> None: ...
    def GetSelection(self) -> tuple[int, int]: ...   # (start, end); (caret, caret) when empty
    def SetSelection(self, start: int, end: int) -> None: ...
    def SetFocus(self) -> None: ...
    def surface_kind(self) -> str: return "richedit_rtf"

    # --- RTF I/O via native streaming (the new capability) ---
    def load_rtf(self, path: str) -> "LoadReport": ...   # EM_STREAMIN + EDITSTREAM
    def save_rtf(self, path: str) -> None: ...           # EM_STREAMOUT + EDITSTREAM
    def get_plain_text(self) -> str: ...                 # for search/spell/AI/read-aloud/braille

    # --- formatting commands (CHARFORMAT2 / PARAFORMAT2) ---
    def apply_bold(self) -> None: ...
    def apply_italic(self) -> None: ...
    def apply_underline(self) -> None: ...
    def set_font_name(self, name: str) -> None: ...
    def set_font_size(self, points: int) -> None: ...
    def set_alignment(self, how: str) -> None: ...       # left/center/right/justify
    # bullets, indent, color … added incrementally

    # --- state the app already relies on ---
    def get_selection_info(self) -> "SelectionInfo": ... # for the status bar + braille status line
    def is_modified(self) -> bool: ...
    def capabilities(self) -> "CapabilityReport": ...     # what this RTF file/mode does NOT preserve
```

**Implementation, layered for safety and testability:**

1. **Inner control = the native Rich Edit we already ship.** First implementation hosts `wx.TextCtrl(style=TE_MULTILINE | TE_RICH2 | TE_NOHIDESEL)` and reaches its `HWND` (`editor.GetHandle()`), so the contract methods (value/caret/selection/undo/events) come "for free" through wx and are already battle-tested — we only *add* the native RTF/format/TOM layer on top.
2. **RTF streaming** via `ctypes`: `EM_STREAMIN` / `EM_STREAMOUT` with an `EDITSTREAM` callback that pumps bytes to/from Python. This is the one genuinely new native path; it is small, and it is unit-testable at the seams (the byte-pump and the `SF_RTF` flag plumbing) even though the round-trip itself needs on-device verification.
3. **Formatting** via `EM_SETCHARFORMAT` (`CHARFORMAT2`) and `EM_SETPARAFORMAT` (`PARAFORMAT2`) — the documented, stable Rich Edit messages.
4. **Capability reporting + graceful fallback.** On load, inspect the RTF for objects/tables/images the mode won't fully preserve and report them ("this file contains a table QUILL's RTF mode shows as text"); if hosting or streaming fails for any reason, fall back to a plain `wx.TextCtrl` exactly like `win32`/`rtf`/`stc` already do (`create_*` returns `None` → factory falls back). The editor is **never** left broken.
5. **Pure seams stay in `quill/core` / a wx-free helper** where possible (RTF capability sniffing, plain-text extraction contracts, offset mapping), so `mypy` and unit tests cover the logic and the thin `ctypes` shell is the only untested-here part.

---

## 4. How every surface and ability is honored (the integration map)

**Surfaces:** `QuillRichEdit` is *additive* — a new `richedit_rtf` value for `experimental_editor_surface`, wired into the one factory in `main_frame.py` beside `rtf`/`win32`/`stc`, behind the same two gates. It does **not** alter `default`/`rich2`/`rich`/`plain` or the alternate `CsvGrid`/`Word`/`RichText` surfaces. `surface_kind()` returns `"richedit_rtf"` so command code that branches on plain-vs-rich (`editor_surface.surface_kind`) sees a rich surface and behaves correctly.

**Abilities:** because the inner control is the same native `wx.TextCtrl` the default uses, the offset-anchored, type-time, and continuous features keep their existing wx code paths. Where RTF adds meaning:

- **Reveal Codes / hidden formatting / Illuminations:** QUILL's canonical text stays Markdown; the RTF surface exposes `get_plain_text()` for all offset-anchored features, and formatting is a *view/serialization* concern (RTF on disk ↔ QUILL markup via the existing `io/rtf.py` ↔ `rtf_model.py`), so Reveal Codes still reflects QUILL's codes.
- **Search/replace, spell, AI previews, read-aloud, page indicator, GLOW, Copy Tray, export:** all consume `GetValue()`/selection/`Replace` — unchanged, since the wrapper implements them over the native control.
- **Anything RTF genuinely can't do losslessly** (complex tables, embedded objects) surfaces through `capabilities()` and the load report — honored by *telling the user*, never by silent data loss. A too-complex file offers to open as plain text (the fallback path).

A **parametrized contract test** (the doc's own recommendation: "same assertions, run against each surface with real wx") is extended to include `richedit_rtf`, so the two crashes-from-contract-drift class of bug can't recur.

---

## 5. The braille payoff (#616 cell-2 and #813 dots 7-8)

This is where the wrapper earns its keep beyond RTF. Today these are *known, tracked, and stuck* because we can only A/B wx surfaces against each other:

- **#616 — cell-2 offset:** JAWS renders `RICHEDIT50W` starting in **cell 2** (the long-standing MS Word behavior); NVDA and the plain `EDIT` control render from **cell 1** (measured four-way table, `editor-surface-experiments.md:406-411`). The plain surface fixes it but loses rich display and (per the RichEdit rationale) the strongest `IAccessible` value path.
- **#813 — dots 7-8 on selection:** JAWS braille intermittently not showing the selection dots (7-8) under selected text; **suspected to live in `RICHEDIT50W`**, and the doc predicts the fix is *"a UIA/IAccessible selection-reporting workaround here, not a default-surface change."*

The wrapper is precisely that workaround's *home*, because it gives us the two things wx hides:

1. **The Rich Edit TOM (`ITextDocument`/`ITextSelection`).** Selection exposure to `IAccessible2` (which is what JAWS reads to render dots 7-8) is driven by this layer. With the HWND we can obtain the TOM via `EM_GETOLEINTERFACE` and explicitly set/verify the active selection so the AT sees it — the direct instrument #813 has been missing. We can also *measure* it (log what the TOM reports vs. what the braille shows) to confirm the root cause instead of guessing.
2. **`EM_SETEDITSTYLE` and margin/format control on a real Rich Edit HWND.** Unlike the failed Scintilla bridge (which faked native messages on a *generic* window class and JAWS never trusted), this is a genuine Rich Edit control — JAWS's dedicated Rich Edit path already engages. So cell-2 mitigations (edit-style flags, `EM_SETMARGINS`, or a JAWS class-channel nudge) can be tried and measured *on the control JAWS already treats as Rich Edit*, which is the only place they have a chance of sticking.

Crucially, this reframes the braille work: **stop A/B-ing whole surfaces, and start driving the one native control we already ship.** Even if the first cut only *measures* #616/#813 precisely (TOM selection dump, class-name/edit-style logging in Copy Diagnostic Summary), that alone converts two stuck investigations into tractable ones — and the wrapper is the natural place for the eventual fix to live.

---

## 6. What this is explicitly NOT

- **Not `wx.RichTextCtrl`.** wx's own docs: it can't read/write RTF (uses its own XML), isn't native, and is a poor screen-reader choice. The existing `rtf` surface is a dead end for this goal and should be documented as such (and eventually retired once `richedit_rtf` supersedes it).
- **Not a custom rich-text engine.** The hard parts aren't bold/italic — they're caret behavior, selection ranges, keyboard nav, screen-reader exposure, clipboard interop, undo/redo, IME, paragraph formatting, and real-world RTF. Reusing native Rich Edit gets all of those for free.
- **Not a Word clone.** No promise of perfect tables, headers/footers, comments, tracked changes, embedded objects, pagination, or DOCX fidelity. Basic RTF: fonts, bold/italic/underline, alignment, bullets, color, links, simple documents.
- **Not a change to the default.** The plain-text/Markdown editor stays QUILL's default and its screen-reader-first identity is untouched. This is an *opt-in, gated, Windows-only* mode for testers and, later, for users who want lightweight RTF.

---

## 7. Build order (each phase ships value alone, mirrors the existing experiment pattern)

| Phase | Deliverable | Ships value alone? |
|---|---|---|
| **0** | `QuillRichEdit` wrapper module + `create_richedit_rtf(...)` factory returning `None` off-Windows/on failure (the proven `create_*` fallback idiom); `surface_kind="richedit_rtf"`; wired into the `main_frame` factory + Experimental-tab description; parametrized contract test extended. | **Yes** — a new, safe, gated surface that *is* the native Rich Edit, selectable for testing, with zero risk to defaults. |
| **1** | RTF load/save via `EM_STREAMIN`/`EM_STREAMOUT` + `EDITSTREAM`; capability sniffing + load report; plain-text extraction wired to search/spell/AI/read-aloud. | **Yes** — basic RTF open/edit/save (the WordPad/HJPad capability). |
| **2** | Formatting commands (`CHARFORMAT2`/`PARAFORMAT2`): bold/italic/underline/font/size/alignment, then bullets/indent/color. | **Yes** — the "rich" in rich text. |
| **3** | **Braille instrument:** TOM selection dump + edit-style/class logging in Copy Diagnostic Summary; then the #813 selection-exposure workaround and #616 cell-2 mitigation experiments, measured on the real HWND. | **Yes** — even measurement-only closes the loop on two stuck bugs. |

Phase 0 is a few careful files that mirror `win32_edit_surface.py`/`stc_edit_surface.py` exactly and cannot hurt the shipping build (gated + fallback). Phases 1-3 layer capability on the isolated wrapper.

---

## 8. Invariants & gate checklist (QUILL house rules)

- **Layering & Windows-only:** `QuillRichEdit` lives in `quill/ui` (it wraps a wx control), with wx-free pure helpers (RTF capability sniffing, offset/plain-text contracts) in `quill/core`. All `ctypes`/Win32 behind `sys.platform == "win32"` guards; `create_richedit_rtf` returns `None` elsewhere so the factory falls back — never a hard dependency.
- **Never break the editor:** any hosting/streaming/format failure falls back to a plain `wx.TextCtrl`, exactly like the three existing experimental surfaces.
- **Contract test (GATE-worthy):** extend the parametrized "editor contract" test to `richedit_rtf` (value/caret/selection shape, `(caret,caret)`-when-empty, LF-only) — the guard against the contract-drift crashes that already bit twice.
- **Accessibility (the whole point):** measured on JAWS *and* NVDA with a braille display before any promise; capability reporting is spoken/announced; the surface is keyboard-complete; gating copy states "experimental, may degrade." Route any new dialog/prompt through `_show_modal_dialog` + `apply_modal_ids`.
- **Safe Mode / gating:** honors `experimental_acknowledged` + `experimental_editor_surfaces_enabled`; no network, no AI.
- **Module size budget (GATE-11):** new logic in new modules (`quill/ui/richedit_rtf_surface.py`, a core RTF-capability helper), keeping `main_frame.py` to a one-branch addition in the factory.
- **Docs:** fold the surface into `docs/planning/editor-surface-experiments.md` (it already tracks all seven surfaces and both braille bugs) and the Accessibility settings help text.

---

## 9. Open decisions for review

1. **Surface id:** `richedit_rtf` (proposed) vs. repurposing the existing `rtf` id (which currently means `wx.RichTextCtrl`). Recommendation: **new id `richedit_rtf`**, and mark the old `rtf` (RichTextCtrl) surface deprecated/"dead end" in the help text — keep them distinct during A/B so testers can compare the native wrapper against the control the research warns against.
2. **Host strategy:** wrap `wx.TextCtrl TE_RICH2` and reach its HWND (proposed — inherits the tested contract) vs. host a raw `MSFTEDIT_CLASS` HWND directly (more control, more surface area). Recommendation: **wrap the wx control first**; drop to a raw HWND only if the TOM/selection work needs it.
3. **Canonical model:** RTF-on-disk ↔ QUILL Markdown markup via the existing `io/rtf.py`, keeping Markdown canonical (proposed), vs. letting the RTF surface hold RTF as its own truth. Recommendation: **keep Markdown canonical** so every existing ability (search/AI/GLOW/export/read-aloud) keeps working through `GetValue()`; RTF is an import/export + live-formatting view.
4. **Scope of the braille phase now:** measurement-only instrument first (TOM/edit-style logging in diagnostics), or attempt the #813/#616 fixes in the same pass? Recommendation: **instrument first** — confirm root cause on the real HWND, then fix, so we never ship another unverified bridge.

---
---

# Outstanding from the 2026-07-08 session: unresolved reports + follow-ups needing hardware

Everything else reported/found in this session (voice preview feedback; #915-918; the Mac sound/file-open/keybinding fixes; the OpenAI wizard stuck-state fix; the clipboard retry fix) shipped and is documented in CHANGELOG.md / the PRD / the user guide / release notes. These items did not ship and need attention before they can be closed out.

## 1. Windows crash reported from typing "help." — unresolved, no root cause found

A user reported QUILL crashed on Windows 11 "just by attempting to type the word, 'help.'" while also typing a URL (`www.jessicadail.com`) in the same post. Investigated: no crash-report/diagnostics log on this machine matched the incident; "help" is not a reserved trigger word anywhere in the abbreviation/smart-trigger/command-palette code; QUILL has no live URL auto-linkification feature to misbehave on a domain string; targeted reproduction attempts (feeding the exact text through abbreviations, spellcheck, intellisense, and TTS normalization in isolation) produced no exception.

**Next step:** this needs a real crash-report bundle or traceback from the reporter's own machine (Help > Report a Bug, or their `%APPDATA%\Quill\diagnostics\` folder) to make any further progress — do not guess at a fix without one.

## 2. Missing API-key entry UI for OpenAI Agents SDK / Claude Agent SDK harnesses

Found while fixing the AI Setup Wizard stuck-active bug: `openai_agents` and `claude_agent_sdk` both declare `requires_api_key=True`, but unlike GitHub Copilot (which has `CopilotOnboardingDialog`), the AI Hub's Engines tab has no API-key entry surface for either of them at all — they only read auth from process environment variables, not QUILL's credential store. This is a real, separate gap from the crash-recovery fix (which only stopped a broken install from looking permanently "active"); a *successfully* installed OpenAI/Claude Agent SDK harness still has no in-app way to add a key. Needs its own small onboarding dialog, modeled on `CopilotOnboardingDialog`.

## 3. NSSound macOS backend — needs real hardware to confirm

The new `_NSSoundBackend` (AppKit `NSSound` via `pyobjc`) in `quill/platform/sound_player.py` is unit-tested with fakes only (this dev box is Windows). Two things still need a real Mac: (a) that `NSSound.alloc().initWithData_()` actually produces audible output for QUILL's WAV format, and (b) that the bounded live-sound retention (16 entries) is generous enough under real earcon firing rates without AppKit tearing down a sound mid-playback.

## 4. macOS file-open + document-switch chord — needs real hardware to confirm

`MacOpenFileApp`'s `MacOpenFile`/`MacOpenFiles` override (Finder/Dock/`open -a` file-open handling) is standard wx API usage but the exact Apple Event delivery timing (especially the cold-launch race where a file-open event arrives before `MainFrame` finishes constructing) needs a real Mac to confirm end-to-end. Separately, the new default document-switching chord (`Cmd+Shift+]`/`[`, chosen to match Safari/Xcode's tab-cycling convention) is a UX pick, not mechanically forced — worth confirming with an actual Mac user it doesn't collide with anything on their setup before calling it final.

## 5. Latent risk (not yet reproduced): `_show_intellisense_popup` could still crash on a dead popup

The #917/#918 fix made `_IntellisensePopup.is_visible()` tolerate a deleted C/C++ `Frame` (from `main_frame_intellisense.py`'s `_handle_intellisense_key_down`). But `_show_intellisense_popup` (same mixin) still calls `popup.update(...)` / `popup.show(...)` on the same popup object after checking `is_visible()` — if a *future* keystroke reaches that path with the same dead-frame condition instead of the key-down handler, those calls are unguarded and could raise the same class of `RuntimeError` somewhere new. No crash report evidences this path is actually reached (the two filed crashes were both in `is_visible()` specifically, called from the key-down handler), so this is a documented risk, not a confirmed bug — revisit if a similar crash resurfaces with a different traceback location.

