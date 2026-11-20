"""Confirmed WordPress interaction failures (plan.md, 2026-11-20), core half.

Each test reproduces the original failure with the real function and fake
boundaries -- no site, no network:

1. a renamed Practice Site was refused as "not ready" on its next start;
2. Open by Web Address ignored ports and matched ``/blog`` inside ``/blogger``;
3. a renamed draft's file was looked for under its new title;
6. the Discussion preview counted one link twice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.core.wordpress import sites as st
from quill.core.wordpress import workbench_practice_process as process
from quill.core.wordpress.workbench_practice import (
    _HANDOFF_DIR,
    _SETUP_MARKER,
    PracticeTools,
    site_url,
    start_command,
)
from quill.core.wordpress.workbench_settings_more import discussion_lines

# --------------------------------------------------------------------------- #
# 1. the Practice Site's readiness does not depend on its title


class _Running:
    pid = 0
    stdin = stdout = stderr = None

    def poll(self) -> None:
        return None


def _answer_index(monkeypatch: pytest.MonkeyPatch, index: dict[str, Any]) -> None:
    class Response:
        status = 200

        def read(self) -> bytes:
            return json.dumps(index).encode("utf-8")

    class Connection:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def request(self, *_a: Any, **_k: Any) -> None:
            pass

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(process, "HTTPConnection", Connection)


def _tools(tmp_path: Path) -> PracticeTools:
    core = tmp_path / "core"
    core.mkdir()
    (core / "wp-load.php").write_text("<?php", encoding="utf-8")
    return PracticeTools(tmp_path / "node.exe", tmp_path / "cli.js", wordpress=core)


def test_a_renamed_practice_site_is_still_ready_after_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tools, folder = _tools(tmp_path), tmp_path / "site"
    start_command(tools, folder)
    (folder / _HANDOFF_DIR / _SETUP_MARKER).write_text("1", encoding="utf-8")
    learner = folder / "wordpress" / "wp-content" / "database" / ".ht.sqlite"
    learner.parent.mkdir(parents=True)
    learner.write_bytes(b"the learner's posts")
    index = {"name": "Practice Site", "url": site_url(), "namespaces": ["oembed/1.0", "wp/v2"]}
    _answer_index(monkeypatch, index)
    process.wait_for_site(_Running(), folder, timeout=0)  # type: ignore[arg-type]

    # The learner renames the site in Settings > General, then restarts it.
    index["name"] = "My Learning Site"
    argv = start_command(tools, folder)
    assert not any(a.startswith("--blueprint") for a in argv), "a restart re-ran the setup"
    process.wait_for_site(_Running(), folder, timeout=0)  # type: ignore[arg-type]
    assert learner.read_bytes() == b"the learner's posts"


def test_readiness_still_refuses_another_address_or_an_unset_up_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "site"
    (folder / _HANDOFF_DIR).mkdir(parents=True)
    _answer_index(
        monkeypatch, {"name": "Practice Site", "url": site_url(), "namespaces": ["wp/v2"]}
    )
    with pytest.raises(RuntimeError, match="did not become ready"):
        process.wait_for_site(_Running(), folder, timeout=0)  # type: ignore[arg-type]
    (folder / _HANDOFF_DIR / _SETUP_MARKER).write_text("1", encoding="utf-8")
    _answer_index(
        monkeypatch,
        {"name": "Practice Site", "url": "http://127.0.0.1:8080", "namespaces": ["wp/v2"]},
    )
    with pytest.raises(RuntimeError, match="did not become ready"):
        process.wait_for_site(_Running(), folder, timeout=0)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 2. Open by Web Address: origin, effective port and path segments


def _store(*urls: str, wpcom: str = "") -> st.SiteStore:
    return st.SiteStore([
        st.SiteProfile(id=f"s{i}", name=f"Site {i}", site_url=url, wpcom_site=wpcom)
        for i, url in enumerate(urls)
    ])


def test_another_port_on_the_same_host_is_another_site() -> None:
    store = _store("http://127.0.0.1:9400")
    assert store.match_url("http://127.0.0.1:8080/?p=77") is None
    assert store.match_url("http://127.0.0.1/?p=77") is None
    assert store.match_url("http://127.0.0.1:9400/?p=77").id == "s0"  # type: ignore[union-attr]


def test_two_sites_on_one_host_are_told_apart_by_port() -> None:
    store = _store("http://localhost:9400", "http://localhost:8080")
    assert store.match_url("http://localhost:8080/hello/").id == "s1"  # type: ignore[union-attr]
    assert store.match_url("http://localhost:9400/hello/").id == "s0"  # type: ignore[union-attr]


def test_a_subsite_owns_only_whole_path_segments() -> None:
    store = _store("https://example.org/blog")
    assert store.match_url("https://example.org/blogger/post") is None
    assert store.match_url("https://example.org/blog").id == "s0"  # type: ignore[union-attr]
    assert store.match_url("https://example.org/blog/").id == "s0"  # type: ignore[union-attr]
    assert store.match_url("https://example.org/blog/hello/").id == "s0"  # type: ignore[union-attr]


def test_the_root_site_takes_what_the_subsite_does_not() -> None:
    store = _store("https://example.org", "https://example.org/blog/")
    assert store.match_url("https://example.org/blog/hi").id == "s1"  # type: ignore[union-attr]
    assert store.match_url("https://example.org/blogger/hi").id == "s0"  # type: ignore[union-attr]
    assert store.match_url("https://example.org/").id == "s0"  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "url",
    [
        "https://www.example.org/hello/",  # www. is the same site
        "https://EXAMPLE.org/hello/",
        "https://example.org:443/hello/",  # the default port, written out
        "http://example.org/hello/",  # http and https on their default ports
    ],
)
def test_intended_canonical_aliases_still_match(url: str) -> None:
    assert _store("https://example.org").match_url(url) is not None


@pytest.mark.parametrize(
    "url", ["https://example.org:8443/hello/", "ftp://example.org/hello/", "https://example.net/"]
)
def test_other_origins_do_not_match(url: str) -> None:
    assert _store("https://example.org").match_url(url) is None


def test_a_wordpress_com_site_matches_by_its_own_address() -> None:
    store = _store("https://public-api.wordpress.com", wpcom="radio.wordpress.com")
    assert store.match_url("https://radio.wordpress.com/2026/11/hello/") is not None
    assert store.match_url("https://radio.wordpress.com:8443/hello/") is None


# --------------------------------------------------------------------------- #
# 3. a draft's file keeps its name when its title changes


def test_the_document_file_does_not_follow_the_title(tmp_path: Path) -> None:
    store = lc.LocalStore(tmp_path)
    copy = lc.WorkingCopy(site_id="radio", kind="post", local_id="abc", title="First Title")
    path = store.write_document(copy)
    path.write_text("The learner's writing", encoding="utf-8")

    copy.title = "A Better Title"  # Properties
    store.save(copy)
    assert store.document_path(copy) == path
    reopened = store.drafts()[0]
    assert store.document_path(reopened) == path
    assert store.copy_for_path(store.document_path(reopened)).text == "The learner's writing"  # type: ignore[union-attr]

    store.rekey(reopened, 77)  # sent: an id on the site, the folder kept
    again = store.find("radio", "post", 77)
    assert again is not None and store.document_path(again) == path
    assert store.write_document(again) == path, "a rewrite moved the open file"
    assert path.is_file() and len(list(path.parent.glob("*.md"))) == 1


def test_a_restored_version_keeps_the_current_file_name(tmp_path: Path) -> None:
    store = lc.LocalStore(tmp_path)
    copy = lc.WorkingCopy(site_id="radio", kind="post", local_id="abc", title="Old")
    path = store.write_document(copy)
    recorded = copy.properties.pop("document_file")  # a version kept before names were
    version = store.add_version(copy, lc.REASON_SAVED, title="Older Title")
    copy.properties["document_file"] = recorded
    store.save(copy)
    restored = store.restore(copy, version.id)
    assert store.document_path(restored) == path


def test_a_recorded_name_that_is_not_a_plain_file_name_is_ignored(tmp_path: Path) -> None:
    store = lc.LocalStore(tmp_path)
    copy = lc.WorkingCopy(site_id="radio", kind="post", local_id="abc", title="Safe")
    copy.properties["document_file"] = "..\\..\\elsewhere.md"
    assert store.document_path(copy).name == "Safe.md"
    copy.properties["document_file"] = "page.html"  # the wrong format for a Markdown copy
    assert store.document_path(copy).name == "Safe.md"


# --------------------------------------------------------------------------- #
# 6. the Discussion preview counts links the way WordPress does


def _held_line(*contents: str) -> str:
    comments = [{"content": {"raw": c}, "author": 1} for c in contents]
    return next(line for line in discussion_lines(comments) if line.startswith("Hold a comment"))


def test_one_linked_anchor_is_one_link() -> None:
    assert "would have held 0 " in _held_line('Read <a href="https://example.org/a">this</a>.')


def test_two_links_are_held_under_the_two_link_rule() -> None:
    two = '<a href="https://a.example/">a</a> and http://b.example/'
    assert "would have held 1 " in _held_line(two)


def test_text_without_an_address_is_not_a_link() -> None:
    assert "would have held 0 " in _held_line("I said http twice: http, <a name=x>.")
