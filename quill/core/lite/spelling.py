"""QUILL Lite's spelling: whose dictionary, and when to speak up.

The engine is QUILL's -- :mod:`quill.core.spellcheck` for the wordlist and the
suggestions, :mod:`quill.core.spelling` for the guided F7 review. Nothing about
checking a word is re-implemented here. What this module owns is the two
questions QUILL does not have to answer, because QUILL is the only editor in
its own data folder and opens documents rather than files.

**Whose dictionary.** QUILL Lite keeps its taught words in QUILL Lite's folder by
default, exactly as it keeps its abbreviations there, and for the same reason: a
machine that has never had QUILL installed must not grow a ``%APPDATA%\\Quill``
because somebody taught a text editor that "Bhattacharya" is a word. One switch
in Preferences points it at QUILL's shared dictionary instead, off by default,
and that switch is the whole of the sharing story -- there is no merge, no sync
and no copy, because a dictionary that quietly half-merged would be worse than
either honest answer.

**When to speak up.** A live spell checker is a service in a letter and an
insult in ``settings.json``, so the default follows the file's extension
(:mod:`quill.core.spellcheck_filetypes`, the rule Notepad ships). That is a
*default*, decided once when a document is opened; :func:`initial_live_check`
answers it and the window remembers the answer, so somebody who turns the check
on in a ``.py`` keeps it on for as long as that document is open.

The explicit F7 review is never gated by any of this. A default is about what
happens when nobody has said anything, and pressing F7 is saying something.

wx-free, so the tests run without a display.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.spellcheck_filetypes import is_code_filename, live_check_default_for

__all__ = [
    "add_word",
    "dictionary_dir",
    "initial_live_check",
    "load_dictionary",
    "skipped_as_code",
]


def dictionary_dir(settings: Any, data_dir: Path) -> Path:
    """The folder the personal dictionary is read from and written to.

    QUILL Lite's own unless the listener has asked, in Preferences, to share
    QUILL's -- in which case this is QUILL's data directory and a word taught
    here is taught there. Mirrors ``abbreviation_dir`` exactly, on purpose: two
    switches that behave differently would be two switches to remember.
    """
    if getattr(settings, "share_quill_dictionary", False):
        from quill.core.paths import app_data_dir

        return app_data_dir()
    return data_dir


def load_dictionary(settings: Any, data_dir: Path, document_path: Path | None) -> set[str]:
    """Every word this document should treat as correct.

    The personal list plus the document's own ``.quill-dict.json`` sidecar.
    There is no project scope: QUILL Lite opens files, not projects, and a
    checkout root is not a thing it has any way to know about.

    Never raises. A dictionary that cannot be read is an empty one, because an
    editor that refuses to open a file over a malformed word list is an editor
    somebody loses work to.
    """
    from quill.core.spellcheck import load_scope_dictionary

    personal_dir = dictionary_dir(settings, data_dir)
    words: set[str] = set()
    for scope in ("personal", "document"):
        try:
            words |= load_scope_dictionary(scope, document_path, None, personal_dir)
        except Exception:  # noqa: BLE001 - a bad dictionary must not stop the editor
            continue
    return words


def add_word(
    word: str,
    settings: Any,
    data_dir: Path,
    document_path: Path | None,
    scope: str = "personal",
) -> bool:
    """Teach *word*. ``True`` when it was written, ``False`` when it could not be.

    A read-only profile is a real situation and not an error worth a dialog, so
    the caller gets a boolean to announce rather than an exception to handle.

    ``False`` also when there was simply nowhere to write: a "this document
    only" dictionary is a file beside the document, so an unsaved buffer has
    none. That used to return ``True`` and the word stayed underlined with
    nothing said about it (bad.md S3).
    """
    from quill.core.spellcheck import add_word_to_scope

    try:
        return add_word_to_scope(
            word, scope, document_path, None, dictionary_dir(settings, data_dir)
        )
    except Exception:  # noqa: BLE001 - see the docstring
        return False


def initial_live_check(document_path: Path | None) -> bool:
    """Should this document start with spell-check-as-you-type switched on?

    Prose yes, code no, an unnamed document yes. The window keeps whatever this
    returns and the user may change it; this is only the opening answer.
    """
    return live_check_default_for(document_path)


def skipped_as_code(document_path: Path | None) -> bool:
    """True when the *reason* the check is off by default is the extension.

    Worth its own name because the answer becomes a sentence somebody hears:
    "spell check is off for this file type" is a fact they can act on, where
    silence is a bug they have to guess at.
    """
    return is_code_filename(document_path)
