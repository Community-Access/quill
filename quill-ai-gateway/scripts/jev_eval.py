"""Run QUILL's live Jev evaluation set through this service's own code.

Run inside the web container, with the cases file copied in::

    docker compose -f docker-compose.prod.yml exec -T web \\
        python scripts/jev_eval.py /tmp/jev_eval.jsonl > results.jsonl

Each case's ``body`` is exactly what QUILL sends to ``POST /v1/decide``. This
builds the TypeSafe request with the route's own :func:`app.jev.build_body`
and sends it with :func:`app.jev.ask_typesafe`, so the questions and the
descriptions are the ones live traffic gets. It goes around the route's caps on
purpose (an evaluation of a few thousand requests would trip the per-device
minute cap), so it is a measurement of Jev, not of the caps, which
``tests/test_decide.py`` covers.

Prints one JSON line per case (the case id and Jev's answer, never the key) and
a summary line on stderr. Options: ``--workers N`` (default 4), ``--repeat N``
to send each hand case N times (for consistency), ``--only hand``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, "/app")  # inside the container, wherever this file was copied

from app import create_app  # noqa: E402
from app.jev import DecideError, ask_typesafe, build_body  # noqa: E402


def _one(config, case: dict, attempt: int) -> dict:
    out = {"case_id": case["case_id"], "attempt": attempt}
    try:
        built = build_body(case["body"])
    except DecideError as error:
        out.update(error=error.error, message=error.message)
        return out
    for tries in range(4):
        try:
            answer = ask_typesafe(config, built.body, built.offered)
            out.update(answer)
            out.pop("error", None)
            return out
        except DecideError as error:
            out.update(error=error.error, message=error.message)
            if error.status in (429, 502, 504) and tries < 3:
                time.sleep(1.5 * (tries + 1))
                continue
            return out
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--only", choices=("hand", "corpus"), default=None)
    args = parser.parse_args()
    cases = [json.loads(line) for line in Path(args.cases).read_text(encoding="utf-8").splitlines()]
    if args.only:
        cases = [case for case in cases if case["source"] == args.only]
    jobs = [(case, n) for case in cases for n in range(args.repeat)]
    app = create_app()
    started = time.monotonic()
    done = errors = tokens = 0
    with app.app_context(), ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda job: _one(app.config, *job), jobs):
            done += 1
            if "error" in result:
                errors += 1
            tokens += int(result.get("usage", {}).get("input_tokens", 0) or 0)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if done % 200 == 0:
                print(f"{done}/{len(jobs)} sent, {errors} errors", file=sys.stderr, flush=True)
    seconds = time.monotonic() - started
    print(
        f"done: {done} requests, {errors} errors, {tokens} input tokens "
        f"(${tokens * 0.042 / 1_000_000:.4f}), {seconds:.0f}s",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
