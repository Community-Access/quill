"""Every key the QuillVille family ships, and every system-wide show/hide key.

One collection, read by two very different callers:

* the gate (``tests/unit/ui/test_global_hotkeys.py``), which fails when any
  app's default key equals any app's default show/hide key. A show/hide key is
  registered with ``RegisterHotKey``, so it reaches its owner before any window
  sees it: a menu key in one app that equals another app's show/hide key never
  fires while that other app runs, and nothing says so;
* the **Show and Hide Key** picker in Quill Weather, Converter, Media Player
  and Inkwell (``quill/ui/show_hide_key_picker.py``), which refuses a key the
  family already uses for the same reason, in one plain sentence.

Most keys come from importable tables (QUILL's keymap, QUILL Lite's command
table, ``APP_KEYMAPS``, the QuillVille launchers). The rest are written into
menu labels (``"Name\\tCtrl+Alt+X"``) or row tables all over ``quill/apps``,
``quill/ui`` and ``quill/core``, and only a scan of the source finds them.
A frozen build ships no source, so the scan's result is committed beside this
module as ``data/family_menu_chords.json`` and the gate fails when it drifts:
``python -m quill.tools.family_chords_snapshot --write`` regenerates it.

**The four apps with no show/hide key by default** (2026-10-05). Weather,
Converter, Media Player and Inkwell each claimed a Ctrl+Alt+Shift letter that
was already a menu key somewhere else in the family, nineteen collisions in
all. Radio, QUILL and Cast keep theirs, because those are the three people
switch to all day; the other four are off until somebody chooses a key, and
somebody who had the old default is told once. Pure and wx-free.

**Every other system-wide key, too** (2026-10-05). Inkwell also registered
Quick Insert on Ctrl+Alt+Shift+K and Expand Word on Ctrl+Alt+Shift+X, both
menu keys elsewhere in the family (X is Quill Radio's Export My Setup), so they
went the same way: off until chosen, through the same picker and the same
refusals. :func:`default_system_wide_keys` is the whole list of keys any family
app registers out of the box, and the gate holds every one of them against
every family key.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "RETIRED_SHOW_HIDE_DEFAULTS",
    "SHOW_HIDE_DEFAULTS",
    "SNAPSHOT_PATH",
    "SNAPSHOT_SCHEMA",
    "FamilyChord",
    "SystemKey",
    "default_system_wide_keys",
    "every_default_chord",
    "migrate_show_hide_key",
    "retired_key_notice",
    "scan_menu_chords",
    "show_hide_key_problem",
    "show_hide_owners",
    "snapshot_chords",
    "suggest_show_hide_key",
]

#: Each app's default system-wide show/hide key. ``""`` is "none until the
#: listener chooses one" -- no ``RegisterHotKey`` call at all.
SHOW_HIDE_DEFAULTS: dict[str, str] = {
    "quill": "Ctrl+Alt+Shift+Q",
    "radio": "Ctrl+Alt+Shift+R",
    # A function key nothing else in the family uses as a command. It is also
    # the key on Quill Cast's own QuillVille row in every other app
    # (app_keymaps.SIBLING_APP_FIXED_ACCELERATORS), so one key means Cast
    # wherever you are.
    "cast": "Ctrl+Alt+Shift+F12",
    "weather": "",
    "converter": "",
    "player": "",
    "inkwell": "",
}

#: The keys the four apps registered until 2026-10-05. A saved key equal to one
#: of these is moved to "none", and the listener is told once.
RETIRED_SHOW_HIDE_DEFAULTS: dict[str, str] = {
    "weather": "Ctrl+Alt+Shift+W",
    "converter": "Ctrl+Alt+Shift+C",
    "player": "Ctrl+Alt+Shift+P",
    "inkwell": "Ctrl+Alt+Shift+I",
}

#: Where the scan's result is committed, so a frozen build can read it.
SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "family_menu_chords.json"
SNAPSHOT_SCHEMA = 1

#: What the scan walks, under ``quill/``.
_SCANNED = ("apps", "ui", "core")

_F_KEY = re.compile(r"^F\d{1,2}$")


@dataclass(frozen=True, slots=True)
class FamilyChord:
    """One default key: the app a listener meets it in, where it is, and the key."""

    app: str
    where: str
    chord: str


def _identity(chord: str) -> str:
    from quill.core.lite.keymap import chord_identity

    return chord_identity(chord)


def _title(app_id: str) -> str:
    from quill.core.app_launcher import app_name

    return app_name(app_id)


def show_hide_owners() -> dict[str, str]:
    """``{chord identity: app id}`` for every app that registers a key by default."""
    return {_identity(chord): app for app, chord in SHOW_HIDE_DEFAULTS.items() if chord}


@dataclass(frozen=True, slots=True)
class SystemKey:
    """One key an app registers system-wide out of the box: whose, what for."""

    app_id: str
    purpose: str
    chord: str


def default_system_wide_keys() -> list[SystemKey]:
    """Every key a family app registers with ``RegisterHotKey`` by default.

    The show/hide keys, Inkwell's Quick Insert and Expand Word keys, and
    QUILL's default Global Hotkeys table. Not the hardware media keys
    (``AppShellFrame._MEDIA_KEY_CODES``): Play/Pause and its neighbours have no
    modifier and are no shortcut in any app. Empty keys are left out, because
    an empty key registers nothing.
    """
    from quill.core.expansion.settings import InkwellSettings
    from quill.core.settings import Settings

    keys = [SystemKey(app, "show and hide key", chord) for app, chord in SHOW_HIDE_DEFAULTS.items()]
    inkwell = InkwellSettings()
    keys += [
        SystemKey("inkwell", "Quick Insert key", inkwell.quick_insert_hotkey),
        SystemKey("inkwell", "Expand Word key", inkwell.expand_now_hotkey),
    ]
    keys += [
        SystemKey("quill", f"system-wide key for {command}", chord)
        for command, chord in Settings().global_hotkeys.items()
    ]
    return [key for key in keys if key.chord.strip()]


# -- the tables ---------------------------------------------------------------


def _table_chords() -> list[FamilyChord]:
    from quill.core.app_keymaps import (
        APP_KEYMAPS,
        SIBLING_APP_ACCELERATORS,
        SIBLING_APP_FIXED_ACCELERATORS,
    )
    from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.keymap import default_aliases

    found = [FamilyChord("QUILL", f"QUILL {cid}", chord) for cid, chord in DEFAULT_KEYMAP.items()]
    found += [
        FamilyChord("QUILL", f"QUILL alias {cid}", chord) for cid, chord in DEFAULT_ALIASES.items()
    ]
    found += [FamilyChord("QUILL Lite", f"QUILL Lite {row[3]}", row[2]) for row in COMMANDS]
    found += [
        FamilyChord("QUILL Lite", f"QUILL Lite alias {name}", chord)
        for name, chord in default_aliases().items()
    ]
    for app_id, table in APP_KEYMAPS.items():
        found += [
            FamilyChord(_title(app_id), f"{app_id} {cid}", chord) for cid, chord in table.items()
        ]
    found += [
        FamilyChord("every QuillVille app", f"QuillVille launcher row {index}", chord)
        for index, chord in enumerate(SIBLING_APP_ACCELERATORS, start=1)
    ]
    found += [
        FamilyChord("every QuillVille app", f"QuillVille launcher: Open {_title(app)}", chord)
        for app, chord in SIBLING_APP_FIXED_ACCELERATORS.items()
    ]
    return found


# -- the scan -----------------------------------------------------------------


def _app_for(relative: str) -> str:
    """The app a scanned file's keys are met in, by where the file lives."""
    head = relative.split("/")
    name = head[-1]
    prefixes = (
        (("apps", "radio"), "radio"),
        (("ui", "radio"), "radio"),
        (("apps", "podcasts"), "cast"),
        (("ui", "podcasts"), "cast"),
        (("apps", "studio"), "studio"),
        (("apps", "weather"), "weather"),
        (("apps", "converter"), "converter"),
        (("apps", "player"), "player"),
        (("apps", "inkwell"), "inkwell"),
    )
    for (folder, stem), app in prefixes:
        if head[0] == folder and (name.startswith(stem) or (len(head) > 2 and head[1] == stem)):
            return _title(app)
    if (head[0] == "apps" and name.startswith("lite")) or head[:2] == ["core", "lite"]:
        return "QUILL Lite"
    if head[0] == "ui" and name.startswith("main_frame"):
        return "QUILL"
    return "a QuillVille app"


