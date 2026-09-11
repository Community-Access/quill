"""The site's per-app pages are copies, so they are checked rather than trusted.

``docs/site/docs/*.html`` mirrors each app's own rendered documentation. Copies
rot, and a rotted copy is invisible: the page loads, it reads as documentation,
and it describes an app that no longer looks like that. Radio's pages were found
in exactly that state in 2026-08, predating Radio 3.0 entirely.

Two failures this file catches, and only one of them is staleness:

* **A declared render that does not exist.** A typo in the map is a page that is
  never written and never noticed, because there is nothing to compare it to.
* **An app with no pages at all.** Eight of the nine siblings were in that state
  until 2026-09-10 -- not stale, absent, which nobody can report: there is no
  wrong page to complain about.

Whether the copies are *current* is a build step, not a test: it depends on the
renders having been run, which a checkout does not guarantee. Run
``python scripts/sync_site_docs.py --check`` for that.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_sync_module():
    """Import ``scripts/sync_site_docs.py``, which is not an installed package."""
    path = _REPO_ROOT / "scripts" / "sync_site_docs.py"
    spec = importlib.util.spec_from_file_location("sync_site_docs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_site_docs"] = module
    spec.loader.exec_module(module)
    return module


sync = _load_sync_module()


def test_every_declared_render_exists() -> None:
    """A typo in the map is a page nothing ever writes and nobody ever misses."""
    missing = [
        str(source.relative_to(_REPO_ROOT))
        for _page, source in sync.planned()
        if not source.is_file()
    ]
    assert missing == [], "declared renders that do not exist: " + ", ".join(missing)


def test_every_app_that_ships_docs_is_on_the_site() -> None:
    """The gap that had no symptom: eight siblings with no site page at all."""
    shipping = {
        folder.parent.name
        for folder in (_REPO_ROOT / "standalone").glob("*/docs")
        if (folder / "userguide.html").is_file()
    }
    # radio-mac and social are not shipped products with their own site presence;
    # beacon ships a PRD only. Named rather than inferred, so adding an app to the
    # family fails this test until somebody decides whether it belongs on the site.
    exempt = {"radio-mac", "social", "beacon"}
    absent = sorted(shipping - set(sync.SYNC_MAP) - exempt)
    assert absent == [], "apps that ship a user guide and have no site page: " + ", ".join(absent)


def test_every_app_offers_at_least_its_user_guide() -> None:
    for app_key, renders in sync.SYNC_MAP.items():
        assert "userguide" in renders, app_key


def test_no_two_apps_write_the_same_site_page() -> None:
    pages = [page for page, _source in sync.planned()]
    assert len(set(pages)) == len(pages)


def test_the_site_pages_are_present_in_the_tree() -> None:
    """They are committed, not generated at publish time: the site is static."""
    missing = [
        str(page.relative_to(_REPO_ROOT)) for page, _source in sync.planned() if not page.is_file()
    ]
    assert missing == [], "site pages not in the tree: " + ", ".join(missing)


def test_the_index_links_to_every_page_that_was_synced() -> None:
    """A page nothing links to is a page nobody finds."""
    index = (_REPO_ROOT / "docs" / "site" / "docs.html").read_text(encoding="utf-8")
    unlinked = [
        page.name for page, _source in sync.planned() if f'href="/docs/{page.name}"' not in index
    ]
    assert unlinked == [], "synced but not linked from docs.html: " + ", ".join(unlinked)


def test_an_unknown_app_key_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert sync.main(["--app", "nonesuch"]) == 2
    assert "Unknown app key" in capsys.readouterr().err


def test_the_radio_only_entry_point_still_works() -> None:
    """Radio's build_release.ps1 calls it by name; a rename must not reach it."""
    assert (_REPO_ROOT / "scripts" / "sync_site_radio_docs.py").is_file()
    assert sync.main(["--app", "radio", "--check"]) == 0
