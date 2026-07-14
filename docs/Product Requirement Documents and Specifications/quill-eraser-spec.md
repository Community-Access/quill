# Quill Eraser — Product Requirement Document

**Version:** 1.0  
**Date:** 2026-06-17  
**Author:** Jeff Bishop  
**Status:** Implemented (MVP shipped in QUILL 0.6.0)

---

## 1. Overview

Quill Eraser is a deterministic, rule-based text hygiene checker built into QUILL. It catches common mechanical writing problems — extra spaces, trailing whitespace, missing spaces after punctuation, excessive blank lines, lowercase sentence starts — and offers one-click fixes for each finding.

It operates without AI, without a network call, and without any probabilistic model. Every finding is reproducible: the same input always produces the same output. This is a deliberate design choice that separates Quill Eraser from AI writing tools: it is a mechanical proofreader, not a style advisor.

---

## 2. Goals

- Give writers a fast, offline way to catch spacing and punctuation mechanics errors before sharing or publishing.
- Respect screen-reader workflows: every finding, fix, and navigation action is announced.
- Never flag content that is legitimately correct: URLs, emails, code, file paths, numbers, and Markdown structure are all exempt.
- Integrate as a first-class QUILL feature with menu items, settings, and feature-catalog registration.
- Keep the implementation pure-domain (no wx imports in core) so the engine is fully testable in isolation.

---

## 3. Non-goals

- Style advice (sentence length, passive voice, readability) — that is the AI writing layer's job.
- Grammar checking — deferred to AI grammar tools.
- Spelling — covered by the existing spell-check commands.
- PDF, DOCX, or other non-text formats — Quill Eraser operates on the editor's text buffer only.
- Custom user-defined rules in this release — the engine exposes a `HygieneRule` ABC and `extra_rules` parameter for future extension.

---

## 4. User stories

**U-1. Trailing whitespace cleanup**  
As a writer finishing a document, I want to remove all trailing spaces at once so my file is clean before sharing.

**U-2. Space-after-punctuation check**  
As a writer who types quickly, I sometimes miss a space after a comma or period. I want Quill to find those spots and fix them with a single keystroke.

**U-3. Scoped check on selection**  
As a writer editing a section I just rewrote, I want to check only that section rather than the whole document to avoid noise from parts I have not touched yet.

**U-4. Code-file safety**  
As a developer who sometimes opens Python or JavaScript files in QUILL, I do not want prose rules to fire on code. I am happy to run trailing-space cleanup if I opt in.

**U-5. Screen-reader workflow**  
As a screen-reader user, I want every finding and every fix to be announced so I can work through the list entirely by keyboard without visual feedback.

---

## 5. Architecture

### 5.1 Core package: `quill/core/hygiene/`

| Module | Responsibility |
|--------|---------------|
| `findings.py` | Pure data: `HygieneFinding`, `HygieneSettings`, `HygieneContext`, `TextRange` frozen dataclasses |
| `ignored_ranges.py` | `compute_ignored_ranges(text, *, is_markdown)` — regex-based range exclusion for URLs, emails, file paths, code, etc. |
| `rules.py` | `HygieneRule` ABC and seven built-in rule classes; `BUILTIN_RULES` tuple |
| `engine.py` | `HygieneEngine`: orchestrates rules, handles code-file suppression, re-bases scoped offsets, deduplicates overlapping findings |
| `__init__.py` | Re-exports `HygieneEngine`, `HygieneFinding`, `HygieneContext`, `HygieneSettings`, `TextRange` |

The entire `quill/core/hygiene/` package has no `wx` imports and is fully strict-typed under mypy.

### 5.2 UI layer

| Module | Responsibility |
|--------|---------------|
| `quill/ui/hygiene_dialog.py` | `HygieneReviewDialog` — modeless `wx.Dialog` with `ListCtrl`, detail pane, and action buttons |
| `quill/ui/main_frame_hygiene.py` | `HygieneMixin` — mixes into `MainFrame`; owns `open_quill_eraser`, `_run_hygiene`, `_hygiene_apply_fix`, `_hygiene_goto` |

The mixin is wired into `MainFrame` via the MRO. Menu items and bindings are in `main_frame_menu.py`.

### 5.3 Settings

Four new fields in `quill/core/settings.py`:

```python
hygiene_min_confidence: str = "high"          # "high" | "medium" | "low"
hygiene_allow_double_space_after_period: bool = False
hygiene_max_blank_lines: int = 2              # 1..10
hygiene_rules_disabled: str = ""              # comma-separated rule IDs
```

### 5.4 Feature catalog

