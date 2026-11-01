"""End-to-end smoke test for Gemini AI integration in QUILL.

Run: python tests/e2e_gemini.py
Requires the Gemini API key in the GEMINI_API_KEY environment variable
or passed as the first CLI argument.
"""

from __future__ import annotations

import os
import sys
import textwrap

# Allow running from repo root without installing.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

GEMINI_KEY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GEMINI_API_KEY", "")
from quill.stability.redaction import redact_known_secrets, remember_secret  # noqa: E402

remember_secret(GEMINI_KEY)
if not GEMINI_KEY:
    print("FAIL: no key — pass as argv[1] or set GEMINI_API_KEY")
    sys.exit(1)


def _check(label: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    # An error string can quote the request, key and all: scrub what this run
    # was given before it reaches the console (CodeQL clear-text logging).
    suffix = f"  ({redact_known_secrets(detail)})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    if not passed:
        _FAILURES.append(label)


_FAILURES: list[str] = []

from quill.core.assistant_ai import (  # noqa: E402
    AssistantConnectionSettings,
    generate_assistant_response,
    generate_assistant_response_stream,
    list_assistant_models,
    verify_assistant_connection,
)

SETTINGS = AssistantConnectionSettings(
    provider="gemini",
    host="https://generativelanguage.googleapis.com",
    model="gemini-2.5-flash",
)

# ---------------------------------------------------------------------------
# 1. List models
# ---------------------------------------------------------------------------
print("\n=== 1. List models ===")
models, err = list_assistant_models(SETTINGS, GEMINI_KEY, timeout_seconds=15)
_check("list_assistant_models returns no error", err is None, err or "")
_check("model list is non-empty", bool(models), f"got {len(models) if models else 0}")
if models:
    gemini_flash = next((m for m in models if "flash" in m.lower()), None)
    _check(
        "gemini-2.5-flash (or variant) present in list",
        gemini_flash is not None,
        gemini_flash or "not found",
    )
    print(f"     First 5 models: {models[:5]}")

# ---------------------------------------------------------------------------
# 2. Verify connection
# ---------------------------------------------------------------------------
print("\n=== 2. Verify connection ===")
ok, msg = verify_assistant_connection(SETTINGS, GEMINI_KEY, timeout_seconds=15)
_check("verify_assistant_connection succeeds", ok, msg)

# ---------------------------------------------------------------------------
# 3. Basic generate (non-streaming)
# ---------------------------------------------------------------------------
print("\n=== 3. Non-streaming generate ===")
text, err = generate_assistant_response(
    SETTINGS,
    GEMINI_KEY,
    "Reply with exactly: pong",
    max_tokens=16,
    timeout_seconds=30,
)
_check("generate_assistant_response returns no error", err is None, err or "")
_check("response is non-empty", bool(text and text.strip()), repr(text))
if text:
    print(f"     Response: {text.strip()[:120]}")

# ---------------------------------------------------------------------------
# 4. Streaming generate
# ---------------------------------------------------------------------------
print("\n=== 4. Streaming generate ===")
fragments: list[str] = []
text_stream, err_stream = generate_assistant_response_stream(
    SETTINGS,
    GEMINI_KEY,
    "Count from 1 to 3, one number per line.",
    lambda frag: fragments.append(frag),
    max_tokens=32,
    timeout_seconds=30,
)
_check("streaming generate returns no error", err_stream is None, err_stream or "")
_check(
    "at least one streaming fragment delivered",
    len(fragments) > 0,
    f"{len(fragments)} fragments",
)
_check("streaming text is non-empty", bool(text_stream and text_stream.strip()), repr(text_stream))
if text_stream:
    print(f"     Streamed result: {text_stream.strip()[:120]}")

# ---------------------------------------------------------------------------
# 5. ProviderChatBackend (higher-level adapter)
# ---------------------------------------------------------------------------
print("\n=== 5. ProviderChatBackend ===")
from quill.core.ai.provider_backend import ProviderChatBackend  # noqa: E402

backend = ProviderChatBackend(settings=SETTINGS, api_key=GEMINI_KEY)
avail, reason = backend.is_available()
_check("backend.is_available() is True", avail, reason or "")

response = None
backend_err = None
try:
    response = backend.respond("Reply with exactly: pong")
except RuntimeError as exc:
    backend_err = str(exc)
_check("backend.respond() succeeds", backend_err is None, backend_err or "")
_check("backend response non-empty", bool(response and response.strip()), repr(response))

# ---------------------------------------------------------------------------
# 6. Prompt Library backend path (generate with a writing prompt)
# ---------------------------------------------------------------------------
print("\n=== 6. Writing prompt (summarize) ===")
sample_doc = textwrap.dedent("""\
    QUILL is a screen-reader-first word processor for Windows.
    It supports AI-assisted writing, Markdown, and rich text.
    QUILL integrates with providers like Gemini, OpenAI, and local Ollama models.
""")
summarize_prompt = f"Summarize the following document in one sentence:\n\n{sample_doc}"
summary_text, summary_err = generate_assistant_response(
    SETTINGS, GEMINI_KEY, summarize_prompt, max_tokens=80, timeout_seconds=30
)
_check("summarize prompt returns no error", summary_err is None, summary_err or "")
_check("summary is non-empty", bool(summary_text and summary_text.strip()), repr(summary_text))
if summary_text:
    print(f"     Summary: {summary_text.strip()[:200]}")

# ---------------------------------------------------------------------------
# 7. Grammar check prompt path
# ---------------------------------------------------------------------------
print("\n=== 7. Grammar check prompt ===")
grammar_prompt = (
    "Identify any grammar errors in the following sentence and correct them. "
    "If there are no errors, say 'No errors found.'\n\n"
    "Sentence: 'She don't like going to the store on fridays.'"
)
grammar_text, grammar_err = generate_assistant_response(
    SETTINGS, GEMINI_KEY, grammar_prompt, max_tokens=80, timeout_seconds=30
)
_check("grammar check returns no error", grammar_err is None, grammar_err or "")
_check(
    "grammar response non-empty",
    bool(grammar_text and grammar_text.strip()),
    repr(grammar_text),
)
if grammar_text:
    print(f"     Grammar response: {grammar_text.strip()[:200]}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if _FAILURES:
    print(f"RESULT: {len(_FAILURES)} FAILED — {', '.join(_FAILURES)}")
    sys.exit(1)
else:
    print("RESULT: all checks passed")
    sys.exit(0)
