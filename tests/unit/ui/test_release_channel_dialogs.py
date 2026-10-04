"""The release-channel windows (plan 7.2 to 7.6), built for real.

The decisions are tested without wx in tests/unit/core; this file pins what a
keyboard and screen-reader user meets: the titles F1 knows, focus landing on
the words rather than a button, choosing never happening on a selection
change, Move refusing until the box is ticked, Escape meaning "change nothing",
and the flow running the core with the person's answers.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

from quill.core.updater import history  # noqa: E402
from quill.core.updater.channels import ChannelState, load_channels  # noqa: E402
from quill.core.updater.switch import RiskContext, SwitchRequest, plan_switch  # noqa: E402
from quill.ui.updates import flow  # noqa: E402
from quill.ui.updates.channel_risk_dialog import TICK_FIRST, RiskDialog  # noqa: E402
from quill.ui.updates.release_channel_dialog import ReleaseChannelDialog  # noqa: E402
from quill.ui.updates.update_history_dialog import (  # noqa: E402
    UpdateHistoryDialog,
    details_text,
)


@pytest.fixture
def wx_app():
    app = wx.App()
    # SetHelpText stores nothing without a provider; the apps install one at
    # activation (app_context_help.ensure_help_provider).
    wx.HelpProvider.Set(wx.SimpleHelpProvider())
    yield app
    app.Destroy()


@pytest.fixture
def family(tmp_path: Path, monkeypatch) -> Path:
    folder = tmp_path / "QuillVille"
    monkeypatch.setenv("QUILL_FAMILY_DIR", str(folder))
    return folder


def _context(target: str = "beta") -> RiskContext:
    return RiskContext(
        app_key="radio",
        display_name="Quill Radio",
        target=target,  # type: ignore[arg-type]
        also_moving=(),
        snapshot_covers="your favorites, history and settings",
        snapshot_leaves="Your recordings are not copied, and updates don't change them.",
        uses_shared_runtime=True,
    )


def _describe(target: str, also: tuple[str, ...]):
    return plan_switch(SwitchRequest("quill", target, "1.0.0", also), states={})  # type: ignore[arg-type]


def test_the_chooser_explains_without_changing_anything(wx_app, family) -> None:
    dialog = ReleaseChannelDialog(
        None,
        app_name="QUILL",
        state=ChannelState(),
        siblings=[("quilllite", "QUILL Lite", ChannelState())],
        describe=_describe,
        show_history=lambda: None,
    )
    try:
        assert dialog.GetTitle() == "Release Channel: QUILL"
        assert dialog.chosen() == "stable"
        assert "on Stable already" in dialog._meaning.GetValue()
        dialog._choices.SetSelection(2)  # arrowing to Dev only explains
        dialog._refresh(None)
        assert dialog.chosen() == "dev"
        assert "will move to Dev" in dialog._meaning.GetValue()
        assert dialog.also_move() == ()  # every sibling unticked by default
        assert not load_channels().apps  # nothing was written
        for control in (dialog._choices, dialog._meaning, dialog._switch):
            assert control.GetHelpText().strip()
    finally:
        dialog.Destroy()


def test_move_does_nothing_until_the_box_is_ticked(wx_app) -> None:
    said: list[str] = []
    dialog = RiskDialog(None, _context("dev"), announce=said.append)
    try:
        assert dialog.GetTitle() == "Move Quill Radio to Dev?"
        assert "Expect things to break" in dialog._text.GetValue()
        dialog._on_move(None)
        assert said == [TICK_FIRST]
        assert dialog.answer() == "stay"
        assert dialog.GetEscapeId() == wx.ID_CANCEL
        assert dialog._understood.GetHelpText().strip()
    finally:
        dialog.Destroy()


def test_history_rows_show_every_detail(wx_app, tmp_path) -> None:
    path = tmp_path / "update-history.jsonl"
    history.record(
        "quill",
        "channel_changed",
        from_version="1.0.0",
        channel="beta",
        detail="Joined Beta.",
        path=path,
    )
    events = history.read_events("quill", path)
    dialog = UpdateHistoryDialog(None, app_name="QUILL", events=events)
    try:
        assert dialog.GetTitle() == "Update History: QUILL"
        assert dialog._list.GetItemCount() == 1
        assert dialog._list.GetItemText(0, 1) == "Changed release channel"
        text = details_text(events[0])
        assert "From version: 1.0.0" in text and "Channel: Beta" in text
    finally:
        dialog.Destroy()


def test_the_flow_runs_the_core_with_the_persons_answers(wx_app, family, monkeypatch) -> None:
    taken: list[tuple[str, str, str]] = []

    def _snapshot(app: str, version: str, reason: str, **_kw) -> Path:
        taken.append((app, version, reason))
        target = family / f"{app}.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"copy")
        return target

    monkeypatch.setattr(flow.snapshots, "take_snapshot", _snapshot)

    def _show(dialog, _title):
        if isinstance(dialog, ReleaseChannelDialog):
            dialog._choices.SetSelection(1)  # Beta
            return wx.ID_OK
        if isinstance(dialog, RiskDialog):
            dialog._understood.SetValue(True)
            dialog._answer = "move"
            return wx.ID_OK
        return wx.ID_CANCEL

    said: list[str] = []
    changed: list[ChannelState] = []
    checked: list[bool] = []
    outcome = flow.open_release_channel(
        None,
        app_key="quill",
        installed_version="1.0.0",
        show_modal=_show,
        announce=said.append,
        on_changed=changed.append,
        check_now=lambda: checked.append(True),
    )
    assert outcome is not None and outcome.changed
    assert taken == [("quill", "1.0.0", "joined-beta")]
    assert load_channels().state("quill").channel == "beta"
    assert said == ["Saved a copy of your settings. QUILL is on Beta."]
    assert changed[0].channel == "beta" and checked == [True]


def test_escape_on_the_chooser_changes_nothing(wx_app, family) -> None:
    outcome = flow.open_release_channel(
        None,
        app_key="quill",
        installed_version="1.0.0",
        show_modal=lambda _d, _t: wx.ID_CANCEL,
        announce=lambda _m: None,
    )
    assert outcome is None and not load_channels().apps


def test_runtime_context_for_quill_has_no_runtime(wx_app) -> None:
    assert flow.runtime_context("quill") == ([], False)
    assert SimpleNamespace  # keep the import honest for type checkers
