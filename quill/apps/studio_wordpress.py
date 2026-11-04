"""QUILL Studio's door to WordPress: Post an Episode (wordpress.md 15 item 9).

An adapter with no WordPress code of its own. Studio makes the audio; this asks
which finished file to post, reads any chapters the file carries, and hands the
episode to :func:`quill.ui.wordpress_family.post_episode` -- the same code QUILL,
QUILL Lite and QUILL Cast run, which offers a transcript made on this computer
when there is none, uploads the audio and drafts the post.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.wordpress.episode import Chapter, Episode, title_from_file

AUDIO_WILDCARD = (
    "Audio (*.mp3;*.m4a;*.m4b;*.ogg;*.opus;*.flac;*.wav)"
    "|*.mp3;*.m4a;*.m4b;*.ogg;*.opus;*.flac;*.wav|All files (*.*)|*.*"
)

#: The WordPress menu's one row: label (with its key) and what it runs.
POST_LABEL = "&Post an Episode to WordPress...\tCtrl+Shift+W"


def studio_episode(path: Path) -> Episode:
    """A finished Studio file as an episode: its name for a title, its own chapters."""
    from quill.core.podcasts.chapter_sources import read_file_chapters

    try:
        found = list(read_file_chapters(path))
    except Exception:  # noqa: BLE001 - a file with unreadable tags still posts
        found = []
    return Episode(
        title=title_from_file(path.name),
        audio_path=path,
        chapters=tuple(Chapter(c.start_ms / 1000.0, str(c.title)) for c in found),
    )


def post_an_episode(app: Any) -> None:
    from quill.ui import wordpress_family as fam
    from quill.ui import wordpress_listen_dialogs as ldlg

    if getattr(app, "_safe_mode", False):
        app._announce(fam.SAFE_MODE_SENTENCE)
        return
    path = ldlg.pick_file(
        app.frame,
        app._show_modal_dialog,
        title="Post an Episode to WordPress",
        wildcard=AUDIO_WILDCARD,
    )
    if path is not None:
        fam.post_episode(app, studio_episode(path))


def build_wordpress_menu(app: Any, wx: Any) -> tuple[Any, list[tuple[Any, Any]]]:
    """The WordPress menu and its bindings; the caller hangs it on the bar."""
    menu = wx.Menu()
    item_id = wx.NewIdRef()
    menu.Append(item_id, POST_LABEL)
    return menu, [(item_id, lambda: post_an_episode(app))]
