"""Which sound events an app actually posts (GATE-SOUND).

Written after three hand-rolled greps gave three different answers to one
question -- *"are all of them supported in both quill and quill lite?"* -- and
every one of them was wrong. A regex over ``post_sound\\(`` misses the cues that
go through a helper; widening it to any string literal that looks like an event
id counts docstrings and label tables; and neither notices ``SoundEvent.WARNING``
reached through a mapping. The measurement has to be structural, or it is a
guess with a number attached.

So: an AST walk. A call to any of the **posting functions** below counts, and
its first argument is resolved when it is an ``SoundEvent`` member, a string
literal, a module constant bound to either, or a ``dict``/mapping literal of
them (which is how the dictation and conversation cues are dispatched). A
mention in a docstring is not a call and does not count; nor is a label table.

Two questions this answers, and both are gated:

* **Does this app post everything it lists?** A rostered event that nothing
  posts is a row in the Sound Scheme window that can be chosen and will never
  be heard.
* **Does it list everything it posts?** Worse: a sound that fires and is not in
  the window is one nobody can switch off.

Run directly::

    python -m quill.tools.sound_event_audit
    python -m quill.tools.sound_event_audit --app quilllite

wx-free, and it reads source rather than importing it, so it costs nothing and
cannot be defeated by an import that fails on a headless machine.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Every function whose call means "make this noise". A helper that forwards to
#: one of these counts too, because its *callers* name the event -- which is the
#: thing being measured.
POSTING_CALLS: frozenset[str] = frozenset({
    "post_sound",
    "post_sound_and_wait",
    "play_and_wait",
    "post_cue",
    "cue",
    "play_sound",
    "_play_speech_sound",
    "_cue",
    "_play_cue",
})

#: Where each app's own code lives. "quill" is everything that is not somebody
#: else's app, because the full editor is the default owner of the catalogue.
APP_SOURCES: dict[str, tuple[str, ...]] = {
    "quill": ("quill/ui/**/*.py", "quill/core/**/*.py", "quill/stability/**/*.py"),
    "quilllite": ("quill/apps/lite*.py", "quill/core/lite/*.py"),
    # The companion apps, so the seven cues that belong to them can be shown to
    # be posted *somewhere* rather than counted against the editor. They are
    # QUILL's package but not QUILL's product: a text editor that never played
    # "radio buffering" is correct, not incomplete.
    "companions": (
        "quill/apps/*.py",
        "quill/apps/beacon/*.py",
        "quill/ui/radio/*.py",
        "quill/ui/weather/*.py",
    ),
}

#: Which app owns each cue, for the "is it posted anywhere?" question. Anything
#: not listed belongs to the editor.
COMPANION_PREFIXES: tuple[str, ...] = ("radio_", "cast_", "weather_", "beacon_")

#: Keyword arguments that carry a cue to something that will play it. The
#: announcement service takes ``sound=`` and hands it to a SoundSink, so a call
#: that names no posting function still makes a noise.
_CUE_KEYWORDS: frozenset[str] = frozenset({"sound", "cue", "earcon", "sound_event"})

#: Posted by the sound machinery itself rather than by any app: the keep-alive
#: clip is played on a timer inside the manager, whose file is excluded from the
#: scan precisely because it is infrastructure. Counting it as unposted would be
#: reporting a gap that does not exist.
INFRASTRUCTURE_EVENTS: frozenset[str] = frozenset({"keepalive"})

#: Files that talk *about* events without posting them. Excluded so a catalogue
#: cannot make itself look like a call site.
_CATALOGUE_FILES = frozenset({
    "sound_events.py",
    "sound_event_labels.py",
    "sound_app_events.py",
    "sound_scheme.py",
    "sound_scheme_dialog.py",
    "sound_pack.py",
    "sound_manager.py",
    "sound_player.py",
    "sound_event_audit.py",
})


@dataclass
class _Scan:
    """What one file's syntax tree says about the sounds it makes."""

    known: frozenset[str]
    posted: set[str] = field(default_factory=set)
    constants: dict[str, str] = field(default_factory=dict)

    def resolve(self, node: ast.AST) -> set[str]:
        """Every event id *node* could evaluate to."""
        found: set[str] = set()
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in self.known:
                found.add(node.value)
        elif isinstance(node, ast.Attribute):
            # SoundEvent.TEXT_PASTED -> "text_pasted". Compared by the member
            # name lowercased, which is the enum's own convention and is checked
            # against the known set, so a typo resolves to nothing rather than
            # to a plausible-looking id.
            lowered = node.attr.lower()
            if lowered in self.known:
                found.add(lowered)
        elif isinstance(node, ast.Name):
            value = self.constants.get(node.id)
            if value:
                found.add(value)
        elif isinstance(node, ast.Subscript):
            # events[kind] -- a mapping lookup. Anything the mapping can hold.
            found |= self.resolve(node.value)
        elif isinstance(node, ast.Dict):
            for value in node.values:
                found |= self.resolve(value)
        elif isinstance(node, ast.IfExp):
            found |= self.resolve(node.body) | self.resolve(node.orelse)
        elif isinstance(node, ast.Call):
            # events.get(kind) and the like: look inside the callee's object.
            if isinstance(node.func, ast.Attribute):
                found |= self.resolve(node.func.value)
        return found


def _known_events() -> frozenset[str]:
    from quill.core.sound_events import SoundEvent

    return frozenset(event.value for event in SoundEvent)


