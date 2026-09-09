"""What the wx/UI test grouping actually does, as opposed to what it intends.

``tests/conftest.py`` marks every test under ``tests/unit/ui`` with one shared
``xdist_group`` so ``-n 8 --dist loadgroup`` would run them on a single worker:
they drive real wx widgets against per-machine global resources -- the Windows
clipboard, ``RegisterHotKey``, the screen-reader COM bridges -- and eight
workers doing that at once produced native worker crashes in 2026-08.

**The grouping does not currently take effect**, and the one-word fix for it
makes the suite hang instead. The full reasoning is in that conftest's
docstring; the short version is that xdist reads the mark in *its own*
``pytest_collection_modifyitems`` (rewriting the nodeid to ``<nodeid>@<group>``,
which is what the scheduler splits on), so ours has to run first -- and making
it run first concentrates 3,606 wx tests in one worker whose shutdown then never
completes. Measured twice: every test ran, zero failures, no summary, processes
still alive.

So this file does two things and deliberately not a third:

* it checks the mark **is** applied, which is true, cheap, and the half that
  would silently rot if the rule were edited;
* it records the hook-ordering fact as an executable note, so the next person
  who "fixes" the ordering finds out here why it was left alone;
* it does **not** assert the ordering, because the state that assertion would
  demand is one where the suite does not terminate.

If somebody makes the grouping both real and terminating -- most likely by
grouping only the tests that genuinely touch global resources rather than all of
``tests/unit/ui`` -- this file is where the assertion belongs.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import tests.conftest as suite_conftest

_UI_DIR = Path(__file__).resolve().parent / "ui"


def test_every_ui_test_is_put_in_the_one_shared_group() -> None:
    """Collect for real and check the mark, rather than re-deriving the rule."""

    class _Probe:
        groups: dict[str, list[str]] = {}

        @pytest.hookimpl(trylast=True)
        def pytest_collection_modifyitems(
            self, config: pytest.Config, items: list[pytest.Item]
        ) -> None:
            for item in items:
                _Probe.groups[item.nodeid] = [
                    mark.args[0] for mark in item.iter_markers("xdist_group") if mark.args
                ]

    result = pytest.main(
        [
            str(_UI_DIR / "test_clip_library_dialog.py"),
            str(Path(__file__).resolve().parent / "core" / "test_paths.py"),
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        plugins=[_Probe()],
    )
    assert result == 0, "the probe collection itself failed"
    assert _Probe.groups, "nothing was collected; has the layout moved?"

    ui = {node: g for node, g in _Probe.groups.items() if "/ui/" in node.replace("\\", "/")}
    other = {node: g for node, g in _Probe.groups.items() if node not in ui}
    assert ui, "no UI tests collected"
    assert other, "no non-UI tests collected; the contrast is the point"

    assert all(g == ["wx-ui"] for g in ui.values()), (
        f"UI tests must all carry the 'wx-ui' group: {sorted({tuple(g) for g in ui.values()})}"
    )
    assert all(g and g[0] != "wx-ui" for g in other.values()), (
        "non-UI tests must keep their own per-file group so they still fan out"
    )


def test_the_hook_ordering_caveat_is_still_written_down() -> None:
    """The mark is applied and still ignored, and that has to stay documented.

    Not an assertion about the ordering itself: making this hook ``tryfirst``
    is what would honour the group, and doing that hangs the suite at shutdown
    (17,821 of 17,823 results, zero failures, no summary, workers alive). This
    checks only that the explanation has not been quietly deleted, because a
    grouping that looks deliberate and does nothing is exactly what cost a
    session's worth of chasing a "flaky" clipboard test.
    """
    hook = suite_conftest.pytest_collection_modifyitems
    marks = [m for m in getattr(hook, "pytestmark", []) if getattr(m, "name", "") == "hookimpl"]
    ordered_first = any(m.kwargs.get("tryfirst") for m in marks)

    doc = inspect.getdoc(hook) or ""
    if ordered_first:
        pytest.fail(
            "tests/conftest.py's collection hook is now tryfirst, so the wx-ui "
            "group is real. If the suite terminates, delete this test and "
            "assert the ordering in the one above; if it still hangs at "
            "shutdown, this is the regression the docstring warns about."
        )
    assert "KNOWN BROKEN" in doc and "never exits" in doc, (
        "The grouping is marked up but not in effect, and the docstring must "
        "keep saying so -- including that making it effective hangs the suite. "
        "Without that, the next person applies the one-word fix and loses a day."
    )
