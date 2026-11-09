"""The language-server allowlist (quill.core.lsp.servers) is frozen: a new
server, or a server allowed the network, is a deliberate change here too."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.lsp import servers
from quill.core.lsp.servers import (
    LANGUAGE_SERVERS,
    language_id_for,
    resolve_server,
    server_for_path,
)


def test_the_allowlist_is_exactly_the_approved_servers() -> None:
    assert [(spec.name, spec.origin) for spec in LANGUAGE_SERVERS] == [
        ("HTML server", "bundled"),
        ("CSS server", "bundled"),
        ("JSON server", "bundled"),
        ("Markdown server", "bundled"),
        ("TypeScript server", "bundled"),
        ("Pyright", "bundled"),
        ("clangd", "installed"),
        ("PowerShell Editor Services", "installed"),
    ]
    text = " ".join(str(spec) for spec in LANGUAGE_SERVERS).lower()
    assert "pylance" not in text and "cpptools" not in text


def test_no_server_is_allowed_the_network() -> None:
    by_name = {spec.name: spec for spec in LANGUAGE_SERVERS}
    json_spec = by_name["JSON server"]
    assert json_spec.settings["json"]["schemaDownload"]["enable"] is False
    assert json_spec.init_options["handledSchemaProtocols"] == ["file"]
    markdown = by_name["Markdown server"].settings["markdown"]["validate"]
    assert {"http://**", "https://**"} <= set(markdown["ignoredLinks"])
    assert by_name["TypeScript server"].init_options["disableAutomaticTypingAcquisition"] is True


@pytest.mark.parametrize(
    ("name", "server", "language"),
    [
        ("page.html", "HTML server", "html"),
        ("site.scss", "CSS server", "scss"),
        ("tsconfig.jsonc", "JSON server", "jsonc"),
        ("README.md", "Markdown server", "markdown"),
        ("app.tsx", "TypeScript server", "typescriptreact"),
        ("tool.py", "Pyright", "python"),
        ("main.cpp", "clangd", "cpp"),
        ("build.ps1", "PowerShell Editor Services", "powershell"),
    ],
)
def test_each_file_finds_its_server(name: str, server: str, language: str) -> None:
    spec = server_for_path(name)
    assert spec is not None and spec.name == server
    assert language_id_for(name) == language


def test_nothing_for_unknown_or_missing() -> None:
    assert server_for_path("notes.txt") is None
    assert server_for_path(None) is None


def test_bundled_servers_need_the_bundled_node_and_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.delenv("QUILL_LANGUAGE_SERVERS_DIR", raising=False)
    monkeypatch.delenv("QUILL_LANGUAGE_SERVERS_NODE", raising=False)
    monkeypatch.setattr(servers.sys, "executable", str(tmp_path / "python.exe"))
    spec = server_for_path("data.json")
    assert resolve_server(spec) is None
    tools = tmp_path / "tools"
    (tools / "nodejs").mkdir(parents=True)
    (tools / "nodejs" / "node.exe").write_bytes(b"")
    script = tools / "language-servers" / spec.script
    script.parent.mkdir(parents=True)
    script.write_text("", encoding="utf-8")
    resolved = resolve_server(spec)
    assert resolved is not None
    assert resolved.argv == (str(tools / "nodejs" / "node.exe"), str(script), "--stdio")


def test_installed_servers_are_only_found_on_the_path(monkeypatch) -> None:
    spec = server_for_path("main.c")
    monkeypatch.setattr(servers.shutil, "which", lambda _name: None)
    assert resolve_server(spec) is None
    monkeypatch.setattr(servers.shutil, "which", lambda name: f"C:/llvm/{name}.exe")
    resolved = resolve_server(spec)
    assert resolved is not None and resolved.argv[0] == "C:/llvm/clangd.exe"
