"""Shared HTTP identity for QUILL's radio network calls.

Gives mpv and ffmpeg one User-Agent so a station owner sees ``Quill Radio``
in their listener logs instead of the default ``Lavf``/``libmpv``
(quill-radio #6). The product name and version are resolvable at runtime so the
standalone Quill Radio app can report its own release version rather than the
embedded :data:`quill.__version__`.

wx-free, strict-typed.
"""

from __future__ import annotations

from quill import __version__

_PROJECT_URL = "https://github.com/Community-Access/quill"

# Module-global identity. Defaults identify the embedded QUILL radio; the
# standalone app overrides these once, at startup, via set_product_identity.
_product_name = "Quill Radio"
_product_version = __version__


def set_product_identity(name: str, version: str) -> None:
    """Override the product name/version reported in the User-Agent.

    The standalone Quill Radio calls this at startup with its own ``_VERSION``
    so playback and recording are not misreported as the embedded
    :data:`quill.__version__`. Blank arguments are ignored, so a caller can
    override just one field.
    """
    global _product_name, _product_version
    if name.strip():
        _product_name = name.strip()
    if version.strip():
        _product_version = version.strip()


def user_agent() -> str:
    """The User-Agent for radio network calls: ``Quill Radio/<version> (+url)``."""
    return f"{_product_name}/{_product_version} (+{_PROJECT_URL})"
