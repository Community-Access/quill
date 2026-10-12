from __future__ import annotations

import ast
import ssl
from pathlib import Path

import pytest

from quill.core.net import configure_ssl_trust, ssl_trust_configured, verified_ssl_context

_QUILL_ROOT = Path(__file__).resolve().parents[3] / "quill"

# Patterns that disable TLS verification. None of these may appear anywhere in
# the shipped package (SEC-5: AI, update, and download requests verify certs).
_FORBIDDEN_SNIPPETS = (
    "_create_unverified_context",
    "CERT_NONE",
)


def test_verified_context_requires_certificates() -> None:
    context = verified_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_application_truststore_configuration_is_idempotent() -> None:
    configure_ssl_trust()
    assert ssl_trust_configured()
    context = ssl.create_default_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_application_entrypoints_configure_truststore_before_running() -> None:
    main_source = (_QUILL_ROOT / "__main__.py").read_text(encoding="utf-8")
    main_tree = ast.parse(main_source)
    main = next(
        node for node in main_tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    first = main.body[0]
    second = main.body[1]
    assert isinstance(first, ast.ImportFrom)
    assert first.module == "quill.core.net"
    assert isinstance(second, ast.Expr)
    assert isinstance(second.value, ast.Call)
    assert isinstance(second.value.func, ast.Name)
    assert second.value.func.id == "configure_ssl_trust"

    apps_source = (_QUILL_ROOT / "apps" / "__init__.py").read_text(encoding="utf-8")
    apps_tree = ast.parse(apps_source)
    assert any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "configure_ssl_trust"
        for node in apps_tree.body
    )


def _python_sources() -> list[Path]:
    return sorted(_QUILL_ROOT.rglob("*.py"))


def test_no_unverified_ssl_context_in_package() -> None:
    offenders: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for snippet in _FORBIDDEN_SNIPPETS:
            if snippet in text:
                offenders.append(f"{path.relative_to(_QUILL_ROOT)}: {snippet}")
    assert not offenders, "Unverified TLS usage found: " + "; ".join(offenders)


def test_no_check_hostname_or_verify_mode_disabled() -> None:
    # Catch `ctx.check_hostname = False` and `ctx.verify_mode = ssl.CERT_NONE`
    # style assignments via AST so formatting variations cannot hide them.
    # Prefilter by text before AST parsing to avoid walking every file in the
    # package; files that don't mention the attribute names can't contain the
    # violation.
    _AST_PREFILTER = ("check_hostname", "verify_mode")
    offenders: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        if not any(needle in text for needle in _AST_PREFILTER):
            continue
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and target.attr == "check_hostname"
                        and isinstance(node.value, ast.Constant)
                        and node.value.value is False
                    ):
                        offenders.append(f"{path.relative_to(_QUILL_ROOT)}:{node.lineno}")
    assert not offenders, "check_hostname disabled at: " + "; ".join(offenders)


@pytest.mark.parametrize(
    "url,expect_https",
    [
        ("https://api.openai.com/v1/models", True),
        ("http://localhost:11434/api/tags", False),
    ],
)
def test_assistant_context_only_for_https(url: str, expect_https: bool) -> None:
    from quill.core.assistant_ai import _context_for

    context = _context_for(url)
    if expect_https:
        assert context is not None
        assert context.verify_mode == ssl.CERT_REQUIRED
    else:
        assert context is None
