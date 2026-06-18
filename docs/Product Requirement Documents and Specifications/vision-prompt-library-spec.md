# Vision Prompt Library — PM/Dev Spec

**Issue:** #195
**Status:** Draft — awaiting review
**Date:** 2026-06-14
**Feature area:** Tools > Describe Image with AI

---

## Section 1: Executive Summary

Quill's "Describe Image with AI" feature today uses a single hardcoded prompt optimized for blind readers. The Image Description Toolkit (IDT) has evaluated 12 distinct prompt styles whose outputs vary substantially by use case — a screen-reader description, alt-text drafts, technical evaluations, and mood descriptions each benefit from a different instruction. This spec adds a prompt library to Quill so users can choose a style that fits their purpose, while keeping the default behavior unchanged for users who don't want to be bothered with the choice.

---

## Section 2: User Problem & Opportunity

### 2.1 Current state (verified)

| Surface | Today | Pain | Who feels it |
|---|---|---|---|
| Describe Image with AI | Single hardcoded prompt, always runs "accessibility" style | No way to get a concise one-liner, alt-text variants, or a technical evaluation | Power users with diverse needs |
| Describe Image dialog | No "try again" option — if the description is wrong style, user must restart the whole flow | Extra clicks, re-picking image source, waiting again | Anyone who wants to compare styles |
| Settings > AI | No vision-specific options | Can't set a preferred style once and forget it | Casual users who want to pick once |

Verified: `quill/core/ai/vision.py:37` — `DEFAULT_IMAGE_DESCRIPTION_PROMPT` is hardcoded. `quill/ui/main_frame_image.py:392` — `describe_image()` is called with no `prompt=` argument. `describe_image()` already accepts `prompt=` (`vision.py:160`).

### 2.2 Target personas

**Casual user (most common):** Wants the existing behavior, doesn't care about style. Needs the feature to stay out of their way — no new dialogs unless they opt in.

**Screen-reader user writing documents:** Usually wants "accessibility" or "narrative" output. Setting a default once is enough; occasional "try again" is a bonus.

**Content creator / web publisher:** Needs alt-text variants at 25 / 50 / 100 words. The "aialttext" IDT style exists for this — they just need access to it.

**Technical user or photographer:** Wants composition analysis, orientation notes, lighting. "Technical" and "detailed" IDT styles serve this.

**Researcher or teacher:** Wants a concise one-sentence summary. "Simple" or "concise" IDT styles.

### 2.3 Why now

The plumbing is entirely in place. `describe_image(prompt=...)` already works. The 12 IDT prompts are evaluated and production-quality. The IDT and Quill share the same author, making the transfer straightforward.

---

## Section 3: Design Principles

1. **Zero disruption by default.** Users who never change a setting see identical behavior. The default style maps to the same "accessibility" intent as today's hardcoded prompt.
2. **One click to try a different style, never more.** Power users reach the picker from the review dialog — no need to restart the flow.
3. **Opt-in picker, not forced picker.** Showing a style-picker before every description is off by default. Users who want it can turn it on.
4. **Prompt management is discoverable but not prominent.** Accessible from Settings > AI, not buried three menus deep — but not on the main toolbar either.
5. **Built-in prompts are immutable; custom prompts are additive.** Users can disable built-ins and add their own, but the shipped prompts are not editable in place (prevents accidental data loss).
6. **Progressive involvement.** The feature has three layers of engagement and never forces the user deeper than they want to go: (a) casual users see only the result, with no new choices; (b) users who open the style picker see names only — no prompt text, no clutter; (c) users who open Manage Image Prompts can read the full text of any style in a preview pane, and at that level can also create custom prompts. The prompt text is never visible unless the user explicitly seeks it out.

---

## Section 4: Feature Scope & Acceptance Criteria

### 4.1 In scope (v1)

