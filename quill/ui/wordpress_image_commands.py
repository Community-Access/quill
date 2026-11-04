"""Image Size, Make a Smaller Copy and the Alt Text Review (wordpress.md 6.5, 6.8).

A mixin of :class:`~quill.ui.wordpress_media_commands.WordPressMediaCommands`.
Image Size and Make a Smaller Copy send nothing but the upload (6.12): the
size choice changes only the markup, and the copy is made on this computer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.ai.doc_images import DocImage, list_document_images
from quill.core.wordpress import local as lc
from quill.core.wordpress import media_alt as ma
from quill.core.wordpress import media_tools as mt
from quill.core.wordpress import site_media as wpm
from quill.ui import wordpress_dialogs as dlg

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

#: The local history of each placement's earlier sizes (6.7): new address -> earlier.
SIZE_HISTORY = "image_size_history"


class WordPressImageCommands:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    def _image_at_caret(self, command: str) -> DocImage | None:
        image = ma.image_at(self.host.current_text(), self.host.caret_offset())
        if image is None:
            self.host.announce(
                f"Put the caret on a picture in the document first, then choose {command}."
            )
        return image

    def _fresh(self, copy: lc.WorkingCopy) -> lc.WorkingCopy:
        return self.local.copy_for_path(self.host.current_path()) or copy

    def _same_image(self, image: DocImage) -> DocImage | None:
        """*image* again in the text as it is now, or None when it has gone."""
        for fresh in list_document_images(self.host.current_text()):
            if fresh.number == image.number and fresh.source == image.source:
                return fresh
        for fresh in list_document_images(self.host.current_text()):
            if fresh.source == image.source:
                return fresh
        return None

    def _put_source(self, image: DocImage, source: str, width: int) -> bool:
        fresh = self._same_image(image)
        if fresh is None:
            self.host.announce(
                "The picture has moved or gone from the document, so nothing changed."
            )
            return False
        self.host.replace_text(ma.with_source(self.host.current_text(), fresh, source, width))
        self.host.go_to_offset(fresh.start)
        return True

    # ------------------------------------------------------------------ #
    # Image Size (6.5, 6.7)

    def cmd_image_size(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        image = self._image_at_caret("Image Size")
        if image is None:
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        media_id = ma.media_id_in(self.host.current_text(), image)

        def work() -> list[mt.ImageSize]:
            wanted = media_id
            if not wanted:
                item = mt.find_media_by_address(api, image.source)
                wanted = item.id if item else 0
            return mt.load_image_sizes(api, wanted) if wanted else []

        self.background(
            "reading the picture's sizes",  # type: ignore[attr-defined]
            work,
            lambda sizes: self._choose_size(copy, profile, image, sizes),
        )

    def _choose_size(
        self,
        copy: lc.WorkingCopy,
        profile: st.SiteProfile,
        image: DocImage,
        sizes: list[mt.ImageSize],
    ) -> None:
        history: dict[str, dict[str, Any]] = dict(
            self._fresh(copy).properties.get(SIZE_HISTORY) or {}
        )
        earlier = history.get(image.source)
        if not sizes and not earlier:
            self.host.announce(
                f"This picture is not in {profile.name}'s Media Library, so it has no other "
                "sizes. Upload it first."
            )
            return
        current = next((s for s in sizes if s.source_url == image.source), None)
        rows = [f"Back to Earlier Size: {earlier['label']}"] if earlier else []
        offset = len(rows)
        rows += [s.spoken() + (", the size it is now" if s is current else "") for s in sizes]
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Image Size",
            prompt="&Size:",
            rows=rows,
            initial=(sizes.index(current) + offset) if current else 0,
            help_text=(
                "How wide the picture shows on the page, from the sizes WordPress made of it. "
                "Proportions are kept and nothing is cropped; only the markup changes. Back to "
                "Earlier Size puts the previous choice back."
            ),
        )
        if index is None:
            return
        if earlier and index == 0:
            source, width, label = (
                str(earlier["src"]),
                int(earlier.get("width", 0)),
                str(earlier["label"]),
            )
            history.pop(image.source, None)
        else:
            chosen = sizes[index - offset]
            if chosen is current:
                self.host.announce("The picture is already that size.")
                return
            source, width, label = chosen.source_url, chosen.width, chosen.spoken()
            history[source] = {
                "src": image.source,
                "width": current.width if current else 0,
                "label": current.spoken() if current else "the size it was",
            }
        if not self._put_source(image, source, width):
            return
        fresh = self._fresh(copy)
        fresh.properties[SIZE_HISTORY] = history
        self.local.save(fresh)
        self.host.announce(f"Picture shown at {label}.")

    # ------------------------------------------------------------------ #
    # Make a Smaller Copy (6.5)

    def cmd_smaller_copy(self) -> None:
        target = self._media_site("Make a Smaller Copy")  # type: ignore[attr-defined]
        if target is None:
            return
        profile, copy = target
        api = self.api(profile)  # type: ignore[attr-defined]
        image = ma.image_at(self.host.current_text(), self.host.caret_offset()) if copy else None
        if image is not None:
            media_id = ma.media_id_in(self.host.current_text(), image)

            def find() -> wpm.MediaItem | None:
                if media_id:
                    return wpm.media_from_payload(
                        api.get(f"wp/v2/media/{media_id}", context="edit")
                    )
                return mt.find_media_by_address(api, image.source)

            def found(item: wpm.MediaItem | None) -> None:
                if item is None:
                    self.host.announce(
                        f"This picture is not in {profile.name}'s Media Library. Upload it first."
                    )
                    return
                self._shrink(profile, api, item, image)

            self.background("finding the picture in the library", find, found)  # type: ignore[attr-defined]
            return

        def choose(items: list[wpm.MediaItem]) -> None:
            if not items:
                self.host.announce(f"{profile.name}'s Media Library has no pictures.")
                return
            index = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Make a Smaller Copy",
                prompt="&Picture:",
                rows=[m.spoken() for m in items],
                help_text="The picture to make a smaller copy of. The original is never changed.",
            )
            if index is not None:
                self._shrink(profile, api, items[index], None)

        self.background(  # type: ignore[attr-defined]
            f"reading the pictures on {profile.name}",
            lambda: list(wpm.list_media(api, media_type="image")),
            choose,
        )

    def _shrink(
        self, profile: st.SiteProfile, api: Any, item: wpm.MediaItem, image: DocImage | None
    ) -> None:
        name = item.title or item.filename
        widths = [w for w in mt.SMALLER_WIDTHS if not item.width or w < item.width]
        if not widths:
            self.host.announce(f"{name} is already {item.width} pixels wide or less.")
            return
        width_index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Make a Smaller Copy",
            prompt="&Largest width:",
            rows=[f"{w} pixels wide" for w in widths],
            help_text=(
                f"{name} is {item.width} by {item.height}. The copy keeps the proportions and is "
                "no wider than this."
            ),
        )
        if width_index is None:
            return
        format_index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Make a Smaller Copy",
            prompt="&Format:",
            rows=[f[0] for f in mt.SMALLER_FORMATS],
            help_text=(
                "JPEG suits photographs; WebP is smaller still and every current browser shows "
                "it; PNG keeps sharp edges and transparency."
            ),
        )
        if format_index is None:
            return
        max_width = widths[width_index]
        format_name = mt.SMALLER_FORMATS[format_index][0]

        def made(small: mt.SmallerCopy) -> None:
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Make a Smaller Copy",
                message=(
                    f"{name}. {small.report()} The copy was made on this computer. Upload it to "
                    f"{profile.name} as a new file? The original stays in the library."
                ),
                yes_label="Upload",
            ):
                return
            filename = mt.smaller_copy_name(
                item.filename or "picture", small.width, small.extension
            )
            self.background(  # type: ignore[attr-defined]
                f"uploading the smaller copy to {profile.name}",
                lambda: wpm.upload_media(
                    api,
                    filename,
                    small.data,
                    small.mime,
                    title=f"{name} (smaller copy)",
                    alt_text=item.alt_text,
                    caption=item.caption,
                ),
                lambda new: self._smaller_uploaded(profile, new, image),
            )

        self.background(  # type: ignore[attr-defined]
            f"making a smaller copy of {name}",
            lambda: mt.make_smaller_copy(mt.fetch_media_bytes(api, item), max_width, format_name),
            made,
        )

    def _smaller_uploaded(
        self, profile: st.SiteProfile, new: wpm.MediaItem, image: DocImage | None
    ) -> None:
        if image is not None and self._put_source(image, new.source_url, new.width):
            self.host.announce(
                f"Smaller copy uploaded to {profile.name} and used here. The original is still "
                "in the library."
            )
            return
        self.host.announce(
            f"Smaller copy uploaded to {profile.name} as {new.filename}. The original is still "
            "in the library."
        )

    # ------------------------------------------------------------------ #
    # Alt Text Review (6.8)

    def cmd_alt_text_review(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        _copy, profile = found
        rows = ma.review_rows(self.host.current_text())
        if not rows:
            self.host.announce("This document has no pictures.")
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        needing = sum(1 for r in rows if r.problem)

        def refresh() -> list[str]:
            rows[:] = ma.review_rows(self.host.current_text())
            return [r.spoken() for r in rows]

        def apply_alt(image: DocImage, value: str) -> bool:
            fresh = self._same_image(image)
            if fresh is None:
                self.host.announce("That picture has moved or gone from the document.")
                return False
            self.host.replace_text(ma.set_alt(self.host.current_text(), fresh, value.strip()))
            return True

        def ask_alt(image: DocImage, value: str) -> str | None:
            return dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Alternative Text: {image.name}",
                prompt="&Alternative text:",
                value=value,
                multiline=True,
                help_text=(
                    "What this picture contributes here, for someone using a screen reader. "
                    "If a person is shown and the page does not name them, add the name if it "
                    "matters. Nothing changes until you choose OK."
                ),
            )

        def edit(index: int | None) -> object:
            if index is None:
                return None
            image = rows[index].image
            value = ask_alt(image, image.alt_text)
            if value is None or not apply_alt(image, value):
                return None
            return refresh()

        def decorative(index: int | None) -> object:
            if index is None:
                return None
            fresh = self._same_image(rows[index].image)
            if fresh is None:
                return None
            self.host.replace_text(ma.mark_decorative(self.host.current_text(), fresh))
            return refresh()

        def suggest(index: int | None) -> object:
            if index is None:
                return None
            image = rows[index].image
            context = ma.image_context(self.host.current_text(), image)

            def fill(proposal: str) -> None:
                value = ask_alt(image, proposal)
                if value is not None and apply_alt(image, value):
                    self.host.announce(f"Alternative text set for picture {image.number}.")

            self._suggest_alt(image.source, api, image.name, context, fill)  # type: ignore[attr-defined]
            return None

        def go(index: int | None) -> object:
            if index is None:
                return None
            fresh = self._same_image(rows[index].image)
            if fresh is not None:
                self.host.go_to_offset(fresh.start)
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Alt Text Review",
            purpose=(
                f"Every picture in this document with its alternative text: {len(rows)} "
                f"picture{'s' if len(rows) != 1 else ''}, {needing} to look at. Empty, "
                "file-name-like and very long alternative text are marked."
            ),
            list_label="&Pictures:",
            list_help=(
                "Each row gives the picture's number and file, then its alternative text or "
                "what is wrong with it."
            ),
            rows=[r.spoken() for r in rows],
            details=lambda i: review_details(rows[i]),
            actions=[
                dlg.Action("&Edit...", "Write or change the selected picture's text.", edit),
                dlg.Action(
                    "Mark Decorati&ve",
                    "Empty alternative text on purpose, for a picture that adds nothing a "
                    "visitor needs; screen readers skip it.",
                    decorative,
                ),
                dlg.Action(
                    "&Suggest...",
                    "Ask your chosen AI to propose alternative text from the picture and the "
                    "text around it. You read and change it before anything is set.",
                    suggest,
                ),
                dlg.Action(
                    "&Go to Picture", "Close this window with the caret on the picture.", go
                ),
            ],
        )
        window.Destroy()


def review_details(row: ma.AltReviewRow) -> str:
    verdict = "Decorative" if row.decorative else f"Problem: {row.problem or 'none'}"
    return (
        f"Picture {row.image.number}: {row.image.source}\n"
        f"Alternative text: {row.image.alt_text or 'none'}\n{verdict}"
    )
