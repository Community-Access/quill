"""Tests for the platform-aware UI noun helpers (#37)."""

from __future__ import annotations

import sys

from quill.core import platform_nouns


def test_credential_store_name_windows() -> None:
    if sys.platform != "win32":
        return  # no-op off-Windows
    assert platform_nouns.credential_store_name() == "Windows Credential Manager"


def test_credential_store_name_macos(monkeypatch) -> None:
    monkeypatch.setattr(platform_nouns.sys, "platform", "darwin")
    assert platform_nouns.credential_store_name() == "macOS Keychain"


def test_credential_store_name_neutral_off_platform(monkeypatch) -> None:
    monkeypatch.setattr(platform_nouns.sys, "platform", "linux")
    name = platform_nouns.credential_store_name()
    assert "Credential Manager" not in name
    assert "Keychain" not in name


def test_primary_command_chord_label_windows() -> None:
    if sys.platform != "win32":
        return
    assert platform_nouns.primary_command_chord_label() == "Ctrl+Alt"


def test_primary_command_chord_label_macos(monkeypatch) -> None:
    monkeypatch.setattr(platform_nouns.sys, "platform", "darwin")
    assert platform_nouns.primary_command_chord_label() == "Cmd+Alt"


def test_helpers_read_platform_at_call_time(monkeypatch) -> None:
    """The helper must re-read sys.platform each call so tests can patch it."""
    monkeypatch.setattr(platform_nouns.sys, "platform", "win32")
    assert "Credential Manager" in platform_nouns.credential_store_name()
    monkeypatch.setattr(platform_nouns.sys, "platform", "darwin")
    assert "Keychain" in platform_nouns.credential_store_name()
