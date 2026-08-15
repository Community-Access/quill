"""Did a browse come back empty, or come back broken?

A branch that returns nothing has two completely different meanings, and reading
one as the other is how a listener concludes a working source is broken -- or
worse, that a broken one is simply empty and stops trying. :func:`browse` never
raises for a source problem, precisely so a bad directory cannot take the window
with it, which means the *reason* has to be recorded somewhere for the caller to
ask about.

That is this module. It was promised in ``browse``'s own docstring long before
it existed, which is exactly the kind of thing that misleads whoever reads the
code next.

**Per thread, deliberately.** The browse tree fetches on the task manager while
other code may be browsing elsewhere; a single shared slot would let one
branch's failure describe another branch's empty folder, which is a worse lie
than saying nothing.

wx-free, strict-typed.
"""

from __future__ import annotations

import http.client
import socket
import ssl
import threading
import urllib.error

#: The last browse failure on each thread, so a caller can ask whether an empty
#: result was *empty* or *broken*. Per thread because the tree fetches on the
#: task manager while other code may browse elsewhere, and a shared slot would
#: let one branch's failure describe another branch's empty folder.
LAST_FAILURE: dict[int, BaseException] = {}


def _thread_key() -> int:
    return threading.get_ident()


def remember_failure(error: BaseException) -> None:
    LAST_FAILURE[_thread_key()] = error


def last_error_was_network(error: BaseException | None = None) -> bool:
    """Whether this thread's most recent :func:`browse` failed on the network.

    Promised in :func:`browse`'s docstring long before it existed, which is
    exactly the kind of thing that misleads whoever reads it next. It exists
    now, and the dialog uses it to tell "this folder is empty" apart from "this
    source could not be reached" -- reading the second as the first is how a
    listener concludes a working source is broken, or the reverse.
    """
    failure = error if error is not None else LAST_FAILURE.get(_thread_key())
    if failure is None:
        return False
    return isinstance(
        failure,
        urllib.error.URLError
        | TimeoutError
        | ssl.SSLError
        | socket.gaierror
        | http.client.HTTPException
        | ConnectionError
        | OSError,
    )
