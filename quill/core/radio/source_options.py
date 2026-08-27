"""Options a *source* declares and the app renders, with no UI code per source.

WHY THIS EXISTS
---------------
Radio Paradise offers six qualities and Quill Radio picks one to put first.
SHOUTcast lists five hundred stations of which forty are on the air, and which
of those two lists a listener wants is a preference. Both are settings that
belong to **one source** and to nothing else, and there are two bad ways to
provide them: a checkbox in the global Preferences dialog for every source that
ever wants one, or a bespoke dialog per source. The first turns Preferences
into a junk drawer; the second is a new surface, a new tab order and a new
screen-reader pass every time somebody adds a directory.

StreamTuner-ng solved this with an ``options_spec`` on the plugin class -- the
plugin declares, the host renders (``radio2.md`` part VII). This is that idea in
Quill Radio's idiom: a source declares a :class:`ChoiceOption` or a
:class:`SecretOption`, the browse tree renders it on the source's own context
menu, and the value is stored in one dict on ``RadioHistory``. A new source that
wants an option writes a tuple; it writes no UI at all.

THE TWO KINDS, AND WHY ONLY TWO
--------------------------------
* **Choice** -- one of a short list. Rendered as a menu of named values, which
  is a control every screen reader already reads correctly and which needs no
  new dialog.
* **Secret** -- a key or token, entered masked and never shown again. Declared
  here so the *shape* exists before the first keyed source does; the rule that
  goes with it lives in :mod:`quill.core.radio.keyed_source` -- a credential is
  never written into a station row.

A free-text option is deliberately absent. Every one that has come up (a
bitrate, a filter, a region) is a choice from a known set, and a text box for a
value with three legal answers is a way to typo.

wx-free, strict-typed, pure. The dict this reads and writes is the listener's;
this module never touches storage.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChoiceOption:
    """One of a short list of named values."""

    key: str
    label: str
    default: str
    #: ``(what it reads as, the stored value)``, in the order they are offered.
    choices: tuple[tuple[str, str], ...]
    #: One line for the menu's help string and the spoken confirmation.
    note: str = ""

    @property
    def kind(self) -> str:
        return "choice"

    def label_for(self, value: str) -> str:
        """What *value* reads as, or the default's label if it is unknown."""
        for said, stored in self.choices:
            if stored == value:
                return said
        for said, stored in self.choices:
            if stored == self.default:
                return said
        return value

    def valid(self, value: object) -> bool:
        return any(stored == value for _said, stored in self.choices)


@dataclass(frozen=True, slots=True)
class SecretOption:
    """A key or token: entered masked, stored by the host, never displayed."""

    key: str
    label: str
    placeholder: str = ""
    note: str = ""

    @property
    def kind(self) -> str:
        return "secret"

    def valid(self, value: object) -> bool:
        return isinstance(value, str)


Option = ChoiceOption | SecretOption

#: Radio Paradise offers every channel at six qualities and the rows are
#: ordered so that one of them is what Enter lands on. Which one is a property
#: of the listener's connection, not of the station, so it is theirs to say.
RADIO_PARADISE_QUALITY = ChoiceOption(
    key="radioparadise_quality",
    label="Radio Paradise Quality",
    default="320",
    choices=(
        ("320k AAC (best lossy)", "320"),
        ("192k MP3", "192"),
        ("128k AAC", "128"),
        ("64k AAC+", "64"),
        ("32k AAC+ (slowest connections)", "32"),
        ("FLAC (lossless, heaviest)", "flac"),
    ),
    note="Which quality is offered first for each channel. Every other one is still listed.",
)

#: A SHOUTcast genre page is 500 stations of which typically fewer than one in
#: ten has anybody listening. Which of those two lists somebody wants is the
#: definition of a preference: "everything the directory lists" is right for
#: hunting something obscure, "only stations on the air" for everything else.
SHOUTCAST_SHOW = ChoiceOption(
    key="shoutcast_show",
    label="SHOUTcast Stations to Show",
    default="all",
    choices=(
        ("Every station the directory lists", "all"),
        ("Only stations with listeners right now", "live"),
    ),
    note="SHOUTcast lists many stations that are not currently broadcasting.",
)

