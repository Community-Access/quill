"""Run short Python snippets under layered isolation (SEC-14).

Threat model (read before widening any entry point):

* The primary containment is the **subprocess boundary**, not the Python-level
  builtins shim. Snippets run in a separate, isolated interpreter (``-I -B``)
  with a scrubbed environment (no secrets, only the minimum OS vars), a temp
  cwd, a wall-clock timeout, and best-effort memory/CPU caps (a Windows job
  object / POSIX ``setrlimit``).
* The in-process defenses are defense-in-depth: a restricted ``__builtins__``,
  an ``__import__`` guard limited to :data:`ALLOWED_IMPORTS`, and a static AST
  policy (:func:`_validate_code_policy`) that rejects disallowed imports **and**
  dunder attribute/name access. The dunder block closes the classic escape
  ``().__class__.__base__.__subclasses__()`` that reaches already-imported
  modules (``os``/``subprocess``) through the object graph, which the import
  guard alone cannot see.
* The resource caps are **best-effort**: if the OS call to install them fails
  (e.g. ``CreateJobObject`` is denied) the snippet still runs, bounded only by
  the wall-clock timeout. Callers that need a hard memory guarantee must not
  rely on this alone.

This is safe for user-authored snippets (the user already controls their own
machine) and reasonably hardened against hostile AI/Quillin-authored code, but
it is not a security boundary strong enough to run fully untrusted third-party
code at scale. Keep both layers when editing: do not add builtins, widen
``ALLOWED_IMPORTS``, or relax the AST policy without re-checking this model.
"""

from __future__ import annotations

import ast
import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from typing import Any

ALLOWED_IMPORTS: frozenset[str] = frozenset({
    "collections",
    "dataclasses",
    "datetime",
    "decimal",
    "fractions",
    "functools",
    "heapq",
    "itertools",
    "json",
    "math",
    "operator",
    "re",
    "statistics",
    "string",
    "textwrap",
    "typing",
})

