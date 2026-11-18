"""Unit tests for the GitHub provider binary-detection / ref-cap logic.

Covers finding #25 (binary corruption guard) and #34 (list_refs cap) at the
provider boundary so the dialog layer can stay simple.  The tests build a
fake PyGithub Content object so the provider does not need a live network
or a real PyGithub install.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

from quill.core.github.github_provider import GitHubRemoteProvider, _looks_binary


def _install_fake_pygithub() -> None:
    """Install a stub ``github`` module on ``sys.modules`` if PyGithub is absent.

    The provider does ``import github`` lazily; we just need the import to
    succeed.  The Content stubs we pass in are plain SimpleNamespace objects,
    so no API surface is needed here.
    """
    # Only a real PyGithub counts: a folder that happens to be called "github"
    # on sys.path imports as an empty namespace package, which once hid this
    # stub and failed the provider tests in whichever shard ran it after one.
    if hasattr(sys.modules.get("github"), "Github"):
        return
    fake = types.ModuleType("github")
    fake.Github = MagicMock()
    fake.GithubException = type("GithubException", (Exception,), {})
    fake.Auth = SimpleNamespace(Token=lambda token: ("token", token))
    sys.modules["github"] = fake


def test_looks_binary_flags_nul_byte() -> None:
    assert _looks_binary(b"PNG\r\n\x1a\n\x00\x00\x00") is True
    assert _looks_binary(b"hello, world!\nthis is text\n") is False


def test_looks_binary_skips_bytes_after_sample_window() -> None:
    # Long string with a NUL far past the sample window -- still text from
    # the editor's point of view.
    data = b"a" * 8_000 + b"\x00"
    assert _looks_binary(data, sample=100) is False


def test_get_file_rejects_binary_payload() -> None:
    _install_fake_pygithub()
    provider = GitHubRemoteProvider(token=None)
    binary = SimpleNamespace(
        type="file",
        size=16,
        decoded_content=b"\x89PNG\r\n\x1a\n\x00\x00\x00",
        html_url="https://example.com/file.png",
        sha="abc123",
    )
    repo = SimpleNamespace(full_name="owner/repo")
    provider._gh.get_repo = MagicMock(
        return_value=SimpleNamespace(get_contents=MagicMock(return_value=binary))
    )
    try:
        provider.get_file(repo, "image.png", "main")
    except ValueError as exc:
        assert "binary" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError for binary content")


def test_get_file_accepts_utf8_text() -> None:
    _install_fake_pygithub()
    provider = GitHubRemoteProvider(token=None)
    text = SimpleNamespace(
        type="file",
        size=11,
        decoded_content=b"hello world",
        html_url="https://example.com/file.txt",
        sha="deadbeef",
    )
    repo = SimpleNamespace(full_name="owner/repo")
    provider._gh.get_repo = MagicMock(
        return_value=SimpleNamespace(get_contents=MagicMock(return_value=text))
    )
    result = provider.get_file(repo, "readme.md", "main")
    assert result.content == b"hello world"
    assert result.sha == "deadbeef"


def test_list_refs_caps_results() -> None:
    _install_fake_pygithub()
    provider = GitHubRemoteProvider(token=None)
    branches = [SimpleNamespace(name=f"branch-{i}") for i in range(150)]
    tags = [SimpleNamespace(name=f"v{i}") for i in range(5)]
    provider._gh.get_repo = MagicMock(
        return_value=SimpleNamespace(
            get_branches=MagicMock(return_value=iter(branches)),
            get_tags=MagicMock(return_value=iter(tags)),
        )
    )
    refs = provider.list_refs(SimpleNamespace(full_name="owner/repo"), limit=100)
    # Per-kind cap: 100 branches + 5 tags = 105 total.
    # Tags must be visible even when branches fill the cap.
    assert len(refs) == 105
    branch_refs = [r for r in refs if r.kind == "branch"]
    tag_refs = [r for r in refs if r.kind == "tag"]
    assert len(branch_refs) == 100
    assert len(tag_refs) == 5


def test_list_refs_tags_visible_when_branches_at_limit() -> None:
    """Regression: repos with >= limit branches must still show tags."""
    _install_fake_pygithub()
    provider = GitHubRemoteProvider(token=None)
    branches = [SimpleNamespace(name=f"b{i}") for i in range(100)]
    tags = [SimpleNamespace(name=f"v{i}") for i in range(10)]
    provider._gh.get_repo = MagicMock(
        return_value=SimpleNamespace(
            get_branches=MagicMock(return_value=iter(branches)),
            get_tags=MagicMock(return_value=iter(tags)),
        )
    )
    refs = provider.list_refs(SimpleNamespace(full_name="owner/repo"), limit=100)
    tag_refs = [r for r in refs if r.kind == "tag"]
    assert len(tag_refs) == 10


def test_list_refs_default_limit_is_100() -> None:
    _install_fake_pygithub()
    provider = GitHubRemoteProvider(token=None)
    branches = [SimpleNamespace(name=f"b{i}") for i in range(250)]
    provider._gh.get_repo = MagicMock(
        return_value=SimpleNamespace(
            get_branches=MagicMock(return_value=iter(branches)),
            get_tags=MagicMock(return_value=iter([])),
        )
    )
    refs = provider.list_refs(SimpleNamespace(full_name="owner/repo"))
    assert len(refs) == 100
