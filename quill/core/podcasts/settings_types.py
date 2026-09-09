"""What a QUILL Cast setting *is*: the shape every one of them is described by.

Cast had settings long before it had a description of a setting. Values lived
on :class:`~quill.core.podcasts.models_settings.PodcastSettings`, their words
lived in :mod:`quill.core.podcasts.settings_help`, their controls lived in two
dialogs, and nothing tied the three together -- so "which settings are there?"
had no answer, "where did this value come from?" had no answer, and a listener
looking for the metered-connection guard had to know which of two windows it
was in.

This module is the missing noun. One :class:`SettingDef` per setting, carrying
what it is called, what it does, what kind of value it holds, **which levels
may set it**, and where it is stored. Everything downstream reads from that:

* :mod:`quill.core.podcasts.settings_resolver` resolves a value through the
  levels and can say which level answered;
* :mod:`quill.core.podcasts.settings_catalog` assembles every definition and
  makes them searchable, which is what *Find a Setting* is;
* the "settings you have changed" report is a walk of the same catalogue.

**Levels.** A setting declares the levels it makes sense at. Some are global
only (the download folder is a property of this computer, not of a podcast);
some are per-podcast only (a filter, a pronunciation); most are both, and
resolve **shared default -> folder -> podcast**, nearest wins.

**Storage.** ``settings_field`` names a ``PodcastSettings`` attribute when the
setting predates this catalogue; everything newer stores by id, which is why adding a
setting no longer means growing a 500-line dataclass. Both kinds resolve
identically -- the difference is invisible above the resolver.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

# -- levels ------------------------------------------------------------------

#: The shared default: one value for every podcast that has no opinion.
LEVEL_GLOBAL = "global"
#: A folder's value, inherited by every podcast filed in it or beneath it.
LEVEL_FOLDER = "folder"
#: One podcast's own value.
LEVEL_SHOW = "show"

LEVELS: tuple[str, ...] = (LEVEL_GLOBAL, LEVEL_FOLDER, LEVEL_SHOW)

#: How each level reads when a value's provenance is spoken.
LEVEL_LABELS: dict[str, str] = {
    LEVEL_GLOBAL: "the shared default",
    LEVEL_FOLDER: "the folder",
    LEVEL_SHOW: "this podcast",
}

# -- kinds -------------------------------------------------------------------
#
# Deliberately few. A kind exists to tell an editor which control to build and
# to tell the resolver how to coerce a stored value; it is not a type system.

KIND_BOOL = "bool"
KIND_INT = "int"
KIND_FLOAT = "float"
KIND_TEXT = "text"
#: One of ``choices``.
KIND_CHOICE = "choice"
#: A value with structure the catalogue does not model -- a rule list, a set of
#: scopes. It is listed and searchable, and its editor is its own window.
KIND_OPAQUE = "opaque"

# -- categories --------------------------------------------------------------
#
# The five groups every Cast setting actually falls into. They are the tabs of
# the survey view, the grouping of the search results, and the order the
# "settings you have changed" report walks.

CATEGORY_ARRIVAL = "arrival"
CATEGORY_PLAYBACK = "playback"
CATEGORY_STORAGE = "storage"
CATEGORY_ANNOUNCEMENTS = "announcements"
CATEGORY_CURATION = "curation"

CATEGORIES: tuple[str, ...] = (
    CATEGORY_ARRIVAL,
    CATEGORY_PLAYBACK,
    CATEGORY_STORAGE,
    CATEGORY_ANNOUNCEMENTS,
    CATEGORY_CURATION,
)

CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_ARRIVAL: "Arrival",
    CATEGORY_PLAYBACK: "Playback",
    CATEGORY_STORAGE: "Storage",
    CATEGORY_ANNOUNCEMENTS: "Announcements",
    CATEGORY_CURATION: "Curation",
}


@dataclass(frozen=True, slots=True)
class Choice:
    """One option of a :data:`KIND_CHOICE` setting: the value, and its words."""

    value: object
    label: str


@dataclass(frozen=True, slots=True)
class SettingDef:
    """One setting, completely described.

    The fields are ordered by how often somebody reading this needs them:
    what it is called, what it does, what it holds, and only then where it
    lives.
    """

    id: str
    #: The control's own label, with its access key where it has one.
    label: str
    #: What it does, then the misreading it prevents -- the house rule
    #: (``settings_help``), enforced by ``test_settings_help.py`` for the
    #: tables and by ``test_settings_catalog.py`` for these.
    help: str
    kind: str = KIND_BOOL
    category: str = CATEGORY_PLAYBACK
    #: The levels that may set it, in resolution order. A setting absent from
    #: a level is not merely hidden there -- the resolver will not read it.
    levels: tuple[str, ...] = LEVELS
    #: The value when nobody anywhere has an opinion.
    default: object = False
    choices: tuple[Choice, ...] = ()
    #: The ``PodcastSettings`` attribute this reads and writes, for settings
    #: that predate the catalogue. Empty means "stored by id".
    #:
    #: Named ``settings_field`` rather than ``field`` on purpose: a dataclass
    #: attribute called ``field`` shadows ``dataclasses.field`` inside the class
    #: body, and the failure is a ``TypeError`` at import time on a completely
    #: unrelated line.
    settings_field: str = ""
    #: Never synced, never shared: a property of this computer rather than of
    #: this listener. The download folder, not the playback speed.
    device_local: bool = False
    #: Extra words a search should match -- the synonyms somebody would
    #: actually type. "wifi" for the metered guard, "podcast name" for the row
    #: order. Cheap, and the difference between a search that works and one
    #: that only works if you already knew the label.
    aliases: tuple[str, ...] = ()
    #: Says the value back in words rather than as a number: "Keeping the 5
    #: newest downloaded episodes", never "5". Defaults to a plain rendering.
    describe: Callable[[object], str] | None = None
    #: Numeric bounds, for the editors that need them.
    minimum: float = 0.0
    maximum: float = 0.0
    #: Free-form notes for the generated settings reference.
    notes: str = ""
    #: Set when this definition is a family rather than a single control (a
    #: rule list, a scope set): the window that edits it.
    editor: str = ""
    tags: tuple[str, ...] = ()

    # -- questions the catalogue is asked ------------------------------------

    def allows(self, level: str) -> bool:
        """Whether *level* may set this setting."""
        return level in self.levels

    @property
    def per_podcast(self) -> bool:
        return LEVEL_SHOW in self.levels

    @property
    def global_only(self) -> bool:
        return self.levels == (LEVEL_GLOBAL,)

    def coerce(self, value: object) -> object:
        """A stored value, made safe for this setting.

        Every stored value is somebody else's input -- a hand-edited file, a
        record written by a newer build, a synced value from a version that
        spelled a choice differently. The rule throughout is the same one the
        rest of Cast follows: **an unreadable value reads as the default**,
        never as something that does more work than was asked for.
        """
        if self.kind == KIND_BOOL:
            return bool(value)
        if self.kind == KIND_INT:
            try:
                whole = int(float(value))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return self.default
            return self._clamp(whole)
        if self.kind == KIND_FLOAT:
            # A separate name from the int branch above: one `number` bound to
            # both an int and a float is a genuine conflict, not a nuisance.
            try:
                fractional = float(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return self.default
            return self._clamp(fractional)
        if self.kind == KIND_CHOICE:
            allowed = {choice.value for choice in self.choices}
            return value if value in allowed else self.default
        if self.kind == KIND_TEXT:
            return str(value or "")
        return value

    def _clamp(self, number: float) -> object:
        if self.maximum > self.minimum:
            number = max(self.minimum, min(self.maximum, number))
        elif self.minimum:
            number = max(self.minimum, number)
        return int(number) if self.kind == KIND_INT else float(number)

    def label_text(self) -> str:
        """The label without its access key, for speech and for search."""
        return self.label.replace("&", "")

    def choice_label(self, value: object) -> str:
        """How one value of a choice setting reads."""
        for choice in self.choices:
            if choice.value == value:
                return choice.label
        return str(value)

    def say(self, value: object) -> str:
        """This value, in words.

        The house rule for every editor Cast has: *the change is said back in
        words, not as the number that was just typed*. "Keeping the 5 newest
        downloaded episodes" is an answer; "5" is a reading of the box.
        """
        if self.describe is not None:
            return self.describe(value)
        if self.kind == KIND_BOOL:
            return f"{self.label_text()}: {'on' if value else 'off'}"
        if self.kind == KIND_CHOICE:
            return f"{self.label_text()}: {self.choice_label(value)}"
        if self.kind == KIND_TEXT and not value:
            return f"{self.label_text()}: not set"
        return f"{self.label_text()}: {value}"

    def matches(self, needle: str) -> bool:
        """Whether a search for *needle* should find this setting.

        Matched against the label, the help, the id, the choice labels and the
        aliases -- because somebody looking for the metered guard types "wifi",
        and a search that only knows its own vocabulary is a search that only
        works for the person who wrote it.
        """
        wanted = needle.strip().casefold()
        if not wanted:
            return False
        haystack = [
            self.label_text(),
            self.help,
            self.id.replace("_", " "),
            *(choice.label for choice in self.choices),
            *self.aliases,
        ]
        return any(wanted in part.casefold() for part in haystack)


def define(
    setting_id: str,
    label: str,
    help_text: str,
    **kwargs: object,
) -> SettingDef:
    """A :class:`SettingDef`, spelled the way the family modules read best.

    Three positional arguments because those three are never omitted, and
    keywords for the rest -- a catalogue entry should read as a sentence about
    a setting, not as a fourteen-field constructor call.
    """
    return SettingDef(id=setting_id, label=label, help=help_text, **kwargs)  # type: ignore[arg-type]


def choices(*pairs: tuple[object, str]) -> tuple[Choice, ...]:
    """``choices((0, "Never"), (7, "After a week"))`` -- values and their words."""
    return tuple(Choice(value=value, label=label) for value, label in pairs)


def by_id(definitions: Sequence[SettingDef]) -> dict[str, SettingDef]:
    return {definition.id: definition for definition in definitions}


__all__ = [
    "CATEGORIES",
    "CATEGORY_ANNOUNCEMENTS",
    "CATEGORY_ARRIVAL",
    "CATEGORY_CURATION",
    "CATEGORY_LABELS",
    "CATEGORY_PLAYBACK",
    "CATEGORY_STORAGE",
    "KIND_BOOL",
    "KIND_CHOICE",
    "KIND_FLOAT",
    "KIND_INT",
    "KIND_OPAQUE",
    "KIND_TEXT",
    "LEVELS",
    "LEVEL_FOLDER",
    "LEVEL_GLOBAL",
    "LEVEL_LABELS",
    "LEVEL_SHOW",
    "Choice",
    "SettingDef",
    "by_id",
    "choices",
    "define",
]
