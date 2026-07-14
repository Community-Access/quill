# SPEC TEMPLATE — Quill AI-Collaborative Development

> Adapted from the QuickMail spec template for contributions to Community-Access/quill.
>
> **Key principle:** Specs are not just documentation; they are a contract between you and the AI about what will be built, with explicit decision points for when to start new sessions and what success looks like. For upstream contributions, the spec also lives in `_fork-private/` — it is your pre-flight work, not a requirement of the upstream project.

---

## How This Template Works

### Your Workflow

1. **Session 1 (this template):** You provide a broad goal. Claude writes a combined PM + Dev spec, you review and approve.
2. **Session 2 (implementation):** Implementing AI (DeepSeek or other) reads the approved spec plus the constraints block (§5 of this template) and builds the feature.
3. **Session 3 (manual testing):** You run the app and work through the Acceptance Walkthrough (§8). Note any failures.
4. **Session 4 (code review):** Claude reviews the implementation, fixes issues, and runs CI gates.
5. **Session 5 (PR + merge):** Polish, push, mark ready, request review from `accesswatch`.

### Why This Matters

- **Session 1 catches design gaps early** — keyboard walkthrough and shared component audit before any code is written.
- **Session 2 has the constraints** — banned patterns, dialog contract, module budgets. Without these, the implementing AI will produce code that fails CI.
- **Session 3 is manual human verification** — AI cannot test the UI. You do. The acceptance walkthrough is your script.
- **Session 4 is systematic** — fresh session, no prior context biases. CI gates catch what review misses.

---

## Section 1: Executive Summary

**Length:** 3–4 sentences. **Purpose:** Why this feature exists and what it does.

This should answer:
- What problem does it solve?
- Who benefits (especially screen reader / AT users)?
- How is it different from today?

**Example:**
> Quill today describes images with a single fixed prompt, giving users no control over the description style. This spec adds a Vision Prompt Library of 12 IDT-evaluated styles so users can choose the level of detail and framing that suits their workflow. The default behavior is unchanged; the picker is opt-in via Settings.

---

## Section 2: User Problem & Opportunity

### 2.1 Current state (verified)

Before/after table of the specific friction:

| Surface | Today | Pain | Who feels it |
|---|---|---|---|
| Feature X | Current behavior | What users can't do | User type |

**Key rule:** Every "today" claim must be verified against the code. If you say "there is no retry in the review dialog," grep for the dialog class and confirm. AI will ask you to verify; have the evidence ready.

### 2.2 Target personas (3–5)

For each persona:
- **Who** (role, context — include AT users where relevant)
- **What they want**
- **Why it matters**
- **How they'd use this feature**

### 2.3 Why now (optional)

Why is this the right time? E.g., a dependency just shipped, user feedback accumulated, roadmap alignment.

---

## Section 3: Design Principles

List 3–5 non-negotiable principles that resolve tie-breakers.

**Quill-specific examples:**
- "Zero-change for users who don't opt in."
- "Keyboard-only and screen reader users are the primary audience, not an afterthought."
- "Safe Mode is respected — AI-dependent features degrade gracefully when `QUILL_SAFE_MODE=1`."
- "No new network calls without a new entry in the egress audit."
- "Settings changes are written atomically; no partial writes."

---

## Section 4: Feature Scope & Acceptance Criteria

### 4.1 In scope (v1)

| Feature | Setting key | Default | Notes |
|---|---|---|---|
| Feature A | `settings.field_name` | value | What it does |

### 4.2 Explicitly out of scope (v1)

What does **not** ship. Prevents scope creep and surfaces hidden assumptions.

If something is deferred to v2, say so — don't leave it implicit.

---

## Section 5: Quill Project Constraints

**This section is copy-pasted verbatim to the implementing AI at the start of Session 2.**

