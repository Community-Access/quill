"""wp-admin parity on Posts, Pages and Media, in the Workbench (wordpress.md 9.18, 1 to 3).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`;
what each command means is :mod:`quill.core.wordpress.workbench_parity`, and
its context-menu rows, with why none has a chord, are
:mod:`quill.core.wordpress.workbench_parity_actions`.

- **Counts by Status** says wp-admin's view counts in one sentence.
- **Duplicate as Draft**, after a confirmation; Ctrl+Z moves the copy to the Trash.
- **Empty Trash** lists what it will delete, permanently, and cannot be undone.
- **Edit Picture** offers the site's own edits and a crop by numbers, read
  back in words in a preview. WordPress keeps the original, so the edit
  touches nothing that could have changed meanwhile; no conflict check is
  needed and the original is the undo.
- **Attach**, **Detach**: a conflict-checked save of ``post``, undone by Ctrl+Z.
- **Regenerate Sizes**, **Download** and **Open in wp-admin** for what REST
  cannot do.

Every network call runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress import workbench_parity as wpp
from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_edit import EditConflict, EditRefused, save
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchParityCommands", "choose_save_path"]

_CROP_BY_NUMBERS = "Crop by numbers, in percent..."
_SCALE = "Scale the original to a size (opens wp-admin)..."


def choose_save_path(parent: Any, show_modal: Any, *, title: str, name: str) -> Path | None:
    """A standard Save As box for one file; None when cancelled."""
    import wx

    with wx.FileDialog(
        parent,
        title,
        defaultFile=name,
        wildcard="All files|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as picker:
        if show_modal(picker, title) != wx.ID_OK:
            return None
        return Path(picker.GetPath())


def _kind_words(kind: str) -> str:
    return {"post": "Posts", "page": "Pages"}.get(kind, kind.replace("_", " ").title())


class WorkbenchParityCommands:
    """Counts, Duplicate, Empty Trash, and the Media Library's own jobs."""

    frame: Any
    commands: Any
    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    split: Callable[[str], tuple[str, str]]

    # -- which list -----------------------------------------------------------------

    def _list_of(self, ref: Any, row: WbRow | None) -> tuple[str, str, str]:
        """(site, family, kind) of the list *row* or *ref* means: family is items or media."""
        if row is not None and row.kind == "item":
            return row.site, "items", row.subkind
        if row is not None and row.kind == "media":
            return row.site, "media", ""
        frame = self.frame
        if frame is None or ref is None:
            return "", "", ""
        family, _sep, what = frame.node(ref).loader.partition(":")
        site, dynamic = self.split(ref.instance)
        if family == "items":
            return site, family, dynamic if what == "custom" else what
        return (site, family, "") if family == "media" else ("", "", "")

    def do_status_counts(self, ref: Any, row: WbRow | None) -> None:
        site, family, kind = self._list_of(ref, row)
        if not site or not family:
            self.say("Counts by Status works in a site's posts, pages, content types or media.")
            return
        if family == "media":
            route, views, what = "wp/v2/media", wpp.MEDIA_VIEWS, "Media"
        else:
            route, views, what = kind_route(kind), wpp.ITEM_VIEWS, _kind_words(kind)

        def work() -> list[tuple[str, int]]:
            ctx = self.ensure(self.ctx(site))
            me = ctx.account.id if ctx.account is not None else 0
            return wpp.status_counts(ctx.api, route, me, views)

        self.background(
            f"counting {what.lower()}",
            work,
            lambda counts: self.say(wpp.counts_text(what, site, counts)),
        )

    # -- the featured image, chosen from the library ------------------------------------

    def featured_buttons(self, site: str) -> list[Any]:
        """Choose from Library and Remove Featured Image, beside Properties' featured image."""
        from quill.ui.workbench_sheet_editor import FieldButton

        return [
            FieldButton(
                "C&hoose from Library...",
                "List this site's pictures by title and alt text, and use the one you choose.",
                lambda set_value, _now: self.choose_featured(site, set_value),
            ),
            FieldButton(
                "&Remove Featured Image",
                "Clear the featured image. Nothing is sent until OK or Apply.",
                lambda set_value, _now: set_value(wpp.NO_PICTURE),
            ),
        ]

    def choose_featured(self, site: str, set_value: Callable[[str], None]) -> None:
        """The Media node's pictures, read off the UI thread, then chosen by title and alt text."""

        def work() -> list[WbRow]:
            from quill.core.wordpress.workbench_load import load_media

            return load_media(self.ensure(self.ctx(site)), "pictures", {})

        def chosen(pictures: list[WbRow]) -> None:
            if not pictures:
                self.say(f"{site}'s Media Library has no pictures.")
                return
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Choose a Featured Image",
                prompt="&Picture:",
                rows=[wpp.picture_row(p) for p in pictures],
                help_text=(
                    f"The pictures in {site}'s Media Library, newest first, each with its alt "
                    "text. The one you choose is shown with it; nothing is sent until OK or Apply."
                ),
            )
            if index is not None:
                picture = pictures[index]
                set_value(f"{picture.title} ({picture.key})")

        self.background(f"reading {site}'s pictures", work, chosen)

    # -- Duplicate and Empty Trash ------------------------------------------------------

    def do_duplicate(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "item":
            self.say("Duplicate as Draft works on a post, page or custom item.")
            return
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Duplicate as Draft",
            message=(
                f"Make a draft copy of {row.title} on {row.site}, called {row.title} (copy)? "
                "Visitors will not see it."
            ),
            yes_label="Make a Copy",
        ):
            return
        api = self.ctx(row.site).api

        def done(item: Any) -> None:
            said = f"{item.title} is a new draft on {row.site}. Ctrl+Z moves it to the Trash."
            self.say(said)

            def undo() -> str:
                from quill.core.wordpress import site as wp

                wp.trash_item(api, item.kind, item.id)
                return f"Moved {item.title} to the Trash."

            self.history.record(Change(row.title, said, undo=undo))
            self.refresh()

        self.background(f"duplicating {row.title}", lambda: wpp.duplicate(api, row), done)

    def do_empty_trash(self, ref: Any, row: WbRow | None) -> None:
        site, family, kind = self._list_of(ref, row)
        if family != "items" or not kind:
            self.say("Empty Trash works in a site's posts, pages or content types.")
            return
        what = _kind_words(kind).lower()
        api = self.ctx(site).api

        def found(rows: list[WbRow]) -> None:
            if not rows:
                self.say(f"The Trash on {site} has no {what}.")
                return
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Empty Trash",
                summary=(
                    f"Delete {len(rows)} {what} in the Trash on {site} permanently? "
                    "This cannot be undone, and Ctrl+Z will not bring them back."
                ),
                lines=[r.title for r in rows],
                yes="Delete Permanently",
            ):
                return

            def done(results: Any) -> None:
                said = wpp.outcome(results, "Deleted {n} from the Trash permanently", site)
                self.say(said)
                self.history.record(Change(said, said, undo=None))
                self.refresh()

            self.background(
                "emptying the Trash",
                lambda: wpp.each(rows, lambda r: api.delete(r.route, force=True), "deleted"),
                done,
            )

        self.background(
            f"reading the Trash on {site}", lambda: wpp.trash_rows(api, kind, site), found
        )

    # -- Media ------------------------------------------------------------------------

    def _picture(self, row: WbRow | None, doing: str) -> WbRow | None:
        if row is None or row.kind != "media" or row.subkind != "image":
            self.say(f"{doing} works on a picture in the Media Library.")
            return None
        return row

    def do_edit_picture(self, _ref: Any, row: WbRow | None) -> None:
        picture = self._picture(row, "Edit Picture")
        if picture is None:
            return
        details = picture.raw.get("media_details")
        details = details if isinstance(details, dict) else {}
        width, height = int(details.get("width", 0) or 0), int(details.get("height", 0) or 0)
        api = self.ctx(picture.site).api

        def offered() -> tuple[list[tuple[str, Any]], bool]:
            from quill.core.wordpress.site_features import read_index

            modifiers = read_index(api).edit_modifiers()
            return wpp.picture_choices(modifiers, width, height), "crop" in modifiers

        def chosen(found: tuple[list[tuple[str, Any]], bool]) -> None:
            choices, can_crop = found
            labels = [label for label, _m in choices]
            if can_crop:
                labels.append(_CROP_BY_NUMBERS)
            labels.append(_SCALE)
            size = f" It is {width} by {height}." if width and height else ""
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title=f"Edit {picture.title}",
                prompt="&Edit:",
                rows=labels,
                help_text=(
                    f"The edits {picture.site} takes.{size} WordPress keeps the original and "
                    "makes the edit a new picture. Scale opens wp-admin, because the REST "
                    "route cannot scale."
                ),
            )
            if index is None:
                return
            label = labels[index]
            if label == _SCALE:
                self.do_dashboard_screen(None, picture)
                return
            if label == _CROP_BY_NUMBERS:
                text = dlg.ask_text(
                    self.parent,
                    self.show_modal,
                    title="Crop by Numbers",
                    prompt="&Crop, in percent (left, top, width, height):",
                    value="0, 0, 100, 100",
                    help_text=(
                        "Four numbers in percent of the picture: how far in from the left and "
                        "from the top the crop starts, then its width and height. 10, 0, 80, 100 "
                        "keeps the middle 80 percent of the width."
                    ),
                )
                if text is None:
                    return
                try:
                    box = wpp.parse_crop(text)
                except EditRefused as exc:
                    self.say(str(exc.args[0]))
                    return
                modifiers: Any = [{"type": "crop", "args": box}]
                words = f"The crop {wpp.crop_words(box)}."
            else:
                modifiers = choices[index][1]
                words = f"{label}."
            self._send_picture_edit(picture, modifiers, label, words)

        self.background(f"reading what {picture.site} can edit", offered, chosen)

    def _send_picture_edit(self, picture: WbRow, modifiers: Any, label: str, words: str) -> None:
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Edit Picture",
            summary=(
                f"Edit {picture.title} on {picture.site}? WordPress keeps the original "
                "and makes the edit a new picture in the library."
            ),
            lines=[words, f"Sent to wp/v2/media/{picture.key}/edit"],
            yes="Make Edited Copy",
        ):
            return
        api = self.ctx(picture.site).api

        def done(new: Any) -> None:
            name = wpp.media_title(new) if isinstance(new, dict) else picture.title
            said = (
                f"Edited copy made on {picture.site}: {name}. The original is unchanged; "
                "Shift+Delete on the copy removes it."
            )
            self.say(said)
            self.history.record(Change(picture.title, said, undo=None))
            self.refresh()

        self.background(
            f"editing {picture.title}", lambda: wpp.edit_picture(api, picture, modifiers), done
        )

    def do_regenerate_sizes(self, _ref: Any, row: WbRow | None) -> None:
        picture = self._picture(row, "Regenerate Sizes")
        if picture is None:
            return
        api = self.ctx(picture.site).api

        def work() -> Any:
            from quill.core.wordpress.media_pieces import regenerate_sizes

            return regenerate_sizes(api, int(picture.key))

        def done(item: Any) -> None:
            count = len(getattr(item, "sizes", ()) or ())
            self.say(f"Sizes remade for {picture.title} on {picture.site}: {count} sizes.")

        self.background(f"remaking sizes of {picture.title}", work, done)

    def _save_post(self, row: WbRow, post: int, said: str) -> None:
        """A conflict-checked save of the file's ``post``; Ctrl+Z puts the old one back."""
        api = self.ctx(row.site).api
        old = int(row.raw.get("post", 0) or 0)

        def done(_result: Any) -> None:
            self.say(said)
            self.history.record(
                Change(
                    row.title,
                    said,
                    undo=lambda: (save(api, row, {"post": old}), f"{row.title} put back.")[1],
                )
            )
            self.refresh()

        def failed(error: BaseException) -> None:
            if isinstance(error, EditConflict):
                self.say(f"{error.args[0]} Press F5 and try again.")
                return
            self.say(getattr(error, "plain", "") or str(error))

        self.frame._run_background(
            f"WordPress Workbench: changing {row.title}",
            lambda: save(
                api, row, {"post": post}, loaded_modified=row.modified_gmt, before=row.raw
            ),
            done,
            failed,
        )

    def do_detach(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "media":
            self.say("Detach works on a file in the Media Library.")
            return
        old = int(row.raw.get("post", 0) or 0)
        if not old:
            self.say(f"{row.title} is not attached to anything.")
            return
        if dlg.confirm(
            self.parent,
            self.show_modal,
            title="Detach",
            message=f"Detach {row.title} from post {old} on {row.site}? It stays in the library.",
            yes_label="Detach",
        ):
            self._save_post(
                row, 0, f"{row.title} is attached to nothing. Ctrl+Z attaches it again."
            )

    def do_attach(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "media":
            self.say("Attach works on a file in the Media Library.")
            return
        words = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Attach {row.title}",
            prompt="&Post or page, by words or number:",
            help_text="Words from its title, or its number. QUILL lists what matches.",
        )
        if not words or not words.strip():
            return
        text = words.strip()
        api = self.ctx(row.site).api

        def find() -> list[tuple[int, str]]:
            if text.isdigit():
                return [(int(text), f"number {text}")]
            found = api.get("wp/v2/search", search=text, type="post", per_page=20)
            return [
                (int(f.get("id", 0)), f"{f.get('title', '')} ({f.get('subtype', '')})")
                for f in (found if isinstance(found, list) else [])
                if isinstance(f, dict) and f.get("id")
            ]

        def picked(matches: list[tuple[int, str]]) -> None:
            if not matches:
                self.say(f"Nothing on {row.site} matches {text}.")
                return
            index = 0
            if len(matches) > 1:
                chosen = dlg.ask_choice(
                    self.parent,
                    self.show_modal,
                    title=f"Attach {row.title}",
                    prompt="&Attach to:",
                    rows=[name for _i, name in matches],
                    help_text="The post or page the file is attached to.",
                )
                if chosen is None:
                    return
                index = chosen
            post, name = matches[index]
            if dlg.confirm(
                self.parent,
                self.show_modal,
                title="Attach",
                message=f"Attach {row.title} to {name} on {row.site}?",
                yes_label="Attach",
            ):
                self._save_post(row, post, f"{row.title} is attached to {name}. Ctrl+Z undoes it.")

        self.background(f"finding {text} on {row.site}", find, picked)

    def do_download(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "media":
            self.say("Download works on a file in the Media Library.")
            return
        source = str(row.raw.get("source_url", "") or row.link)
        name = source.rsplit("/", 1)[-1] or f"{row.title}"
        path = choose_save_path(self.parent, self.show_modal, title="Download", name=name)
        if path is None:
            return
        api = self.ctx(row.site).api

        def work() -> Path:
            from quill.core.wordpress import media_tools as mt

            got = mt.download_file(
                api._opener,
                source,
                timeout=api.timeout,
                any_type=True,
                max_bytes=wpp.DOWNLOAD_CAP,
            )
            path.write_bytes(got.content)
            return path

        self.background(
            f"downloading {row.title}",
            work,
            lambda saved: self.say(f"Saved {row.title} to {saved}."),
        )

    def do_dashboard_screen(self, _ref: Any, row: WbRow | None) -> None:
        if row is None:
            return
        profile = self.profile(row.site)
        link, why = wpp.dashboard_screen(profile.site_url if profile else "", row)
        if not link:
            self.say(why or "This has no wp-admin screen QUILL knows.")
            return
        self.say(f"Opening {why} You must be signed in to wp-admin in your browser.")
        self.commands.host.open_in_browser(link)
