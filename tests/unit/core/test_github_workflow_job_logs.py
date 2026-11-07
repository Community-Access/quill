"""Job log redirects never receive the GitHub bearer token."""

from __future__ import annotations

import zipfile
from io import BytesIO
from urllib.error import HTTPError

import pytest

from quill.core.github import workflow_job_logs


def test_job_log_redirect_drops_token(monkeypatch) -> None:
    requests = []

    class Opener:
        def open(self, request, *, timeout):
            requests.append(request)
            if len(requests) == 1:
                raise HTTPError(
                    request.full_url,
                    302,
                    "Moved",
                    {"Location": "https://signed.example/job.txt"},
                    None,
                )
            return BytesIO(b"job log text")

    monkeypatch.setattr(workflow_job_logs.urllib.request, "build_opener", lambda *_args: Opener())
    assert workflow_job_logs.fetch_job_log("secret", "owner/repo", 123) == "job log text"
    assert requests[0].get_header("Authorization") == "Bearer secret"
    assert requests[1].full_url == "https://signed.example/job.txt"
    assert requests[1].get_header("Authorization") is None


def test_job_log_refuses_non_https_redirect(monkeypatch) -> None:
    class Opener:
        def open(self, request, *, timeout):
            raise HTTPError(request.full_url, 302, "Moved", {"Location": "http://bad"}, None)

    monkeypatch.setattr(workflow_job_logs.urllib.request, "build_opener", lambda *_args: Opener())
    with pytest.raises(workflow_job_logs.GitHubJobLogError, match="non-HTTPS"):
        workflow_job_logs.fetch_job_log("secret", "owner/repo", 123)


def test_job_log_is_bounded_and_invalid_repo_is_refused(monkeypatch) -> None:
    class Opener:
        def open(self, _request, *, timeout):
            return BytesIO(b"123456789")

    monkeypatch.setattr(workflow_job_logs.urllib.request, "build_opener", lambda *_args: Opener())
    assert "truncated" in workflow_job_logs.fetch_job_log(None, "o/r", 1, max_bytes=4)
    with pytest.raises(workflow_job_logs.GitHubJobLogError, match="valid owner/repo"):
        workflow_job_logs.fetch_job_log(None, "../../x", 1)


def test_zip_job_log_is_read_as_bounded_text(monkeypatch) -> None:
    archive_bytes = BytesIO()
    with zipfile.ZipFile(archive_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("1_Set up job.txt", "line one\nline two\n")

    class Opener:
        def open(self, _request, *, timeout):
            return BytesIO(archive_bytes.getvalue())

    monkeypatch.setattr(workflow_job_logs.urllib.request, "build_opener", lambda *_args: Opener())
    result = workflow_job_logs.fetch_job_log(None, "owner/repo", 1)

    assert "line one\nline two" in result
    assert "PK" not in result


def test_zip_job_log_truncates_expanded_text(monkeypatch) -> None:
    archive_bytes = BytesIO()
    with zipfile.ZipFile(archive_bytes, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("job.txt", "123456789")

    class Opener:
        def open(self, _request, *, timeout):
            return BytesIO(archive_bytes.getvalue())

    monkeypatch.setattr(workflow_job_logs.urllib.request, "build_opener", lambda *_args: Opener())
    result = workflow_job_logs.fetch_job_log(None, "owner/repo", 1, max_bytes=4)

    assert result.startswith("1234")
    assert "truncated after 4 bytes" in result


def test_job_log_redirects_only_once(monkeypatch) -> None:
    class Opener:
        def open(self, request, *, timeout):
            raise HTTPError(
                request.full_url,
                302,
                "Moved",
                {"Location": "https://signed.example/another-hop"},
                None,
            )

    monkeypatch.setattr(workflow_job_logs.urllib.request, "build_opener", lambda *_args: Opener())
    with pytest.raises(workflow_job_logs.GitHubJobLogError, match="more than once"):
        workflow_job_logs.fetch_job_log("secret", "owner/repo", 1)


def test_job_log_rejects_invalid_zip_response(monkeypatch) -> None:
    class Opener:
        def open(self, _request, *, timeout):
            return BytesIO(b"PK\x03\x04incomplete")

    monkeypatch.setattr(workflow_job_logs.urllib.request, "build_opener", lambda *_args: Opener())
    with pytest.raises(workflow_job_logs.GitHubJobLogError, match="invalid or incomplete"):
        workflow_job_logs.fetch_job_log(None, "owner/repo", 1)


def test_job_log_output_limit_is_bounded(monkeypatch) -> None:
    with pytest.raises(workflow_job_logs.GitHubJobLogError, match="between 1 byte"):
        workflow_job_logs.fetch_job_log(None, "owner/repo", 1, max_bytes=0)
    with pytest.raises(workflow_job_logs.GitHubJobLogError, match="between 1 byte"):
        workflow_job_logs.fetch_job_log(None, "owner/repo", 1, max_bytes=4_000_001)
