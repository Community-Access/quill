"""Unit tests for the OpenClipboard/GetData retry helper (support report:

'Failed to get data from the clipboard (error -2147221040: OpenClipboard
Failed)'). Windows' clipboard is a shared, single-owner OS resource; a
clipboard-history manager, Win+V history, or a screen reader polling
clipboard content for an announcement can transiently hold it open at the
exact moment QUILL tries to read it. wx's own wxClipboard::GetData logs a
GUI error dialog immediately on any such failure -- even one that would have
succeeded a few milliseconds later -- so these tests simulate that race with
a fake ``wx`` module and assert the retry loop gives it a real chance before
the existing (wx-native) error dialog is allowed through.
"""

from __future__ import annotations

from quill.ui.clipboard_retry import read_clipboard_text, with_clipboard_read_retry


class _FakeTextDataObject:
    def __init__(self) -> None:
        self._text = ""

    def GetText(self) -> str:
        return self._text


class _FakeLogNull:
    """Stands in for wx.LogNull: counts how many attempts were suppressed."""

    instances = 0

    def __init__(self) -> None:
        type(self).instances += 1


class _FakeClipboard:
    """Simulates the two places OpenClipboard contention can bite:

    ``open_fail_times`` makes ``Open()`` itself fail (return False) for that
    many calls before succeeding; ``get_data_fail_times`` makes ``Open()``
    succeed immediately but ``GetData`` fail for that many calls first --
    the exact race in the bug report, where wx.TheClipboard.Open() can
    already have returned True moments before GetData's own internal
    clipboard access loses the race.
    """

    def __init__(
        self,
        *,
        open_fail_times: int = 0,
        get_data_fail_times: int = 0,
        text: str = "pasted text",
    ) -> None:
        self.open_fail_times = open_fail_times
        self.get_data_fail_times = get_data_fail_times
        self.open_calls = 0
        self.get_data_calls = 0
        self.close_calls = 0
        self.text = text

    def Open(self) -> bool:
        self.open_calls += 1
        return self.open_calls > self.open_fail_times

    def GetData(self, data_object: _FakeTextDataObject) -> bool:
        self.get_data_calls += 1
        if self.get_data_calls <= self.get_data_fail_times:
            return False
        data_object._text = self.text
        return True

    def Close(self) -> None:
        self.close_calls += 1


class _FakeWx:
    def __init__(self, clipboard: _FakeClipboard) -> None:
        self.TheClipboard = clipboard
        self.TextDataObject = _FakeTextDataObject
        self.LogNull = _FakeLogNull


def _make_wx(**kwargs: object) -> _FakeWx:
    _FakeLogNull.instances = 0
    return _FakeWx(_FakeClipboard(**kwargs))  # type: ignore[arg-type]


def test_retry_recovers_from_transient_open_clipboard_failures() -> None:
    """OpenClipboard fails (sharing violation) the first 3 attempts, then
    succeeds -- the retry loop must give it a real chance rather than
    erroring on the very first denial."""
    wx = _make_wx(open_fail_times=3)
    text = read_clipboard_text(wx, max_attempts=10, delay=0.0)
    assert text == "pasted text"
    assert wx.TheClipboard.open_calls == 4


def test_retry_recovers_from_transient_get_data_failures() -> None:
    """The exact race from the bug report: Open() succeeds right away, but
    GetData loses its own internal race the first few times (another
    process/AT briefly holds the clipboard). The retry loop must recover."""
    wx = _make_wx(get_data_fail_times=4)
    text = read_clipboard_text(wx, max_attempts=10, delay=0.0)
    assert text == "pasted text"
    assert wx.TheClipboard.get_data_calls == 5
    # Every attempt closes what it opened -- no clipboard handle leak.
    assert wx.TheClipboard.open_calls == wx.TheClipboard.close_calls == 5


def test_early_attempts_suppress_wx_error_dialog() -> None:
    """wx.LogNull() must be used on every attempt except a genuinely final
    one, so a transient failure never pops wx's own error dialog."""
    wx = _make_wx(open_fail_times=3)
    read_clipboard_text(wx, max_attempts=10, delay=0.0)
    # 3 failed attempts + the 4th (successful) attempt were all suppressed;
    # only an attempt that could be the LAST one goes unsuppressed, and this
    # succeeded before reaching the last of 10 attempts.
    assert _FakeLogNull.instances == 4


def test_first_attempt_success_needs_no_retry() -> None:
    wx = _make_wx()
    text = read_clipboard_text(wx, max_attempts=10, delay=0.0)
    assert text == "pasted text"
    assert wx.TheClipboard.open_calls == 1


def test_retry_exhausted_fails_but_final_attempt_is_unsuppressed() -> None:
    """A real, sustained lock (contention never clears within the retry
    budget) must still be surfaced: the existing wx error dialog is the
    final fallback, so the very last attempt must run WITHOUT log
    suppression."""
    wx = _make_wx(open_fail_times=999)
    text = read_clipboard_text(wx, max_attempts=5, delay=0.0)
    assert text == ""
    assert wx.TheClipboard.open_calls == 5
    # The first 4 attempts are suppressed; the 5th (last) is not, so wx's
    # native "Failed to get data from the clipboard" dialog can still fire
    # exactly as it did before this retry loop existed.
    assert _FakeLogNull.instances == 4


def test_with_clipboard_read_retry_balances_open_and_close() -> None:
    """Guards against a clipboard-handle leak: every attempt that manages to
    open the clipboard must close it again, even attempts that ultimately
    report failure."""
    wx = _make_wx(get_data_fail_times=2)

    def action() -> bool:
        clipboard = wx.TheClipboard
        if not clipboard.Open():
            return False
        try:
            data = wx.TextDataObject()
            return clipboard.GetData(data)
        finally:
            clipboard.Close()

    assert with_clipboard_read_retry(wx, action, max_attempts=10, delay=0.0) is True
    assert wx.TheClipboard.open_calls == wx.TheClipboard.close_calls == 3


def test_no_clipboard_attribute_returns_empty_string() -> None:
    """Defensive: a wx stub with no TheClipboard (as some test doubles use)
    must not raise."""

    class _NoClipboardWx:
        pass

    assert read_clipboard_text(_NoClipboardWx()) == ""
