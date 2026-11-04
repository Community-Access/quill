"""The project boundary and secret rules (code.md 4.4, Phase 1 gates)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from quill.core.ai.project import Project, ProjectError, is_secret_path
from quill.core.ai.project_outline import enclosing_name, outline_text


@pytest.fixture
def project(tmp_path: Path) -> Project:
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "cli.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / ".env").write_text("API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456\n", encoding="utf-8")
    (root / "deploy.pem").write_text("-----BEGIN KEY-----\n", encoding="utf-8")
    (root / ".ssh").mkdir()
    (root / ".ssh" / "id_rsa").write_text("secret\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "out.log").write_text("built\n", encoding="utf-8")
    (root / ".gitignore").write_text("build/\n*.tmp\n", encoding="utf-8")
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00" + b"\x00" * 64)
    return Project(root)


@pytest.mark.parametrize(
    "rel",
    [
        "../outside.txt",
        "src/../../outside.txt",
        "C:\\Windows\\win.ini",
        "C:/Windows/win.ini",
        "/etc/passwd",
        "\\\\server\\share\\file.txt",
        "//server/share/file.txt",
        "README.md:hidden",
        "CON",
        "src/nul.txt",
        "COM1.log",
    ],
)
def test_escapes_and_devices_are_refused(project: Project, rel: str) -> None:
    with pytest.raises(ProjectError):
        project.resolve(rel)


def test_symlink_out_of_the_project_is_refused(project: Project, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.txt").write_text("x", encoding="utf-8")
    link = project.root / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks need developer mode on this machine")
    with pytest.raises(ProjectError):
        project.resolve("link/x.txt")
    assert not any(e.path.startswith("link") for e in project.list_folder().entries)


def test_junction_out_of_the_project_is_refused(project: Project, tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("junctions are a Windows feature")
    import subprocess

    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "y.txt").write_text("y", encoding="utf-8")
    junction = project.root / "jn"
    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        check=False,
    )
    if made.returncode != 0:
        pytest.skip("could not make a junction here")
    with pytest.raises(ProjectError):
        project.resolve("jn/y.txt")


@pytest.mark.parametrize(
    "rel",
    [
        ".env",
        ".env.local",
        "deploy.pem",
        ".ssh/id_rsa",
        "id_ed25519.pub",
        "vault.kdbx",
        "credentials.json",
        "secrets.yaml",
        ".git/config",
        "config/.npmrc",
        "my.key",
    ],
)
def test_secret_names(rel: str) -> None:
    assert is_secret_path(rel)


@pytest.mark.parametrize("rel", ["src/cli.py", "README.md", "keyboard.py", "tokenizer.py"])
def test_ordinary_names_are_not_secret(rel: str) -> None:
    assert not is_secret_path(rel)


def test_secrets_are_never_listed_and_the_count_is_said(project: Project) -> None:
    result = project.list_folder()
    listed = {e.path for e in result.entries}
    assert "src/cli.py" in listed and "README.md" in listed
    assert not any(p in listed for p in (".env", "deploy.pem", ".ssh/id_rsa", ".git/config"))
    assert result.hidden_secrets == 2  # .env and deploy.pem; .ssh and .git are never entered
    assert result.ignored >= 0
    assert "build/out.log" not in listed  # .gitignore


def test_secrets_are_never_read_or_searched(project: Project) -> None:
    for rel in (".env", "deploy.pem", ".ssh/id_rsa", ".git/config"):
        with pytest.raises(ProjectError):
            project.read(rel)
    assert project.search("sk-abc") == []
    assert project.search("BEGIN KEY") == []


def test_read_numbers_lines_and_caps_ranges(project: Project) -> None:
    (project.root / "long.txt").write_text(
        "\n".join(f"line {n}" for n in range(1, 1001)), encoding="utf-8"
    )
    result = project.read("long.txt")
    assert result.start == 1 and result.end == 400 and result.total_lines == 1000
    assert result.truncated
    assert result.text.splitlines()[0].strip().startswith("1: line 1")
    ranged = project.read("long.txt", 990, 1000)
    assert ranged.text.splitlines()[-1].endswith("line 1000")


def test_reads_are_scrubbed(project: Project) -> None:
    (project.root / "settings.py").write_text(
        'TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"\n', encoding="utf-8"
    )
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in project.read("settings.py").text
    hits = project.search("TOKEN")
    assert hits and "ghp_abcdefghij" not in hits[0].text


def test_binary_files_are_described_not_sent(project: Project) -> None:
    result = project.read("logo.png")
    assert result.binary
    assert result.text.startswith("PNG image") and "Not sent" in result.text


def test_ignored_file_can_still_be_read_by_name(project: Project) -> None:
    assert "built" in project.read("build/out.log").text


def test_outline_python_and_other_languages() -> None:
    py = outline_text(".py", "class A:\n    def go(self):\n        pass\n\ndef main():\n    pass\n")
    assert [(i.kind, i.name, i.line) for i in py] == [
        ("class", "A", 1),
        ("function", "go", 2),
        ("function", "main", 5),
    ]
    js = outline_text(".js", "export function parse(a) {\n}\nconst run = (x) => x\n")
    assert [i.name for i in js] == ["parse", "run"]
    assert enclosing_name(py, 3) == "function go"
