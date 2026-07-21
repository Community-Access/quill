"""Guarded headless tests for the composer dialog.

Skips cleanly when wx cannot initialize. Covers the pure schedule helper, a
headless construction with real accounts, draft building with media (including
alt text) and a native poll, and that the schedule action records an epoch-ms
schedule time. Never calls MainLoop; EndModal is stubbed so the finish path can
be exercised without a modal loop.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.capabilities import Capabilities  # noqa: E402
from quill_social.model import Account, Media  # noqa: E402
from quill_social.ui import composer as composer_mod  # noqa: E402
from quill_social.ui.composer import (  # noqa: E402
    ComposerDialog,
    media_kind_for_path,
    schedule_to_ms,
)


@pytest.fixture
def app():
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def _accounts() -> list[Account]:
    return [Account(account_id="acct_1", network="mock", handle="me", is_default=True)]


def _caps(accounts) -> dict[str, Capabilities]:
    return {a.account_id: Capabilities(network=a.network) for a in accounts}


def test_schedule_to_ms_helper():
    # 2030-01-02 03:04 UTC -> known epoch ms.
    assert schedule_to_ms("2030-01-02", "03:04") == 1893553440000
    # Empty / malformed inputs return None.
    assert schedule_to_ms("", "03:04") is None
    assert schedule_to_ms("2030-01-02", "") is None
    assert schedule_to_ms("2030-13-02", "03:04") is None  # bad month
    assert schedule_to_ms("2030-01-02", "24:00") is None  # bad hour


def test_media_kind_for_path():
    assert media_kind_for_path("photo.PNG") == "image"
    assert media_kind_for_path("clip.mp4") == "video"
    assert media_kind_for_path("voice.m4a") == "audio"
    assert media_kind_for_path("data.bin") == "unknown"


def test_dialog_constructs_headlessly(app):
    accounts = _accounts()
    dlg = ComposerDialog(None, accounts, _caps(accounts))
    try:
        # Single account is auto-selected, report renders without error.
        assert dlg._selected_account_ids() == ["acct_1"]
        assert isinstance(dlg.report.GetValue(), str)
    finally:
        dlg.Destroy()


def test_build_draft_with_media_and_poll(app):
    accounts = _accounts()
    dlg = ComposerDialog(None, accounts, _caps(accounts))
    try:
        dlg.editor.SetValue("Hello there")
        dlg._media = [
            Media(kind="image", local_path="/tmp/a.png", alt_text="a cat"),
            Media(kind="image", local_path="/tmp/b.png"),
        ]
        dlg.poll_toggle.SetValue(True)
        dlg._poll_options = ["Yes", "No", ""]
        dlg.poll_multiple.SetValue(True)

        draft = dlg._build_draft()
        assert len(draft.media) == 2
        assert draft.media[0].alt_text == "a cat"
        assert draft.media[0].has_alt
        assert not draft.media[1].has_alt
        assert draft.poll is not None
        assert [o.title for o in draft.poll.options] == ["Yes", "No"]
        assert draft.poll.multiple is True
        assert draft.poll.expires_at is not None

        # Report reflects media and poll.
        dlg._refresh_report()
        report = dlg.report.GetValue()
        assert "attachment" in report
        assert "Poll" in report
    finally:
        dlg.Destroy()


def test_schedule_action_sets_schedule_at(app):
    accounts = _accounts()
    now_ms = 1_700_000_000_000
    dlg = ComposerDialog(None, accounts, _caps(accounts), now_ms=now_ms)
    try:
        dlg.editor.SetValue("Scheduled post")
        dlg.schedule_date.SetValue("2030-06-01")
        dlg.schedule_time.SetValue("09:30")
        dlg.EndModal = lambda code: None  # avoid needing a modal loop

        dlg._finish("schedule")
        assert dlg.result_action == "schedule"
        assert dlg.result_draft is not None
        assert dlg.result_schedule_at == schedule_to_ms("2030-06-01", "09:30")
    finally:
        dlg.Destroy()


def test_default_schedule_prefilled_one_hour_ahead(app):
    accounts = _accounts()
    now_ms = 1_700_000_000_000
    dlg = ComposerDialog(None, accounts, _caps(accounts), now_ms=now_ms)
    try:
        got = schedule_to_ms(dlg.schedule_date.GetValue(), dlg.schedule_time.GetValue())
        # Prefilled default is one hour ahead of the injected now (minute precision).
        assert got is not None
        assert abs(got - (now_ms + composer_mod._ONE_HOUR_MS)) < 60_000
    finally:
        dlg.Destroy()
