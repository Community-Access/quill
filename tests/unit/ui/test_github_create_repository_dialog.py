"""Create GitHub Repository: every option, and a refusal said before anything is sent."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")


class _Event:
    def __init__(self) -> None:
        self.skipped = False

    def Skip(self) -> None:  # noqa: N802 - wx's name
        self.skipped = True


def test_a_template_with_a_readme_stays_open_and_says_why(wx_session_app: Any) -> None:
    from quill.ui.github_repo_admin_dialogs import CreateRepositoryDialog

    dialog = CreateRepositoryDialog(None, template="o/t")
    try:
        dialog._name_ctrl.SetValue("site")
        dialog._readme_check.SetValue(True)
        event = _Event()
        dialog._on_create(event)
        assert not event.skipped
        assert "brings its own files" in dialog._problem_ctrl.GetValue()
        assert dialog._problem_ctrl.IsShown()

        dialog._readme_check.SetValue(False)
        dialog._branches_check.SetValue(True)
        dialog._visibility_choice.SetSelection(1)
        event = _Event()
        dialog._on_create(event)
        assert event.skipped
        new = dialog._new()
        assert (new.template, new.include_all_branches, new.visibility) == ("o/t", True, "public")
    finally:
        dialog.dialog.Destroy()


def test_a_fresh_repository_takes_licence_gitignore_and_website(wx_session_app: Any) -> None:
    from quill.ui.github_repo_admin_dialogs import CreateRepositoryDialog

    dialog = CreateRepositoryDialog(None)
    try:
        dialog._name_ctrl.SetValue("tool")
        dialog._org_ctrl.SetValue("@acme")
        dialog._homepage_ctrl.SetValue("https://acme.example")
        dialog._gitignore_combo.SetValue("Python")
        dialog._license_choice.SetSelection(1)
        dialog._visibility_choice.SetSelection(1)
        new = dialog._new()
        assert new.owner == "acme" and new.visibility == "public"
        assert (new.gitignore, new.license, new.homepage) == (
            "Python",
            "mit",
            "https://acme.example",
        )
        event = _Event()
        dialog._on_create(event)
        assert event.skipped and not dialog._problem_ctrl.IsShown()
    finally:
        dialog.dialog.Destroy()
