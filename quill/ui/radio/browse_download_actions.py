"""What a row's download and transport verbs actually do.

Split out of ``browse_tree_menu`` under GATE-11 (extract, never rebaseline)
when a downloaded row grew its own verbs: Play/Pause, a Stop of its own, and
Remove Download. That module is a map from action ids to handlers, and these
are five answers to one question -- *what is on disk for this row, and what can
be done to it* -- which is a different question from *what does this row
offer*.

The disk is the record. Whether a row is downloaded is one ``is_file()``
against the path the download would have been written to: no index, no scan on
startup, and no network, so opening a context menu never costs a round trip and
somebody who deleted the file in Explorer has un-downloaded that episode.
"""

from __future__ import annotations

from typing import Any


def is_downloaded(dialog: Any, node: Any, station: Any) -> bool:
    """Whether this row already has a saved copy on disk.

    One local ``is_file()`` against the path the download would have been
    written to -- no scan, no index, and no network, so it obeys the rule that
    opening a menu never costs a round trip.
    """
    if station is None:
        return False
    from quill.core.paths import app_data_dir
    from quill.core.radio import downloaded_media

    return downloaded_media.is_downloaded(
        app_data_dir(), station, group=show_group(dialog, node, station)
    )


def show_group(dialog: Any, node: Any, station: Any) -> str:
    """The show a podcast episode belongs to, for the per-show download folder.

    The parent row's text minus its unheard badge -- the same name Download
    All uses, so single and bulk downloads land in the same folder. "" for
    everything else, which files exactly as before.
    """
    from quill.core.podcasts.radio_listens import PODCAST_EPISODE_SOURCES

    if str(getattr(station, "source", "")) not in PODCAST_EPISODE_SOURCES:
        return ""
    try:
        parent = dialog._tree.GetItemParent(node)
        if parent is not None and parent.IsOk():
            return dialog._tree.GetItemText(parent).split(" (")[0]
    except Exception:  # noqa: BLE001 - a widget probe must never break Download
        pass
    return ""


def stop_playback(dialog: Any, station: Any) -> None:
    """Stop, and say so -- whether or not this row is the one playing."""
    if dialog._is_playing(station):
        dialog._controller.stop()
        dialog._announce("Stopped.")
        return
    dialog._controller.stop()
    dialog._announce("Nothing was playing.")


def remove_download(dialog: Any, node: Any, station: Any) -> None:
    """Delete this row's saved copy; the subscription is untouched."""
    from quill.core.paths import app_data_dir
    from quill.core.radio import downloaded_media

    dialog._announce(
        downloaded_media.remove_download(
            app_data_dir(), station, group=show_group(dialog, node, station)
        )
    )


def download_all(dialog: Any, node: Any, host: Any) -> None:
    """Download every savable row under this folder, bounded and counted.

    It used to enqueue silently and say only whatever the queue said next
    (11.4): a folder of forty chapters, thirty-nine of them already on disk,
    reported the same thing as a folder of forty new ones.
    """
    from quill.core.podcasts.download_batch import plan_download_all
    from quill.ui.radio import download_command, download_runner

    title = dialog._tree.GetItemText(node)
    rows = [r for r in dialog._loaded_stations_under(node) if download_command.can_download(r)]
    if not rows:
        dialog._announce(f"Nothing under {title} can be saved.")
        return
    batch = plan_download_all(
        rows,
        already_have=lambda row: download_runner.already_have(host, row, work=title),
    )
    if batch.started:
        download_command.download_book(host, list(batch.started), title=title)
    dialog._announce(batch.sentence(title))
