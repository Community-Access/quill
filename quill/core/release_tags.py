"""What a release in this repository is called, once and for all nine apps.

Eleven products ship out of one repository and update independently of each
other. That works because each release carries only one app's assets and each
app looks for its own prefix (``companion_install.ASSET_PREFIX``,
``updates.fetch_app_releases``) -- but the *tag* those releases carry had never
been decided. ``quill-<app>-v<version>`` was **inferred** from the asset prefix
by whoever read the code last, and no sibling app had ever been released, so
nothing on the server settled it either.

Deciding it here rather than in a wiki page, because the decision has to be
enforceable: whatever is chosen becomes the convention for eight more apps, and
a tag that does not match is a release the app looking for it cannot see. There
is nothing to notice when that happens -- the updater simply reports no update,
forever, to the people who most need one.

**The convention**

* **QUILL itself keeps ``v<version>``** -- ``v1.0.0``. Fourteen releases already
  carry that shape and rewriting them would break every checkout that pins one.
  QUILL is also the only app whose tag has ever had to be typed by a person.
* **Every sibling is ``quill-<app key>-v<version>``** -- ``quill-radio-v3.0.0``,
  ``quill-cast-v2.0.0``. The app key is the one in
  :data:`quill.core.app_launcher.APP_NAMES`, so a tag and a launcher entry
  cannot describe two different apps.
* **One grandfathered exception: QUILL Lite is ``quill-lite-v``**, not
  ``quill-quilllite-v``. Every QUILL Lite release since 1.0.0 carries it, the
  copies already installed look for it, and the sibling-version gate reads it
  (release-channels plan 1.3 and open question 10). :data:`RELEASE_TAG_KEYS`
  holds the mapping in both directions, so the app key stays ``quilllite``
  everywhere else.
* **The version is a bare dotted number**, optionally with a pre-release
  suffix: ``3.0.0``, ``0.9.0-beta.3``. No ``v`` inside it; the ``v`` is the
  separator, not part of the number.
* **A build number is a pre-release identifier in a tag** (2026-10):
  ``quill-radio-v3.2.0-build.12``, ``v1.1.0-beta.1.build.3``. The canonical
  version is ``3.2.0+12``, but a ``+`` in a tag is read by the copies already
  installed as part of the patch number (``v1.0.0+2`` was 1.0.2 to them) or as
  no version at all, so :func:`release_tag` spells the build the way they can
  read: as a pre-release of the same number, which an older release still sees
  as newer. Reading accepts both spellings, and build-less tags stay valid.

**Why the prefix and not just the app name.** Tags in this repository are
globally ordered and globally listed: ``git tag`` is read by people, and a list
where half the entries begin with ``quill-`` and half do not is a list you have
to know the answer to before you can read it. The prefix also keeps a future
non-app tag (``runtime-latest``, ``assets-v1``, both of which already exist)
from ever colliding with an app's.

wx-free and dependency-free on purpose: the build scripts and the update client
both need this, and neither should import a UI to find out what a tag is called.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import NamedTuple

__all__ = [
    "RELEASE_TAG_KEYS",
    "TAG_PATTERN",
    "ReleaseTag",
    "is_release_tag",
    "next_build",
    "parse_release_tag",
    "release_tag",
]

#: The app whose tag has no prefix, for the reason in the module docstring.
_UNPREFIXED_APP = "quill"

#: The prefix every sibling's tag carries.
_PREFIX = "quill-"

#: App key -> the key its tags spell, where the two differ (grandfathered).
RELEASE_TAG_KEYS: dict[str, str] = {"quilllite": "lite"}
_APP_FOR_TAG_KEY = {tag_key: app for app, tag_key in RELEASE_TAG_KEYS.items()}

#: A version: dotted numbers, optionally a pre-release suffix. Anchored, because
#: a "version" that merely *contains* a number is how a typo ships.
_VERSION = (
    r"\d+\.\d+(?:\.\d+)?(?:[-.][0-9A-Za-z][0-9A-Za-z.]*)?"
    r"(?:\+[0-9A-Za-z][0-9A-Za-z.]*)?"
)

#: The whole tag. ``quill-radio-v3.0.0``, or ``v1.0.0`` for QUILL itself.
TAG_PATTERN = re.compile(rf"^(?:{_PREFIX}(?P<app>[a-z][a-z0-9]*)-)?v(?P<version>{_VERSION})$")


class ReleaseTag(NamedTuple):
    """``(app_key, version)``, the two things a tag says.

    A NamedTuple so it unpacks like the pair it is and still answers by name at
    a call site that wants to be readable.
    """

    app_key: str
    version: str


def release_tag(app_key: str, version: str) -> str:
    """The tag ``app_key`` version *version* is released under.

    >>> release_tag("quill", "1.0.0")
    'v1.0.0'
    >>> release_tag("radio", "3.0.0")
    'quill-radio-v3.0.0'

    A leading ``v`` on *version* is tolerated and dropped: the ``v`` in the tag
    is the separator, and ``quill-radio-vv3.0.0`` is a tag nothing will match.
    A build number is spelled the way installed copies read it (module
    docstring): ``release_tag("radio", "3.2.0+12")`` is
    ``quill-radio-v3.2.0-build.12``; commit metadata (``+g1a2b3c``) is dropped.
    """
    number = str(version).strip().lstrip("vV")
    key = str(app_key).strip().lower()
    if not re.fullmatch(_VERSION, number):
        raise ValueError(f"{version!r} is not a release version (expected e.g. '3.0.0')")
    if "+" in number:
        from quill.core.versioning import ReleaseVersion

        number = ReleaseVersion.parse(number).tag_version()
    if key == _UNPREFIXED_APP:
        return f"v{number}"
    if not re.fullmatch(r"[a-z][a-z0-9]*", key):
        raise ValueError(f"{app_key!r} is not an app key (expected e.g. 'radio')")
    return f"{_PREFIX}{RELEASE_TAG_KEYS.get(key, key)}-v{number}"


def parse_release_tag(tag: str) -> ReleaseTag | None:
    """``('radio', '3.0.0')`` for a tag that matches, ``None`` for one that does not.

    ``None`` rather than a guess, because guessing is what let a tag nobody's
    updater matches look like a release: a tag this cannot read is a tag that
    was never one of ours, and the caller should skip it rather than half-read
    it.
    """
    match = TAG_PATTERN.match(str(tag or "").strip())
    if match is None:
        return None
    tag_key = match.group("app") or _UNPREFIXED_APP
    return ReleaseTag(_APP_FOR_TAG_KEY.get(tag_key, tag_key), match.group("version"))


def is_release_tag(tag: str, app_key: str | None = None) -> bool:
    """Whether *tag* is one of ours, optionally for one particular app."""
    parsed = parse_release_tag(tag)
    if parsed is None:
        return False
    return app_key is None or parsed.app_key == str(app_key).strip().lower()


def next_build(tags: Iterable[str], app_key: str, version: str) -> int:
    """The build number the next release of *version* for *app_key* takes.

    One more than the highest build already tagged for that exact release
    number, in either spelling; a build-less tag (every release before build
    numbers) counts as build 0, so the first rebuild of an old ``3.0.4`` is
    build 1. Nothing tagged yet: build 1. Other apps' tags and other versions
    are ignored.
    """
    from quill.core.versioning import ReleaseVersion

    wanted = ReleaseVersion.parse(version).without_build()
    key = str(app_key).strip().lower()
    builds = []
    for tag in tags:
        parsed = parse_release_tag(tag)
        if parsed is None or parsed.app_key != key:
            continue
        found = ReleaseVersion.try_parse(parsed.version)
        if found is not None and found.same_number(wanted):
            builds.append(found.build)
    return max(builds, default=0) + 1
