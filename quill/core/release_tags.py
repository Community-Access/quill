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
  ``quill-cast-v2.0.0``, ``quill-quilllite-v1.0.0``. The app key is the one in
  :data:`quill.core.app_launcher.APP_NAMES`, so a tag and a launcher entry
  cannot describe two different apps.
* **The version is a bare dotted number**, optionally with a pre-release
  suffix: ``3.0.0``, ``0.9.0-beta.3``. No ``v`` inside it; the ``v`` is the
  separator, not part of the number.

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
from typing import NamedTuple

__all__ = [
    "TAG_PATTERN",
    "ReleaseTag",
    "is_release_tag",
    "parse_release_tag",
    "release_tag",
]

#: The app whose tag has no prefix, for the reason in the module docstring.
_UNPREFIXED_APP = "quill"

#: The prefix every sibling's tag carries.
_PREFIX = "quill-"

#: A version: dotted numbers, optionally a pre-release suffix. Anchored, because
#: a "version" that merely *contains* a number is how a typo ships.
_VERSION = r"\d+\.\d+(?:\.\d+)?(?:[-.][0-9A-Za-z][0-9A-Za-z.]*)?"

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
    """
    number = str(version).strip().lstrip("vV")
    key = str(app_key).strip().lower()
    if not re.fullmatch(_VERSION, number):
        raise ValueError(f"{version!r} is not a release version (expected e.g. '3.0.0')")
    if key == _UNPREFIXED_APP:
        return f"v{number}"
    if not re.fullmatch(r"[a-z][a-z0-9]*", key):
        raise ValueError(f"{app_key!r} is not an app key (expected e.g. 'radio')")
    return f"{_PREFIX}{key}-v{number}"


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
    return ReleaseTag(match.group("app") or _UNPREFIXED_APP, match.group("version"))


def is_release_tag(tag: str, app_key: str | None = None) -> bool:
    """Whether *tag* is one of ours, optionally for one particular app."""
    parsed = parse_release_tag(tag)
    if parsed is None:
        return False
    return app_key is None or parsed.app_key == str(app_key).strip().lower()
