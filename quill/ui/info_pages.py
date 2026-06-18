"""Native wx replacements for web-view-based informational pages.

All surfaces here use only wx controls so screen readers never have to
switch between Browse mode and Forms/Application mode.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any


def _md_to_plain(text: str) -> str:
    """Convert the subset of Markdown used in QUILL info pages to plain text."""
    lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            heading = m.group(2).strip()
            underline = ("=" if len(m.group(1)) == 1 else "-") * min(len(heading), 60)
            lines.append(heading)
            lines.append(underline)
            continue
        lines.append(line)
    result = "\n".join(lines)
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", result)
    result = re.sub(r"`(.+?)`", r"\1", result)
    result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", result)
    return result.strip()


def show_about_quill_native(
    parent: Any,
    wx: Any,
    markdown_text: str,
    open_notices_fn: Callable[[], None],
    show_modal_dialog: Callable[[Any, str], int],
) -> None:
    """Modal About Quill dialog backed by a read-only TextCtrl."""
    from quill.ui.dialog_contract import apply_modal_ids

    text = _md_to_plain(markdown_text)
    dialog = wx.Dialog(
        parent,
        title="About Quill",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((660, 580))
    sizer = wx.BoxSizer(wx.VERTICAL)
    body = wx.TextCtrl(
        dialog,
        value=text,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL | wx.TE_RICH2,
        name="about_body",
    )
    body.SetMinSize((-1, 300))
    sizer.Add(body, 1, wx.EXPAND | wx.ALL, 12)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_sizer.AddStretchSpacer()
    notices_btn = wx.Button(dialog, wx.ID_HELP, label="Open Third-Party Notices")
    close_btn = wx.Button(dialog, wx.ID_OK, label="Close")
    close_btn.SetDefault()
    notices_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_HELP))
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
    btn_sizer.Add(notices_btn, 0, wx.RIGHT, 8)
    btn_sizer.Add(close_btn, 0)
    sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
    wx.CallAfter(body.SetFocus)
    try:
        result = show_modal_dialog(dialog, "About Quill")
    finally:
        dialog.Destroy()
    if result == wx.ID_HELP:
        open_notices_fn()


def show_startup_wizard_page_native(
    parent: Any,
    wx: Any,
    steps: list[tuple[str, str, str]],
    show_modal_dialog: Callable[[Any, str], int],
) -> None:
    """Modal Startup Wizard overview dialog with a native ListCtrl for steps."""
    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.Dialog(
        parent,
        title="Startup Wizard",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((660, 520))
    sizer = wx.BoxSizer(wx.VERTICAL)

    intro = wx.TextCtrl(
        dialog,
        value=(
            "Welcome to Quill - a fast, friendly writing app built to work beautifully "
            "with your screen reader.\n\n"
            "Each step below is optional and takes a moment. "
            "You can stop any time and come back later. "
            "Nothing is downloaded until you say yes."
        ),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        name="wizard_page_intro",
    )
    intro.SetMinSize((-1, 80))
    sizer.Add(intro, 0, wx.EXPAND | wx.ALL, 12)

    steps_list = wx.ListCtrl(
        dialog,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES,
        name="wizard_page_steps",
    )
    steps_list.AppendColumn("Step", width=200)
    steps_list.AppendColumn("Status", width=100)
    steps_list.AppendColumn("Description", width=300)
    for i, (step, status, detail) in enumerate(steps):
        steps_list.InsertItem(i, step)
        steps_list.SetItem(i, 1, status)
        steps_list.SetItem(i, 2, detail)
    sizer.Add(steps_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    btn_sizer = wx.StdDialogButtonSizer()
    close_btn = wx.Button(dialog, wx.ID_OK, label="Close")
    close_btn.SetDefault()
    btn_sizer.AddButton(close_btn)
    btn_sizer.Realize()
    sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
    wx.CallAfter(steps_list.SetFocus)
    try:
        show_modal_dialog(dialog, "Startup Wizard")
    finally:
        dialog.Destroy()


def show_whisperer_about_native(
    parent: Any,
    wx: Any,
    roadmap_rows: list[tuple[str, str, str, str]],
    principles_rows: list[tuple[str, str]],
    show_modal_dialog: Callable[[Any, str], int],
) -> None:
    """Modal About BITS Whisperer dialog with tabbed native ListCtrls."""
    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.Dialog(
        parent,
        title="About BITS Whisperer",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((760, 540))
    sizer = wx.BoxSizer(wx.VERTICAL)
    nb = wx.Notebook(dialog)

    # Overview tab
    overview_panel = wx.Panel(nb)
    ov_sizer = wx.BoxSizer(wx.VERTICAL)
    ov_text = wx.TextCtrl(
        overview_panel,
        value=(
            "The future is bright. BITS Whisperer patterns are being evaluated "
            "for selective adoption inside Quill to improve accessibility, reliability, "
            "and creative flow.\n\n"
            "Quill will progressively absorb proven ideas from BITS Whisperer in focused "
            "phases, while preserving Quill's writing-first experience.\n\n"
            "Next steps:\n"
            "1. Use Startup Wizard to configure profile, AI, and speech foundation.\n"
            "2. Use Status Page to check on downloads, speech, and what's turned on.\n"
            "3. Iterate in small, accessible milestones with clear release notes."
        ),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        name="whisperer_about_overview",
    )
    ov_sizer.Add(ov_text, 1, wx.EXPAND | wx.ALL, 8)
    overview_panel.SetSizer(ov_sizer)
    nb.AddPage(overview_panel, "Overview")

    # Roadmap tab
    roadmap_panel = wx.Panel(nb)
    rm_sizer = wx.BoxSizer(wx.VERTICAL)
    roadmap_list = wx.ListCtrl(
        roadmap_panel,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES,
        name="whisperer_roadmap",
    )
    roadmap_list.AppendColumn("Capability", width=180)
    roadmap_list.AppendColumn("Whisperer Source", width=180)
    roadmap_list.AppendColumn("Phase", width=70)
    roadmap_list.AppendColumn("Quill Plan", width=240)
    for i, (cap, source, phase, notes) in enumerate(roadmap_rows):
        roadmap_list.InsertItem(i, cap)
        roadmap_list.SetItem(i, 1, source)
        roadmap_list.SetItem(i, 2, phase)
        roadmap_list.SetItem(i, 3, notes)
    rm_sizer.Add(roadmap_list, 1, wx.EXPAND | wx.ALL, 8)
    roadmap_panel.SetSizer(rm_sizer)
    nb.AddPage(roadmap_panel, "Roadmap")

    # Principles tab
    principles_panel = wx.Panel(nb)
    pr_sizer = wx.BoxSizer(wx.VERTICAL)
    principles_list = wx.ListCtrl(
        principles_panel,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES,
        name="whisperer_principles",
    )
    principles_list.AppendColumn("Principle", width=180)
    principles_list.AppendColumn("How it applies", width=460)
    for i, (principle, detail) in enumerate(principles_rows):
        principles_list.InsertItem(i, principle)
        principles_list.SetItem(i, 1, detail)
    pr_sizer.Add(principles_list, 1, wx.EXPAND | wx.ALL, 8)
    principles_panel.SetSizer(pr_sizer)
    nb.AddPage(principles_panel, "Principles")

    sizer.Add(nb, 1, wx.EXPAND | wx.ALL, 8)
    btn_sizer = wx.StdDialogButtonSizer()
    close_btn = wx.Button(dialog, wx.ID_OK, label="Close")
    close_btn.SetDefault()
    btn_sizer.AddButton(close_btn)
    btn_sizer.Realize()
    sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
    try:
        show_modal_dialog(dialog, "About BITS Whisperer")
    finally:
        dialog.Destroy()


def show_bw_capability_matrix_native(
    parent: Any,
    wx: Any,
    capability_rows: list[tuple[str, str, str, str]],
    snapshot: dict,
    show_modal_dialog: Callable[[Any, str], int],
) -> None:
    """Modal BITS Whisperer Capability Matrix dialog with a native ListCtrl."""
    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.Dialog(
        parent,
        title="BITS Whisperer Capability Matrix",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((760, 500))
    sizer = wx.BoxSizer(wx.VERTICAL)

    cap_list = wx.ListCtrl(
        dialog,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES,
        name="bw_capability_matrix",
    )
    cap_list.AppendColumn("Capability", width=220)
    cap_list.AppendColumn("Phase", width=80)
    cap_list.AppendColumn("Status", width=90)
    cap_list.AppendColumn("Notes", width=310)
    for i, (name, phase, status, notes) in enumerate(capability_rows):
        cap_list.InsertItem(i, name)
        cap_list.SetItem(i, 1, phase)
        cap_list.SetItem(i, 2, status)
        cap_list.SetItem(i, 3, notes)
    sizer.Add(cap_list, 1, wx.EXPAND | wx.ALL, 12)

    snapshot_text = (
        f"Provider mode: {snapshot.get('provider_mode', '')}\n"
        f"Configured provider: {snapshot.get('provider_name', '')}\n"
        f"Speech model mode: {snapshot.get('speech_model_mode', '')}\n"
        f"Configured speech model: {snapshot.get('speech_model_id', '')}\n"
        f"Downloaded whisper models: {snapshot.get('downloaded_model_count', 0)} "
        f"of {snapshot.get('available_model_count', 0)}"
    )
    snap_ctrl = wx.TextCtrl(
        dialog,
        value=snapshot_text,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        name="bw_snapshot",
    )
    snap_ctrl.SetMinSize((-1, 90))
    sizer.Add(snap_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    btn_sizer = wx.StdDialogButtonSizer()
    close_btn = wx.Button(dialog, wx.ID_OK, label="Close")
    close_btn.SetDefault()
    btn_sizer.AddButton(close_btn)
    btn_sizer.Realize()
    sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
    wx.CallAfter(cap_list.SetFocus)
    try:
        show_modal_dialog(dialog, "BITS Whisperer Capability Matrix")
    finally:
        dialog.Destroy()
