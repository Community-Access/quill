"""Shared reader for GATE-DOCMENU: what a changelog or guide promises about menus.

Jeff, 2026-10-16: "many commands mentioned are not in the menus like search in
files, search in open documents ... I launched from running from source and did
not find them." The chord gates (``test_documentation_chords``, GATE-DOCKEY) ask
whether a key a document teaches is *bound*. Neither asks the question a person
with a changelog in one hand and the running app in the other actually asks:
**is it in the menu where the document says it is, on the menu bar a new user
gets?** A command can be bound, tested and documented and still be hidden by a
feature profile that starts it off, or sit in a submenu whose name gives no hint
of it.

This module is the reader half, shared by one small test per app
(``test_documented_menus_<app>.py``). It knows nothing about any app: each test
hands it the app's menu as a list of :class:`MenuItem` (built in memory, with the
profile a new install gets) and the documents to read, and gets back the claims
those documents make that the menu does not keep.

Three kinds of claim, each in the shapes the documents actually use:

* **A menu path** -- ``Edit > Matches > Search in Files`` or ``Tools ▸ Spelling``,
  in bold, plain or backticks. Only paths whose first segment is one of the app's
  real top-level menus are read: that anchor is what keeps prose such as
  "louder > quieter" out of the claim list without a hand-written exclusion.
  Every segment but the last must match a menu exactly; the last may run on into
  the sentence ("Edit > Go To... opens a window"), so it matches when a real item
  is a whole-word prefix of it.
* **A command name beside a chord** -- ``**Search in Files** (**Ctrl+Alt+Shift+F**)``
  or a table row ``| **Ctrl+Shift+R** | Replace Across Files |``. When the name is
  a menu item the chord must be that item's; when no menu item carries the chord
  and no menu item has the name either, the document is promising a command the
  menus do not show. Alt plus a single letter is skipped: in these documents that
  is a dialog's access key, not a command.
* **An Alt path** -- ``Alt+Q, then W`` -- checked by Radio's own gate in
  ``tests/unit/ui/test_menu_accelerators.py``, which this module does not repeat.

Every finding can be allowlisted per app with a written reason; an allowlist
entry that no longer matches anything fails too, so the list can only shrink
honestly.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

__all__ = [
    "ROOT",
    "MenuItem",
    "OptIn",
    "chord_claims",
    "check_documents",
    "items_from_wx_menu_bar",
    "normalise",
    "path_claims",
]


@dataclass(frozen=True)
class MenuItem:
    """One row of a menu bar: its path of plain titles and the key it shows."""

    path: tuple[str, ...]
    key: str = ""


#: A route written into the title: "(Alt+E, K)", "(QUILL Key + M)", or the bare
#: appended access letter "(&Q)" the route pass gives a title without that letter.
_ROUTE_SUFFIX = re.compile(r"\s*\((?:(?:Alt|Ctrl|Shift|QUILL Key|Cmd)[^()]*|&\w)\)\s*$")
_TAB = chr(9)


def normalise(title: str) -> str:
    """A title as a document would write it: no ``&``, no ellipsis, no route."""
    title = title.split(_TAB, 1)[0]
    while (stripped := _ROUTE_SUFFIX.sub("", title)) != title:
        title = stripped  # "Copy to Slot 1 (QUILL Key + Shift+1) (Alt+E, O, &Q)"
    # Every ampersand goes, the literal one too: a menu writes "Q&&A" and a
    # document "Q&A", and either way the reader hears the same title.
    title = title.replace("&", "")
    title = title.replace("…", "...").strip()
    while title.endswith((".", "?")):
        title = title[:-1].rstrip()  # "What Can I Do Here?..." as "What can I do here"
    title = title.strip("*`\"'“”‘’ ")
    return re.sub(r"\s+", " ", title).lower()


def chord_identity(key: str) -> str:
    """A chord compared without regard to spelling or modifier order."""
    parts = [p.strip().lower() for p in key.replace(" ", "").split("+") if p.strip()]
    if not parts:
        return ""
    *mods, last = parts
    aliases = {
        "control": "ctrl",
        "option": "alt",
        "return": "enter",
        "esc": "escape",
        # Spelled out in prose, a character on the menu row.
        "period": ".",
        "comma": ",",
        "semicolon": ";",
        "slash": "/",
        "minus": "-",
        "equals": "=",
    }
    mods = sorted(aliases.get(m, m) for m in mods)
    return "+".join([*mods, aliases.get(last, last)])


def items_from_wx_menu_bar(bar: object) -> list[MenuItem]:
    """Every item on a real ``wx.MenuBar``, submenu titles included as items."""
    out: list[MenuItem] = []

    def walk(menu: object, path: tuple[str, ...]) -> None:
        for item in menu.GetMenuItems():  # type: ignore[attr-defined]
            if item.IsSeparator():
                continue
            label = item.GetItemLabel()
            title, _, key = label.partition(_TAB)
            here = (*path, title)
            out.append(MenuItem(here, key.strip()))
            sub = item.GetSubMenu()
            if sub is not None:
                walk(sub, here)

    for index in range(bar.GetMenuCount()):  # type: ignore[attr-defined]
        title = bar.GetMenuLabel(index)  # type: ignore[attr-defined]
        out.append(MenuItem((title,)))
        walk(bar.GetMenu(index), (title,))  # type: ignore[attr-defined]
    return out


# --------------------------------------------------------------------- paths

#: Small words that may sit inside a title ("Find in Open Documents") but never
#: start a new one; a lower-case word that is not one of these ends the segment.
_JOINERS = frozenset(
    "a an and as at by for from in into of on or the to with per your my this".split()
)
_ARROW = re.compile(r"\s+(?:>|▸|→)\s+")
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’.,&+/:()\-…]*")


def _segment_from(text: str) -> str:
    """The title-ish run at the start of *text*: words until prose begins."""
    words: list[str] = []
    for raw in text.split():
        word = raw.strip('*`_"“”')
        if not word or word.startswith("("):
            break
        ellipsis = word.rstrip(",;:!?)\"”'’").endswith(("...", "…"))
        if word.endswith(("....", "….")):
            words.append(word.rstrip(".…") + "...")
            break  # the title's ellipsis, then the sentence's full stop
        core = word.rstrip(".,;:!?)\"”'’…")
        if not core or not core[:1].isalnum():
            break
        if core[:1].islower() and core.lower() not in _JOINERS:
            break
        words.append(core + ("..." if ellipsis else ""))
        if ellipsis:
            break  # a title's ellipsis is its last character: "Recordings... and"
        # Punctuation after a word ends the title: "Tools > Dictation)" and
        # "Edit > Lines, then" both stop there. A full stop does too, unless it
        # is the ellipsis that belongs to the title itself.
        if word != core and not (ellipsis and word.endswith(("...", "…"))):
            break
    while words and words[-1].lower() in _JOINERS:
        words.pop()
    return " ".join(words)


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Lines, with a path a hard wrap split put back together.

    "Station >" at the end of one line and "Stop" at the start of the next is
    one claim, and reading line by line never saw it -- which is how a guide
    taught Station > Stop, a path that has never existed, past the first run
    of this gate. Numbered by the line the path starts on.
    """
    raw = text.splitlines()
    out: list[tuple[int, str]] = []
    index = 0
    while index < len(raw):
        number, line = index + 1, raw[index]
        while line.rstrip().endswith((">", "▸", "→")) and index + 1 < len(raw):
            following = raw[index + 1].strip()
            if not following or following.startswith((">", "#", "|", "-", "*")):
                break
            index += 1
            line = line.rstrip() + " " + following
        out.append((number, line))
        index += 1
    return out


