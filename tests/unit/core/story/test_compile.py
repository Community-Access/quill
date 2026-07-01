from __future__ import annotations

from quill.core.story.compile import compile_manuscript
from quill.core.story.model import StoryProject


def _reader(files: dict[str, str]):
    return lambda path: files.get(path, "")


def test_concatenates_manuscript_files_in_order() -> None:
    project = StoryProject(title="B", manuscript=("one.md", "two.md"))
    out = compile_manuscript(
        project, _reader({"one.md": "# One\n\nAlpha.", "two.md": "# Two\n\nBeta."})
    )
    assert out == "# One\n\nAlpha.\n\n# Two\n\nBeta."


def test_strips_front_matter_from_each_file() -> None:
    project = StoryProject(title="B", manuscript=("ch.md",))
    out = compile_manuscript(
        project, _reader({"ch.md": "---\ntype: scene\n---\n# Chapter\n\nProse."})
    )
    assert out == "# Chapter\n\nProse."


def test_empty_manuscript_compiles_to_empty_string() -> None:
    assert compile_manuscript(StoryProject(title="B"), _reader({})) == ""


def test_custom_separator_is_used() -> None:
    project = StoryProject(title="B", manuscript=("a.md", "b.md"))
    out = compile_manuscript(project, _reader({"a.md": "A", "b.md": "B"}), separator="\n\n---\n\n")
    assert out == "A\n\n---\n\nB"
