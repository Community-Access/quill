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
order -- **except a build number**, below. Pure semver would compare pre-release
labels as ASCII and put ``3.3.0-dev.1`` *after* ``3.3.0-beta.1`` -- wrong for us,
because a Dev build is the least finished thing we make.

    3.3.0-dev.20261003.2 < 3.3.0-beta.1 < 3.3.0-rc.1 < 3.3.0 < 3.3.1-dev.20261004.1

**Build numbers (2026-10).** The same release number can ship more than once:
a rebuild of 3.2.0 with a fix is ``3.2.0+2``, and it must be offered to people
who have ``3.2.0+1``. So a *numeric* first identifier after ``+`` is the build
number, and it breaks ties when everything else is equal::

    3.2.0-rc.1+40 < 3.2.0 (build 0, every build-less release so far)
                  < 3.2.0+1 < 3.2.0+2 < 3.2.1

Non-numeric metadata (``+g1a2b3c4``, a commit) is still identity only. The
canonical spelling is ``X.Y.Z[-pre.N]+B``; people hear ``3.2.0 (build 12)``
(:meth:`ReleaseVersion.display`). **Tags spell the build as a pre-release
identifier instead** -- ``quill-radio-v3.2.0-build.12``,
``v1.1.0-beta.1.build.3`` (:meth:`ReleaseVersion.tag_version`) -- because the
copies already installed read a ``+`` in a tag as part of the patch number
(``v1.0.0+2`` was 1.0.2 to them) or not as a version at all, while
``-build.12`` reads to them as a pre-release of 3.2.0: newer than anything they
have on an older release, and never wrongly newer than a later one.
docs/release-channels-plan.md (2.3) has the whole decision.

Accepted spellings, all of which mean the same kind of thing:

* tags: ``quill-radio-v3.3.0-beta.2``, ``v1.0.0``
* semver-shaped: ``3.3.0-beta.2``, ``3.3.0-dev.20261003.1+g1a2b3c4``, ``1.2.0-rc1``
* PEP 440: ``1.0.0b1``, ``1.0.0rc2``, ``1.0.0.dev20261003``, ``0.8.0b1.post1``
* display: ``1.0.0 Beta 1``, ``1.0.0 Release Candidate 2``, ``1.0.0 Dev``,
  ``0.8.0 Beta 1A`` (an interim hand-off build between Beta 1 and Beta 2),
  ``3.2.0 (build 12)``
* builds: ``3.2.0+12``, ``3.2.0+12.g1a2b3c4``, ``3.2.0-build.12``,
  ``3.3.0-beta.2.build.5``, ``quill-radio-v3.2.0-build.12``

An interim letter (``Beta 1A``) and a ``.postN`` both land in :attr:`post`, which
sorts after the plain pre-release and before the next one, exactly as the old
parser promised testers.

wx-free and dependency-free: build scripts, gates and the update client all
import it.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from typing import Literal

