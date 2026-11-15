"""Widgets of every kind, and menu history, in the Workbench (wordpress.md 9.17, gaps 8 and 10).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.
What each command means is :mod:`quill.core.wordpress.widget_types`,
:mod:`quill.core.wordpress.site_structure` and
:mod:`quill.core.wordpress.looks_history`; the context-menu rows, with why
none has a chord, are :mod:`quill.core.wordpress.workbench_dashboard_places`.

- On a widget area: **Add**, **Change**, **Move** and **Remove a Widget**, for
  every widget type the site has (a legacy widget on the form WordPress itself
  draws, a block widget as text), each previewed and undone with Ctrl+Z, and
  **Preview Widgets**, the area as a visitor sees it.
- On a menu: **Earlier Versions** (QUILL's own snapshots of a classic menu,
  which now begin whenever the Workbench reads it) and **Default Navigation
  Menu** (``navigation-fallback``, which can make a menu, so it asks first).

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import looks_history as lh
from quill.core.wordpress import navigation as nav
from quill.core.wordpress import site_structure as ss
from quill.core.wordpress import widget_types as wt
from quill.core.wordpress.block_catalog import Field, assign_access_keys
from quill.core.wordpress.local import now_stamp
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_site_editor import change_lines
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchWidgetCommands", "form_to_fields"]


def form_to_fields(controls: list[wt.FormControl]) -> list[Field]:
    """A widget's own form as QUILL's generated form, each control under its own label."""
    labels = assign_access_keys([f"{c.label}:" if c.kind != "check" else c.label for c in controls])
    fields: list[Field] = []
    for control, label in zip(controls, labels, strict=True):
        if control.kind == "check":
            fields.append(Field(control.name, label, "check", control.label, control.checked))
        elif control.kind == "choice":
            chosen = Field(control.name, label, "choice", control.label, control.value)
            chosen.choices = [words for _v, words in control.choices]
            chosen.values = [value for value, _w in control.choices]
            fields.append(chosen)
        else:
            fields.append(Field(control.name, label, control.kind, control.label, control.value))
    return fields


class WorkbenchWidgetCommands:
    """Widgets beyond Text, and the history of a classic menu."""

    frame: Any
    commands: Any
    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    _data_dir: Any

    def _widget_undo(self, summary: str, undo: Callable[[], str]) -> None:
        self.history.record(Change(summary, summary, undo=undo))

    def _area(self, row: WbRow | None) -> bool:
        if row is None or row.kind != "sidebar":
            self.say("Choose a widget area in Widgets and Sidebars first.")
            return False
        return True

    def _ask_widget_form(self, title: str, encoded: wt.Encoded) -> str | None:
        """The widget's own form; its answers as form data, or None when cancelled."""
        from quill.ui import wordpress_block_dialogs as bdlg

        controls = wt.form_fields(encoded.form)
        if not controls:
            return ""
        answers = bdlg.ask_fields(
            self.parent,
            self.show_modal,
            title=title,
            purpose="The widget's own settings, as WordPress draws them.",
            fields=form_to_fields(controls),
        )
        return None if answers is None else wt.encode_answers(controls, answers)

    # -- add --------------------------------------------------------------------------

    def do_add_widget(self, _ref: Any, row: WbRow | None) -> None:
        if not self._area(row):
            return
        assert row is not None
        api = self.ctx(row.site).api
        self.background(
            "reading the kinds of widget",
            lambda: wt.list_widget_types(api),
            lambda types: self._add_widget(row, api, types),
        )

    def _add_widget(self, row: WbRow, api: Any, types: list[wt.WidgetType]) -> None:
        if not types:
            self.say(f"{row.site} lists no kinds of widget.")
            return
        picked = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Add a Widget to {row.title}",
            prompt="&Kind of widget:",
            rows=[t.row() for t in types],
            help_text="Block holds any block, as text; the rest each have their own settings.",
        )
        if picked is None:
            return
        kind = types[picked]
        if kind.id == "block":
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title=f"Add a Block Widget to {row.title}",
                prompt="&Text:",
                help_text="The words of a paragraph block, shown in this area on every page.",
                multiline=True,
            )
            if not text or not text.strip():
                return
            instance: dict[str, Any] = {"raw": {"content": ss.paragraph_block(text.strip())}}
            self._confirm_add(row, api, "block", kind.name, instance, text.strip())
            return

        def form(encoded: wt.Encoded) -> None:
            data = self._ask_widget_form(f"Add {kind.name}", encoded)
            if data is None:
                return
            self.background(
                f"reading {kind.name}",
                lambda: wt.encode_form(api, kind.id, data),
                lambda done: self._confirm_add(
                    row, api, kind.id, kind.name, dict(done.instance), done.preview
                ),
            )

        self.background(f"reading {kind.name}'s form", lambda: wt.new_form(api, kind.id), form)

    def _confirm_add(
        self, row: WbRow, api: Any, type_id: str, name: str, instance: dict[str, Any], seen: str
    ) -> None:
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Add {name}",
            summary=f"Add this {name} widget to {row.title} on {row.site}? It shows on every page "
            "that has this area.",
            lines=[f"Visitors see: {seen or '(nothing yet)'}"],
            yes="Add",
        ):
            return

        def work() -> dict[str, Any]:
            body = {"id_base": type_id, "sidebar": row.key, "instance": instance}
            answer = api.post("wp/v2/widgets", body, context="edit")
            return answer if isinstance(answer, dict) else {}

        def done(made: dict[str, Any]) -> None:
            widget_id = str(made.get("id", ""))
            summary = f"Added a {name} widget to {row.title} on {row.site}."

            def undo() -> str:
                api.delete(f"wp/v2/widgets/{widget_id}", force=True)
                return f"Removed the {name} widget again."

            self._widget_undo(summary, undo)
            self.say(summary)
            self.refresh()

        self.background(f"adding a {name} widget", work, done)

    # -- choose one of the area's widgets ------------------------------------------

    def _pick_widget(self, row: WbRow, verb: str, then: Callable[[Any, ss.Widget], None]) -> None:
        api = self.ctx(row.site).api

        def chosen(widgets: list[ss.Widget]) -> None:
            if not widgets:
                self.say(f"{row.title} has no widgets.")
                return
            index = 0
            if len(widgets) > 1:
                picked = dlg.ask_choice(
                    self.parent,
                    self.show_modal,
                    title=f"{verb} a Widget",
                    prompt="&Widget:",
                    rows=[w.spoken() for w in widgets],
                    help_text=f"The widgets in {row.title}, in their order on the page.",
                )
                if picked is None:
                    return
                index = picked
            then(api, widgets[index])

        self.background(
            f"reading the widgets in {row.title}", lambda: ss.list_widgets(api, row.key), chosen
        )

    # -- change ---------------------------------------------------------------------

    def do_change_widget(self, _ref: Any, row: WbRow | None) -> None:
        if not self._area(row):
            return
        assert row is not None
        self._pick_widget(row, "Change", lambda api, w: self._change_widget(row, api, w))

    def _change_widget(self, row: WbRow, api: Any, widget: ss.Widget) -> None:
        name = widget.spoken()
        if widget.is_block:
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title=f"Change {name}",
                prompt="&Block markup:",
                value=widget.content,
                help_text="The widget's block markup. OK reads the change back before it is sent.",
                multiline=True,
            )
            if text is None or text == widget.content:
                return
            self._confirm_change(
                row,
                api,
                widget,
                {"raw": {"content": text}},
                change_lines(widget.content, text),
            )
            return

        def form(found: tuple[dict[str, Any], wt.Encoded]) -> None:
            loaded, encoded = found
            data = self._ask_widget_form(f"Change {name}", encoded)
            if not data:
                return
            self.background(
                f"reading {name}",
                lambda: wt.encode_form(api, widget.id_base, data),
                lambda done: self._confirm_change(
                    row,
                    api,
                    widget,
                    dict(done.instance),
                    [f"Visitors saw: {encoded.preview}", f"Visitors will see: {done.preview}"],
                    loaded,
                ),
            )

        def read() -> tuple[dict[str, Any], wt.Encoded]:
            loaded = wt.load_widget(api, widget.id)
            return loaded, wt.new_form(api, widget.id_base, loaded.get("instance") or {})

        self.background(f"reading {name}'s form", read, form)

    def _confirm_change(
        self,
        row: WbRow,
        api: Any,
        widget: ss.Widget,
        instance: dict[str, Any],
        lines: list[str],
        loaded: dict[str, Any] | None = None,
    ) -> None:
        name = widget.spoken()
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Change {name}",
            summary=f"Save {name} in {row.title} on {row.site}?",
            lines=lines,
            yes="Save",
        ):
            return

        def work() -> tuple[dict[str, Any], dict[str, Any]]:
            before = loaded or wt.load_widget(api, widget.id)
            wt.save_instance(api, before, instance)
            return before, wt.load_widget(api, widget.id)

        def done(got: tuple[dict[str, Any], dict[str, Any]]) -> None:
            before, after = got
            summary = f"Saved {name} in {row.title} on {row.site}."

            def undo() -> str:
                wt.save_instance(api, after, before.get("instance") or {})
                return f"{name} is back as it was."

            self._widget_undo(summary, undo)
            self.say(summary)
            self.refresh()

        self.background(f"saving {name}", work, done)

    # -- move and remove -----------------------------------------------------------

    def do_move_widget(self, _ref: Any, row: WbRow | None) -> None:
        if not self._area(row):
            return
        assert row is not None

        def chosen(api: Any, widget: ss.Widget) -> None:
            self.background(
                "reading the widget areas",
                lambda: [s for s in ss.list_sidebars(api) if s.id != row.key],
                lambda areas: self._move_widget(row, api, widget, areas),
            )

        self._pick_widget(row, "Move", chosen)

    def _move_widget(
        self, row: WbRow, api: Any, widget: ss.Widget, areas: list[ss.Sidebar]
    ) -> None:
        if not areas:
            self.say(f"{row.site} has no other widget area to move it to.")
            return
        picked = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Move {widget.spoken()}",
            prompt="&To:",
            rows=[a.name for a in areas],
            help_text="The widget area it moves to; it goes at the end there.",
        )
        if picked is None:
            return
        target = areas[picked]

        def done(_moved: ss.Widget) -> None:
            summary = f"Moved {widget.spoken()} from {row.title} to {target.name}."

            def undo() -> str:
                ss.move_widget(api, widget, row.key)
                return f"{widget.spoken()} is back in {row.title}."

            self._widget_undo(summary, undo)
            self.say(summary)
            self.refresh()

        self.background(
            f"moving {widget.spoken()}", lambda: ss.move_widget(api, widget, target.id), done
        )

    def do_remove_widget(self, _ref: Any, row: WbRow | None) -> None:
        if not self._area(row):
            return
        assert row is not None
        self._pick_widget(row, "Remove", lambda api, w: self._remove_widget(row, api, w))

    def _remove_widget(self, row: WbRow, api: Any, widget: ss.Widget) -> None:
        name = widget.spoken()
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Remove a Widget",
            message=(
                f"Take {name} out of {row.title} on {row.site}? WordPress keeps it in Inactive "
                "Widgets, and Ctrl+Z puts it back."
            ),
            yes_label="Remove",
        ):
            return

        def done(_none: None) -> None:
            summary = f"Removed {name} from {row.title}; it is in Inactive Widgets."

            def undo() -> str:
                ss.move_widget(api, widget, row.key)
                return f"{name} is back in {row.title}."

            self._widget_undo(summary, undo)
            self.say(summary)
            self.refresh()

        self.background(f"removing {name}", lambda: ss.remove_widget(api, widget), done)

    # -- preview ------------------------------------------------------------------

    def do_preview_widgets(self, _ref: Any, row: WbRow | None) -> None:
        if not self._area(row):
            return
        assert row is not None
        api = self.ctx(row.site).api

        def work() -> list[str]:
            lines: list[str] = []
            for widget in ss.list_widgets(api, row.key):
                if widget.is_block:
                    seen = wt.preview_text(widget.rendered)
                else:
                    loaded = wt.load_widget(api, widget.id)
                    seen = wt.render_instance(api, widget.id_base, loaded.get("instance") or {})
                lines.append(f"{widget.spoken()}: {seen or '(shows nothing)'}")
            return lines

        def done(lines: list[str]) -> None:
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"Widgets in {row.title}",
                text="\n".join(lines) or f"{row.title} has no widgets.",
                help_text="Each widget in this area, then what a visitor sees of it.",
            )

        self.background(f"rendering the widgets in {row.title}", work, done)

    # -- menus --------------------------------------------------------------------

    def do_menu_versions(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "menu":
            self.say("Choose a menu first.")
            return
        api = self.ctx(row.site).api
        profile = self.profile(row.site)
        site_id = str(getattr(profile, "id", "") or row.site)

        def work() -> tuple[nav.Menu | None, list[lh.MenuVersion]]:
            menu = next(
                (m for m in nav.load_menus(api) if m.source == "classic" and str(m.id) == row.key),
                None,
            )
            if menu is None:
                return None, []
            store = lh.MenuSnapshots(self._data_dir)
            store.remember(site_id, menu, now_stamp())  # history starts at the first read
            return menu, store.versions(site_id, menu)[1:]

        self.background(
            f"reading {row.title}'s earlier versions",
            work,
            lambda got: self._menu_versions(row, api, *got),
        )

    def _menu_versions(
        self, row: WbRow, api: Any, menu: nav.Menu | None, versions: list[lh.MenuVersion]
    ) -> None:
        if menu is None:
            self.say(f"{row.title} is no longer on {row.site}.")
            return
        if not versions:
            self.say(
                f"{menu.name} has no earlier versions yet. WordPress keeps none for a classic "
                "menu, so QUILL keeps its own each time it reads one, starting now."
            )
            return
        picked = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Earlier Versions of {menu.name}",
            prompt="&Versions:",
            rows=[v.spoken(menu) for v in versions],
            help_text="Each earlier state QUILL kept, newest first, with items since removed.",
        )
        if picked is None:
            return
        version = versions[picked]
        gone = version.missing_from(menu)
        if not gone:
            self.say(f"Every item from then is still in {menu.name}.")
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Bring Back Items to {menu.name}",
            summary=f"Add back the {len(gone)} items {menu.name} has lost since then, at its end?",
            lines=[f"Added back: {title}" for title, *_rest in gone],
            yes="Bring Back",
        ):
            return

        def work() -> list[nav.MenuNode]:
            fresh = next(m for m in nav.load_menus(api) if m.id == menu.id)
            missing = version.missing_from(fresh)  # what is still missing now, no more
            return [
                nav.add_item(api, fresh, nav.MenuNode(t, kind, object_id, url=url))
                for t, kind, object_id, url in missing
            ]

        def done(added: list[nav.MenuNode]) -> None:
            summary = f"Brought back {len(added)} items to {menu.name}."

            def undo() -> str:
                for node in added:
                    if node.item_id:
                        api.delete(f"wp/v2/menu-items/{node.item_id}", force=True)
                return f"Took the {len(added)} items out of {menu.name} again."

            self._widget_undo(summary, undo)
            self.say(summary)
            self.refresh()

        self.background(f"bringing items back to {menu.name}", work, done)

    def do_default_navigation(self, _ref: Any, row: WbRow | None) -> None:
        site = row.site if row is not None else ""
        if not site:
            self.say("Choose a menu on a site first.")
            return
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Default Navigation Menu",
            message=(
                f"Ask {site} which Navigation menu a block theme shows where none is chosen? If "
                "the site has no Navigation menu yet, WordPress makes one from its classic menu "
                "or its pages."
            ),
            yes_label="Ask",
        ):
            return
        api = self.ctx(site).api
        self.background(
            "asking for the default Navigation menu",
            lambda: lh.navigation_fallback(api),
            lambda found: self.say(
                f"Where a block theme has no menu chosen, {site} shows {found[1]}, Navigation "
                f"menu {found[0]}."
            ),
        )
