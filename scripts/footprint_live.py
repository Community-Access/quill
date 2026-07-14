"""Live per-engine footprint measurement — the Phase-0 timing companion.

Completes the footprint baseline that ``scripts/footprint_report.py`` starts:
for each installed speech engine it measures **cold-start**, **first-output**,
and **peak RSS** by running the probe in an isolated subprocess and sampling the
child's memory. Real numbers only — an engine with no model, or no engine at
all, is recorded as a note, never a fabricated timing.

Run it on the reference machine (with the engines/models installed) to fill in
the numbers the static report cannot:

    python scripts/footprint_live.py                       # print + write results
    python scripts/footprint_live.py --merge-baseline      # add to footprint-baseline.json
    python scripts/footprint_live.py --engine whispercpp   # one engine
    python scripts/footprint_live.py --timeout 300         # per-engine cap (seconds)

Nothing here needs network, ``wx``, or admin rights; without ``psutil`` the peak
RSS is reported as unavailable and the timings are still captured.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from quill.core.footprint.live_probe import (  # noqa: E402
    EngineTiming,
    list_speech_engine_ids,
    merge_timings_into_baseline,
    run_engine_probe,
)

_BASELINE = _ROOT / "docs" / "planning" / "footprint" / "footprint-baseline.json"
_DEFAULT_TIMEOUT_S = 240
_SAMPLE_INTERVAL_S = 0.1


def parse_child_output(stdout: str, engine_id: str) -> EngineTiming:
    """Parse the child probe's JSON line into an ``EngineTiming`` (pure)."""
    line = ""
    for candidate in reversed(stdout.strip().splitlines()):
        if candidate.strip().startswith("{"):
            line = candidate.strip()
            break
    if not line:
        return EngineTiming(
            engine_id=engine_id,
            display_name=engine_id,
            available=False,
            note="probe produced no JSON output",
        )
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return EngineTiming(
            engine_id=engine_id,
            display_name=engine_id,
            available=False,
            note="probe output was not valid JSON",
        )
    fields = {k: data.get(k) for k in EngineTiming.__dataclass_fields__}
    fields["engine_id"] = fields.get("engine_id") or engine_id
    fields["display_name"] = fields.get("display_name") or engine_id
    fields["available"] = bool(fields.get("available"))
    return EngineTiming(**fields)  # type: ignore[arg-type]


def _sample_peak_rss(pid: int, proc: subprocess.Popen) -> int | None:
    """Sample a running child's RSS to its peak; ``None`` when psutil is absent."""
    try:
        import psutil  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    try:
        target = psutil.Process(pid)
    except Exception:  # noqa: BLE001
        return None
    peak = 0
    while proc.poll() is None:
        try:
            rss = target.memory_info().rss
            for child in target.children(recursive=True):
                with contextlib.suppress(Exception):
                    rss += child.memory_info().rss
            peak = max(peak, rss)
        except Exception:  # noqa: BLE001 - process may exit mid-sample
            break
        time.sleep(_SAMPLE_INTERVAL_S)
    return peak or None


def measure_engine(engine_id: str, *, timeout_s: int) -> EngineTiming:
    """Run one engine's probe in a subprocess, sampling its peak RSS."""
    cmd = [sys.executable, str(Path(__file__)), "--child", "--engine", engine_id]
    try:
        proc = subprocess.Popen(  # noqa: S603 - fixed argv, our own script
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, cwd=str(_ROOT)
        )
    except OSError as exc:
        return EngineTiming(
            engine_id=engine_id,
            display_name=engine_id,
            available=False,
            note=f"could not launch probe: {exc.__class__.__name__}",
        )
    peak = _sample_peak_rss(proc.pid, proc)
    try:
        stdout, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        return EngineTiming(
            engine_id=engine_id,
            display_name=engine_id,
            available=True,
            note=f"probe exceeded {timeout_s}s timeout",
        )
    timing = parse_child_output(stdout or "", engine_id)
    if timing.peak_rss_bytes is None:
        timing.peak_rss_bytes = peak
    return timing


def measure_all(engine_ids: list[str], *, timeout_s: int) -> list[EngineTiming]:
    return [measure_engine(eid, timeout_s=timeout_s) for eid in engine_ids]


def _mb(n: int | None) -> str:
    return f"{n / (1024 * 1024):.0f} MB" if n else "unavailable"


def _s(v: float | None) -> str:
    return f"{v:.2f}s" if v is not None else "-"


def render_markdown(timings: list[EngineTiming]) -> str:
    lines = ["# QUILL live engine footprint (Phase 0)", ""]
    if not timings:
        lines.append("No speech engines are registered on this machine.")
        return "\n".join(lines)
    lines.append("| Engine | Model | Cold start | First output | Peak RSS | Note |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for t in timings:
        lines.append(
            f"| {t.display_name} | {t.model_id or '-'} | {_s(t.cold_start_s)} | "
            f"{_s(t.first_output_s)} | {_mb(t.peak_rss_bytes)} | {t.note or 'OK'} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live per-engine footprint timings.")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--engine", default=None, help="Measure only this engine id.")
    parser.add_argument("--timeout", type=int, default=_DEFAULT_TIMEOUT_S)
    parser.add_argument("--merge-baseline", action="store_true", help="Add to the baseline JSON.")
    parser.add_argument("--out", type=Path, default=None, help="Write the live report JSON here.")
    args = parser.parse_args(argv)

    # Child mode: run one probe in-process and print its JSON. The parent samples
    # our RSS while we run.
    if args.child:
        engine_id = args.engine or ""
        print(json.dumps(run_engine_probe(engine_id).to_json()))
        return 0

    engine_ids = [args.engine] if args.engine else list_speech_engine_ids()
    timings = measure_all(engine_ids, timeout_s=args.timeout)

    print(render_markdown(timings))

    payload = [t.to_json() for t in timings]
    if args.out is not None:
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.out}")
    if args.merge_baseline and _BASELINE.is_file():
        baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))
        merged = merge_timings_into_baseline(baseline, timings)
        _BASELINE.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        print(f"Merged engine timings into {_BASELINE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
