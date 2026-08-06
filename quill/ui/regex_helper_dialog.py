"""The Regular Expression Helper 2.0 dialog (#1328 P1).

Replaces the old six-recipe flat list with the full guided experience:

- a **category tree** of 100+ recipes (first-letter navigation, spoken counts),
- a **live plain-language explanation** of whatever is in the pattern box —
  typed, pasted, or chosen — via the deterministic explain engine, including
  position-bearing error diagnoses in words,
- a **testing pane** whose results read as sentences ("Match 3: line 4,
  column 7: foo@bar.com"), with replace previews for capture recipes,
- **Use in Find All Matches** — the pattern flows straight into the existing
  search surface with regex mode on, no clipboard hop.

Everything regex lives in the wx-free :mod:`quill.core.regex_helper` package;
this module is presentation only, and ``open_regex_helper`` keeps the whole
surface out of ``main_frame.py`` (which previously carried it inline).
"""

from __future__ import annotations

from typing import Any

from quill.core.regex_helper.catalog import CATEGORIES, RegexRecipe, recipes_by_category
from quill.core.regex_helper.explain import explain_pattern
from quill.core.regex_helper.runner import preview_replace, run_pattern
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

_RESULT_LIMIT = 25


def _results_text(pattern: str, sample: str, replace_template: str | None) -> str:
    """Render a run as spoken-friendly sentences, one per line."""
    if not pattern.strip():
        return "Enter a pattern, or choose a recipe from the tree."
    result = run_pattern(pattern, sample, max_matches=_RESULT_LIMIT + 1)
    if not result.ok:
        return result.error
    if not result.matches:
        return "No matches in the sample text."
    shown = result.matches[:_RESULT_LIMIT]
    noun = "match" if len(result.matches) == 1 else "matches"
    lines = [f"{len(result.matches)}{' or more' if result.truncated else ''} {noun}."]
    for index, match in enumerate(shown, start=1):
        value = match.text.replace("\n", "\\n")
        if len(value) > 80:
            value = value[:77] + "..."
        lines.append(f"Match {index}: line {match.line}, column {match.column}: {value}")
    if len(result.matches) > len(shown):
        lines.append(f"...and {len(result.matches) - len(shown)} more")
    if replace_template:
        lines.append("")
        lines.append(f"Replace preview (template: {replace_template}):")
        lines.extend(preview_replace(pattern, replace_template, sample, count=10))
    return "\n".join(lines)


def _explanation_text(recipe: RegexRecipe | None, pattern: str) -> str:
    """The recipe's own summary (when one is selected) plus the engine's
    step-by-step reading of whatever is actually in the pattern box."""
    parts: list[str] = []
    if recipe is not None and recipe.pattern == pattern:
        parts.append(recipe.explanation)
        if recipe.replace_note:
            parts.append(recipe.replace_note)
        parts.append("")
    explained = explain_pattern(pattern)
    if explained.ok:
        parts.extend(explained.steps)
    elif pattern.strip():
        parts.append(explained.error)
    return "\n".join(parts).strip() or "Type a pattern to hear it explained in plain language."


