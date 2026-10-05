"""Release channels, Phases 0 and 1: the wx-free core.

``channels.json`` (round trip, unknown keys kept, corruption), the update check
filtering by channel, the birth-channel rule, waiting for Stable, the interim
shared-runtime rule, and the whole switch flow with fakes standing in for the
risk dialog and the saved copy. No network, no wx.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.updater import history
from quill.core.updater.channels import (
    ChannelsFile,
    ChannelState,
    includes_prereleases,
    load_channels,
    save_channels,
    shown_channel,
    state_for,
    update_states,
)
from quill.core.updater.check import evaluate, up_to_date_text
from quill.core.updater.policy import choose_offer, visible_on
from quill.core.updater.runtime_rule import runtime_verdict
from quill.core.updater.snapshots import SnapshotError
from quill.core.updater.switch import SwitchRequest, perform_switch, plan_switch
from quill.core.updater.wording import UNSIGNED_NOTE, risk_text, window_titles


def _r(version: str, *, prerelease: bool = False) -> SimpleNamespace:
    return SimpleNamespace(version=version, prerelease=prerelease, has_platform_asset=True)


@pytest.fixture
def store(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        channels=tmp_path / "channels.json", history=tmp_path / "update-history.jsonl"
    )


# -- channels.json -------------------------------------------------------------


def test_channels_round_trip_and_keep_what_a_newer_build_wrote(store) -> None:
    store.channels.write_text(
        json.dumps({
            "version": 1,
            "future_key": {"kept": True},
            "apps": {"radio": {"channel": "beta", "joined_from": "3.2.0", "new_field": 1}},
        }),
        encoding="utf-8",
    )
    data = load_channels(store.channels)
    assert data.state("radio").channel == "beta"
    assert data.state("radio").joined_from == "3.2.0"
    assert data.state("cast") == ChannelState()  # nothing stored: Stable
    save_channels(data.with_state("cast", ChannelState(channel="dev")), store.channels)
    written = json.loads(store.channels.read_text(encoding="utf-8"))
    assert written["future_key"] == {"kept": True}
    assert written["apps"]["cast"]["channel"] == "dev"
    assert load_channels(store.channels).state("radio").channel == "beta"


def test_a_corrupt_file_reads_as_everything_on_stable_and_is_kept_aside(store) -> None:
    store.channels.write_text("{not json", encoding="utf-8")
    assert load_channels(store.channels) == ChannelsFile()
    assert not store.channels.exists()
    assert (store.channels.parent / "channels.json.unreadable").read_text(encoding="utf-8")


def test_a_missing_file_and_an_unknown_channel_are_stable(store) -> None:
    assert state_for("radio", store.channels).channel == "stable"
    store.channels.write_text('{"apps": {"radio": {"channel": "nightly"}}}', encoding="utf-8")
    assert state_for("radio", store.channels).channel == "stable"


def test_update_states_writes_several_apps_in_one_step(store) -> None:
    update_states(
        {"radio": ChannelState(channel="beta"), "quilllite": ChannelState(channel="beta")},
        store.channels,
    )
    data = load_channels(store.channels)
    assert data.state("radio").channel == data.state("quilllite").channel == "beta"


def test_waiting_for_stable_stops_prerelease_offers() -> None:
    waiting = ChannelState(channel="beta", pending_return=True)
    assert not includes_prereleases(waiting)
    assert includes_prereleases(
        ChannelState(channel="beta", pending_return=True, keep_beta_while_waiting=True)
    )
    assert shown_channel(waiting).startswith("Stable (waiting")


# -- what a check may offer ------------------------------------------------------

RELEASES = [
    _r("3.2.0"),
    _r("3.3.0", prerelease=True),  # a candidate still soaking on Beta
    _r("3.3.0-beta.2", prerelease=True),
    _r("3.4.0-dev.20261003.1", prerelease=True),
]


def test_stable_never_sees_a_prerelease_by_flag_or_by_version() -> None:
    stable = ChannelState()
    assert choose_offer("3.1.0", RELEASES, stable).target.version == "3.2.0"
    # A final-numbered build GitHub still marks prerelease is Beta's, not Stable's.
    assert not visible_on(_r("3.3.0", prerelease=True), stable)
    # A pre-release version that GitHub forgot to flag is still not Stable's.
    assert not visible_on(_r("3.3.0-beta.3"), stable)


def test_beta_sees_beta_and_candidates_but_not_dev() -> None:
    decision = choose_offer("3.2.0", RELEASES, ChannelState(channel="beta"))
    assert decision.target.version == "3.3.0"
    assert not visible_on(RELEASES[3], ChannelState(channel="beta"))


def test_dev_sees_everything_and_newest_by_version_wins() -> None:
    decision = choose_offer("3.2.0", RELEASES, ChannelState(channel="dev"))
    assert decision.target.version == "3.4.0-dev.20261003.1"


def test_nothing_older_is_ever_offered() -> None:
    assert choose_offer("3.5.0", RELEASES, ChannelState(channel="dev")).target is None


def test_waiting_for_stable_reports_when_it_has_caught_up() -> None:
    waiting = ChannelState(channel="beta", pending_return=True)
    early = choose_offer("3.3.0-beta.2", [_r("3.2.0")], waiting)
    assert early.target is None and not early.stable_caught_up
    later = choose_offer("3.3.0-beta.2", [_r("3.2.0"), _r("3.3.0")], waiting)
    assert later.stable_caught_up and later.target.version == "3.3.0"


def test_check_sets_the_birth_channel_once_and_says_so(store) -> None:
    result = evaluate(
        "radio", "3.3.0-beta.1", [_r("3.2.0")], path=store.channels, history_path=store.history
    )
    assert result.state.channel == "beta"
    assert result.state.set_by == "installed"
    assert result.notices and "You installed a Beta version" in result.notices[0]
    again = evaluate(
        "radio", "3.3.0-beta.1", [_r("3.2.0")], path=store.channels, history_path=store.history
    )
    assert again.notices == ()  # said once, never again
    assert history.read_events("radio", store.history)[0].kind == "channel_changed"


def test_check_on_a_stable_build_with_nothing_stored_writes_nothing(store) -> None:
    result = evaluate("cast", "2.0.0", [_r("2.0.1")], path=store.channels)
    assert result.target.version == "2.0.1"
    assert not store.channels.exists()


def test_quills_old_beta_box_carries_across_once(store) -> None:
    result = evaluate(
        "quill",
        "1.0.0",
        [_r("1.1.0-beta.1", prerelease=True)],
        legacy_beta=True,
        path=store.channels,
    )
    assert result.state.channel == "beta" and result.target.version == "1.1.0-beta.1"
    assert state_for("quill", store.channels).set_by == "legacy"


def test_caught_up_moves_back_to_stable_and_says_so(store) -> None:
    save_channels(
        ChannelsFile().with_state("radio", ChannelState(channel="beta", pending_return=True)),
        store.channels,
    )
    result = evaluate(
        "radio", "3.3.0-beta.2", [_r("3.3.0")], path=store.channels, history_path=store.history
    )
    assert result.state.channel == "stable"
    assert "Stable has caught up" in result.notices[0]
    assert state_for("radio", store.channels) == result.state


def test_an_app_without_a_profile_keeps_stable_behaviour(store) -> None:
    result = evaluate(
        "weather", "2.2.0", [_r("2.3.0-beta.1", prerelease=True)], path=store.channels
    )
    assert result.target is None and not store.channels.exists()


def test_up_to_date_text_names_the_channel() -> None:
    assert up_to_date_text("3.3.0-beta.2", ChannelState(channel="beta")) == (
        "You are up to date (3.3.0 Beta 2). You are on the Beta channel."
    )
    assert "waiting for Stable" in up_to_date_text("1.0.0", ChannelState(pending_return=True))


# -- the interim shared-runtime rule (plan 6.5) -----------------------------------


def test_quill_and_portable_copies_move_freely() -> None:
    assert runtime_verdict("quill", "dev", runtime_apps=["radio"], states={}).allowed
    assert runtime_verdict(
        "radio", "beta", runtime_apps=["radio", "quilllite"], states={}, portable=True
    ).allowed


def test_a_runtime_app_alone_may_join_beta() -> None:
    assert runtime_verdict("radio", "beta", runtime_apps=["radio"], states={}).allowed
    assert runtime_verdict("radio", "beta", runtime_apps=[], states={}).allowed


def test_a_shared_runtime_needs_everyone_to_move_together() -> None:
    verdict = runtime_verdict("radio", "beta", runtime_apps=["radio", "quilllite"], states={})
    assert not verdict.allowed and verdict.must_move == ("quilllite",)
    assert "QUILL Lite on this computer shares Quill Radio's engine" in verdict.explanation
    assert runtime_verdict(
        "radio", "beta", runtime_apps=["radio", "quilllite"], states={}, moving_too=["quilllite"]
    ).allowed
    # A sibling already on that channel needs no moving.
    assert runtime_verdict(
        "radio",
        "beta",
        runtime_apps=["radio", "quilllite"],
        states={"quilllite": ChannelState(channel="beta")},
    ).allowed


def test_an_app_that_cannot_follow_keeps_everyone_on_stable() -> None:
    verdict = runtime_verdict(
        "radio",
        "beta",
        runtime_apps=["radio", "weather"],
        states={},
        display_names={"weather": "Quill Weather"},
    )
    assert not verdict.allowed and verdict.cannot_follow == ("weather",)
    assert "Quill Weather" in verdict.explanation and "stays on Stable" in verdict.explanation


def test_coming_back_is_never_blocked_by_the_runtime() -> None:
    assert runtime_verdict(
        "radio",
        "stable",
        runtime_apps=["radio", "weather"],
        states={"radio": ChannelState(channel="beta")},
    ).allowed


# -- the switch flow, with fakes ----------------------------------------------------


class _Fakes:
    def __init__(
        self, tmp_path: Path, *, risk: bool = True, wait: bool = True, snapshot_fails: str = ""
    ) -> None:
        self.tmp = tmp_path
        self.risk, self.wait, self.snapshot_fails = risk, wait, snapshot_fails
        self.asked: list[object] = []
        self.snapshots: list[tuple[str, str, str]] = []

    def confirm_risk(self, context: object) -> bool:
        self.asked.append(context)
        return self.risk

    def confirm_wait(self, plan: object) -> bool:
        self.asked.append(plan)
        return self.wait

    def take_snapshot(self, app: str, version: str, reason: str) -> Path:
        if app == self.snapshot_fails:
            raise SnapshotError("the disk is full")
        self.snapshots.append((app, version, reason))
        target = self.tmp / f"{app}-{reason}.zip"
        target.write_bytes(b"copy")
        return target

    def run(self, plan, store):
        return perform_switch(
            plan,
            confirm_risk=self.confirm_risk,
            confirm_wait=self.confirm_wait,
            take_snapshot=self.take_snapshot,
            version_of=lambda _key: "1.2.0",
            path=store.channels,
            history_path=store.history,
        )


def _plan(app: str, target: str, version: str, *, also=(), states=None, runtime=()):
    return plan_switch(
        SwitchRequest(app, target, version, tuple(also)),  # type: ignore[arg-type]
        states=states or {},
        runtime_apps=list(runtime),
    )


def test_joining_beta_asks_saves_a_copy_then_writes(tmp_path, store) -> None:
    fakes = _Fakes(tmp_path)
    outcome = fakes.run(_plan("quill", "beta", "1.0.0"), store)
    assert outcome.changed and outcome.message.endswith("QUILL is on Beta.")
    assert fakes.snapshots == [("quill", "1.0.0", "joined-beta")]
    state = state_for("quill", store.channels)
    assert state.channel == "beta" and state.joined_from == "1.0.0" and state.snapshot
    kinds = [event.kind for event in history.read_events("quill", store.history)]
    assert kinds == ["channel_changed", "snapshot_saved"]


def test_cancelling_the_risk_dialog_changes_nothing(tmp_path, store) -> None:
    fakes = _Fakes(tmp_path, risk=False)
    outcome = fakes.run(_plan("quill", "dev", "1.0.0"), store)
    assert outcome.cancelled and not outcome.changed
    assert fakes.snapshots == [] and not store.channels.exists()


def test_a_failed_copy_means_nothing_moves(tmp_path, store) -> None:
    fakes = _Fakes(tmp_path, snapshot_fails="quilllite")
    plan = _plan("radio", "beta", "3.2.0", also=["quilllite"], runtime=["radio", "quilllite"])
    outcome = fakes.run(plan, store)
    assert not outcome.changed
    assert (
        "QUILL Lite couldn't save a copy" in outcome.message
        and "the disk is full" in outcome.message
    )
    assert not store.channels.exists()


def test_moving_together_writes_every_app_in_one_step(tmp_path, store) -> None:
    fakes = _Fakes(tmp_path)
    plan = _plan("radio", "beta", "3.2.0", also=["quilllite"], runtime=["radio", "quilllite"])
    assert plan.kind == "join"
    outcome = fakes.run(plan, store)
    assert outcome.changed and "Quill Radio and QUILL Lite are on Beta" in outcome.message
    data = load_channels(store.channels)
    assert data.state("radio").channel == data.state("quilllite").channel == "beta"
    assert fakes.asked[0].also_moving == ("QUILL Lite",)


def test_a_blocked_move_explains_and_writes_nothing(tmp_path, store) -> None:
    plan = _plan("radio", "beta", "3.2.0", runtime=["radio", "quilllite"])
    assert plan.kind == "blocked"
    outcome = _Fakes(tmp_path).run(plan, store)
    assert not outcome.changed and "move them together" in outcome.message


def test_already_on_the_channel_says_so(tmp_path, store) -> None:
    outcome = _Fakes(tmp_path).run(_plan("quill", "stable", "1.0.0"), store)
    assert outcome.message == "Already on Stable." and not outcome.changed


def test_returning_on_a_final_build_is_a_same_version_flip(tmp_path, store) -> None:
    states = {"quill": ChannelState(channel="beta")}
    plan = _plan("quill", "stable", "1.1.0", states=states)
    assert plan.kind == "return_now"
    outcome = _Fakes(tmp_path).run(plan, store)
    assert outcome.changed and state_for("quill", store.channels).channel == "stable"


def test_returning_on_a_beta_build_waits_for_stable(tmp_path, store) -> None:
    states = {"radio": ChannelState(channel="beta", joined_from="3.2.0")}
    plan = _plan("radio", "stable", "3.3.0-beta.2", states=states)
    assert plan.kind == "return_wait"
    assert "moves to Stable by itself" in plan.summary()
    fakes = _Fakes(tmp_path)
    outcome = fakes.run(plan, store)
    state = state_for("radio", store.channels)
    assert outcome.changed and state.pending_return and state.channel == "beta"
    assert not includes_prereleases(state)
    declined = _Fakes(tmp_path, wait=False).run(plan, store)
    assert declined.cancelled


def test_choosing_beta_again_while_waiting_resumes(tmp_path, store) -> None:
    states = {"radio": ChannelState(channel="beta", pending_return=True)}
    plan = _plan("radio", "beta", "3.3.0-beta.2", states=states)
    assert plan.kind == "resume"
    assert _Fakes(tmp_path).run(plan, store).changed
    assert not state_for("radio", store.channels).pending_return


# -- wording -----------------------------------------------------------------------


def test_the_risk_wording_says_what_could_go_wrong_and_how_to_come_back(tmp_path, store) -> None:
    fakes = _Fakes(tmp_path, risk=False)
    fakes.run(_plan("radio", "beta", "3.2.0"), store)
    beta = risk_text(fakes.asked[0])
    assert "What could happen" in beta and "How you're protected" in beta
    assert "saves a copy of your favorites, history and settings" in beta
    assert "recordings are not copied" in beta
    assert "Help, Release Channel" in beta
    fakes.run(_plan("radio", "dev", "3.2.0"), store)
    dev = risk_text(fakes.asked[1])
    assert "Expect things to break" in dev and "Beta is probably the better choice" in dev
    # Beta and Dev builds are never code-signed (2026-10-04): both say so, once, kindly.
    for text in (beta, dev):
        assert text.count(UNSIGNED_NOTE) == 1
    assert "unknown publisher" in UNSIGNED_NOTE and "More info, then Run anyway" in UNSIGNED_NOTE


def test_every_window_title_has_an_f1_purpose() -> None:
    titles = window_titles("Quill Radio")
    assert "Release Channel: Quill Radio" in titles
    assert "Move Quill Radio to Dev?" in titles
    assert all(purpose.strip() for purpose in titles.values())
