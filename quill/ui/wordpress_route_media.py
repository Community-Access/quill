"""Big uploads, Regenerate Sizes, the space a site uses, and its design (wordpress.md 9.16).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands` (through
:class:`~quill.ui.wordpress_route_commands.WordPressRouteCommands`), shared by
QUILL and QUILL Lite.

* **Upload a Large File:** a long video or big audio file goes up in one
  request on a background task, with a word first that it can take a while.
  WordPress has no upload in pieces (see :mod:`quill.core.wordpress.media_pieces`).
* **Regenerate Sizes:** remake a picture's thumbnail and medium copies.
* **Space Used:** uploads, themes, plugins, WordPress and the database, in words.
* **Download a Copy of the Site's Design:** a block theme's zip, with the
  person's changes, saved on this computer.
"""

from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import media_pieces as mp
from quill.core.wordpress import site_media as wpm
from quill.core.wordpress import site_space as ss
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_route_dialogs as rdlg

if TYPE_CHECKING:
    from pathlib import Path

    from quill.core.wordpress import sites as st


class WordPressRouteMedia:
    host: Any

    # ------------------------------------------------------------------ #
    # Upload a Large File

    def cmd_upload_large_file(self) -> None:
        profile = self.route_site("Upload a Large File")  # type: ignore[attr-defined]
        if profile is None:
            return
        path = rdlg.pick_file(
            self.host.parent,
            self.host.show_modal,
            title="Upload a Large File",
            wildcard=rdlg.LARGE_FILE_WILDCARD,
        )
        if path is None:
            return
        content = path.read_bytes()
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if len(content) >= mp.LARGE_FROM:
            self.host.announce(
                f"Uploading {path.name}, {ss.size_words(len(content))}, to {profile.name}. A file "
                "this size can take a while; QUILL says when it is there."
            )
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "media",
            f"uploading {path.name} to {profile.name}",
            lambda api: wpm.upload_media(api, path.name, content, kind),
            lambda media: self._uploaded(profile, path, media),
        )

    def _uploaded(self, profile: st.SiteProfile, path: Path, media: wpm.MediaItem) -> None:
        if media.source_url:
            self.host.set_clipboard_text(media.source_url)
            self.host.announce(
                f"{path.name} is in {profile.name}'s Media Library. Its address is on the "
                "clipboard."
            )
        else:
            self.host.announce(f"{path.name} is in {profile.name}'s Media Library.")

    # ------------------------------------------------------------------ #
    # Regenerate Sizes

    def cmd_regenerate_sizes(self) -> None:
        profile = self.route_site("Regenerate Sizes")  # type: ignore[attr-defined]
        if profile is None:
            return
        self.with_route(  # type: ignore[attr-defined]
            profile,
            "post_process",
            f"listing pictures on {profile.name}",
            lambda api: (api, list(wpm.list_media(api, media_type="image"))),
            lambda got: self._pick_to_regenerate(profile, got[0], got[1]),
        )

    def _pick_to_regenerate(
        self, profile: st.SiteProfile, api: Any, pictures: list[wpm.MediaItem]
    ) -> None:
        if not pictures:
            self.host.announce(f"{profile.name} has no pictures in its Media Library.")
            return
        index = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Regenerate Sizes",
            prompt="&Picture:",
            rows=[p.spoken() for p in pictures],
            help_text=(
                "The picture whose thumbnail, medium and large copies the site should make "
                "again from the picture as it is now, for example after Edit a Picture on the "
                "Site."
            ),
        )
        if index is None:
            return
        picture = pictures[index]
        name = picture.title or picture.filename
        self.background(  # type: ignore[attr-defined]
            f"remaking the sizes of {name}",
            lambda: mp.regenerate_sizes(api, picture.id),
            lambda done: self.host.announce(
                f"{profile.name} remade {len(done.sizes)} sizes of {name}."
                if done.sizes
                else f"{profile.name} remade the sizes of {name}."
            ),
        )

    # ------------------------------------------------------------------ #
    # Space Used

    def cmd_site_space(self) -> None:
        profile = self.route_site("Space Used")  # type: ignore[attr-defined]
        if profile is None:
            return

        def show(space: ss.SpaceUse) -> None:
            lines = space.lines()
            total = (
                f"{profile.name} uses {ss.size_words(space.total)} altogether."
                if space.total >= 0
                else f"{profile.name} could not measure the space it uses."
            )
            self.host.announce(total)
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title="Space Used",
                text=f"Space used on {profile.name}:\n\n" + "\n".join(lines),
                help_text=(
                    "How much room the site's uploads, themes, plugins, WordPress itself and "
                    "its database take, as the site measured them."
                ),
            )

        self.with_route(  # type: ignore[attr-defined]
            profile,
            "directory_sizes",
            f"measuring the space {profile.name} uses",
            ss.read_space,
            show,
        )

    # ------------------------------------------------------------------ #
    # Download a Copy of the Site's Design

    def cmd_download_design(self) -> None:
        profile = self.route_site("Download a Copy of the Site's Design")  # type: ignore[attr-defined]
        if profile is None:
            return

        def save(got: tuple[bytes, str]) -> None:
            body, name = got
            path = rdlg.save_as(
                self.host.parent,
                self.host.show_modal,
                title="Download a Copy of the Site's Design",
                name=name,
                wildcard="Zip files (*.zip)|*.zip",
            )
            if path is None:
                self.host.announce("Nothing was saved.")
                return
            path.write_bytes(body)
            self.host.announce(
                f"A copy of {profile.name}'s design is saved as {path.name}, "
                f"{ss.size_words(len(body))}."
            )

        self.with_route(  # type: ignore[attr-defined]
            profile,
            "export",
            f"exporting {profile.name}'s design",
            ss.export_design,
            save,
        )
