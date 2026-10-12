"""Each app offers back the edition the listener is actually running.

``_pick_asset`` (QUILL's own updater) learned this in August, after two users a
month apart reported being handed the wrong download. ``_app_asset_url`` -- the
path every companion app and QUILL Lite takes -- learned it later.

Since 2026-10-11 every app ships two downloads: the installer and the portable
zip. Older releases still carry the retired thin ``-Lite-Setup-`` installer and
the ``-Companion-`` zip, and "Go back to an earlier version" can reach those
releases, so the rule these tests pin is that neither retired asset is ever
offered, whatever the listing order and whichever way the app asks.
"""

from __future__ import annotations

import pytest

from quill.core import install_edition as edition
from quill.core.updates import _app_asset_url


def _assets(prefix: str, version: str) -> list[dict[str, str]]:
    names = [
        f"{prefix}-Companion-{version}.zip",
        f"{prefix}-Lite-Setup-{version}.exe",
        f"{prefix}-Portable-{version}.zip",
        f"{prefix}-Setup-Shared-{version}.exe",
    ]
    return [{"name": n, "browser_download_url": f"https://example.test/{n}"} for n in names]


#: Old releases that still carry all four assets.
LITE = _assets("QuillLite", "1.0.0")
BEACON = _assets("Quill-Beacon", "3.0.0")

_RETIRED = ("Companion", "Lite-Setup")


def _retired(url: str) -> bool:
    name = url.rsplit("/", 1)[-1]
    # "QuillLite-Setup-Shared" contains "Lite-Setup" as a substring; strip the
    # product name first, as install_edition.matches_asset does.
    name = name.removeprefix("QuillLite")
    return any(word in name for word in _RETIRED)


@pytest.mark.parametrize(
    ("running", "expected"),
    [
        (edition.INSTALLER_FULL, "QuillLite-Setup-Shared-1.0.0.exe"),
        (edition.PORTABLE, "QuillLite-Portable-1.0.0.zip"),
    ],
)
def test_quilllite_offers_the_edition_you_are_running(monkeypatch, running, expected) -> None:
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: running)
    url = _app_asset_url(LITE, "QuillLite", prefer_portable=(running == edition.PORTABLE))
    assert url.endswith(expected)


def test_the_answer_does_not_depend_on_how_github_lists_the_assets(monkeypatch) -> None:
    """The old bug in one line: two -setup-*.exe assets, and the last one won."""
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    forward = _app_asset_url(LITE, "QuillLite", prefer_portable=False)
    backward = _app_asset_url(list(reversed(LITE)), "QuillLite", prefer_portable=False)
    assert forward == backward
    assert forward.endswith("QuillLite-Setup-Shared-1.0.0.exe")


@pytest.mark.parametrize("assets,prefix", [(LITE, "QuillLite"), (BEACON, "Quill-Beacon")])
@pytest.mark.parametrize("running", [edition.INSTALLER_FULL, edition.PORTABLE, ""])
@pytest.mark.parametrize("match", [True, False])
@pytest.mark.parametrize("portable", [True, False])
@pytest.mark.parametrize("reverse", [True, False])
def test_a_retired_download_is_never_offered(
    monkeypatch, assets, prefix, running, match, portable, reverse
) -> None:
    """Whatever the running edition, the switch, the portable hint or the
    listing order: an old release's thin installer and Companion zip stay put."""
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: running)
    listed = list(reversed(assets)) if reverse else assets
    url = _app_asset_url(listed, prefix, prefer_portable=portable, match_edition=match)
    assert url
    assert not _retired(url), url


def test_a_release_with_only_retired_assets_offers_nothing(monkeypatch) -> None:
    """Better no update than the wrong one."""
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    retired_only = [a for a in BEACON if _retired(a["name"])]
    assert _app_asset_url(retired_only, "Quill-Beacon", prefer_portable=False) == ""
    assert _app_asset_url(retired_only, "Quill-Beacon", prefer_portable=True) == ""


def test_a_release_missing_this_edition_still_offers_something(monkeypatch) -> None:
    """Fall-through, not nothing: a release that published no portable zip
    still hands a portable listener the installer rather than no update."""
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: edition.PORTABLE)
    without_portable = [a for a in LITE if "Portable" not in a["name"]]
    assert _app_asset_url(without_portable, "QuillLite", prefer_portable=True).endswith(
        "QuillLite-Setup-Shared-1.0.0.exe"
    )


def test_a_source_run_with_no_edition_falls_back_to_the_portable_hint(monkeypatch) -> None:
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: "")
    assert _app_asset_url(LITE, "QuillLite", prefer_portable=True).endswith(
        "QuillLite-Portable-1.0.0.zip"
    )
    assert _app_asset_url(LITE, "QuillLite", prefer_portable=False).endswith(
        "QuillLite-Setup-Shared-1.0.0.exe"
    )


