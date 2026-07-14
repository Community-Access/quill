"""Enterprise admin policy for AI providers (PRD §15).

An organization can constrain which AI providers QUILL may use and whether users
may supply their own API keys. This wx-free core module models that policy and the
two questions it answers: *is this provider allowed?* and *which providers may the
user choose from?* The provider catalog and the AI Hub consult it; nothing here
performs I/O or references wx.

Defaults are permissive (no policy): empty allow/block lists mean "all providers",
and user API keys are allowed. A policy is typically loaded from managed settings
via :meth:`AdminPolicy.from_dict`.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["AdminPolicy", "is_provider_allowed", "filter_providers"]


@dataclass(frozen=True, slots=True)
class AdminPolicy:
    """Organization policy over AI providers and key handling.

    ``allowed_providers`` empty means "all"; a non-empty allowlist restricts to
    exactly those ids (minus anything also blocked). ``blocked_providers`` always
    wins over the allowlist. ``policy_notice_url`` is an optional link the Hub can
    show explaining the policy.
    """

    allowed_providers: frozenset[str] = frozenset()
    blocked_providers: frozenset[str] = frozenset()
    allow_user_api_keys: bool = True
    policy_notice_url: str = ""

    @classmethod
    def from_dict(cls, data: object) -> AdminPolicy:
        """Build a policy from a managed-settings mapping; tolerant of junk."""
        if not isinstance(data, dict):
            return cls()
        return cls(
            allowed_providers=_str_set(data.get("allowedProviders")),
            blocked_providers=_str_set(data.get("blockedProviders")),
            allow_user_api_keys=bool(data.get("allowUserApiKeys", True)),
            policy_notice_url=str(data.get("policyNoticeUrl", "") or ""),
        )

    def is_allowed(self, provider_id: str) -> bool:
        return is_provider_allowed(self, provider_id)


def _str_set(value: object) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(str(item).strip().lower() for item in value if str(item).strip())


def is_provider_allowed(policy: AdminPolicy, provider_id: str) -> bool:
    """True if ``provider_id`` may be used under ``policy``.

    A blocked provider is never allowed. With a non-empty allowlist, only listed
    providers are allowed. ``"off"`` is always allowed — disabling AI must never be
    blocked by policy.
    """
    pid = provider_id.strip().lower()
    if pid == "off":
        return True
    if pid in policy.blocked_providers:
        return False
    if policy.allowed_providers and pid not in policy.allowed_providers:
        return False
    return True


def filter_providers(policy: AdminPolicy, provider_ids: list[str]) -> list[str]:
    """Return the subset of ``provider_ids`` allowed under ``policy`` (order kept)."""
    return [pid for pid in provider_ids if is_provider_allowed(policy, pid)]