def _docstrings(tree: ast.AST) -> set[int]:
    """Ids of the string nodes that are docstrings, so prose cannot count."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                found.add(id(body[0].value))
    return found


def _defines_cue_constants(tree: ast.AST, known: frozenset[str]) -> bool:
    """Whether this module is a table of cue names -- ``CUE_X = "event_id"``."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if (
            isinstance(target, ast.Name)
            and target.id.isupper()
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and value.value in known
        ):
            return True
    return False


def _posts_anything(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else None
        if name is None and isinstance(node.func, ast.Name):
            name = node.func.id
        if name in POSTING_CALLS:
            return True
    return False


def _posted_in(path: Path, known: frozenset[str]) -> set[str]:
    """Every event *path* posts.

    Two rules, and the second is a deliberate over-count.

    Precise: a posting call whose argument resolves to an event. That catches
    the ordinary ``post_sound(SoundEvent.X)`` and the literal form.

    Generous: **in a file that posts at all**, every ``SoundEvent`` member and
    every event-shaped string literal it mentions counts too. That is how the
    table-dispatched cues are caught -- ``post_cue(_STATE_SOUNDS[state])`` names
    its events in a dict three hundred lines away, and a loop over
    ``((EVT_TEXT_CUT, SoundEvent.TEXT_CUT), ...)`` names them in a tuple.
    Chasing those precisely would mean writing a dataflow analysis to answer a
    question whose wrong answers are asymmetric: crediting an event that is only
    mentioned costs a spare row in a settings window, while missing one that is
    genuinely posted means a sound nobody can switch off. Over-count, on purpose.

    Docstrings are excluded either way. A module explaining what
    ``spelling_alert`` is for is not a module that plays it.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    scan = _Scan(known=known)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                values = scan.resolve(node.value)
                if len(values) == 1:
                    scan.constants[target.id] = next(iter(values))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else None
        if name is None and isinstance(node.func, ast.Name):
            name = node.func.id
        if name in POSTING_CALLS and node.args:
            scan.posted |= scan.resolve(node.args[0])
        # ``_announce(message, sound=SoundEvent.X)`` -- the announcement service
        # carries the cue as a keyword and plays it through its own SoundSink,
        # which is how most of the companion apps' earcons are posted. Reading
        # only the first positional argument missed every one of them.
        for keyword in node.keywords:
            if keyword.arg in _CUE_KEYWORDS:
                scan.posted |= scan.resolve(keyword.value)
    if not _posts_anything(tree):
        # A module that defines nothing but cue *constants* still tells us those
        # cues exist and are meant to be played -- ``quill/core/speech/
        # conversation.py`` is nine ``CUE_X = "conversation_x"`` lines and no
        # calls, and the frame that plays them imports the names rather than the
        # strings. Without this the six conversation cues read as unposted while
        # firing perfectly well.
        if _defines_cue_constants(tree, known):
            scan.posted |= set(scan.constants.values())
        return scan.posted
    prose = _docstrings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.lower() in known:
            if isinstance(node.value, ast.Name) and node.value.id == "SoundEvent":
                scan.posted.add(node.attr.lower())
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in known and id(node) not in prose:
                scan.posted.add(node.value)
    return scan.posted


def posted_events(app_id: str) -> set[str]:
    """Every event *app_id*'s own source actually posts."""
    known = _known_events()
    found: set[str] = set()
    for pattern in APP_SOURCES.get(app_id, ()):
        for path in _REPO_ROOT.glob(pattern):
            if path.name in _CATALOGUE_FILES:
                continue
            relative = path.relative_to(_REPO_ROOT).as_posix()
            if app_id == "quill" and ("/lite" in relative or path.name.startswith("lite")):
                continue  # QUILL Lite's cues are QUILL Lite's
            found |= _posted_in(path, known)
    return found


def unposted_events(app_id: str, *, own_only: bool = False) -> list[str]:
    """Declared, catalogued, and never made a noise.

    Ladders are excluded: progress steps, copy-tray slots, bookmark slots and
    indent depths are dispatched by table from a generated id, so no source line
    names them and no scan can find one.

    *own_only* drops the companion apps' cues from the editor's report. A text
    editor that never plays "radio buffering" is correct rather than incomplete,
    and mixing the two makes the number that matters impossible to read.
    """
    known = _known_events()
    ladders = ("indent_", "progress_", "copy_slot_", "bookmark_slot_")
    posted = posted_events(app_id) | INFRASTRUCTURE_EVENTS
    missing = (event for event in known - posted if not event.startswith(ladders))
    if own_only:
        missing = (event for event in missing if not event.startswith(COMPANION_PREFIXES))
    return sorted(missing)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report the sound events an app posts.")
    parser.add_argument("--app", default="quill", choices=sorted(APP_SOURCES))
    parser.add_argument(
        "--own-only",
        action="store_true",
        help="Ignore the companion apps' cues (radio, cast, weather, beacon).",
    )
    args = parser.parse_args(argv)

    known = _known_events()
    posted = posted_events(args.app)
    missing = unposted_events(args.app, own_only=args.own_only)
    print(f"{args.app}: posts {len(posted)} of {len(known)} declared events.")
    if missing:
        print(f"\n{len(missing)} named event(s) declared and never posted:")
        for event in missing:
            print(f"  {event}")
        print(
            "An event nothing posts is a row in the Sound Scheme window "
            "that can be chosen, previewed and switched off, and will "
            "never be heard."
        )
        return 1
    print("Every named event has a call site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