def path_claims(text: str, top_level: Iterable[str]) -> list[tuple[int, tuple[str, ...]]]:
    """Every ``(line, path)`` *text* writes that starts at one of *top_level*."""
    tops = {normalise(t) for t in top_level}
    found: list[tuple[int, tuple[str, ...]]] = []
    for number, line in _logical_lines(text):
        clean = line.replace("**", "").replace("`", "")
        pieces = _ARROW.split(clean)
        if len(pieces) < 2:
            continue
        index = 0
        while index < len(pieces) - 1:
            # The first segment is whatever title ends the text before the arrow.
            before = pieces[index].split()
            first = ""
            for size in range(min(4, len(before)), 0, -1):
                candidate = normalise(" ".join(before[-size:]).lstrip("(\"'“"))
                # "the Weather menu > Quick Weather" names the menu as a menu.
                if candidate.endswith(" menu") and candidate[: -len(" menu")] in tops:
                    candidate = candidate[: -len(" menu")]
                if candidate in tops:
                    first = candidate
                    break
            if not first:
                index += 1
                continue
            path = [first]
            cursor = index + 1
            while cursor < len(pieces):
                segment = _segment_from(pieces[cursor])
                if not segment:
                    break
                # "Edit > Clipboard and Tools > Spelling" is two paths: a joiner
                # followed by a top-level menu starts the next one.
                words = segment.split()
                cut = next(
                    (
                        at
                        for at in range(1, len(words) - 1)
                        if words[at].lower() in {"and", "or"}
                        and normalise(" ".join(words[at + 1 :])) in tops
                    ),
                    0,
                )
                if cut:
                    path.append(normalise(" ".join(words[:cut])))
                    break
                path.append(normalise(segment))
                # The segment continues the path only if the whole piece was it.
                if normalise(pieces[cursor]) != normalise(segment):
                    break
                cursor += 1
            if len(path) > 1:
                found.append((number, tuple(path)))
            index = max(cursor, index + 1)
    return found


