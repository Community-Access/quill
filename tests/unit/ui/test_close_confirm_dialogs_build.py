"""The Exit / Minimize to Tray dialogs of Quill Radio and QUILL Cast can be built.

Both took their button ids as ``int(wx.NewIdRef())``, which releases the id the
moment the temporary IdRef is collected; building the buttons then raised
wxAssertionError ("id count already 0"), so closing either app never asked
(found 2026-09-25). Tests that faked the dialog could not see it -- these build
the real thing.
"""

from __future__ import annotations

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.podcasts.close_confirm_dialog import CastCloseConfirmDialog  # noqa: E402
from quill.ui.radio.close_confirm_dialog import RadioCloseConfirmDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.mark.parametrize("recording_active", [False, True])
def test_radio_close_confirm_builds_with_distinct_ids(wx_app, recording_active) -> None:
    dialog = RadioCloseConfirmDialog(None, recording_active=recording_active)
    try:
        assert dialog._minimize_id != dialog._exit_id
        assert dialog.dialog.FindWindowById(dialog._exit_id) is not None
        assert dialog.dialog.FindWindowById(dialog._minimize_id) is not None
    finally:
        dialog.dialog.Destroy()


def test_cast_close_confirm_builds_with_distinct_ids(wx_app) -> None:
    dialog = CastCloseConfirmDialog(None, playing=True, downloads=2)
    try:
        assert dialog._minimize_id != dialog._exit_id
        assert dialog.dialog.FindWindowById(dialog._exit_id) is not None
        assert dialog.dialog.FindWindowById(dialog._minimize_id) is not None
    finally:
        dialog.dialog.Destroy()
