"""Layout checks for the build-dependency staging cache (no network).

``fetch_build_deps`` used to map components with a two-way ternary, so any name
that was not ``ffmpeg`` silently resolved to the libmpv directory. It is a dict
now, and these tests keep the dict and the advertised component list in step --
a component that is offered on the command line but has no layout entry would
otherwise fail with a bare ``KeyError`` partway through a build.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module():
    path = _REPO_ROOT / "scripts" / "fetch_build_deps.py"
    spec = importlib.util.spec_from_file_location("fetch_build_deps", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["fetch_build_deps"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fbd():
    return _load_module()


def test_every_component_has_a_layout_entry(fbd) -> None:
    for component in fbd.COMPONENTS:
        assert component in fbd._LAYOUT, component
        subdir, sentinel = fbd._LAYOUT[component]
        assert subdir and sentinel


def test_no_orphan_layout_entries(fbd) -> None:
    assert set(fbd._LAYOUT) == set(fbd.COMPONENTS)


def test_components_stage_into_distinct_directories(fbd) -> None:
    dirs = [fbd.component_dir(c) for c in fbd.COMPONENTS]
    assert len(set(dirs)) == len(dirs)


def test_piper_is_offered_and_staged_under_its_own_dir(fbd) -> None:
    # gen_voice_previews.py's documented invocation points at this exact path.
    assert "piper" in fbd.COMPONENTS
    assert fbd.component_dir("piper").name == "piper"
    assert fbd._sentinel("piper") == "piper.exe"


def test_deps_root_honours_the_env_override(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path))
    assert fbd.deps_root() == tmp_path
    assert fbd.component_dir("piper") == tmp_path / "piper"


def test_is_staged_is_false_for_an_empty_cache(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path))
    for component in fbd.COMPONENTS:
        assert fbd.is_staged(component) is False


def test_deno_is_offered_pinned_and_official(fbd) -> None:
    """YouTube's challenge solver ships bundled; its pin is exact and official."""
    import re

    assert "deno" in fbd.COMPONENTS
    assert fbd.component_dir("deno").name == "deno"
    assert fbd._sentinel("deno") == "deno.exe"
    assert fbd.DENO_URL.startswith("https://github.com/denoland/deno/releases/download/v")
    assert f"/v{fbd.DENO_VERSION}/" in fbd.DENO_URL
    assert fbd.DENO_URL.endswith("deno-x86_64-pc-windows-msvc.zip")
    assert re.fullmatch(r"[0-9a-f]{64}", fbd.DENO_SHA256)
    assert re.fullmatch(r"[0-9a-f]{64}", fbd.DENO_LICENSE_SHA256)
    assert f"/v{fbd.DENO_VERSION}/" in fbd.DENO_LICENSE_URL


def test_fetch_deno_extracts_only_deno_exe_and_the_licence(fbd, tmp_path, monkeypatch) -> None:
    import zipfile

    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    calls: list[tuple[str, str]] = []

    def fake_download(url, dest, *, sha256="", progress=None, **_kw):
        calls.append((url, sha256))
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if url == fbd.DENO_URL:
            with zipfile.ZipFile(dest, "w") as zf:
                zf.writestr("deno.exe", b"MZ fake")
        else:
            dest.write_text("MIT License", encoding="utf-8")
        return dest

    monkeypatch.setattr(fbd, "download_verified", fake_download)
    out = fbd.fetch_deno()
    assert (out / "deno.exe").read_bytes() == b"MZ fake"
    assert (out / fbd.DENO_LICENSE_NAME).is_file()
    assert calls == [
        (fbd.DENO_URL, fbd.DENO_SHA256),
        (fbd.DENO_LICENSE_URL, fbd.DENO_LICENSE_SHA256),
    ]
    # Staged: a second call downloads nothing.
    calls.clear()
    fbd.fetch_deno()
    assert calls == []


def test_fetch_deno_refuses_an_unexpected_archive(fbd, tmp_path, monkeypatch) -> None:
    import zipfile

    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))

    def fake_download(url, dest, *, sha256="", progress=None, **_kw):
        with zipfile.ZipFile(dest, "w") as zf:
            zf.writestr("deno.exe", b"x")
            zf.writestr("extra.dll", b"y")
        return dest

    monkeypatch.setattr(fbd, "download_verified", fake_download)
    with pytest.raises(fbd.ReleaseAssetError):
        fbd.fetch_deno()
    assert not (fbd.component_dir("deno") / "deno.exe").exists()


# -- the AI engines: copilot and codex ------------------------------------------


