"""The compose dialog runs the shared spelling review on demand (F7 / button),
not only the per-account check-before-post (Leasey Social parity)."""

from __future__ import annotations

from quill.ui.mastodon_dialogs import MastodonComposeDialog


class _FakeText:
    def __init__(self, value: str) -> None:
        self._value = value
        self.focused = False

    def GetValue(self) -> str:  # noqa: N802 - wx shape
        return self._value

    def SetFocus(self) -> None:  # noqa: N802 - wx shape
        self.focused = True


def _dialog(text: str, spell_review) -> MastodonComposeDialog:
    d = MastodonComposeDialog.__new__(MastodonComposeDialog)
    d._spell_review = spell_review
    d._text = _FakeText(text)
    d._announce = lambda _m: None
    return d


def test_on_spell_check_runs_the_review_over_the_post() -> None:
    seen = []
    d = _dialog("teh cat", spell_review=lambda ctrl: seen.append(ctrl))
    d._on_spell_check(None)
    assert len(seen) == 1  # review ran over the post's text control


def test_on_spell_check_empty_post_does_not_review() -> None:
    seen = []
    d = _dialog("   ", spell_review=lambda ctrl: seen.append(ctrl))
    d._on_spell_check(None)
    assert seen == []  # nothing to check
    assert d._text.focused  # focus returns to the empty field


def test_on_spell_check_no_reviewer_is_graceful() -> None:
    said = []
    d = _dialog("hello", spell_review=None)
    d._announce = lambda m: said.append(m)
    d._on_spell_check(None)  # must not raise
    assert said and "not available" in said[0]