```
You are implementing a feature for the Quill wxPython desktop application.
Read CLAUDE.md before writing any code. Key constraints:

ARCHITECTURE — strict import boundaries:
  - quill/core  = pure domain logic. NO wx imports. Strict-typed (mypy).
  - quill/io    = format readers/writers. NO wx imports. Strict-typed.
  - quill/ui    = wxPython layer. wx imports allowed here only.

BANNED PATTERNS — these fail the banned-patterns CI gate. Never use:
  - wx.ALIGN_RIGHT  →  use wx.EXPAND or wx.LEFT
  - dlg.ShowModal() directly  →  always use show_modal_dialog(dlg, "Title")
    from quill.ui.dialog_contract
  - apply_modal_ids() must be called on every new dialog
  - Inline imports inside functions  →  all imports at module top, sorted

SETTINGS — new settings fields:
  - Add to the Settings dataclass in quill/core/settings.py
  - Add validation in Settings.from_dict() with type narrowing
  - Use direct attribute access (settings.field_name), NOT getattr()
  - Sensitive values use DPAPI; see existing examples in settings.py

DIALOGS — contract:
  - All modal dialogs go through show_modal_dialog() from dialog_contract
  - Never call ShowModal() directly
  - Every dialog needs apply_modal_ids(dlg, affirmative_id=..., escape_id=...)
  - dialog_inventory.py audits compliance; your dialogs will be checked

MODULE SIZE BUDGETS — quill/tools/module_size_budgets.json is a ratchet:
  - If a tracked file grows past its budget, update the entry
  - Add a comment: _rebaseline_<date>_<reason>

THREADING — all wx widget access must be on the UI thread:
  - Background work via stability.task_manager.QuillTaskManager
  - Cross-thread UI updates via wx.CallAfter

SAFE MODE — QUILL_SAFE_MODE=1 disables AI, watch folder, and Quillins:
  - AI-dependent features must check safe mode and degrade gracefully

PERSISTENCE — all JSON writes via core.storage.write_json_atomic

LINT — before handing off, run:
  ruff check .
  ruff format --check .
  python -m quill.tools.check_banned_patterns quill/
  mypy quill/core quill/io
  pytest tests/unit/ tests/stability/ -q
```

---

## Section 6: Architecture & Technical Decisions

### 6.1 Key architectural decisions

For each major decision:

**Decision:** [Single-sentence statement of choice]

**Alternatives:**
1. Alt A: Pro X, Con Y.
2. Alt B: Pro X, Con Y.

**Rationale:** Why this was chosen. Include verified constraints.

**Quill-specific decisions to document:**
- Which layer does new logic live in? (core vs. ui — default to core if no wx needed)
- New settings fields: type, validation rules, defaults
- Dialog structure: new dialog or extend existing? If extending, name all call sites
- Threading: does this touch the network or file system? Background thread required?
- Safe mode: does this feature need to degrade when `QUILL_SAFE_MODE=1`?
- New AI session type or reuse of `core/ai/`?

### 6.2 Safe mode compatibility

If your feature has AI, network, or Quillin dependencies:

| Mode | Behavior | Fallback |
|---|---|---|
| Normal | Full feature available | — |
| `QUILL_SAFE_MODE=1` | Feature disabled/degraded | Show message or hide UI element |

### 6.3 Shared component audit (mandatory)

**List every existing class, dialog, or method the feature will modify or call, plus its other consumers.**

