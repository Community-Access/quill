"""Changing a global style from the WordPress Workbench (W7).

A mixin under :class:`quill.ui.wordpress_workbench_bold.WorkbenchBoldCommands`:
Enter on a Global Styles row changes that colour or font size on the site,
previewed with its contrast, verified after saving, and recorded so Undo
WordPress Change can put the previous style back.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg

__all__ = ["WorkbenchGlobalStyleCommands"]


class WorkbenchGlobalStyleCommands:
    """Change one global style (a colour or a font size) on the site, with undo."""

    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    _base: Callable[[], Path]

    def do_edit_global_style(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "global_style":
            return
        from quill.core.wordpress import site_styles as styles

        site = row.site
        profile = self.profile(site)
        if profile is None:
            self.say(f"{site} is no longer in your list of sites.")
            return
        kind = row.subkind
        name = row.cell("setting") or str(row.raw.get("name", "style"))
        old_value = row.cell("value") or str(row.raw.get("value", ""))
        new_value = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Change {name}",
            prompt="&New value:",
            value=old_value,
            help_text=(
                "Type a colour such as #1a4d2e."
                if kind == "colour"
                else "Type a font size with its unit, such as 1.125rem or 18px."
            ),
        )
        if new_value is None:
            return
        try:
            checked = (
                styles.check_colour(new_value) if kind == "colour" else styles.check_size(new_value)
            )
        except styles.StyleValueError as exc:
            self.say(str(exc))
            return
        if checked == old_value:
            self.say(f"{name} on {site} already has that value.")
            return
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title=f"Change {name}",
            message=self._global_style_preview(styles, row, site, name, old_value, checked, kind),
            yes_label=f"Change {name}",
        ):
            return

        stylesheet = str(row.raw.get("stylesheet", ""))
        styles_id = int(row.raw.get("styles_id", 0) or 0)
        slug = str(row.raw.get("slug", ""))
        api = self.ctx(site).api

        def work() -> dict[str, Any]:
            theme = styles.active_theme(api)
            if theme.stylesheet != stylesheet or theme.styles_id != styles_id:
                raise RuntimeError(f"The active theme on {site} changed. Refresh this list first.")
            if not styles_id:
                raise RuntimeError(f"The active theme on {site} has no editable style record.")
            base = styles.theme_styles(api, stylesheet)
            before = styles.load_user_styles(api, styles_id)
            current = next(
                (
                    entry
                    for entry in styles.entries(base, before)
                    if entry.kind == kind and entry.slug == slug
                ),
                None,
            )
            if current is None or current.value != old_value:
                raise RuntimeError(
                    f"{name} on {site} changed since this list loaded. Refresh and try again."
                )
            settings = styles.changed_settings(base, before, current, checked)
            styles.keep_previous(self._base(), profile.id, before, reason=f"changing {name}")
            styles.save_user_styles(api, styles_id, {"settings": settings})
            after = styles.load_user_styles(api, styles_id)
            saved = next(
                (
                    entry
                    for entry in styles.entries(base, after)
                    if entry.kind == kind and entry.slug == slug
                ),
                None,
            )
            if saved is None or saved.value != checked:
                raise RuntimeError(f"The site did not verify the new value for {name}.")
            return before

        def done(before: dict[str, Any]) -> None:
            def undo() -> str:
                live = styles.load_user_styles(api, styles_id)
                base = styles.theme_styles(api, stylesheet)
                current = next(
                    (
                        entry
                        for entry in styles.entries(base, live)
                        if entry.kind == kind and entry.slug == slug
                    ),
                    None,
                )
                if current is None or current.value != checked:
                    return f"Not undone: {name} on {site} changed again on the site."
                body = {
                    "settings": before.get("settings") or {},
                    "styles": before.get("styles") or {},
                }
                if before.get("title"):
                    body["title"] = before["title"]
                styles.save_user_styles(api, styles_id, body)
                restored = styles.load_user_styles(api, styles_id)
                prior = next(
                    (
                        entry
                        for entry in styles.entries(base, restored)
                        if entry.kind == kind and entry.slug == slug
                    ),
                    None,
                )
                if prior is None or prior.value != old_value:
                    raise RuntimeError(f"The site did not verify the restored value for {name}.")
                return f"Restored {name} on {site}."

            said = (
                f"{name} changed on {site}. Undo WordPress Change can restore its previous value."
            )
            self._record(said, undo, target=f"{site}: {name}")  # type: ignore[attr-defined]
            self.say(said)
            self.refresh()

        self.background(f"changing {name}", work, done)

    @staticmethod
    def _global_style_preview(
        styles: Any, row: WbRow, site: str, name: str, old_value: str, new_value: str, kind: str
    ) -> str:
        message = (
            f"Change {name} on {site} from {old_value} to {new_value}? Visitors see this "
            "change immediately. Undo WordPress Change can put the previous style back."
        )
        if kind == "colour":
            message += (
                " "
                + styles.contrast_sentence(
                    name,
                    new_value,
                    str(row.raw.get("_background") or "#ffffff"),
                    str(row.raw.get("_foreground") or "#000000"),
                )
                + "."
            )
        return message
