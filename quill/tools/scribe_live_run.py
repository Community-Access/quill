"""The Scribe for Documents live regression run (docs/qa/scribe-live-regression.md).

Sign in to Scribe for Documents in QUILL first (Tools, Scribe for Documents,
Sign In). Then, from the repository root::

    python -m quill.tools.scribe_live_run --profile quick --dry-run   # the plan, nothing sent
    python -m quill.tools.scribe_live_run --profile quick              # asks before sending
    python -m quill.tools.scribe_live_run --profile full --yes --cap 500

    python -m quill.tools.scribe_live_run --replay-only D:\\scribe-corpus\\runs\\2026-11-24-0930
    python -m quill.tools.scribe_live_run --compare-only <run folder> [--baseline <folder>]
    python -m quill.tools.scribe_live_run --resume <run folder> --yes
    python -m quill.tools.scribe_live_run --clean-up <run folder> --yes

Before anything is sent the plan is printed (uploads, conversions, the two
ways credit may be counted, and pages), and nothing is sent without
``--yes`` or a typed ``yes``. Outputs go to a dated folder outside the
repository (``--out``, default ``D:\\scribe-corpus\\runs``), the run's
documents are deleted from the account afterwards, the replay suite runs
against the folder, and the run is compared with the previous one (or with
Pneuma's corpus). It never runs in CI: it needs Jeff's own sign-in, which it
reuses from QUILL's credential store and never reads, prints or keeps.

The console says everything as plain sentences, summary first: no tables,
no spinners, progress as an occasional line. Exit 0 when everything went as
planned, 1 when something failed, broke or did not replay, 2 when the run
stopped before sending anything.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.tools.scribe_live import LiveRunError
from quill.tools.scribe_live.compare import (
    SIZE_THRESHOLD,
    compare_runs,
    comparison_sentences,
    find_baseline,
    write_comparison,
)
from quill.tools.scribe_live.execute import Executor, Usage, delete_uploaded, family_queue_busy
from quill.tools.scribe_live.layout import (
    copy_sources,
    finish_record,
    load_record,
    new_record,
    save_record,
    write_readme,
    write_validation,
)
from quill.tools.scribe_live.plan import (
    PROFILES,
    QUICK,
    Conversion,
    Plan,
    Upload,
    build_plan,
    plan_details,
    plan_sentences,
)
from quill.tools.scribe_live.replay import Replay, run_replay
from quill.tools.scribe_live.sources import (
    DEFAULT_OURS,
    DEFAULT_PNEUMA,
    DEFAULT_RUNS,
    REPO_ROOT,
    Found,
    find_sources,
    is_inside,
)

Say = Callable[[str], None]
EXIT_OK, EXIT_FAILED, EXIT_STOPPED = 0, 1, 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m quill.tools.scribe_live_run",
        description="Convert test documents through the real Scribe for Documents, collect "
        "everything, replay it through every app, and compare with the last run.",
    )
    parser.add_argument("--profile", choices=PROFILES, default=QUICK)
    parser.add_argument("--dry-run", action="store_true", help="print the plan; send nothing")
    parser.add_argument("--list", action="store_true", help="also list every upload")
    parser.add_argument("--yes", action="store_true", help="start without asking")
    parser.add_argument("--cap", type=int, default=None, help="at most this many conversions")
    parser.add_argument("--out", type=Path, default=DEFAULT_RUNS, help="the runs folder")
    parser.add_argument("--sources", type=Path, default=DEFAULT_OURS, help="our test documents")
    parser.add_argument(
        "--pneuma", type=Path, default=DEFAULT_PNEUMA, help="Pneuma's extracted corpus folder"
    )
    parser.add_argument("--baseline", type=Path, default=None, help="compare with this folder")
    parser.add_argument("--size-threshold", type=float, default=SIZE_THRESHOLD)
    parser.add_argument("--keep-in-account", action="store_true", help="do not delete afterwards")
    parser.add_argument("--no-replay", action="store_true", help="skip the replay suite")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--replay-only", type=Path, metavar="RUN", help="replay a finished run")
    group.add_argument("--compare-only", type=Path, metavar="RUN", help="compare a finished run")
    group.add_argument("--resume", type=Path, metavar="RUN", help="continue a stopped run")
    group.add_argument("--clean-up", type=Path, metavar="RUN", help="delete a run's documents")
    return parser


class _Scribe:
    """QUILL's stored sign-in and client; built only when a live call is due."""

    def __init__(self, session: Any = None, client_factory: Any = None, opener: Any = None):
        self._session = session
        self._client_factory = client_factory
        self.channel_opener = opener

    @property
    def session(self) -> Any:
        if self._session is None:
            from quill.core.scribe.auth import ScribeSession

            self._session = ScribeSession()
        return self._session

    def client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory()
        from quill.core.scribe.client import ScribeClient

        return ScribeClient(self.session, base_url=self.session.base_url)

    def ready(self) -> str:
        """Why no live call can be made now, or ``""``."""
        from quill.core import scribe

        reason = scribe.unavailable_reason("QUILL")
        if reason:
            return reason
        if not self.session.is_signed_in():
            return (
                "You are not signed in to Scribe for Documents. Sign in from QUILL (Tools, "
                "Scribe for Documents, Sign In), then run this again."
            )
        return family_queue_busy()


