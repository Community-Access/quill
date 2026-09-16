"""Three small defects that each hid behind something invisible.

**The F8 marker could not be cancelled, in either editor** (bad.md L4). Press
F8, change your mind, and there was no way out: QUILL's Escape cleared *extend
mode* and left the anchor sitting there, QuillLite's ``cancel_extend_selection``
had no callers at all, and pressing F8 again silently MOVED the marker rather
than dropping it. The state is invisible, so it was also impossible to tell
which of those had happened. Escape drops it now, in both, and says so.

**A literal accelerator claimed a key the keymap had given away** (bad.md H4).
``Open User Guide`` carried ``Ctrl+F1`` as text after a tab in its menu label,
outside the keymap entirely -- so it was absent from the generated reference,
unreachable from the Keyboard Manager, and deaf to a rebinding. Harmless until
``help.key_cheatsheet`` gained the ``Ctrl+F1`` alias QuillLite uses, at which
point two menu items claimed one key and one of them silently stopped firing.
No gate could see it, because a literal in a label is not a binding.

**QuillLite told people the wrong key** (bad.md R10). "Press Control Shift M to
switch to rich text" -- but Ctrl+Shift+M is a *ring* (plain, Markdown, HTML,
rich), so one press from a plain document lands on Markdown. The method that
said it has a docstring explaining that advice which is wrong half the time is
worse than none.
"""

from __future__ import annotations

from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP

# -- H4: the literal accelerator ------------------------------------------------


def test_open_user_guide_has_a_real_binding_rather_than_a_literal() -> None:
    from pathlib import Path

    assert DEFAULT_KEYMAP["help.open_user_guide"] == "Ctrl+Shift+F1"
    source = Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8")
    assert "\\tCtrl+F1" not in source, (
        "a literal accelerator is invisible to the keymap, the reference and "
        "every gate; route it through _menu_label instead"
    )


def test_ctrl_f1_is_claimed_once() -> None:
    """It was claimed twice the moment the cheatsheet alias landed."""
    owners = [c for c, chord in DEFAULT_KEYMAP.items() if chord == "Ctrl+F1"]
    owners += [f"{c} (alias)" for c, chord in DEFAULT_ALIASES.items() if chord == "Ctrl+F1"]
    assert owners == ["help.key_cheatsheet (alias)"], owners


def test_f1_belongs_to_the_command_whose_docstring_answers_it() -> None:
    """F1 was claimed by a literal AND by an alias, so one of them never fired.

    The alias was added on the premise that "F1 was bound to nothing at all in
    QUILL". F1 was in fact answered -- by a literal in a menu label, which is
    invisible to the keymap, the generated reference and the Keyboard Manager.
    It now belongs to show_help_on_control, which is what it always did, and
    which is also QuillLite's F1 and the GATE-<APP>-HELP contract.
    """
    owners = [c for c, chord in DEFAULT_KEYMAP.items() if chord == "F1"]
    owners += [f"{c} (alias)" for c, chord in DEFAULT_ALIASES.items() if chord == "F1"]
    assert owners == ["help.help_on_control"], owners
    # And the command it was taken from keeps its own chord.
    assert DEFAULT_KEYMAP["help.context_help"].startswith("Ctrl+Shift+Grave")


def test_no_menu_label_in_quill_carries_a_literal_tab_accelerator() -> None:
    """The class of defect, not just the one instance."""
    import re
    from pathlib import Path

    for module in ("quill/ui/main_frame_menu.py", "quill/ui/main_frame_format_codes.py"):
        source = Path(module).read_text(encoding="utf-8")
        # A label ending in \t<chord> is a native accelerator wx will parse.
        literals = re.findall(r'_\("([^"]*\\t[^"]*)"\)', source)
        # The stock clipboard verbs are wx ID_* items whose accelerator IS the
        # label by convention; they have no keymap command to render from.
        allowed = {"Cu&t\\tCtrl+X", "&Copy\\tCtrl+C", "&Paste\\tCtrl+V", "Select &All\\tCtrl+A"}
        offenders = [text for text in literals if text not in allowed]
        assert offenders == [], f"{module} carries literal accelerators: {offenders}"


# -- L4: the marker that could not be cancelled ---------------------------------


class _Editor:
    def __init__(self, text: str = "hello world") -> None:
        self._text = text

    def GetValue(self) -> str:  # noqa: N802 - wx API shape
        return self._text

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return 3


class _QuillHost:
    """The three attributes SelectionSpanMixin.cancel_selection_anchor uses."""

    def __init__(self, anchor: int | None) -> None:
        self.editor = _Editor()
        self._selection_anchor = anchor
        self.announced: list[str] = []

    def _announce_result(self, message: str) -> None:
        self.announced.append(message)


def _quill_cancel(host: _QuillHost) -> bool:
    from quill.ui.main_frame_selection_span import SelectionSpanMixin

    return SelectionSpanMixin.cancel_selection_anchor(host)


def test_quill_escape_drops_a_waiting_marker_and_says_so() -> None:
    host = _QuillHost(anchor=7)
    assert _quill_cancel(host) is True
    assert host._selection_anchor is None
    assert host.announced == ["Selection marker dropped"]


def test_quill_cancel_reports_false_when_no_marker_is_waiting() -> None:
    """Escape belongs to everything else too, so it must carry on."""
    host = _QuillHost(anchor=None)
    assert _quill_cancel(host) is False
    assert host.announced == []


def test_quill_escape_handler_asks_the_canceller() -> None:
    from pathlib import Path

    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    assert "self.cancel_selection_anchor()" in source, (
        "Escape must drop the F8 marker, not only clear extend mode"
    )


def test_quilllite_cancel_reports_whether_it_did_anything() -> None:
    import inspect

    from quill.apps.lite_window_selection import DocumentSelectionMixin

    signature = inspect.signature(DocumentSelectionMixin.cancel_extend_selection)
    # A string, because the module uses "from __future__ import annotations".
    assert signature.return_annotation in (bool, "bool")


def test_quilllite_escape_is_wired_to_the_canceller() -> None:
    """It had NO callers outside tests, and a test asserted Escape never reached it."""
    from pathlib import Path

    source = Path("quill/apps/lite_window_typing.py").read_text(encoding="utf-8")
    assert "self.cancel_extend_selection()" in source
    assert "wx.WXK_ESCAPE" in source


# -- R10: the wrong key in the message -------------------------------------------


def test_quilllite_no_longer_promises_one_press_to_rich_text() -> None:
    from pathlib import Path

    source = Path("quill/apps/lite_window_format.py").read_text(encoding="utf-8")
    assert "Press Control Shift M to switch to rich text" not in source
    assert "Press Control Shift M for rich text" not in source
    assert "cycles" in source, "say that the key is a ring, since that is what it is"


def test_the_ring_really_does_have_four_stops() -> None:
    """The reason the old message was wrong, asserted rather than assumed."""
    from quill.apps.lite_window_markup import DOCUMENT_KINDS

    assert len(DOCUMENT_KINDS) == 4
    assert DOCUMENT_KINDS[0] == ("plain", "plain")
    assert DOCUMENT_KINDS[-1][0] == "rich"
