"""Is this file one you can save back? Asked at open, in both editors.

Neither editor looked. You could open a file from a read-only share, or one
Windows had marked read-only, type for twenty minutes and find out at `Ctrl+S`
-- which is the worst possible moment and the one where the answer costs the
most (bad.md P2.12).

The check is deliberately about *writing the file back*, not about the file's
attributes in general: a file inside a folder you cannot write to is one you
cannot save, whatever the file itself says, and a file that does not exist yet
is not read-only -- it is new.

wx-free, so both editors ask the same question and say the same sentence.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["READ_ONLY_NOTICE", "is_read_only"]

#: What to say on open. It names the consequence rather than the state --
#: "read-only" is a word people read past, and "Save As" is the thing they will
#: actually need.
READ_ONLY_NOTICE = "This file is read-only. Editing is allowed; saving will need Save As."


def is_read_only(path: Path | str | None) -> bool:
    """Whether *path* exists and cannot be written back.

    ``False`` for ``None``, for a path that does not exist (a new document is
    not read-only), and whenever the question cannot be answered -- a guess in
    that direction merely says nothing, where the other direction would refuse
    a save somebody could have made.
    """
    if path is None:
        return False
    target = Path(path)
    try:
        if not target.exists():
            return False
        if target.is_file():
            return not os.access(target, os.W_OK)
        return False
    except OSError:
        return False
