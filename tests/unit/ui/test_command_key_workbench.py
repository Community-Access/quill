"""Say or Type a Command inside a Workbench window (command-key.md 13.12).

F11 in the GitHub or the WordPress Workbench runs that window's commands,
through the window's own dispatcher (so its write gate), and nothing typed
leaves the computer. The real GitHub Workbench frame is used where it can be;
the WordPress window is its menu bar over a recorder.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.command_catalogue import Risk, rows_for_app  # noqa: E402
from quill.core.command_catalogue.policy import NOT_HERE_MESSAGE  # noqa: E402
from quill.core.github.permissions import AccessLevel  # noqa: E402
from quill.core.github.workbench_window_menu import WINDOW_MENU as GITHUB_MENU  # noqa: E402
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS  # noqa: E402
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS  # noqa: E402
from quill.core.wordpress.workbench_window_menu import GO_NODES as WP_GO  # noqa: E402
from quill.core.wordpress.workbench_window_menu import WINDOW_MENU as WP_MENU  # noqa: E402
from quill.core.wordpress.workbench_window_menu import WORDPRESS_KEYS  # noqa: E402
from quill.core.workbench.menus import all_rows  # noqa: E402
from quill.ui import command_key_ui  # noqa: E402
from quill.ui.command_key_workbench import (  # noqa: E402
    WorkbenchRegistry,
    workbench_command_key,
)
from tests.unit.ui import test_github_workbench_tools as _tools  # noqa: E402

bench = _tools.bench  # the window over a recorded API, shared with the tools tests


def _typed(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    said = iter(answers)
    monkeypatch.setattr(command_key_ui, "ask_for_command", lambda *_a, **_k: next(said, None))


def test_both_workbenches_have_the_family_keys_on_their_help_menus() -> None:
    for keys, prefix in ((WORKBENCH_KEYS, "github"), (WORDPRESS_KEYS, "wordpress")):
        assert keys[f"{prefix}.workbench.command_key"] == "F11"
        assert keys[f"{prefix}.workbench.what_can_i_say_here"] == "Ctrl+Alt+Shift+F1"


def test_every_row_is_on_its_windows_bar_or_is_the_batch_still_to_land() -> None:
    bars = {"github_workbench": GITHUB_MENU, "wordpress_workbench": WP_MENU}
    for app, bar in bars.items():
        ids = {row.command_id for _menu, row in all_rows(bar)}
        missing = [s.id for s in rows_for_app(app) if s.id not in ids]
        # GitHub's Plain-Language Batch arrives with its own pull request (#1960);
        # until then its row is simply not offered in that window.
        assert missing in ([], ["github.workbench.plain_batch"]), app


def test_no_row_sends_to_github_by_itself() -> None:
    """A write is reached only by a window that previews it, never run outright."""
    for spec in rows_for_app("github_workbench"):
        need = COMMAND_REQUIREMENTS.get(spec.id)
        if need and need[0] != "local":
            assert spec.kind.value == "opens_dialog", spec.id
        assert spec.risk is Risk.SAFE


def test_f11_in_the_github_workbench_goes_where_it_is_asked(bench, monkeypatch) -> None:
    _typed(monkeypatch, "show the pull requests")
    workbench_command_key(bench)
    assert bench.current.key == "pulls"


def test_a_sentence_passes_the_write_gate_like_the_menu(bench, monkeypatch) -> None:
    provider = bench.provider
    monkeypatch.setattr(provider, "access_level", lambda: AccessLevel.READ_ONLY)
    _typed(monkeypatch, "file a bug")
    workbench_command_key(bench)
    assert "this account is Read Only" in bench.said[-1]


def test_what_this_window_does_not_have_is_not_reached(bench, monkeypatch) -> None:
    ran: list[str] = []
    monkeypatch.setattr(bench, "run", ran.append)
    _typed(monkeypatch, "publish the post")
    workbench_command_key(bench)
    assert ran == []
    assert bench.said[-1] == NOT_HERE_MESSAGE or bench.said[-1].startswith("Not from a sentence")


def _wordpress_frame(said: list[str], ran: list[str]) -> Any:
    return SimpleNamespace(
        provider=SimpleNamespace(menu=WP_MENU, keymap_id="wordpress_workbench", go_nodes=WP_GO),
        frame=None,
        current=SimpleNamespace(key="posts"),
        _keys=dict(WORDPRESS_KEYS),
        _say=said.append,
        can_run=lambda _c: True,
        reason=lambda _c: "Not available here.",
        run=ran.append,
    )


def test_f11_in_the_wordpress_workbench_opens_its_plain_language_batch(
    monkeypatch, quill_data_dir
) -> None:
    said: list[str] = []
    ran: list[str] = []
    _typed(monkeypatch, "change many posts in words")
    workbench_command_key(_wordpress_frame(said, ran))
    assert ran == ["wordpress.workbench.plain_batch"]


def test_a_greyed_command_is_refused_with_the_windows_reason(monkeypatch) -> None:
    said: list[str] = []
    frame = _wordpress_frame(said, [])
    frame.can_run = lambda c: not c.endswith("rest_console")
    frame.reason = lambda _c: "Open a site first."
    registry = WorkbenchRegistry(frame)
    assert registry.get("wordpress.workbench.rest_console")
    assert registry.unavailable_reason("wordpress.workbench.rest_console") == "Open a site first."
    assert registry.unavailable_reason("wordpress.workbench.go_posts") == ""
    assert registry.get("github.workbench.go_issues") is None
    assert registry.keybinding_for("wordpress.workbench.plain_batch") == "Ctrl+Alt+B"
