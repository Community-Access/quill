"""Unit tests for the rule that suppresses expansion in credential surfaces.

The important property is that the decision uses the foreground window only --
never the typed text -- so these tests pass process/title/class and nothing else.
"""

from __future__ import annotations

import pytest

from quill.core.expansion.targets import is_denied_target


@pytest.mark.parametrize(
    "process",
    ["1password.exe", "KeePassXC.exe", "bitwarden.exe", "LogonUI.exe", "consent.exe"],
)
def test_password_and_credential_processes_are_denied(process: str) -> None:
    assert is_denied_target(process) is True


def test_process_matching_ignores_case() -> None:
    assert is_denied_target("LastPass.EXE") is True


def test_ordinary_applications_are_allowed() -> None:
    assert is_denied_target("notepad.exe", "Untitled - Notepad", "Notepad") is False


def test_credential_window_class_is_denied_whatever_owns_it() -> None:
    assert is_denied_target("explorer.exe", "", "Credential Dialog Xaml Host") is True


@pytest.mark.parametrize(
    "title",
    [
        "Sign in to your account",
        "Please log on",
        "Enter your password",
        "Windows Security",
        "Unlock your vault",
        "Two-factor authentication",
    ],
)
def test_credential_titles_are_denied(title: str) -> None:
    assert is_denied_target("chrome.exe", title) is True


def test_user_exclusions_are_honoured() -> None:
    assert is_denied_target("notepad.exe", extra_processes={"Notepad.exe"}) is True
    assert is_denied_target("notepad.exe", extra_processes={"other.exe"}) is False


def test_unknown_window_is_allowed_but_only_on_its_own_merits() -> None:
    # An empty answer means "could not read the window", which must not by
    # itself deny every expansion -- otherwise a transient failure silently
    # turns the whole feature off.
    assert is_denied_target("", "", "") is False
