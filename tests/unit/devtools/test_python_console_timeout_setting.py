"""``console_python_timeout`` stops a runaway console command (question 38).

The setting was drawn in Settings and read by nothing, so ``while True: pass``
froze QUILL. These tests run real console commands on this thread -- the same
thread arrangement as the UI -- and show the limit changes what happens.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

from quill.core.script_results import ScriptError, ScriptSuccess
from quill.devtools.python_console import PythonConsole
from quill.devtools.python_timeout import ConsoleTimedOut, run_with_timeout


def _console(seconds: float) -> PythonConsole:
    host = SimpleNamespace(settings=SimpleNamespace(console_python_timeout=seconds))
    return PythonConsole({}, settings_host=host)


def test_a_runaway_loop_is_stopped_at_the_limit() -> None:
    console = _console(0.3)
    started = time.monotonic()
    result = console.execute("while True:\n    pass\n")
    assert isinstance(result, ScriptError)
    assert result.message == "Stopped after 0.3 seconds."
    assert "Python console execution timeout" in (result.suggestion or "")
    assert time.monotonic() - started < 5


def test_a_scripts_own_except_exception_cannot_swallow_the_stop() -> None:
    console = _console(0.3)
    source = "while True:\n    try:\n        pass\n    except Exception:\n        pass\n"
    assert isinstance(console.execute(source), ScriptError)


def test_a_longer_limit_lets_the_same_work_finish() -> None:
    # 0.6 s of busy work: stopped under a 0.2 s limit, finishes under 10 s.
    source = "import time\nend = time.monotonic() + 0.6\nwhile time.monotonic() < end:\n    pass\n"
    assert isinstance(_console(0.2).execute(source), ScriptError)
    assert isinstance(_console(10).execute(source), ScriptSuccess)


def test_the_limit_is_read_live_for_each_command() -> None:
    settings = SimpleNamespace(console_python_timeout=10)
    console = PythonConsole({}, settings_host=SimpleNamespace(settings=settings))
    assert console.timeout_seconds() == 10
    settings.console_python_timeout = 45
    assert console.timeout_seconds() == 45


def test_no_settings_falls_back_to_the_thirty_second_default() -> None:
    assert PythonConsole({}).timeout_seconds() == 30.0


def test_a_finished_command_leaves_nothing_pending_on_the_thread() -> None:
    assert run_with_timeout(lambda: 7, 0.05) == 7
    # Well past the limit: a stray interruption would land here.
    try:
        end = time.monotonic() + 0.3
        while time.monotonic() < end:
            pass
    except ConsoleTimedOut:  # pragma: no cover - the failure this guards against
        raise AssertionError("timeout fired after the command had finished") from None
