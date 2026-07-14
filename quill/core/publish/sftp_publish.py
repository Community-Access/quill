"""Upload a finished book (and its companions) to an SFTP destination.

Rides QUILL's own SSH client (``quill.core.ssh.client``) so the SEC-9 host-key
policy holds: unknown hosts are **rejected** unless the user has opted into
trust-first-use. The password comes from the Windows Credential Manager (never
from settings); the whole operation is an explicit, consented user action in
the publish dialog and is absent in Safe Mode. wx-free, strict-typed.
"""

from __future__ import annotations

import posixpath
from collections.abc import Callable
from pathlib import Path

from quill.core.publish.destinations import SftpDestination


class PublishError(RuntimeError):
    """An upload failed; the message is speakable."""


class PublishCancelled(PublishError):
    """The user cancelled mid-upload; nothing more was sent."""


def companion_files(book_path: Path) -> list[Path]:
    """The book's sidecars worth publishing alongside it (those that exist)."""
    companions = [
        book_path.with_suffix(".chapters.json"),
        book_path.with_suffix(".chapters.txt"),
        book_path.with_suffix(".rss"),
    ]
    return [p for p in companions if p.is_file()]


def public_url(destination: SftpDestination, filename: str) -> str:
    """The public URL a published *filename* will have (empty when unknown)."""
    base = destination.url_base.strip().rstrip("/")
    return f"{base}/{filename}" if base else ""


def publish_files(
    destination: SftpDestination,
    files: list[Path],
    password: str,
    *,
    trust_first_use: bool | None = None,
    on_progress: Callable[[str], None] | None = None,
    on_bytes: Callable[[str, int, int], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> list[str]:
    """Upload *files* to *destination*; returns the remote paths written.

    Uses ``sftp.put`` streaming (no whole-file buffering). Raises
    :class:`PublishError` with a speakable message on any failure.
    ``on_bytes(filename, sent, total)`` reports transfer progress per file;
    ``is_cancelled`` is polled on every block and aborts the transfer with
    :class:`PublishCancelled` (already-completed files stay uploaded).
    """
    from quill.core.ssh.client import SshDependencyError, connect

    remote_paths: list[str] = []
    try:
        connection = connect(
            destination.host,
            port=destination.port,
            username=destination.username,
            password=password,
            trust_first_use=trust_first_use,
        )
    except SshDependencyError as exc:
        raise PublishError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - paramiko raises many shapes
        raise PublishError(f"Could not connect to {destination.host}: {exc}") from exc
    with connection:
        sftp = connection.service._sftp  # the raw handle streams large files
        for local in files:
            if not local.is_file():
                continue
            remote = posixpath.join(destination.remote_dir or "/", local.name)
            if on_progress is not None:
                on_progress(f"Uploading {local.name}...")

            def callback(sent: int, total: int, _name: str = local.name) -> None:
                # paramiko calls this after every block; raising aborts the put.
                if is_cancelled is not None and is_cancelled():
                    raise PublishCancelled("Cancelled — the upload was stopped.")
                if on_bytes is not None:
                    on_bytes(_name, sent, total)

            try:
                sftp.put(  # type: ignore[attr-defined]
                    str(local),
                    remote,
                    confirm=True,
                    callback=None if (on_bytes is None and is_cancelled is None) else callback,
                )
            except PublishCancelled:
                raise
            except Exception as exc:  # noqa: BLE001
                raise PublishError(f"Could not upload {local.name}: {exc}") from exc
            remote_paths.append(remote)
    return remote_paths
