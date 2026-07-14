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

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

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
        self._entry.SetName(f"Type {expected} to confirm")
        sizer.Add(self._entry, flag=wx.EXPAND | wx.ALL, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label=confirm_label)
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(wx.Button(panel, wx.ID_CANCEL, label="Cancel"))
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


class CreateRepositoryDialog:
    """Collect a name, description, visibility, and optional org."""

    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(
            parent, title="Create GitHub Repository", style=wx.DEFAULT_DIALOG_STYLE
        )
        panel = wx.Panel(self.dialog)
        sizer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(panel, label="Repository name"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._name_ctrl = wx.TextCtrl(panel)
        self._name_ctrl.SetName("Repository name")
        grid.Add(self._name_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Description (optional)"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._description_ctrl = wx.TextCtrl(panel)
        self._description_ctrl.SetName("Description")
        grid.Add(self._description_ctrl, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(panel, label="Organization (optional; blank = your account)"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._org_ctrl = wx.TextCtrl(panel)
        self._org_ctrl.SetName("Organization, blank for your own account")
        grid.Add(self._org_ctrl, 1, wx.EXPAND)

        sizer.Add(grid, flag=wx.EXPAND | wx.ALL, border=12)

        self._private_check = wx.CheckBox(panel, label="Private repository")
        self._private_check.SetName("Private repository")
        self._private_check.SetValue(True)
        sizer.Add(self._private_check, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Create")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(wx.Button(panel, wx.ID_CANCEL, label="Cancel"))
        btn_sizer.Realize()
        sizer.Add(btn_sizer, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()
        self._name_ctrl.SetFocus()

    def show(self) -> CreateRepositoryResult | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Create GitHub Repository") != wx.ID_OK:
                return None
            name = self._name_ctrl.GetValue().strip()
            if not name:
                return None
            return CreateRepositoryResult(
                name=name,
                description=self._description_ctrl.GetValue().strip(),
                private=self._private_check.GetValue(),
                org=self._org_ctrl.GetValue().strip(),
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
        self._review_spin.SetName("Required approving reviews")
        rules_grid.Add(self._review_spin, 0)

        rules_grid.Add(
            wx.StaticText(panel, label="Required status checks (comma-separated, optional)"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._checks_ctrl = wx.TextCtrl(panel)
        self._checks_ctrl.SetName("Required status checks, comma separated")
        rules_grid.Add(self._checks_ctrl, 1, wx.EXPAND)
        rules_sizer.Add(rules_grid, flag=wx.EXPAND | wx.ALL, border=8)

        self._enforce_admins_check = wx.CheckBox(panel, label="Apply rules to administrators too")
        self._enforce_admins_check.SetName("Apply rules to administrators too")
        rules_sizer.Add(self._enforce_admins_check, flag=wx.ALL, border=8)
        sizer.Add(rules_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK, label="Apply")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(wx.Button(panel, wx.ID_CANCEL, label="Cancel"))
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
            review_count = self._review_spin.GetValue()
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
