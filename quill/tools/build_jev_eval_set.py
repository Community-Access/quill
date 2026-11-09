"""Build the live Jev evaluation set (command-key.md 14.7).

    python -m quill.tools.build_jev_eval_set --write   (writes the fixture)
    python -m quill.tools.build_jev_eval_set --check   (what the test runs)

One line per case, each holding exactly the ``/v1/decide`` body QUILL would send
for that sentence (the candidates in the matcher's order, the state
``jev_request.build_request`` makes), what the right answer is, and what the
matcher on the computer would have done without Jev. Two sources:

* ``hand``: the natural phrasings in :mod:`quill.tools.jev_eval_cases`, the
  sentences Jev exists for;
* ``corpus``: every row of the seed corpus, so Jev is also measured on the
  sentences the matcher settles and on every kind of refusal.

The gateway's ``scripts/jev_eval.py`` sends each body to Jev and records the
answer; :mod:`quill.tools.jev_eval_report` turns the answers into the report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from quill.core.command_catalogue import rows_for_app
from quill.core.command_catalogue.corpus import load_corpus
from quill.core.command_catalogue.jev_request import CATALOGUE_VERSION, build_request
from quill.core.command_catalogue.resolver import Candidate, resolve
from quill.tools.jev_eval_cases import cases_for

APPS = ("radio", "quill", "lite")
_ROOT = Path(__file__).resolve().parents[2]
_CORPUS = _ROOT / "tests" / "fixtures" / "command_key"
OUT = _CORPUS / "jev_eval.jsonl"


def _offered(app: str) -> list[Candidate]:
    return [Candidate(spec) for spec in rows_for_app(app) if spec.offered]


def _case(
    *,
    case_id: str,
    app: str,
    source: str,
    category: str,
    text: str,
    expect: str,
    candidates: list[Candidate],
    recent: tuple[str, ...] = (),
    last_offer: tuple[str, ...] = (),
    heard: tuple[str, ...] = (),
    size: str = "",
    question: bool | None = None,
) -> dict[str, Any]:
    found = resolve(text, candidates)
    ordered = [item.candidate for item in found.ranked] + [
        item
        for item in candidates
        if item.spec.id not in {r.candidate.spec.id for r in found.ranked}
    ]
    request = build_request(
        text,
        ordered,
        app=app,
        surface="main",
        args=found.args,
        recent=recent,
        last_offer=last_offer,
        heard_alternatives=heard,
    )
    offline_best = found.ranked[0].candidate.spec.id if found.ranked else "none"
    return {
        "case_id": case_id,
        "app": app,
        "source": source,
        "category": category,
        "text": text,
        "expect": expect,
        "expect_size": size,
        "expect_question": question,
        "offline_confident": bool(found.confident),
        "offline_best": offline_best,
        "body": {
            "app": app,
            "catalogue_version": CATALOGUE_VERSION,
            "question_set": request.question_set,
            "candidates": list(request.offered),
            "state": request.body["state"],
        },
    }


def build() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for app in APPS:
        offered = _offered(app)
        number = 0
        for category, cases in cases_for(app).items():
            for case in cases:
                number += 1
                text, expect = case[0], case[1]
                extra: dict[str, Any] = dict(case[2]) if len(case) > 2 else {}  # type: ignore[misc]
                disabled = set(extra.get("disabled", ()))
                candidates = [item for item in offered if item.spec.id not in disabled]
                out.append(
                    _case(
                        case_id=f"{app}-hand-{number:03d}",
                        app=app,
                        source="hand",
                        category=category,
                        text=text,
                        expect=expect,
                        candidates=candidates,
                        recent=tuple(extra.get("recent", ())),
                        last_offer=tuple(extra.get("last_offer", ())),
                        size=str(extra.get("size", "")),
                        question=extra.get("question"),
                    )
                )
        for row in load_corpus(_CORPUS / f"{app}.jsonl"):
            enabled = set(row.enabled) if row.enabled is not None else None
            candidates = [item for item in offered if enabled is None or item.spec.id in enabled]
            if not candidates:
                continue
            out.append(
                _case(
                    case_id=f"{app}-corpus-{row.line:04d}",
                    app=app,
                    source="corpus",
                    category=f"refuse_{row.expect_refuse}" if row.is_refusal else row.mode,
                    text=row.text,
                    expect="none" if row.is_refusal else row.expect_id,
                    candidates=candidates,
                    recent=row.recent,
                    last_offer=row.last_offer,
                    heard=row.heard_alternatives,
                )
            )
    return out


def render() -> str:
    return "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in build())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render()
    if args.write:
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {OUT.relative_to(_ROOT).as_posix()}: {text.count(chr(10))} cases")
        return 0
    if not OUT.is_file() or OUT.read_text(encoding="utf-8") != text:
        print(
            "jev_eval.jsonl is out of date; run python -m quill.tools.build_jev_eval_set --write",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
