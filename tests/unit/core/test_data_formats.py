"""GATE-DATAFMT: every saved shape matches its recorded fingerprint.

"Back to Stable only if safe" trusts the version numbers in
``quill/core/data_formats.py``. This keeps them honest: a serializer that
changes fails here until its format's ``current`` is bumped or the change is
recorded as "additive, compatible" with
``python -m quill.tools.data_format_audit --write --accept <id> --note "..."``.
"""

from __future__ import annotations

import copy
from pathlib import Path

from quill.core.data_formats import FORMATS
from quill.tools import data_format_audit as audit


def test_every_registered_format_has_a_serializer_to_fingerprint() -> None:
    assert {f.id for f in FORMATS} <= set(audit.PROBES)
    assert set(audit.PROBES) <= {f.id for f in FORMATS}


def test_every_saved_shape_matches_its_recorded_fingerprint() -> None:
    problems = audit.audit()
    assert problems == [], "\n".join(problems)


def test_a_new_field_fails_until_it_is_classified(tmp_path: Path) -> None:
    live = audit.live_shapes()
    recorded = copy.deepcopy(live)
    shape = recorded["radio.favorites"]["shape"]
    station = shape["dataclass:quill.core.radio.favorites:RadioFavoritesStore"]
    first = next(iter(station))
    del station[first][next(iter(station[first]))]
    problems = audit.audit(live, recorded)
    assert len(problems) == 1
    assert problems[0].startswith("radio.favorites: the saved shape changed (added ")
    assert "--accept radio.favorites" in problems[0]


def test_a_changed_type_cannot_be_accepted_as_additive(tmp_path: Path, monkeypatch) -> None:
    live = audit.live_shapes()
    fixture = tmp_path / "fingerprints.json"
    monkeypatch.setattr(audit, "live_shapes", lambda: copy.deepcopy(live))
    audit.write(path=fixture)
    changed = copy.deepcopy(live)
    fields = changed["shared.media_bookmarks"]["shape"][
        "dataclass:quill.core.media.bookmarks:MediaBookmark"
    ]["quill.core.media.bookmarks:MediaBookmark"]
    name = next(iter(fields))
    fields[name] = "bytes"
    monkeypatch.setattr(audit, "live_shapes", lambda: copy.deepcopy(changed))
    recorded, refused = audit.write(["shared.media_bookmarks"], path=fixture)
    assert recorded == []
    assert refused and "type changed" in refused[0]
    changed["shared.media_bookmarks"]["current"] = 2
    recorded, refused = audit.write(path=fixture)
    assert refused == [] and recorded == ["shared.media_bookmarks: version bumped to 2"]
    assert audit.audit(changed, audit.load_fixture(fixture)) == []


def test_an_added_field_is_accepted_with_a_note(tmp_path: Path, monkeypatch) -> None:
    live = audit.live_shapes()
    fixture = tmp_path / "fingerprints.json"
    monkeypatch.setattr(audit, "live_shapes", lambda: copy.deepcopy(live))
    audit.write(path=fixture)
    grown = copy.deepcopy(live)
    grown["cast.history"]["shape"]["dataclass:quill.core.podcasts.history:PodcastHistory"][
        "quill.core.podcasts.history:PodcastHistory"
    ]["new_option"] = "bool"
    monkeypatch.setattr(audit, "live_shapes", lambda: copy.deepcopy(grown))
    _recorded, refused = audit.write(path=fixture)
    assert refused, "an unclassified change must not be recorded"
    recorded, refused = audit.write(["cast.history"], note="older builds ignore it", path=fixture)
    assert refused == []
    entry = audit.load_fixture(fixture)["cast.history"]
    assert entry["classification"] == audit.ADDITIVE
    assert entry["note"] == "older builds ignore it"


def test_comments_and_docstrings_do_not_move_a_function_fingerprint() -> None:
    plain = "def save(x):\n    return {'a': x}\n"
    documented = (
        'def save(x):\n    """Says what it does."""\n    # a comment\n    return {"a": x}\n'
    )
    renamed_key = "def save(x):\n    return {'b': x}\n"
    assert audit.source_hash(plain) == audit.source_hash(documented)
    assert audit.source_hash(plain) != audit.source_hash(renamed_key)
