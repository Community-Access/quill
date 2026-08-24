"""Every gate on the scorecard actually runs something.

``platform_report`` runs each gate as ``python -m quill.tools.<name>`` and reads
its exit code. A module with no ``if __name__ == "__main__"`` block does not run
its checks under ``-m``: it imports, defines its functions, and exits 0. The
scorecard then prints **pass**, and the row is a lie -- not a wrong answer, but
a claim that something was verified when nothing was.

Two rows were like this until 2026-08-24, found by adding an egress site and
watching the gate stay green:

* **network-egress** -- ``find_unreviewed_egress`` existed and nothing called
  it from the command line, so an unreviewed outbound call site passed the gate.
  Its command line now lives in ``network_egress_cli`` (the audit module was at
  its GATE-11 ceiling), and the scorecard points at that.
* **binding-labels** -- ``run_checks`` existed, and the same.

Both were still covered by the *suite*, so nothing shipped broken. What was
lost is the gate somebody runs before pushing, and the meaning of a green
scorecard. This test is the thing that would have caught it on the first one.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REPORT = REPO / "quill" / "tools" / "platform_report.py"

#: Gates whose check is genuinely a no-op import (there are none, and adding
#: one should require saying why in this list rather than in a silent pass).
EXEMPT: frozenset[str] = frozenset()


def _module_gates() -> list[str]:
    """Every ``python -m quill.tools.X`` the scorecard shells out to."""
    source = REPORT.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'"-m",\s*"(quill\.tools\.[A-Za-z_]+)"', source)))


def test_the_scorecard_shells_out_to_gates_at_all() -> None:
    """If this finds none, the pattern changed and the rest of this file is
    checking a thing that no longer exists."""
    assert len(_module_gates()) > 10


def test_every_gate_module_has_an_entry_point() -> None:
    """A gate with no ``__main__`` block exits 0 without checking anything."""
    missing = []
    for name in _module_gates():
        if name in EXEMPT:
            continue
        path = REPO / Path(name.replace(".", "/") + ".py")
        assert path.exists(), f"{name} is on the scorecard and does not exist"
        if '__name__ == "__main__"' not in path.read_text(encoding="utf-8"):
            missing.append(name)
    assert missing == [], (
        "these gates report pass without running anything under 'python -m': " + ", ".join(missing)
    )


def test_the_egress_gate_fails_when_a_site_is_unreviewed(tmp_path: Path) -> None:
    """The specific regression: the gate must go red on a new outbound call.

    Driven through the real command line rather than through
    ``find_unreviewed_egress``, because the helper was never the broken part --
    the wiring to it was, and only running the module the way the scorecard
    runs it can tell the difference.
    """
    entries = REPO / "quill" / "tools" / "network_egress_entries.py"
    original = entries.read_bytes()
    text = original.decode("utf-8")
    first = re.search(r'^    "([^"]+)": \(', text, re.MULTILINE)
    assert first is not None, "the entries table changed shape"
    try:
        entries.write_bytes(
            text.replace(f'"{first.group(1)}": (', '"core/nowhere.py::gone": (', 1).encode("utf-8")
        )
        result = subprocess.run(
            [sys.executable, "-m", "quill.tools.network_egress_cli"],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
    finally:
        entries.write_bytes(original)

    assert result.returncode == 1, "an unreviewed egress site must fail the gate"
    assert "UNREVIEWED" in result.stdout
    assert "STALE" in result.stdout


def test_the_egress_gate_passes_on_a_clean_tree() -> None:
    """And it must not be red for its own sake -- a gate that always fails is
    a gate people learn to skip."""
    result = subprocess.run(
        [sys.executable, "-m", "quill.tools.network_egress_cli"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all reviewed" in result.stdout


def test_the_binding_label_gate_runs_and_says_so() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "quill.tools._check_binding_label_consistency"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip(), "a gate that prints nothing cannot be told from one that ran"