```
"core.hygiene": FeatureDefinition(
    "core.hygiene",
    "Quill Eraser",
    aliases=("quill eraser", "text hygiene", "hygiene checker", ...),
    maturity="stable",
    privacy="local only",
    category="writing",
    dependencies=("core.editor",),
)
```

---

## 6. Built-in rules (MVP)

| Rule ID | Name | Confidence | Auto-fixable |
|---------|------|-----------|--------------|
| `prose.multiple_spaces` | Multiple spaces between words | High | Yes — collapse to one space |
| `prose.trailing_spaces` | Trailing spaces at end of line | High | Yes — remove |
| `prose.space_before_punctuation` | Space before punctuation | High | Yes — remove space |
| `prose.excessive_blank_lines` | Excessive blank lines | High | Yes — truncate to max |
| `prose.missing_space_after_sentence_punct` | Missing space after sentence punctuation | Medium | Yes — insert space |
| `prose.missing_space_after_comma` | Missing space after comma/semicolon/colon | Medium | Yes — insert space |
| `prose.lowercase_sentence_start` | Sentence starts with lowercase letter | Medium | Yes — uppercase first letter |

---

## 7. Ignored range categories

The engine never reports findings inside these ranges:

- HTTP/HTTPS/FTP/WWW URLs
- Email addresses
- Decimal numbers (e.g. `3.14`)
- Time patterns (e.g. `14:30`)
- Absolute and relative file paths
- Markdown fenced code blocks (when `is_markdown=True`)
- Markdown inline code spans (when `is_markdown=True`)
- Markdown YAML front matter (when `is_markdown=True`)
- Markdown link URLs — the `(url)` portion of `[text](url)` (when `is_markdown=True`)

---

## 8. Code-file behaviour

Files with extensions in `_CODE_EXTENSIONS` (Python, JavaScript, TypeScript, HTML, CSS, JSON, YAML, etc.) trigger a prompt:

- **Yes — safe checks only:** runs `prose.trailing_spaces` only.
- **No:** skips all checks.
- **Cancel:** returns without scanning.

Indent-sensitive extensions (`py`, `yaml`, `yml`) are identified but not treated differently in this release — the trailing-space check is the only safe-only rule.

---

## 9. Dialog UX

The review dialog (`HygieneReviewDialog`) is modeless so the user can navigate to issues in the editor while the dialog remains open.

Controls:
- **Summary label** — "N issues found" with optional ignored count.
- **Findings list** (`wx.ListCtrl`) — columns: `#`, Confidence, Issue, Line.
- **Detail pane** (`wx.StaticBoxSizer` + multiline read-only `wx.TextCtrl`) — shows title, confidence, location, found text, suggested text, and rule description.
- **Apply Fix** — applies fix, marks as resolved, advances to next finding.
- **Ignore** — hides the finding for this session; does not apply a fix.
- **Go to Issue** — selects the offending range in the editor and announces location.
- **Previous / Next** — navigate the list.
- **Rescan** — re-runs the engine and refreshes the list.
- **Close** — destroys the dialog.

If the text at a finding's position has changed between scan and Apply Fix, a message box explains why the fix could not be applied and prompts the user to rescan.

---

## 10. Accessibility

- All button actions trigger `_announce()` on `MainFrame` for screen-reader feedback.
- Dialog uses `apply_modal_ids(dlg, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)` for keyboard contract.
- `ListCtrl` has an accessible name ("Findings list").
- Detail `TextCtrl` is read-only and word-wrapped, named "Issue detail".
- `Rescan` fires the engine on the same scope (document or selection) so the announcement summarises new findings without losing context.

---

## 11. Testing

41 unit tests in `tests/unit/core/test_hygiene_rules.py` covering:

- All seven rule classes with positive and negative cases
- Double-space-after-period exception
- Engine code-file suppression (`is_code_file`)
- Scope limiting (`scope_start`/`scope_end`)
- `apply_fix` happy path and stale-text guard
- Ignored-range exclusions (URL interior, inline code, fenced code, front matter, link URL, decimal numbers, times)
- Deduplication of overlapping findings

---

## 12. Future directions (out of scope for MVP)

- **User-defined rules** via a Quillin contribution point (`contributes.hygiene_rules`).
- **Batch Fix All** — apply all fixable high-confidence findings in one pass.
- **Ignore word/pattern** — add a term to a per-document or global exception list.
- **Parallel scan** — for very large documents, run rules on background thread and report incrementally.
- **Export findings** — save a findings report as plain text or CSV.
- **Integration with compare mode** — show hygiene findings alongside diff markers.
