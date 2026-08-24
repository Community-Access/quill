"""Move my setup to another machine: one file, exported and imported.

OPML moves subscriptions and nothing else. It does not move your favorite
stations, the folders you filed them into, the places you saved, your Go To
list, your quiet hours, your Quick Action order, or the speeds you chose --
which is to say it moves the part that was easiest to standardise and leaves
the part you actually built (list.md 11.10).

So: one file. A ``.quillsetup`` is an ordinary ZIP holding the settings files
named in :data:`ITEMS` plus a ``manifest.json`` saying what is inside, which
app wrote it and when. Ordinary on purpose -- somebody who wants to know what
they are carrying between machines can open it, and somebody restoring onto a
machine that no longer runs this software can still get their subscription
list out of it.

Three rules the shape follows:

* **A declared inventory, not "everything in the folder."** Each entry names
  a file, says what it is in the words the listener would use, and says which
  app it belongs to. A new store is carried only when somebody adds it here,
  which is the point: a sweep of the data folder would eventually carry a
  cache, a lock file, or a credential nobody meant to move.
* **No secrets, ever.** Feed passwords, saved server credentials and unlock
  codes live in the Windows credential store and in DPAPI-protected files;
  none of them is in :data:`ITEMS` and none of them can be. The import report
  says so out loud rather than leaving somebody to discover it.
* **Import is counted, and says what it did not do.** Restored, skipped (not
  in the file), and failed, each with a number -- the same rule every other
  bulk verb in this family follows (11.4).

Pure: no wx, no clock of its own for the *decision* (the caller stamps the
manifest), and every failure is reported rather than raised.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from quill.core.counted import Counted

__all__ = [
    "EXTENSION",
    "ITEMS",
    "MANIFEST_NAME",
    "SetupItem",
    "describe_contents",
    "export_setup",
    "import_setup",
    "read_manifest",
]

#: What one of these files is called. Not ``.zip``: the extension is what
#: makes "which of these is my setup?" answerable in a folder listing.
EXTENSION = ".quillsetup"
MANIFEST_NAME = "manifest.json"
FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class SetupItem:
    """One store the setup file carries."""

    #: The file's name in the data folder, and inside the archive.
    filename: str
    #: What it is, in the words a listener would use.
    label: str
    #: "radio", "cast", or "both" -- which app would miss it.
    app: str


#: Everything a setup file carries. Ordered so the export report reads in the
#: order somebody would ask about it: what you follow, then what you saved,
#: then how it behaves.
ITEMS: tuple[SetupItem, ...] = (
    SetupItem("podcasts_library.json", "your podcast subscriptions, folders and playlists", "cast"),
    SetupItem("radio_favorites.json", "your favorite stations, folders and saved places", "radio"),
    SetupItem("radio_history.json", "your radio settings and recently played stations", "radio"),
    SetupItem("podcast_history.json", "your podcast settings", "cast"),
    SetupItem("radio-go-to.json", "your Go To list, in the order you put it", "radio"),
    SetupItem("podcast_quick_actions.json", "your Quick Action order", "cast"),
    SetupItem("radio-youtube-saved.json", "your saved YouTube rows", "radio"),
    SetupItem("radio-youtube-channels.json", "the YouTube channels you follow", "radio"),
    SetupItem("radio-my-servers.json", "your own streaming servers", "radio"),
    SetupItem("radio_recording_schedule.json", "your scheduled recordings", "radio"),
    SetupItem("radio_recording_settings.json", "how recordings are made and filed", "radio"),
    SetupItem("radio-listens.json", "where you had got to in each podcast, from Radio", "both"),
    SetupItem("radio-actions.json", "your row-action order in Radio", "radio"),
    SetupItem("podcast-ask-prefs.json", "the confirmations you asked not to see again", "cast"),
    SetupItem("quiet-hours.json", "your quiet hours", "both"),
    SetupItem("bookmarks.json", "your bookmarks", "both"),
    SetupItem(
        "media_bookmarks.json",
        "the moments you bookmarked in podcasts, stations and recordings",
        "both",
    ),
    SetupItem("keymap.json", "the keys you rebound", "both"),
)

_BY_NAME = {item.filename: item for item in ITEMS}

#: Said in the export and import reports. The one thing somebody must not
#: assume moved with the rest.
SECRETS_NOTE = (
    "Passwords are not included: private-feed sign-ins, server credentials and "
    "unlock codes stay on the machine that holds them, and have to be entered "
    "again on the new one."
)


def describe_contents(present: list[str]) -> str:
    """What a setup file holds, as one readable sentence per app."""
    if not present:
        return "This setup file is empty."
    labels = [_BY_NAME[name].label for name in present if name in _BY_NAME]
    unknown = len(present) - len(labels)
    parts = "; ".join(labels)
    tail = f"; and {unknown} item(s) this version does not recognise" if unknown else ""
    return f"It carries {parts}{tail}."


def export_setup(data_dir: Path, target: Path, *, app: str, stamped: str) -> Counted:
    """Write *target* holding every item of :data:`ITEMS` that exists.

    Returns the tally: how many stores were found and written, and how many
    were skipped because this machine has never made one. *stamped* is an
    ISO-8601 timestamp the caller supplies, so this stays clock-free.
    """
    written: list[str] = []
    skipped = 0
    failed = 0
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in ITEMS:
                source = data_dir / item.filename
                if not source.is_file():
                    skipped += 1
                    continue
                try:
                    archive.write(source, arcname=item.filename)
                    written.append(item.filename)
                except OSError:
                    failed += 1
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(
                    {
                        "format": FORMAT_VERSION,
                        "app": app,
                        "created": stamped,
                        "files": written,
                        "note": SECRETS_NOTE,
                    },
                    indent=2,
                ),
            )
    except OSError:
        return Counted(done=0, skipped=0, failed=1, nothing_because="the file could not be written")
    return Counted(
        done=len(written),
        skipped=skipped,
        failed=failed,
        skipped_because="this machine has never made one",
        nothing_because="there is nothing here to carry yet",
    )


def read_manifest(source: Path) -> dict:
    """The manifest of a setup file, or ``{}`` when it is not one."""
    try:
        with zipfile.ZipFile(source) as archive:
            raw = archive.read(MANIFEST_NAME)
    except (OSError, KeyError, zipfile.BadZipFile):
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def import_setup(source: Path, data_dir: Path, *, only: set[str] | None = None) -> Counted:
    """Restore the stores in *source* into *data_dir*, overwriting.

    Overwriting is the point -- "move my setup to another machine" means the
    other machine ends up with this setup, and a merge of two libraries is a
    different feature with different questions. The caller is expected to have
    said so before calling; nothing here asks.

    *only* limits the restore to those filenames (the caller's checklist).
    Anything in the archive that is not in :data:`ITEMS` is skipped rather
    than written: a setup file is not a way to drop an arbitrary file into
    somebody's data folder.
    """
    restored = 0
    skipped = 0
    failed = 0
    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            for item in ITEMS:
                if item.filename not in names:
                    skipped += 1
                    continue
                if only is not None and item.filename not in only:
                    skipped += 1
                    continue
                try:
                    payload = archive.read(item.filename)
                    json.loads(payload.decode("utf-8"))  # refuse to write junk
                except (OSError, KeyError, UnicodeDecodeError, ValueError):
                    failed += 1
                    continue
                try:
                    from quill.core.storage import write_json_atomic

                    write_json_atomic(data_dir / item.filename, json.loads(payload.decode("utf-8")))
                    restored += 1
                except OSError:
                    failed += 1
    except (OSError, zipfile.BadZipFile):
        return Counted(
            done=0, skipped=0, failed=1, nothing_because="that file is not a Quill setup file"
        )
    return Counted(
        done=restored,
        skipped=skipped,
        failed=failed,
        skipped_because="not in this setup file",
        nothing_because="that setup file holds nothing this version can restore",
    )
