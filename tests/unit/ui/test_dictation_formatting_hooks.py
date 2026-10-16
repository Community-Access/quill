"""Bold, italic and headings by voice reach each editor's own command (D-23).

The controller asks the document port two optional questions --
``formatting()`` and ``apply_style()`` -- and the port asks its host. These
pin the three hosts' answers without building an editor: QUILL runs
``format.<style>`` through its registry and says the outcome only for markup
(rich text speaks for itself), QUILL Lite runs its own ``cmd_<style>`` in a rich
document only, and neither runs anything in plain text.
"""

from __future__ import annotations

from typing import Any

from quill.apps.lite_window_dictation import DocumentDictationMixin
from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin
from quill.ui.windows_dictation_ports import EditorDocument


class _Registry:
    def __init__(self) -> None:
        self.ran: list[str] = []

    def run(self, command_id: str) -> None:
        self.ran.append(command_id)


class _Quill(WindowsDictationCommandsMixin):
    def __init__(self, mode: str, markup: str | None) -> None:
        self.commands = _Registry()
        self._mode = mode
        self._markup = markup

    def _current_editor_mode(self) -> str:
        return self._mode

    def _active_markup_surface(self) -> str | None:
        return self._markup


def test_quill_uses_its_own_commands_and_speaks_only_for_markup() -> None:
    rich = _Quill("rich", None)
    assert rich._dictation_formatting() == "rich"
    assert rich._dictation_apply_style("bold") == ""
    assert rich.commands.ran == ["format.bold"]
    markdown = _Quill("text", "markdown")
    assert markdown._dictation_formatting() == "markdown"
    assert markdown._dictation_apply_style("heading_2") == "Heading 2."
    plain = _Quill("text", None)
    assert plain._dictation_formatting() == ""
    assert plain._dictation_apply_style("italic") is None
    assert plain.commands.ran == []


class _Editor:
    def __init__(self, mode: str) -> None:
        self.mode = mode


class _Lite(DocumentDictationMixin):
    def __init__(self, mode: str) -> None:
        self.editor = _Editor(mode)
        self.ran: list[str] = []

    def cmd_bold(self) -> None:
        self.ran.append("bold")


def test_quill_lite_formats_only_a_rich_document() -> None:
    rich = _Lite("rich")
    assert rich._dictation_formatting() == "rich"
    assert rich._dictation_apply_style("bold") == ""
    assert rich._dictation_apply_style("no_such_style") is None
    assert rich.ran == ["bold"]
    plain = _Lite("plain")
    assert plain._dictation_formatting() == ""
    assert plain._dictation_apply_style("bold") is None
    assert plain.ran == []


class _Control:
    def __init__(self) -> None:
        self.selected: tuple[int, int] | None = None

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.selected = (start, end)


class _Host:
    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.after = 0

    def _dictation_formatting(self) -> str:
        return "rich"

    def _dictation_apply_style(self, _style: str) -> Any:
        return self.answer

    def _dictation_after_edit(self) -> None:
        self.after += 1


def test_the_editor_port_selects_the_words_then_asks_its_host() -> None:
    control, host = _Control(), _Host("")
    port = EditorDocument(host, control)
    assert port.formatting() == "rich"
    assert port.apply_style("bold", 3, 9) == ""
    assert control.selected == (3, 9) and host.after == 1
    refused = EditorDocument(_Host(None), _Control())
    assert refused.apply_style("bold", 0, 1) is None
    background = EditorDocument(host, control, background=True)
    assert background.formatting() == ""  # a live transcript is never formatted
