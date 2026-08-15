"""The two settings surfaces the download queue and browse tree read.

Both dialogs are thin over tested core models, so what is worth pinning here is
the *surface contract*: a row says its own state (the reason the house pattern
exists), toggling changes exactly the selection it claims, OK returns the
controls as edited, and Cancel returns nothing at all.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.core.radio import browse_visibility as bv
from quill.core.radio.download_prefs import DownloadPrefs
from quill.ui.radio.browse_sources_dialog import BrowseSourcesDialog, describe_source
from quill.ui.radio.download_prefs_dialog import DownloadPrefsDialog


@pytest.fixture(scope="module")
def _app() -> wx.App:
    return wx.App()


def _announcer() -> tuple[list[str], object]:
    spoken: list[str] = []
    return spoken, spoken.append


# --- Browse Sources -----------------------------------------------------------


def test_a_row_says_its_own_state() -> None:
    source = bv.BROWSE_SOURCES[0]
    on = describe_source(source, enabled=True, first_in_group=True)
    off = describe_source(source, enabled=False, first_in_group=False)
    assert on.startswith("On.") and source.label in on and source.group in on
    assert off.startswith("Off.") and source.description in off


def test_toggle_flips_exactly_one_branch(_app: wx.App) -> None:
    spoken, announce = _announcer()
    dialog = BrowseSourcesDialog(
        None, enabled=None, show_modal_dialog=lambda *_a, **_k: None, announce=announce
    )
    try:
        before = set(dialog.selection())
        dialog._list.SetSelection(0)
        first = dialog._sources[0]
        dialog._toggle()
        after = set(dialog.selection())
        assert before.symmetric_difference(after) == {first.id}
        assert any(first.label in line for line in spoken)
    finally:
        dialog.dialog.Destroy()


def test_selection_is_returned_in_tree_order(_app: wx.App) -> None:
    dialog = BrowseSourcesDialog(
        None,
        enabled=("wikidata", "favorites", "acb"),
        show_modal_dialog=lambda *_a, **_k: None,
        announce=lambda _m: None,
    )
    try:
        assert dialog.selection() == bv.normalize(("favorites", "acb", "wikidata"))
    finally:
        dialog.dialog.Destroy()


# --- Download Preferences -----------------------------------------------------


def _prefs_dialog(result: int, prefs: DownloadPrefs | None = None) -> DownloadPrefsDialog:
    return DownloadPrefsDialog(
        None,
        prefs=prefs or DownloadPrefs(),
        show_modal_dialog=lambda *_a, **_k: result,
        announce=lambda _m: None,
    )


def test_ok_returns_the_controls_as_edited(_app: wx.App) -> None:
    dialog = _prefs_dialog(wx.ID_OK)
    dialog._root_ctrl.SetValue(r"C:\Radio Saves")
    dialog._always_ask.SetValue(True)
    dialog._keep_going.SetValue(False)
    chosen = dialog.show()
    assert chosen is not None
    assert chosen.root == r"C:\Radio Saves"
    assert chosen.always_ask is True
    assert chosen.keep_going_in_background is False
    assert chosen.folder_per_book is True  # untouched rules keep their defaults


def test_cancel_returns_nothing(_app: wx.App) -> None:
    dialog = _prefs_dialog(wx.ID_CANCEL)
    dialog._root_ctrl.SetValue(r"C:\Radio Saves")
    assert dialog.show() is None


def test_the_effect_line_answers_the_question(_app: wx.App) -> None:
    dialog = _prefs_dialog(wx.ID_CANCEL, DownloadPrefs(always_ask=True))
    try:
        assert "asks where" in dialog._effect.GetLabel()
    finally:
        dialog.dialog.Destroy()


def test_download_host_state_refresh(_app: wx.App) -> None:
    """The runner caches prefs on its host; the command must replace the cache.

    Pinned via the attribute contract rather than the whole command, which
    needs a frame: what matters is that ``_download_prefs`` is what enqueue
    reads, so assigning it is how a new choice takes effect immediately.
    """
    from quill.ui.radio import download_runner

    host = SimpleNamespace(_download_prefs=DownloadPrefs(root="old"))
    assert download_runner._prefs(host).root == "old"
    host._download_prefs = DownloadPrefs(root="new")
    assert download_runner._prefs(host).root == "new"
