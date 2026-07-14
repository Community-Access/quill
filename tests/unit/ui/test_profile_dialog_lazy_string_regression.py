"""Regression tests for issues #878/#879 — Profiles and Features dialog crash.

Opening Tools > Customize and Support > Profiles and Features (or its command
palette entry) raised ``TypeError: Item at index 0 has type '_LazyString' but
a sequence of bytes or strings is expected`` and crashed. Built-in profile
names (``quill.core.features.PROFILE_DEFINITIONS[...].name``) are
``lazy_gettext(...)`` proxies for translation; ``wx.ListBox.Set()`` requires
real ``str`` instances, unlike f-string interpolation (which already
coerces), so the built-in branch of the labels comprehension needs an
explicit ``str(...)``.

Mirrors the pattern from issue #614 — see
``tests/unit/ui/test_ai_hub_lazy_string_regression.py``.
"""

from __future__ import annotations

import re
from pathlib import Path


def _main_frame_source() -> str:
    ui = Path(__file__).resolve().parents[3] / "quill" / "ui"
    return (ui / "main_frame.py").read_text(encoding="utf-8")


def _refresh_profile_list_source() -> str:
    src = _main_frame_source()
    match = re.search(
        r"        def refresh_profile_list\(.*?\n(?=        def [a-z_]+\()", src, re.DOTALL
    )
    assert match is not None, "refresh_profile_list function not found"
    return match.group(0)


def test_refresh_profile_list_coerces_built_in_names_to_str() -> None:
    body = _refresh_profile_list_source()
    match = re.search(r"labels\s*=\s*\[[^\]]+\]", body)
    assert match is not None, "refresh_profile_list labels comprehension not found"
    assert "str(name)" in match.group(0), (
        "refresh_profile_list labels comprehension must coerce built-in "
        "(lazy_gettext) profile names to str before chooser.Set(labels)"
    )
    assert "chooser.Set(labels)" in body
