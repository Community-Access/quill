"""Write the dictation page's command reference from the table dictation reads.

``docs/site/dictation.html`` is an authored page: its prose, its keyboard tables
and its troubleshooting are written by hand. One region of it is not. Everything
dictation *listens for* -- 52 punctuation, bracket, symbol and layout phrases and
17 spoken commands -- lives in
:mod:`quill.core.windows_dictation.vocabulary`, and that is also what the
in-app "What can I say?" window and both editors' ``dictation-commands`` guides
render. A hand-copied fourth copy on a public web page is a copy that goes stale
the first time somebody teaches dictation a new phrase, and nobody would notice:
the page would simply be missing a row.

So the region between ``<!-- dictation-vocabulary:start -->`` and
``<!-- dictation-vocabulary:end -->`` is generated, and everything outside those
markers is authored and never touched. This is the same arrangement
``scripts/build_lite_key_table.py`` uses for QUILL Lite's guide.

``tests/unit/docs/test_dictation_page.py`` fails when the region falls behind,
so the build catches it rather than a reader.

Usage::

    python scripts/build_dictation_page.py          # rewrite the region
    python scripts/build_dictation_page.py --check  # fail if it is stale
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from quill.core.windows_dictation.vocabulary import (  # noqa: E402
    COMMAND_HELP,
    DASH_STYLES,
    MARKS,
    SPELLING_ALPHABET,
    Mark,
)
from quill.core.windows_dictation.wake import (  # noqa: E402
    DEFAULT_STOP_PHRASE,
    DEFAULT_WAKE_PHRASE,
)

PAGE = _REPO / "docs" / "site" / "dictation.html"
START = "    <!-- dictation-vocabulary:start -->"
END = "    <!-- dictation-vocabulary:end -->"

#: An English name for everything dictation can write, because the character on
#: its own is not readable.
#:
#: A cell whose entire content is "." is announced as nothing at NVDA's and
#: JAWS's default punctuation level, and as "dot" at a higher one -- so the most
#: important column on the page would be silent for exactly the rows a person
#: looks up. This is the same finding that keeps tick and cross glyphs out of
#: the comparison tables: a bare symbol is announced at one verbosity level and
#: skipped at another, leaving the cell reading as blank.
#:
#: The name is therefore *visible* text rather than a hidden label. Hiding it
#: would help a screen reader and leave a sighted reader squinting at a comma in
#: a wide cell, and it would double-speak for anyone reading at full verbosity.
#: Both halves are in the DOM, so both survive High Contrast, a stylesheet that
#: fails to load, and being copied into a document.
#:
#: :func:`_writes` raises for a mark that is not here, so a phrase added to
#: vocabulary.py cannot reach the page as an unnamed cell.
_NAMES = {
    ".": "a full stop",
    ",": "a comma",
    "?": "a question mark",
    "!": "an exclamation mark",
    ":": "a colon",
    ";": "a semicolon",
    "...": "three dots, an ellipsis",
    '"': "a double quotation mark",
    "'": "a single quotation mark, also the apostrophe",
    "(": "an opening round bracket",
    ")": "a closing round bracket",
    "[": "an opening square bracket",
    "]": "a closing square bracket",
    "{": "an opening curly brace",
    "}": "a closing curly brace",
    "<": "an opening angle bracket, the less-than sign",
    ">": "a closing angle bracket, the greater-than sign",
    "-": "a hyphen",
    "/": "a forward slash",
    "\\": "a backslash",
    "_": "an underscore",
    "@": "an at sign",
    "#": "a hash, the number sign",
    "$": "a dollar sign",
    "%": "a percent sign",
    "&": "an ampersand",
    "*": "an asterisk",
    "+": "a plus sign",
    "=": "an equals sign",
}

#: Where two different phrases write the same character and are not synonyms,
#: so a reader meeting the second row does not take it for a mistake.
_SAME_AS = {"minus sign": 'a hyphen, the same character that "hyphen" writes'}

#: The three that write no character at all, so there is nothing to show beside
#: the words -- the words are the whole answer.
_WORDS_ONLY = {
    "\n": "a line break, ending the line",
    "\n\n": "a blank line, starting a new paragraph",
    "\t": "a tab",
}

#: A one-line answer above each table, so the category is readable before the
#: grid is entered. Keyed by the group name vocabulary.py uses.
_INTROS = {
    "Punctuation": (
        "Say any of these anywhere in a phrase. Spaces go where they belong: none "
        "before a comma, one after a full stop."
    ),
    "Brackets": "Both halves are separate phrases, so you can say one without the other.",
    "Dashes and joining": (
        'What "dash" writes is up to you, in Dictation Settings. This row '
        "shows what it writes until you change it."
    ),
    "Symbols": "The symbols people dictate most often in ordinary prose and in code.",
    "Lines and layout": ("These change where the next words go rather than adding a character."),
    "Correcting": (
        "Each of these works only as a whole phrase, said on its own after a pause, "
        "and only while the phrase it changes is still exactly as dictation wrote it."
    ),
    "Moving the cursor": "Said on their own, after a pause.",
    "Dictation itself": "Said on their own, after a pause.",
}


def _writes(mark: Mark, dash: str = "em") -> str:
    """The "What it writes" cell for *mark*, as HTML: its name, then the character.

    Words first. A cell that opens with the character reads as "period, then
    silence, then full stop" -- the inaudible token comes first and the answer
    arrives after a gap. Leading with the words removes the stumble, and the
    character still follows for anyone who needs to see which one it is (em dash
    against en dash, straight quote against curly).

    Raises for a mark this module has no name for, so a phrase added to
    vocabulary.py fails the build rather than reaching the page as a cell a
    screen reader reads as blank.
    """
    if mark.text == "{dash}":
        shown = DASH_STYLES[dash][1].strip()
        return (
            "a dash, as chosen in Dictation Settings "
            f'<code class="glyph">{html.escape(shown)}</code>'
        )
    if mark.text in _WORDS_ONLY:
        return _WORDS_ONLY[mark.text]
    if mark.text not in _NAMES:
        raise SystemExit(
            f"No English name for the character dictation writes for "
            f"{' '.join(mark.phrase)!r} ({mark.text!r}). Add it to _NAMES in "
            f"{Path(__file__).name}: a cell holding only a symbol is announced at one "
            f"screen-reader verbosity level and skipped at another."
        )
    name = _SAME_AS.get(" ".join(mark.phrase)) or _NAMES[mark.text]
    return f'{name} <code class="glyph">{html.escape(mark.text)}</code>'


def _grouped_marks() -> dict[str, list[Mark]]:
    groups: dict[str, list[Mark]] = {}
    for mark in MARKS:
        groups.setdefault(mark.group, []).append(mark)
    return groups


def _grouped_commands() -> dict[str, list[tuple[str, str]]]:
    groups: dict[str, list[tuple[str, str]]] = {}
    for entry in COMMAND_HELP:
        said = " or ".join(entry.phrases)
        groups.setdefault(entry.group, []).append((said, entry.description))
    return groups


def _slug(text: str) -> str:
    return "v-" + "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def _table(
    *, anchor: str, heading: str, caption: str, left: str, right: str, rows: list[tuple[str, str]]
) -> list[str]:
    """One accessible table, in the shape the site's other tables use.

    Every value is a word or a character in the DOM -- never a symbol standing in
    for one -- and the first cell of each row is a ``th scope="row"`` so a reader
    moving across a row is told what it is answering. See docs/site/compare.html
    for the reasoning; the CSS is shared.
    """
    out = [
        f'      <h4 id="{anchor}" tabindex="-1" class="focus-target">{heading}</h4>',
        f'      <p class="group-verdict">{caption}</p>',
        '      <div class="cmp-scroll">',
        '        <table class="cmp cmp-2">',
        f"          <caption>{heading}: what to say, and what dictation writes.</caption>",
        "          <thead>",
        "            <tr>",
        f'              <th scope="col">{left}</th>',
        f'              <th scope="col">{right}</th>',
        "            </tr>",
        "          </thead>",
        "          <tbody>",
    ]
    for said, does in rows:
        out.append(f'            <tr><th scope="row">{said}</th><td>{does}</td></tr>')
    out += ["          </tbody>", "        </table>", "      </div>"]
    return out


def rendered() -> str:
    """The generated region, without its markers."""
    lines: list[str] = []
    e = html.escape

    marks = _grouped_marks()
    commands = _grouped_commands()

    # The text below is plain ASCII on purpose: straight quotes and commas, not
    # curly quotes and dashes. The one exception is a character dictation really
    # writes (the em dash), which rendered() emits as a numeric reference.
    lines.append(
        f"      <p>There are {len(MARKS)} punctuation marks and layout phrases, and "
        f"{len(COMMAND_HELP)} spoken commands. This list comes straight from "
        "dictation itself, so it is always complete. While you are dictating, say "
        '"what can I say" to hear the same list in a window.</p>'
    )

    # Each group's table is an h4 under one of these two h3s, so heading
    # navigation shows "what to say" and "commands" as the two branches they are.
    lines.append(
        '      <h3 id="v-marks" tabindex="-1" class="focus-target">'
        "What you can say, and what it writes</h3>"
    )
    lines.append(
        "      <p>Punctuation, brackets, symbols and layout. Each table lists the words "
        "to say and what appears in your document.</p>"
    )
    for group, group_marks in marks.items():
        lines += _table(
            anchor=_slug(group),
            heading=e(group),
            caption=e(_INTROS.get(group, "")),
            left="Say",
            right="What it writes",
            # _writes already returns HTML (a code element plus words), so it is
            # not escaped again here; the phrase, which is plain data, is.
            rows=[(e(" ".join(mark.phrase)), _writes(mark)) for mark in group_marks],
        )

    lines.append(
        '      <h3 id="v-commands" tabindex="-1" class="focus-target">Commands dictation obeys</h3>'
    )
    lines.append(
        "      <p>A command works only when it is the whole phrase, said on its own "
        'after a pause. "Delete that line of text" in the middle of a longer sentence '
        'is just words, and is written as words. Say "literal" before any '
        "phrase on this page to write it out instead of acting on it.</p>"
    )
    for group, entries in commands.items():
        lines += _table(
            anchor=_slug("command " + group),
            heading=e(group),
            caption=e(_INTROS.get(group, "")),
            left="Say, on its own",
            right="What happens",
            rows=[(e(said), e(does)) for said, does in entries],
        )

    digits = ", ".join(k for k, v in SPELLING_ALPHABET.items() if v.isdigit())
    lines += [
        '      <h3 id="v-spelling" tabindex="-1" class="focus-target">Spelling a word out</h3>',
        "      <ul>",
        '        <li>Say "start spelling", then letters. Everything you say is '
        'written as letters until you say "stop spelling".</li>',
        '        <li>Say "capital" before a letter for a capital, and "space" for a space.</li>',
        '        <li>Letter names work ("bee", "see"), but the '
        "phonetic alphabet works much better: alpha, bravo, charlie, delta, echo, "
        "foxtrot, golf, hotel, india, juliet, kilo, lima, mike, november, oscar, papa, "
        "quebec, romeo, sierra, tango, uniform, victor, whiskey, x-ray, yankee, zulu.</li>",
        f"        <li>Numbers are written as digits: {e(digits)}.</li>",
        "      </ul>",
        '      <h3 id="v-by-voice" tabindex="-1" class="focus-target">Starting and stopping'
        " without the keyboard</h3>",
        "      <ul>",
        "        <li>With the wake phrase switched on in Dictation Settings, say "
        f'"{e(DEFAULT_WAKE_PHRASE)}" to start dictation without touching a key. '
        "Anything you say after it in the same breath is written.</li>",
        f'        <li>Say "{e(DEFAULT_STOP_PHRASE)}" on its own, after a pause, '
        "to stop. With the wake phrase on, stopping goes back to waiting for the wake "
        "phrase, so you need never touch the keyboard at all.</li>",
        "        <li>You choose both phrases yourself, and each needs at least two words, "
        "so ordinary talk cannot start or stop dictation by accident.</li>",
        "      </ul>",
    ]
    # Keep the region plain ASCII: a character dictation writes that is not
    # ASCII (the em dash in the "dash" row) becomes a numeric reference, which
    # still renders as the real character.
    return "\n".join(lines).encode("ascii", "xmlcharrefreplace").decode("ascii")


def _split(text: str) -> tuple[str, str, str]:
    nl = "\r\n" if "\r\n" in text else "\n"
    start = text.index(START)
    end = text.index(END)
    return text[: start + len(START) + len(nl)], text[end:], nl


def current() -> str:
    text = PAGE.read_text(encoding="utf-8")
    head, _, nl = _split(text)
    return text[len(head) : text.index(END)].rstrip(nl)


def write() -> bool:
    text = PAGE.read_text(encoding="utf-8")
    head, tail, nl = _split(text)
    body = rendered().replace("\n", nl)
    new = head + body + nl + tail
    if new == text:
        return False
    PAGE.write_text(new, encoding="utf-8", newline="")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if not PAGE.is_file():
        print(f"{PAGE} does not exist.")
        return 1
    if args.check:
        if current().replace("\r\n", "\n") != rendered():
            print(f"{PAGE} vocabulary region is out of date. Run: python {Path(__file__).name}")
            return 1
        return 0
    print("rewrote the vocabulary region" if write() else "already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
