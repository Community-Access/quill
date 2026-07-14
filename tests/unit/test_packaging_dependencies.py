"""Packaging-dependency invariants.

These guard a class of "green tests, broken build" bugs where a package that a
*default* feature needs at runtime is declared only in an optional extra (or the
dev extra). Dev and CI install those extras, so import-based tests pass -- but the
shipped runtime, which installs only the base dependencies, is missing the package
and the feature fails at first use. See the beta-2 speech-engine fixes:

- huggingface_hub: the default whisper.cpp speech-to-text engine downloads its
  GGML models via huggingface_hub.hf_hub_download, so it must be a base dep.
- Babel: the Kokoro ONNX voice chain (kokoro-onnx -> phonemizer -> segments ->
  csvw -> babel.numbers) needs it; it must ride with the [kokoro] extra, not only
  [dev].
"""

from __future__ import annotations

import pathlib
import tomllib

import pytest

_PYPROJECT = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"


@pytest.fixture(scope="module")
def project() -> dict:
    return tomllib.loads(_PYPROJECT.read_text("utf-8"))["project"]


def _names(requirements: list[str]) -> set[str]:
    """Distribution names from PEP 508 requirement strings, lowercased.

    Normalizes '-'/'_' so 'huggingface_hub' and 'huggingface-hub' compare equal.
    """
    out: set[str] = set()
    for req in requirements:
        head = req.split(";", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", ">", "<", "!=", "[", " "):
            head = head.split(sep, 1)[0]
        out.add(head.strip().lower().replace("_", "-"))
    return out


def test_huggingface_hub_is_a_base_runtime_dependency(project: dict) -> None:
    """The default whisper.cpp downloader needs huggingface_hub on a clean install.

    It must be in [project].dependencies -- not only the optional [fasterwhisper]
    extra -- so speech-to-text model downloads work without opting into Faster
    Whisper. Regression guard for QUILL-SPEECH-PROVIDER-FAILED "needs the
    'huggingface_hub' package" on a fresh install.
    """
    assert "huggingface-hub" in _names(project["dependencies"])


def test_babel_rides_with_the_kokoro_extra(project: dict) -> None:
    """The Kokoro ONNX voice chain imports babel.numbers transitively via csvw.

    Declaring Babel in the [kokoro] extra keeps that runtime chain self-contained
    so a pruned/partial install can't leave the ONNX voice path failing with
    ModuleNotFoundError: No module named 'babel'.
    """
    assert "babel" in _names(project["optional-dependencies"]["kokoro"])


@pytest.mark.parametrize("dist", ["markitdown", "pdfplumber", "pypdf"])
def test_free_import_pipeline_is_a_base_runtime_dependency(project: dict, dist: str) -> None:
    """The free-first import pipeline must be built-in on every install (#909).

    The product advertises MarkItDown as the built-in "free local converter" and
    PDF text extraction as always-available (`quill/io/docconvert.py`,
    `quill/io/pdf.py`), but they used to live only in the [pages] extra / nowhere,
    so a clean `pip install quill[ui]` (and the shipping Windows build, which does
    not bundle [pages]) had NO PDF/Office text extractor and Import → PDF/OCR
    failed out of the box. They must be in [project].dependencies so the promise
    and the manifest agree.
    """
    assert dist in _names(project["dependencies"])


def test_free_import_pipeline_imports_under_the_shipping_set() -> None:
    """Beyond the manifest, the packages must actually import in the test env.

    Complements the manifest check above: catches the case where a dependency is
    declared but broken/uninstallable on this platform. Skips (rather than fails)
    if the environment genuinely lacks them, so the manifest test stays the hard
    guard while this one confirms real availability where present.
    """
    import importlib.util

    names = ("markitdown", "pdfplumber", "pypdf")
    missing = [m for m in names if importlib.util.find_spec(m) is None]
    if missing:
        pytest.skip(f"not installed in this environment: {', '.join(missing)}")
    import markitdown  # noqa: F401
    import pdfplumber  # noqa: F401
    import pypdf  # noqa: F401
