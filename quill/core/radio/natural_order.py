"""Sorting names the way a person reads them: 2 before 10.

Reported 2026-08-26: a folder listed **ACB Media 1, ACB Media 10, ACB Media 2**
and on through 9. That is what sorting text does -- ``"10"`` really is less than
``"2"`` when the comparison is character by character -- and it is wrong for
every list of names a human wrote, because the number in a station name is a
number, not a word.

The fix everyone reaches for first is to rename the stations ``ACB Media 01``.
That was explicitly refused, and rightly: it is not what the broadcaster calls
the station, so it would be wrong in the details panel, wrong when read aloud,
wrong in a favourites export, and wrong when somebody searches for the name they
actually know. The display name is the broadcaster's; the *ordering* is ours.

So the key splits a name into runs of digits and runs of everything else, and
compares digits as integers. ``ACB Media 2`` becomes ``("acb media ", 2, "")``
and ``ACB Media 10`` becomes ``("acb media ", 10, "")``, so 2 sorts first
without a character of the name changing.

Two deliberate limits. Case is folded, so ``kexp`` and ``KEXP`` sit together
rather than in two alphabets. And a digit run is compared as an integer however
long it is -- a station whose name contains a forty-digit number is not a
sorting problem anybody has.

wx-free, pure, no dependencies. Every list of names in Quill Radio that is
sorted for a human to read should use this rather than ``str.casefold``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

_DIGITS = re.compile(r"(\d+)")


def natural_key(text: object) -> tuple[object, ...]:
    """A sort key where ``2`` comes before ``10`` (pure).

    Mixed types never meet: the split alternates text, number, text, number,
    so position *n* of any two keys is always the same kind. That is what makes
    this safe as a plain ``sort(key=...)`` on arbitrary names, which the naive
    "int if it looks like one" version is not.
    """
    parts = _DIGITS.split(str(text or ""))
    return tuple(int(part) if index % 2 else part.casefold() for index, part in enumerate(parts))


def sorted_by_name(
    items: list[Any], name_of: Callable[[Any], object] = lambda item: item
) -> list[Any]:
    """*items* ordered by :func:`natural_key` of their name (pure).

    A convenience for the common case -- a list of stations sorted by
    ``station.name`` -- so call sites read as what they mean instead of
    repeating a lambda that is easy to get subtly different each time.
    """
    return sorted(items, key=lambda item: natural_key(name_of(item)))