@pytest.mark.parametrize("component", ["copilot", "codex"])
def test_ai_engines_are_offered_pinned_and_official(fbd, component) -> None:
    import re

    assert component in fbd.COMPONENTS
    assert fbd.component_dir(component).name == component
    if component == "copilot":
        assert fbd._sentinel("copilot") == "copilot.exe"
        assert fbd.COPILOT_URL.startswith(
            "https://github.com/github/copilot-cli/releases/download/v"
        )
        from quill.core.ai import copilot_runtime

        assert f"/v{fbd.COPILOT_VERSION}/" in fbd.COPILOT_URL
        # The unified runtime package the SDK downloads, not the legacy SEA zip.
        assert fbd.COPILOT_URL.endswith(
            f"/github-copilot-{copilot_runtime.COPILOT_CLI_VERSION}-win32-x64.tgz"
        )
        assert not hasattr(fbd, "COPILOT_LICENSE_URL"), "the licence comes from the package"
        # One pin per bundle file, shared with the launch-time check.
        assert fbd.COPILOT_WRAPPER_SHA256 == copilot_runtime.COPILOT_WRAPPER_SHA256
        assert fbd.COPILOT_RUNTIME_NODE_SHA256 == copilot_runtime.COPILOT_RUNTIME_NODE_SHA256
        assert fbd.COPILOT_ASSETS_MARKER == copilot_runtime.COPILOT_ASSETS_MARKER
        hashes = (
            fbd.COPILOT_SHA256,
            fbd.COPILOT_WRAPPER_SHA256,
            fbd.COPILOT_RUNTIME_NODE_SHA256,
            fbd.COPILOT_LICENSE_SHA256,
        )
    else:
        from quill.core.ai import codex_binary

        assert fbd._sentinel("codex") == "codex-app-server.exe"
        assert fbd.CODEX_URL.startswith("https://github.com/openai/codex/releases/download/rust-v")
        assert f"/rust-v{codex_binary.CODEX_VERSION}/" in fbd.CODEX_URL
        assert fbd.CODEX_URL.endswith(".exe.zip"), "the zipped asset, not the bare exe"
        for url in (fbd.CODEX_LICENSE_URL, fbd.CODEX_NOTICE_URL):
            assert f"/rust-v{codex_binary.CODEX_VERSION}/" in url
        # One pin for the unpacked exe, shared with the launch-time check.
        assert fbd.CODEX_APP_SERVER_SHA256 == codex_binary.CODEX_APP_SERVER_SHA256
        hashes = (
            fbd.CODEX_SHA256,
            fbd.CODEX_APP_SERVER_SHA256,
            fbd.CODEX_LICENSE_SHA256,
            fbd.CODEX_NOTICE_SHA256,
        )
    for value in hashes:
        assert re.fullmatch(r"[0-9a-f]{64}", value)


def _fake_engine_download(fbd, monkeypatch, *, member: str, exe: bytes, extra: bool = False):
    import zipfile

    calls: list[tuple[str, str]] = []

    def fake_download(url, dest, *, sha256="", progress=None, **_kw):
        calls.append((url, sha256))
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".zip"):
            with zipfile.ZipFile(dest, "w") as zf:
                zf.writestr(member, exe)
                if extra:
                    zf.writestr("extra.dll", b"y")
        else:
            dest.write_text("licence", encoding="utf-8")
        return dest

    monkeypatch.setattr(fbd, "download_verified", fake_download)
    return calls


#: A miniature of the real package: every rule of the SDK's filter has a member
#: that it drops, and every kind of kept entry has one that survives.
_COPILOT_PACKAGE = {
    "package/LICENSE.md": b"GitHub Copilot CLI License",
    "package/package.json": b"{}",
    "package/index.js": b"// SEA host",
    "package/copilot.exe": b"MZ legacy sea",
    "package/assets/a.txt": b"x",
    "package/webview/w.js": b"x",
    "package/tree-sitter-go.wasm": b"x",
    "package/voice-server.js": b"x",
    "package/schemas/api.schema.json": b"{}",
    "package/definitions/sidekick/task.yaml": b"x",
    "package/ripgrep/bin/win32-x64/rg.exe": b"MZ rg",
    "package/plugins/computer-use/mediaremote-adapter/x.dylib": b"x",
    "package/prebuilds/win32-x64/copilot-runtime.exe": b"MZ wrapper",
    "package/prebuilds/win32-x64/runtime.node": b"MZ runtime",
    "package/prebuilds/win32-x64/cli-native.node": b"MZ sea native",
    "package/prebuilds/win32-x64/copilot-runtime-bin.exe": b"x",
    "package/prebuilds/win32-x64/OneAuthInterop.LICENSE.txt": b"MS licence",
    "package/prebuilds/linux-x64/runtime.node": b"ELF",
}


