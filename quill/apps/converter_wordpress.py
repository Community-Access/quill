"""Quill Converter's door to WordPress: Upload to WordPress (wordpress.md 15 item 9).

WordPress as a destination for what the Converter made. An adapter with no
WordPress code of its own: it asks which files to send, starting in the folder
the last conversion wrote to, and hands them to
:func:`quill.ui.wordpress_family.upload_to_wordpress` -- the same upload, the
same duplicate check and the same spoken outcome as the editors' Media Library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

UPLOAD_WILDCARD = (
    "Audio and video (*.mp3;*.m4a;*.m4b;*.ogg;*.opus;*.flac;*.wav;*.mp4;*.webm)"
    "|*.mp3;*.m4a;*.m4b;*.ogg;*.opus;*.flac;*.wav;*.mp4;*.webm|All files (*.*)|*.*"
)


def output_folder(host: Any) -> Path | None:
    """Where the last conversion wrote, else the folder the Converter would write to."""
    last = getattr(host, "_last_output", None)
    if last is not None:
        return Path(last)
    try:
        return Path(host._destination())
    except Exception:  # noqa: BLE001 - no destination yet is an ordinary state
        return None


def upload_outputs(host: Any) -> None:
    """File > Upload to WordPress."""
    from quill.ui import wordpress_family as fam
    from quill.ui import wordpress_listen_dialogs as ldlg

    if getattr(host, "_safe_mode", False):
        host._announce(fam.SAFE_MODE_SENTENCE)
        return
    paths = ldlg.pick_files(
        host.frame,
        host._show_modal_dialog,
        title="Upload to WordPress",
        wildcard=UPLOAD_WILDCARD,
        folder=output_folder(host),
    )
    if paths:
        fam.upload_to_wordpress(host, paths)
