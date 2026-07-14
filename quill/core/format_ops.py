from __future__ import annotations

import html
import random
import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.links import infer_markup_kind


@dataclass(frozen=True, slots=True)
class MarkdownListContinuation:
    text: str
    caret: int
    exited_list: bool


_MARKDOWN_LIST_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?:(?P<number>\d+)(?P<num_sep>[.)])|(?P<bullet>[-+*]))"
    r"(?P<spacing>[ \t]+)(?:(?P<task>\[[ xX]\])(?P<task_spacing>[ \t]+))?(?P<body>.*)$"
)


def continue_markdown_list(text: str, caret: int) -> MarkdownListContinuation | None:
    if caret < 0 or caret > len(text):
        return None
    line_start, line_end = _line_bounds(text, caret, caret)
    line_text = text[line_start:line_end].rstrip("\r\n")
    match = _MARKDOWN_LIST_PATTERN.match(line_text)
    if match is None:
        return None

    marker_end = _marker_end_offset(match)
    line_offset = caret - line_start
    if line_offset < marker_end:
        return None

    before_body = line_text[marker_end:line_offset]
    after_body = line_text[line_offset:]
    if not before_body.strip() and not after_body.strip():
        indent = match.group("indent")
        updated = text[:line_start] + indent + text[line_end:]
        return MarkdownListContinuation(updated, line_start + len(indent), exited_list=True)

    continuation_marker = _continuation_marker(match)
    inserted = "\n" + continuation_marker
    updated = text[:caret] + inserted + text[caret:]
    return MarkdownListContinuation(updated, caret + len(inserted), exited_list=False)


def indent_lines(
    text: str,
    start: int,
    end: int,
    indent_unit: str = "    ",
) -> tuple[str, int, int]:
    line_start, line_end = _line_bounds(text, start, end)
    original = text[line_start:line_end]
    lines = _split_lines_keepends(original)
    updated = "".join(f"{indent_unit}{line}" for line in lines)
    merged = text[:line_start] + updated + text[line_end:]

    if start == end:
        caret = start + len(indent_unit)
        return merged, caret, caret

    return merged, line_start, line_start + len(updated)


def outdent_lines(
    text: str,
    start: int,
    end: int,
    indent_unit: str = "    ",
) -> tuple[str, int, int]:
    line_start, line_end = _line_bounds(text, start, end)
    original = text[line_start:line_end]
    lines = _split_lines_keepends(original)

    updated_parts: list[str] = []
    removed_first = 0
    for index, line in enumerate(lines):
        outdented, removed = _outdent_single_line(line, indent_unit)
        if index == 0:
            removed_first = removed
        updated_parts.append(outdented)
    updated = "".join(updated_parts)
    merged = text[:line_start] + updated + text[line_end:]

    if start == end:
        caret = max(line_start, start - removed_first)
        return merged, caret, caret

    return merged, line_start, line_start + len(updated)


def describe_indent_depth(text: str, caret: int) -> str:
    """Describe the leading indentation of the line containing *caret*.

    Returns e.g. ``"4 spaces"``, ``"8 spaces"``, ``"1 tab"``, ``"2 tabs"``,
    ``"1 tab, 3 spaces"`` (mixed), or ``"No indentation"``. Tabs/spaces aware so a
    screen reader can speak the new depth after Tab / Shift+Tab instead of a terse
    "Indented lines".
    """
    caret = max(0, min(caret, len(text)))
    line_start = text.rfind("\n", 0, caret) + 1
    line_end = text.find("\n", line_start)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end]
    leading = line[: len(line) - len(line.lstrip(" \t"))]
    if not leading:
        return "No indentation"
    tabs = leading.count("\t")
    spaces = leading.count(" ")
    parts: list[str] = []
    if tabs:
        parts.append(f"{tabs} tab" if tabs == 1 else f"{tabs} tabs")
    if spaces:
        parts.append(f"{spaces} space" if spaces == 1 else f"{spaces} spaces")
    return ", ".join(parts)


