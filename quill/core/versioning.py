"""One version parser for every app in the family (release-channels plan, 2.3).

Until 2026-10 there were three: ``updates._version_tuple``, which tied two Dev
builds from the same day and read ``quill-radio-v3.0.4`` as ``0.0.0``;
``check_sibling_versions.parse_version``, which made every pre-release of a
version equal; and the build-info generator's own spelling rules. A channel
system that cannot put its own builds in order cannot decide what to offer, so
this module is the one place that knows.

**Ordering: PEP 440 semantics with semver spelling.** Within one
``major.minor.patch`` the order is ``dev < alpha < beta < rc < final``. Numeric
parts compare as numbers, so ``dev.20261003.2`` is after ``dev.20261003.1``.
Build metadata after ``+`` (``+g1a2b3c4``) is kept for identity and ignored for
order. Pure semver would compare pre-release labels as ASCII and put
``3.3.0-dev.1`` *after* ``3.3.0-beta.1`` -- wrong for us, because a Dev build is
the least finished thing we make.

    3.3.0-dev.20261003.2 < 3.3.0-beta.1 < 3.3.0-rc.1 < 3.3.0 < 3.3.1-dev.20261004.1

Accepted spellings, all of which mean the same kind of thing:

* tags: ``quill-radio-v3.3.0-beta.2``, ``v1.0.0``
* semver-shaped: ``3.3.0-beta.2``, ``3.3.0-dev.20261003.1+g1a2b3c4``, ``1.2.0-rc1``
* PEP 440: ``1.0.0b1``, ``1.0.0rc2``, ``1.0.0.dev20261003``, ``0.8.0b1.post1``
* display: ``1.0.0 Beta 1``, ``1.0.0 Release Candidate 2``, ``1.0.0 Dev``,
  ``0.8.0 Beta 1A`` (an interim hand-off build between Beta 1 and Beta 2)

An interim letter (``Beta 1A``) and a ``.postN`` both land in :attr:`post`, which
sorts after the plain pre-release and before the next one, exactly as the old
parser promised testers.

wx-free and dependency-free: build scripts, gates and the update client all
import it.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "STAGES",
    "ReleaseVersion",
    "Stage",
    "is_newer",
    "select_latest",
    "sort_key",
]

Stage = Literal["dev", "alpha", "beta", "rc", "final"]

#: Least finished first. The index is the rank.
STAGES: tuple[Stage, ...] = ("dev", "alpha", "beta", "rc", "final")
_RANK = {stage: index for index, stage in enumerate(STAGES)}

_DISPLAY_STAGE = {
    "dev": "Dev",
    "alpha": "Alpha",
    "beta": "Beta",
    "rc": "Release Candidate",
}

# Longest spellings first, so "beta" is not read as "b" followed by "eta".
_LABELS: tuple[tuple[str, Stage], ...] = (
    (r"release\s*candidate", "rc"),
    (r"preview", "rc"),
    (r"alpha", "alpha"),
    (r"beta", "beta"),
    (r"dev", "dev"),
    (r"rc", "rc"),
    (r"pre", "rc"),
    (r"a", "alpha"),
    (r"b", "beta"),
    (r"c", "rc"),
)
_LABEL_RE = re.compile(
    r"^(?:" + "|".join(f"(?P<l{i}>{pattern})" for i, (pattern, _s) in enumerate(_LABELS)) + r")",
    re.I,
)
_BASE_RE = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?")
_POST_RE = re.compile(r"[.\-_\s]*post[.\-_\s]*(\d*)", re.I)


@dataclass(frozen=True)
class ReleaseVersion:
    """A parsed version. Compare with ``<``; :meth:`key` is the sort key.

    Equality is identity (it includes :attr:`local`); ordering ignores
    :attr:`local`, as PEP 440 does.
    """

    base: tuple[int, int, int]
    stage: Stage = "final"
    numbers: tuple[int, ...] = ()
    post: int = 0
    local: str = ""

    # -- parsing -----------------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> ReleaseVersion:
        """Parse any accepted spelling, or raise :class:`ValueError`."""
        raw = str(text or "").strip()
        if not raw:
            raise ValueError("an empty string is not a version")
        value = raw
        # A tag names its app before the version; read the version part.
        from quill.core.release_tags import parse_release_tag

        tagged = parse_release_tag(value)
        if tagged is not None:
            value = tagged.version
        else:
            prefixed = re.match(r"^[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*-v(?=\d+\.\d)", value, re.I)
            if prefixed:
                value = value[prefixed.end() :]
        if value[:1] in ("v", "V") and value[1:2].isdigit():
            value = value[1:]
        value, _plus, local = value.partition("+")
        base_match = _BASE_RE.match(value)
        if base_match is None:
            raise ValueError(f"{raw!r} is not a version (expected e.g. '3.3.0-beta.2')")
        base = (
            int(base_match.group(1)),
            int(base_match.group(2) or 0),
            int(base_match.group(3) or 0),
        )
        rest = value[base_match.end() :].strip().lstrip("-._ ").strip()
        stage: Stage = "final"
        numbers: tuple[int, ...] = ()
        post = 0
        if rest:
            post_match = _POST_RE.search(rest)
            if post_match is not None:
                post = int(post_match.group(1) or 0) or 1
                rest = rest[: post_match.start()].strip()
            label_match = _LABEL_RE.match(rest) if rest else None
            if label_match is not None:
                stage = next(
                    _LABELS[int(name[1:])][1]
                    for name, hit in label_match.groupdict().items()
                    if hit is not None
                )
                tail = rest[label_match.end() :]
            elif rest:
                # Unrecognised: the earliest stage, so an unknown suffix can
                # never outrank a real build. (The old parser did the same.)
                stage = "dev"
                tail = rest
            else:
                tail = ""
            numbers = tuple(int(run) for run in re.findall(r"\d+", tail))
            letter = re.search(r"\d([a-z])\b", tail, re.I)
            if letter is not None and not post:
                post = ord(letter.group(1).lower()) - ord("a") + 1
        return cls(base=base, stage=stage, numbers=numbers, post=post, local=local.strip())

    @classmethod
    def try_parse(cls, text: str) -> ReleaseVersion | None:
        """:meth:`parse`, or ``None`` for text that is not a version."""
        try:
            return cls.parse(text)
        except ValueError:
            return None

    # -- ordering ----------------------------------------------------------

    def key(self) -> tuple[tuple[int, int, int], int, tuple[int, ...], int]:
        return (self.base, _RANK[self.stage], self.numbers, self.post)

    def __lt__(self, other: ReleaseVersion) -> bool:
        return self.key() < other.key()

    def __le__(self, other: ReleaseVersion) -> bool:
        return self.key() <= other.key()

    def __gt__(self, other: ReleaseVersion) -> bool:
        return self.key() > other.key()

    def __ge__(self, other: ReleaseVersion) -> bool:
        return self.key() >= other.key()

    def same_release(self, other: ReleaseVersion) -> bool:
        """Equal for ordering purposes (build metadata ignored)."""
        return self.key() == other.key()

    # -- facts -------------------------------------------------------------

    @property
    def is_prerelease(self) -> bool:
        return self.stage != "final"

    @property
    def base_text(self) -> str:
        return ".".join(str(part) for part in self.base)

    # -- spellings ---------------------------------------------------------

    def display(self) -> str:
        """How a person hears it: ``3.3.0 Beta 2``, ``1.0.0 Release Candidate 1``.

        A screen reader reads ``3.3.0-beta.2`` as a subtraction; this is the
        form every dialog shows (plan 8.1).
        """
        text = self.base_text
        if self.stage != "final":
            text += f" {_DISPLAY_STAGE[self.stage]}"
            if self.numbers:
                text += " " + ".".join(str(n) for n in self.numbers)
            if self.post:
                text += chr(ord("A") + self.post - 1) if self.post <= 26 else f" post {self.post}"
        elif self.post:
            text += f" post {self.post}"
        return text

    def semver(self) -> str:
        """The tag spelling: ``3.3.0-beta.2``, ``3.3.0-dev.20261003.1``."""
        text = self.base_text
        if self.stage != "final":
            text += f"-{self.stage}"
            if self.numbers:
                text += "." + ".".join(str(n) for n in self.numbers)
        if self.post:
            text += f".post{self.post}" if self.stage != "final" else f"-post.{self.post}"
        if self.local:
            text += f"+{self.local}"
        return text

    def tag(self, app_key: str) -> str:
        """The release tag this version ships under for *app_key*."""
        from quill.core.release_tags import release_tag

        return release_tag(app_key, self.semver().partition("+")[0])

    def __str__(self) -> str:
        return self.semver()


def sort_key(text: str) -> tuple[tuple[int, int, int], int, tuple[int, ...], int]:
    """A sort key that never raises: text that is not a version sorts first.

    For callers that compare whatever a server sent; a malformed version must
    lose every comparison rather than crash the update check.
    """
    parsed = ReleaseVersion.try_parse(text)
    if parsed is None:
        return ((0, 0, 0), _RANK["dev"], (), 0)
    return parsed.key()


def is_newer(current: str, available: str) -> bool:
    """True when *available* sorts after *current*."""
    return sort_key(available) > sort_key(current)


def select_latest[T](
    items: Iterable[T],
    *,
    version_of: Callable[[T], str],
    include_prereleases: bool = False,
) -> T | None:
    """The item with the highest version, by version and never by list order.

    GitHub lists releases newest *created* first, which is not the same thing:
    a 3.2.1 hotfix published after 3.3.0-beta.1, or a re-uploaded asset, moves
    a release up the list. Every "take the first stable one" shortcut this
    replaces trusted that order. Items whose version does not parse are
    skipped; pre-releases count only when *include_prereleases* is true.
    """
    best: T | None = None
    best_key: tuple[tuple[int, int, int], int, tuple[int, ...], int] | None = None
    for item in items:
        parsed = ReleaseVersion.try_parse(version_of(item))
        if parsed is None:
            continue
        if parsed.is_prerelease and not include_prereleases:
            continue
        key = parsed.key()
        if best_key is None or key > best_key:
            best, best_key = item, key
    return best
