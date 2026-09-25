"""Bring a QUILL Lite setup into QUILL, and share what is worth sharing.

QUILL Lite keeps its state in its own folder, on purpose:
``quill/core/lite/paths.py`` says why -- a Notepad-scale editor that silently
adopted a writing environment's settings would be deciding something nobody
asked it to, and uninstalling it could then cost the user something QUILL owns.
That reasoning is about *silence*, not about sharing, and this module is the
other half of it: everything here happens because somebody asked for it, once,
by name.

Two kinds of state, and they are treated differently (decided 2026-09-18):

**Content is shared, in QUILL's folder.** Abbreviations, the personal
dictionary, the copy tray, the clip library and per-file bookmarks are things a
person builds up over months, and keeping two copies in step by hand is the
chore that ends with one copy quietly stale. QUILL Lite already has this for two
of them -- ``share_quill_abbreviations`` and ``share_quill_dictionary`` point it
at QUILL's folder -- so QUILL's folder is *already* the shared home, and this
follows that direction rather than inventing a second one. QUILL Lite's content
is merged in once, and its switches are turned on, so from then on a change in
either editor is a change in both.

**Preferences are copied.** Wrap, autosave, spell-check-while-typing and the
rest are about *the editor you are in*, and the two are not the same editor:
QUILL has menus, panels and a leader key QUILL Lite does not have. A one-time
copy gets somebody started in the shape they know and then lets the two drift,
which is the honest answer. Keymap overrides come the same way and for the same
reason -- a chord you rebound in a nine-menu editor should not silently rebind
something in a twenty-menu one.

**Merging never loses.** QUILL's own entry wins every collision, in every store.
Somebody running this has been using QUILL; what is already here is more recent
than what QUILL Lite's file remembers, and an import that overwrites it is an
import that undoes their work.

wx-free: the UI asks for a plan, shows it, and applies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.lite.parity import NOT_ALIASES, quill_setting_for

__all__ = [
    "SHARED_CONTENT_STORES",
    "BringPlan",
    "SharedStore",
    "apply_bring_plan",
    "describe_plan",
    "enable_lite_sharing",
    "lite_data_dir",
    "merge_json_store",
    "plan_bring_from_lite",
    "translate_lite_keymap",
    "translate_lite_settings",
]


@dataclass(frozen=True, slots=True)
class SharedStore:
    """One store both editors can keep in QUILL's folder."""

    #: The key the report and the tests use.
    key: str
    #: What it is called to a person, in a sentence that says what is in it.
    label: str
    #: The file name inside QUILL Lite's data directory.
    lite_file: str
    #: The file name inside QUILL's data directory.
    quill_file: str
    #: The QUILL Lite setting that points it at QUILL's folder from then on, or
    #: ``""`` for a store QUILL Lite has no switch for yet.
    lite_share_field: str = ""


#: The five content stores, in the order a person would think of them. The two
#: with a switch are the two QUILL Lite already ships sharing for; the other three
#: are merged once, and QUILL is where they live afterwards.
SHARED_CONTENT_STORES: tuple[SharedStore, ...] = (
    SharedStore(
        "abbreviations",
        "Abbreviations -- the short forms you type and what they expand to",
        "abbreviations.json",
        "abbreviations.json",
        "share_quill_abbreviations",
    ),
    SharedStore(
        "dictionary",
        "Personal dictionary -- the words you have told the spell checker are real",
        "dictionaries/personal.json",
        "dictionaries/personal.json",
        "share_quill_dictionary",
    ),
    SharedStore(
        "copy_tray",
        "Copy tray -- the twelve numbered slots and their labels",
        "copy_tray.json",
        "copy_tray.json",
    ),
    SharedStore(
        "clip_library",
        "Clip library -- the clips you have kept",
        "clip_library.json",
        "clip_library.json",
    ),
    SharedStore(
        "bookmarks",
        "Bookmarks -- the named places in each file you come back to",
        "document_memory.json",
        "document_memory.json",
    ),
)

