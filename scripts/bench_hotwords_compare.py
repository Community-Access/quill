"""Compare paired dictbench runs for D-28, without running or adopting a model.

Supply names-only and held-out B-1 runs, with and without hotwords, plus the
same vocabulary used for decoding. Nothing is downloaded, recorded or played.
Only counts and input hashes enter the result; transcripts stay in the inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from bench_scoring import LIMITS, basic_normalize  # noqa: E402

from quill.core.storage import write_json_atomic  # noqa: E402
from quill.core.windows_dictation.word_errors import word_errors  # noqa: E402


@dataclass(frozen=True)
class Row:
    reference: str
    heard: str
    audio_seconds: float
    failed: str = ""


def load_report(path: Path) -> tuple[dict[str, Row], str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise ValueError("A dictbench report must have a files list.")
    rows: dict[str, Row] = {}
    for item in data["files"]:
        if not isinstance(item, dict):
            raise ValueError("Each benchmark file must be an object.")
        name, reference, heard = (item.get(key) for key in ("name", "reference", "heard"))
        seconds, failure = item.get("audio_seconds"), item.get("failed", "")
        if (
            not isinstance(name, str)
            or not name.strip()
            or name in rows
            or not isinstance(reference, str)
            or not basic_normalize(reference)
            or not isinstance(heard, str)
            or not isinstance(failure, str)
            or isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or seconds <= 0
            or seconds > sys.float_info.max
            or not math.isfinite(seconds)
        ):
            raise ValueError("Invalid or duplicate benchmark file; expected text and duration.")
        rows[name] = Row(reference, heard, float(seconds), failure)
    if not rows:
        raise ValueError("A benchmark report must not be empty.")
    return rows, hashlib.sha256(raw).hexdigest()


def load_names(path: Path) -> tuple[list[tuple[str, ...]], str]:
    raw = path.read_bytes()
    names: list[tuple[str, ...]] = []
    for line in raw.decode("utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        words = tuple(basic_normalize(line))
        if not words or words in names:
            raise ValueError("Vocabulary must contain distinct, nonempty names, one per line.")
        names.append(words)
    if not names:
        raise ValueError("The names vocabulary must not be empty.")
    return names, hashlib.sha256(raw).hexdigest()


def _paired(before: Mapping[str, Row], after: Mapping[str, Row]) -> None:
    if not before or before.keys() != after.keys():
        raise ValueError("Paired runs must contain exactly the same nonempty set of files.")
    for name, row in before.items():
        other = after[name]
        if row.reference != other.reference or row.audio_seconds != other.audio_seconds:
            raise ValueError("Paired runs have different references or audio durations.")
        if row.failed or other.failed:
            raise ValueError(
                "A failed recognition must be rerun, not counted as a valid comparison."
            )


def _contains(words: Sequence[str], name: tuple[str, ...]) -> bool:
    return any(tuple(words[i : i + len(name)]) == name for i in range(len(words) - len(name) + 1))


def _name_hits(rows: Mapping[str, Row], names: Sequence[tuple[str, ...]]) -> int:
    heard: set[tuple[str, ...]] = set()
    covered: set[tuple[str, ...]] = set()
    for row in rows.values():
        reference_words, heard_words = basic_normalize(row.reference), basic_normalize(row.heard)
        for name in names:
            if _contains(reference_words, name):
                covered.add(name)
                if _contains(heard_words, name):
                    heard.add(name)
    if covered != set(names):
        raise ValueError("Every vocabulary name must occur in the names-set references.")
    return len(heard)


def _errors(rows: Mapping[str, Row]) -> tuple[int, int]:
    errors = words = 0
    for row in rows.values():
        reference = basic_normalize(row.reference)
        words += len(reference)
        errors += word_errors(reference, basic_normalize(row.heard))
    return errors, words


def compare(
    names: Sequence[tuple[str, ...]],
    names_before: Mapping[str, Row],
    names_after: Mapping[str, Row],
    b1_before: Mapping[str, Row],
    b1_after: Mapping[str, Row],
    *,
    real_heldout: bool,
) -> dict[str, Any]:
    _paired(names_before, names_after)
    _paired(b1_before, b1_after)
    if not names or any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("The names vocabulary must be nonempty and distinct.")
    before_hits, after_hits = _name_hits(names_before, names), _name_hits(names_after, names)
    before_errors, before_words = _errors(b1_before)
    after_errors, after_words = _errors(b1_after)
    reasons = []
    if len(names) < 20:
        reasons.append("D-28 requires at least 20 distinct names.")
    if not real_heldout:
        reasons.append("Real, consented, held-out speech has not been attested.")
    if not before_hits:
        reasons.append("The baseline recognizes no names; relative improvement is undefined.")
    # Compare integer counts, not rounded WER or a rounded improvement fraction.
    improvement_met = after_hits * 2 >= before_hits * 3 if before_hits else None
    wer_no_worse = after_errors * before_words <= before_errors * after_words
    status = (
        "insufficient_evidence"
        if reasons
        else "measurement_pass"
        if improvement_met and wer_no_worse
        else "measurement_fail"
    )
    return {
        "schema_version": 1,
        "experiment": "D-28",
        "status": status,
        "adopted": False,
        "normalizer": "basic: case and punctuation ignored; accents retained",
        "real_heldout_attested": real_heldout,
        "names": {
            "distinct": len(names),
            "recognized_without": before_hits,
            "recognized_with": after_hits,
            "relative_increase": (after_hits - before_hits) / before_hits if before_hits else None,
            "at_least_50_percent_relative_increase": improvement_met,
        },
        "b1": {
            "reference_words": before_words,
            "errors_without": before_errors,
            "errors_with": after_errors,
            "wer_without": before_errors / before_words,
            "wer_with": after_errors / after_words,
            "wer_no_worse": wer_no_worse,
        },
        "insufficient_evidence": reasons,
        "limits": [
            LIMITS,
            "Name recognition means at least one exact token-sequence match per distinct name "
            "in a clip whose reference includes it; this is not per-occurrence recall.",
            "50 percent better means a relative increase in distinct names recognized. "
            "A zero-hit baseline is inconclusive, not an automatic pass.",
            "File names, reference text and duration must match. These reports do not prove "
            "the same source audio, decoding settings or model was used.",
            "Input hashes identify reports and vocabulary, not model files or licenses. "
            "Review model provenance, real/held-out status, performance, memory and accessibility "
            "separately. A measurement pass never adopts or enables a model.",
            "Run separately for each language, speaker cohort and condition; an aggregate "
            "comparison cannot prove non-regression for every group.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", required=True, type=Path)
    for name in ("names-without", "names-with", "b1-without", "b1-with"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument(
        "--real-heldout",
        action="store_true",
        help="Attest both sets are consented real speech, held out from model training.",
    )
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    inputs = {
        name: getattr(args, name.replace("-", "_"))
        for name in ("names-without", "names-with", "b1-without", "b1-with")
    }
    if args.out.resolve() in {path.resolve() for path in (args.names, *inputs.values())}:
        parser.error("The output must not overwrite an input.")
    try:
        names, names_hash = load_names(args.names)
        reports = {name: load_report(path) for name, path in inputs.items()}
        result = compare(
            names,
            reports["names-without"][0],
            reports["names-with"][0],
            reports["b1-without"][0],
            reports["b1-with"][0],
            real_heldout=args.real_heldout,
        )
        result["input_sha256"] = {
            "names": names_hash,
            **{name: report[1] for name, report in reports.items()},
        }
        write_json_atomic(args.out, result)
    except (OSError, ValueError) as error:
        parser.error(f"{error} No new result was written; any previous report is unchanged.")
    print(f"D-28: {result['status']}. Adoption remains off. Results: {args.out}")
    return 0 if result["status"] == "measurement_pass" else 1


if __name__ == "__main__":
    sys.exit(main())