def _resolves(path: tuple[str, ...], items: list[MenuItem]) -> bool:
    known = {tuple(normalise(p) for p in item.path) for item in items}
    if path in known:
        return True
    head, last = path[:-1], path[-1]
    for candidate in known:
        if len(candidate) != len(path) or candidate[:-1] != head:
            continue
        # The sentence ran on past the title ("Go To opens"), or the document
        # wrote the title short ("Help > About" for "About QUILL Lite").
        if last.startswith(candidate[-1] + " ") or candidate[-1].startswith(last + " "):
            return True
    return False


# -------------------------------------------------------------------- chords

_CHORD = r"(?:Ctrl|Alt|Shift|Win)\+[A-Za-z0-9+.,;'\[\]/\\=<>\-]{1,24}|F\d{1,2}"
#: A command name, which may carry its menu path in front of it ("Weather >
#: Start Weather Monitoring"); the path is split off before the lookup.
_NAME = r"[A-Z][A-Za-z0-9 .&'’/>▸-]{1,80}?"
#: The bold name and the whole parenthesis after it. Every key in the
#: parenthesis's first clause is read, not only the first: "(Alt+Y, or Ctrl+P)"
#: is a dialog letter and then the command's key, and the second is the claim.
_NAME_THEN_PAREN = re.compile(rf"\*\*({_NAME})(?:\.\.\.|…)?\*\*\s*\(([^()]{{1,120}})\)")
_CHORD_RE = re.compile(_CHORD)
_TABLE_ROW = re.compile(rf"^\|\s*\*\*({_CHORD})\*\*\s*\|\s*([^|]+?)\s*\|")


def _tidy_chord(chord: str) -> str:
    while len(chord) > 2 and chord[-1] in ".,:;)" and chord[-2] != "+":
        chord = chord[:-1]
    return chord


