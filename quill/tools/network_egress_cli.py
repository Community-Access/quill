"""The network-egress gate's command line.

Its own module because the audit module was at its GATE-11 ceiling, and
because the two are genuinely different things: the audit *walks the source
tree* and answers a question, and this *is a gate* -- it decides what an exit
code and a printed line should be. The first changes almost never; the second
is where the wording lives.

**Why this had to be written at all.** ``platform_report`` runs
``python -m quill.tools.network_egress_audit`` and reads its exit code. The
audit module defined :func:`~quill.tools.network_egress_audit.find_unreviewed_egress`
and had no ``__main__`` block, so under ``-m`` it imported, defined its
functions, and exited 0 -- and the "network-egress" row on the scorecard
reported green without checking anything. The unit tests did call the helper,
so nothing shipped unreviewed; what was lost was the fast gate somebody runs
before pushing, and the meaning of a green row. Found 2026-08-24 by adding an
egress site (the ACB Media schedule) and watching the gate stay green.
:mod:`tests/unit/tools/test_gate_entry_points.py` now fails on a third one.
"""

from __future__ import annotations

from quill.tools.network_egress_audit import discover_egress_sites, find_unreviewed_egress


def main() -> int:
    """Green when every discovered call site has a reviewed entry, red otherwise.

    Both directions are reported: a site with no entry (somebody added a
    network call and did not write down why), and an entry with no site (the
    call went away and its justification outlived it, which is how a reviewed
    set stops describing the program).
    """
    missing, stale = find_unreviewed_egress()
    if not missing and not stale:
        print(f"Network egress: {len(discover_egress_sites())} site(s), all reviewed.")
        return 0
    for site in sorted(missing):
        print(
            f"UNREVIEWED {site}: a new outbound call with no entry in "
            "_REVIEWED_EGRESS. Add one saying what it fetches, what reaches it, "
            "and what Safe Mode does."
        )
    for site in sorted(stale):
        print(f"STALE {site}: reviewed, but no such call site exists any more.")
    return 1


if __name__ == "__main__":  # pragma: no cover - the gate's entry point
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover - the gate's entry point
    raise SystemExit(main())
