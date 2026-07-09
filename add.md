# Backlog review: remaining open issues

Proposals and priorities for the rest of the open backlog. **Already shipped and documented in the CHANGELOG / release notes (removed from this future-facing list):** #909 (the free-first import pipeline is now a base dependency), #890 (Casual Writer tightened to a true "just write" profile), the Report-a-Bug "No token" build regression, #897 (Wikipedia lookup), #895 (Clip Library), #900 (Send/Copy as Email), #894 (Accessible AutoOutline), and #896 (Work Personas). Closed items (#898 Second View, #901 tablet/low-vision, #905/#906/#907 Convert-Non-ASCII bugs) are excluded.

## Priority ladder (my recommendation)

| Rank | Issue | Title (short) | Impact | Confidence | Why here |
|------|-------|---------------|--------|-----------|----------|
| **P1** | #891 | Print Studio (preview, margins, odd/even/reverse) | High | Medium | "The biggest concrete gap" in the Jarte comparison; a blind user still prints for sighted colleagues. |
| **P1** | #899 | Mandatory alt text + inline object placeholders | High | Medium | The one genuine *accessibility* win here (not just parity). Now well-scoped — GLOW already does audit/repair; only insertion-time enforcement + inline announcement remain. |
| **P2** | #892 | Keyboard-first Header/Footer Builder | High | Medium | Named Jarte-Plus gap; self-contained, but real net-new metadata + export work. Natural sibling to #891. |
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

## 1. NSSound macOS backend — needs real hardware to confirm

The new `_NSSoundBackend` (AppKit `NSSound` via `pyobjc`) in `quill/platform/sound_player.py` is unit-tested with fakes only (this dev box is Windows). Two things still need a real Mac: (a) that `NSSound.alloc().initWithData_()` actually produces audible output for QUILL's WAV format, and (b) that the bounded live-sound retention (16 entries) is generous enough under real earcon firing rates without AppKit tearing down a sound mid-playback.

## 2. macOS file-open + document-switch chord — needs real hardware to confirm

`MacOpenFileApp`'s `MacOpenFile`/`MacOpenFiles` override (Finder/Dock/`open -a` file-open handling) is standard wx API usage but the exact Apple Event delivery timing (especially the cold-launch race where a file-open event arrives before `MainFrame` finishes constructing) needs a real Mac to confirm end-to-end. Separately, the new default document-switching chord (`Cmd+Shift+]`/`[`, chosen to match Safari/Xcode's tab-cycling convention) is a UX pick, not mechanically forced — worth confirming with an actual Mac user it doesn't collide with anything on their setup before calling it final.

## 3. Latent risk (not yet reproduced): `_show_intellisense_popup` could still crash on a dead popup

The #917/#918 fix made `_IntellisensePopup.is_visible()` tolerate a deleted C/C++ `Frame` (from `main_frame_intellisense.py`'s `_handle_intellisense_key_down`). But `_show_intellisense_popup` (same mixin) still calls `popup.update(...)` / `popup.show(...)` on the same popup object after checking `is_visible()` — if a *future* keystroke reaches that path with the same dead-frame condition instead of the key-down handler, those calls are unguarded and could raise the same class of `RuntimeError` somewhere new. No crash report evidences this path is actually reached (the two filed crashes were both in `is_visible()` specifically, called from the key-down handler), so this is a documented risk, not a confirmed bug — revisit if a similar crash resurfaces with a different traceback location.
