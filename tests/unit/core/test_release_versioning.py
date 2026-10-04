"""GATE-VERSORT: one version order for every spelling the family uses.

Release-channels plan 2.3. Pure semver would put ``3.3.0-dev.1`` *after*
``3.3.0-beta.1`` (ASCII); the family's order is PEP 440's -- dev < alpha <
beta < rc < final -- with semver spelling in tags. The old parsers tied two
Dev builds from one day, made every pre-release of a version equal, and read
``quill-radio-v3.0.4`` as ``0.0.0``; each of those has a row here.
"""

from __future__ import annotations

import itertools
import re
from types import SimpleNamespace

import pytest

from quill.core.updates import is_newer_version, select_latest
from quill.core.versioning import ReleaseVersion, is_newer, sort_key
from quill.core.versioning import select_latest as select_latest_by_version

#: Strictly increasing. Every pair is checked both ways.
ORDERED = [
    "3.2.0",
    "3.3.0-dev.20261003.1",
    "3.3.0-dev.20261003.2",
    "3.3.0-dev.20261004.1",
    "3.3.0-alpha.1",
    "3.3.0-beta.1",
    "3.3.0-beta.1.post1",
    "3.3.0-beta.2",
    "3.3.0-rc.1",
    "3.3.0",
    "3.3.1-dev.20261020.1",
    "3.10.0",
]


@pytest.mark.parametrize(("lower", "higher"), list(itertools.combinations(ORDERED, 2)))
def test_every_pair_sorts_in_family_order(lower: str, higher: str) -> None:
    assert ReleaseVersion.parse(lower) < ReleaseVersion.parse(higher)
    assert is_newer(lower, higher)
    assert not is_newer(higher, lower)


@pytest.mark.parametrize(
    ("spelling", "same_as"),
    [
        ("quill-radio-v3.3.0-beta.2", "3.3.0-beta.2"),
        ("quill-lite-v1.1.2", "1.1.2"),
        ("v0.9.0-beta.3", "0.9.0-beta.3"),
        ("1.0.0b1", "1.0.0-beta.1"),
        ("1.0.0rc2", "1.0.0-rc.2"),
        ("1.0.0.dev20261003", "1.0.0-dev.20261003"),
        ("0.8.0b1.post1", "0.8.0 Beta 1A"),
        ("1.0.0 Beta 1", "1.0.0-beta.1"),
        ("1.0.0 Release Candidate 2", "1.0.0-rc.2"),
        ("1.0.0 Dev", "1.0.0-dev"),
        ("1.2.0-rc1", "1.2.0-rc.1"),
    ],
)
def test_every_spelling_means_the_same_release(spelling: str, same_as: str) -> None:
    assert ReleaseVersion.parse(spelling).same_release(ReleaseVersion.parse(same_as))


def test_build_metadata_is_identity_not_order() -> None:
    a = ReleaseVersion.parse("3.3.0-dev.20261003.1+g1a2b3c4")
    b = ReleaseVersion.parse("3.3.0-dev.20261003.1+g9f9f9f9")
    assert a.same_release(b)
    assert a != b
    assert not a < b and not b < a


def test_display_is_what_a_screen_reader_should_say() -> None:
    assert ReleaseVersion.parse("3.3.0-beta.2").display() == "3.3.0 Beta 2"
    assert ReleaseVersion.parse("1.0.0rc1").display() == "1.0.0 Release Candidate 1"
    assert ReleaseVersion.parse("0.8.0b1.post1").display() == "0.8.0 Beta 1A"
    assert ReleaseVersion.parse("quill-radio-v3.0.4").display() == "3.0.4"


def test_tag_and_semver_round_trip() -> None:
    version = ReleaseVersion.parse("3.3.0 Beta 2")
    assert version.semver() == "3.3.0-beta.2"
    assert version.tag("radio") == "quill-radio-v3.3.0-beta.2"
    assert version.tag("quill") == "v3.3.0-beta.2"
    assert ReleaseVersion.parse(version.semver()).same_release(version)


def test_not_a_version_sorts_first_and_never_raises() -> None:
    assert ReleaseVersion.try_parse("runtime-latest") is None
    assert ReleaseVersion.try_parse("") is None
    assert sort_key("nonsense") < sort_key("0.0.1-dev")
    with pytest.raises(ValueError):
        ReleaseVersion.parse("nonsense")


def test_the_old_wrappers_agree_with_the_new_order() -> None:
    # Every existing caller of updates.is_newer_version keeps working.
    for lower, higher in itertools.combinations(ORDERED, 2):
        assert is_newer_version(lower, higher), (lower, higher)
        assert not is_newer_version(higher, lower), (lower, higher)


