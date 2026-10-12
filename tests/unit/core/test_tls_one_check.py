"""One certificate check: every secure connection goes through quill/core/net.py.

QUILL and its family apps verify HTTPS certificates the way Windows does, with
the operating-system store via ``truststore``. That only holds if nothing builds
a context of its own and nothing switches verification off, so this gate reads
the source of ``quill/`` and fails on:

(a) anything that turns verification off: ``_create_unverified_context``,
    ``CERT_NONE``/``CERT_OPTIONAL``, ``check_hostname = False``, a replaced
    ``_create_default_https_context``, ``verify=False`` and
    ``cert_reqs="CERT_NONE"``;
(b) an SSL context built anywhere but ``quill/core/net.py``
    (``create_default_context``, ``SSLContext(...)``);
(c) a urllib call (``urlopen``, ``build_opener``, ``HTTPSHandler``,
    ``HTTPSConnection``) in a module that never imports ``quill.core.net``.

It also checks that every app entry point configures the shared trust before
it does anything else, and that ``certificate_problem`` says the one sentence.
"""

from __future__ import annotations

import ast
import ssl
import urllib.error
from functools import cache
from pathlib import Path

import pytest

from quill.core import net

_REPO = Path(__file__).resolve().parents[3]
_QUILL = _REPO / "quill"
_NET = _QUILL / "core" / "net.py"

# Rule (b): modules allowed to build an SSL context themselves, with the reason.
# Keep this empty unless there is no other way.
_CONTEXT_ALLOWLIST: dict[str, str] = {}

# Rule (c): modules whose urllib calls are plain-HTTP by construction, so a TLS
# context would never be used. Each needs a written reason.
_PLAIN_HTTP_ALLOWLIST: dict[str, str] = {}

_URLLIB_CALLS = frozenset({"urlopen", "build_opener", "HTTPSHandler", "HTTPSConnection"})
_UNVERIFIED_NAMES = frozenset({"_create_unverified_context", "CERT_NONE", "CERT_OPTIONAL"})
_CONTEXT_BUILDERS = frozenset({"create_default_context", "SSLContext"})


_OFF_NEEDLES = (
    "_create_unverified_context",
    "CERT_NONE",
    "CERT_OPTIONAL",
    "check_hostname",
    "_create_default_https_context",
    "verify=",
    "cert_reqs",
)


@cache
def _sources() -> tuple[Path, ...]:
    return tuple(sorted(_QUILL.rglob("*.py")))


@cache
def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _mentioning(*needles: str) -> list[Path]:
    """Only the sources that could hold a match; parsing all of quill/ is slow."""
    return [p for p in _sources() if any(n in _text(p) for n in needles)]


def _rel(path: Path) -> str:
    return path.relative_to(_REPO).as_posix()


@cache
def _tree(path: Path) -> ast.Module:
    return ast.parse(_text(path), filename=str(path))


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_false(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _says_cert_none(node: ast.AST) -> bool:
    return (isinstance(node, ast.Constant) and node.value == "CERT_NONE") or (
        _name(node) == "CERT_NONE"
    )


def _imports_net(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "quill.core.net":
                return True
            if node.module == "quill.core" and any(a.name == "net" for a in node.names):
                return True
        if isinstance(node, ast.Import) and any(a.name == "quill.core.net" for a in node.names):
            return True
    return False


def test_nothing_switches_certificate_verification_off() -> None:
    offenders: list[str] = []
    for path in _mentioning(*_OFF_NEEDLES):
        for node in ast.walk(_tree(path)):
            where = f"{_rel(path)}:{getattr(node, 'lineno', 0)}"
            if isinstance(node, (ast.Attribute, ast.Name)) and _name(node) in _UNVERIFIED_NAMES:
                offenders.append(f"{where} {_name(node)}")
            elif isinstance(node, ast.alias) and node.name in _UNVERIFIED_NAMES:
                offenders.append(f"{_rel(path)} imports {node.name}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    attr = _name(target)
                    if attr == "check_hostname" and _is_false(node.value):
                        offenders.append(f"{where} check_hostname = False")
                    if attr == "_create_default_https_context":
                        offenders.append(f"{where} replaces the default HTTPS context")
            elif isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "verify" and _is_false(keyword.value):
                        offenders.append(f"{where} verify=False")
                    if keyword.arg == "cert_reqs" and _says_cert_none(keyword.value):
                        offenders.append(f"{where} cert_reqs=CERT_NONE")
    assert not offenders, "Certificate verification switched off: " + "; ".join(offenders)


def test_only_net_builds_an_ssl_context() -> None:
    offenders: list[str] = []
    for path in _mentioning(*_CONTEXT_BUILDERS):
        if path == _NET or _rel(path) in _CONTEXT_ALLOWLIST:
            continue
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call) and _name(node.func) in _CONTEXT_BUILDERS:
                offenders.append(f"{_rel(path)}:{node.lineno} {_name(node.func)}()")
    assert not offenders, (
        "Build TLS contexts only in quill/core/net.py; use net.verified_ssl_context() "
        "or net.context_for(url): " + "; ".join(offenders)
    )


def test_every_urllib_caller_goes_through_net() -> None:
    offenders: list[str] = []
    for path in _mentioning(*_URLLIB_CALLS):
        if _rel(path) in _PLAIN_HTTP_ALLOWLIST:
            continue
        tree = _tree(path)
        calls = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _name(node.func) in _URLLIB_CALLS
        ]
        if calls and not _imports_net(tree):
            offenders.append(f"{_rel(path)} (line {calls[0]})")
    assert not offenders, (
        "These modules open URLs without quill.core.net; pass "
        "context=verified_ssl_context() or context=context_for(url): " + "; ".join(offenders)
    )


def test_allowlists_name_real_files_with_reasons() -> None:
    for allowlist in (_CONTEXT_ALLOWLIST, _PLAIN_HTTP_ALLOWLIST):
        for rel, reason in allowlist.items():
            assert (_REPO / rel).is_file(), f"{rel} no longer exists; drop it from the allowlist"
            assert len(reason.split()) >= 4, f"{rel} needs a written reason"


def _app_entry_modules() -> list[Path]:
    """Every module under quill/apps that defines a top-level ``main``."""
    found: list[Path] = []
    for path in _mentioning("def main("):
        if (_QUILL / "apps") not in path.parents:
            continue
        tree = _tree(path)
        if any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body):
            found.append(path)
    return found


