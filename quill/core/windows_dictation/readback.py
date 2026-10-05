"""Punctuation said aloud in the read-back: "Hello comma world period".

dict.md 3.1 (gap 3). The read-back exists so you can check what went in, and
with a screen reader's punctuation level at Some or None, "Hello, world." is
heard as "Hello world": the comma you said, or the full stop the engine added,
cannot be heard at all. With **Say punctuation marks in the read-back** on (the
default), every mark is turned into its name before the read-back is spoken,
whatever the screen reader's own punctuation level is.

The names are dictation's own -- "period", "question mark", "open quote",
"new paragraph" -- so what you hear is what you would say to write it. In
Spanish, the Spanish names ("coma", "punto").

Kept silent, because they are part of a word rather than punctuation in it:

* an apostrophe inside a word ("don't"),
* a hyphen inside a word ("well-known"),
* a full stop or comma between digits ("3.5", "1,000"),
* a full stop between letters with no space after it ("example.com" says
  "example dot com", which is how an address is said).

Only the spoken copy changes. The status bar and a braille display keep the
real characters ("Dictated: Hello, world."), because braille shows marks
exactly and words there would be worse. Not :mod:`quill.core.punctuation_speech`,
whose names are Read Aloud's ("dot", "exclamation") and differ from what
dictation teaches.

Pure and wx-free.
"""

from __future__ import annotations

__all__ = ["mark_names", "spoken_marks"]

#: Character -> its dictation name, in English. Quotes are decided by position.
_ENGLISH: dict[str, str] = {
    ".": "period",
    ",": "comma",
    "?": "question mark",
    "!": "exclamation mark",
    ":": "colon",
    ";": "semicolon",
    "(": "open paren",
    ")": "close paren",
    "[": "open bracket",
    "]": "close bracket",
    "{": "open brace",
    "}": "close brace",
    "<": "less than sign",
    ">": "greater than sign",
    "-": "hyphen",
    "/": "slash",
    "\\": "backslash",
    "_": "underscore",
    "@": "at sign",
    "#": "hash sign",
    "$": "dollar sign",
    "%": "percent sign",
    "&": "ampersand",
    "*": "asterisk",
    "+": "plus sign",
    "=": "equals sign",
    "`": "backtick",
    "~": "tilde",
    "|": "vertical bar",
    "^": "caret",
    chr(0x2014): "dash",
    chr(0x2013): "dash",
    chr(0x2026): "ellipsis",
    chr(0xBF): "open question mark",
    chr(0xA1): "open exclamation mark",
}

#: The Spanish names, from the Spanish punctuation words dictation teaches.
_SPANISH: dict[str, str] = {
    ".": "punto",
    ",": "coma",
    "?": "cerrar interrogación",
    "!": "cerrar exclamación",
    ":": "dos puntos",
    ";": "punto y coma",
    "(": "abrir paréntesis",
    ")": "cerrar paréntesis",
    "-": "guión",
    "@": "arroba",
    chr(0x2014): "guión largo",
    chr(0x2013): "guión largo",
    chr(0x2026): "puntos suspensivos",
    chr(0xBF): "abrir interrogación",
    chr(0xA1): "abrir exclamación",
}

_QUOTES = {
    "en": ("open quote", "close quote", "open single quote", "close single quote"),
    "es": ("abrir comillas", "cerrar comillas", "abrir comillas", "cerrar comillas"),
}
_BREAKS = {
    "en": ("new line", "new paragraph", "tab", "ellipsis", "dot"),
    "es": ("nueva línea", "nuevo párrafo", "tabulador", "puntos suspensivos", "punto"),
}
_CURLY = {chr(0x201C): '"', chr(0x201D): '"', chr(0x2018): "'", chr(0x2019): "'"}


def mark_names(language: str = "en") -> dict[str, str]:
    """The name each character is read as, in *language* (``en`` or ``es``)."""
    if language == "es":
        return {**_ENGLISH, **_SPANISH}
    return dict(_ENGLISH)


def spoken_marks(text: str, language: str = "en") -> str:
    """*text* with every punctuation mark said by its name.

    "Hello, world." becomes "Hello comma world period". Words are left exactly
    as they are; only the marks between and around them become words.
    """
    language = "es" if language == "es" else "en"
    names = mark_names(language)
    open_quote, close_quote, open_single, close_single = _QUOTES[language]
    new_line, new_paragraph, tab, ellipsis, dot = _BREAKS[language]
    out: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = _CURLY.get(text[index], text[index])
        before = text[index - 1] if index else ""
        after = text[index + 1] if index + 1 < length else ""
        if text.startswith("\n\n", index) or text.startswith("\r\n\r\n", index):
            out.append(f" {new_paragraph} ")
            index += 4 if text.startswith("\r\n\r\n", index) else 2
            continue
        if char in "\r\n":
            out.append(f" {new_line} ")
            index += 2 if text.startswith("\r\n", index) else 1
            continue
        if char == "\t":
            out.append(f" {tab} ")
        elif text.startswith("...", index):
            out.append(f" {ellipsis} ")
            index += 3
            continue
        elif text.startswith("--", index):
            out.append(f" {names[chr(0x2014)]} ")  # two hyphens are the dash style
            index += 2
            continue
        elif char.isalnum() or char.isspace():
            out.append(char if not char.isspace() else " ")
        elif char in ".," and before.isdigit() and after.isdigit():
            out.append(char)  # 3.5 and 1,000 are numbers, said as numbers
        elif char == "." and before.isalnum() and after.isalnum():
            out.append(f" {dot} ")  # example.com
        elif char in "'-" and before.isalnum() and after.isalnum():
            out.append(char)  # don't, well-known
        elif char == '"':
            opening = not before or before.isspace() or before in "([{"
            out.append(f" {open_quote if opening else close_quote} ")
        elif char == "'":
            opening = not before or before.isspace() or before in "([{"
            out.append(f" {open_single if opening else close_single} ")
        elif char in names:
            out.append(f" {names[char]} ")
        else:
            out.append(char)
        index += 1
    return " ".join("".join(out).split())