def sort_lines(
    text: str,
    descending: bool = False,
    case_sensitive: bool = False,
) -> str:
    lines, terminal_newline = _split_body_lines(text)
    lines.sort(key=lambda line: _line_sort_key(line, case_sensitive), reverse=descending)
    return _join_body_lines(lines, terminal_newline)


def reverse_lines(text: str) -> str:
    lines, terminal_newline = _split_body_lines(text)
    lines.reverse()
    return _join_body_lines(lines, terminal_newline)


def remove_duplicate_lines(text: str, case_sensitive: bool = True) -> str:
    lines, terminal_newline = _split_body_lines(text)
    seen: set[str] = set()
    updated: list[str] = []
    for line in lines:
        key = _line_sort_key(line, case_sensitive)
        if key in seen:
            continue
        seen.add(key)
        updated.append(line)
    return _join_body_lines(updated, terminal_newline)


def trim_trailing_whitespace(text: str) -> str:
    return "\n".join(line.rstrip(" \t") for line in _split_lines(text))


def normalize_whitespace(text: str) -> str:
    updated = []
    for line in _split_lines(text):
        if not line.strip():
            updated.append("")
            continue
        updated.append(" ".join(line.split()))
    return "\n".join(updated)


def convert_indentation_to_spaces(text: str, indent_width: int = 4) -> str:
    indent_width = max(1, indent_width)
    lines = _split_lines(text)
    updated = []
    for line in lines:
        indent, rest = _split_leading_whitespace(line)
        updated.append(f"{indent.expandtabs(indent_width)}{rest}")
    return "\n".join(updated)


def convert_indentation_to_tabs(text: str, indent_width: int = 4) -> str:
    indent_width = max(1, indent_width)
    lines = _split_lines(text)
    updated = []
    for line in lines:
        indent, rest = _split_leading_whitespace(line)
        expanded = indent.expandtabs(indent_width)
        tabs, spaces = divmod(len(expanded), indent_width)
        updated.append("\t" * tabs + " " * spaces + rest)
    return "\n".join(updated)


def toggle_line_comment(
    text: str,
    start: int,
    end: int,
    path: Path | None,
    profile: object | None = None,
) -> tuple[str, int, int]:
    line_start, line_end = _line_bounds(text, start, end)
    original = text[line_start:line_end]
    lines = _split_lines_keepends(original)
    style = _line_comment_style(path, profile)

    if style == "html":
        all_commented = _all_html_commented(lines)
        updated = "".join(
            _uncomment_html_line(line) if all_commented else _comment_html_line(line)
            for line in lines
        )
    else:
        all_commented = _all_prefix_commented(lines, style)
        updated = "".join(
            _uncomment_prefix_line(line, style)
            if all_commented
            else _comment_prefix_line(line, style)
            for line in lines
        )

    merged = text[:line_start] + updated + text[line_end:]
    return merged, line_start, line_start + len(updated)


def strip_html_tags(text: str) -> str:
    """Remove all HTML tags from text, leaving only the inner content."""
    return re.sub(r"<[^>]+>", "", text)


def decode_html_entities(text: str) -> str:
    """Decode HTML entities such as &amp; and &#034; to their Unicode equivalents."""
    return html.unescape(text)


def encode_html_entities(text: str) -> str:
    """Encode <, >, &, " and ' as HTML entities."""
    return html.escape(text)


_EMAIL_QUOTE_PREFIX = re.compile(r"^(?:\s*>+\s?)+")


def remove_email_quote_markers(text: str) -> str:
    """Strip leading ``>`` quote markers (and ``Name>`` prefixes) from each line."""
    lines = []
    for line in _split_lines(text):
        stripped = _EMAIL_QUOTE_PREFIX.sub("", line)
        if stripped == line:
            stripped = re.sub(r"^\s*\S+>\s?", "", line, count=1)
        lines.append(stripped)
    return "\n".join(lines)


def strip_low_ascii(text: str) -> str:
    """Remove control characters (codepoints below 0x20), keeping tab and newline."""
    return "".join(ch for ch in text if ord(ch) >= 0x20 or ch in "\t\n\r")


