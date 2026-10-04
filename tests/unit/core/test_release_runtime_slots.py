"""Release channels, Phase 3: channel runtime slots for the shared runtime.

Each channel has its own runtime folder (``Runtime\\3.13``, ``3.13-beta``,
``3.13-dev``); within a slot the newest build wins, across slots nothing is
shared. This pins the Python side (``runtime_slots``, slot-keyed
``runtime_refs``, the marker reader, the lifted interim rule, the risk window's
disk sentence, the update helper's ``/CHANNEL``, and the channel-aware
GATE-SIBVER) and the agreement between the installer fragment, the runtime
installer and its publish script. The launcher's C side has its own mirror in
``tests/unit/native/test_runtime_slot_resolver.py``. Nothing is built or run.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from quill.core import runtime_cli, runtime_refs
from quill.core.app_version import read_marker_value, runtime_slot
from quill.core.self_update import build_apply_update_script
from quill.core.updater.channels import ChannelState
from quill.core.updater.runtime_rule import runtime_verdict
from quill.core.updater.runtime_slots import (
    SLOT_EXTRA_MB,
    channel_of_slot,
    default_channel,
    installer_args,
    is_valid_slot,
    launcher_slot_dir,
    self_heal_tag,
    slot_for,
    slots_in_use,
)
from quill.core.updater.switch import RiskContext
from quill.core.updater.wording import risk_text

REPO = Path(__file__).resolve().parents[3]


# -- slots ----------------------------------------------------------------------


def test_each_channel_has_its_own_slot() -> None:
    assert slot_for("stable") == "3.13"
    assert slot_for("beta") == "3.13-beta"
    assert slot_for("dev") == "3.13-dev"
    assert [channel_of_slot(s) for s in ("3.13", "3.13-beta", "3.13-dev")] == [
        "stable",
        "beta",
        "dev",
    ]


@pytest.mark.parametrize(
    ("version", "requested", "channel"),
    [
        ("3.3.0", "", "stable"),
        ("3.3.0-beta.2", "", "beta"),
        ("3.3.0-rc.1", "", "beta"),
        ("3.3.0-dev.20261003.1", "", "dev"),
        ("3.3.0", "beta", "beta"),
        ("3.3.0-beta.1", "stable", "stable"),
    ],
)
def test_the_installers_default_channel(version, requested, channel) -> None:
    assert default_channel(version, requested) == channel


def test_self_heal_tags_and_runtime_latest_stays_an_alias() -> None:
    assert self_heal_tag("3.13") == "runtime-latest"
    assert self_heal_tag("3.13-beta") == "runtime-beta"
    assert self_heal_tag("3.13-dev") is None


def test_launcher_rule_in_python(tmp_path: Path) -> None:
    assert launcher_slot_dir(tmp_path, "3.13-beta") == tmp_path / "QuillVille/Runtime/3.13-beta"
    for bad in ("", "..\\..\\Windows", "3.13-evil", "3", "beta"):
        assert not is_valid_slot(bad)
        assert launcher_slot_dir(tmp_path, bad) == tmp_path / "QuillVille/Runtime/3.13"


def test_installer_args_always_name_the_channel() -> None:
    assert installer_args("beta") == ["/CHANNEL=beta"]
    assert installer_args("nonsense") == ["/CHANNEL=stable"]


# -- reference counting by slot ------------------------------------------------------


def test_refs_by_slot_keep_an_older_apps_stable_folder(tmp_path: Path) -> None:
    runtime_refs.register(tmp_path, "weather", "3.13.1")  # an installer from before slots
    runtime_refs.register(tmp_path, "radio", "3.13-beta")
    assert runtime_refs.slot_of("3.13.14") == "3.13"
    assert runtime_refs.slot_referenced(tmp_path, "3.13")
    assert runtime_refs.slot_referenced(tmp_path, "3.13-beta")
    assert slots_in_use(runtime_refs.all_refs(tmp_path)) == {
        "3.13": ["weather"],
        "3.13-beta": ["radio"],
    }


def test_the_last_app_leaving_a_beta_slot_frees_it(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_cli, "_data_dir", lambda: tmp_path)
    runtime_refs.register(tmp_path, "radio", "3.13-beta")
    runtime_refs.register(tmp_path, "quilllite", "3.13")
    assert runtime_cli.main(["unregister", "radio", "3.13-beta"]) == 10
    assert runtime_cli.main(["unregister", "nothing", "3.13"]) == 0


# -- the marker -------------------------------------------------------------------


def test_marker_slot_and_channel(tmp_path: Path) -> None:
    (tmp_path / "quill-app-version.ini").write_text(
        "[app]\nversion=3.3.0-beta.2\nchannel=beta\n\n[runtime]\nslot=3.13-beta\n",
        encoding="utf-8",
    )
    assert read_marker_value(tmp_path, "app", "channel") == "beta"
    assert runtime_slot(tmp_path) == "3.13-beta"
    assert runtime_slot(tmp_path / "missing") == ""


# -- the rule the slots retire -------------------------------------------------------


def test_with_slots_a_runtime_app_moves_alone() -> None:
    states = {"quilllite": ChannelState(), "radio": ChannelState()}
    interim = runtime_verdict("radio", "beta", runtime_apps=["radio", "quilllite"], states=states)
    assert not interim.allowed
    slotted = runtime_verdict(
        "radio", "beta", runtime_apps=["radio", "quilllite", "weather"], states=states, slots=True
    )
    assert slotted.allowed


def test_the_risk_window_states_the_disk_cost_for_runtime_apps_only() -> None:
    def context(uses_runtime: bool) -> RiskContext:
        return RiskContext("radio", "Quill Radio", "beta", (), "x", "y", uses_runtime)

    assert f"about {SLOT_EXTRA_MB} MB more disk space" in risk_text(context(True))
    assert "MB" not in risk_text(context(False))
    assert SLOT_EXTRA_MB == 335


# -- the update helper ---------------------------------------------------------------


def test_installer_mode_passes_the_channel_and_a_log(tmp_path: Path) -> None:
    script = build_apply_update_script(
        pid=1,
        mode="installer",
        install_dir=tmp_path,
        exe_path=tmp_path / "QuillRadio.exe",
        log_path=tmp_path / "apply.log",
        setup_exe=tmp_path / "Setup.exe",
        channel="beta",
        setup_log=tmp_path / "setup-3.3.0.log",
    )
    assert "'/CHANNEL=beta'" in script
    assert "/LOG=" in script and "setup-3.3.0.log" in script


# -- GATE-SIBVER-CH -----------------------------------------------------------------


def _sibver():
    spec = importlib.util.spec_from_file_location(
        "check_sibling_versions", REPO / "scripts" / "check_sibling_versions.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_sibling_versions"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_beta_and_dev_slots_may_carry_a_sibling_ahead_stable_may_not() -> None:
    sib = _sibver()
    sources = {"quilllite": "1.3.0", "radio": "3.2.0"}
    published = {"quilllite": "1.2.0", "radio": "3.2.0"}
    assert sib.disagreements(sources, published, {"radio"}, channel="beta") == [
        "radio: this build says it is releasing radio, but source still says 3.2.0, which "
        "is already published. Bump the version in the release commit."
    ]
    strict = sib.disagreements(sources, published, set(), channel="stable")
    assert any(p.startswith("quilllite: source says 1.3.0") for p in strict)
    behind = sib.disagreements({"radio": "3.1.0"}, {"radio": "3.2.0"}, set(), channel="dev")
    assert behind and "behind" in behind[0]


# -- the installers agree --------------------------------------------------------------


def test_the_fragment_installs_registers_and_uninstalls_by_slot() -> None:
    fragment = (REPO / "installer" / "shared-runtime.iss").read_text(encoding="utf-8")
    assert "{param:CHANNEL|}" in fragment
    assert "function RuntimeSlot(Param: string): string;" in fragment
    assert 'Key: "slot"; String: "{code:RuntimeSlot}"' in fragment
    assert 'Key: "channel"; String: "{code:InstallChannel}"' in fragment
    assert "runtime_cli register {#AppRefId} {code:RuntimeSlot}" in fragment
    assert "GetIniString('runtime', 'slot'" in fragment
    assert "unregister {#AppRefId} ' + gUninstallSlot" in fragment


def test_the_runtime_installer_builds_a_beta_slot_and_publishes_both_tags() -> None:
    iss = (REPO / "standalone" / "runtime" / "installer" / "quillville-runtime.iss").read_text(
        encoding="utf-8"
    )
    script = (REPO / "standalone" / "runtime" / "build_runtime_installer.ps1").read_text(
        encoding="utf-8"
    )
    assert "DefaultDirName={localappdata}\\QuillVille\\Runtime\\{#RuntimeSlot}" in iss
    assert iss.count("AppId=") == 2
    assert '@("runtime-stable", "runtime-latest")' in script
    assert '@("runtime-beta")' in script
    assert "/dRuntimeSlot=$pythonMinor-beta" in script
