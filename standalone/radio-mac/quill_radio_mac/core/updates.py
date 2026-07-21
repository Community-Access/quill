"""Check GitHub Releases for newer builds of Quill Radio for Mac.

Ported from upstream ``quill.core.updates``, trimmed to the release-lookup
surface this app needs. Upstream also signs an update manifest and
downloads/launches a Windows installer or extracts a portable .zip; none
of that applies here, so it is dropped entirely (per
``.superpowers/sdd/global-constraints.md``): a macOS app has no self-run
installer to download and execute. Instead, :func:`latest_release_page_url`
hands the caller a plain browser URL -- the release's own GitHub page --
so the UI can open it and let the user download the .dmg/.pkg themselves.

``fetch_releases`` and ``is_newer_version`` are kept faithful to upstream:
same draft filtering, same JSON-array validation, and the exact same
pre-release version ordering (``_version_tuple`` / ``_prerelease_rank``,
copied verbatim from ``quill.core.updates`` since a build offered as
"newer" must sort identically on both platforms). The only behavioral
difference is the source repository, which here always comes from
:data:`quill_radio_mac.GITHUB_OWNER` / :data:`quill_radio_mac.GITHUB_REPO`
rather than a hardcoded upstream constant.

Threading contract: :func:`fetch_releases` performs one blocking HTTPS GET
-- callers run it off the UI thread, the same way
:mod:`quill_radio_mac.core.radio_browser` and
:mod:`quill_radio_mac.core.link_finder` are used. Every other function
here (``is_newer_version``, ``select_latest``, ``find_release``,
``latest_release_page_url``) is a pure, in-memory computation and safe to
call from any thread.

macOS notes: none beyond the shared verified-TLS ``urllib``/``ssl``
pattern used by every other network module in this package -- the GitHub
REST API needs no platform-specific handling.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

from quill_radio_mac import GITHUB_OWNER, GITHUB_REPO, __version__
from quill_radio_mac.core.error_codes import CodedError

_USER_AGENT = f"QuillRadioMac/{__version__}"
_TIMEOUT_SECONDS = 10.0

# Pre-release ordering: a final (non-pre-release) build outranks every
# pre-release of the same major.minor.patch. See _version_tuple / _prerelease_rank.
_STABLE_PRERELEASE_RANK = (9, 0, 0)


class UpdatesError(CodedError):
    """A GitHub release check failed (network, or an unreadable reply)."""

    code = "QUILL-RADIO-UPDATES-REQUEST"


def _releases_api_url() -> str:
    """The GitHub Releases API URL for this app's own repository."""
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


@dataclass(frozen=True, slots=True)
class GitHubRelease:
    """One published GitHub release, trimmed to what this app needs.

    Upstream's ``GitHubRelease`` also carries ``download_url`` and
    ``has_platform_asset`` for its installer-download flow. This port has
    no such flow (see the module docstring), so those fields are replaced
    by ``html_url`` -- the release's own GitHub page, returned by
    :func:`latest_release_page_url` for opening in a browser.
    """

    #: The release's tag, e.g. "1.3.0" or "1.4.0-rc1".
    version: str
    published_at: str
    notes: str
    prerelease: bool
    html_url: str


def _http_get_json(url: str) -> object:
    """One HTTPS GET returning decoded JSON -- the reviewed egress site.

    Certificates are always fully verified (the default ``ssl`` context).
    Tests monkeypatch this function directly rather than mocking
    ``urlopen``, the same pattern used by ``radio_browser._http_json`` and
    ``link_finder._http_get_text``.
    """
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": _USER_AGENT},
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload = resp.read().decode("utf-8", errors="strict")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise UpdatesError(f"Could not reach GitHub to check for updates: {error}") from error
    try:
        return json.loads(payload) if payload else []
    except ValueError as error:
        raise UpdatesError("GitHub returned an unreadable reply.") from error


def _release_from_json(data: dict) -> GitHubRelease:
    """Build one :class:`GitHubRelease` from a GitHub Releases API entry."""
    return GitHubRelease(
        version=str(data.get("tag_name") or data.get("name") or "").strip(),
        published_at=str(data.get("published_at") or "").strip(),
        notes=str(data.get("body") or "").strip(),
        prerelease=bool(data.get("prerelease")),
        html_url=str(data.get("html_url") or "").strip(),
    )


def fetch_releases(api_url: str | None = None) -> list[GitHubRelease]:
    """All non-draft GitHub releases for this app (newest-first, as GitHub
    returns them).

    ``api_url`` overrides the default (this app's own repository) -- used
    in tests and by anyone rehearsing against a throwaway repo.
    """
    raw = _http_get_json(api_url or _releases_api_url())
    if not isinstance(raw, list):
        raise UpdatesError("GitHub releases payload must be a JSON array")
    return [_release_from_json(r) for r in raw if isinstance(r, dict) and not r.get("draft")]


