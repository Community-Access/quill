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

from quill.core.action_feedback import coerce as _coerce_action_feedback
from quill.core.lite.paths import settings_path
from quill.core.markdown_breaks import normalise_hard_break_style
from quill.core.settings_portable import (
    PortabilityReport,
    portable_export,
    portable_import,
)
from quill.core.storage import write_json_atomic
from quill.core.structure_announce import HEADING_POSITIONS

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

#: Where a heading's level goes relative to its text. Read from the shared
#: table so the two editors cannot offer different answers to one question.
_HEADING_POSITIONS = frozenset(HEADING_POSITIONS)

#: How the letters of a word may be spoken. The same three QUILL offers; the
#: labels live in :data:`quill.core.spelling.voicing.LETTER_STYLES` so the two
#: apps put the same words on screen.
_LETTER_STYLES = frozenset({"letters", "phonetic", "both"})

#: Bounds for the spell-aloud pauses. The ceiling is deliberately generous: a
#: listener on a slow synthesiser genuinely waits longer than three seconds to
#: hear a word out, and the number that makes the feature usable for them should
#: not be un-typeable.
_MIN_SPELL_MS = 100
_MAX_SPELL_MS = 5000
_MAX_ALERT_REPEAT_MS = 10000

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
    #: Say "Heading 2" when the caret arrives on a heading. On, because nothing
    #: else in the stack can say it -- no Windows edit control exposes a
    #: paragraph style, so with this off a heading reads exactly like ordinary
    #: text. Off is for the person editing a document *as* text, where the
    #: structure is not what they are listening for, and for anyone who finds
    #: it one sentence too many. Ctrl+Alt+F3 toggles it without leaving the
    #: document, which is the point: it is a per-task decision, not a
    #: preference you set once.
    announce_headings: bool = True
    #: Say "Bulleted list, 5 items" entering a list, "Level 2, 3 items" a rung
    #: down, and "Out of list" leaving it. On, and separately from the heading
    #: cue on purpose: a browser tells a screen reader an ``<ul>`` is a list with
    #: a count, and an editor cannot, so with this off a nested outline is
    #: indistinguishable by ear from a run of ordinary lines beginning with a
    #: dash. Off is for proof-reading, where the structure is settled and the
    #: phrase is one thing between you and every item. Ctrl+Alt+F5 toggles it.
    announce_lists: bool = True
    #: Where "Heading 2" goes relative to the heading's own text: ``"before"``
    #: (the default) says "Heading 2, Installing" as one sentence of QuillLite's
    #: own, and ``"after"`` lets the screen reader read the line and adds
    #: "Heading 2" behind it.
    #:
    #: Before is the default because after is **lossy**, and not in a way anyone
    #: would guess. A cue queued behind the reader is at the reader's mercy: on
    #: a large caret jump -- Ctrl+Home, a search hit, a bookmark -- NVDA and JAWS
    #: cancel what is pending and start again on the new line, so the "Heading 1"
    #: waiting its turn is never heard. Reported exactly that way: arrowing onto
    #: a heading announced it, Ctrl+Home onto the same heading did not. Before is
    #: also the order a browser gives you, where the reader says "heading level
    #: two" and then the words.
    #:
    #: After is kept, and is the right choice for anyone who would rather hear
    #: the words first and the label as a footnote -- it is the same information
    #: in the other order, and on ordinary line-by-line reading it is reliable.
    heading_announce_position: str = "before"
    # How a hard line break is written in Markdown: "backslash" or "spaces".
    # Shared with QUILL, which must never be behind QuillLite (#1488).
    markdown_hard_break_style: str = "backslash"
    #: What a plain Ctrl+N creates. The explicit New Rich Text and New Plain
    #: Text commands ignore this.
    default_mode: str = "plain"
    window_width: int = 900
    window_height: int = 650
    #: Maximized on a first launch, and whatever you left it as after that.
    #: The default is True for the reason set out in
    #: :mod:`quill.core.window_geometry`: a small window is where clipped labels
    #: and four-row lists come from, and it costs a sighted user one keystroke
    #: to undo while costing everybody else something on every launch. QuillLite
    #: keeps its geometry here rather than in the shared store for the same
    #: reason it keeps its abbreviations here -- a machine that has never had
    #: QUILL installed must not grow a Quill data folder because somebody opened
    #: a text file.
    window_maximized: bool = True
    recent_files: list[str] = field(default_factory=list)
    #: Seconds between recovery copies of a modified document. **30, matching
    #: QUILL's autosave_interval_seconds** (2026-09-15): it was 60 here for no
    #: stated reason, which meant the same crash cost a QuillLite user up to a
    #: minute of typing and a QUILL user up to thirty seconds. The two products
    #: make the same promise about unsaved work and should keep it equally well.
    #: The names still differ because each dataclass is its own store; the
    #: numbers no longer do.
    autosave_seconds: int = 30
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
    #: Whether the status bar is on screen at all. Notepad's View menu has had
    #: this checkbox since Windows 95 and QuillLite had no answer to it: the bar
    #: was always there. Per app rather than per document, because it is a
    #: statement about how you want to work rather than about a file.
    show_status_bar: bool = True
    #: Check spelling as you type. On, but never in a source or configuration
    #: file: the per-document default comes from the extension
    #: (quill.core.spellcheck_filetypes), and this is the answer for everything
    #: that rule says to check. Turning it off here silences the live check
    #: everywhere; F7 still reviews on demand, because that one is asked for.
    spell_check_while_typing: bool = True
    #: Open a blank document when nothing else is being opened. On, because that
    #: is what Notepad and WordPad do and what most people expect -- but off is a
    #: real preference and it had no way to be expressed: somebody who always
    #: opens an existing file was given an Untitled they then had to close, every
    #: launch. With it off the shell opens with no document, and File > New,
    #: Ctrl+N or Open makes the first one.
    open_blank_document_at_startup: bool = True
    # -- How a misspelling is said -----------------------------------------
    # The same twelve names QUILL stores, with the same defaults, so somebody
    # who tunes this in one editor finds the other already tuned -- and so the
    # one engine that reads them (quill.core.spelling.voicing) needs to know
    # nothing about which app handed it a settings object.
    #
    # Why they exist at all: a misspelling is the one thing in an editor that
    # speech alone cannot convey. "receive" and "recieve" are the same sound, so
    # being told the word is being told nothing; the letters are the answer, and
    # how quickly somebody wants that answer is a fact about them and their
    # synthesiser rather than about the editor.
    spell_aloud_enabled: bool = True
    spell_aloud_delay_ms: int = 800
    spell_aloud_on_navigation: bool = True
    spell_aloud_navigation_delay_ms: int = 600
    spell_aloud_suggestions: bool = True
    spell_aloud_suggestion_delay_ms: int = 600
    spell_aloud_first_suggestion: bool = False
    #: ``letters``, ``phonetic`` or ``both``.
    spell_aloud_style: str = "letters"
    spell_aloud_capitals: bool = True
    #: The alert while you type is a sound, never a voice, unless asked. Speech
    #: there interrupts the sentence it is commenting on, and somebody composing
    #: a paragraph is the person least able to afford it.
    spelling_alert_sound: bool = True
    spelling_alert_speech: bool = False
    #: Shortest gap between two alerts for the same word, so one stubborn proper
    #: noun does not become a drum. 0 means alert every time.
    spelling_alert_repeat_ms: int = 750
    # -- How a key that *did something* reports back ------------------------
    #: ``sound``, ``speech``, ``both`` or ``silent``, resolved for each moment
    #: by :func:`quill.core.action_feedback.resolve`. Stored here as well as in
    #: QUILL's settings, with the same name and the same default, so somebody
    #: who chooses words in one editor is not surprised by silence in the other.
    #: The rule itself is deliberately *not* duplicated -- both editors call the
    #: shared resolver, which is what stops the two answering differently.
    action_feedback: str = "sound"
    #: And the same choice for a search that found nothing. Separate, because
    #: wanting every success spoken and every miss kept to a tone is a coherent
    #: preference and F3 is pressed in runs.
    find_not_found_feedback: str = "sound"
    #: Carry on from the other end when a search reaches the end of the
    #: document. On, which is what QuillLite always did with no way to say
    #: otherwise; off makes Find Next stop at the end and say so.
    wrap_find: bool = True
    # -- Updates -------------------------------------------------------------
    #: Look for a new QuillLite once a day, at launch, and say nothing unless
    #: there is one. On, because the alternative is what QuillLite shipped
    #: with: a user who never opens GitHub staying on the version they
    #: installed forever, with no way to know that was happening. Nothing is
    #: downloaded or installed without being asked -- the check finds a
    #: version number and shows what changed.
    check_updates_on_launch: bool = True
    #: ISO timestamp of the last *silent* launch check, so QuillLite does not
    #: reach the network on every single launch. Ctrl+Alt+U always runs.
    last_update_check: str = ""

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
        self.markdown_hard_break_style = normalise_hard_break_style(self.markdown_hard_break_style)
        if self.spell_aloud_style not in _LETTER_STYLES:
            self.spell_aloud_style = "letters"
        # Back to "before" rather than to "after", because "before" is the one
        # that works on every kind of caret move: a hand-edited file with a typo
        # in it should not quietly cost somebody the cue on every Ctrl+Home.
        if self.heading_announce_position not in _HEADING_POSITIONS:
            self.heading_announce_position = "before"
        # Clamped rather than validated-and-refused: a hand-edited settings file
        # with a delay of 0 should give the shortest pause the feature works
        # with, not an editor that will not start.
        self.spell_aloud_delay_ms = _clamp_ms(self.spell_aloud_delay_ms, 800)
        self.spell_aloud_navigation_delay_ms = _clamp_ms(self.spell_aloud_navigation_delay_ms, 600)
        self.spell_aloud_suggestion_delay_ms = _clamp_ms(self.spell_aloud_suggestion_delay_ms, 600)
        # Floor of 0 here, because "every time" is a real answer: a throttle you
        # cannot switch off is one that eventually hides something.
        self.spelling_alert_repeat_ms = _clamp_ms(
            self.spelling_alert_repeat_ms, 750, low=0, high=_MAX_ALERT_REPEAT_MS
        )
        # Through the shared coercion rather than a local frozenset, so a mode
        # added to the enum is understood here on the day it is added.
        self.action_feedback = str(_coerce_action_feedback(self.action_feedback))
        self.find_not_found_feedback = str(_coerce_action_feedback(self.find_not_found_feedback))
        return self


