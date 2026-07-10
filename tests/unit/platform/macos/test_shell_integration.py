"""Tests for the macOS file-type association module (#50).

The pure helpers (``launcher_command``, ``document_types_plist``,
``build_shell_integration_plan``, ``remove_shell_integration``) need no fakes.
``install_shell_integration`` is best-effort and early-returns off macOS or when
``duti`` is missing, so those branches are covered via monkeypatch on every
platform; the live ``duti`` invocation is faked by recording ``subprocess.run``.
"""

from __future__ import annotations

import pytest

import quill.platform.macos.shell_integration as si

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_launcher_command_uses_open_a_quill():
    cmd = si.launcher_command()
    assert cmd == 'open -a "Quill"'


def test_document_types_plist_shape():
    plist = si.document_types_plist()
    assert len(plist) == 3
    for entry in plist:
        assert entry["CFBundleTypeRole"] == "Editor"
        assert "CFBundleTypeName" in entry
        assert isinstance(entry["LSItemContentTypes"], list) and entry["LSItemContentTypes"]
        assert isinstance(entry["CFBundleTypeExtensions"], list)
    names = [entry["CFBundleTypeName"] for entry in plist]
    assert names == ["Plain Text Document", "Markdown Document", "HTML Document"]


def test_document_types_plist_covers_expected_extensions():
    plist = si.document_types_plist()
    all_exts = {ext for entry in plist for ext in entry["CFBundleTypeExtensions"]}
    for ext in (*si.TEXT_EXTENSIONS, *si.MARKUP_EXTENSIONS, *si.HTML_EXTENSIONS):
        assert ext in all_exts


def test_build_shell_integration_plan_lists_three_doc_types():
    plan = si.build_shell_integration_plan()
    assert len(plan) == 3
    assert all(isinstance(entry, si.ShellIntegrationEntry) for entry in plan)
    # The command argument is intentionally ignored (associations are bundle-declared).
    assert si.build_shell_integration_plan("ignored") == si.build_shell_integration_plan(None)


def test_remove_shell_integration_is_noop():
    assert si.remove_shell_integration() is None


def test_app_path_stub_returns_none():
    # Packaging helper; currently a stub. Documented behavior: returns None.
    assert si._app_path() is None


# ---------------------------------------------------------------------------
# install_shell_integration (best-effort, non-raising) -- monkeypatched
# ---------------------------------------------------------------------------


def test_install_shell_integration_noop_off_darwin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(si.sys, "platform", "win32")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        si.subprocess, "run", lambda *a, **k: calls.append(a[0] if a else k.get("args"))
    )
    assert si.install_shell_integration() is None
    assert calls == []


def test_install_shell_integration_noop_when_duti_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(si.sys, "platform", "darwin")
    monkeypatch.setattr(si.shutil, "which", lambda name: None)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        si.subprocess, "run", lambda *a, **k: calls.append(a[0] if a else k.get("args"))
    )
    assert si.install_shell_integration() is None
    assert calls == []


def test_install_shell_integration_invokes_duti_once_per_extension(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(si.sys, "platform", "darwin")
    monkeypatch.setattr(
        si.shutil, "which", lambda name: "/usr/local/bin/duti" if name == "duti" else None
    )
    calls: list[list[str]] = []

    def _record(args, **kwargs):
        calls.append(list(args))
        return None

    monkeypatch.setattr(si.subprocess, "run", _record)
    assert si.install_shell_integration() is None
    expected_exts = list(si.TEXT_EXTENSIONS + si.MARKUP_EXTENSIONS + si.HTML_EXTENSIONS)
    assert len(calls) == len(expected_exts)
    for call, ext in zip(calls, expected_exts, strict=False):
        assert call == ["duti", "-s", si.BUNDLE_IDENTIFIER, f".{ext}", "all"]
