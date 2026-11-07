"""Mermaid diagram accessibility checks, and their place in the Tune-Up."""

from __future__ import annotations

from quill.core.accessibility_agent import apply_plan, build_plan
from quill.core.mermaid_a11y import check_mermaid, find_mermaid_blocks

GOOD = (
    "# Flow\n\n"
    "```mermaid\n"
    "flowchart TD\n"
    "    accTitle: Order flow\n"
    "    accDescr: An order is placed, then paid for.\n"
    "    A --> B\n"
    "```\n"
)


def _kinds(text: str) -> list[tuple[str, int]]:
    return [(f.kind, f.line) for f in check_mermaid(text)]


def test_a_labelled_diagram_has_no_findings() -> None:
    assert check_mermaid(GOOD) == []


def test_missing_title_and_description_point_at_the_opening_fence() -> None:
    text = "Intro\n\n```mermaid\nflowchart TD\n    A --> B\n```\n"
    assert _kinds(text) == [("acc-descr", 3), ("acc-title", 3)]


def test_a_multi_line_description_counts() -> None:
    text = "```mermaid\npie\n  accTitle: Pets\n  accDescr {\n    Mostly cats.\n  }\n```\n"
    assert check_mermaid(text) == []


def test_theme_in_an_init_block_is_flagged_on_its_line() -> None:
    text = GOOD.replace("flowchart TD\n", "%%{init: {'theme': 'dark'}}%%\nflowchart TD\n")
    assert ("theme", 4) in _kinds(text)


def test_an_init_block_without_a_theme_is_fine() -> None:
    text = GOOD.replace(
        "flowchart TD\n", "%%{init: {'flowchart': {'curve': 'basis'}}}%%\nflowchart TD\n"
    )
    assert check_mermaid(text) == []


def test_colours_advise_a_contrast_check() -> None:
    text = GOOD.replace(
        "    A --> B\n",
        "    A --> B\n    style A fill:#f9f,color:#fff\n    classDef hot fill:red\n",
    )
    findings = [f for f in check_mermaid(text) if f.kind == "colour"]
    assert [f.line for f in findings] == [8, 9]
    assert "contrast" in findings[0].rationale


def test_several_diagrams_each_want_a_heading() -> None:
    body = "flowchart TD\n    accTitle: t\n    accDescr: d\n    A --> B\n"
    text = f"# One\n\n```mermaid\n{body}```\n\nSome words.\n\n```mermaid\n{body}```\n"
    assert _kinds(text) == [("heading", 12)]


def test_a_single_diagram_needs_no_heading() -> None:
    assert check_mermaid(GOOD.replace("# Flow\n\n", "Words first.\n\n")) == []


def test_other_fences_and_tilde_fences() -> None:
    text = "```python\nprint('mermaid')\n```\n\n~~~mermaid\nflowchart TD\n~~~\n"
    blocks = find_mermaid_blocks(text)
    assert [b.start_line for b in blocks] == [5]


def test_the_tune_up_lists_diagram_findings_for_review_only() -> None:
    text = "```mermaid\nflowchart TD\n    A --> B\n```\n"
    plan = build_plan("d.md", text, "markdown")
    steps = [s for s in plan.steps if s.category == "diagrams"]
    assert [s.line for s in steps] == [1, 1]
    assert all(not s.auto_fixable for s in steps)
    assert apply_plan(plan, text, {s.step_id for s in plan.steps}).text == text


def test_the_tune_up_ignores_mermaid_outside_markdown() -> None:
    text = "```mermaid\nflowchart TD\n```\n"
    plan = build_plan("d.txt", text, "html")
    assert not [s for s in plan.steps if s.category == "diagrams"]
