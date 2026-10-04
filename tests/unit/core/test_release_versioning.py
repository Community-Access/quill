"""GATE-VERSORT: one version order for every spelling the family uses.

Release-channels plan 2.3. Pure semver would put ``3.3.0-dev.1`` *after*
``3.3.0-beta.1`` (ASCII); the family's order is PEP 440's -- dev < alpha <
beta < rc < final -- with semver spelling in tags. The old parsers tied two
Dev builds from one day, made every pre-release of a version equal, and read
``quill-radio-v3.0.4`` as ``0.0.0``; each of those has a row here.
"""

from __future__ import annotations

import itertools
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
