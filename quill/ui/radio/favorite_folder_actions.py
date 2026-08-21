"""Play, shuffle or export a whole favorites folder.

The listening half of :mod:`quill.core.radio.folder_actions`. The rules are
there and pure; what is here is the queue that has to live somewhere with a
player, and the sentences.

**Why a folder queue rather than "play them in order".** A live radio station
never ends, so there is nothing for a sequential playlist to advance *on*.
Playing a folder therefore means: start the first station, and remember the rest
so Next and Previous walk them. That is what somebody asking to "play the News
folder" actually wants -- one keystroke to the next station in the set they
chose, instead of reopening the list every time.

The queue is a plain list and an index held on the host. Deliberately not
persisted: a queue that survived a restart would leave Next moving through a
folder nobody remembers choosing.

Recordings and downloaded episodes still end, and those already have their own
queue in ``ui/radio/recordings_queue.py`` -- this one never touches it.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import folder_actions
from quill.core.radio.favorites import FavoriteStation

__all__ = [
    "export_folder",
    "next_in_folder",
    "play_folder",
    "previous_in_folder",
    "queue_summary",
]

#: Where the queue lives on the host. One attribute rather than two, so a
#: half-set state cannot exist.
_QUEUE_ATTR = "_radio_folder_queue"


def _set_queue(host: Any, folder: str, stations: list[FavoriteStation], index: int) -> None:
    setattr(host, _QUEUE_ATTR, {"folder": folder, "stations": stations, "index": index})


def _queue(host: Any) -> dict[str, Any] | None:
    queue = getattr(host, _QUEUE_ATTR, None)
    return queue if isinstance(queue, dict) and queue.get("stations") else None


def queue_summary(host: Any) -> str:
    """What the folder queue is currently doing, or "" when there is none."""
    queue = _queue(host)
    if queue is None:
        return ""
    stations = queue["stations"]
    index = int(queue["index"])
    name = str(queue["folder"]).rstrip("/").rsplit("/", 1)[-1] or "Favorites"
    return f"{index + 1} of {len(stations)} in {name}"


def play_folder(
    host: Any, folder: str, *, store: Any, controller: Any, shuffle: bool = False
) -> bool:
    """Start a folder playing and remember the rest for Next.

    The store and the player are passed in rather than dug out of *host*: the
    two callers are an app frame and a dialog, they spell those attributes
    differently, and a getattr chain across both is how a caller ends up
    silently doing nothing. *host* is only what the queue hangs on and what
    speaks.

    Returns False, having said why, when the folder holds nothing playable --
    which is a real case: a folder can contain only sub-folders, or only places
    (browse-tree bookmarks) with no stream behind them.
    """
    announce = getattr(host, "_announce", None) or (lambda _m: None)
    if store is None or controller is None:
        return False

    stations = [
        row
        for row in folder_actions.stations_in_folder(store, folder)
        if str(getattr(row.station, "stream_url", "") or "").strip()
    ]
    if not stations:
        announce("There is nothing to play in that folder.")
        return False
    if shuffle:
        stations = folder_actions.shuffled(stations)

    _set_queue(host, folder, stations, 0)
    controller.play_station(stations[0].station)
    name = folder.rstrip("/").rsplit("/", 1)[-1] or "Favorites"
    count = len(stations)
    how = "Shuffling" if shuffle else "Playing"
    announce(
        f"{how} {name}: {count} station{'' if count == 1 else 's'}. "
        f"Now playing {stations[0].display_label}. "
        "Next and Previous move through the folder."
    )
    return True


def _step(host: Any, delta: int, controller: Any) -> bool:
    queue = _queue(host)
    announce = getattr(host, "_announce", None) or (lambda _m: None)
    if queue is None:
        announce("No folder is playing. Play a folder first.")
        return False
    stations = queue["stations"]
    index = int(queue["index"]) + delta
    if index < 0 or index >= len(stations):
        # Deliberately not wrapping. A folder is a set somebody chose, and
        # silently looping back to the top is how a listener ends up hearing
        # the same station twice without knowing why they are there again.
        edge = "start" if index < 0 else "end"
        announce(f"That is the {edge} of the folder.")
        return False
    queue["index"] = index
    if controller is None:
        return False
    controller.play_station(stations[index].station)
    announce(f"{stations[index].display_label}, {index + 1} of {len(stations)}.")
    return True


def next_in_folder(host: Any, controller: Any) -> bool:
    """The next station in the folder that is playing."""
    return _step(host, 1, controller)


def previous_in_folder(host: Any, controller: Any) -> bool:
    """The previous station in the folder that is playing."""
    return _step(host, -1, controller)


def export_folder(host: Any, folder: str, *, store: Any) -> bool:
    """Write one folder's stations out as a playlist file the listener chooses.

    Reuses :mod:`quill.core.radio.playlist_export` unchanged -- the difference
    between exporting everything and exporting a folder is which list is handed
    in, and it would be a poor reason for a second exporter.
    """
    import wx

    from quill.core.radio.playlist_export import export_m3u

    announce = getattr(host, "_announce", None) or (lambda _m: None)
    if store is None:
        return False
    playable = [
        row
        for row in folder_actions.stations_in_folder(store, folder)
        if str(getattr(row.station, "stream_url", "") or "").strip()
    ]
    if not playable:
        announce("There is nothing to export in that folder.")
        return False

    name = folder.rstrip("/").rsplit("/", 1)[-1] or "favorites"
    safe = "".join(char for char in name if char.isalnum() or char in " -_").strip() or "favorites"
    frame = getattr(host, "frame", None) or host
    with wx.FileDialog(
        frame,
        f"Export {name} to a playlist",
        defaultFile=f"{safe}.m3u",
        wildcard="M3U playlist (*.m3u)|*.m3u|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as file_dialog:
        if file_dialog.ShowModal() != wx.ID_OK:
            return False
        destination = file_dialog.GetPath()

    from pathlib import Path

    try:
        Path(destination).write_text(export_m3u(playable), encoding="utf-8")
    except OSError as error:
        announce(f"Could not write the playlist: {error}.")
        return False
    count = len(playable)
    announce(f"Exported {count} station{'' if count == 1 else 's'} to {Path(destination).name}.")
    return True
