"""QUILL Lite's portable carries everything QUILL Lite offers (2026-11-23).

The audit lives in :mod:`quill.core.lite.portable_needs`: every menu of QUILL
Lite's command table, and what no menu owns, mapped to the optional-dependency
groups and runtime tools its commands need. These tests hold the portable build
(``standalone/studio/scripts/build_portable.py``, product ``quilllite``) to that
table, and the table to the menus, the shared runtime and the staging script,
so each of these fails the build until somebody decides:

* QUILL Lite gains a menu (a feature) the table does not classify;
* the table names a group or tool the portable does not install, or the
  portable installs one the table does not ask for;
* the shared runtime gains a group or tool nobody has said whether QUILL Lite
  needs;
* the portable's copy of a tool's required files drifts from the runtime's.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import tomllib
from pathlib import Path

import pytest

from quill.core.lite import portable_needs as needs
from quill.core.lite.commands import COMMANDS

_ROOT = Path(__file__).resolve().parents[3]


def _load_build_portable():
    name = "quill_build_portable_lite_needs"
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "standalone" / "studio" / "scripts" / "build_portable.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bp = _load_build_portable()
LITE = bp.PRODUCTS["quilllite"]


def _runtime_groups() -> set[str]:
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    runtime = project["optional-dependencies"]["runtime"]
    return {re.fullmatch(r"quill\[(.+)\]", spec).group(1) for spec in runtime}


def _runtime_tools() -> list[str]:
    text = (_ROOT / "standalone" / "runtime" / "stage_runtime_tools.ps1").read_text(
        encoding="utf-8"
    )
    found = re.search(r"^\$tools = @\(([^)]*)\)", text, re.MULTILINE)
    assert found, "stage_runtime_tools.ps1 no longer lists its tools as $tools = @(...)"
    return re.findall(r'"([^"]+)"', found.group(1))


def _ps_list(text: str, variable: str) -> list[str]:
    found = re.search(rf"^\${variable} = @\(([^)]*)\)", text, re.MULTILINE)
    assert found, f"${variable} = @(...) not found"
    return re.findall(r'"([^"]+)"', found.group(1))


# -- the table covers QUILL Lite ---------------------------------------------


def test_every_menu_quill_lite_has_is_classified() -> None:
    """A new menu (a new feature) fails here until its needs are written down."""
    menus = {row[0] for row in COMMANDS}
    assert menus - set(needs.MENU_NEEDS) == set(), "classify in portable_needs.MENU_NEEDS"
    assert set(needs.MENU_NEEDS) - menus == set(), "a classified menu no longer exists"


def test_every_need_says_why() -> None:
    for name, need in {**needs.MENU_NEEDS, **needs.ALWAYS_NEEDS}.items():
        assert need.why.strip(), name


def test_every_runtime_group_is_needed_or_excluded_with_a_reason() -> None:
    runtime = _runtime_groups()
    bundled = set(needs.bundled_groups())
    excluded = set(needs.EXCLUDED_GROUPS)
    assert bundled & excluded == set()
    assert runtime - bundled - excluded == set(), "decide in portable_needs"
    # QUILL Lite's portable is never ahead of its installer: everything it
    # carries is in the shared runtime too.
    assert bundled - runtime == set()
    assert all(reason.strip() for reason in needs.EXCLUDED_GROUPS.values())


def test_every_runtime_tool_is_needed_or_excluded_with_a_reason() -> None:
    runtime = set(_runtime_tools())
    bundled = set(needs.bundled_tools())
    excluded = set(needs.EXCLUDED_TOOLS)
    assert bundled & excluded == set()
    assert runtime == bundled | excluded
    assert all(reason.strip() for reason in needs.EXCLUDED_TOOLS.values())


# -- the portable matches the table ------------------------------------------


def test_the_portable_installs_exactly_the_groups_quill_lite_needs() -> None:
    assert len(LITE.dep_groups) == len(set(LITE.dep_groups))
    assert set(LITE.dep_groups) == set(needs.bundled_groups())


def test_the_portable_carries_exactly_the_tools_quill_lite_needs() -> None:
    assert tuple(sorted(LITE.runtime_tools)) == needs.bundled_tools()
    assert set(LITE.runtime_tools) <= set(bp.RUNTIME_TOOLS)


def test_the_release_script_fetches_the_same_tools() -> None:
    text = (_ROOT / "standalone" / "quilllite" / "scripts" / "build_release.ps1").read_text(
        encoding="utf-8"
    )
    assert sorted(_ps_list(text, "portableTools")) == sorted(LITE.runtime_tools)


@pytest.mark.parametrize("group", needs.bundled_groups())
def test_every_bundled_group_is_import_checked(group: str) -> None:
    """The build imports a module from each group, so a broken group fails it."""
    if group == "ui":
        return  # step 8 always imports wx
    if group == "docx":
        assert LITE.check_word
        return
    module = needs.GROUP_IMPORTS[group]
    assert module in LITE.must_import
    assert f"import {module};" in bp.import_check_source(LITE)


def test_the_group_imports_name_modules_of_their_group() -> None:
    """Each named import belongs to a package its group installs."""
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    groups = project["optional-dependencies"]
    distributions = {
        "sherpa_onnx": "sherpa-onnx",
        "pdfplumber": "pdfplumber",
        "winrt.windows.media.ocr": "winrt-Windows.Media.Ocr",
        "docx": "python-docx",
        "enchant": "pyenchant",
        "sound_lib.output": "sound_lib",
        "winrt.windows.media.playback": "winrt-Windows.Media.Playback",
        "latex2mathml.converter": "latex2mathml",
        "soundfile": "soundfile",
        "mutagen": "mutagen",
        "github": "PyGithub",
        "copilot": "microsoft-copilot-sdk",
    }
    for group, module in needs.GROUP_IMPORTS.items():
        assert any(spec.startswith(distributions[module]) for spec in groups[group]), group


# -- the tools ----------------------------------------------------------------


def test_the_required_files_match_the_runtime_staging() -> None:
    """build_portable.RUNTIME_TOOLS is StageMediaTools.ps1's table, file for file."""
    text = (_ROOT / "scripts" / "StageMediaTools.ps1").read_text(encoding="utf-8")
    table: dict[str, tuple[str, tuple[str, ...]]] = {}
    for match in re.finditer(
        r'Name = "([^"]+)"; Copy = "([^"]+)"; Files = @\(([^)]*)\)', text, re.DOTALL
    ):
        files = tuple(f.replace("\\", "/") for f in re.findall(r'"([^"]+)"', match.group(3)))
        table[match.group(1)] = (match.group(2), files)
    assert table == bp.RUNTIME_TOOLS
    assert set(bp.RUNTIME_TOOL_PROBES) == set(bp.RUNTIME_TOOLS)


