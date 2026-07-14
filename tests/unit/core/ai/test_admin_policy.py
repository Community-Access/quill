"""AdminPolicy: allow/block resolution, off-always-allowed, loading, filtering."""

from __future__ import annotations

from quill.core.ai.admin_policy import AdminPolicy, filter_providers, is_provider_allowed


def test_default_policy_allows_everything() -> None:
    p = AdminPolicy()
    assert p.is_allowed("openai")
    assert p.is_allowed("claude")
    assert p.allow_user_api_keys is True


def test_blocklist_wins() -> None:
    p = AdminPolicy(blocked_providers=frozenset({"openai"}))
    assert not p.is_allowed("openai")
    assert p.is_allowed("claude")


def test_allowlist_restricts() -> None:
    p = AdminPolicy(allowed_providers=frozenset({"claude", "ollama"}))
    assert p.is_allowed("claude")
    assert p.is_allowed("ollama")
    assert not p.is_allowed("openai")


def test_block_overrides_allow() -> None:
    p = AdminPolicy(
        allowed_providers=frozenset({"claude", "openai"}),
        blocked_providers=frozenset({"openai"}),
    )
    assert p.is_allowed("claude")
    assert not p.is_allowed("openai")


def test_off_always_allowed() -> None:
    p = AdminPolicy(allowed_providers=frozenset({"claude"}), blocked_providers=frozenset({"off"}))
    assert is_provider_allowed(p, "off")  # disabling AI cannot be policy-blocked


def test_case_insensitive() -> None:
    p = AdminPolicy(blocked_providers=frozenset({"openai"}))
    assert not is_provider_allowed(p, "OpenAI")


def test_from_dict_parses_managed_settings() -> None:
    p = AdminPolicy.from_dict({
        "allowedProviders": ["Claude", "ollama"],
        "blockedProviders": ["openai"],
        "allowUserApiKeys": False,
        "policyNoticeUrl": "https://example.org/policy",
    })
    assert p.allowed_providers == frozenset({"claude", "ollama"})
    assert p.blocked_providers == frozenset({"openai"})
    assert p.allow_user_api_keys is False
    assert p.policy_notice_url == "https://example.org/policy"


def test_from_dict_tolerates_junk() -> None:
    assert AdminPolicy.from_dict(None) == AdminPolicy()
    assert (
        AdminPolicy.from_dict({"allowedProviders": "not-a-list"}).allowed_providers == frozenset()
    )


def test_filter_providers_preserves_order() -> None:
    p = AdminPolicy(blocked_providers=frozenset({"gemini"}))
    assert filter_providers(p, ["openai", "gemini", "claude"]) == ["openai", "claude"]
