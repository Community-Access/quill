"""Put Back from a Snapshot restores more than the words (how.md review, safety 6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quill.core.wordpress.workbench_snapshot import RESTORE_TERMS, restore_plan

SAVED = {
    "id": 7,
    "title": {"raw": "Spring news"},
    "content": {"raw": "Hello"},
    "excerpt": {"raw": ""},
    "status": "publish",
    "slug": "spring-news",
    "categories": [3, 4],
    "tags": [9],
    "featured_media": 55,
    "comment_status": "open",
}


class _Api:
    def __init__(self, now: list[dict[str, Any]]) -> None:
        self.now = now

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        yield from (self.now if route == "wp/v2/posts" else [])


def _snapshot(tmp_path: Path) -> Path:
    (tmp_path / "posts.json").write_text(json.dumps([SAVED]), encoding="utf-8")
    return tmp_path


def test_a_changed_post_gets_its_status_address_terms_and_picture_back(tmp_path) -> None:
    changed = {
        **SAVED,
        "status": "draft",
        "slug": "spring-news-2",
        "categories": [1],
        "featured_media": 0,
    }
    lines = restore_plan(_Api([changed]), _snapshot(tmp_path))
    assert len(lines) == 1 and lines[0].action == "put back"
    body = lines[0].body
    assert body["status"] == "publish" and body["slug"] == "spring-news"
    assert body["categories"] == [3, 4] and body["tags"] == [9] and body["featured_media"] == 55


def test_a_deleted_post_comes_back_as_a_draft_with_everything_else(tmp_path) -> None:
    lines = restore_plan(_Api([]), _snapshot(tmp_path))
    assert lines[0].action == "make again"
    body = lines[0].body
    assert body["status"] == "draft"
    assert body["slug"] == "spring-news" and body["categories"] == [3, 4]


def test_an_unchanged_post_is_left_alone_and_the_terms_say_what_comes_back(tmp_path) -> None:
    assert restore_plan(_Api([dict(SAVED)]), _snapshot(tmp_path)) == []
    assert "status, address, categories and tags, featured image" in RESTORE_TERMS
