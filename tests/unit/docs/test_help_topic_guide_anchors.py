"""Every F1 help topic's "Full details" link lands on a real guide heading.

QUILL's help topics (``quill/core/help/topics.json``) carry a
``user_guide_section`` slug. F1's "Full details" opens the user guide rendered
by ``render_preview_html`` and scrolls to the element with that id; when no
heading has it, the browser silently opens at the top of a 900-heading guide
and nothing says the link went nowhere. The 2026-10 guide restructure left
three slugs ("editing", "files", "keyboard-and-sound") pointing at headings
that no longer existed -- 46 topics -- and no test noticed.

This checks the ids the *real renderer* gives the *real guide*, not a slug
function re-implemented here, so a change to either side is caught.

QUILL is the only family app whose F1 help deep-links into its guide; Radio,
Cast, QUILL Lite and the rest open whole documents by file stem from the Help
menu. If another app's help ever gains section anchors, add its pair to
``_GUIDES`` below.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core.browser_preview import render_preview_body
from quill.core.help.renderer import load_topics

_REPO = Path(__file__).resolve().parents[3]

#: (label, guide markdown, {topic id: anchor}) loaders, one per app whose
#: help links into a guide section.
_GUIDES = {
    "QUILL": (
        _REPO / "docs" / "user guide" / "userguide.md",
        lambda: {
            topic.id: topic.user_guide_section
            for topic in load_topics().values()
            if topic.user_guide_section
        },
    ),
}


def _heading_ids(guide: Path) -> set[str]:
    html = render_preview_body(guide.read_text(encoding="utf-8"), "markdown")
    return set(re.findall(r'id="([^"]+)"', html))


@pytest.mark.parametrize("app", sorted(_GUIDES))
def test_every_help_topic_anchor_resolves(app: str) -> None:
    guide, load = _GUIDES[app]
    anchors = load()
    assert anchors, f"{app}: no help topics carry a guide section; the loader is broken"
    ids = _heading_ids(guide)
    broken = sorted(f"{topic} -> #{slug}" for topic, slug in anchors.items() if slug not in ids)
    assert not broken, (
        f"{app}: {len(broken)} F1 help topic(s) link to a guide heading that does "
        f"not exist in {guide.name}. Point each at an existing heading's id, or "
        "add the section to the guide:\n  " + "\n  ".join(broken)
    )


def test_renderer_still_gives_headings_ids() -> None:
    """Guard the guard: if headings lost their ids, every anchor would fail
    for the wrong reason (or a loosened check would pass for none)."""
    ids = _heading_ids(_GUIDES["QUILL"][0])
    assert "general-preferences" in ids
    assert len(ids) > 100