def _first_statement(main: ast.FunctionDef) -> ast.stmt:
    body = main.body
    head = body[0]
    if isinstance(head, ast.Expr) and isinstance(head.value, ast.Constant):
        return body[1]
    return head


def _calls_configure_first(main: ast.FunctionDef) -> bool:
    body = main.body
    start = body.index(_first_statement(main))
    for stmt in body[start:]:
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "quill.core.net":
            continue
        return (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and _name(stmt.value.func) == "configure_ssl_trust"
        )
    return False


def test_there_are_app_entry_points_to_check() -> None:
    names = {p.stem for p in _app_entry_modules()}
    assert {"radio", "podcasts", "lite", "weather", "studio", "player"} <= names


@pytest.mark.parametrize("path", _app_entry_modules(), ids=lambda p: _rel(p))
def test_every_app_main_configures_trust_first(path: Path) -> None:
    main = next(n for n in _tree(path).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    assert _calls_configure_first(main), (
        f"{_rel(path)}: main() must call quill.core.net.configure_ssl_trust() before anything else"
    )


def test_quill_main_and_the_apps_package_configure_trust() -> None:
    main = next(
        n
        for n in _tree(_QUILL / "__main__.py").body
        if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    assert _calls_configure_first(main)
    package = _tree(_QUILL / "apps" / "__init__.py")
    assert any(
        isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and _name(n.value.func) == "configure_ssl_trust"
        for n in package.body
    )


# Standalone wrappers that do not start QUILL code, with the reason.
_STANDALONE_EXEMPT = {
    "radio-mac": "the macOS port is a separate stdlib-only package outside the Windows family",
    "social": "QUILL Social is its own package and does not run quill.apps code",
}


def _standalone_mains() -> list[Path]:
    found: list[Path] = []
    for app in sorted((_REPO / "standalone").iterdir()):
        if not app.is_dir() or app.name in _STANDALONE_EXEMPT:
            continue
        for init in sorted(app.glob("quill_*/__init__.py")):
            found.append(init)
        launcher = app / "launcher.py"
        if launcher.is_file() and not list(app.glob("quill_*/__init__.py")):
            found.append(launcher)
    return found


@pytest.mark.parametrize("path", _standalone_mains(), ids=lambda p: _rel(p))
def test_standalone_wrappers_start_through_quill_apps(path: Path) -> None:
    """A wrapper that runs ``quill.apps.<app>.main`` inherits the trust call."""
    main = next(
        (n for n in _tree(path).body if isinstance(n, ast.FunctionDef) and n.name == "main"),
        None,
    )
    assert main is not None, f"{_rel(path)} has no main()"
    modules = {n.module or "" for n in ast.walk(main) if isinstance(n, ast.ImportFrom)}
    assert any(m.startswith("quill.apps") for m in modules), (
        f"{_rel(path)}: main() must start the app through quill.apps so trust is configured"
    )


def test_feed_problems_says_the_shared_sentence() -> None:
    from quill.core.podcasts import feed_problems

    assert feed_problems.sentence_for(feed_problems.CERTIFICATE) == net.CERTIFICATE_SENTENCE


def _verify_error() -> ssl.SSLCertVerificationError:
    error = ssl.SSLCertVerificationError(
        1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer"
    )
    return error


class _MaxRetryLike(Exception):
    def __init__(self, reason: BaseException) -> None:
        super().__init__("Max retries exceeded")
        self.reason = reason


class SSLError(OSError):
    """Stands in for requests.exceptions.SSLError, which wraps urllib3's error in args."""


@pytest.mark.parametrize(
    "error",
    [
        _verify_error(),
        urllib.error.URLError(_verify_error()),
        SSLError(_MaxRetryLike(_verify_error())),
        ssl.SSLError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"),
    ],
    ids=["bare", "urllib", "requests", "text-only"],
)
def test_certificate_problem_recognises_a_bad_certificate(error: BaseException) -> None:
    assert net.certificate_problem(error) == net.CERTIFICATE_SENTENCE


def test_certificate_problem_follows_the_cause_chain() -> None:
    try:
        try:
            raise _verify_error()
        except ssl.SSLError as inner:
            raise RuntimeError("download failed") from inner
    except RuntimeError as outer:
        assert net.certificate_problem(outer) == net.CERTIFICATE_SENTENCE


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timed out"),
        urllib.error.URLError(ConnectionRefusedError(10061, "refused")),
        ssl.SSLError(1, "[SSL: WRONG_VERSION_NUMBER] wrong version number"),
        ValueError("certificate field missing"),
    ],
)
def test_certificate_problem_ignores_other_failures(error: BaseException) -> None:
    assert net.certificate_problem(error) is None


def test_context_for_verifies_https_and_skips_plain_http() -> None:
    context = net.context_for("https://example.org/feed")
    assert context is not None
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert net.context_for("http://127.0.0.1:11434/api/tags") is None