def _copilot_tgz(path: Path, members: dict[str, bytes]) -> None:
    import io
    import tarfile

    with tarfile.open(path, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def _fake_copilot_download(fbd, monkeypatch, members: dict[str, bytes] | None = None):
    import hashlib

    package = dict(_COPILOT_PACKAGE if members is None else members)
    monkeypatch.setattr(fbd, "COPILOT_WRAPPER_SHA256", hashlib.sha256(b"MZ wrapper").hexdigest())
    monkeypatch.setattr(
        fbd, "COPILOT_RUNTIME_NODE_SHA256", hashlib.sha256(b"MZ runtime").hexdigest()
    )
    monkeypatch.setattr(
        fbd, "COPILOT_LICENSE_SHA256", hashlib.sha256(b"GitHub Copilot CLI License").hexdigest()
    )
    calls: list[tuple[str, str]] = []

    def fake_download(url, dest, *, sha256="", progress=None, **_kw):
        calls.append((url, sha256))
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        _copilot_tgz(Path(dest), package)
        return dest

    monkeypatch.setattr(fbd, "download_verified", fake_download)
    return calls


def _tree(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def test_fetch_copilot_materialises_the_sdk_hostless_bundle(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    calls = _fake_copilot_download(fbd, monkeypatch)
    out = fbd.fetch_copilot()
    assert calls == [(fbd.COPILOT_URL, fbd.COPILOT_SHA256)]
    assert _tree(out) == [
        ".hostless-runtime-assets-v2",
        "COPILOT-CLI-LICENSE.txt",
        "OneAuthInterop.LICENSE.txt",
        "copilot-runtime.exe",
        "copilot.exe",
        "definitions/sidekick/task.yaml",
        "ripgrep/bin/win32-x64/rg.exe",
        "runtime.node",
        "schemas/api.schema.json",
    ]
    # download_cli's alias is the wrapper, byte for byte -- not the legacy SEA exe.
    assert (out / "copilot.exe").read_bytes() == b"MZ wrapper"
    assert (out / "runtime.node").read_bytes() == b"MZ runtime"
    assert (out / "COPILOT-CLI-LICENSE.txt").read_bytes() == b"GitHub Copilot CLI License"
    assert (out / ".hostless-runtime-assets-v2").read_text(encoding="ascii").strip() == "1"
    assert fbd.is_complete("copilot")
    calls.clear()
    fbd.fetch_copilot()
    assert calls == []


def test_fetch_copilot_replaces_a_legacy_stage_whole(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    legacy = fbd.component_dir("copilot")
    legacy.mkdir(parents=True)
    (legacy / "copilot.exe").write_bytes(b"MZ legacy sea")
    (legacy / "COPILOT-CLI-LICENSE.txt").write_text("old", encoding="utf-8")
    (legacy / "stale.dll").write_bytes(b"x")
    assert fbd.is_staged("copilot") and not fbd.is_complete("copilot")
    _fake_copilot_download(fbd, monkeypatch)
    out = fbd.fetch_copilot()
    assert not (out / "stale.dll").exists()
    assert (out / "copilot.exe").read_bytes() == b"MZ wrapper"
    assert not any(p.name.startswith(".copilot-staging-") for p in out.parent.iterdir())


@pytest.mark.parametrize(
    ("extra", "match"),
    [
        ({"package/brand-new-dir/x.js": b"x"}, "layout"),
        ({"outside/x.txt": b"x"}, "Unexpected copilot package entry"),
        ({"package/../escape.txt": b"x"}, "Unsafe"),
    ],
)
def test_fetch_copilot_refuses_an_unexpected_package(
    fbd, tmp_path, monkeypatch, extra, match
) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    _fake_copilot_download(fbd, monkeypatch, {**_COPILOT_PACKAGE, **extra})
    with pytest.raises(fbd.ReleaseAssetError, match=match):
        fbd.fetch_copilot()
    assert not fbd.component_dir("copilot").exists()
    assert not any(p.name.startswith(".copilot-staging-") for p in (tmp_path / "deps").iterdir())


@pytest.mark.parametrize("member", ["copilot-runtime.exe", "runtime.node"])
def test_fetch_copilot_refuses_a_bundle_file_that_misses_its_pin(
    fbd, tmp_path, monkeypatch, member
) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    package = {**_COPILOT_PACKAGE, f"package/prebuilds/win32-x64/{member}": b"not it"}
    _fake_copilot_download(fbd, monkeypatch, package)
    with pytest.raises(fbd.ReleaseAssetError, match="pinned SHA-256"):
        fbd.fetch_copilot()
    assert not fbd.component_dir("copilot").exists()


def test_fetch_copilot_refuses_a_package_without_its_licence(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    package = {k: v for k, v in _COPILOT_PACKAGE.items() if k != "package/LICENSE.md"}
    _fake_copilot_download(fbd, monkeypatch, package)
    with pytest.raises(fbd.ReleaseAssetError, match="LICENSE.md"):
        fbd.fetch_copilot()


def test_a_copilot_bundle_missing_its_marker_is_not_complete(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path))
    staged = tmp_path / "copilot"
    staged.mkdir()
    for name in ("copilot.exe", "copilot-runtime.exe", "runtime.node", "COPILOT-CLI-LICENSE.txt"):
        (staged / name).write_bytes(b"MZ")
    assert not fbd.is_complete("copilot")
    (staged / ".hostless-runtime-assets-v2").write_text("1\n", encoding="ascii")
    assert fbd.is_complete("copilot")


def test_copilot_filter_matches_the_sdk_rules(fbd) -> None:
    """Spot checks of the reimplemented ``_hostless_runtime_path``."""
    path = fbd.copilot_bundle_path
    assert path("package/prebuilds/win32-x64/runtime.node").as_posix() == "runtime.node"
    assert path("package/prebuilds/win32-arm64/runtime.node") is None
    assert path("package/prebuilds/win32-x64") is None
    assert path("package/plugins/a/cli-native.node") is None
    assert path("package/tree-sitter.wasm") is None
    assert path("package/voice-engine.worker.js") is None
    assert path("package/LICENSE.md") is None
    assert path("package/README.md") is None
    assert path("other/runtime.node") is None
    assert path("package/schemas/x.json").as_posix() == "schemas/x.json"
    with pytest.raises(fbd.ReleaseAssetError):
        path("package\\schemas\\x.json")


def test_fetch_codex_renames_the_exe_and_stages_licence_and_notice(
    fbd, tmp_path, monkeypatch
) -> None:
    import hashlib

    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    monkeypatch.setattr(fbd, "CODEX_APP_SERVER_SHA256", hashlib.sha256(b"MZ codex").hexdigest())
    calls = _fake_engine_download(
        fbd, monkeypatch, member=fbd.CODEX_ARCHIVE_MEMBER, exe=b"MZ codex"
    )
    out = fbd.fetch_codex()
    assert sorted(p.name for p in out.iterdir()) == [
        "CODEX-LICENSE.txt",
        "CODEX-NOTICE.txt",
        "codex-app-server.exe",
    ]
    assert calls == [
        (fbd.CODEX_URL, fbd.CODEX_SHA256),
        (fbd.CODEX_LICENSE_URL, fbd.CODEX_LICENSE_SHA256),
        (fbd.CODEX_NOTICE_URL, fbd.CODEX_NOTICE_SHA256),
    ]
    assert fbd.is_complete("codex")


def test_an_engine_without_its_licence_is_not_complete(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path))
    (tmp_path / "codex").mkdir()
    (tmp_path / "codex" / "codex-app-server.exe").write_bytes(b"MZ")
    (tmp_path / "codex" / "CODEX-LICENSE.txt").write_text("x", encoding="utf-8")
    assert fbd.is_staged("codex")
    assert not fbd.is_complete("codex"), "the NOTICE is missing"


def test_fetch_engine_refuses_an_unexpected_archive(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    _fake_engine_download(fbd, monkeypatch, member=fbd.CODEX_ARCHIVE_MEMBER, exe=b"x", extra=True)
    with pytest.raises(fbd.ReleaseAssetError, match="layout"):
        fbd.fetch_codex()
    assert not (fbd.component_dir("codex") / "codex-app-server.exe").exists()


def test_fetch_engine_refuses_an_exe_that_misses_its_pin(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path / "deps"))
    _fake_engine_download(fbd, monkeypatch, member=fbd.CODEX_ARCHIVE_MEMBER, exe=b"not it")
    with pytest.raises(fbd.ReleaseAssetError, match="pinned SHA-256"):
        fbd.fetch_codex()
    staged = fbd.component_dir("codex")
    assert not (staged / "codex-app-server.exe").exists()
    assert not (staged / "codex-app-server.exe.part").exists()