This is where bugs hide. The Vision Prompt Library (#195) modified `OcrReviewDialog`, which had two call sites (OCR results and AI image description). The spec didn't name the second call site; the implementing AI introduced a retry button that appeared in the wrong context.

| Component | File | Other consumers | Change needed |
|---|---|---|---|
| `ExistingDialog` | `quill/ui/existing_dialog.py` | Called from X, Y | Add `new_flag=False` param |

### 6.4 Code reuse and duplication risks

Call out code you might duplicate and plan extractions:

- "The settings reload pattern exists in three places. Plan: reuse the same pattern, don't introduce a fourth variant."

---

## Section 7: Keyboard Walkthrough (Mandatory)

Proves the feature is fully designed before code is written. A numbered script of what the user does and what they hear/see.

**Complete every path without ambiguity.** A gap is a design decision — resolve it now, not during implementation.

**Format:**

### Path: [Name]

1. User is in [context]. User presses [key]. **Expected:** Focus moves to [element], screen reader announces "[text]", [visual change].
2. User presses [key]. **Expected:** …

**Paths to cover:**
- Happy path (primary use case)
- Error / failure cases
- Edge cases (empty state, no items, boundary values)
- Every settings variant
- Keyboard-only navigation (no mouse)
- Screen reader user (all announcements, control names via `SetName()`)
- Safe mode (if applicable)

**Quill-specific:**
- What does `SetName()` return for every new control?
- If a dialog opens — how does focus return when it closes?
- If a dropdown/listbox — what does the screen reader announce per item?
- If settings change — does the relevant UI refresh without requiring a restart?

---

## Section 8: Acceptance Walkthrough (Mandatory)

**This is different from the keyboard walkthrough.** The keyboard walkthrough is a design document — it proves the feature is fully specified. The acceptance walkthrough is a runtime testing script — it proves the feature actually works after implementation. You run this in the app at Session 3.

Each step is a concrete action you perform and a concrete thing you verify.

**Format:**

### Scenario: [Name]

**Setup:** [App state before starting — e.g., "app running, Settings > AI open"]

1. Do [action]. **Verify:** [Exact observable outcome — text, focus, announcement, absence of error.]
2. Do [action]. **Verify:** …
3. **Edge case:** Do [unusual action]. **Verify:** [No crash / graceful handling.]

**Mark each step pass/fail when testing. Any fail = document before handing to Session 4.**

**Scenarios to cover:**
- The primary happy path end-to-end
- The primary error case (what happens when the operation fails)
- Any new settings — toggle on, toggle off, verify UI responds
- Shared components you modified — verify the other call sites still work correctly
- Safe mode — run with `QUILL_SAFE_MODE=1` if the feature touches AI/network/Quillins
- Screen reader — tab through every new control, confirm `SetName()` is readable

**Example from Vision Prompt Library (#195):**

### Scenario: Describe image with non-default style

**Setup:** App running, an image file is loaded in the document.

1. Open the AI image description flow. **Verify:** Picker dialog appears (if `vision_prompt_picker_enabled = True`). Screen reader announces dialog title.
2. Select "Detailed description" style from the list. Press Enter. **Verify:** Description runs, review dialog opens, edit control is named "Image description" (not "Recognized text").
3. In the review dialog, click Retry. **Verify:** Picker reappears, previous style is pre-selected.
4. Cancel from the picker. **Verify:** Returns to review dialog with original text intact.
5. Accept the description. **Verify:** Text inserted into document.

### Scenario: OCR — verify no regression from shared dialog

**Setup:** App running, an image is loaded.

1. Run OCR (not AI description). **Verify:** Review dialog opens. **No retry button is present.** Edit control is named "Recognized text."

---

## Section 9: Success Metrics

How will you know the feature works?

- **Behavioral:** "User can [primary action] with [result]."
- **Keyboard-centric:** "All primary actions work keyboard-only."
- **No regressions:** "Existing [related feature] behavior is unchanged."
- **Accessibility:** "Screen reader user can [navigate/use feature] and learns [state] from announcements."
- **Safe mode:** (if applicable) "Feature degrades gracefully with `QUILL_SAFE_MODE=1`."

---

## Section 10: Implementation Phases

Break into 3–5 testable phases. Each phase:

- **Name**
- **Goal** (what's complete)
- **Deliverables** (files created/modified)
- **Tests** (what pytest tests cover it)
- **Risk** (what could go wrong, when caught)

**Example from Vision Prompt Library:**

### Phase 1: Core data and settings

**Goal:** Prompt styles defined, settings fields exist and round-trip.

**Deliverables:**
- `quill/core/ai/vision_prompts.py` — prompt data, `BUILTIN_STYLE_IDS`
- `quill/core/settings.py` — 4 new fields, `from_dict()` validation

**Tests:**
- `tests/unit/core/test_vision_prompts.py`
- `tests/unit/core/test_settings.py` — validation, defaults, round-trip

**Risk:** Type validation in `from_dict()` is easy to get wrong for nested types. Catch with unit tests covering malformed input.

### Phase 2: UI — picker and manager dialogs

**Goal:** Picker dialog and Manage dialog exist and are navigable keyboard-only.

**Deliverables:**
- `quill/ui/vision_prompt_picker_dialog.py`
- `quill/ui/vision_prompt_manager_dialog.py`

**Risk:** `wx.ALIGN_RIGHT` and bare `ShowModal()` are common mistakes. Run banned-patterns check after each file.

### Phase 3: Integration into image description flow

**Goal:** Full end-to-end flow works; retry loop works; settings dropdown refreshes.

**Deliverables:**
- `quill/ui/main_frame_image.py` — call picker, pass style to AI session
- `quill/ui/assistant_tools.py` — refresh dropdown after Manage dialog closes
- `quill/ui/ocr_review_dialog.py` — `allow_retry` and `text_label` params

**Risk:** Shared dialog (`OcrReviewDialog`) has two call sites. Verify OCR path explicitly in acceptance walkthrough.

---

## Section 11: Files to Create / Modify

Implementation checklist and code reviewer's map.

### Files to Create

| File | Purpose | Lines (est.) |
|---|---|---|
| `quill/core/ai/new_module.py` | Domain logic | 50–100 |
| `quill/ui/new_dialog.py` | UI dialog | 150–250 |

### Files to Modify

| File | Changes | Lines changed (est.) |
|---|---|---|
| `quill/core/settings.py` | New fields + validation | +30 |
| `quill/ui/main_frame_image.py` | Call new dialog | +20 |
| `quill/tools/module_size_budgets.json` | Rebaseline if needed | varies |

---

## Section 12: Tests to Add

| Test file | Test methods | What's covered |
|---|---|---|
| `tests/unit/core/test_X.py` | `test_happy_path`, `test_invalid_input` | New domain logic |
| `tests/unit/core/test_settings.py` | `test_new_field_defaults`, `test_new_field_validation` | Settings round-trip |

**Key rule:** Every new public function in `quill/core` or `quill/io` gets at least one unit test. Every branch in validation logic gets a test case.

---

## Section 13: Known Risks & Open Questions

### 13.1 Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Shared dialog modified without checking all call sites | Medium | Major | Shared component audit in §6.3; acceptance walkthrough scenario for each call site |
| Module budget exceeded without rebaseline | High | CI fail | Check budgets after implementation; rebaseline with comment |
| Settings field missing from `from_dict()` | Medium | Silent data loss | Unit test: malformed input returns safe default |

### 13.2 Open questions

Every open question gets a decision before the spec is approved. Document the decision and rationale.

---

## Section 14: Keyboard Reference

If the feature adds shortcuts:

| Key | Action | Context | Notes |
|---|---|---|---|
| `Ctrl+X` | [Action] | [Where] | [Notes] |

---

## Section 15: Implementation Guidance for AI

**This section is written to the AI assistant for Session 2.**

### 15.1 What you're expected to decide

State what's intentionally left vague, expecting the AI to use judgment:

- "The spec describes X but doesn't specify Y. You'll decide based on [constraint]."
- "If [situation] arises, prefer [approach]."

### 15.2 When to ask for clarification

- "If a shortcut conflicts with an existing one, stop and ask before working around it."
- "If the module budget for [file] must be raised by more than 100 lines, ask first."

### 15.3 Acceptance walkthrough preview

"After you build this, the user will test using the Acceptance Walkthrough in §8. Specifically:
- [Bullet the steps most likely to catch bugs in this feature]

If any of these fail, document the failure and it will be addressed in Session 4 (code review)."

---

## Section 16: Session Boundaries

### Session 1 → Session 2

**When:** Spec approved, no open questions.

**Give Session 2:** The approved spec + §5 (constraints block) + CLAUDE.md.

**Session 2 delivers:** Working code, lint-clean, with unit tests passing. Ready for manual testing.

### Session 2 → Session 3

**When:** Implementation done.

**You do:** Run the Acceptance Walkthrough in §8. Note every pass/fail.

### Session 3 → Session 4

**When:** Manual testing complete.

**Give Session 4 (Claude):** "Tested. Found: [list of failures or 'no failures']. Request code review."

**Session 4 delivers:** Review findings addressed, all CI gates passing, PR ready for upstream.

---

## Checklist for Approving a Spec

- [ ] Scope is bounded. Feature doesn't try to do too much in one session.
- [ ] Architecture is decided. No "figure it out during coding."
- [ ] **Shared component audit complete (§6.3).** Every existing class/dialog modified is named, with all its callers listed.
- [ ] Keyboard walkthrough complete. No TBD paths.
- [ ] Acceptance walkthrough written. Covers happy path, error case, every shared component caller.
- [ ] Safe mode behavior defined (if applicable).
- [ ] Implementation phases are testable independently.
- [ ] Risks documented with mitigations.
- [ ] No open questions remain.
- [ ] Files and tests listed.
- [ ] Module budgets checked — if files will grow, pre-plan the rebaseline.

---

## When This Template is Overkill

- **Bug fix or small enhancement** — Sections 1, 4, 6 (abbreviated), 8, 11 only.
- **Refactor with no user-facing change** — Section 6 (architecture), skip UI/keyboard.
- **Settings tweak** — Sections 1, 4, and a settings table.

Adjust depth to scope. The template is a maximum, not a minimum.

---

## Fork PR Reminders

- Keep spec and artifacts in `_fork-private/` on `main` — never include in feature branch
- Any `docs/**/*.md` added requires `.html` and `.epub` committed alongside it (see `ai-handoff.md`)
- Set branch tracking after first push: `git branch --set-upstream-to=origin/<branch> <branch>`
- Mark PR ready for review only after code-side CI gates pass (`regenerate` failure is expected for fork PRs)
- Request review from `accesswatch`
