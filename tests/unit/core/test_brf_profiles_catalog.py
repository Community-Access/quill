"""Regression test for issue #877 — Danish Braille table missing from Translation.

``liblouis/vendor/braille/pack/brf_profiles.json`` is the hand-curated list
the Translation submenu (``main_frame_braille.py:_build_translation_menu``)
reads via ``quill.core.braille_pack.get_brf_profiles``. The Danish liblouis
tables (``da-dk-g16.ctb``, ``da-dk-g26.ctb``, ...) are vendored and present on
disk, but no Danish entry was ever added to the curated profile list, so
Danish never appeared under Tools > Braille > Translation > More Languages
even though liblouis ships it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_PACK_DIR = Path(__file__).resolve().parents[3] / "liblouis" / "vendor" / "braille" / "pack"
_PROFILES_PATH = _PACK_DIR / "brf_profiles.json"

# brf_profiles.json is a vendored/generated braille-pack artifact (built by
# scripts/build_braille_pack.py); it is not committed, so a plain CI checkout
# does not have it. Skip when absent -- the profiles are still verified wherever
# the pack has been built (local dev / packaging).
pytestmark = pytest.mark.skipif(
    not _PROFILES_PATH.exists(),
    reason="vendored braille pack (brf_profiles.json) is not present in this checkout",
)


def _load_profiles() -> list[dict]:
    data = json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
    return data["profiles"]


def test_danish_profiles_are_present() -> None:
    profiles = _load_profiles()
    danish = [p for p in profiles if p.get("language_code") == "da"]
    assert danish, "No Danish (language_code='da') profile found in brf_profiles.json"
    assert len(danish) >= 2, "Expected at least a grade 1 and grade 2 Danish profile"


def test_danish_profiles_reference_real_vendored_tables() -> None:
    profiles = _load_profiles()
    danish = [p for p in profiles if p.get("language_code") == "da"]
    for profile in danish:
        table_path = _PACK_DIR / profile["translation_table"]
        assert table_path.is_file(), f"{profile['id']}: {table_path} does not exist"
        display_path = _PACK_DIR / profile["display_table"]
        assert display_path.is_file(), f"{profile['id']}: {display_path} does not exist"


def test_danish_profiles_use_the_other_languages_convention() -> None:
    """Match every other small-language entry: category, status, and a
    forward-only direction (back-translation confidence is unvetted for
    non-English tables across the whole 'Other languages' set)."""
    profiles = _load_profiles()
    danish = [p for p in profiles if p.get("language_code") == "da"]
    for profile in danish:
        assert profile["category"] == "Other languages"
        assert profile["status"] == "available"
        assert profile["direction"] == ["text-to-brf"]
        assert profile["id"] not in {p["id"] for p in profiles if p is not profile}
