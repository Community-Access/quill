"""GitHub auth failures identify expiration, SSO, rate limits, and scopes."""

from __future__ import annotations

from quill.core.github.auth_diagnostics import github_auth_hint


def test_invalid_or_expired_token_has_recovery_action() -> None:
    hint = github_auth_hint(401)

    assert hint is not None
    assert "invalid or expired" in hint
    assert "switch accounts" in hint


def test_sso_denial_is_distinguished_from_missing_repository_scope() -> None:
    hint = github_auth_hint(403, headers={"X-GitHub-SSO": "required; url=https://github.com"})

    assert hint is not None
    assert "SSO authorization" in hint
    assert "authorize" in hint


def test_rate_limit_is_distinguished_from_permissions() -> None:
    hint = github_auth_hint(403, headers={"X-RateLimit-Remaining": "0"})

    assert hint == "GitHub rate-limited this request. Wait before retrying."


def test_generic_permission_denial_does_not_claim_there_are_no_alerts() -> None:
    hint = github_auth_hint(403)

    assert hint is not None
    assert "token permissions" in hint
    assert "SSO authorization" in hint
