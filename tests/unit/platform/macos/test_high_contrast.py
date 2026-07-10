from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="macOS Increase Contrast is macOS-only"
)

from quill.platform.macos import high_contrast  # noqa: E402


class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


def test_returns_bool() -> None:
    assert isinstance(high_contrast.is_high_contrast_enabled(), bool)


def test_detects_high_contrast_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """increaseContrast=1 reads as enabled, not just 'a bool was returned'."""
    monkeypatch.setattr(
        high_contrast.subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(0, "1"),
    )
    assert high_contrast.is_high_contrast_enabled() is True


@pytest.mark.parametrize("stdout", ["0", "", "NO", "false"])
def test_detects_high_contrast_off(monkeypatch: pytest.MonkeyPatch, stdout: str) -> None:
    """Any non-affirmative value (including empty) reads as disabled."""
    monkeypatch.setattr(
        high_contrast.subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(0, stdout),
    )
    assert high_contrast.is_high_contrast_enabled() is False


def test_defaults_off_when_defaults_cli_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A nonzero exit (preference key absent) reads as disabled, not an error."""
    monkeypatch.setattr(
        high_contrast.subprocess,
        "run",
        lambda *a, **k: _FakeCompleted(1, ""),
    )
    assert high_contrast.is_high_contrast_enabled() is False


def test_defaults_off_when_defaults_cli_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the `defaults` binary can't be invoked, fall back to disabled."""

    def _raise(*a, **k):
        raise OSError("command not found")

    monkeypatch.setattr(high_contrast.subprocess, "run", _raise)
    assert high_contrast.is_high_contrast_enabled() is False
