"""Tests for the context-sensitive help infrastructure."""

from __future__ import annotations

import json

from quill.core.feature_command_map import COMMAND_FEATURE_MAP
from quill.core.help.renderer import load_topics
from quill.tools import check_help_coverage as gate


def test_topics_json_loads() -> None:
    """topics.json must load without errors and return at least one topic."""
    topics = load_topics()
    assert topics, "topics.json loaded no topics"


def test_all_topics_have_required_fields() -> None:
    """Every topic must have a non-empty id, title, and body."""
    topics = load_topics()
    for topic_id, topic in topics.items():
        assert topic.id, f"Topic {topic_id!r} has empty id"
        assert topic.title, f"Topic {topic_id!r} has empty title"
        assert topic.body, f"Topic {topic_id!r} has empty body"


def test_topic_render_live() -> None:
    topics = load_topics()
    for topic in topics.values():
        rendered = topic.render(mode="live")
        assert topic.title in rendered


def test_topic_render_doc() -> None:
    topics = load_topics()
    for topic in topics.values():
        rendered = topic.render(mode="doc")
        assert "###" in rendered


def test_every_braille_command_has_a_help_topic() -> None:
    """Every braille.* command in the feature command map must have a topic.

    Regression guard for #294: 0.7.0 F1 help was silent on braille controls.
    """
    topics = load_topics()
    topic_ids = set(topics)
    braille_commands = sorted(cmd for cmd in COMMAND_FEATURE_MAP if cmd.startswith("braille."))
    assert braille_commands, "No braille commands found in COMMAND_FEATURE_MAP"
    missing = [cmd for cmd in braille_commands if cmd not in topic_ids]
    assert not missing, (
        f"braille commands without help topics: {missing}. "
        f"Add an entry to quill/core/help/topics.json for each."
    )


def test_gate_loads_real_topics_and_passes_integrity() -> None:
    """The repaired gate must find the bundled topics and report no errors.

    Regression guard: the gate previously pointed at the wrong path
    (``QUILL/core/help`` instead of ``QUILL/quill/core/help``) and silently
    checked nothing.
    """
    entries = gate._load_raw()
    assert entries, "gate loaded no topics from the bundled topics.json"
    assert gate.check_integrity(entries) == []
    assert gate.run(strict=False) == 0


def test_check_integrity_flags_duplicates_empty_and_dangling() -> None:
    bad = [
        {"id": "a.one", "title": "One", "body": "Body."},
        {"id": "a.one", "title": "Dup", "body": "Body."},  # duplicate id
        {"id": "a.two", "title": "", "body": "Body."},  # empty title
        {"id": "a.three", "title": "Three", "body": ""},  # empty body
        {"id": "a.four", "title": "Four", "body": "B.", "see_also": ["nope"]},  # dangling
    ]
    errors = gate.check_integrity(bad)
    joined = " ".join(errors)
    assert "duplicate topic id" in joined
    assert "empty title" in joined
    assert "empty body" in joined
    assert "unknown topic" in joined


def test_scaffold_adds_stub(tmp_path, monkeypatch) -> None:
    topics_file = tmp_path / "topics.json"
    topics_file.write_text(
        json.dumps([{"id": "a.one", "title": "One", "body": "Body."}]), encoding="utf-8"
    )
    monkeypatch.setattr(gate, "_TOPICS_PATH", topics_file)
    assert gate._scaffold(["a.one", "z.new"]) == 0  # a.one already exists, z.new added
    written = json.loads(topics_file.read_text(encoding="utf-8"))
    ids = {e["id"] for e in written}
    assert ids == {"a.one", "z.new"}
    new = next(e for e in written if e["id"] == "z.new")
    assert new["title"] == "New"
    assert new["body"].startswith("TODO")
