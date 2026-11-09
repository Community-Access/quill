"""Tier 1: checkers built in, with no outside tool and no new dependency.

Each checker takes the document's text (and its path, when it has one) and
returns every problem it can find. A parser that stops at its first error --
``json``, ``tomllib``, ``compile`` -- can only ever report one; the checkers
that walk the text themselves (HTML, CSV, Markdown, INI) report them all.
"""

from __future__ import annotations

import configparser
import csv
import io
import json
import re
import tomllib
import warnings
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path

from quill.core.problems.model import Problem

Checker = Callable[[str, Path | None], list[Problem]]


def _line_column(text: str, offset: int) -> tuple[int, int]:
    offset = max(0, min(offset, len(text)))
    line = text.count("\n", 0, offset) + 1
    column = offset - (text.rfind("\n", 0, offset) + 1) + 1
    return line, column


# -- JSON and JSONC ------------------------------------------------------------ #


def check_json(text: str, _path: Path | None = None) -> list[Problem]:
    if not text.strip():
        return []
    try:
        json.loads(text)
    except json.JSONDecodeError as error:
        return [Problem(error.lineno, error.colno, "error", error.msg, "JSON")]
    except (RecursionError, MemoryError):
        return [Problem(1, 1, "warning", "Nested too deeply to check", "JSON")]
    return []


_JSONC_COMMENTS = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', re.DOTALL)
_JSONC_TRAILING = re.compile(r'"(?:\\.|[^"\\])*"|,(?=\s*[}\]])')


def _blank_out(match: re.Match[str]) -> str:
    token = match.group(0)
    if token.startswith('"'):
        return token
    # Same length, newlines kept, so every position after it stays true.
    return re.sub(r"[^\n]", " ", token)


def strip_jsonc(text: str) -> str:
    """JSONC as JSON: comments, then trailing commas, blanked; positions kept."""
    return _JSONC_TRAILING.sub(_blank_out, _JSONC_COMMENTS.sub(_blank_out, text))


def check_jsonc(text: str, _path: Path | None = None) -> list[Problem]:
    if not text.strip():
        return []
    unterminated = re.search(r"/\*(?![\s\S]*?\*/)", _strings_removed(text))
    if unterminated is not None:
        line, column = _line_column(text, unterminated.start())
        return [Problem(line, column, "error", "Comment is never closed", "JSONC")]
    try:
        json.loads(strip_jsonc(text))
    except json.JSONDecodeError as error:
        return [Problem(error.lineno, error.colno, "error", error.msg, "JSONC")]
    except (RecursionError, MemoryError):
        return [Problem(1, 1, "warning", "Nested too deeply to check", "JSONC")]
    return []


def _strings_removed(text: str) -> str:
    return re.sub(r'"(?:\\.|[^"\\\n])*"', lambda m: " " * len(m.group(0)), text)


# -- XML ---------------------------------------------------------------------- #


def check_xml(text: str, _path: Path | None = None) -> list[Problem]:
    from quill.core import safe_xml

    if not text.strip():
        return []
    try:
        safe_xml.fromstring(text)
    except safe_xml.ParseError as error:
        line, column = getattr(error, "position", (1, 0))
        message = str(error).split(": line ")[0]
        return [Problem(int(line), int(column) + 1, "error", message, "XML")]
    except Exception as error:  # noqa: BLE001 - entity attacks, refused by design
        return [Problem(1, 1, "error", f"Not checked: {error}", "XML")]
    return []


# -- HTML --------------------------------------------------------------------- #

_VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr "
    "basefont bgsound frame keygen command".split()
)
#: Elements whose end tag HTML lets you leave out.
_OPTIONAL_END = frozenset(
    "p li dt dd tr td th thead tbody tfoot option optgroup colgroup caption "
    "rb rt rtc rp html head body".split()
)


