"""Edit a Picture on the Site, and alternative text for the whole library (wordpress.md 9.15).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands` (through
:class:`~quill.ui.wordpress_api_writing_commands.WordPressApiWritingCommands`).

- **Edit a Picture on the Site** (``media/{id}/edit``, WordPress 5.5+): turn,
  flip, or crop to a ratio. WordPress keeps the original and makes the edit a
  new library item; Describe Image then runs on the result when AI is on, so
  you hear what the crop kept.
- **Alt Text for the Whole Library:** every picture in the Media Library with
  no alternative text, one after another, with Suggest, saved in batches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import media_alt as ma
from quill.core.wordpress import media_edit as me
from quill.core.wordpress import media_tools as mt
from quill.core.wordpress import site_media as wpm
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_api_base import WordPressApiBase

if TYPE_CHECKING:
    from quill.core.ai.doc_images import DocImage
    from quill.core.wordpress import sites as st


class WordPressPictureEditCommands(WordPressApiBase):
    # ------------------------------------------------------------------ #
    # Edit a Picture on the Site

    def cmd_edit_picture_on_site(self) -> None:
        target = self._media_site("Edit a Picture on the Site")  # type: ignore[attr-defined]
        if target is None:
            return
        profile, copy = target
        text = self.host.current_text() if copy else ""
        image = ma.image_at(text, self.host.caret_offset()) if copy else None
        media_id = ma.media_id_in(text, image) if image is not None else 0

        def work(api: Any, index: Any, _account: Any) -> tuple[Any, tuple[str, ...], Any]:
            modifiers = index.edit_modifiers()
            if image is None:
                return api, modifiers, list(wpm.list_media(api, media_type="image"))
            if media_id:
                return (
                    api,
                    modifiers,
                    wpm.media_from_payload(api.get(f"wp/v2/media/{media_id}", context="edit")),
                )
            return api, modifiers, mt.find_media_by_address(api, image.source)

        def found(result: tuple[Any, tuple[str, ...], Any]) -> None:
            api, modifiers, data = result
            if image is not None:
                if data is None:
                    self.host.announce(
                        f"This picture is not in {profile.name}'s Media Library, so the site "
                        "cannot edit it. Upload it first."
                    )
                    return
                self._choose_edit(profile, api, data, image, modifiers)
                return
            if not data:
                self.host.announce(f"{profile.name}'s Media Library has no pictures.")
                return
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Edit a Picture on the Site",
                prompt="&Picture:",
                rows=[m.spoken() for m in data],
                help_text=(
                    "The picture to edit. WordPress keeps it as it is and makes the edit a new "
                    "picture in the library."
                ),
            )
            if picked is not None:
                self._choose_edit(profile, api, data[picked], None, modifiers)

        self.with_feature(
            profile, "edit_picture", f"reading pictures on {profile.name}", work, found
        )

    def _choose_edit(
        self,
        profile: st.SiteProfile,
        api: Any,
        item: wpm.MediaItem,
        image: DocImage | None,
        modifiers: tuple[str, ...],
    ) -> None:
        name = item.title or item.filename
        edits = me.offered(modifiers, item)
        if not edits:
            self.host.announce(f"{profile.name} offers no edits QUILL can make to {name}.")
            return
        picked = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title=f"Edit {name}",
            prompt="&Edit:",
            rows=[e.label for e in edits],
            help_text=(
                f"{name} is {item.width} by {item.height}. A crop keeps the middle of the "
                "picture at the shape you choose."
            ),
        )
        if picked is None:
            return
        edit = edits[picked]
        width, height = me.result_size(edit, item.width, item.height)
        size = f" The new picture is about {width} by {height}." if width and height else ""
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Edit a Picture on the Site",
            message=(
                f"{edit.label}: {name}, on {profile.name}? WordPress keeps the original and "
                f"makes the edit a new picture in the library.{size}"
            ),
            yes_label="Make Edited Copy",
        ):
            return
        self.background(  # type: ignore[attr-defined]
            f"editing {name} on {profile.name}",
            lambda: me.edit_on_site(api, item, edit),
            lambda new: self._edited(profile, api, new, image),
        )

    def _edited(
        self, profile: st.SiteProfile, api: Any, new: wpm.MediaItem, image: DocImage | None
    ) -> None:
        name = new.title or new.filename
        size = f", {new.width} by {new.height}" if new.width else ""
        self.host.announce(
            f"Edited copy made on {profile.name}: {name}{size}. The original is unchanged."
        )
        if image is not None and dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Edit a Picture on the Site",
            message="Use the edited copy here, in place of the original?",
            yes_label="Use It Here",
        ):
            self._put_source(image, new.source_url, new.width)  # type: ignore[attr-defined]
        if callable(getattr(self.host, "ai_describe_image", None)):
            self._describe(new, api, name)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Alt Text for the Whole Library

    def cmd_library_alt_text(self) -> None:
        target = self._media_site("Alt Text for the Whole Library")  # type: ignore[attr-defined]
        if target is None:
            return
        profile = target[0]

        def work(api: Any, index: Any, _account: Any) -> tuple[Any, bool, list[wpm.MediaItem]]:
            return api, index.supports("batch/v1"), me.pictures_without_alt(api)

        self.with_feature(
            profile,
            "library_alt",
            f"finding pictures without alternative text on {profile.name}",
            work,
            lambda found: self._show_library_alt(profile, *found),
        )

    def _show_library_alt(
        self, profile: st.SiteProfile, api: Any, can_batch: bool, items: list[wpm.MediaItem]
    ) -> None:
        site = profile.name
        if not items:
            self.host.announce(f"Every picture in {site}'s Media Library has alternative text.")
            return
        written: dict[int, str] = {}
        saved: list[int] = []

        def rows() -> list[str]:
            return [me.library_row(m, written, saved) for m in items]

        def waiting() -> dict[int, str]:
            return {i: t for i, t in written.items() if i not in saved}

        def save(quiet_when_none: bool = True) -> None:
            pending = waiting()
            if not pending:
                if not quiet_when_none:
                    self.host.announce("Nothing is waiting to be saved.")
                return

            def done(ids: list[int]) -> None:
                saved.extend(ids)
                missed = len(pending) - len(ids)
                extra = (
                    f" {missed} could not be saved; {site} refused them, so try those again."
                    if missed
                    else ""
                )
                noun = "description" if len(ids) == 1 else "descriptions"
                self.host.announce(f"{len(ids)} {noun} saved on {site}.{extra}")

            self.background(  # type: ignore[attr-defined]
                f"saving alternative text on {site}",
                lambda: me.save_alt_texts(api, pending, can_batch=can_batch),
                done,
            )

        def keep(item: wpm.MediaItem, value: str | None) -> bool:
            if value is None or not value.strip():
                return False
            written[item.id] = value.strip()
            if item.id in saved:
                saved.remove(item.id)
            if len(waiting()) >= me.BATCH_SIZE:
                save()
            return True

        def ask(item: wpm.MediaItem, value: str) -> str | None:
            return dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Alternative Text: {item.title or item.filename}",
                prompt="&Alternative text:",
                value=value,
                multiline=True,
                help_text=(
                    "What this picture shows, for someone using a screen reader. This becomes "
                    "the library's default; each page can still say what it means there."
                ),
            )

        def write(index: int | None) -> object:
            if index is None or index >= len(items):
                return None
            item = items[index]
            return rows() if keep(item, ask(item, written.get(item.id, ""))) else None

        def suggest(index: int | None) -> object:
            if index is None or index >= len(items):
                return None
            item = items[index]
            name = item.title or item.filename
            context = ma.ImageContext(caption=item.caption)

            def fill(proposal: str) -> None:
                if keep(item, ask(item, proposal)):
                    self.host.announce(
                        f"Alternative text written for {name}. It is saved with the next batch."
                    )

            self._suggest_alt(item, api, name, context, fill)  # type: ignore[attr-defined]
            return None

        def save_now(_index: int | None) -> object:
            save(quiet_when_none=False)
            return rows()

        count = len(items)
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Alt Text for the Whole Library, {site}",
            purpose=(
                f"{count} picture{'s' if count != 1 else ''} in {site}'s Media Library with no "
                f"alternative text. Write or Suggest for each; every {me.BATCH_SIZE} are saved "
                "together, and the rest when you close this window."
            ),
            list_label="&Pictures:",
            list_help=(
                "Each picture's name, and whether its alternative text is written, saved, or "
                "still missing. Enter writes it."
            ),
            rows=rows(),
            details=lambda i: _details(items[i], written),
            on_enter=write,
            actions=[
                dlg.Action("&Write...", "Write the selected picture's alternative text.", write),
                dlg.Action(
                    "&Suggest...",
                    "Ask your chosen AI to propose alternative text from the picture. You read "
                    "and change it before anything is kept.",
                    suggest,
                ),
                dlg.Action(
                    "Save &Now",
                    "Save what you have written so far without waiting for the batch.",
                    save_now,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()
        save()


def _details(item: wpm.MediaItem, written: dict[int, str]) -> str:
    lines = [
        f"File: {item.filename}",
        f"Size: {item.width} by {item.height}" if item.width else "Size: not given",
        f"Caption: {item.caption or 'none'}",
        f"Alternative text: {written.get(item.id) or 'none yet'}",
        f"Address: {item.source_url}",
    ]
    return "\n".join(lines)