def strip_high_ascii(text: str) -> str:
    """Remove every character above 0x7E (non-ASCII), leaving plain ASCII text."""
    return "".join(ch for ch in text if ord(ch) <= 0x7E or ch in "\t\n\r")


def multi_replace(text: str, pairs: list[tuple[str, str]], *, case_sensitive: bool = True) -> str:
    """Apply up to several search/replace pairs to *text* in one pass.

    Pairs are applied in order, left to right, each over the result of the
    previous one. Empty search strings are skipped rather than raising.
    """
    result = text
    for search, replacement in pairs:
        if not search:
            continue
        if case_sensitive:
            result = result.replace(search, replacement)
        else:

            def _repl(_m: re.Match[str], r: str = replacement) -> str:
                return r

            result = re.sub(re.escape(search), _repl, result, flags=re.IGNORECASE)
    return result


def count_occurrences(text: str, needle: str, *, case_sensitive: bool = True) -> int:
    """Count non-overlapping occurrences of *needle* in *text*."""
    if not needle:
        return 0
    if case_sensitive:
        return text.count(needle)
    return text.lower().count(needle.lower())


def compute_line_statistics(text: str) -> str:
    """Render count/total/average/median/mode/standard deviation for numeric lines.

    Non-numeric and blank lines are ignored. Designed to be read with a
    screen reader: one labeled value per line.
    """
    import statistics

    values: list[float] = []
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        try:
            values.append(float(candidate))
        except ValueError:
            continue
    if not values:
        return "No numeric lines were found."
    lines = [
        f"Numeric lines: {len(values)}",
        f"Total: {sum(values):g}",
        f"Average: {statistics.mean(values):g}",
        f"Median: {statistics.median(values):g}",
    ]
    try:
        lines.append(f"Mode: {statistics.mode(values):g}")
    except statistics.StatisticsError:
        lines.append("Mode: no unique mode")
    if len(values) > 1:
        lines.append(f"Standard deviation: {statistics.stdev(values):g}")
    else:
        lines.append("Standard deviation: not enough data")
    return "\n".join(lines)


