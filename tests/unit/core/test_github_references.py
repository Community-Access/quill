"""GitHub URLs route safely to native workbench objects or explicit fallback."""

from __future__ import annotations

import pytest

from quill.core.github.references import GitHubReferenceError, parse_github_reference


@pytest.mark.parametrize(
    ("value", "kind", "number", "ref", "path", "line", "line_end", "section"),
    [
        ("owner/repo", "repository", None, "", "", 0, 0, ""),
        (
            "https://github.com/owner/repo/issues/42",
            "issue",
            42,
            "",
            "",
            0,
            0,
            "",
        ),
        (
            "https://github.com/owner/repo/pull/7/files#L10-L12",
            "pull_request",
            7,
            "",
            "",
            10,
            12,
            "files",
        ),
        (
            "https://github.com/owner/repo/discussions/19",
            "discussion",
            19,
            "",
            "",
            0,
            0,
            "",
        ),
        (
            "https://github.com/owner/repo/commit/abc123",
            "commit",
            None,
            "abc123",
            "",
            0,
            0,
            "",
        ),
        (
            "https://github.com/owner/repo/blob/main/src/app.py#L9",
            "file",
            None,
            "main",
            "src/app.py",
            9,
            9,
            "",
        ),
        (
            "https://github.com/owner/repo/tree/feature%2Fbranch/src",
            "branch",
            None,
            "feature/branch",
            "src",
            0,
            0,
            "",
        ),
        (
            "https://github.com/owner/repo/releases/tag/v1.2.0",
            "release",
            None,
            "v1.2.0",
            "",
            0,
            0,
            "",
        ),
        (
            "https://github.com/owner/repo/actions/runs/101",
            "workflow_run",
            101,
            "",
            "",
            0,
            0,
            "",
        ),
        (
            "https://github.com/owner/repo/actions/workflows/ci.yml",
            "workflow",
            None,
            "ci.yml",
            "",
            0,
            0,
            "",
        ),
        (
            "https://github.enterprise.local/owner/repo/issues/3",
            "issue",
            3,
            "",
            "",
            0,
            0,
            "",
        ),
    ],
)
def test_parses_supported_reference_shapes(
    value: str,
    kind: str,
    number: int | None,
    ref: str,
    path: str,
    line: int,
    line_end: int,
    section: str,
) -> None:
    reference = parse_github_reference(value)

    assert reference.repository == "owner/repo"
    assert reference.kind == kind
    assert reference.number == number
    assert reference.ref == ref
    assert reference.path == path
    assert reference.line == line
    assert reference.line_end == line_end
    assert reference.section == section
    assert reference.supports_native_view is (
        reference.host in {"github.com", "www.github.com"}
        and kind
        in {
            "repository",
            "issue",
            "pull_request",
            "discussion",
            "file",
            "commit",
            "release",
            "workflow",
            "workflow_run",
        }
        or reference.host in {"github.com", "www.github.com"}
        and kind == "branch"
        and not path
    )


def test_ssh_remote_and_git_suffix_normalize_to_repository() -> None:
    reference = parse_github_reference("git@github.com:owner/repo.git")

    assert reference.repository == "owner/repo"
    assert reference.kind == "repository"
    assert reference.url == "https://github.com/owner/repo.git"
    assert reference.supports_native_view


def test_unsupported_github_object_retains_a_safe_browser_fallback() -> None:
    reference = parse_github_reference("https://github.com/owner/repo/settings/branches")

    assert reference.kind == "unsupported"
    assert not reference.supports_native_view
    assert reference.url.endswith("/owner/repo/settings/branches")


def test_discussions_are_native_and_comparisons_use_browser_fallback() -> None:
    discussion = parse_github_reference("https://github.com/owner/repo/discussions/18")
    comparison = parse_github_reference("https://github.com/owner/repo/compare/main...feature")

    assert discussion.supports_native_view
    assert not comparison.supports_native_view


@pytest.mark.parametrize(
    "value",
    [
        "https://github.com/owner/repo/blob/main/file.py#L0",
        "https://github.com/owner/repo/blob/main/file.py#L20-L10",
    ],
)
def test_rejects_malformed_line_anchors(value: str) -> None:
    with pytest.raises(GitHubReferenceError, match="line"):
        parse_github_reference(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://user:secret@github.com/owner/repo",
        "https://github.com/owner/repo?access_token=secret",
        "http://github.com/owner/repo",
        "https://github.com/owner",
        "https://github.com/owner/repo/issues/not-a-number",
        "https://github.com/owner/repo/actions/runs/0",
        "https://github.com/../repo",
    ],
)
def test_rejects_malformed_or_credential_bearing_references(value: str) -> None:
    with pytest.raises(GitHubReferenceError):
        parse_github_reference(value)
