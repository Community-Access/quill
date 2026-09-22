"""Tests that QDC execution results are announced to screen readers.

These tests pin the requirement from PRD §7.3:
- stdout output short enough to speak is announced verbatim.
- Long output is summarized (line count) rather than flood-spoken.
- Errors are announced with the "Error:" prefix.
- Silent success (no output, no return value) announces "Done."
- Result values are announced with the "Result:" prefix.

The five tests that actually run a script take ``quill_data_dir``: running one
appends to the console history under the data directory, and without isolation
that is the developer's own ``%APPDATA%\Quill\console\history.jsonl``. It
was, silently, until the profile guard in ``tests/conftest.py`` learned to watch
``pathlib`` writes on 2026-09-21.
"""

from __future__ import annotations

from quill.core.script_results import ScriptError, ScriptSuccess
from quill.ui.main_frame_devtools import DevToolsMixin


class _FakeWin:
    def __init__(self) -> None:
        self.transcript: list[str] = []
        self.status: str = ""

    def append_transcript(self, text: str) -> None:
        self.transcript.append(text)

    def set_status(self, text: str) -> None:
        self.status = text


class _FakeDT(DevToolsMixin):
    """Minimal stub that exposes only what DevToolsMixin needs."""

    def __init__(self) -> None:
        self._announcements: list[str] = []
        self._win = _FakeWin()

    def _announce(self, text: str) -> None:
        self._announcements.append(text)

    def _dt_window(self) -> _FakeWin:  # type: ignore[override]
        return self._win

    # ConsoleHost stubs (not exercised here, just satisfy the call signature)
    def console_get_editor_text(self) -> str:
        return ""

    def console_set_editor_text(self, text: str) -> None:
        pass

    def console_get_selected_text(self) -> str:
        return ""

    def console_replace_selection(self, text: str) -> None:
        pass

    def console_goto_line(self, line: int) -> None:
        pass

    def console_goto_offset(self, offset: int) -> None:
        pass

    def console_get_document_name(self) -> str:
        return "test.txt"

    def console_run_command(self, command_id: str) -> None:
        pass

    def console_command_exists(self, command_id: str) -> bool:
        return False

    def console_list_commands(self, query):
        return []

    def console_announce(self, text: str) -> None:
        self._announce(text)

    def console_get_last_announcements(self) -> list[str]:
        return []

    def console_document_stats(self) -> dict:
        return {}


def _dt() -> _FakeDT:
    return _FakeDT()


# ---------------------------------------------------------------------------
# Output announcement tests


def test_short_stdout_is_announced_verbatim(quill_data_dir):
    dt = _dt()
    result = ScriptSuccess(value=None, output="hello world\n")
    dt._dt_ts_done(result, "print('hello world')", dt._win)
    assert any("hello world" in ann for ann in dt._announcements)


def test_long_stdout_is_summarized_not_flood_spoken(quill_data_dir):
    dt = _dt()
    many_lines = "\n".join(f"line {i}" for i in range(20))
    result = ScriptSuccess(value=None, output=many_lines)
    dt._dt_ts_done(result, "q.list_commands()", dt._win)
    # Must NOT speak all 20 lines
    full_flood = any(all(f"line {i}" in ann for i in range(20)) for ann in dt._announcements)
    assert not full_flood
    # Must announce a summary with the line count
    assert any("lines" in ann.lower() and "transcript" in ann.lower() for ann in dt._announcements)


def test_silent_success_announces_done(quill_data_dir):
    dt = _dt()
    result = ScriptSuccess(value=None, output="")
    dt._dt_ts_done(result, "q.goto_line(1)", dt._win)
    assert any("Done" in ann or "done" in ann for ann in dt._announcements)


def test_result_value_announced_with_prefix(quill_data_dir):
    dt = _dt()
    result = ScriptSuccess(value=42, output="")
    dt._dt_ts_done(result, "1 + 41", dt._win)
    assert any("Result" in ann and "42" in ann for ann in dt._announcements)


def test_error_announced_with_error_prefix(quill_data_dir):
    dt = _dt()
    result = ScriptError(message="NameError: name 'foo' is not defined")
    dt._dt_ts_done(result, "foo", dt._win)
    assert any(ann.startswith("Error:") for ann in dt._announcements)
    assert any("NameError" in ann for ann in dt._announcements)


def test_python_short_stdout_announced():
    """Python execution: print('hello') must be announced, not just transcribed."""
    from quill.devtools.python_console import PythonConsole

    dt = _dt()
    py = PythonConsole({})
    result = py.execute("print('hello from python')")
    # Simulate what _dt_on_execute_python does with the result
    if result.output:  # type: ignore[union-attr]
        dt._win.append_transcript(result.output)  # type: ignore[union-attr]
        dt._dt_announce_output(result.output)  # type: ignore[union-attr]
    assert any("hello from python" in ann for ann in dt._announcements)


def test_python_long_output_summarized():
    from quill.devtools.python_console import PythonConsole

    dt = _dt()
    py = PythonConsole({})
    result = py.execute("for i in range(30): print(f'item {i}')")
    assert isinstance(result, ScriptSuccess), f"Expected ScriptSuccess, got: {result}"
    if result.output:
        dt._dt_announce_output(result.output)
    assert any("lines" in ann.lower() for ann in dt._announcements)
    # Must NOT speak 30 individual lines
    assert not any(all(f"item {i}" in ann for i in range(10)) for ann in dt._announcements)


# ---------------------------------------------------------------------------
# announce_output threshold test


def test_announce_output_boundary_exactly_3_lines():
    dt = _dt()
    output = "a\nb\nc"  # exactly 3 lines, short
    dt._dt_announce_output(output)
    assert dt._announcements == ["a\nb\nc"]


def test_announce_output_boundary_4_lines_gets_summary():
    dt = _dt()
    output = "a\nb\nc\nd"  # 4 lines
    dt._dt_announce_output(output)
    assert any("lines" in ann.lower() for ann in dt._announcements)
    assert not any(ann == "a\nb\nc\nd" for ann in dt._announcements)


def test_announce_output_long_single_line_gets_summary():
    dt = _dt()
    output = "x" * 200  # > 150 chars
    dt._dt_announce_output(output)
    assert any("lines" in ann.lower() for ann in dt._announcements)


def test_announce_output_empty_is_silent():
    dt = _dt()
    dt._dt_announce_output("   \n  ")
    assert dt._announcements == []
