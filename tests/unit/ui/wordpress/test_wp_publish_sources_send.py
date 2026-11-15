"""Publishing Markdown, block markup, HTML and plain text, end to end, in both editors.

Each source goes through the real commands -- Send This Document (Save Draft
to Site), then Publish, then the item opened again from the site and updated
-- against a fake site that keeps what it is sent. What the site receives must
be block markup, on the right route, with the right title and status, and the
second and third sends must carry exactly what the first did.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.core.wordpress.blocks import parse
from quill.ui.wordpress_commands import WordPressCommands

API = "/wp-json/wp/v2"
EDITOR = {
    "id": 7,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["editor"],
    "capabilities": {"edit_posts": True, "publish_posts": True, "publish_pages": True},
}
ROUTES = {"/wp/v2/posts": {}, "/wp/v2/pages": {}, "/wp/v2/events": {}}

SOURCES: dict[str, tuple[str, str]] = {
    "markdown": (
        "spring.md",
        "# Spring News\n\nWe are *back* & on [air](https://radio.example/live).\n\n"
        "- one\n  - nested\n\n> Quoted\n\n```\na < b\n```\n\n---\n\n| A | B |\n| --- | --- |\n"
        "| 1 | 2 |\n",
    ),
    "blocks": (
        "spring.html",
        '<!-- wp:heading {"level":1} -->\n<h1 class="wp-block-heading">Spring News</h1>\n'
        "<!-- /wp:heading -->\n\n<!-- wp:paragraph -->\n<p>We are <em>back</em>.</p>\n"
        "<!-- /wp:paragraph -->\n\n<!-- wp:separator -->\n"
        '<hr class="wp-block-separator has-alpha-channel-opacity"/>\n<!-- /wp:separator -->',
    ),
    "html": (
        "spring.html",
        "<html><head><title>Ignored</title></head><body><h1>Spring News</h1>"
        "<p>We are <em>back</em> &amp; on air.</p><ul><li>one<ul><li>nested</li></ul></li></ul>"
        "<table><tr><th>A</th></tr><tr><td>1</td></tr></table><hr></body></html>",
    ),
    "text": ("Spring News.txt", "We are back\nand on air.\n\n5 < 6 & 7 > 3\n"),
}

#: What each source must arrive as: its blocks, in order.
EXPECTED_BLOCKS = {
    "markdown": [
        "core/paragraph",
        "core/list",
        "core/quote",
        "core/code",
        "core/separator",
        "core/table",
    ],
    "blocks": ["core/paragraph", "core/separator"],
    "html": ["core/paragraph", "core/list", "core/table", "core/separator"],
    "text": ["core/paragraph", "core/paragraph"],
}


class StoringSite:
    """Routes on the fake site that keep one item per collection, as WordPress would."""

    def __init__(self, wp_site: Any, collection: str, kind: str) -> None:
        self.wp_site = wp_site
        self.path = f"{API}/{collection}"
        self.kind = kind
        self.item: dict[str, Any] = {}
        self.stamp = 0
        wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": ROUTES})
        wp_site.on("GET", f"{API}/users/me", EDITOR)
        wp_site.on("POST", self.path, self._save)
        wp_site.on("POST", f"{self.path}/41", self._save)
        wp_site.on("GET", f"{self.path}/41", lambda _r, _q: self._payload())

    def _save(self, request: Any, _query: Any) -> dict[str, Any]:
        sent = json.loads(request.data or b"{}")
        self.stamp += 1
        self.item.update(sent)
        return self._payload()

    def _payload(self) -> dict[str, Any]:
        return {
            "id": 41,
            "type": self.kind,
            "title": {"raw": self.item.get("title", "")},
            "content": {"raw": self.item.get("content", "")},
            "status": self.item.get("status", "draft"),
            "link": f"https://radio.example/?p=41&kind={self.kind}",
            "modified_gmt": f"2026-11-13T10:00:{self.stamp:02d}",
        }

    def bodies(self) -> list[dict[str, Any]]:
        sent = self.wp_site.sent("POST", self.path) + self.wp_site.sent("POST", f"{self.path}/41")
        sent.sort(key=self.wp_site.requests.index)
        return [self.wp_site.body(r) for r in sent]


def _block_names(content: str) -> list[str]:
    return [b.name for b in parse(content) if b.name is not None]


def _assert_is_blocks(source: str, content: str) -> None:
    assert _block_names(content) == EXPECTED_BLOCKS[source]
    assert "Spring News" not in content  # the title is the title, not the first block
    assert "<html" not in content and "<head" not in content and "Ignored" not in content
    for raw_markdown in ("**", "](", "\n- ", "```", "\n> ", "| --- |"):
        assert raw_markdown not in content
    if source == "markdown":
        assert '<a href="https://radio.example/live">air</a>' in content
        assert "&amp; on" in content and "a &lt; b" in content
        nested = [b for b in parse(content) if b.name][1].inner_blocks[0].inner_blocks
        assert nested and nested[0].name == "core/list"
    if source == "blocks":
        assert content == SOURCES["blocks"][1].split("<!-- /wp:heading -->\n\n", 1)[1]
    if source == "html":
        assert "<em>back</em> &amp; on air." in content
        assert "<thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody>" in content
    if source == "text":
        assert "<p>We are back<br>and on air.</p>" in content
        assert "<p>5 &lt; 6 &amp; 7 &gt; 3</p>" in content


@pytest.fixture
def send(wp, wp_site, wp_dialogs, tmp_path):
    def run(source: str, kind: str) -> tuple[StoringSite, dict[str, Any]]:
        name, text = SOURCES[source]
        doc = tmp_path / name
        doc.write_text(text, encoding="utf-8", newline="")
        wp.host.open_path(doc)
        site = StoringSite(wp_site, "posts" if kind == "post" else "pages", kind)
        wp_dialogs.answer("ask_choice", 0 if kind == "post" else 1)
        wp.cmd_send_document()
        bodies = site.bodies()
        assert len(bodies) == 1, wp.host.said
        return site, bodies[0]

    return run


@pytest.mark.parametrize("kind", ["post", "page"])
@pytest.mark.parametrize("source", list(SOURCES))
def test_draft_publish_and_update_send_the_same_blocks(
    send, wp, wp_site, wp_dialogs, source, kind
) -> None:
    site, draft = send(source, kind)
    expected_title = "Spring News"
    assert draft["title"] == expected_title
    assert draft["status"] == "draft"
    _assert_is_blocks(source, draft["content"])
    if kind == "page":
        assert "categories" not in draft and draft["parent"] == 0
    else:
        assert "parent" not in draft
    assert wp.host.announced[-1] == "Draft saved to Community Radio. It is not public."

    # Publish the working copy QUILL opened.
    wp_dialogs.answer("confirm", True)
    wp.cmd_publish()
    published = site.bodies()[-1]
    assert wp_site.sent("POST", f"{site.path}/41"), "Publish must update item 41, not create"
    assert published["status"] == "publish"
    assert published["content"] == draft["content"]
    assert published["title"] == expected_title

    # Open it again from the site, once as Markdown and once as HTML, and Update.
    for open_as in (1, 0):
        copy = wp.local.copy_for_path(wp.host.current_path())
        wp.local.discard(copy.key)
        wp_dialogs.answer("ask_choice", open_as)
        wp.open_item(wp.profile, kind, 41)
        reopened = wp.local.copy_for_path(wp.host.current_path())
        assert reopened.text_format == ("markdown" if open_as == 1 else "html")
        wp_dialogs.answer("confirm", True)
        wp.cmd_publish()
        again = site.bodies()[-1]
        assert again["content"] == draft["content"], f"drift after opening as {open_as}"
        assert again["status"] == "publish" and again["title"] == expected_title


def test_a_custom_type_publishes_on_its_own_route(wp, wp_site, wp_dialogs) -> None:
    site = StoringSite(wp_site, "events", "events")
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="events",
        local_id="ev1",
        title="Open Day",
        text="## When\n\nSaturday *morning*.\n",
        text_format="markdown",
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.cmd_save_draft()
    wp_dialogs.answer("confirm", True)
    wp.cmd_publish()
    draft, published = site.bodies()
    assert wp_site.sent("POST", f"{API}/events") and wp_site.sent("POST", f"{API}/events/41")
    assert draft["status"] == "draft" and published["status"] == "publish"
    assert _block_names(published["content"]) == ["core/heading", "core/paragraph"]
    assert "<em>morning</em>" in published["content"]


# --------------------------------------------------------------------------- #
# Both editors: the real host adapters, where opening a file differs


class _Control:
    def __init__(self, text: str) -> None:
        self.text = text

    def GetValue(self) -> str:  # noqa: N802 - wx's name
        return self.text

    def IsModified(self) -> bool:  # noqa: N802 - wx's name
        return False


class _LiteApp:
    def __init__(self) -> None:
        self.windows: list[Any] = []

    def open_path(self, path: Path) -> None:
        # QUILL Lite opens every file in a window of its own.
        self.windows.append(_LiteWindow(self, Path(path)))


class _LiteWindow:
    def __init__(self, app: _LiteApp, path: Path) -> None:
        self.app = app
        self.path = path
        self.control = _Control(path.read_text(encoding="utf-8"))
        self.said: list[str] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def cmd_save(self) -> None:
        return None


class _QuillDocument:
    def __init__(self, path: Path) -> None:
        self.path = str(path)
        self.modified = False


class _QuillFrame:
    def __init__(self, path: Path) -> None:
        self.frame = None
        self.said: list[str] = []
        self.open_file(path)

    def open_file(self, path: Path) -> None:
        # QUILL replaces the document in front.
        self.document = _QuillDocument(Path(path))
        self.editor = _Control(Path(path).read_text(encoding="utf-8"))

    def save_file(self) -> None:
        return None

    def _announce(self, text: str) -> None:
        self.said.append(text)


def _synchronous(host_class: type) -> type:
    class Host(host_class):  # type: ignore[misc, valid-type]
        def run_task(self, name, func, on_success, on_failure):  # type: ignore[no-untyped-def]
            try:
                result = func()
            except BaseException as exc:  # noqa: BLE001
                on_failure(exc)
                return
            on_success(result)

        def set_clipboard_text(self, text: str) -> None:
            self.clipboard = text

        def start_repeating(self, _seconds, _callback):  # type: ignore[no-untyped-def]
            return lambda: None

    return Host


@pytest.mark.parametrize("editor", ["QUILL", "QUILL Lite"])
@pytest.mark.parametrize("source", list(SOURCES))
def test_send_this_document_reaches_the_site_from_either_editor(
    wp, wp_site, wp_dialogs, tmp_path, editor, source
) -> None:
    from quill.apps.lite_window_wordpress_host import LiteWordPressHost
    from quill.ui.main_frame_wordpress import QuillWordPressHost

    name, text = SOURCES[source]
    doc = tmp_path / name
    doc.write_text(text, encoding="utf-8", newline="")
    if editor == "QUILL":
        window: Any = _QuillFrame(doc)
        host = _synchronous(QuillWordPressHost)(window)
    else:
        window = _LiteWindow(_LiteApp(), doc)
        host = _synchronous(LiteWordPressHost)(window)
    commands = WordPressCommands(host, data_dir=wp._data_dir, opener=wp_site)
    site = StoringSite(wp_site, "pages", "page")
    wp_dialogs.answer("ask_choice", 1)
    commands.cmd_send_document()
    bodies = site.bodies()
    assert len(bodies) == 1, window.said
    assert bodies[0]["title"] == "Spring News" and bodies[0]["status"] == "draft"
    _assert_is_blocks(source, bodies[0]["content"])
    assert window.said[-1] == "Draft saved to Community Radio. It is not public."


def test_an_html_working_copy_without_blocks_goes_exactly_as_written(wp, wp_site) -> None:
    """Opened "as HTML" or begun as HTML, the text is the site's own: a Classic post
    stays Classic rather than being re-cut into blocks on every Update."""
    site = StoringSite(wp_site, "posts", "post")
    classic = "<p>Old <b>classic</b> post.</p>\n<p>Second &amp; last.</p>"
    copy = lc.WorkingCopy(
        site_id="radio", kind="post", local_id="c1", title="Old", text=classic, text_format="html"
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.cmd_save_draft()
    assert site.bodies()[0]["content"] == classic
