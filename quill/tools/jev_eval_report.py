"""Turn a live Jev evaluation run into numbers (command-key.md 14.8).

    python -m quill.tools.jev_eval_report CASES RESULTS [--json OUT]

*CASES* is ``tests/fixtures/command_key/jev_eval.jsonl``; *RESULTS* is what the
gateway's ``scripts/jev_eval.py`` printed. Every answer is read the way the
app reads it (:func:`quill.core.command_catalogue.jev.read_answer`, with the
pinned thresholds), so "acted", "asked" and "refused" here mean what a person
would have heard. Prints a plain-text summary; ``--json`` also writes every
number and every miss, for the write-up.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from quill.core.command_catalogue import rows_for_app
from quill.core.command_catalogue.jev import JevError, parse_answer, read_answer
from quill.core.command_catalogue.spec import Kind

USD_PER_TOKEN = 0.042 / 1_000_000


def _readouts(app: str) -> frozenset[str]:
    return frozenset(spec.id for spec in rows_for_app(app) if spec.kind is Kind.READOUT)


def outcome(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """What the person would have got from Jev alone, and from the matcher then Jev."""
    expect = case["expect"]
    if "error" in result:
        return {"jev": "error", "pipeline": "error", "top": "", "detail": result["error"]}
    try:
        answer = parse_answer(result, case["body"]["candidates"])
    except JevError as error:
        return {"jev": "bad_answer", "pipeline": "error", "top": "", "detail": str(error)}
    verdict = read_answer(answer, _readouts(case["app"]))
    top = answer.ranked()[0][0]
    if expect == "none":
        jev = {"refuse": "right_refuse", "ask": "asked_wrongly"}.get(verdict.kind, "acted_wrongly")
    elif verdict.kind in ("act", "readout"):
        jev = "right_act" if verdict.ids[0] == expect else "acted_wrongly"
    elif verdict.kind == "ask":
        jev = "right_ask" if expect in verdict.ids else "asked_wrongly"
    else:
        jev = "missed"
    if case["offline_confident"]:
        best = case["offline_best"]
        if expect == "none":
            pipeline = "matcher_acted_wrongly"
        else:
            pipeline = "matcher_right" if best == expect else "matcher_acted_wrongly"
    else:
        pipeline = jev
    return {
        "jev": jev,
        "pipeline": pipeline,
        "top": top,
        "verdict": verdict.kind,
        "ids": list(verdict.ids),
        "size": verdict.size,
        "fits": answer.fits,
        "confidence": answer.confidence,
        "is_question": answer.is_question,
        "top_p": answer.ranked()[0][1],
    }


GOOD = {"right_act", "right_refuse", "right_ask", "matcher_right"}
HARMFUL = {"acted_wrongly", "matcher_acted_wrongly"}


def summarise(cases_path: Path, results_path: Path) -> dict[str, Any]:
    cases = {
        json.loads(line)["case_id"]: json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
    }
    results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("{"):
            row = json.loads(line)
            results[row["case_id"]].append(row)
    groups: dict[str, Counter[str]] = defaultdict(Counter)
    latency: list[int] = []
    tokens: list[int] = []
    misses: list[dict[str, Any]] = []
    size_right = size_total = q_right = q_total = 0
    consistent = repeated = 0
    offline_only = Counter()
    for case_id, case in cases.items():
        rows = results.get(case_id)
        if not rows:
            continue
        first = rows[0]
        got = outcome(case, first)
        key_app = f"{case['app']}/{case['source']}"
        groups[f"{key_app}/all"][got["jev"]] += 1
        groups[f"{key_app}/{case['category']}"][got["jev"]] += 1
        groups[f"{key_app}/pipeline"][got["pipeline"]] += 1
        if case["source"] == "hand":
            if case["offline_confident"]:
                offline_only["right" if case["offline_best"] == case["expect"] else "wrong"] += 1
            else:
                offline_only["open"] += 1
        if "latency_ms" in first:
            latency.append(int(first["latency_ms"]))
        tokens.append(int(first.get("usage", {}).get("input_tokens", 0) or 0))
        if case["expect_size"] and got.get("verdict") in ("act", "ask"):
            size_total += 1
            size_right += got.get("size") == case["expect_size"]
        if case["expect_question"] is not None and "is_question" in got:
            q_total += 1
            q_right += (got["is_question"] >= 0.7) == bool(case["expect_question"])
        if len(rows) > 1:
            repeated += 1
            tops = {outcome(case, row).get("top") for row in rows}
            consistent += len(tops) == 1
        if case["source"] == "hand" and got["jev"] not in GOOD:
            misses.append({
                "case_id": case_id,
                "app": case["app"],
                "category": case["category"],
                "text": case["text"],
                "expect": case["expect"],
                "got": got,
                "offline_best": case["offline_best"],
                "offline_confident": case["offline_confident"],
            })
    total_tokens = sum(tokens)
    return {
        "groups": {name: dict(counter) for name, counter in sorted(groups.items())},
        "requests": len(tokens),
        "latency_ms": {
            "median": statistics.median(latency) if latency else 0,
            "p90": sorted(latency)[int(len(latency) * 0.9) - 1] if latency else 0,
            "max": max(latency) if latency else 0,
        },
        "tokens": {
            "total": total_tokens,
            "mean": round(total_tokens / len(tokens)) if tokens else 0,
            "cost_usd": round(total_tokens * USD_PER_TOKEN, 4),
            "cost_per_1000_requests_usd": round(
                (total_tokens / len(tokens)) * 1000 * USD_PER_TOKEN, 4
            )
            if tokens
            else 0,
        },
        "size": {"right": size_right, "of": size_total},
        "question": {"right": q_right, "of": q_total},
        "consistency": {"same_top_every_time": consistent, "of": repeated},
        "hand_offline_only": dict(offline_only),
        "hand_misses": misses,
    }


def _rate(counter: dict[str, int], good: set[str]) -> str:
    total = sum(counter.values())
    right = sum(v for k, v in counter.items() if k in good)
    harmful = sum(v for k, v in counter.items() if k in HARMFUL)
    return (
        f"{right}/{total} ({100 * right / total:.0f}%) good, {harmful} acted wrongly"
        if total
        else "-"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    data = summarise(args.cases, args.results)
    for name, counter in data["groups"].items():
        print(f"{name}: {_rate(counter, GOOD)}  {counter}")
    print("latency", data["latency_ms"], "tokens", data["tokens"])
    print("size", data["size"], "question", data["question"], "consistency", data["consistency"])
    print("hand, matcher alone:", data["hand_offline_only"], "misses:", len(data["hand_misses"]))
    if args.json:
        args.json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
