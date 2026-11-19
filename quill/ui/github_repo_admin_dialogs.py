"""Dialogs for repository-lifecycle GitHub actions: create, rename,
visibility, default branch, fork, branch protection, and multi-file commits.

Sibling of :mod:`quill.ui.github_dialogs` (consent/sign-in/browse) and
:mod:`quill.ui.github_items_dialog` (issues/PRs/branches viewer). This module
holds the custom multi-field dialogs; simple single-value prompts and
confirmations are built inline in :mod:`quill.ui.main_frame_github_admin`
with stock wx dialogs, matching the precedent in
:mod:`quill.ui.main_frame_git_sync`.

Accessibility contract (same as every other GitHub dialog in this package):
every control has a ``SetName``, all navigation is keyboard-completable, no
custom-drawn controls, and every dialog goes through ``apply_modal_ids`` +
``show_modal_dialog`` -- never a raw ``ShowModal()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.github.repo_create import (
    GITIGNORE_TEMPLATES,
    LICENSE_TEMPLATES,
    NewRepository,
    problem,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog
from quill.ui.spin_value import spin_value

# ---------------------------------------------------------------------------
# Typed confirmation -- the stronger gate for the four highest-consequence
# actions (merge a pull request, delete a branch, rename a repository, flip
# a repository's visibility). Retyping the exact name/number is a deliberate
# extra step beyond a plain Yes/No: it protects against an accidental Enter
# press landing on a destructive default, and for a screen-reader user
# reading a Yes/No dialog by ear, retyping something specific removes any
# ambiguity about which item the confirmation applies to.
# ---------------------------------------------------------------------------


class TypedConfirmDialog:
    """Ask the user to retype *expected* exactly before proceeding.

    Returns True only when the typed text matches *expected* verbatim (case-
    sensitive) and the user pressed OK; anything else (Cancel, a mismatch, a
    blank field) is a decline. A mismatch does not loop or nag -- it simply
    declines, matching QUILL's convention that a cancelled/failed
    confirmation is always silent-safe (nothing happens) rather than a retry
    prompt that could pressure a user into pasting the value blindly.
    """

    def __init__(
        self,
        parent: object,
        *,
        title: str,
        message: str,
        expected: str,
        confirm_label: str = "Confirm",
    ) -> None:
        import wx

        self._wx = wx
        self._expected = expected
        self.dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(panel, label=message)
        intro.Wrap(440)
        sizer.Add(intro, flag=wx.ALL, border=12)

        label = wx.StaticText(panel, label=f'Type "{expected}" to confirm:')
        sizer.Add(label, flag=wx.LEFT | wx.RIGHT, border=12)
        self._entry = wx.TextCtrl(panel)
        self._entry.SetHelpText("Type exactly what the line above asks for, to confirm.")
        self._entry.SetName(f"Type {expected} to confirm")
        sizer.Add(self._entry, flag=wx.EXPAND | wx.ALL, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=confirm_label)
        ok_btn.SetHelpText("Do it on GitHub. This is the button that makes the change.")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        cancel_button = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_button.SetHelpText("Close without changing anything. Escape does the same.")
        btn_sizer.AddButton(cancel_button)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        self._entry.SetFocus()

    def show(self) -> bool:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            answer = show_modal_dialog(self.dialog, self.dialog.GetTitle())
            if answer != wx.ID_OK:
                return False
            return self._entry.GetValue() == self._expected
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Create repository
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CreateRepositoryResult:
    name: str
    description: str
    private: bool
    org: str  # "" for the authenticated user's own account
    new: NewRepository | None = None
    """Every option asked, for :func:`quill.core.github.repo_create.create_kwargs`."""


_VISIBILITY_WORDS = ("Private", "Public")
_NO_LICENSE = "No licence"


class CreateRepositoryDialog:
    """Every option GitHub's create and generate routes take (GitHub PRD 14.1).

    Owner, name, description, website and visibility; then how it starts: a
    template repository (with all its branches or only the default), or a
    README, a .gitignore template and a licence. OK checks the combination
    with :func:`quill.core.github.repo_create.problem` and, when GitHub would
    refuse it, says why in the Problem box and stays open.
    """

    def __init__(self, parent: object, *, template: str = "") -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(
            parent, title="Create GitHub Repository", style=wx.DEFAULT_DIALOG_STYLE
        )
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._problem_ctrl = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_MULTILINE)
        self._problem_ctrl.SetHelpText(
            "Why GitHub would refuse what is chosen, and what to change."
        )
        self._problem_ctrl.SetName("Problem")
        self._problem_ctrl.Hide()
        sizer.Add(self._problem_ctrl, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, border=12)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        def row(label: str, ctrl: Any) -> None:
            grid.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        self._org_ctrl = wx.TextCtrl(panel)
        self._org_ctrl.SetHelpText(
            "An organization to create it in. Leave it empty to create it on your account."
        )
        self._org_ctrl.SetName("Owner, blank for your own account")
        row("Owner (optional; blank = your account)", self._org_ctrl)
        self._name_ctrl = wx.TextCtrl(panel)
        self._name_ctrl.SetHelpText("The new repository's name, such as my-project.")
        self._name_ctrl.SetName("Repository name")
        row("Repository name", self._name_ctrl)
        self._description_ctrl = wx.TextCtrl(panel)
        self._description_ctrl.SetHelpText(
            "A short sentence about what the repository is for. You can leave it empty."
        )
        self._description_ctrl.SetName("Description")
        row("Description (optional)", self._description_ctrl)
        self._homepage_ctrl = wx.TextCtrl(panel)
        self._homepage_ctrl.SetHelpText(
            "An address shown beside the description, such as the project's site."
        )
        self._homepage_ctrl.SetName("Website")
        row("Website (optional)", self._homepage_ctrl)

        grid.Add(wx.StaticText(panel, label="Visibility"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._visibility_choice = wx.Choice(panel, choices=list(_VISIBILITY_WORDS))
        self._visibility_choice.SetSelection(0)
        self._visibility_choice.SetHelpText("Private: only people you add. Public: everyone.")
        self._visibility_choice.SetName("Visibility")
        grid.Add(self._visibility_choice, 1, wx.EXPAND)

        self._template_ctrl = wx.TextCtrl(panel, value=template)
        self._template_ctrl.SetHelpText(
            "A template repository to copy, as owner/name. Leave it empty to start a new one."
        )
        self._template_ctrl.SetName("Template repository, blank to start fresh")
        row("Template (optional, owner/name)", self._template_ctrl)

        grid.Add(wx.StaticText(panel, label=".gitignore template"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._gitignore_combo = wx.ComboBox(panel, choices=["", *GITIGNORE_TEMPLATES])
        self._gitignore_combo.SetHelpText(
            "Files Git should ignore, from GitHub's templates, such as Python or Node. "
            "Type any template name GitHub lists, or leave it empty."
        )
        self._gitignore_combo.SetName(".gitignore template")
        grid.Add(self._gitignore_combo, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Licence"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._license_keys = ["", *LICENSE_TEMPLATES]
        self._license_choice = wx.Choice(panel, choices=[_NO_LICENSE, *LICENSE_TEMPLATES.values()])
        self._license_choice.SetSelection(0)
        self._license_choice.SetHelpText(
            "The licence GitHub adds as a LICENSE file, or none. Not with a template."
        )
        self._license_choice.SetName("Licence")
        grid.Add(self._license_choice, 1, wx.EXPAND)

        sizer.Add(grid, flag=wx.EXPAND | wx.ALL, border=12)

        self._branches_check = wx.CheckBox(panel, label="Include all of the template's branches")
        self._branches_check.SetHelpText(
            "Copy every branch of the template, not only its default branch."
        )
        self._branches_check.SetName("Include all of the template's branches")
        sizer.Add(self._branches_check, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self._readme_check = wx.CheckBox(panel, label="Add a README")
        self._readme_check.SetHelpText(
            "Start with a first commit holding a README, so it can be cloned at once."
        )
        self._readme_check.SetName("Add a README")
        sizer.Add(self._readme_check, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Create")
        ok_btn.SetHelpText("Do it on GitHub. This is the button that makes the change.")
        ok_btn.SetDefault()
        ok_btn.Bind(wx.EVT_BUTTON, self._on_create)
        btn_sizer.AddButton(ok_btn)
        cancel_button = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_button.SetHelpText("Close without changing anything. Escape does the same.")
        btn_sizer.AddButton(cancel_button)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        self._panel = panel
        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        self._name_ctrl.SetFocus()

    def _new(self) -> NewRepository:
        visibility = ("private", "public")[max(0, self._visibility_choice.GetSelection())]
        return NewRepository(
            name=self._name_ctrl.GetValue().strip(),
            owner=self._org_ctrl.GetValue().strip().lstrip("@"),
            description=self._description_ctrl.GetValue().strip(),
            homepage=self._homepage_ctrl.GetValue().strip(),
            visibility=visibility,
            template=self._template_ctrl.GetValue().strip(),
            include_all_branches=self._branches_check.GetValue(),
            auto_init=self._readme_check.GetValue(),
            gitignore=self._gitignore_combo.GetValue().strip(),
            license=self._license_keys[max(0, self._license_choice.GetSelection())],
        )

    def _on_create(self, event: Any) -> None:
        why = problem(self._new())
        if not why:
            event.Skip()
            return
        # Stay open and say why: focus on the Problem box reads it.
        self._problem_ctrl.SetValue(why)
        self._problem_ctrl.Show()
        self._panel.Layout()
        self.dialog.Fit()
        self._problem_ctrl.SetFocus()

    def show(self) -> CreateRepositoryResult | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Create GitHub Repository") != wx.ID_OK:
                return None
            new = self._new()
            if not new.name:
                return None
            return CreateRepositoryResult(
                name=new.name,
                description=new.description,
                private=new.private,
                org=new.owner,
                new=new,
            )
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Branch protection wizard
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class BranchProtectionResult:
    branch: str
    remove: bool  # True = clear all protection instead of applying it
    required_approving_review_count: int | None
    required_status_checks: tuple[str, ...]
    enforce_admins: bool


class BranchProtectionDialog:
    """A small wizard: pick a branch, then either protect it (with the
    fields below) or clear its existing protection."""

    def __init__(self, parent: object, *, branches: tuple[str, ...], default_branch: str) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(
            parent, title="Configure Branch Protection", style=wx.DEFAULT_DIALOG_STYLE
        )
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(panel, label="Branch"), 0, wx.ALIGN_CENTER_VERTICAL)
        choices = list(branches) or [default_branch]
        self._branch_choice = wx.Choice(panel, choices=choices)
        self._branch_choice.SetHelpText("The branch these protection rules are for.")
        self._branch_choice.SetName("Branch to configure")
        initial = choices.index(default_branch) if default_branch in choices else 0
        self._branch_choice.SetSelection(initial)
        grid.Add(self._branch_choice, 1, wx.EXPAND)
        sizer.Add(grid, flag=wx.EXPAND | wx.ALL, border=12)

        self._remove_check = wx.CheckBox(
            panel, label="Remove all protection from this branch instead"
        )
        self._remove_check.SetName("Remove all protection from this branch instead")
        sizer.Add(self._remove_check, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        self._remove_check.Bind(wx.EVT_CHECKBOX, self._on_remove_toggled)

        rules_box = wx.StaticBox(panel, label="Protection rules (applied when not removing)")
        rules_sizer = wx.StaticBoxSizer(rules_box, wx.VERTICAL)
        rules_grid = wx.FlexGridSizer(0, 2, 8, 8)
        rules_grid.AddGrowableCol(1, 1)

        rules_grid.Add(
            wx.StaticText(panel, label="Required approving reviews (0 = not required)"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._review_spin = wx.SpinCtrl(panel, min=0, max=6, initial=0)
        self._review_spin.SetHelpText(
            "How many approving reviews a pull request needs before it can merge."
        )
        set_accessible_name(self._review_spin, "Required approving reviews")
        rules_grid.Add(self._review_spin, 0)

        rules_grid.Add(
            wx.StaticText(panel, label="Required status checks (comma-separated, optional)"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._checks_ctrl = wx.TextCtrl(panel)
        self._checks_ctrl.SetHelpText("Checks that must pass before merging, separated by commas.")
        self._checks_ctrl.SetName("Required status checks, comma separated")
        rules_grid.Add(self._checks_ctrl, 1, wx.EXPAND)
        rules_sizer.Add(rules_grid, flag=wx.EXPAND | wx.ALL, border=8)

        self._enforce_admins_check = wx.CheckBox(panel, label="Apply rules to administrators too")
        self._enforce_admins_check.SetName("Apply rules to administrators too")
        rules_sizer.Add(self._enforce_admins_check, flag=wx.ALL, border=8)
        sizer.Add(rules_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Apply")
        ok_btn.SetHelpText("Do it on GitHub. This is the button that makes the change.")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        cancel_button = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_button.SetHelpText("Close without changing anything. Escape does the same.")
        btn_sizer.AddButton(cancel_button)
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        self._apply_remove_enablement()

    def _on_remove_toggled(self, _event: object) -> None:
        self._apply_remove_enablement()

    def _apply_remove_enablement(self) -> None:
        enabled = not self._remove_check.GetValue()
        for ctrl in (self._review_spin, self._checks_ctrl, self._enforce_admins_check):
            ctrl.Enable(enabled)

    def show(self) -> BranchProtectionResult | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Configure Branch Protection") != wx.ID_OK:
                return None
            branch = self._branch_choice.GetStringSelection()
            if not branch:
                return None
            remove = self._remove_check.GetValue()
            review_count = spin_value(self._review_spin)
            checks = tuple(
                part.strip() for part in self._checks_ctrl.GetValue().split(",") if part.strip()
            )
            return BranchProtectionResult(
                branch=branch,
                remove=remove,
                required_approving_review_count=review_count if review_count > 0 else None,
                required_status_checks=checks,
                enforce_admins=self._enforce_admins_check.GetValue(),
            )
        finally:
            self.dialog.Destroy()


__all__ = [
    "BranchProtectionDialog",
    "BranchProtectionResult",
    "CreateRepositoryDialog",
    "CreateRepositoryResult",
    "TypedConfirmDialog",
]
