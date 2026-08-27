"""A source added in a later release must reach people who already chose.

Reported 2026-08-26, from a build run out of the source tree: the three new
directories were switched on in the settings list and still absent from the
tree. A stored "these are my sources" list can only name sources that existed
when it was saved, and ``normalize`` drops anything it does not name -- so a new
source is invisible to everybody who has ever opened the chooser. Browse sources
learned this in August (the Podcast Index branch did exactly the same thing);
the *search* list had the identical hole and nothing had been added since to
reveal it.
"""

from __future__ import annotations

from quill.core.radio import browse_visibility, search_sources

_NEW = ("shoutcast", "live365", "radioparadise")


# --- browse ------------------------------------------------------------------


def test_a_stored_browse_choice_gains_the_new_branches() -> None:
    saved = tuple(s for s in browse_visibility.default_enabled() if s not in _NEW)
    assert not any(source_id in saved for source_id in _NEW)

    shown = browse_visibility.with_new_sources(saved, 1)  # stamped before the bump

    assert all(source_id in shown for source_id in _NEW)


def test_a_branch_switched_off_after_seeing_it_stays_off() -> None:
    seen = browse_visibility.with_new_sources(browse_visibility.default_enabled(), 1)
    hidden = browse_visibility.toggle(seen, "live365")
    assert "live365" not in hidden

    still_hidden = browse_visibility.with_new_sources(hidden, browse_visibility.SOURCES_EPOCH)

    assert "live365" not in still_hidden


def test_the_epoch_names_every_new_branch_exactly_once() -> None:
    listed = [
        source_id for ids in browse_visibility.INTRODUCED_BY_EPOCH.values() for source_id in ids
    ]
    assert len(listed) == len(set(listed))
    assert all(browse_visibility.source(source_id) is not None for source_id in listed)
    assert max(browse_visibility.INTRODUCED_BY_EPOCH) == browse_visibility.SOURCES_EPOCH


# --- search ------------------------------------------------------------------


def test_a_stored_search_choice_gains_the_new_sources() -> None:
    saved = tuple(s for s in search_sources.DEFAULT_ENABLED if s not in _NEW)

    shown = search_sources.with_new_sources(saved, 0)

    assert all(source_id in shown for source_id in _NEW)


def test_a_search_source_switched_off_after_seeing_it_stays_off() -> None:
    seen = search_sources.with_new_sources(search_sources.DEFAULT_ENABLED, 0)
    without = tuple(s for s in seen if s != "shoutcast")

    still_without = search_sources.with_new_sources(without, search_sources.SEARCH_SOURCES_EPOCH)

    assert "shoutcast" not in still_without


def test_turning_every_search_source_off_is_respected() -> None:
    """The other direction of the same bug: an explicit "none" is a choice."""
    assert search_sources.with_new_sources((), 0) == ()


def test_never_having_chosen_still_answers_with_the_defaults() -> None:
    assert search_sources.with_new_sources(None, 0) == search_sources.DEFAULT_ENABLED


def test_all_three_directories_are_searchable_at_all() -> None:
    """Browsing a directory you cannot search is half a source."""
    assert all(search_sources.source(source_id) is not None for source_id in _NEW)
    assert all(source_id in search_sources.DEFAULT_ENABLED for source_id in _NEW)


# --- the stored profile ------------------------------------------------------


def test_a_saved_profile_is_stamped_and_upgraded(tmp_path, monkeypatch) -> None:
    """End to end through the history file: an old profile, then a new one."""
    import json

    from quill.core.radio import (
        history,  # imported first: see history.py's late import
        history_store,
    )

    assert history is not None
    path = tmp_path / history_store._FILE_NAME
    saved_search = [s for s in search_sources.DEFAULT_ENABLED if s not in _NEW]
    saved_browse = [s for s in browse_visibility.default_enabled() if s not in _NEW]
    path.write_text(
        json.dumps({
            "search_sources_enabled": saved_search,
            "browse_sources_enabled": saved_browse,
            "browse_sources_epoch": 1,
        }),
        encoding="utf-8",
    )

    history = history_store.load_history(tmp_path)

    assert all(source_id in history.search_sources_enabled for source_id in _NEW)
    assert all(source_id in (history.browse_sources_enabled or ()) for source_id in _NEW)
    assert history.search_sources_epoch == search_sources.SEARCH_SOURCES_EPOCH
    assert history.browse_sources_epoch == browse_visibility.SOURCES_EPOCH

    # ...and the stamps are written back, so this happens once rather than
    # every launch.
    history_store.save_history(tmp_path, history)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["search_sources_epoch"] == search_sources.SEARCH_SOURCES_EPOCH
    assert raw["browse_sources_epoch"] == browse_visibility.SOURCES_EPOCH
