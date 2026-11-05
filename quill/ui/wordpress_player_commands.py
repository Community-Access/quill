"""Play, Play Media Here, and the other ways to listen (wordpress.md 6.1a).

A mixin of :class:`~quill.ui.wordpress_media_commands.WordPressMediaCommands`,
shared by QUILL and QUILL Lite; it reaches the editor only through
``self.host``. The Media Library's Play action calls
:meth:`_play_library_item`; a document's audio or video block plays with
:meth:`cmd_play_media_here`. Both open :mod:`quill.ui.wordpress_player_window`,
which streams the file and stops it on close. Captions are read from the site
in ``self.background``, only when asked for.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quill.core.wordpress import media_play as mp
from quill.ui import wordpress_player_window as pwin

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st
    from quill.core.wordpress.site_media import MediaItem

NOT_PLAYABLE = "That file is not audio or video. Play works on sound and video files."
NOTHING_HERE = (
    "There is no audio or video block at the caret. Move to one, or insert one with "
    "Insert from Media Library."
)


class WordPressPlayerCommands:
    # Provided by WordPressCommands.
    host: Any

    def cmd_play_media_here(self) -> None:
        found = self.current("Play Media Here")  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        islands = dict(copy.properties.get("islands") or {})
        playable = mp.media_at(
            self.host.current_text(), copy.text_format, self.host.caret_offset(), islands
        )
        if playable is None:
            self.host.announce(NOTHING_HERE)
            return
        self._play_media(profile, self.api(profile), playable)  # type: ignore[attr-defined]

    def _play_library_item(
        self, profile: st.SiteProfile, api: Any, item: MediaItem, items: list[MediaItem]
    ) -> None:
        playable = mp.from_library(item, items)
        if playable is None:
            self.host.announce(NOT_PLAYABLE)
            return
        self._play_media(profile, api, playable)

    def _play_media(self, profile: st.SiteProfile, api: Any, playable: mp.Playable) -> None:
        problem = mp.stream_problem(playable.url)
        if problem:
            self.host.announce(problem)
            return

        def read_captions(track: mp.CaptionTrack, done: Any) -> None:
            self.background(  # type: ignore[attr-defined]
                f"reading the captions on {profile.name}",
                lambda: mp.fetch_captions(api, track, profile.site_url),
                done,
            )

        pwin.play(
            self.host.parent,
            self.host.show_modal,
            playable,
            site_name=profile.name,
            announce=self.host.announce,
            read_captions=read_captions,
            open_in_player=self._open_in_media_player,
            open_in_browser=self.host.open_in_browser,
        )

    def _open_in_media_player(self, playable: mp.Playable) -> None:
        from quill.core import app_launcher

        if not app_launcher.is_app_released("player"):
            self.host.announce(
                "Quill Media Player is not part of this release yet. Use Open in Browser."
            )
            return
        if app_launcher.launch_app("player", extra_args=(playable.url,)):
            self.host.announce(f"Opening {playable.title} in Quill Media Player.")
            return
        self.host.announce(
            "Quill Media Player is not installed beside this app. Use Open in Browser instead."
        )
