"""Read one GitHub Actions job log without forwarding credentials to redirects."""

from __future__ import annotations

import io
import urllib.error
import urllib.request
import zipfile
import zlib
from urllib.parse import urlsplit

from quill.core.error_codes import CodedError
from quill.core.net import verified_ssl_context


class GitHubJobLogError(CodedError):
    """A workflow job log could not be retrieved."""

    code = "QUILL-GITHUB-JOB-LOG-ERROR"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


_MAX_ARCHIVE_BYTES = 16_000_000
_MAX_LOG_BYTES = 4_000_000


def _limit_label(max_bytes: int) -> str:
    if max_bytes > 0 and max_bytes % 1_000_000 == 0:
        return f"{max_bytes // 1_000_000} MB"
    if max_bytes > 0 and max_bytes % 1_000 == 0:
        return f"{max_bytes // 1_000} KB"
    return f"{max_bytes:,} bytes"


def _read_log_bytes(raw: bytes, max_bytes: int) -> tuple[bytes, bool]:
    """Decode GitHub's ZIP response in memory without expanding beyond the cap."""
    if not zipfile.is_zipfile(io.BytesIO(raw)):
        if raw.startswith(b"PK"):
            raise GitHubJobLogError(
                "GitHub returned an invalid or incomplete job log archive. Open the job on GitHub."
            )
        return raw[:max_bytes], len(raw) > max_bytes

    output = bytearray()
    truncated = False
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files = [entry for entry in archive.infolist() if not entry.is_dir()]
            if not files:
                raise GitHubJobLogError("GitHub returned a job log archive with no log files.")
            for entry in files:
                if output:
                    separator = b"\n"
                    available = max_bytes - len(output)
                    if available <= 0:
                        truncated = True
                        break
                    output.extend(separator[:available])
                available = max_bytes - len(output)
                if available <= 0:
                    truncated = True
                    break
                with archive.open(entry) as stream:
                    chunk = stream.read(available + 1)
                output.extend(chunk[:available])
                if len(chunk) > available or entry.file_size > len(chunk):
                    truncated = True
                    break
    except GitHubJobLogError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error) as exc:
        raise GitHubJobLogError(
            "GitHub returned an invalid or incomplete job log archive. Open the job on GitHub."
        ) from exc
    return bytes(output), truncated


def fetch_job_log(token: str | None, repo: str, job_id: int, *, max_bytes: int = 4_000_000) -> str:
    """Return bounded plain text; report truncation and refuse unsafe redirects."""
    if max_bytes <= 0 or max_bytes > _MAX_LOG_BYTES:
        raise GitHubJobLogError(
            f"Choose a job log limit between 1 byte and {_limit_label(_MAX_LOG_BYTES)}."
        )
    parts = repo.split("/")
    if len(parts) != 2 or not all(
        part.replace("-", "").replace("_", "").isalnum() for part in parts
    ):
        raise GitHubJobLogError("Enter a valid owner/repo before loading job logs.")
    if job_id <= 0:
        raise GitHubJobLogError("This workflow job has no GitHub job ID.")
    url = f"https://api.github.com/repos/{repo}/actions/jobs/{job_id}/logs"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "QUILL-GitHub-Workbench"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    context = verified_ssl_context()
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=context))
    try:
        try:
            response = opener.open(request, timeout=30)  # noqa: S310 - HTTPS fixed above
        except urllib.error.HTTPError as exc:
            if exc.code not in (301, 302, 303, 307, 308):
                raise GitHubJobLogError(
                    f"GitHub returned HTTP {exc.code} for the job log."
                ) from exc
            location = exc.headers.get("Location", "") if exc.headers else ""
            try:
                parsed = urlsplit(location)
                safe_redirect = (
                    parsed.scheme.lower() == "https"
                    and bool(parsed.hostname)
                    and parsed.username is None
                    and parsed.password is None
                    and parsed.port in (None, 443)
                    and not parsed.fragment
                )
            except ValueError:
                safe_redirect = False
            if not safe_redirect:
                raise GitHubJobLogError(
                    "GitHub returned an unsafe or non-HTTPS log location."
                ) from exc
            # Signed redirect may be on another host. Never send the GitHub token there.
            redirect_request = urllib.request.Request(
                location,
                headers={
                    "Accept": "application/zip, text/plain",
                    "User-Agent": "QUILL-GitHub-Workbench",
                },
            )
            try:
                response = opener.open(redirect_request, timeout=30)  # noqa: S310 - validated HTTPS URL
            except urllib.error.HTTPError as redirect_error:
                if redirect_error.code in (301, 302, 303, 307, 308):
                    raise GitHubJobLogError(
                        "GitHub redirected the job log more than once."
                    ) from redirect_error
                raise GitHubJobLogError(
                    f"The signed job log URL returned HTTP {redirect_error.code}."
                ) from redirect_error
        with response:
            raw = response.read(_MAX_ARCHIVE_BYTES + 1)
    except GitHubJobLogError:
        raise
    except Exception as exc:  # noqa: BLE001 - network errors become visible
        raise GitHubJobLogError(f"Could not load job log: {exc}") from exc
    if len(raw) > _MAX_ARCHIVE_BYTES:
        raise GitHubJobLogError(
            "The job log response exceeds the 16 MB download limit. Open the job on GitHub."
        )
    bounded, truncated = _read_log_bytes(raw, max_bytes)
    text = bounded.decode("utf-8", errors="replace")
    return text + (
        f"\n\n[Log truncated after {_limit_label(max_bytes)}. Open the job on GitHub for the rest.]"
        if truncated
        else ""
    )
