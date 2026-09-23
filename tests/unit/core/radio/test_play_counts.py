"""Whether a play is reported to RadioBrowser's community count."""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.radio import play_counts


@dataclass
class _Prefs:
    share_play_counts: bool = True


def test_sharing_is_the_default_and_opting_out_is_honoured() -> None:
    assert play_counts.should_report_play(_Prefs(share_play_counts=True)) is True
    assert play_counts.should_report_play(_Prefs(share_play_counts=False)) is False


def test_absent_state_means_yes_not_no() -> None:
    """An upgrade from a build predating the preference, or a caller with no
    preferences at all, must not be read as a refusal -- the stored default is
    on, and a silent absence has to agree with it."""

    class _Older:  # no share_play_counts attribute at all
        pass

    assert play_counts.should_report_play(None) is True
    assert play_counts.should_report_play(_Older()) is True  # type: ignore[arg-type]


def test_opting_out_sends_nothing(monkeypatch) -> None:
    from quill.core.radio import radio_browser

    calls: list[str] = []
    monkeypatch.setattr(radio_browser, "register_click", lambda u, **k: calls.append(u))
    play_counts.report_play("9617a958-0601-11e8-ae97-52543be04c81", history=_Prefs(False))
    assert calls == []
    play_counts.report_play("9617a958-0601-11e8-ae97-52543be04c81", history=_Prefs(True))
    assert calls == ["9617a958-0601-11e8-ae97-52543be04c81"]


def test_safe_mode_travels_through(monkeypatch) -> None:
    from quill.core.radio import radio_browser

    seen: dict[str, object] = {}
    monkeypatch.setattr(radio_browser, "register_click", lambda u, **k: seen.update(uuid=u, **k))
    play_counts.report_play("u", history=_Prefs(True), safe_mode=True)
    assert seen["safe_mode"] is True


def test_a_failure_never_surfaces(monkeypatch) -> None:
    """A missed vote is not worth a message, let alone interrupting playback."""
    from quill.core.radio import radio_browser

    def boom(_u, **_k):
        raise OSError("the directory is down")

    monkeypatch.setattr(radio_browser, "register_click", boom)
    play_counts.report_play("u", history=_Prefs(True))  # must not raise