#: Settings that must NOT be copied even though both editors have the field.
#: Each describes this computer or this window rather than a preference, and
#: bringing it over is how somebody ends up with a window off the edge of a
#: screen they do not have, or a Recent list of files this install cannot open.
_NOT_COPIED: frozenset[str] = frozenset({
    "recent_files",
    "session_files",
    "window_width",
    "window_height",
    "window_x",
    "window_y",
    "window_maximized",
    "last_directory",
    "last_open_directory",
    "last_save_directory",
    "share_quill_abbreviations",
    "share_quill_dictionary",
})

#: QUILL Lite's ``default_mode`` is plain/rich and QUILL's
#: ``default_new_document_format`` names a format, so the value needs
#: translating rather than copying. The parity table records the pair; this is
#: the translation it says an importer has to do.
_MODE_TO_FORMAT: dict[str, str] = {"plain": "txt", "rich": "rtf"}


@dataclass(slots=True)
class BringPlan:
    """What bringing a QUILL Lite setup over would actually do."""

    #: QUILL Lite's data directory, or ``None`` when there is no setup to bring.
    lite_dir: Path | None = None
    #: ``QUILL field -> value``, ready to set on :class:`~quill.core.settings.Settings`.
    settings: dict[str, object] = field(default_factory=dict)
    #: ``QUILL command id -> chord``, translated from QUILL Lite's handler names.
    keymap: dict[str, str] = field(default_factory=dict)
    #: The content stores QUILL Lite actually has a file for.
    shared: tuple[SharedStore, ...] = ()
    #: Fields found in QUILL Lite's settings that QUILL has no home for, so the
    #: report can say what is being left behind rather than implying it came.
    skipped: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.settings or self.keymap or self.shared)


def lite_data_dir() -> Path | None:
    """QUILL Lite's data directory, if this machine has one.

    ``None`` rather than a guess when QUILL Lite has never run: an import that
    finds nothing and reports success is worse than one that says there is
    nothing here.
    """
    try:
        from quill.core.lite.paths import data_dir
    except Exception:  # noqa: BLE001 - a missing sibling is not an error
        return None
    try:
        directory = data_dir()
    except Exception:  # noqa: BLE001
        return None
    return directory if directory.is_dir() else None


def translate_lite_settings(raw: dict[str, object]) -> tuple[dict[str, object], tuple[str, ...]]:
    """QUILL Lite's settings as QUILL's, plus the names that had no home here.

    The name mapping is :func:`quill.core.lite.parity.quill_setting_for`, so this
    cannot drift from the parity gate. Two things it refuses to do: copy a field
    that describes this computer rather than a preference, and copy a field whose
    QUILL namesake means something else (``NOT_ALIASES`` -- QUILL Lite's
    ``recent_files`` is a list of files and QUILL's ``recent_files_limit`` is a
    number, and handing an importer one where it expects the other is the most
    plausible single way to corrupt a settings file).
    """
    from quill.core.settings import Settings

    known = {f for f in Settings.__dataclass_fields__ if not f.startswith("_")}
    brought: dict[str, object] = {}
    skipped: list[str] = []
    for lite_field, value in sorted(raw.items()):
        if lite_field.startswith("_") or lite_field == "schema":
            continue
        if lite_field in _NOT_COPIED or lite_field in NOT_ALIASES:
            skipped.append(lite_field)
            continue
        quill_field = quill_setting_for(lite_field)
        if quill_field not in known:
            skipped.append(lite_field)
            continue
        if lite_field == "default_mode":
            translated = _MODE_TO_FORMAT.get(str(value))
            if translated is None:
                skipped.append(lite_field)
                continue
            brought[quill_field] = translated
            continue
        brought[quill_field] = value
    return brought, tuple(skipped)


