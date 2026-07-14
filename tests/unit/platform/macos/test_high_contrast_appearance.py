"""Tests for the macOS high-contrast detection.

These run on every platform: the helper is pure ``defaults``-CLI parsing and is
exercised by faking ``subprocess.run``. The Dark Mode and Reduce Motion probes
prototyped under #6 were removed as dead code (no consumer; wx
``SystemSettings.GetAppearance`` reports Dark Mode and this wxPython app has no
visual animations to gate on Reduce Motion), so only high contrast is covered
here.
"""

from __future__ import annotations

from quill.platform.macos import high_contrast as hc


class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


def _fake_run(table: dict[tuple[str, str], tuple[int, str]]):
    """Return a ``subprocess.run`` replacement keyed by (domain, key)."""

    def _run(args, **kwargs):  # noqa: ANN001 - matches subprocess.run signature
        domain, key = args[2], args[3]
        rc, stdout = table.get((domain, key), (1, ""))
        return _FakeCompleted(rc, stdout)

    return _run


def test_is_high_contrast_enabled_still_works(monkeypatch) -> None:
    monkeypatch.setattr(
        hc.subprocess,
        "run",
        _fake_run({("com.apple.universalaccess", "increaseContrast"): (0, "1")}),
    )
    assert hc.is_high_contrast_enabled() is True


def test_is_high_contrast_disabled_when_absent(monkeypatch) -> None:
    # Key absent -> nonzero exit -> disabled (regression of the original behavior).
    monkeypatch.setattr(hc.subprocess, "run", _fake_run({}))
    assert hc.is_high_contrast_enabled() is False


def test_read_defaults_returns_none_on_oserror(monkeypatch) -> None:
    def _raise(*a, **k):
        raise OSError("command not found")

    monkeypatch.setattr(hc.subprocess, "run", _raise)
    assert hc._read_defaults("com.apple.universalaccess", "increaseContrast") is None
    assert hc.is_high_contrast_enabled() is False


def test_neutral_module_exposes_high_contrast() -> None:
    import quill.platform.high_contrast as neutral

    assert callable(neutral.is_high_contrast_enabled)
    assert "is_high_contrast_enabled" in neutral.__all__
