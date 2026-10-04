"""What each app writes to disk, and in which version of each shape (plan 5.1).

"Back to Stable only if safe" needs an answer to one question: *can the version
you are going back to read what this computer has already saved?* This table
is how a build answers for itself. Each :class:`DataFormat` names one on-disk
shape, the files it lives in, the version this build **writes**
(:attr:`~DataFormat.current`), and the highest version it can **read** without
losing anything (:attr:`~DataFormat.reads_up_to`).

**The version is the contract, not the JSON layout.** It goes up only when an
older build would misread or lose data. Additive fields an older build ignores
safely are not a new version -- except for QUILL Lite, whose ``save`` drops keys
it does not know, so an older Lite *reads* a newer file but forgets the new
settings when it saves: that is recorded in :attr:`~DataFormat.lossy_reads`
rather than hidden.

**Losses, declared by the writer.** When a new version only *adds* to the shape
-- an older build can still read it and merely forgets what it does not know --
the build that writes it says so in :attr:`~DataFormat.readable_with_losses_from`:
"a build that reads version N can read this, losing only the new fields". The
feed carries it (``lossy_formats``), and going back to such a build is offered
as "safe, but these settings go back to their usual values" rather than refused.

Every app notes these versions in the per-machine ledger
(:mod:`quill.core.data_format_ledger`) at start-up, and "is it safe to go back
to Stable?" is decided from that ledger
(:func:`quill.core.updater.going_back.downgrade_verdict`). Derived
data that is rebuilt rather than migrated -- Radio's station catalog, caches --
is deliberately not listed.

wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["FORMATS", "DataFormat", "formats_for"]

Location = Literal["quill_data", "lite_data"]


@dataclass(frozen=True)
class DataFormat:
    #: ``"radio.favorites"`` -- owner, then what it is.
    id: str
    #: The app that writes it, or ``"shared"`` when several do.
    owner: str
    files: tuple[str, ...]
    #: ``quill_data`` is the shared ``%APPDATA%\\Quill`` folder (QUILL, Radio,
    #: Cast, Inkwell); ``lite_data`` is QUILL Lite's own folder.
    location: Location
    #: The version this build writes.
    current: int
    #: The highest version this build reads without loss.
    reads_up_to: int
    #: Versions it reads but would drop fields from on its next save.
    lossy_reads: tuple[int, ...] = ()
    #: Apps besides the owner that write it too (for ``shared`` formats).
    writers: tuple[str, ...] = ()
    #: When this version only adds to the previous ones: the oldest version
    #: whose readers can still read what this build writes, losing only the
    #: new fields (0: no such promise, an older reader is refused).
    readable_with_losses_from: int = 0


FORMATS: tuple[DataFormat, ...] = (
    # QUILL's settings already carry the full versioned-delta contract
    # (settings_migration.SETTINGS_SCHEMA_VERSION); this mirrors that number.
    DataFormat("quill.settings", "quill", ("settings.json",), "quill_data", 2, 2),
    DataFormat("quill.keymap", "quill", ("keymap.json",), "quill_data", 1, 1),
    DataFormat("lite.settings", "quilllite", ("settings.json",), "lite_data", 1, 1),
    DataFormat("lite.keymap", "quilllite", ("keymap.json",), "lite_data", 1, 1),
    DataFormat("radio.favorites", "radio", ("radio_favorites.json",), "quill_data", 1, 1),
    DataFormat("radio.history", "radio", ("radio_history.json",), "quill_data", 1, 1),
    DataFormat("cast.library", "cast", ("podcasts_library.json",), "quill_data", 1, 1),
    DataFormat("cast.history", "cast", ("podcast_history.json",), "quill_data", 1, 1),
    DataFormat(
        "shared.media_bookmarks",
        "shared",
        ("media_bookmarks.json",),
        "quill_data",
        1,
        1,
        writers=("radio", "cast"),
    ),
    DataFormat(
        "shared.listens",
        "shared",
        ("radio-listens.json",),
        "quill_data",
        1,
        1,
        writers=("radio", "cast"),
    ),
)


def formats_for(app_key: str) -> tuple[DataFormat, ...]:
    """The formats *app_key* writes: its own, and the shared ones it writes too."""
    return tuple(f for f in FORMATS if f.owner == app_key or app_key in f.writers)
