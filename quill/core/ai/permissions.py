"""Permission Broker, risk levels, and safety profiles (PRD §10).

The broker is the single place that answers one question: *given the active
agent's risk level and the user's global safety profile, may this tool category
run, and how?* The answer is one of allow / deny / ask / preview_required.

This is wx-free core. The UI consumes a :class:`PermissionResult` and, when the
decision is ``ASK`` or ``PREVIEW_REQUIRED``, renders the prompt / diff review;
the broker itself never touches widgets and never performs the action.

**Floor (non-negotiable):** ``run_quill_command`` may only target an id in
:data:`quill.core.ai.agent.SAFE_TOOL_IDS`, regardless of profile. No profile can
loosen that, and the broker enforces it before consulting the profile table.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from quill.core.ai.agent import SAFE_TOOL_IDS

__all__ = [
    "PermissionCategory",
    "Decision",
    "RiskLevel",
    "SafetyProfile",
    "PermissionRequest",
    "PermissionResult",
    "PermissionBroker",
]


class PermissionCategory(StrEnum):
    """The tool categories the broker arbitrates (PRD §10 table)."""

    READ_SELECTION = "read_selection"
    READ_DOCUMENT = "read_document"
    READ_WORKSPACE = "read_workspace"
    MODIFY_SELECTION = "modify_selection"
    MODIFY_DOCUMENT = "modify_document"
    CREATE_FILE = "create_file"
    GITHUB = "github"
    TERMINAL = "terminal"
    WEB = "web"
    MEMORY = "memory"
    RUN_COMMAND = "run_command"


class Decision(StrEnum):
    """How a request may proceed.

    Ordered by strictness via :data:`_STRICTNESS`: ``ALLOW`` < ``ASK`` <
    ``PREVIEW_REQUIRED`` < ``DENY``. Risk escalation only ever moves *up* this
    ordering (tightens); it never loosens a profile's default.
    """

    ALLOW = "allow"
    ASK = "ask"
    PREVIEW_REQUIRED = "preview_required"
    DENY = "deny"


class RiskLevel(StrEnum):
    """An agent's declared risk level (from its catalog entry)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyProfile(StrEnum):
    """The user's global safety posture (Permissions tab)."""

    CAREFUL = "careful"
    BALANCED = "balanced"
    POWER_USER = "power_user"
    LOCKED_DOWN = "locked_down"


# Strictness ranking used to take the *stricter* of two decisions. Higher means
# more restrictive.
_STRICTNESS: dict[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.ASK: 1,
    Decision.PREVIEW_REQUIRED: 2,
    Decision.DENY: 3,
}


def _stricter(a: Decision, b: Decision) -> Decision:
    """Return whichever decision is more restrictive."""
    return a if _STRICTNESS[a] >= _STRICTNESS[b] else b


# Per-profile default decision per category. Balanced encodes the PRD §10
# "Default" column; Careful tightens it; Power User loosens the low-risk reads
# and selection edits; Locked Down denies everything that leaves the editor or
# mutates the document without review.
_PROFILE_DEFAULTS: dict[SafetyProfile, dict[PermissionCategory, Decision]] = {
    SafetyProfile.CAREFUL: {
        PermissionCategory.READ_SELECTION: Decision.ALLOW,
        PermissionCategory.READ_DOCUMENT: Decision.ASK,
        PermissionCategory.READ_WORKSPACE: Decision.ASK,
        PermissionCategory.MODIFY_SELECTION: Decision.PREVIEW_REQUIRED,
        PermissionCategory.MODIFY_DOCUMENT: Decision.PREVIEW_REQUIRED,
        PermissionCategory.CREATE_FILE: Decision.ASK,
        PermissionCategory.GITHUB: Decision.ASK,
        PermissionCategory.TERMINAL: Decision.DENY,
        PermissionCategory.WEB: Decision.ASK,
        PermissionCategory.MEMORY: Decision.ASK,
        PermissionCategory.RUN_COMMAND: Decision.ASK,
    },
    SafetyProfile.BALANCED: {
        PermissionCategory.READ_SELECTION: Decision.ALLOW,
        PermissionCategory.READ_DOCUMENT: Decision.ASK,
        PermissionCategory.READ_WORKSPACE: Decision.ASK,
        PermissionCategory.MODIFY_SELECTION: Decision.PREVIEW_REQUIRED,
        PermissionCategory.MODIFY_DOCUMENT: Decision.PREVIEW_REQUIRED,
        PermissionCategory.CREATE_FILE: Decision.ASK,
        PermissionCategory.GITHUB: Decision.ASK,
        PermissionCategory.TERMINAL: Decision.ASK,
        PermissionCategory.WEB: Decision.ASK,
        PermissionCategory.MEMORY: Decision.ASK,
        PermissionCategory.RUN_COMMAND: Decision.ASK,
    },
    SafetyProfile.POWER_USER: {
        PermissionCategory.READ_SELECTION: Decision.ALLOW,
        PermissionCategory.READ_DOCUMENT: Decision.ALLOW,
        PermissionCategory.READ_WORKSPACE: Decision.ASK,
        PermissionCategory.MODIFY_SELECTION: Decision.ALLOW,
        PermissionCategory.MODIFY_DOCUMENT: Decision.PREVIEW_REQUIRED,
        PermissionCategory.CREATE_FILE: Decision.ASK,
        PermissionCategory.GITHUB: Decision.ASK,
        PermissionCategory.TERMINAL: Decision.ASK,
        PermissionCategory.WEB: Decision.ALLOW,
        PermissionCategory.MEMORY: Decision.ALLOW,
        PermissionCategory.RUN_COMMAND: Decision.ALLOW,
    },
    SafetyProfile.LOCKED_DOWN: {
        PermissionCategory.READ_SELECTION: Decision.DENY,
        PermissionCategory.READ_DOCUMENT: Decision.DENY,
        PermissionCategory.READ_WORKSPACE: Decision.DENY,
        PermissionCategory.MODIFY_SELECTION: Decision.DENY,
        PermissionCategory.MODIFY_DOCUMENT: Decision.DENY,
        PermissionCategory.CREATE_FILE: Decision.DENY,
        PermissionCategory.GITHUB: Decision.DENY,
        PermissionCategory.TERMINAL: Decision.DENY,
        PermissionCategory.WEB: Decision.DENY,
        PermissionCategory.MEMORY: Decision.DENY,
        PermissionCategory.RUN_COMMAND: Decision.DENY,
    },
}

