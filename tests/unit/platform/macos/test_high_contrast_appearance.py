"""Tests for the macOS appearance/motion detection added in #6.

Unlike ``test_high_contrast.py`` (which is skipif-darwin because it predates the
shared ``_read_defaults`` helper), these run on every platform: the helpers are
pure ``defaults``-CLI parsing and are exercised by faking ``subprocess.run``.
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


def test_is_reduce_motion_enabled(monkeypatch) -> None:
    monkeypatch.setattr(
        hc.subprocess,
        "run",
        _fake_run({("com.apple.universalaccess", "reduceMotion"): (0, "1")}),
    )
    assert hc.is_reduce_motion_enabled() is True


def test_is_reduce_motion_disabled(monkeypatch) -> None:
    monkeypatch.setattr(hc.subprocess, "run", _fake_run({}))
    assert hc.is_reduce_motion_enabled() is False


def test_is_dark_mode_enabled(monkeypatch) -> None:
    monkeypatch.setattr(
        hc.subprocess, "run", _fake_run({("-g", "AppleInterfaceStyle"): (0, "Dark")})
    )
    assert hc.is_dark_mode_enabled() is True


def test_is_dark_mode_case_insensitive(monkeypatch) -> None:
    monkeypatch.setattr(
        hc.subprocess, "run", _fake_run({("-g", "AppleInterfaceStyle"): (0, "dark")})
    )
    assert hc.is_dark_mode_enabled() is True


def test_is_dark_mode_disabled_in_light_mode(monkeypatch) -> None:
    # Light mode: the key is absent -> nonzero exit -> disabled.
    monkeypatch.setattr(hc.subprocess, "run", _fake_run({}))
    assert hc.is_dark_mode_enabled() is False


def test_is_dark_mode_disabled_when_value_is_not_dark(monkeypatch) -> None:
    # A future value like "Auto" must not read as dark.
    monkeypatch.setattr(
        hc.subprocess, "run", _fake_run({("-g", "AppleInterfaceStyle"): (0, "Auto")})
    )
    assert hc.is_dark_mode_enabled() is False


def test_macos_appearance_reads_all_three(monkeypatch) -> None:
    monkeypatch.setattr(
        hc.subprocess,
        "run",
        _fake_run({
            ("com.apple.universalaccess", "increaseContrast"): (0, "1"),
            ("com.apple.universalaccess", "reduceMotion"): (0, "1"),
            ("-g", "AppleInterfaceStyle"): (0, "Dark"),
        }),
    )
    appearance = hc.macos_appearance()
    assert appearance.high_contrast is True
    assert appearance.dark_mode is True
    assert appearance.reduce_motion is True


def test_macos_appearance_defaults_off_when_unreadable(monkeypatch) -> None:
    monkeypatch.setattr(hc.subprocess, "run", _fake_run({}))
    appearance = hc.macos_appearance()
    assert appearance == hc.MacOSAppearance(
        high_contrast=False, dark_mode=False, reduce_motion=False
    )


def test_read_defaults_returns_none_on_oserror(monkeypatch) -> None:
    def _raise(*a, **k):
        raise OSError("command not found")

    monkeypatch.setattr(hc.subprocess, "run", _raise)
    assert hc._read_defaults("-g", "AppleInterfaceStyle") is None
    assert hc.is_dark_mode_enabled() is False


def test_neutral_module_exposes_new_hooks() -> None:
    import quill.platform.high_contrast as neutral

    assert callable(neutral.is_dark_mode_enabled)
    assert callable(neutral.is_reduce_motion_enabled)
    assert callable(neutral.macos_appearance)
    assert "is_dark_mode_enabled" in neutral.__all__
