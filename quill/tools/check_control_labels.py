"""GATE-CTLLABEL: no control may ship with a name no screen reader will read.

The reason this gate exists, and the rule it enforces, are in
:mod:`quill.tools.control_label_scan` -- the short version is that on wxMSW a
plain control's accessible name comes from the ``wx.StaticText`` constructed
immediately before it in z-order, never from ``SetName``, and two edit fields in
``quill/ui/podcasts/add_podcast_dialog.py`` shipped announcing as bare "edit"
with careful ``SetName`` calls on both of them (``ba69898``).

This module is the half that decides pass or fail: it holds the snapshot, the
one-way ratchet over the backlog that already existed, and the command line.
The split happened when the scanner crossed GATE-11's default cap, and the seam
is the right one -- walking the tree and deciding an exit code are two jobs, the
same reason ``network_egress_audit`` and ``network_egress_cli`` are two modules.

The snapshot keys a site as ``<path>:<line>: <wx.Class>`` so every line it prints
can be pasted into an editor, and carries two things:

* ``reviewed`` -- one exact site mapped to the reason it is fine without a label
  (a single-column list whose column header is its name; a field labelled by a
  ``wx.StaticBox`` heading). The reason *is* the review.
* ``grandfathered`` plus ``high_water_mark`` -- the 165 offenders that existed
  when the gate landed. A new one fails the build; an old one waits its turn.
  The list may only shrink, which is what the mark makes assertable: appending
  an entry to silence the gate stops the two agreeing, so the only way through
  is to raise a number a reviewer will see. Same ratchet as
  ``module_size_budgets.json`` and the GATE-SETDOC backlog.

Matching against the backlog is deliberately **not** by line alone. It tries the
exact key first, then falls back to a per-``(file, control class)`` count, so an
edit elsewhere in a file does not resurrect its whole backlog as "new". A gate
that cries wolf after an unrelated edit is one people learn to regenerate
without reading, and this one is meant to be read.

Run it::

    python -m quill.tools.check_control_labels            # scorecard
    python -m quill.tools.check_control_labels --write     # regenerate snapshot
    python -m quill.tools.check_control_labels --list named-only
    python -m quill.tools.check_control_labels --list named-only --under quill/ui/podcasts
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Iterable

from quill.tools.control_label_scan import (
    LABELLED,
    NAMED_ONLY,
    OFFENDING,
    REPO_ROOT,
    REVIEWED,
    UNLABELLED,
    ControlSite,
    scan_control_sites,
)

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "control_labels.json"

_REGEN = "Regenerate with: python -m quill.tools.check_control_labels --write"


def load_snapshot() -> dict[str, object]:
    try:
        raw = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def apply_snapshot(sites: Iterable[ControlSite], snapshot: dict[str, object]) -> list[ControlSite]:
    """Re-classify the sites a human has already reviewed.

    Reviewed entries are keyed on the exact ``path:line`` spelling, unlike the
    grandfathered ratchet. That is deliberate: a reviewed entry is a claim about
    one specific construction ("this list's column header is its name"), and a
    claim that silently reattached to a different control after an edit would be
    a lie the gate told on the author's behalf.
    """
    reviewed = snapshot.get("reviewed")
    reasons = reviewed if isinstance(reviewed, dict) else {}
    out: list[ControlSite] = []
    for site in sites:
        reason = reasons.get(site.key)
        if isinstance(reason, str) and reason.strip():
            out.append(
                ControlSite(
                    path=site.path,
                    line=site.line,
                    kind=site.kind,
                    status=REVIEWED,
                    qualname=site.qualname,
                    reason=reason,
                )
            )
        else:
            out.append(site)
    return out


def offenders(sites: Iterable[ControlSite]) -> list[ControlSite]:
    """The sites that would fail the build if nothing were grandfathered."""
    return sorted(site for site in sites if site.status in OFFENDING)


def grandfathered_keys(snapshot: dict[str, object]) -> list[str]:
    stored = snapshot.get("grandfathered")
    return [str(item) for item in stored] if isinstance(stored, list) else []


def high_water_mark(snapshot: dict[str, object]) -> int:
    """The reviewed ceiling on the backlog: how many offenders are tolerated.

    Stored as a number as well as a list, because "the list may only shrink"
    cannot be checked against a file's own past. With both, appending an entry to
    silence the gate no longer works quietly -- the count stops matching, and the
    fix is to raise the number, which is a one-line diff a reviewer cannot miss.
    """
    mark = snapshot.get("high_water_mark")
    return mark if isinstance(mark, int) else len(grandfathered_keys(snapshot))


def _group_of(key: str) -> tuple[str, str]:
    """Recover ``(path, wx.Class)`` from a stored ``path:line: wx.Class`` key."""
    location, _, kind = key.partition(": ")
    path, _, _line = location.rpartition(":")
    return (path, kind.strip())


def new_offenders(live: Iterable[ControlSite], snapshot: dict[str, object]) -> list[ControlSite]:
    """Offenders the grandfathered backlog does not already account for.

    Matching happens twice: first on the exact key, so an untouched file reports
    exactly what it reported yesterday; then on ``(file, control class)`` count,
    so an edit elsewhere in the file that shifts every line does not resurrect
    the whole backlog as "new". Anything still unmatched is a genuine addition
    and fails the build.
    """
    stored = grandfathered_keys(snapshot)
    allowance = Counter(_group_of(key) for key in stored)
    exact = set(stored)

    remaining: list[ControlSite] = []
    for site in sorted(live):
        if site.key in exact and allowance[site.group] > 0:
            exact.discard(site.key)
            allowance[site.group] -= 1
        else:
            remaining.append(site)

    fresh: list[ControlSite] = []
    for site in remaining:
        if allowance[site.group] > 0:
            allowance[site.group] -= 1
        else:
            fresh.append(site)
    return fresh


def build_snapshot(sites: Iterable[ControlSite], previous: dict[str, object]) -> dict[str, object]:
    """The snapshot to commit: reviewed entries kept, backlog re-measured."""
    reviewed = previous.get("reviewed")
    keep = {
        str(key): str(value)
        for key, value in (reviewed.items() if isinstance(reviewed, dict) else [])
        if str(value).strip()
    }
    backlog = [site.key for site in offenders(sites)]
    # The mark is re-measured, not carried forward, so it falls with every fix.
    # Carrying the old maximum would leave a ceiling nobody could ever push
    # down, which is the one thing a ratchet must not do. Growth shows up as a
    # raised number in the diff -- the same conspicuous one-line change a raised
    # entry in ``module_size_budgets.json`` is.
    return {
        "_about": (
            "GATE-CTLLABEL. On wxMSW a control's accessible name comes from the "
            "wx.StaticText built immediately before it in z-order, never from "
            "SetName. 'reviewed' maps one exact site to the reason it is fine "
            "without one. 'grandfathered' is the backlog that existed when the "
            "gate landed; it may only shrink, and 'high_water_mark' is what "
            "makes that assertable. Regenerate with "
            "'python -m quill.tools.check_control_labels --write'."
        ),
        "high_water_mark": len(backlog),
        "reviewed": dict(sorted(keep.items())),
        "grandfathered": backlog,
    }


def write_snapshot(snapshot: dict[str, object]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(snapshot, indent=2, ensure_ascii=False)
    SNAPSHOT_PATH.write_text(body + "\n", encoding="utf-8", newline="\n")


def counts(sites: Iterable[ControlSite]) -> dict[str, int]:
    tally = Counter(site.status for site in sites)
    return {s: tally.get(s, 0) for s in (LABELLED, NAMED_ONLY, UNLABELLED, REVIEWED)}


def worst_files(sites: Iterable[ControlSite], limit: int = 10) -> list[tuple[str, int]]:
    """The files with the most offenders, so somebody knows where to start."""
    tally = Counter(site.path for site in offenders(sites))
    return sorted(tally.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]


def _explain(site: ControlSite) -> str:
    if site.status == NAMED_ONLY:
        return (
            "a name is written for this control and no screen reader will ever "
            "read it. Add a wx.StaticText built BEFORE the control."
        )
    return (
        "no label and no name: this announces as a bare role. Add a "
        "wx.StaticText built BEFORE the control."
    )


def _print_scorecard(sites: list[ControlSite], snapshot: dict[str, object]) -> None:
    """The accessible scorecard: counts first, then where to start.

    Counts before the list, because a reader who is listening to this needs the
    shape of the answer before the detail, and the detail is 165 lines long.
    """
    tally = counts(sites)
    backlog = grandfathered_keys(snapshot)
    print(f"Control labels (GATE-CTLLABEL): {len(sites)} control site(s) scanned.")
    print(f"  labelled (a static text precedes them):   {tally[LABELLED]}")
    print(f"  named-only (SetName written, never heard): {tally[NAMED_ONLY]}")
    print(f"  unlabelled (announces as a bare role):     {tally[UNLABELLED]}")
    print(f"  reviewed (classified with a reason):       {tally[REVIEWED]}")
    print(
        f"  grandfathered backlog: {len(backlog)} of a ceiling of "
        f"{high_water_mark(snapshot)} -- this number may only fall."
    )
    worst = worst_files(sites)
    if worst:
        print("  worst files, most offenders first:")
        for path, count in worst:
            print(f"    {count:4d}  {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the snapshot")
    parser.add_argument(
        "--list",
        dest="list_status",
        choices=sorted({LABELLED, NAMED_ONLY, UNLABELLED, REVIEWED}),
        help="list every site with one classification and exit 0",
    )
    parser.add_argument(
        "--under",
        default="",
        help="with --list, restrict to paths starting with this prefix",
    )
    args = parser.parse_args()

    snapshot = load_snapshot()
    skipped: list[str] = []
    sites = apply_snapshot(scan_control_sites(skipped=skipped), snapshot)
    for path in skipped:
        # Reported, never swallowed: a file the scan could not read is a file it
        # cannot vouch for, and quiet omission is the same class of mistake as a
        # name nobody hears.
        print(f"SKIPPED {path}: not parseable as Python, so nothing was checked in it.")

    if args.list_status:
        for site in sites:
            if site.status == args.list_status and site.path.startswith(args.under):
                print(f"{site.key}  ({site.qualname})")
        return 0

    if args.write:
        write_snapshot(build_snapshot(sites, snapshot))
        snapshot = load_snapshot()

    fresh = new_offenders(offenders(sites), snapshot)
    _print_scorecard(sites, snapshot)

    if fresh:
        print("")
        for site in fresh:
            print(f"UNNAMED {site.key} -- {_explain(site)}")
        print(
            f"{len(fresh)} control(s) need a label, or a reviewed entry with a "
            f"reason in {SNAPSHOT_PATH.relative_to(REPO_ROOT).as_posix()}."
        )
        print(_REGEN)
        return 1
    print("No new unnamed control. Every offender is grandfathered or reviewed.")
    return 0


if __name__ == "__main__":  # pragma: no cover - the gate's entry point
    raise SystemExit(main())