#: Source id -> the options it declares, in the order they are offered.
OPTIONS_BY_SOURCE: dict[str, tuple[Option, ...]] = {
    "radioparadise": (RADIO_PARADISE_QUALITY,),
    "shoutcast": (SHOUTCAST_SHOW,),
}

#: Every declared option, by key, for reading a stored value back.
_BY_KEY: dict[str, Option] = {
    option.key: option for options in OPTIONS_BY_SOURCE.values() for option in options
}


def options_for(source_id: object) -> tuple[Option, ...]:
    """What this source declares, or ``()``. Safe on any string."""
    return OPTIONS_BY_SOURCE.get(str(source_id or "").strip(), ())


def option(key: object) -> Option | None:
    """The declared option with this key, or ``None``."""
    return _BY_KEY.get(str(key or "").strip())


def value(stored: object, key: object) -> str:
    """The listener's value for *key*, or its default (pure).

    *stored* is ``RadioHistory.source_options`` -- untyped on purpose, because
    it has been through JSON and a caller should not have to prove it is a dict
    before asking a question about one key.
    """
    declared = option(key)
    if declared is None:
        return ""
    if isinstance(stored, dict):
        held = stored.get(str(key))
        if declared.valid(held):
            return str(held)
    return declared.default if isinstance(declared, ChoiceOption) else ""


def with_value(stored: object, key: object, chosen: object) -> dict[str, str]:
    """*stored* plus one changed option (pure), dropping anything unknown.

    Unknown keys are dropped rather than kept, exactly as the source lists do:
    an option removed in a later release cannot linger in a profile and cannot
    come back to life if the key is ever reused for something else.
    """
    out: dict[str, str] = {}
    if isinstance(stored, dict):
        for held_key, held in stored.items():
            declared = option(held_key)
            if declared is not None and declared.valid(held):
                out[str(held_key)] = str(held)
    declared = option(key)
    if declared is not None and declared.valid(chosen):
        out[str(key)] = str(chosen)
    return out


def normalize(stored: object) -> dict[str, str]:
    """A stored options dict, cleaned to declared keys and legal values (pure)."""
    return with_value(stored, "", None)


def describe(key: object, stored: object) -> str:
    """One spoken sentence about where an option now stands."""
    declared = option(key)
    if declared is None:
        return ""
    if isinstance(declared, SecretOption):
        held = (stored or {}).get(str(key), "") if isinstance(stored, dict) else ""
        return f"{declared.label} is {'set' if held else 'not set'}."
    return f"{declared.label} is now {declared.label_for(value(stored, key))}."


# --- the values in force, for a source module that has no host to ask --------
#
# A source client (``radio_paradise``, ``shoutcast``) is wx-free, is called from
# a browse handler that takes only ``args`` and ``safe_mode``, and has no route
# to the listener's history. Threading the whole options dict through every
# browse signature to serve two sources would be a large change to a contract
# many sources share, so the values in force live here instead -- the same
# shape ``directory_registry`` and ``source_health`` already use, and for the
# same reason.
#
# The app sets this once when history loads and again whenever an option
# changes; tests set it directly. Nothing here reads or writes storage.

_CURRENT: dict[str, str] = {}


def current() -> dict[str, str]:
    """The option values in force in this process."""
    return dict(_CURRENT)


def set_current(stored: object) -> dict[str, str]:
    """Replace the values in force with *stored*, cleaned. Returns them."""
    _CURRENT.clear()
    _CURRENT.update(normalize(stored))
    return dict(_CURRENT)


def chosen(key: object) -> str:
    """The value in force for *key*, or its default."""
    return value(_CURRENT, key)
