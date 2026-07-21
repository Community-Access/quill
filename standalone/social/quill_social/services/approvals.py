"""Approval workflow: roles, state transitions, and audit trail (PRD 18.8).

Organizational publishing needs a reviewable pipeline (PRD 18.8). This module
provides:

- A role/action permission matrix (``can_perform``) over the PRD roles: owner,
  administrator, publisher, approver, contributor, and viewer.
- The approval-state transitions among the PRD 18.8 states (idea, draft, ready,
  changes_requested, approved, queued, ...).
- Action helpers (``request_approval``, ``approve``, ``request_changes``, and
  friends) that apply a transition and append an immutable audit entry recording
  who acted, when, and any note.

An ``ApprovalRecord`` tracks one item's current state plus its full audit trail
and persists to the document store under kind ``"approval"``. The logic is pure
and clock-injectable so it is unit-testable without a database. This complements
:mod:`quill_social.services.scheduler`, which owns the publishing-side state
machine; here we cover the review-side transitions that precede queueing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill_social.model import new_id, now_ms

DOC_KIND = "approval"

# Roles, ordered from most to least privileged (PRD 18.8).
ROLES = ("owner", "administrator", "publisher", "approver", "contributor", "viewer")

# Actions a role may attempt in the approval workflow.
ACTIONS = (
    "create",           # create an idea/draft
    "edit",             # edit draft content
    "submit",           # request approval (ready for review)
    "request_changes",  # send back to the author
    "approve",          # approve for queueing
    "queue",            # move an approved item into the queue
    "publish",          # publish now / trigger delivery
    "cancel",           # cancel a plan
    "manage_roles",     # assign roles, manage the workspace
    "view",             # read-only visibility
)

# Which actions each role may perform. Higher roles are supersets in practice
# but the matrix is explicit so the policy is auditable (PRD 18.8).
_MATRIX: dict[str, frozenset[str]] = {
    "owner": frozenset(ACTIONS),
    "administrator": frozenset(ACTIONS),
    "publisher": frozenset(
        {"create", "edit", "submit", "request_changes", "approve", "queue",
         "publish", "cancel", "view"}
    ),
    "approver": frozenset({"request_changes", "approve", "view"}),
    "contributor": frozenset({"create", "edit", "submit", "view"}),
    "viewer": frozenset({"view"}),
}

# Review-side transitions (PRD 18.8). Publishing-side moves (scheduled,
# publishing, published, ...) are owned by the scheduler; here we stop at
# ``queued`` where the two pipelines meet.
_TRANSITIONS: dict[str, frozenset[str]] = {
    "idea": frozenset({"draft", "cancelled"}),
    "draft": frozenset({"ready", "cancelled"}),
    "ready": frozenset({"changes_requested", "approved", "cancelled"}),
    "changes_requested": frozenset({"draft", "ready", "cancelled"}),
    "approved": frozenset({"queued", "changes_requested", "cancelled"}),
    "queued": frozenset({"cancelled"}),
    "cancelled": frozenset(),
}

# The action that drives each transition, for permission checks.
_ACTION_FOR: dict[tuple[str, str], str] = {
    ("idea", "draft"): "edit",
    ("draft", "ready"): "submit",
    ("ready", "approved"): "approve",
    ("ready", "changes_requested"): "request_changes",
    ("changes_requested", "draft"): "edit",
    ("changes_requested", "ready"): "submit",
    ("approved", "queued"): "queue",
    ("approved", "changes_requested"): "request_changes",
}


class ApprovalError(Exception):
    """Raised when a transition is invalid or the actor lacks permission."""


@dataclass
class AuditEntry:
    """One immutable step in an item's approval history (PRD 18.8)."""

    at_ms: int
    actor: str
    role: str
    action: str
    from_state: str
    to_state: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "at_ms": self.at_ms,
            "actor": self.actor,
            "role": self.role,
            "action": self.action,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AuditEntry:
        return cls(
            at_ms=int(d.get("at_ms", 0) or 0),
            actor=d.get("actor", ""),
            role=d.get("role", ""),
            action=d.get("action", ""),
            from_state=d.get("from_state", ""),
            to_state=d.get("to_state", ""),
            note=d.get("note", ""),
        )


