from __future__ import annotations

import json
import subprocess
import sys

import pytest

from quill.core.python_sandbox import run_python_sandbox

pytestmark = pytest.mark.smoke


def test_python_sandbox_runs_simple_transform() -> None:
    result = run_python_sandbox(
        "result = selection_text.upper()",
        selection_text="hello",
        timeout_seconds=5.0,
    )

    assert result.succeeded is True
    assert result.result == "HELLO"


def test_python_sandbox_blocks_disallowed_imports() -> None:
    result = run_python_sandbox("import os\nresult = 'x'")

    assert result.succeeded is False
    assert "not allowed" in result.error.lower()


def test_python_sandbox_blocks_dunder_subclasses_escape() -> None:
    # The classic sandbox escape reaches subprocess/os through the object graph.
    # The AST policy must reject dunder attribute access before it can run.
    result = run_python_sandbox("result = ().__class__.__base__.__subclasses__()")

    assert result.succeeded is False
    assert "dunder" in result.error.lower()


def test_python_sandbox_blocks_dunder_name_access() -> None:
    result = run_python_sandbox("result = __import__('os').getcwd()")

    assert result.succeeded is False
    assert "dunder" in result.error.lower() or "not allowed" in result.error.lower()


def test_python_sandbox_times_out_runaway_code() -> None:
    result = run_python_sandbox("while True:\n    pass", timeout_seconds=0.2)

    assert result.timed_out is True


def test_python_sandbox_payload_delivered_via_stdin_not_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # SEC-14: the payload must travel on stdin so a sandboxed program cannot
    # read it back out of the environment.
    captured: dict[str, object] = {}

    def _fake_run(cmd: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["env"] = kwargs.get("env")
        captured["input"] = kwargs.get("input")
        body = json.dumps({"stdout": "", "stderr": "", "result": "ok", "error": ""})
        return subprocess.CompletedProcess(cmd, 0, stdout=body, stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = run_python_sandbox("set_result('ok')")

    assert result.result == "ok"
    env = captured["env"] or {}
    assert isinstance(env, dict)
    assert "QUILL_SANDBOX_PAYLOAD" not in env
    assert isinstance(captured["input"], str) and captured["input"]


def test_python_sandbox_payload_includes_resource_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # SEC-14: memory and CPU limits are plumbed through to the child via the
    # stdin payload.
    import base64

    captured: dict[str, object] = {}

    def _fake_run(cmd: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["input"] = kwargs.get("input")
        body = json.dumps({"stdout": "", "stderr": "", "result": "", "error": ""})
        return subprocess.CompletedProcess(cmd, 0, stdout=body, stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    run_python_sandbox("set_result(1)", timeout_seconds=3.0, memory_limit_mb=128)

    raw = captured["input"]
    assert isinstance(raw, str)
    payload = json.loads(base64.b64decode(raw).decode("utf-8"))
    assert payload["memory_limit_bytes"] == 128 * 1024 * 1024
    assert payload["cpu_limit_seconds"] >= 4


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Real memory-cap enforcement is verified on the Windows target; "
    "lowering RLIMIT_AS after interpreter startup is unreliable to assert in CI.",
)
def test_python_sandbox_enforces_memory_limit_on_windows() -> None:
    # SEC-14: a snippet that tries to allocate far past the cap must fail rather
    # than exhaust host memory.
    result = run_python_sandbox(
        "data = [0] * (60 * 1024 * 1024)\nset_result(len(data))",
        timeout_seconds=10.0,
        memory_limit_mb=64,
    )

    assert result.succeeded is False
    assert "memoryerror" in result.error.lower() or result.returncode != 0


def test_builtins_rebinding_blocked() -> None:
    # M-7: user code that tries to rebind __builtins__ in globals() must not
    # succeed. The _ProtectedGlobals wrapper silently ignores the write.
    code = (
        "import builtins as _b; globals()['__builtins__'] = _b; "
        "set_result(type(globals().get('__builtins__')).__name__)"
    )
    result = run_python_sandbox(code, timeout_seconds=5.0)
    # Even if the assignment runs, __builtins__ must remain a restricted dict.
    # result.result is the type name of what's in __builtins__.
    builtins_type = result.result or ""
    assert builtins_type != "module", (
        f"__builtins__ was replaced with the real module; got type={builtins_type!r}"
    )
