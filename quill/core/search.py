from __future__ import annotations

import re
from dataclasses import dataclass

import regex as regex_module

from quill.core.error_codes import CodedError
from quill.stability.safe_regex import RegexTimeoutError, safe_finditer, safe_subn


@dataclass(frozen=True, slots=True)
class SearchOptions:
    case_sensitive: bool = False
    whole_word: bool = False
    use_regex: bool = False
    wildcard: bool = False


class SearchPatternError(CodedError):
    code = "QUILL-SEARCH-PATTERN-INVALID"


def find_matches(
    text: str,
    query: str,
    options: SearchOptions | None = None,
) -> list[tuple[int, int]]:
    options = options or SearchOptions()
    if not query:
        return []
    pattern = _pattern(query, options)
    try:
        if options.use_regex or options.wildcard:
            flags = 0 if options.case_sensitive else re.IGNORECASE
            return [
                (match.start(), match.end()) for match in safe_finditer(pattern, text, flags=flags)
            ]
        flags = 0 if options.case_sensitive else re.IGNORECASE
        return [(match.start(), match.end()) for match in re.finditer(pattern, text, flags)]
    except RegexTimeoutError as error:
        raise SearchPatternError(str(error)) from error
    except regex_module.error as error:
        raise SearchPatternError(_friendly_regex_error(error)) from error
    except re.error as error:
        raise SearchPatternError(_friendly_regex_error(error)) from error


def replace_all(
    text: str,
    query: str,
    replacement: str,
    options: SearchOptions | None = None,
) -> tuple[str, int]:
    options = options or SearchOptions()
    if not query:
        return text, 0
    pattern = _pattern(query, options)
    try:
        if options.use_regex or options.wildcard:
            flags = 0 if options.case_sensitive else re.IGNORECASE
            return safe_subn(pattern, replacement, text, flags=flags)
        flags = 0 if options.case_sensitive else re.IGNORECASE
        return re.subn(pattern, replacement, text, flags=flags)
    except RegexTimeoutError as error:
        raise SearchPatternError(str(error)) from error
    except regex_module.error as error:
        raise SearchPatternError(_friendly_regex_error(error)) from error
    except re.error as error:
        raise SearchPatternError(_friendly_regex_error(error)) from error


def _pattern(query: str, options: SearchOptions) -> str:
    if options.use_regex:
        base = query
    elif options.wildcard:
        base = _wildcard_to_regex(query)
    else:
        base = re.escape(query)
    if options.whole_word:
        return rf"\b{base}\b"
    return base


def _wildcard_to_regex(query: str) -> str:
    pieces: list[str] = []
    for character in query:
        if character == "*":
            pieces.append(".*?")
        elif character == "?":
            pieces.append(".")
        else:
            pieces.append(re.escape(character))
    return "".join(pieces)


def _friendly_regex_error(error: re.error) -> str:
    message = str(error)
    pos = error.pos if getattr(error, "pos", None) is not None else None
    if "unterminated subpattern" in message or "missing )" in message:
        if pos is not None:
            return (
                f"The opening parenthesis at character {pos + 1} "
                "does not have a closing parenthesis."
            )
        return (
            "The search pattern has an opening parenthesis "
            "that does not have a closing parenthesis."
        )
    if "unterminated character set" in message or "missing ]" in message:
        if pos is not None:
            return (
                f"The character class starting at character {pos + 1} is missing a closing bracket."
            )
        return "The search pattern has a character class that is missing a closing bracket."
    if "nothing to repeat" in message:
        if pos is not None:
            return f"The repeat marker at character {pos + 1} has nothing to repeat."
        return "A repeat marker has nothing to repeat."
    if "bad escape" in message:
        return "The search pattern uses an invalid escape sequence."
    if "invalid group reference" in message:
        return "The replacement refers to a capture group that the search pattern does not define."
    return "The regular expression is invalid."
