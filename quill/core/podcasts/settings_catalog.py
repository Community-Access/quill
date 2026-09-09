"""Every QUILL Cast setting, in one place, and the two questions that needs.

Cast's settings were spread across a dataclass, two help tables and three
dialogs, and the two questions somebody actually asks had no answer at all:

* **"Where is the setting for...?"** -- :func:`search`, which is what *Find a
  Setting* runs. Over a hundred settings, a search that matches the label, the
  help, the choice names **and** a list of synonyms somebody would really type
  ("wifi" for the metered guard) is worth more than any reorganisation of the
  windows. It is the one feature that makes a hundred settings survivable.
* **"What have I actually changed?"** -- :func:`changed`, which walks the same
  catalogue and reports every level's opinions. It answers the question support
  always asks and nobody can answer, and it doubles as the honest reset
  surface: you cannot sensibly offer *put it all back* without first being able
  to say what *it all* is.

The catalogue is assembled from four files rather than written here, because
the entries are pure data that belongs beside the family it describes -- and
because one file of a hundred settings is a file nobody reads.

Nothing in this module knows about wx, and nothing in it stores a value; the
storage and the inheritance chain are
:mod:`quill.core.podcasts.settings_resolver`'s.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from quill.core.podcasts import (
    row_speech,
    settings_defs_library,
    settings_defs_playback,
    settings_defs_show,
)
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.settings_types import (
    CATEGORIES,
    LEVEL_FOLDER,
    LEVEL_GLOBAL,
    LEVEL_SHOW,
    SettingDef,
)
from quill.core.podcasts.subscriptions import PodcastLibrary

#: Every setting Cast has, in a stable order: the playback family, the library
#: family, the row-speech family, then everything the per-podcast proposal
#: added. Order matters only for the reports -- lookups are by id.
CATALOG: tuple[SettingDef, ...] = (
    *settings_defs_playback.SETTINGS,
    *settings_defs_library.SETTINGS,
    *row_speech.SETTINGS,
    *settings_defs_show.SETTINGS,
)

_BY_ID: dict[str, SettingDef] = {item.id: item for item in CATALOG}
_BY_FIELD: dict[str, SettingDef] = {
    item.settings_field: item for item in CATALOG if item.settings_field
}


def definition(setting_id: str) -> SettingDef | None:
    """One setting by id, or ``None`` when the catalogue does not know it."""
    return _BY_ID.get(setting_id)


def by_field(field_name: str) -> SettingDef | None:
    """One setting by its ``PodcastSettings`` attribute name.

    The bridge ``apply_show_override`` crosses: its callers name a dataclass
    field, and the resolver needs the definition that owns it.
    """
    return _BY_FIELD.get(field_name)


def for_level(level: str) -> tuple[SettingDef, ...]:
    """Every setting that may be set at *level*, in catalogue order."""
    return tuple(item for item in CATALOG if item.allows(level))


def for_category(category: str, *, level: str = LEVEL_GLOBAL) -> tuple[SettingDef, ...]:
    """Every setting of one category that may be set at *level*."""
    return tuple(item for item in for_level(level) if item.category == category)


@lru_cache(maxsize=1)
def categories_with_settings() -> tuple[str, ...]:
    """The categories that actually contain something, in display order."""
    present = {item.category for item in CATALOG}
    return tuple(category for category in CATEGORIES if category in present)


# -- search ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One search result, with enough context to land on the control."""

    definition: SettingDef
    #: Where it can be set, narrowed to what the search was scoped to.
    levels: tuple[str, ...]

    @property
    def id(self) -> str:
        return self.definition.id

    def label(self) -> str:
        """The row a person hears: the setting, then where it lives."""
        where = ", ".join(_LEVEL_WORDS[level] for level in self.levels)
        return f"{self.definition.label_text()} ({where})"


_LEVEL_WORDS = {
    LEVEL_GLOBAL: "shared default",
    LEVEL_FOLDER: "per folder",
    LEVEL_SHOW: "per podcast",
}


def search(needle: str, *, level: str = "") -> list[SearchHit]:
    """Every setting matching *needle*, best-looking matches first.

    Ranked rather than merely filtered, because a search that puts *Volume
    Boost* twelfth when you typed "volume" is a search you stop using: a hit on
    the label outranks a hit on a synonym, which outranks a hit buried in the
    help text. Within a rank, catalogue order -- which is category order, and
    therefore stable.
    """
    wanted = needle.strip().casefold()
    if not wanted:
        return []
    scored: list[tuple[int, int, SettingDef]] = []
    for index, item in enumerate(CATALOG):
        if level and not item.allows(level):
            continue
        if not item.matches(wanted):
            continue
        label = item.label_text().casefold()
        if label.startswith(wanted):
            rank = 0
        elif wanted in label:
            rank = 1
        elif any(wanted in alias.casefold() for alias in item.aliases):
            rank = 2
        elif any(wanted in choice.label.casefold() for choice in item.choices):
            rank = 3
        else:
            rank = 4
        scored.append((rank, index, item))
    scored.sort()
    return [
        SearchHit(
            definition=item,
            levels=tuple(lvl for lvl in item.levels if not level or lvl == level),
        )
        for _rank, _index, item in scored
    ]


