"""Everything ships in both downloads of Quill Radio (and QUILL Lite's launcher).

Owner's rule (2026-09-27): every DLL and component ships inside BOTH the
installer and the portable zip; nothing downloads at install or first use; the
Help-menu Repair items are emergency repair only. These pin the build plumbing
that makes that true without running a real build.
"""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

from scripts import build_native_launcher as bnl

_ROOT = Path(__file__).resolve().parents[3]
_OFFLINE = ("radio", "quilllite")


def _load_build_portable():
    name = "quill_build_portable_bundle_everything"
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bp = _load_build_portable()


# -- the portable launcher never offers the shared-runtime download ----------


def test_configure_always_passes_the_runtime_url_explicitly(tmp_path: Path) -> None:
    """Left out, CMake would reuse whatever URL the cache last held."""
    product = bnl.PRODUCTS["radio"]
    installed = bnl.configure_args(
        "cmake", product, tmp_path, version="3.0.1", runtime_url=bnl.DEFAULT_RUNTIME_URL
    )
    portable = bnl.configure_args("cmake", product, tmp_path, version="3.0.1", runtime_url="")
    assert f"-DPRODUCT_RUNTIME_URL={bnl.DEFAULT_RUNTIME_URL}" in installed
    assert "-DPRODUCT_RUNTIME_URL=" in portable
    assert not any("runtime-latest" in arg for arg in portable)


def test_the_two_flavours_build_in_separate_cmake_trees(tmp_path: Path) -> None:
    product = bnl.PRODUCTS["radio"]
    installed = bnl.launcher_build_dir(product, tmp_path, runtime_url=bnl.DEFAULT_RUNTIME_URL)
    portable = bnl.launcher_build_dir(product, tmp_path, runtime_url="")
    assert installed != portable
    assert installed.name == "radio"


def test_the_default_url_matches_the_cmake_default() -> None:
    cmake = (_ROOT / "quill" / "native" / "launcher" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert bnl.DEFAULT_RUNTIME_URL in cmake


def test_main_no_runtime_download_compiles_an_empty_url(monkeypatch, tmp_path: Path) -> None:
    seen: dict = {}

    def fake_build(product, out_dir, *, runtime_url):
        seen["url"] = runtime_url

    monkeypatch.setattr(bnl, "build_launcher", fake_build)
    assert bnl.main(["--product", "radio", "--out", str(tmp_path), "--no-runtime-download"]) == 0
    assert seen["url"] == ""
    assert bnl.main(["--product", "radio", "--out", str(tmp_path)]) == 0
    assert seen["url"] == bnl.DEFAULT_RUNTIME_URL


def test_build_launcher_puts_the_url_on_the_configure_line(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(bnl, "find_cmake", lambda: "cmake")
    monkeypatch.setattr(bnl, "find_msvc", lambda: tmp_path)
    monkeypatch.setattr(bnl.subprocess, "run", lambda cmd, **_k: calls.append(list(cmd)))
    with pytest.raises(RuntimeError, match="is not in"):
        bnl.build_launcher(bnl.PRODUCTS["radio"], tmp_path, build_root=tmp_path, runtime_url="")
    assert "-DPRODUCT_RUNTIME_URL=" in calls[0]
    assert str(tmp_path / "radio-portable") in calls[0]


@pytest.mark.parametrize("key", _OFFLINE)
def test_portable_launcher_is_offline_and_the_installer_gets_its_own(key: str, tmp_path) -> None:
    product = bp.PRODUCTS[key]
    assert product.offline_portable_launcher is True
    out = tmp_path / "dist" / product.exe
    portable = bp.launcher_command(_ROOT, product, out, runtime_download=False)
    installer = bp.launcher_command(
        _ROOT, product, bp.installer_launcher_dir(out, product), runtime_download=True
    )
    assert "--no-runtime-download" in portable
    assert "--no-runtime-download" not in installer
    assert bp.installer_launcher_dir(out, product) == tmp_path / "dist" / f"{product.exe}-installer"


@pytest.mark.parametrize(
    ("key", "iss"),
    [
        ("radio", "standalone/radio/installer/quill-radio.iss"),
        ("quilllite", "standalone/quilllite/installer/quilllite.iss"),
    ],
)
def test_each_installer_copies_the_installer_launcher(key: str, iss: str) -> None:
    exe = bp.PRODUCTS[key].exe
    text = (_ROOT / iss).read_text(encoding="utf-8")
    assert f'Source: "..\\dist\\{exe}-installer\\{exe}.exe"' in text
    assert f'Source: "..\\dist\\{exe}\\{exe}.exe"' not in text


def test_the_portable_message_says_what_is_wrong() -> None:
    source = (_ROOT / "quill" / "native" / "launcher" / "launcher.c").read_text(encoding="utf-8")
    assert "PRODUCT_RUNTIME_URL[0] == '\\0'" in source
    assert "portable copy of %s is incomplete" in source


# -- yt-dlp, yt-dlp-ejs and deno ship in both downloads -----------------------


def test_radio_bundles_yt_dlp_and_deno() -> None:
    product = bp.PRODUCTS["radio"]
    assert "youtube" in product.dep_groups
    assert product.stage_deno is True


def test_the_youtube_group_carries_the_matching_challenge_solver() -> None:
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    youtube = project["optional-dependencies"]["youtube"]
    assert any(r.startswith("yt-dlp>=") for r in youtube)
    assert "yt-dlp-ejs==0.8.0" in youtube


def test_stage_deno_copies_the_exe_and_its_licence(tmp_path: Path) -> None:
    deps = tmp_path / "deno"
    deps.mkdir()
    (deps / "deno.exe").write_bytes(b"MZ")
    (deps / "DENO-LICENSE.txt").write_text("MIT", encoding="utf-8")
    out = tmp_path / "bundle"
    bp._stage_deno(out, deps)
    assert (out / "tools" / "deno" / "deno.exe").read_bytes() == b"MZ"
    assert (out / "tools" / "deno" / "DENO-LICENSE.txt").is_file()


def test_stage_deno_is_required_not_best_effort(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="--deno-dir"):
        bp._stage_deno(tmp_path / "bundle", None)
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "deno.exe").write_bytes(b"MZ")
    with pytest.raises(RuntimeError, match="licence"):
        bp._stage_deno(tmp_path / "bundle", tmp_path / "d")


def test_radio_release_stages_deno_in_the_runtime_and_the_portable() -> None:
    text = (_ROOT / "standalone/radio/scripts/build_release.ps1").read_text(encoding="utf-8")
    assert 'fetch_build_deps.py") --only deno' in text
    assert "-DenoDir $DenoDir" in text
    assert "--deno-dir $DenoDir" in text


def test_the_runtime_spec_collects_the_challenge_solver() -> None:
    spec = (_ROOT / "standalone" / "runtime" / "quillville-runtime.spec").read_text(
        encoding="utf-8"
    )
    assert 'collect_all("yt_dlp_ejs")' in spec


# -- OptiLab is required in a Radio release -----------------------------------


def test_radio_release_fails_without_the_optilab_adapter() -> None:
    text = (_ROOT / "standalone/radio/scripts/build_release.ps1").read_text(encoding="utf-8")
    assert 'build_native_optilab.py") --out $appDir --require' in text
    assert "No OptiLab adapter in this build" not in text
    assert 'throw "No quill-optilab.exe was built.' in text
