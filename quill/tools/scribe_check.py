"""One command to check Scribe for Documents in every QUILL app.

    python -m quill.tools.scribe_check                    # offline: no network, no credit
    python -m quill.tools.scribe_check --replay <run>     # the same suite on an earlier run
    python -m quill.tools.scribe_check --live quick       # a live run first, then the suite
    python -m quill.tools.scribe_check --live full --yes --cap 500

Offline (the default), it runs the whole Scribe suite: our own fixtures and
the fake Scribe server (every app's entry point, the F1 to F8 shapes, the
sentences), and, when Pneuma's corpus is on this computer, its replays and
the opens-and-reads table -- every app that receives each format opens and
reads every file. Nothing is sent anywhere.

``--live`` hands over to :mod:`quill.tools.scribe_live_run`, which prints
the plan, asks before sending anything, collects every file into a dated
folder outside the repository and then runs this same suite on it.

The result is said first, then each app and each format, then any failure,
as plain sentences. ``scripts\\scribe-check.bat`` runs the offline check
from a double-click and keeps the window open.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

from quill.tools.scribe_live.replay import Replay, run_replay, run_suite
from quill.tools.scribe_live.sources import DEFAULT_PNEUMA

Say = Callable[[str], None]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m quill.tools.scribe_check",
        description="Check Scribe for Documents in every QUILL app: offline by default.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", choices=("quick", "full"), help="a live run first (uses credit)")
    mode.add_argument("--replay", type=Path, metavar="RUN", help="the suite on an earlier run")
    parser.add_argument("--pneuma", type=Path, default=DEFAULT_PNEUMA, help="Pneuma's corpus")
    parser.add_argument("--yes", action="store_true", help="with --live: start without asking")
    parser.add_argument("--cap", type=int, default=None, help="with --live: most conversions")
    parser.add_argument("--out", type=Path, default=None, help="with --live: the runs folder")
    parser.add_argument("--dry-run", action="store_true", help="with --live: the plan only")
    return parser


def report(replay: Replay, say: Say, *, what: str) -> int:
    """The result first, then by app and by format, then each failure."""
    if not replay.ran:
        say(f"Scribe check could not run: {replay.note}")
        return 1
    passed, failed = replay.count("passed"), replay.count("failed")
    skipped = replay.count("skipped")
    if failed:
        first = f"Scribe check failed, {what}: {failed} of {passed + failed} tests failed, "
        first += f"{passed} passed"
    else:
        every = f"all {passed}" if passed > 1 else f"{passed} of {passed}"
        first = f"Scribe check passed, {what}: {every} tests passed"
    if skipped:
        first += f", {skipped} skipped"
    say(first + ".")
    for line in replay.sentences()[1:]:
        say(line)
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None, *, say: Say = print) -> int:
    args = _parser().parse_args(argv)
    if args.live:
        from quill.tools import scribe_live_run

        forward = ["--profile", args.live, "--pneuma", str(args.pneuma)]
        forward += ["--yes"] if args.yes else []
        forward += ["--dry-run"] if args.dry_run else []
        forward += ["--cap", str(args.cap)] if args.cap is not None else []
        forward += ["--out", str(args.out)] if args.out is not None else []
        return scribe_live_run.main(forward, say=say)
    if args.replay:
        say(f"Running the Scribe suite on {args.replay}. This takes a few minutes.")
        return report(run_replay(args.replay, say), say, what="on that run's files")
    corpus = args.pneuma if (args.pneuma / "validation.json").is_file() else None
    if corpus is None:
        say(
            "Pneuma's corpus was not found, so only our own fixtures run. The opens-and-reads "
            f"table needs the corpus, or a run folder given with --replay. Looked in {args.pneuma}."
        )
    say("Running the offline Scribe suite. Nothing is sent anywhere. This takes a few minutes.")
    with tempfile.TemporaryDirectory(prefix="scribe-check-") as out:
        replay = run_suite(corpus, Path(out), say)
    what = "offline with Pneuma's corpus" if corpus else "offline with our own fixtures only"
    return report(replay, say, what=what)


if __name__ == "__main__":
    sys.exit(main())
