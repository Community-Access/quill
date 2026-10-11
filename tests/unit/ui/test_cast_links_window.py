"""Links in These Notes, grown for the Notes reader (qc.md 5c).

Built headlessly and never shown. The window raised TypeError on construction
until 2026-10-02 (``bind_close_button`` lost its required ``modeless`` keyword),
so the first test is simply that it builds.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.text_links import Link  # noqa: E402
from quill.ui.link_list_dialog import LinkListDialog  # noqa: E402

LINKS = [
    Link(url="https://www.patreon.com/thedaily", text="Support the show"),
    Link(url="https://example.com/paper", text="The paper"),
    Link(url="https://example.com/bare"),
]


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def window(wx_app):
    frame = wx.Frame(None)
    said: list[str] = []
    dialog = LinkListDialog(
        frame, links=LINKS, title="Links in These Notes", announce_cb=said.append
    )
    yield dialog, said
    dialog.dialog.Destroy()
    frame.Destroy()


def test_it_builds_and_each_row_reads_title_then_where_it_goes(window) -> None:
    dialog, _said = window
    rows = [dialog._list.GetString(i) for i in range(dialog._list.GetCount())]
    assert rows == [
        "Support the show, patreon.com/thedaily",
        "The paper, example.com/paper",
        "example.com/bare",
    ]


def test_the_buttons_are_the_four_the_plan_names(window) -> None:
    dialog, _said = window
    labels = [
        dialog._open_btn.GetLabel(),
        dialog._copy_btn.GetLabel(),
        dialog._copy_all_btn.GetLabel(),
    ]
    assert labels == ["&Open in Browser", "&Copy Address", "Copy &All Addresses"]


def test_the_context_menu_adds_copy_title_and_address_one_row_deeper() -> None:
    assert [label for label, _m in LinkListDialog.MENU_ROWS] == [
        "Open in Browser",
        "Copy Address",
        "Copy Title and Address",
        "Copy All Addresses",
    ]
    for _label, method in LinkListDialog.MENU_ROWS:
        assert callable(getattr(LinkListDialog, method))


def test_it_opens_on_the_link_the_reader_was_on(wx_app) -> None:
    frame = wx.Frame(None)
    try:
        dialog = LinkListDialog(frame, links=LINKS, select_url="https://example.com/paper/")
        assert dialog.selected() == LINKS[1]
        dialog.dialog.Destroy()
    finally:
        frame.Destroy()


def test_the_copies_say_what_they_copied(window, monkeypatch) -> None:
    dialog, said = window
    copied: list[str] = []
    monkeypatch.setattr(
        dialog, "_to_clipboard", lambda text, spoken: (copied.append(text), said.append(spoken))[0]
    )
    dialog._list.SetSelection(0)
    dialog.copy_selected()
    dialog.copy_title_and_address()
    dialog.copy_all()
    assert copied == [
        "https://www.patreon.com/thedaily",
        "Support the show\nhttps://www.patreon.com/thedaily",
        "https://www.patreon.com/thedaily\nhttps://example.com/paper\nhttps://example.com/bare",
    ]
    assert said[-1] == "Copied 3 addresses."


def test_open_in_browser_says_so(window, monkeypatch) -> None:
    dialog, said = window
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    dialog._list.SetSelection(1)
    assert dialog.open_selected()
    assert opened == ["https://example.com/paper"]
    assert said[-1] == "Opened in your browser."


@pytest.mark.parametrize(
    ("opens", "sets_data", "succeeds"),
    [(False, True, False), (True, False, False), (True, True, True)],
)
def test_copy_only_announces_success_after_clipboard_accepts_data(
    window, opens: bool, sets_data: bool, succeeds: bool
) -> None:
    dialog, said = window

    class Clipboard:
        closed = False

        @staticmethod
        def Open() -> bool:
            return opens

        @staticmethod
        def SetData(_data: object) -> bool:
            return sets_data

        @classmethod
        def Close(cls) -> None:
            cls.closed = True

    dialog._wx = SimpleNamespace(
        TheClipboard=Clipboard,
        TextDataObject=lambda text: text,
    )

    assert dialog._to_clipboard("address", "Copied address.") == ("address" if succeeds else "")
    assert said[-1] == ("Copied address." if succeeds else "That could not be copied.")
    assert Clipboard.closed is opens
