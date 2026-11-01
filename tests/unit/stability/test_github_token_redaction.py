"""GitHub tokens never reach a log, console history or diagnostic bundle.

The Copilot device flow yields a ``gho_`` token; a GitHub App gives ``ghu_``,
fine-grained PATs are ``github_pat_``. Bodies here are deliberately shorter
than the generic 36-character catch-all, so only the prefix rule can match.
"""

from __future__ import annotations

import pytest

from quill.stability.redaction import (
    redact_command_arg,
    redact_source_tokens,
    redact_text_for_bundle,
)

_BODY = "AbCdEf0123456789xyzQ"  # 20 chars: below the generic 36-char rule


@pytest.mark.parametrize("prefix", ["gho_", "ghu_", "ghs_", "ghr_", "ghp_", "github_pat_"])
def test_prefixed_github_tokens_are_redacted(prefix: str) -> None:
    token = prefix + _BODY
    line = f"copilot session started with token {token} ok"
    assert token not in redact_source_tokens(line)
    assert "[TOKEN]" in redact_source_tokens(line)
    assert token not in redact_command_arg(f"--token={token}")
    assert token not in redact_text_for_bundle(line)


def test_ordinary_words_survive() -> None:
    line = "GitHub Copilot answered in 2 seconds"
    assert redact_source_tokens(line) == line