def test_select_latest_is_by_version_never_by_list_order() -> None:
    # GitHub lists newest *created* first: a 3.2.1 hotfix published after a
    # 3.3.0 beta sits above it, and a stable 3.0.4 re-upload above both.
    listed = [
        SimpleNamespace(version="3.0.4", prerelease=False, has_platform_asset=True),
        SimpleNamespace(version="3.2.1", prerelease=False, has_platform_asset=True),
        SimpleNamespace(version="3.3.0-beta.1", prerelease=True, has_platform_asset=True),
        SimpleNamespace(version="3.2.0", prerelease=False, has_platform_asset=True),
    ]
    assert select_latest(listed).version == "3.2.1"  # type: ignore[arg-type,union-attr]
    assert select_latest(listed, include_prereleases=True).version == "3.3.0-beta.1"  # type: ignore[arg-type,union-attr]
    picked = select_latest_by_version(listed, version_of=lambda r: r.version)
    assert picked is not None and picked.version == "3.2.1"


def test_select_latest_skips_what_does_not_parse() -> None:
    items = ["runtime-latest", "assets-v1", "1.0.0"]
    assert select_latest_by_version(items, version_of=str) == "1.0.0"


# -- build numbers (2026-10) --------------------------------------------------
#
# The same release number can ship more than once: a rebuild of 3.2.0 with a
# fix is 3.2.0+2, and it must be offered to everyone on 3.2.0+1. The build
# breaks ties when everything else is equal; build 0 is every release made
# before build numbers existed.

BUILDS_ORDERED = [
    "3.1.1",
    "3.2.0-rc.1",
    "3.2.0-rc.1+40",
    "3.2.0",
    "3.2.0+1",
    "3.2.0+2",
    "3.2.0+12",
    "3.2.1-dev.20261010.1",
    "3.2.1",
]


@pytest.mark.parametrize(("lower", "higher"), list(itertools.combinations(BUILDS_ORDERED, 2)))
def test_a_build_breaks_ties_and_nothing_else(lower: str, higher: str) -> None:
    assert ReleaseVersion.parse(lower) < ReleaseVersion.parse(higher)
    assert is_newer(lower, higher)
    assert is_newer_version(lower, higher)
    assert not is_newer(higher, lower)


@pytest.mark.parametrize(
    ("spelling", "same_as"),
    [
        ("3.2.0-build.12", "3.2.0+12"),
        ("quill-radio-v3.2.0-build.12", "3.2.0+12"),
        ("v1.0.0-build.2", "1.0.0+2"),
        ("3.3.0-beta.2.build.5", "3.3.0-beta.2+5"),
        ("3.2.0 (build 12)", "3.2.0+12"),
        ("1.0.0 Beta 1 (build 3)", "1.0.0-beta.1+3"),
        ("3.2.0+12.g1a2b3c4", "3.2.0+12"),
        ("3.2.0+build.12", "3.2.0+12"),
        ("quill-lite-v1.2.0+3", "1.2.0+3"),
    ],
)
def test_every_spelling_of_a_build_means_the_same_build(spelling: str, same_as: str) -> None:
    assert ReleaseVersion.parse(spelling).same_release(ReleaseVersion.parse(same_as))
    assert ReleaseVersion.parse(spelling).build == ReleaseVersion.parse(same_as).build > 0


def test_commit_metadata_is_still_not_a_build() -> None:
    dev = ReleaseVersion.parse("3.3.0-dev.20261003.1+g1a2b3c4")
    assert dev.build == 0 and dev.local == "g1a2b3c4"
    assert ReleaseVersion.parse("3.2.0+g9f9f9f9").same_release(ReleaseVersion.parse("3.2.0"))


def test_the_spellings_of_a_build() -> None:
    build = ReleaseVersion.parse("3.2.0+12")
    assert build.semver() == "3.2.0+12"
    assert build.tag_version() == "3.2.0-build.12"
    assert build.tag("radio") == "quill-radio-v3.2.0-build.12"
    assert build.tag("quill") == "v3.2.0-build.12"
    assert build.display() == "3.2.0 (build 12)"
    assert build.display(with_build=False) == "3.2.0"
    assert build.plain() == "3.2.0"
    assert build.file_version() == "3.2.0.12"
    beta = ReleaseVersion.parse("3.3.0-beta.2+5")
    assert beta.tag_version() == "3.3.0-beta.2.build.5"
    assert beta.display() == "3.3.0 Beta 2 (build 5)"
    assert ReleaseVersion.parse(beta.tag_version()).same_release(beta)
    assert ReleaseVersion.parse("3.2.0").file_version() == "3.2.0.0"
    assert ReleaseVersion.parse("3.2.0+12.g1a2b3c").semver() == "3.2.0+12.g1a2b3c"


