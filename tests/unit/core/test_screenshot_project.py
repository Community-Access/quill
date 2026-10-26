"""Exported masks, edit reversibility, source integrity and bundle privacy."""

import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from quill.core.screenshot_project import ScreenshotProject, compare_screenshots, percent_box
from quill.core.studio_capture import verify_capture


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "private-original.png"
    Image.new("RGB", (200, 120), "white").save(path)
    return ScreenshotProject(verify_capture(path, "Private application title"))


def test_redaction_is_flattened_and_original_is_unchanged(project, tmp_path):
    project.add("redact", box=(0, 0, 50, 100))
    export = project.export(tmp_path)
    with Image.open(export.path) as image:
        assert image.getpixel((10, 60)) == (0, 0, 0)
        assert image.getpixel((150, 60)) == (255, 255, 255)
    with Image.open(project.evidence.path) as image:
        assert image.getpixel((10, 60)) == (255, 255, 255)


def test_undo_redo_includes_removal_and_movement(project):
    project.add("rectangle", box=(10, 10, 30, 30), text="Issue")
    original_box = project.operations[0]["box"]
    project.move(0, dx=1)
    assert project.operations[0]["box"][0] == 11
    project.undo()
    assert project.operations[0]["box"] == original_box
    project.remove(0)
    assert not project.operations
    project.undo()
    assert project.operations
    project.redo()
    assert not project.operations


def test_invalid_move_retains_prior_edit_and_review(project):
    project.add("redact", box=(0, 0, 50, 100))
    with pytest.raises(ValueError):
        project.move(0, dx=-1)
    assert project.operations[0]["box"] == (0, 0, 50, 100)


def test_edits_invalidate_prior_human_review(project):
    project.review = {"privacy": "reviewed", "content": "reviewed"}
    project.add("crop", box=(0, 0, 50, 100))
    assert project.review == {}


def test_bundle_excludes_original_and_escapes_description(project, tmp_path):
    project.goal = "<script>alert('bad')</script>"
    project.add("redact", box=(0, 0, 50, 100))
    bundle = project.bundle(tmp_path)
    with zipfile.ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {
            "screenshot.png",
            "evidence.json",
            "description.md",
            "description.html",
        }
        manifest = json.loads(archive.read("evidence.json"))
        assert manifest["original_included"] is False
        assert "Private application title" not in archive.read("description.md").decode()
        assert "<script>" not in archive.read("description.html").decode()
        assert "&lt;script&gt;" in archive.read("description.html").decode()
        assert Path(project.evidence.path).name not in archive.namelist()


def test_strict_bundle_requires_review_or_explicit_waiver(project, tmp_path):
    with pytest.raises(ValueError, match="Strict"):
        project.bundle(tmp_path, strict=True)
    bundle = project.bundle(tmp_path, strict=True, waiver="Internal draft; not ready to share")
    with zipfile.ZipFile(bundle) as archive:
        assert json.loads(archive.read("evidence.json"))["waiver"].startswith("Internal")


def test_project_load_does_not_restore_publication_permission(project, tmp_path):
    project.add("crop", box=(0, 0, 50, 100))
    project.review = {"privacy": "reviewed", "content": "reviewed"}
    path = tmp_path / "saved.screenshot.json"
    project.save(path)
    loaded = ScreenshotProject.load(path)
    assert loaded.operations == project.operations
    assert not loaded.review
    assert loaded.render().size == (100, 120)


def test_shared_project_cannot_open_remote_source(project, tmp_path):
    path = tmp_path / "shared.screenshot.json"
    project.save(path)
    raw = json.loads(path.read_text())
    raw["source"]["path"] = "\\\\untrusted-server\\share\\secret.png"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="local absolute"):
        ScreenshotProject.load(path)


@pytest.mark.parametrize(
    "box", [(0, 0, 101, 100), (-1, 0, 1, 1), (0, 0, 0, 100), (float("nan"), 0, 1, 1)]
)
def test_region_validation_rejects_invalid_parameters(box):
    with pytest.raises(ValueError):
        percent_box(box, (100, 100))


def test_changed_source_is_rejected_before_export(project, tmp_path):
    Path(project.evidence.path).write_bytes(b"replaced")
    with pytest.raises(ValueError, match="changed"):
        project.export(tmp_path)


def test_comparison_counts_pixel_changes_and_dimension_mismatch(project, tmp_path):
    image = Image.new("RGB", (200, 120), "white")
    image.putpixel((10, 10), (0, 0, 0))
    path = tmp_path / "other.png"
    image.save(path)
    compared = compare_screenshots(project.evidence, verify_capture(path, "Other"))
    assert compared["changed_pixels"] == 1
    assert compared["bounding_box"] == (10, 10, 11, 11)
    Image.new("RGB", (1, 1)).save(path)
    assert not compare_screenshots(project.evidence, verify_capture(path, "Other"))[
        "same_dimensions"
    ]
