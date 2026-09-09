"""QuillLite's settings: ten fields, one small JSON file, written atomically.

Deliberately not :class:`quill.core.settings.Settings`. QUILL's settings object
carries hundreds of fields for features QuillLite does not have and must never
grow -- AI, dictation, Quillins, publishing -- and sharing it would make
QuillLite's data folder a place a QUILL feature could appear by accident. A
dozen fields is the whole product: a theme, a font, a wrap, a default mode, a
window size, a recent list, a session list, and how often unsaved work is copied
aside.

What *is* shared is the write: :func:`~quill.core.storage.write_json_atomic`,
QUILL's own temp-file-plus-``os.replace`` writer, so a settings file cannot be
left half-written by a power cut mid-save. The loader is deliberately tolerant
in the other direction -- a corrupt or hand-edited file yields defaults and
never an exception, because an editor that refuses to open because its settings
file has a stray comma is an editor somebody loses work to.

**Only what differs from the default is written**, which is the one thing
QUILL's versioned-delta contract (``docs/design/persistence-and-migration.md``)
exists to buy, taken directly rather than through the machinery. If a later
version decides dark mode should follow the system instead, everybody who never
expressed a preference moves with it -- because their file never said "dark", it
said nothing. A store that writes every field freezes today's defaults into
every user's profile forever, and the person who suffers for it is the one who
never touched the setting.

The file carries a ``schema`` stamp so a future shape change has something to
branch on. There is nothing to migrate *from* yet -- this is 1.0.0 -- and the
loader's tolerance means an unstamped or foreign file still opens.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from quill.core.lite.paths import settings_path
from quill.core.storage import write_json_atomic

__all__ = ["MAX_RECENT", "MAX_SESSION", "SCHEMA", "Settings", "load", "save"]

#: The on-disk shape's version. Bumped only when a field changes meaning in a
#: way the tolerant loader cannot absorb -- which has not happened yet.
SCHEMA = 1

#: How many recent files are remembered. Nine are offered with an Alt+digit
#: mnemonic; the tenth is the one that falls off the end next.
MAX_RECENT = 10

#: How many documents a restored session reopens. Nine, because that is how many
#: the Window menu can put a digit on, and reopening thirty files because
#: somebody once had thirty open is not a service.
MAX_SESSION = 9

#: The allowed values for the two closed-vocabulary fields, so a hand-edited
#: file cannot put the editor into a mode it has no code for.
_THEMES = frozenset({"dark", "system"})
_MODES = frozenset({"plain", "rich"})

#: Point sizes outside this range are either unreadable or a typo.
_MIN_FONT_POINTS = 6
_MAX_FONT_POINTS = 72

#: Never copy unsaved work aside more often than this: the copy is a TOM save
#: on a real control, and a two-second timer would be felt while typing.
_MIN_AUTOSAVE_SECONDS = 15


@dataclass
class Settings:
    """Everything QuillLite remembers between sessions."""

    #: ``dark`` or ``system``. Dark is the default, and that is a decision
    #: rather than a fashion: the users this editor is for are
    #: disproportionately light-sensitive, and a first launch that is bright
    #: white is a first launch some of them cannot read.
    theme: str = "dark"
    #: Empty means the system default face; a name means that face.
    font_name: str = ""
    font_size: int = 12
    word_wrap: bool = True
    #: What a plain Ctrl+N creates. The explicit New Rich Text and New Plain
    #: Text commands ignore this.
    default_mode: str = "plain"
    window_width: int = 900
    window_height: int = 650
    window_maximized: bool = False
    recent_files: list[str] = field(default_factory=list)
    autosave_seconds: int = 60
    #: Reopen the documents that were open when the app last closed. On by
    #: default: with MDI there is one window and a numbered list inside it, so
    #: coming back to yesterday's four documents is the expected shape rather
    #: than a surprise. Distinct from crash recovery, which only ever restores
    #: work that was never saved.
    restore_session: bool = True
    #: The files open at the last clean exit, in the order they were numbered.
    #: Written on exit and read once at start; never used for anything else.
    session_files: list[str] = field(default_factory=list)
    #: Read abbreviations from QUILL's shared library instead of QuillLite's own.
    #: Off by default and deliberately so: Inkwell shares that library because
    #: one library is its entire value, while QuillLite is offered as an
    #: alternative to QUILL -- and a machine that has never had QUILL installed
    #: must not grow a Quill data folder because somebody opened a text file.
    share_quill_abbreviations: bool = False
    #: Read and write taught words in QUILL's shared dictionary instead of
    #: QuillLite's own. Off by default for the same reason the abbreviation
    #: switch is: a machine that has never had QUILL installed must not grow a
    #: Quill data folder because somebody taught a text editor a word.
    share_quill_dictionary: bool = False
    #: Check spelling as you type. On, but never in a source or configuration
    #: file: the per-document default comes from the extension
    #: (quill.core.spellcheck_filetypes), and this is the answer for everything
    #: that rule says to check. Turning it off here silences the live check
    #: everywhere; F7 still reviews on demand, because that one is asked for.
    spell_check_while_typing: bool = True

    def remember_recent(self, path: str | Path) -> None:
        """Move *path* to the head of the recent list, without duplicating it."""
        text = str(path)
        self.recent_files = [entry for entry in self.recent_files if entry != text]
        self.recent_files.insert(0, text)
        del self.recent_files[MAX_RECENT:]

    def normalized(self) -> Settings:
        """This object with every field forced back into range. Returns self."""
        if self.theme not in _THEMES:
            self.theme = "dark"
        if self.default_mode not in _MODES:
            self.default_mode = "plain"
        self.font_size = max(_MIN_FONT_POINTS, min(_MAX_FONT_POINTS, int(self.font_size)))
        self.autosave_seconds = max(_MIN_AUTOSAVE_SECONDS, int(self.autosave_seconds))
        self.window_width = max(320, int(self.window_width))
        self.window_height = max(240, int(self.window_height))
        self.recent_files = [str(entry) for entry in self.recent_files][:MAX_RECENT]
        self.session_files = [str(entry) for entry in self.session_files][:MAX_SESSION]
        return self


def _coerce(current: Any, value: Any) -> Any | None:
    """*value* if it can stand in for *current*, else ``None`` (keep the default).

    ``bool`` is checked before ``int`` because ``isinstance(True, int)`` is true
    in Python, and a ``word_wrap`` of ``3`` should not be accepted as truthy.
    """
    if isinstance(current, bool):
        return value if isinstance(value, bool) else None
    if isinstance(current, int):
        return value if isinstance(value, int) and not isinstance(value, bool) else None
    if isinstance(current, str):
        return value if isinstance(value, str) else None
    if isinstance(current, list):
        return [str(item) for item in value] if isinstance(value, list) else None
    return None


def load(path: Path | None = None) -> Settings:
    """Read the settings file. A missing, corrupt or foreign file gives defaults."""
    target = path if path is not None else settings_path()
    settings = Settings()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings.normalized()
    if not isinstance(raw, dict):
        return settings.normalized()
    known = {spec.name for spec in fields(Settings)}
    for key, value in raw.items():
        if key not in known:
            continue  # a field from a newer build, or somebody's note to self
        coerced = _coerce(getattr(settings, key), value)
        if coerced is not None:
            setattr(settings, key, coerced)
    return settings.normalized()


def save(settings: Settings, path: Path | None = None) -> None:
    """Write the settings file atomically, storing only what is not a default.

    Raises ``OSError`` if the disk says no; that is the caller's to swallow,
    because a read-only profile must not make the editor unusable.
    """
    target = path if path is not None else settings_path()
    write_json_atomic(target, {"schema": SCHEMA, **_deltas(settings.normalized())})


def _deltas(settings: Settings) -> dict[str, Any]:
    """Every field whose value differs from the code default.

    The whole reason this function exists: a user who never chose a theme has no
    ``theme`` in their file, so a later version that changes the default takes
    them with it. Writing every field would freeze today's answer into their
    profile forever.
    """
    default = asdict(Settings())
    return {key: value for key, value in asdict(settings).items() if value != default[key]}
