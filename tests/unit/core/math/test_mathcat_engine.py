"""ctypes binding to the optional MathCAT engine pack.

Most of this suite runs regardless of whether the engine pack is installed
(the unavailable-degradation path); the handful of tests that need real
MathCAT output are skipped unless a real engine pack is present at the
actual app-data location (i.e. the user has downloaded it through the app),
matching the existing pandoc/latex2mathml gating convention in this repo.
"""

from __future__ import annotations

import pytest

from quill.core.math import mathcat_engine


def _real_engine_available() -> bool:
    return mathcat_engine.is_available()


def test_is_available_false_when_pack_missing(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mathcat_engine, "pack_dir", lambda: tmp_path / "nowhere")
    assert mathcat_engine.is_available() is False


def test_is_available_false_when_dll_present_but_no_rules(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = tmp_path / "mathcat"
    pack.mkdir()
    (pack / "libmathcat_c.dll").write_bytes(b"not a real dll")
    monkeypatch.setattr(mathcat_engine, "pack_dir", lambda: pack)
    assert mathcat_engine.is_available() is False


def test_is_available_true_when_both_present(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    pack = tmp_path / "mathcat"
    (pack / "Rules").mkdir(parents=True)
    (pack / "libmathcat_c.dll").write_bytes(b"not a real dll")
    monkeypatch.setattr(mathcat_engine, "pack_dir", lambda: pack)
    assert mathcat_engine.is_available() is True


def test_load_raises_unavailable_when_pack_missing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mathcat_engine, "pack_dir", lambda: tmp_path / "nowhere")
    monkeypatch.setattr(mathcat_engine, "_dll", None)
    with pytest.raises(mathcat_engine.MathCatUnavailable):
        mathcat_engine._load()


def test_mathml_to_speech_raises_unavailable_when_pack_missing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mathcat_engine, "pack_dir", lambda: tmp_path / "nowhere")
    monkeypatch.setattr(mathcat_engine, "_dll", None)
    with pytest.raises(mathcat_engine.MathCatUnavailable):
        mathcat_engine.mathml_to_speech("<math><mi>x</mi></math>")


@pytest.mark.skipif(not _real_engine_available(), reason="MathCAT engine pack not installed")
def test_real_engine_reports_a_version() -> None:
    version = mathcat_engine.get_version()
    assert version
    assert "." in version


@pytest.mark.skipif(not _real_engine_available(), reason="MathCAT engine pack not installed")
def test_real_engine_speaks_pythagorean_theorem() -> None:
    mathml = (
        '<math xmlns="http://www.w3.org/1998/Math/MathML">'
        "<mrow><msup><mi>a</mi><mn>2</mn></msup><mo>+</mo>"
        "<msup><mi>b</mi><mn>2</mn></msup><mo>=</mo>"
        "<msup><mi>c</mi><mn>2</mn></msup></mrow></math>"
    )
    speech = mathcat_engine.mathml_to_speech(mathml)
    assert "squared" in speech
