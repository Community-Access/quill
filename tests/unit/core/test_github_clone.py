"""Clone Repository's core (quill/core/github/clone.py): parsing, argv, the token's path."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.github import clone
from quill.stability.redaction import redact_known_secrets

_TOKEN = "gho_" + "A1b2C3d4E5f6G7h8I9j0" * 2


@pytest.mark.parametrize(
    ("text", "url", "full_name"),
    [
        (
            "octocat/hello-world",
            "https://github.com/octocat/hello-world.git",
            "octocat/hello-world",
        ),
        (
            "https://github.com/octocat/Hello.git",
            "https://github.com/octocat/Hello.git",
            "octocat/Hello",
        ),
        (
            "https://github.com/octocat/hello/tree/main/docs",
            "https://github.com/octocat/hello.git",
            "octocat/hello",
        ),
        ("git@github.com:octocat/hello.git", "git@github.com:octocat/hello.git", "octocat/hello"),
        ("https://gitlab.com/group/thing.git", "https://gitlab.com/group/thing.git", ""),
    ],
)
def test_parse_accepts_names_and_addresses(text: str, url: str, full_name: str) -> None:
    source = clone.parse_clone_source(text)
    assert (source.url, source.full_name) == (url, full_name)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "octocat",
        "a/b/c",
        "http://github.com/o/r",
        "https://user:pw@github.com/o/r",
        "file:///x",
    ],
)
def test_parse_refuses_what_it_cannot_clone_safely(text: str) -> None:
    with pytest.raises(clone.CloneError):
        clone.parse_clone_source(text)


def test_the_command_is_argv_with_the_url_after_double_dash() -> None:
    source = clone.parse_clone_source("o/r")
    argv = clone.clone_command(Path("C:/git/cmd/git.exe"), source, Path("C:/work/r"))
    assert argv[1:4] == ["clone", "--", "https://github.com/o/r.git"]
    assert _TOKEN not in " ".join(argv)


def test_the_token_travels_only_in_the_environment_scoped_to_github() -> None:
    source = clone.parse_clone_source("o/r")
    env = clone.clone_environment(_TOKEN, source, base={"GIT_CONFIG_COUNT": "2"})
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_CONFIG_COUNT"] == "3"
    assert env["GIT_CONFIG_KEY_2"] == "http.https://github.com/.extraheader"
    value = env["GIT_CONFIG_VALUE_2"]
    assert value.startswith("AUTHORIZATION: basic ")
    decoded = base64.b64decode(value.split()[-1]).decode()
    assert decoded == f"x-access-token:{_TOKEN}"
    # Remembered for redaction: neither the token nor the header survives a log line.
    line = f"token {_TOKEN} header {value}"
    assert _TOKEN not in redact_known_secrets(line)
    assert value.split()[-1] not in redact_known_secrets(line)


def test_no_token_for_somewhere_other_than_github() -> None:
    env = clone.clone_environment(_TOKEN, clone.parse_clone_source("https://gitlab.com/g/t"), {})
    assert "GIT_CONFIG_COUNT" not in env
    assert _TOKEN not in " ".join(env.values())


def test_target_folder_refuses_a_folder_with_something_in_it(tmp_path: Path) -> None:
    source = clone.parse_clone_source("o/r")
    assert clone.target_folder(tmp_path, source) == tmp_path / "r"
    (tmp_path / "r").mkdir()
    (tmp_path / "r" / "x.txt").write_text("x", encoding="utf-8")
    with pytest.raises(clone.CloneError):
        clone.target_folder(tmp_path, source)
    with pytest.raises(clone.CloneError):
        clone.target_folder(tmp_path / "missing", source)


def test_a_failed_clone_says_what_git_said_without_the_token(tmp_path: Path) -> None:
    source = clone.parse_clone_source("o/r")
    seen: dict[str, object] = {}

    def runner(argv, *, cwd, timeout_seconds, env):
        seen.update(argv=argv, cwd=cwd, env=env)
        return SimpleNamespace(
            returncode=128,
            stderr=f"Cloning into 'r'...\nfatal: could not read {_TOKEN}: repository not found\n",
        )

    with pytest.raises(clone.CloneError) as caught:
        clone.clone_repository("git", source, tmp_path / "r", token=_TOKEN, runner=runner)
    message = str(caught.value)
    assert "Could not clone r." in message and "repository not found" in message
    assert _TOKEN not in message
    assert seen["cwd"] == str(tmp_path)
    assert _TOKEN not in " ".join(seen["argv"])  # type: ignore[arg-type]


def test_a_timeout_is_said_plainly(tmp_path: Path) -> None:
    def runner(argv, **_kwargs):
        raise subprocess.TimeoutExpired(argv, 1)

    with pytest.raises(clone.CloneError, match="took too long"):
        clone.clone_repository(
            "git", clone.parse_clone_source("o/r"), tmp_path / "r", token="", runner=runner
        )


def test_a_real_local_clone_writes_no_token_into_git_config(tmp_path: Path) -> None:
    """The real git, the real runner, a local source: .git/config stays clean."""
    from quill.core.git_binaries import find_git
    from quill.stability.safe_subprocess import run_subprocess_safely

    git = find_git()
    if git is None:
        pytest.skip("git is not installed")
    origin = tmp_path / "origin"
    origin.mkdir()
    run_subprocess_safely([str(git), "init", "-q", str(origin)])
    run_subprocess_safely([
        str(git),
        "-C",
        str(origin),
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.invalid",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "first",
    ])
    # A plain path is not https, so no token is attached -- but the environment
    # path is exercised end to end, and the config is checked all the same.
    source = clone.CloneSource(url=str(origin), name="copy")
    folder = clone.clone_repository(
        git, source, tmp_path / "copy", token=_TOKEN, runner=run_subprocess_safely
    )
    config = (folder / ".git" / "config").read_text(encoding="utf-8")
    assert _TOKEN not in config and "extraheader" not in config


def test_find_git_honours_quill_git_only_in_a_dev_build(tmp_path: Path, monkeypatch) -> None:
    from quill.core import git_binaries, paths

    fake = tmp_path / "git.exe"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("QUILL_GIT", str(fake))
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    assert git_binaries.find_git() == fake
    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    assert git_binaries.find_git() != fake
    other = tmp_path / "evil.exe"
    other.write_text("", encoding="utf-8")
    monkeypatch.setenv("QUILL_GIT", str(other))
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    with pytest.raises(git_binaries.GitBinaryError):
        git_binaries.find_git()
