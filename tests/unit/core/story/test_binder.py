from __future__ import annotations

from quill.core.story.binder import build_binder
from quill.core.story.model import ElementKind, StoryProject, new_element


def _reader(files: dict[str, str]):
    return lambda path: files.get(path, "")


def test_empty_project_has_only_an_empty_manuscript_group() -> None:
    root = build_binder(StoryProject(title="My Book"), _reader({}))
    assert root.label == "My Book"
    assert root.node_type == "root"
    assert [c.label for c in root.children] == ["Manuscript"]
    assert root.children[0].children == ()


def test_manuscript_headings_nest_by_level() -> None:
    text = "# Part One\n\n## Chapter 1\n\n### Scene A\n\n## Chapter 2\n"
    root = build_binder(
        StoryProject(title="B", manuscript=("manuscript.md",)),
        _reader({"manuscript.md": text}),
    )
    manuscript_group = root.children[0]
    file_node = manuscript_group.children[0]
    assert file_node.node_type == "manuscript"
    assert file_node.path == "manuscript.md"
    part = file_node.children[0]
    assert part.label == "Part One"
    assert [c.label for c in part.children] == ["Chapter 1", "Chapter 2"]
    assert part.children[0].children[0].label == "Scene A"


def test_heading_nodes_carry_level_and_offset() -> None:
    text = "## Chapter 1\n"
    root = build_binder(StoryProject(title="B", manuscript=("m.md",)), _reader({"m.md": text}))
    heading = root.children[0].children[0].children[0]
    assert heading.node_type == "heading"
    assert heading.level == 2
    assert heading.offset == 0
    assert heading.path == "m.md"


def test_elements_group_under_labelled_groups_in_order() -> None:
    project = StoryProject(
        title="B",
        elements=(
            new_element(ElementKind.PLOT, "The Betrayal", "plots/b.md"),
            new_element(ElementKind.CHARACTER, "Elena", "characters/e.md"),
            new_element(ElementKind.LOCATION, "Harbor", "places/h.md"),
        ),
    )
    root = build_binder(project, _reader({}))
    # Manuscript first, then element groups in a fixed reading order; empty
    # groups (Research, Brainstorm) are omitted.
    assert [c.label for c in root.children] == [
        "Manuscript",
        "Characters",
        "Places",
        "Plot threads",
    ]
    characters = next(c for c in root.children if c.label == "Characters")
    elena = characters.children[0]
    assert elena.node_type == "element"
    assert elena.label == "Elena"
    assert elena.path == "characters/e.md"
    assert elena.element_id


def test_a_manuscript_file_with_no_headings_is_a_leaf() -> None:
    root = build_binder(
        StoryProject(title="B", manuscript=("flat.md",)),
        _reader({"flat.md": "Just prose, no headings.\n"}),
    )
    file_node = root.children[0].children[0]
    assert file_node.path == "flat.md"
    assert file_node.children == ()
