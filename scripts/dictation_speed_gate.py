"""The dictation benchmark gate: every model QUILL can recommend keeps its word.

The recommendation (``quill.core.windows_dictation.model_advice``) picks a model
from two numbers per model: its cost, as a multiple of Moonshine tiny's speed
(``cost_factor``), and its measured word errors (``MEASURED``). Both came from
one machine run on real recordings (dictation design, sections 36 and 37). This
gate checks that they still hold, on the committed recordings in
``tests/corpus/dictation`` -- real people reading public-domain books for
LibriVox, catalogued after every model's training cutoff:

* **The advice keeps to its budget** (no models needed, every CI run):
  across a grid of computers, languages and priorities, the recommended model's
  pace -- this computer's Moonshine tiny times the model's cost -- is inside the
  0.25 one-thread budget, or twice it where two threads are allowed, unless the
  advice itself says it may lag; and it fits the memory the advice allows.
* **The models keep their numbers** (``--run``, the weekly workflow, which
  passes ``--report-only`` since 2026-10-24 -- see below): each
  recommendable model recognises the committed recordings on one thread. Its
  speed is compared with Moonshine tiny's *on the same machine in the same
  run*: a model must not cost more than :data:`SPEED_TOLERANCE` times its
  catalogue figure. The ratio is not machine-independent -- on GitHub's
  Windows runner (2026-10-23) the Parakeet models cost 6 to 7 times Moonshine
  tiny against about 4 on the measuring laptop -- so a failure here may be the
  processor rather than the model, and is a reason to re-measure, not to
  loosen the tolerance. Until the costs are re-measured on a real modest
  Windows computer (the B-8 check), the weekly run is ``--report-only``
  (Jeff, 2026-10-24): it reports every figure in the job summary and as
  warnings, and fails only on the advice's own budget rules, which stay a
  hard gate here and in every pull request. Its word
  errors must stay within :data:`ERROR_ALLOWANCE` points of the measured
  figure -- loose, because ten recordings are a smoke test, not a benchmark.

Usage::

    python scripts/dictation_speed_gate.py --list          # what can be recommended
    python scripts/dictation_speed_gate.py --fetch         # download those models
    python scripts/dictation_speed_gate.py --run           # measure them here
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from quill.core.windows_dictation import model_advice  # noqa: E402
from quill.core.windows_dictation.model_types import MEASURED  # noqa: E402
from quill.core.windows_dictation.speed_check import BUDGET, SpeedCheck  # noqa: E402

CORPUS = _REPO / "tests" / "corpus" / "dictation"
#: A model may run this many times its catalogue cost before the gate fails:
#: room for one machine's noise, not for a model that has become slower.
SPEED_TOLERANCE = 1.5
#: Percentage points of word errors above the measured figure that the ten
#: committed recordings may show before the gate fails.
ERROR_ALLOWANCE = 15.0
_LANGUAGES = ("en", "es")


def machines() -> list[SpeedCheck]:
    """Computers from the weakest QUILL supports to a fast one."""
    found = []
    for tiny in (0.03, 0.05, 0.07, 0.1, 0.12, 0.2):
        for cores in (2, 4, 8):
            for memory in (3.8, 7.8, 15.8, 31.8):
                found.append(SpeedCheck(tiny=tiny, cores=cores, memory_gb=memory))
    return found


def recommendations() -> list[tuple[SpeedCheck, str, str, model_advice.Recommendation]]:
    return [
        (check, language, priority, model_advice.recommend(check, language, priority=priority))
        for check in machines()
        for language in _LANGUAGES
        for priority, _label in model_advice.PRIORITIES
    ]


def recommendable() -> dict[str, set[str]]:
    """Every model the advice can name, and the languages it is named for."""
    found: dict[str, set[str]] = {}
    for _check, language, _priority, advice in recommendations():
        found.setdefault(advice.model_id, set()).add(language)
    return found


def costs(language: str) -> dict[str, float]:
    return {c.id: c.cost_factor for c in model_advice._candidates(language)}


def budget_problems() -> list[str]:
    """Recommendations that break the advice's own rules. Empty is a pass."""
    problems = []
    for check, language, priority, advice in recommendations():
        cost = costs(language)[advice.model_id]
        pace = (check.tiny or 0.0) * cost
        two_threads = priority == model_advice.PRIORITY_ACCURACY or (
            priority == model_advice.PRIORITY_BALANCED
            and not check.weak
            and (check.memory_gb or 0) >= 15.0
        )
        limit = 2 * BUDGET if two_threads else BUDGET
        where = f"{advice.model_id} for {language}/{priority} on {check}"
        if pace > limit and not advice.may_lag and not advice.built_in:
            problems.append(f"{where}: pace {pace:.3f} over its {limit} budget, unannounced")
        if MEASURED[advice.model_id].peak_mb > model_advice._memory_cap_mb(check):
            if not advice.built_in:
                problems.append(f"{where}: needs {MEASURED[advice.model_id].peak_mb} MB")
    return problems


