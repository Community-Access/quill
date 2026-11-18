"""New Star List, Star Lists... and Rename or Delete Star List (GitHub PRD 14.2)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_star_lists import GitHubWorkbenchStarListsMixin
from tests.unit.core.github_workbench.test_star_lists import FakeApi

ROW = ExploreRow("Screen readers: o/r", "", "", "o/r", "repo", "o/r")


class _Dialog:
    selected: list[int] = []
    answer = 5100  # wx.ID_OK

    def __init__(self, *_a: Any) -> None:
        self.preset: list[int] = []

    def __enter__(self) -> _Dialog:
        return self

    def __exit__(self, *_a: Any) -> None:
        return None

    def SetSelections(self, chosen: list[int]) -> None:  # noqa: N802 - wx's name
        self.preset[:] = chosen
        _Dialog.preset_seen = list(chosen)

    def GetSelections(self) -> list[int]:  # noqa: N802 - wx's name
        return _Dialog.selected


class _Window(GitHubWorkbenchStarListsMixin):
    signed_in = True

    def __init__(self, *, picks: list[int] | None = None, texts: list[str] | None = None) -> None:
        self.api = FakeApi()
        self.picks, self.texts = list(picks or []), list(texts or [])
        self.said: list[str] = []
        wx = SimpleNamespace(MultiChoiceDialog=_Dialog, ID_OK=5100)
        self.frame = SimpleNamespace(
            frame=None,
            _wx=wx,
            current=SimpleNamespace(key="star_lists"),
            reload=lambda: self.said.append("(reloaded)"),
        )

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, *_a: Any) -> int:
        return self.picks.pop(0)

    def _confirm(self, *_a: Any) -> bool:
        return True

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return self.texts.pop(0)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_registered_and_where_each_fits() -> None:
    assert {"new_star_list", "star_lists", "edit_star_list"} <= set(DEVELOPMENT_VERBS)
    window = _Window()
    assert window._fits_new_star_list(None) and window._fits_edit_star_list(ROW)
    window.frame.current = SimpleNamespace(key="starred")
    assert window._fits_star_lists(ROW) and not window._fits_edit_star_list(ROW)


def test_new_star_list_asks_name_description_and_who_sees_it() -> None:
    window = _Window(picks=[0], texts=["Reading", ""])
    window._do_new_star_list(None, None)
    assert window.said == ["Made the private star list Reading.", "(reloaded)"]


def test_star_lists_checks_the_ones_it_is_on_and_sends_the_choice(monkeypatch: Any) -> None:
    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", lambda *_a: 5100)
    _Dialog.selected = [1]
    window = _Window()
    window._do_star_lists(None, ROW)
    assert _Dialog.preset_seen == [0]
    assert window.api.sent[-1][1] == {"itemId": "R_9", "listIds": ["UL_2"]}
    assert window.said[0] == "o/r is now on: Tools I use."


def test_rename_or_delete_works_on_the_rows_list() -> None:
    window = _Window(picks=[3])
    window._do_edit_star_list(None, ROW)
    assert window.api.sent[-1][1] == {"listId": "UL_1"}
    window = _Window(picks=[1])
    window._do_edit_star_list(None, ROW)
    assert window.api.sent[-1][1]["isPrivate"] is True
