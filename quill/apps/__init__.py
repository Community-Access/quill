"""Standalone companion apps that reuse QUILL's core/UI feature modules
without loading the full editor. See docs/planning/apps.md.
"""

from __future__ import annotations

from quill.core.net import configure_ssl_trust

configure_ssl_trust()
