"""FUX-16: a failure in plain words, of a kind a next step can fit.

``plain_failure`` tells a full disk, a denied permission, a missing file, a
device, the network, an expired sign-in, a missing part and an unsupported
request apart, and never puts the exception's raw text in the sentence.
``failure_details`` is what Copy Details copies: versions and the error,
redacted.
"""

from __future__ import annotations

import errno

import pytest

from quill.core import command_failure as cf
from quill.core.error_codes import CodedError


class _HttpError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(f"{status} Client Error: secret body")
        self.status = status


class _Response:
    def __init__(self, status: int) -> None:
        self.status_code = status


class _RequestsLike(OSError):
    def __init__(self, status: int) -> None:
        super().__init__("HTTP error")
        self.response = _Response(status)


class ConnectTimeout(Exception):
    """Named like requests' class; matched by name so core need not import it."""


class _Coded(CodedError):
    code = "QUILL-TEST-FAILURE-WORDS"
    user_hint = "Open Settings, Recording, to choose another folder."


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (OSError(errno.ENOSPC, "No space left on device"), cf.DISK_FULL),
        (PermissionError(errno.EACCES, "Permission denied", "C:/x"), cf.DENIED),
        (FileNotFoundError(errno.ENOENT, "No such file"), cf.MISSING),
        (ConnectionResetError(errno.ECONNRESET, "reset"), cf.OFFLINE),
        (TimeoutError("timed out"), cf.OFFLINE),
        (ConnectTimeout("slow"), cf.OFFLINE),
        (_HttpError(401), cf.SIGNED_OUT),
        (_HttpError(403), cf.DENIED),
        (_HttpError(503), cf.OFFLINE),
        (_RequestsLike(401), cf.SIGNED_OUT),
        (ModuleNotFoundError("No module named 'x'"), cf.UNAVAILABLE),
        (NotImplementedError(), cf.UNSUPPORTED),
        (ValueError("boom"), cf.OTHER),
    ],
)
def test_each_kind_is_told_apart(error: BaseException, kind: str) -> None:
    assert cf.plain_failure(error).kind == kind


def test_windows_error_numbers_are_read_too() -> None:
    sharing = OSError(None, "in use")
    sharing.winerror = 32  # type: ignore[attr-defined]
    full = OSError(None, "full")
    full.winerror = 112  # type: ignore[attr-defined]
    not_ready = OSError(None, "not ready")
    not_ready.winerror = 21  # type: ignore[attr-defined]
    assert cf.plain_failure(sharing).kind == cf.DENIED
    assert cf.plain_failure(full).kind == cf.DISK_FULL
    assert cf.plain_failure(not_ready).kind == cf.DEVICE


def test_the_sentence_never_carries_the_raw_text() -> None:
    words = cf.plain_failure(_HttpError(401))
    assert "secret body" not in words.reason
    assert "401" not in words.reason
    other = cf.plain_failure(ValueError("Traceback: line 12 in foo.py"))
    assert "foo.py" not in other.reason
    assert "Copy Details" in other.reason


def test_only_a_passing_failure_is_transient() -> None:
    assert cf.plain_failure(TimeoutError()).transient is True
    assert cf.plain_failure(OSError(errno.ENOSPC, "full")).transient is False


def test_a_coded_error_keeps_its_own_words_without_the_code() -> None:
    words = cf.plain_failure(_Coded("The recordings folder could not be made."))
    assert words.reason.startswith("The recordings folder could not be made.")
    assert "Open Settings, Recording" in words.reason
    assert "QUILL-TEST" not in words.reason


def test_a_coded_error_wrapping_a_full_disk_is_a_full_disk() -> None:
    try:
        try:
            raise OSError(errno.ENOSPC, "No space left on device")
        except OSError as inner:
            raise _Coded(f"Could not start: {inner}") from inner
    except _Coded as outer:
        words = cf.plain_failure(outer)
    assert words.kind == cf.DISK_FULL
    assert "Errno" not in words.reason


def test_details_carry_versions_and_the_error_redacted() -> None:
    error = PermissionError(errno.EACCES, "Permission denied", "C:/Users/someone/Documents/a.txt")
    text = cf.failure_details(error, app="QUILL Lite", version="9.9", context="Opening a.txt")
    assert "App: QUILL Lite 9.9" in text
    assert "Windows:" in text
    assert "What was happening: Opening a.txt" in text
    assert "Kind: denied" in text
    assert "PermissionError" in text


def test_details_redact_a_token() -> None:
    error = ValueError("request failed with token ghp_" + "a" * 36)
    text = cf.failure_details(error, app="QUILL", version="1")
    assert "ghp_" + "a" * 36 not in text


def test_every_save_sentence_says_the_text_is_kept() -> None:
    for error in (
        OSError(errno.ENOSPC, "full"),
        PermissionError(errno.EACCES, "denied"),
        FileNotFoundError(errno.ENOENT, "gone"),
        OSError(errno.EIO, "I/O error"),
    ):
        sentence = cf.save_failure_sentence("notes.md", error, app="QUILL Lite")
        assert "your text is still open and unsaved" in sentence
        assert "notes.md" in sentence
        assert "QUILL Lite" in sentence
        assert "I/O error" not in sentence
