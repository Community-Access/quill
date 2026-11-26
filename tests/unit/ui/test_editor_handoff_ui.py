"""FUX-02: show notes and transcripts reach QUILL as a document, said once."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.ui import editor_handoff, scribe_app_host


@pytest.fixture
def editor(monkeypatch):
    """QUILL installed; records what it was asked to open, and at which line."""
    opened: list[tuple[str, int | None]] = []
    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: "QUILL")
    monkeypatch.setattr(
        scribe_app_host,
        "open_in_editor",
        lambda path, line=None: opened.append((Path(path).name, line)) or "QUILL",
    )
    return opened


def test_saved_then_opened_at_the_line_said_once_before_quill_comes_forward(
    tmp_path: Path, editor
) -> None:
    said: list[str] = []
    order: list[str] = []
    editor_handoff.hand_to_editor(
        "# Doc\n",
        filename="Show - Ep.md",
        kind="the transcript",
        source_app="QUILL Cast",
        announce=lambda m: (said.append(m), order.append("said")),
        line=7,
        folder=tmp_path / "QUILL Cast",
    )
    assert (tmp_path / "QUILL Cast" / "Show - Ep.md").read_text(encoding="utf-8") == "# Doc\n"
    assert said == ["Saved in Documents, in the QUILL Cast folder. Opening it in QUILL."]
    assert editor == [("Show - Ep.md", 7)]


def test_sending_again_reopens_the_copy_and_says_so(tmp_path: Path, editor) -> None:
    (tmp_path / "Show - Ep.md").write_text("# Doc\n", encoding="utf-8")
    said: list[str] = []
    editor_handoff.hand_to_editor(
        "# Doc\n",
        filename="Show - Ep.md",
        kind="the transcript",
        source_app="QUILL Cast",
        announce=said.append,
        folder=tmp_path,
    )
    assert (
        said[0]
        == f"Already saved in Documents, in the {tmp_path.name} folder. Opening it in QUILL."
    )
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Show - Ep.md"]


def test_no_editor_keeps_the_document_and_says_where(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: "")
    launched: list[object] = []
    monkeypatch.setattr(scribe_app_host, "open_in_editor", lambda *a, **k: launched.append(a))
    said: list[str] = []
    path = editor_handoff.hand_to_editor(
        "notes",
        filename="n.md",
        kind="the show notes",
        source_app="QUILL Cast",
        announce=said.append,
        folder=tmp_path,
    )
    assert path is not None and path.read_text(encoding="utf-8") == "notes"
    assert launched == []
    assert said == [
        f"Saved the show notes as n.md in Documents, in the {tmp_path.name} folder. "
        "QUILL is not installed with this copy, so it was not opened."
    ]


def test_a_folder_that_cannot_be_written_says_so(tmp_path: Path, editor) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    said: list[str] = []
    result = editor_handoff.hand_to_editor(
        "x",
        filename="n.md",
        kind="the show notes",
        source_app="QUILL Cast",
        announce=said.append,
        folder=blocker / "inside",
    )
    assert result is None and editor == []
    assert said[0].startswith("Could not save the show notes in Documents, in the inside folder:")


def test_inside_quill_it_opens_as_a_new_document_and_saves_nothing(tmp_path: Path) -> None:
    opened: list[str] = []
    editor_handoff.send_text(
        "Guests",
        source_app="QUILL",
        announce=lambda _m: None,
        title="Thursday",
        show="The Daily",
        open_here=lambda document, _line: opened.append(document),
    )
    assert opened and opened[0].startswith("# Thursday\n\n*The Daily*\n\nShow notes, from QUILL.")
