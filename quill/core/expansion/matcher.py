"""Match the typed-character buffer against the shared abbreviation library.

The library is exactly the one QUILL's editor uses
(:mod:`quill.core.abbreviations`) -- same file, same per-entry settings, no
sync and no second copy. What differs is only the input: the editor knows the
document text and a caret offset, while system-wide expansion knows a buffer of
recent keys and must say how many characters to erase.

Pure and wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from quill.core.abbreviations import (
    Abbreviation,
    AbbreviationLibrary,
    resolve_expansion,
)
from quill.core.expansion.ring_buffer import RingBuffer
from quill.core.snippets import Snippet, SnippetLibrary

#: The characters that end a word and so can fire an expansion. An entry's own
#: ``triggers`` setting then decides whether *it* accepts the one that fired.
TRIGGER_CHARS: frozenset[str] = frozenset({
    " ",
    "\t",
    "\n",
    ".",
    ",",
    ";",
    ":",
    "!",
    "?",
    ")",
    "]",
    "}",
    '"',
    "'",
})

_SPACE_TRIGGERS: frozenset[str] = frozenset({" ", "\t", "\n"})


#: A ``${input:name}`` field in a snippet body. A body with one of these is
#: handed to the shared prompt untouched -- the expander cannot ask a question
#: from inside a keyboard hook, and guessing an answer is worse than asking.
_INPUT_FIELD = re.compile(r"\$\{input:[^}]*\}")

#: ``${selection}``: the text selected in the application in front. The context
#: provider is the only thing that can read it, and it costs a round trip to
#: another process, so it is asked for ONLY once a snippet has already matched.
_SELECTION_FIELD = "${selection}"
_CURSOR_FIELD = "${cursor}"


@dataclass(slots=True)
class GlobalMatch:
    """One expansion to perform in whatever application has focus."""

    abbreviation: Abbreviation | None
    #: The expansion, with variables resolved and any ``${cursor}`` removed.
    text: str
    #: How many characters to erase before typing :attr:`text`: the length of
    #: the abbreviation only. The trigger character is *swallowed by the hook*
    #: rather than erased -- it has not reached the application yet when the
    #: match is found, and racing it with backspaces is exactly how an expander
    #: corrupts text. The worker types it back after the expansion.
    backspace_count: int
    #: Where the caret should end up, as an offset into :attr:`text`.
    cursor_offset: int
    has_cursor: bool
    #: Type one more space after the trigger character. Only set when the entry
    #: asked for a trailing space and the trigger was punctuation.
    trailing_space: bool
    #: The character that fired this expansion, retyped after the expansion so
    #: the user's own keystroke still lands where they put it.
    trigger_char: str = ""
    #: The snippet that matched, when this expansion came from the snippet
    #: library rather than the abbreviation library. Exactly one of
    #: :attr:`abbreviation` and this is set.
    snippet: Snippet | None = None
    #: The body as authored, before any substitution. Equal to :attr:`text` for
    #: a snippet the expander handed on to the shared prompt untouched.
    template: str = ""
    #: What the context provider actually returned and this expansion used, as
    #: a stable tuple so a match can be compared and logged.
    context_values: tuple[tuple[str, str], ...] = field(default_factory=tuple)


def apply_typed_case(typed: str, expansion: str) -> str:
    """Carry the case the user typed over to *expansion*.

    Typing "BTW" gives "BY THE WAY" and "Btw" gives "By The Way", while the
    ordinary "btw" is left exactly as the entry defines it. Only applies to
    case-insensitive entries -- a case-sensitive entry matched one exact
    spelling, so its expansion is used verbatim.
    """
    if len(typed) > 1 and typed.isupper():
        return expansion.upper()
    if typed.istitle():
        return " ".join(word.capitalize() for word in expansion.split(" "))
    return expansion


def _matching_snippet(
    text: str, token_end: int, snippet_library: SnippetLibrary | None
) -> tuple[Snippet, int] | None:
    """The snippet whose trigger the buffer just finished typing, and its length.

    Matched against the raw buffer rather than the abbreviation token, because a
    snippet trigger conventionally *starts* with punctuation (``;wrap``) and the
    token scan stops at punctuation by design. Longest trigger wins, and the
    character before it must be a boundary so ``foo;wrap`` does not fire.
    """
    if snippet_library is None:
        return None
    typed = text[:token_end]
    candidates = sorted(
        (s for s in snippet_library.snippets if s.enabled and s.trigger),
        key=lambda s: len(s.trigger),
        reverse=True,
    )
    for snippet in candidates:
        if not typed.endswith(snippet.trigger):
            continue
        before = typed[: -len(snippet.trigger)]
        if before and not before[-1].isspace():
            continue
        return snippet, len(snippet.trigger)
    return None


def _expand_snippet(
    snippet: Snippet,
    context: Mapping[str, str] | None,
) -> tuple[str, int, bool, tuple[tuple[str, str], ...]] | None:
    """``(text, cursor_offset, has_cursor, context_values)``, or ``None`` to decline.

    Two rules, both about not guessing:

    * a body carrying an ``${input:...}`` field is returned **verbatim**, for
      the shared prompt to fill in -- a keyboard hook cannot ask a question, and
      a snippet silently expanded with its questions unanswered is worse than
      one that waits;
    * a body needing ``${selection}`` with no selection available does not match
      at all, rather than expanding to a hole where the selected text should be.
    """
    body = snippet.body
    if _INPUT_FIELD.search(body):
        return body, len(body), False, ()

    values: dict[str, str] = {}
    text = body
    if _SELECTION_FIELD in body:
        selection = (context or {}).get("selection")
        if selection is None:
            return None
        values["selection"] = selection
        text = text.replace(_SELECTION_FIELD, selection)

    cursor_index = text.find(_CURSOR_FIELD)
    has_cursor = cursor_index != -1
    if has_cursor:
        text = text.replace(_CURSOR_FIELD, "", 1)
        cursor_offset = cursor_index
    else:
        cursor_offset = len(text)
    return text, cursor_offset, has_cursor, tuple(values.items())


def match_buffer(
    buffer: RingBuffer,
    library: AbbreviationLibrary,
    clipboard_text: str = "",
    *,
    process_name: str = "",
    snippet_library: SnippetLibrary | None = None,
    snippet_context_provider: Callable[[], Mapping[str, str]] | None = None,
) -> GlobalMatch | None:
    """Return the expansion the buffer's last word just triggered, if any.

    The buffer must end with a trigger character. The buffer is not modified --
    the caller clears it when it acts on the result.

    *process_name* is the application in front, so an entry scoped to particular
    applications (``Abbreviation.apps``) only fires in one of them. A signature
    belongs in a mail client and a code snippet in an editor, and an expander
    that fires both everywhere is one people switch off.

    *snippet_library* adds the snippet library as a second source of triggers,
    finishing the half that landed in ``3aaa96b`` with its tests and without its
    implementation. **A user's own abbreviation wins a same-trigger collision**:
    the abbreviation library is the one a person edits directly, and a snippet
    quietly shadowing an entry somebody wrote themselves is the wrong way round.

    *snippet_context_provider* reads what is selected in the application in
    front. It is called **only after a snippet has matched**, because reading
    another process's selection is a cross-process round trip and doing it on
    every space would make typing feel heavy for a feature that fires rarely.
    """
    text = buffer.text()
    if len(text) < 2:
        return None
    trigger_char = text[-1]
    if trigger_char not in TRIGGER_CHARS:
        return None

    token_end = len(text) - 1
    token_start = token_end
    while token_start > 0:
        previous = text[token_start - 1]
        if previous.isspace() or previous in TRIGGER_CHARS:
            break
        token_start -= 1
    if token_start >= token_end:
        return None
    token = text[token_start:token_end]

    # Longest abbreviation wins, so "addr" cannot be shadowed by "ad".
    for entry in sorted(library.enabled_only(), key=lambda a: len(a.abbreviation), reverse=True):
        if not entry.accepts_trigger(trigger_char):
            continue
        if not entry.matches_app(process_name):
            continue
        if entry.case_sensitive:
            if token != entry.abbreviation:
                continue
        elif token.lower() != entry.abbreviation.lower():
            continue
        resolved, cursor_offset, has_cursor = resolve_expansion(entry.expansion, clipboard_text)
        if not entry.case_sensitive:
            cased = apply_typed_case(token, resolved)
            # Case folding must not move the caret marker, so only take it when
            # the length is unchanged (it always is for ASCII, and this keeps a
            # locale-specific surprise from misplacing the caret).
            if len(cased) == len(resolved):
                resolved = cased
        return GlobalMatch(
            abbreviation=entry,
            text=resolved,
            backspace_count=len(token),
            cursor_offset=cursor_offset,
            has_cursor=has_cursor,
            trailing_space=entry.trailing_space and trigger_char not in _SPACE_TRIGGERS,
            trigger_char=trigger_char,
        )

    # Snippets only after every abbreviation has been offered the trigger.
    found = _matching_snippet(text, token_end, snippet_library)
    if found is None:
        return None
    snippet, trigger_length = found
    context = snippet_context_provider() if snippet_context_provider is not None else None
    expanded = _expand_snippet(snippet, context)
    if expanded is None:
        return None
    resolved, cursor_offset, has_cursor, values = expanded
    return GlobalMatch(
        abbreviation=None,
        text=resolved,
        backspace_count=trigger_length,
        cursor_offset=cursor_offset,
        has_cursor=has_cursor,
        trailing_space=False,
        trigger_char=trigger_char,
        snippet=snippet,
        template=snippet.body,
        context_values=values,
    )
