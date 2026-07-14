# AI Handoff Guide — kellylford/quill fork

> **FORK-PRIVATE — do not include in PRs to Community-Access/quill.**
> This file lives on `main` in the fork only. Never add it to a feature branch
> or include it in a PR diff.

This document captures the process and constraints for using multiple AI tools
to develop and contribute features to this project. Written after the Vision
Prompt Library (issue #195 / PR #248) contribution.

**See also:** `_fork-private/spec-template.md` — the full spec template adapted
for this project. Use it for Session 1 (spec drafting). Section 5 of the
template is the constraints block that gets copy-pasted to the implementing AI.

---

## The workflow that works

1. **You** — originate the idea and requirements
2. **Claude** (spec drafting) — turn your concept into a structured spec
3. **DeepSeek or another coding AI** — implement from the spec
4. **Claude** (review + cleanup) — code review, fix issues, run CI gates, finish the PR

This division works because spec drafting and project-aware review benefit from
deep context, while raw implementation benefits from coding speed. The review
pass is **not optional** — this project has enough internal gates that outside
implementation always needs a cleanup pass.

---

## What to give the implementing AI

Always include all three of these at the start of the implementation session:

### 1. The spec document
The full feature spec. Make sure it explicitly names any existing shared
components the feature will touch and lists their other consumers. The #195
review found a pre-existing bug where `OcrReviewDialog` had two call sites
(OCR results and AI image description) and its edit control name was always
"Recognized text" regardless of context. The spec didn't flag this; it should
have.

### 2. CLAUDE.md (the project instructions)
Paste the full contents of `CLAUDE.md` from the repo root. The implementing AI
will not automatically read this and it contains critical project-specific
rules.

### 3. The project constraints block (copy-paste this)

```
This project has several non-obvious rules you must follow:

BANNED PATTERNS — these will fail CI. Never use:
  - wx.ALIGN_RIGHT (use wx.EXPAND or wx.LEFT)
  - bare ShowModal() calls — always use show_modal_dialog() from dialog_contract
  - inline imports inside functions (imports go at module top)

MODULE SIZE BUDGETS — quill/tools/module_size_budgets.json tracks line-count
ceilings. If your changes cause a tracked file to exceed its budget, update
the budget entry and add a _rebaseline_<date>_<reason> comment.

DIALOG CONTRACT — all modal dialogs must use _show_modal_dialog (MainFrame) or
show_modal_dialog (dialog_contract). Never call dlg.ShowModal() directly.
apply_modal_ids() must be called on every dialog.

SETTINGS — new settings fields go in Settings dataclass in core/settings.py
with validation in from_dict(). Use direct attribute access (settings.field),
not getattr(settings, 'field').

IMPORTS — quill/core has no wx imports (pure domain logic). quill/ui is the
wxPython layer. Never import wx in core/.
  
LINT — run these before handing off:
  ruff check .
  ruff format --check .
  python -m quill.tools.check_banned_patterns quill/

TYPING — new core/ and io/ code must be strict-typed (mypy clean):
  mypy quill/core quill/io
```

---

## Pre-handoff spec checklist

Before giving a spec to an implementing AI, verify it covers:

- [ ] Names every existing file/class/dialog the feature touches
- [ ] **Shared component audit complete** — for every existing class/dialog being modified, lists all its other callers
- [ ] Specifies new settings fields, their types, and valid values
- [ ] Describes the dialog/UI structure down to button labels and control names (`SetName()` values matter for screen readers)
- [ ] Calls out any module budget files that will grow
- [ ] Keyboard walkthrough covers every path including error cases and edge cases
- [ ] **Acceptance walkthrough written** — numbered steps to run in the app after implementation (see below)

---

## Acceptance walkthrough (add to every spec)

The keyboard walkthrough in the spec proves the feature is *designed*. The
acceptance walkthrough proves it *works*. Write it in the spec before
implementation starts, then run it yourself at Session 3.

**Format:** numbered steps with concrete actions and verifiable outcomes.
Each step is something you physically do and something you physically observe.

```
### Scenario: [Name]
Setup: [app state — e.g., "app running, image loaded"]

1. Do [action]. Verify: [exact observable outcome].
2. Do [action]. Verify: [exact observable outcome].
3. Edge case: Do [unusual action]. Verify: [no crash / graceful handling].
```

**Always include:**
- The primary happy path end-to-end
- The primary error/failure case
- Every shared component you modified — one scenario per call site
- New settings toggled on and off — verify UI responds without restart
- Screen reader — tab through every new control, read `SetName()` aloud
- Safe mode (`QUILL_SAFE_MODE=1`) if the feature touches AI/network/Quillins

**Lesson from #195:** The `OcrReviewDialog` shared dialog bug (retry button
appearing in OCR context) would have been caught immediately by a scenario
that said: "Run OCR. Verify: no retry button is present." Write those
scenarios for every shared component — don't assume unchanged call sites
are safe.

