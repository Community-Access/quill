"""The portable build's import check must not dirty its package inventory."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_BUILDER_PATH = _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
_SPEC = importlib.util.spec_from_file_location("quill_build_portable_runtime_check", _BUILDER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_BUILDER = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _BUILDER
_SPEC.loader.exec_module(_BUILDER)


def test_sanity_import_disables_bytecode_writes() -> None:
    product = _BUILDER.PRODUCTS["quilllite"]
    python_exe = Path("bundle") / "python.exe"

    assert _BUILDER.import_check_command(python_exe, product) == [
        str(python_exe),
        "-B",
        "-c",
        _BUILDER.import_check_source(product),
    ]


def test_engine_staging_excludes_dectalk(tmp_path: Path) -> None:
    source = tmp_path / "source" / "speech"
    (source / "DECtalk").mkdir(parents=True)
    (source / "DECtalk" / "DECtalk.dll").write_bytes(b"test")
    (source / "piper").mkdir()
    (source / "piper" / "piper.exe").write_bytes(b"test")
    output = tmp_path / "output"
    output.mkdir()

    _BUILDER._stage_engines(output, tmp_path / "source")

    assert not (output / "data" / "speech" / "DECtalk").exists()
    assert (output / "data" / "speech" / "piper" / "piper.exe").is_file()


def test_engine_staging_only_copies_supported_speech_directories(tmp_path: Path) -> None:
    source = tmp_path / "source" / "speech"
    for engine, executable in (
        ("piper", "piper.exe"),
        ("espeak-ng", "espeak-ng.exe"),
        ("unrecognized", "engine.exe"),
    ):
        (source / engine).mkdir(parents=True)
        (source / engine / executable).write_bytes(b"test")
    (source / "personal-data.txt").write_text("private", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()

    staged = _BUILDER._stage_engines(output, tmp_path / "source")

    assert set(staged) == {"speech/piper", "speech/espeak-ng"}
    assert (output / "data" / "speech" / "piper" / "piper.exe").is_file()
    assert (output / "data" / "speech" / "espeak-ng" / "espeak-ng.exe").is_file()
    assert not (output / "data" / "speech" / "unrecognized").exists()
    assert not (output / "data" / "speech" / "personal-data.txt").exists()