def main(
    argv: Sequence[str] | None = None,
    *,
    scribe: _Scribe | None = None,
    say: Say = print,
    ask: Callable[[str], str] = input,
    interactive: bool | None = None,
    executor_options: dict[str, Any] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    scribe = scribe or _Scribe()
    interactive = sys.stdin.isatty() if interactive is None else interactive
    try:
        if args.replay_only:
            return _replay_only(args.replay_only, say)
        if args.compare_only:
            return _compare_only(args, args.compare_only, say)
        if args.clean_up:
            return _clean_up(args, scribe, say, ask, interactive)
        return _run(args, scribe, say, ask, interactive, executor_options or {})
    except LiveRunError as error:
        say(error.args[0] if error.args else "The live run stopped.")
        return EXIT_STOPPED


def _confirm(
    args: argparse.Namespace, ask: Callable[[str], str], live: bool, question: str, act: str
) -> None:
    """Nothing is sent or deleted without ``--yes`` or a typed yes."""
    if args.yes:
        return
    if not live:
        raise LiveRunError(
            "Nothing was sent. A live run needs --yes, or yes typed at the prompt in a "
            "console window."
        )
    answer = ask(f"{question} Type yes and press Enter to {act}, or just press Enter to stop: ")
    answer = answer.strip().lower()
    if answer == "y":
        raise LiveRunError("You typed y, not yes, so nothing was sent.")
    if answer != "yes":
        raise LiveRunError("Stopped. Nothing was sent to Scribe.")


def _run(
    args: argparse.Namespace,
    scribe: _Scribe,
    say: Say,
    ask: Callable[[str], str],
    interactive: bool,
    options: dict[str, Any],
) -> int:
    found = find_sources(args.sources, args.pneuma)
    if args.resume:
        record = load_record(args.resume)
        if record is None:
            raise LiveRunError(f"{args.resume} has no run.json, so it is not a run to resume.")
        plan = plan_from_record(record, found)
        run_dir = args.resume
        say(
            f"Resuming the run of {run_dir.name}: {plan.upload_count} uploads are left to "
            f"send, for {plan.conversion_count} conversions."
        )
    else:
        if is_inside(args.out, REPO_ROOT):
            raise LiveRunError(
                f"{args.out} is inside the repository. Runs are kept outside it; choose "
                "another folder with --out."
            )
        plan = build_plan(found, args.profile, cap=args.cap)
        if not plan.uploads:
            raise LiveRunError("There is nothing to send: no test documents were found.")
        if args.dry_run:
            say("Dry run: this is the plan only, and nothing will be sent to Scribe.")
        for line in plan_sentences(plan, found):
            say(line)
        if args.list:
            for line in plan_details(plan):
                say(line)
        if args.dry_run:
            say("End of the dry run. Nothing was sent.")
            return EXIT_OK
        run_dir = args.out / datetime.now().strftime("%Y-%m-%d-%H%M")
        record = None
    reason = scribe.ready()
    if reason:
        raise LiveRunError(reason)
    question = (
        f"Send {plan.upload_count} uploads to Scribe now, for {plan.conversion_count} conversions?"
    )
    _confirm(args, ask, interactive, question, "start")
    if record is None:
        run_dir.mkdir(parents=True, exist_ok=False)
        record = new_record(plan, found, run_dir)
        save_record(run_dir, record)
        copy_sources(run_dir, plan)
    executor = Executor(
        run_dir, record, client_factory=scribe.client, channel_opener=scribe.channel_opener,
        say=say, **options,
    )  # fmt: skip
    say(f"Starting. Every file goes to {run_dir}.")
    notes: list[str] = []
    if args.resume:
        for upload in plan.uploads:
            job_id = next(e["job_id"] for e in record["uploads"] if e["name"] == upload.name)
            if upload.source.password and job_id:
                executor.service.provide_password(job_id, upload.source.password)
    else:
        notes += executor.preflight(plan)
        for line in notes:
            say(line)
        executor.queue_plan(plan)
    usage = executor.run(plan)
    notes = executor.after()
    if executor.stopped:
        record["stopped"] = executor.stopped
    elif not args.keep_in_account:
        notes += executor.clean_up()
    finish_record(record)
    save_record(run_dir, record)
    remove_staging(run_dir)
    write_validation(run_dir, record)
    write_readme(run_dir, record, found)
    return _finish(args, run_dir, record, usage, notes, say)


def _finish(
    args: argparse.Namespace,
    run_dir: Path,
    record: dict[str, Any],
    usage: Usage,
    notes: list[str],
    say: Say,
) -> int:
    baseline = args.baseline or find_baseline(args.out, run_dir, args.pneuma)
    comparison = compare_runs(run_dir, baseline, size_threshold=args.size_threshold)
    write_comparison(run_dir, comparison)
    replay = Replay(False, note="it was turned off with --no-replay.")
    if not args.no_replay:
        say("Running the replay suite against this run's folder. This takes a few minutes.")
        replay = run_replay(run_dir)
    record["replay"] = {"summary": replay.summary(), "failed": replay.count("failed")}
    record["comparison"] = {"baseline": comparison.baseline, "breaks": len(comparison.breaks)}
    save_record(run_dir, record)
    planned = sum(len(e["conversions"]) for e in record["uploads"] if e["expect"] == "converts")
    not_planned = [e for e in record["uploads"] if e.get("outcome", "") not in ("as planned",)]
    failed = bool(not_planned or comparison.breaks or replay.count("failed"))
    failed = failed or bool(usage.defaults_changed) or (not replay.ran and not args.no_replay)
    say("")
    say(_first_sentence(record, usage, planned, replay, len(comparison.breaks), failed))
    say(_usage_sentence(usage))
    if not_planned:
        listed = "; ".join(
            f"{e['name']}, {e.get('outcome') or e['state']}" for e in not_planned[:10]
        )
        more = "; and more, in run.json." if len(not_planned) > 10 else "."
        say(f"{_count(len(not_planned), 'upload')} did not end as planned: {listed}{more}")
    for line in notes:
        say(line)
    for line in replay.sentences() if not replay.ran else replay.sentences()[1:]:
        say(line)
    for line in comparison_sentences(comparison):
        say(line)
    say(
        f"Everything is in {run_dir}. Start with README.md; the details are in "
        "comparison.md and replay.xml."
    )
    return EXIT_FAILED if failed else EXIT_OK


def _count(number: int, noun: str) -> str:
    return f"{number:,} {noun if number == 1 else noun + 's'}"


def _first_sentence(
    record: dict[str, Any], usage: Usage, planned: int, replay: Replay, breaks: int, failed: bool
) -> str:
    """The verdict first, then the three counts that decide it."""
    profile = record["profile"]
    if record.get("stopped"):
        return f"The {profile} live run stopped early: {record['stopped']}"
    got = usage.formats_collected
    if got == planned:
        collected = f"collected all {planned} planned files"
    else:
        collected = f"collected {got} of {planned} planned files"
    if breaks:
        compared = f"the comparison found {_count(breaks, 'change')} that could break QUILL"
    else:
        compared = "nothing changed that could break QUILL"
    verdict = "failed" if failed else "passed"
    text = f"The {profile} live run {verdict}: it {collected}, {_replay_phrase(replay)}, "
    text += f"and {compared}"
    if usage.defaults_changed:
        text += ", and the account's defaults changed"
    return text + "."


def _replay_phrase(replay: Replay) -> str:
    if not replay.ran:
        return "the replay suite did not run"
    passed, failed = replay.count("passed"), replay.count("failed")
    if not failed:
        return f"the replay suite passed all {passed} tests"
    return f"the replay suite passed {passed} of {passed + failed} tests"


def _usage_sentence(usage: Usage) -> str:
    text = (
        f"It uploaded {_count(usage.uploads, 'document')} and collected "
        f"{_count(usage.formats_collected, 'file')}."
    )
    if usage.pages_used is not None:
        text += (
            f" It used {_count(usage.pages_used, 'page')}: the account went from "
            f"{usage.pages_before:,} pages left to {usage.pages_after:,}."
        )
    if usage.deleted:
        were = "was" if usage.deleted == 1 else "were"
        text += f" {_count(usage.deleted, 'test document')} {were} deleted from the account."
    return text


def plan_from_record(record: dict[str, Any], found: Found) -> Plan:
    """The uploads of a recorded run that have not finished, to resume them."""
    by_file = {s.file: s for s in found.all}
    plan = Plan(str(record.get("profile", QUICK)))
    for entry in record.get("uploads", []):
        if entry.get("state") in ("done", "failed"):
            continue
        source = by_file.get(entry["source"])
        if source is None:
            raise LiveRunError(f"{entry['source']} is no longer among the test documents.")
        conversions = [Conversion(c["format"], c.get("label", "")) for c in entry["conversions"]]
        plan.uploads.append(
            Upload(replace(source), dict(entry["settings"]), conversions, entry["run_id"],
                   entry["name"])
        )  # fmt: skip
    return plan


def _replay_only(run_dir: Path, say: Say) -> int:
    replay = run_replay(run_dir)
    for line in replay.sentences():
        say(line)
    return EXIT_OK if replay.ran and not replay.count("failed") else EXIT_FAILED


def _compare_only(args: argparse.Namespace, run_dir: Path, say: Say) -> int:
    baseline = args.baseline or find_baseline(args.out, run_dir, args.pneuma)
    comparison = compare_runs(run_dir, baseline, size_threshold=args.size_threshold)
    write_comparison(run_dir, comparison)
    for line in comparison_sentences(comparison):
        say(line)
    return EXIT_FAILED if comparison.breaks else EXIT_OK


def _clean_up(
    args: argparse.Namespace,
    scribe: _Scribe,
    say: Say,
    ask: Callable[[str], str],
    interactive: bool,
) -> int:
    record = load_record(args.clean_up)
    if record is None:
        raise LiveRunError(f"{args.clean_up} has no run.json, so there is nothing to delete.")
    waiting = [e for e in record["uploads"] if e.get("document_id") and not e.get("deleted")]
    say(f"{_count(len(waiting), 'document')} of this run are still in the Scribe account.")
    if not waiting:
        return EXIT_OK
    reason = scribe.ready()
    if reason:
        raise LiveRunError(reason)
    question = f"Delete {_count(len(waiting), 'document')} from the Scribe account for good?"
    _confirm(args, ask, interactive, question, "delete")
    usage = Usage()
    notes = delete_uploaded(args.clean_up, record, scribe.client, usage)
    say(f"{_count(usage.deleted, 'document')} deleted for good.")
    for line in notes:
        say(line)
    return EXIT_FAILED if notes else EXIT_OK


def remove_staging(run_dir: Path) -> None:
    """The private queue and staging folders, once a run is finished with."""
    for name in (".staging",):
        shutil.rmtree(run_dir / name, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