---

## Post-implementation review checklist

When Claude reviews the implementation, check these explicitly:

- [ ] No `wx.ALIGN_RIGHT` or bare `ShowModal()` calls
- [ ] All imports at module top, sorted (ruff I001)
- [ ] `ruff format` clean
- [ ] `ruff check` clean
- [ ] `mypy quill/core quill/io` clean
- [ ] Module size budgets updated if any tracked file grew
- [ ] Settings fields use direct access, not getattr
- [ ] Any shared dialog/component — verify behavior at all call sites
- [ ] New settings validated in `from_dict()` with type narrowing
- [ ] UI dropdowns/controls that reflect settings refresh after dialogs close
- [ ] `python -m quill.tools.check_banned_patterns quill/` passes
- [ ] `python -m quill.tools.dialog_inventory` passes

---

## Fork PR process specifics

This fork (`kellylford/quill`) targets `Community-Access/quill:main`.

**Docs artifacts:** Any file added or changed under `docs/**/*.md` requires
matching `.html` and `.epub` files committed in the same PR. The
`docs-artifacts.yml` workflow auto-generates these for same-repo PRs but
**cannot push back to a fork branch**. Generate them locally:

```powershell
# Install Pandoc once (winget)
winget install --id JohnMacFarlane.Pandoc

# Refresh PATH in the same session
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")

# Generate for a changed doc
pandoc docs/my-spec.md -f gfm -t html5 -s -o docs/my-spec.html
pandoc docs/my-spec.md -f gfm -t epub3      -o docs/my-spec.epub
```

Commit the `.html` and `.epub` alongside the `.md`. The `accessibility-tests`
CI check validates this; the `regenerate` check will still fail for fork PRs
(infrastructure limitation) but is not a blocking gate.

**Branch tracking:** After pushing a new feature branch, set its tracking
reference so GitHub Desktop doesn't show it as unpublished:

```bash
git branch --set-upstream-to=origin/<branch> <branch>
```

**PR draft → ready:** Mark the PR ready for review only after all code-side
CI checks pass. The `regenerate` failure is expected and acceptable for fork
PRs.

---

## Lessons from #195 (Vision Prompt Library)

- DeepSeek implemented the core feature correctly but missed project conventions
  it couldn't have known without CLAUDE.md — ruff formatting, banned patterns,
  module budgets. Feed it the constraints block above next time.
- A pre-existing bug (`OcrReviewDialog` edit control always named "Recognized
  text" regardless of caller) was discovered during manual testing, not during
  code review. AI cannot test UI. The acceptance walkthrough would have surfaced
  this with a single scenario: "Run OCR. Verify: no retry button, control named
  'Recognized text'."
- The spec's shared component audit was missing — it didn't name `OcrReviewDialog`'s
  second call site (OCR results). A shared component audit + acceptance walkthrough
  scenario per call site would have caught this before implementation.
- The spec document was committed to `main` but never cherry-picked onto the
  feature branch — caught during PR review. Make adding the spec to the feature
  branch part of the initial commit.
- Pandoc artifacts for the spec doc had to be generated locally because the
  CI auto-generate workflow can't push to fork branches.
