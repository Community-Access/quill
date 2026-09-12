"""Every app in the family has the same way of reaching a person.

A source-level check rather than a launch, for the same reason as
``test_every_app_remembers_its_window``: the failure worth catching is a *new*
app quietly shipping without it. Until 2026-09-11 six of the ten surfaces had no
reporting item at all -- Quill Weather, Quill Converter, Quill Media Player,
Quill Inkwell, QuillBeacon and QuillLite printed the support address in their
About box and left you to copy it out by hand -- and the four that did have one
filed a GitHub issue in a public repository that the reporter could not be
answered in.

What the item then does is asserted in ``tests/unit/ui/test_support_dialog.py``
and ``tests/unit/core/test_support_message.py``; there is no point re-testing it
once per app.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.app_launcher import APP_NAMES
from quill.core.support_message import SUPPORT_EMAIL, SUPPORT_MENU_KEY

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: app key -> the module that builds its Help menu.
_HELP_MENU: dict[str, str] = {
    "quill": "quill/ui/main_frame_menu.py",
    "radio": "quill/apps/radio.py",
    "weather": "quill/apps/weather.py",
    "cast": "quill/apps/podcasts_menu.py",
    "studio": "quill/apps/studio.py",
    "converter": "quill/apps/converter.py",
    "player": "quill/apps/player.py",
    "inkwell": "quill/apps/inkwell.py",
}

#: Where each app's About box is written. The address belongs here too: About is
#: where people look for it first, and it is the path that still works when the
#: form cannot open at all.
_ABOUT: dict[str, str] = {
    "quill": "quill/ui/info_pages.py",
    "radio": "quill/apps/radio.py",
    "weather": "quill/apps/weather_help.py",
    "cast": "quill/apps/podcasts.py",
    "studio": "quill/apps/studio.py",
    "converter": "quill/apps/converter.py",
    "player": "quill/apps/player.py",
    "inkwell": "quill/apps/inkwell.py",
    "beacon": "quill/apps/beacon/app.py",
    "lite": "quill/apps/lite_window_commands.py",
}


def _source(relative: str) -> str:
    return (_REPO_ROOT / relative).read_text(encoding="utf-8")


@pytest.mark.parametrize(("app_key", "module"), sorted(_HELP_MENU.items()))
def test_every_app_offers_get_help_from_support(app_key: str, module: str) -> None:
    """Either seam counts: the shared menu helper, or the label written out."""
    text = _source(module)
    wired = "append_get_help_item" in text or "Get Help from &Support" in text
    assert wired, f"{module} has no Get Help from Support item"


def test_beacon_and_quilllite_have_it_too() -> None:
    """Neither is in APP_NAMES -- one is a browser companion, the other the
    editor-only sibling -- and both are somebody's whole experience of Quill."""
    assert "Get Help from &Support" in _source("quill/apps/beacon/app.py")
    assert "cmd_get_help_from_support" in _source("quill/core/lite/commands.py")


def test_every_launchable_app_is_accounted_for() -> None:
    """A new app fails this until somebody gives it the item.

    Named rather than globbed, for the same reason as the window-geometry gate:
    adding an app is a decision about how its users reach support, and a test
    that discovers modules would quietly pass for an app it never found.
    """
    missing = sorted(set(APP_NAMES) - set(_HELP_MENU))
    assert missing == [], f"apps with no support item: {missing}"


@pytest.mark.parametrize(("app_key", "module"), sorted(_ABOUT.items()))
def test_every_about_box_gives_the_support_address(app_key: str, module: str) -> None:
    text = _source(module)
    assert SUPPORT_EMAIL in text or "SUPPORT_EMAIL" in text, (
        f"{module} does not show the support address"
    )


def test_the_family_key_is_one_key() -> None:
    """One chord, everywhere. A support key that differs per app is one nobody
    remembers on the day they need it.

    QUILL is checked through the keymap rather than the label, because its menu
    renders whatever ``help.report_bug`` is *actually* bound to -- which is the
    house rule, and what lets the key follow a listener who rebinds it.
    """
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["help.report_bug"] == SUPPORT_MENU_KEY

    for module in {*_HELP_MENU.values(), "quill/ui/support_menu.py"}:
        for line in _source(module).splitlines():
            if "Get Help from &Support" not in line:
                continue
            if "_menu_label" in line or "SUPPORT_MENU_KEY" in line:
                continue  # the key comes from the keymap or the shared constant
            assert SUPPORT_MENU_KEY in line, f"{module} advertises a different key: {line}"
