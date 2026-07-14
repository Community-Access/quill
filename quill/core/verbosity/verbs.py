"""Verb specs and the built-in verb catalog (verbosity §15).

A *verb* is a thing QUILL might announce — moving to the next line, saving a
document, hitting a search with no results. Each :class:`VerbSpec` declares the
tokens that verb can expose, its default template, its default data order, and a
:class:`Severity` that later drives per-profile suppression (a routine
confirmation is silenced in Expert; an error always speaks).

The catalog below is the initial set from verbosity §15. (The §15 prose says
"44 verbs" but enumerates 34; this module registers exactly the 34 it names. The
count is asserted from the catalog itself, not hard-coded, so the registry stays
honest if the catalog grows.)

Pure and wx-free.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from quill.core.verbosity.data_order import DataOrder
from quill.core.verbosity.tokens import TokenSpec, TokenType

__all__ = ["Severity", "VerbSpec", "BUILTIN_VERBS"]


class Severity(enum.Enum):
    """How important a verb's announcement is — drives profile suppression."""

    ROUTINE = "routine"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"
    NAVIGATION = "navigation"
    EDITING = "editing"
    DOCUMENT_STATE = "document_state"


@dataclass(frozen=True, slots=True)
class VerbSpec:
    """The verbosity contract for one announceable action."""

    id: str
    namespace: str
    human_name: str
    firing_context: str
    supported_tokens: tuple[TokenSpec, ...]
    default_template: str
    severity: Severity
    description: str = ""
    default_data_order: DataOrder | None = None


# --- Reusable token specs (shared across verbs) ---------------------------

_LINE = TokenSpec("line", TokenType.INT, "1-based line number", filters=("ordinal", "pad"))
_TOTAL = TokenSpec("total", TokenType.INT, "total line/page count", filters=("pad",))
_COLUMN = TokenSpec("column", TokenType.INT, "1-based column", filters=("ordinal", "pad"))
_WORD = TokenSpec(
    "word", TokenType.STR, "the word at the caret", filters=("upper", "lower", "title", "truncate")
)
_CHARACTER = TokenSpec("character", TokenType.STR, "the character", filters=("upper", "lower"))
_TEXT = TokenSpec("text", TokenType.STR, "the affected text", filters=("truncate",))
_COUNT = TokenSpec("count", TokenType.INT, "number of items affected", filters=("pad",))
_NAME = TokenSpec("name", TokenType.STR, "the document name", filters=("truncate",))
_QUERY = TokenSpec("query", TokenType.STR, "the search query", filters=("truncate",))
_MATCH_INDEX = TokenSpec(
    "match_index", TokenType.INT, "current match number", filters=("ordinal", "pad")
)
_MATCH_TOTAL = TokenSpec("match_total", TokenType.INT, "total matches", filters=("pad",))
_REPLACEMENTS = TokenSpec("replacements", TokenType.INT, "number replaced", filters=("pad",))
_ENCODING = TokenSpec("encoding", TokenType.STR, "the text encoding", filters=("upper",))
_MESSAGE = TokenSpec("message", TokenType.STR, "the message text", filters=("truncate",))
_PERCENT = TokenSpec("percent", TokenType.INT, "percent complete", filters=())
_PAGE = TokenSpec("page", TokenType.STR, "print-page label", filters=())


def _v(
    verb_id: str,
    human_name: str,
    firing_context: str,
    tokens: tuple[TokenSpec, ...],
    template: str,
    severity: Severity,
    *,
    order: tuple[str, ...] | None = None,
) -> VerbSpec:
    namespace = verb_id.split(".", 1)[0]
    data_order = DataOrder(verb_id, order) if order is not None else None
    return VerbSpec(
        id=verb_id,
        namespace=namespace,
        human_name=human_name,
        firing_context=firing_context,
        supported_tokens=tokens,
        default_template=template,
        severity=severity,
        default_data_order=data_order,
    )


