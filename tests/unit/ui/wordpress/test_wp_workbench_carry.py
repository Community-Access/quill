"""WP-G in the real frame: Import a Folder of Documents uploads pictures and maps links,
and Export List, Import Posts, Take a Snapshot and Copy to Site each name what they
left out. Each is called through its command on the fake site."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.sites import SiteProfile  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_lists import bench as _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE, _go, _select  # noqa: E402

bench = _bench


@pytest.fixture
def answers(monkeypatch):
    """Choosers pick the first row; previews are accepted and kept; reports are kept."""
    seen: dict[str, list[Any]] = {"reports": [], "previews": []}
    monkeypatch.setattr(dlg, "ask_choice", lambda *a, **k: 0)
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *a, **k: seen["previews"].append(k["lines"]) or True
    )
    monkeypatch.setattr(dlg, "show_report", lambda *a, **k: seen["reports"].append(k["text"]))
    return seen


def test_import_a_folder_uploads_its_pictures_and_lists_what_it_left_out(
    bench, answers, monkeypatch, tmp_path: Path
) -> None:
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "cat.png").write_bytes(b"PNG")
    (folder / "one.md").write_text(
        "# Opening Night\n\n![the cat](cat.png)\n\n![lost](lost.png)\n", encoding="utf-8"
    )
    uploads: list[str] = []

    def upload(route: str, name: str, data: bytes, kind: str, **_k: Any) -> Any:
        uploads.append(name)
        return {"id": 9, "source_url": "https://radio.example/up/cat.png"}

    monkeypatch.setattr(bench.api, "upload", upload, raising=False)
    monkeypatch.setattr(type(bench.provider), "_folder", lambda self, title: folder)
    _go(bench, NodeRef("site", "posts", SITE))
    bench.run(command("import_folder"))
    assert (
        "Left out: one.md: the picture lost.png was not found beside it."
        in (answers["previews"][0])
    )
    assert uploads == ["cat.png"]
    made = [w[2] for w in bench.api.writes if w[1] == "wp/v2/posts"]
    assert 'src="https://radio.example/up/cat.png"' in made[0]["content"]
    report = answers["reports"][-1].splitlines()
    assert report[0] == "Uploaded the picture cat.png."
    assert "Left out:" in report and "- one.md: the picture lost.png was not found beside it" in (
        report
    )


def test_import_posts_from_a_spreadsheet_reports_what_it_left_out(
    bench, answers, monkeypatch, tmp_path: Path
) -> None:
    sheet = tmp_path / "posts.csv"
    sheet.write_text("Title,Colour\nGo,red\n", encoding="utf-8")
    monkeypatch.setattr(type(bench.provider), "_file", lambda self, *a, **k: sheet)
    _go(bench, NodeRef("site", "posts", SITE))
    bench.run(command("import_posts"))
    report = answers["reports"][-1].splitlines()
    assert report[0].startswith("Made Row 2: Go")
    assert "- columns matching no field: colour" in report
    assert any(line.startswith("- Not carried from a spreadsheet: pictures") for line in report)


def test_export_list_says_what_the_file_leaves_out(
    bench, answers, monkeypatch, tmp_path: Path
) -> None:
    out = tmp_path / "list.csv"
    monkeypatch.setattr(type(bench.provider), "_file", lambda self, *a, **k: out)
    _go(bench, NodeRef("site", "posts", SITE))
    bench.run(command("export_list"))
    assert out.is_file()
    assert "Left out:" in bench.said[-1] and "each item's full text" in bench.said[-1]


def test_a_snapshot_says_what_it_left_out(bench, answers) -> None:
    _go(bench, NodeRef("site", "overview", SITE))
    bench.run(command("snapshot"))
    said = bench.said[-1]
    assert "Snapshot of" in said and "Left out: the media files themselves" in said


def test_copy_to_site_previews_what_it_will_not_carry(bench, answers) -> None:
    bench.provider._profiles["Staging"] = SiteProfile(
        "s2", "Staging", "https://staging.example", "jeff"
    )
    _go(bench, NodeRef("site", "posts", SITE))
    _select(bench, 1)
    bench.run(command("copy_to_site"))
    lines = answers["previews"][0]
    assert any(line.startswith("Left out: Not copied: comments, revisions") for line in lines)
