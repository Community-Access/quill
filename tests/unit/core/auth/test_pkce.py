"""Unit tests for ``quill.core.auth.pkce`` (RFC 7636)."""

from __future__ import annotations

import re

import pytest

from quill.core.auth import code_challenge_s256, generate_code_verifier, generate_pkce_pair

_UNRESERVED_RE = re.compile(r"^[A-Za-z0-9._~-]+$")


@pytest.mark.smoke
def test_rfc7636_appendix_b_vector() -> None:
    # The canonical worked example from RFC 7636, Appendix B.
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert code_challenge_s256(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_challenge_is_url_safe_and_unpadded() -> None:
    challenge = code_challenge_s256("some-verifier-value-1234567890")
    assert "=" not in challenge
    assert "+" not in challenge
    assert "/" not in challenge


def test_verifier_length_bounds() -> None:
    assert len(generate_code_verifier(43)) == 43
    assert len(generate_code_verifier(128)) == 128
    with pytest.raises(ValueError):
        generate_code_verifier(42)
    with pytest.raises(ValueError):
        generate_code_verifier(129)


def test_verifier_uses_unreserved_alphabet() -> None:
    assert _UNRESERVED_RE.match(generate_code_verifier(64))


def test_pairs_are_random_and_consistent() -> None:
    a = generate_pkce_pair()
    b = generate_pkce_pair()
    assert a.verifier != b.verifier
    assert a.method == "S256"
    # the challenge is deterministically derived from its own verifier
    assert a.challenge == code_challenge_s256(a.verifier)