BUILTIN_VERBS: tuple[VerbSpec, ...] = (
    # --- Navigation ---
    _v(
        "nav.next_line",
        "Next line",
        "caret moves down a line",
        (_LINE, _TOTAL, _TEXT),
        "Line {line}",
        Severity.NAVIGATION,
        order=("line", "text"),
    ),
    _v(
        "nav.previous_line",
        "Previous line",
        "caret moves up a line",
        (_LINE, _TOTAL, _TEXT),
        "Line {line}",
        Severity.NAVIGATION,
        order=("line", "text"),
    ),
    _v(
        "nav.next_word",
        "Next word",
        "caret moves to the next word",
        (_WORD, _COLUMN),
        "{word}",
        Severity.NAVIGATION,
    ),
    _v(
        "nav.previous_word",
        "Previous word",
        "caret moves to the previous word",
        (_WORD, _COLUMN),
        "{word}",
        Severity.NAVIGATION,
    ),
    _v(
        "nav.next_character",
        "Next character",
        "caret moves right one character",
        (_CHARACTER, _COLUMN),
        "{character}",
        Severity.NAVIGATION,
    ),
    _v(
        "nav.previous_character",
        "Previous character",
        "caret moves left one character",
        (_CHARACTER, _COLUMN),
        "{character}",
        Severity.NAVIGATION,
    ),
    _v(
        "nav.document_start",
        "Document start",
        "caret jumps to the top",
        (_LINE, _TOTAL),
        "Document start",
        Severity.NAVIGATION,
    ),
    _v(
        "nav.document_end",
        "Document end",
        "caret jumps to the end",
        (_LINE, _TOTAL),
        "Document end",
        Severity.NAVIGATION,
    ),
    _v(
        "nav.next_print_page",
        "Next print page",
        "caret enters the next print page",
        (_PAGE, _TOTAL),
        "Page {page}",
        Severity.NAVIGATION,
    ),
    _v(
        "nav.previous_print_page",
        "Previous print page",
        "caret enters the previous print page",
        (_PAGE, _TOTAL),
        "Page {page}",
        Severity.NAVIGATION,
    ),
    # --- Editing ---
    _v(
        "edit.insert_text",
        "Insert text",
        "text is inserted at the caret",
        (_TEXT, _COUNT),
        "{text}",
        Severity.EDITING,
    ),
    _v(
        "edit.delete_character",
        "Delete character",
        "a character is deleted",
        (_CHARACTER,),
        "Deleted {character}",
        Severity.EDITING,
    ),
    _v(
        "edit.delete_word",
        "Delete word",
        "a word is deleted",
        (_WORD,),
        "Deleted {word}",
        Severity.EDITING,
    ),
    _v(
        "edit.select_word_right",
        "Select word right",
        "selection extends one word right",
        (_WORD, _COUNT),
        "Selected {word}",
        Severity.EDITING,
    ),
    _v(
        "edit.select_line",
        "Select line",
        "the current line is selected",
        (_LINE, _COUNT),
        "Selected line {line}",
        Severity.EDITING,
    ),
    _v(
        "edit.unquote_lines",
        "Unquote lines",
        "quote markers are removed",
        (_COUNT,),
        "Unquoted {count} lines",
        Severity.EDITING,
    ),
    # --- Document ---
    _v(
        "doc.open",
        "Open document",
        "a document is opened",
        (_NAME, _ENCODING),
        "Opened {name}",
        Severity.DOCUMENT_STATE,
    ),
    _v(
        "doc.save",
        "Save document",
        "a document is saved",
        (_NAME,),
        "Saved {name}",
        Severity.DOCUMENT_STATE,
    ),
    _v(
        "doc.save_as",
        "Save as",
        "a document is saved under a new name",
        (_NAME,),
        "Saved as {name}",
        Severity.DOCUMENT_STATE,
    ),
    _v(
        "doc.modified",
        "Document modified",
        "the buffer becomes dirty",
        (_NAME,),
        "Modified",
        Severity.DOCUMENT_STATE,
    ),
    _v(
        "doc.read_only",
        "Read only",
        "a read-only document is opened",
        (_NAME,),
        "Read only",
        Severity.DOCUMENT_STATE,
    ),
    _v(
        "doc.encoding_changed",
        "Encoding changed",
        "the text encoding changes",
        (_ENCODING,),
        "Encoding {encoding}",
        Severity.DOCUMENT_STATE,
    ),
    # --- Search ---
    _v(
        "search.find",
        "Find",
        "a search runs",
        (_QUERY, _MATCH_TOTAL),
        "Found {match_total}",
        Severity.ROUTINE,
    ),
    _v(
        "search.find_next",
        "Find next",
        "the next match is selected",
        (_QUERY, _MATCH_INDEX, _MATCH_TOTAL),
        "{match_index} of {match_total}",
        Severity.ROUTINE,
    ),
    _v(
        "search.find_previous",
        "Find previous",
        "the previous match is selected",
        (_QUERY, _MATCH_INDEX, _MATCH_TOTAL),
        "{match_index} of {match_total}",
        Severity.ROUTINE,
    ),
    _v(
        "search.no_results",
        "No results",
        "a search finds nothing",
        (_QUERY,),
        "No results for {query}",
        Severity.WARNING,
    ),
    _v(
        "search.replace",
        "Replace",
        "one match is replaced",
        (_QUERY, _REPLACEMENTS),
        "Replaced {replacements}",
        Severity.ROUTINE,
    ),
    _v(
        "search.replace_all",
        "Replace all",
        "all matches are replaced",
        (_QUERY, _REPLACEMENTS),
        "Replaced {replacements}",
        Severity.ROUTINE,
    ),
    # --- System ---
    _v("system.error", "Error", "an error is reported", (_MESSAGE,), "{message}", Severity.ERROR),
    _v(
        "system.warning",
        "Warning",
        "a warning is reported",
        (_MESSAGE,),
        "{message}",
        Severity.WARNING,
    ),
    _v(
        "system.info",
        "Info",
        "an informational message is shown",
        (_MESSAGE,),
        "{message}",
        Severity.ROUTINE,
    ),
    _v(
        "system.progress",
        "Progress",
        "a long operation reports progress",
        (_MESSAGE, _PERCENT),
        "{message}",
        Severity.PROGRESS,
    ),
    _v(
        "system.operation_complete",
        "Operation complete",
        "a long operation finishes",
        (_MESSAGE, _COUNT),
        "{message}",
        Severity.ROUTINE,
    ),
    # --- Legacy passthrough ---
    _v(
        "_legacy",
        "Legacy announcement",
        "an un-migrated call site speaks",
        (_MESSAGE,),
        "{message}",
        Severity.ROUTINE,
    ),
)