def chord_claims(text: str) -> list[tuple[int, str, str]]:
    """Every ``(line, name, chord)`` *text* pairs, in the two common shapes."""
    found: list[tuple[int, str, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in _NAME_THEN_PAREN.finditer(line):
            # The first clause only: "(Ctrl+Shift+F10; QUILL Lite: Ctrl+Alt+Shift+F8)"
            # names a second product's key after the semicolon.
            clause = re.split(r"[;:](?:\s|$)|\bin QUILL\b|\bQUILL Lite\b", match.group(2))[0]
            clause = clause.replace("*", "").replace("`", "")
            if not re.match(r"\s*(?:" + _CHORD + ")", clause):
                continue  # the parenthesis does not start with a key: prose
            chords = _CHORD_RE.findall(clause)
            # "Skip Back and Skip Forward (Ctrl+Left, Ctrl+Right)" pairs two
            # names with two keys; which goes with which is prose, not a claim.
            if len(chords) > 1 and (
                re.search(r"\band\b|/", match.group(1)) or re.search(r"\s/\s|\band\b", clause)
            ):
                continue
            if chords:
                found.append((number, match.group(1), "|".join(_tidy_chord(c) for c in chords)))
        if (row := _TABLE_ROW.match(line)) is not None:
            name = row.group(2).replace("*", "").split(":")[0].strip()
            found.append((number, name, _tidy_chord(row.group(1))))
    return found


def _is_dialog_access_key(chord: str) -> bool:
    return bool(re.fullmatch(r"Alt\+[A-Za-z0-9]", chord))


# --------------------------------------------------------------------- check


@dataclass(frozen=True)
class OptIn:
    """A menu bar as it is once a documented switch is on, and how to say so."""

    items: list[MenuItem]
    #: Any one of these, in the claim's section, counts as telling the reader.
    switch_phrases: tuple[str, ...]


#: Chapters, not subsections: a guide says once, at the top of its AI chapter,
#: that the long AI menu is behind a checkbox, and every section under that
#: chapter is covered by that sentence. Smaller than a chapter would demand the
#: same sentence thirty times; larger would let a sentence in one chapter vouch
#: for a claim in another.
_HEADING = re.compile(r"^#{1,2}\s")


def _sections(text: str) -> list[tuple[int, str]]:
    """``(first line, lower-cased text)`` for each heading-delimited section."""
    out: list[tuple[int, str]] = []
    start, chunk = 1, []
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced  # a "## heading" in a code sample is not a chapter
        if not fenced and _HEADING.match(line) and chunk:
            out.append((start, re.sub(r"\s+", " ", " ".join(chunk)).lower()))
            start, chunk = number, []
        chunk.append(line)
    out.append((start, re.sub(r"\s+", " ", " ".join(chunk)).lower()))
    return out


def _opted_in(number, sections, opt_ins, resolves) -> bool:  # type: ignore[no-untyped-def]
    section = ""
    for start, body in sections:
        if start > number:
            break
        section = body
    for option in opt_ins:
        if resolves(option) and any(p.lower() in section for p in option.switch_phrases):
            return True
    return False


def check_documents(
    documents: Iterable[Path],
    items: list[MenuItem],
    allow: Mapping[str, str],
    *,
    extra_keys: Mapping[str, str] | None = None,
    opt_in: Iterable[OptIn] = (),
) -> tuple[list[str], set[str]]:
    """Findings for *documents* against *items*, and the allowlist keys used.

    *allow* maps a finding key to the reason it is allowed: ``"path:edit >
    foo"`` for a path, ``"key:foo"`` for a command named beside a chord. A
    finding whose key is allowed is not reported; the caller asserts the used
    set equals the allowlist, so a stale entry fails as well.

    *extra_keys* maps chord identity to a command name for keys an app binds
    without a menu row on purpose (a global hotkey, a list-only key); naming one
    of those beside its own chord is not a finding.

    *opt_in* is what a new user does **not** see until they turn something on:
    each :class:`OptIn` is the menu bar with that switch on and the words a
    document must use to say so. A claim that only that bar keeps passes when
    the same section of the document (between two headings) names the switch --
    "Customize Features", "Show advanced AI features" -- and is a finding
    otherwise, because a guide that teaches a hidden command without saying how
    to unhide it is the exact report this gate was written for.
    """
    opt_ins = list(opt_in)
    tops = [item.path[0] for item in items if len(item.path) == 1]
    by_name: dict[str, set[str]] = {}
    by_key: dict[str, str] = {}
    for item in items:
        if len(item.path) < 2:
            continue
        name = normalise(item.path[-1])
        by_name.setdefault(name, set())
        if item.key:
            identity = chord_identity(item.key)
            by_name[name].add(identity)
            by_key.setdefault(identity, name)
    extra = {chord_identity(k): normalise(v) for k, v in (extra_keys or {}).items()}
    findings: list[str] = []
    used: set[str] = set()
    for document in documents:
        text = document.read_text(encoding="utf-8")
        sections = _sections(text)
        for number, path in path_claims(text, tops):
            if _resolves(path, items):
                continue
            if _opted_in(number, sections, opt_ins, lambda o, p=path: _resolves(p, o.items)):
                continue
            key = "path:" + " > ".join(path)
            if key in allow:
                used.add(key)
                continue
            findings.append(f"{document.name}:{number}: no menu path {' > '.join(path)!r}")
        for number, name, chord in chord_claims(text):
            if _is_dialog_access_key(chord):
                continue
            leaf = normalise(re.split(r"\s*(?:>|▸)\s*", name)[-1])
            identities = {chord_identity(c) for c in chord.split("|")}
            identity = next(iter(identities))
            if leaf in by_name:
                keys = by_name[leaf]
                if (
                    keys
                    and not (identities & keys)
                    and all(extra.get(i) != leaf for i in identities)
                ):
                    key = f"key:{leaf}"
                    if key in allow:
                        used.add(key)
                        continue
                    findings.append(
                        f"{document.name}:{number}: {name!r} is written beside {chord}, "
                        f"but its menu row shows another key"
                    )
                continue
            if any(i in by_key or i in extra for i in identities):
                continue  # a reworded name for a key the menus do show
            if _opted_in(
                number,
                sections,
                opt_ins,
                lambda o, n=leaf, i=identity: any(
                    normalise(it.path[-1]) == n or (it.key and chord_identity(it.key) == i)
                    for it in o.items
                    if len(it.path) > 1
                ),
            ):
                continue
            key = f"key:{leaf}"
            if key in allow:
                used.add(key)
                continue
            findings.append(
                f"{document.name}:{number}: {name!r} on {chord} is in no menu a new install shows"
            )
    return findings, used
