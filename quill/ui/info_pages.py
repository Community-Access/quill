"""Native wx replacements for web-view-based informational pages.

All surfaces here use only wx controls so screen readers never have to
switch between Browse mode and Forms/Application mode.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def show_about_quill_native(
    parent: Any,
    wx: Any,
    about_info: Any,
    open_notices_fn: Callable[[], None],
    show_modal_dialog: Callable[[Any, str], int],
) -> None:
    """Modal About Quill dialog backed by a ``wx.Notebook``.

    Tabs (Overview, Golden Quills, Legal, Dependencies, Links) surface the
    version, supporters, dependencies, and links as navigable controls so JAWS in
    Forms mode reads them as distinct elements rather than a flattened blob (#260).
    """
    from quill.core.about_info import AboutInfo
    from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control

    assert isinstance(about_info, AboutInfo)
    dialog = wx.Dialog(
        parent,
        title=f"About {about_info.product_name}",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((760, 580))
    sizer = wx.BoxSizer(wx.VERTICAL)

    notebook = wx.Notebook(dialog, name="About sections")

    # --- Overview tab ---
    overview = wx.Panel(notebook)
    ov_sizer = wx.BoxSizer(wx.VERTICAL)
    overview_lines = [
        about_info.headline(),
        "",
        about_info.tagline,
        "",
        about_info.glow_summary,
        "",
        *about_info.overview_paragraphs,
    ]
    overview_text = wx.TextCtrl(
        overview,
        value="\n".join(overview_lines),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        name="about_overview",
    )
    overview_text.SetMinSize((-1, 320))
    ov_sizer.Add(overview_text, 1, wx.EXPAND | wx.ALL, 8)
    overview.SetSizer(ov_sizer)
    notebook.AddPage(overview, "Overview")

    # --- Golden Quills tab (financial supporters) ---
    _build_golden_quills_tab(notebook, wx, about_info)

    # --- Legal tab ---
    legal_panel = wx.Panel(notebook)
    legal_sizer = wx.BoxSizer(wx.VERTICAL)
    notice_label = wx.StaticText(
        legal_panel,
        label="Independence and trademark notice",
        name="about_legal_label",
    )
    notice_label.SetFont(notice_label.GetFont().Bold())
    legal_sizer.Add(notice_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    legal_text = wx.TextCtrl(
        legal_panel,
        value="\n\n".join([
            about_info.independence_notice,
            about_info.copyright,
            f"Licensed under {about_info.license_name}.",
            f"Build: {about_info.support_info}",
        ]),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        name="about_legal_text",
    )
    legal_text.SetMinSize((-1, 240))
    legal_sizer.Add(legal_text, 1, wx.EXPAND | wx.ALL, 8)
    legal_panel.SetSizer(legal_sizer)
    notebook.AddPage(legal_panel, "Legal")

    # --- Dependencies tab ---
    deps_panel = wx.Panel(notebook)
    deps_sizer = wx.BoxSizer(wx.VERTICAL)
    if about_info.dependencies_available:
        deps_list = _build_dependency_list(deps_panel, wx, about_info.dependencies)
        deps_sizer.Add(deps_list, 1, wx.EXPAND | wx.ALL, 8)
    else:
        deps_msg = wx.StaticText(
            deps_panel,
            label="Dependency metadata is not available in this build.",
            name="about_dependencies_missing",
        )
        deps_sizer.Add(deps_msg, 1, wx.EXPAND | wx.ALL, 12)
    if about_info.bundled_components:
        bundled_label = wx.StaticText(
            deps_panel,
            label="Bundled components and data sources",
            name="about_bundled_label",
        )
        bundled_label.SetFont(bundled_label.GetFont().Bold())
        deps_sizer.Add(bundled_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        bundled_list = _build_dependency_list(deps_panel, wx, about_info.bundled_components)
        deps_sizer.Add(bundled_list, 1, wx.EXPAND | wx.ALL, 8)
    deps_panel.SetSizer(deps_sizer)
    notebook.AddPage(deps_panel, "Dependencies")

    # --- Links tab ---
    links_panel = wx.Panel(notebook)
    links_sizer = wx.BoxSizer(wx.VERTICAL)
    org_label = wx.StaticText(links_panel, label="Organizations", name="about_orgs_label")
    org_label.SetFont(org_label.GetFont().Bold())
    links_sizer.Add(org_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
    org_list = _build_link_list(links_panel, wx, about_info.org_links)
    links_sizer.Add(org_list, 1, wx.EXPAND | wx.ALL, 8)

    contrib_label = wx.StaticText(links_panel, label="Project on GitHub", name="about_github_label")
    contrib_label.SetFont(contrib_label.GetFont().Bold())
    links_sizer.Add(contrib_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    contrib_list = _build_link_list(links_panel, wx, about_info.github_links)
    links_sizer.Add(contrib_list, 1, wx.EXPAND | wx.ALL, 8)

    contrib_people_label = wx.StaticText(
        links_panel, label="Contributors", name="about_contributors_label"
    )
    contrib_people_label.SetFont(contrib_people_label.GetFont().Bold())
    links_sizer.Add(contrib_people_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
    contributors_list = _build_link_list(links_panel, wx, about_info.contributors)
    links_sizer.Add(contributors_list, 1, wx.EXPAND | wx.ALL, 8)

    link_buttons = wx.BoxSizer(wx.HORIZONTAL)
    visit_btn = wx.Button(links_panel, label="Visit", name="about_link_visit")
    copy_btn = wx.Button(links_panel, label="Copy", name="about_link_copy")
    link_buttons.Add(visit_btn, 0, wx.RIGHT, 8)
    link_buttons.Add(copy_btn, 0)
    links_sizer.Add(link_buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    _bind_link_buttons(wx, visit_btn, copy_btn, org_list, contrib_list, contributors_list)
    links_panel.SetSizer(links_sizer)
    notebook.AddPage(links_panel, "Links")

    sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_sizer.AddStretchSpacer()
    copy_support_btn = wx.Button(dialog, label="Copy Support Info", name="about_copy_support")
    notices_btn = wx.Button(dialog, wx.ID_HELP, label="Open Third-Party Notices")
    close_btn = wx.Button(dialog, wx.ID_OK, label="Close")
    close_btn.SetDefault()
    copy_support_btn.Bind(
        wx.EVT_BUTTON,
        lambda _e: _copy_support_to_clipboard(wx, about_info),
    )
    notices_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_HELP))
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
    btn_sizer.Add(copy_support_btn, 0, wx.RIGHT, 8)
    btn_sizer.Add(notices_btn, 0, wx.RIGHT, 8)
    btn_sizer.Add(close_btn, 0)
    sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
    # Land focus on the first control of the visible tab, not the tab strip or
    # the default Close button. This dialog is shown through the module-level
    # show_modal_dialog (no MainFrame focus seam), so it applies the contract's
    # notebook-aware focus routing itself.
    focus_primary_control(dialog)
    try:
        result = show_modal_dialog(dialog, f"About {about_info.product_name}")
    finally:
        dialog.Destroy()
    if result == wx.ID_HELP:
        open_notices_fn()


def _copy_support_to_clipboard(wx: Any, about_info: Any) -> None:
    """Copy the support block to the clipboard and announce the result."""
    text = about_info.support_info or ""
    if not text:
        return
    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()


def _build_golden_quills_tab(notebook: Any, wx: Any, about_info: Any) -> None:
    """A warm recognition tab for people who support QUILL financially.

    QUILL is free; donating is entirely optional and never required to use any
    feature. This tab simply says thank you, lists supporters in alphabetical
    order, and offers an optional Donate button.
    """
    panel = wx.Panel(notebook)
    sizer = wx.BoxSizer(wx.VERTICAL)

    heading = wx.StaticText(
        panel, label="Golden Quills — with heartfelt thanks", name="golden_quills_heading"
    )
    heading_font = heading.GetFont()
    heading_font.SetPointSize(heading_font.GetPointSize() + 2)
    heading.SetFont(heading_font.Bold())
    sizer.Add(heading, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

    intro = wx.TextCtrl(
        panel,
        value=(
            "QUILL is free, and it always will be. The people below — our Golden "
            "Quills — chose to support the project financially, and their generosity "
            "helps keep QUILL independent, accessible, and moving forward. From all "
            "of us: thank you.\n\n"
            "Donating is completely optional and is NEVER required to use any part of "
            "QUILL. Every feature is, and will remain, fully available to everyone. If "
            "you would like to chip in, the Donate button below opens a PayPal page in "
            "your browser; if not, please simply enjoy QUILL with our gratitude."
        ),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        name="golden_quills_intro",
    )
    intro.SetMinSize((-1, 130))
    sizer.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

    roll_label = wx.StaticText(panel, label="Our Golden Quills", name="golden_quills_roll_label")
    roll_label.SetFont(roll_label.GetFont().Bold())
    sizer.Add(roll_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

    roll = wx.ListCtrl(
        panel,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER | wx.LC_HRULES,
        name="golden_quills_list",
    )
    roll.AppendColumn("Supporter", width=420)
    names = list(getattr(about_info, "golden_quills", ()) or ())
    if names:
        for i, name in enumerate(names):
            roll.InsertItem(i, name)
    else:
        roll.InsertItem(0, "Be the first — your name could appear here.")
    sizer.Add(roll, 1, wx.EXPAND | wx.ALL, 10)

    donate_url = str(getattr(about_info, "donate_url", "") or "")
    note = wx.StaticText(
        panel,
        label="Optional — never required. QUILL stays free for everyone.",
        name="golden_quills_optional_note",
    )
    sizer.Add(note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

    if donate_url:
        donate_btn = wx.Button(panel, label="Donate (optional)", name="golden_quills_donate")
        donate_btn.SetToolTip(f"Open {donate_url} in your browser. Donating is optional.")

        def _on_donate(_event: Any) -> None:
            import webbrowser

            webbrowser.open(donate_url)

        donate_btn.Bind(wx.EVT_BUTTON, _on_donate)
        sizer.Add(donate_btn, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)

    panel.SetSizer(sizer)
    notebook.AddPage(panel, "Golden Quills")


def _build_dependency_list(parent: Any, wx: Any, rows: Any) -> Any:
    list_ctrl = wx.ListCtrl(
        parent,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_VRULES | wx.LC_HRULES,
        name="about_dependency_list",
    )
    list_ctrl.AppendColumn("Dependency", width=200)
    list_ctrl.AppendColumn("Version", width=140)
    list_ctrl.AppendColumn("License", width=160)
    list_ctrl.AppendColumn("Homepage", width=220)
    for i, row in enumerate(rows):
        list_ctrl.InsertItem(i, row.name)
        list_ctrl.SetItem(i, 1, row.version)
        list_ctrl.SetItem(i, 2, row.license)
        list_ctrl.SetItem(i, 3, row.homepage)
    return list_ctrl


def _build_link_list(parent: Any, wx: Any, links: Any) -> Any:
    list_ctrl = wx.ListCtrl(
        parent,
        style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES,
        name="about_link_list",
    )
    list_ctrl.AppendColumn("Name", width=260)
    list_ctrl.AppendColumn("URL", width=420)
    for i, link in enumerate(links):
        list_ctrl.InsertItem(i, link.name)
        list_ctrl.SetItem(i, 1, link.url)
    return list_ctrl


def _bind_link_buttons(
    wx: Any,
    visit_btn: Any,
    copy_btn: Any,
    *lists: Any,
) -> None:
    """Bind Visit (open URL in browser) and Copy (URL to clipboard).

    Enter on a row also activates Visit so keyboard users get a single
    press path. The focused list at the time of the click determines
    which URL is acted on; clicking Visit with no focused list is a
    no-op rather than a confusing error.
    """

    def _selected_url() -> str:
        for lst in lists:
            idx = lst.GetFirstSelected()
            if idx >= 0:
                return lst.GetItem(idx, 1).GetText()
        return ""

    def _on_visit(_event: Any) -> None:
        url = _selected_url()
        if not url:
            return
        import webbrowser

        webbrowser.open(url)

    def _on_copy(_event: Any) -> None:
        url = _selected_url()
        if not url:
            return
        if not wx.TheClipboard.IsOpened():
            wx.TheClipboard.Open()
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(url))
        finally:
            wx.TheClipboard.Close()

    visit_btn.Bind(wx.EVT_BUTTON, _on_visit)
    copy_btn.Bind(wx.EVT_BUTTON, _on_copy)
    for lst in lists:
        lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED, _on_visit)


def show_whisperer_about_native(
    parent: Any,
    wx: Any,
    roadmap_rows: list[tuple[str, str, str, str]],
    principles_rows: list[tuple[str, str]],
    show_modal_dialog: Callable[[Any, str], int],
) -> None:
    """Modal About BITS Whisperer dialog with tabbed native ListCtrls."""
    from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control

    dialog = wx.Dialog(
        parent,
        title="About BITS Whisperer",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((760, 540))
    sizer = wx.BoxSizer(wx.VERTICAL)
    nb = wx.Notebook(dialog)
    nb.SetName("About sections")

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
    # Land focus on the first control of the visible tab, not the tab strip or
    # the default Close button (module-level show_modal_dialog, no MainFrame seam).
    focus_primary_control(dialog)
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
