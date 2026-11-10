"""W6: the Workbench is where Tools > WordPress leads, with the classic windows a choice."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.menu import LAYER_KEYS, TOOLS_ROWS  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.core.wordpress.workbench_flag import workbench_window_enabled  # noqa: E402
from quill.core.wordpress.workbench_options import load_options  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402


def test_open_wordpress_workbench_is_first_in_tools_wordpress_with_a_key() -> None:
    rows = TOOLS_ROWS[1].rows  # type: ignore[union-attr]
    assert rows[0] == ("wordpress.workbench", "Open WordPress Workbench...", "cmd_workbench")
    assert LAYER_KEYS["H"] == "wordpress.workbench"


bench = _bench


def test_workbench_options_turn_the_classic_windows_on_and_off(bench, monkeypatch) -> None:
    monkeypatch.delenv("QUILL_WORDPRESS_WORKBENCH_WINDOW", raising=False)
    from quill.ui.workbench_frame import NodeRef

    bench.select(NodeRef("", "start"))
    base = bench.provider._data_dir
    assert workbench_window_enabled(base=base)
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [0])
    bench.run(command("options"))
    assert load_options(base).classic_windows
    assert not workbench_window_enabled(base=base)
    assert any("classic windows" in s for s in bench.said)
    monkeypatch.setattr(wdlg, "ask_checks", lambda *a, **k: [])
    bench.run(command("options"))
    assert workbench_window_enabled(base=base)


def test_the_editor_row_always_opens_the_workbench(monkeypatch) -> None:
    from quill.ui import wordpress_workbench_window as window
    from quill.ui.wordpress_commands import WordPressCommands

    opened: list[Any] = []
    monkeypatch.setattr(window, "open_workbench", lambda commands, **kw: opened.append(kw))
    monkeypatch.setenv("QUILL_WORDPRESS_WORKBENCH_WINDOW", "0")

    class _Host:
        def announce(self, _text: str) -> None:
            pass

    fake = type("C", (), {"host": _Host(), "_data_dir": None})()
    WordPressCommands.cmd_workbench(fake)  # type: ignore[arg-type]
    assert opened and opened[0]["data_dir"] is None
