"""Tests for the context-sensitive help infrastructure."""

from __future__ import annotations

from quill.core.feature_command_map import COMMAND_FEATURE_MAP
from quill.core.help.renderer import load_topics


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
