"""The 8 GB machine run (dict.md section 8, B-8).

Every catalogue model that is on this computer, with NVDA or JAWS running,
from files and (with ``--live``) at live pace, on the fixed B-1a English and
Spanish subsets and the B-1c script::

    python scripts/bench_machine_run.py --set en=librivox-heldout-en --set es=librivox-heldout-es \\
        --set b1c=D:/bench/b1c-en --live --sr-note "JAWS 2026 running, speech on" \\
        --out D:/bench/machine-run

Each model runs in **its own process** (``dictbench.py --json``), so peak
memory and load time are that model's alone. The results go to
``machine-run-<date>.json`` and a Markdown table beside it, with:

* speed per thread, peak memory, load time, word errors and punctuation F1,
  per model and per set (never averaged across sets);
* **proposed** ``cost_factor`` values (speed per thread over Moonshine tiny's
  on the same run) and a proposed RAM tier per model (:func:`ram_tier`), for
  a person to copy into ``model_catalog.py`` if they agree -- this script
  never edits the catalogue;
* the screen-reader note, as given. Screen-reader lag is not measured by any
  script: it is the manual part of B-8 (``docs/qa/screen-reader-checks-2026-10.md``).

It downloads nothing: a model that is not on this computer is listed as not
run. It plays and records nothing.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

#: Peak memory (MB) a model may use on each machine size, leaving room for
#: Windows, a screen reader and the editor. A proposal, stated so it can be argued.
RAM_TIERS = ((600, "4 GB"), (1_600, "8 GB"), (4_000, "16 GB"))


def ram_tier(peak_mb: float | None) -> str:
    """The smallest machine a model's measured peak memory fits."""
    if peak_mb is None:
        return "not measured"
    for ceiling, label in RAM_TIERS:
        if peak_mb <= ceiling:
            return label
    return "more than 16 GB"


def installed_models() -> list[str]:
    """The built-in engines, and every downloaded catalogue model on this computer."""
    from quill.core.windows_dictation import model_store
    from quill.core.windows_dictation.model_catalog import CATALOGUE

    found = ["moonshine", "whisper"]
    found += [model.id for model in CATALOGUE if model_store.installed(model)]
    return found


def proposals(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per model: the proposed cost factor (from the files run, against
    Moonshine tiny on the same set) and RAM tier (from the worst peak)."""
    rows = list(rows)
    baseline: dict[str, float] = {
        r["set"]: r["speed_per_thread"]
        for r in rows
        if r["engine"] == "moonshine" and r.get("speed_per_thread")
    }
    found: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = found.setdefault(row["engine"], {"factors": [], "peaks": []})
        base = baseline.get(row["set"])
        if base and row.get("speed_per_thread"):
            entry["factors"].append(row["speed_per_thread"] / base)
        if row.get("peak_memory_mb"):
            entry["peaks"].append(row["peak_memory_mb"])
    result: dict[str, dict[str, Any]] = {}
    for engine, entry in found.items():
        factors = sorted(entry["factors"])
        peak = max(entry["peaks"]) if entry["peaks"] else None
        result[engine] = {
            "cost_factor": round(factors[len(factors) // 2], 1) if factors else None,
            "peak_memory_mb": peak,
            "ram_tier": ram_tier(peak),
        }
    return result


def table(rows: Sequence[dict[str, Any]]) -> str:
    """The results as one Markdown table, a row per model and set."""
    lines = [
        "| Model | Set | Mode | Word errors | Full stop F1 | Comma F1 | Speed per thread "
        "| Text p95 | Peak memory | Load |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        marks = (row.get("punctuation") or {}).get("marks", {})
        lines.append(
            f"| {row['engine']} | {row['set']} | {row['mode']} "
            f"| {_percent(row.get('word_error_rate'))} "
            f"| {marks.get('period', {}).get('f1', '-')} | {marks.get('comma', {}).get('f1', '-')} "
            f"| {row.get('speed_per_thread', '-')} | {row.get('text_p95_seconds', '-')} "
            f"| {row.get('peak_memory_mb', '-')} MB | {row.get('startup_seconds', '-')} s |"
        )
    return "\n".join(lines) + "\n"


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def _set_arguments(source: str) -> list[str]:
    """``--dataset ID`` for a known dataset id, otherwise a folder."""
    return [source] if Path(source).is_dir() else ["--dataset", source]


def run_one(  # pragma: no cover - runs the models
    engine: str, label: str, source: str, mode: str, out: Path, subset: str | None
) -> dict[str, Any]:
    target = out / f"{engine}-{label}-{mode}.json"
    command = [sys.executable, str(_HERE / "dictbench.py"), *_set_arguments(source)]
    command += ["--engine", engine, "--json", str(target)]
    if label.startswith("es"):
        command += ["--language", "es"]
    if label.startswith("b1c"):
        command += ["--parse", "--group-by", "group"]
    if subset and not Path(source).is_dir():
        command += ["--subset", subset]
    if mode == "live":
        command += ["--latency"]
    # dictbench writes UTF-8 (2026-10-22); decoding it with the console's
    # cp1252 raised in the reader thread on a Spanish transcript.
    finished = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    if finished.returncode != 0 or not target.is_file():
        return {"engine": engine, "set": label, "mode": mode, "failed": finished.stderr[-500:]}
    summary = json.loads(target.read_text(encoding="utf-8"))["summary"]
    return {"engine": engine, "set": label, "mode": mode, **summary}


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - a person runs it
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", action="append", default=[], help="LABEL=DATASET_ID_OR_FOLDER")
    parser.add_argument("--subset", default="default")
    parser.add_argument("--models", nargs="*", help="default: every model on this computer")
    parser.add_argument("--live", action="store_true", help="also run each at live pace")
    parser.add_argument("--sr-note", default="", help="which screen reader ran, and what lagged")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.set:
        parser.error("give at least one --set LABEL=SOURCE")
    args.out.mkdir(parents=True, exist_ok=True)
    models = args.models or installed_models()
    rows: list[dict[str, Any]] = []
    for engine in models:
        for item in args.set:
            label, _eq, source = item.partition("=")
            for mode in ("files", "live") if args.live else ("files",):
                print(f"{engine} on {label} ({mode})...")
                rows.append(run_one(engine, label, source, mode, args.out, args.subset))
    date = time.strftime("%Y-%m-%d")
    report = {
        "date": date,
        "screen_reader_note": args.sr_note,
        "rows": rows,
        "proposals": proposals(r for r in rows if r["mode"] == "files" and "failed" not in r),
    }
    (args.out / f"machine-run-{date}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (args.out / f"machine-run-{date}.md").write_text(
        f"# Machine run, {date}\n\nScreen reader: {args.sr_note or 'not given'}\n\n"
        + table([r for r in rows if "failed" not in r]),
        encoding="utf-8",
    )
    print(json.dumps(report["proposals"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
