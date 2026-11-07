"""Diff-explanation requests are bounded, source-cited, and honest about gaps."""

from __future__ import annotations

from quill.core.github.diff_explanation import (
    build_diff_explanation_request,
    format_diff_explanation,
)
from quill.core.github.items_provider import GitHubPullDiff, GitHubPullFile


def _diff(head_sha: str = "a" * 40) -> GitHubPullDiff:
    return GitHubPullDiff(
        number=42,
        title="Set safe defaults",
        base_ref="main",
        base_sha="b" * 40,
        head_ref="feature",
        head_sha=head_sha,
        files=(GitHubPullFile(filename="src/app.py", status="modified"),),
    )


def test_diff_explanation_request_keeps_file_head_and_explicit_truncation() -> None:
    diff_text = "Changed line\n" + ("context\n" * 4_000)

    request = build_diff_explanation_request("owner/repo", _diff(), _diff().files[0], diff_text)

    assert request.omitted
    assert len(request.evidence) == 24_000
    assert "Repository: owner/repo" in request.prompt
    assert "Pull request: #42 Set safe defaults" in request.prompt
    assert "Head SHA: " + "a" * 40 in request.prompt
    assert "src/app.py" in request.prompt
    assert "untrusted source material" in request.prompt
    assert "The AI input below is truncated" in request.prompt
    result = format_diff_explanation("The code changes the default.", request)
    assert "https://github.com/owner/repo/blob/" + "a" * 40 + "/src/app.py" in result
    assert "AI context truncated at 24,000 characters" in result


def test_diff_explanation_without_head_sha_does_not_invent_a_file_source() -> None:
    diff = _diff(head_sha="")
    request = build_diff_explanation_request("owner/repo", diff, diff.files[0], "small diff")
    result = format_diff_explanation("A short explanation.", request)

    assert not request.omitted
    assert not request.source_file_url
    assert "head SHA was unavailable" in result
    assert "unknown" in result
