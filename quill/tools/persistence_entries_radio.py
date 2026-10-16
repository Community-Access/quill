"""Quill Radio's reviewed persistence sites for things the listener wrote.

Split from :mod:`quill.tools.persistence_audit` under GATE-11 -- extract, never
rebaseline -- when a per-favourite system-wide key (xradio2 4.9) needed one more
entry. The seam is real: these are the small maps a listener fills in by hand
on a station (a note, their own tags, a key), every one keyed by a station's
stable key and every one ``content`` for the same reason, which is the review.
"""

from __future__ import annotations

RADIO_LISTENER_ENTRIES: dict[str, str] = {
    # A line the listener wrote themselves about a station or a podcast. Their
    # own words, so it is content rather than configuration: additive and
    # self-describing (a flat key -> text map), with no defaults that could
    # change meaning under it, and nothing to migrate. Losing it would lose
    # something somebody made, which is why it is written atomically -- but
    # not something the versioned-delta contract helps with.
    "core/radio/item_notes.py::set_note": "content",
    # Your own tags on stations that are not favorites; additive, self-describing.
    "core/radio/station_tags.py::save_tag_store": "content",
    # The system-wide key the listener gave a favourite (xradio2 4.9): their
    # own choice, a flat favourite-key -> chord map, additive and
    # self-describing with nothing to migrate; an unreadable file is no keys.
    "core/radio/favorite_hotkeys.py::save_hotkeys": "content",
}

__all__ = ["RADIO_LISTENER_ENTRIES"]
