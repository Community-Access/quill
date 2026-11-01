"""GATE-CAPS: no AI request reaches a connection that cannot do it (codex.md 10A.8).

Choose Your AI's capability registry (:mod:`quill.core.ai.connection_caps`)
says what each connection can do; this gate makes sure every request asks it.
Three checks, all static, all fast:

1. **Every claim names its source.** A capability with an empty ``source`` is
   a guess, and a guess is a request that fails on the far side.
2. **Every hosted-AI entry point declares what it needs.** A call to the
   shared service's ``ask``, ``converse`` or ``describe_image`` anywhere in
   ``quill/ui`` or ``quill/apps`` passes ``requires=(...)``, and the service's
   own three methods call ``request_allowed`` -- the one place
   :func:`~quill.core.ai.connection_caps.require` is asked before anything
   leaves.
3. **Nothing goes round the check.** An engine call -- the ChatGPT plan's
   ``ask_with_chatgpt`` / ``converse_with_chatgpt`` /
   ``describe_image_with_chatgpt`` / ``respond_on_plan``, the own key's
   ``ask_with_own_key`` / ``describe_image_with_own_key``, or the free
   service's ``client.ask`` / ``client.converse`` -- sits in a function that
   also calls ``require(`` or ``request_allowed(``.

The behavioural half -- a faked registry record lacking a capability, and no
request reaching that connection -- is ``tests/unit/ui/test_hosted_ai_connections.py``.

Usage::

    python -m quill.tools.connection_caps_audit
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where hosted-AI requests are made from (10A.8: quill/ui and quill/apps).
SCAN_ROOTS: tuple[str, ...] = ("quill/ui", "quill/apps")

#: The shared service's request methods, which must declare ``requires=``.
SERVICE_METHODS = frozenset({"ask", "converse", "describe_image"})

#: Calls that send a request to a connection directly.
ENGINE_FUNCTIONS = frozenset({
    "ask_with_chatgpt",
    "converse_with_chatgpt",
    "describe_image_with_chatgpt",
    "respond_on_plan",
    "ask_with_own_key",
    "describe_image_with_own_key",
})
#: ``client.ask`` / ``client.converse``: the free service's gateway client.
CLIENT_METHODS = frozenset({"ask", "converse"})

#: Calls that count as asking the registry first.
CHECKS = frozenset({"require", "request_allowed"})

SERVICE_MODULE = "quill/ui/hosted_ai_service.py"


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _called_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _receiver(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Attribute):
        try:
            return ast.unparse(func.value)
        except Exception:  # noqa: BLE001 - an odd receiver is simply not a service
            return ""
    return ""


def _outer_functions(tree: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Module-level functions and methods: the unit a check must share with a call."""
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield item


def _calls(node: ast.AST) -> Iterator[ast.Call]:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            yield child


def _is_service_request(call: ast.Call) -> bool:
    if _called_name(call) not in SERVICE_METHODS or not isinstance(call.func, ast.Attribute):
        return False
    return "service" in _receiver(call).lower()


def _is_engine_call(call: ast.Call) -> bool:
    name = _called_name(call)
    if name in ENGINE_FUNCTIONS:
        return True
    return name in CLIENT_METHODS and _receiver(call) == "client"


def scan_source(source: str, path: str) -> list[Finding]:
    """Every GATE-CAPS finding in one module's *source*."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [Finding(path, error.lineno or 0, "could not be parsed")]
    findings: list[Finding] = []
    for function in _outer_functions(tree):
        calls = list(_calls(function))
        checked = any(_called_name(call) in CHECKS for call in calls)
        for call in calls:
            if _is_service_request(call) and not any(k.arg == "requires" for k in call.keywords):
                findings.append(
                    Finding(
                        path,
                        call.lineno,
                        f"{_receiver(call)}.{_called_name(call)}(...) declares no requires=(...)",
                    )
                )
            if _is_engine_call(call) and not checked:
                findings.append(
                    Finding(
                        path,
                        call.lineno,
                        f"{_called_name(call)}(...) in {function.name}() bypasses require(...)",
                    )
                )
        if path == SERVICE_MODULE and function.name in SERVICE_METHODS:
            if not any(_called_name(call) == "request_allowed" for call in calls):
                findings.append(
                    Finding(
                        path, function.lineno, f"AiService.{function.name} skips request_allowed"
                    )
                )
    return findings


def _files(roots: Iterable[str]) -> Iterator[Path]:
    for root in roots:
        yield from sorted((_REPO_ROOT / root).rglob("*.py"))


def scan_tree(roots: Iterable[str] = SCAN_ROOTS) -> list[Finding]:
    findings: list[Finding] = []
    for path in _files(roots):
        rel = path.relative_to(_REPO_ROOT).as_posix()
        findings.extend(scan_source(path.read_text(encoding="utf-8"), rel))
    return findings


def claim_findings() -> list[Finding]:
    """Every capability claim with an empty source, for every own-key provider.

    My own key has one record per provider it offers (decision 20), so each
    provider in :data:`~quill.core.ai.own_key_providers.PROVIDERS` is checked:
    a provider added to the list without a sourced record fails here.
    """
    from quill.core.ai.connection_caps import all_records
    from quill.core.ai.own_key_providers import PROVIDERS

    path = "quill/core/ai/connection_caps.py"
    findings: list[Finding] = []
    for provider in PROVIDERS:
        for record in all_records(own_key_provider=provider, web_search_enabled=True):
            for capability, claim in record.claims.items():
                if not claim.source.strip():
                    who = record.connection
                    if who == "own_key":
                        who = f"own_key[{provider}]"
                    finding = Finding(path, 0, f"{who}.{capability} names no source")
                    if finding not in findings:
                        findings.append(finding)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.parse_args(argv)
    findings = claim_findings() + scan_tree()
    for finding in findings:
        print(finding)
    if findings:
        print(f"GATE-CAPS: {len(findings)} finding(s).")
        return 1
    print("GATE-CAPS: every request asks the capability registry first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
