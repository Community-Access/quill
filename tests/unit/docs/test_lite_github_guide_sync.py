"""QUILL Lite's GitHub Guide is QUILL's, written by scripts/sync_lite_github_guide.py.

The two copies drifted while both were edited by hand: chapters fixed in one
book stayed wrong in the other, and QUILL Lite's contents page linked headings
QUILL's had renamed. The copy is now generated, and this fails until it is
regenerated after an edit to QUILL's book.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "scripts" / "sync_lite_github_guide.py"


def _sync():
    spec = importlib.util.spec_from_file_location("sync_lite_github_guide", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quill_lites_copy_is_current() -> None:
    assert _sync().main(["--check"]) == 0, "run python scripts/sync_lite_github_guide.py"


def test_the_copy_links_its_own_chapters_and_its_own_user_guide() -> None:
    sync = _sync()
    text = sync.lite_text(
        "[Chapter 2](github-guide-02-getting-around.html#the-panes) and "
        "[Contents](github-guide.html), then [QUILL User Guide](../userguide.html)."
    )
    assert "(lite-github-guide-02-getting-around.html#the-panes)" in text
    assert "(lite-github-guide.html)" in text
    assert "[QUILL Lite User Guide](../userguide.html)" in text


def test_a_link_that_would_be_dead_in_quill_lite_keeps_its_words() -> None:
    text = _sync().lite_text("See [Sync a Folder](../quill-guide/quill-guide-14-x.html#sync).")
    assert text == "See Sync a Folder."
