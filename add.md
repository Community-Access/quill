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

1. **Printing epic: #891 then #892** -- the single biggest comparison gap, done as one coherent "printing & page layout" push.
2. **#899** -- spike the inline-object model, then insertion-time enforcement + inline announcement on top of GLOW.
3. **#893** -- low-urgency discoverability polish; fold into whatever onboarding-wizard work is already happening rather than scheduling standalone.

*(Accessibility note: #891, #892, #899 all add user-facing surfaces to a screen-reader-first product. Each proposal above bakes in the non-visual equivalent -- spoken print summaries, keyboard-first builders, inline "alt text MISSING" announcements -- rather than treating accessibility as a later review pass. When these move to implementation, route the new dialogs through `_show_modal_dialog` + `apply_modal_ids` and the existing dialog-inventory gate, same as every other QUILL surface.)*

---

# Outstanding from the 2026-07-08 session: unresolved reports + follow-ups needing hardware

Everything else reported/found in this session (voice preview feedback; #915-918; the Mac sound/file-open/keybinding fixes; the OpenAI wizard stuck-state fix; the clipboard retry fix) shipped and is documented in CHANGELOG.md / the PRD / the user guide / release notes. These items did not ship and need attention before they can be closed out.

## 1. NSSound macOS backend — needs real hardware to confirm

The new `_NSSoundBackend` (AppKit `NSSound` via `pyobjc`) in `quill/platform/sound_player.py` is unit-tested with fakes only (this dev box is Windows). Two things still need a real Mac: (a) that `NSSound.alloc().initWithData_()` actually produces audible output for QUILL's WAV format, and (b) that the bounded live-sound retention (16 entries) is generous enough under real earcon firing rates without AppKit tearing down a sound mid-playback.

## 2. macOS file-open + document-switch chord — needs real hardware to confirm

`MacOpenFileApp`'s `MacOpenFile`/`MacOpenFiles` override (Finder/Dock/`open -a` file-open handling) is standard wx API usage but the exact Apple Event delivery timing (especially the cold-launch race where a file-open event arrives before `MainFrame` finishes constructing) needs a real Mac to confirm end-to-end. Separately, the new default document-switching chord (`Cmd+Shift+]`/`[`, chosen to match Safari/Xcode's tab-cycling convention) is a UX pick, not mechanically forced — worth confirming with an actual Mac user it doesn't collide with anything on their setup before calling it final.

## 3. Latent risk (not yet reproduced): `_show_intellisense_popup` could still crash on a dead popup

The #917/#918 fix made `_IntellisensePopup.is_visible()` tolerate a deleted C/C++ `Frame` (from `main_frame_intellisense.py`'s `_handle_intellisense_key_down`). But `_show_intellisense_popup` (same mixin) still calls `popup.update(...)` / `popup.show(...)` on the same popup object after checking `is_visible()` — if a *future* keystroke reaches that path with the same dead-frame condition instead of the key-down handler, those calls are unguarded and could raise the same class of `RuntimeError` somewhere new. No crash report evidences this path is actually reached (the two filed crashes were both in `is_visible()` specifically, called from the key-down handler), so this is a documented risk, not a confirmed bug — revisit if a similar crash resurfaces with a different traceback location.