def _fake_deps(root: Path, names: tuple[str, ...]) -> Path:
    deps = root / "deps"
    for name in names:
        _mode, files = bp.RUNTIME_TOOLS[name]
        for file in files:
            path = deps / name / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name, encoding="utf-8")
    return deps


def test_staging_copies_named_files_and_whole_trees(tmp_path: Path) -> None:
    deps = _fake_deps(tmp_path, ("nodejs", "wp-playground-cli"))
    (deps / "nodejs" / "stray.txt").write_text("not shipped", encoding="utf-8")
    extra = deps / "wp-playground-cli" / "node_modules" / "other" / "index.js"
    extra.parent.mkdir(parents=True)
    extra.write_text("shipped", encoding="utf-8")
    out = tmp_path / "out"

    staged = bp.stage_runtime_tools(out, ("nodejs", "wp-playground-cli"), deps)

    assert staged == ["nodejs", "wp-playground-cli"]
    assert (out / "tools" / "nodejs" / "node.exe").is_file()
    assert not (out / "tools" / "nodejs" / "stray.txt").exists()
    tree = out / "tools" / "wp-playground-cli"
    assert (tree / ".quill-playground-pruned-v1").is_file()  # dot-named marker too
    assert (tree / "wordpress-7.1.4.zip").is_file()
    assert (tree / "node_modules" / "other" / "index.js").is_file()


def test_a_missing_tool_fails_the_build_before_copying(tmp_path: Path) -> None:
    deps = _fake_deps(tmp_path, ("nodejs",))
    out = tmp_path / "out"
    with pytest.raises(RuntimeError) as raised:
        bp.stage_runtime_tools(out, ("nodejs", "codex"), deps)
    message = str(raised.value)
    assert "codex is missing" in message
    assert "fetch_build_deps.py --only nodejs --only codex" in message
    assert not (out / "tools").exists()


def test_a_missing_required_file_fails_the_build(tmp_path: Path) -> None:
    deps = _fake_deps(tmp_path, ("codex",))
    (deps / "codex" / "CODEX-NOTICE.txt").unlink()
    with pytest.raises(RuntimeError, match="CODEX-NOTICE.txt is missing"):
        bp.stage_runtime_tools(tmp_path / "out", ("codex",), deps)


