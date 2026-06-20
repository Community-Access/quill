"""Repo-level tests for legal and trademark documentation.

These are existence + content-shape tests. They guard against a future
merge that deletes a legal file or strips the independence notice from
the canonical sources. They do not assert legal claims.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_trademarks_file_exists() -> None:
    text = _read("TRADEMARKS.md")
    assert "QUILL for All" in text
    assert "Community Access" in text
    assert "Quill.js" in text or "QuillBot" in text


def test_notice_file_exists() -> None:
    text = _read("NOTICE")
    assert "QUILL for All" in text
    assert "Community Access" in text
    assert "independent" in text.lower()


def test_third_party_notices_file_exists() -> None:
    text = _read("THIRD_PARTY_NOTICES.md")
    assert "Third-Party" in text or "third-party" in text or "third party" in text


def test_legal_notices_doc_exists() -> None:
    text = _read("docs/legal/legal-notices.md")
    assert "Independence Notice" in text
    assert "QUILL for All" in text


def test_trademark_notices_doc_exists() -> None:
    text = _read("docs/legal/trademark-notices.md")
    assert "QUILL for All" in text
    assert "Community Access" in text


def test_readme_introduces_quill_for_all() -> None:
    text = _read("README.md")
    # The first heading should be the public project name.
    assert text.splitlines()[0].lstrip("# ").strip() == "QUILL for All"
    # The body must contain the description and the legal section.
    assert "accessibility-focused editor" in text.lower()
    assert "Legal and Trademark Notices" in text
    assert "TRADEMARKS.md" in text


def test_branding_module_independence_notice_in_test_data() -> None:
    """The independence notice in branding is the canonical text."""
    from quill.branding import INDEPENDENCE_NOTICE

    assert "QUILL for All" in INDEPENDENCE_NOTICE
    assert "Community Access" in INDEPENDENCE_NOTICE
    assert "Quill.js" in INDEPENDENCE_NOTICE
    assert "QuillBot" in INDEPENDENCE_NOTICE


def test_legal_docs_do_not_claim_trademark_registration() -> None:
    """Avoid wording that would imply a registered mark unless one exists."""
    for rel in (
        "TRADEMARKS.md",
        "NOTICE",
        "docs/legal/legal-notices.md",
        "docs/legal/trademark-notices.md",
    ):
        text = _read(rel).lower()
        # We do not assert any specific trademark registration status.
        # No file should claim a registered mark.
        assert "registered trademark" not in text, (
            f"{rel} asserts a registered trademark; remove the claim "
            "or have it reviewed by counsel first."
        )
