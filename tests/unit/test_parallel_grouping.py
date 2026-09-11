"""What the parallel-run grouping does, as opposed to what it intends.

``tests/conftest.py`` puts every test marked ``machine_global`` into one
``xdist_group`` so ``-n 8 --dist loadgroup`` runs them on a single worker. They
drive a resource the *machine* owns rather than the process -- the Windows
clipboard, the system-wide ``RegisterHotKey`` table, the screen-reader COM
bridges -- and two workers using one of those at once is not slow, it is wrong.

This file exists because the grouping has been silently wrong twice, in opposite
directions, and each failure was invisible from the outside:

* **Marked up and ignored** (2026-08 to 2026-09-10): the hook ran after xdist's
  own, which had already rewritten every nodeid to ``<nodeid>@<group>``, so the
  mark reached the scheduler too late. All eight workers ran UI tests, and the
  only symptom was a clipboard test that "flaked" under ``-n``.
* **Real but too coarse**: making the hook ``tryfirst`` while the group was
  "everything under ``tests/unit/ui``" put 3,606 wx tests on one worker, and the
  suite ran every test and never exited -- no summary, processes alive.

Both are now assertable, because the group is a *marker* rather than a
directory: the ordering is real and the group is small. So this file asserts
what it could only describe before.

What it deliberately does **not** assert is that a parallel run always finishes.
It usually does now, where before it never did -- but a worker can still die with
``node down: Not properly terminated`` somewhere in the wx/UI tests, and that
predates this change and is unrelated to it. See ``tests/conftest.py`` for the
measurements. The serial run is the authoritative one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.conftest as suite_conftest

_TESTS = Path(__file__).resolve().parent


def _collect(*paths: Path) -> dict[str, list[str]]:
    """Collect for real and read back each item's ``xdist_group``."""

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
        [*(str(path) for path in paths), "--collect-only", "-q", "-p", "no:cacheprovider"],
        plugins=[_Probe()],
    )
    assert result == 0, "the probe collection itself failed"
    assert _Probe.groups, "nothing was collected; has the layout moved?"
    return dict(_Probe.groups)


def test_a_machine_global_test_joins_the_shared_group() -> None:
    groups = _collect(_TESTS / "ui" / "test_clip_library_dialog.py")
    assert groups
    assert all(group == [suite_conftest.MACHINE_GLOBAL_GROUP] for group in groups.values()), groups


def test_an_ordinary_ui_test_keeps_its_own_file_and_fans_out() -> None:
    """The half the old all-of-``tests/unit/ui`` rule got wrong.

    Most of that directory mocks ``wx.TheClipboard`` rather than using it, and
    serialising it bought nothing while costing the suite its ability to finish.
    """
    groups = _collect(_TESTS / "ui" / "test_menu_routes.py")
    assert groups
    for nodeid, group in groups.items():
        assert group and group[0] != suite_conftest.MACHINE_GLOBAL_GROUP, nodeid
        assert group[0].endswith("test_menu_routes.py"), nodeid


def test_a_non_ui_test_keeps_its_own_file_too() -> None:
    groups = _collect(_TESTS / "core" / "test_paths.py")
    assert all(group and group[0].endswith("test_paths.py") for group in groups.values()), groups


def test_the_hook_runs_before_xdists_own() -> None:
    """The one-word fact that made the mark reach the scheduler at all.

    xdist reads ``xdist_group`` in its own ``pytest_collection_modifyitems``
    (``xdist/remote.py`` rewrites each nodeid to ``<nodeid>@<group>`` and the
    scheduler splits on that suffix). Without ``tryfirst`` here the mark is
    added after that rewrite and is simply never seen -- which looks exactly
    like a working grouping and is not one.
    """
    hook = suite_conftest.pytest_collection_modifyitems
    # ``@pytest.hookimpl`` stores its options on the function as ``pytest_impl``.
    # The version of this test that read ``pytestmark`` instead was reading an
    # attribute that is never set here, so it could only ever pass -- which is
    # how "the hook is not tryfirst" stayed asserted while nobody could tell.
    options = getattr(hook, "pytest_impl", {})
    assert options.get("tryfirst"), (
        "tests/conftest.py's collection hook must be tryfirst, or xdist never "
        f"sees the group and every worker runs machine-global tests at once: {options}"
    )


def test_the_shared_group_stays_small_enough_to_shut_down() -> None:
    """The other half: 3,606 wx tests on one worker hung its shutdown every time.

    A file count rather than a test count, because the count is the thing a
    reviewer can check against the list in the conftest docstring, and because
    the failure mode is "somebody marked a whole directory again".
    """
    here = Path(__file__).resolve()
    marked = sorted(
        path.relative_to(_TESTS).as_posix()
        for path in _TESTS.rglob("test_*.py")
        if path != here
        and "pytestmark = pytest.mark.machine_global" in path.read_text(encoding="utf-8")
    )
    assert marked, "nothing is marked machine_global; the grouping does nothing"
    assert len(marked) <= 12, (
        "too many files are serialized onto one worker. Concentrating wx/COM "
        f"objects there is what hung the suite in 2026-09. Marked: {marked}"
    )


def test_every_marked_file_says_why_it_is_marked() -> None:
    """A mark with no reason is one nobody can ever remove."""
    for path in _TESTS.rglob("test_*.py"):
        if path == Path(__file__).resolve():
            continue  # this file quotes the marker line; it does not carry it
        text = path.read_text(encoding="utf-8")
        if "pytestmark = pytest.mark.machine_global" not in text:
            continue
        before = text.split("pytestmark = pytest.mark.machine_global")[0]
        assert "#: Serialized onto one worker" in before, path.name
