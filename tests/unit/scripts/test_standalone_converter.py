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


def test_the_portable_radio_bundles_yt_dlp_like_its_installer() -> None:
    """Otherwise the first YouTube link in a portable copy runs pip, whose cache
    lands in the host's %LOCALAPPDATA%. The inventory gate must expect it too."""
    import json

    bp = _load_build_portable()
    assert "youtube" in bp.PRODUCTS["radio"].dep_groups
    inventory = json.loads(
        (_ROOT / "standalone" / "radio" / "portable-inventory.json").read_text(encoding="utf-8")
    )
    assert {"yt_dlp", "yt-dlp", "curl_cffi", "curl-cffi"} <= set(inventory["site-packages"])


def test_pywin32_makepy_cache_stays_in_the_bundle(tmp_path: Path) -> None:
    """With no win32com\gen_py package, pywin32 writes generated wrappers to
    %TEMP%\gen_py on the host and never removes them."""
    bp = _load_build_portable()
    win32com = tmp_path / "Lib" / "site-packages" / "win32com"
    win32com.mkdir(parents=True)

    bp._keep_makepy_cache_in_bundle(tmp_path)

    assert (win32com / "gen_py" / "__init__.py").is_file()


def test_no_win32com_means_no_gen_py(tmp_path: Path) -> None:
    bp = _load_build_portable()
    bp._keep_makepy_cache_in_bundle(tmp_path)
    assert not (tmp_path / "Lib").exists()


# -- the two-download release process (2026-09-26) ----------------------------
#
# Converter shipped only a portable zip until 2026-09-26; it now publishes the
# same two downloads as Quill Radio 3.0.0 and QUILL Lite. The installer's
# accessibility (native checkboxes, no [Tasks], no postinstall) is covered for
# every family installer by test_installer_accessible_checkboxes.py, and its
# runtime/ffmpeg wiring by tests/unit/structure/test_shared_runtime_installer.py.

_ISS = _CONVERTER / "installer" / "quill-converter.iss"
_BUILD = _CONVERTER / "scripts" / "build_release.ps1"


def _version() -> str:
    import re

    source = (_ROOT / "quill" / "apps" / "converter.py").read_text(encoding="utf-8")
    match = re.search(r'^_VERSION\s*=\s*"([^"]+)"', source, re.M)
    assert match
    return match.group(1)


def test_release_scripts_exist() -> None:
    for path in (_ISS, _BUILD, _CONVERTER / "scripts" / "render_docs.ps1"):
        assert path.is_file(), path


def test_build_produces_exactly_the_two_downloads() -> None:
    import re

    script = _BUILD.read_text(encoding="utf-8")
    iss = _ISS.read_text(encoding="utf-8")
    assert "Quill-Converter-Portable-$version.zip" in script
    assert "OutputBaseFilename=Quill-Converter-Setup-Shared-{#AppVersion}" in iss
    assert "installer\\quill-converter.iss" in script
    # Only one installer, and no Companion or thin-installer artifact.
    assert sorted(p.name for p in (_CONVERTER / "installer").glob("*.iss")) == [
        "quill-converter.iss"
    ]
    assert "Companion-" not in script and "Lite-Setup" not in script
    assert "--no-runtime" not in script and "--companion" not in script
    zips = set(re.findall(r"Quill-Converter-[A-Za-z-]+-\$version\.zip", script))
    assert zips == {"Quill-Converter-Portable-$version.zip"}
    # The zip name agrees with the portable builder's.
    product = _load_build_portable().PRODUCTS["converter"]
    assert product.zip_name == "Quill-Converter-Portable-{ver}.zip"


def test_build_signs_and_carries_no_token() -> None:
    script = _BUILD.read_text(encoding="utf-8")
    param_block = script.split("param(", 1)[1].split(")", 1)[0]
    assert "[switch]$Sign" in param_block
    for gone in ("TokenFile", "SkipToken", "Token"):
        assert gone not in param_block, gone
    assert "generate_feedback_token" not in script
    assert "Resolve-QuillTokenFile" not in script
    assert "code_signing.py" in script and "sign-build" in script
    assert '"/DSign"' in script
    iss = _ISS.read_text(encoding="utf-8")
    assert "#ifdef Sign" in iss and "SignTool=quilltrusted" in iss


def test_build_stages_ffmpeg_not_mpv() -> None:
    script = _BUILD.read_text(encoding="utf-8")
    assert "--product converter" in script
    assert "--ffmpeg-dir" in script
    assert "--mpv-dir" not in script and "LibmpvDir" not in script
    assert (
        'Assert-QuillRuntimeHasModule -RuntimeDir $sharedRuntimeDist -Module "quill.apps.converter"'
        in script
    )
    assert "Resolve-QuillIscc" in script


def test_versions_agree_with_the_app() -> None:
    import re

    version = _version()
    script = _BUILD.read_text(encoding="utf-8")
    assert re.search(rf'^\$version = "{re.escape(version)}"', script, re.M)
    iss = _ISS.read_text(encoding="utf-8")
    assert f'#define AppVersion "{version}"' in iss
    assert f"VersionInfoVersion={version}.0" in iss


def test_installer_has_its_own_app_id_and_ref() -> None:
    import re

    iss = _ISS.read_text(encoding="utf-8")
    app_id = re.search(r"^AppId=\{\{([0-9A-F-]{36})\}\}", iss, re.M)
    assert app_id
    others = [
        p
        for p in _ROOT.glob("standalone/*/installer/*.iss")
        if p != _ISS and app_id.group(1).lower() in p.read_text(encoding="utf-8").lower()
    ]
    assert not others, f"AppId reused by {others}"
    assert '#define AppRefId "converter"' in iss
    assert "{app}\\QuillConverter.exe" in iss


def test_installer_writes_no_registry_the_app_does_not_expect() -> None:
    """The Convert with Quill verb is QUILL's (installer/quill.iss), not this app's."""
    iss = _ISS.read_text(encoding="utf-8")
    assert "[Registry]" not in iss


def test_the_icon_generator_draws_the_converter() -> None:
    source = (_ROOT / "scripts" / "build_app_icons.py").read_text(encoding="utf-8")
    assert '"converter": _converter' in source
    assert "standalone/converter/assets/quill-converter.ico" in source
