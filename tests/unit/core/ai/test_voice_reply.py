"""Delivery policy for a voice-asked AI reply.

The rules that matter are the ones a user would be annoyed to discover by
accident: a cloud voice is never selected for them, truncation applies to
announcements and not to speech, and a mode that cannot be honoured degrades
towards the offline default while saying so.
"""

from __future__ import annotations

import pytest

from quill.core.ai.voice_reply import mode_label, plan_voice_reply, truncate_announcement
from quill.core.settings import VOICE_REPLY_MODES, Settings


def _settings(**kwargs: object) -> Settings:
    settings = Settings()
    for key, value in kwargs.items():
        setattr(settings, key, value)
    return settings


def test_default_is_the_historical_announcement() -> None:
    """Nobody's setup changes until they opt in."""
    plan = plan_voice_reply("The answer is 42.", _settings())
    assert plan.mode == "announce"
    assert plan.announce_text == "Quill says: The answer is 42."
    assert not plan.speaks
    assert not plan.uses_cloud


def test_announcement_is_truncated_but_speech_is_not() -> None:
    """A 140-char cap summarises well and speaks badly.

    Reading the first 137 characters of an answer aloud and stopping mid-word is
    worse than not reading it, so the cap belongs to announcements alone.
    """
    long_reply = "word " * 200

    announced = plan_voice_reply(long_reply, _settings(ai_voice_reply_mode="announce"))
    assert len(announced.announce_text) <= 140 + len("Quill says: ")
    assert announced.announce_text.endswith("...")

    spoken = plan_voice_reply(long_reply, _settings(ai_voice_reply_mode="local_tts"))
    assert spoken.spoken_text == " ".join(long_reply.split())
    assert not spoken.spoken_text.endswith("...")


def test_announce_limit_zero_speaks_the_whole_summary() -> None:
    reply = "word " * 100
    plan = plan_voice_reply(
        reply, _settings(ai_voice_reply_mode="announce", ai_voice_reply_announce_limit=0)
    )
    assert not plan.announce_text.endswith("...")
    assert plan.announce_text.endswith("word")


def test_text_mode_speaks_nothing() -> None:
    plan = plan_voice_reply("Some answer.", _settings(ai_voice_reply_mode="text"))
    assert plan.mode == "text"
    assert not plan.speaks
    assert plan.announce_text == ""


def test_ai_voice_speaks_the_whole_reply_and_is_flagged_as_cloud() -> None:
    plan = plan_voice_reply(
        "Some answer.",
        _settings(ai_voice_reply_mode="ai_voice", ai_tts_provider="openai"),
    )
    assert plan.mode == "ai_voice"
    assert plan.spoken_text == "Some answer."
    assert plan.uses_cloud, "billing/egress must be visible to the caller"


def test_ai_voice_without_a_key_degrades_to_offline_and_says_why() -> None:
    """Fallback is always *more* private, never less."""
    plan = plan_voice_reply(
        "Some answer.",
        _settings(ai_voice_reply_mode="ai_voice", ai_tts_provider="openai"),
        cloud_voice_available=False,
    )
    assert plan.mode == "local_tts"
    assert not plan.uses_cloud
    assert "API key" in plan.fallback_reason


def test_export_only_provider_cannot_speak_a_reply() -> None:
    """ElevenLabs is export-only in cloud_tts, so selecting it must degrade.

    Failing at the moment of speaking would strand the reply; this catches it
    while there is still a working alternative.
    """
    plan = plan_voice_reply(
        "Some answer.",
        _settings(ai_voice_reply_mode="ai_voice", ai_tts_provider="elevenlabs"),
    )
    assert plan.mode == "local_tts"
    assert "export" in plan.fallback_reason.lower()


def test_degrades_all_the_way_to_announcement_when_nothing_can_speak() -> None:
    plan = plan_voice_reply(
        "Some answer.",
        _settings(ai_voice_reply_mode="ai_voice", ai_tts_provider="openai"),
        cloud_voice_available=False,
        local_tts_available=False,
    )
    assert plan.mode == "announce"
    assert plan.announce_text.startswith("Quill says:")
    assert plan.fallback_reason


def test_empty_reply_produces_nothing_to_say() -> None:
    for mode in VOICE_REPLY_MODES:
        plan = plan_voice_reply("   \n  ", _settings(ai_voice_reply_mode=mode))
        assert not plan.speaks
        assert plan.announce_text == ""


@pytest.mark.parametrize("mode", VOICE_REPLY_MODES)
def test_every_mode_is_handled_and_never_both_speaks_and_announces(mode: str) -> None:
    """Speaking and announcing at once would talk over itself."""
    plan = plan_voice_reply("An answer.", _settings(ai_voice_reply_mode=mode))
    assert not (plan.spoken_text and plan.announce_text)
    assert mode_label(mode) != mode, "every mode needs human phrasing"


def test_unknown_mode_falls_back_rather_than_raising() -> None:
    """Settings validate this, but a caller constructing Settings directly may not."""
    plan = plan_voice_reply("An answer.", _settings(ai_voice_reply_mode="nonsense"))
    assert plan.mode == "announce"
    assert plan.announce_text


def test_truncate_announcement_is_the_shared_rule() -> None:
    """Replies, errors and proposals all go through this one function.

    It used to be a literal 140 inside the chat panel's announcement helper, so
    the user's configured length governed replies while errors and edit
    proposals silently kept the old number.
    """
    long_text = "word " * 100
    assert truncate_announcement(long_text, 20).endswith("...")
    assert len(truncate_announcement(long_text, 20)) == 20
    # 0 means "no cap", not "announce nothing".
    assert truncate_announcement(long_text, 0) == " ".join(long_text.split())
    # Short input is returned whole, never padded or ellipsised.
    assert truncate_announcement("Short.", 140) == "Short."
    # Whitespace is collapsed so a multi-line reply announces as one utterance.
    assert truncate_announcement("a\n\n  b\tc", 140) == "a b c"
    assert truncate_announcement("   ", 140) == ""


def test_announcement_limit_is_honoured_by_the_plan_too() -> None:
    """The same limit the helper uses also shapes a planned announcement."""
    reply = "word " * 100
    plan = plan_voice_reply(
        reply, _settings(ai_voice_reply_mode="announce", ai_voice_reply_announce_limit=30)
    )
    body = plan.announce_text.split(": ", 1)[1]
    assert len(body) == 30
