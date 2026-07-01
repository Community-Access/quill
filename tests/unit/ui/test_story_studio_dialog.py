"""Seam tests for StoryStudioDialog that need no live wx control tree.

Like the List Studio tests, these guard the wx-free logic — how a binder node
maps to an "open this file at this offset" action and when activation should
close the binder — so a regression is caught without a wx display. The TreeCtrl
population and key handling are exercised by hand with a screen reader.
"""

from __future__ import annotations

from quill.core.story.binder import BinderNode
from quill.core.story.model import ElementKind, StoryProject, new_element
from quill.ui.story_studio_dialog import StoryStudioDialog


def _studio(
    project: StoryProject, files: dict[str, str] | None = None, on_open=None, on_edit_details=None
):
    files = files or {}
    return StoryStudioDialog(
        wx=object(),
        project=project,
        read_text=lambda p: files.get(p, ""),
        on_open=on_open,
        on_edit_details=on_edit_details,
    )


def _element_node(root):
    characters = next(c for c in root.children if c.label == "Characters")
    return characters.children[0]


def test_edit_details_on_element_invokes_callback_with_path_and_kind() -> None:
    calls: list[tuple[str, str]] = []
    project = StoryProject(
        title="B",
        elements=(new_element(ElementKind.CHARACTER, "Elena", "characters/elena.md"),),
    )
    studio = _studio(project, on_edit_details=lambda path, kind: calls.append((path, kind)))
    node = _element_node(studio.root_node)
    assert studio.edit_details(node) is True
    assert calls == [("characters/elena.md", "character")]


def test_edit_details_on_group_returns_false() -> None:
    calls: list[object] = []
    studio = _studio(StoryProject(title="B"), on_edit_details=lambda *a: calls.append(a))
    assert studio.edit_details(BinderNode("Manuscript", "group")) is False
    assert calls == []


def test_root_node_reflects_the_project() -> None:
    project = StoryProject(
        title="My Book",
        elements=(new_element(ElementKind.CHARACTER, "Elena", "characters/elena.md"),),
    )
    studio = _studio(project)
    assert studio.root_node.label == "My Book"
    assert [c.label for c in studio.root_node.children] == ["Manuscript", "Characters"]


def test_open_target_for_each_node_type() -> None:
    studio = _studio(StoryProject(title="B"))
    assert studio.open_target(BinderNode("Manuscript", "group")) is None
    assert studio.open_target(BinderNode("B", "root")) is None
    assert studio.open_target(BinderNode("m.md", "manuscript", path="m.md")) == ("m.md", None)
    assert studio.open_target(
        BinderNode("Elena", "element", path="characters/e.md", element_id="x")
    ) == ("characters/e.md", None)
    assert studio.open_target(
        BinderNode("Chapter 1", "heading", path="m.md", offset=42, level=2)
    ) == ("m.md", 42)


def test_activate_opens_a_file_node_and_signals_close() -> None:
    opened: list[tuple[str, int | None]] = []
    studio = _studio(
        StoryProject(title="B", manuscript=("m.md",)),
        on_open=lambda path, offset: opened.append((path, offset)),
    )
    node = BinderNode("Chapter 1", "heading", path="m.md", offset=10, level=1)
    assert studio.activate(node) is True
    assert opened == [("m.md", 10)]


def test_activate_group_does_nothing_and_keeps_dialog_open() -> None:
    opened: list[object] = []
    studio = _studio(StoryProject(title="B"), on_open=lambda *a: opened.append(a))
    assert studio.activate(BinderNode("Manuscript", "group")) is False
    assert opened == []