def test_with_build_and_file_version_helpers() -> None:
    from quill.core.versioning import display_version, file_version, with_build

    assert with_build("3.2.0", 2) == "3.2.0+2"
    assert with_build("3.2.0", 0) == "3.2.0"
    assert with_build("3.2.0", None) == "3.2.0"
    assert with_build("not a version", 3) == "not a version"
    assert with_build("1.0.0 Beta 1", "4") == "1.0.0-beta.1+4"
    assert file_version("3.2.0", 7) == "3.2.0.7"
    assert file_version("3.3.0-beta.2+5") == "3.3.0.5"
    assert display_version("1.0.0+1") == "1.0.0 (build 1)"
    assert display_version("") == ""


def test_same_number_ignores_only_the_build() -> None:
    one, two = ReleaseVersion.parse("3.2.0+1"), ReleaseVersion.parse("3.2.0-build.2")
    assert one.same_number(two) and not one.same_release(two)
    assert not one.same_number(ReleaseVersion.parse("3.2.1+1"))
    assert one.without_build() == ReleaseVersion.parse("3.2.0")


def test_select_latest_takes_the_newest_build() -> None:
    listed = [
        SimpleNamespace(version="3.2.0-build.1", prerelease=False, has_platform_asset=True),
        SimpleNamespace(version="3.2.0-build.2", prerelease=False, has_platform_asset=True),
        SimpleNamespace(version="3.1.1", prerelease=False, has_platform_asset=True),
    ]
    assert select_latest(listed).version == "3.2.0-build.2"  # type: ignore[arg-type,union-attr]


# The parser every copy installed before 2026-10 carries (quill/core/updates.py
# at eb4ef6b, with the tag reader in front of it), frozen here so the tag
# spelling is checked against what those copies actually do. It is why a
# build is tagged ``-build.N`` and never ``+N``.


def _old_app_version_from_tag(tag: str) -> str:
    match = re.search(r"(\d+\.\d+(?:\.\d+)?(?:[-.][0-9A-Za-z.]+)?)\s*$", tag or "")
    return match.group(1) if match else (tag or "").strip()


def _old_version_tuple(value: str) -> tuple[int, int, int, tuple[int, int, int]]:
    cleaned = value.strip().lstrip("v")
    core, separator, suffix = cleaned.partition("-")
    parts = core.split(".")
    integers = [
        int("".join(c for c in (parts[i] if i < len(parts) else "") if c.isdigit()) or "0")
        for i in range(3)
    ]
    if not separator:
        return integers[0], integers[1], integers[2], (9, 0, 0)
    lowered = suffix.strip().lower()
    tier = 2 if lowered.startswith("rc") else 1 if lowered.startswith(("beta", "b")) else 0
    number_match = re.search(r"(\d+)", lowered)
    return (
        integers[0],
        integers[1],
        integers[2],
        (tier, int(number_match.group(1)) if number_match else 0, 0),
    )


def _old_sees(installed: str, tag: str) -> bool:
    """Whether a pre-build-number copy on *installed* is offered *tag*."""
    return _old_version_tuple(_old_app_version_from_tag(tag)) > _old_version_tuple(installed)


def test_a_copy_on_an_older_release_is_offered_a_rebuild() -> None:
    # The guarantee build numbers must keep for copies already installed.
    assert _old_sees("3.1.1", "quill-radio-v3.2.0-build.2")
    assert _old_sees("3.0.4", "quill-radio-v3.2.0-build.1")
    assert _old_sees("1.1.2", "quill-lite-v1.2.0-build.1")
    assert _old_sees("0.9.0-beta.3", "v1.0.0-build.1")
    # And among two builds of the newer release, the later build wins for them too.
    old_key = _old_version_tuple
    assert old_key(_old_app_version_from_tag("quill-radio-v3.2.0-build.2")) > old_key(
        _old_app_version_from_tag("quill-radio-v3.2.0-build.1")
    )


def test_a_plus_in_a_tag_would_have_broken_installed_copies() -> None:
    """The reason tags spell ``-build.N``: to an installed copy, ``+N`` in a
    sibling tag is not a version at all, and in QUILL's own tag it is a patch."""
    assert not _old_sees("3.1.1", "quill-radio-v3.2.0+2")  # read as 0.0.0: never offered
    assert _old_version_tuple("1.0.0+2")[:3] == (1, 0, 2)  # read as 1.0.2: wrongly newer


def test_a_copy_already_on_that_number_is_not_offered_the_rebuild() -> None:
    """Accepted: an old copy at 3.2.0 reads -build.2 as a pre-release of 3.2.0.
    Its next update to a later release brings it the build-aware parser."""
    assert not _old_sees("3.2.0", "quill-radio-v3.2.0-build.2")
    assert _old_sees("3.2.0", "quill-radio-v3.2.1-build.1")