| Feature | Setting / location | Default | Notes |
|---|---|---|---|
| 12 IDT built-in prompt styles | `quill/core/ai/vision_prompts.py` (constants) | n/a | Exact text from IDT `docs/archive/prompts.md` |
| Default prompt style setting | `QuillSettings.vision_default_prompt_style` | `"accessibility"` | Applied silently when picker is off |
| Opt-in pre-describe picker | `QuillSettings.vision_prompt_picker_enabled` | `False` | When True, picker appears before each describe |
| "Try a different prompt" in review dialog | New button in `OcrReviewDialog` | Always visible in review dialog | Shows picker, re-runs describe, updates text in dialog |
| Disabled built-ins list | `QuillSettings.vision_disabled_builtin_styles` | `[]` | List of style IDs to hide from picker |
| User custom prompts | `QuillSettings.vision_custom_prompts` | `[]` | List of `{id, title, prompt}` dicts |
| Manage Image Prompts dialog | Settings > AI panel — "Image Prompt Styles..." button | — | Enable/disable built-ins, add/edit/delete custom prompts |

### 4.2 Explicitly out of scope (v1)

- **"Run all styles"** at once — useful but adds significant complexity (multiple background threads, result tabbing). Deferred to v2.
- **Per-document or per-image remembered style** — style is global, not per-file.
- **Editing built-in prompt text** — users can disable built-ins and create custom replacements, but not edit in-place.
- **Reordering built-in prompts** — the 12 IDT styles appear in their canonical order.
- **Any Quillin / extension API changes** — Approach C from the issue is a future concern.
- **Safe Mode behavior change** — `QUILL_SAFE_MODE=1` already disables all AI including vision; no new gating needed.

---

## Section 5: Architecture & Technical Decisions

### 5.1 Prompt data: where to store

**Decision:** Built-in prompts ship as module-level constants in a new `quill/core/ai/vision_prompts.py`. User preferences (disabled built-ins, custom prompts, default style, picker toggle) live in `QuillSettings` in `quill/core/settings.py`.

**Alternatives:**
1. JSON file bundled with the package — adds a file to parse at runtime, no benefit over constants.
2. Stored entirely in settings JSON — makes the settings file large; built-in prompt text shouldn't be in the user's settings file.

**Rationale:** Constants are testable without I/O. Settings fields follow the existing pattern for all other user preferences.

### 5.2 Settings additions to `QuillSettings`

