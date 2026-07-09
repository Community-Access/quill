# Backlog review: remaining open issues

Proposals and priorities for the rest of the open backlog. **Already shipped and documented in the CHANGELOG / release notes (removed from this future-facing list):** #909 (the free-first import pipeline is now a base dependency), #890 (Casual Writer tightened to a true "just write" profile), the Report-a-Bug "No token" build regression, #897 (Wikipedia lookup), #895 (Clip Library), #900 (Send/Copy as Email), #894 (Accessible AutoOutline), #896 (Work Personas), #899 (Mandatory alt text + inline image descriptions), and #891 (Print Studio). Closed items (#898 Second View, #901 tablet/low-vision, #905/#906/#907 Convert-Non-ASCII bugs) are excluded.

## Priority ladder (my recommendation)

| Rank | Issue | Title (short) | Impact | Confidence | Why here |
|------|-------|---------------|--------|-----------|----------|
| **P2** | #892 | Keyboard-first Header/Footer Builder | High | Medium | Named Jarte-Plus gap; self-contained, but real net-new metadata + export work. Natural sibling to #891 (shipped). |
| **P3** | #893 | "Rich Document" discoverability | Medium | High (feature exists) | Downgraded per the issue's own re-check: serves a *secondary* audience (low-vision / ex-Word), not QUILL's core keyboard-first user. Low cost, low urgency. |

Rationale for the shape: the two items that are genuinely *mission* work (printing you can't do today, accessibility you can't enforce today) lead, then a band of solid, well-scoped features, with the integration-heavy and secondary-audience items last.

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

1. **#892** -- the remaining half of the "printing & page layout" epic now that #891 (Print Studio) has shipped.
2. **#893** -- low-urgency discoverability polish; fold into whatever onboarding-wizard work is already happening rather than scheduling standalone.

*(Accessibility note: #892 adds a user-facing surface to a screen-reader-first product. Bake in the non-visual equivalent -- a keyboard-first builder, not a blank canvas -- rather than treating accessibility as a later review pass. Route the new dialog through `_show_modal_dialog` + `apply_modal_ids` and the existing dialog-inventory gate, same as every other QUILL surface.)*

---

# Outstanding from the 2026-07-08 session: unresolved reports + follow-ups needing hardware

Everything else reported/found in this session (voice preview feedback; #915-918; the Mac sound/file-open/keybinding fixes; the OpenAI wizard stuck-state fix; the clipboard retry fix) shipped and is documented in CHANGELOG.md / the PRD / the user guide / release notes. These items did not ship and need attention before they can be closed out.

## 1. NSSound macOS backend — needs real hardware to confirm

The new `_NSSoundBackend` (AppKit `NSSound` via `pyobjc`) in `quill/platform/sound_player.py` is unit-tested with fakes only (this dev box is Windows). Two things still need a real Mac: (a) that `NSSound.alloc().initWithData_()` actually produces audible output for QUILL's WAV format, and (b) that the bounded live-sound retention (16 entries) is generous enough under real earcon firing rates without AppKit tearing down a sound mid-playback.

## 2. macOS file-open + document-switch chord — needs real hardware to confirm

`MacOpenFileApp`'s `MacOpenFile`/`MacOpenFiles` override (Finder/Dock/`open -a` file-open handling) is standard wx API usage but the exact Apple Event delivery timing (especially the cold-launch race where a file-open event arrives before `MainFrame` finishes constructing) needs a real Mac to confirm end-to-end. Separately, the new default document-switching chord (`Cmd+Shift+]`/`[`, chosen to match Safari/Xcode's tab-cycling convention) is a UX pick, not mechanically forced — worth confirming with an actual Mac user it doesn't collide with anything on their setup before calling it final.

## 3. Latent risk (not yet reproduced): `_show_intellisense_popup` could still crash on a dead popup

The #917/#918 fix made `_IntellisensePopup.is_visible()` tolerate a deleted C/C++ `Frame` (from `main_frame_intellisense.py`'s `_handle_intellisense_key_down`). But `_show_intellisense_popup` (same mixin) still calls `popup.update(...)` / `popup.show(...)` on the same popup object after checking `is_visible()` — if a *future* keystroke reaches that path with the same dead-frame condition instead of the key-down handler, those calls are unguarded and could raise the same class of `RuntimeError` somewhere new. No crash report evidences this path is actually reached (the two filed crashes were both in `is_visible()` specifically, called from the key-down handler), so this is a documented risk, not a confirmed bug — revisit if a similar crash resurfaces with a different traceback location.