def search_summary(hits: list[SearchHit], needle: str) -> str:
    """What the search box says on Enter.

    Counted, like every other list verb in this family: a search that says only
    "found" leaves somebody who cannot see the list unable to tell one match
    from forty. A search with nothing says what it searched, so the answer is
    "there is no such setting" rather than silence.
    """
    text = needle.strip()
    if not text:
        return f"Type to search {len(CATALOG)} settings."
    if not hits:
        return (
            f"No setting matches {text!r}. All {len(CATALOG)} settings were "
            "searched, including their descriptions."
        )
    if len(hits) == 1:
        return f"1 setting matches {text!r}: {hits[0].label()}."
    return f"{len(hits)} settings match {text!r}. {hits[0].label()} is first."


# -- what has been changed ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChangedSetting:
    """One setting somebody has an opinion about, and where."""

    definition: SettingDef
    value: object
    level: str
    scope_id: str = ""
    scope_name: str = ""

    def label(self) -> str:
        """The row: what it is set to, and where that was set."""
        said = self.definition.say(self.value)
        if self.level == LEVEL_GLOBAL:
            return f"{said} (shared default)"
        if self.level == LEVEL_FOLDER:
            where = self.scope_name or "a folder"
            return f"{said} (folder: {where})"
        return f"{said} ({self.scope_name or 'this podcast'})"


def changed(library: PodcastLibrary, *, show: PodcastShow | None = None) -> list[ChangedSetting]:
    """Every setting anybody has an opinion about; the shared defaults omitted.

    Scoped to one podcast when *show* is given -- the chain that actually
    decides that podcast's behaviour, folders included -- and to the whole
    library otherwise.

    The point is subtraction. A settings window shows a hundred controls and
    tells you nothing about which of them you touched; this shows only the
    answer to "what is not the default here", which is almost always a short
    list and is exactly what somebody needs when a podcast is behaving oddly.
    """
    from quill.core.podcasts.settings_resolver import (
        FOLDER_PREFIX,
        SHOW_PREFIX,
        folder_chain,
        migrate_show,
    )

    results: list[ChangedSetting] = []

    def _collect(bucket: dict[str, object], level: str, scope_id: str, scope_name: str) -> None:
        for item in CATALOG:
            if item.id not in bucket or not item.allows(level):
                continue
            results.append(
                ChangedSetting(
                    definition=item,
                    value=item.coerce(bucket[item.id]),
                    level=level,
                    scope_id=scope_id,
                    scope_name=scope_name,
                )
            )

    if show is not None:
        migrate_show(library, show)
        _collect(
            library.scope_overrides.get(f"{SHOW_PREFIX}{show.id}", {}),
            LEVEL_SHOW,
            show.id,
            show.title,
        )
        for folder_id in folder_chain(library, show.folder_id):
            folder = library.find_folder(folder_id)
            _collect(
                library.scope_overrides.get(f"{FOLDER_PREFIX}{folder_id}", {}),
                LEVEL_FOLDER,
                folder_id,
                folder.name if folder is not None else "",
            )
        return results

    _collect(dict(library.extra_settings), LEVEL_GLOBAL, "", "")
    for folder in library.folders:
        _collect(
            library.scope_overrides.get(f"{FOLDER_PREFIX}{folder.id}", {}),
            LEVEL_FOLDER,
            folder.id,
            folder.name,
        )
    for subscribed in library.shows:
        _collect(
            library.scope_overrides.get(f"{SHOW_PREFIX}{subscribed.id}", {}),
            LEVEL_SHOW,
            subscribed.id,
            subscribed.title,
        )
    return results


def changed_summary(entries: list[ChangedSetting], *, subject: str = "") -> str:
    """What the report says when it opens.

    Names the subject, because "nothing" about one podcast and "nothing" about
    a whole library are different reassurances.
    """
    where = f" for {subject}" if subject else ""
    if not entries:
        return (
            f"Nothing{where} differs from the shared defaults. "
            f"All {len(CATALOG)} settings are following them."
        )
    count = len(entries)
    return (
        f"{count} setting{'' if count == 1 else 's'}{where} "
        f"differ{'s' if count == 1 else ''} from the shared defaults, "
        f"out of {len(CATALOG)}."
    )


__all__ = [
    "CATALOG",
    "ChangedSetting",
    "SearchHit",
    "by_field",
    "categories_with_settings",
    "changed",
    "changed_summary",
    "definition",
    "for_category",
    "for_level",
    "search",
    "search_summary",
]
