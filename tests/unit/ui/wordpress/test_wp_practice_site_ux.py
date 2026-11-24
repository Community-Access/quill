"""The Practice Site, as Jeff found it on 2026-11-23, and the changes he agreed.

The defect: Start left the Practice Site list's Running row on "no" until
Connect, because only connecting refreshed that list (and Stop had the same
gap the other way). Now the list follows the server -- started, ready,
stopped, failed, exited on its own -- in place (FUX-06).

The changes: Start connects it; the first connection asks, defaulting to No,
whether to make it the default site; its commands are on the context menu of
everything that is the Practice Site; lists of sites name it as being on this
computer. No real Playground starts here: the process is a fake.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import sites as st  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS  # noqa: E402
from quill.core.wordpress.workbench_practice import (  # noqa: E402
    PracticeTools,
    listed_name,
    practice_dir,
    site_url,
)
from quill.core.wordpress.workbench_practice_actions import (  # noqa: E402
    PRACTICE_NODE_KIND,
    PRACTICE_ROW_KIND,
    PRACTICE_SITE_KIND,
    PRACTICE_SITE_NODE_KIND,
    PRACTICE_SUB,
    command,
)
from quill.core.wordpress.workbench_window_menu import WINDOW_MENU, WORDPRESS_KEYS  # noqa: E402
from quill.core.workbench.list_place import changed_cells  # noqa: E402
from quill.core.workbench.menus import problems  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_practice_run as run  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402

PRACTICE_NODE = NodeRef("", "practice")
REAL = st.SiteProfile("r1", "Radio Club", "https://radio.example.org", "jeff")


class _Commands:
    def __init__(self, store: st.SiteStore) -> None:
        self.store = store

    def sites(self) -> st.SiteStore:
        return self.store


class _Process:
    """A Practice Site server: running until told otherwise."""

    def __init__(self) -> None:
        self.code: int | None = None

    def poll(self) -> int | None:
        return self.code


class _Window:
    def __init__(self, *, active: bool = True) -> None:
        self.active = active
        self.bound: list[Any] = []

    def IsActive(self) -> bool:  # noqa: N802 - wx's name
        return self.active

    def Bind(self, _event: Any, handler: Any) -> None:  # noqa: N802 - wx's name
        self.bound.append(handler)

    def Unbind(self, _event: Any, handler: Any = None) -> None:  # noqa: N802 - wx's name
        self.bound.remove(handler)


class _Frame:
    """The Workbench window, as far as the Practice Site touches it."""

    def __init__(self, current: NodeRef | None = PRACTICE_NODE) -> None:
        self.current = current
        self.frame = _Window()
        self.reloads = 0
        self.rebuilds = 0

    def reload(self, **_kw: Any) -> None:
        self.reloads += 1

    def rebuild_tree(self) -> None:
        self.rebuilds += 1


def _provider(tmp_path: Path, monkeypatch, sites: list[st.SiteProfile], default_id: str = ""):
    store = st.SiteStore(list(sites), default_id)
    said: list[str] = []
    made = WordPressWorkbenchProvider(_Commands(store), announce=said.append, data_dir=tmp_path)
    made.said = said  # type: ignore[attr-defined]
    made.store = store  # type: ignore[attr-defined]
    made.frame = _Frame()  # type: ignore[assignment]
    monkeypatch.setattr(made, "background", lambda _name, work, done: done(work()))
    monkeypatch.setattr(made, "say", said.append)
    monkeypatch.setattr(made, "_watch", lambda _process: None)
    monkeypatch.setattr(st, "save_secret", lambda _id, _secret: None)
    monkeypatch.setattr(st, "forget_secret", lambda _id: None)
    return made


def _tools() -> PracticeTools:
    return PracticeTools(Path("node.exe"), Path("cli.js"))


def _fake_server(monkeypatch, provider, *, password: bool = True, fail: str = "") -> _Process:
    """start_process and wait_for_site, faked: the site answers, and leaves its password."""
    process = _Process()
    folder = practice_dir(provider._base())

    def wait(_process: Any, _folder: Path) -> None:
        if fail:
            raise RuntimeError(fail)
        if password:
            handoff = folder / "handoff"
            handoff.mkdir(parents=True, exist_ok=True)
            (handoff / "quill-practice-password.json").write_text(
                '{"username": "admin", "password": "abcd efgh"}', encoding="utf-8"
            )

    monkeypatch.setattr(run, "start_process", lambda _tools, _folder: process)
    monkeypatch.setattr(run, "wait_for_site", wait)
    monkeypatch.setattr(run, "stop_process", lambda p: setattr(p, "code", 1))
    return process


def _running_row(provider) -> str:
    rows = provider.practice_rows()
    return next(r.cells["value"] for r in rows if r.cells["fact"] == "Running")


@pytest.fixture
def confirm(monkeypatch) -> dict[str, Any]:
    seen: dict[str, Any] = {"answer": False, "asked": []}

    def ask(_parent, _show, **kw) -> bool:
        seen["asked"].append(kw)
        return bool(seen["answer"])

    monkeypatch.setattr(dlg, "confirm", ask)
    return seen


# -- the defect: the list follows the server ------------------------------------------


def test_starting_refreshes_the_practice_list_without_connect(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    provider = _provider(tmp_path, monkeypatch, [REAL], "r1")
    _fake_server(monkeypatch, provider)
    assert _running_row(provider) == "no"
    before = provider.frame.reloads
    provider.practice_start(_tools(), practice_dir(provider._base()))
    assert provider.frame.reloads > before  # the list was refreshed, not left saying "no"
    assert _running_row(provider) == f"yes, at {site_url()}"


def test_the_list_says_starting_until_the_site_answers(tmp_path, monkeypatch) -> None:
    provider = _provider(tmp_path, monkeypatch, [])
    provider._practice = _Process()
    assert _running_row(provider) == "starting"
    provider._practice_ready = provider._practice
    assert _running_row(provider).startswith("yes, at ")


def test_stop_refreshes_the_list_and_says_so_once(tmp_path, monkeypatch) -> None:
    provider = _provider(tmp_path, monkeypatch, [])
    process = _fake_server(monkeypatch, provider)
    provider._practice = provider._practice_ready = process
    provider.do_practice_stop(None, None)
    assert provider.frame.reloads == 1
    assert provider.said == [run.STOPPED]
    assert _running_row(provider) == "no"


def test_a_failed_start_refreshes_and_says_why(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    provider = _provider(tmp_path, monkeypatch, [])
    _fake_server(
        monkeypatch, provider, fail="The Practice Site stopped before WordPress was ready."
    )
    provider.practice_start(_tools(), practice_dir(provider._base()))
    assert provider.said[-1] == "The Practice Site stopped before WordPress was ready."
    assert provider.frame.reloads >= 2  # starting, then stopped
    assert provider._practice is None and _running_row(provider) == "no"


def test_exiting_on_its_own_is_said_once_and_refreshes(tmp_path, monkeypatch) -> None:
    provider = _provider(tmp_path, monkeypatch, [])
    process = _fake_server(monkeypatch, provider)
    provider._practice = provider._practice_ready = process
    provider.practice_tick()
    assert provider.said == []  # still running: nothing to say
    process.code = 3
    provider.practice_tick()
    provider.practice_tick()
    assert provider.said == [run.EXITED]
    assert provider.frame.reloads == 1 and provider._practice is None


def test_another_list_is_left_alone(tmp_path, monkeypatch) -> None:
    provider = _provider(tmp_path, monkeypatch, [])
    provider.frame.current = NodeRef("", "calendar")
    provider._practice = _fake_server(monkeypatch, provider)
    provider.do_practice_stop(None, None)
    assert provider.frame.reloads == 0


def test_a_refresh_with_one_changed_value_changes_only_that_cell() -> None:
    before = [["Node.js", "C:\\node.exe"], ["Running", "no"]]
    after = [["Node.js", "C:\\node.exe"], ["Running", "yes, at http://127.0.0.1:9400"]]
    assert changed_cells(before, after) == [(1, 1, "yes, at http://127.0.0.1:9400")]
    assert changed_cells(before, before) == []
    assert changed_cells(before, after[:1]) is None  # a row went: fill it again
    assert changed_cells(before, [["Node", "x"], after[1]]) is None  # another row


def test_the_frame_sets_changed_cells_in_place_and_keeps_focus() -> None:
    from quill.ui.workbench_frame_groups import WorkbenchGroupsMixin

    class _List:
        def __init__(self) -> None:
            self.set: list[tuple[int, int, str]] = []

        def GetItemCount(self) -> int:  # noqa: N802 - wx's name
            return 2

        def SetItem(self, row: int, column: int, text: str) -> None:  # noqa: N802
            self.set.append((row, column, text))

    frame = WorkbenchGroupsMixin()
    frame.list = _List()
    frame.rows = ["a", "b"]
    frame._shown_cells = [["Node.js", "x"], ["Running", "no"]]
    assert frame.update_in_place(["a", "b"], [["Node.js", "x"], ["Running", "starting"]])
    assert frame.list.set == [(1, 1, "starting")]  # one cell; nothing selected or focused


# -- Start connects it, and the default is offered once ---------------------------------


def test_start_connects_it_so_new_page_finds_it(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    provider = _provider(tmp_path, monkeypatch, [REAL], "r1")
    _fake_server(monkeypatch, provider)
    provider.practice_start(_tools(), practice_dir(provider._base()))
    practice = provider.practice_profile()
    assert practice is not None and practice.site_url == site_url()
    assert st.load_sites(tmp_path).get(practice.id) is not None  # saved, so New Page lists it
    assert provider.said == [run.STARTING, run.RUNNING_AND_CONNECTED]  # said once
    assert provider.store.default_id == "r1"  # No, the default answer, keeps it


def test_the_default_question_is_asked_at_start_not_minutes_later(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    provider = _provider(tmp_path, monkeypatch, [REAL], "r1")
    _fake_server(monkeypatch, provider)
    order: list[str] = []
    monkeypatch.setattr(
        provider, "background", lambda _name, work, done: (order.append("work"), done(work()))
    )
    asking = run.dlg.confirm

    def ask(*args, **kw):
        order.append("asked")
        return asking(*args, **kw)

    monkeypatch.setattr(run.dlg, "confirm", ask)
    provider.practice_start(_tools(), practice_dir(provider._base()))
    assert order[:2] == ["asked", "work"]  # before the background start, never after it
    (asked,) = confirm["asked"]
    assert asked["title"] == run.DEFAULT_TITLE == "Default Site"
    assert asked["message"] == run.default_question("Radio Club")
    assert asked["yes_label"] == "Make It My Default" and asked["no_label"] == "No"


def test_yes_makes_it_the_default_when_it_connects(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    confirm["answer"] = True
    provider = _provider(tmp_path, monkeypatch, [REAL], "r1")
    _fake_server(monkeypatch, provider)
    provider.practice_start(_tools(), practice_dir(provider._base()))
    practice = provider.practice_profile()
    assert practice is not None and provider.store.default_id == practice.id
    assert st.load_sites(tmp_path).default_id == practice.id
    assert provider.said[-1] == f"{run.RUNNING_AND_CONNECTED} {run.NOW_DEFAULT}"


def test_the_only_site_is_the_default_and_says_so(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    provider = _provider(tmp_path, monkeypatch, [])
    _fake_server(monkeypatch, provider)
    provider.practice_start(_tools(), practice_dir(provider._base()))
    assert confirm["asked"] == []
    assert provider.said[-1] == (
        f"{run.RUNNING_AND_CONNECTED} It is your default site, because it is your only one."
    )


def test_adding_it_never_moves_an_unset_default(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    provider = _provider(tmp_path, monkeypatch, [REAL], "")  # sites, but no default saved
    _fake_server(monkeypatch, provider)
    provider.practice_start(_tools(), practice_dir(provider._base()))
    assert provider.store.default_id == "r1"
    assert len(confirm["asked"]) == 1


def test_a_later_start_says_running_and_connected_without_asking(
    tmp_path, monkeypatch, wx_call_after, confirm
) -> None:
    wx_call_after()
    practice = st.SiteProfile("p1", "Practice Site", site_url(), "admin")
    provider = _provider(tmp_path, monkeypatch, [REAL, practice], "r1")
    _fake_server(monkeypatch, provider, password=False)
    (practice_dir(provider._base()) / "handoff").mkdir(parents=True)
    provider.practice_start(_tools(), practice_dir(provider._base()))
    assert confirm["asked"] == []
    assert provider.said[-1] == run.RUNNING_AND_CONNECTED


def test_a_used_up_password_is_said_plainly_and_mended(tmp_path, monkeypatch) -> None:
    provider = _provider(tmp_path, monkeypatch, [REAL], "r1")
    process = _Process()
    provider._practice = provider._practice_ready = process
    handoff = practice_dir(provider._base()) / "handoff"
    handoff.mkdir(parents=True)
    marker = handoff / ".quill-practice-initialized"
    marker.write_text("1", encoding="utf-8")
    provider.do_practice_connect(None, None)
    assert provider.said == [run.USED_UP]
    assert not marker.exists()  # the next start makes a new password


# -- the context menus -------------------------------------------------------------------


def test_every_practice_menu_offers_its_five_commands() -> None:
    wanted = [
        "Start the Practice Site",
        "Stop the Practice Site",
        "Connect It as Practice Site",
        "Make It My Default Site",
        "Reset the Practice Site...",
    ]
    for kind in (
        PRACTICE_ROW_KIND,
        PRACTICE_SITE_KIND,
        PRACTICE_NODE_KIND,
        PRACTICE_SITE_NODE_KIND,
    ):
        top, _more = WORDPRESS_ACTIONS.menu_for(kind)
        assert [r.label for r in top[1:6]] == wanted, kind  # on top, straight after the default


def test_tools_practice_site_reaches_each_by_keyboard() -> None:
    assert problems(WINDOW_MENU) == []
    assert WORDPRESS_KEYS[command("practice")] == "Ctrl+Alt+P"
    verbs = {row.command_id for row in PRACTICE_SUB.rows if row is not None}
    assert verbs == {command(v) for v in ("practice", *run_verbs())}


def run_verbs() -> tuple[str, ...]:
    from quill.core.wordpress.workbench_practice_actions import PRACTICE_VERBS

    return PRACTICE_VERBS


def test_the_menus_belong_to_the_practice_site_only(tmp_path, monkeypatch) -> None:
    practice = st.SiteProfile("p1", "Practice Site", site_url(), "admin")
    provider = _provider(tmp_path, monkeypatch, [REAL, practice], "r1")
    provider.reload_profiles()
    assert provider.node_menu_kind(PRACTICE_NODE) == PRACTICE_NODE_KIND
    assert provider.node_menu_kind(NodeRef("site", "site", "Practice Site")) == (
        PRACTICE_SITE_NODE_KIND
    )
    assert provider.node_menu_kind(NodeRef("site", "site", "Radio Club")) == "node"
    assert provider.node_menu_kind(NodeRef("site", "posts", "Practice Site")) == "node"
    kinds = {provider._site_row(name).kind for name in provider._profiles}
    assert kinds == {"site", PRACTICE_SITE_KIND}
    assert {r.kind for r in provider.practice_rows()} == {PRACTICE_ROW_KIND}


def test_a_greyed_command_says_why(tmp_path, monkeypatch) -> None:
    provider = _provider(tmp_path, monkeypatch, [REAL], "r1")
    refusal = provider.practice_refusal
    assert refusal(command("practice_stop")) == "The Practice Site is not running."
    assert refusal(command("practice_connect")).startswith("The Practice Site is not running.")
    assert refusal(command("practice_default")) == (
        "The Practice Site is not connected yet. Starting it connects it."
    )
    assert refusal(command("practice_reset")) == ""
    provider._practice = _Process()  # starting: not answering yet
    assert refusal(command("practice_connect")).startswith("The Practice Site is starting.")
    provider._practice_ready = provider._practice
    assert refusal(command("practice_connect")) == ""
    assert refusal(command("practice_default")) == (
        "The Practice Site is not connected yet. Choose Connect It as Practice Site first."
    )
    assert refusal(command("practice_start")) == "The Practice Site is already running."
    assert refusal(command("practice_reset")) == "Stop the Practice Site before you reset it."
    assert refusal(command("practice_stop")) == ""
    assert refusal(command("trash")) == ""  # not a Practice Site command


def test_make_it_my_default_from_the_menu(tmp_path, monkeypatch) -> None:
    practice = st.SiteProfile("p1", "Practice Site", site_url(), "admin")
    provider = _provider(tmp_path, monkeypatch, [REAL, practice], "r1")
    provider.do_practice_default(None, None)
    assert provider.store.default_id == "p1"
    assert st.load_sites(tmp_path).default_id == "p1"
    provider.do_practice_default(None, None)
    assert provider.said[-2:] == [
        "The Practice Site is now your default site. New Page and New Post start there.",
        "The Practice Site is already your default site.",
    ]


# -- its name, wherever sites are listed ---------------------------------------------------


def test_lists_of_sites_say_it_is_on_this_computer() -> None:
    assert listed_name("Practice Site", site_url()) == "Practice Site (on this computer)"
    assert listed_name("My Blog", site_url()) == "My Blog (practice site, on this computer)"
    assert listed_name("Radio Club", "https://radio.example.org") == "Radio Club"
    practice = st.SiteProfile("p1", "Practice Site", site_url(), "admin", role="Administrator")
    assert practice.spoken() == "Practice Site (on this computer), Administrator"
    assert REAL.spoken() == "Radio Club, radio.example.org"


def test_new_page_lists_it_by_that_name(tmp_path, monkeypatch) -> None:
    from quill.ui import wordpress_commands as wc

    practice = st.SiteProfile("p1", "Practice Site", site_url(), "admin")
    seen: dict[str, Any] = {}

    def ask_new_item(_parent, _show, **kw):
        seen.update(kw)
        return None

    monkeypatch.setattr(wc.idlg, "ask_new_item", ask_new_item)
    commands = wc.WordPressCommands.__new__(wc.WordPressCommands)
    store = st.SiteStore([REAL, practice], "p1")
    monkeypatch.setattr(commands, "need_site", lambda: store, raising=False)
    monkeypatch.setattr(
        commands, "background", lambda _name, work, done: done(([], [])), raising=False
    )
    commands.host = type("H", (), {"parent": None, "show_modal": None})()
    commands._last_format = "blocks"
    commands.api = lambda _p: None  # type: ignore[method-assign]
    commands._new("page")
    assert seen["sites"] == ["Radio Club", "Practice Site (on this computer)"]
    assert seen["site_index"] == 1


def test_the_lesson_teaches_the_sentence_start_says() -> None:
    from quill.core.tutorials import wordpress_practice_lessons as lessons

    assert lessons.RUNNING_AND_CONNECTED == run.RUNNING_AND_CONNECTED
    (start,) = [t for t in lessons.practice_lessons() if t.slug == "workbench-practice-start"]
    assert run.RUNNING_AND_CONNECTED in [step.hear for step in start.steps]
    assert not any("Connect It as Practice Site" in step.body for step in start.steps)
