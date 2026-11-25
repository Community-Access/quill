"""FUX-02: Radio offers the QUILL Cast handoffs only where Cast can take them."""

from __future__ import annotations

import pytest

from quill.core import app_launcher
from quill.core.radio import cast_handoff, row_actions


def _episode_row() -> list[str]:
    actions = row_actions.station_actions(
        playing=False,
        saved=False,
        has_homepage=False,
        can_download=True,
        can_report=False,
        is_recording=True,
        episode_played=False,
    )
    return [action.id for action in actions]


@pytest.mark.parametrize(
    ("released", "argv", "offered"),
    [(True, ["cast"], True), (False, ["cast"], False), (True, None, False)],
)
def test_the_cast_rows_follow_release_and_install(
    monkeypatch: pytest.MonkeyPatch, released: bool, argv: list[str] | None, offered: bool
) -> None:
    monkeypatch.setattr(app_launcher, "is_app_released", lambda key: released)
    monkeypatch.setattr(app_launcher, "build_launch_argv", lambda key: argv)
    ids = _episode_row()
    assert (cast_handoff.CAST_PLAY_NEXT in ids) is offered
    assert (cast_handoff.CAST_SEND_TO_INBOX in ids) is offered
    assert row_actions.MARK_EPISODE_PLAYED in ids
