"""Search YouTube...: the menu row, the palette entry and the in-tree search."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.radio.federated_browse import FederatedBrowse
from quill.ui.radio import youtube_search_ui


class _Tasks:
    def submit(self, name, work, *, on_success=None, on_failure=None):
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            on_failure(name, error)
            return
        on_success(name, result)


def _dialog():
    said: list[str] = []
    return SimpleNamespace(
        _safe_mode=False,
        _task_manager=_Tasks(),
        _announce=said.append,
        _tree=object(),
        said=said,
    ), said


def test_the_keys_are_in_the_radio_keymap_and_free_on_the_bar() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.keymap_query import canonical_binding

    radio = APP_KEYMAPS["radio"]
    assert radio["radio.search_youtube"] == "Ctrl+Shift+6"
    assert radio["radio.youtube_comments"] == "Ctrl+Shift+7"
    mine = {canonical_binding("Ctrl+Shift+6"), canonical_binding("Ctrl+Shift+7")}
    others = [
        canonical_binding(key)
        for command, key in radio.items()
        if key and command not in ("radio.search_youtube", "radio.youtube_comments")
    ]
    assert not mine & set(others)


def test_both_commands_reach_the_palette() -> None:
    from quill.ui.radio import palette_commands

    registered: dict[str, tuple] = {}

    def _register(cid, title, handler, *args, **kwargs):
        registered.setdefault(cid, (title, handler))

    class _Host:
        commands = SimpleNamespace(try_register=_register, register=_register)

        def __getattr__(self, name):
            return lambda *a, **k: ""

    palette_commands.register_radio_commands(_Host())
    assert registered["radio.search_youtube"][0] == "Internet Radio: Search YouTube..."
    assert registered["radio.youtube_comments"][0] == "Internet Radio: Read YouTube Comments..."


def test_the_search_runs_off_thread_and_shows_rows_once(monkeypatch) -> None:
    from quill.core.radio import youtube_search
    from quill.ui.radio import browse_feedback, browse_search_all

    found = FederatedBrowse(counts={"Video": 1})
    shown: list = []
    monkeypatch.setattr(youtube_search, "search", lambda text, safe_mode=False: found)
    monkeypatch.setattr(browse_search_all, "show_results", lambda d, q, f: shown.append((q, f)))
    monkeypatch.setattr(browse_feedback, "start_search_notice", lambda *a: None)
    monkeypatch.setattr(browse_feedback, "stop_search_notice", lambda *a: None)
    dialog, said = _dialog()
    youtube_search_ui.run_in_tree(dialog, "bristol walk")
    assert shown == [("bristol walk", found)]
    assert said == ["Searching YouTube for bristol walk..."]


def test_a_failed_search_is_said_and_recorded(monkeypatch, quill_data_dir) -> None:
    from quill.core import problem_log
    from quill.core.radio import youtube_search
    from quill.core.radio.youtube_requests import YouTubeRequestError
    from quill.ui.radio import browse_feedback

    def broken(text, safe_mode=False):
        raise YouTubeRequestError(
            "YouTube could not be reached. Check your connection and try again."
        )

    monkeypatch.setattr(youtube_search, "search", broken)
    monkeypatch.setattr(browse_feedback, "start_search_notice", lambda *a: None)
    monkeypatch.setattr(browse_feedback, "stop_search_notice", lambda *a: None)
    dialog, said = _dialog()
    youtube_search_ui.run_in_tree(dialog, "bristol")
    assert said[-1].startswith("YouTube could not be searched. YouTube could not be reached.")
    problems = problem_log.load_problems(quill_data_dir)
    assert problems and problems[-1].subject == "Search YouTube for bristol"


def test_safe_mode_says_so_and_searches_nothing() -> None:
    dialog, said = _dialog()
    dialog._safe_mode = True
    youtube_search_ui.run_in_tree(dialog, "x")
    assert said == ["YouTube is not available in Safe Mode."]


def test_without_a_browse_tree_it_opens_search_stations_on_youtube() -> None:
    opened: list[dict] = []
    host = SimpleNamespace(
        _safe_mode=False,
        _windows=None,
        _announce=lambda m: None,
        open_internet_radio=lambda **kw: opened.append(kw),
    )
    youtube_search_ui.search_youtube(host)
    assert opened == [{"focus_search": True, "source_facet": "YouTube"}]


def test_the_youtube_branch_row_is_a_known_action() -> None:
    from quill.ui.radio import browse_actions

    assert browse_actions.is_action_id("searchyoutube")
