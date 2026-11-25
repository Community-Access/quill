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

It also checks that every app configures the shared trust before its first
network callback. Windowed apps may defer that setup until their shell exists;
headless commands must still configure it synchronously.
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

#: Wrapper modules that are themselves the one place their callers open URLs,
#: every call passing ``context=`` from quill.core.net (asserted below by
#: test_every_verified_opener_passes_a_net_context). A caller importing one of
#: these goes through net as surely as one importing net itself; without this,
#: the seven cloud dictation providers (D-31 to D-37), which all open through
#: cloud/transport.py, read as offenders.
_VERIFIED_OPENERS: dict[str, str] = {
    "quill.core.windows_dictation.cloud.transport": (
        "quill/core/windows_dictation/cloud/transport.py"
    ),
}

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


#: Standalone packages outside quill/ that ship the quill package and so must use
#: its one check too. Quill Social built its own context here until 2026-10-15,
#: because this gate read only quill/. Quill Radio for Mac is not listed: it is a
#: separate macOS app that does not ship the quill package or truststore.
_STANDALONE_EXEMPT = ("radio-mac",)


@cache
def _sources() -> tuple[Path, ...]:
    standalone = [
        path
        for pkg in sorted((_REPO / "standalone").glob("*/quill_*"))
        if pkg.is_dir() and pkg.parent.name not in _STANDALONE_EXEMPT
        for path in pkg.rglob("*.py")
    ]
    return tuple(sorted([*_QUILL.rglob("*.py"), *standalone]))


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


def _is_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


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
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if (
                    f"{node.module}.{alias.name}" in _VERIFIED_OPENERS
                    or node.module in _VERIFIED_OPENERS
                ):
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


_SHELL_DEFERRED_APPS = {
    "quill/apps/converter.py",
    "quill/apps/inkwell.py",
    "quill/apps/player.py",
    "quill/apps/podcasts.py",
    "quill/apps/radio.py",
    "quill/apps/studio.py",
    "quill/apps/transcribe.py",
    "quill/apps/weather.py",
}


def test_there_are_app_entry_points_to_check() -> None:
    names = {p.stem for p in _app_entry_modules()}
    assert {"radio", "podcasts", "lite", "weather", "studio", "player"} <= names


@pytest.mark.parametrize("path", _app_entry_modules(), ids=lambda p: _rel(p))
def test_every_app_main_configures_trust_before_network(path: Path) -> None:
    main = next(n for n in _tree(path).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    relative = _rel(path)
    if relative in _SHELL_DEFERRED_APPS:
        assert "AppShellFrame" in _text(path), (
            f"{relative}: deferred trust setup requires the shared AppShellFrame"
        )
        return
    if relative == "quill/apps/beacon/__init__.py":
        app = _tree(_QUILL / "apps" / "beacon" / "app.py")
        assert any(
            _name(n.func) == "defer_ssl_trust_setup"
            for n in ast.walk(app)
            if isinstance(n, ast.Call)
        )
        return
    if relative == "quill/apps/lite.py":
        startup = _tree(_QUILL / "apps" / "lite_startup.py")
        assert any(
            _name(n.func) == "configure_ssl_trust"
            for n in ast.walk(startup)
            if isinstance(n, ast.Call)
        )
        return
    assert _calls_configure_first(main), (
        f"{relative}: headless or CLI main() must configure trust before anything else"
    )


def test_windowed_apps_defer_trust_setup_until_after_their_shell_exists() -> None:
    app_shell = _tree(_QUILL / "ui" / "app_shell.py")
    init_shell = next(
        n
        for cls in ast.walk(app_shell)
        if isinstance(cls, ast.ClassDef) and cls.name == "AppShellFrame"
        for n in cls.body
        if isinstance(n, ast.FunctionDef) and n.name == "_init_app_shell"
    )
    setup_call = next(
        index
        for index, line in enumerate(init_shell.body)
        if any(
            isinstance(n, ast.Call) and _name(n.func) == "defer_ssl_trust_setup"
            for n in ast.walk(line)
        )
    )
    frame_assignment = next(
        index
        for index, line in enumerate(init_shell.body)
        if any(
            isinstance(n, ast.Attribute) and n.attr == "frame"
            for n in ast.walk(line)
            if isinstance(n, (ast.Attribute, ast.Assign))
        )
    )
    assert setup_call < frame_assignment


def test_quill_and_the_apps_package_do_not_import_trust_before_a_window() -> None:
    main = next(
        n
        for n in _tree(_QUILL / "__main__.py").body
        if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    assert not _calls_configure_first(main)
    deferred = next(
        n
        for n in _tree(_QUILL / "ui" / "main_frame.py").body
        if isinstance(n, ast.ClassDef) and n.name == "MainFrame"
        for n in n.body
        if isinstance(n, ast.FunctionDef) and n.name == "_run_deferred_startup_tasks"
    )
    assert any(
        _name(n.func) == "configure_ssl_trust"
        for n in ast.walk(deferred)
        if isinstance(n, ast.Call)
    )
    package = _tree(_QUILL / "apps" / "__init__.py")
    assert not any(
        (isinstance(n, ast.ImportFrom) and n.module == "quill.core.net")
        or (isinstance(n, ast.Import) and any(alias.name == "quill.core.net" for alias in n.names))
        for n in ast.walk(package)
    )


def test_social_defers_live_network_refresh_and_trust_setup_until_show() -> None:
    app = _tree(_REPO / "standalone" / "social" / "quill_social" / "ui" / "app.py")
    source = _text(_REPO / "standalone" / "social" / "quill_social" / "ui" / "app.py")
    frame_show = source.index("frame.Show()")
    assert source.index("defer_ssl_trust_setup(wx)", frame_show) > frame_show
    assert source.index("frame._refresh_from_network", frame_show) > frame_show
    constructor = next(
        n
        for n in ast.walk(app)
        if isinstance(n, ast.ClassDef) and n.name == "SocialFrame"
        for n in n.body
        if isinstance(n, ast.FunctionDef) and n.name == "__init__"
    )
    assert any(
        isinstance(n, ast.Call)
        and _name(n.func) == "_refresh_from_network"
        and any(keyword.arg == "local_only" and _is_true(keyword.value) for keyword in n.keywords)
        for n in ast.walk(constructor)
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


def test_every_verified_opener_passes_a_net_context() -> None:
    """A wrapper counts as going through net only if every URL or socket it
    opens is given a context from quill.core.net."""
    for module, rel in _VERIFIED_OPENERS.items():
        path = _REPO / rel
        assert path.is_file(), f"{module} no longer exists; drop it from _VERIFIED_OPENERS"
        tree = _tree(path)
        assert "verified_ssl_context" in path.read_text(encoding="utf-8"), rel
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _name(node.func) in {"_open", "connect"}:
                keywords = {k.arg for k in node.keywords}
                assert keywords & {"context", "ssl"}, (
                    f"{rel}:{node.lineno} opens a connection without a net context"
                )
