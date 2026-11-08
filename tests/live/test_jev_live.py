"""The recorded live Jev suite (docs/design/command-key.md 14.7). Never in PR CI.

Runs only with ``QUILL_JEV_LIVE=1`` **and** a TypeSafe key in Windows Credential
Manager (generic credential ``QUILL TypeSafe dev key``); otherwise every test
skips. The key is read by :func:`quill.core.command_catalogue.jev._key_from_credential_manager`
and is never printed, logged or written anywhere.

    $env:QUILL_JEV_LIVE = "1"; pytest tests/live/test_jev_live.py -m live_jev -q

It sends the held-out corpus rows the offline tiers could not settle, with the
model pinned, and writes a short report (accuracy, latency, tokens) to
``tests/fixtures/command_key/live-report.md``. Each request costs a fraction of
a cent; the whole run is a few hundred requests at most.
"""

from __future__ import annotations

import os
import statistics
import time
from pathlib import Path

import pytest

from quill.core.command_catalogue import rows_for_app
from quill.core.command_catalogue.corpus import load_corpus
from quill.core.command_catalogue.jev import JEV_MODEL_NOTE, OwnKeyJev, _key_from_credential_manager
from quill.core.command_catalogue.jev_request import JEV_MODEL, build_request
from quill.core.command_catalogue.resolver import Candidate, resolve

pytestmark = [
    pytest.mark.live_jev,
    pytest.mark.timeout(1800),
    pytest.mark.skipif(
        os.environ.get("QUILL_JEV_LIVE") != "1", reason="live Jev runs only with QUILL_JEV_LIVE=1"
    ),
]

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "command_key"
_LIMIT = 150


@pytest.mark.parametrize("app", ["radio", "quill"])
def test_jev_on_what_the_offline_tiers_left_open(app: str) -> None:
    if not _key_from_credential_manager():
        pytest.skip("no TypeSafe key in Credential Manager")
    candidates = [Candidate(spec) for spec in rows_for_app(app) if spec.offered]
    route = OwnKeyJev()
    rows = [
        row
        for row in load_corpus(_FIXTURES / f"{app}.jsonl")
        if row.set == "held_out" and row.expect_id and not resolve(row.text, candidates).confident
    ][:_LIMIT]
    right = 0
    latencies: list[float] = []
    tokens = 0
    for row in rows:
        found = resolve(row.text, candidates)
        ordered = [item.candidate for item in found.ranked] + [
            item for item in candidates if item.spec.id not in {r.id for r in found.ranked}
        ]
        request = build_request(row.text, ordered, app=app, surface="", args=found.args)
        started = time.monotonic()
        answer = route.decide(request)
        latencies.append(time.monotonic() - started)
        tokens += answer.input_tokens
        right += answer.ranked()[0][0] == row.expect_id
    report = _FIXTURES / "live-report.md"
    median = statistics.median(latencies) if latencies else 0.0
    report.write_text(
        f"# Live Jev, {app}, {JEV_MODEL}\n\n{right} of {len(rows)} right; "
        f"median {median:.2f} s; {tokens} input tokens. {JEV_MODEL_NOTE}\n",
        encoding="utf-8",
    )
    assert not rows or right / len(rows) >= 0.5
