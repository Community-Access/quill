from __future__ import annotations

from quill.core.story.model import ElementKind, StoryElement, StoryProject, new_element


def test_new_element_mints_a_nonempty_id() -> None:
    a = new_element(ElementKind.CHARACTER, "Elena", "characters/elena.md")
    b = new_element(ElementKind.CHARACTER, "Elena", "characters/elena.md")
    assert a.id and b.id and a.id != b.id
    assert a.kind is ElementKind.CHARACTER
    assert a.title == "Elena"
    assert a.path == "characters/elena.md"
    assert a.tags == ()


def test_element_round_trips_through_dict() -> None:
    element = StoryElement(
        id="x1",
        kind=ElementKind.PLOT,
        title="The Betrayal",
        path="plots/betrayal.md",
        tags=("act-one", "pov"),
    )
    assert StoryElement.from_dict(element.to_dict()) == element


def test_element_from_dict_defaults_missing_tags_and_unknown_kind() -> None:
    element = StoryElement.from_dict({"id": "y", "title": "Mystery", "path": "a.md"})
    assert element.tags == ()
    # An unrecognized/absent kind falls back to RESEARCH rather than raising.
    assert element.kind is ElementKind.RESEARCH


def test_project_round_trips_through_dict() -> None:
    project = StoryProject(
        title="The Novel",
        manuscript=("manuscript.md", "epilogue.md"),
        elements=(
            new_element(ElementKind.CHARACTER, "Elena", "characters/elena.md"),
            new_element(ElementKind.LOCATION, "Old Harbor", "places/harbor.md"),
        ),
    )
    restored = StoryProject.from_dict(project.to_dict())
    assert restored == project


def test_project_to_dict_stamps_schema_version() -> None:
    data = StoryProject(title="T").to_dict()
    assert data["schema_version"] == StoryProject.SCHEMA_VERSION
    assert data["title"] == "T"


def test_project_from_dict_tolerates_garbage_and_keeps_good_elements() -> None:
    data = {
        "title": "T",
        "manuscript": ["a.md", 5, "b.md"],  # non-str dropped
        "elements": [
            {"id": "ok", "kind": "character", "title": "Good", "path": "g.md"},
            "not-a-dict",  # dropped
            {"kind": "location"},  # missing id/title/path -> dropped
        ],
    }
    project = StoryProject.from_dict(data)
    assert project.manuscript == ("a.md", "b.md")
    assert [e.id for e in project.elements] == ["ok"]


def test_project_from_dict_empty_is_all_defaults() -> None:
    project = StoryProject.from_dict({})
    assert project.title == "Untitled Project"
    assert project.manuscript == ()
    assert project.elements == ()
