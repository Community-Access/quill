"""Per-app feature areas the user can turn off (like QUILL's feature profiles,
but for the standalone companion apps -- Quill Radio, Quill Weather, Quill Cast).

Each app declares its major **areas** (e.g. Radio's "Weather" menu). A user can
switch any of them off, and the app honors that when it builds its menus -- a
disabled area simply is not created, so its menu (and every command under it)
disappears. Areas default to **on**; only an explicit "off" is stored, so a new
area added in a later version is enabled for everyone until they say otherwise.

The store is shared by the sibling apps (one data dir) but keyed by app id, so
turning "Weather" off in Quill Radio never touches Quill Cast. wx-free,
strict-typed, atomic JSON like the rest of the app stores.

Note: this is deliberately separate from ``core/features.FeatureManager`` (the
editor-feature catalog with profiles, unlock codes, and dependency chains).
That system treats an unknown id as *off*; app areas must default *on*, and are
a much simpler concern -- a flat set of "areas this user turned off."
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

_STORE_NAME = "app_area_features.json"

#: Sentinel for "this settings object has no such attribute", so a profile that
#: names a field an older build does not have compares unequal rather than
#: matching a None somebody happened to store.
_MISSING = object()


@dataclass(frozen=True, slots=True)
class AppArea:
    """One switchable area of an app (id, a short label, and a one-line why)."""

    id: str
    label: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class AppProfile:
    """A named starting point: the set of areas it switches *off*.

    QUILL's own feature system has had profiles since it had features
    (:data:`quill.core.features.PROFILE_DEFINITIONS`), and for the same reason:
    a checklist is the right way to change one thing and the wrong way to say
    "give me the small one". A profile is a baseline, not a mode -- applying one
    ticks and unticks the boxes and then the boxes are the truth, so the very
    next change is an ordinary per-area override rather than an escape from a
    setting that owns the dialog.

    ``disabled`` is written as what the profile takes away rather than what it
    keeps, so an area added in a later version is *on* in every existing profile
    -- the same rule :class:`AppFeatureSettings` follows, and for the same
    reason: a feature nobody chose to remove should not vanish because a profile
    written before it existed did not list it.

    ``settings`` is for the part of a name that a list of menus cannot express.
    "Notepad" does not only mean *these menus*; it means the thing you type in
    is plain text. A profile that removed the Format menu and still created rich
    text documents on Ctrl+N would be keeping the letter of its name and
    breaking its promise -- and the user would find out one document later.
    Written as ``(attribute, value)`` pairs so the dataclass stays frozen and
    comparable, and applied to whatever settings object the app hands over, so
    this module needs to know nothing about what those settings are.

    Most profiles carry none. A profile should only claim a setting when its
    *name* makes the claim: "Notepad" and "WordPad" are named after products
    whose whole identity is the answer, while "Recommended" and "Everything" are
    statements about which areas exist and have no opinion about the rest.
    """

    id: str
    name: str
    description: str
    disabled: frozenset[str] = frozenset()
    settings: tuple[tuple[str, object], ...] = ()


@dataclass(slots=True)
class AppFeatureSettings:
    """Which of an app's areas the user has turned off. Everything not listed is
    on, so unknown/new areas default enabled."""

    app_id: str
    disabled: set[str] = field(default_factory=set)

    def is_enabled(self, area_id: str) -> bool:
        return area_id not in self.disabled

    def set_enabled(self, area_id: str, enabled: bool) -> None:
        if enabled:
            self.disabled.discard(area_id)
        else:
            self.disabled.add(area_id)

    def matches_profile(
        self, profile: AppProfile, areas: Iterable[AppArea], app_settings: object = None
    ) -> bool:
        """Whether these settings are exactly what *profile* would produce.

        Compared over the known areas only, so a marker or a stale id left in
        the store by an older version cannot make a profile look unapplied.

        *app_settings*, when given, is also compared against whatever the
        profile claims (see :class:`AppProfile`). Somebody on the Notepad
        profile who switches Ctrl+N to rich text has left what that name
        promises, and reading back "Custom" is the honest answer -- the
        alternative is a control saying Notepad while the app makes something
        else.
        """
        if not all(self.is_enabled(area.id) == (area.id not in profile.disabled) for area in areas):
            return False
        if app_settings is None:
            return True
        return all(
            getattr(app_settings, name, _MISSING) == value for name, value in profile.settings
        )


def apply_profile(
    settings: AppFeatureSettings, profile: AppProfile, areas: Iterable[AppArea]
) -> None:
    """Set every known area to what *profile* says, leaving the rest alone.

    Every *known* area, not every stored id: the store also carries private
    markers (QuillLite seeds its default-off set exactly once and records that
    it did), and a profile has no opinion about those.
    """
    for area in areas:
        settings.set_enabled(area.id, area.id not in profile.disabled)


def apply_profile_settings(app_settings: object, profile: AppProfile) -> list[str]:
    """Set the app settings *profile* claims, and name the ones that changed.

    The names come back so the caller can *say* what happened: applying a
    profile changes something the user is not looking at -- what Ctrl+N will
    create -- and a change nobody is told about is one they discover a document
    later. An attribute the settings object does not have is skipped rather than
    created: a profile written for a newer build must not grow a field on an
    older one.
    """
    changed: list[str] = []
    for name, value in profile.settings:
        if not hasattr(app_settings, name) or getattr(app_settings, name) == value:
            continue
        setattr(app_settings, name, value)
        changed.append(name)
    return changed


def profile_impact(
    profile: AppProfile,
    areas: Sequence[AppArea],
    setting_words: Mapping[str, str] | None = None,
) -> str:
    """What choosing *profile* would mean, in full, as readable prose.

    The profile's own paragraph says what it *is*; this says what it **does** to
    the app in front of you -- which areas survive, which go, and what else it
    changes -- and it is computed from the areas rather than written beside
    them, so it cannot drift. An area added in a later version appears in the
    "keeps" list of every profile written before it existed, exactly as
    :class:`AppProfile` promises, without anyone editing a paragraph.

    Written for a control somebody *reads*, not for a line somebody hears in
    passing: a read-only text box a screen reader can arrow through line by
    line. So it is several short blocks rather than one long sentence, and each
    block leads with the number, because "two of seventeen" is the fact people
    actually want and counting checkboxes to get it is the cost this replaces.

    *setting_words* turns a profile's ``settings`` pairs into English -- keyed by
    attribute name, each a template taking ``{value}``. A setting with no entry
    is left out rather than printed as a variable name: "default_mode = plain"
    tells a listener nothing they can act on.

    wx-free, so both the Customize Features dialog and Preferences can show the
    same words and a test can assert them without a display.
    """
    kept = [area for area in areas if area.id not in profile.disabled]
    dropped = [area for area in areas if area.id in profile.disabled]
    total = len(areas)
    blocks = [profile.description]
    if kept:
        blocks.append(
            f"Keeps {len(kept)} of {total}: " + _sentence_list(area.label for area in kept) + "."
        )
    else:  # pragma: no cover - no shipped profile removes everything
        blocks.append(f"Keeps none of the {total} areas.")
    if dropped:
        blocks.append(
            f"Removes {len(dropped)}: " + _sentence_list(area.label for area in dropped) + "."
        )
    else:
        blocks.append("Removes nothing: every area stays switched on.")
    said = _setting_sentences(profile, setting_words)
    if said:
        # Its own block, because it is the half of the change nobody is looking
        # at: menus are visible the moment you open one, and what Ctrl+N creates
        # is not discovered until a document later.
        blocks.append("It also changes: " + " ".join(said))
    return "\n\n".join(blocks)


def profile_summary(
    profile: AppProfile,
    areas: Sequence[AppArea],
    setting_words: Mapping[str, str] | None = None,
) -> str:
    """The one-line version of :func:`profile_impact`, for saying out loud.

    An outcome and nothing else -- how many areas survive, and what else moved.
    The full text is on screen for reading; a paragraph spoken over a reader
    that is already saying the profile's name is the chattiness GATE-13 exists
    to stop.
    """
    kept = sum(1 for area in areas if area.id not in profile.disabled)
    line = f"{profile.name} profile: {kept} of {len(areas)} features on."
    said = _setting_sentences(profile, setting_words)
    return " ".join([line, *said])


def _setting_sentences(profile: AppProfile, setting_words: Mapping[str, str] | None) -> list[str]:
    """*profile*'s settings as English sentences, skipping any with no words.

    Read off the profile rather than off what would actually change, because the
    user is being told what the profile *means*: "new documents are plain text"
    is true of Notepad whether or not they were plain text already.
    """
    if not setting_words:
        return []
    return [
        setting_words[name].format(value=value)
        for name, value in profile.settings
        if name in setting_words
    ]


def _sentence_list(labels: Iterable[str]) -> str:
    """``"a, b and c"`` -- a list somebody reads aloud, not one they parse."""
    items = list(labels)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


def _read_all(data_dir: Path) -> dict:
    import json

    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def load_app_features(data_dir: Path, app_id: str) -> AppFeatureSettings:
    """Read one app's disabled-area set (absent or broken reads as all-on)."""
    raw = _read_all(data_dir)
    entry = raw.get(app_id)
    disabled: set[str] = set()
    if isinstance(entry, dict) and isinstance(entry.get("disabled"), list):
        disabled = {str(x) for x in entry["disabled"]}
    elif isinstance(entry, list):  # tolerate a bare list form
        disabled = {str(x) for x in entry}
    return AppFeatureSettings(app_id=app_id, disabled=disabled)


def save_app_features(data_dir: Path, settings: AppFeatureSettings) -> None:
    """Persist one app's disabled-area set without disturbing the others'."""
    from quill.core.storage import write_json_atomic

    raw = _read_all(data_dir)
    raw[settings.app_id] = {"disabled": sorted(settings.disabled)}
    write_json_atomic(_store_path(data_dir), raw)