def translate_lite_keymap(raw: dict[str, object]) -> dict[str, str]:
    """QUILL Lite's saved rebindings as QUILL command ids.

    Through :data:`quill.core.lite.parity.COMMAND_EQUIVALENTS`, the one table
    that knows which handler is which command. A handler with no QUILL
    equivalent is dropped rather than guessed at: a chord landing on the wrong
    command is worse than a chord that stayed where it was.
    """
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    brought: dict[str, str] = {}
    for handler, chord in sorted(raw.items()):
        command_id = COMMAND_EQUIVALENTS.get(str(handler), "")
        if not command_id or command_id not in DEFAULT_KEYMAP:
            continue
        if not isinstance(chord, str) or not chord.strip():
            continue
        brought[command_id] = chord.strip()
    return brought


def plan_bring_from_lite(lite_dir: Path | None = None) -> BringPlan:
    """What is there to bring, without changing anything.

    Split from applying it so the question can be asked with the answer in hand:
    "bring my settings across" is a reasonable thing to offer and an
    unreasonable thing to do on a guess, and somebody who cannot see the result
    needs to be told what it would be before it happens.
    """
    from quill.core.storage import read_json

    directory = lite_dir if lite_dir is not None else lite_data_dir()
    if directory is None:
        return BringPlan()

    raw_settings = read_json(directory / "settings.json", default={})
    settings: dict[str, object] = {}
    skipped: tuple[str, ...] = ()
    if isinstance(raw_settings, dict):
        settings, skipped = translate_lite_settings(raw_settings)

    raw_keymap = read_json(directory / "keymap.json", default={})
    keymap = translate_lite_keymap(raw_keymap) if isinstance(raw_keymap, dict) else {}

    shared = tuple(
        store for store in SHARED_CONTENT_STORES if (directory / store.lite_file).is_file()
    )
    return BringPlan(
        lite_dir=directory,
        settings=settings,
        keymap=keymap,
        shared=shared,
        skipped=skipped,
    )


def merge_json_store(lite_path: Path, quill_path: Path) -> int:
    """Merge *lite_path* into *quill_path*, QUILL winning. Returns entries added.

    Shape-agnostic on purpose: these five files are a dict of entries, a list of
    entries, or a dict with one list inside it, and a merger that knew each shape
    would be five mergers to keep in step with five schemas. What matters is the
    rule, and the rule is the same for all of them -- **nothing already in QUILL
    is replaced**, and anything QUILL Lite has that QUILL does not is added.

    Returns 0 and writes nothing when there is nothing to add, when either file
    cannot be read, or when the two are different shapes. A merge that cannot be
    done safely is a merge that is not done: these files are the user's work.
    """
    from quill.core.storage import read_json, write_json_atomic

    lite_data = read_json(lite_path, default=None)
    if lite_data is None:
        return 0
    quill_data = read_json(quill_path, default=None)
    if quill_data is None:
        quill_data = [] if isinstance(lite_data, list) else {}
    if type(lite_data) is not type(quill_data):
        return 0

    if isinstance(lite_data, list):
        merged, added = _merge_lists(lite_data, list(quill_data))
        if added:
            write_json_atomic(quill_path, merged)
        return added

    if isinstance(lite_data, dict):
        result = dict(quill_data)
        added = 0
        for key, value in lite_data.items():
            if key in result:
                if isinstance(value, list) and isinstance(result[key], list):
                    merged_list, gained = _merge_lists(value, list(result[key]))
                    if gained:
                        result[key] = merged_list
                        added += gained
                continue
            result[key] = value
            added += 1
        if added:
            write_json_atomic(quill_path, result)
        return added
    return 0


