"""Every app in the family opens maximized and remembers what you do to it.

A source-level check rather than a launch, because launching eleven apps in a
test is not a thing anybody would run -- and because the failure this catches is
a *new* app quietly shipping the old behaviour. Before 2026-09-10 every app
opened at a size written into its own source and forgot the window entirely:
Quill Radio at 460x360, QUILL at 1000x700, Beacon at 1100x720, relaunch after
relaunch.

The check is that each app names itself to the geometry layer. What that layer
then does is asserted in ``tests/unit/core/test_window_geometry.py`` and
``tests/unit/ui/test_window_state.py``; there is no point re-testing it once per
app.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.app_launcher import APP_NAMES

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: app key -> the module whose main window has to be wired. QuillLite is absent
#: on purpose (see below) and so is Beacon, which is not in APP_NAMES.
_MAIN_WINDOW: dict[str, str] = {
    "quill": "quill/ui/main_frame.py",
    "radio": "quill/apps/radio.py",
    "weather": "quill/apps/weather.py",
    "cast": "quill/apps/podcasts.py",
    "studio": "quill/apps/studio.py",
    "converter": "quill/apps/converter.py",
    "player": "quill/apps/player.py",
    "inkwell": "quill/apps/inkwell.py",
}


def _source(relative: str) -> str:
    return (_REPO_ROOT / relative).read_text(encoding="utf-8")


@pytest.mark.parametrize(("app_key", "module"), sorted(_MAIN_WINDOW.items()))
def test_every_app_names_itself_to_the_geometry_layer(app_key: str, module: str) -> None:
    """The app id is what keeps QUILL's window size from being Quill Radio's."""
    text = _source(module)
    # Either seam counts: the shared shell takes app_id, and the two apps that
    # build their own frame call the helper directly. A plain substring rather
    # than a regex over the call -- size=(460, 360) has a bracket in it, and a
    # pattern clever enough to span that is one nobody can read.
    wired = (
        f'app_id="{app_key}"' in text or f'apply_window_geometry(self.frame, "{app_key}"' in text
    )
    assert wired, f"{module} does not pass {app_key!r} to the geometry layer"


def test_beacon_is_wired_too() -> None:
    """Not in APP_NAMES -- it is a browser companion rather than a launchable
    sibling -- but it is a main window and it opened at 1100x720 every time."""
    assert 'apply_window_geometry(self, "beacon"' in _source("quill/apps/beacon/app.py")


def test_every_launchable_app_is_accounted_for() -> None:
    """A new app in the launcher table fails this until somebody wires it.

    Named rather than globbed: the point is that adding an app is a decision
    about its window too, and a test that discovers modules would quietly pass
    for an app it never found.
    """
    missing = sorted(set(APP_NAMES) - set(_MAIN_WINDOW))
    assert missing == [], f"apps with no window-geometry wiring: {missing}"


def test_quilllite_keeps_its_own_store_and_still_defaults_to_maximized() -> None:
    """The one deliberate exception, and it must not drift into the shared store.

    QuillLite keeps its geometry in its own settings file for the same reason it
    keeps its abbreviations there: a machine that has never had QUILL installed
    must not grow a Quill data folder because somebody opened a text file. What
    it must *not* differ on is the default.
    """
    from quill.core.lite.settings import Settings

    assert Settings().window_maximized is True
    assert "window_geometry" not in _source("quill/apps/lite.py")
