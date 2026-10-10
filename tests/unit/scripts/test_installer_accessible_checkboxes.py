"""Installer choices must be native checkboxes a screen reader can read.

Inno Setup draws [Tasks] entries and postinstall [Run] entries in a
TNewCheckListBox, a custom-drawn control that does not expose its checked
state: a screen reader announces every box as "not checked" whatever it is.
Every family installer builds the same choices from TNewCheckBox instead (a
real Windows BUTTON control) in its [Code] section. These tests keep a new
installer, or a new task on an old one, from bringing the check list back.

They also pin the build to Inno Setup 7: scripts/BuildEnv.ps1 used to fall
back to version 6, which rejects the v7-only directives the family uses.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

INSTALLER_SCRIPTS = sorted(REPO.glob("standalone/*/installer/*.iss")) + [
    REPO / "installer" / "quill.iss"
]

_DESKTOP = re.compile(r"\{(?:autodesktop|userdesktop|commondesktop)\}", re.IGNORECASE)
_CHECK_FUNCS = re.compile(r"\bCheck:\s*([^;]+)")


def _entry_lines(text: str) -> list[str]:
    """Non-blank, non-comment lines (Inno comments start with ';')."""
    return [
        line
        for line in (raw.strip() for raw in text.splitlines())
        if line and not line.startswith(";")
    ]


def _ids(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def test_every_family_installer_is_covered() -> None:
    names = {p.name for p in INSTALLER_SCRIPTS}
    # The ones the owner listed; a rename should fail here, not go unchecked.
    for expected in (
        "quill.iss",
        "quill-radio.iss",
        "quilllite.iss",
        "quill-cast.iss",
        "quill-cast-shared.iss",
        "quill-weather.iss",
        "quill-weather-lite.iss",
        "quill-audio-studio.iss",
        "quill-audio-studio-lite.iss",
        "quill-inkwell.iss",
        "quill-inkwell-lite.iss",
        "quill-social.iss",
        "quill-social-shared.iss",
        "quill-social-lite.iss",
        "quill-beacon.iss",
        "quill-beacon-shared.iss",
        "quill-beacon-lite.iss",
    ):
        assert expected in names


@pytest.mark.parametrize("script", INSTALLER_SCRIPTS, ids=_ids)
def test_no_tasks_section_and_no_postinstall_entry(script: Path) -> None:
    lines = _entry_lines(script.read_text(encoding="utf-8"))
    assert not any(line.lower() == "[tasks]" for line in lines), (
        f"{_ids(script)} has a [Tasks] section; build the choice from a TNewCheckBox in [Code]"
    )
    offenders = [
        line for line in lines if re.search(r"\bFlags:[^;]*\bpostinstall\b", line, re.IGNORECASE)
    ]
    assert not offenders, (
        f"{_ids(script)} has a postinstall [Run] entry; offer it as a TNewCheckBox on the "
        f"Finished page instead: {offenders}"
    )
    gated = [line for line in lines if re.search(r"(^|;)\s*Tasks:", line)]
    assert not gated, f"{_ids(script)} gates entries on a task: {gated}"
    assert "WizardIsTaskSelected" not in script.read_text(encoding="utf-8")


@pytest.mark.parametrize("script", INSTALLER_SCRIPTS, ids=_ids)
def test_desktop_icon_choice_is_a_native_checkbox(script: Path) -> None:
    text = script.read_text(encoding="utf-8")
    desktop = [line for line in _entry_lines(text) if _DESKTOP.search(line)]
    if not desktop:
        pytest.skip("no desktop icon")
    assert "TNewCheckBox" in text, f"{_ids(script)} has a desktop icon but no TNewCheckBox"


@pytest.mark.parametrize("script", INSTALLER_SCRIPTS, ids=_ids)
def test_every_check_function_is_defined(script: Path) -> None:
    """A Check: naming a Wants* checkbox function must have that function."""
    text = script.read_text(encoding="utf-8")
    code = text.split("[Code]", 1)[1] if "[Code]" in text else ""
    for line in _entry_lines(text):
        for expr in _CHECK_FUNCS.findall(line):
            for name in re.findall(r"\bWants\w+", expr):
                assert re.search(rf"function {name}\(\): Boolean;", code), (
                    f"{_ids(script)}: Check: {name} has no function in [Code]"
                )


@pytest.mark.parametrize("script", INSTALLER_SCRIPTS, ids=_ids)
def test_launch_checkbox_never_runs_in_a_silent_install(script: Path) -> None:
    """The replaced run entries were skipifsilent; the checkbox must be too."""
    text = script.read_text(encoding="utf-8")
    if "LaunchCheck" not in text:
        pytest.skip("no launch checkbox")
    assert "WizardSilent" in text
    assert "ewNoWait" in text
    # Every launch default was unchecked; keep it that way.
    assert "LaunchCheck.Checked := True" not in text


def test_build_env_requires_inno_setup_7() -> None:
    build_env = (REPO / "scripts" / "BuildEnv.ps1").read_text(encoding="utf-8")
    assert "Inno Setup 6" not in build_env
    assert "Inno Setup 7" in build_env
