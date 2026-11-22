"""Scribe for Documents in the rest of the family: the shared wx pieces (PRD 8.3 to 8.10).

A result that opens in another app never opens by itself (the result
sentence would be cut off); an app's own step on the result is said inside
the one sentence; the shared submenu has a key on every row and the same keys
everywhere; Convert Linked Document says there is nothing, goes straight to
the Convert dialog for one link, and asks with a labelled list for several;
Save a Beacon Place asks where with the headings words first; Explorer's Send
To gathers the files sent together into one Convert dialog.
"""

# ruff: noqa: F811 - the shared fixtures are imported from test_scribe_ui and used by name
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.scribe import queue as q
from tests.unit.ui.test_scribe_ui import Host, controller, isolated  # noqa: F401

pytestmark = pytest.mark.usefixtures("wx_session_app")


@pytest.fixture(autouse=True)
def _holding() -> Any:
    from quill.ui.scribe_controller import ScribeController

    original = ScribeController.__dict__["holding"]
    ScribeController.holding = property(lambda _self: True)  # type: ignore[assignment]
    yield
    ScribeController.holding = original  # type: ignore[assignment]


def _now(controller: Any) -> None:
    """Run the controller's background work at once, on this thread."""

    def run(work: Any, done: Any, failed: Any = None) -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            (failed or controller._failed)(error)
            return
        done(result)

    controller._background = run


def _done_job(tmp_path: Path, app: str = "QUILL") -> q.Job:
    path = tmp_path / "Notes.docx"
    path.write_bytes(b"docx")
    return q.Job(
        app=app, file_name="Notes.pdf", formats=["docx"], state=q.DONE, outputs={"docx": str(path)}
    )


# ------------------------------------------------------- opening, and the note


def test_a_result_that_opens_elsewhere_never_opens_by_itself(
    controller: Any, tmp_path: Path
) -> None:
    controller.host.scribe_opens_on_its_own = False
    controller._on_event("done", _done_job(tmp_path))
    assert controller.host.opened == []
    assert controller.host.said[-1].endswith("Open it from Scribe Conversions.")
    # Open Result, the person's own command, still opens it.
    controller.open_job_result(_done_job(tmp_path))
    assert [f for f, _p in controller.host.opened] == ["docx"]


def test_the_apps_own_step_is_said_inside_the_one_result_sentence(
    controller: Any, tmp_path: Path
) -> None:
    _now(controller)
    controller.host.scribe_opens_on_its_own = False
    controller.host.scribe_finish_job = lambda job: "with 3 chapter markers"
    controller._on_event("done", _done_job(tmp_path))
    assert len(controller.host.said) == 1
    assert "Notes.docx, with 3 chapter markers" in controller.host.said[0]
    # Another app's job: no step, and the sentence is plain.
    controller.host.said.clear()
    controller._on_event("done", _done_job(tmp_path, app="QUILL Studio"))
    assert "chapter markers" not in controller.host.said[0]


# ------------------------------------------------------------- the submenu


class _Owner:
    def __init__(self) -> None:
        import wx

        self.frame = wx.Frame(None)
        self.ran: list[str] = []
        self.ready = 0

    def _scribe_menu_ready(self) -> None:
        self.ready += 1

    def __getattr__(self, name: str) -> Any:
        if name.startswith("scribe_"):
            return lambda: self.ran.append(name)
        raise AttributeError(name)


def test_the_submenu_has_a_key_on_every_row_and_runs_each_command() -> None:
    import wx

    from quill.ui.scribe_app_host import COMMON_ROWS, ENTRY_KEY, append_scribe_submenu

    owner = _Owner()
    try:
        menu = wx.Menu()
        ids = append_scribe_submenu(owner, menu, wx, first=("&Add Places", lambda: None))
        submenu = menu.GetMenuItems()[0].GetSubMenu()
        labels = [i.GetItemLabel() for i in submenu.GetMenuItems() if not i.IsSeparator()]
        assert labels[0] == f"&Add Places\t{ENTRY_KEY}"
        assert all("\t" in label for label in labels) and len(ids) == len(labels)
        keys = [label.partition("\t")[2] for label in labels]
        assert len(set(keys)) == len(keys)
        letters = [label.split("&")[1][0].lower() for label in labels]
        assert len(set(letters)) == len(letters)
        assert owner.ready == 1
        for item_id, (_cid, _label, handler, _key) in zip(ids[1:], COMMON_ROWS, strict=True):
            owner.frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, int(item_id)))
            assert owner.ran[-1] == handler
    finally:
        owner.frame.Destroy()


def test_the_keys_avoid_the_family_f_row_and_altgr() -> None:
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS
    from quill.ui.scribe_app_host import COMMON_ROWS, ENTRY_KEY

    keys = [ENTRY_KEY, *(key for *_rest, key in COMMON_ROWS)]
    assert all(key.startswith("Alt+Shift+F") for key in keys)
    assert not set(keys) & set(SIBLING_APP_ACCELERATORS)


def test_next_steps_elsewhere_name_the_editor_and_the_player(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_app_host

    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: "QUILL")
    opened: list[str] = []
    monkeypatch.setattr(scribe_app_host, "open_in_editor", lambda p: opened.append(p.name) or "")
    said: list[str] = []
    ready = {"docx": tmp_path / "N.docx", "mp3": tmp_path / "N.mp3"}
    steps = scribe_app_host.elsewhere_steps(q.Job(file_name="N.pdf"), ready, said.append)
    assert [label for label, _run in steps] == [
        "Open in QUILL (Word)",
        "Send to Media Player (MP3 audio)",
    ]
    steps[0][1]()
    assert opened == ["N.docx"] and said == [
        "QUILL could not be opened. N.docx is saved in its folder."
    ]


