"""Opening a subscription list by double-clicking it.

An OPML file is how one podcast app hands its whole subscription list to
another, and until now QUILL Cast could only receive one through a file picker
inside a dialog inside a menu. Somebody who exported from another app and has
the file sitting in Downloads should be able to open it the way they open
anything else -- which means the app has to accept a path on the command line,
and the installer has to offer to register the extension.

This is the command-line half: work out whether an argument list names a
subscription list, and which file. Wx-free and pure, so the rule is testable
without launching anything.

Three decisions:

* **Only a file that exists.** A path typed wrongly, or one whose file has since
  been moved, must open the app normally rather than showing an import flow for
  something that is not there.
* **Switches are never paths.** ``--safe-mode`` and friends share the argument
  list, and a leading dash is the one reliable way to tell them apart.
* **``.xml`` counts.** Plenty of apps export OPML with an ``.xml`` extension, and
  refusing those would fail the exact hand-off this exists for. The importer
  validates the content anyway, so a wrong guess costs a message, not a crash.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

#: Extensions a subscription list arrives with, lowercase.
OPML_SUFFIXES: frozenset[str] = frozenset({".opml", ".xml"})


def _clean(argument: str) -> str:
    """One argument as a path: trimmed, and unwrapped from a shell's quotes.

    Explorer hands a quoted path to the association's command, and some shells
    pass the quotes through into ``argv``. A path whose suffix is ``.opml"``
    matches nothing, which would silently turn a double-click into an ordinary
    launch -- the failure that is hardest to report because nothing went wrong.
    """
    return str(argument or "").strip().strip('"').strip("'")


def looks_like_opml_path(argument: str) -> bool:
    """Whether *argument* names a subscription list, by shape alone."""
    text = _clean(argument)
    if not text or text.startswith("-"):
        return False
    return Path(text).suffix.lower() in OPML_SUFFIXES


def opml_path_from_argv(argv: Sequence[str]) -> Path | None:
    """The subscription list named on the command line, if there is one.

    Returns the first argument that both looks like one and actually exists.
    Nothing else in the argument list is consumed or judged: the app's own
    switch parsing still sees everything, so this can never swallow a flag.
    """
    for argument in argv or ():
        if not looks_like_opml_path(argument):
            continue
        path = Path(_clean(argument))
        try:
            if path.is_file():
                return path
        except OSError:
            # A path the operating system will not even stat (a stale network
            # share, a name it rejects) is not a file we can import.
            continue
    return None


def opml_progid(app_id: str = "QUILLCast") -> str:
    """The registry ProgID an installer uses for the association.

    Here rather than only in the installer script so the name has one source:
    an app that registers ``QUILLCast.opml`` and an uninstaller that removes
    ``QUILLCast.OPML`` would leave a broken association behind.
    """
    return f"{app_id}.opml"


def describe_opened_file(path: Path) -> str:
    """What to say when the app opens because a file was double-clicked.

    Said before the import window appears, because the window arriving with no
    explanation is the confusing part: the app was asked to start, and instead
    of the library it usually shows, something else is in front of you.
    """
    name = os.fspath(path)
    return f"Opening the subscription list {Path(name).name}."
