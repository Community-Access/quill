"""Public product-name and branding constants for QUILL.

This module centralises the strings that identify QUILL in user-facing
surfaces (About dialog, Help menu, README, installer metadata, support
bundles, crash reports). Internal code identifiers (Python package name
``quill``, settings paths, data directories) are intentionally not
renamed - changing those would break saved settings, keymaps, and
extension manifests.

Constants:

* :data:`APP_DISPLAY_NAME` - full public name, ``"QUILL for All"``.
* :data:`APP_ORGANIZATION` - publisher, ``"Community Access"``.
* :data:`APP_FULL_NAME` - organisational form, ``"QUILL for All by
  Community Access"``.
* :data:`APP_SHORT_NAME` - short form after first use, ``"QUILL"``.
* :data:`APP_DESCRIPTION` - one-line description.
* :data:`APP_COPYRIGHT` - copyright line.
* :data:`APP_LICENSE_NAME` - the project's license name.
* :data:`INDEPENDENCE_NOTICE` - the multi-line text asserting that
  QUILL for All is not affiliated with similarly named projects.

The independence notice is intentionally calm and factual. It is not a
legal statement; it is risk-reduction language agreed with the
maintainers so that the project can continue to use its name while
making the scope of the project clear to users.
"""

from __future__ import annotations

APP_DISPLAY_NAME = "QUILL for All"
APP_ORGANIZATION = "Community Access"
APP_FULL_NAME = "QUILL for All by Community Access"
APP_SHORT_NAME = "QUILL"
APP_DESCRIPTION = "An open-source, accessibility-focused editor."
APP_COPYRIGHT = "Copyright (c) 2026 Community Access."
APP_LICENSE_NAME = "MIT License"

INDEPENDENCE_NOTICE = (
    f"{APP_DISPLAY_NAME} is an independent open-source project by "
    f"{APP_ORGANIZATION}. It is not affiliated with, sponsored by, or "
    "endorsed by Quill.js, QuillBot, Quill.org, or any other similarly "
    "named product, project, company, or organization."
)


__all__ = [
    "APP_DISPLAY_NAME",
    "APP_ORGANIZATION",
    "APP_FULL_NAME",
    "APP_SHORT_NAME",
    "APP_DESCRIPTION",
    "APP_COPYRIGHT",
    "APP_LICENSE_NAME",
    "INDEPENDENCE_NOTICE",
]
