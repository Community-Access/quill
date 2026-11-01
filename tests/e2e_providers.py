"""End-to-end smoke tests for QUILL AI provider integration.

Tests every cloud provider QUILL supports using QUILL's actual code paths
(not raw HTTP) so failures here mean the product will fail for users.

Run:
    python tests/e2e_providers.py

Keys are read from environment variables. Set them or pass them on the command
line in KEY=VALUE pairs:

    python tests/e2e_providers.py GEMINI_KEY=... CLAUDE_KEY=... OPENAI_KEY=...
"""

from __future__ import annotations

import os
import sys
import textwrap

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Key resolution — env vars or KEY=VALUE args
# ---------------------------------------------------------------------------

_overrides: dict[str, str] = {}
for _arg in sys.argv[1:]:
    if "=" in _arg:
        _k, _v = _arg.split("=", 1)
        _overrides[_k.strip()] = _v.strip()


def _key(name: str) -> str:
    return _overrides.get(name, os.environ.get(name, ""))


GEMINI_KEY = _key("GEMINI_KEY")
CLAUDE_KEY = _key("CLAUDE_KEY")
OPENAI_KEY = _key("OPENAI_KEY")
OPENROUTER_KEY = _key("OPENROUTER_KEY")
from quill.stability.redaction import redact_known_secrets, remember_secret  # noqa: E402

for _secret in (GEMINI_KEY, CLAUDE_KEY, OPENAI_KEY, OPENROUTER_KEY):
    remember_secret(_secret)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_FAILURES: list[str] = []
_SKIPPED: list[str] = []


def _check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    # An error string can quote the request, key and all: scrub what this run
    # was given before it reaches the console (CodeQL clear-text logging).
    suffix = f"  ({redact_known_secrets(detail)})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    if not passed:
        _FAILURES.append(label)


def _skip(label: str, reason: str) -> None:
    print(f"  [SKIP] {label}  ({reason})")
    _SKIPPED.append(label)


from quill.core.ai.provider_backend import ProviderChatBackend  # noqa: E402
from quill.core.assistant_ai import (  # noqa: E402
    AssistantConnectionSettings,
    generate_assistant_response,
    generate_assistant_response_stream,
    list_assistant_models,
    verify_assistant_connection,
)

_SAMPLE_DOC = textwrap.dedent("""\
    QUILL is a screen-reader-first word processor for Windows.
    It supports AI-assisted writing, Markdown, and rich text.
""")


def _run_provider_suite(
    name: str,
    settings: AssistantConnectionSettings,
    api_key: str,
    *,
    expect_model_list: bool = True,
) -> None:
    """Run the standard 6-check suite against one provider."""
    print(f"\n=== {name} ===")

    # 1. List models
    models, err = list_assistant_models(settings, api_key, timeout_seconds=20)
    if expect_model_list:
        _check(f"{name}: list models returns no error", err is None, err or "")
        _check(
            f"{name}: model list non-empty",
            bool(models),
            f"{len(models) if models else 0} models",
        )
        if models:
            print(f"     First 5 models: {models[:5]}")
    else:
        print(f"     Model listing skipped for {name}")

    # 2. Verify connection
    ok, msg = verify_assistant_connection(settings, api_key, timeout_seconds=20)
    _check(f"{name}: verify connection", ok, msg)

    # 3. Non-streaming generate
    text, err = generate_assistant_response(
        settings,
        api_key,
        "Reply with exactly: pong",
        max_tokens=24,
        timeout_seconds=30,
    )
    _check(f"{name}: non-streaming generate no error", err is None, err or "")
    _check(f"{name}: non-streaming response non-empty", bool(text and text.strip()), repr(text))
    if text:
        print(f"     Response: {text.strip()[:80]}")

    # 4. Streaming generate
    fragments: list[str] = []
    stream_text, stream_err = generate_assistant_response_stream(
        settings,
        api_key,
        "Count from 1 to 3, one number per line.",
        lambda frag: fragments.append(frag),
        max_tokens=32,
        timeout_seconds=30,
    )
    _check(f"{name}: streaming generate no error", stream_err is None, stream_err or "")
    _check(
        f"{name}: streaming fragments delivered",
        len(fragments) > 0,
        f"{len(fragments)} fragments",
    )
    if stream_text:
        print(f"     Streamed: {stream_text.strip()[:80]}")

    # 5. ProviderChatBackend
    backend = ProviderChatBackend(settings=settings, api_key=api_key)
    avail, reason = backend.is_available()
    _check(f"{name}: backend available", avail, reason or "")
    if avail:
        response = None
        backend_err = None
        try:
            response = backend.respond("Reply with exactly: pong")
        except RuntimeError as exc:
            backend_err = str(exc)
        _check(f"{name}: backend.respond succeeds", backend_err is None, backend_err or "")
        _check(
            f"{name}: backend response non-empty",
            bool(response and response.strip()),
            repr(response),
        )

    # 6. Writing task
    summary_text, summary_err = generate_assistant_response(
        settings,
        api_key,
        f"Summarize the following in one sentence:\n\n{_SAMPLE_DOC}",
        max_tokens=80,
        timeout_seconds=30,
    )
    _check(f"{name}: summarize prompt no error", summary_err is None, summary_err or "")
    _check(
        f"{name}: summary non-empty",
        bool(summary_text and summary_text.strip()),
        repr(summary_text),
    )
    if summary_text:
        print(f"     Summary: {summary_text.strip()[:120]}")


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

if not GEMINI_KEY:
    _skip("Gemini suite", "GEMINI_KEY not set")
else:
    _run_provider_suite(
        "Google Gemini",
        AssistantConnectionSettings(
            provider="gemini",
            host="https://generativelanguage.googleapis.com",
            model="gemini-2.5-flash",
        ),
        GEMINI_KEY,
    )

# ---------------------------------------------------------------------------
# Claude (Anthropic)
# ---------------------------------------------------------------------------

if not CLAUDE_KEY:
    _skip("Claude suite", "CLAUDE_KEY not set")
else:
    _run_provider_suite(
        "Claude (Anthropic)",
        AssistantConnectionSettings(
            provider="claude",
            host="https://api.anthropic.com",
            model="claude-haiku-4-5-20251001",
        ),
        CLAUDE_KEY,
    )

# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

if not OPENAI_KEY:
    _skip("OpenAI suite", "OPENAI_KEY not set")
else:
    _run_provider_suite(
        "OpenAI",
        AssistantConnectionSettings(
            provider="openai",
            host="https://api.openai.com",
            model="gpt-4o-mini",
        ),
        OPENAI_KEY,
    )

# ---------------------------------------------------------------------------
# OpenRouter
# ---------------------------------------------------------------------------

if not OPENROUTER_KEY:
    _skip("OpenRouter suite", "OPENROUTER_KEY not set")
else:
    _run_provider_suite(
        "OpenRouter",
        AssistantConnectionSettings(
            provider="openrouter",
            host="https://openrouter.ai/api",
            model="openrouter/auto",
        ),
        OPENROUTER_KEY,
        expect_model_list=True,
    )

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
if _SKIPPED:
    print(f"Skipped: {len(_SKIPPED)} suite(s) — {', '.join(_SKIPPED)}")
if _FAILURES:
    print(f"RESULT: {len(_FAILURES)} FAILED — {', '.join(_FAILURES)}")
    sys.exit(1)
else:
    active = [
        s for s in ("Gemini", "Claude", "OpenAI", "OpenRouter") if any(s in f for f in []) or True
    ]
    ran = 4 - len(_SKIPPED)
    print(f"RESULT: all checks passed  ({ran} provider(s) tested)")
    sys.exit(0)