class _HtmlChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.problems: list[Problem] = []
        self.stack: list[tuple[str, int, int]] = []
        self.ids: dict[str, int] = {}

    def _here(self) -> tuple[int, int]:
        line, column = self.getpos()
        return line, column + 1

    def _add(self, severity: str, message: str, where: tuple[int, int] | None = None) -> None:
        line, column = where or self._here()
        self.problems.append(Problem(line, column, severity, message, "HTML"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._attributes(tag, attrs)
        if tag in _VOID:
            return
        line, column = self._here()
        self.stack.append((tag, line, column))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._attributes(tag, attrs)

    def _attributes(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            if element_id in self.ids:
                self._add(
                    "error",
                    f'Duplicate id "{element_id}", first used on line {self.ids[element_id]}',
                )
            else:
                self.ids[element_id] = self._here()[0]
        if tag == "img" and "alt" not in values:
            self._add("warning", "Image has no alt text")

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID:
            return
        names = [name for name, _line, _column in self.stack]
        if tag not in names:
            self._add("error", f"</{tag}> closes nothing: there is no open <{tag}>")
            return
        while self.stack:
            name, line, column = self.stack.pop()
            if name == tag:
                return
            if name not in _OPTIONAL_END:
                self._add(
                    "error",
                    f"<{name}> opened on line {line} is not closed before </{tag}>",
                    (line, column),
                )

    def finish(self) -> list[Problem]:
        self.close()
        for name, line, column in self.stack:
            if name not in _OPTIONAL_END:
                self._add("error", f"<{name}> is never closed", (line, column))
        return self.problems


def check_html(text: str, _path: Path | None = None) -> list[Problem]:
    checker = _HtmlChecker()
    checker.feed(text)
    return checker.finish()


# -- TOML --------------------------------------------------------------------- #

_TOML_AT = re.compile(r"\(at line (\d+), column (\d+)\)")


def check_toml(text: str, _path: Path | None = None) -> list[Problem]:
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        line = getattr(error, "lineno", None)
        column = getattr(error, "colno", None)
        message = getattr(error, "msg", None) or str(error)
        found = _TOML_AT.search(str(error))
        if (line is None or column is None) and found is not None:
            line, column = int(found.group(1)), int(found.group(2))
        message = _TOML_AT.sub("", str(message)).strip()
        return [Problem(int(line or 1), int(column or 1), "error", message, "TOML")]
    return []


# -- YAML ---------------------------------------------------------------------- #


def yaml_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("yaml") is not None


def check_yaml(text: str, _path: Path | None = None) -> list[Problem]:
    import yaml  # type: ignore[import-untyped]

    try:
        for _document in yaml.safe_load_all(text):
            pass
    except yaml.MarkedYAMLError as error:
        mark = error.problem_mark or error.context_mark
        line = mark.line + 1 if mark is not None else 1
        column = mark.column + 1 if mark is not None else 1
        message = " ".join(part for part in (error.context, error.problem) if part)
        return [Problem(line, column, "error", message or "Not valid YAML", "YAML")]
    except yaml.YAMLError as error:
        return [Problem(1, 1, "error", str(error), "YAML")]
    return []


# -- Python ------------------------------------------------------------------- #


def check_python(text: str, path: Path | None = None) -> list[Problem]:
    """``compile``, which finds everything ``ast.parse`` does and a little more
    ("'return' outside function"), plus the warnings it raises on the way (an
    invalid escape sequence). The code object is thrown away: nothing is run."""
    name = str(path) if path is not None else "<document>"
    problems: list[Problem] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compile(text, name, "exec", dont_inherit=True)
        except SyntaxError as error:
            problems.append(
                Problem(
                    error.lineno or 1,
                    max(1, error.offset or 1),
                    "error",
                    error.msg,
                    "Python",
                )
            )
        except ValueError as error:  # a NUL byte in the source
            problems.append(Problem(1, 1, "error", str(error), "Python"))
        except (RecursionError, MemoryError):
            problems.append(Problem(1, 1, "warning", "Nested too deeply to check", "Python"))
    for item in caught:
        if issubclass(item.category, SyntaxWarning | DeprecationWarning):
            problems.append(
                Problem(int(item.lineno or 1), 1, "warning", str(item.message), "Python")
            )
    return problems


def _text(value: object) -> str:
    return str(value).strip()


# -- INI ---------------------------------------------------------------------- #


def check_ini(text: str, _path: Path | None = None) -> list[Problem]:
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        parser.read_string(text)
    except configparser.MissingSectionHeaderError as error:
        return [Problem(error.lineno, 1, "error", "A setting comes before any [section]", "INI")]
    except configparser.DuplicateSectionError as error:
        return [
            Problem(
                error.lineno or 1, 1, "error", f"Section [{error.section}] appears twice", "INI"
            )
        ]
    except configparser.DuplicateOptionError as error:
        return [
            Problem(
                error.lineno or 1,
                1,
                "error",
                f"{error.option} appears twice in [{error.section}]",
                "INI",
            )
        ]
    except configparser.ParsingError as error:
        return [
            Problem(int(lineno), 1, "error", f"Not a setting or a section: {_text(line)}", "INI")
            for lineno, line in error.errors
        ]
    except configparser.Error as error:
        return [Problem(1, 1, "error", str(error), "INI")]
    return []


# -- CSV ---------------------------------------------------------------------- #

#: Enough to show a pattern without a list nobody can arrow to the end of.
CSV_ROW_LIMIT = 200


def check_csv(text: str, path: Path | None = None) -> list[Problem]:
    if not text.strip():
        return []
    delimiter = "\t" if path is not None and path.suffix.lower() == ".tsv" else ","
    if path is None or path.suffix.lower() != ".tsv":
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    problems: list[Problem] = []
    expected: int | None = None
    try:
        for row in reader:
            if not row:
                continue
            if expected is None:
                expected = len(row)
                continue
            if len(row) != expected and len(problems) < CSV_ROW_LIMIT:
                problems.append(
                    Problem(
                        reader.line_num,
                        1,
                        "warning",
                        f"This row has {len(row)} fields; the first row has {expected}",
                        "CSV",
                    )
                )
    except csv.Error as error:
        problems.append(Problem(reader.line_num or 1, 1, "error", str(error), "CSV"))
    return problems


# -- Markdown ------------------------------------------------------------------ #

_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]*)(?:\s+\"[^\"]*\")?\)")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def check_markdown(text: str, path: Path | None = None) -> list[Problem]:
    """Heading levels that skip, images without alt text (the GLOW audit's own
    rules, reused), empty links, and relative links to files that are not there."""
    from quill.core.glow import audit_text

    problems = [
        Problem(f.line or 1, f.column or 1, f.severity, f.message, "Markdown")
        for f in audit_text(text, "markdown")
        if f.rule_id in {"GLOW-MD-HEADING-JUMP", "GLOW-MD-IMAGE-ALT"}
    ]
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in _LINK.finditer(line):
            image, label, target = match.group(1), match.group(2).strip(), match.group(3)
            column = match.start() + 1
            if not target:
                problems.append(Problem(number, column, "error", "Link has no address", "Markdown"))
                continue
            if not image and not label:
                problems.append(Problem(number, column, "error", "Link has no text", "Markdown"))
            broken = _broken_relative(target, path)
            if broken:
                problems.append(
                    Problem(number, column, "warning", f"No file at {broken}", "Markdown")
                )
    return problems


def _broken_relative(target: str, path: Path | None) -> str:
    """The relative link target that names no file beside the document, or "".

    Only plain relative paths are looked at. A UNC path (``\\\\host\\share``,
    ``//host/share``), a drive path or anything with a scheme is skipped: asking
    Windows whether ``\\\\host\\share\\f`` exists makes it connect to that host,
    which sends the user's credentials and can hang the window.
    """
    if path is None or target.startswith(("#", "/", "<", "\\")) or _SCHEME.match(target):
        return ""
    local = target.split("#", 1)[0].split("?", 1)[0]
    if not local or Path(local).is_absolute() or Path(local).drive:
        return ""
    from urllib.parse import unquote

    decoded = unquote(local)
    if decoded.startswith(("\\", "/")) or Path(decoded).is_absolute() or Path(decoded).drive:
        return ""  # %5C%5Chost decodes to a UNC path: never touched either
    try:
        exists = (path.parent / decoded).exists()
    except OSError:
        return ""
    return "" if exists else local


#: Language key -> (checker name, checker). YAML joins only when a YAML
#: library is importable (PyYAML arrives with the speech packages).
BUILTIN_CHECKERS: dict[str, tuple[str, Checker]] = {
    "json": ("JSON", check_json),
    "jsonc": ("JSONC", check_jsonc),
    "xml": ("XML", check_xml),
    "html": ("HTML", check_html),
    "toml": ("TOML", check_toml),
    "python": ("Python", check_python),
    "ini": ("INI", check_ini),
    "csv": ("CSV", check_csv),
    "markdown": ("Markdown", check_markdown),
}
if yaml_available():
    BUILTIN_CHECKERS["yaml"] = ("YAML", check_yaml)