# -- the run: real models on the committed recordings ------------------------ #


@dataclass
class Measurement:
    model_id: str
    language: str
    speed: float
    word_errors: float


def _measure(model_id: str, language: str) -> Measurement:
    import dictbench

    folder = CORPUS / language
    transcripts = dictbench.read_transcripts(folder)
    recognizer = dictbench.load_engine(model_id, language, threads=1)
    computing = audio = 0.0
    errors = words = 0
    for name, reference in transcripts.items():
        samples = dictbench.read_wav(folder / name)
        began = time.perf_counter()
        heard = dictbench.recognise(recognizer, samples)
        computing += time.perf_counter() - began
        audio += len(samples) / dictbench.RATE
        result = dictbench.score(name, reference, heard)
        errors, words = errors + result.errors, words + result.words
    return Measurement(model_id, language, computing / audio, 100 * errors / max(1, words))


def run_problems(report: list[str] | None = None) -> list[str]:
    """Measure every recommendable model here. Empty is a pass."""
    report = report if report is not None else []
    problems = []
    tiny = _measure("moonshine", "en").speed
    report.append(f"moonshine tiny: {tiny:.4f} s per second of speech, one thread")
    for model_id, languages in sorted(recommendable().items()):
        for language in sorted(languages):
            found = _measure(model_id, language)
            cost = costs(language)[model_id]
            ratio = found.speed / tiny
            measured: Any = MEASURED[model_id]
            expected = measured.word_errors if language == "en" else measured.word_errors_es
            report.append(
                f"{model_id} ({language}): {ratio:.1f} x tiny (catalogue {cost}), "
                f"{found.word_errors:.1f}% words wrong (measured {expected})"
            )
            if ratio > cost * SPEED_TOLERANCE:
                problems.append(
                    f"{model_id} ({language}) ran at {ratio:.1f} times Moonshine tiny; the "
                    f"catalogue says {cost}, so the advice may name a model that lags"
                )
            if expected is not None and found.word_errors > expected + ERROR_ALLOWANCE:
                problems.append(
                    f"{model_id} ({language}) got {found.word_errors:.1f}% of words wrong "
                    f"on the committed recordings, against {expected} measured"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="what the advice can recommend")
    parser.add_argument("--fetch", action="store_true", help="download those models")
    parser.add_argument("--run", action="store_true", help="measure them on this computer")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="--run: report the models' figures as warnings, never fail on them",
    )
    args = parser.parse_args(argv)
    if args.list or not (args.fetch or args.run):
        for model_id, languages in sorted(recommendable().items()):
            print(model_id, ", ".join(sorted(languages)))
    problems = budget_problems()
    if args.fetch:
        import dictbench

        for model_id in sorted(recommendable()):
            if model_id not in {"moonshine", "whisper"}:
                dictbench.fetch_model(model_id)
    measured: list[str] = []
    if args.run:
        report: list[str] = []
        measured = run_problems(report)
        print("\n".join(report))
        _summary(report, measured, report_only=args.report_only)
    for problem in problems:
        print(f"FAIL: {problem}")
    for problem in measured:
        # ::warning:: is a GitHub Actions annotation; elsewhere it is plain text.
        print(f"::warning::{problem}" if args.report_only else f"FAIL: {problem}")
    if args.report_only:
        measured = []
    return 1 if problems or measured else 0


def _summary(report: list[str], problems: list[str], *, report_only: bool) -> None:
    """The run's figures in the GitHub job summary, when there is one."""
    import os

    path = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if not path:
        return
    lines = ["## Dictation models on real speech, this runner", ""]
    lines += [f"- {line}" for line in report]
    if problems:
        lines += ["", "### Outside the catalogue's figures", ""]
        lines += [f"- {problem}" for problem in problems]
        if report_only:
            lines += [
                "",
                "Reported, not failed: a cost measured on a shared cloud runner is not "
                "the computers the advice is for "
                "(docs/qa/dictation-live-and-whispercpp-2026-10-23.md).",
            ]
    with open(path, "a", encoding="utf-8") as out:
        out.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
