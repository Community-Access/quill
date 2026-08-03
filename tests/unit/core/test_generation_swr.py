"""GenerationCounter and the stale-while-revalidate core (items 11/12)."""

from __future__ import annotations

from quill.core.generation import GenerationCounter
from quill.core.swr import decide_refresh, structural_signature


def test_only_the_newest_token_is_current() -> None:
    counter = GenerationCounter()
    first = counter.advance()
    assert counter.is_current(first)
    second = counter.advance()
    assert not counter.is_current(first)
    assert counter.is_current(second)


def test_unstarted_counter_has_no_current_token() -> None:
    counter = GenerationCounter()
    assert not counter.is_current(0) or counter.current == 0
    # A token from another counter's life can never be current.
    assert not counter.is_current(99)


def test_structural_signature_is_case_insensitive_and_order_sensitive() -> None:
    assert structural_signature(["Word", "Excel"]) == structural_signature(["word", "excel"])
    assert structural_signature(["a", "b"]) != structural_signature(["b", "a"])


def test_structural_signature_with_a_key_uses_identity_fields() -> None:
    items = [{"name": "Word", "target": "w.exe", "mtime": 1}]
    later = [{"name": "Word", "target": "w.exe", "mtime": 2}]

    def key(item: object) -> tuple[object, ...]:
        assert isinstance(item, dict)
        return (item["name"], item["target"])

    # mtime churn alone must not count as a change (no silent rebuild).
    assert structural_signature(items, key) == structural_signature(later, key)


def test_refresh_decision_is_always_silent_and_position_preserving() -> None:
    unchanged = decide_refresh((("a",),), (("a",),))
    assert not unchanged.changed
    changed = decide_refresh((("a",),), (("b",),))
    assert changed.changed
    # The accessibility contract: a background refresh never announces and
    # never moves the user's selection.
    for decision in (unchanged, changed):
        assert decision.announce is False
        assert decision.keep_selection is True
