"""The WordPress Workbench's own options, kept beside the site list (decision 7, W6).

The Workbench is where Tools > WordPress leads in both editors. For one
release the old windows stay parked behind one choice, **Use the classic
WordPress windows**, for anyone partway through work in them; with it on,
each Tools > WordPress door opens its own window again, as before the
Workbench. The choice lives here rather than in Settings because it belongs
to the Workbench and goes away with the classic windows.

:func:`load_options` and :func:`save_options` read and write
``workbench_options.json`` beside ``wordpress_sites.json``, atomically. A
missing or unreadable file is the defaults. Wx-free.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.sites import sites_path

__all__ = ["CLASSIC_LABEL", "WorkbenchOptions", "load_options", "options_path", "save_options"]

CLASSIC_LABEL = "Use the classic WordPress windows"
"""The choice's words, the same in the Options sheet, the docs and the help."""


@dataclass
class WorkbenchOptions:
    """What the person chose. Every field has the default a new install gets."""

    classic_windows: bool = False
    watch_minutes: int = 15
    #: Watches (15.7) on, by kind; none until the person turns them on.
    watches: tuple[str, ...] = ()
    #: Site Sets (15.12): a name, and the site names in it.
    site_sets: dict[str, list[str]] = field(default_factory=dict)


def options_path(base: Path | None = None) -> Path:
    return sites_path(base).parent / "workbench_options.json"


def load_options(base: Path | None = None) -> WorkbenchOptions:
    raw = read_json(options_path(base), default={})
    if not isinstance(raw, dict):
        return WorkbenchOptions()
    minutes = raw.get("watch_minutes", 15)
    watches = raw.get("watches")
    sets = raw.get("site_sets")
    return WorkbenchOptions(
        classic_windows=bool(raw.get("classic_windows", False)),
        watch_minutes=max(15, int(minutes)) if isinstance(minutes, int) else 15,
        watches=tuple(str(w) for w in watches)
        if isinstance(watches, list)
        else WorkbenchOptions().watches,
        site_sets={str(k): [str(s) for s in v] for k, v in sets.items() if isinstance(v, list)}
        if isinstance(sets, dict)
        else {},
    )


def save_options(options: WorkbenchOptions, base: Path | None = None) -> None:
    body = asdict(options)
    body["watches"] = list(options.watches)
    write_json_atomic(options_path(base), body)
