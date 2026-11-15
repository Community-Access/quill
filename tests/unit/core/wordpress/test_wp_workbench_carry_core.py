"""WP-G, wx-free: imports, exports, copies, snapshots and archives carry media and links
where they can, and every report names what it left out."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_carry import (
    copy_left_out,
    export_left_out,
    folder_left_out,
    left_out_section,
    send_folder,
    strip_front_matter,
)
from quill.core.wordpress.workbench_io import folder_plan
from quill.core.wordpress.workbench_snapshot import snapshot_left_out, take_snapshot
from quill.core.wordpress.writing_archive import ArchiveResult, archive_sentence


class FakeSite:
    """Makes drafts with addresses and uploads pictures; records every request."""

    def __init__(self, refuse_upload: str = "") -> None:
        self.writes: list[tuple[str, Any]] = []
        self.uploads: list[str] = []
        self.refuse_upload = refuse_upload
        self.next_id = 100

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append((route, body))
        if route.count("/") > 2:  # an update
            return {"id": int(route.rsplit("/", 1)[1])}
        self.next_id += 1
        return {"id": self.next_id, "link": f"https://a.example/?p={self.next_id}"}

    def upload(self, route: str, name: str, data: bytes, kind: str, **_kw: Any) -> Any:
        if name == self.refuse_upload:
            raise WordPressApiError("too big", status=413)
        self.uploads.append(f"{name} {kind} {len(data)}")
        return {"id": 7, "source_url": f"https://a.example/up/{name}"}

    def get(self, route: str, **_params: Any) -> Any:
        return []

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        if route == "wp/v2/menus":
            raise WordPressApiError("no", status=500)
        yield from []


def _folder(tmp_path: Path) -> Path:
    (tmp_path / "pics").mkdir()
    (tmp_path / "pics" / "cat.png").write_bytes(b"PNG")
    (tmp_path / "a.md").write_text(
        "---\ntitle: First\ntags: news\n---\n# First\n\n![a cat](pics/cat.png)\n\n"
        "See [the second](b.md), [the notes](notes.pdf) and [WordPress](https://wordpress.org)."
        "\n\n![gone](pics/dog.png)\n\n![far](https://x.org/far.png)\n",
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text(
        "# Second\n\nThe same cat inline ![cat](pics/cat.png), back to [first](a.md).\n",
        encoding="utf-8",
    )
    return tmp_path


def test_the_folder_plan_finds_pictures_links_and_what_it_leaves_out(tmp_path: Path) -> None:
    plan = folder_plan(_folder(tmp_path), lambda p: p.read_text(encoding="utf-8"))
    first, second = plan
    assert first.fields["title"] == "First" and "title: First" not in first.fields["content"]
    assert list(first.carry["pictures"]) == ["pics/cat.png"]
    assert first.carry["links"] == {"b.md": "b.md"} and second.carry["links"] == {"a.md": "a.md"}
    assert (
        first.sentence == "a.md: First, as draft, 1 pictures to upload, 1 links to the other drafts"
    )
    left = folder_left_out(plan)
    assert "a.md: the picture pics/dog.png was not found beside it" in left
    assert "a.md: the picture https://x.org/far.png stays on x.org, not uploaded" in left
    assert any("the link to notes.pdf is left as written" in line for line in left)
    assert "a.md: its front matter (title, tags)" in left
    assert not any(line.find("wordpress.org") >= 0 for line in left)  # an outside link is carried


def test_send_folder_uploads_once_rewrites_links_and_ends_with_left_out(tmp_path: Path) -> None:
    site = FakeSite()
    plan = folder_plan(_folder(tmp_path), lambda p: p.read_text(encoding="utf-8"))
    said = send_folder(site, "post", plan)  # type: ignore[arg-type]
    assert site.uploads == ["cat.png image/png 3"]
    made = [body for route, body in site.writes if route == "wp/v2/posts"]
    assert 'src="https://a.example/up/cat.png"' in made[0]["content"]
    assert '<img src="https://a.example/up/cat.png" alt="cat"/>' in made[1]["content"]
    updates = dict(site.writes[2:])
    assert 'href="https://a.example/?p=102"' in updates["wp/v2/posts/101"]["content"]
    assert 'href="https://a.example/?p=101"' in updates["wp/v2/posts/102"]["content"]
    assert said[:3] == [
        "Uploaded the picture cat.png.",
        "Made a.md: First, number 101.",
        "Made b.md: Second, number 102.",
    ]
    assert "Linked a.md to the other drafts it names." in said
    assert said[said.index("Left out:") - 1] == ""
    assert any(line.startswith("- a.md: the picture pics/dog.png") for line in said)


def test_a_picture_the_site_refuses_is_listed_as_left_out(tmp_path: Path) -> None:
    site = FakeSite(refuse_upload="cat.png")
    plan = folder_plan(_folder(tmp_path), lambda p: p.read_text(encoding="utf-8"))
    said = send_folder(site, "post", plan)  # type: ignore[arg-type]
    assert "- a.md: the picture pics/cat.png could not be uploaded: too big" in said


def test_word_pictures_are_counted_and_left_out(tmp_path: Path) -> None:
    doc = tmp_path / "w.docx"
    with zipfile.ZipFile(doc, "w") as book:
        book.writestr("word/document.xml", "<w/>")
        book.writestr("word/media/image1.png", b"PNG")
        book.writestr("word/media/image2.png", b"PNG")
    plan = folder_plan(tmp_path, lambda _p: "# Report\n\nWords.")
    assert folder_left_out(plan) == [
        "w.docx: its 2 pictures (QUILL reads a Word file's words only)"
    ]


def test_left_out_sections_exports_and_copies_say_what_did_not_travel() -> None:
    assert left_out_section([]) == ["", "Left out: nothing."]
    assert left_out_section(["x", ""]) == ["", "Left out:", "- x"]
    said = export_left_out(["Title"], ["Title", "Author"])
    assert said.startswith("Left out: columns you have hidden (Author), each item's full text")
    copied = copy_left_out([
        {"status": "private", "content": {"raw": "<!-- wp:acme/slider /-->"}},
        {"status": "publish", "content": {"raw": "<!-- wp:paragraph -->"}},
    ])
    assert copied[0].startswith("Not copied: comments, revisions, custom fields")
    assert "1 private items arrive as drafts" in copied[1]
    assert copied[2].endswith("same plugin: acme/slider.")


def test_a_snapshot_records_what_it_left_out(tmp_path: Path) -> None:
    where, _counts = take_snapshot(FakeSite(), tmp_path, site="A", clock=lambda: 0)  # type: ignore[arg-type]
    left = snapshot_left_out(where)
    assert left[0].startswith("the media files themselves (not asked for")
    assert "never taken" in left[1] and left[2].startswith("menus: the site would not give it")
    told = json.loads((where / "snapshot.json").read_text(encoding="utf-8"))
    assert told["left_out"] == left


def test_the_archive_sentence_names_what_it_left_out(tmp_path: Path) -> None:
    said = archive_sentence("Radio", tmp_path / "arch", ArchiveResult(saved=2))
    assert said.startswith("Your writing on Radio is in arch: 2 saved. Left out: comments")


def test_front_matter_is_taken_off_and_named() -> None:
    assert strip_front_matter("---\na: 1\nb: 2\n---\n# T\n") == ("# T\n", ["a", "b"])
    assert strip_front_matter("# T\n---\n") == ("# T\n---\n", [])