_SANDBOX_BOOTSTRAP = textwrap.dedent(
    """
    from __future__ import annotations

    import base64
    import builtins
    import contextlib
    import io
    import json
    import os
    import sys
    import traceback

    # SEC-14: the payload arrives on stdin (never the environment) so the
    # sandboxed program cannot read it back out of os.environ, and resource
    # limits are applied to *this* child process before any user code runs.
    payload = json.loads(base64.b64decode(sys.stdin.buffer.read()).decode("utf-8"))
    code = base64.b64decode(payload["code_b64"]).decode("utf-8")
    document_text = payload.get("document_text", "")
    selection_text = payload.get("selection_text", "")
    input_text = payload.get("input_text", "")
    outline = payload.get("outline")


    def _apply_windows_memory_limit(limit_bytes):
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # Declare signatures so 64-bit HANDLEs are not truncated to c_int.
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

        class _BASIC(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _IO(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class _EXT(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _BASIC),
                ("IoInfo", _IO),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
        JobObjectExtendedLimitInformation = 9
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return False
        info = _EXT()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY
        info.ProcessMemoryLimit = limit_bytes
        if not kernel32.SetInformationJobObject(
            job, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)
        ):
            return False
        return bool(kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()))


    def _apply_resource_limits(payload):
        # Returns a list of caps that were requested but could NOT be installed, so
        # the parent can log that containment is weaker than intended (SEC-14). Best
        # effort by design: a failure here never stops the snippet running (bounded
        # by the wall-clock timeout regardless).
        unapplied = []
        memory_limit_bytes = int(payload.get("memory_limit_bytes") or 0)
        cpu_limit_seconds = int(payload.get("cpu_limit_seconds") or 0)
        if sys.platform == "win32":
            if memory_limit_bytes > 0:
                ok = False
                try:
                    ok = _apply_windows_memory_limit(memory_limit_bytes)
                except Exception:
                    ok = False
                if not ok:
                    unapplied.append("memory")
            return unapplied
        try:
            import resource
        except Exception:
            if memory_limit_bytes > 0:
                unapplied.append("memory")
            if cpu_limit_seconds > 0:
                unapplied.append("cpu")
            return unapplied
        if memory_limit_bytes > 0:
            try:
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
            except Exception:
                unapplied.append("memory")
        if cpu_limit_seconds > 0:
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit_seconds, cpu_limit_seconds))
            except Exception:
                unapplied.append("cpu")
        return unapplied


    _caps_unapplied = _apply_resource_limits(payload)

    allowed_modules = set(payload.get("allowed_imports", ()))
    original_import = builtins.__import__

    def _blocked(name: str, *_args, **_kwargs):
        raise PermissionError(f"{name} is not available in the sandbox")

    def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        root_name = name.split(".", 1)[0]
        if root_name not in allowed_modules:
            raise ImportError(f"Import of {root_name} is not allowed in the sandbox")
        return original_import(name, globals, locals, fromlist, level)

    class _ProtectedGlobals(dict):
        # Silently ignores __builtins__ rewrites from user code.
        def __setitem__(self, key, value):
            if key == "__builtins__":
                return
            super().__setitem__(key, value)

    safe_builtins = {
        "abs": builtins.abs,
        "all": builtins.all,
        "any": builtins.any,
        "bool": builtins.bool,
        "dict": builtins.dict,
        "enumerate": builtins.enumerate,
        "filter": builtins.filter,
        "float": builtins.float,
        "format": builtins.format,
        "frozenset": builtins.frozenset,
        "getattr": builtins.getattr,
        "hasattr": builtins.hasattr,
        "hash": builtins.hash,
        "int": builtins.int,
        "isinstance": builtins.isinstance,
        "issubclass": builtins.issubclass,
        "iter": builtins.iter,
        "len": builtins.len,
        "list": builtins.list,
        "map": builtins.map,
        "max": builtins.max,
        "min": builtins.min,
        "next": builtins.next,
        "object": builtins.object,
        "pow": builtins.pow,
        "print": builtins.print,
        "range": builtins.range,
        "repr": builtins.repr,
        "reversed": builtins.reversed,
        "round": builtins.round,
        "set": builtins.set,
        "slice": builtins.slice,
        "sorted": builtins.sorted,
        "str": builtins.str,
        "sum": builtins.sum,
        "tuple": builtins.tuple,
        "zip": builtins.zip,
        "__import__": _guarded_import,
        "open": _blocked,
        "input": _blocked,
        "eval": _blocked,
        "exec": _blocked,
        "compile": _blocked,
        "help": _blocked,
        "breakpoint": _blocked,
        "exit": _blocked,
        "quit": _blocked,
    }

    globals_ns = _ProtectedGlobals({
        "__builtins__": safe_builtins,
        "document_text": document_text,
        "selection_text": selection_text,
        "outline": outline,
        "result": None,
        "set_result": lambda value: globals_ns.__setitem__("result", value),
    })
    sys.stdin = io.StringIO(input_text)
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(sys.stdout), contextlib.redirect_stderr(sys.stderr):
            exec(compile(code, "<quill-sandbox>", "exec"), globals_ns, globals_ns)
    except BaseException:
        payload = {
            "stdout": sys.stdout.getvalue(),
            "stderr": sys.stderr.getvalue(),
            "result": globals_ns.get("result"),
            "error": traceback.format_exc(),
            "caps_unapplied": _caps_unapplied,
        }
    else:
        payload = {
            "stdout": sys.stdout.getvalue(),
            "stderr": sys.stderr.getvalue(),
            "result": globals_ns.get("result"),
            "error": "",
            "caps_unapplied": _caps_unapplied,
        }
    if payload["result"] is not None and not isinstance(payload["result"], str):
        payload["result"] = str(payload["result"])
    sys.__stdout__.write(json.dumps(payload))
    """
).strip()


@dataclass(frozen=True, slots=True)
class PythonSandboxResult:
    stdout: str
    stderr: str
    result: str
    error: str
    timed_out: bool
    returncode: int
    elapsed_seconds: float

    @property
    def succeeded(self) -> bool:
        return not self.timed_out and self.returncode == 0 and not self.error


