"""Spanish dictation's words: punctuation now, commands drafted and switched off.

dict.md section 9.4 C and D, with the owner's answers of 2026-10-03:

**Punctuation (shipped).** "coma", "punto", "punto y coma", "dos puntos",
"abrir interrogación" and the rest write their marks -- but only while the
engine is *not* punctuating by itself (automatic punctuation off, or Windows
speech recognition). "Coma" is also a verb ("que coma") and "punto" an everyday
noun ("el punto es que..."); with automatic punctuation on, Whisper punctuates
and nobody needs to say them, so Spanish dictation just writes what you say
(option 1). "literal" before a word writes the word: "literal coma" is *coma*.

**Commands (drafted, off).** The first release is Spanish text with the
English commands (dict.md 9.8, answer 4). The table below is a first draft
**awaiting native-speaker review** and is used only when
:func:`~quill.core.windows_dictation.speech_language.spanish_commands_enabled`
says so -- a development build with ``QUILL_DICTATION_SPANISH_COMMANDS=1``.

Phrases are written here with their accents, as a reader expects; they are
matched without them (:func:`~quill.core.windows_dictation.speech_language.fold`),
because a recogniser may write "linea" or "línea".

Pure and wx-free.
"""

from __future__ import annotations

from quill.core.windows_dictation.vocabulary import (
    DASH_PLACEHOLDER,
    Command,
    CommandHelp,
    Glue,
    Mark,
)

__all__ = [
    "SPANISH_CAPITAL_WORDS",
    "SPANISH_COMMAND_HELP",
    "SPANISH_MARKS",
    "SPANISH_SPACE_WORDS",
    "spanish_mark_rows",
]

_OPEN_QUESTION = chr(0xBF)  # the inverted question mark
_OPEN_EXCLAMATION = chr(0xA1)  # the inverted exclamation mark


def _m(text: str, glue: Glue, *, ends: bool = False, spoken: str = "", group: str) -> Mark:
    # The phrase is filled in per spoken form by _rows; it is only a key there.
    return Mark((), text, glue, ends, spoken, group)


_FULL_STOP = _m(".", Glue.LEFT, ends=True, group="Puntuación")
_NEW_PARAGRAPH = _m("\n\n", Glue.BREAK, ends=True, spoken="New paragraph", group="Líneas")

#: ``(spoken forms, marks written)``, in the order the reference lists them.
#: "Punto y aparte" is a full stop *and* a new paragraph, which is why a row
#: writes a tuple of marks.
_ROWS: tuple[tuple[tuple[str, ...], tuple[Mark, ...]], ...] = (
    (("punto", "punto y seguido", "punto final"), (_FULL_STOP,)),
    (("punto y aparte",), (_FULL_STOP, _NEW_PARAGRAPH)),
    (("coma",), (_m(",", Glue.LEFT, group="Puntuación"),)),
    (("punto y coma",), (_m(";", Glue.LEFT, group="Puntuación"),)),
    (("dos puntos",), (_m(":", Glue.LEFT, group="Puntuación"),)),
    (("puntos suspensivos",), (_m("...", Glue.LEFT, group="Puntuación"),)),
    (
        (
            "abrir interrogación",
            "abre interrogación",
            "signo de interrogación abierto",
            "abrir signo de interrogación",
        ),
        (_m(_OPEN_QUESTION, Glue.OPEN, group="Puntuación"),),
    ),
    (
        (
            "cerrar interrogación",
            "cierra interrogación",
            "signo de interrogación cerrado",
            "cerrar signo de interrogación",
            "signo de interrogación",
        ),
        (_m("?", Glue.LEFT, ends=True, group="Puntuación"),),
    ),
    (
        (
            "abrir exclamación",
            "abre exclamación",
            "signo de exclamación abierto",
            "abrir signo de exclamación",
        ),
        (_m(_OPEN_EXCLAMATION, Glue.OPEN, group="Puntuación"),),
    ),
    (
        (
            "cerrar exclamación",
            "cierra exclamación",
            "signo de exclamación cerrado",
            "cerrar signo de exclamación",
            "signo de exclamación",
        ),
        (_m("!", Glue.LEFT, ends=True, group="Puntuación"),),
    ),
    (("abrir paréntesis", "abre paréntesis"), (_m("(", Glue.OPEN, group="Puntuación"),)),
    (("cerrar paréntesis", "cierra paréntesis"), (_m(")", Glue.LEFT, group="Puntuación"),)),
    (("abrir comillas", "abre comillas"), (_m('"', Glue.OPEN, group="Puntuación"),)),
    (("cerrar comillas", "cierra comillas"), (_m('"', Glue.LEFT, group="Puntuación"),)),
    (("guion", "guión"), (_m("-", Glue.JOIN, group="Puntuación"),)),
    (("guion largo", "guión largo"), (_m(DASH_PLACEHOLDER, Glue.JOIN, group="Puntuación"),)),
    (("arroba",), (_m("@", Glue.JOIN, group="Puntuación"),)),
    (
        ("nueva línea", "nuevo renglón"),
        (_m("\n", Glue.BREAK, ends=True, spoken="New line", group="Líneas"),),
    ),
    (("nuevo párrafo",), (_NEW_PARAGRAPH,)),
    (("tabulador",), (_m("\t", Glue.BREAK, spoken="Tab", group="Líneas"),)),
)

