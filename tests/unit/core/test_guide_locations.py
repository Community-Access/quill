"""Where each editor finds its guides, in every kind of download."""

from __future__ import annotations

from pathlib import Path

from quill.core import guide_locations as gl


def _quill_install(root: Path) -> Path:
    (root / "docs" / "quill-guide").mkdir(parents=True)
    (root / "docs" / "github-guide").mkdir(parents=True)
    (root / "docs" / "userguide.md").write_text("# QUILL\n", encoding="utf-8")
    (root / "docs" / "github-guide" / "github-guide.html").write_text("<p>", encoding="utf-8")
    return root


def _lite_install(root: Path) -> Path:
    (root / "docs" / "guide").mkdir(parents=True)
    (root / "docs" / "userguide.md").write_text("# Lite\n", encoding="utf-8")
    (root / "docs" / "guide" / "lite-github-guide.html").write_text("<p>", encoding="utf-8")
    return root


def test_an_installed_quill_finds_its_guides_in_the_app_folder(tmp_path) -> None:
    app = _quill_install(tmp_path / "app")
    assert gl.find_guide("quill", "user", roots=[app]) == app / "docs" / "userguide.md"
    assert gl.find_guide("quill", "github", roots=[app]) == (
        app / "docs" / "github-guide" / "github-guide.html"
    )


def test_an_installed_quill_lite_finds_its_guides_in_the_app_folder(tmp_path) -> None:
    app = _lite_install(tmp_path / "app")
    assert gl.find_guide("quilllite", "user", roots=[app]) == app / "docs" / "userguide.md"
    assert gl.find_guide("quilllite", "github", roots=[app]) == (
        app / "docs" / "guide" / "lite-github-guide.html"
    )


def test_one_editors_guide_is_never_taken_for_the_others(tmp_path) -> None:
    lite = _lite_install(tmp_path / "lite")
    quill = _quill_install(tmp_path / "quill")
    # The Lite folder comes first, and its userguide.md has no quill-guide beside it.
    assert gl.find_guide("quill", "user", roots=[lite, quill]) == quill / "docs" / "userguide.md"
    assert gl.find_guide("quilllite", "user", roots=[quill, lite]) == (
        lite / "docs" / "userguide.md"
    )


def test_a_development_run_falls_back_to_this_checkout() -> None:
    assert gl.find_guide("quill", "user", roots=[]) == gl._REPO_ROOT.joinpath(
        "docs", "user guide", "userguide.md"
    )
    for product in ("quill", "quilllite"):
        found = gl.find_guide(product, "github", roots=[])
        assert found is not None and found.is_file() and found.suffix == ".html"


def test_the_search_starts_beside_the_program_whatever_the_working_directory(tmp_path) -> None:
    env = {
        "QUILL_LAUNCHER_DIR": str(tmp_path / "launcher"),
        "QUILL_APP_ROOT": str(tmp_path / "portable"),
        "RESOURCEPATH": str(tmp_path / "Resources"),
    }
    roots = gl.search_roots(env=env, executable=str(tmp_path / "runtime" / "pythonw.exe"))
    assert roots[:4] == [
        tmp_path / "launcher",
        (tmp_path / "runtime").resolve(),
        tmp_path / "portable",
        tmp_path / "Resources",
    ]
    # Every folder above the module: how {app}\Lib\site-packages\quill finds {app}.
    for parent in Path(gl.__file__).resolve().parents:
        assert parent in roots
    assert Path.cwd() not in roots[:4]
