"""Payment provider secrets never reach a log or a diagnostic bundle.

QUILL holds no Stripe or PayPal secret -- the QAF plugin keeps them on the
WordPress site -- but a site's error message, pasted or logged, could carry
one. Bodies here are shorter than the generic 36-character catch-all, so only
the prefix rules can match.
"""

from __future__ import annotations

import pytest

from quill.stability.redaction import redact_source_tokens, redact_text_for_bundle

_BODY = "AbCdEf0123456789xyzQ"  # 20 chars: below the generic 36-char rule


@pytest.mark.parametrize(
    "prefix", ["sk_test_", "sk_live_", "rk_test_", "rk_live_", "whsec_", "A21AA"]
)
def test_payment_secrets_are_redacted(prefix: str) -> None:
    secret = prefix + _BODY
    line = f"The site said: invalid key {secret}."
    assert secret not in redact_source_tokens(line)
    assert secret not in redact_text_for_bundle(line)


@pytest.mark.parametrize(
    "line",
    [
        "network_egress_entries_wordpress checked 12 sites",
        "Verify Payment Setup read 2 providers from the site",
    ],
)
def test_ordinary_words_survive(line: str) -> None:
    assert redact_source_tokens(line) == line
