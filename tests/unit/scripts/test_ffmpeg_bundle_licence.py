"""No bundle ships ffmpeg.exe without FFmpeg's licence beside it (no network).

The pinned FFmpeg is a GPLv3 build (``--enable-gpl --enable-version3``). Its
licence and source offer live once in ``quill/data/notices/ffmpeg``. These tests
hold every way an ffmpeg.exe reaches a user to that: the build-dependency cache
(``fetch_build_deps.py``), the bundle check every media app's build runs
(``check_ffmpeg_notices.py``), the build scripts that call it, Quill Cast's
onedir (which guessed at a path and shipped neither until 2026-10-15), and the
installers, which name the notices one by one so ISCC refuses to compile
without them.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import zipfile
from pathlib import Path

import pytest

from quill.core.speech.ffmpeg_install import FFMPEG_NOTICE_FILES

_REPO_ROOT = Path(__file__).resolve().parents[3]
_NOTICES = _REPO_ROOT / "quill" / "data" / "notices" / "ffmpeg"


def _load(name: str):
    path = _REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def check():
    return _load("check_ffmpeg_notices")


@pytest.fixture(scope="module")
def fbd():
    return _load("fetch_build_deps")


def _bundle_with_ffmpeg(root: Path, *, notices: bool) -> Path:
    tools = root / "tools" / "ffmpeg"
    tools.mkdir(parents=True)
    (tools / "ffmpeg.exe").write_bytes(b"MZ fake")
    if notices:
        for name in FFMPEG_NOTICE_FILES:
            (tools / name).write_bytes((_NOTICES / name).read_bytes())
    return tools


# -- the bundle check ---------------------------------------------------------


def test_the_check_fails_a_bundle_that_ships_ffmpeg_without_its_licence(check, tmp_path) -> None:
    _bundle_with_ffmpeg(tmp_path, notices=False)
    problems = check.problems_in(tmp_path)
    assert len(problems) == len(FFMPEG_NOTICE_FILES)
    assert all("without" in line for line in problems)
    assert check.main([str(tmp_path)]) == 1


def test_the_check_passes_a_bundle_that_carries_both_notices(check, tmp_path) -> None:
    _bundle_with_ffmpeg(tmp_path, notices=True)
    assert check.problems_in(tmp_path) == []
    assert check.main([str(tmp_path)]) == 0


def test_the_check_catches_a_stale_source_offer(check, tmp_path) -> None:
    tools = _bundle_with_ffmpeg(tmp_path, notices=True)
    (tools / "README-SOURCE.txt").write_text("FFmpeg 7.0 from somewhere else", encoding="utf-8")
    problems = check.problems_in(tmp_path)
    assert len(problems) == 1 and "README-SOURCE.txt" in problems[0]


def test_a_bundle_with_no_ffmpeg_needs_no_notices(check, tmp_path) -> None:
    (tmp_path / "QuillWeather.exe").write_bytes(b"MZ")
    assert check.problems_in(tmp_path) == []


def test_every_ffmpeg_in_a_bundle_is_checked_not_only_the_first(check, tmp_path) -> None:
    _bundle_with_ffmpeg(tmp_path / "portable", notices=True)
    _bundle_with_ffmpeg(tmp_path / "runtime", notices=False)
    assert len(check.problems_in(tmp_path)) == len(FFMPEG_NOTICE_FILES)


def test_a_missing_folder_is_a_failure_not_a_pass(check, tmp_path) -> None:
    assert check.main([str(tmp_path / "never-built")]) == 1


# -- the build-dependency cache ------------------------------------------------


def _fake_ffmpeg_zip(dest: Path) -> None:
    with zipfile.ZipFile(dest, "w") as zf:
        zf.writestr("ffmpeg-8.1.2-essentials_build/bin/ffmpeg.exe", b"MZ ffmpeg")
        zf.writestr("ffmpeg-8.1.2-essentials_build/bin/ffprobe.exe", b"MZ ffprobe")


def test_fetch_ffmpeg_stages_the_licence_beside_the_binaries(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    calls: list[str] = []

    def fake_download(url, dest, *, sha256="", progress=None, **_kw):
        calls.append(url)
        _fake_ffmpeg_zip(Path(dest))
        return dest

    monkeypatch.setattr(fbd, "download_verified", fake_download)
    out = fbd.fetch_ffmpeg()
    assert (out / "ffmpeg.exe").is_file() and (out / "ffprobe.exe").is_file()
    for name in FFMPEG_NOTICE_FILES:
        assert (out / name).read_bytes() == (_NOTICES / name).read_bytes()
    assert len(calls) == 1, "the notices come from the package, not a second download"
    assert fbd.is_complete("ffmpeg")


def test_a_cache_staged_before_the_notices_is_completed_without_a_download(
    fbd, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    old = fbd.component_dir("ffmpeg")
    old.mkdir(parents=True)
    (old / "ffmpeg.exe").write_bytes(b"MZ")
    assert fbd.is_staged("ffmpeg") and not fbd.is_complete("ffmpeg")

    def no_download(*_a, **_kw):
        raise AssertionError("must not download")

    monkeypatch.setattr(fbd, "download_verified", no_download)
    fbd.fetch_ffmpeg()
    assert fbd.is_complete("ffmpeg")


def test_verify_only_reports_ffmpeg_without_its_licence_as_missing(
    fbd, tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    old = fbd.component_dir("ffmpeg")
    old.mkdir(parents=True)
    (old / "ffmpeg.exe").write_bytes(b"MZ")
    assert fbd.main(["--verify-only", "--only", "ffmpeg"]) == 1
    assert "ffmpeg: MISSING" in capsys.readouterr().out


# -- the build scripts and installers -------------------------------------------

_MEDIA_BUILDS = ("cast", "converter", "radio", "studio")


def _ships_ffmpeg(script: str) -> bool:
    return bool(
        re.search(r"-FfmpegDir \$FfmpegDir|--ffmpeg-dir|ffmpeg\.exe\"\) \$toolsDir", script)
    )


def test_every_app_build_that_ships_ffmpeg_runs_the_check() -> None:
    builds = sorted((_REPO_ROOT / "standalone").glob("*/scripts/build_release.ps1"))
    shipping = [p for p in builds if _ships_ffmpeg(p.read_text(encoding="utf-8"))]
    assert {p.parts[-3] for p in shipping} == set(_MEDIA_BUILDS), (
        "a build started or stopped shipping ffmpeg; update this list and make "
        "sure it runs scripts\\check_ffmpeg_notices.py"
    )
    for path in shipping:
        text = path.read_text(encoding="utf-8")
        assert "check_ffmpeg_notices.py" in text, (
            f"{path} ships ffmpeg without checking its licence"
        )
        assert text.index("check_ffmpeg_notices.py") < text.index("Compress-Archive"), path


def test_casts_onedir_stages_the_package_notices_not_a_guess() -> None:
    text = (_REPO_ROOT / "standalone/cast/scripts/build_release.ps1").read_text(encoding="utf-8")
    assert r"quill\data\notices\ffmpeg" in text
    assert "FFMPEG-LICENSE.txt" not in text


def test_the_runtime_staging_and_the_portables_use_the_package_notices() -> None:
    stage = (_REPO_ROOT / "scripts/StageMediaTools.ps1").read_text(encoding="utf-8")
    portable = (_REPO_ROOT / "standalone/studio/scripts/build_portable.py").read_text(
        encoding="utf-8"
    )
    assert r"quill\data\notices\ffmpeg" in stage
    assert '"notices" / "ffmpeg"' in portable


@pytest.mark.parametrize(
    ("iss", "prefix"),
    [
        ("installer/shared-runtime.iss", r"{#RuntimeSourceDir}\tools\ffmpeg"),
        ("standalone/cast/installer/quill-cast.iss", r"..\dist\QUILLCast\tools\ffmpeg"),
    ],
)
def test_each_installer_names_the_notices_so_iscc_refuses_without_them(iss, prefix) -> None:
    text = (_REPO_ROOT / iss).read_text(encoding="utf-8")
    for name in FFMPEG_NOTICE_FILES:
        line = next(
            (ln for ln in text.splitlines() if f'Source: "{prefix}\\{name}"' in ln),
            None,
        )
        assert line is not None, f"{iss} does not list {name}"
        assert "skipifsourcedoesntexist" not in line


def test_the_third_party_notices_list_ffmpeg_and_its_licence() -> None:
    from quill.core.speech.ffmpeg_install import FFMPEG_PINNED_VERSION

    for rel in ("docs/legal/THIRD_PARTY_NOTICES.md", "docs/legal/THIRD_PARTY_NOTICES.txt"):
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "FFmpeg" in text, rel
        assert "GPL-3.0-or-later" in text, rel
        assert FFMPEG_PINNED_VERSION in text, rel
