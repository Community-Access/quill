from __future__ import annotations

from pathlib import Path

from quill.core.external_tools import (
    format_tool_status_report,
    get_external_tool_status,
)


def test_detect_tool_prefers_bundled_path(monkeypatch, tmp_path: Path) -> None:
    tool_root = tmp_path / "tools" / "pandoc"
    tool_root.mkdir(parents=True)
    executable = tool_root / "pandoc.exe"
    executable.write_text("binary", encoding="utf-8")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path))
    monkeypatch.setattr("quill.core.external_tools._tool_version", lambda *_args: "Pandoc 3.0")

    status = get_external_tool_status("pandoc")

    assert status.installed is True
    assert status.source == "bundled"
    assert status.path == str(executable.resolve())
    assert status.version == "Pandoc 3.0"


def test_detect_tool_finds_macos_well_known_path_when_not_on_path(
    monkeypatch, tmp_path: Path
) -> None:
    """A Finder-launched .app bundle's PATH does not include /usr/local/bin or
    /opt/homebrew/bin (those are only sourced by login/interactive shells), so
    a pandoc installed via the pandoc.org .pkg installer -- not Homebrew --
    is invisible to shutil.which() even though it is genuinely on disk. This
    is exactly the report from @quillforall/@NightDrake (Mastodon): pandoc
    installed from the website, QUILL still reports it missing."""
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr("quill.core.external_tools.sys.platform", "darwin")
    monkeypatch.setattr("quill.core.external_tools.shutil.which", lambda _name: None)
    fallback_dir = tmp_path / "usr-local-bin"
    fallback_dir.mkdir()
    executable = fallback_dir / "pandoc"
    executable.write_text("binary", encoding="utf-8")
    monkeypatch.setattr("quill.core.external_tools._MACOS_FALLBACK_DIRS", (str(fallback_dir),))
    monkeypatch.setattr("quill.core.external_tools._tool_version", lambda *_args: None)

    status = get_external_tool_status("pandoc")

    assert status.installed is True
    assert status.source == "system"
    assert status.path == str(executable)


def test_detect_tool_macos_fallback_is_a_noop_on_windows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr("quill.core.external_tools.sys.platform", "win32")
    monkeypatch.setattr("quill.core.external_tools.shutil.which", lambda _name: None)
    fallback_dir = tmp_path / "usr-local-bin"
    fallback_dir.mkdir()
    (fallback_dir / "pandoc").write_text("binary", encoding="utf-8")
    monkeypatch.setattr("quill.core.external_tools._MACOS_FALLBACK_DIRS", (str(fallback_dir),))

    status = get_external_tool_status("pandoc")

    assert status.installed is False


def test_bundled_subpaths_use_forward_slashes_for_cross_platform_path_composition() -> None:
    """#59: bundled_subpath used to be Windows raw strings (``pandoc\\pandoc.exe``).
    On macOS, ``Path(app_root) / "tools" / "pandoc\\pandoc.exe"`` treats the
    backslash as a literal filename character (one component named
    ``pandoc\\pandoc.exe``), so the bundled binary is never found even when
    it genuinely exists. Forward slashes compose correctly on both platforms.
    """
    from quill.core.external_tools import TOOL_DEFINITIONS

    for definition in TOOL_DEFINITIONS:
        assert "\\" not in definition.bundled_subpath, (
            f"{definition.tool_id} bundled_subpath must use forward slashes: "
            f"{definition.bundled_subpath!r}"
        )
        composed = Path("tools") / definition.bundled_subpath
        # Forward-slash composition yields separate parts (tools/, subdir/, exe);
        # a backslash would collapse to a single literal component.
        assert composed.parts == ("tools", *definition.bundled_subpath.split("/"))


def test_format_tool_status_report_mentions_install_command(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr("quill.core.external_tools.shutil.which", lambda _name: None)

    report = format_tool_status_report()

    assert "Pandoc" in report
    assert "Install command:" in report
    assert "HTML Tidy" in report
    assert "PyMarkdown" in report
