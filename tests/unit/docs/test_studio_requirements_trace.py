"""The consolidated Studio requirements retain history without competing authority."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs" / "planning" / "QUILL-Studio-PRD.md"
BUILT = ROOT / "standalone" / "studio" / "docs" / "prd.md"
HISTORICAL = ROOT / "docs" / "audio-studio" / "prd.md"


def _ids(path: Path) -> set[str]:
    return set(re.findall(r"^- ([A-Z]+-\d+[a-z]?)\.", path.read_text(encoding="utf-8"), re.M))


def test_legacy_studio_requirements_all_have_a_canonical_home() -> None:
    historical = _ids(HISTORICAL)
    assert len(historical) >= 129
    assert historical <= _ids(BUILT), sorted(historical - _ids(BUILT))


@pytest.mark.parametrize("document", [PLAN, BUILT, HISTORICAL])
def test_studio_requirement_documents_have_no_broken_local_document_links(document: Path) -> None:
    links = re.findall(r"\[[^\]]+\]\((<[^>]+>|[^)]+)\)", document.read_text(encoding="utf-8"))
    for link in links:
        target = urlsplit(link.strip("<>"))
        if target.scheme or target.netloc or not target.path:
            continue
        assert (document.parent / unquote(target.path)).is_file(), (document, link)


def test_consolidation_keeps_withdrawn_work_and_unaccepted_work_distinct() -> None:
    text = PLAN.read_text(encoding="utf-8")
    assert "Cart Wall (CW-001 to CW-009) withdrawn" in text
    assert "## Appendix A. Requirement ID trace" in text
    assert "Windows.Graphics.Capture (spike S1) is not implemented" in text
    assert "default **Library** workspace" not in text
    assert "next-to-build" not in text
    assert "](../design/quill-studio-prd.md)" not in text
    built_ids = _ids(BUILT)
    assert {f"AS-{number}" for number in range(120, 131)} <= built_ids
