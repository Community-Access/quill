from __future__ import annotations

from pathlib import Path

from quill.core.story.model import ElementKind, StoryProject, new_element
from quill.core.story.storage import PROJECT_FILENAME, load_project, save_project


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    project = StoryProject(
        title="The Novel",
        manuscript=("manuscript.md",),
        elements=(new_element(ElementKind.CHARACTER, "Elena", "characters/elena.md"),),
    )
    save_project(tmp_path, project)
    assert (tmp_path / PROJECT_FILENAME).is_file()
    assert load_project(tmp_path) == project


def test_load_without_sidecar_scans_folder_for_manuscript(tmp_path: Path) -> None:
    (tmp_path / "02-two.md").write_text("# Two\n", encoding="utf-8")
    (tmp_path / "01-one.md").write_text("# One\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes\n", encoding="utf-8")
    (tmp_path / "cover.png").write_bytes(b"\x89PNG")
    project = load_project(tmp_path)
    # Sorted by name, text files only, the PNG ignored.
    assert project.manuscript == ("01-one.md", "02-two.md", "notes.txt")
    assert project.title == tmp_path.name
    assert project.elements == ()


def test_load_ignores_the_sidecar_file_itself_when_scanning(tmp_path: Path) -> None:
    # An empty/garbage sidecar still takes the "parse" path, not the scan path.
    (tmp_path / "chapter.md").write_text("# Ch\n", encoding="utf-8")
    save_project(tmp_path, StoryProject(title="Saved", manuscript=("chapter.md",)))
    assert PROJECT_FILENAME not in load_project(tmp_path).manuscript


def test_load_corrupt_sidecar_falls_back_to_defaults(tmp_path: Path) -> None:
    (tmp_path / PROJECT_FILENAME).write_text("{not valid json", encoding="utf-8")
    project = load_project(tmp_path)
    assert isinstance(project, StoryProject)
    assert project.manuscript == ()


def test_saved_paths_are_relative_posix(tmp_path: Path) -> None:
    save_project(tmp_path, StoryProject(title="T", manuscript=("sub/ch1.md",)))
    raw = (tmp_path / PROJECT_FILENAME).read_text(encoding="utf-8")
    assert "sub/ch1.md" in raw
    assert str(tmp_path) not in raw  # no absolute path leaks into the sidecar
