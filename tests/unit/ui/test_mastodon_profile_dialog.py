"""The Mastodon profile dialog's follow/unfollow toggle updates label + text."""

from __future__ import annotations

from quill.core.mastodon.social import Account, Relationship
from quill.ui.mastodon_social_dialogs import MastodonProfileDialog


class _FakeStatic:
    def __init__(self) -> None:
        self.label = ""

    def SetLabel(self, value: str) -> None:  # noqa: N802 - wx shape
        self.label = value


def _dialog(rel: Relationship, toggle) -> MastodonProfileDialog:
    d = MastodonProfileDialog.__new__(MastodonProfileDialog)
    d._account = Account(id="1", acct="alice", display_name="Alice")
    d._relationship = rel
    d._on_toggle_follow = toggle
    d._announce = lambda _m: None
    d._relationship_text = _FakeStatic()
    d._follow_btn = _FakeStatic()

    def _set_name(_ctrl, _name):
        pass

    # set_accessible_name is imported at module scope; patch via the module.
    import quill.ui.mastodon_social_dialogs as mod

    mod.set_accessible_name = _set_name  # type: ignore[assignment]
    return d


def test_follow_label_reflects_state() -> None:
    d = _dialog(Relationship("1", following=False, followed_by=False), toggle=lambda f: None)
    assert d._follow_label() == "&Follow"
    d._relationship = Relationship("1", following=True, followed_by=False)
    assert d._follow_label() == "Un&follow"


def test_on_follow_updates_button_and_summary() -> None:
    now_following = Relationship("1", following=True, followed_by=True)
    d = _dialog(
        Relationship("1", following=False, followed_by=True),
        toggle=lambda follow: now_following if follow else None,
    )
    d._on_follow(None)
    assert d._relationship.following is True
    assert d._follow_btn.label == "Un&follow"
    assert "follow each other" in d._relationship_text.label


def test_on_follow_failure_leaves_state() -> None:
    d = _dialog(
        Relationship("1", following=False, followed_by=False),
        toggle=lambda follow: None,  # host reports failure
    )
    d._on_follow(None)
    assert d._relationship.following is False  # unchanged
