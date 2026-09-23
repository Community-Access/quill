"""No test's scratch edit is left behind in tracked source.

Some gates can only be tested honestly by running the real command line against
the real tree, which means briefly editing a tracked file and putting it back.
``tests/unit/tools/test_gate_entry_points.py`` does exactly that to prove the
network-egress gate goes red on an unreviewed call site, and it restores the
file in a ``finally``.

A ``finally`` does not run when the process is killed. On 2026-09-23 a pytest
run was superseded mid-window and the scratch key stayed in
``quill/tools/network_egress_entries.py``, where it renamed a real reviewed
entry. The consequences were nasty out of proportion to the cause: the egress
gate went red, the failure pointed at ``core/audio/url_import.py`` (a file
nobody had touched), the bogus diff read as somebody's deliberate edit, and the
scorecard had passed minutes earlier so the two facts looked unrelated.

This test is the thirty-second version of that diagnosis. It does not prevent
the residue -- only not editing the tree could -- but it names the cause the
moment anything runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]

#: (marker, the file it belongs to, the test that writes it). Keep in step with
#: the tests that make scratch edits; a new one belongs here on the day it lands.
_RESIDUE: tuple[tuple[str, str, str], ...] = (
    (
        "core/nowhere.py::gone",
        "quill/tools/network_egress_entries.py",
        "tests/unit/tools/test_gate_entry_points.py::"
        "test_the_egress_gate_fails_when_a_site_is_unreviewed",
    ),
)


@pytest.mark.parametrize(("marker", "relative", "culprit"), _RESIDUE)
def test_no_scratch_edit_survived_in_tracked_source(
    marker: str, relative: str, culprit: str
) -> None:
    path = _REPO / relative
    assert path.exists(), f"{relative} moved; update this guard"
    assert marker not in path.read_text(encoding="utf-8"), (
        f"{relative} still carries the scratch marker {marker!r}, left by "
        f"{culprit} being killed before it could restore the file. Nothing is "
        f"wrong with the source itself -- run 'git checkout -- {relative}' and "
        f"the egress gate goes green again."
    )