def _is_chord(text: str) -> bool:
    from quill.core.lite.keymap import normalise_chord

    return bool(text) and bool(normalise_chord(text))


def _numbered(prefix: str) -> list[str]:
    """A row label built as ``f"...\\tAlt+Shift+{n}"``: the nine digits it can be."""
    return [f"{prefix}{digit}" for digit in range(1, 10)]


def _scan_tree(tree: ast.AST, relative: str) -> list[FamilyChord]:
    app = _app_for(relative)
    found: list[FamilyChord] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "\t" in node.value:
            label, _tab, chord = node.value.partition("\t")
            chord = chord.strip()
            if _is_chord(chord):
                found.append(FamilyChord(app, f"{relative} {label.replace('&', '')}", chord))
        elif isinstance(node, ast.JoinedStr):
            # Numbered rows: "&{n} name\tAlt+Shift+{n}" -- recent documents,
            # recent stations, window switching, a manager's direct keys.
            values = node.values
            for index, part in enumerate(values[:-1]):
                if not (isinstance(part, ast.Constant) and isinstance(part.value, str)):
                    continue
                tail = part.value.partition("\t")[2] if "\t" in part.value else ""
                if tail.endswith("+") and isinstance(values[index + 1], ast.FormattedValue):
                    found += [
                        FamilyChord(app, f"{relative} numbered row", chord)
                        for chord in _numbered(tail)
                        if _is_chord(chord)
                    ]
        elif isinstance(node, ast.Tuple):
            # Row tables -- (menu, "&Label", "Ctrl+X", handler) and the like:
            # a tuple holding a menu label and a key.
            texts = [
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
            labels = [text for text in texts if "&" in text and "\t" not in text]
            if not labels:
                continue
            for text in texts:
                if "&" in text or "\t" in text:
                    continue
                if ("+" in text or _F_KEY.match(text)) and _is_chord(text):
                    found.append(
                        FamilyChord(app, f"{relative} {labels[-1].replace('&', '')}", text)
                    )
    return found


def scan_menu_chords(package_root: Path | None = None) -> list[FamilyChord]:
    """Every key written into a menu label or row table under ``quill/``.

    Needs the source, so it runs in a checkout (the gate, and the snapshot
    tool); an installed build reads :func:`snapshot_chords` instead.
    """
    root = package_root or Path(__file__).resolve().parents[1]
    found: list[FamilyChord] = []
    for folder in _SCANNED:
        for path in sorted((root / folder).rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            found += _scan_tree(ast.parse(path.read_text(encoding="utf-8")), relative)
    unique = {(item.app, item.where, item.chord): item for item in found}
    return [unique[key] for key in sorted(unique)]


def snapshot_chords(path: Path | None = None) -> list[FamilyChord]:
    """The committed scan. Empty when it cannot be read -- never an error."""
    try:
        raw = json.loads((path or SNAPSHOT_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = raw.get("rows", []) if isinstance(raw, dict) else []
    return [
        FamilyChord(str(row[0]), str(row[1]), str(row[2]))
        for row in rows
        if isinstance(row, list) and len(row) == 3
    ]


def every_default_chord(menus: list[FamilyChord] | None = None) -> list[FamilyChord]:
    """Every default key the family ships: the tables plus the menus.

    *menus* defaults to the committed snapshot; the gate passes a fresh scan.
    """
    rows = _table_chords() + (snapshot_chords() if menus is None else menus)
    return [row for row in rows if row.chord]


# -- the listener's own choice ---------------------------------------------------


def migrate_show_hide_key(
    app_id: str, saved: str | None, *, existing_user: bool
) -> tuple[str, bool]:
    """``(key to use, tell the listener once)`` for one of the four apps.

    *saved* is ``None`` when the app has never stored a choice (Weather,
    Converter and Media Player had nowhere to store one). Somebody who had the
    old default -- stored, or simply never changed -- is moved to none and
    told; somebody who chose their own key keeps it; somebody new is told
    nothing, because nothing changed for them.
    """
    retired = RETIRED_SHOW_HIDE_DEFAULTS.get(app_id, "")
    if saved is None:
        return SHOW_HIDE_DEFAULTS.get(app_id, ""), existing_user and bool(retired)
    if retired and saved.strip() and _identity(saved) == _identity(retired):
        return "", True
    return saved.strip(), False


def retired_key_notice(app_id: str) -> str:
    """What somebody who had the old default is told, once, at the next launch."""
    title = _title(app_id)
    return (
        f"{title}'s show and hide key is now off by default so it no longer blocks "
        "other apps' shortcuts. To choose one, open the File menu and choose "
        "Show and Hide Key."
    )


def show_hide_key_problem(
    chord: str,
    *,
    app_id: str,
    taken: dict[str, str] | None = None,
    menus: list[FamilyChord] | None = None,
    own: dict[str, str] | None = None,
) -> str:
    """Why *chord* cannot be one of *app_id*'s system-wide keys, in one sentence, or "".

    An empty *chord* is allowed: it means no key. *taken* is ``{app id: key}``
    for show/hide keys other apps in the family have been given by their
    listener; *own* is ``{purpose: key}`` for *app_id*'s other system-wide keys
    (Inkwell's ``{"show and hide key": ..., "Expand Word key": ...}`` while its
    Quick Insert key is being chosen).
    """
    from quill.core.lite.keymap import describe_binding_problem, normalise_chord

    text = chord.strip()
    if not text:
        return ""
    problem = describe_binding_problem(text)
    if problem:
        return problem
    parts = {part.strip().lower() for part in normalise_chord(text).split("+")[:-1]}
    if not parts & {"ctrl", "alt"}:
        return (
            f"{text} has no Ctrl or Alt in it, so it would take that key away from "
            "every program you type in."
        )
    me = _title(app_id)
    wanted = _identity(text)
    for purpose, key in (own or {}).items():
        if key.strip() and _identity(key) == wanted:
            return f"{text} is already {me}'s {purpose}."
    for system in default_system_wide_keys():
        if system.app_id != app_id and _identity(system.chord) == wanted:
            return f"{text} is already {_title(system.app_id)}'s {system.purpose}."
    for other, key in (taken or {}).items():
        if other != app_id and key and _identity(key) == wanted:
            return f"{text} is already {_title(other)}'s show and hide key."
    for row in every_default_chord(menus):
        if _identity(row.chord) == wanted:
            return (
                f"{text} is already a shortcut in {row.app}, and it would stop "
                f"working there whenever {me} is running."
            )
    return ""


#: Keys offered as an example in the picker, first free one wins. Not the
#: arrows: the screen-reader keymap profile walks table cells with them. Not
#: Ctrl+Alt+Shift+PageUp/PageDown either: dictation took both in 2026-10.
#: Not Ctrl+Alt with a letter or digit: on an AltGr keyboard that types a
#: character. tests/unit/core/test_show_hide_keys.py checks each is still free.
_SUGGESTIONS = (
    "Ctrl+Alt+PageUp",
    "Ctrl+Alt+PageDown",
    # Inkwell has three keys to choose, so the picker needs more than two to offer.
    "Alt+Shift+PageUp",
    "Alt+Shift+PageDown",
)


def suggest_show_hide_key(
    app_id: str, *, taken: dict[str, str] | None = None, own: dict[str, str] | None = None
) -> str:
    """A key nothing in the family uses, to offer as an example, or ""."""
    menus = snapshot_chords()
    for chord in _SUGGESTIONS:
        if not show_hide_key_problem(chord, app_id=app_id, taken=taken, menus=menus, own=own):
            return chord
    return ""
