"""ear.md A10: where QUILL Cast's AI is not allowed, as a test rather than a promise.

No AI on a path that deletes, unfollows or spends; no AI in a background pass;
no AI request the listener did not start. The background passes -- the feed
check, the schedule, retention and housekeeping -- and the destructive verbs
must not reach the AI service at all, so this reads their source for any way
in. Cast's AI lives in ``quill/ui/podcasts/cast_ai_features.py``, where every
verb starts from a menu row the listener pressed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]

#: Background passes and destructive verbs.
NO_AI: tuple[str, ...] = (
    "quill/core/podcasts/check_state.py",
    "quill/core/podcasts/refresh_policy.py",
    "quill/core/podcasts/refresh_schedule.py",
    "quill/core/podcasts/schedule_policy.py",
    "quill/core/podcasts/retention.py",
    "quill/core/podcasts/episode_filter_maintenance.py",
    "quill/core/podcasts/refresh_audio.py",
    "quill/ui/podcasts/check_monitor.py",
    "quill/ui/podcasts/feed_refresh.py",
    "quill/ui/podcasts/folder_watch.py",
    "quill/ui/podcasts/show_actions.py",
    "quill/ui/main_frame_podcast_session.py",
)
#: Any of these in a module's source is a way to the AI.
WAYS_IN: tuple[str, ...] = (
    "hosted_ai",
    "_ai_service",
    "AiService",
    "own_key",
    "chatgpt",
    "cast_ai_features",
    "ai_listening",
    "ai_organise",
)


@pytest.mark.parametrize("relative", NO_AI)
def test_a_background_pass_or_destructive_verb_never_reaches_the_ai(relative: str) -> None:
    source = (ROOT / relative).read_text(encoding="utf-8")
    found = [way for way in WAYS_IN if way in source]
    assert found == [], f"{relative} reaches the AI through {found}"


def test_every_cast_ai_verb_is_a_menu_row_the_listener_presses() -> None:
    from quill.ui.podcasts.cast_ai_features import AI_FEATURE_ROWS, CastDomainAiMixin

    for _command, _label, handler in AI_FEATURE_ROWS:
        assert callable(getattr(CastDomainAiMixin, handler))
    # Nothing schedules them: no timer, no task submit, no idle hook in the module.
    source = (ROOT / "quill/ui/podcasts/cast_ai_features.py").read_text(encoding="utf-8")
    for forbidden in ("wx.Timer", "CallLater", "EVT_IDLE", "_task_manager.submit"):
        assert forbidden not in source
