"""Tests for quill.branding product-name constants.

These constants are the single source of truth for user-visible project
naming. If a future change drops the independence notice or renames the
publisher, tests here fail first.
"""

from __future__ import annotations

from quill import branding


def test_display_name_is_quill_for_all() -> None:
    assert branding.APP_DISPLAY_NAME == "QUILL for All"


def test_short_name_is_quill() -> None:
    assert branding.APP_SHORT_NAME == "QUILL"


def test_full_name_includes_organization() -> None:
    assert branding.APP_FULL_NAME == "QUILL for All by Community Access"
    assert branding.APP_ORGANIZATION in branding.APP_FULL_NAME


def test_independence_notice_names_third_parties() -> None:
    notice = branding.INDEPENDENCE_NOTICE
    assert "QUILL for All" in notice
    assert "Community Access" in notice
    # The notice must list at least one similarly named third party so
    # the user understands what it does and does not apply to.
    assert "QuillBot" in notice
    assert "Quill.js" in notice
    assert "independent open-source project" in notice


def test_independence_notice_does_not_claim_trademark_registration() -> None:
    # We do not assert any specific trademark registration status. The
    # notice must avoid wording that would imply a registered mark.
    notice = branding.INDEPENDENCE_NOTICE
    assert "registered trademark" not in notice.lower()


def test_copyright_year_present() -> None:
    assert "2026" in branding.APP_COPYRIGHT


def test_description_is_accessibility_focused() -> None:
    assert "accessibility" in branding.APP_DESCRIPTION.lower()
