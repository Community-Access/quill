"""QUILL Lite's end of the token work and the Workbench status cell (2026-11-08).

The shared halves are tested beside them: the warning in
``tests/unit/ui/test_github_token_expiry_warning.py``, the suggestion in
``tests/unit/ui/test_github_token_nudge.py``, QUILL's cell in
``tests/unit/ui/test_github_workbench_status_cell.py``. This file reaches them
through QUILL Lite's own handlers, and builds QUILL Lite's real cell row.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.apps.lite_status_cells import (
    CELLS,
    SHOWN_ONLY_WITH_TEXT,
    native_cell_labels,
    shared_ai_cells,
    workbench_cell,
)
from quill.core.github import workbench_menu
from quill.ui.github_token_expiry import GITHUB_ACCOUNTS_TARGET

wx = pytest.importorskip("wx")


@pytest.fixture
def in_a_repository(monkeypatch):
    found: list[object] = []

    def detect(path):
        found.append(path)
        return "community-access/quill"

    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", detect)
    return found


# -- the expiry warning's two ends ----------------------------------------- #


def test_the_workbench_gate_starts_the_expiry_watch(lite_window, monkeypatch) -> None:
    watched: list[object] = []
    monkeypatch.setattr("quill.core.github.github_provider.require_pygithub", lambda: None)
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: "ghp_tok")
    monkeypatch.setattr(
        "quill.core.github.items_provider.GitHubItemsProvider",
        lambda *, token=None: SimpleNamespace(token=token),
    )
    monkeypatch.setattr(
        "quill.ui.github_token_expiry.watch_token_expiry",
        lambda host, token: watched.append((host.app_name, token, host.notice_path)),
    )
    win = lite_window("")

    provider = win._github_provider(lambda: None)

    assert provider.token == "ghp_tok"
    [(app, token, path)] = watched
    assert (app, token) == ("QUILL Lite", "ghp_tok")
    assert path is not None and path.name == "notifications.json"  # QUILL Lite's own file


def test_the_notice_opens_manage_github_accounts(lite_window, lite_dialogs, monkeypatch) -> None:
    monkeypatch.setattr("quill.ui.github_accounts_flow.load_github_token", lambda: "")
    monkeypatch.setattr("quill.ui.github_accounts_flow.list_github_accounts", lambda: [])
    monkeypatch.setattr("quill.ui.github_accounts_flow.active_github_account_id", lambda: None)
    win = lite_window("")

    win.open_notification_target(GITHUB_ACCOUNTS_TARGET)

    assert lite_dialogs.names() == ["GitHubManageAccountsDialog"]


# -- the Workbench cell ---------------------------------------------------- #


def test_the_cell_is_empty_out_of_the_mode_and_names_the_repository_in_it(
    lite_window, in_a_repository
) -> None:
    win = lite_window("")
    assert workbench_cell(win) == ""
    assert shared_ai_cells(win)["workbench"] == ""

    win.cmd_toggle_github_workbench()
    assert workbench_cell(win) == "Workbench: community-access/quill"

    win.cmd_toggle_github_workbench()
    assert workbench_cell(win) == ""
    # Only the mode's own sentences: the cell is never announced (GATE-13).
    assert win.announcements == [workbench_menu.ANNOUNCE_ON, workbench_menu.ANNOUNCE_OFF]


def test_with_no_repository_it_reads_workbench_alone(lite_window, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", lambda _p: "")
    win = lite_window("")
    win.cmd_toggle_github_workbench()

    assert workbench_cell(win) == "Workbench"


def test_the_repository_is_read_once_per_document_while_the_mode_is_on(
    lite_window, in_a_repository
) -> None:
    win = lite_window("")
    win.cmd_toggle_github_workbench()
    for _ in range(4):
        win.github_workbench_status_text()

    assert len(in_a_repository) == 1


def test_the_cell_is_catalogued_like_the_others() -> None:
    cell = next(cell for cell in CELLS if cell.key == "workbench")
    assert cell.label == "Workbench"  # its accessible name
    assert cell.help_text == workbench_menu.STATUS_CELL_HELP  # what F1 says
    assert "workbench" in SHOWN_ONLY_WITH_TEXT
    # The native bar reads it as it is: the text already names itself.
    labels = native_cell_labels({"workbench": "Workbench: o/n", "message": "Ready"})
    assert labels == ["Workbench: o/n"]


def test_the_real_row_shows_the_cell_only_in_the_mode(wx_session_app, in_a_repository) -> None:
    from quill.apps.lite_github_workbench import GitHubWorkbenchLiteMixin
    from quill.apps.lite_window_status import DocumentStatusMixin
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # without one, SetHelpText stores nothing

    class _Window(wx.Frame, DocumentStatusMixin, GitHubWorkbenchLiteMixin):
        app = SimpleNamespace(settings=SimpleNamespace(show_status_bar=True))
        path = "C:/work/notes.md"

        def __init__(self) -> None:
            super().__init__(None, size=(900, 300))
            self.said: list[str] = []
            self._init_status_bar()

        def _announce(self, message: str) -> None:
            self.said.append(message)

        def _cell_values(self) -> dict[str, str]:
            return {**shared_ai_cells(self), "message": "Ready"}

        def fill(self) -> None:
            self._status_dirty = True
            self._refresh_status()

    window = _Window()
    try:
        button = window._status_buttons["workbench"]
        assert button.GetName() == "Workbench"
        assert button.GetHelpText() == workbench_menu.STATUS_CELL_HELP
        window.fill()
        assert not button.IsShown()

        window.cmd_toggle_github_workbench()
        window.fill()
        assert button.IsShown()
        assert button.GetLabel() == "Workbench: community-access/quill"

        window.cmd_toggle_github_workbench()
        window.fill()
        assert not button.IsShown()
        assert window.said == [workbench_menu.ANNOUNCE_ON, workbench_menu.ANNOUNCE_OFF]
    finally:
        window._stop_status_timer()
        window.Destroy()
