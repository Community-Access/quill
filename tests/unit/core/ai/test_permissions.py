"""Permission Broker resolution per profile, risk floor, and the command floor."""

from __future__ import annotations

from quill.core.ai.agent import SAFE_TOOL_IDS
from quill.core.ai.permissions import (
    Decision,
    PermissionBroker,
    PermissionCategory,
    PermissionRequest,
    RiskLevel,
    SafetyProfile,
)


def _req(
    category: PermissionCategory,
    *,
    risk: RiskLevel = RiskLevel.LOW,
    command_id: str | None = None,
) -> PermissionRequest:
    return PermissionRequest(
        category=category,
        agent_id="test-agent",
        agent_risk=risk,
        command_id=command_id,
    )


def test_balanced_defaults_match_prd_table() -> None:
    broker = PermissionBroker(SafetyProfile.BALANCED)
    assert broker.resolve(_req(PermissionCategory.READ_SELECTION)).decision is Decision.ALLOW
    assert broker.resolve(_req(PermissionCategory.READ_DOCUMENT)).decision is Decision.ASK
    assert (
        broker.resolve(_req(PermissionCategory.MODIFY_DOCUMENT)).decision
        is Decision.PREVIEW_REQUIRED
    )


def test_locked_down_denies_everything_outbound() -> None:
    broker = PermissionBroker(SafetyProfile.LOCKED_DOWN)
    for category in PermissionCategory:
        result = broker.resolve(_req(category, command_id="file.save"))
        assert result.decision is Decision.DENY, category


def test_risk_floor_only_tightens_never_loosens() -> None:
    broker = PermissionBroker(SafetyProfile.POWER_USER)
    # Power User allows reading the document outright for a low-risk agent...
    low = broker.resolve(_req(PermissionCategory.READ_DOCUMENT, risk=RiskLevel.LOW))
    assert low.decision is Decision.ALLOW
    # ...but a high-risk agent floors it to preview, and critical to deny.
    high = broker.resolve(_req(PermissionCategory.READ_DOCUMENT, risk=RiskLevel.HIGH))
    assert high.decision is Decision.PREVIEW_REQUIRED
    critical = broker.resolve(_req(PermissionCategory.READ_DOCUMENT, risk=RiskLevel.CRITICAL))
    assert critical.decision is Decision.DENY


def test_run_command_floor_blocks_non_allowlisted_regardless_of_profile() -> None:
    for profile in SafetyProfile:
        broker = PermissionBroker(profile)
        result = broker.resolve(
            _req(PermissionCategory.RUN_COMMAND, command_id="file.delete_everything")
        )
        assert result.decision is Decision.DENY
        assert "allowlist" in result.reason


def test_run_command_allows_safe_tool_under_power_user() -> None:
    broker = PermissionBroker(SafetyProfile.POWER_USER)
    safe_id = SAFE_TOOL_IDS[0]
    result = broker.resolve(_req(PermissionCategory.RUN_COMMAND, command_id=safe_id))
    assert result.decision is Decision.ALLOW


def test_overrides_are_honored_but_floor_still_applies() -> None:
    broker = PermissionBroker(
        SafetyProfile.BALANCED,
        overrides={PermissionCategory.READ_DOCUMENT: Decision.ALLOW},
    )
    # Override loosens to ALLOW for a low-risk agent.
    assert (
        broker.resolve(_req(PermissionCategory.READ_DOCUMENT, risk=RiskLevel.LOW)).decision
        is Decision.ALLOW
    )
    # The command floor is independent of overrides.
    blocked = broker.resolve(_req(PermissionCategory.RUN_COMMAND, command_id="not.allowed"))
    assert blocked.decision is Decision.DENY


def test_result_helpers() -> None:
    broker = PermissionBroker(SafetyProfile.BALANCED)
    allowed = broker.resolve(_req(PermissionCategory.READ_SELECTION))
    assert allowed.allowed_outright is True
    assert allowed.blocked is False
    denied = broker.resolve(_req(PermissionCategory.RUN_COMMAND, command_id="nope"))
    assert denied.blocked is True
    assert denied.allowed_outright is False