# ------------------------------------------------- Convert Linked Document


class _UrlController:
    def __init__(self) -> None:
        self.urls: list[tuple[str, str]] = []

    def check_available(self) -> bool:
        return True

    def convert_url(self, url: str, *, open_as: str = "") -> list[str]:
        self.urls.append((url, open_as))
        return ["job"]


def test_linked_documents_none_one_and_several(monkeypatch: pytest.MonkeyPatch) -> None:
    import wx

    from quill.core.scribe.links import documents_in_html
    from quill.ui.scribe_link_choice import TITLE, convert_linked

    controller = _UrlController()
    said: list[str] = []
    asked: list[tuple[str, str, list[str], str]] = []

    def modal(dialog: Any, title: str) -> int:
        listbox = next(c for c in dialog.GetChildren() if isinstance(c, wx.ListBox))
        rows = [listbox.GetString(i) for i in range(listbox.GetCount())]
        message = next(c for c in dialog.GetChildren() if isinstance(c, wx.StaticText))
        asked.append((title, message.GetLabel(), rows, listbox.GetName()))
        assert dialog.GetSelection() == 0
        dialog.SetSelection(1)
        return wx.ID_OK

    common = {
        "parent": None,
        "where": "this post",
        "subject": "this post",
        "verb": "links",
        "say": said.append,
        "modal": modal,
    }
    convert_linked(controller, [], **common)
    assert said == ["This post links no documents Scribe for Documents can convert."]
    one = documents_in_html('<a href="https://a.org/x.pdf">x</a>')
    convert_linked(controller, one, **common)
    assert controller.urls == [("https://a.org/x.pdf", "linked")] and asked == []
    two = documents_in_html(
        '<a href="https://a.org/x.pdf">X</a> <a href="https://a.org/y.pdf">Y</a>'
    )
    convert_linked(controller, two, **common)
    assert asked == [
        (TITLE, "Linked documents in this post, 2:", ["X (a.org)", "Y (a.org)"], "Linked documents")
    ]
    assert controller.urls[-1] == ("https://a.org/y.pdf", "linked")


# ---------------------------------------------------------- Save a Beacon Place


def test_save_a_beacon_place_asks_where_and_says_it_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    from quill.ui.scribe_beacon_place import TITLE, save_beacon_place

    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path / "beacon"))
    html = tmp_path / "Notes.html"
    html.write_text("<h1>Notes</h1><h2>Methods</h2>", encoding="utf-8")
    seen: list[tuple[str, list[str]]] = []

    def modal(dialog: Any, title: str) -> int:
        listbox = next(c for c in dialog.GetChildren() if isinstance(c, wx.ListBox))
        seen.append((title, [listbox.GetString(i) for i in range(listbox.GetCount())]))
        dialog.SetSelection(2)
        return wx.ID_OK

    said: list[str] = []
    job = q.Job(file_name="Notes.pdf", title="Notes", document_id="doc-9")
    save_beacon_place(job, "html", html, parent=None, say=said.append, modal=modal)
    assert seen == [
        (
            TITLE,
            ["The start of the document", "Notes, heading level 1", "Methods, heading level 2"],
        )
    ]
    assert said == ["Saved a Beacon place: Notes, at Methods."]
    from quill.apps.beacon.scribe_places import open_store, scribe_places

    store = open_store()
    try:
        places = scribe_places(store)
        assert [p.locations[0].heading_path for p in places] == [["Notes", "Methods"]]
    finally:
        store.close()


def test_quills_next_steps_offer_a_beacon_place_only_where_beacon_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_beacon_place
    from quill.ui.main_frame_scribe import QuillScribeHost

    host = QuillScribeHost(type("MF", (), {"settings": None, "_announce": print})())
    ready = {"docx": tmp_path / "N.docx", "html": tmp_path / "N.html"}
    job = q.Job(file_name="N.pdf", document_id="d1")
    monkeypatch.setattr(scribe_beacon_place, "beacon_available", lambda: True)
    labels = [label for label, _run in host.scribe_next_steps(job, ready)]
    assert "Save a Beacon Place (Word)..." in labels
    assert "Save a Beacon Place (Accessible HTML)..." in labels
    monkeypatch.setattr(scribe_beacon_place, "beacon_available", lambda: False)
    labels = [label for label, _run in host.scribe_next_steps(job, ready)]
    assert not any("Beacon" in label for label in labels)


# ------------------------------------------------------------- Send To


def test_send_to_gathers_the_files_into_one_convert_dialog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    from quill.ui.main_frame_scribe import ScribeMixin

    later: list[Any] = []
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: later.append(fn))
    sent: list[list[Path]] = []

    class Frame(ScribeMixin):
        def __init__(self) -> None:
            self.frame = wx.Frame(None)
            self.said: list[str] = []

        def _announce(self, text: str) -> None:
            self.said.append(text)

        def _scribe(self) -> Any:
            return type("C", (), {"convert_files": lambda _s, paths: sent.append(paths)})()

    frame = Frame()
    try:
        first, second = tmp_path / "a.pdf", tmp_path / "b.docx"
        frame._scribe_shell_request(first)
        frame._scribe_shell_request(second)
        frame._scribe_shell_request(first)
        assert len(later) == 1  # one flush for the files sent together
        monkeypatch.setattr(wx, "GetActiveWindow", lambda: None)
        later[0]()
        assert sent == [[first, second]] and frame.said == []
    finally:
        frame.frame.Destroy()