#: What every app publishes since 2026-10-11: an installer and a portable zip.
#: Spelled out rather than filtered out of LITE -- "QuillLite-Setup-Shared"
#: contains the substring "Lite-Setup", so the obvious filter silently drops the
#: installer. That is the same trap install_edition.matches_asset carries an
#: app_prefix to avoid.
LITE_TWO = [
    a
    for a in LITE
    if a["name"] in {"QuillLite-Setup-Shared-1.0.0.exe", "QuillLite-Portable-1.0.0.zip"}
]


@pytest.mark.parametrize(
    ("portable", "expected"),
    [
        (False, "QuillLite-Setup-Shared-1.0.0.exe"),
        (True, "QuillLite-Portable-1.0.0.zip"),
    ],
)
def test_without_the_edition_step_portable_alone_decides(monkeypatch, portable, expected) -> None:
    """``match_edition=False``: whatever detect() says, it must not reach the answer."""
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    url = _app_asset_url(LITE_TWO, "QuillLite", prefer_portable=portable, match_edition=False)
    assert url.endswith(expected)


@pytest.mark.parametrize(
    ("running", "expected"),
    [
        (edition.INSTALLER_FULL, "QuillLite-Setup-Shared-1.0.0.exe"),
        (edition.PORTABLE, "QuillLite-Portable-1.0.0.zip"),
    ],
)
def test_with_the_edition_step_the_running_edition_decides(monkeypatch, running, expected) -> None:
    """The apps on the default (Inkwell, Player, Studio...) ask detect(), and it
    can only answer one of the same two downloads."""
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: running)
    # The portable hint deliberately disagrees: the edition the copy reports wins.
    url = _app_asset_url(
        LITE_TWO, "QuillLite", prefer_portable=(running != edition.PORTABLE), match_edition=True
    )
    assert url.endswith(expected)


def test_another_apps_assets_are_never_picked(monkeypatch) -> None:
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    assert _app_asset_url(BEACON, "QuillLite", prefer_portable=False) == ""


def test_a_non_https_url_is_ignored(monkeypatch) -> None:
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    spoofed = [
        {
            "name": "QuillLite-Setup-Shared-1.0.0.exe",
            "browser_download_url": "http://example.test/evil.exe",
        }
    ]
    assert _app_asset_url(spoofed, "QuillLite", prefer_portable=False) == ""


RADIO_TWO = [
    {"name": n, "browser_download_url": f"https://example.test/{n}"}
    for n in ("Quill-Radio-Portable-3.0.0.zip", "Quill-Radio-Setup-Shared-3.0.0.exe")
]


@pytest.mark.parametrize(
    ("portable", "expected"),
    [
        (False, "Quill-Radio-Setup-Shared-3.0.0.exe"),
        (True, "Quill-Radio-Portable-3.0.0.zip"),
    ],
)
def test_quill_radio_is_a_two_asset_app(monkeypatch, portable, expected) -> None:
    """Radio publishes two downloads since 3.0.0, and answers as QUILL Lite does."""
    monkeypatch.setattr(edition, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    url = _app_asset_url(RADIO_TWO, "Quill-Radio", prefer_portable=portable, match_edition=False)
    assert url.endswith(expected)


def test_quill_radio_asks_the_two_asset_question() -> None:
    """The wiring half: both of Radio's update checks opt out of the edition step.

    Read from source because the calls sit inside a wx menu binding and a launch
    hook; what matters is that no call site was left on the default.
    """
    from pathlib import Path

    import quill.apps.radio as radio

    assert radio._MATCH_EDITION is False
    source = Path(radio.__file__).read_text(encoding="utf-8")
    # The Help menu's update row moved with the menu bar (F-08, 2026-10-03).
    source += Path(radio.__file__).with_name("radio_menu_bar.py").read_text(encoding="utf-8")
    calls = source.count("self.check_for_app_updates(")
    assert calls >= 2
    assert source.count("match_edition=_MATCH_EDITION") == calls


@pytest.mark.parametrize("silent", [False, True])
def test_quill_cast_asks_the_two_asset_question(monkeypatch, silent) -> None:
    """Cast publishes two downloads from its first release (2026-10-05): Help >
    Check for Updates and the quiet launch check both opt out of the edition
    step, as Radio and QUILL Lite do."""
    import quill.ui.updates.shell as shell
    from quill.apps.podcasts_preferences import CastPreferencesMixin

    monkeypatch.setattr(shell, "installed_app_version", lambda _key: "2.0.0")
    calls: list[dict[str, object]] = []

    class _Host(CastPreferencesMixin):
        def check_for_app_updates(self, **kwargs: object) -> None:
            calls.append(kwargs)

    _Host()._check_cast_updates(silent=silent)

    assert calls == [
        {
            "repo_slug": "Community-Access/quill",
            "current_version": "2.0.0",
            "app_key": "cast",
            "silent_no_update": silent,
            "match_edition": False,
        }
    ]
