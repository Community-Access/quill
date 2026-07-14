from __future__ import annotations

from quill.tools.persistence_audit import (
    _CLASSIFICATIONS,
    _REVIEWED_PERSISTENCE,
    discover_persistence_sites,
    find_unreviewed_persistence,
    needs_versioning_backlog,
)


def test_no_unreviewed_persistence_sites() -> None:
    """Every write_json_atomic site must be classified.

    A failure means a new persisted store appeared without deciding whether it
    needs the versioned-delta migration contract. Classify it in
    _REVIEWED_PERSISTENCE (see docs/design/persistence-and-migration.md).
    """
    unreviewed, _stale = find_unreviewed_persistence()
    assert not unreviewed, "Unclassified persistence write sites:\n" + "\n".join(
        f"  {s}" for s in sorted(unreviewed)
    )


def test_every_site_uses_a_known_classification() -> None:
    bad = {site: tag for site, tag in _REVIEWED_PERSISTENCE.items() if tag not in _CLASSIFICATIONS}
    assert not bad, f"Sites with unknown classification tags: {bad}"


def test_every_classification_has_a_rationale() -> None:
    for tag, rationale in _CLASSIFICATIONS.items():
        assert rationale.strip(), f"Classification {tag!r} has no rationale."


def test_discovered_sites_are_inside_the_quill_package() -> None:
    for site in discover_persistence_sites():
        path = site.split("::", 1)[0]
        assert not path.startswith(("/", "..")), site
        assert path.endswith(".py"), site


def test_needs_versioning_backlog_is_a_subset_of_reviewed() -> None:
    backlog = set(needs_versioning_backlog())
    assert backlog <= set(_REVIEWED_PERSISTENCE)
    # The backlog is informational, but it should not silently empty out by a
    # mis-tag: every backlog entry really is tagged needs-versioning.
    for site in backlog:
        assert _REVIEWED_PERSISTENCE[site] == "needs-versioning"
