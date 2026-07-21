"""Tests for quill_radio_mac.core.updates.

``is_newer_version`` is exercised directly against a version-string matrix
(the pure comparison the "update available" decision hinges on, including
prerelease/interim-build ordering, per :func:`updates._version_tuple`).
``fetch_releases`` and its downstream helpers (``select_latest``,
``find_release``, ``latest_release_page_url``) are exercised against a
canned GitHub Releases API payload with the network egress function
(``_http_get_json``) monkeypatched -- no real HTTP calls, matching the
pattern used by ``tests/test_link_finder.py``.
"""

from __future__ import annotations

import pytest

from quill_radio_mac.core import updates
from quill_radio_mac.core.updates import (
    GitHubRelease,
    UpdatesError,
    fetch_releases,
    find_release,
    is_newer_version,
    latest_release_page_url,
    select_latest,
)


@pytest.mark.parametrize(
    ("current", "available", "expected"),
    [
        # Plain patch/minor/major bumps.
        ("1.0.0", "1.0.1", True),
        ("1.0.1", "1.0.0", False),
        ("1.0.0", "1.0.0", False),
        ("1.0.0", "2.0.0", True),
        ("1.0.0", "1.1.0", True),
        # A missing patch component defaults to 0, so these compare equal.
        ("1.0", "1.0.0", False),
        # A leading "v" is stripped.
        ("v1.0.0", "1.0.1", True),
        # A final release always outranks any prerelease of the same core.
        ("1.2.0", "1.2.0-rc1", False),
        ("1.2.0-rc1", "1.2.0", True),
        # Prerelease stage ordering: alpha < beta < rc.
        ("1.2.0-alpha1", "1.2.0-beta1", True),
        ("1.2.0-beta1", "1.2.0-rc1", True),
        ("1.2.0-rc1", "1.2.0-beta1", False),
        # Prerelease numbering within the same stage.
        ("1.2.0-rc1", "1.2.0-rc2", True),
        ("1.2.0-rc2", "1.2.0-rc1", False),
        ("1.2.0-rc1", "1.2.0-rc1", False),
        # Human-readable display form, as produced by a build's short version
        # string, normalizes the same as the PEP 440 hyphen form.
        ("1.2.0 Beta 1", "1.2.0 Beta 2", True),
        ("1.2.0 Release Candidate 1", "1.2.0", True),
        # Interim hand-off build ordering (upstream's display-letter rule):
        # "Beta 1" < "Beta 1A" < "Beta 2", asserted in both directions.
        ("0.8.0 Beta 1", "0.8.0 Beta 1A", True),
        ("0.8.0 Beta 1A", "0.8.0 Beta 1", False),
        ("0.8.0 Beta 1A", "0.8.0 Beta 2", True),
        ("0.8.0 Beta 2", "0.8.0 Beta 1A", False),
        # Malformed/garbage tags parse to 0.0.0, so any real version
        # outranks them and they never outrank a real version.
        ("not-a-version", "1.0.0", True),
        ("1.0.0", "not-a-version", False),
        ("", "1.0.0", True),
        ("1.0.0", "", False),
    ],
)
def test_is_newer_version_matrix(current: str, available: str, expected: bool) -> None:
    assert is_newer_version(current, available) is expected


_RELEASES_PAYLOAD = [
    {
        "tag_name": "1.3.0",
        "name": "1.3.0",
        "body": "Stable release notes",
        "published_at": "2026-06-01T00:00:00Z",
        "prerelease": False,
        "draft": False,
        "html_url": "https://github.com/Community-Access/quill-radio-mac/releases/tag/1.3.0",
    },
    {
        "tag_name": "1.4.0-rc1",
        "name": "1.4.0 Release Candidate 1",
        "body": "RC notes",
        "published_at": "2026-06-15T00:00:00Z",
        "prerelease": True,
        "draft": False,
        "html_url": "https://github.com/Community-Access/quill-radio-mac/releases/tag/1.4.0-rc1",
    },
    {
        "tag_name": "1.5.0-draft",
        "name": "Draft",
        "body": "not published yet",
        "published_at": "",
        "prerelease": False,
        "draft": True,
        "html_url": "https://github.com/Community-Access/quill-radio-mac/releases/tag/1.5.0-draft",
    },
]


def test_fetch_releases_skips_drafts_and_parses_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updates, "_http_get_json", lambda url: _RELEASES_PAYLOAD)
    releases = fetch_releases()
    assert [r.version for r in releases] == ["1.3.0", "1.4.0-rc1"]
    stable = releases[0]
    assert stable.notes == "Stable release notes"
    assert stable.published_at == "2026-06-01T00:00:00Z"
    assert stable.prerelease is False
    assert stable.html_url.endswith("/1.3.0")


def test_fetch_releases_requests_this_apps_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: dict[str, str] = {}

    def fake_http_get_json(url: str) -> object:
        requested["url"] = url
        return _RELEASES_PAYLOAD

    monkeypatch.setattr(updates, "_http_get_json", fake_http_get_json)
    fetch_releases()
    assert requested["url"] == (
        "https://api.github.com/repos/Community-Access/quill-radio-mac/releases"
    )


def test_fetch_releases_rejects_non_list_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updates, "_http_get_json", lambda url: {"not": "a list"})
    with pytest.raises(UpdatesError):
        fetch_releases()


def test_select_latest_stable_excludes_prerelease(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updates, "_http_get_json", lambda url: _RELEASES_PAYLOAD)
    releases = fetch_releases()
    stable = select_latest(releases, include_prereleases=False)
    assert stable is not None
    assert stable.version == "1.3.0"


def test_select_latest_beta_includes_prerelease(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updates, "_http_get_json", lambda url: _RELEASES_PAYLOAD)
    releases = fetch_releases()
    beta = select_latest(releases, include_prereleases=True)
    assert beta is not None
    assert beta.version == "1.4.0-rc1"


def test_select_latest_returns_none_when_no_eligible_release() -> None:
    assert select_latest([], include_prereleases=True) is None
    prerelease_only = [
        GitHubRelease(
            version="1.4.0-rc1",
            published_at="",
            notes="",
            prerelease=True,
            html_url="https://example.com/1.4.0-rc1",
        )
    ]
    assert select_latest(prerelease_only, include_prereleases=False) is None


def test_find_release_matches_by_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updates, "_http_get_json", lambda url: _RELEASES_PAYLOAD)
    releases = fetch_releases()
    found = find_release(releases, "1.3.0")
    assert found is not None
    assert found.html_url.endswith("/1.3.0")
    assert find_release(releases, "9.9.9") is None


def test_latest_release_page_url_returns_html_url() -> None:
    release = GitHubRelease(
        version="1.3.0",
        published_at="2026-06-01T00:00:00Z",
        notes="notes",
        prerelease=False,
        html_url="https://github.com/Community-Access/quill-radio-mac/releases/tag/1.3.0",
    )
    assert (
        latest_release_page_url(release)
        == "https://github.com/Community-Access/quill-radio-mac/releases/tag/1.3.0"
    )
