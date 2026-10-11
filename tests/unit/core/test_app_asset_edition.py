"""Each app offers back the edition the listener is actually running.

``_pick_asset`` (QUILL's own updater) learned this in August, after two users a
month apart reported being handed the wrong download. ``_app_asset_url`` -- the
path every companion app and QUILL Lite takes -- never did, so the same two
failures stayed live there:

* of the two ``-setup-*.exe`` assets it took whichever GitHub listed **last**,
  so a full-edition user could be handed the thin installer or not depending on
  listing order;
* a Companion listener, whose asset is a zip that is not the portable one, was
  handed an ``.exe`` that cannot install their copy at all.
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


LITE = _assets("QuillLite", "1.0.0")
#: Quill Radio shipped four until 3.0.0 and QUILL Cast never did publicly (two
#: since its first release, 2.0.0); QuillBeacon still does, so it is the
#: four-asset example now.
BEACON = _assets("Quill-Beacon", "3.0.0")


@pytest.mark.parametrize(
    ("running", "expected"),
    [
        (edition.INSTALLER_FULL, "QuillLite-Setup-Shared-1.0.0.exe"),
        (edition.INSTALLER_LITE, "QuillLite-Lite-Setup-1.0.0.exe"),
        (edition.PORTABLE, "QuillLite-Portable-1.0.0.zip"),
        (edition.COMPANION, "QuillLite-Companion-1.0.0.zip"),
    ],
)
def test_quilllite_offers_the_edition_you_are_running(monkeypatch, running, expected) -> None:
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: running)
    url = _app_asset_url(LITE, "QuillLite", prefer_portable=(running == edition.PORTABLE))
    assert url.endswith(expected)


def test_the_answer_does_not_depend_on_how_github_lists_the_assets(monkeypatch) -> None:
    """The bug in one line: two -setup-*.exe assets, and the last one won."""
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    forward = _app_asset_url(LITE, "QuillLite", prefer_portable=False)
    backward = _app_asset_url(list(reversed(LITE)), "QuillLite", prefer_portable=False)
    assert forward == backward
    assert forward.endswith("QuillLite-Setup-Shared-1.0.0.exe")


def test_a_companion_listener_is_never_handed_an_exe(monkeypatch) -> None:
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.COMPANION)
    assert _app_asset_url(BEACON, "Quill-Beacon", prefer_portable=False).endswith(
        "Quill-Beacon-Companion-3.0.0.zip"
    )


def test_a_release_missing_this_edition_still_offers_something(monkeypatch) -> None:
    """Fall-through, not nothing: a release that published no Companion zip
    should still hand a Companion listener an installable asset rather than
    leaving them with no update at all."""
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.COMPANION)
    without_companion = [a for a in LITE if "Companion" not in a["name"]]
    assert _app_asset_url(without_companion, "QuillLite", prefer_portable=False).endswith(".exe")


def test_a_source_run_with_no_edition_falls_back_to_the_old_rules(monkeypatch) -> None:
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: "")
    assert _app_asset_url(LITE, "QuillLite", prefer_portable=True).endswith(
        "QuillLite-Portable-1.0.0.zip"
    )
    assert _app_asset_url(LITE, "QuillLite", prefer_portable=False).endswith(".exe")


#: What QUILL Lite publishes since 2026-09-15: an installer and a portable zip.
#: Spelled out rather than filtered out of LITE -- "QuillLite-Setup-Shared"
#: contains the substring "Lite-Setup", so the obvious filter silently drops the
#: full installer. That is the same trap install_edition.matches_asset carries an
#: app_prefix to avoid, and it caught this test on the first run.
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
def test_two_assets_are_decided_by_portable_alone(monkeypatch, portable, expected) -> None:
    """QUILL Lite's rule, and the whole of it: portable, or not.

    ``match_edition=False`` is the app saying it publishes two downloads rather
    than four, so there is no edition question to get wrong.
    """
    import quill.core.install_edition as edition_module

    # Whatever detect() says, it must not reach the answer.
    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.COMPANION)
    url = _app_asset_url(LITE_TWO, "QuillLite", prefer_portable=portable, match_edition=False)
    assert url.endswith(expected)


def test_the_companion_misdetection_cannot_reach_a_two_asset_app(monkeypatch) -> None:
    """The reason this switch exists rather than being left to luck.

    An installed QuillVille app resolves QUILL_APP_ROOT to the SHARED RUNTIME's
    folder -- where there is no edition marker, no uninstaller, no data folder --
    so detect() answers "companion" for every one of them (verified
    2026-09-15). With the edition step on, an installed QUILL Lite is asking a
    chooser that believes it is something it is not, and comes out right only
    because no Companion zip is published any more. With it off, the question
    is never asked.
    """
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.COMPANION)
    matched = _app_asset_url(LITE_TWO, "QuillLite", prefer_portable=False, match_edition=True)
    skipped = _app_asset_url(LITE_TWO, "QuillLite", prefer_portable=False, match_edition=False)
    assert matched == skipped, "same answer today -- by luck on one side, by rule on the other"
    assert skipped.endswith("QuillLite-Setup-Shared-1.0.0.exe")


def test_the_edition_step_is_untouched_for_the_apps_that_ship_four(monkeypatch) -> None:
    """The other eight still answer by edition; the switch is opt-in."""
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.COMPANION)
    assert _app_asset_url(BEACON, "Quill-Beacon", prefer_portable=False).endswith(
        "Quill-Beacon-Companion-3.0.0.zip"
    )


def test_another_apps_assets_are_never_picked(monkeypatch) -> None:
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    assert _app_asset_url(BEACON, "QuillLite", prefer_portable=False) == ""


def test_a_non_https_url_is_ignored(monkeypatch) -> None:
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
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
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.COMPANION)
    url = _app_asset_url(RADIO_TWO, "Quill-Radio", prefer_portable=portable, match_edition=False)
    assert url.endswith(expected)


def test_quill_radio_asks_the_two_asset_question() -> None:
    """The wiring half: both of Radio's update checks opt out of the edition step.

    Read from source because the calls sit inside a wx menu binding and a launch
    hook; what matters is that no call site was left on the four-way default.
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
