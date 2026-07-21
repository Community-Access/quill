"""Tests for the approval workflow (PRD 18.8)."""

import pytest

from quill_social.services import approvals as ap
from quill_social.services.approvals import ApprovalError, ApprovalRecord


def test_permission_matrix():
    assert ap.can_perform("owner", "manage_roles")
    assert ap.can_perform("approver", "approve")
    assert not ap.can_perform("approver", "publish")
    assert not ap.can_perform("contributor", "approve")
    assert ap.can_perform("contributor", "submit")
    assert ap.can_perform("viewer", "view")
    assert not ap.can_perform("viewer", "edit")


def test_valid_transitions():
    assert ap.can_transition("draft", "ready")
    assert ap.can_transition("ready", "approved")
    assert ap.can_transition("approved", "queued")
    assert not ap.can_transition("draft", "approved")
    assert not ap.can_transition("cancelled", "draft")


def test_happy_path_with_audit():
    rec = ApprovalRecord(state="draft", draft_id="d1")
    ap.request_approval(rec, actor="alice", role="contributor", note="please review")
    assert rec.state == "ready"
    ap.approve(rec, actor="bob", role="approver", note="looks good")
    assert rec.state == "approved"
    ap.queue(rec, actor="carol", role="publisher")
    assert rec.state == "queued"
    # Audit trail records who/when/what for each step.
    assert [a.action for a in rec.audit] == ["submit", "approve", "queue"]
    assert rec.audit[0].actor == "alice"
    assert rec.audit[0].note == "please review"
    assert rec.audit[1].from_state == "ready" and rec.audit[1].to_state == "approved"


def test_request_changes_sends_back():
    rec = ApprovalRecord(state="ready")
    ap.request_changes(rec, actor="bob", role="approver", note="fix the alt text")
    assert rec.state == "changes_requested"
    assert rec.audit[-1].note == "fix the alt text"


def test_role_without_permission_is_rejected():
    rec = ApprovalRecord(state="ready")
    with pytest.raises(ApprovalError):
        ap.approve(rec, actor="eve", role="contributor")
    # State unchanged and nothing written to the audit trail.
    assert rec.state == "ready"
    assert rec.audit == []


def test_invalid_transition_rejected():
    rec = ApprovalRecord(state="draft")
    with pytest.raises(ApprovalError):
        ap.approve(rec, actor="bob", role="approver")
    assert rec.state == "draft"


def test_transition_timestamp_uses_clock():
    rec = ApprovalRecord(state="draft")
    ap.request_approval(rec, actor="alice", role="contributor", now=12345)
    assert rec.audit[-1].at_ms == 12345
    assert rec.updated == 12345


def test_persistence_roundtrip(store):
    rec = ApprovalRecord(state="draft", draft_id="d1")
    ap.request_approval(rec, actor="alice", role="contributor", now=100)
    ap.save(store, rec)
    loaded = ap.load(store, rec.record_id)
    assert loaded is not None
    assert loaded.state == "ready"
    assert loaded.audit[-1].actor == "alice"
    assert [r.record_id for r in ap.load_all(store)] == [rec.record_id]