def run_python_sandbox(
    code: str,
    *,
    document_text: str = "",
    selection_text: str = "",
    input_text: str = "",
    outline: list[dict[str, Any]] | None = None,
    timeout_seconds: float = 5.0,
    memory_limit_mb: int = 512,
) -> PythonSandboxResult:
    try:
        _validate_code_policy(code)
    except (SyntaxError, ValueError) as error:
        return PythonSandboxResult("", "", "", str(error), False, 1, 0.0)
    # SEC-14: cap address space (POSIX) / process memory (Windows job object) and
    # CPU time so a runaway snippet cannot exhaust the host. Wall-clock time is
    # bounded separately by ``timeout_seconds`` below.
    memory_limit_bytes = max(0, int(memory_limit_mb)) * 1024 * 1024
    cpu_limit_seconds = max(1, int(timeout_seconds) + 1)
    payload = {
        "code_b64": base64.b64encode(code.encode("utf-8")).decode("ascii"),
        "document_text": document_text,
        "selection_text": selection_text,
        "input_text": input_text,
        "outline": outline,
        "allowed_imports": sorted(ALLOWED_IMPORTS),
        "memory_limit_bytes": memory_limit_bytes,
        "cpu_limit_seconds": cpu_limit_seconds,
    }
    # SEC-14: the payload is delivered on stdin, never via the environment, so
    # the sandboxed program cannot recover it from os.environ. Only the minimal
    # OS variables needed to launch the interpreter are forwarded.
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    }
    env.update({
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    stdin_payload = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    start = time.perf_counter()
    completed: subprocess.CompletedProcess[str] | None = None
    timed_out = False
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", "-c", _SANDBOX_BOOTSTRAP],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
            cwd=tempfile.gettempdir(),
            input=stdin_payload,
        )
    except subprocess.TimeoutExpired:
        timed_out = True
    except OSError as error:
        elapsed = time.perf_counter() - start
        return PythonSandboxResult("", "", "", str(error), False, 1, elapsed)
    elapsed = time.perf_counter() - start
    if timed_out:
        return PythonSandboxResult("", "", "", "Execution timed out", True, 124, elapsed)
    assert completed is not None
    if not completed.stdout:
        return PythonSandboxResult(
            "", completed.stderr, "", "No result returned", False, completed.returncode, elapsed
        )
    try:
        payload_data = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return PythonSandboxResult(
            completed.stdout,
            completed.stderr,
            "",
            f"Could not parse sandbox output: {error}",
            False,
            completed.returncode,
            elapsed,
        )
    # SEC-14: if the child could not install its memory/CPU caps, containment is
    # weaker than intended (the run is still wall-clock bounded). Log it so a
    # misconfigured host is visible rather than silently unprotected.
    caps_unapplied = payload_data.get("caps_unapplied") or []
    if caps_unapplied:
        logging.getLogger(__name__).warning(
            "python sandbox resource cap(s) not applied: %s (run was time-bounded only)",
            ", ".join(str(c) for c in caps_unapplied),
        )
    return PythonSandboxResult(
        stdout=str(payload_data.get("stdout", "")),
        stderr=str(payload_data.get("stderr", "")),
        result=str(payload_data.get("result", "")),
        error=str(payload_data.get("error", "")),
        timed_out=False,
        returncode=completed.returncode,
        elapsed_seconds=elapsed,
    )


def _validate_code_policy(code: str) -> None:
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", 1)[0]
                if root_name not in ALLOWED_IMPORTS:
                    raise ValueError(f"Import of {root_name} is not allowed in the sandbox")
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            root_name = node.module.split(".", 1)[0]
            if root_name not in ALLOWED_IMPORTS:
                raise ValueError(f"Import of {root_name} is not allowed in the sandbox")
        # SEC-14 hardening: reject dunder attribute/name access. The classic
        # Python-sandbox escape reaches already-imported modules through the
        # object graph -- e.g. ``().__class__.__base__.__subclasses__()`` to find
        # ``subprocess.Popen`` or ``os.system`` -- which the import guard cannot
        # see. Legitimate snippets that transform document text never need
        # ``__``-prefixed attributes, so blocking them closes the escape without
        # meaningful cost. (The subprocess boundary + resource caps remain the
        # outer defense; this removes the cheap in-process traversal.)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                raise ValueError(
                    f"Access to dunder attribute '{node.attr}' is not allowed in the sandbox"
                )
        elif isinstance(node, ast.Name):
            if node.id.startswith("__") and node.id.endswith("__"):
                raise ValueError(f"Access to dunder name '{node.id}' is not allowed in the sandbox")