def test_an_unknown_tool_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not a runtime tool"):
        bp.stage_runtime_tools(tmp_path / "out", ("deno",), tmp_path)


def test_the_tool_probe_asks_quills_own_finders(tmp_path: Path) -> None:
    source = bp.runtime_tool_probe_source(LITE.runtime_tools)
    compile(source, "<probe>", "exec")
    for finder in (
        "find_copilot_runtime",
        "find_codex_app_server",
        "bundled_node",
        "language_servers_dir",
        "find_cli",
    ):
        assert finder in source
    assert "rg.exe" not in source  # ripgrep is not one of QUILL Lite's tools


def test_the_tool_probe_ignores_the_builders_overrides(monkeypatch) -> None:
    for name in ("QUILL_APP_ROOT", "QUILL_BUILD_DEPS_DIR", "QUILL_PLAYGROUND_CLI_DIR"):
        monkeypatch.setenv(name, os.fspath(Path.home()))
    env = bp._tool_probe_env()
    for name in ("QUILL_APP_ROOT", "QUILL_BUILD_DEPS_DIR", "QUILL_PLAYGROUND_CLI_DIR"):
        assert name not in env


def test_other_portables_carry_no_runtime_tools_yet() -> None:
    """QUILL Lite first (Jeff, 2026-11-23); the others are the next change."""
    others = {key for key, product in bp.PRODUCTS.items() if product.runtime_tools}
    assert others == {"quilllite"}


@pytest.mark.skipif(os.name != "nt", reason="the 260-character limit is Windows'")
def test_deep_tool_files_copy_past_the_path_limit(tmp_path: Path) -> None:
    """pyright's stubs sit 157 characters below tools/; the copy must not stop at 260."""
    deps = _fake_deps(tmp_path, ("language-servers",))
    deep = deps / "language-servers" / "node_modules"
    for part in ("a" * 60, "b" * 60, "c" * 60, "d" * 60):
        deep = deep / part
    long_deep = Path(bp._long_path(deep))
    long_deep.mkdir(parents=True)
    (long_deep / "stub.pyi").write_text("x", encoding="utf-8")
    out = tmp_path / "out"
    bp.stage_runtime_tools(out, ("language-servers",), deps)
    copied = Path(bp._long_path(out / "tools" / "language-servers")) / deep.relative_to(
        deps / "language-servers"
    )
    assert (copied / "stub.pyi").is_file()
    assert bp._long_path(Path(bp._long_path(tmp_path))) == bp._long_path(tmp_path)


# -- ffmpeg, for Make a Listening Version (2026-11-23) -----------------------


def test_both_downloads_carry_ffmpeg_for_the_listening_version() -> None:
    """The table, the app's declared components, the portable and the installer agree."""
    from quill.apps import lite

    assert needs.bundled_media_tools() == ("ffmpeg",)
    assert lite.REQUIRED_COMPONENTS == needs.bundled_media_tools()
    assert "ffmpeg" in needs.MENU_NEEDS["&Tools|WordPress|M&ore Media"].media
    assert LITE.stage_ffmpeg is True and LITE.stage_mpv is False
    assert bp.media_tools(LITE) == needs.bundled_media_tools()
    iss = (_ROOT / "standalone" / "quilllite" / "installer" / "quilllite.iss").read_text(
        encoding="utf-8"
    )
    assert "#define ToolFfmpeg" in iss and "#define ToolMpv" not in iss


def test_the_portable_build_proves_ffmpeg_and_ffprobe_are_found() -> None:
    source = bp.runtime_tool_probe_source(LITE.runtime_tools, bp.media_tools(LITE))
    compile(source, "<probe>", "exec")
    assert "find_ffmpeg()" in source and "find_ffprobe()" in source
    # A product with no media tools probes only its runtime tools.
    assert "find_ffmpeg" not in bp.runtime_tool_probe_source(LITE.runtime_tools)


def test_the_release_script_stages_the_pinned_ffmpeg_in_both_downloads() -> None:
    text = (_ROOT / "standalone" / "quilllite" / "scripts" / "build_release.ps1").read_text(
        encoding="utf-8"
    )
    assert 'fetch_build_deps.py") --only ffmpeg' in text
    assert "Stage-QuillMediaTools -RuntimeDist $sharedRuntimeDist -FfmpegDir $FfmpegDir" in text
    assert "--ffmpeg-dir $FfmpegDir" in text
    assert "check_ffmpeg_notices.py" in text
    # libmpv is still stripped from the communal runtime; ffmpeg no longer is.
    assert 'foreach ($tool in @("mpv"))' in text
    assert '@("ffmpeg", "mpv")' not in text
