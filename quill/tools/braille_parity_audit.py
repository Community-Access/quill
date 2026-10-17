"""Braille parity (GATE-BRAILLE): every place that speaks also reaches braille.

A deafblind user, or anyone reading a braille display with speech off, gets
from QUILL exactly what reaches the display -- an announcement that is only
spoken does not exist for them, and nobody who tests by ear notices. The
routing has three layers, and a speech call can bypass braille at any of them:

* the **announcement service** (``quill/core/announce``), where
  ``announce_wiring`` installs a ``SpeechSink`` and a ``BrailleSink`` side by
  side, and switches the engine's own inline braille off so nothing is written
  twice;
* the **engine** (``prism_bridge.AnnouncementEngine.announce``), which mirrors
  each spoken message to braille itself, for hosts without the service --
  unless that inline braille has been switched off, after which a direct
  ``engine.announce`` call is speech only;
* the **fallbacks inside the engine**: the Narrator UIA notification, VoiceOver,
  and the system voice that speaks only when no screen reader runs.

This audit walks ``quill/`` and finds every *speech primitive* call -- an
``announce(..., force_speech=...)`` on an engine, a ``speak(..., interrupt=...)``,
``narrator_announce.announce``, ``voiceover_announce``,
``speak_announcement`` and ``_enqueue_tts``. A call is ``mirrored`` when the
function that makes it also writes braille (it calls something named
``braille``/``_braille``/``_braille_writer`` or installs a ``BrailleSink``).
Every other call must be classified in the reviewed snapshot
(``tests/unit/tools/fixtures/braille_parity.json``) as ``delegates`` (it hands
the text to something that mirrors, and says what) or ``speech_only`` (with the
reason braille cannot or need not follow). A new unclassified call fails; so
does a snapshot row whose call has gone.

Run::

    python -m quill.tools.braille_parity_audit           # check (exit 1 on drift)
    python -m quill.tools.braille_parity_audit --write    # add new rows as "unreviewed"

``--write`` never classifies anything: a new row is written ``unreviewed`` and
still fails until a person sets its kind and reason.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "tools" / "fixtures" / "braille_parity.json"

KINDS = ("delegates", "speech_only")
_BRAILLE_NAMES = frozenset({"braille", "_braille", "_braille_writer", "BrailleSink"})
_PLAIN_SPEECH = frozenset({"voiceover_announce", "speak_announcement", "_enqueue_tts"})


@dataclass(frozen=True, slots=True)
class SpeechCall:
    """One speech primitive call and whether its function mirrors braille."""

    key: str  # "quill/x.py::Class.function::primitive"
    line: int
    mirrored: bool


def _name(func: ast.AST) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _keywords(call: ast.Call) -> set[str]:
    return {k.arg for k in call.keywords if k.arg}


def _primitive(call: ast.Call) -> str:
    """The speech primitive *call* is, or ""."""
    name = _name(call.func)
    words = _keywords(call)
    if name == "announce" and "force_speech" in words:
        return "engine.announce"
    if name == "speak" and "interrupt" in words:
        return "speak(interrupt)"
    if (
        name == "announce"
        and isinstance(call.func, ast.Attribute)
        and _name(call.func.value) == "narrator_announce"
    ):
        return "narrator_announce.announce"
    if name in _PLAIN_SPEECH:
        return name
    return ""


def _has_braille_call(node: ast.AST) -> bool:
    for inner in ast.walk(node):
        if isinstance(inner, ast.Call):
            if _name(inner.func) in _BRAILLE_NAMES:
                return True
            # self._braille_writer()(text): the outer call's func is a Call.
            if isinstance(inner.func, ast.Call) and _name(inner.func.func) in _BRAILLE_NAMES:
                return True
    return False


#: Statement bodies a path always runs through; climbing stops at any other
#: owner (an ``if`` branch, a loop, the function), because braille written
#: outside a branch may be skipped by that branch's ``return``.
_PASS_THROUGH = (ast.Try, ast.With, ast.AsyncWith)


def _mirrored(call: ast.Call, parents: dict[ast.AST, ast.AST]) -> bool:
    """True when braille is written on the same path as *call*.

    From the statement holding the call, look at that statement (when it is a
    simple one) and every statement after it in the same body; climb out of
    ``try``/``with`` bodies and stop at the first branch, loop or function.
    So the engine's Narrator and VoiceOver fallbacks, which return before the
    engine's braille line, are not counted as mirrored, and the Prism path,
    which reaches it, is.
    """
    node: ast.AST = call
    while True:
        parent = parents.get(node)
        if parent is None:
            return False
        if isinstance(node, ast.stmt):
            for field in ("body", "orelse", "finalbody", "handlers"):
                body = getattr(parent, field, None)
                if isinstance(body, list) and node in body:
                    index = body.index(node)
                    if not isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                        if _has_braille_call(node):
                            return True
                    if any(_has_braille_call(after) for after in body[index + 1 :]):
                        return True
                    break
            if not isinstance(parent, (*_PASS_THROUGH, ast.ExceptHandler)):
                return False
        node = parent


def _calls_in(source: str, relative: str) -> list[SpeechCall]:
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    found: list[SpeechCall] = []

    def visit(node: ast.AST, scope: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, [*scope, child.name])
                continue
            if isinstance(child, ast.Call):
                primitive = _primitive(child)
                if primitive:
                    where = ".".join(scope) or "<module>"
                    found.append(
                        SpeechCall(
                            key=f"{relative}::{where}::{primitive}",
                            line=child.lineno,
                            mirrored=_mirrored(child, parents),
                        )
                    )
            visit(child, scope)

    visit(tree, [])
    return found


def scan(root: Path = REPO_ROOT) -> list[SpeechCall]:
    """Every speech primitive call under ``quill/`` (tools excluded)."""
    calls: list[SpeechCall] = []
    for path in sorted((root / "quill").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("quill/tools/"):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not any(
            word in source
            for word in ("force_speech", "interrupt", "narrator_announce", *_PLAIN_SPEECH)
        ):
            continue
        calls.extend(_calls_in(source, relative))
    return calls


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("calls", {}))


def problems(calls: list[SpeechCall], snapshot: dict[str, dict[str, str]]) -> list[str]:
    """What is wrong, as sentences; empty when the gate passes."""
    out: list[str] = []
    unmirrored = {call.key: call for call in calls if not call.mirrored}
    for key, call in sorted(unmirrored.items()):
        row = snapshot.get(key)
        if row is None:
            out.append(
                f"{key} (line {call.line}) speaks without writing braille and is not "
                "classified: mirror it, or classify it delegates/speech_only with a reason"
            )
        elif row.get("kind") not in KINDS or not str(row.get("reason", "")).strip():
            out.append(f"{key} is classified {row.get('kind')!r}: it needs a kind and a reason")
    for key in sorted(set(snapshot) - set(unmirrored)):
        out.append(f"{key} is in the snapshot but no longer an unmirrored speech call: remove it")
    return out


def write_snapshot(calls: list[SpeechCall], path: Path = SNAPSHOT_PATH) -> None:
    """Keep reviewed rows, drop gone ones, add new ones as unreviewed."""
    old = load_snapshot(path)
    rows: dict[str, dict[str, str]] = {}
    for call in sorted((c for c in calls if not c.mirrored), key=lambda c: c.key):
        rows[call.key] = old.get(call.key, {"kind": "unreviewed", "reason": ""})
    payload = {
        "_doc": (
            "Speech calls that do not write braille in the same function, each "
            "reviewed: 'delegates' (hands the text to something that mirrors) or "
            "'speech_only' (why braille cannot or need not follow). Generated by "
            "python -m quill.tools.braille_parity_audit --write; kinds and reasons "
            "are written by a person."
        ),
        "calls": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="refresh the snapshot")
    args = parser.parse_args(argv)
    calls = scan()
    if args.write:
        write_snapshot(calls)
    found = problems(calls, load_snapshot())
    mirrored = sum(1 for call in calls if call.mirrored)
    if found:
        print("GATE-BRAILLE braille parity: FAIL")
        for line in found:
            print(f"  {line}")
        return 1
    print(
        f"GATE-BRAILLE braille parity: OK ({len(calls)} speech calls; {mirrored} mirror "
        f"braille, {len(calls) - mirrored} reviewed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