#: Every Spanish mark phrase (as written, with accents) and what it writes.
SPANISH_MARKS: dict[str, tuple[Mark, ...]] = {
    spoken: marks for forms, marks in _ROWS for spoken in forms
}


def spanish_mark_rows() -> list[tuple[str, str]]:
    """``(what to say, what it writes)`` for the reference, one row per mark."""
    rows = []
    for forms, marks in _ROWS:
        written = "".join(mark.text for mark in marks)
        rows.append((" or ".join(f'"{form}"' for form in forms), written))
    return rows


#: Spelling mode's Spanish words for a capital and a space.
SPANISH_CAPITAL_WORDS = frozenset({"mayuscula", "mayusculas"})
SPANISH_SPACE_WORDS = frozenset({"espacio"})

#: The drafted Spanish commands. **Awaiting native-speaker review; switched
#: off** -- see the module docstring. Descriptions stay in English, like the
#: rest of the interface (dict.md 9.6).
SPANISH_COMMAND_HELP: tuple[CommandHelp, ...] = (
    CommandHelp(
        Command.SCRATCH,
        ("borra eso", "borrar eso"),
        "Removes the phrase you dictated last.",
        "Correcting",
    ),
    CommandHelp(Command.UNDO, ("deshacer", "deshaz eso"), "The same as Ctrl+Z.", "Correcting"),
    CommandHelp(
        Command.SELECT,
        ("selecciona eso", "seleccionar eso"),
        "Selects the phrase you dictated last.",
        "Correcting",
    ),
    CommandHelp(
        Command.CAPITALIZE,
        ("mayúscula inicial", "primera en mayúscula"),
        "Gives every word of the last phrase a capital.",
        "Correcting",
    ),
    CommandHelp(
        Command.UPPERCASE,
        ("todo en mayúsculas", "en mayúsculas"),
        "Puts the last phrase in capitals.",
        "Correcting",
    ),
    CommandHelp(
        Command.LOWERCASE,
        ("en minúsculas", "todo en minúsculas"),
        "Puts the last phrase in small letters.",
        "Correcting",
    ),
    CommandHelp(
        Command.DELETE_WORD,
        ("borra palabra", "borra la última palabra"),
        "Deletes the word just before the cursor.",
        "Correcting",
    ),
    CommandHelp(
        Command.DELETE_SENTENCE,
        ("borra frase", "borra la última frase"),
        "Deletes from the start of the sentence up to the cursor.",
        "Correcting",
    ),
    CommandHelp(
        Command.READ_BACK,
        ("léelo", "repite eso"),
        "Reads the last phrase aloud again.",
        "Correcting",
    ),
    CommandHelp(
        Command.LINE_START,
        ("ir al principio de la línea", "inicio de línea"),
        "Moves the cursor to the start of the line.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.LINE_END,
        ("ir al final de la línea", "fin de línea"),
        "Moves the cursor to the end of the line.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.DOCUMENT_START,
        ("ir al principio", "ir al principio del documento"),
        "Moves the cursor to the start of the document.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.DOCUMENT_END,
        ("ir al final", "ir al final del documento"),
        "Moves the cursor to the end of the document.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.SPELL_ON,
        ("empieza a deletrear", "modo deletreo"),
        "Starts spelling mode.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.SPELL_OFF, ("deja de deletrear",), "Leaves spelling mode.", "Dictation itself"
    ),
    CommandHelp(
        Command.HELP,
        ("qué puedo decir", "muestra los comandos"),
        "Opens the list of commands.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.STOP,
        ("deja de dictar", "para de dictar", "detén el dictado"),
        "Stops dictation.",
        "Dictation itself",
    ),
)
