from __future__ import annotations

import pytest

from quill.core.lists.model import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
)
from quill.core.lists.render import (
    DefinitionProfileError,
    render_definition_with_choice,
    render_html,
    render_markdown,
)
from quill.core.lists.settings import DefinitionMarkdownProfile, StructuredListSettings


def test_render_definition_with_choice_resolves_each_fallback() -> None:
    # ASK profile (the default) would raise; an explicit choice renders instead,
    # without mutating the stored settings (§7.6/§21.3).
    dl = DefinitionList(entries=[DefinitionEntry(terms=["Term"], definitions=["Def"])])
    cfg = StructuredListSettings()
    assert cfg.definition_markdown_profile is DefinitionMarkdownProfile.ASK

    assert "<dl>" in render_definition_with_choice(dl, cfg, "html")
    assert "Term\n: Def" in render_definition_with_choice(dl, cfg, "pandoc")
    plain = render_definition_with_choice(dl, cfg, "plain")
    assert "Term" in plain and "Def" in plain

    # The one-off choice did not mutate the caller's settings.
    assert cfg.definition_markdown_profile is DefinitionMarkdownProfile.ASK
    with pytest.raises(KeyError):
        render_definition_with_choice(dl, cfg, "bogus")


def _flat(list_type: ListType, *items: ListItem, start: int = 1) -> FlatList:
    return FlatList(list_type=list_type, items=list(items), ordered_start=start)


# -- Markdown --------------------------------------------------------------- #


def test_bullet_markdown_default_dash() -> None:
    md = render_markdown(_flat(ListType.BULLET, ListItem("apples"), ListItem("oranges")))
    assert md == "- apples\n- oranges"


def test_bullet_marker_configurable() -> None:
    md = render_markdown(
        _flat(ListType.BULLET, ListItem("a")), StructuredListSettings(bullet_marker="*")
    )
    assert md == "* a"


def test_ordered_sequential_numbers() -> None:
    md = render_markdown(_flat(ListType.ORDERED, ListItem("a"), ListItem("b"), ListItem("c")))
    assert md == "1. a\n2. b\n3. c"


def test_ordered_preserves_start_value() -> None:
    md = render_markdown(_flat(ListType.ORDERED, ListItem("a"), ListItem("b"), start=5))
    assert md == "5. a\n6. b"


def test_ordered_repeat_one_strategy() -> None:
    md = render_markdown(
        _flat(ListType.ORDERED, ListItem("a"), ListItem("b")),
        StructuredListSettings(ordered_strategy="repeat_one"),
    )
    assert md == "1. a\n1. b"


def test_checklist_markdown_reflects_checked_state() -> None:
    md = render_markdown(
        _flat(
            ListType.CHECKLIST, ListItem("buy milk", checked=True), ListItem("call", checked=False)
        )
    )
    assert md == "- [x] buy milk\n- [ ] call"


def test_nested_bullets_indent_in_markdown() -> None:
    md = render_markdown(_flat(ListType.BULLET, ListItem("top"), ListItem("child", level=1)))
    assert md == "- top\n  - child"


# -- HTML ------------------------------------------------------------------- #


def test_bullet_html() -> None:
    html = render_html(_flat(ListType.BULLET, ListItem("a"), ListItem("b")))
    assert html == "<ul>\n  <li>a</li>\n  <li>b</li>\n</ul>"


def test_ordered_html_start_attribute() -> None:
    html = render_html(_flat(ListType.ORDERED, ListItem("a"), start=3))
    assert html.startswith('<ol start="3">')


def test_checklist_html_disabled_checkbox_default() -> None:
    html = render_html(_flat(ListType.CHECKLIST, ListItem("task", checked=True)))
    assert '<input type="checkbox" checked disabled> task' in html


def test_html_escapes_item_text() -> None:
    html = render_html(_flat(ListType.BULLET, ListItem("a < b & c")))
    assert "a &lt; b &amp; c" in html


def test_nested_html_structure() -> None:
    html = render_html(_flat(ListType.BULLET, ListItem("top"), ListItem("child", level=1)))
    assert "<ul>" in html and html.count("<ul>") == 2  # nested list opened


# -- definition lists ------------------------------------------------------- #


def _deflist() -> DefinitionList:
    return DefinitionList(
        entries=[
            DefinitionEntry(terms=["Screen reader"], definitions=["Speaks on-screen text."]),
            DefinitionEntry(
                terms=["HTML", "HyperText Markup Language"], definitions=["Web markup."]
            ),
        ]
    )


def test_definition_html_semantics() -> None:
    html = render_html(_deflist())
    assert "<dl>" in html and "</dl>" in html
    assert "<dt>Screen reader</dt>" in html
    assert "<dd>Speaks on-screen text.</dd>" in html
    # Multiple terms share one definition: two <dt> before the <dd>.
    assert "<dt>HTML</dt>" in html and "<dt>HyperText Markup Language</dt>" in html


def test_definition_markdown_pandoc_profile() -> None:
    md = render_markdown(
        _deflist(),
        StructuredListSettings(definition_markdown_profile=DefinitionMarkdownProfile.PANDOC),
    )
    assert "Screen reader\n: Speaks on-screen text." in md


def test_definition_markdown_ask_profile_raises() -> None:
    with pytest.raises(DefinitionProfileError):
        render_markdown(
            _deflist(),
            StructuredListSettings(definition_markdown_profile=DefinitionMarkdownProfile.ASK),
        )


def test_definition_markdown_html_fallback() -> None:
    md = render_markdown(
        _deflist(),
        StructuredListSettings(definition_markdown_profile=DefinitionMarkdownProfile.HTML_FALLBACK),
    )
    assert md.startswith("<dl>")
