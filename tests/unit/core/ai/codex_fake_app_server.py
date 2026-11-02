"""A fake Codex app-server for tests/unit/core/ai/test_codex_engine.py.

Run as a child process (never imported). It speaks the pinned app-server's
wire format -- newline-delimited JSON-RPC without the ``jsonrpc`` field --
and records every message it receives, with a timestamp, to the JSON-lines
file named by ``FAKE_CODEX_LOG``. ``FAKE_CODEX_SCENARIO`` picks the turn:

- ``answer``: streams two deltas, completes the message, reports usage.
- ``tool``: calls ``FAKE_CODEX_TOOL`` through ``item/tool/call`` first.
- ``approval``: asks for a built-in command approval first.
- ``hang``: never finishes until ``turn/interrupt``.
- ``unauthorized_once``: a turn on ``ACCESS_TOKEN == "old-token"`` fails 401.
- ``stubborn``: like ``answer``, but ignores stdin closing (must be killed).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

LOG = os.environ.get("FAKE_CODEX_LOG", "")
SCENARIO = os.environ.get("FAKE_CODEX_SCENARIO", "answer")
TOOL = os.environ.get("FAKE_CODEX_TOOL", "")
TOKEN = os.environ.get("ACCESS_TOKEN", "")
HOME = Path(os.environ.get("CODEX_HOME", "."))


def record(entry: dict) -> None:
    if not LOG:
        return
    entry["t"] = time.monotonic()
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def send(message: dict) -> None:
    sys.stdout.buffer.write((json.dumps(message) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def finish_turn(thread_id: str, turn_id: str, text: str) -> None:
    for part in (text[: len(text) // 2], text[len(text) // 2 :]):
        send({
            "method": "item/agentMessage/delta",
            "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "m1", "delta": part},
        })
    send({
        "method": "item/completed",
        "params": {
            "threadId": thread_id,
            "turnId": turn_id,
            "item": {"type": "agentMessage", "id": "m1", "text": text},
        },
    })
    send({
        "method": "thread/tokenUsage/updated",
        "params": {
            "threadId": thread_id,
            "turnId": turn_id,
            "tokenUsage": {
                "total": {"inputTokens": 120, "outputTokens": 30},
                "last": {"inputTokens": 120, "outputTokens": 30},
            },
        },
    })
    send({
        "method": "turn/completed",
        "params": {"threadId": thread_id, "turn": {"id": turn_id, "status": "completed"}},
    })


def main() -> None:
    record({
        "launch": True,
        "argv": sys.argv[1:],
        "token": TOKEN,
        "home": str(HOME),
        "home_listing": sorted(p.name for p in HOME.rglob("*")) if HOME.exists() else [],
    })
    sys.stderr.write(f"fake codex starting with {TOKEN}\n")
    sys.stderr.flush()
    turns = 0
    pending: dict[str, tuple[str, str]] = {}
    for raw in iter(sys.stdin.buffer.readline, b""):
        message = json.loads(raw)
        record({"in": message})
        method = message.get("method")
        params = message.get("params") or {}
        msg_id = message.get("id")
        if method is None:  # an answer to one of our requests
            thread_id, turn_id = pending.pop(str(msg_id), ("", ""))
            result = message.get("result") or {}
            text = json.dumps(result)
            finish_turn(thread_id, turn_id, f"Tool said {text}")
            continue
        if method == "initialize":
            send({"id": msg_id, "result": {"userAgent": "fake-codex/0.166.0"}})
        elif method == "thread/start":
            sessions = HOME / "sessions"
            sessions.mkdir(parents=True, exist_ok=True)
            (sessions / "thr_1.jsonl").write_text("{}\n", encoding="utf-8")
            send({"id": msg_id, "result": {"thread": {"id": "thr_1"}}})
        elif method == "thread/resume":
            found = (HOME / "sessions" / "thr_1.jsonl").exists()
            record({"resume_found_thread_file": found})
            send({"id": msg_id, "result": {"thread": {"id": params.get("threadId")}}})
        elif method == "account/rateLimits/read":
            send({
                "id": msg_id,
                "result": {
                    "rateLimits": {
                        "primary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": 1},
                    }
                },
            })
        elif method == "turn/start":
            turns += 1
            thread_id = params.get("threadId", "")
            turn_id = f"turn_{turns}"
            send({"id": msg_id, "result": {"turn": {"id": turn_id, "status": "inProgress"}}})
            send({
                "method": "turn/started",
                "params": {"threadId": thread_id, "turn": {"id": turn_id}},
            })
            if SCENARIO == "tool":
                pending["srv-tool"] = (thread_id, turn_id)
                send({
                    "id": "srv-tool",
                    "method": "item/tool/call",
                    "params": {
                        "threadId": thread_id,
                        "turnId": turn_id,
                        "callId": "call_1",
                        "tool": TOOL,
                        "arguments": {"what": "levels"},
                    },
                })
            elif SCENARIO == "approval":
                pending["srv-approval"] = (thread_id, turn_id)
                send({
                    "id": "srv-approval",
                    "method": "item/commandExecution/requestApproval",
                    "params": {"threadId": thread_id, "turnId": turn_id, "itemId": "c1"},
                })
            elif SCENARIO == "hang":
                pass
            elif SCENARIO == "unauthorized_once" and TOKEN == "old-token":
                send({
                    "method": "turn/completed",
                    "params": {
                        "threadId": thread_id,
                        "turn": {
                            "id": turn_id,
                            "status": "failed",
                            "error": {
                                "message": "401 Unauthorized",
                                "codexErrorInfo": "unauthorized",
                            },
                        },
                    },
                })
            else:
                finish_turn(thread_id, turn_id, "Hello")
        elif method == "turn/interrupt":
            send({"id": msg_id, "result": {}})
            send({
                "method": "turn/completed",
                "params": {
                    "threadId": params.get("threadId"),
                    "turn": {"id": params.get("turnId"), "status": "interrupted"},
                },
            })
        elif msg_id is not None:
            send({"id": msg_id, "error": {"code": -32601, "message": "unknown"}})
    record({"eof": True})
    if SCENARIO == "stubborn":
        time.sleep(60)


if __name__ == "__main__":
    main()
