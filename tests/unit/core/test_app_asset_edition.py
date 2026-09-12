"""Each app offers back the edition the listener is actually running.

``_pick_asset`` (QUILL's own updater) learned this in August, after two users a
month apart reported being handed the wrong download. ``_app_asset_url`` -- the
path every companion app and QuillLite takes -- never did, so the same two
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
RADIO = _assets("Quill-Radio", "3.0.0")


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
    assert _app_asset_url(RADIO, "Quill-Radio", prefer_portable=False).endswith(
        "Quill-Radio-Companion-3.0.0.zip"
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


def test_another_apps_assets_are_never_picked(monkeypatch) -> None:
    import quill.core.install_edition as edition_module

    monkeypatch.setattr(edition_module, "detect", lambda *_a, **_k: edition.INSTALLER_FULL)
    assert _app_asset_url(RADIO, "QuillLite", prefer_portable=False) == ""


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