@dataclass
class ApprovalRecord:
    """The approval state and full audit trail for one draft or plan."""

    record_id: str = field(default_factory=lambda: new_id("appr"))
    draft_id: str = ""
    campaign_id: str = ""
    state: str = "idea"
    audit: list[AuditEntry] = field(default_factory=list)
    created: int = field(default_factory=now_ms)
    updated: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "draft_id": self.draft_id,
            "campaign_id": self.campaign_id,
            "state": self.state,
            "audit": [a.to_dict() for a in self.audit],
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ApprovalRecord:
        return cls(
            record_id=d.get("record_id") or new_id("appr"),
            draft_id=d.get("draft_id", ""),
            campaign_id=d.get("campaign_id", ""),
            state=d.get("state", "idea"),
            audit=[AuditEntry.from_dict(a) for a in d.get("audit", [])],
            created=int(d.get("created", 0) or now_ms()),
            updated=int(d.get("updated", 0) or now_ms()),
        )


# -- policy -------------------------------------------------------------------


def can_perform(role: str, action: str) -> bool:
    """True if ``role`` is permitted to perform ``action`` (PRD 18.8)."""
    return action in _MATRIX.get(role, frozenset())


def can_transition(src: str, dst: str) -> bool:
    """True if the approval state may move from ``src`` to ``dst`` (PRD 18.8)."""
    return dst in _TRANSITIONS.get(src, frozenset())


def action_for_transition(src: str, dst: str) -> str:
    """The workflow action that drives ``src`` -> ``dst`` (``""`` if none)."""
    return _ACTION_FOR.get((src, dst), "")


# -- transitions --------------------------------------------------------------


def transition(
    record: ApprovalRecord,
    to_state: str,
    *,
    actor: str,
    role: str,
    note: str = "",
    now: int | None = None,
) -> ApprovalRecord:
    """Apply a state change with a permission check and audit entry (PRD 18.8).

    Raises :class:`ApprovalError` if the transition is not allowed or the actor's
    role lacks permission for the driving action. On success the record's state
    is updated and an :class:`AuditEntry` is appended. The record is mutated in
    place and returned; persistence is the caller's responsibility.
    """
    at = now if now is not None else now_ms()
    src = record.state
    if not can_transition(src, to_state):
        raise ApprovalError(f"cannot move approval from {src} to {to_state}")
    action = action_for_transition(src, to_state) or (
        "cancel" if to_state == "cancelled" else "edit"
    )
    if not can_perform(role, action):
        raise ApprovalError(f"role {role} may not {action}")
    record.audit.append(
        AuditEntry(
            at_ms=at, actor=actor, role=role, action=action,
            from_state=src, to_state=to_state, note=note,
        )
    )
    record.state = to_state
    record.updated = at
    return record


def request_approval(
    record: ApprovalRecord, *, actor: str, role: str, note: str = "",
    now: int | None = None,
) -> ApprovalRecord:
    """Move a draft to ``ready`` for review (PRD 18.8)."""
    return transition(record, "ready", actor=actor, role=role, note=note, now=now)


def approve(
    record: ApprovalRecord, *, actor: str, role: str, note: str = "",
    now: int | None = None,
) -> ApprovalRecord:
    """Approve a ready item (PRD 18.8)."""
    return transition(record, "approved", actor=actor, role=role, note=note, now=now)


def request_changes(
    record: ApprovalRecord, *, actor: str, role: str, note: str = "",
    now: int | None = None,
) -> ApprovalRecord:
    """Send an item back to its author for changes (PRD 18.8)."""
    return transition(
        record, "changes_requested", actor=actor, role=role, note=note, now=now
    )


def queue(
    record: ApprovalRecord, *, actor: str, role: str, note: str = "",
    now: int | None = None,
) -> ApprovalRecord:
    """Move an approved item into the publishing queue (PRD 18.8)."""
    return transition(record, "queued", actor=actor, role=role, note=note, now=now)


def cancel(
    record: ApprovalRecord, *, actor: str, role: str, note: str = "",
    now: int | None = None,
) -> ApprovalRecord:
    """Cancel the item (PRD 18.8)."""
    return transition(record, "cancelled", actor=actor, role=role, note=note, now=now)


# -- persistence --------------------------------------------------------------


def save(store, record: ApprovalRecord) -> ApprovalRecord:
    """Persist an approval record (kind ``approval``)."""
    store.put_document(DOC_KIND, record.record_id, record.to_dict())
    return record


def load(store, record_id: str) -> ApprovalRecord | None:
    data = store.get_document(DOC_KIND, record_id)
    return ApprovalRecord.from_dict(data) if data else None


def load_all(store) -> list[ApprovalRecord]:
    return [ApprovalRecord.from_dict(d) for d in store.list_documents(DOC_KIND)]
