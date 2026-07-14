"""Tests for the build-info generator's pure helpers.

The script (``tools/generate_build_info.py``) is exercised end-to-end
in CI. These unit tests cover the pure helpers (``pep440_version`` and
``display_version``) so a future change to the format does not require
running a full build to catch a regression.
"""

from __future__ import annotations

from generate_build_info import display_version, pep440_version


def test_stable_pep440_returns_base() -> None:
    assert pep440_version("0.7.0", "stable", 0, "1", "20260619") == "0.7.0"


def test_alpha_pep440() -> None:
    assert pep440_version("0.8.0", "alpha", 2, "1", "20260619") == "0.8.0a2"


def test_beta_pep440() -> None:
    assert pep440_version("0.7.0", "beta", 1, "1", "20260619") == "0.7.0b1"


def test_rc_pep440() -> None:
    assert pep440_version("0.7.0", "rc", 3, "1", "20260619") == "0.7.0rc3"


def test_dev_pep440_concatenates_date_and_build_number() -> None:
    # Dev/nightly: 0.8.0.dev20260619142
    assert pep440_version("0.8.0", "dev", 0, "142", "20260619") == "0.8.0.dev20260619142"


def test_stable_display_returns_base() -> None:
    assert display_version("0.7.0", "stable", 0) == "0.7.0"


def test_beta_display_includes_capitalized_channel() -> None:
    assert display_version("0.7.0", "beta", 1) == "0.7.0 Beta 1"


def test_rc_display() -> None:
    assert display_version("0.7.0", "rc", 2) == "0.7.0 Release Candidate 2"


def test_dev_display() -> None:
    assert display_version("0.8.0", "dev", 0) == "0.8.0 Dev"


def test_alpha_display() -> None:
    assert display_version("0.8.0", "alpha", 1) == "0.8.0 Alpha 1"
