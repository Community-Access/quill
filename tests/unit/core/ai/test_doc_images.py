"""Alt text for a document's own images, as agent tools (codex.md 6.4, 10B, decision 13)."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.doc_images import (
    doc_image_tools,
    image_list_text,
    list_document_images,
    resolve_image_source,
    with_alt_text,
)
from quill.core.ai.family_tools import EDITOR_APP, FamilyToolRegistry, ToolImage
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity

_DOC = (
    "# Trip\n\n![](beach.png)\n\nSome words.\n\n"
    '<p><img src="dog.jpg" width="20"></p>\n\n![A map](map.png "Route")\n'
)


def test_images_are_listed_in_reading_order_with_their_alt_text() -> None:
    images = list_document_images(_DOC)
    assert [(i.number, i.source, i.alt_text, i.kind) for i in images] == [
        (1, "beach.png", "", "markdown"),
        (2, "dog.jpg", "", "html"),
        (3, "map.png", "A map", "markdown"),
    ]
    text = image_list_text(images)
    assert text.splitlines()[0] == "3 images, 2 without alt text."
    assert "1. beach.png (markdown). Alt text: missing" in text
    assert "3. map.png (markdown). Alt text: A map" in text


def test_no_images_is_said_plainly() -> None:
    assert image_list_text(list_document_images("Just words.")) == "This document has no images."


def test_markdown_alt_text_is_written_and_the_title_kept() -> None:
    revised = with_alt_text(_DOC, 3, "The route [north]\nalong the coast")
    assert '![The route (north) along the coast](map.png "Route")' in revised
    assert revised.replace('![The route (north) along the coast](map.png "Route")', "") == (
        _DOC.replace('![A map](map.png "Route")', "")
    )


def test_html_alt_text_is_added_and_escaped() -> None:
    revised = with_alt_text(_DOC, 2, 'A "good" dog & ball')
    assert '<img alt="A &quot;good&quot; dog &amp; ball" src="dog.jpg" width="20">' in revised


def test_existing_html_alt_text_is_replaced_not_doubled() -> None:
    text = '<img src="a.png" alt="old">'
    assert with_alt_text(text, 1, "new") == '<img src="a.png" alt="new">'


def test_a_missing_image_number_is_refused() -> None:
    with pytest.raises(ValueError):
        with_alt_text(_DOC, 9, "x")


def test_a_web_address_is_never_resolved_and_relative_paths_sit_beside_the_document(
    tmp_path: Path,
) -> None:
    (tmp_path / "beach.png").write_bytes(b"png")
    document = tmp_path / "trip.md"
    assert resolve_image_source("https://example.com/a.png", document) is None
    assert resolve_image_source("beach.png", document) == tmp_path / "beach.png"
    assert resolve_image_source("beach.png", None) is None
    assert resolve_image_source("missing.png", document) is None
    data = base64.b64encode(b"bytes").decode()
    assert resolve_image_source(f"data:image/png;base64,{data}", None) == b"bytes"


class _Approver:
    def __init__(self, choice: ApprovalChoice) -> None:
        self.choice = choice
        self.asked: list[str] = []

    def ask(self, tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return self.choice


def _registry(tools, approver) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(), ActivityLog(), AgentIdentity("t", RiskLevel.LOW)
    )
    registry.register_app(EDITOR_APP, tools)
    registry.gate.begin_task(approver)
    return registry


def test_listing_is_a_read_and_asks_nothing() -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(doc_image_tools(lambda: _DOC, lambda *_a: True), approver)
    result = registry.call("doc_list_images")
    assert result.ok and "3 images" in result.text
    assert approver.asked == []
    assert "doc.image" not in registry.names()  # no loader: a connection that cannot see


def test_setting_alt_text_goes_through_the_reviewed_patch() -> None:
    applied: list[tuple[str, str, str]] = []

    def apply(original: str, revised: str, label: str) -> bool:
        applied.append((original, revised, label))
        return True

    registry = _registry(doc_image_tools(lambda: _DOC, apply), _Approver(ApprovalChoice.DENY))
    result = registry.call("doc_set_alt_text", {"number": 1, "alt_text": "Waves on sand"})
    assert result.ok
    assert "can be undone" in result.text
    original, revised, label = applied[0]
    assert original == _DOC
    assert "![Waves on sand](beach.png)" in revised
    assert label == "Alt text for image 1"
    assert registry.mutated()


def test_a_declined_review_is_not_a_change() -> None:
    registry = _registry(
        doc_image_tools(lambda: _DOC, lambda *_a: False), _Approver(ApprovalChoice.DENY)
    )
    result = registry.call("doc_set_alt_text", {"number": 1, "alt_text": "Waves"})
    assert not result.ok
    assert not registry.mutated()


def test_a_bad_number_fails_without_touching_the_document() -> None:
    applied: list[object] = []
    registry = _registry(
        doc_image_tools(lambda: _DOC, lambda *a: applied.append(a)), _Approver(ApprovalChoice.DENY)
    )
    result = registry.call("doc_set_alt_text", {"number": 7, "alt_text": "x"})
    assert not result.ok and "no image 7" in result.text
    assert applied == []


def test_looking_at_a_picture_asks_first_and_names_it() -> None:
    loaded: list[str] = []

    def load(image):
        loaded.append(image.source)
        return ToolImage(b"jpg", "image/jpeg", description="Image 2, dog.jpg.")

    approver = _Approver(ApprovalChoice.ONCE)
    registry = _registry(doc_image_tools(lambda: _DOC, lambda *_a: True, load), approver)
    result = registry.call("doc_image", {"number": 2})
    assert approver.asked == [
        "Send the picture dog.jpg from this document to your AI, to describe it."
    ]
    assert result.image is not None and loaded == ["dog.jpg"]


def test_a_refused_picture_is_never_loaded() -> None:
    loaded: list[str] = []
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(
        doc_image_tools(lambda: _DOC, lambda *_a: True, lambda image: loaded.append("x") or "x"),
        approver,
    )
    result = registry.call("doc_image", {"number": 1})
    assert not result.ok
    assert loaded == []
