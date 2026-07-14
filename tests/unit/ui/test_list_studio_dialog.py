"""Wiring tests for ListStudioDialog that do not need a live wx control tree.

The full control behavior is exercised by hand with a screen reader; here we guard
the seam between the dialog and ``quill.core.lists`` — that the dialog renders the
model it was given through the right renderer and reports an accurate summary — so
a regression in that wiring is caught without a wx display.
"""

from __future__ import annotations

from quill.core.lists import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
)
from quill.core.lists.settings import DefinitionMarkdownProfile, StructuredListSettings
from quill.ui.list_studio_dialog import ListStudioDialog


def _studio(**kwargs: object) -> ListStudioDialog:
    # __init__ only stores its arguments; no wx objects are constructed until
    # populate(), so a placeholder wx module is fine for these seam tests.
    return ListStudioDialog(wx=object(), **kwargs)  # type: ignore[arg-type]


def test_renders_flat_markdown_by_default() -> None:
    studio = _studio(flat=FlatList(items=[ListItem("apples"), ListItem("oranges")]))
    assert studio._render() == "- apples\n- oranges"
    assert studio.summary == "Bulleted list, 2 items."


def test_renders_flat_html_when_format_is_html() -> None:
    studio = _studio(flat=FlatList(items=[ListItem("a")]), target_format="html")
    assert studio._render() == "<ul>\n  <li>a</li>\n</ul>"


def test_definition_model_selects_definition_type() -> None:
    dl = DefinitionList(entries=[DefinitionEntry(terms=["Term"], definitions=["Def"])])
    studio = _studio(
        definition=dl,
        settings=StructuredListSettings(
            definition_markdown_profile=DefinitionMarkdownProfile.PANDOC
        ),
    )
    assert studio._is_definition()
    assert "Term\n: Def" in studio._render()


def _definition_studio(fallback: object, **kwargs: object) -> ListStudioDialog:
    dl = DefinitionList(entries=[DefinitionEntry(terms=["Term"], definitions=["Def"])])
    # Default settings carry the ASK profile, so _render() raises and the
    # resolution path (the injected prompt) is taken.
    return _studio(definition=dl, resolve_definition_fallback=fallback, **kwargs)


def test_resolve_source_prompts_and_renders_chosen_fallback() -> None:
    # §7.6/§21.3: when no Markdown definition profile is set, the prompt's choice
    # decides the source instead of a silent HTML fallback.
    assert "<dl>" in (_definition_studio(lambda: "html")._resolve_source() or "")
    assert "Term\n: Def" in (_definition_studio(lambda: "pandoc")._resolve_source() or "")
    plain = _definition_studio(lambda: "plain")._resolve_source() or ""
    assert "Term" in plain and "Def" in plain


def test_resolve_source_returns_none_when_prompt_cancelled() -> None:
    # A cancelled prompt leaves the document untouched (the caller keeps the dialog
    # open) rather than committing a guessed format.
    assert _definition_studio(lambda: None)._resolve_source() is None


def test_resolve_source_skips_prompt_when_profile_configured() -> None:
    dl = DefinitionList(entries=[DefinitionEntry(terms=["Term"], definitions=["Def"])])

    def _should_not_run() -> str:
        raise AssertionError("prompt must not fire when a profile is configured")

    studio = _studio(
        definition=dl,
        settings=StructuredListSettings(
            definition_markdown_profile=DefinitionMarkdownProfile.PANDOC
        ),
        resolve_definition_fallback=_should_not_run,
    )
    assert "Term\n: Def" in (studio._resolve_source() or "")


def test_checklist_render_reflects_checked_state() -> None:
    studio = _studio(
        flat=FlatList(
            list_type=ListType.CHECKLIST,
            items=[ListItem("done", checked=True), ListItem("todo")],
        )
    )
    assert studio._render() == "- [x] done\n- [ ] todo"


def test_multiple_terms_render_as_multiple_dt() -> None:
    # One entry with two synonymous terms (§15.3) emits two <dt> in HTML.
    dl = DefinitionList(
        entries=[
            DefinitionEntry(
                terms=["HTTP", "HyperText Transfer Protocol"],
                definitions=["A protocol"],
            )
        ]
    )
    studio = _studio(definition=dl, target_format="html")
    rendered = studio._render()
    assert "<dt>HTTP</dt>" in rendered
    assert "<dt>HyperText Transfer Protocol</dt>" in rendered
    assert "<dd>A protocol</dd>" in rendered


def test_multiple_definitions_render_as_multiple_dd() -> None:
    # One entry with two definitions (§15.4) emits two <dd> in HTML.
    dl = DefinitionList(
        entries=[
            DefinitionEntry(
                terms=["bank"],
                definitions=["A financial institution", "The side of a river"],
            )
        ]
    )
    studio = _studio(definition=dl, target_format="html")
    rendered = studio._render()
    assert "<dd>A financial institution</dd>" in rendered
    assert "<dd>The side of a river</dd>" in rendered


def test_lossless_flat_to_definition_conversion_carries_content() -> None:
    studio = _studio(flat=FlatList(items=[ListItem("HTTP: A protocol")]))
    assert studio._convert_across_boundary(ListType.DEFINITION) is True
    entry = studio._definition.entries[0]
    assert entry.primary_term == "HTTP"
    assert entry.primary_definition == "A protocol"


def test_lossy_conversion_blocked_when_declined() -> None:
    studio = _studio(
        flat=FlatList(list_type=ListType.CHECKLIST, items=[ListItem("a", checked=True)])
    )
    asked: list[list[str]] = []
    studio._confirm_conversion = lambda reasons: asked.append(reasons) or False
    assert studio._convert_across_boundary(ListType.DEFINITION) is False
    assert asked and asked[0]  # the user was warned with reasons
    assert studio._definition.entries[0].is_blank()  # original model untouched


def test_lossy_conversion_proceeds_when_approved() -> None:
    studio = _studio(
        flat=FlatList(list_type=ListType.CHECKLIST, items=[ListItem("a", checked=True)])
    )
    studio._confirm_conversion = lambda _reasons: True
    assert studio._convert_across_boundary(ListType.DEFINITION) is True
    assert studio._definition.entries[0].primary_term == "a"


def test_approve_loss_without_hook_proceeds() -> None:
    studio = _studio(flat=FlatList(items=[ListItem("x")]))
    assert studio._approve_loss(["dropped something"]) is True


def test_validation_issues_clean_for_a_normal_list() -> None:
    studio = _studio(flat=FlatList(items=[ListItem("apples"), ListItem("oranges")]))
    studio.result_source = studio._render()
    assert studio.validation_issues() == []


def test_validation_issues_flags_injected_markup() -> None:
    studio = _studio(flat=FlatList(items=[ListItem("intro\n- sneaky")]))
    studio.result_source = studio._render()
    issues = studio.validation_issues()
    assert issues and "round-trip" in issues[0]