def hex_dump(text: str, *, bytes_per_line: int = 16) -> str:
    """Render *text* (encoded as UTF-8) as a classic hex + ASCII dump."""
    data = text.encode("utf-8")
    lines = []
    for offset in range(0, len(data), bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        hex_part = " ".join(f"{byte:02x}" for byte in chunk)
        hex_part = hex_part.ljust(bytes_per_line * 3 - 1)
        ascii_part = "".join(chr(byte) if 0x20 <= byte < 0x7F else "." for byte in chunk)
        lines.append(f"{offset:08x}  {hex_part}  {ascii_part}")
    return "\n".join(lines)


def shuffle_lines(text: str) -> str:
    """Randomly reorder the lines of text."""
    lines, terminal_newline = _split_body_lines(text)
    random.shuffle(lines)
    return _join_body_lines(lines, terminal_newline)


def trim_blank_lines(text: str) -> str:
    """Remove leading and trailing blank lines."""
    parts = text.split("\n")
    while parts and not parts[0].strip():
        parts.pop(0)
    while parts and not parts[-1].strip():
        parts.pop()
    return "\n".join(parts)


def quote_lines(text: str, prefix: str = "> ") -> str:
    """Prefix every non-empty line with prefix (default: email block-quote style)."""
    lines, terminal_newline = _split_body_lines(text)
    updated = [f"{prefix}{line}" if line.strip() else line for line in lines]
    return _join_body_lines(updated, terminal_newline)


def unquote_lines(text: str) -> str:
    """Remove a leading block-quote prefix ("> " or ">") from each line."""
    lines, terminal_newline = _split_body_lines(text)
    updated: list[str] = []
    for line in lines:
        if line.startswith("> "):
            updated.append(line[2:])
        elif line.startswith(">"):
            updated.append(line[1:])
        else:
            updated.append(line)
    return _join_body_lines(updated, terminal_newline)


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def delete_lines_containing(text: str, pattern: str, *, case_sensitive: bool = True) -> str:
    """Remove every line that contains a match for pattern."""
    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = re.compile(pattern, flags)
    lines, terminal_newline = _split_body_lines(text)
    updated = [line for line in lines if not compiled.search(line)]
    return _join_body_lines(updated, terminal_newline)


def delete_lines_not_containing(text: str, pattern: str, *, case_sensitive: bool = True) -> str:
    """Keep only lines that contain a match for pattern (delete the rest)."""
    flags = 0 if case_sensitive else re.IGNORECASE
    compiled = re.compile(pattern, flags)
    lines, terminal_newline = _split_body_lines(text)
    updated = [line for line in lines if compiled.search(line)]
    return _join_body_lines(updated, terminal_newline)


def sort_lines_numeric(text: str, descending: bool = False) -> str:
    """Sort lines by the first number found in each line.

    Lines containing no number sort after all numeric lines.
    """
    lines, terminal_newline = _split_body_lines(text)
    numeric: list[tuple[float, str]] = []
    non_numeric: list[str] = []
    for line in lines:
        body, _ = _split_line_ending(line)
        m = _NUMBER_RE.search(body)
        if m:
            try:
                numeric.append((float(m.group()), line))
                continue
            except ValueError:
                pass
        non_numeric.append(line)
    numeric.sort(key=lambda pair: pair[0], reverse=descending)
    sorted_lines = [line for _, line in numeric] + non_numeric
    return _join_body_lines(sorted_lines, terminal_newline)


def sort_lines_by_length(text: str, descending: bool = False) -> str:
    """Sort lines by their length, excluding line-ending characters."""
    lines, terminal_newline = _split_body_lines(text)
    lines.sort(key=lambda line: len(_split_line_ending(line)[0]), reverse=descending)
    return _join_body_lines(lines, terminal_newline)


def toggle_block_comment(
    text: str,
    start: int,
    end: int,
    path: Path | None,
    profile: object | None = None,
) -> tuple[str, int, int]:
    opening, closing = _block_comment_tokens(path, profile)
    selected = text[start:end]
    if selected:
        stripped = selected.strip()
        if stripped.startswith(opening) and stripped.endswith(closing):
            inner = stripped[len(opening) : len(stripped) - len(closing)].strip()
            merged = text[:start] + inner + text[end:]
            return merged, start, start + len(inner)
        wrapped = f"{opening}{selected}{closing}"
        merged = text[:start] + wrapped + text[end:]
        return merged, start, start + len(wrapped)

    inserted = f"{opening}{closing}"
    merged = text[:start] + inserted + text[end:]
    caret = start + len(opening)
    return merged, caret, caret


def _line_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    left = min(start, end)
    right = max(start, end)
    line_start = text.rfind("\n", 0, left) + 1
    line_end = text.find("\n", right)
    if line_end == -1:
        line_end = len(text)
    else:
        line_end += 1
    return line_start, line_end


def _marker_end_offset(match: re.Match[str]) -> int:
    marker = match.group(0)
    body = match.group("body")
    return len(marker) - len(body)


def _continuation_marker(match: re.Match[str]) -> str:
    indent = match.group("indent")
    bullet = match.group("bullet")
    number = match.group("number")
    num_sep = match.group("num_sep") or "."
    spacing = match.group("spacing") or " "
    task = match.group("task")
    task_spacing = match.group("task_spacing") or " "
    if task is not None:
        return f"{indent}{bullet or '-'} [ ]{task_spacing}"
    if bullet is not None:
        return f"{indent}{bullet}{spacing}"
    next_number = int(number or "1") + 1
    return f"{indent}{next_number}{num_sep}{spacing}"


def _split_lines_keepends(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    return lines or [text]


def _split_lines(text: str) -> list[str]:
    if text == "":
        return [""]
    return text.split("\n")


def _split_body_lines(text: str) -> tuple[list[str], bool]:
    lines = _split_lines(text)
    if lines and lines[-1] == "":
        return lines[:-1], True
    return lines, False


def _join_body_lines(lines: list[str], terminal_newline: bool) -> str:
    updated = "\n".join(lines)
    if terminal_newline:
        return f"{updated}\n"
    return updated


def _split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1], line[-1]
    return line, ""


def _split_leading_whitespace(text: str) -> tuple[str, str]:
    index = 0
    while index < len(text) and text[index] in {" ", "\t"}:
        index += 1
    return text[:index], text[index:]


def _line_sort_key(line: str, case_sensitive: bool) -> str:
    body, _ = _split_line_ending(line)
    return body if case_sensitive else body.casefold()


def _outdent_single_line(line: str, indent_unit: str) -> tuple[str, int]:
    if not line:
        return line, 0
    if line.startswith(indent_unit):
        return line[len(indent_unit) :], len(indent_unit)
    if line.startswith("\t"):
        return line[1:], 1
    spaces = len(line) - len(line.lstrip(" "))
    if spaces == 0:
        return line, 0
    remove_count = min(len(indent_unit), spaces)
    return line[remove_count:], remove_count


def _line_comment_style(path: Path | None, profile: object | None = None) -> str:
    # A user-pinned language profile wins over the file name, so e.g. a .txt set
    # to Python comments with "# " and one set to HTML comments with <!-- -->.
    if profile is not None:
        if getattr(profile, "markup_kind", "") in {"html", "markdown"}:
            return "html"
        prefix = getattr(profile, "comment_prefix", "")
        if prefix:
            return prefix
        return "// "

    kind = infer_markup_kind(path)
    if kind in {"html", "markdown"}:
        return "html"

    extension = path.suffix.lower() if path is not None else ""
    if extension in {".sql", ".lua", ".hs"}:
        return "-- "
    if extension in {".py", ".rb", ".sh", ".yml", ".yaml", ".toml", ".ini", ".conf"}:
        return "# "
    return "// "


def _block_comment_tokens(path: Path | None, profile: object | None = None) -> tuple[str, str]:
    if profile is not None:
        if getattr(profile, "markup_kind", "") in {"html", "markdown"}:
            return "<!-- ", " -->"
        start = getattr(profile, "block_comment_start", "")
        end = getattr(profile, "block_comment_end", "")
        if start and end:
            return f"{start} ", f" {end}"
        return "/* ", " */"

    style = _line_comment_style(path)
    if style == "html":
        return "<!-- ", " -->"
    return "/* ", " */"


def _all_html_commented(lines: list[str]) -> bool:
    relevant = [line for line in lines if line.strip()]
    if not relevant:
        return False
    return all(_is_html_commented_line(line) for line in relevant)


def _is_html_commented_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("<!--") and stripped.endswith("-->")


def _comment_html_line(line: str) -> str:
    newline = "\n" if line.endswith("\n") else ""
    content = line[:-1] if newline else line
    if not content.strip():
        return f"<!--  -->{newline}"
    return f"<!-- {content} -->{newline}"


def _uncomment_html_line(line: str) -> str:
    newline = "\n" if line.endswith("\n") else ""
    content = line[:-1] if newline else line
    stripped = content.strip()
    if stripped.startswith("<!--") and stripped.endswith("-->"):
        inner = stripped[4:-3].strip()
        return f"{inner}{newline}"
    return line


def _all_prefix_commented(lines: list[str], prefix: str) -> bool:
    relevant = [line for line in lines if line.strip()]
    if not relevant:
        return False
    return all(_is_prefix_commented_line(line, prefix) for line in relevant)


def _is_prefix_commented_line(line: str, prefix: str) -> bool:
    stripped = line.lstrip(" \t")
    return stripped.startswith(prefix)


def _comment_prefix_line(line: str, prefix: str) -> str:
    newline = "\n" if line.endswith("\n") else ""
    content = line[:-1] if newline else line
    indent_length = len(content) - len(content.lstrip(" \t"))
    indent = content[:indent_length]
    body = content[indent_length:]
    return f"{indent}{prefix}{body}{newline}"


def _uncomment_prefix_line(line: str, prefix: str) -> str:
    newline = "\n" if line.endswith("\n") else ""
    content = line[:-1] if newline else line
    indent_length = len(content) - len(content.lstrip(" \t"))
    indent = content[:indent_length]
    body = content[indent_length:]
    if body.startswith(prefix):
        return f"{indent}{body[len(prefix) :]}{newline}"
    return line