def _merge_lists(incoming: list[object], existing: list[object]) -> tuple[list[object], int]:
    """*existing* plus whatever *incoming* has that it does not. QUILL wins.

    Identity is the whole entry for a scalar, and the ``id``/``abbreviation``/
    ``word`` field for a record -- whichever it has, in that order. Comparing
    whole records would re-add an entry somebody had edited on one side, which is
    the one duplicate a person would actually notice.
    """
    seen = {_identity(entry) for entry in existing}
    added = 0
    for entry in incoming:
        key = _identity(entry)
        if key in seen:
            continue
        seen.add(key)
        existing.append(entry)
        added += 1
    return existing, added


def _identity(entry: object) -> object:
    if isinstance(entry, dict):
        for name in ("id", "abbreviation", "word", "trigger", "name"):
            if name in entry:
                return (name, str(entry[name]).lower())
        return repr(sorted((str(k), repr(v)) for k, v in entry.items()))
    return repr(entry)


def apply_bring_plan(plan: BringPlan, quill_dir: Path) -> dict[str, int]:
    """Merge the plan's content stores into *quill_dir*. Returns entries added per store.

    The settings and the keymap are the caller's to apply -- they live on objects
    the UI owns. Only the files are done here, because only the files can be done
    without wx.
    """
    if plan.lite_dir is None:
        return {}
    added: dict[str, int] = {}
    for store in plan.shared:
        target = quill_dir / store.quill_file
        target.parent.mkdir(parents=True, exist_ok=True)
        gained = merge_json_store(plan.lite_dir / store.lite_file, target)
        if gained:
            added[store.key] = gained
    return added


def enable_lite_sharing(plan: BringPlan) -> tuple[str, ...]:
    """Point QUILL Lite at QUILL's folder for the stores it has a switch for.

    The only thing this module writes into QUILL Lite's own settings, and the
    reason it is allowed to: a person who has just asked for one shared set of
    abbreviations has asked for exactly this, and doing half of it -- QUILL
    holding QUILL Lite's words while QUILL Lite still reads its own copy -- is the
    shape that makes a "shared" store look broken.

    Returns the switches it turned on. Silent when QUILL Lite is not installed.
    """
    from quill.core.storage import read_json, write_json_atomic

    if plan.lite_dir is None:
        return ()
    fields = tuple(store.lite_share_field for store in plan.shared if store.lite_share_field)
    if not fields:
        return ()
    path = plan.lite_dir / "settings.json"
    raw = read_json(path, default={})
    if not isinstance(raw, dict):
        return ()
    changed = [name for name in fields if not raw.get(name, False)]
    if not changed:
        return ()
    for name in changed:
        raw[name] = True
    write_json_atomic(path, raw)
    return tuple(changed)


def describe_plan(plan: BringPlan) -> str:
    """The plan as sentences, for a dialog and for a screen reader.

    Counts first, because a count is the one thing a listener cannot get by
    exploring the dialog, and what is being *left behind* last, because "it
    brought everything" is the impression an import gives if nobody says
    otherwise.
    """
    if plan.lite_dir is None:
        return "QUILL Lite has not been run on this computer, so there is nothing to bring."
    if plan.is_empty:
        return (
            f"QUILL Lite's folder is here ({plan.lite_dir}) but holds nothing to bring: "
            "no changed settings, no rebound keys, and none of the shared stores."
        )
    lines: list[str] = []
    if plan.settings:
        lines.append(f"{len(plan.settings)} setting(s) copied.")
    if plan.keymap:
        lines.append(f"{len(plan.keymap)} rebound key(s) copied, where QUILL has the command.")
    if plan.shared:
        lines.append(
            f"{len(plan.shared)} store(s) merged into QUILL and shared from then on, "
            "so a change in either editor is a change in both:"
        )
        lines.extend(f"  {store.label}" for store in plan.shared)
        lines.append("Nothing already in QUILL is replaced.")
    if plan.skipped:
        lines.append(
            f"Left behind ({len(plan.skipped)}): "
            + ", ".join(plan.skipped)
            + ". These describe QUILL Lite or this computer rather than a preference."
        )
    return "\n".join(lines)
