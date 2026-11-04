"""The Media Library window, and inserting from it (wordpress.md 6.1, 6.3, 6.4).

A mixin of :class:`~quill.ui.wordpress_media_commands.WordPressMediaCommands`,
moved here from ``wordpress_site_commands.py`` when the window grew Used In,
Attach, Featured Image and the AI actions. Reaches the editor only through
``self.host``; every network call runs in ``self.background``.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.ai.doc_images import DocImage
from quill.core.wordpress import local as lc
from quill.core.wordpress import media_alt as ma
from quill.core.wordpress import media_tools as mt
from quill.core.wordpress import site_media as wpm
from quill.core.wordpress.site import human_size, plain_text
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui import wordpress_media_dialogs as mdlg
from quill.ui.wordpress_site_commands import backup_media, picture_markup, picture_size_text

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

#: Up to this many files, Used In is found for all of them as the window opens.
USED_IN_SCAN_LIMIT = 500


class WordPressMediaLibrary:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # where, and for which document

    def _media_site(self, title: str) -> tuple[st.SiteProfile, lc.WorkingCopy | None] | None:
        """The site of the WordPress document in front, else one the person picks."""
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return None
        copy = self.local.copy_for_path(self.host.current_path())
        profile = store.get(copy.site_id) if copy else None
        profile = profile or self.pick_site(store, title)  # type: ignore[attr-defined]
        if profile is None:
            return None
        return profile, copy

    def _caret_context(self) -> ma.ImageContext:
        text = self.host.current_text()
        caret = self.host.caret_offset()
        return ma.image_context(text, DocImage(0, "", "", "markdown", caret, caret))

    def _used_in_cache(self, site_id: str) -> dict[int, list[mt.UsedIn]]:
        caches: dict[str, dict[int, list[mt.UsedIn]]] = self.__dict__.setdefault("_wp_used_in", {})
        return caches.setdefault(site_id, {})

    # ------------------------------------------------------------------ #
    # inserting (6.4)

    def cmd_insert_picture(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, _profile = found
        path = mdlg.choose_picture(
            self.host.parent, self.host.show_modal, title="Insert Picture from This Computer"
        )
        if path is None:
            return
        context = self._caret_context()
        fuller: list[str] = []
        answer = idlg.ask_image(
            self.host.parent,
            self.host.show_modal,
            name=path.name,
            size_text=picture_size_text(path),
            on_suggest_async=lambda fill: self._suggest_alt(  # type: ignore[attr-defined]
                path, None, path.name, context, fill, fuller.append
            ),
            on_describe=lambda: self._describe(path, None, path.name),  # type: ignore[attr-defined]
        )
        if answer is None:
            return
        self.host.insert_text(picture_markup(copy.text_format, path.as_uri(), answer))
        copy = self.local.copy_for_path(self.host.current_path()) or copy
        copy.pending_uploads.append({
            "path": str(path),
            "alt": answer.alt,
            "caption": answer.caption,
            "featured": answer.featured,
        })
        self.local.save(copy)
        self.host.announce(
            f"Picture inserted: {answer.alt or path.name}. It is uploaded when you next send."
        )
        self._offer_fuller(copy, fuller)

    def _offer_fuller(self, copy: lc.WorkingCopy, fuller: list[str]) -> None:
        """Add a Fuller Description After the Image, when the AI wrote one (6.8)."""
        text = fuller[-1].strip() if fuller else ""
        if not text or not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Fuller Description",
            message=(
                "Your AI also wrote a fuller description, as it does for a chart or a diagram. "
                "Add it as a paragraph after the picture, for you to edit?"
            ),
            yes_label="Add Description",
        ):
            return
        if copy.text_format == "html":
            self.host.insert_text(f"<p>{html.escape(text, quote=False)}</p>\n")
        else:
            self.host.insert_text(f"\n{text}\n")

    def cmd_insert_from_library(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        api = self.api(profile)  # type: ignore[attr-defined]

        def choose(items: list[wpm.MediaItem]) -> None:
            if not items:
                self.host.announce(f"{profile.name}'s Media Library is empty. Use Upload Files.")
                return
            index = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Insert from Media Library",
                prompt="&Files:",
                rows=[m.spoken() for m in items],
                help_text=(
                    f"Every file in {profile.name}'s Media Library, newest first. Choose one to "
                    "insert at the caret; a picture opens the picture dialog first."
                ),
            )
            if index is not None:
                self._insert_media(copy, items[index], api)

        self.background(  # type: ignore[attr-defined]
            f"reading the Media Library on {profile.name}",
            lambda: list(wpm.list_media(api)),
            choose,
        )

    def _insert_media(self, copy: lc.WorkingCopy, m: wpm.MediaItem, api: Any) -> bool:
        """Insert one library file at the caret: a picture through the image dialog (6.7)."""
        name = m.title or m.filename
        if m.kind_label != "image":
            self.host.insert_text(media_markup(copy.text_format, m))
            self.host.announce(f"{m.kind_label.capitalize()} inserted: {name}.")
            return True
        context = self._caret_context()
        fuller: list[str] = []
        answer = idlg.ask_image(
            self.host.parent,
            self.host.show_modal,
            name=name,
            size_text=f"image is {m.width} by {m.height}" if m.width else "",
            alt=m.alt_text,
            caption=m.caption,
            on_suggest_async=lambda fill: self._suggest_alt(  # type: ignore[attr-defined]
                m, api, name, context, fill, fuller.append
            ),
            on_describe=lambda: self._describe(m, api, name),  # type: ignore[attr-defined]
        )
        if answer is None:
            return False
        self.host.insert_text(picture_markup(copy.text_format, m.source_url, answer, media_id=m.id))
        if answer.featured:
            fresh = self.local.copy_for_path(self.host.current_path()) or copy
            fresh.properties["featured_media"] = m.id
            self.local.save(fresh)
        self.host.announce(f"Picture inserted: {answer.alt or name}.")
        self._offer_fuller(copy, fuller)
        return True

    # ------------------------------------------------------------------ #
    # the window (6.1, 6.3)

    def cmd_media_library(self) -> None:
        target = self._media_site("Media Library")
        if target is None:
            return
        profile, copy = target
        api = self.api(profile)  # type: ignore[attr-defined]
        self.background(  # type: ignore[attr-defined]
            f"reading the Media Library on {profile.name}",
            lambda: list(wpm.list_media(api)),
            lambda items: self._show_media(profile, api, copy, items),
        )

    def _scan_used_in(self, profile: st.SiteProfile, api: Any, items: list[wpm.MediaItem]) -> None:
        """Find Used In for a small library as the window opens (6.1), once per site."""
        cache = self._used_in_cache(profile.id)
        if not items or len(items) > USED_IN_SCAN_LIMIT or all(m.id in cache for m in items):
            return

        def done(found: dict[int, list[mt.UsedIn]]) -> None:
            cache.update(found)
            used = sum(1 for places in found.values() if places)
            self.host.announce(
                f"Used In is ready: {used} of {len(found)} files on {profile.name} are used "
                "in a page or post."
            )

        self.background(  # type: ignore[attr-defined]
            f"finding where each file is used on {profile.name}",
            lambda: mt.used_in_all(api, items),
            done,
        )

    def _show_media(
        self,
        profile: st.SiteProfile,
        api: Any,
        copy: lc.WorkingCopy | None,
        items: list[wpm.MediaItem],
    ) -> None:
        shown = list(items)
        cache = self._used_in_cache(profile.id)
        self._scan_used_in(profile, api, items)

        def used_in_words(m: wpm.MediaItem) -> str:
            if m.id not in cache:
                return "not checked yet; choose Used In"
            places = cache[m.id]
            return ", ".join(p.spoken() for p in places) if places else "nothing"

        def details(index: int) -> str:
            m = shown[index]
            size = f"{m.width} by {m.height}, " if m.width else ""
            return (
                f"Title: {m.title}\nFile: {m.filename}\nType: {m.mime_type}\n"
                f"Size: {size}{human_size(m.filesize) if m.filesize else 'unknown'}\n"
                f"Address: {m.source_url}\n"
                f"Alternative text: {m.alt_text or 'none'}\nCaption: {m.caption or 'none'}\n"
                f"Description: {plain_text(m.description) or 'none'}\n"
                f"Attached to: {'item ' + str(m.post) if m.post else 'nothing'}\n"
                f"Used in: {used_in_words(m)}"
            )

        def on_filter(words: str) -> list[str]:
            needle = words.strip().lower()
            shown[:] = [
                m
                for m in items
                if needle in (m.title + " " + m.filename + " " + m.alt_text).lower()
            ]
            return [m.spoken() for m in shown]

        def replace(old: wpm.MediaItem, new: wpm.MediaItem) -> None:
            for group in (items, shown):
                for i, m in enumerate(group):
                    if m.id == old.id:
                        group[i] = new

        def need_document(what: str) -> bool:
            if copy is None:
                self.host.announce(f"Open a WordPress document first to {what}.")
                return False
            return True

        def insert(index: int | None) -> object:
            if index is None or not need_document("insert a file into it"):
                return None
            assert copy is not None
            return dlg.CLOSE if self._insert_media(copy, shown[index], api) else None

        def used_in(index: int | None) -> object:
            if index is None:
                return None
            m = shown[index]
            name = m.title or m.filename
            if m.id in cache:
                self._say_used_in(profile, name, cache[m.id])
                return None

            def done(places: list[mt.UsedIn]) -> None:
                cache[m.id] = places
                self._say_used_in(profile, name, places)

            self.host.announce(f"Searching {profile.name}'s pages and posts for {name}.")
            self.background(  # type: ignore[attr-defined]
                f"finding where {name} is used", lambda: mt.used_in_one(api, m), done
            )
            return None

        def attach(index: int | None) -> object:
            if index is None or not need_document("attach a file to it"):
                return None
            assert copy is not None
            m = shown[index]
            if not copy.remote_id:
                self.host.announce(
                    f"This document is not on {profile.name} yet. Save Draft to Site first, "
                    "then attach."
                )
                return None
            title = copy.title or "this document"

            def done(updated: wpm.MediaItem) -> None:
                replace(m, updated)
                self.host.announce(
                    f"{m.title or m.filename} attached to {title} on {profile.name}."
                )

            self.background(  # type: ignore[attr-defined]
                "attaching the file",
                lambda: wpm.update_media(api, m.id, post=copy.remote_id),
                done,
            )
            return None

        def featured(index: int | None) -> object:
            if index is None or not need_document("give it a featured image"):
                return None
            assert copy is not None
            m = shown[index]
            if m.kind_label != "image":
                self.host.announce("Only a picture can be a featured image.")
                return None
            fresh = self.local.copy_for_path(self.host.current_path()) or copy
            fresh.properties["featured_media"] = m.id
            self.local.save(fresh)
            self.host.announce(
                f"{m.title or m.filename} is now the featured image. It goes to {profile.name} "
                "with your next Save Draft to Site or Publish."
            )
            return None

        def edit_alt(m: wpm.MediaItem, value: str) -> None:
            alt = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Edit Alternative Text",
                prompt="&Alternative text:",
                value=value,
                multiline=True,
                help_text=(
                    "The library's default alternative text for this picture. Each place it is "
                    "used can still have its own. Nothing is saved until you choose OK."
                ),
            )
            if alt is None:
                return

            def done(updated: wpm.MediaItem) -> None:
                replace(m, updated)
                self.host.announce(f"Alternative text saved on {profile.name}.")

            self.background(  # type: ignore[attr-defined]
                "saving the picture's details",
                lambda: wpm.update_media(api, m.id, alt_text=alt.strip()),
                done,
            )

        def edit(index: int | None) -> object:
            if index is not None:
                edit_alt(shown[index], shown[index].alt_text)
            return None

        def picture_only(index: int | None) -> wpm.MediaItem | None:
            if index is None:
                return None
            if shown[index].kind_label != "image":
                self.host.announce("That file is not a picture.")
                return None
            return shown[index]

        def suggest(index: int | None) -> object:
            m = picture_only(index)
            if m is not None:
                self._suggest_alt(  # type: ignore[attr-defined]
                    m, api, m.title or m.filename, ma.ImageContext(), lambda t: edit_alt(m, t)
                )
            return None

        def describe(index: int | None) -> object:
            m = picture_only(index)
            if m is not None:
                self._describe(m, api, m.title or m.filename)  # type: ignore[attr-defined]
            return None

        def copy_address(index: int | None) -> object:
            if index is not None:
                self.host.set_clipboard_text(shown[index].source_url)
                self.host.announce("Address copied.")
            return None

        def remove(index: int | None) -> object:
            if index is None:
                return None
            m = shown[index]
            places = cache.get(m.id)
            uses = ""
            if places is not None:
                uses = (
                    f" {len(places)} page{'s' if len(places) != 1 else ''} or "
                    f"post{'s' if len(places) != 1 else ''} use it, and would show a missing file."
                    if places
                    else " Nothing on the site links to it."
                )
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Remove from Library",
                message=(
                    f"Remove {m.filename} from {profile.name}'s Media Library?{uses} "
                    "WordPress has no Trash for media, so QUILL first saves a copy in your "
                    "Documents folder, under 'Removed from WordPress'."
                ),
                yes_label="Remove",
            ):
                return None

            def work() -> Path:
                saved = backup_media(api, m, profile.name)
                wpm.delete_media(api, m.id)
                return saved

            self.background(  # type: ignore[attr-defined]
                "removing the file",
                work,
                lambda saved: self.host.announce(
                    f"Removed from the library. A copy is in {saved.parent}."
                ),
            )
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Media Library: {profile.name}",
            purpose=f"Every file in {profile.name}'s Media Library, newest first.",
            list_label="Fi&les:",
            list_help="Each row gives the title, type, size, alternative text and upload date.",
            rows=[m.spoken() for m in items],
            details=details,
            on_filter=on_filter,
            filter_label="&Find:",
            filter_help="Type part of a title, file name or alternative text, and press Enter.",
            actions=[
                dlg.Action(
                    "&Insert...",
                    "Insert the selected file at the caret; a picture opens the picture dialog.",
                    insert,
                ),
                dlg.Action(
                    "&Used In",
                    "Which pages and posts link to the selected file.",
                    used_in,
                ),
                dlg.Action(
                    "A&ttach to This Page or Post",
                    "Make the open document the selected file's parent on the site. Galleries "
                    "and some themes use this; it is separate from inserting.",
                    attach,
                ),
                dlg.Action(
                    "Set as Featured Ima&ge",
                    "Use the selected picture as the open document's featured image.",
                    featured,
                ),
                dlg.Action(
                    "&Suggest Alternative Text...",
                    "Ask your chosen AI to propose alternative text for the selected picture. "
                    "It goes into an edit field; nothing is saved until you choose OK.",
                    suggest,
                ),
                dlg.Action(
                    "Describe I&mage...",
                    "Ask your chosen AI for a longer description of the selected picture, "
                    "for you rather than for visitors.",
                    describe,
                ),
                dlg.Action(
                    "&Edit Alternative Text...",
                    "Change the library's alternative text on the site.",
                    edit,
                ),
                dlg.Action(
                    "Copy &Address", "Put the file's web address on the clipboard.", copy_address
                ),
                dlg.Action(
                    "&Remove from Library...",
                    "Delete the file from the site, after saving a copy here.",
                    remove,
                ),
            ],
        )
        window.Destroy()

    def _say_used_in(self, profile: st.SiteProfile, name: str, places: list[mt.UsedIn]) -> None:
        if not places:
            self.host.announce(f"Nothing on {profile.name} links to {name}.")
            return
        if len(places) <= 5:
            where = "; ".join(p.spoken() for p in places)
            count = f"{len(places)} place{'s' if len(places) != 1 else ''}"
            self.host.announce(f"{name} is used in {count} on {profile.name}: {where}.")
            return
        dlg.show_report(
            self.host.parent,
            self.host.show_modal,
            title=f"Used In: {name}",
            text=f"{name} is used in {len(places)} places on {profile.name}.\n\n"
            + "\n".join(p.spoken() for p in places),
            help_text="The pages and posts whose content links to this file.",
        )


def media_markup(text_format: str, m: wpm.MediaItem) -> str:
    """Sound, video and documents at the caret (6.4); pictures go through the image dialog."""
    title = (m.title or m.filename).replace('"', "'")
    if m.kind_label in ("audio", "video"):
        tag = m.kind_label
        return (
            f'\n<figure class="wp-block-{tag}"><{tag} controls src="{m.source_url}">'
            f"</{tag}></figure>\n"
        )
    if text_format == "markdown":
        return f"[{title.replace('[', '(').replace(']', ')')}]({m.source_url})"
    return f'<a href="{m.source_url}">{title}</a>'
