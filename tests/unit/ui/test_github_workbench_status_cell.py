"""QUILL's Workbench status cell: there in the mode, gone out of it, and what it says.

QUILL Lite's cell is tested in
``tests/unit/apps/test_lite_github_tokens_and_readout.py``; both read their words
from :mod:`quill.core.github.workbench_menu`, which is asserted here too.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github import workbench_menu as table
from quill.ui.main_frame_github_status import GitHubWorkbenchStatusCellMixin


class _Bar:
    """StatusBarMixin's two answers, as a stand-in further down the MRO."""

    def _statusbar_items(self) -> list[str]:
        return ["line_column", "word_count", "message"]

    def _statusbar_text_for_item(self, item: str) -> str:
        return f"<{item}>"


class _Frame(GitHubWorkbenchStatusCellMixin, _Bar):
    def __init__(self, repository: str = "") -> None:
        self._github_workbench_mode = False
        self.document = SimpleNamespace(path="C:/work/notes.md")
        self.lookups: list[str] = []
        self.refreshed: list[str] = []
        self._repository = repository

    def _github_items_initial_repo(self) -> str:
        self.lookups.append("lookup")
        return self._repository

    def _refresh_statusbar(self) -> None:
        self.refreshed.append("bar")


def test_the_cell_is_absent_out_of_the_mode() -> None:
    frame = _Frame("community-access/quill")

    assert table.STATUS_CELL_KEY not in frame._statusbar_items()
    assert frame._statusbar_text_for_item(table.STATUS_CELL_KEY) == ""
    assert frame.lookups == []  # no disk read for a cell nobody can see


def test_in_the_mode_it_names_the_repository_before_the_message() -> None:
    frame = _Frame("community-access/quill")
    frame._github_workbench_mode = True

    assert frame._statusbar_items() == ["line_column", "word_count", "workbench", "message"]
    assert frame._statusbar_text_for_item("workbench") == "Workbench: community-access/quill"
    assert frame._statusbar_text_for_item("word_count") == "<word_count>"


def test_with_no_repository_it_reads_workbench_alone() -> None:
    frame = _Frame("")
    frame._github_workbench_mode = True

    assert frame._statusbar_text_for_item("workbench") == "Workbench"


def test_the_repository_is_looked_up_once_per_document_until_the_mode_changes() -> None:
    frame = _Frame("community-access/quill")
    frame._github_workbench_mode = True

    for _ in range(5):
        frame.github_workbench_status_text()
    assert frame.lookups == ["lookup"]

    frame._refresh_github_status_cell()
    frame.github_workbench_status_text()
    assert frame.lookups == ["lookup", "lookup"]
    assert frame.refreshed == ["bar"]


def test_a_cell_the_user_unhid_still_leaves_with_the_mode() -> None:
    class _Unhidden(_Bar):
        def _statusbar_items(self) -> list[str]:
            return ["workbench", "message"]

    class _UnhiddenFrame(GitHubWorkbenchStatusCellMixin, _Unhidden):
        _github_workbench_mode = False

    assert _UnhiddenFrame()._statusbar_items() == ["message"]


def test_switching_the_mode_redraws_the_bar_without_a_word_of_its_own() -> None:
    from quill.ui.main_frame_github_menu import GitHubWorkbenchMenuMixin

    class _Menu(GitHubWorkbenchMenuMixin, _Frame):
        def __init__(self) -> None:
            super().__init__("community-access/quill")
            self.said: list[str] = []

        def _feature_enabled(self, _feature: str) -> bool:
            return True

        def _announce(self, message: str) -> None:
            self.said.append(message)

        def _build_menu(self) -> None:
            pass

    frame = _Menu()
    frame.toggle_github_workbench_mode()
    assert frame.refreshed == ["bar"]
    assert "workbench" in frame._statusbar_items()
    frame.toggle_github_workbench_mode()

    # Only the mode's own two sentences: the cell itself is never announced.
    assert frame.said == [table.ANNOUNCE_ON, table.ANNOUNCE_OFF]
    assert "workbench" not in frame._statusbar_items()


def test_main_frame_wires_the_cell_ahead_of_the_status_bar() -> None:
    from quill.core.settings_normalizers import STATUS_BAR_ITEMS, _default_status_bar_hidden
    from quill.ui.main_frame import MainFrame
    from quill.ui.main_frame_statusbar import StatusBarMixin
    from quill.ui.statusbar_cell_help import STATUS_BAR_CELL_HELP

    mro = MainFrame.__mro__
    assert mro.index(GitHubWorkbenchStatusCellMixin) < mro.index(StatusBarMixin)
    # Its accessible name and its F1 sentence.
    assert MainFrame._STATUS_BAR_LABELS["workbench"] == table.STATUS_CELL_LABEL == "Workbench"
    assert STATUS_BAR_CELL_HELP["workbench"] == table.STATUS_CELL_HELP
    # Listed, so Customize Status Bar knows it, and hidden unless the mode shows it.
    assert "workbench" in STATUS_BAR_ITEMS
    assert "workbench" in _default_status_bar_hidden()


def test_the_words_are_shared() -> None:
    assert table.status_cell_text(" owner/name ") == "Workbench: owner/name"
    assert table.status_cell_text("") == "Workbench"
