"""Rich bold says which way it went, and rich documents have an outline.

bad.md R8 and R12, the QUILL half of P1.17.

R8: `Ctrl+B` announced "Bold" in both directions, so the one thing the
keystroke decided -- on or off -- was the one thing it did not say, and a
listener with no visual feedback had to type a character to find out.

R12: an `.rtf` or `.docx` tab has no markup, so `_effective_markup_kind()`
calls it "plain" and the Outline Navigator refused it -- for the one kind of
document whose headings are real paragraph styles rather than characters.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.outline import OutlineEntry
from quill.ui.main_frame import MainFrame
from quill.ui.main_frame_rich_mode import RichModeMixin


class _Wrapper:
    def __init__(self, *, state: bool = True, headings=()) -> None:
        self.state = state
        self.headings = list(headings)
        self.toggled: list[str] = []

    def toggle_font_attr(self, attr: str) -> bool:
        self.toggled.append(attr)
        return self.state

    def all_headings(self):
        return list(self.headings)


class _Host(RichModeMixin):
    def __init__(self, *, mode: str = "rich", wrapper: _Wrapper | None = None) -> None:
        self._mode = mode
        self._wrapper = wrapper
        self.status: list[str] = []
        self.announced: list[str] = []

    def _current_editor_mode(self) -> str:
        return self._mode

    def _active_richedit(self):
        return self._wrapper

    def _mark_rich_formatting_dirty(self) -> None:
        pass

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.status.append(message)

    def _announce(self, message: str) -> None:
        self.announced.append(message)


def test_bold_on_says_on() -> None:
    host = _Host(wrapper=_Wrapper(state=True))
    assert host._rich_toggle_run_attr("apply_bold") is True
    assert host.announced == ["Bold on"]


def test_bold_off_says_off() -> None:
    host = _Host(wrapper=_Wrapper(state=False))
    host._rich_toggle_run_attr("apply_bold")
    assert host.announced == ["Bold off"]


def test_italic_and_underline_answer_the_same_way() -> None:
    for method, label in (("apply_italic", "Italic"), ("apply_underline", "Underline")):
        host = _Host(wrapper=_Wrapper(state=True))
        host._rich_toggle_run_attr(method)
        assert host.announced == [f"{label} on"]


def test_a_markup_document_falls_through_to_the_markup_path() -> None:
    host = _Host(mode="markup", wrapper=_Wrapper())
    assert host._rich_toggle_run_attr("apply_bold") is False
    assert host.announced == []


def test_the_three_commands_use_it() -> None:
    import inspect

    for name in ("format_bold", "format_italic", "format_underline"):
        source = inspect.getsource(getattr(MainFrame, name))
        assert "_rich_toggle_run_attr(" in source, name


class _OutlineHost(MainFrame):
    """Only the two methods the outline path needs."""

    def __init__(self, headings=(), *, mode: str = "rich") -> None:  # noqa: D107
        self._mode = mode
        self._wrapper = SimpleNamespace(all_headings=lambda: list(headings))

    def _current_editor_mode(self) -> str:
        return self._mode

    def _active_richedit(self):
        return self._wrapper


def test_a_rich_document_has_an_outline() -> None:
    host = _OutlineHost(headings=[(0, 1, "Title"), (40, 2, "Section")])
    entries = host._outline_entries()
    assert entries == [
        OutlineEntry(level=1, title="Title", position=0),
        OutlineEntry(level=2, title="Section", position=40),
    ]


def test_a_markup_document_still_reads_its_markup() -> None:
    host = _OutlineHost(headings=[], mode="markup")
    host.editor = SimpleNamespace(GetValue=lambda: "# One" + chr(10) + "## Two")
    host._effective_markup_kind = lambda: "markdown"  # type: ignore[method-assign]
    entries = host._outline_entries()
    assert [e.title for e in entries] == ["One", "Two"]


def test_a_readback_failure_is_not_an_outline_crash() -> None:
    def _boom():
        raise RuntimeError("the TOM is gone")

    host = _OutlineHost()
    host._wrapper = SimpleNamespace(all_headings=_boom)
    assert host._rich_headings() == []


def test_the_navigator_no_longer_refuses_a_rich_document() -> None:
    import inspect

    source = inspect.getsource(MainFrame.open_outline_navigator)
    assert 'if markup_kind == "plain" and not self._rich_headings():' in source
