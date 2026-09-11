"""The release-tag convention, made enforceable rather than inferred.

Nine apps ship out of one repository and update independently. That only works
because each app's updater finds its own releases -- and a tag it cannot read is
a release it cannot see, which shows up as "no update available", forever, with
nothing to notice. So the convention is asserted here against the app tables it
has to agree with, rather than written down somewhere and hoped for.
"""

from __future__ import annotations

import pytest

from quill.core.app_launcher import APP_NAMES
from quill.core.companion_install import ASSET_PREFIX
from quill.core.release_tags import (
    ReleaseTag,
    is_release_tag,
    parse_release_tag,
    release_tag,
)
from quill.core.updates import _app_version_from_tag

# ---------------------------------------------------------------------------
# the shape


def test_quill_itself_keeps_the_tag_it_already_has() -> None:
    """Fourteen releases carry v<version>; rewriting them breaks every pin."""
    assert release_tag("quill", "1.0.0") == "v1.0.0"


def test_a_sibling_is_prefixed_and_named() -> None:
    assert release_tag("radio", "3.0.0") == "quill-radio-v3.0.0"
    assert release_tag("cast", "2.0.0") == "quill-cast-v2.0.0"


def test_a_pre_release_version_survives() -> None:
    assert release_tag("quill", "0.9.0-beta.3") == "v0.9.0-beta.3"


def test_a_leading_v_on_the_version_is_dropped() -> None:
    """The v in the tag is the separator; quill-radio-vv3.0.0 matches nothing."""
    assert release_tag("radio", "v3.0.0") == "quill-radio-v3.0.0"


def test_the_app_key_is_case_folded() -> None:
    assert release_tag("Radio", "3.0.0") == "quill-radio-v3.0.0"


@pytest.mark.parametrize("bad", ["", "three", "v", "3", "1.2.3.4.5-", "latest"])
def test_something_that_is_not_a_version_is_refused(bad: str) -> None:
    """A typo has to fail at build time, not on the release page."""
    with pytest.raises(ValueError):
        release_tag("radio", bad)


@pytest.mark.parametrize("bad", ["", "Quill Radio", "radio-", "9lives"])
def test_something_that_is_not_an_app_key_is_refused(bad: str) -> None:
    with pytest.raises(ValueError):
        release_tag(bad, "1.0.0")


# ---------------------------------------------------------------------------
# reading one back


def test_a_tag_round_trips() -> None:
    for app_key in APP_NAMES:
        tag = release_tag(app_key, "1.2.3")
        assert parse_release_tag(tag) == ReleaseTag(app_key, "1.2.3"), tag


def test_an_unprefixed_tag_reads_as_quills() -> None:
    assert parse_release_tag("v0.9.0-beta.3") == ReleaseTag("quill", "0.9.0-beta.3")


@pytest.mark.parametrize("other", ["runtime-latest", "assets-v1", "podcast-v1", "", "quill-radio"])
def test_a_tag_that_is_not_ours_reads_as_none(other: str) -> None:
    """None rather than a guess: half-reading a foreign tag is how a release
    nobody's updater matches gets mistaken for one."""
    assert parse_release_tag(other) is None


def test_the_existing_non_app_tags_cannot_be_mistaken_for_an_app_release() -> None:
    """runtime-latest and assets-v1 already exist in this repository."""
    for tag in ("runtime-latest", "assets-v1", "podcast-v1"):
        assert not is_release_tag(tag)


def test_is_release_tag_can_ask_about_one_app() -> None:
    assert is_release_tag("quill-radio-v3.0.0", "radio")
    assert not is_release_tag("quill-radio-v3.0.0", "cast")
    assert is_release_tag("v1.0.0", "quill")


# ---------------------------------------------------------------------------
# agreement with everything that already reads a tag


def test_every_launchable_app_has_a_distinct_tag() -> None:
    """Two apps on one tag is two releases that overwrite each other."""
    tags = [release_tag(app_key, "1.0.0") for app_key in APP_NAMES]
    assert len(set(tags)) == len(tags), tags


def test_every_app_that_publishes_assets_has_a_tag() -> None:
    for app_key in ASSET_PREFIX:
        assert is_release_tag(release_tag(app_key, "1.0.0"), app_key), app_key


def test_the_updater_can_read_the_version_out_of_every_tag() -> None:
    """``fetch_app_releases`` compares versions pulled out of the tag, so a tag
    shape it cannot read is an app that never sees an update again."""
    for app_key in APP_NAMES:
        assert _app_version_from_tag(release_tag(app_key, "3.0.0")) == "3.0.0", app_key
        assert _app_version_from_tag(release_tag(app_key, "0.9.0-beta.3")) == "0.9.0-beta.3"
