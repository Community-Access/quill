"""Help > What's New: the shared changelog opener every QuillVille app calls."""

from __future__ import annotations

from pathlib import Path

from quill.ui import whats_new


def test_a_packaged_build_prefers_its_own_docs_folder(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CHANGELOG.html").write_text("<p>new</p>", encoding="utf-8")
    assert whats_new.find_changelog("radio", folders=[tmp_path]) == docs / "CHANGELOG.html"


def test_html_wins_over_markdown_in_the_same_folder(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CHANGELOG.md").write_text("# new", encoding="utf-8")
    (docs / "CHANGELOG.html").write_text("<p>new</p>", encoding="utf-8")
    assert whats_new.find_changelog("cast", folders=[tmp_path]).suffix == ".html"


def test_a_checkout_finds_each_apps_changelog() -> None:
    for app in ("quilllite", "radio", "cast", "transcribe", "converter", "studio", "weather"):
        found = whats_new.find_changelog(app, folders=[])
        assert found is not None, app
        assert app in found.as_posix(), (app, found)


def test_quill_itself_reads_the_root_changelog() -> None:
    found = whats_new.find_changelog("quill", folders=[])
    assert found is not None and found.parent == whats_new._REPO_ROOT


def test_opening_announces_the_outcome(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CHANGELOG.html").write_text("<p>new</p>", encoding="utf-8")
    said: list[str] = []
    urls: list[str] = []
    opened = whats_new.open_whats_new(
        "radio",
        "Quill Radio",
        said.append,
        folders=[tmp_path],
        open_url=lambda url: urls.append(url) or True,
    )
    assert opened is True
    assert urls == [(docs / "CHANGELOG.html").as_uri()]
    assert said == ["Opened What's New in Quill Radio in your browser"]


def test_a_missing_changelog_says_so_rather_than_doing_nothing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(whats_new, "_REPO_ROOT", tmp_path)
    said: list[str] = []
    assert whats_new.open_whats_new("nowhere", "Nothing", said.append, folders=[tmp_path]) is False
    assert said == ["What's New in Nothing was not found in this build."]


def test_a_markdown_only_changelog_is_rendered_to_html(tmp_path: Path, quill_data_dir) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CHANGELOG.md").write_text("# Changelog\n\n- one", encoding="utf-8")
    urls: list[str] = []
    whats_new.open_whats_new(
        "beacon",
        "QuillBeacon",
        lambda _m: None,
        folders=[tmp_path],
        open_url=lambda url: urls.append(url) or True,
    )
    assert urls and urls[0].endswith("CHANGELOG.html")
    assert "whats-new" in urls[0]
