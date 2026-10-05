"""Go back to Stable? -- the window and the flow behind it (release channels, Phase 4).

Built for real: focus on the words, the default that fits the verdict ("Go
back now" when safe, "Wait for Stable" when not), "Use the copy" only when a
copy exists, Close with no access key. The flow runs with the person's answers
faked: going back now flips the channel and hands the Stable build to the app's
own installer; waiting is the Phase 1 path; nothing is downloaded here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.data_format_ledger import Ledger, LedgerEntry  # noqa: E402
from quill.core.updater.channels import ChannelState, load_channels, save_channels  # noqa: E402
from quill.core.updater.feed import FeedAsset, FeedRelease, ReleaseFeed  # noqa: E402
from quill.core.updater.going_back import assess_return  # noqa: E402
from quill.core.updater.switch import SwitchOutcome, SwitchRequest, plan_switch  # noqa: E402
from quill.ui.updates import going_back_flow  # noqa: E402
from quill.ui.updates.return_to_stable_dialog import ReturnToStableDialog  # noqa: E402


@pytest.fixture
def wx_app():
    app = wx.App()
    wx.HelpProvider.Set(wx.SimpleHelpProvider())
    yield app
    app.Destroy()


def _release(version: str, reads: int, channels: tuple[str, ...]) -> FeedRelease:
    name = f"Quill-Radio-Setup-Shared-{version}.exe"
    url = (
        f"https://github.com/Community-Access/quill/releases/download/quill-radio-v{version}/{name}"
    )
    return FeedRelease(
        version=version,
        tag=f"quill-radio-v{version}",
        channels=channels,
        assets=(FeedAsset("installer", name, url, 10, "b" * 64),),
        reads_formats={"radio.favorites": reads},
        data_formats={"radio.favorites": reads},
    )


def _feed(stable_reads: int) -> ReleaseFeed:
    return ReleaseFeed(
        "radio",
        "Quill Radio",
        3,
        "",
        (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        (
            _release("3.2.0", stable_reads, ("stable", "beta")),
            _release("3.3.0-beta.2", 2, ("beta",)),
        ),
    )


def _labels(dialog) -> list[str]:
    return [c.GetLabel() for c in dialog.GetChildren() if isinstance(c, wx.Button)]


def test_safe_defaults_to_going_back_now(wx_app) -> None:
    assessment = assess_return(
        "radio", "3.3.0-beta.2", _feed(2), ChannelState(channel="beta"), [Ledger()], {}
    )
    dialog = ReturnToStableDialog(None, assessment, app_name="Quill Radio", channel="beta")
    try:
        assert dialog.GetTitle() == "Go back to Stable?"
        assert _labels(dialog)[0] == "&Go back to 3.2.0 now"
        assert "Close" in _labels(dialog)
        assert wx.Window.FindFocus() in (None, dialog._text)
        assert all(c.GetHelpText() for c in dialog.GetChildren() if isinstance(c, wx.Button))
    finally:
        dialog.Destroy()


def test_unsafe_offers_waiting_and_the_copy(wx_app, tmp_path: Path) -> None:
    copy = tmp_path / "radio-3.2.0-joined-beta.qrbackup"
    copy.write_bytes(b"x")
    state = ChannelState(channel="beta", snapshot=str(copy), joined_at="2026-10-03T10:00:00Z")
    ledger = Ledger({"radio.favorites": LedgerEntry(2)})
    assessment = assess_return("radio", "3.3.0-beta.2", _feed(1), state, [ledger], {})
    dialog = ReturnToStableDialog(None, assessment, app_name="Quill Radio", channel="beta")
    try:
        assert dialog.GetTitle() == "Going straight back isn't safe yet"
        labels = _labels(dialog)
        assert "&Wait for Stable" in labels and "&Use the copy from 3 October" in labels
        assert not any(label.startswith("&Go back") for label in labels)
    finally:
        dialog.Destroy()


def test_going_back_now_flips_the_channel_and_installs_stable(
    wx_app, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("QUILL_FAMILY_DIR", str(tmp_path / "family"))
    save_channels(load_channels().with_state("radio", ChannelState(channel="beta")))
    monkeypatch.setattr("quill.core.updater.feed_fetch.cached_feed", lambda app_key, **_k: _feed(2))
    monkeypatch.setattr(going_back_flow, "_portable", lambda _key: False)
    monkeypatch.setattr(ReturnToStableDialog, "answer", lambda self: "now")
    plan = plan_switch(
        SwitchRequest("radio", "stable", "3.3.0-beta.2"),
        states={"radio": ChannelState(channel="beta")},
    )
    assert plan.kind == "return_wait"
    installed: list[object] = []
    outcome = going_back_flow.go_back(
        None,
        plan,
        show_modal=lambda _d, _t: wx.ID_OK,
        announce=lambda _m: None,
        install_release=installed.append,
        wait=lambda: SwitchOutcome(False, "waited"),
    )
    assert outcome is not None and outcome.changed
    assert load_channels().state("radio").channel == "stable"
    assert [getattr(r, "version", "") for r in installed] == ["3.2.0"]


def test_no_saved_list_means_the_old_waiting_path(wx_app, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.updater.feed_fetch.cached_feed", lambda app_key, **_k: None)
    plan = plan_switch(
        SwitchRequest("radio", "stable", "3.3.0-beta.2"),
        states={"radio": ChannelState(channel="beta")},
    )
    assert (
        going_back_flow.go_back(
            None,
            plan,
            show_modal=lambda _d, _t: wx.ID_OK,
            announce=lambda _m: None,
            install_release=lambda _r: None,
            wait=lambda: SwitchOutcome(False, "waited"),
        )
        is None
    )
