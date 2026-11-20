"""Check Download...: a downloaded release file against GitHub's SHA-256 digest (GX10)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from quill.core.github.asset_digest import (
    AssetDigestError,
    asset_digest,
    check_file,
    file_sha256,
)
from quill.core.github.rest_transport import RestResponse

BODY = b"QUILL release file\n" * 1000
GOOD = "sha256:" + hashlib.sha256(BODY).hexdigest()


class FakeApi:
    def __init__(self, release: Any) -> None:
        self.release = release
        self.paths: list[str] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        assert method == "GET"
        self.paths.append(path)
        return RestResponse(200, {}, self.release)

    def graphql(self, *_a: Any) -> Any:
        raise AssertionError("not used")


@pytest.fixture
def download(tmp_path: Path) -> Path:
    path = tmp_path / "quill-setup.exe"
    path.write_bytes(BODY)
    return path


def test_a_matching_file_is_said_to_match(download: Path) -> None:
    found = check_file(download, "quill-setup.exe", GOOD)
    assert found.matched is True
    assert found.sentence == (
        "quill-setup.exe matches quill-setup.exe: its SHA-256 is the digest GitHub has, "
        f"{GOOD[7:19]}."
    )
    assert found.lines()[1] == f"GitHub's digest: {GOOD}."


def test_a_changed_file_is_said_not_to_match(download: Path) -> None:
    download.write_bytes(BODY + b"tampered")
    found = check_file(download, "quill-setup.exe", GOOD)
    assert found.matched is False
    assert found.sentence.startswith("quill-setup.exe does not match quill-setup.exe.")
    assert found.sentence.endswith("Do not use it; download it again.")


def test_the_digest_is_compared_without_regard_to_case(download: Path) -> None:
    assert check_file(download, "x", "SHA256:" + GOOD[7:].upper()).matched is True


def test_no_digest_is_never_a_match_and_the_file_is_not_hashed(download: Path) -> None:
    found = check_file(download, "old.zip", "")
    assert found.matched is None and found.actual == ""
    assert found.sentence.startswith("GitHub has no digest for old.zip")
    other = check_file(download, "x", "sha512:abc")
    assert other.matched is None and "not SHA-256" in other.sentence


def test_hashing_reads_in_pieces_and_says_an_unreadable_file(tmp_path: Path) -> None:
    big = tmp_path / "big.bin"
    big.write_bytes(b"a" * (3 * 1024 * 1024 + 5))
    assert file_sha256(big) == hashlib.sha256(big.read_bytes()).hexdigest()
    with pytest.raises(AssetDigestError, match="Could not read missing.bin"):
        file_sha256(tmp_path / "missing.bin")
    with pytest.raises(AssetDigestError, match="cancelled"):
        file_sha256(big, should_cancel=lambda: True)


def test_the_digest_is_read_fresh_from_the_release() -> None:
    api = FakeApi({"assets": [{"name": "a.zip", "digest": GOOD}, {"name": "b.zip"}]})
    assert asset_digest(api, "o/r", "v1.0", "a.zip") == GOOD
    assert asset_digest(api, "o/r", "v1.0", "b.zip") == ""
    assert api.paths[0] == "/repos/o/r/releases/tags/v1.0"
    with pytest.raises(AssetDigestError, match="v1.0 has no file called c.zip now."):
        asset_digest(api, "o/r", "v1.0", "c.zip")
