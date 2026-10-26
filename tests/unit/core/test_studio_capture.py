"""Evidence must reject corruption and replacement without overstating success."""

import hashlib
import json

import pytest
from PIL import Image, UnidentifiedImageError

from quill.core.studio_capture import save_capture_report, verify_capture


def test_decode_and_report_are_grounded_in_saved_bytes(tmp_path):
    path = tmp_path / "capture.png"
    Image.new("RGB", (83, 41), "black").save(path)
    evidence = verify_capture(path, "active_window")
    assert (evidence.width, evidence.height) == (83, 41)
    assert evidence.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    report = json.loads(save_capture_report(evidence).read_text())
    assert report["schema_version"] == 1
    assert "privacy" in report["not_verified"]
    assert "wrong window" in evidence.summary()
    assert "full_image_decode" in report["verified"]


@pytest.mark.parametrize("data", [b"", b"not an image", b"\x89PNG\r\n\x1a\n"])
def test_empty_and_corrupt_files_cannot_pass(tmp_path, data):
    path = tmp_path / "capture.png"
    path.write_bytes(data)
    with pytest.raises((UnidentifiedImageError, OSError)):
        verify_capture(path, "screen")


def test_replaced_image_cannot_be_reported_as_original(tmp_path):
    path = tmp_path / "capture.png"
    Image.new("RGB", (10, 10), "white").save(path)
    evidence = verify_capture(path, "screen")
    Image.new("RGB", (10, 10), "red").save(path)
    with pytest.raises(ValueError, match="changed"):
        save_capture_report(evidence, observations="Looks correct")
    assert not path.with_suffix(".verification.json").exists()


def test_ai_observations_never_become_verified_checks(tmp_path):
    path = tmp_path / "capture.png"
    Image.new("RGB", (10, 10)).save(path)
    evidence = verify_capture(path, "screen")
    report = json.loads(
        save_capture_report(evidence, observations="Everything is safe").read_text()
    )
    assert report["observations_unverified"] == "Everything is safe"
    assert "Everything is safe" not in report["verified"]