# Minimum strictness floor an agent's risk level imposes on every category. A
# higher-risk agent can only make the profile default stricter, never looser.
_RISK_FLOOR: dict[RiskLevel, Decision] = {
    RiskLevel.LOW: Decision.ALLOW,
    RiskLevel.MEDIUM: Decision.ASK,
    RiskLevel.HIGH: Decision.PREVIEW_REQUIRED,
    RiskLevel.CRITICAL: Decision.DENY,
}


@dataclass(frozen=True, slots=True)
class PermissionRequest:
    """A single ask: this agent wants to use this category, optionally on this
    command id (only meaningful for :attr:`PermissionCategory.RUN_COMMAND`)."""

    category: PermissionCategory
    agent_id: str
    agent_risk: RiskLevel
    command_id: str | None = None


@dataclass(frozen=True, slots=True)
class PermissionResult:
    """The broker's verdict for a :class:`PermissionRequest`."""

    decision: Decision
    category: PermissionCategory
    reason: str

    @property
    def allowed_outright(self) -> bool:
        """True only when no prompt or preview is needed."""
        return self.decision is Decision.ALLOW

    @property
    def blocked(self) -> bool:
        """True when the action must not proceed at all."""
        return self.decision is Decision.DENY


class PermissionBroker:
    """Resolve :class:`PermissionRequest` -> :class:`PermissionResult`.

    Stateless beyond the configured profile and per-category overrides, so it is
    cheap to construct and trivially testable. The active profile and any
    per-category overrides come from the Permissions tab settings.
    """

    def __init__(
        self,
        profile: SafetyProfile = SafetyProfile.BALANCED,
        *,
        overrides: dict[PermissionCategory, Decision] | None = None,
    ) -> None:
        self._profile = profile
        self._overrides = dict(overrides or {})

    @property
    def profile(self) -> SafetyProfile:
        return self._profile

    def resolve(self, request: PermissionRequest) -> PermissionResult:
        """Return the verdict, applying the floor, profile, overrides, and risk."""
        category = request.category

        # Non-negotiable floor: run_quill_command can only target SAFE_TOOL_IDS.
        if category is PermissionCategory.RUN_COMMAND:
            target = request.command_id or ""
            if target not in SAFE_TOOL_IDS:
                return PermissionResult(
                    decision=Decision.DENY,
                    category=category,
                    reason=(
                        f"Command {target!r} is not on the safe-tool allowlist; "
                        "no profile can permit it."
                    ),
                )

        base = self._overrides.get(category) or _PROFILE_DEFAULTS[self._profile][category]
        risk_floor = _RISK_FLOOR[request.agent_risk]
        decision = _stricter(base, risk_floor)

        reason = (
            f"{self._profile.value} profile -> {base.value}; "
            f"{request.agent_risk.value}-risk agent floor -> {risk_floor.value}; "
            f"effective {decision.value}."
        )
        return PermissionResult(decision=decision, category=category, reason=reason)
