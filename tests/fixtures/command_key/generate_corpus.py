"""Generate the Command Key's seed corpus (docs/design/command-key.md 14.1).

    python tests/fixtures/command_key/generate_corpus.py

Writes ``quill.jsonl``, ``lite.jsonl`` and ``radio.jsonl`` beside this file.
The seed is mechanical: for every offered catalogue row, its examples and
aliases, politer and terser ways of putting them, one-typo "misheard" forms,
and the same example with the command switched off (which must be refused with
the probe's reason, never swapped for a near miss). For every app, negatives:
NEVER rows' words, questions for Ask, other apps' commands, dangerous verbs
and nonsense. ``held_out`` is every fifth row, never tuned on.

Hand-written rows -- the blind testers' phrasings above all -- go in
``<app>.extra.jsonl``, which this script never touches.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parents[2]))

from quill.core.command_catalogue import CommandSpec, rows_for_app  # noqa: E402
from quill.core.command_catalogue.policy import _shared  # noqa: E402

_APPS = ("quill", "lite", "radio")
_POLITE = ("please {}", "{} please", "can you {}", "could you {} for me", "I want to {}")
_NONSENSE = (
    "flibbertigibbet",
    "purple monkey dishwasher",
    "zxcv",
    "the quick brown fox",
    "banana",
    "hmm",
    "lorem ipsum dolor",
    "seventeen giraffes",
)
_ASK = (
    "why is the sky blue",
    "write me a poem about autumn",
    "who won the world cup",
    "explain photosynthesis",
    "tell me a joke",
    "how do magnets work",
    "translate hello into French",
    "summarize the news",
)
_DANGER = (
    "delete everything",
    "send this to my boss",
    "publish it",
    "upload my files",
    "sign me in to ChatGPT",
    "erase all my work",
    "uninstall the app",
    "push to GitHub",
)


def _typo(text: str) -> str | None:
    """The sentence with one letter dropped from its longest long word."""
    words = text.split()
    longest = max(range(len(words)), key=lambda index: len(words[index]))
    word = words[longest]
    if len(word) < 7 or not word.isalpha():
        return None
    middle = len(word) // 2
    words[longest] = word[:middle] + word[middle + 1 :]
    return " ".join(words)


def _row(text: str, app: str, expect: dict[str, object], **extra: object) -> dict[str, object]:
    row: dict[str, object] = {"text": text, "app": app, "mode": "typed", "expect": expect}
    row.update(extra)
    return row


def _positive_rows(app: str, spec: CommandSpec, ids: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    expect = {"id": spec.id}
    # A phrase the shared rows answer ("again", "what can I do here") is theirs.
    phrases = [
        phrase
        for phrase in dict.fromkeys((*spec.examples, *spec.aliases, spec.title))
        if _shared(phrase) is None
    ]
    if not phrases:
        return []
    for phrase in phrases:
        rows.append(_row(phrase, app, expect, tier_max=1))
    for template in _POLITE:
        rows.append(_row(template.format(phrases[0]), app, expect))
    for phrase in phrases:
        typo = _typo(phrase)
        if typo is not None:
            rows.append(_row(typo, app, expect, mode="misheard"))
    others = [command_id for command_id in ids if command_id != spec.id]
    rows.append(_row(phrases[0], app, {"refuse": "disabled"}, enabled=others))
    return rows


def _negative_rows(
    app: str, never: list[CommandSpec], other: list[CommandSpec]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for text in _NONSENSE:
        rows.append(_row(text, app, {"refuse": "not_here"}))
    for text in _ASK:
        rows.append(_row(text, app, {"refuse": "ask"}))
    for text in _DANGER:
        rows.append(_row(text, app, {"refuse": "never"}))
    for spec in never:
        for alias in spec.aliases[:2] or (spec.title,):
            rows.append(_row(alias, app, {"refuse": "never"}))
    for spec in other:
        rows.append(_row(spec.examples[0], app, {"refuse": "other_app", "pointer": spec.apps[0]}))
    return rows


def _other_app_rows(app: str) -> list[CommandSpec]:
    """A handful of unmistakable commands from another app."""
    if app == "radio":
        wanted = ("format.bold", "tools.spell_check_dialog", "navigate.next_heading")
        return [spec for spec in rows_for_app("quill") if spec.id in wanted]
    wanted = ("radio.identify_song", "radio.jump_to_live", "radio.wake_timer")
    return [spec for spec in rows_for_app("radio") if spec.id in wanted]


def build(app: str) -> list[dict[str, object]]:
    rows = rows_for_app(app)
    offered = [spec for spec in rows if spec.offered]
    never = [spec for spec in rows if not spec.offered]
    ids = [spec.id for spec in offered]
    out: list[dict[str, object]] = []
    for spec in offered:
        out.extend(_positive_rows(app, spec, ids))
    out.extend(_negative_rows(app, never, _other_app_rows(app)))
    for index, row in enumerate(out):
        row["set"] = "held_out" if index % 5 == 4 else "train"
    return out


def main() -> int:
    for app in _APPS:
        rows = build(app)
        path = _HERE / f"{app}.jsonl"
        text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        path.write_bytes(text.encode("utf-8"))
        print(f"{path.name}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
