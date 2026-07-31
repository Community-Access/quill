"""The standalone Quill Converter project is wired to build (#1255)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_CONVERTER = _ROOT / "standalone" / "converter"


def _load_build_portable():
    name = "quill_build_portable"
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec so the module's @dataclass can resolve its __module__.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_converter_is_a_registered_build_product() -> None:
    bp = _load_build_portable()
    assert "converter" in bp.PRODUCTS
    product = bp.PRODUCTS["converter"]
    assert product.module == "quill.apps.converter"
    assert product.exe == "QuillConverter"
    assert product.display == "Quill Converter"
    # The converter's whole job is FFmpeg conversion: stage ffmpeg, nothing else.
    assert product.stage_ffmpeg is True
    assert product.stage_engines is False
    assert product.stage_mpv is False


def test_converter_exe_in_portable_evidence_allowlist() -> None:
    # A portable QuillConverter bundle must route data to its own data/ folder.
    from quill.core import storage_mode

    src = Path(storage_mode.__file__).read_text(encoding="utf-8")
    assert "QuillConverter.exe" in src


def test_standalone_project_files_present() -> None:
    for rel in (
        "quill-converter.spec",
        "launcher.py",
        "pyproject.toml",
        "README.md",
        "run-quill-converter.bat",
        "quill_converter/__init__.py",
        "quill_converter/__main__.py",
        "assets/quill-converter.ico",
        "assets/make_quill_converter_icon.py",
    ):
        assert (_CONVERTER / rel).is_file(), rel


def test_spec_names_the_exe_and_icon() -> None:
    spec = (_CONVERTER / "quill-converter.spec").read_text(encoding="utf-8")
    assert 'name="QuillConverter"' in spec
    assert 'icon="assets/quill-converter.ico"' in spec
    assert 'collect_all("quill")' in spec


def test_launcher_hands_off_to_the_app() -> None:
    init = (_CONVERTER / "quill_converter" / "__init__.py").read_text(encoding="utf-8")
    assert "from quill.apps.converter import main" in init
    # Anchors QUILL_APP_ROOT for the frozen build (bundled ffmpeg discovery).
    assert "QUILL_APP_ROOT" in init and "tools" in init


def test_tile_icon_has_all_resolutions() -> None:
    from PIL import Image

    icon = Image.open(_CONVERTER / "assets" / "quill-converter.ico")
    sizes = set(icon.info.get("sizes", []))
    for wanted in [(16, 16), (32, 32), (48, 48), (256, 256)]:
        assert wanted in sizes, wanted
