"""The SwiftLetter mixin's two UI paths: the fallback after a refresh, and Enter on a newsletter."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.wordpress.workbench_swiftletter import NEWSLETTER, ROOT  # noqa: E402
from quill.ui.wordpress_workbench_swiftletter import WorkbenchSwiftLetter  # noqa: E402
from quill.ui.wordpress_workbench_window import SEP  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402


class _Tree:
    def __init__(self) -> None:
        self.focused = False

    def SetFocus(self) -> None:  # noqa: N802 - wx's name
        self.focused = True


class _Frame:
    def __init__(self, current: NodeRef | None, present: set[NodeRef]) -> None:
        self.current = current
        self.present = present
        self.tree = _Tree()
        self.rebuilt = 0
        self.selected: list[tuple[NodeRef, bool]] = []

    def rebuild_tree(self) -> None:
        self.rebuilt += 1

    def select(self, ref: NodeRef, *, remember: bool = True) -> bool:
        if ref not in self.present:
            return False
        self.selected.append((ref, remember))
        return True


class _Bench(WorkbenchSwiftLetter):
    def __init__(self, frame: _Frame) -> None:
        self.frame = frame
        self.said: list[str] = []

    def say(self, words: str) -> None:
        self.said.append(words)


def _newsletter_ref(key: str) -> NodeRef:
    return NodeRef("site", NEWSLETTER, f"Test{SEP}{key}")


def test_a_refresh_that_drops_the_shown_newsletter_lands_on_swiftletter_quietly():
    root = NodeRef("site", ROOT, "Test")
    frame = _Frame(_newsletter_ref("9"), {root})
    bench = _Bench(frame)
    bench._swiftletter_nodes = {"Test": ((f"Test{SEP}12", "January"),)}
    bench._swiftletter_tree_changed()
    assert frame.rebuilt == 1
    assert frame.selected == [(root, False)]
    assert bench.said == []


def test_a_refresh_that_keeps_the_shown_newsletter_leaves_the_place_alone():
    kept = _newsletter_ref("9")
    frame = _Frame(kept, {kept, NodeRef("site", ROOT, "Test")})
    bench = _Bench(frame)
    bench._swiftletter_nodes = {"Test": ((kept.instance, "December"),)}
    bench._swiftletter_tree_changed()
    assert frame.selected == []  # rebuild_tree itself re-selects what is still there


def _row(key: str = "9", title: str = "December") -> WbRow:
    return WbRow(NEWSLETTER, "Test", key, {"title": title}, f"{title}.")


def test_show_articles_selects_the_newsletter_and_moves_to_the_tree():
    target = _newsletter_ref("9")
    frame = _Frame(NodeRef("site", ROOT, "Test"), {target})
    bench = _Bench(frame)
    bench.do_show_articles(NodeRef("site", ROOT, "Test"), _row())
    assert frame.selected == [(target, True)]
    assert frame.tree.focused
    assert bench.said == []


def test_show_articles_says_so_when_the_newsletter_is_not_in_the_tree():
    frame = _Frame(NodeRef("site", ROOT, "Test"), set())
    bench = _Bench(frame)
    bench.do_show_articles(NodeRef("site", ROOT, "Test"), _row())
    assert not frame.tree.focused
    assert bench.said == ["December is not in the tree yet. Refresh lists the newsletters again."]


def test_show_articles_ignores_a_row_that_is_not_a_newsletter():
    frame = _Frame(None, set())
    bench = _Bench(frame)
    other: Any = WbRow("swiftletter_article", "Test", "4", {"title": "Draft"}, "Draft.")
    bench.do_show_articles(NodeRef("site", NEWSLETTER, "Test"), other)
    assert frame.selected == [] and bench.said == []


class _Listing(_Bench):
    """A bench with the lists mixin's two pieces remember_newsletters writes to."""

    def __init__(self, frame: _Frame) -> None:
        super().__init__(frame)
        self.cut: dict[str, str] = {"site|swiftletter|Test": "The first 300 are shown."}

    @staticmethod
    def page_key(ref: NodeRef) -> str:
        return f"{ref.template}|{ref.key}|{ref.instance}"


def test_a_known_total_replaces_the_usual_more_words_once(monkeypatch: Any) -> None:
    from tests.wx_session import patch_call_after

    patch_call_after(monkeypatch, lambda *_args: None)
    ref = NodeRef("site", ROOT, "Test")
    bench = _Listing(_Frame(ref, {ref}))
    left = "112 more of the site's 412 newsletters are not listed yet."
    row = WbRow(NEWSLETTER, "Test", "9", {"title": "December"}, "December.", raw={"left": left})
    bench.remember_newsletters("Test", SEP, [row], ref)
    assert bench.cut["site|swiftletter|Test"] == left
    empty = WbRow(NEWSLETTER, "Test", "9", {}, "", raw={"left": ""})
    bench.remember_newsletters("Test", SEP, [empty], ref)
    assert bench.cut["site|swiftletter|Test"] == ""


class _Address:
    def __init__(self, wpcom: bool) -> None:
        self.is_wpcom = wpcom


class _Context:
    def __init__(self, wpcom: bool) -> None:
        self.api = type("Api", (), {"address": _Address(wpcom)})()


def test_swiftletter_is_never_offered_on_a_wordpress_com_connection() -> None:
    bench = _Bench(_Frame(None, set()))
    assert not bench.swiftletter_offered(ROOT, _Context(wpcom=True))
    assert bench.swiftletter_offered(ROOT, _Context(wpcom=False))
    assert bench.swiftletter_offered(ROOT, None)  # not yet connected: decided by the index
    assert bench.swiftletter_offered("shop", _Context(wpcom=True))
