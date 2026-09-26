"""Radio 3.0.0 release fixes (2026-09-25): safe defaults and true help text.

Restore from Backup and Clear Song History both defaulted to the destructive
button, so Enter -- the key a listener presses to accept "the usual" -- replaced
every station or cleared a station's history. These tests drive each handler
with Enter modelled as "the default button" and assert nothing was destroyed.

The Resume Recording checkbox promised a Preferences option that did not
exist until 2026-09-25; the test builds both dialogs and holds the text to
what the code does.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.radio import backup_ui  # noqa: E402
from quill.ui.radio.resume_recording_dialog import (  # noqa: E402
    ResumeRecordingDialog,
    ResumeRecordingsBatchDialog,
)
from quill.ui.radio.song_history_dialog import SongHistoryDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _enter_on(style: int, *, yes_no_cancel: bool) -> int:
    """What Enter answers in a wx message box of *style* (its default button)."""
    if yes_no_cancel and style & wx.CANCEL_DEFAULT:
        return wx.ID_CANCEL
    if style & wx.NO_DEFAULT:
        return wx.NO if not yes_no_cancel else wx.ID_NO
    return wx.YES if not yes_no_cancel else wx.ID_YES


class _FakeFileDialog:
    def __init__(self, *_a: object, **_k: object) -> None:
        pass

    def __enter__(self) -> _FakeFileDialog:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def GetPath(self) -> str:  # noqa: N802 - wx API
        return "C:/backups/radio.qrbackup"


def test_restore_from_backup_enter_does_not_restore(monkeypatch) -> None:
    from quill.core.radio import backup

    monkeypatch.setattr(wx, "FileDialog", _FakeFileDialog)
    monkeypatch.setattr(
        backup,
        "read_manifest",
        lambda _p: SimpleNamespace(created="2026-09-01", recordings=0, data_files=["a", "b"]),
    )
    restored: list[object] = []
    monkeypatch.setattr(backup, "restore_backup", lambda *a, **k: restored.append(a))
    styles: list[int] = []

    def _message_box(_msg: str, _title: str, style: int) -> int:
        styles.append(style)
        return _enter_on(style, yes_no_cancel=False)

    frame = SimpleNamespace(
        frame=None,
        _show_modal_dialog=lambda _dlg, _title: wx.ID_OK,
        _show_message_box=_message_box,
        _set_status=lambda _m: restored.append("status"),
        settings=None,
    )
    backup_ui.restore_radio_data(frame)

    assert styles and styles[0] & wx.NO_DEFAULT, "No must be the default button"
    assert restored == [], "Enter on the confirm must not start a restore"


class _RecordingMessageDialog:
    last: _RecordingMessageDialog | None = None

    def __init__(self, _parent: object, message: str, _title: str, style: int) -> None:
        self.message = message
        self.style = style
        self.labels: tuple[str, ...] = ()
        _RecordingMessageDialog.last = self

    def SetYesNoCancelLabels(self, *labels: str) -> None:  # noqa: N802 - wx API
        self.labels = labels

    def Destroy(self) -> None:  # noqa: N802 - wx API
        pass


def test_clear_song_history_enter_clears_nothing() -> None:
    cleared: list[str] = []
    history = SimpleNamespace(
        clear_station=lambda key: cleared.append(key),
        clear_all=lambda: cleared.append("*"),
    )
    fake_wx = SimpleNamespace(
        MessageDialog=_RecordingMessageDialog,
        YES_NO=wx.YES_NO,
        CANCEL=wx.CANCEL,
        CANCEL_DEFAULT=wx.CANCEL_DEFAULT,
        ICON_QUESTION=wx.ICON_QUESTION,
        ID_CANCEL=wx.ID_CANCEL,
        ID_YES=wx.ID_YES,
    )
    dlg = SongHistoryDialog.__new__(SongHistoryDialog)
    dlg._wx = fake_wx
    dlg.dialog = None
    dlg._history = history
    dlg._current_station_name = lambda: "WQXR"
    dlg._show_modal = lambda d, _title: _enter_on(d.style, yes_no_cancel=True)
    dlg._announce = lambda _m: cleared.append("announced")
    dlg._on_changed = lambda: cleared.append("changed")

    dlg._on_clear(None)

    shown = _RecordingMessageDialog.last
    assert shown is not None and shown.style & wx.CANCEL_DEFAULT
    assert cleared == [], "Enter must cancel, not clear a station's history"
    # The message names the buttons the listener actually hears.
    assert "Choose No" not in shown.message
    assert "All stations" in shown.message
    assert shown.labels[1] == "&All stations"


@pytest.mark.parametrize(
    "build",
    [
        lambda: ResumeRecordingDialog(
            None, station_name="WQXR", remaining_minutes=12, scheduled_end="2026-09-25T09:00"
        ),
        lambda: ResumeRecordingsBatchDialog(None, lines=["WQXR -- 12 minute(s) left", "KUSC"]),
    ],
)
def test_resume_dont_ask_again_points_at_preferences(wx_app, build) -> None:
    dlg = build()
    try:
        names = [child.GetName() for child in dlg.dialog.GetChildren()]
    finally:
        dlg.dialog.Destroy()
    remember = [n for n in names if n.startswith("Don't ask me again")]
    assert remember, names
    # Preferences > Interrupted recordings at launch is the way back, and the
    # text must send the listener there rather than leave the choice permanent.
    assert "Preferences" in remember[0]


def test_resume_f1_help_names_the_real_buttons() -> None:
    from quill.core.radio.surface_help import PURPOSES

    single = PURPOSES["Resume Recording"]
    batch = PURPOSES["Resume Recordings"]
    assert "Dismiss" not in single and "Dismiss" not in batch
    assert "Skip" in single and "Skip All" in batch
    assert "Preferences" in single
