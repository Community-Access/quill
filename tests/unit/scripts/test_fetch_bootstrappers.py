from __future__ import annotations

import pytest

from scripts.fetch_bootstrappers import (
    DEFAULT_BASE_URL,
    _resolve_base_url,
)


def test_default_base_url_is_pinned_to_a_commit_sha() -> None:
    """The committed default URL must not point at a moving branch ref.

    This guards finding #36 (release-time supply-chain risk): the bootstrap
    executable is shipped to end-user machines, so a moving ref is a path
    straight to attacker-controlled bytes.
    """
    assert "/HEAD" not in DEFAULT_BASE_URL
    assert "/head" not in DEFAULT_BASE_URL.lower()
    assert "/master/" not in DEFAULT_BASE_URL.lower()
    assert "/main/" not in DEFAULT_BASE_URL.lower()


def test_resolve_base_url_rejects_head_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_BOOTSTRAPPER_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="moving branch ref"):
        _resolve_base_url("https://example.com/HEAD/")


def test_resolve_base_url_rejects_master_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_BOOTSTRAPPER_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="moving branch ref"):
        _resolve_base_url("https://example.com/master/foo/")


def test_resolve_base_url_rejects_unresolved_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    placeholder_url = (
        "https://raw.githubusercontent.com/owner/repo/"
        "<REPLACE_WITH_COMMIT_SHA>/autoupdate/bootstrappers/"
    )
    monkeypatch.delenv("QUILL_BOOTSTRAPPER_BASE_URL", raising=False)
    monkeypatch.setattr("scripts.fetch_bootstrappers.DEFAULT_BASE_SHA", "<REPLACE_WITH_COMMIT_SHA>")
    monkeypatch.setattr("scripts.fetch_bootstrappers.DEFAULT_BASE_URL", placeholder_url)
    with pytest.raises(ValueError, match="placeholder"):
        _resolve_base_url(None)


def test_resolve_base_url_accepts_explicit_pinned_url() -> None:
    pinned = "https://raw.githubusercontent.com/owner/repo/abc123def/file/"
    assert _resolve_base_url(pinned) == pinned


def test_resolve_base_url_uses_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pinned = "https://raw.githubusercontent.com/owner/repo/deadbeef/file/"
    monkeypatch.setenv("QUILL_BOOTSTRAPPER_BASE_URL", pinned)
    assert _resolve_base_url(None) == pinned


def test_arg_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--base-url`` is the most specific override and wins over the env var."""
    monkeypatch.setenv(
        "QUILL_BOOTSTRAPPER_BASE_URL",
        "https://raw.githubusercontent.com/owner/repo/deadbeef/file/",
    )
    explicit = "https://raw.githubusercontent.com/owner/repo/cafef00d/file/"
    assert _resolve_base_url(explicit) == explicit
