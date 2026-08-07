"""Contract tests for the interactive acceptance runner generator."""

from __future__ import annotations

from pathlib import Path

from scripts.gen_acceptance_html import _convert

_SCENARIO_MD = """# Section — Example

Intro paragraph with `code` and **bold**.

---

## EX-01 — Do the thing (`ex.thing`, Ctrl+T)

*What & why.* Because.

**Before you start**
- QUILL open.

**Do this**
1. Press **Ctrl+T**.

**You should see and hear**
- The thing happens.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## Checklist group

- [ ] `first` item — contract shorthand
- [ ] `first` item — contract shorthand
- [ ] second item

### Section sign-off
- Tester:
- Scenarios passed / total: ___ / 1
"""

_FENCE_MD = """# Fenced

## Not a checklist

```
- [ ] this checkbox is inside a fence and must stay literal
```

> **Sign off** — `[ ] Pass` in a blockquote must stay literal too.
"""


def _convert_text(tmp_path: Path, name: str, text: str):
    md = tmp_path / name
    md.write_text(text, encoding="utf-8")
    return _convert(md)


def test_scenario_block_gets_persistent_controls(tmp_path: Path) -> None:
    body, page = _convert_text(tmp_path, "section-example.md", _SCENARIO_MD)
    assert page.scenario_count == 1
    # The printed sign-off lines are replaced by real controls.
    assert "**Sign off**" not in body
    assert "____________" not in body
    assert 'name="section-example:scn:EX-01:outcome"' in body
    assert 'data-key="section-example:scn:EX-01:works"' in body
    assert 'data-key="section-example:scn:EX-01:notes"' in body
    # Scenario sections are collapsible regions with the heading preserved.
    assert '<details class="sec scenario" open data-kind="scenario">' in body
    assert "<summary><h2>EX-01" in body


def test_checklist_items_get_stable_distinct_keys(tmp_path: Path) -> None:
    body, page = _convert_text(tmp_path, "section-example.md", _SCENARIO_MD)
    assert page.checkbox_count == 3
    # Identical lines get occurrence-suffixed keys so state stays distinct.
    assert body.count('input type="checkbox" class="cb"') == 3
    keys = [part.split('"')[0] for part in body.split('data-key="')[1:]]
    assert len(keys) == len(set(keys))


def test_footer_fields_become_saved_inputs(tmp_path: Path) -> None:
    body, _ = _convert_text(tmp_path, "section-example.md", _SCENARIO_MD)
    assert '<section class="footerblock">' in body
    assert 'class="meta"' in body
    assert 'value="___ / 1"' in body


def test_fences_and_blockquotes_stay_literal(tmp_path: Path) -> None:
    body, page = _convert_text(tmp_path, "fenced.md", _FENCE_MD)
    assert page.scenario_count == 0
    assert page.checkbox_count == 0
    assert "input" not in body
    assert "[ ] this checkbox is inside a fence" in body


_QUALIFIED_MD = """# Section — Q

## Q-01 — Twin scenario

**Do this**
1. Step.

**Sign off (First half)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____

**Sign off (Second half)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____
"""


def test_qualified_signoff_lines_each_get_controls(tmp_path: Path) -> None:
    body, page = _convert_text(tmp_path, "section-q.md", _QUALIFIED_MD)
    assert page.scenario_count == 2
    assert 'data-sid="Q-01:first-half"' in body
    assert 'data-sid="Q-01:second-half"' in body
    assert "**Sign off" not in body


def test_inline_keeps_code_globs_and_bold_around_code() -> None:
    from scripts.gen_acceptance_html import _inline

    got = _inline("(`navigate.*`, `verbosity.*`) and **`Book Library`**")
    assert "<code>navigate.*</code>" in got
    assert "<code>verbosity.*</code>" in got
    assert "<strong><code>Book Library</code></strong>" in got