def open_regex_helper(controller: Any) -> None:
    """Open the helper for the host MainFrame (keeps main_frame thin)."""
    wx = controller._wx
    by_category = recipes_by_category()

    dialog = wx.Dialog(
        controller.frame,
        title="Regular Expression Helper",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((900, 680))
    root = wx.BoxSizer(wx.VERTICAL)

    intro = wx.StaticText(
        dialog,
        label=(
            "Choose a recipe from the tree, or type a pattern — it is explained in plain "
            "language as you go, and previews run against the sample text."
        ),
    )
    root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

    content = wx.BoxSizer(wx.HORIZONTAL)

    left = wx.BoxSizer(wx.VERTICAL)
    left.Add(wx.StaticText(dialog, label="&Recipes"), 0, wx.BOTTOM, 4)
    tree = wx.TreeCtrl(dialog, style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_SINGLE)
    set_accessible_name(tree, "Recipes by category")
    tree.SetMinSize((300, -1))
    root_item = tree.AddRoot("Recipes")
    recipe_for_item: dict[Any, RegexRecipe] = {}
    for category in CATEGORIES:
        recipes = by_category.get(category, ())
        if not recipes:
            continue
        node = tree.AppendItem(root_item, f"{category} ({len(recipes)})")
        for recipe in recipes:
            item = tree.AppendItem(node, recipe.name)
            recipe_for_item[item] = recipe
    left.Add(tree, 1, wx.EXPAND)
    content.Add(left, 0, wx.EXPAND | wx.ALL, 10)

    right = wx.BoxSizer(wx.VERTICAL)
    right.Add(wx.StaticText(dialog, label="&Pattern"), 0, wx.BOTTOM, 4)
    pattern_ctrl = wx.TextCtrl(dialog, style=wx.TE_PROCESS_ENTER)
    set_accessible_name(pattern_ctrl, "Pattern")
    right.Add(pattern_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)

    right.Add(wx.StaticText(dialog, label="&What this pattern means"), 0, wx.BOTTOM, 4)
    explanation_ctrl = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
    set_accessible_name(explanation_ctrl, "What this pattern means")
    explanation_ctrl.SetMinSize((520, 110))
    right.Add(explanation_ctrl, 0, wx.EXPAND | wx.BOTTOM, 8)

    right.Add(wx.StaticText(dialog, label="&Sample text"), 0, wx.BOTTOM, 4)
    default_sample = (
        controller.editor.GetStringSelection().strip() or controller.editor.GetValue()[:1200]
    )
    sample_ctrl = wx.TextCtrl(dialog, value=default_sample, style=wx.TE_MULTILINE)
    set_accessible_name(sample_ctrl, "Sample text")
    sample_ctrl.SetMinSize((520, 130))
    right.Add(sample_ctrl, 1, wx.EXPAND | wx.BOTTOM, 8)

    right.Add(wx.StaticText(dialog, label="Preview res&ults"), 0, wx.BOTTOM, 4)
    results_ctrl = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
    set_accessible_name(results_ctrl, "Preview results")
    results_ctrl.SetMinSize((520, 150))
    right.Add(results_ctrl, 1, wx.EXPAND)

    content.Add(right, 1, wx.EXPAND | wx.ALL, 10)
    root.Add(content, 1, wx.EXPAND)

    button_row = wx.BoxSizer(wx.HORIZONTAL)
    preview_btn = wx.Button(dialog, label="Pre&view")
    use_btn = wx.Button(dialog, label="Use in &Find All Matches")
    copy_btn = wx.Button(dialog, label="&Copy Pattern")
    close_btn = wx.Button(dialog, id=wx.ID_CLOSE, label="Close")
    button_row.Add(preview_btn, 0, wx.RIGHT, 8)
    button_row.Add(use_btn, 0, wx.RIGHT, 8)
    button_row.Add(copy_btn, 0, wx.RIGHT, 8)
    button_row.AddStretchSpacer(1)
    button_row.Add(close_btn, 0)
    root.Add(button_row, 0, wx.EXPAND | wx.ALL, 10)

    dialog.SetSizer(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)

    state: dict[str, RegexRecipe | None] = {"recipe": None}
    pending: list[Any] = []  # the debounce CallLater handle, if any

    def current_recipe_template() -> str | None:
        recipe = state["recipe"]
        if recipe is not None and recipe.pattern == pattern_ctrl.GetValue():
            return recipe.replace_template
        return None

    def refresh_explanation(*, announce: bool = False) -> None:
        explanation = _explanation_text(state["recipe"], pattern_ctrl.GetValue())
        explanation_ctrl.SetValue(explanation)
        # The live explanation is the whole point of this dialog; on a debounced
        # typing update, speak its first (summary) line so a screen-reader user
        # hears it without tabbing into the read-only pane. One line only, to
        # mirror Find's incremental-count cadence and stay non-chatty.
        if announce and pattern_ctrl.GetValue().strip():
            first_line = next((line for line in explanation.split("\n") if line.strip()), "")
            if first_line:
                controller._announce(first_line)

    def render_preview(*, announce: bool = False) -> None:
        results = _results_text(
            pattern_ctrl.GetValue(), sample_ctrl.GetValue(), current_recipe_template()
        )
        results_ctrl.SetValue(results)
        # Preview/Enter leave focus on the button; speak the summary line (already
        # sentence-shaped, e.g. "3 matches.") so the run is confirmed audibly.
        if announce:
            first_line = next((line for line in results.split("\n") if line.strip()), "")
            if first_line:
                controller._announce(first_line)

    def on_tree_selection(_event: object) -> None:
        recipe = recipe_for_item.get(tree.GetSelection())
        if recipe is None:  # a category node: nothing to load, keep browsing
            return
        state["recipe"] = recipe
        pattern_ctrl.ChangeValue(recipe.pattern)  # ChangeValue: no EVT_TEXT churn
        if recipe.sample and not controller.editor.GetStringSelection().strip():
            sample_ctrl.ChangeValue(recipe.sample)
        refresh_explanation()
        render_preview()

    def on_pattern_changed(event: object) -> None:
        event.Skip()
        for handle in pending:
            handle.Stop()
        pending.clear()
        pending.append(wx.CallLater(300, lambda: refresh_explanation(announce=True)))

    def on_copy(_event: object) -> None:
        pattern = pattern_ctrl.GetValue()
        if not pattern.strip():
            controller._set_status("Regular Expression helper: no pattern to copy")
            return
        if controller._copy_to_clipboard(pattern):
            controller._set_status("Regular Expression pattern copied")
        else:
            controller._set_status("Regular Expression helper could not copy pattern")

    def on_use(_event: object) -> None:
        pattern = pattern_ctrl.GetValue()
        if not pattern.strip():
            controller._set_status("Enter a pattern first")
            return
        from quill.core.search import SearchOptions

        # Seed the existing surface and let it run: no clipboard hop, and the
        # user lands in the flow they already know.
        controller._last_find_query = pattern
        controller._last_search_options = SearchOptions(
            case_sensitive=False, whole_word=False, use_regex=True, wildcard=False
        )
        dialog.EndModal(wx.ID_CLOSE)
        wx.CallAfter(controller.find_all_matches)

    tree.Bind(wx.EVT_TREE_SEL_CHANGED, on_tree_selection)
    preview_btn.Bind(wx.EVT_BUTTON, lambda _e: render_preview(announce=True))
    use_btn.Bind(wx.EVT_BUTTON, on_use)
    copy_btn.Bind(wx.EVT_BUTTON, on_copy)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    pattern_ctrl.Bind(wx.EVT_TEXT_ENTER, lambda _e: render_preview(announce=True))
    pattern_ctrl.Bind(wx.EVT_TEXT, on_pattern_changed)

    first_category = tree.GetFirstChild(root_item)[0]
    if first_category.IsOk():
        tree.Expand(first_category)
        tree.SelectItem(first_category)
    refresh_explanation()
    render_preview()
    tree.SetFocus()

    try:
        controller._show_modal_dialog(dialog, "Regular Expression Helper")
    finally:
        for handle in pending:
            handle.Stop()
        dialog.Destroy()