Four new fields on the `QuillSettings` dataclass (all backward-compatible; existing settings files simply won't have the keys and will fall back to defaults):

```python
vision_default_prompt_style: str = "accessibility"
vision_prompt_picker_enabled: bool = False
vision_disabled_builtin_styles: list[str] = field(default_factory=list)
vision_custom_prompts: list[dict] = field(default_factory=list)
```

`vision_default_prompt_style` is validated against the union of built-in IDs and user custom IDs; falls back to `"accessibility"` if the referenced style no longer exists.

### 5.3 "Describe Again" in OcrReviewDialog — button placement

**Decision:** Add a regular `wx.Button` labeled "Try a different prompt..." in a separate horizontal sizer row inserted between the text area and the `StdDialogButtonSizer`. Return a new constant `ID_RETRY = 5103` (wx.ID_HELP, which is an unused-in-this-dialog standard id) from `_end()` when this button is clicked.

**Rationale:** `wx.StdDialogButtonSizer` only places buttons with specific wx standard IDs (OK/Cancel/Apply/Yes/No/Help). Using `wx.ID_HELP` (5103) for the retry action is a minor convention abuse but avoids fighting the sizer layout. The alternative — a fully custom horizontal button sizer — would break the native button ordering on Windows and require auditing focus/tab order. This is noted as a known oddity.

**Alternative considered:** Separate "Describe again" as a toolbar/menu action outside the dialog. Rejected because the user is already in the review dialog looking at the result — the friction of dismissing it and re-invoking the flow is exactly the pain we're solving.

### 5.4 Re-describe loop in `describe_image_with_ai`

When `OcrReviewDialog` returns `ID_RETRY`, `describe_image_with_ai()` in `main_frame_image.py`:
1. Shows the style picker (`wx.SingleChoiceDialog` listing enabled prompts).
2. If cancelled, re-shows the *same* review dialog with the *same* text (no re-describe).
3. If a style is chosen, runs `describe_image(..., prompt=chosen_prompt)` in a background thread (same progress dialog pattern).
4. Re-shows `OcrReviewDialog` with the new description.
5. Loop continues until user hits Insert, Copy, or Discard.

This is a simple while loop in `describe_image_with_ai()`. No new threading primitives needed.

### 5.5 Manage Image Prompts dialog

A new `quill/ui/vision_prompt_manager_dialog.py` provides a `VisionPromptManagerDialog`. It is opened from Settings > AI panel (an existing settings dialog that already manages other AI fields). The dialog has:
- A `wx.ListBox` listing all built-in and custom prompts (disabled built-ins shown with a `[hidden]` marker).
- A **read-only preview pane** (`wx.TextCtrl`, `TE_MULTILINE | TE_READONLY`) below the list that shows the full prompt text for whichever style is currently selected. This is the only place in the UI where prompt text is visible — not in the picker, not in the review dialog. Users who pick by name and never open this dialog never see raw prompt text. The preview pane updates automatically as the user arrows through the list.
- **Enable / Disable** toggle button for built-in prompts.
- **Add / Edit / Delete** buttons for custom prompts; a text entry sub-dialog for the title and prompt text.
- "Close" closes and writes settings. No "Cancel" — changes are visible immediately in the list and saved on Close (following the pattern of other Quill settings panels that write on exit rather than transactionally).

The dialog does **not** need to be in the main modal chain — it's opened via `_show_modal_dialog` like all other modal dialogs per the invariant.

### 5.6 Runtime / Safe Mode

No change needed. `load_ai_enabled()` already gates the entry point; `QUILL_SAFE_MODE=1` already returns early before image selection.

---

## Section 6: Keyboard Walkthrough

### Path A: Casual user (picker off, uses default style)

1. User presses the Describe Image with AI shortcut or navigates Tools menu. **Expected:** Image source picker appears (unchanged today).
2. User picks a file. **Expected:** Progress dialog: "Asking the model to describe the image…" Screen reader announces the dialog title.
3. AI returns. Progress closes. Review dialog opens. **Expected:** Screen reader announces "Describe Image. Review the recognized text below, then choose Insert, Copy, or Discard." Focus is on the text area. Text contains the description.
4. User presses Tab to reach "Try a different prompt…" button. **Expected:** Screen reader announces "Try a different prompt…, button."
5. User presses Tab past it to "Insert" (default). User presses Space or Enter. **Expected:** Text inserted at cursor. Dialog closes. Status bar: "Image description inserted."

### Path B: User with picker enabled

1. User triggers Describe Image with AI. **Expected:** Image source picker appears (unchanged).
2. User picks image. **Expected:** Style picker dialog opens: "Choose a description style — [list of enabled prompt titles]." Focus is on the list. Screen reader announces dialog title and first item.
3. User arrows through list. **Expected:** Screen reader announces each style name.
4. User presses Enter on "Concise." **Expected:** Picker closes. Progress dialog opens: "Asking the model to describe the image…"
5. Continues as Path A from step 3.

### Path C: User tries a different prompt in the review dialog

1. User is in the review dialog, unhappy with the result. User presses Tab to "Try a different prompt…" and activates it. **Expected:** Dialog stays open (or closes and re-opens — see open question §7.1). Style picker appears: "Choose a different style — [list]." Current style is shown selected in the list.
2. User picks "Artistic." **Expected:** Picker closes. Progress dialog opens. New description retrieved.
3. Review dialog re-opens (or updates) with the new text. **Expected:** Focus is on the text area. Screen reader announces the dialog title.
4. User chooses Insert. **Expected:** New description inserted. Status: "Image description inserted."

### Path D: Manage prompts from Settings > AI

1. User opens Settings > AI (existing path, no change).
2. User Tabs to "Image Prompt Styles…" button and activates it. **Expected:** Manage Image Prompts dialog opens. Focus is on the list. Screen reader announces dialog title.
3. User arrows through the list. **Expected:** Each built-in or custom prompt name announced. Disabled built-ins are indicated (e.g., "[hidden] Mood").
4. User selects "Mood" and activates "Disable." **Expected:** Item label changes to "[hidden] Mood."
5. User activates "Add." **Expected:** Sub-dialog opens with a text entry for Title and a multi-line text entry for Prompt text. User fills in and presses OK. New style appears at the bottom of the list.
6. User activates "Close." **Expected:** Dialog closes. Settings saved. Focus returns to Settings > AI panel.

### Path E: Error case — AI call fails on retry

1. User activates "Try a different prompt…" and picks a style. Network fails. **Expected:** Progress dialog closes. Error message box: [error text]. Dialog returns to the previous review dialog text (the describe-again attempt failed, user can still insert the first result). *(See open question §7.2.)*

---

## Section 7: Accessibility Checklist

- **AutomationProperties / accessible names:** Style picker is `wx.SingleChoiceDialog` (built-in accessible). "Try a different prompt…" button label is its accessible name — no extra annotation needed. Manage dialog list items are the style title strings.
- **Announcements:** No new `_announce()` calls needed beyond what `show_modal_dialog` already provides for dialog open/close. The retry result (new description) is announced via focus landing on the text area in the review dialog (screen readers auto-read focused multiline text controls).
- **Focus restoration:** Style picker closes → focus returns to review dialog text area (this is the natural behavior when a child dialog closes; must be verified in manual test). Manage dialog closes → focus returns to Settings > AI panel.
- **Escape key:** Style picker: Escape cancels (built-in `wx.SingleChoiceDialog` behavior). Review dialog "Try different prompt" picker cancellation: re-shows the existing review dialog (same text, no re-run). Manage dialog: Escape should be equivalent to Close (no changes discarded — there is no Cancel in this dialog; Escape should call Close handler).
- **Tab order in review dialog:** existing order is TextCtrl → Insert → Copy → Discard. New order: TextCtrl → "Try a different prompt…" → Insert → Copy → Discard. "Try a different prompt" is above the standard buttons to make it easy to find without being the default action.
- **No color-only information.** Disabled built-ins in the Manage dialog are indicated with text ("[hidden]"), not color alone.

---

## Section 8: Open Questions

These must be resolved before or during implementation:

### 8.1 Does "Try a different prompt" keep the review dialog open while the AI runs?

The current flow for the progress dialog is modal and blocks the UI. If the review dialog stays open during re-describe, the progress dialog would be a child of the review dialog, which is itself a child of MainFrame. This works technically but is slightly unusual.

**Proposed resolution:** Close the review dialog when "Try a different prompt" is activated. Show the progress dialog parented to MainFrame. Re-open a new review dialog with the new text. This is cleaner and avoids stacked modals. The "retry" loop happens in `describe_image_with_ai()`, not inside the dialog.

### 8.2 What happens if the retry AI call fails?

If the first description succeeded but the retry fails, the user has lost the original text (the review dialog was closed per 8.1).

**Proposed resolution:** Keep the original description in a local variable in `describe_image_with_ai()`. If the retry errors, show the error and re-open the review dialog with the *original* text. This way the user can still insert the first result.

### 8.3 Should the style picker remember the last-picked style across retries within the same session?

**Proposed resolution:** Yes. Within one invocation of `describe_image_with_ai()`, the picker should default-select whatever style was last used in that session (including the default style if this is the first retry). This is a simple local variable.

---

## Section 9: Success Metrics

- A user who never changes Settings can trigger Describe Image with AI and get the same result as today. Zero regressions.
- A user can go to Settings > AI, disable two built-in styles, add a custom prompt, and confirm those changes appear in the style picker.
- The style picker shows only enabled styles in alphabetical order (built-ins in canonical IDT order first, custom prompts appended).
- The "Try a different prompt" button is reachable by keyboard from the review dialog in one Tab press from the text area.
- All paths in §6 can be completed keyboard-only without a mouse.

---

## Section 10: Implementation Phases

### Phase 1: Prompt constants and settings fields

**Goal:** The 12 IDT prompt texts exist in the codebase. Settings can store and round-trip the four new fields. Zero user-visible change.

**Deliverables:**
- Create `quill/core/ai/vision_prompts.py` — 12 constants (`PROMPT_NARRATIVE`, `PROMPT_ACCESSIBILITY`, etc.) and a `BUILTIN_PROMPT_STYLES: list[dict]` with `{id, title, prompt}` for each. The "accessibility" entry uses the IDT `accessibility` prompt text (replaces the current `DEFAULT_IMAGE_DESCRIPTION_PROMPT`; they are semantically equivalent and the IDT text is slightly richer).
- Modify `quill/core/settings.py` — add four fields to `QuillSettings`; add validation for `vision_default_prompt_style`.

**Tests:**
- `tests/unit/core/test_vision_prompts.py` — all 12 styles present, IDs are unique, default "accessibility" prompt is in the list.
- `tests/unit/core/test_settings.py` — round-trip for all four new fields; unknown `vision_default_prompt_style` falls back to "accessibility".

**Risk:** Settings round-trip must not break existing settings files that lack the new keys. Mitigation: `data.get("key", default)` pattern already used throughout `settings.py`.

### Phase 2: Default style applied silently

**Goal:** `describe_image_with_ai()` uses `vision_default_prompt_style` instead of the hardcoded constant. Picker still never appears (picker off by default).

**Deliverables:**
- Modify `quill/ui/main_frame_image.py:describe_image_with_ai()` — resolve active prompt from settings before calling `describe_image()`. A `_resolve_active_prompt(settings) -> str` helper returns the prompt text for the configured default style (or `DEFAULT_IMAGE_DESCRIPTION_PROMPT` as ultimate fallback).

**Tests:**
- `tests/unit/ui/` — can't unit-test wx easily; this is manual-test territory.
- Existing unit tests for `vision.py` are unaffected (they test the core, not the UI).

**Risk:** If `_resolve_active_prompt` is wrong, all descriptions use the wrong prompt. Mitigation: the helper is a pure function; unit-test it directly.

### Phase 3: Pre-describe picker (opt-in) + "Try a different prompt" in review dialog

**Goal:** `vision_prompt_picker_enabled = True` shows a style picker before describing. The review dialog has a "Try a different prompt…" button that loops.

**Deliverables:**
- Modify `quill/ui/main_frame_image.py:describe_image_with_ai()` — add the picker branch and the retry loop (while loop around the review dialog check for `ID_RETRY`).
- Modify `quill/ui/ocr_review_dialog.py` — add `ID_RETRY = 5103`, add "Try a different prompt…" `wx.Button` in a row above the `StdDialogButtonSizer`.
- Utility: `_show_style_picker(parent, styles, *, current_id=None) -> str | None` — wraps `wx.SingleChoiceDialog`, returns chosen style ID or None if cancelled.

**Tests:**
- Manual test: keyboard walkthrough paths B and C from §6.
- Unit test for `_show_style_picker` is not feasible (wx dialog); document as manual-only.

**Risk:** The retry loop in `describe_image_with_ai()` could grow complex. Mitigation: extract the "describe + show review" logic into a private `_run_describe_and_review(image_path, prompt, ...) -> int` helper that returns the dialog choice. The while loop then becomes 5 lines.

### Phase 4: Manage Image Prompts dialog + Settings > AI integration

**Goal:** Users can enable/disable built-in styles and add/edit/delete custom prompts from Settings > AI.

**Deliverables:**
- Create `quill/ui/vision_prompt_manager_dialog.py` — `VisionPromptManagerDialog`.
- Modify the Settings > AI panel (wherever it lives in `main_frame.py` or a settings dialog module) — add "Image Prompt Styles…" button that opens `VisionPromptManagerDialog`.
- Add `vision_prompt_picker_enabled` checkbox to Settings > AI panel (alongside the new button).
- `vision_default_prompt_style` dropdown in Settings > AI — populated from enabled styles.

**Tests:**
- Manual: keyboard walkthrough path D from §6.
- Unit test for save/load of `vision_custom_prompts` in `test_settings.py` (list of dicts round-trip).

**Risk:** Locating the Settings > AI panel code in `main_frame.py` (19k lines) — grep for the existing `assistant_prompt_style` setting binding to find the exact location. Add new controls adjacent to existing AI settings.

---

## Section 11: Files to Create / Modify

### Create

| File | Purpose | Lines (est.) |
|---|---|---|
| `quill/core/ai/vision_prompts.py` | 12 IDT prompt constants + `BUILTIN_PROMPT_STYLES` list | 80–100 |
| `quill/ui/vision_prompt_manager_dialog.py` | Manage built-in enable/disable + custom prompts | 150–200 |
| `tests/unit/core/test_vision_prompts.py` | Prompt constants unit tests | 30–40 |

### Modify

| File | Changes | Lines changed (est.) |
|---|---|---|
| `quill/core/settings.py` | Four new fields + validation | +30 |
| `quill/core/ai/vision.py` | `DEFAULT_IMAGE_DESCRIPTION_PROMPT` can stay as fallback; no breaking change | +0 |
| `quill/ui/main_frame_image.py` | Picker branch, retry loop, `_resolve_active_prompt`, `_show_style_picker` helpers | +60–80 |
| `quill/ui/ocr_review_dialog.py` | `ID_RETRY` constant, "Try a different prompt…" button and sizer row | +20 |
| `quill/ui/[settings dialog]` | "Image Prompt Styles…" button, picker toggle checkbox, default style dropdown | +30–50 |
| `tests/unit/core/test_settings.py` | New field round-trip tests | +25 |

---

## Section 12: Risks & Known Issues

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `wx.StdDialogButtonSizer` layout breaks with 4th standard button `ID_HELP` | Low | Minor (cosmetic) | Keep "Try a different prompt" in a separate sizer row above the `StdDialogButtonSizer`; test visually |
| Retry loop loses original description on AI failure | Medium | Major (user work lost) | Resolve in §8.2 — cache original text, re-show review dialog on retry failure |
| Settings round-trip silently drops unknown `vision_custom_prompts` entries (e.g., after schema change) | Low | Minor | Unit-test round-trip with unexpected dict keys inside custom prompt entries |
| `main_frame_image.py` grows beyond GATE-11 budget | Medium | Blocker if gate is tight | Extract helpers into `_pick_and_describe.py` or similar if needed; check budget before implementation |

---

## Section 13: Implementation Guidance for AI (Session 2)

### Adjustments expected

- The spec doesn't specify the exact location of the Settings > AI panel code in `main_frame.py`. Find it by searching for `assistant_prompt_style` binding — the new controls go adjacent.
- The spec says `ID_RETRY = 5103` maps to `wx.ID_HELP`. Verify this is correct for the installed wx version before using it. If `wx.ID_HELP` is already used elsewhere in the dialog infrastructure, use a different approach (e.g., don't add it to `StdDialogButtonSizer` at all — just use a plain `wx.Button` with a custom ID > 10000 and a separate sizer).
- Phase order is firm (1 → 2 → 3 → 4). Do not skip ahead — Phase 1 must pass its unit tests before Phase 2 touches the UI.

### When to ask for clarification

- If the `module_size_budget.json` gate for `main_frame_image.py` is already at or near its ceiling, stop and report before adding Phase 3 code.
- The keyboard walkthrough for Path C (§6) specifies that the review dialog closes before the retry. If implementing this causes a focus-restoration problem (focus doesn't return to the retry-result dialog), ping the user before applying a workaround.

### After implementation: what will be manually tested

1. Default user path: trigger Describe Image with AI, confirm output is same quality as today. Confirm settings file did not gain unexpected entries.
2. Set `vision_prompt_picker_enabled = True` in Settings; trigger describe; confirm picker appears and "Concise" produces a shorter result.
3. From review dialog, activate "Try a different prompt…", pick "Artistic", confirm new description appears in a fresh review dialog.
4. Open Manage Image Prompts, disable "Mood", confirm it no longer appears in picker.
5. Add a custom prompt "One sentence:", confirm it appears in picker and is used.
6. Tab-only navigation for all five paths in §6. No mouse.

---

## Section 14: Prompt Reference (IDT Prompts v1)

Source: [IDT docs/archive/prompts.md](https://github.com/Community-Access/image-description-toolkit/blob/main/docs/archive/prompts.md)

| ID | Title | First line / purpose |
|---|---|---|
| `narrative` | Narrative | Scene overview, left-to-right, spatial relationships |
| `detailed` | Detailed | Structured: SUBJECT / SETTING / COLORS / COMPOSITION / DETAILS |
| `concise` | Concise | 2–3 sentence summary: what, where, happening |
| `artistic` | Artistic | Visual qualities: light, color relationships, mood |
| `technical` | Technical | Orientation, lighting, composition, clarity, strengths/limits |
| `colorful` | Colorful | Specific color names, lighting direction, one-sentence atmosphere |
| `simple` | Simple | One sentence |
| `accessibility` | Accessibility *(default)* | Screen-reader optimized; left-to-right with sizes and positions |
| `comparison` | Comparison | Analogies and familiar-object comparisons |
| `mood` | Mood | Emotional atmosphere, psychological tone |
| `functional` | Functional | Focus on function, purpose, verbs (illuminates, supports, connects…) |
| `aialttext` | AI Alt Text | Three alt-text variants at 25 / 50 / 100 words |
