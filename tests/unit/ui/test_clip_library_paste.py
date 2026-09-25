"""Recent Clips pastes where the caret is, on Enter (bad.md C9, P3.5).

QUILL Lite's Recent Clips inserts the clip at the caret and closes. QUILL's Clip
Library put the clip on the *system clipboard* and left the dialog open, so
reaching a remembered clip took Enter, Escape and then Ctrl+V -- three keys for
the verb the dialog exists to perform, and a silent overwrite of whatever the
person had in the clipboard on the way past.

Copy to Clipboard stays: it is a real second verb (hand this to another app),
just not the one Enter should mean.
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame_clip_library import ClipLibraryMixin

SOURCE = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "clip_library_dialog.py"
).read_text(encoding="utf-8")


class _Editor:
    def __init__(self, text: str, caret: int) -> None:
        self.text = text
        self.caret = caret

    def WriteText(self, text: str) -> None:
        self.text = self.text[: self.caret] + text + self.text[self.caret :]
        self.caret += len(text)

    def GetValue(self) -> str:
        return self.text

    def SetFocus(self) -> None:
        self.focused = True


class _Document:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class _Host(ClipLibraryMixin):
    def __init__(self) -> None:
        self.editor = _Editor("ab", caret=1)
        self.document = _Document()
        self.announced: list[str] = []
        self.results: list[str] = []
        self.frame = None

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _announce_result(self, message: str) -> None:
        self.results.append(message)

    def _set_status(self, message: str) -> None:
        pass


def test_the_clip_lands_at_the_caret() -> None:
    host = _Host()
    host._paste_clip_at_caret("X")
    assert host.editor.text == "aXb"
    assert host.document.text == "aXb"


def test_an_empty_clip_writes_nothing() -> None:
    host = _Host()
    host._paste_clip_at_caret("")
    assert host.editor.text == "ab"
    assert host.results == []


def test_the_paste_is_announced_because_nothing_else_says_it() -> None:
    host = _Host()
    host._paste_clip_at_caret("hello")
    assert host.results == ["Pasted 5 characters from the Clip Library"]


def test_enter_on_a_clip_pastes_rather_than_copying() -> None:
    assert "apply_listbox_activation(self._listbox, lambda _e: self._on_paste(_e))" in SOURCE


def test_the_dialog_takes_a_paste_callback_and_offers_a_button() -> None:
    assert "paste_cb: Callable[[str], None] | None = None" in SOURCE
    assert 'label="&Paste at the Cursor"' in SOURCE


def test_promote_gives_up_p_so_paste_can_have_it() -> None:
    # GATE-14: one Alt letter, one control, per window.
    assert 'label="Promote to Copy &Tray..."' in SOURCE


def test_open_clip_library_hands_the_dialog_a_paste_callback() -> None:
    source = (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_clip_library.py"
    ).read_text(encoding="utf-8")
    assert "paste_cb=self._paste_clip_at_caret" in source


def test_pasting_closes_the_dialog() -> None:
    # The clip is in the document; leaving the dialog up means the next key
    # goes to a list instead of the text the person just pasted into.
    assert "self.dialog.EndModal(wx.ID_OK)" in SOURCE
