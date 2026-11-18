"""A Project's row in the GitHub Workbench: its own care, asked and said."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import project_admin as pa
from quill.core.github.explore_models import ExploreRow
from quill.ui.github_workbench_project_admin import (
    PROJECT_ADMIN_VERBS,
    GitHubWorkbenchProjectAdminMixin,
)

ROW = ExploreRow("Roadmap (#3)", "A board.", "https://x/p/3", "o/r", "project", "P_3")


class _Host(GitHubWorkbenchProjectAdminMixin):
    def __init__(self, answers: list[Any]) -> None:
        self.answers = answers
        self.said: list[str] = []
        self.signed_in = True
        self.items = type("Items", (), {"token": "t"})()
        self.frame = type("Frame", (), {"reload": lambda self: None})()
        self._say = self.said.append  # type: ignore[assignment]
        self._background = lambda _what, work, done: done(work())  # type: ignore[assignment]
        self._ask_text = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._choose = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._confirm = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]


def test_every_verb_is_for_a_project_row_and_fits_only_signed_in() -> None:
    host = _Host([])
    assert all(kinds == frozenset({"project"}) for kinds in PROJECT_ADMIN_VERBS.values())
    assert host._fits_project_delete(ROW)
    host.signed_in = False
    assert not host._fits_project_delete(ROW)
    assert not _Host([])._fits_project_draft(ExploreRow("x", "y", kind="issue", key="1"))


def test_delete_needs_the_title_typed_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[str] = []
    monkeypatch.setattr(pa, "delete_project", lambda _t, pid: deleted.append(pid))
    host = _Host(["roadmap"])
    host._do_project_delete(None, ROW)
    assert deleted == [] and host.said[-1].startswith("That is not the project's title")
    host = _Host(["Roadmap"])
    host._do_project_delete(None, ROW)
    assert deleted == ["P_3"] and host.said[-1] == "Roadmap deleted."


def test_a_single_select_field_asks_for_its_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    made: list[tuple[str, str, list[str]]] = []
    monkeypatch.setattr(
        pa,
        "create_field",
        lambda _t, _p, name, code, options: made.append((name, code, options)) or name,
    )
    host = _Host(["Size", 3, "S, M, L"])
    host._do_project_field(None, ROW)
    assert made == [("Size", "SINGLE_SELECT", ["S", "M", "L"])]
    assert host.said[-1] == "Field Size added to Roadmap."
