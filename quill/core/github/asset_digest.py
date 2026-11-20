"""Check a downloaded release file against GitHub's digest for it (GX10, complete.md 1.3).

GitHub keeps a SHA-256 ``digest`` for each release file (``sha256:<hex>`` on
the asset). Check Download... on a release file's row reads that digest fresh
from GitHub (:func:`asset_digest`), hashes the file the person downloaded
(:func:`file_sha256`, on this computer, in pieces, so a large file never sits
in memory), and :func:`check_file` says whether the two match.

A match means the file on disk is byte for byte the file GitHub holds. It
does not say who built that file: that is what attestations are for, and
QUILL reads them without checking their signatures
(:data:`quill.core.github.release_evidence.VERIFY_NOTE`).

A file GitHub has no digest for (one uploaded before GitHub kept them) is
said as not checkable, never as a match. wx-free and strict-typed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = ["AssetDigestError", "DigestCheck", "asset_digest", "check_file", "file_sha256"]

_CHUNK = 1024 * 1024


class AssetDigestError(CodedError):
    """The file or its digest could not be read; the message is said."""

    code = "QUILL-GITHUB-ASSET-DIGEST"


@dataclass(frozen=True)
class DigestCheck:
    name: str
    """The release file's name on GitHub."""
    file: str
    """The checked file's name on this computer."""
    expected: str
    """GitHub's digest as it gave it (``sha256:<hex>``), or ``""`` when it has none."""
    actual: str = ""
    """The file's SHA-256, in hexadecimal; ``""`` when it was not hashed."""

    @property
    def algorithm(self) -> str:
        return self.expected.partition(":")[0].casefold() if ":" in self.expected else ""

    @property
    def matched(self) -> bool | None:
        """True or False; None when there was nothing to compare with."""
        if self.algorithm != "sha256" or not self.actual:
            return None
        return self.expected.partition(":")[2].strip().casefold() == self.actual.casefold()

    @property
    def sentence(self) -> str:
        if not self.expected:
            return (
                f"GitHub has no digest for {self.name}, so {self.file} cannot be checked. "
                "Files uploaded before GitHub kept digests have none."
            )
        if self.matched is None:
            return (
                f"GitHub's digest for {self.name} is {self.algorithm or 'of an unknown kind'}, "
                "not SHA-256, so QUILL cannot check it."
            )
        if self.matched:
            return (
                f"{self.file} matches {self.name}: its SHA-256 is the digest GitHub has, "
                f"{self.actual[:12]}."
            )
        return (
            f"{self.file} does not match {self.name}. Its SHA-256 starts {self.actual[:12]}, "
            f"and GitHub's digest starts {self.expected.partition(':')[2][:12]}. "
            "Do not use it; download it again."
        )

    def lines(self) -> list[str]:
        return [
            self.sentence,
            f"GitHub's digest: {self.expected or 'none'}.",
            f"This file's SHA-256: {self.actual or 'not worked out'}.",
        ]


def file_sha256(path: Path, *, should_cancel: Callable[[], bool] | None = None) -> str:
    """The SHA-256 of the file at *path*, read a piece at a time."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_CHUNK):
                if should_cancel is not None and should_cancel():
                    raise AssetDigestError("Checking the file was cancelled.")
                digest.update(chunk)
    except OSError as exc:
        raise AssetDigestError(f"Could not read {path.name}: {exc.strerror or exc}") from exc
    return digest.hexdigest()


def check_file(path: Path, name: str, expected: str) -> DigestCheck:
    """Hash *path* and compare it with *expected*; nothing is hashed when there is no digest."""
    if not expected or not expected.casefold().startswith("sha256:"):
        return DigestCheck(name, path.name, expected)
    return DigestCheck(name, path.name, expected, file_sha256(path))


def asset_digest(api: GitHubApi, repo: str, tag: str, name: str) -> str:
    """GitHub's digest for the file *name* of the release tagged *tag*, read now."""
    release = api.rest("GET", f"/repos/{repo}/releases/tags/{quote(tag, safe='')}").data
    for asset in release.get("assets") or () if isinstance(release, Mapping) else ():
        if isinstance(asset, Mapping) and asset.get("name") == name:
            return str(asset.get("digest") or "")
    raise AssetDigestError(f"{tag} has no file called {name} now.")
