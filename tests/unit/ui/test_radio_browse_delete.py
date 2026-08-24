"""Delete, in the browse tree: ask, remove, and show that it is gone.

Reported 2026-08-23: "pressing delete doesn't seem to delete an item from the
list and the user should be asked and doing so should refresh the treeview to
show that it is gone." All three halves are pinned here -- the question, the
removal, and the reload -- plus the two refusals that matter: a No removes
nothing, and a row with nothing to remove says so instead of swallowing the key.

A stand-in dialog, like the other ``ui/radio`` helper-module tests: these
modules take a host and touch only that.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.radio.browse_nodes import make_id
from quill.ui.radio import browse_delete, browse_keys


class _Box:
    """Stands in for wx.RichMessageDialog."""

    def __init__(self, wx: Any, message: str, style: int) -> None:
        self._wx = wx
        self.message = message
        self.style = style
        self.checkbox = ""
        self.checkbox_initial = None
        self.destroyed = False

    def ShowCheckBox(self, label: str, checked: bool = False) -> None:  # noqa: N802
        self.checkbox = label
        self.checkbox_initial = checked

    def IsCheckBoxChecked(self) -> bool:  # noqa: N802
        return self._wx.tick

    def ShowModal(self) -> int:  # noqa: N802
        return self._wx.answer

    def Destroy(self) -> None:  # noqa: N802
        self.destroyed = True


class _Wx:
    YES = 5103
    NO = 5104
    ID_YES = 5103
    ID_NO = 5104
    YES_NO = 10
    NO_DEFAULT = 20
    OK = 4
    ICON_QUESTION = 40
    ICON_INFORMATION = 50
    WXK_DELETE = 127
    WXK_ESCAPE = 27
    WXK_F4 = 344

    def __init__(self, answer: int) -> None:
        self.answer = answer
        self.tick = False
        self.asked: list[str] = []
        self.boxes: list[_Box] = []

    def RichMessageDialog(  # noqa: N802
        self, _parent: Any, message: str, _title: str, style: int
    ) -> _Box:
        self.asked.append(message)
        box = _Box(self, message, style)
        self.boxes.append(box)
        return box


class _Tree:
    def __init__(self, label: str) -> None:
        self._label = label
        self.selection = object()

    def GetSelection(self) -> Any:  # noqa: N802
        return self.selection

    def GetItemText(self, _node: Any) -> str:  # noqa: N802
        return self._label


class _History:
    confirm_browse_delete = True
    explain_browse_delete = True


class _Frame:
    """The app frame behind a browse window: where the answers are remembered."""

    def __init__(self) -> None:
        self._radio_history = _History()
        self.saves = 0

    def _save_radio_history(self) -> None:
        self.saves += 1


class _Favorites:
    def __init__(self, holds: Any = None) -> None:
        self._holds = holds
        self.removed: list[str] = []

    def contains(self, station: Any) -> bool:
        return self._holds is station

    def remove(self, key: str) -> None:
        self.removed.append(key)


class _Dialog:
    def __init__(self, data: dict | None, *, answer: int = _Wx.YES, label: str = "A Video") -> None:
        self._wx = _Wx(answer)
        self._tree = _Tree(label)
        self._win = object()
        self._data = data
        self._favorites = _Favorites()
        self._download_host = _Frame()
        self.said: list[str] = []
        self.reloaded: list[str] = []
        self.favorites_refreshed = 0

    def _node_data(self, _node: Any) -> dict | None:
        return self._data

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _reload_source_branch(self, node_id: str) -> None:
        self.reloaded.append(node_id)

    def _on_favorites_changed(self) -> None:
        return None

    def _refresh_favorites_branch(self) -> None:
        self.favorites_refreshed += 1


_URL = "https://www.youtube.com/watch?v=iG9CE55wbtY"


def _video_row() -> dict:
    return {"node_id": make_id("ytvideo", _URL), "label": "A Video"}


def test_deleting_a_saved_video_asks_by_name_then_removes_and_reloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.radio.youtube_saved import SavedStore

    removed: list[str] = []
    monkeypatch.setattr(SavedStore, "remove", lambda self, url: removed.append(url))
    dialog = _Dialog(_video_row(), label="Do schools kill creativity?")

    assert browse_delete.delete_selected(dialog) is True

    # Asked, and the question names the thing -- "are you sure?" is not a
    # question anybody can answer.
    assert dialog._wx.asked == ["Remove Do schools kill creativity? from YouTube?"]
    assert removed == [_URL]
    # And the branch is re-fetched, so the row actually disappears.
    assert dialog.reloaded == ["youtube"]
    assert any("Removed Do schools kill creativity?" in m for m in dialog.said)


def test_answering_no_removes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio.youtube_saved import SavedStore

    removed: list[str] = []
    monkeypatch.setattr(SavedStore, "remove", lambda self, url: removed.append(url))
    dialog = _Dialog(_video_row(), answer=_Wx.NO)

    assert browse_delete.delete_selected(dialog) is False
    assert removed == []
    assert dialog.reloaded == []
    assert "Nothing was removed." in dialog.said


def test_the_question_defaults_to_no_and_the_checkbox_starts_unticked() -> None:
    """One mis-press must not both delete a row and switch the question off."""
    dialog = _Dialog(_video_row(), answer=_Wx.NO)

    browse_delete.confirm(dialog, "Remove it?")

    box = dialog._wx.boxes[0]
    assert box.style & _Wx.NO_DEFAULT
    assert box.checkbox_initial is False
    assert "again" in box.checkbox
    assert box.destroyed


def test_a_followed_channel_is_unfollowed(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio.youtube_channels import ChannelStore

    removed: list[str] = []
    monkeypatch.setattr(ChannelStore, "remove", lambda self, url: removed.append(url))
    channel = "https://www.youtube.com/@TED"
    dialog = _Dialog({"node_id": make_id("youtubechannel", channel), "label": "TED"})

    assert browse_delete.delete_selected(dialog) is True
    assert removed == [channel]
    assert dialog.reloaded == ["youtube"]


def test_a_server_is_removed_from_my_servers(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio.my_servers import ServerStore

    removed: list[str] = []
    monkeypatch.setattr(ServerStore, "remove", lambda self, url: removed.append(url))
    root = "http://stream.example.org:8000"
    dialog = _Dialog({"node_id": make_id("myservers", root), "label": "example.org"})

    assert browse_delete.delete_selected(dialog) is True
    assert removed == [root]
    assert dialog.reloaded == ["myservers"]
    assert any("My Servers" in m for m in dialog._wx.asked)


def test_a_favorite_row_is_unfavorited() -> None:
    class _Station:
        display_name = "KFI AM 640"
        station_uuid = "uuid-1"
        stream_url = "http://stream/kfi"

    station = _Station()
    dialog = _Dialog({"node_id": "station\thttp://stream/kfi", "station": station})
    dialog._favorites = _Favorites(station)

    assert browse_delete.delete_selected(dialog) is True
    assert dialog._favorites.removed == ["uuid-1"]
    assert dialog.favorites_refreshed == 1
    assert any("Remove KFI AM 640 from Favorites?" == m for m in dialog._wx.asked)


def test_a_row_with_nothing_to_remove_says_so_rather_than_swallowing_the_key() -> None:
    dialog = _Dialog({"node_id": "popular", "label": "Popular Stations"})

    assert browse_delete.delete_selected(dialog) is False
    assert browse_delete.NOTHING_TO_DELETE in dialog.said
    # It explains rather than asking: there is nothing here to say yes to.
    assert all("Remove" not in message for message in dialog._wx.asked)


def test_the_root_youtube_branch_itself_is_not_deletable() -> None:
    """The branch has no args, so there is nothing it names to remove."""
    dialog = _Dialog({"node_id": "youtube", "label": "YouTube"})
    assert browse_delete.delete_selected(dialog) is False


# -- the key itself ----------------------------------------------------------------


class _Event:
    def __init__(self, key: int, *, control: bool = False) -> None:
        self._key = key
        self._control = control

    def GetKeyCode(self) -> int:  # noqa: N802
        return self._key

    def ControlDown(self) -> bool:  # noqa: N802
        return self._control

    def ShiftDown(self) -> bool:  # noqa: N802
        return False

    def AltDown(self) -> bool:  # noqa: N802
        return False


class _KeyDialog(_Dialog):
    """A dialog that can say where focus is, for the key policy."""

    def __init__(self, focus: str = "tree", **kwargs: Any) -> None:
        super().__init__(_video_row(), **kwargs)
        self._find_ctrl = object()
        self._find_active = False
        self._modeless = True
        self._focus = self._tree if focus == "tree" else self._find_ctrl
        self._win = _Win(self._focus)

    def _clear_find(self) -> None:
        self.said.append("cleared")


class _Win:
    def __init__(self, focus: Any) -> None:
        self._focus = focus
        self.closed = 0

    def FindFocus(self) -> Any:  # noqa: N802
        return self._focus

    def Close(self) -> None:  # noqa: N802
        self.closed += 1


def test_delete_on_the_tree_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio.youtube_saved import SavedStore

    monkeypatch.setattr(SavedStore, "remove", lambda self, url: None)
    dialog = _KeyDialog("tree")

    assert browse_keys.handle(dialog, _Event(_Wx.WXK_DELETE)) is True
    assert dialog.reloaded == ["youtube"]


def test_delete_in_the_find_box_is_an_ordinary_delete() -> None:
    """Stealing it there would make the search field unusable."""
    dialog = _KeyDialog("find")

    assert browse_keys.handle(dialog, _Event(_Wx.WXK_DELETE)) is False
    assert dialog._wx.asked == []


def test_escape_still_closes_a_modeless_window() -> None:
    dialog = _KeyDialog("tree")
    assert browse_keys.handle(dialog, _Event(_Wx.WXK_ESCAPE)) is True
    assert dialog._win.closed == 1


def test_escape_in_the_find_box_clears_the_search_first() -> None:
    dialog = _KeyDialog("find")
    dialog._find_active = True

    assert browse_keys.handle(dialog, _Event(_Wx.WXK_ESCAPE)) is True
    assert "cleared" in dialog.said
    assert dialog._win.closed == 0


def test_an_unclaimed_key_is_left_to_the_tree() -> None:
    dialog = _KeyDialog("tree")
    assert browse_keys.handle(dialog, _Event(ord("A"))) is False


# -- "don't ask me again" ----------------------------------------------------------


def test_ticking_the_box_stops_the_question_and_is_remembered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.radio.youtube_saved import SavedStore

    monkeypatch.setattr(SavedStore, "remove", lambda self, url: None)
    dialog = _Dialog(_video_row())
    dialog._wx.tick = True

    assert browse_delete.delete_selected(dialog) is True

    history = dialog._download_host._radio_history
    assert history.confirm_browse_delete is False
    # Persisted, not just held for this window: a preference set once has to
    # survive the app being closed.
    assert dialog._download_host.saves == 1


def test_once_it_is_off_delete_removes_without_asking(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio.youtube_saved import SavedStore

    removed: list[str] = []
    monkeypatch.setattr(SavedStore, "remove", lambda self, url: removed.append(url))
    dialog = _Dialog(_video_row())
    dialog._download_host._radio_history.confirm_browse_delete = False

    assert browse_delete.delete_selected(dialog) is True

    assert dialog._wx.asked == []  # no question
    assert removed == [_URL]
    # Never silent, though: the row is still named out loud.
    assert any("Removed" in m for m in dialog.said)


def test_a_standard_folder_explains_itself_in_a_dialog() -> None:
    """Spoken only, this was easy to miss on the key people press first."""
    dialog = _Dialog({"node_id": "popular", "label": "Popular Stations"}, label="Popular Stations")

    assert browse_delete.delete_selected(dialog) is False

    assert browse_delete.NOTHING_TO_DELETE in dialog.said
    assert len(dialog._wx.boxes) == 1
    assert "Popular Stations" in dialog._wx.boxes[0].message
    assert "Hide This Source" in dialog._wx.boxes[0].message


def test_the_explanation_can_be_switched_off_too() -> None:
    dialog = _Dialog({"node_id": "popular", "label": "Popular Stations"})
    dialog._wx.tick = True
    browse_delete.delete_selected(dialog)
    assert dialog._download_host._radio_history.explain_browse_delete is False

    dialog._wx.boxes.clear()
    browse_delete.delete_selected(dialog)

    assert dialog._wx.boxes == []
    # Still said out loud, because a key that appears to do nothing is
    # indistinguishable from a broken one.
    assert dialog.said.count(browse_delete.NOTHING_TO_DELETE) == 2


def test_a_window_with_no_frame_behind_it_always_asks() -> None:
    dialog = _Dialog(_video_row(), answer=_Wx.NO)
    dialog._download_host = object()

    assert browse_delete.delete_selected(dialog) is False
    assert len(dialog._wx.boxes) == 1