__all__ = [
    "STAGES",
    "ReleaseVersion",
    "Stage",
    "VersionKey",
    "display_version",
    "file_version",
    "is_newer",
    "select_latest",
    "sort_key",
    "with_build",
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
#: The tag and display spellings of a build number, at the end of what follows
#: the base: ``-build.12``, ``.build.5`` after a pre-release, `` (build 12)``.
_BUILD_RE = re.compile(r"(?:^|[\s.\-_(]+)build[\s.\-_]*(\d+)\s*\)?\s*$", re.I)
#: A build number at the start of ``+`` metadata: ``+12``, ``+12.g1a2b3c``,
#: ``+build.12``.
_LOCAL_BUILD_RE = re.compile(r"^(?:build[.\-_]?)?(\d+)(?:[.\-_](.*))?$", re.I)

#: The sort key: base, stage rank, pre-release numbers, interim, build.
VersionKey = tuple[tuple[int, int, int], int, tuple[int, ...], int, int]


@dataclass(frozen=True)
class ReleaseVersion:
    """A parsed version. Compare with ``<``; :meth:`key` is the sort key.

    Equality is identity (it includes :attr:`local`); ordering ignores
    :attr:`local`, as PEP 440 does, but counts :attr:`build`: 0 means "no build
    number", which is every release made before build numbers existed.
    """

    base: tuple[int, int, int]
    stage: Stage = "final"
    numbers: tuple[int, ...] = ()
    post: int = 0
    local: str = ""
    build: int = 0

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
        build = 0
        local = local.strip()
        local_build = _LOCAL_BUILD_RE.match(local) if local else None
        if local_build is not None:
            build = int(local_build.group(1))
            local = (local_build.group(2) or "").strip()
        base_match = _BASE_RE.match(value)
        if base_match is None:
            raise ValueError(f"{raw!r} is not a version (expected e.g. '3.3.0-beta.2')")
        base = (
            int(base_match.group(1)),
            int(base_match.group(2) or 0),
            int(base_match.group(3) or 0),
        )
        rest = value[base_match.end() :].strip().lstrip("-._ ").strip()
        tag_build = _BUILD_RE.search(rest)
        if tag_build is not None:
            build = build or int(tag_build.group(1))
            rest = rest[: tag_build.start()].strip().rstrip("-._ ").strip()
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
        return cls(
            base=base, stage=stage, numbers=numbers, post=post, local=local.strip(), build=build
        )

    @classmethod
    def try_parse(cls, text: str) -> ReleaseVersion | None:
        """:meth:`parse`, or ``None`` for text that is not a version."""
        try:
            return cls.parse(text)
        except ValueError:
            return None

    # -- ordering ----------------------------------------------------------

    def key(self) -> VersionKey:
        return (self.base, _RANK[self.stage], self.numbers, self.post, self.build)

    def __lt__(self, other: ReleaseVersion) -> bool:
        return self.key() < other.key()

    def __le__(self, other: ReleaseVersion) -> bool:
        return self.key() <= other.key()

    def __gt__(self, other: ReleaseVersion) -> bool:
        return self.key() > other.key()

    def __ge__(self, other: ReleaseVersion) -> bool:
        return self.key() >= other.key()

    def same_release(self, other: ReleaseVersion) -> bool:
        """Equal for ordering purposes: the same build of the same version
        (commit metadata ignored)."""
        return self.key() == other.key()

    def same_number(self, other: ReleaseVersion) -> bool:
        """The same release number, whatever the build: ``3.2.0+1`` and ``3.2.0+2``."""
        return self.without_build().key() == other.without_build().key()

    def without_build(self) -> ReleaseVersion:
        """This version with no build number (build 0)."""
        return replace(self, build=0)

    def with_build(self, build: int) -> ReleaseVersion:
        """This version as build *build* (0 or less means no build number)."""
        return replace(self, build=max(0, int(build)))

    # -- facts -------------------------------------------------------------

    @property
    def is_prerelease(self) -> bool:
        return self.stage != "final"

    @property
    def base_text(self) -> str:
        return ".".join(str(part) for part in self.base)

    # -- spellings ---------------------------------------------------------

    def display(self, *, with_build: bool = True) -> str:
        """How a person hears it: ``3.3.0 Beta 2``, ``1.0.0 Release Candidate 1``,
        ``3.2.0 (build 12)``.

        A screen reader reads ``3.3.0-beta.2`` as a subtraction; this is the
        form every dialog shows (plan 8.1). The build is said where a person
        needs it (About, Update History, an update notice); release notes talk
        about the release, so they pass ``with_build=False``.
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
        if with_build and self.build:
            text += f" (build {self.build})"
        return text

    def plain(self) -> str:
        """The release number with no build and no metadata: ``3.2.0``,
        ``3.3.0-beta.2``. What release notes and file names say."""
        text = self.base_text
        if self.stage != "final":
            text += f"-{self.stage}"
            if self.numbers:
                text += "." + ".".join(str(n) for n in self.numbers)
        if self.post:
            text += f".post{self.post}" if self.stage != "final" else f"-post.{self.post}"
        return text

    def semver(self) -> str:
        """The canonical spelling: ``3.3.0-beta.2``, ``3.2.0+12``,
        ``3.3.0-dev.20261003.1+g1a2b3c4``."""
        text = self.plain()
        parts = [str(self.build)] if self.build else []
        if self.local:
            parts.append(self.local)
        if parts:
            text += "+" + ".".join(parts)
        return text

    def tag_version(self) -> str:
        """The version as a release tag spells it: ``3.2.0-build.12``,
        ``3.3.0-beta.2.build.5``, ``3.2.0`` (no build).

        A build becomes a pre-release identifier rather than ``+12``; the
        module docstring says why installed copies need that.
        """
        text = self.plain()
        if self.build:
            text += f".build.{self.build}" if "-" in text else f"-build.{self.build}"
        return text

    def file_version(self) -> str:
        """The Windows file version, ``X.Y.Z.B`` (``3.2.0.12``; ``3.2.0.0`` with no build)."""
        return f"{self.base_text}.{self.build}"

    def tag(self, app_key: str) -> str:
        """The release tag this version ships under for *app_key*."""
        from quill.core.release_tags import release_tag

        return release_tag(app_key, self.tag_version())

    def __str__(self) -> str:
        return self.semver()


def sort_key(text: str) -> VersionKey:
    """A sort key that never raises: text that is not a version sorts first.

    For callers that compare whatever a server sent; a malformed version must
    lose every comparison rather than crash the update check.
    """
    parsed = ReleaseVersion.try_parse(text)
    if parsed is None:
        return ((0, 0, 0), _RANK["dev"], (), 0, 0)
    return parsed.key()


def with_build(version: str, build: int | str | None) -> str:
    """*version* as build *build*, canonically spelled: ``with_build("3.2.0", 12)``
    is ``3.2.0+12``. A build of 0, ``None`` or "" leaves *version* as it is, and
    so does text that is not a version (a source checkout's odd constant must
    not crash About).
    """
    try:
        number = int(str(build).strip() or 0) if build is not None else 0
    except ValueError:
        number = 0
    parsed = ReleaseVersion.try_parse(version)
    if parsed is None or number <= 0:
        return str(version)
    return parsed.with_build(number).semver()


def display_version(version: str, *, with_build: bool = True) -> str:
    """How a person hears *version* (``3.2.0 (build 12)``); text that is not a
    version comes back unchanged."""
    parsed = ReleaseVersion.try_parse(version)
    return parsed.display(with_build=with_build) if parsed is not None else str(version)


def file_version(version: str, build: int | str | None = None) -> str:
    """``X.Y.Z.B`` for a Windows VERSIONINFO, from any spelling of *version*.

    *build*, when given, wins over a build the text carries.
    """
    parsed = ReleaseVersion.parse(with_build(version, build) if build else version)
    return parsed.file_version()


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
    best_key: VersionKey | None = None
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
