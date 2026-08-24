"""Nothing tells Cast's listener when a media tool is missing (list.md 5.3).

Quill Radio says it once, in one plain sentence, and stays quiet on a healthy
install. QUILL Cast said nothing at all -- and Cast needs FFmpeg for more than
Radio does, in ways that are much harder to notice.

That is the point worth pinning. A missing playback engine announces itself:
the station does not play. Every one of Cast's FFmpeg features fails by
producing a **plausible** result. The download completes and is not trimmed.
The episode plays and is not normalised. The chapter analysis finishes and
finds nothing, which is exactly what an episode with no chapters looks like.
None of those are distinguishable from working, so nobody reports them.
"""

from __future__ import annotations

from quill.core.podcasts.media_health import FFMPEG_CAPABILITIES, CastMediaHealth


def test_a_healthy_install_says_nothing_at_launch() -> None:
    """The rule the rest of the app follows: a launch that reports all-is-well
    every time is a launch nobody can listen past."""
    healthy = CastMediaHealth(ffmpeg=True)

    assert healthy.healthy is True
    assert healthy.summary() == ""
    assert healthy.notice() == ""
    assert healthy.lost_capabilities == ()


def test_asking_always_gets_an_answer_even_when_all_is_well() -> None:
    """The one place silence would be wrong: somebody chose a menu item.

    A menu item that says nothing reads as a broken menu item, not as good
    news -- so the readout, unlike the notice, is never empty.
    """
    said = CastMediaHealth(ffmpeg=True).readout()

    assert said
    assert "installed" in said


def test_a_missing_tool_names_what_it_costs_rather_than_itself() -> None:
    """ "FFmpeg is missing" alone is a fact about a machine. What the listener
    needs is what it means for them."""
    said = CastMediaHealth(ffmpeg=False).summary()

    assert "FFmpeg is missing" in said
    for capability in FFMPEG_CAPABILITIES:
        assert capability in said


def test_it_says_what_still_works_too() -> None:
    """Otherwise a missing optional tool reads as a broken app, and somebody
    stops using a podcast player that downloads and plays perfectly well."""
    said = CastMediaHealth(ffmpeg=False).summary()

    assert "download and play normally" in said


def test_the_repair_advice_leads_with_the_thing_that_works_for_everybody() -> None:
    hint = CastMediaHealth(ffmpeg=False).repair_hint()

    assert hint.startswith("Choose Help, then Get FFmpeg")
    assert "reinstalling restores it" in hint


def test_the_thin_installer_is_not_told_to_reinstall_it() -> None:
    """The lite edition carries no media tools at all, so a reinstall cannot
    help. Advice that sends somebody to repeat an install that could not have
    worked is worse than no advice."""
    hint = CastMediaHealth(ffmpeg=False).repair_hint(lite=True)

    assert "reinstalling restores" not in hint
    assert "full QUILL Cast installer" in hint


def test_the_notice_is_the_summary_and_the_repair_together() -> None:
    health = CastMediaHealth(ffmpeg=False)

    assert health.notice() == f"{health.summary()} {health.repair_hint()}"


def test_the_signature_distinguishes_the_two_states() -> None:
    """Notices are remembered against this rather than a "told them" flag, so
    a machine repaired and later broken again is told again."""
    assert CastMediaHealth(ffmpeg=True).signature() != CastMediaHealth(ffmpeg=False).signature()


def test_the_capability_list_is_written_for_a_listener_not_an_engineer() -> None:
    """Every entry is a real call site, but named as the thing the listener
    chose rather than the function that implements it."""
    for capability in FFMPEG_CAPABILITIES:
        assert capability[0].islower() or capability.startswith("Sound Enhancements")
        assert "ffmpeg" not in capability.lower()
        assert "()" not in capability


def test_the_list_is_joined_so_a_listener_can_find_the_boundaries() -> None:
    """These phrases contain commas and "and" of their own; comma-joining them
    produces one long run with no audible edges."""
    said = CastMediaHealth(ffmpeg=False).summary()

    assert "; " in said
