"""A hang is not a failure (list.md 12.2).

``test_button_mnemonics`` once stalled entire runs through a deferred modal and
reported as **"still going"** rather than red. That is the worst shape a test
problem can take: a red test gets fixed, and a run that never ends gets
abandoned -- along with everything it would have told you about the other
sixteen thousand.

The ceiling that prevents it exists (``timeout = 30`` in ``pyproject.toml``,
via pytest-timeout) and was *measured* to catch both a plain sleep and a live
``wx.Dialog.ShowModal`` loop, which is the case that actually happened. What
did not exist was anything stopping somebody from removing it, raising it to
something useless, or losing it in a config merge -- so the guard rail had no
guard rail.

These are cheap, static checks. They do not hang anything to prove the point;
the hang-proving test is marked ``perf`` and runs on request, because a suite
that spends a minute demonstrating its own timeouts twice a day is paying real
money for a fact that changes about never.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

#: Above this a hang is indistinguishable from a slow test, and somebody
#: watching the run has already gone to do something else.
CEILING_MAX_SECONDS = 120
#: Below this an honest slow test starts failing for being honest.
CEILING_MIN_SECONDS = 10


def _pytest_config() -> dict:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["pytest"]["ini_options"]


def test_there_is_a_per_test_ceiling_at_all() -> None:
    """The whole point: a test that stops responding must go red, not quiet."""
    assert "timeout" in _pytest_config(), (
        "pyproject.toml has no pytest `timeout`, so a hung test stalls the run "
        "instead of failing it -- which is how one deferred modal once cost an "
        "entire suite (list.md 12.2)."
    )


def test_the_ceiling_is_a_useful_number() -> None:
    """Not so high it never fires, not so low it fails honest tests."""
    timeout = float(_pytest_config()["timeout"])

    assert CEILING_MIN_SECONDS <= timeout <= CEILING_MAX_SECONDS, (
        f"a {timeout}s per-test ceiling is not a ceiling anybody benefits from"
    )


def test_pytest_timeout_is_a_declared_dependency() -> None:
    """A ceiling in the config and no plugin to enforce it is a config that
    lies -- pytest ignores an unknown ini key with a warning nobody reads."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert "pytest-timeout" in text

    import pytest_timeout  # noqa: F401  -- installed here, not merely declared


def test_slow_tests_are_reported_before_they_reach_the_ceiling() -> None:
    """A test creeping from two seconds to twenty-nine is invisible without a
    durations floor, and then it is a failure rather than a warning."""
    addopts = _pytest_config().get("addopts", "")

    assert "--durations" in addopts, (
        "nothing reports the slowest tests, so the only signal that one is "
        "getting slower is the moment it hits the ceiling"
    )


def test_the_durations_floor_is_below_the_ceiling() -> None:
    """A floor at or above the ceiling reports nothing that has not already
    failed, which is a warning that arrives after the accident."""
    config = _pytest_config()
    addopts = str(config.get("addopts", ""))
    floor = 0.0
    for chunk in addopts.split():
        if chunk.startswith("--durations-min="):
            floor = float(chunk.split("=", 1)[1])

    assert 0 < floor < float(config["timeout"])


@pytest.mark.perf
@pytest.mark.timeout(CEILING_MAX_SECONDS * 2)
@pytest.mark.skipif(
    not os.environ.get("RUN_PERF"),
    reason="costs the ceiling in wall-clock; run with RUN_PERF=1",
)
def test_the_ceiling_actually_stops_a_hung_test() -> None:
    """Measured, not assumed -- and measured on the case that happened.

    A ``wx.Dialog.ShowModal`` with nothing to dismiss it is a native message
    loop, not a Python sleep, so a timeout implementation that only interrupts
    Python bytecode would sail straight past it. This runs pytest in a child
    process against a generated test and asserts the child dies red rather than
    running for ever.

    Skipped unless ``RUN_PERF=1``, and given twice the ceiling as its own
    timeout: proving a thirty-second ceiling takes thirty seconds, and a suite
    that pays that twice a day is buying a fact that changes about never. It
    also needs a longer limit than the thing it is measuring, or it would be
    killed by the very mechanism it exists to verify.
    """
    probe = REPO / "tests" / "unit" / "tools" / "_generated_hang_probe.py"
    probe.write_text(
        "import pytest\n\n"
        'wx = pytest.importorskip("wx")\n\n\n'
        "def test_hangs_in_a_modal_loop() -> None:\n"
        "    app = wx.App()\n"
        "    frame = wx.Frame(None)\n"
        "    wx.Dialog(frame, title='Probe').ShowModal()\n",
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(probe), "-q", "-p", "no:cacheprovider"],
            capture_output=True,
            text=True,
            cwd=REPO,
            timeout=CEILING_MAX_SECONDS,
        )
    finally:
        probe.unlink(missing_ok=True)

    assert result.returncode != 0, "a hung test must fail the run"
    assert "Timeout" in result.stdout + result.stderr
