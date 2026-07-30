"""Headless tests for fediverse onboarding in the Add Account dialog.

Exercises the non-modal network-switch logic (guidance text, sign-in
enablement, instance defaulting) without opening a browser or a modal.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.ui import app as app_mod  # noqa: E402


@pytest.fixture
def app():
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def _select(dlg, network: str) -> None:
    dlg.network.SetStringSelection(network)
    dlg._on_network(None)


def test_fediverse_networks_are_offered(app):
    dlg = app_mod.AddAccountDialog(None)
    try:
        choices = [dlg.network.GetString(i) for i in range(dlg.network.GetCount())]
        for net in ("mastodon", "pixelfed", "gotosocial", "firefish", "lemmy"):
            assert net in choices
    finally:
        dlg.Destroy()


def test_mastodon_compatible_uses_browser_signin(app):
    dlg = app_mod.AddAccountDialog(None)
    try:
        _select(dlg, "pixelfed")
        assert dlg.signin_btn.IsEnabled() is True
        assert "Pixelfed" in dlg.guidance.GetLabel()
        # A Mastodon preset server must not leak into a Pixelfed account.
        assert dlg.instance.GetValue() not in app_mod.INSTANCE_PRESETS
    finally:
        dlg.Destroy()


def test_lemmy_reads_publicly_without_signin(app):
    dlg = app_mod.AddAccountDialog(None)
    try:
        _select(dlg, "lemmy")
        assert dlg.signin_btn.IsEnabled() is False
        assert "Lemmy" in dlg.guidance.GetLabel()
        dlg.instance.SetValue("lemmy.world")
        acct = dlg._temp_account()
        assert acct.network == "lemmy"
        assert acct.instance == "lemmy.world"
    finally:
        dlg.Destroy()