def select_latest(
    releases: list[GitHubRelease], include_prereleases: bool = False
) -> GitHubRelease | None:
    """The newest release the user is eligible for.

    Stable channel (default): newest non-prerelease release. Beta channel
    (``include_prereleases=True``): newest release including prereleases.
    Returns ``None`` when no eligible release exists.
    """
    candidates = [r for r in releases if include_prereleases or not r.prerelease]
    if not candidates:
        return None
    return max(candidates, key=lambda r: _version_tuple(r.version))


def find_release(releases: list[GitHubRelease], version: str) -> GitHubRelease | None:
    """The release whose tag matches ``version`` (so a caller can tell
    whether the running build is itself a prerelease)."""
    target = _version_tuple(version)
    for release in releases:
        if _version_tuple(release.version) == target:
            return release
    return None


def latest_release_page_url(release: GitHubRelease) -> str:
    """The release's own GitHub page, for opening in a browser.

    Replaces upstream's asset-download flow: this app has no installer to
    fetch and run, so "get the update" here means "open this page and
    download the .dmg/.pkg yourself".
    """
    return release.html_url


def is_newer_version(current: str, available: str) -> bool:
    """True when ``available`` outranks ``current``.

    See :func:`_version_tuple` for the full ordering rules, including
    pre-release stages.
    """
    return _version_tuple(available) > _version_tuple(current)


def _version_tuple(value: str) -> tuple[int, int, int, tuple[int, int, int]]:
    """Sortable version key with intentional pre-release ordering.

    Copied verbatim from upstream ``quill.core.updates._version_tuple``
    (including its pre-release/interim-build ordering rules) so a release
    offered as "newer" here sorts identically to the Windows app.

    The fourth element ranks the pre-release stage so that, for the same
    ``major.minor.patch``, a final release always sorts *after* any of its
    pre-releases (``1.2.0`` > ``1.2.0-rc2`` > ``1.2.0-rc1`` > ``1.2.0-beta1`` >
    ``1.2.0-alpha1``). Unrecognized suffixes are treated as the earliest stage so
    an unknown pre-release never outranks a stable build.

    Its third sub-element is an *interim patch* so a hand-off test build can sit
    strictly between two pre-releases: ``Beta 1`` < ``Beta 1A`` < ``Beta 2``
    (display letter) and the equivalent PEP 440 ``0.8.0b1`` < ``0.8.0b1.post1`` <
    ``0.8.0b2``.

    Accepts both PEP 440 hyphen form (``1.2.0-rc1``) and the human-readable
    display form (``1.2.0 Beta 1``, ``1.2.0 Release Candidate 2``).
    """

    cleaned = value.strip().lstrip("v")
    # Normalize the display form ("0.7.0 Beta 1", "0.7.0 Release Candidate 2")
    # to the PEP 440 hyphen form ("0.7.0-beta1", "0.7.0-rc2") so the rest of
    # the parser only has to know one shape.
    space_match = re.match(
        r"^(\d+\.\d+(?:\.\d+)?)\s+"
        r"(alpha|beta|release\s+candidate|rc|dev)"
        r"\.?\s*(\d*)([a-z]?)\b",
        cleaned,
        re.I,
    )
    if space_match:
        base, label, number, patch = space_match.groups()
        label_key = label.strip().lower()
        if label_key == "release candidate":
            label_key = "rc"
        cleaned = f"{base}-{label_key}{number}{patch}"
    # Separate the core x.y.z from any pre-release suffix (-rc1, -beta.2, ...) so
    # the suffix digits cannot leak into the patch number.
    core, separator, suffix = cleaned.partition("-")
    parts = core.split(".")
    integers: list[int] = []
    for index in range(3):
        if index < len(parts):
            token = "".join(char for char in parts[index] if char.isdigit())
            integers.append(int(token or "0"))
        else:
            integers.append(0)
    prerelease = _prerelease_rank(suffix) if separator else _STABLE_PRERELEASE_RANK
    return integers[0], integers[1], integers[2], prerelease


def _prerelease_rank(suffix: str) -> tuple[int, int, int]:
    """Copied verbatim from upstream ``quill.core.updates._prerelease_rank``."""
    lowered = suffix.strip().lower()
    if lowered.startswith("rc"):
        tier = 2
    elif lowered.startswith(("beta", "b")):
        tier = 1
    else:
        # alpha/a and anything unrecognized fall to the earliest stage.
        tier = 0
    # The pre-release number is the first run of digits (so "beta1.post1" is
    # number 1, not 11). The interim patch is either a trailing letter right
    # after that number ("beta1a" -> 1, i.e. "A") or a PEP 440 ".postN" suffix.
    number_match = re.search(r"(\d+)", lowered)
    number = int(number_match.group(1)) if number_match else 0
    post = 0
    letter_match = re.search(r"\d([a-z])", lowered)
    post_match = re.search(r"post(\d+)", lowered)
    if letter_match:
        post = ord(letter_match.group(1)) - ord("a") + 1
    elif post_match:
        post = int(post_match.group(1))
    return tier, number, post


__all__ = [
    "GitHubRelease",
    "UpdatesError",
    "fetch_releases",
    "find_release",
    "is_newer_version",
    "latest_release_page_url",
    "select_latest",
]
