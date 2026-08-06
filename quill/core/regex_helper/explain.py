"""Deterministic plain-language explanations of regular expressions.

A sighted user can eyeball ``^\\d+(?:\\.\\d{2})?`` and pick it apart visually;
a screen-reader user hears it as an undifferentiated stream of punctuation.
This module walks Python ``re`` syntax and produces a numbered reading in
ordinary sentences -- "At the start of a line.", "One or more digits.",
"Optionally: a period followed by exactly two digits." -- so the pattern can be
reviewed by ear, one step at a time, with no regex jargon.

Everything here is deterministic and offline: no AI, no network, no wx. Invalid
patterns come back as a plain-language diagnosis that names the character
position, because "missing ), unterminated subpattern at position 4" is not a
sentence anyone should have to hear.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.error_codes import CodedError

__all__ = ["ExplainResult", "explain_pattern"]


@dataclass(frozen=True)
class ExplainResult:
    """The outcome of explaining a pattern.

    ``steps`` is a numbered plain-language reading when ``ok`` is true.
    When ``ok`` is false, ``error`` carries a spoken-friendly diagnosis that
    names the character position, and ``error_position`` holds the zero-based
    offset from :class:`re.error` when the compiler reported one.
    """

    ok: bool
    steps: tuple[str, ...]
    error: str
    error_position: int | None


# -- friendly names ------------------------------------------------------------

#: Spoken names for punctuation, used for escaped characters and for single
#: characters inside classes and quantified literals. A screen reader may skip
#: or mangle bare punctuation, so every character gets a pronounceable name.
_CHAR_NAMES: dict[str, str] = {
    ".": "a period",
    ",": "a comma",
    "!": "an exclamation mark",
    "?": "a question mark",
    "-": "a hyphen",
    "_": "an underscore",
    "/": "a slash",
    "\\": "a backslash",
    "(": "an open parenthesis",
    ")": "a close parenthesis",
    "[": "an open bracket",
    "]": "a close bracket",
    "{": "an open brace",
    "}": "a close brace",
    "*": "an asterisk",
    "+": "a plus sign",
    "$": "a dollar sign",
    "^": "a caret",
    "|": "a vertical bar",
    '"': "a double quotation mark",
    "'": "an apostrophe",
    ":": "a colon",
    ";": "a semicolon",
    "@": "an at sign",
    "#": "a hash sign",
    "&": "an ampersand",
    "%": "a percent sign",
    "=": "an equals sign",
    "<": "a less-than sign",
    ">": "a greater-than sign",
    "~": "a tilde",
    "`": "a backtick",
    " ": "a space",
    "\n": "a newline character",
    "\t": "a tab character",
    "\r": "a carriage-return character",
}

#: Class-shorthand escapes: singular and plural spoken forms. The plural feeds
#: quantifier phrasing ("one or more digits" rather than "one or more
#: repetitions of: a digit").
_SHORTHAND: dict[str, tuple[str, str]] = {
    "d": ("a digit", "digits"),
    "D": ("a character that is not a digit", "characters that are not digits"),
    "w": (
        "a word character (a letter, digit, or underscore)",
        "word characters (letters, digits, or underscores)",
    ),
    "W": ("a character that is not a word character", "characters that are not word characters"),
    "s": ("a whitespace character", "whitespace characters"),
    "S": ("a character that is not whitespace", "characters that are not whitespace"),
}

#: Zero-width position escapes and anchors.
_ANCHORS: dict[str, str] = {
    "^": "at the start of a line",
    "$": "at the end of a line",
    "A": "at the very start of the text",
    "Z": "at the very end of the text",
    "b": "at a word boundary (the edge of a word)",
    "B": "at a position inside a word, not at its edge",
}

#: Inline-flag letters, phrased as what they change for the listener.
_FLAG_MEANINGS: dict[str, str] = {
    "i": "capital and small letters are treated the same",
    "m": "the start and end anchors match at each line, not just the whole text",
    "s": "the dot also matches newline characters",
    "x": "spaces and comments inside the pattern are ignored",
    "a": "shorthand classes match ASCII characters only",
    "u": "the pattern uses full Unicode matching",
    "L": "matching follows the current locale",
}

_NUMBER_WORDS: dict[int, str] = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}


def _num(n: int) -> str:
    """Spell small counts out; digits read fine for larger ones."""
    return _NUMBER_WORDS.get(n, str(n))


def _char_name(ch: str) -> str:
    return _CHAR_NAMES.get(ch, f"the character '{ch}'")


# -- phrase model --------------------------------------------------------------


@dataclass(frozen=True)
class _Phrase:
    """One atom of the pattern, rendered as a noun phrase.

    ``plural`` enables natural quantifier phrasing; ``lit`` carries the raw
    character when the atom is a plain, unquantified literal so adjacent
    literals can be merged into one "the text '...'" step.
    """

    singular: str
    plural: str | None = None
    lit: str | None = None


class _Unexplainable(CodedError):
    """Internal bail-out: the walker met syntax it cannot describe.

    Never escapes this module -- ``explain_pattern`` catches it and falls back
    to an honest generic step -- but GATE-EC codes every exception regardless.
    """

    code = "QUILL-CORE-REGEXHELP-UNEXPLAINABLE"


# -- parser --------------------------------------------------------------------


class _Parser:
    """Recursive-descent walker over an already-validated pattern.

    The pattern has passed ``re.compile`` before this runs, so the walker can
    focus on phrasing rather than on error recovery; anything it does not
    recognise raises :class:`_Unexplainable` and the caller degrades to a
    generic-but-honest description.
    """

    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self.pos = 0
        self.group_number = 0

    # -- low-level helpers

    def _peek(self) -> str:
        return self.pattern[self.pos] if self.pos < len(self.pattern) else ""

    def _take(self) -> str:
        ch = self.pattern[self.pos]
        self.pos += 1
        return ch

    # -- alternation and sequences

    def parse_alternation(self) -> list[list[_Phrase]]:
        alternatives = [self.parse_sequence()]
        while self._peek() == "|":
            self._take()
            alternatives.append(self.parse_sequence())
        return alternatives

    def parse_sequence(self) -> list[_Phrase]:
        items: list[_Phrase] = []
        while self.pos < len(self.pattern) and self._peek() not in "|)":
            items.append(self._parse_quantified())
        return items

    def _parse_quantified(self) -> _Phrase:
        atom = self._parse_atom()
        return self._apply_quantifier(atom)

    # -- atoms

    def _parse_atom(self) -> _Phrase:
        ch = self._take()
        if ch == ".":
            return _Phrase("any character", "characters of any kind")
        if ch == "^":
            return _Phrase(_ANCHORS["^"])
        if ch == "$":
            return _Phrase(_ANCHORS["$"])
        if ch == "\\":
            return self._parse_escape()
        if ch == "[":
            return self._parse_class()
        if ch == "(":
            return self._parse_group()
        return _Phrase(_char_name(ch), plural=f"'{ch}' characters", lit=ch)

    def _parse_escape(self) -> _Phrase:
        ch = self._take()
        if ch in _SHORTHAND:
            singular, plural = _SHORTHAND[ch]
            return _Phrase(singular, plural)
        if ch in ("A", "Z", "b", "B"):
            return _Phrase(_ANCHORS[ch])
        if ch == "n":
            return _Phrase("a newline character", "newline characters")
        if ch == "t":
            return _Phrase("a tab character", "tab characters")
        if ch == "r":
            return _Phrase("a carriage-return character", "carriage-return characters")
        if ch == "f":
            return _Phrase("a form-feed character")
        if ch == "v":
            return _Phrase("a vertical-tab character")
        if ch.isdigit():
            return _Phrase(f"the same text as group {ch} matched, again")
        if ch == "x" and self.pos + 1 < len(self.pattern):
            code = self.pattern[self.pos : self.pos + 2]
            self.pos += 2
            return _Phrase(f"the character with code {code} (hexadecimal)")
        # Escaped punctuation or any other single character.
        return _Phrase(_char_name(ch))

    def _parse_class(self) -> _Phrase:
        negated = False
        if self._peek() == "^":
            self._take()
            negated = True
        parts: list[str] = []
        first = True
        while True:
            if self.pos >= len(self.pattern):
                raise _Unexplainable("unclosed class reached the walker")
            ch = self._take()
            if ch == "]" and not first:
                break
            first = False
            if ch == "\\":
                esc = self._take()
                if esc in _SHORTHAND:
                    parts.append(_SHORTHAND[esc][0])
                else:
                    parts.append(_char_name(esc))
                continue
            # A range like a-z (a hyphen not at the end of the class).
            if self._peek() == "-" and self.pos + 1 < len(self.pattern):
                nxt = self.pattern[self.pos + 1]
                if nxt != "]":
                    self._take()  # the hyphen
                    end = self._take()
                    if end == "\\":
                        end = self._take()
                    parts.append(f"'{ch}' through '{end}'")
                    continue
            parts.append(_char_name(ch) if ch in _CHAR_NAMES else f"'{ch}'")
        listing = _join_or(parts)
        if negated:
            return _Phrase(
                f"one character that is not any of: {listing}",
                f"characters that are not any of: {listing}",
            )
        return _Phrase(
            f"one character that is any of: {listing}",
            f"characters that are any of: {listing}",
        )

    # -- groups and constructs starting with "("

    def _parse_group(self) -> _Phrase:
        rest = self.pattern[self.pos :]
        if rest.startswith("?"):
            return self._parse_special_group(rest)
        self.group_number += 1
        number = self.group_number
        inner = self._render_alternatives(self.parse_alternation())
        self._expect_close()
        return _Phrase(f"capture group {number}, containing {inner}")

    def _parse_special_group(self, rest: str) -> _Phrase:
        # Whole-pattern inline flags: (?imsx) with no colon.
        flags = re.match(r"\?([aiLmsux]+)\)", rest)
        if flags:
            self.pos += flags.end()
            meanings = [_FLAG_MEANINGS[letter] for letter in flags.group(1)]
            return _Phrase(f"a setting for the whole pattern: {_join_and(meanings)}")
        named = re.match(r"\?P<([^>]+)>", rest)
        if named:
            self.pos += named.end()
            inner = self._render_alternatives(self.parse_alternation())
            self._expect_close()
            return _Phrase(f"a group named '{named.group(1)}', capturing {inner}")
        backref = re.match(r"\?P=([^)]+)\)", rest)
        if backref:
            self.pos += backref.end()
            name = backref.group(1)
            return _Phrase(
                f"an advanced construct: (?P={name}), "
                f"matching the same text as group '{name}' matched"
            )
        for prefix, template in (
            ("?:", "{inner}"),
            ("?=", "a check that what comes next is {inner} (looked at, not consumed)"),
            ("?!", "a check that what comes next is not {inner}"),
            ("?<=", "a check that what comes just before this point is {inner}"),
            ("?<!", "a check that what comes just before this point is not {inner}"),
        ):
            if rest.startswith(prefix):
                self.pos += len(prefix)
                inner = self._render_alternatives(self.parse_alternation())
                self._expect_close()
                return _Phrase(template.format(inner=inner))
        # Comments, conditionals, atomic groups, scoped flags: swallow the whole
        # balanced construct and describe it honestly rather than guessing.
        literal = self._consume_balanced()
        return _Phrase(f"an advanced regular-expression construct: '({literal})'")

    def _expect_close(self) -> None:
        if self._peek() != ")":
            raise _Unexplainable("group did not end where expected")
        self._take()

    def _consume_balanced(self) -> str:
        """Swallow up to the matching close-parenthesis, honouring escapes."""
        start = self.pos
        depth = 1
        while self.pos < len(self.pattern):
            ch = self._take()
            if ch == "\\" and self.pos < len(self.pattern):
                self._take()
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return self.pattern[start : self.pos - 1]
        raise _Unexplainable("unbalanced advanced construct")

    # -- quantifiers

    def _apply_quantifier(self, atom: _Phrase) -> _Phrase:
        ch = self._peek()
        phrase: str | None = None
        if ch == "?":
            self._take()
            phrase = f"optionally: {atom.singular}"
        elif ch == "+":
            self._take()
            phrase = (
                f"one or more {atom.plural}"
                if atom.plural
                else f"one or more repetitions of: {atom.singular}"
            )
        elif ch == "*":
            self._take()
            phrase = (
                f"zero or more {atom.plural}"
                if atom.plural
                else f"zero or more repetitions of: {atom.singular}"
            )
        elif ch == "{":
            counted = self._parse_counted(atom)
            if counted is None:
                return atom
            phrase = counted
        if phrase is None:
            return atom
        suffix = self._peek()
        if suffix == "?":
            self._take()
            phrase += ", matching as few as possible"
        elif suffix == "+":
            self._take()
            phrase += ", never giving back what it matched (possessive)"
        return _Phrase(phrase)

    def _parse_counted(self, atom: _Phrase) -> str | None:
        """Handle ``{m}``, ``{m,}``, ``{m,n}``; a bare brace is a literal."""
        spec = re.match(r"\{(\d*)(,?)(\d*)\}", self.pattern[self.pos :])
        if not spec or (not spec.group(1) and not spec.group(3)):
            return None
        self.pos += spec.end()
        low = int(spec.group(1)) if spec.group(1) else 0
        plural = atom.plural or f"repetitions of: {atom.singular}"
        if not spec.group(2):
            if low == 1:
                return f"exactly one of: {atom.singular}"
            return f"exactly {_num(low)} {plural}"
        if not spec.group(3):
            return f"{_num(low)} or more {plural}"
        high = int(spec.group(3))
        return f"between {_num(low)} and {_num(high)} {plural}"

    # -- rendering

    def _render_alternatives(self, alternatives: list[list[_Phrase]]) -> str:
        rendered = [_render_sequence(_merge_literals(seq)) for seq in alternatives]
        return _join_or_phrases(rendered)


def _merge_literals(items: list[_Phrase]) -> list[_Phrase]:
    """Fold runs of plain literal characters into one "the text '...'" phrase.

    Hearing "the text 'cat'" once beats hearing three one-letter steps; the
    merge only applies to unquantified literals, so ``ca+t`` still reads as
    three distinct pieces.
    """
    merged: list[_Phrase] = []
    run: list[str] = []

    def flush() -> None:
        if not run:
            return
        if len(run) == 1:
            merged.append(_Phrase(_char_name(run[0])))
        else:
            merged.append(_Phrase("the text '" + "".join(run) + "'"))
        run.clear()

    for item in items:
        if item.lit is not None:
            run.append(item.lit)
        else:
            flush()
            merged.append(item)
    flush()
    return merged


def _render_sequence(items: list[_Phrase]) -> str:
    phrases = [item.singular for item in items]
    if not phrases:
        return "nothing (an empty part)"
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} followed by {phrases[1]}"
    return ", then ".join(phrases)


def _join_or(parts: list[str]) -> str:
    if not parts:
        return "nothing"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f", or {parts[-1]}"


def _join_and(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    return "; and ".join(parts)


def _join_or_phrases(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    return " or ".join(parts)


def _step(number: int, text: str) -> str:
    sentence = text[0].upper() + text[1:] if text else text
    if not sentence.endswith((".", "!", "?")):
        sentence += "."
    return f"{number}. {sentence}"


# -- error diagnosis -----------------------------------------------------------


def diagnose_error(pattern: str, err: re.error) -> tuple[str, int | None]:
    """Turn an :class:`re.error` into a spoken-friendly, position-bearing sentence.

    Positions are reported one-based ("at character 4") because that is how a
    person counts characters when arrowing through the pattern field; the raw
    zero-based offset is returned separately for callers that move the caret.
    """
    msg = err.msg or str(err)
    pos: int | None = getattr(err, "pos", None)
    where = f"at character {pos + 1}" if pos is not None else "in the pattern"
    if "unterminated subpattern" in msg:
        return (
            f"Unclosed group: the open-parenthesis {where} has no matching close-parenthesis.",
            pos,
        )
    if "unbalanced parenthesis" in msg:
        return (f"Extra close-parenthesis {where} with no matching open-parenthesis.", pos)
    if "unterminated character set" in msg:
        return (
            f"Unclosed character class: the open-bracket {where} has no matching close-bracket.",
            pos,
        )
    if "nothing to repeat" in msg:
        offender = pattern[pos] if pos is not None and pos < len(pattern) else "quantifier"
        return (
            f"Dangling quantifier: the '{offender}' {where} has nothing before it to repeat.",
            pos,
        )
    if "multiple repeat" in msg:
        return (f"Two quantifiers in a row {where}; a repeat cannot itself be repeated.", pos)
    if "bad escape (end of pattern)" in msg:
        return (
            f"Trailing backslash: the pattern ends with a lone backslash {where}. "
            "To match a real backslash, double it.",
            pos,
        )
    if "min repeat greater than max repeat" in msg:
        return (
            f"Impossible repeat count {where}: the minimum is larger than the maximum.",
            pos,
        )
    if "bad character range" in msg:
        return (
            f"Backwards range inside a character class {where}: "
            "the range must run from the lower character to the higher one.",
            pos,
        )
    if "bad escape" in msg:
        return (f"Unknown escape sequence {where}.", pos)
    if "unknown group name" in msg or "invalid group reference" in msg:
        return (f"The pattern refers to a group that does not exist, {where}.", pos)
    sentence = msg[0].upper() + msg[1:] if msg else "The pattern is not valid"
    return (f"{sentence}, {where}.", pos)


# -- public API ----------------------------------------------------------------


def explain_pattern(pattern: str) -> ExplainResult:
    """Explain ``pattern`` as numbered plain-language steps.

    Always returns a result, never raises: invalid patterns come back with
    ``ok=False`` and a diagnosis naming the character position, and exotic but
    valid syntax the walker does not model is described generically rather
    than wrongly -- an honest "advanced construct" beats a confident
    misreading when the listener cannot double-check by sight.
    """
    try:
        re.compile(pattern)
    except re.error as err:
        message, position = diagnose_error(pattern, err)
        return ExplainResult(ok=False, steps=(), error=message, error_position=position)
    if not pattern:
        return ExplainResult(
            ok=True,
            steps=("1. An empty pattern, which matches at every position in the text.",),
            error="",
            error_position=None,
        )
    try:
        parser = _Parser(pattern)
        alternatives = parser.parse_alternation()
        if parser.pos != len(pattern):
            raise _Unexplainable("walker stopped before the end of the pattern")
    except _Unexplainable:
        return ExplainResult(
            ok=True,
            steps=(f"1. An advanced regular-expression pattern: '{pattern}'.",),
            error="",
            error_position=None,
        )
    steps: list[str] = []
    if len(alternatives) == 1:
        for item in _merge_literals(alternatives[0]):
            steps.append(_step(len(steps) + 1, item.singular))
    else:
        for index, seq in enumerate(alternatives):
            phrase = _render_sequence(_merge_literals(seq))
            lead = "either " if index == 0 else "or "
            steps.append(_step(len(steps) + 1, lead + phrase))
    return ExplainResult(ok=True, steps=tuple(steps), error="", error_position=None)