def _clamp_ms(
    value: Any, fallback: int, *, low: int = _MIN_SPELL_MS, high: int = _MAX_SPELL_MS
) -> int:
    """A millisecond field forced into range, falling back on nonsense."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


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


#: Settings that describe *this machine* rather than how QuillLite behaves, and
#: so are left out of a portable backup (#1501). The same rule QUILL applies:
#: a list of recent files, a restored session and an update timestamp are a
#: record of one computer, not a configuration to carry to another.
LOCAL_SETTINGS: frozenset[str] = frozenset({
    "recent_files",
    "session_files",
    "last_update_check",
    "window_width",
    "window_height",
    "window_maximized",
})


def export_portable(settings: Settings) -> tuple[dict[str, object], PortabilityReport]:
    """QuillLite's settings as a portable file, and what was left behind."""
    return portable_export(settings, app="quilllite", local_fields=LOCAL_SETTINGS)


def import_portable(raw: object) -> tuple[Settings, PortabilityReport]:
    """The settings in *raw* this build can use, and what was different.

    Applied onto the defaults rather than onto the running settings, so an
    import is a known state rather than a merge nobody can describe afterwards.
    """
    known = frozenset(spec.name for spec in fields(Settings))
    values, report = portable_import(raw, known=known, local_fields=LOCAL_SETTINGS)
    settings = Settings()
    for name, value in values.items():
        coerced = _coerce(getattr(settings, name), value)
        if coerced is not None:
            setattr(settings, name, coerced)
    return settings.normalized(), report


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
